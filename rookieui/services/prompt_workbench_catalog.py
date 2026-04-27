from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from rookieui.contracts.prompt_workbench import (
    build_prompt_workbench_contract_meta,
    normalize_prompt_workbench_language_code,
)
from rookieui.services.model_inventory import discover_model_inventory
from rookieui.services.prompt_workbench_state import _prompt_workbench_root

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_DATA_ROOT = _WORKSPACE_ROOT / "rookieui" / "data" / "prompt_workbench"
_MAX_CATALOG_ENTRIES = 500
_MAX_CATALOG_TEXT_LENGTH = 160
_HIGHLIGHT_BY_CATEGORY = {
    "quality": "quality",
    "style": "style",
    "lighting": "lighting",
    "composition": "composition",
    "negative": "negative",
    "embedding": "embedding",
    "lora": "lora",
    "plain": "plain",
}


def _normalize_catalog_text(value: object, *, max_length: int = _MAX_CATALOG_TEXT_LENGTH) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def _normalize_highlight(value: object, fallback: str = "plain") -> str:
    normalized = _normalize_catalog_text(value, max_length=40).lower().replace(" ", "_")
    if normalized in _HIGHLIGHT_BY_CATEGORY.values():
        return normalized
    return _HIGHLIGHT_BY_CATEGORY.get(normalized, fallback)


def _build_tag_entry(
    tag: str,
    *,
    category: str = "",
    aliases: object = None,
    count: object = None,
    highlight: str = "",
    label: object = "",
    local_label: object = "",
    english_label: object = "",
    insert_token: object = "",
) -> dict[str, Any]:
    normalized_tag = _normalize_catalog_text(tag)
    normalized_category = _normalize_catalog_text(category, max_length=80) or "plain"
    normalized_insert_token = _normalize_catalog_text(insert_token) or normalized_tag
    normalized_label = _normalize_catalog_text(label) or normalized_tag
    normalized_local_label = _normalize_catalog_text(local_label)
    normalized_english_label = _normalize_catalog_text(english_label) or normalized_tag
    if isinstance(aliases, str):
        alias_list = [entry.strip() for entry in aliases.replace("|", ",").split(",") if entry.strip()]
    elif isinstance(aliases, list):
        alias_list = [_normalize_catalog_text(entry) for entry in aliases if _normalize_catalog_text(entry)]
    else:
        alias_list = []
    normalized_count = int(count) if isinstance(count, int) and not isinstance(count, bool) and count >= 0 else 0
    return {
        "tag": normalized_tag,
        "label": normalized_label,
        "local_label": normalized_local_label,
        "english_label": normalized_english_label,
        "insert_token": normalized_insert_token,
        "category": normalized_category,
        "aliases": alias_list[:8],
        "count": normalized_count,
        "highlight": _normalize_highlight(highlight or normalized_category),
    }


def _load_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _runtime_catalog_root() -> Path:
    return _prompt_workbench_root() / "catalogs"


def _resolve_group_tag_path(language: str) -> tuple[Path, str]:
    runtime_root = _runtime_catalog_root()
    candidate_names = [
        f"group_tags.{language}.json",
        "group_tags.custom.json",
        "group_tags.default.json",
    ]
    for candidate_name in candidate_names:
        runtime_candidate = runtime_root / candidate_name
        if runtime_candidate.exists():
            return runtime_candidate, "runtime"
    for candidate_name in candidate_names:
        builtin_candidate = _DATA_ROOT / candidate_name
        if builtin_candidate.exists():
            return builtin_candidate, "builtin"
    return _DATA_ROOT / "group_tags.default.json", "builtin"


def _resolve_prompt_library_path() -> tuple[Path, str]:
    runtime_candidate = _runtime_catalog_root() / "prompt_library.json"
    if runtime_candidate.exists():
        return runtime_candidate, "runtime"
    return _DATA_ROOT / "prompt_library.default.json", "builtin"


