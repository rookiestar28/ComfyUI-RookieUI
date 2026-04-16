from __future__ import annotations

import os

ROOKIEUI_CONTROLNET_ENABLED_ENV = "ROOKIEUI_CONTROLNET_ENABLED"
ROOKIEUI_CONTROLNET_A1111_ALIAS_ENABLED_ENV = "ROOKIEUI_CONTROLNET_A1111_ALIAS_ENABLED"
ROOKIEUI_CONTROLNET_PREPROCESSOR_ENABLED_ENV = "ROOKIEUI_CONTROLNET_PREPROCESSOR_ENABLED"

CONTROLNET_WARNING_FEATURE_DISABLED = "CONTROLNET_FEATURE_DISABLED"
CONTROLNET_WARNING_ALIAS_NATIVE_OVERRIDE = "CONTROLNET_ALIAS_NATIVE_OVERRIDE"
CONTROLNET_WARNING_ALIAS_DISABLED = "CONTROLNET_ALIAS_DISABLED"
CONTROLNET_WARNING_UNIT_LIMIT_TRUNCATED = "CONTROLNET_UNIT_LIMIT_TRUNCATED"
CONTROLNET_WARNING_PREPROCESSOR_DISABLED = "CONTROLNET_PREPROCESSOR_DISABLED"
CONTROLNET_WARNING_PREPROCESSOR_UNAVAILABLE = "CONTROLNET_PREPROCESSOR_UNAVAILABLE"
CONTROLNET_WARNING_PREPROCESSOR_HOST_FALLBACK = "CONTROLNET_PREPROCESSOR_HOST_FALLBACK"
CONTROLNET_WARNING_PREPROCESSOR_EMPTY_OUTPUT = "CONTROLNET_PREPROCESSOR_EMPTY_OUTPUT"

_WARNING_MESSAGES = {
    CONTROLNET_WARNING_FEATURE_DISABLED: "ControlNet payload was ignored because ControlNet is disabled by feature flag.",
    CONTROLNET_WARNING_ALIAS_NATIVE_OVERRIDE: "A1111 alias ControlNet payload was ignored because RookieUI-native controlnet_units were provided.",
    CONTROLNET_WARNING_ALIAS_DISABLED: "A1111 alias ControlNet payload was ignored because alias compatibility is disabled by feature flag.",
    CONTROLNET_WARNING_UNIT_LIMIT_TRUNCATED: "ControlNet unit count exceeded guardrail; extra units were ignored.",
    CONTROLNET_WARNING_PREPROCESSOR_DISABLED: "ControlNet preprocessors are disabled by feature flag; detect request returned passthrough images.",
    CONTROLNET_WARNING_PREPROCESSOR_UNAVAILABLE: (
        "ControlNet preprocessors are unavailable because runtime dependencies (numpy/torch/Pillow) are missing."
    ),
    CONTROLNET_WARNING_PREPROCESSOR_HOST_FALLBACK: (
        "ComfyUI host preprocessor node is unavailable for the selected module; using RookieUI fallback output."
    ),
    CONTROLNET_WARNING_PREPROCESSOR_EMPTY_OUTPUT: (
        "ComfyUI host preprocessor completed but output is near-empty for the current image/module settings."
    ),
}


def _env_flag(name: str, *, default: bool) -> bool:
    raw_value = str(os.getenv(name, "1" if default else "0")).strip().lower()
    if raw_value in {"1", "true", "yes", "on"}:
        return True
    if raw_value in {"0", "false", "no", "off"}:
        return False
    return default


def is_controlnet_enabled() -> bool:
    return _env_flag(ROOKIEUI_CONTROLNET_ENABLED_ENV, default=True)


def is_controlnet_alias_enabled() -> bool:
    return _env_flag(ROOKIEUI_CONTROLNET_A1111_ALIAS_ENABLED_ENV, default=True)


def is_controlnet_preprocessor_enabled() -> bool:
    return _env_flag(ROOKIEUI_CONTROLNET_PREPROCESSOR_ENABLED_ENV, default=True)


def warning_messages_from_codes(codes: list[str]) -> list[str]:
    messages: list[str] = []
    for code in codes:
        message = _WARNING_MESSAGES.get(code)
        if message:
            messages.append(message)
    return messages
