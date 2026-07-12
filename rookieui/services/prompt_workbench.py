from __future__ import annotations

from typing import Any

from rookieui.contracts.prompt_workbench import (
    PROMPT_WORKBENCH_NAMESPACES,
    PROMPT_WORKBENCH_STATE_SCHEMA_VERSION,
    build_default_prompt_workbench_config,
    build_prompt_workbench_contract_meta,
)
from rookieui.services.prompt_workbench_state import (
    apply_prompt_workbench_favorite_action,
    apply_prompt_workbench_history_action,
    get_prompt_workbench_blacklist,
    get_prompt_workbench_bootstrap_payload,
    get_prompt_workbench_favorites,
    get_prompt_workbench_history,
    get_prompt_workbench_surface_state,
    export_prompt_workbench_store,
    import_prompt_workbench_store,
    update_prompt_workbench_blacklist,
    update_prompt_workbench_config,
    update_prompt_workbench_surface_state,
)
from rookieui.services.prompt_workbench_analysis import analyze_prompt_workbench_payload
from rookieui.services.prompt_workbench_assist import assist_prompt_workbench_payload
from rookieui.services.prompt_workbench_catalog import build_prompt_workbench_catalog_payload
from rookieui.services.prompt_workbench_danbooru import (
    build_prompt_workbench_danbooru_host_action_payload,
    execute_prompt_workbench_danbooru_request_async,
)
from rookieui.services.prompt_workbench_translation import (
    build_prompt_workbench_provider_payload,
    translate_prompt_workbench_payload,
)
from rookieui.contracts.prompt_workbench import PROMPT_WORKBENCH_DANBOORU_ACTION_ID


def _build_prompt_workbench_persistence_meta() -> dict[str, Any]:
    config = get_prompt_workbench_bootstrap_payload().get("config", build_default_prompt_workbench_config())
    if not isinstance(config, dict):
        config = build_default_prompt_workbench_config()
    return {
        "schema_version": PROMPT_WORKBENCH_STATE_SCHEMA_VERSION,
        "namespaces": list(PROMPT_WORKBENCH_NAMESPACES),
        "history_limit": int(config.get("history_limit", build_default_prompt_workbench_config()["history_limit"])),
        "favorites_limit": int(config.get("favorites_limit", build_default_prompt_workbench_config()["favorites_limit"])),
        "storage": "rookieui_prompt_workbench_state",
    }


def build_prompt_workbench_config_payload() -> dict[str, Any]:
    payload = get_prompt_workbench_bootstrap_payload()
    payload["host_actions"] = {
        **(payload.get("host_actions", {}) if isinstance(payload.get("host_actions"), dict) else {}),
        PROMPT_WORKBENCH_DANBOORU_ACTION_ID: build_prompt_workbench_danbooru_host_action_payload(),
    }
    payload["contract"] = build_prompt_workbench_contract_meta(surface="prompt_tools_config")
    payload["persistence"] = _build_prompt_workbench_persistence_meta()
    return payload


def build_prompt_workbench_blacklist_payload() -> dict[str, Any]:
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_blacklist"),
        "blacklist": get_prompt_workbench_blacklist(),
    }


def build_prompt_workbench_surface_state_payload(namespace: object) -> dict[str, Any]:
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_state"),
        "namespace": str(namespace),
        "state": get_prompt_workbench_surface_state(namespace),
        "persistence": _build_prompt_workbench_persistence_meta(),
    }


def build_prompt_workbench_history_payload(namespace: object) -> dict[str, Any]:
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_history"),
        "namespace": str(namespace),
        "items": get_prompt_workbench_history(namespace),
        "persistence": _build_prompt_workbench_persistence_meta(),
    }


def build_prompt_workbench_favorites_payload(namespace: object) -> dict[str, Any]:
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_favorites"),
        "namespace": str(namespace),
        "items": get_prompt_workbench_favorites(namespace),
        "persistence": _build_prompt_workbench_persistence_meta(),
    }


def build_prompt_workbench_provider_catalog_payload() -> dict[str, Any]:
    return build_prompt_workbench_provider_payload()


def build_prompt_workbench_export_payload() -> dict[str, Any]:
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_export"),
        "export": export_prompt_workbench_store(),
    }


def apply_prompt_workbench_import(payload: object) -> dict[str, Any]:
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_import"),
        "import_result": import_prompt_workbench_store(payload),
        "persistence": _build_prompt_workbench_persistence_meta(),
    }


def build_prompt_workbench_catalog_snapshot(*, language: object = "en") -> dict[str, Any]:
    return build_prompt_workbench_catalog_payload(language=language)


def apply_prompt_workbench_config_update(payload: object) -> dict[str, Any]:
    update_prompt_workbench_config(payload)
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_config"),
        "config": get_prompt_workbench_bootstrap_payload()["config"],
        "persistence": _build_prompt_workbench_persistence_meta(),
        "saved": True,
    }


def apply_prompt_workbench_blacklist_update(payload: object) -> dict[str, Any]:
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_blacklist"),
        "blacklist": update_prompt_workbench_blacklist(payload),
    }


def apply_prompt_workbench_surface_state_update(namespace: object, payload: object) -> dict[str, Any]:
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_state"),
        "namespace": str(namespace),
        "state": update_prompt_workbench_surface_state(namespace, payload),
        "persistence": _build_prompt_workbench_persistence_meta(),
    }


def apply_prompt_workbench_history_update(namespace: object, *, action: object, payload: object) -> dict[str, Any]:
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_history"),
        "namespace": str(namespace),
        "items": apply_prompt_workbench_history_action(namespace, action=action, payload=payload),
        "persistence": _build_prompt_workbench_persistence_meta(),
    }


def apply_prompt_workbench_favorites_update(namespace: object, *, action: object, payload: object) -> dict[str, Any]:
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_favorites"),
        "namespace": str(namespace),
        "items": apply_prompt_workbench_favorite_action(namespace, action=action, payload=payload),
        "persistence": _build_prompt_workbench_persistence_meta(),
    }


def execute_prompt_workbench_translate(payload: object) -> dict[str, Any]:
    return translate_prompt_workbench_payload(payload).to_payload()


def execute_prompt_workbench_ai_assist(payload: object) -> dict[str, Any]:
    return assist_prompt_workbench_payload(payload).to_payload()


def execute_prompt_workbench_analysis(payload: object) -> dict[str, Any]:
    return analyze_prompt_workbench_payload(payload)


async def execute_prompt_workbench_upsample(payload: object) -> dict[str, Any]:
    return await execute_prompt_workbench_danbooru_request_async(payload)
