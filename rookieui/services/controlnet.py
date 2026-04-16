from __future__ import annotations

import logging

from rookieui.contracts.controlnet_integrated import build_controlnet_integrated_contract_meta
from rookieui.contracts.controlnet import NormalizedControlNetUnit
from rookieui.security.request_guard import resolve_inventory_selector
from rookieui.services.asset_store import decode_image_data, resolve_asset_path, store_uploaded_image
from rookieui.services.controlnet_catalog import (
    ROOKIEUI_CONTROLNET_EXTRA_MODULES_ENV,
    build_control_types_payload,
    build_model_list_payload,
    build_module_alias_map,
    build_module_list_payload,
    discover_controlnet_modules,
    sanitize_controlnet_model_inventory,
)
from rookieui.services.controlnet_detect import build_controlnet_detect_payload as _build_controlnet_detect_payload
from rookieui.services.controlnet_normalization import (
    _normalize_controlnet_advanced_block,
    normalize_controlnet_units as _normalize_controlnet_units,
)
from rookieui.services.controlnet_runtime import (
    image_tensor_from_bytes,
    image_tensor_to_data_url,
    mask_tensor_from_bytes,
    preprocess_controlnet_tensor,
    runtime_dependencies_available,
)
from rookieui.services.controlnet_warnings import (
    CONTROLNET_WARNING_ALIAS_DISABLED,
    CONTROLNET_WARNING_ALIAS_NATIVE_OVERRIDE,
    CONTROLNET_WARNING_FEATURE_DISABLED,
    CONTROLNET_WARNING_PREPROCESSOR_DISABLED,
    CONTROLNET_WARNING_PREPROCESSOR_EMPTY_OUTPUT,
    CONTROLNET_WARNING_PREPROCESSOR_HOST_FALLBACK,
    CONTROLNET_WARNING_PREPROCESSOR_UNAVAILABLE,
    CONTROLNET_WARNING_UNIT_LIMIT_TRUNCATED,
    ROOKIEUI_CONTROLNET_A1111_ALIAS_ENABLED_ENV,
    ROOKIEUI_CONTROLNET_ENABLED_ENV,
    ROOKIEUI_CONTROLNET_PREPROCESSOR_ENABLED_ENV,
    is_controlnet_alias_enabled,
    is_controlnet_enabled,
    is_controlnet_preprocessor_enabled,
    warning_messages_from_codes,
)
from rookieui.services.model_inventory import discover_model_inventory

# IMPORTANT: phase-59 refactor keeps this module as the stable ControlNet facade.
# Route handlers and existing tests should continue importing and patching here while catalog/normalization/detect ownership is split behind it.

__all__ = [
    "CONTROLNET_WARNING_ALIAS_DISABLED",
    "CONTROLNET_WARNING_ALIAS_NATIVE_OVERRIDE",
    "CONTROLNET_WARNING_FEATURE_DISABLED",
    "CONTROLNET_WARNING_PREPROCESSOR_DISABLED",
    "CONTROLNET_WARNING_PREPROCESSOR_EMPTY_OUTPUT",
    "CONTROLNET_WARNING_PREPROCESSOR_HOST_FALLBACK",
    "CONTROLNET_WARNING_PREPROCESSOR_UNAVAILABLE",
    "CONTROLNET_WARNING_UNIT_LIMIT_TRUNCATED",
    "ROOKIEUI_CONTROLNET_A1111_ALIAS_ENABLED_ENV",
    "ROOKIEUI_CONTROLNET_ENABLED_ENV",
    "ROOKIEUI_CONTROLNET_EXTRA_MODULES_ENV",
    "ROOKIEUI_CONTROLNET_PREPROCESSOR_ENABLED_ENV",
    "_normalize_controlnet_advanced_block",
    "build_controlnet_control_types_payload",
    "build_controlnet_detect_payload",
    "build_controlnet_model_list_payload",
    "build_controlnet_module_list_payload",
    "is_controlnet_alias_enabled",
    "is_controlnet_enabled",
    "is_controlnet_preprocessor_enabled",
    "normalize_controlnet_units",
    "warning_messages_from_codes",
]

_LOGGER = logging.getLogger("ComfyUI-RookieUI")


def _coerce_inventory_model_list(inventory_models: object) -> list[object]:
    if inventory_models in (None, ""):
        return []
    try:
        return list(inventory_models)
    except TypeError:
        return []


def normalize_controlnet_units(
    payload: dict[str, object],
    *,
    inventory_models: list[str] | None = None,
    strict_model_match: bool = False,
    fallback_image_asset: str = "",
    fallback_image_data: str = "",
) -> tuple[list[NormalizedControlNetUnit], list[str], list[str]]:
    available_modules = discover_controlnet_modules()
    module_aliases = build_module_alias_map(available_modules)
    normalized_inventory_models = sanitize_controlnet_model_inventory(_coerce_inventory_model_list(inventory_models))
    return _normalize_controlnet_units(
        payload,
        inventory_models=normalized_inventory_models,
        strict_model_match=strict_model_match,
        fallback_image_asset=fallback_image_asset,
        fallback_image_data=fallback_image_data,
        module_aliases=module_aliases,
        feature_enabled=is_controlnet_enabled(),
        alias_enabled=is_controlnet_alias_enabled(),
        resolve_inventory_selector_fn=resolve_inventory_selector,
        resolve_asset_path_fn=resolve_asset_path,
        store_uploaded_image_fn=store_uploaded_image,
        warning_message_builder=warning_messages_from_codes,
    )


def build_controlnet_module_list_payload() -> dict[str, object]:
    contract_meta = build_controlnet_integrated_contract_meta()
    modules = discover_controlnet_modules()
    return build_module_list_payload(contract_meta=contract_meta, modules=modules)


def build_controlnet_model_list_payload() -> dict[str, object]:
    inventory = discover_model_inventory()
    model_list = sanitize_controlnet_model_inventory(_coerce_inventory_model_list(inventory.controlnet))
    return build_model_list_payload(
        inventory_source=inventory.source,
        contract_meta=build_controlnet_integrated_contract_meta(),
        model_list=model_list,
    )


def build_controlnet_control_types_payload() -> dict[str, object]:
    inventory = discover_model_inventory()
    model_list = sanitize_controlnet_model_inventory(_coerce_inventory_model_list(inventory.controlnet))
    module_list = discover_controlnet_modules()
    return build_control_types_payload(
        contract_meta=build_controlnet_integrated_contract_meta(),
        module_list=module_list,
        model_list=model_list,
    )


def build_controlnet_detect_payload(payload: dict[str, object]) -> dict[str, object]:
    available_modules = discover_controlnet_modules()
    module_aliases = build_module_alias_map(available_modules)
    return _build_controlnet_detect_payload(
        payload,
        module_aliases=module_aliases,
        contract_meta=build_controlnet_integrated_contract_meta(),
        preprocessor_enabled=is_controlnet_preprocessor_enabled(),
        runtime_available=runtime_dependencies_available(),
        warning_message_builder=warning_messages_from_codes,
        decode_image_data_fn=decode_image_data,
        image_tensor_from_bytes_fn=image_tensor_from_bytes,
        mask_tensor_from_bytes_fn=mask_tensor_from_bytes,
        preprocess_controlnet_tensor_fn=preprocess_controlnet_tensor,
        image_tensor_to_data_url_fn=image_tensor_to_data_url,
        logger=_LOGGER,
    )
