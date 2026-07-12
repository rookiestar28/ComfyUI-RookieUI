from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib import parse

from rookieui.contracts.prompt_workbench import (
    PromptWorkbenchProviderCatalogEntry,
    build_prompt_workbench_contract_meta,
    build_prompt_workbench_provider_catalog_payload,
    get_prompt_workbench_provider_catalog_entry,
    get_prompt_workbench_provider_execution_state,
)
from rookieui.services.prompt_workbench_openai import (
    PromptWorkbenchOpenAIProviderError,
    bounded_provider_timeout,
    openai_chat_completion,
    urlopen_json,
    validate_provider_endpoint,
)
from rookieui.services.prompt_workbench_state import _prompt_workbench_root, load_prompt_workbench_store
from rookieui.services.prompt_workbench_tokens import parse_prompt_workbench_tokens

_MAX_TRANSLATE_ITEMS = 32
_MAX_TRANSLATE_TEXT_LENGTH = 16000


class PromptWorkbenchTranslateProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class PromptWorkbenchTranslationExecutionResult:
    provider_id: str
    provider_title: str
    mode: str
    from_lang: str
    to_lang: str
    translated_text: str | None = None
    translated_texts: list[str] | None = None
    provider_layer: str = ""
    dictionary_hits: list[str] | None = None
    dictionary_misses: list[str] | None = None
    blacklisted_terms: list[str] | None = None
    fallback_provider_id: str = ""
    dictionary_only: bool = False

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["contract"] = build_prompt_workbench_contract_meta(surface="prompt_tools_translate")
        return payload


