from __future__ import annotations

import logging
import os
import re
from typing import Any

from rookieui.contracts.controlnet_integrated import (
    CONTROLNET_INTEGRATED_CONTROL_TYPE_ORDER,
    build_controlnet_integrated_contract_meta,
)
from rookieui.contracts.controlnet import (
    CONTROLNET_ADVANCED_WEIGHT_PRESETS,
    NormalizedControlNetAdvancedRequest,
    NormalizedControlNetUnit,
)
from rookieui.security.request_guard import normalize_option_label, resolve_inventory_selector
from rookieui.services.asset_store import decode_image_data, resolve_asset_path, store_uploaded_image
from rookieui.services.coercion import (
    coerce_bool as _coerce_bool,
    coerce_float as _coerce_float,
    coerce_int as _coerce_int,
)
from rookieui.services.controlnet_runtime import (
    CONTROLNET_PREPROCESSOR_OPTION_ORDER,
    image_tensor_from_bytes,
    image_tensor_to_data_url,
    mask_tensor_from_bytes,
    normalize_preprocessor_option_key,
    preprocess_controlnet_tensor,
    runtime_dependencies_available,
)
from rookieui.services.model_inventory import discover_model_inventory

ROOKIEUI_CONTROLNET_ENABLED_ENV = "ROOKIEUI_CONTROLNET_ENABLED"
ROOKIEUI_CONTROLNET_A1111_ALIAS_ENABLED_ENV = "ROOKIEUI_CONTROLNET_A1111_ALIAS_ENABLED"
ROOKIEUI_CONTROLNET_PREPROCESSOR_ENABLED_ENV = "ROOKIEUI_CONTROLNET_PREPROCESSOR_ENABLED"
ROOKIEUI_CONTROLNET_EXTRA_MODULES_ENV = "ROOKIEUI_CONTROLNET_EXTRA_MODULES"

CONTROLNET_WARNING_FEATURE_DISABLED = "CONTROLNET_FEATURE_DISABLED"
CONTROLNET_WARNING_ALIAS_NATIVE_OVERRIDE = "CONTROLNET_ALIAS_NATIVE_OVERRIDE"
CONTROLNET_WARNING_ALIAS_DISABLED = "CONTROLNET_ALIAS_DISABLED"
CONTROLNET_WARNING_UNIT_LIMIT_TRUNCATED = "CONTROLNET_UNIT_LIMIT_TRUNCATED"
CONTROLNET_WARNING_PREPROCESSOR_DISABLED = "CONTROLNET_PREPROCESSOR_DISABLED"
CONTROLNET_WARNING_PREPROCESSOR_UNAVAILABLE = "CONTROLNET_PREPROCESSOR_UNAVAILABLE"
CONTROLNET_WARNING_PREPROCESSOR_HOST_FALLBACK = "CONTROLNET_PREPROCESSOR_HOST_FALLBACK"
CONTROLNET_WARNING_PREPROCESSOR_EMPTY_OUTPUT = "CONTROLNET_PREPROCESSOR_EMPTY_OUTPUT"

_LOGGER = logging.getLogger("ComfyUI-RookieUI")

_MAX_CONTROLNET_UNITS = 8
_MAX_CONTROLNET_LAYER_WEIGHTS = 32
_MAX_CONTROLNET_TIMESTEP_KEYFRAMES = 16
_MIN_WEIGHT = 0.0
_MAX_WEIGHT = 2.0
_MIN_GUIDANCE = 0.0
_MAX_GUIDANCE = 1.0
_MIN_PROCESSOR_RES = 64
_MAX_PROCESSOR_RES = 2048
_MIN_THRESHOLD = 0.0
_MAX_THRESHOLD = 255.0

_DEFAULT_MODULE = "none"
_DEFAULT_RESIZE_MODE = "crop_and_resize"
_DEFAULT_CONTROL_MODE = "balanced"
_DEFAULT_HR_OPTION = "both"

_CONTROLNET_BASE_MODULES = CONTROLNET_PREPROCESSOR_OPTION_ORDER

_CONTROL_TYPE_MODEL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "All": (),
    "Blur": ("blur",),
    "Canny": ("canny",),
    "Depth": ("depth",),
    "IP-Adapter": ("ipadapter", "ip-adapter", "ip_adapter"),
    "Inpaint": ("inpaint",),
    "Instant-ID": ("instantid", "instant-id", "instant_id"),
    "Lineart": ("lineart",),
    "MLSD": ("mlsd",),
    "NormalMap": ("normal", "normalmap"),
    "OpenPose": ("openpose", "pose"),
    "Reference": ("reference",),
    "Scribble": ("scribble",),
    "Segmentation": ("seg", "segmentation"),
    "Shuffle": ("shuffle",),
    "Sketch": ("sketch",),
    "SoftEdge": ("softedge", "hed", "soft_edge"),
    "T2I-Adapter": ("t2iadapter", "t2i-adapter", "t2i_adapter"),
    "Tile": ("tile",),
}