def _normalize_group_tags_payload(payload: object, *, language: str, source: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"language": language, "source": source, "groups": []}
    groups = payload.get("groups", [])
    normalized_groups: list[dict[str, Any]] = []

    def normalize_tag_entry(tag: object, *, group_id: str) -> dict[str, Any] | None:
        if isinstance(tag, str) and str(tag).strip():
            return _build_tag_entry(tag, category=group_id)
        if not isinstance(tag, dict):
            return None
        tag_text = _normalize_catalog_text(tag.get("tag", tag.get("english_label", tag.get("label", tag.get("insert_token", "")))))
        if not tag_text:
            return None
        return _build_tag_entry(
            tag_text,
            category=_normalize_catalog_text(tag.get("category", group_id), max_length=80) or group_id,
            aliases=tag.get("aliases"),
            count=tag.get("count"),
            highlight=_normalize_catalog_text(tag.get("highlight", ""), max_length=40),
            label=tag.get("label", ""),
            local_label=tag.get("local_label", ""),
            english_label=tag.get("english_label", ""),
            insert_token=tag.get("insert_token", ""),
        )

    def normalize_subgroup(subgroup: dict[str, Any], *, group_id: str, group_title: str, fallback_id: str) -> dict[str, Any] | None:
        subgroup_id = _normalize_catalog_text(subgroup.get("id", ""), max_length=80) or fallback_id
        subgroup_title = _normalize_catalog_text(subgroup.get("title", ""), max_length=80) or group_title
        raw_tags = subgroup.get("tag_entries", subgroup.get("tags", []))
        if not isinstance(raw_tags, list):
            return None
        tag_entries = [entry for entry in (normalize_tag_entry(tag, group_id=group_id) for tag in raw_tags) if entry]
        tag_entries = tag_entries[:_MAX_CATALOG_ENTRIES]
        if not tag_entries:
            return None
        return {
            "id": subgroup_id,
            "title": subgroup_title,
            "tags": [entry["tag"] for entry in tag_entries],
            "tag_entries": tag_entries,
        }

    if isinstance(groups, list):
        for group in groups:
            if not isinstance(group, dict):
                continue
            group_id = _normalize_catalog_text(group.get("id", ""), max_length=80)
            title = _normalize_catalog_text(group.get("title", ""), max_length=80)
            if not group_id or not title:
                continue

            subgroups: list[dict[str, Any]] = []
            raw_subgroups = group.get("subgroups", [])
            if isinstance(raw_subgroups, list):
                for index, subgroup in enumerate(raw_subgroups):
                    if not isinstance(subgroup, dict):
                        continue
                    normalized_subgroup = normalize_subgroup(
                        subgroup,
                        group_id=group_id,
                        group_title=title,
                        fallback_id=f"{group_id}_{index + 1}",
                    )
                    if normalized_subgroup:
                        subgroups.append(normalized_subgroup)

            raw_group_tags = group.get("tag_entries", group.get("tags", []))
            if not subgroups and isinstance(raw_group_tags, list):
                normalized_subgroup = normalize_subgroup(
                    {"id": group_id, "title": title, "tag_entries": raw_group_tags},
                    group_id=group_id,
                    group_title=title,
                    fallback_id=group_id,
                )
                if normalized_subgroup:
                    subgroups.append(normalized_subgroup)

            tag_entries = [entry for subgroup in subgroups for entry in subgroup["tag_entries"]][:_MAX_CATALOG_ENTRIES]
            if not tag_entries:
                continue
            normalized_groups.append(
                {
                    "id": group_id,
                    "title": title,
                    "tags": [entry["tag"] for entry in tag_entries],
                    "tag_entries": tag_entries,
                    "subgroups": subgroups,
                }
            )
    return {"language": language, "source": source, "groups": normalized_groups}


def _normalize_prompt_library_payload(payload: object, *, source: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"source": source, "sections": []}
    sections = payload.get("sections", [])
    normalized_sections: list[dict[str, Any]] = []
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            section_id = str(section.get("id", "")).strip()
            title = str(section.get("title", "")).strip()
            raw_entries = section.get("entries", [])
            if not section_id or not title or not isinstance(raw_entries, list):
                continue
            entries: list[dict[str, Any]] = []
            for entry in raw_entries:
                if not isinstance(entry, dict):
                    continue
                entry_id = str(entry.get("id", "")).strip()
                label = str(entry.get("label", "")).strip()
                prompt_text = str(entry.get("prompt_text", "")).strip()
                if entry_id and label and prompt_text:
                    entries.append({"id": entry_id, "label": label, "prompt_text": prompt_text})
            if entries:
                normalized_sections.append({"id": section_id, "title": title, "entries": entries})
    return {"source": source, "sections": normalized_sections}


def _build_extra_network_payload() -> dict[str, Any]:
    inventory = discover_model_inventory()
    embeddings = [
        {
            "id": name,
            "title": name,
            "family": "embedding",
            "insert_token": f"embedding:{name}",
            "highlight": "embedding",
            "highlight_class": "rookieui-shell__prompt-workbench-chip--embedding",
        }
        for name in inventory.embeddings
    ]
    loras = [
        {
            "id": name,
            "title": name,
            "family": "lora",
            "insert_token": f"<lora:{name}:0.8>",
            "default_strength_model": 0.8,
            "default_strength_clip": 0.8,
            "highlight": "lora",
            "highlight_class": "rookieui-shell__prompt-workbench-chip--lora",
        }
        for name in inventory.loras
    ]
    return {
        "embeddings": embeddings,
        "loras": loras,
    }


