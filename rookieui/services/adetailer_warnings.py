from __future__ import annotations

ADETAILER_WARNING_UNIT_LIMIT_TRUNCATED = "ADETAILER_UNIT_LIMIT_TRUNCATED"
ADETAILER_WARNING_SKIP_IMG2IMG_IGNORED = "ADETAILER_SKIP_IMG2IMG_IGNORED"
ADETAILER_WARNING_NO_ACTIVE_UNITS = "ADETAILER_NO_ACTIVE_UNITS"
ADETAILER_WARNING_DETECTOR_NOT_IN_CATALOG = "ADETAILER_DETECTOR_NOT_IN_CATALOG"
ADETAILER_WARNING_DETECTOR_RUNTIME_FALLBACK_MASK = "ADETAILER_DETECTOR_RUNTIME_FALLBACK_MASK"
ADETAILER_WARNING_CONTROLNET_PASSTHROUGH_EMPTY = "ADETAILER_CONTROLNET_PASSTHROUGH_EMPTY"
ADETAILER_WARNING_CONTROLNET_CUSTOM_MODEL_MISSING = "ADETAILER_CONTROLNET_CUSTOM_MODEL_MISSING"

ADETAILER_DEGRADED_WARNING_CODES: tuple[str, ...] = (
    ADETAILER_WARNING_DETECTOR_NOT_IN_CATALOG,
    ADETAILER_WARNING_DETECTOR_RUNTIME_FALLBACK_MASK,
    ADETAILER_WARNING_CONTROLNET_PASSTHROUGH_EMPTY,
    ADETAILER_WARNING_CONTROLNET_CUSTOM_MODEL_MISSING,
)

_ADETAILER_WARNING_MESSAGES = {
    ADETAILER_WARNING_UNIT_LIMIT_TRUNCATED: "ADetailer unit payload exceeded the supported 4-unit contract and was truncated.",
    ADETAILER_WARNING_SKIP_IMG2IMG_IGNORED: "ADetailer skip-img2img is only meaningful for img2img surfaces and was ignored.",
    ADETAILER_WARNING_NO_ACTIVE_UNITS: "ADetailer is enabled but no enabled unit has a detector selected.",
    ADETAILER_WARNING_DETECTOR_NOT_IN_CATALOG: "ADetailer detector is not present in the current host catalog; fallback mask behavior may be used.",
    ADETAILER_WARNING_DETECTOR_RUNTIME_FALLBACK_MASK: "ADetailer detector runtime degraded to RookieUI's fallback mask seam for the selected provider family.",
    ADETAILER_WARNING_CONTROLNET_PASSTHROUGH_EMPTY: "ADetailer ControlNet passthrough was requested but no primary ControlNet unit is enabled.",
    ADETAILER_WARNING_CONTROLNET_CUSTOM_MODEL_MISSING: "ADetailer custom ControlNet mode was requested without a ControlNet model.",
}


def warning_messages_from_codes(codes: list[str]) -> list[str]:
    return [_ADETAILER_WARNING_MESSAGES[code] for code in codes if code in _ADETAILER_WARNING_MESSAGES]


def build_adetailer_warning_code_payload() -> dict[str, str]:
    return dict(_ADETAILER_WARNING_MESSAGES)
