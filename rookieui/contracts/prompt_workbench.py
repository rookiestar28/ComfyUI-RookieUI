from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PROMPT_WORKBENCH_CONTRACT_VERSION = "r123f114-20260417"
PROMPT_WORKBENCH_STATE_SCHEMA_VERSION = 1
PROMPT_WORKBENCH_ROUTE_FAMILY = "/rookieui/prompt-tools"
PROMPT_WORKBENCH_NAMESPACES = (
    "txt2img_prompt",
    "txt2img_negative",
    "img2img_prompt",
    "img2img_negative",
)
PROMPT_WORKBENCH_PROVIDER_SECRET_FIELD_KEYS = (
    "access_token",
    "api_key",
    "authorization",
    "password",
    "secret",
    "token",
)


def _default_formatting_rules() -> dict[str, Any]:
    return {
        "dedupe_commas": True,
        "normalize_spacing": True,
        "trim_outer_whitespace": True,
    }


def _default_ui_preferences() -> dict[str, Any]:
    return {
        "default_open": False,
        "preferred_panel": "editor",
        "show_history": True,
        "show_favorites": True,
    }


def _default_blacklist_state() -> dict[str, Any]:
    return {
        "enabled": False,
        "entries": [],
    }


def _default_provider_settings() -> dict[str, Any]:
    return {
        "default_provider": "",
        "providers": {},
    }


def build_default_prompt_workbench_config() -> dict[str, Any]:
    return {
        "language": "en",
        "theme_style": "rookieui_classic",
        "history_limit": 100,
        "favorites_limit": 100,
        "formatting_rules": _default_formatting_rules(),
        "ui_preferences": _default_ui_preferences(),
        "translation": _default_provider_settings(),
        "ai_assist": _default_provider_settings(),
    }


def build_default_prompt_workbench_surface_state(namespace: str) -> dict[str, Any]:
    return {
        "namespace": namespace,
        "workbench_open": False,
        "active_panel": "editor",
        "draft_prompt": "",
        "selected_entry_id": "",
    }


@dataclass(frozen=True)
class PromptWorkbenchRouteContract:
    version: str = PROMPT_WORKBENCH_CONTRACT_VERSION
    surface: str = "prompt_tools"
    route_family: str = PROMPT_WORKBENCH_ROUTE_FAMILY
    state_schema_version: int = PROMPT_WORKBENCH_STATE_SCHEMA_VERSION
    namespaces: tuple[str, ...] = PROMPT_WORKBENCH_NAMESPACES
    provider_secret_field_keys: tuple[str, ...] = PROMPT_WORKBENCH_PROVIDER_SECRET_FIELD_KEYS
    notes: tuple[str, ...] = (
        "Prompt-workbench state is RookieUI-owned and versioned.",
        "Provider secret fields must remain masked in readback payloads.",
        "Heavy history/favorite data should stay lazy-loaded outside bootstrap.",
    )

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromptWorkbenchBootstrapSnapshot:
    contract: PromptWorkbenchRouteContract = field(default_factory=PromptWorkbenchRouteContract)
    config: dict[str, Any] = field(default_factory=build_default_prompt_workbench_config)
    blacklist: dict[str, Any] = field(default_factory=_default_blacklist_state)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


def build_prompt_workbench_contract_meta(*, surface: str = "prompt_tools") -> dict[str, Any]:
    contract = PromptWorkbenchRouteContract(surface=surface)
    return contract.to_payload()
