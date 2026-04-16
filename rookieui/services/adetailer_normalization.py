from __future__ import annotations

from dataclasses import dataclass

from rookieui.contracts.adetailer import (
    ADETAILER_INTEGRATED_DEFAULT_UNIT_COUNT,
    NormalizedADetailerRequest,
)
from rookieui.services.model_inventory import resolve_primary_model_selector_context
from rookieui.services.adetailer_refinement import (
    build_normalized_unit_request,
    finalize_adetailer_warnings_and_diagnostics,
)
from rookieui.services.adetailer_warnings import (
    ADETAILER_WARNING_SKIP_IMG2IMG_IGNORED,
    ADETAILER_WARNING_UNIT_LIMIT_TRUNCATED,
)
from rookieui.services.coercion import coerce_bool as _coerce_bool


@dataclass(frozen=True)
class ADetailerNormalizationContext:
    detector_entries: list[dict[str, object]]
    controlnet_model_list: list[str]
    controlnet_module_list: list[str]
    inventory: object
    compatibility_payload: dict[str, object]
    detector_runtime: dict[str, object]


def _coerce_string_list(values: object) -> list[str]:
    if values in (None, ""):
        return []
    try:
        iterable = list(values)
    except TypeError:
        return []
    return [str(value).strip() for value in iterable if isinstance(value, str) and str(value).strip()]


def normalize_adetailer_payload(
    payload: dict[str, object],
    *,
    profile_id: str,
    surface: str,
    strict_inventory_match: bool,
    primary_controlnet_unit_count: int = 0,
    context: ADetailerNormalizationContext,
    warning_message_builder,
    detector_runtime_is_degraded_fn,
    summarize_detector_runtime_fn,
) -> NormalizedADetailerRequest:
    raw_block = payload.get("adetailer", {})
    if raw_block in (None, ""):
        raw_block = {}
    if not isinstance(raw_block, dict):
        raise ValueError("adetailer must be an object.")

    enabled = _coerce_bool(raw_block.get("enabled", False), "adetailer.enabled", strict=False)
    skip_img2img = _coerce_bool(raw_block.get("skip_img2img", False), "adetailer.skip_img2img", strict=False)
    warning_codes: list[str] = []
    if surface != "img2img" and skip_img2img:
        warning_codes.append(ADETAILER_WARNING_SKIP_IMG2IMG_IGNORED)
        skip_img2img = False

    raw_units = raw_block.get("units", [])
    if raw_units in (None, ""):
        raw_units = []
    if not isinstance(raw_units, list):
        raise ValueError("adetailer.units must be an array.")
    if len(raw_units) > ADETAILER_INTEGRATED_DEFAULT_UNIT_COUNT:
        warning_codes.append(ADETAILER_WARNING_UNIT_LIMIT_TRUNCATED)

    detector_choices = [str(entry["id"]) for entry in context.detector_entries]
    _, primary_model_selectors, _ = resolve_primary_model_selector_context(profile_id, context.inventory)
    sampler_choices = [
        entry["title"] for entry in context.compatibility_payload.get("samplers", []) if isinstance(entry, dict)
    ]
    scheduler_choices = [
        entry["title"] for entry in context.compatibility_payload.get("schedulers", []) if isinstance(entry, dict)
    ]
    vae_choices = _coerce_string_list(getattr(context.inventory, "vae", []))

    units = [
        build_normalized_unit_request(
            raw_units[index] if index < len(raw_units) and isinstance(raw_units[index], dict) else {},
            index=index,
            detector_choices=detector_choices,
            strict_inventory_match=strict_inventory_match,
            controlnet_model_list=context.controlnet_model_list,
            controlnet_module_list=context.controlnet_module_list,
            primary_model_selectors=primary_model_selectors,
            vae_choices=vae_choices,
            sampler_choices=sampler_choices,
            scheduler_choices=scheduler_choices,
        )
        for index in range(ADETAILER_INTEGRATED_DEFAULT_UNIT_COUNT)
    ]

    warning_codes, diagnostics = finalize_adetailer_warnings_and_diagnostics(
        enabled=enabled,
        units=units,
        detector_choices=detector_choices,
        primary_controlnet_unit_count=primary_controlnet_unit_count,
        detector_runtime=context.detector_runtime,
        warning_codes=warning_codes,
        detector_runtime_is_degraded_fn=detector_runtime_is_degraded_fn,
        summarize_detector_runtime_fn=summarize_detector_runtime_fn,
    )
    return NormalizedADetailerRequest(
        enabled=enabled,
        skip_img2img=skip_img2img,
        units=units,
        warning_codes=warning_codes,
        warnings=warning_message_builder(warning_codes),
        diagnostics=diagnostics,
    )
