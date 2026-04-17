from __future__ import annotations

import json
import os
import secrets
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from rookieui.services.state_persistence import atomic_write_json, quarantine_corrupt_json
from rookieui.contracts.prompt_workbench import (
    PROMPT_WORKBENCH_NAMESPACES,
    PROMPT_WORKBENCH_PROVIDER_SECRET_FIELD_KEYS,
    PROMPT_WORKBENCH_STATE_SCHEMA_VERSION,
    PromptWorkbenchBootstrapSnapshot,
    build_default_prompt_workbench_config,
    build_default_prompt_workbench_surface_state,
    get_prompt_workbench_provider_catalog_entry,
)

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_STATE_LOCK = threading.RLock()
_MAX_PROMPT_TEXT_LENGTH = 16000
_MAX_ENTRY_LABEL_LENGTH = 200
_MAX_TAG_COUNT = 64
_MAX_TAG_LENGTH = 120


def _prompt_workbench_root() -> Path:
    override = os.environ.get("ROOKIEUI_PROMPT_WORKBENCH_RUNTIME_ROOT", "").strip()
    if override:
        return Path(override)
    return _WORKSPACE_ROOT / ".rookieui_runtime" / "prompt_workbench"


def _prompt_workbench_state_path() -> Path:
    return _prompt_workbench_root() / "state.json"


def _ensure_prompt_workbench_dir() -> None:
    _prompt_workbench_root().mkdir(parents=True, exist_ok=True)


def _default_surface_collections(namespace: str) -> dict[str, Any]:
    return {
        "state": build_default_prompt_workbench_surface_state(namespace),
        "history": [],
        "favorites": [],
    }


def _default_prompt_workbench_store() -> dict[str, Any]:
    return {
        "schema_version": PROMPT_WORKBENCH_STATE_SCHEMA_VERSION,
        "config": build_default_prompt_workbench_config(),
        "blacklist": PromptWorkbenchBootstrapSnapshot().blacklist,
        "surfaces": {
            namespace: _default_surface_collections(namespace)
            for namespace in PROMPT_WORKBENCH_NAMESPACES
        },
    }


def _normalize_text(value: object, *, max_length: int) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def _normalize_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _normalize_positive_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(1, value)
    return default


def _normalize_tag_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    tags: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            continue
        normalized = entry.strip()[:_MAX_TAG_LENGTH]
        if normalized:
            tags.append(normalized)
        if len(tags) >= _MAX_TAG_COUNT:
            break
    return tags


def _normalize_provider_field_value(field_spec: dict[str, Any], raw_value: object) -> Any:
    value_type = str(field_spec.get("value_type", "string")).strip() or "string"
    if value_type == "boolean":
        if isinstance(raw_value, bool):
            return raw_value
        return bool(field_spec.get("default", False))
    if value_type in {"integer", "number"}:
        default = field_spec.get("default", 0)
        if not isinstance(default, (int, float)) or isinstance(default, bool):
            default = 0
        if isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool):
            normalized_number: int | float = int(raw_value) if value_type == "integer" else float(raw_value)
        else:
            normalized_number = int(default) if value_type == "integer" else float(default)
        min_value = field_spec.get("min_value")
        max_value = field_spec.get("max_value")
        if isinstance(min_value, (int, float)):
            normalized_number = max(normalized_number, int(min_value) if value_type == "integer" else float(min_value))
        if isinstance(max_value, (int, float)):
            normalized_number = min(normalized_number, int(max_value) if value_type == "integer" else float(max_value))
        return normalized_number

    default = str(field_spec.get("default", "")).strip()
    max_length = int(field_spec.get("max_length", 512) or 512)
    if not isinstance(raw_value, str):
        return default[:max_length]
    return raw_value.strip()[:max_length]


def _normalize_provider_payload(value: object, *, surface: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"default_provider": "", "providers": {}}

    providers: dict[str, Any] = {}
    raw_providers = value.get("providers", {})
    if isinstance(raw_providers, dict):
        for provider_id, provider_payload in raw_providers.items():
            normalized_provider_id = _normalize_text(provider_id, max_length=80)
            catalog_entry = get_prompt_workbench_provider_catalog_entry(normalized_provider_id)
            if (
                not normalized_provider_id
                or catalog_entry is None
                or surface not in catalog_entry.surface_scopes
                or not isinstance(provider_payload, dict)
            ):
                continue
            normalized_provider: dict[str, Any] = {}
            for field_spec in catalog_entry.to_payload()["config_fields"]:
                field_key = str(field_spec.get("key", "")).strip()
                if not field_key:
                    continue
                normalized_provider[field_key] = _normalize_provider_field_value(
                    field_spec,
                    provider_payload.get(field_key),
                )
            providers[normalized_provider_id] = normalized_provider

    default_provider = _normalize_text(value.get("default_provider", ""), max_length=80)
    if default_provider not in providers and get_prompt_workbench_provider_catalog_entry(default_provider) is None:
        default_provider = ""

    return {
        "default_provider": default_provider,
        "providers": providers,
    }


