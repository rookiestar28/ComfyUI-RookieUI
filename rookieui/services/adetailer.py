from __future__ import annotations

from rookieui.contracts.adetailer import build_adetailer_integrated_contract_meta
from rookieui.services.compatibility import build_compatibility_payload
from rookieui.services.controlnet import build_controlnet_model_list_payload, build_controlnet_module_list_payload
from rookieui.services.adetailer_catalog import (
    build_adetailer_availability_payload as _build_adetailer_availability_payload,
    build_adetailer_capability_payload as _build_adetailer_capability_payload,
    build_adetailer_catalog_payload as _build_adetailer_catalog_payload,
    build_detector_entries,
)
from rookieui.services.adetailer_normalization import (
    ADetailerNormalizationContext,
    normalize_adetailer_payload as _normalize_adetailer_payload,
)
from rookieui.services.adetailer_runtime import (
    build_detector_runtime_availability,
    detector_runtime_is_degraded,
    summarize_detector_runtime,
)
from rookieui.services.adetailer_warnings import (
    ADETAILER_DEGRADED_WARNING_CODES,
    ADETAILER_WARNING_CONTROLNET_CUSTOM_MODEL_MISSING,
    ADETAILER_WARNING_CONTROLNET_PASSTHROUGH_EMPTY,
    ADETAILER_WARNING_DETECTOR_NOT_IN_CATALOG,
    ADETAILER_WARNING_DETECTOR_RUNTIME_FALLBACK_MASK,
    ADETAILER_WARNING_NO_ACTIVE_UNITS,
    ADETAILER_WARNING_SKIP_IMG2IMG_IGNORED,
    ADETAILER_WARNING_UNIT_LIMIT_TRUNCATED,
    build_adetailer_warning_code_payload,
    warning_messages_from_codes,
)
from rookieui.services.model_inventory import discover_model_inventory

# IMPORTANT: phase-59 refactor keeps this module as the stable ADetailer facade.
# Route/catalog consumers should continue importing and patching here while catalog/normalization/refinement ownership is split behind it.

__all__ = [
    "ADETAILER_WARNING_CONTROLNET_CUSTOM_MODEL_MISSING",
    "ADETAILER_WARNING_CONTROLNET_PASSTHROUGH_EMPTY",
    "ADETAILER_WARNING_DETECTOR_NOT_IN_CATALOG",
    "ADETAILER_WARNING_DETECTOR_RUNTIME_FALLBACK_MASK",
    "ADETAILER_WARNING_NO_ACTIVE_UNITS",
    "ADETAILER_WARNING_SKIP_IMG2IMG_IGNORED",
    "ADETAILER_WARNING_UNIT_LIMIT_TRUNCATED",
    "build_adetailer_availability_payload",
    "build_adetailer_capability_payload",
    "build_adetailer_catalog_payload",
    "build_adetailer_warning_code_payload",
    "normalize_adetailer_payload",
]


def _build_catalog_inputs() -> tuple[object, list[dict[str, object]], str, list[str], list[str], dict[str, object]]:
    inventory = discover_model_inventory()
    detector_entries, detector_source = build_detector_entries(inventory=inventory)
    controlnet_models = list(build_controlnet_model_list_payload().get("model_list", []))
    controlnet_modules = list(build_controlnet_module_list_payload().get("module_list", []))
    detector_runtime = build_detector_runtime_availability()
    return inventory, detector_entries, detector_source, controlnet_models, controlnet_modules, detector_runtime


def build_adetailer_availability_payload() -> dict[str, object]:
    _, detector_entries, detector_source, controlnet_models, _, detector_runtime = _build_catalog_inputs()
    return _build_adetailer_availability_payload(
        detector_entries=detector_entries,
        detector_source=detector_source,
        controlnet_models=controlnet_models,
        detector_runtime=detector_runtime,
        degraded_warning_codes=list(ADETAILER_DEGRADED_WARNING_CODES),
    )


def build_adetailer_catalog_payload() -> dict[str, object]:
    inventory, detector_entries, detector_source, controlnet_models, controlnet_modules, detector_runtime = (
        _build_catalog_inputs()
    )
    availability_payload = _build_adetailer_availability_payload(
        detector_entries=detector_entries,
        detector_source=detector_source,
        controlnet_models=controlnet_models,
        detector_runtime=detector_runtime,
        degraded_warning_codes=list(ADETAILER_DEGRADED_WARNING_CODES),
    )
    return _build_adetailer_catalog_payload(
        contract_meta=build_adetailer_integrated_contract_meta(),
        detector_entries=detector_entries,
        detector_source=detector_source,
        compatibility_payload=build_compatibility_payload(),
        controlnet_models=controlnet_models,
        controlnet_modules=controlnet_modules,
        inventory=inventory,
        availability_payload=availability_payload,
        warning_code_payload=build_adetailer_warning_code_payload(),
    )


def build_adetailer_capability_payload() -> dict[str, object]:
    return _build_adetailer_capability_payload(
        contract_meta=build_adetailer_integrated_contract_meta(),
        availability_payload=build_adetailer_availability_payload(),
        warning_code_payload=build_adetailer_warning_code_payload(),
    )


def normalize_adetailer_payload(
    payload: dict[str, object],
    *,
    profile_id: str,
    surface: str,
    strict_inventory_match: bool,
    primary_controlnet_unit_count: int = 0,
):
    inventory, detector_entries, _, controlnet_models, controlnet_modules, detector_runtime = _build_catalog_inputs()
    return _normalize_adetailer_payload(
        payload,
        profile_id=profile_id,
        surface=surface,
        strict_inventory_match=strict_inventory_match,
        primary_controlnet_unit_count=primary_controlnet_unit_count,
        context=ADetailerNormalizationContext(
            detector_entries=detector_entries,
            controlnet_model_list=controlnet_models,
            controlnet_module_list=controlnet_modules,
            inventory=inventory,
            compatibility_payload=build_compatibility_payload(),
            detector_runtime=detector_runtime,
        ),
        warning_message_builder=warning_messages_from_codes,
        detector_runtime_is_degraded_fn=detector_runtime_is_degraded,
        summarize_detector_runtime_fn=summarize_detector_runtime,
    )
