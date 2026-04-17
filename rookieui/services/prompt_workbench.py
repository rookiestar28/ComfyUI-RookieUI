from __future__ import annotations

from typing import Any

from rookieui.contracts.prompt_workbench import build_prompt_workbench_contract_meta
from rookieui.services.prompt_workbench_state import (
    apply_prompt_workbench_favorite_action,
    apply_prompt_workbench_history_action,
    get_prompt_workbench_blacklist,
    get_prompt_workbench_bootstrap_payload,
    get_prompt_workbench_favorites,
    get_prompt_workbench_history,
    get_prompt_workbench_surface_state,
    update_prompt_workbench_blacklist,
    update_prompt_workbench_config,
    update_prompt_workbench_surface_state,
)
from rookieui.services.prompt_workbench_analysis import analyze_prompt_workbench_payload
from rookieui.services.prompt_workbench_assist import assist_prompt_workbench_payload
from rookieui.services.prompt_workbench_catalog import build_prompt_workbench_catalog_payload
from rookieui.services.prompt_workbench_translation import (
    build_prompt_workbench_provider_payload,
    translate_prompt_workbench_payload,
)


def build_prompt_workbench_config_payload() -> dict[str, Any]:
    payload = get_prompt_workbench_bootstrap_payload()
    payload["contract"] = build_prompt_workbench_contract_meta(surface="prompt_tools_config")
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
    }


def build_prompt_workbench_history_payload(namespace: object) -> dict[str, Any]:
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_history"),
        "namespace": str(namespace),
        "items": get_prompt_workbench_history(namespace),
    }


def build_prompt_workbench_favorites_payload(namespace: object) -> dict[str, Any]:
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_favorites"),
        "namespace": str(namespace),
        "items": get_prompt_workbench_favorites(namespace),
    }


def build_prompt_workbench_provider_catalog_payload() -> dict[str, Any]:
    return build_prompt_workbench_provider_payload()


def build_prompt_workbench_catalog_snapshot(*, language: object = "en") -> dict[str, Any]:
    return build_prompt_workbench_catalog_payload(language=language)


def apply_prompt_workbench_config_update(payload: object) -> dict[str, Any]:
    update_prompt_workbench_config(payload)
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_config"),
        "config": get_prompt_workbench_bootstrap_payload()["config"],
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
    }


def apply_prompt_workbench_history_update(namespace: object, *, action: object, payload: object) -> dict[str, Any]:
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_history"),
        "namespace": str(namespace),
        "items": apply_prompt_workbench_history_action(namespace, action=action, payload=payload),
    }


def apply_prompt_workbench_favorites_update(namespace: object, *, action: object, payload: object) -> dict[str, Any]:
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_favorites"),
        "namespace": str(namespace),
        "items": apply_prompt_workbench_favorite_action(namespace, action=action, payload=payload),
    }


def execute_prompt_workbench_translate(payload: object) -> dict[str, Any]:
    return translate_prompt_workbench_payload(payload).to_payload()


def execute_prompt_workbench_ai_assist(payload: object) -> dict[str, Any]:
    return assist_prompt_workbench_payload(payload).to_payload()


def execute_prompt_workbench_analysis(payload: object) -> dict[str, Any]:
    return analyze_prompt_workbench_payload(payload)