def _normalize_text(value: object, *, max_length: int) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def _normalize_translate_payload(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Prompt-workbench translate payload must be an object.")

    single_text = _normalize_text(payload.get("text"), max_length=_MAX_TRANSLATE_TEXT_LENGTH)
    batch_payload = payload.get("texts")
    batch_texts: list[str] = []
    if isinstance(batch_payload, list):
        for raw_text in batch_payload[:_MAX_TRANSLATE_ITEMS]:
            batch_texts.append(_normalize_text(raw_text, max_length=_MAX_TRANSLATE_TEXT_LENGTH))

    if single_text and batch_texts:
        raise ValueError("Provide either text or texts, not both.")
    if not single_text and not batch_texts:
        raise ValueError("Prompt-workbench translate requests require text or texts.")

    return {
        "provider": _normalize_text(payload.get("provider"), max_length=80),
        "from_lang": _normalize_text(payload.get("from_lang"), max_length=32) or "auto",
        "to_lang": _normalize_text(payload.get("to_lang"), max_length=32) or "en",
        "text": single_text,
        "texts": batch_texts,
        "dictionary_first": bool(payload.get("dictionary_first")),
        "dictionary_only": bool(payload.get("dictionary_only"))
        or bool(payload.get("auto_translate"))
        or _normalize_text(payload.get("translation_mode"), max_length=40) == "auto",
        "fallback_provider": _normalize_text(payload.get("fallback_provider"), max_length=80),
    }


def _provider_layer(provider_id: str) -> str:
    if provider_id == "csv_tag_dictionary":
        return "csv_tag_dictionary"
    if provider_id == "mymemory_free":
        return "shipped_lightweight"
    if provider_id == "openai":
        return "optional_openai_compatible"
    if provider_id == "local_host_model":
        return "optional_local_host_model"
    return "reference_only"


def _effective_translation_provider(provider_override: str) -> tuple[PromptWorkbenchProviderCatalogEntry, dict[str, Any]]:
    store = load_prompt_workbench_store()
    translation_config = store["config"]["translation"]
    provider_id = provider_override or str(translation_config.get("default_provider", "")).strip()
    if not provider_id:
        raise ValueError("No prompt-workbench translation provider is configured.")

    entry = get_prompt_workbench_provider_catalog_entry(provider_id)
    if entry is None or "translation" not in entry.surface_scopes:
        raise ValueError("Requested prompt-workbench translation provider is not in the translation catalog.")
    if get_prompt_workbench_provider_execution_state(entry.provider_id, surface="translation") != "shipped":
        raise ValueError("Requested prompt-workbench translation provider is not shipped in RookieUI.")
    providers = translation_config.get("providers", {})
    provider_config = providers.get(provider_id, {}) if isinstance(providers, dict) else {}
    return entry, provider_config if isinstance(provider_config, dict) else {}


def _provider_availability(
    entry: PromptWorkbenchProviderCatalogEntry,
    provider_config: dict[str, Any],
    *,
    surface: str,
) -> dict[str, Any]:
    execution_state = get_prompt_workbench_provider_execution_state(entry.provider_id, surface=surface)
    if execution_state == "reference_only":
        return {"status": "reference_only", "detail": "Provider exists only as a migration reference entry."}
    if execution_state == "deferred":
        return {"status": "deferred", "detail": "Provider catalog entry is accepted, but execution is deferred."}

    missing_required: list[str] = []
    for field_spec in entry.to_payload()["config_fields"]:
        if not field_spec.get("required"):
            continue
        field_key = str(field_spec.get("key", "")).strip()
        field_value = provider_config.get(field_key)
        if isinstance(field_value, str):
            if not field_value.strip():
                missing_required.append(field_key)
        elif field_value in (None, False):
            missing_required.append(field_key)

    if missing_required:
        return {
            "status": "configuration_required",
            "detail": f"Missing required provider fields: {', '.join(missing_required)}.",
        }
    return {"status": "ready", "detail": "Provider is configured for execution."}


def build_prompt_workbench_provider_payload() -> dict[str, Any]:
    payload = build_prompt_workbench_provider_catalog_payload()
    store = load_prompt_workbench_store()
    surfaces_payload = payload["surfaces"]
    for surface_name in ("translation", "ai_assist"):
        surface_config = store["config"].get(surface_name, {})
        configured_default_provider = ""
        providers_config = surface_config.get("providers", {}) if isinstance(surface_config, dict) else {}
        if isinstance(surface_config, dict):
            configured_default_provider = str(surface_config.get("default_provider", "")).strip()
        surface_payload = surfaces_payload[surface_name]
        for provider_entry in surface_payload["providers"]:
            provider_id = provider_entry["provider_id"]
            provider_config = providers_config.get(provider_id, {}) if isinstance(providers_config, dict) else {}
            catalog_entry = get_prompt_workbench_provider_catalog_entry(provider_id)
            availability = (
                _provider_availability(
                    catalog_entry,
                    provider_config if isinstance(provider_config, dict) else {},
                    surface=surface_name,
                )
                if catalog_entry is not None
                else {"status": "unavailable", "detail": "Provider catalog entry is missing."}
            )
            provider_entry["availability"] = availability
            provider_entry["configured"] = isinstance(provider_config, dict) and bool(provider_config)
            provider_entry["default_selected"] = provider_id == configured_default_provider
            provider_entry["provider_layer"] = _provider_layer(provider_id)
        surface_payload["default_provider"] = configured_default_provider
        if surface_name == "translation":
            surface_payload["provider_layer_order"] = [
                "csv_tag_dictionary",
                "shipped_lightweight",
                "optional_openai_compatible",
                "optional_local_host_model",
                "reference_only",
            ]
    return payload


def _translate_via_openai(text: str, *, from_lang: str, to_lang: str, provider_config: dict[str, Any]) -> str:
    system_prompt = (
        f"Translate the user's Stable Diffusion prompt from {from_lang} to {to_lang}. "
        "Preserve prompt syntax, weighting parentheses/brackets, BREAK, AND, inline <lora:...> tokens, "
        "embedding: tokens, numbers, and comma-separated structure. Return only the translated prompt text."
    )
    try:
        return openai_chat_completion(
            provider_config=provider_config,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
        )
    except PromptWorkbenchOpenAIProviderError as exc:
        raise PromptWorkbenchTranslateProviderError(str(exc)) from exc


def _translate_via_mymemory(text: str, *, from_lang: str, to_lang: str, provider_config: dict[str, Any]) -> str:
    base_url = validate_provider_endpoint(
        provider_config.get("base_url"),
        default_url="https://api.mymemory.translated.net/get",
        allow_custom_endpoint=provider_config.get("allow_custom_endpoint") is True,
    )
    timeout_seconds = bounded_provider_timeout(provider_config.get("timeout_seconds", 15), default=15)
    query = {
        "q": text,
        "langpair": f"{from_lang}|{to_lang}",
    }
    email = str(provider_config.get("email", "")).strip()
    if email:
        query["de"] = email
    response_payload = urlopen_json(
        f"{base_url}?{parse.urlencode(query)}",
        timeout=timeout_seconds,
    )
    response_data = response_payload.get("responseData", {})
    translated_text = str(response_data.get("translatedText", "")).strip() if isinstance(response_data, dict) else ""
    if not translated_text:
        raise PromptWorkbenchTranslateProviderError("MyMemory translation response returned empty content.")
    return translated_text


def _translation_dictionary_paths(to_lang: str) -> tuple[Path, ...]:
    catalog_root = _prompt_workbench_root() / "catalogs"
    normalized_lang = str(to_lang or "").strip()
    candidates = []
    if normalized_lang:
        candidates.append(catalog_root / f"translation_dictionary.{normalized_lang}.csv")
    candidates.append(catalog_root / "translation_dictionary.csv")
    return tuple(candidates)


def _load_translation_dictionary(to_lang: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for path in _translation_dictionary_paths(to_lang):
        if not path.exists() or not path.is_file():
            continue
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            for row_index, row in enumerate(reader):
                if len(row) < 2:
                    continue
                source = _normalize_text(row[0], max_length=512)
                target = _normalize_text(row[1], max_length=512)
                if row_index == 0 and source.lower() in {"source", "tag", "en"}:
                    continue
                if source and target:
                    entries[source.lower()] = target
    return entries


def _translation_blacklist_terms() -> set[str]:
    store = load_prompt_workbench_store()
    blacklist_state = store.get("blacklist", {})
    entries = blacklist_state.get("translation_entries", []) if isinstance(blacklist_state, dict) else []
    if not isinstance(entries, list):
        return set()
    return {
        _normalize_text(entry, max_length=512).lower()
        for entry in entries
        if _normalize_text(entry, max_length=512)
    }


def _translate_via_dictionary(
    text: str,
    *,
    to_lang: str,
    translation_blacklist: set[str] | None = None,
) -> tuple[str, list[str], list[str], list[str]]:
    dictionary = _load_translation_dictionary(to_lang)
    tokens = parse_prompt_workbench_tokens(text)
    translated_tokens: list[str] = []
    hits: list[str] = []
    misses: list[str] = []
    blacklisted_terms: list[str] = []
    blacklist = translation_blacklist or set()
    for token in tokens:
        lookup_key = token.raw_text.lower()
        if lookup_key in blacklist:
            translated_tokens.append(token.raw_text)
            blacklisted_terms.append(token.raw_text)
            continue
        translated = dictionary.get(lookup_key)
        if translated:
            translated_tokens.append(translated)
            hits.append(token.raw_text)
        else:
            translated_tokens.append(token.raw_text)
            misses.append(token.raw_text)
    return ", ".join(translated_tokens), hits, misses, blacklisted_terms


def _translate_text_with_entry(
    entry: PromptWorkbenchProviderCatalogEntry,
    text: str,
    *,
    from_lang: str,
    to_lang: str,
    provider_config: dict[str, Any],
) -> str:
    if entry.provider_id == "openai":
        return _translate_via_openai(
            text,
            from_lang=from_lang,
            to_lang=to_lang,
            provider_config=provider_config,
        )
    if entry.provider_id == "mymemory_free":
        return _translate_via_mymemory(
            text,
            from_lang=from_lang,
            to_lang=to_lang,
            provider_config=provider_config,
        )
    raise PromptWorkbenchTranslateProviderError("Prompt-workbench translation provider is not implemented.")


def translate_prompt_workbench_payload(payload: object) -> PromptWorkbenchTranslationExecutionResult:
    normalized = _normalize_translate_payload(payload)
    provider_override = "csv_tag_dictionary" if normalized["dictionary_only"] else normalized["provider"]
    entry, provider_config = _effective_translation_provider(provider_override)
    availability = _provider_availability(entry, provider_config, surface="translation")
    if availability["status"] != "ready":
        raise ValueError(str(availability["detail"]))

    texts = normalized["texts"] or ([normalized["text"]] if normalized["text"] else [])
    translated_texts: list[str] = []
    dictionary_hits: list[str] = []
    dictionary_misses: list[str] = []
    blacklisted_terms: list[str] = []
    fallback_provider_id = ""
    translation_blacklist = _translation_blacklist_terms()
    for text in texts:
        if not text:
            translated_texts.append("")
            continue
        try:
            if entry.provider_id == "csv_tag_dictionary":
                translated, hits, misses, skipped = _translate_via_dictionary(
                    text,
                    to_lang=normalized["to_lang"],
                    translation_blacklist=translation_blacklist,
                )
                translated_texts.append(translated)
                dictionary_hits.extend(hits)
                dictionary_misses.extend(misses)
                blacklisted_terms.extend(skipped)
            elif normalized["dictionary_first"]:
                translated, hits, misses, skipped = _translate_via_dictionary(
                    text,
                    to_lang=normalized["to_lang"],
                    translation_blacklist=translation_blacklist,
                )
                dictionary_hits.extend(hits)
                dictionary_misses.extend(misses)
                blacklisted_terms.extend(skipped)
                if not misses:
                    translated_texts.append(translated)
                    continue
                fallback_provider_id = entry.provider_id
                dictionary = _load_translation_dictionary(normalized["to_lang"])
                translated_parts: list[str] = []
                for token in parse_prompt_workbench_tokens(text):
                    lookup_key = token.raw_text.lower()
                    if lookup_key in translation_blacklist:
                        translated_parts.append(token.raw_text)
                        continue
                    dictionary_hit = dictionary.get(token.raw_text.lower())
                    if dictionary_hit:
                        translated_parts.append(dictionary_hit)
                    else:
                        translated_parts.append(
                            _translate_text_with_entry(
                                entry,
                                token.raw_text,
                                from_lang=normalized["from_lang"],
                                to_lang=normalized["to_lang"],
                                provider_config=provider_config,
                            )
                        )
                translated_texts.append(", ".join(translated_parts))
            else:
                tokens = parse_prompt_workbench_tokens(text)
                skipped = [
                    token.raw_text
                    for token in tokens
                    if token.raw_text.lower() in translation_blacklist
                ]
                if skipped:
                    blacklisted_terms.extend(skipped)
                    translated_parts = []
                    for token in tokens:
                        if token.raw_text.lower() in translation_blacklist:
                            translated_parts.append(token.raw_text)
                        else:
                            translated_parts.append(
                                _translate_text_with_entry(
                                    entry,
                                    token.raw_text,
                                    from_lang=normalized["from_lang"],
                                    to_lang=normalized["to_lang"],
                                    provider_config=provider_config,
                                )
                            )
                    translated_texts.append(", ".join(translated_parts))
                else:
                    translated_texts.append(
                        _translate_text_with_entry(
                            entry,
                            text,
                            from_lang=normalized["from_lang"],
                            to_lang=normalized["to_lang"],
                            provider_config=provider_config,
                        )
                    )
        except PromptWorkbenchTranslateProviderError:
            raise
        except Exception as exc:  # pragma: no cover - error normalization path
            raise PromptWorkbenchTranslateProviderError(str(exc)) from exc

    if normalized["texts"]:
        return PromptWorkbenchTranslationExecutionResult(
            provider_id=entry.provider_id,
            provider_title=entry.title,
            mode="batch",
            from_lang=normalized["from_lang"],
            to_lang=normalized["to_lang"],
            translated_texts=translated_texts,
            provider_layer=_provider_layer(entry.provider_id),
            dictionary_hits=dictionary_hits,
            dictionary_misses=dictionary_misses,
            blacklisted_terms=blacklisted_terms,
            fallback_provider_id=fallback_provider_id,
            dictionary_only=normalized["dictionary_only"],
        )
    return PromptWorkbenchTranslationExecutionResult(
        provider_id=entry.provider_id,
        provider_title=entry.title,
        mode="single",
        from_lang=normalized["from_lang"],
        to_lang=normalized["to_lang"],
        translated_text=translated_texts[0] if translated_texts else "",
        provider_layer=_provider_layer(entry.provider_id),
        dictionary_hits=dictionary_hits,
        dictionary_misses=dictionary_misses,
        blacklisted_terms=blacklisted_terms,
        fallback_provider_id=fallback_provider_id,
        dictionary_only=normalized["dictionary_only"],
    )