_CONTROL_TYPE_MODULE_HINTS: dict[str, tuple[str, ...]] = {
    "All": (),
    "Blur": ("blur",),
    "Canny": ("canny",),
    "Depth": ("depth",),
    "IP-Adapter": ("ipadapter",),
    "Inpaint": ("inpaint",),
    "Instant-ID": ("instantid",),
    "Lineart": ("lineart",),
    "MLSD": ("mlsd",),
    "NormalMap": ("normalmap", "normal"),
    "OpenPose": ("openpose",),
    "Reference": ("reference",),
    "Scribble": ("scribble",),
    "Segmentation": ("segmentation", "seg"),
    "Shuffle": ("shuffle",),
    "Sketch": ("sketch",),
    "SoftEdge": ("softedge", "hed"),
    "T2I-Adapter": ("t2iadapter",),
    "Tile": ("tile",),
}


def _normalize_control_type_alias_key(raw_value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", raw_value.strip().lower())


_CONTROL_TYPE_ALIASES: dict[str, str] = {
    _normalize_control_type_alias_key(name): name for name in CONTROLNET_INTEGRATED_CONTROL_TYPE_ORDER
}
_CONTROL_TYPE_ALIASES.update(
    {
        "normal": "NormalMap",
        "normalmap": "NormalMap",
        "openpose": "OpenPose",
        "ipadapter": "IP-Adapter",
        "instantid": "Instant-ID",
        "t2iadapter": "T2I-Adapter",
    }
)

_CONTROLNET_MODULE_ALIAS_PATCHES = {
    "ip_adapter": "ipadapter",
    "ip-adapter": "ipadapter",
    "instant_id": "instantid",
    "instant-id": "instantid",
    "t2i_adapter": "t2iadapter",
    "t2i-adapter": "t2iadapter",
    "normal_map": "normalmap",
}

_RESIZE_MODE_ALIASES = {
    "just_resize": "just_resize",
    "just resize": "just_resize",
    "crop_and_resize": "crop_and_resize",
    "crop and resize": "crop_and_resize",
    "resize_and_fill": "resize_and_fill",
    "resize and fill": "resize_and_fill",
}
_CONTROL_MODE_ALIASES = {
    "balanced": "balanced",
    "0": "balanced",
    "my_prompt_is_more_important": "prompt",
    "prompt": "prompt",
    "1": "prompt",
    "controlnet_is_more_important": "control",
    "control": "control",
    "2": "control",
}
_HR_OPTION_ALIASES = {
    "both": "both",
    "low res only": "low_res_only",
    "low_res_only": "low_res_only",
    "high res only": "high_res_only",
    "high_res_only": "high_res_only",
}
_ADVANCED_WEIGHT_PRESET_ALIASES = {
    preset: preset for preset in CONTROLNET_ADVANCED_WEIGHT_PRESETS
}

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

_CONTROLNET_GENERATION_MODEL_EXTENSIONS = (".safetensors", ".ckpt", ".pt")


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


def _normalize_module_name(raw_value: object) -> str:
    normalized = normalize_option_label(raw_value, "controlnet_module", max_length=64).strip().lower()
    if not normalized:
        return ""
    token = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    token = _CONTROLNET_MODULE_ALIAS_PATCHES.get(token, token)
    # DEBUG HOTSPOT: module token normalization seam for Control-Type-filtered preprocessor variants.
    # Keep option keys intact here (for UI filtering) and defer base-module collapsing to runtime dispatch.
    return normalize_preprocessor_option_key(token)


def _discover_controlnet_modules() -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def _push(module_name: object) -> None:
        try:
            normalized = _normalize_module_name(module_name)
        except ValueError:
            return
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        ordered.append(normalized)

    for base_module in _CONTROLNET_BASE_MODULES:
        _push(base_module)

    raw_extra_modules = str(os.getenv(ROOKIEUI_CONTROLNET_EXTRA_MODULES_ENV, "")).strip()
    if raw_extra_modules:
        for candidate in re.split(r"[,\n;]+", raw_extra_modules):
            _push(candidate)

    if "none" not in seen:
        ordered.insert(0, "none")
    return ordered


def _build_module_alias_map(modules: list[str]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for module in modules:
        normalized = _normalize_module_name(module)
        if not normalized:
            continue
        aliases[normalized] = normalized
        aliases[normalized.replace("_", "-")] = normalized
        aliases[normalized.replace("_", " ")] = normalized
    return aliases


def _sanitize_controlnet_model_inventory(models: list[str]) -> list[str]:
    normalized_models = [str(model).strip() for model in models if isinstance(model, str) and str(model).strip()]
    if not normalized_models:
        return []
    # DEBUG HOTSPOT: control-model inventory filtering seam.
    # Exclude host annotator/preprocessor checkpoints (commonly *.pth under controlnet_aux ckpts)
    # so the ControlNet model selector stays generation-only and does not leak preprocessing weights.
    filtered = [
        model
        for model in normalized_models
        if str(model).strip().lower().endswith(_CONTROLNET_GENERATION_MODEL_EXTENSIONS)
    ]
    return filtered if filtered else normalized_models


def _filter_models_by_keywords(model_list: list[str], keywords: tuple[str, ...]) -> list[str]:
    if not keywords:
        return list(model_list)
    lowered_keywords = [keyword.lower() for keyword in keywords if keyword]
    if not lowered_keywords:
        return list(model_list)
    return [model for model in model_list if any(keyword in str(model).lower() for keyword in lowered_keywords)]


def _build_type_module_list(control_type: str, module_list: list[str]) -> list[str]:
    if control_type == "All":
        return list(module_list)

    hints = _CONTROL_TYPE_MODULE_HINTS.get(control_type, ())
    if not hints:
        return list(module_list)

    filtered = [
        module for module in module_list if module == "none" or any(hint in module for hint in hints)
    ]
    if not filtered:
        return list(module_list)
    if "none" not in filtered:
        return ["none", *filtered]
    return filtered


def _select_default_model(model_list: list[str]) -> str:
    if not model_list:
        return ""
    for candidate in model_list:
        if "11" in str(candidate).lower():
            return str(candidate)
    return str(model_list[0])


def _normalize_choice(value: object, *, field_name: str, aliases: dict[str, str], default_value: str) -> str:
    raw = normalize_option_label(value, field_name, max_length=64).lower()
    if not raw:
        return default_value
    normalized = aliases.get(raw)
    if normalized is None:
        raise ValueError(f"{field_name} is unsupported.")
    return normalized


def _normalize_control_type(value: object, *, field_name: str) -> str:
    raw = normalize_option_label(value, field_name, max_length=48)
    if not raw:
        return "All"
    alias_key = _normalize_control_type_alias_key(raw)
    # IMPORTANT: keep unknown/legacy control-type labels rollback-safe by degrading to "All" instead of throwing; this avoids breaking older payload snapshots during phased integrated rollout.
    return _CONTROL_TYPE_ALIASES.get(alias_key, "All")


def _coerce_unit_weight(value: object, field_name: str) -> float:
    normalized = round(_coerce_float(value, field_name, default=1.0), 3)
    if normalized < _MIN_WEIGHT or normalized > _MAX_WEIGHT:
        raise ValueError(f"{field_name} must be between {_MIN_WEIGHT} and {_MAX_WEIGHT}.")
    return normalized


def _coerce_unit_guidance(value: object, field_name: str, default_value: float) -> float:
    normalized = round(_coerce_float(value, field_name, default=default_value), 4)
    if normalized < _MIN_GUIDANCE or normalized > _MAX_GUIDANCE:
        raise ValueError(f"{field_name} must be between {_MIN_GUIDANCE} and {_MAX_GUIDANCE}.")
    return normalized


def _coerce_processor_res(value: object, field_name: str) -> int:
    normalized = _coerce_int(value, field_name, default=512)
    if normalized < _MIN_PROCESSOR_RES or normalized > _MAX_PROCESSOR_RES:
        raise ValueError(f"{field_name} must be between {_MIN_PROCESSOR_RES} and {_MAX_PROCESSOR_RES}.")
    return normalized


def _coerce_threshold(value: object, field_name: str, default_value: float) -> float:
    normalized = round(_coerce_float(value, field_name, default=default_value), 3)
    if normalized < _MIN_THRESHOLD or normalized > _MAX_THRESHOLD:
        raise ValueError(f"{field_name} must be between {_MIN_THRESHOLD} and {_MAX_THRESHOLD}.")
    return normalized


def _normalize_controlnet_advanced_block(
    raw_block: object,
    *,
    field_prefix: str,
) -> NormalizedControlNetAdvancedRequest:
    if raw_block in (None, "", False):
        return NormalizedControlNetAdvancedRequest()
    if not isinstance(raw_block, dict):
        raise ValueError(f"{field_prefix} must be an object.")

    enabled = _coerce_bool(raw_block.get("enabled", True), f"{field_prefix}.enabled", default=True, strict=False)
    preset = _normalize_choice(
        raw_block.get("weight_preset"),
        field_name=f"{field_prefix}.weight_preset",
        aliases=_ADVANCED_WEIGHT_PRESET_ALIASES,
        default_value="balanced",
    )

    raw_layer_weights = raw_block.get("layer_weights", [])
    if raw_layer_weights in (None, ""):
        raw_layer_weights = []
    if not isinstance(raw_layer_weights, list):
        raise ValueError(f"{field_prefix}.layer_weights must be an array.")
    if len(raw_layer_weights) > _MAX_CONTROLNET_LAYER_WEIGHTS:
        raise ValueError(
            f"{field_prefix}.layer_weights supports at most {_MAX_CONTROLNET_LAYER_WEIGHTS} entries."
        )
    layer_weights = [
        round(_coerce_float(value, f"{field_prefix}.layer_weights[{index}]"), 4)
        for index, value in enumerate(raw_layer_weights)
    ]
    for index, value in enumerate(layer_weights):
        if value < 0.0 or value > _MAX_WEIGHT:
            raise ValueError(f"{field_prefix}.layer_weights[{index}] must be between 0.0 and {_MAX_WEIGHT}.")

    raw_keyframes = raw_block.get("timestep_keyframes", [])
    if raw_keyframes in (None, ""):
        raw_keyframes = []
    if not isinstance(raw_keyframes, list):
        raise ValueError(f"{field_prefix}.timestep_keyframes must be an array.")
    if len(raw_keyframes) > _MAX_CONTROLNET_TIMESTEP_KEYFRAMES:
        raise ValueError(
            f"{field_prefix}.timestep_keyframes supports at most {_MAX_CONTROLNET_TIMESTEP_KEYFRAMES} entries."
        )
    timestep_keyframes: list[dict[str, float]] = []
    for index, entry in enumerate(raw_keyframes):
        if not isinstance(entry, dict):
            raise ValueError(f"{field_prefix}.timestep_keyframes[{index}] must be an object.")
        start_percent = _coerce_unit_guidance(
            entry.get("start_percent"),
            f"{field_prefix}.timestep_keyframes[{index}].start_percent",
            0.0,
        )
        end_percent = _coerce_unit_guidance(
            entry.get("end_percent"),
            f"{field_prefix}.timestep_keyframes[{index}].end_percent",
            1.0,
        )
        if end_percent < start_percent:
            raise ValueError(
                f"{field_prefix}.timestep_keyframes[{index}].end_percent must be >= start_percent."
            )
        strength_scale = _coerce_unit_weight(
            entry.get("strength_scale", 1.0),
            f"{field_prefix}.timestep_keyframes[{index}].strength_scale",
        )
        timestep_keyframes.append(
            {
                "start_percent": start_percent,
                "end_percent": end_percent,
                "strength_scale": strength_scale,
            }
        )

    return NormalizedControlNetAdvancedRequest(
        enabled=enabled,
        weight_preset=preset,
        layer_weights=layer_weights,
        timestep_keyframes=timestep_keyframes,
        mask_aware_apply=_coerce_bool(
            raw_block.get("mask_aware_apply"),
            f"{field_prefix}.mask_aware_apply",
            default=False,
            strict=False,
        ),
    )


def _resolve_unit_asset(
    *,
    asset_value: object,
    data_value: object,
    field_name: str,
    data_field_name: str,
    upload_prefix: str,
    fallback_asset: str,
    fallback_data: str,
    required: bool,
) -> str:
    raw_asset = normalize_option_label(asset_value, field_name, max_length=80)
    if raw_asset:
        resolve_asset_path(raw_asset)
        return raw_asset

    if isinstance(data_value, str) and data_value.strip():
        return store_uploaded_image(data_value, prefix=upload_prefix).handle

    if fallback_asset:
        resolve_asset_path(fallback_asset)
        return fallback_asset
    if fallback_data:
        return store_uploaded_image(fallback_data, prefix=upload_prefix).handle

    if required:
        raise ValueError(f"{field_name} or {data_field_name} is required.")
    return ""


def _extract_alias_units(alwayson_scripts: object) -> list[object]:
    if not isinstance(alwayson_scripts, dict):
        return []
    for key, value in alwayson_scripts.items():
        if str(key).strip().lower() != "controlnet":
            continue
        if not isinstance(value, dict):
            return []
        args = value.get("args", [])
        return args if isinstance(args, list) else []
    return []


def _extract_unit_field(raw_unit: dict[str, object], field_name: str, alias_field_name: str | None = None) -> object:
    if field_name in raw_unit:
        return raw_unit.get(field_name)
    if alias_field_name and alias_field_name in raw_unit:
        return raw_unit.get(alias_field_name)
    return None


def _extract_alias_image_payload(raw_unit: dict[str, object]) -> tuple[object, object]:
    image_value = raw_unit.get("image")
    mask_value = raw_unit.get("mask")
    input_image = raw_unit.get("input_image")
    if isinstance(input_image, dict):
        if image_value in (None, ""):
            image_value = input_image.get("image")
        if mask_value in (None, ""):
            mask_value = input_image.get("mask")
    return image_value, mask_value


def normalize_controlnet_units(
    payload: dict[str, object],
    *,
    inventory_models: list[str] | None = None,
    strict_model_match: bool = False,
    fallback_image_asset: str = "",
    fallback_image_data: str = "",
) -> tuple[list[NormalizedControlNetUnit], list[str], list[str]]:
    warning_codes: list[str] = []
    available_modules = _discover_controlnet_modules()
    module_aliases = _build_module_alias_map(available_modules)

    raw_native_units = payload.get("controlnet_units")
    if raw_native_units is not None and not isinstance(raw_native_units, list):
        raise ValueError("controlnet_units must be an array.")

    raw_alias_units = _extract_alias_units(payload.get("alwayson_scripts"))
    if raw_alias_units and not is_controlnet_alias_enabled():
        warning_codes.append(CONTROLNET_WARNING_ALIAS_DISABLED)
        raw_alias_units = []

    if raw_native_units and raw_alias_units:
        warning_codes.append(CONTROLNET_WARNING_ALIAS_NATIVE_OVERRIDE)

    selected_units: list[object] = (
        raw_native_units
        if isinstance(raw_native_units, list) and len(raw_native_units) > 0
        else raw_alias_units
    )
    if not selected_units:
        return [], warning_codes, warning_messages_from_codes(warning_codes)

    if not is_controlnet_enabled():
        warning_codes.append(CONTROLNET_WARNING_FEATURE_DISABLED)
        return [], warning_codes, warning_messages_from_codes(warning_codes)

    normalized_inventory_models = _sanitize_controlnet_model_inventory(list(inventory_models or []))
    units = selected_units[:_MAX_CONTROLNET_UNITS]
    if len(selected_units) > _MAX_CONTROLNET_UNITS:
        warning_codes.append(CONTROLNET_WARNING_UNIT_LIMIT_TRUNCATED)

    normalized_units: list[NormalizedControlNetUnit] = []
    for index, raw_unit in enumerate(units):
        if not isinstance(raw_unit, dict):
            raise ValueError(f"controlnet_units[{index}] must be an object.")

        source = "native" if raw_unit in (raw_native_units or []) else "alwayson_scripts.controlnet"
        image_value, mask_value = _extract_alias_image_payload(raw_unit)
        enabled = _coerce_bool(raw_unit.get("enabled", True), f"controlnet_units[{index}].enabled", strict=False)
        module = _normalize_choice(
            _extract_unit_field(raw_unit, "module", "preprocessor"),
            field_name=f"controlnet_units[{index}].module",
            aliases=module_aliases,
            default_value=_DEFAULT_MODULE,
        )
        model = resolve_inventory_selector(
            _extract_unit_field(raw_unit, "model"),
            f"controlnet_units[{index}].model",
            default_value="",
            inventory_selectors=normalized_inventory_models,
            strict_match=strict_model_match,
        )
        if enabled and not model:
            raise ValueError(f"controlnet_units[{index}].model is required when enabled.")

        image_asset = _resolve_unit_asset(
            asset_value=_extract_unit_field(raw_unit, "image_asset") or image_value,
            data_value=_extract_unit_field(raw_unit, "image_data") or image_value,
            field_name=f"controlnet_units[{index}].image_asset",
            data_field_name=f"controlnet_units[{index}].image_data",
            upload_prefix="rookieui_controlnet_input",
            fallback_asset=fallback_image_asset,
            fallback_data=fallback_image_data,
            required=enabled,
        )
        mask_asset = _resolve_unit_asset(
            asset_value=_extract_unit_field(raw_unit, "mask_asset") or mask_value,
            data_value=_extract_unit_field(raw_unit, "mask_data") or mask_value,
            field_name=f"controlnet_units[{index}].mask_asset",
            data_field_name=f"controlnet_units[{index}].mask_data",
            upload_prefix="rookieui_controlnet_mask",
            fallback_asset="",
            fallback_data="",
            required=False,
        )
        use_mask_value = _extract_unit_field(raw_unit, "use_mask")
        use_mask = _coerce_bool(
            use_mask_value,
            f"controlnet_units[{index}].use_mask",
            default=False,
            strict=False,
        )
        if use_mask_value is None and mask_asset:
            # IMPORTANT: preserve legacy payload compatibility; historical unit payloads may carry mask_asset without an explicit use_mask toggle.
            use_mask = True
        control_type = _normalize_control_type(
            _extract_unit_field(raw_unit, "control_type", "type"),
            field_name=f"controlnet_units[{index}].control_type",
        )
        allow_preview = _coerce_bool(
            _extract_unit_field(raw_unit, "allow_preview"),
            f"controlnet_units[{index}].allow_preview",
            default=False,
            strict=False,
        )
        advanced = _normalize_controlnet_advanced_block(
            _extract_unit_field(raw_unit, "advanced"),
            field_prefix=f"controlnet_units[{index}].advanced",
        )

        weight = _coerce_unit_weight(raw_unit.get("weight", 1.0), f"controlnet_units[{index}].weight")
        guidance_start = _coerce_unit_guidance(
            _extract_unit_field(raw_unit, "guidance_start"),
            f"controlnet_units[{index}].guidance_start",
            0.0,
        )
        guidance_end = _coerce_unit_guidance(
            _extract_unit_field(raw_unit, "guidance_end"),
            f"controlnet_units[{index}].guidance_end",
            1.0,
        )
        if guidance_end < guidance_start:
            raise ValueError(f"controlnet_units[{index}].guidance_end must be >= guidance_start.")
        resize_mode = _normalize_choice(
            _extract_unit_field(raw_unit, "resize_mode"),
            field_name=f"controlnet_units[{index}].resize_mode",
            aliases=_RESIZE_MODE_ALIASES,
            default_value=_DEFAULT_RESIZE_MODE,
        )
        control_mode = _normalize_choice(
            _extract_unit_field(raw_unit, "control_mode"),
            field_name=f"controlnet_units[{index}].control_mode",
            aliases=_CONTROL_MODE_ALIASES,
            default_value=_DEFAULT_CONTROL_MODE,
        )
        processor_res = _coerce_processor_res(
            _extract_unit_field(raw_unit, "processor_res"),
            f"controlnet_units[{index}].processor_res",
        )
        threshold_a = _coerce_threshold(
            _extract_unit_field(raw_unit, "threshold_a"),
            f"controlnet_units[{index}].threshold_a",
            64.0,
        )
        threshold_b = _coerce_threshold(
            _extract_unit_field(raw_unit, "threshold_b"),
            f"controlnet_units[{index}].threshold_b",
            64.0,
        )
        pixel_perfect = _coerce_bool(
            _extract_unit_field(raw_unit, "pixel_perfect"),
            f"controlnet_units[{index}].pixel_perfect",
            default=False,
            strict=False,
        )
        hr_option = _normalize_choice(
            _extract_unit_field(raw_unit, "hr_option"),
            field_name=f"controlnet_units[{index}].hr_option",
            aliases=_HR_OPTION_ALIASES,
            default_value=_DEFAULT_HR_OPTION,
        )
        normalized_units.append(
            NormalizedControlNetUnit(
                enabled=enabled,
                module=module,
                model=model,
                weight=weight,
                guidance_start=guidance_start,
                guidance_end=guidance_end,
                resize_mode=resize_mode,
                control_mode=control_mode,
                processor_res=processor_res,
                threshold_a=threshold_a,
                threshold_b=threshold_b,
                pixel_perfect=pixel_perfect,
                hr_option=hr_option,
                image_asset=image_asset,
                mask_asset=mask_asset,
                source=source,
                control_type=control_type,
                use_mask=use_mask,
                allow_preview=allow_preview,
                advanced=advanced,
            )
        )

    warning_codes = list(dict.fromkeys(warning_codes))
    return normalized_units, warning_codes, warning_messages_from_codes(warning_codes)


def build_controlnet_module_list_payload() -> dict[str, object]:
    modules = _discover_controlnet_modules()
    return {
        "source": "internal",
        "contract": build_controlnet_integrated_contract_meta(),
        "module_list": modules,
        "default_module": _DEFAULT_MODULE,
    }


def build_controlnet_model_list_payload() -> dict[str, object]:
    inventory = discover_model_inventory()
    model_list = _sanitize_controlnet_model_inventory(list(inventory.controlnet))
    return {
        "source": inventory.source,
        "contract": build_controlnet_integrated_contract_meta(),
        "model_list": model_list,
        "default_model": "",
    }


def build_controlnet_control_types_payload() -> dict[str, object]:
    model_list = list(build_controlnet_model_list_payload()["model_list"])
    module_list = _discover_controlnet_modules()
    control_types: dict[str, dict[str, object]] = {}

    for control_type in CONTROLNET_INTEGRATED_CONTROL_TYPE_ORDER:
        type_module_list = _build_type_module_list(control_type, module_list)
        type_model_list = (
            _filter_models_by_keywords(model_list, _CONTROL_TYPE_MODEL_KEYWORDS.get(control_type, ()))
            if control_type != "All"
            else list(model_list)
        )
        if not type_model_list:
            type_model_list = list(model_list)

        default_option = _DEFAULT_MODULE
        if control_type != "All":
            default_option = next((module for module in type_module_list if module != "none"), _DEFAULT_MODULE)

        control_types[control_type] = {
            "module_list": type_module_list,
            "model_list": type_model_list,
            "default_option": default_option,
            "default_model": _select_default_model(type_model_list),
        }

    return {
        "source": "internal",
        "contract": build_controlnet_integrated_contract_meta(),
        "control_type_order": list(CONTROLNET_INTEGRATED_CONTROL_TYPE_ORDER),
        "default_type": "All",
        "control_types": control_types,
    }


def _normalize_detect_images(payload: dict[str, object]) -> list[str]:
    raw_images = payload.get("controlnet_input_images")
    if isinstance(raw_images, list) and raw_images:
        images = [entry for entry in raw_images if isinstance(entry, str) and entry.strip()]
    else:
        single_image = payload.get("image")
        images = [single_image] if isinstance(single_image, str) and single_image.strip() else []
    if not images:
        raise ValueError("controlnet_input_images or image is required.")
    if len(images) > 8:
        raise ValueError("controlnet_input_images must contain at most 8 images.")
    return images


def _normalize_detect_masks(payload: dict[str, object], *, image_count: int) -> list[str]:
    raw_masks = payload.get("controlnet_masks")
    if raw_masks is None:
        return []
    if not isinstance(raw_masks, list):
        raise ValueError("controlnet_masks must be an array when provided.")
    masks = [entry for entry in raw_masks if isinstance(entry, str) and entry.strip()]
    if masks and len(masks) != image_count:
        raise ValueError("controlnet_masks must be empty or match controlnet_input_images length.")
    return masks


def build_controlnet_detect_payload(payload: dict[str, object]) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError("ControlNet detect payload must be an object.")

    available_modules = _discover_controlnet_modules()
    module_aliases = _build_module_alias_map(available_modules)
    module = _normalize_choice(
        payload.get("controlnet_module"),
        field_name="controlnet_module",
        aliases=module_aliases,
        default_value=_DEFAULT_MODULE,
    )
    requested_controlnet_model = normalize_option_label(
        payload.get("controlnet_model"),
        "controlnet_model",
        max_length=256,
    )
    input_images = _normalize_detect_images(payload)
    warning_codes: list[str] = []

    if module == "none":
        return {
            "source": "rookieui",
            "detect_backend": "passthrough_none",
            "contract": build_controlnet_integrated_contract_meta(),
            "module": module,
            "requested_controlnet_model": requested_controlnet_model,
            "images": input_images,
            "warning_codes": warning_codes,
            "warnings": warning_messages_from_codes(warning_codes),
        }

    processor_res = _coerce_processor_res(payload.get("controlnet_processor_res"), "controlnet_processor_res")
    threshold_a = _coerce_threshold(payload.get("controlnet_threshold_a"), "controlnet_threshold_a", 64.0)
    threshold_b = _coerce_threshold(payload.get("controlnet_threshold_b"), "controlnet_threshold_b", 64.0)
    input_masks = _normalize_detect_masks(payload, image_count=len(input_images))
    if len(input_masks) < len(input_images):
        input_masks.extend([""] * (len(input_images) - len(input_masks)))
    _ = _coerce_bool(payload.get("low_vram"), "low_vram", default=False, strict=False)

    if not is_controlnet_preprocessor_enabled():
        warning_codes.append(CONTROLNET_WARNING_PREPROCESSOR_DISABLED)
        return {
            "source": "rookieui",
            "detect_backend": "rookieui_internal_disabled",
            "contract": build_controlnet_integrated_contract_meta(),
            "module": module,
            "requested_controlnet_model": requested_controlnet_model,
            "images": input_images,
            "warning_codes": warning_codes,
            "warnings": warning_messages_from_codes(warning_codes),
        }

    if not runtime_dependencies_available():
        warning_codes.append(CONTROLNET_WARNING_PREPROCESSOR_UNAVAILABLE)
        return {
            "source": "rookieui",
            "detect_backend": "rookieui_internal_unavailable",
            "contract": build_controlnet_integrated_contract_meta(),
            "module": module,
            "requested_controlnet_model": requested_controlnet_model,
            "images": input_images,
            "warning_codes": warning_codes,
            "warnings": warning_messages_from_codes(warning_codes),
        }

    output_images: list[str] = []
    backend_labels: list[str] = []
    processor_names: list[str] = []
    fallback_used = False
    fallback_diagnostics: list[str] = []
    near_empty_diagnostics: list[str] = []
    for index, raw_image in enumerate(input_images):
        try:
            image_bytes, _ = decode_image_data(raw_image)
            image_tensor = image_tensor_from_bytes(image_bytes)
            mask_tensor = None
            raw_mask = input_masks[index]
            if raw_mask:
                mask_bytes, _ = decode_image_data(raw_mask)
                mask_tensor = mask_tensor_from_bytes(mask_bytes)
            runtime_result = preprocess_controlnet_tensor(
                image_tensor=image_tensor,
                module=module,
                processor_res=processor_res,
                threshold_a=threshold_a,
                threshold_b=threshold_b,
                mask_tensor=mask_tensor,
            )
            # DEBUG HOTSPOT: inspect per-image runtime seam first when preprocess output appears visually incorrect.
            # This captures backend/processor provenance before payload-level warning aggregation.
            backend_labels.append(runtime_result.backend)
            processor_names.append(runtime_result.processor_name)
            if runtime_result.used_fallback:
                fallback_used = True
                fallback_diagnostics.extend(list(runtime_result.diagnostics))
            else:
                # DEBUG HOTSPOT: successful-host-but-empty-output seam; this isolates black/blank previews
                # that are not runtime failures and should surface as targeted warnings.
                near_empty_diagnostics.extend(
                    [entry for entry in runtime_result.diagnostics if "output_near_empty" in str(entry)]
                )
            output_images.append(image_tensor_to_data_url(runtime_result.image))
        except Exception as exc:
            raise ValueError(f"controlnet_input_images[{index}] or controlnet_masks[{index}] is not a valid image payload.") from exc

    if fallback_used:
        warning_codes.append(CONTROLNET_WARNING_PREPROCESSOR_HOST_FALLBACK)
        if fallback_diagnostics:
            # DEBUG HOTSPOT: primary fallback triage seam for run-preprocessor regressions.
            # Prioritize markers like `prompt_server_last_prompt_id_shim_applied`, node exception text, and probe-limit diagnostics.
            _LOGGER.warning(
                "RookieUI ControlNet detect host preprocessor fallback engaged (module=%s): %s",
                module,
                " | ".join(fallback_diagnostics[:3]),
            )
    if near_empty_diagnostics:
        warning_codes.append(CONTROLNET_WARNING_PREPROCESSOR_EMPTY_OUTPUT)
        # DEBUG HOTSPOT: near-empty host output seam (often seen in pose/seg detectors on incompatible crops).
        _LOGGER.warning(
            "RookieUI ControlNet detect host preprocessor produced near-empty output (module=%s): %s",
            module,
            " | ".join(near_empty_diagnostics[:3]),
        )

    detect_backend = "rookieui_internal"
    if backend_labels:
        unique_backends = list(dict.fromkeys(backend_labels))
        detect_backend = unique_backends[0] if len(unique_backends) == 1 else "rookieui_internal_mixed"

    return {
        "source": "rookieui",
        "detect_backend": detect_backend,
        "contract": build_controlnet_integrated_contract_meta(),
        "module": module,
        "requested_controlnet_model": requested_controlnet_model,
        "processor": processor_names[0] if processor_names else module,
        "images": output_images,
        "warning_codes": warning_codes,
        "warnings": warning_messages_from_codes(warning_codes),
    }