def _normalize_formatting_rules(value: object) -> dict[str, Any]:
    defaults = build_default_prompt_workbench_config()["formatting_rules"]
    if not isinstance(value, dict):
        return defaults
    return {
        "dedupe_commas": _normalize_bool(value.get("dedupe_commas"), defaults["dedupe_commas"]),
        "normalize_spacing": _normalize_bool(value.get("normalize_spacing"), defaults["normalize_spacing"]),
        "trim_outer_whitespace": _normalize_bool(
            value.get("trim_outer_whitespace"),
            defaults["trim_outer_whitespace"],
        ),
    }


def _normalize_ui_preferences(value: object) -> dict[str, Any]:
    defaults = build_default_prompt_workbench_config()["ui_preferences"]
    if not isinstance(value, dict):
        return defaults
    return {
        "default_open": _normalize_bool(value.get("default_open"), defaults["default_open"]),
        "preferred_panel": _normalize_text(value.get("preferred_panel", defaults["preferred_panel"]), max_length=80)
        or defaults["preferred_panel"],
        "show_history": _normalize_bool(value.get("show_history"), defaults["show_history"]),
        "show_favorites": _normalize_bool(value.get("show_favorites"), defaults["show_favorites"]),
    }


def _normalize_config_payload(existing: dict[str, Any], payload: object) -> dict[str, Any]:
    defaults = build_default_prompt_workbench_config()
    merged = deepcopy(existing) if isinstance(existing, dict) else defaults
    if not isinstance(payload, dict):
        return merged

    if "language" in payload:
        merged["language"] = _normalize_text(payload.get("language", ""), max_length=32) or defaults["language"]
    if "theme_style" in payload:
        merged["theme_style"] = _normalize_text(payload.get("theme_style", ""), max_length=80) or defaults["theme_style"]
    if "history_limit" in payload:
        merged["history_limit"] = min(_normalize_positive_int(payload.get("history_limit"), defaults["history_limit"]), 500)
    if "favorites_limit" in payload:
        merged["favorites_limit"] = min(
            _normalize_positive_int(payload.get("favorites_limit"), defaults["favorites_limit"]),
            500,
        )
    if "formatting_rules" in payload:
        merged["formatting_rules"] = _normalize_formatting_rules(payload.get("formatting_rules"))
    if "ui_preferences" in payload:
        merged["ui_preferences"] = _normalize_ui_preferences(payload.get("ui_preferences"))
    if "translation" in payload:
        merged["translation"] = _normalize_provider_payload(payload.get("translation"), surface="translation")
    if "ai_assist" in payload:
        normalized_ai_assist = _normalize_provider_payload(payload.get("ai_assist"), surface="ai_assist")
        if isinstance(payload.get("ai_assist"), dict):
            normalized_ai_assist["instruction_preset"] = _normalize_text(
                payload["ai_assist"].get("instruction_preset", merged.get("ai_assist", {}).get("instruction_preset", "")),
                max_length=_MAX_PROMPT_TEXT_LENGTH,
            ) or defaults["ai_assist"]["instruction_preset"]
        else:
            normalized_ai_assist["instruction_preset"] = (
                merged.get("ai_assist", {}).get("instruction_preset")
                or defaults["ai_assist"]["instruction_preset"]
            )
        merged["ai_assist"] = normalized_ai_assist
    return merged


def _normalize_blacklist_payload(existing: dict[str, Any], payload: object) -> dict[str, Any]:
    merged = deepcopy(existing) if isinstance(existing, dict) else {"enabled": False, "entries": []}
    if not isinstance(payload, dict):
        return merged
    if "enabled" in payload:
        merged["enabled"] = _normalize_bool(payload.get("enabled"), merged.get("enabled", False))
    if "entries" in payload and isinstance(payload.get("entries"), list):
        merged["entries"] = _normalize_tag_list(payload.get("entries"))
    return merged


def _normalize_surface_state_payload(namespace: str, existing: dict[str, Any], payload: object) -> dict[str, Any]:
    defaults = build_default_prompt_workbench_surface_state(namespace)
    merged = deepcopy(existing) if isinstance(existing, dict) else defaults
    if not isinstance(payload, dict):
        return merged

    if "workbench_open" in payload:
        merged["workbench_open"] = _normalize_bool(payload.get("workbench_open"), defaults["workbench_open"])
    if "active_panel" in payload:
        merged["active_panel"] = _normalize_text(payload.get("active_panel", ""), max_length=80) or defaults["active_panel"]
    if "draft_prompt" in payload:
        merged["draft_prompt"] = _normalize_text(payload.get("draft_prompt", ""), max_length=_MAX_PROMPT_TEXT_LENGTH)
    if "selected_entry_id" in payload:
        merged["selected_entry_id"] = _normalize_text(
            payload.get("selected_entry_id", ""),
            max_length=80,
        )
    merged["namespace"] = namespace
    return merged


