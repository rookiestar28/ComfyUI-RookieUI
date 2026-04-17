from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from rookieui.contracts.prompt_workbench import (
    DEFAULT_PROMPT_WORKBENCH_AI_ASSIST_PRESET,
    PromptWorkbenchProviderCatalogEntry,
    build_prompt_workbench_contract_meta,
    get_prompt_workbench_provider_catalog_entry,
    get_prompt_workbench_provider_execution_state,
)
from rookieui.services.prompt_workbench_openai import (
    PromptWorkbenchOpenAIProviderError,
    openai_chat_completion,
)
from rookieui.services.prompt_workbench_state import load_prompt_workbench_store

_MAX_PROMPT_ASSIST_LENGTH = 16000


class PromptWorkbenchAssistProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class PromptWorkbenchAssistExecutionResult:
    provider_id: str
    provider_title: str
    language: str
    theme_style: str
    instruction_preset: str
    image_description: str
    generated_prompt: str

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["contract"] = build_prompt_workbench_contract_meta(surface="prompt_tools_assist")
        return payload


def _normalize_text(value: object, *, max_length: int) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def _normalize_assist_payload(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("Prompt-workbench assist payload must be an object.")
    image_description = _normalize_text(payload.get("image_description"), max_length=_MAX_PROMPT_ASSIST_LENGTH)
    if not image_description:
        raise ValueError("Prompt-workbench assist requests require image_description.")
    return {
        "provider": _normalize_text(payload.get("provider"), max_length=80),
        "instruction_preset": _normalize_text(
            payload.get("instruction_preset"),
            max_length=_MAX_PROMPT_ASSIST_LENGTH,
        ),
        "image_description": image_description,
        "language": _normalize_text(payload.get("language"), max_length=32) or "en",
        "theme_style": _normalize_text(payload.get("theme_style"), max_length=80) or "rookieui_classic",
    }


def _effective_ai_assist_provider(provider_override: str) -> tuple[PromptWorkbenchProviderCatalogEntry, dict[str, Any], str]:
    store = load_prompt_workbench_store()
    assist_config = store["config"]["ai_assist"]
    provider_id = provider_override or str(assist_config.get("default_provider", "")).strip()
    if not provider_id:
        raise ValueError("No prompt-workbench AI assist provider is configured.")

    entry = get_prompt_workbench_provider_catalog_entry(provider_id)
    if entry is None or "ai_assist" not in entry.surface_scopes:
        raise ValueError("Requested prompt-workbench AI assist provider is not in the AI assist catalog.")
    if get_prompt_workbench_provider_execution_state(entry.provider_id, surface="ai_assist") != "shipped":
        raise ValueError("Requested prompt-workbench AI assist provider is not shipped in RookieUI.")
    providers = assist_config.get("providers", {})
    provider_config = providers.get(provider_id, {}) if isinstance(providers, dict) else {}
    instruction_preset = _normalize_text(
        assist_config.get("instruction_preset"),
        max_length=_MAX_PROMPT_ASSIST_LENGTH,
    ) or DEFAULT_PROMPT_WORKBENCH_AI_ASSIST_PRESET
    return entry, provider_config if isinstance(provider_config, dict) else {}, instruction_preset


def _run_openai_ai_assist(
    *,
    entry: PromptWorkbenchProviderCatalogEntry,
    provider_config: dict[str, Any],
    instruction_preset: str,
    image_description: str,
    language: str,
) -> str:
    if entry.provider_id != "openai":
        raise PromptWorkbenchAssistProviderError("Prompt-workbench AI assist provider is not implemented.")
    output_language = "English" if language.lower() == "en" else language
    system_prompt = (
        "You generate Stable Diffusion prompts for image-generation workflows. "
        f"Return the final prompt in {output_language}. "
        "Keep the result concise, comma-separated when appropriate, and compatible with A1111-style prompt authoring. "
        "Preserve any inline prompt syntax the user already provides, and return prompt text only."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": instruction_preset},
        {"role": "user", "content": image_description},
    ]
    return openai_chat_completion(provider_config=provider_config, messages=messages, temperature=0.4)


def assist_prompt_workbench_payload(payload: object) -> PromptWorkbenchAssistExecutionResult:
    normalized = _normalize_assist_payload(payload)
    entry, provider_config, stored_preset = _effective_ai_assist_provider(normalized["provider"])
    instruction_preset = normalized["instruction_preset"] or stored_preset
    try:
        generated_prompt = _run_openai_ai_assist(
            entry=entry,
            provider_config=provider_config,
            instruction_preset=instruction_preset,
            image_description=normalized["image_description"],
            language=normalized["language"],
        )
    except PromptWorkbenchOpenAIProviderError as exc:
        raise PromptWorkbenchAssistProviderError(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - error normalization path
        raise PromptWorkbenchAssistProviderError(str(exc)) from exc

    return PromptWorkbenchAssistExecutionResult(
        provider_id=entry.provider_id,
        provider_title=entry.title,
        language=normalized["language"],
        theme_style=normalized["theme_style"],
        instruction_preset=instruction_preset,
        image_description=normalized["image_description"],
        generated_prompt=generated_prompt,
    )
