from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rookieui.contracts.prompt_workbench import build_prompt_workbench_contract_meta
from rookieui.services.model_inventory import discover_model_inventory
from rookieui.services.prompt_workbench_state import _prompt_workbench_root

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_DATA_ROOT = _WORKSPACE_ROOT / "rookieui" / "data" / "prompt_workbench"


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
    if isinstance(groups, list):
        for group in groups:
            if not isinstance(group, dict):
                continue
            group_id = str(group.get("id", "")).strip()
            title = str(group.get("title", "")).strip()
            raw_tags = group.get("tags", [])
            if not group_id or not title or not isinstance(raw_tags, list):
                continue
            tags = [str(tag).strip() for tag in raw_tags if isinstance(tag, str) and str(tag).strip()]
            if not tags:
                continue
            normalized_groups.append({"id": group_id, "title": title, "tags": tags})
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
        }
        for name in inventory.loras
    ]
    return {
        "embeddings": embeddings,
        "loras": loras,
    }


def build_prompt_workbench_catalog_payload(*, language: object = "en") -> dict[str, Any]:
    normalized_language = str(language or "").strip() or "en"
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
        "extra_networks": _build_extra_network_payload(),
    }