def _normalize_prompt_entry_payload(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Prompt workbench entry payload must be an object.")

    prompt_text = _normalize_text(payload.get("prompt_text", ""), max_length=_MAX_PROMPT_TEXT_LENGTH)
    if not prompt_text:
        raise ValueError("prompt_text is required.")

    return {
        "id": _normalize_text(payload.get("id", ""), max_length=80) or secrets.token_hex(8),
        "created_at": int(payload.get("created_at", time.time())) if isinstance(payload.get("created_at"), int) else int(time.time()),
        "label": _normalize_text(payload.get("label", ""), max_length=_MAX_ENTRY_LABEL_LENGTH),
        "prompt_text": prompt_text,
        "tag_tokens": _normalize_tag_list(payload.get("tag_tokens")),
    }


def _normalize_namespace(namespace: object) -> str:
    normalized = _normalize_text(namespace, max_length=80)
    if normalized not in PROMPT_WORKBENCH_NAMESPACES:
        raise ValueError("namespace must be one of the supported prompt-workbench surfaces.")
    return normalized


def _mask_sensitive_fields(payload: object) -> object:
    if isinstance(payload, dict):
        masked: dict[str, Any] = {}
        for key, value in payload.items():
            key_text = str(key).strip()
            lower_key = key_text.lower()
            if any(secret_key in lower_key for secret_key in PROMPT_WORKBENCH_PROVIDER_SECRET_FIELD_KEYS):
                string_value = str(value).strip()
                masked[key_text] = "********" if string_value else ""
                continue
            masked[key_text] = _mask_sensitive_fields(value)
        return masked
    if isinstance(payload, list):
        return [_mask_sensitive_fields(entry) for entry in payload]
    return payload


def _coerce_store_shape(payload: object) -> dict[str, Any]:
    defaults = _default_prompt_workbench_store()
    if not isinstance(payload, dict):
        return defaults

    store = deepcopy(defaults)
    if int(payload.get("schema_version", 0) or 0) == PROMPT_WORKBENCH_STATE_SCHEMA_VERSION:
        store["schema_version"] = PROMPT_WORKBENCH_STATE_SCHEMA_VERSION
    store["config"] = _normalize_config_payload(defaults["config"], payload.get("config"))
    store["blacklist"] = _normalize_blacklist_payload(defaults["blacklist"], payload.get("blacklist"))

    raw_surfaces = payload.get("surfaces", {})
    for namespace in PROMPT_WORKBENCH_NAMESPACES:
        raw_surface = raw_surfaces.get(namespace, {}) if isinstance(raw_surfaces, dict) else {}
        existing_surface = defaults["surfaces"][namespace]
        state_payload = raw_surface.get("state", {}) if isinstance(raw_surface, dict) else {}
        history_payload = raw_surface.get("history", []) if isinstance(raw_surface, dict) else []
        favorites_payload = raw_surface.get("favorites", []) if isinstance(raw_surface, dict) else []
        history_items = []
        if isinstance(history_payload, list):
            for entry in history_payload:
                try:
                    history_items.append(_normalize_prompt_entry_payload(entry))
                except ValueError:
                    continue
        favorites_items = []
        if isinstance(favorites_payload, list):
            for entry in favorites_payload:
                try:
                    favorites_items.append(_normalize_prompt_entry_payload(entry))
                except ValueError:
                    continue
        store["surfaces"][namespace] = {
            "state": _normalize_surface_state_payload(namespace, existing_surface["state"], state_payload),
            "history": history_items[: store["config"]["history_limit"]],
            "favorites": favorites_items[: store["config"]["favorites_limit"]],
        }
    return store


def load_prompt_workbench_store() -> dict[str, Any]:
    _ensure_prompt_workbench_dir()
    path = _prompt_workbench_state_path()
    if not path.exists():
        return _default_prompt_workbench_store()
    try:
        return _coerce_store_shape(json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError:
        quarantine_corrupt_json(path)
        return _default_prompt_workbench_store()
    except Exception:
        return _default_prompt_workbench_store()


def save_prompt_workbench_store(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _coerce_store_shape(payload)
    _ensure_prompt_workbench_dir()
    with _STATE_LOCK:
        atomic_write_json(_prompt_workbench_state_path(), normalized)
    return normalized


def get_prompt_workbench_bootstrap_payload() -> dict[str, Any]:
    store = load_prompt_workbench_store()
    snapshot = PromptWorkbenchBootstrapSnapshot(
        config=_mask_sensitive_fields(store["config"]),
        blacklist=store["blacklist"],
    )
    return snapshot.to_payload()


def update_prompt_workbench_config(payload: object) -> dict[str, Any]:
    with _STATE_LOCK:
        store = load_prompt_workbench_store()
        store["config"] = _normalize_config_payload(store["config"], payload)
        for namespace in PROMPT_WORKBENCH_NAMESPACES:
            store["surfaces"][namespace]["history"] = store["surfaces"][namespace]["history"][: store["config"]["history_limit"]]
            store["surfaces"][namespace]["favorites"] = store["surfaces"][namespace]["favorites"][
                : store["config"]["favorites_limit"]
            ]
        return save_prompt_workbench_store(store)["config"]


def get_prompt_workbench_blacklist() -> dict[str, Any]:
    return load_prompt_workbench_store()["blacklist"]


def update_prompt_workbench_blacklist(payload: object) -> dict[str, Any]:
    with _STATE_LOCK:
        store = load_prompt_workbench_store()
        store["blacklist"] = _normalize_blacklist_payload(store["blacklist"], payload)
        return save_prompt_workbench_store(store)["blacklist"]


def get_prompt_workbench_surface_state(namespace: object) -> dict[str, Any]:
    normalized_namespace = _normalize_namespace(namespace)
    return load_prompt_workbench_store()["surfaces"][normalized_namespace]["state"]


def update_prompt_workbench_surface_state(namespace: object, payload: object) -> dict[str, Any]:
    normalized_namespace = _normalize_namespace(namespace)
    with _STATE_LOCK:
        store = load_prompt_workbench_store()
        current_state = store["surfaces"][normalized_namespace]["state"]
        store["surfaces"][normalized_namespace]["state"] = _normalize_surface_state_payload(
            normalized_namespace,
            current_state,
            payload,
        )
        return save_prompt_workbench_store(store)["surfaces"][normalized_namespace]["state"]


def _apply_collection_action(
    *,
    namespace: str,
    collection_name: str,
    action: object,
    payload: object,
) -> list[dict[str, Any]]:
    normalized_action = _normalize_text(action, max_length=40) or "push"
    with _STATE_LOCK:
        store = load_prompt_workbench_store()
        collection = list(store["surfaces"][namespace][collection_name])

        if normalized_action == "clear":
            collection = []
        elif normalized_action == "replace":
            items = payload.get("items") if isinstance(payload, dict) else []
            collection = []
            if isinstance(items, list):
                for entry in items:
                    collection.append(_normalize_prompt_entry_payload(entry))
        elif normalized_action == "remove":
            item_id = _normalize_text(payload.get("item_id", "") if isinstance(payload, dict) else "", max_length=80)
            collection = [entry for entry in collection if entry["id"] != item_id]
        elif normalized_action in {"move_up", "move_down"}:
            item_id = _normalize_text(payload.get("item_id", "") if isinstance(payload, dict) else "", max_length=80)
            index = next((idx for idx, entry in enumerate(collection) if entry["id"] == item_id), -1)
            if index >= 0:
                delta = -1 if normalized_action == "move_up" else 1
                target_index = index + delta
                if 0 <= target_index < len(collection):
                    collection[index], collection[target_index] = collection[target_index], collection[index]
        else:
            entry_payload = payload.get("item") if isinstance(payload, dict) else payload
            collection.append(_normalize_prompt_entry_payload(entry_payload))

        limit_key = "history_limit" if collection_name == "history" else "favorites_limit"
        limit = int(store["config"][limit_key])
        store["surfaces"][namespace][collection_name] = collection[-limit:]
        return save_prompt_workbench_store(store)["surfaces"][namespace][collection_name]


def get_prompt_workbench_history(namespace: object) -> list[dict[str, Any]]:
    normalized_namespace = _normalize_namespace(namespace)
    return load_prompt_workbench_store()["surfaces"][normalized_namespace]["history"]


def apply_prompt_workbench_history_action(
    namespace: object,
    *,
    action: object,
    payload: object,
) -> list[dict[str, Any]]:
    normalized_namespace = _normalize_namespace(namespace)
    return _apply_collection_action(
        namespace=normalized_namespace,
        collection_name="history",
        action=action,
        payload=payload,
    )


def get_prompt_workbench_favorites(namespace: object) -> list[dict[str, Any]]:
    normalized_namespace = _normalize_namespace(namespace)
    return load_prompt_workbench_store()["surfaces"][normalized_namespace]["favorites"]


def apply_prompt_workbench_favorite_action(
    namespace: object,
    *,
    action: object,
    payload: object,
) -> list[dict[str, Any]]:
    normalized_namespace = _normalize_namespace(namespace)
    return _apply_collection_action(
        namespace=normalized_namespace,
        collection_name="favorites",
        action=action,
        payload=payload,
    )