def _resolve_tagcomplete_path(language: str) -> tuple[Path | None, str]:
    runtime_root = _runtime_catalog_root()
    candidate_names = [
        f"tagcomplete.{language}.csv",
        "tagcomplete.csv",
    ]
    for candidate_name in candidate_names:
        runtime_candidate = runtime_root / candidate_name
        if runtime_candidate.exists():
            return runtime_candidate, "runtime"
    return None, "builtin"


def _build_fallback_tagcomplete_entries(
    group_tags_payload: dict[str, Any],
    prompt_library_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in group_tags_payload.get("groups", []):
        if not isinstance(group, dict):
            continue
        for tag_entry in group.get("tag_entries", []):
            if not isinstance(tag_entry, dict):
                continue
            tag = _normalize_catalog_text(tag_entry.get("tag", ""))
            if not tag or tag.lower() in seen:
                continue
            seen.add(tag.lower())
            entries.append(tag_entry)
    for section in prompt_library_payload.get("sections", []):
        if not isinstance(section, dict):
            continue
        for entry in section.get("entries", []):
            if not isinstance(entry, dict):
                continue
            prompt_text = _normalize_catalog_text(entry.get("prompt_text", ""))
            label = _normalize_catalog_text(entry.get("label", prompt_text))
            if not prompt_text or prompt_text.lower() in seen:
                continue
            seen.add(prompt_text.lower())
            tag_entry = _build_tag_entry(prompt_text, category="library", highlight="style")
            tag_entry["label"] = label or prompt_text
            entries.append(tag_entry)
    return entries[:_MAX_CATALOG_ENTRIES]


def _load_tagcomplete_payload(
    *,
    language: str,
    group_tags_payload: dict[str, Any],
    prompt_library_payload: dict[str, Any],
) -> dict[str, Any]:
    tagcomplete_path, source = _resolve_tagcomplete_path(language)
    if tagcomplete_path is None:
        return {
            "language": language,
            "source": source,
            "entries": _build_fallback_tagcomplete_entries(group_tags_payload, prompt_library_payload),
        }

    entries: list[dict[str, Any]] = []
    with tagcomplete_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not isinstance(row, dict):
                continue
            tag = _normalize_catalog_text(row.get("tag") or row.get("name") or row.get("keyword"))
            if not tag:
                continue
            entry = _build_tag_entry(
                tag,
                category=_normalize_catalog_text(row.get("category", ""), max_length=80),
                aliases=row.get("aliases", ""),
                count=int(row["count"]) if str(row.get("count", "")).isdigit() else 0,
                highlight=_normalize_catalog_text(row.get("highlight", ""), max_length=40),
            )
            insert_token = _normalize_catalog_text(row.get("insert_token", ""))
            if insert_token:
                entry["insert_token"] = insert_token
            label = _normalize_catalog_text(row.get("label", ""))
            if label:
                entry["label"] = label
            entries.append(entry)
            if len(entries) >= _MAX_CATALOG_ENTRIES:
                break
    return {"language": language, "source": source, "entries": entries}


def _build_catalog_highlights() -> dict[str, Any]:
    return {
        "token_families": {
            "plain": {"highlight": "plain", "title": "Plain tag"},
            "weighted": {"highlight": "quality", "title": "Weighted tag"},
            "schedule": {"highlight": "composition", "title": "Prompt schedule"},
            "embedding": {"highlight": "embedding", "title": "Embedding"},
            "lora": {"highlight": "lora", "title": "LoRA"},
            "lycoris": {"highlight": "lora", "title": "LyCORIS"},
            "break": {"highlight": "composition", "title": "BREAK separator"},
            "and": {"highlight": "composition", "title": "AND composition separator"},
        },
        "catalog_categories": _HIGHLIGHT_BY_CATEGORY,
    }


def build_prompt_workbench_catalog_payload(*, language: object = "en") -> dict[str, Any]:
    normalized_language = normalize_prompt_workbench_language_code(language)
    group_tags_path, group_tags_source = _resolve_group_tag_path(normalized_language)
    prompt_library_path, prompt_library_source = _resolve_prompt_library_path()
    group_tags_payload = _normalize_group_tags_payload(
        _load_json_file(group_tags_path),
        language=normalized_language,
        source=group_tags_source,
    )
    prompt_library_payload = _normalize_prompt_library_payload(
        _load_json_file(prompt_library_path),
        source=prompt_library_source,
    )
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_catalog"),
        "group_tags": group_tags_payload,
        "prompt_library": prompt_library_payload,
        "tagcomplete": _load_tagcomplete_payload(
            language=normalized_language,
            group_tags_payload=group_tags_payload,
            prompt_library_payload=prompt_library_payload,
        ),
        "extra_networks": _build_extra_network_payload(),
        "catalog_highlights": _build_catalog_highlights(),
    }
