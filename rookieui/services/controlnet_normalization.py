from __future__ import annotations

from typing import Any, Callable

from rookieui.contracts.controlnet import (
    CONTROLNET_ADVANCED_WEIGHT_PRESETS,
    NormalizedControlNetAdvancedRequest,
    NormalizedControlNetUnit,
)
from rookieui.security.request_guard import normalize_option_label
from rookieui.services.coercion import (
    coerce_bool as _coerce_bool,
    coerce_float as _coerce_float,
    coerce_int as _coerce_int,
)
from rookieui.services.controlnet_catalog import (
    CONTROL_TYPE_ALIASES,
    DEFAULT_CONTROLNET_MODULE,
)
from rookieui.services.controlnet_warnings import (
    CONTROLNET_WARNING_ALIAS_DISABLED,
    CONTROLNET_WARNING_ALIAS_NATIVE_OVERRIDE,
    CONTROLNET_WARNING_FEATURE_DISABLED,
    CONTROLNET_WARNING_UNIT_LIMIT_TRUNCATED,
)

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

_DEFAULT_RESIZE_MODE = "crop_and_resize"
_DEFAULT_CONTROL_MODE = "balanced"
_DEFAULT_HR_OPTION = "both"

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
_ADVANCED_WEIGHT_PRESET_ALIASES = {preset: preset for preset in CONTROLNET_ADVANCED_WEIGHT_PRESETS}


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
    alias_key = "".join(character for character in raw.strip().lower() if character.isalnum())
    # IMPORTANT: keep unknown/legacy control-type labels rollback-safe by degrading to "All" instead of throwing; this avoids breaking older payload snapshots during phased integrated rollout.
    return CONTROL_TYPE_ALIASES.get(alias_key, "All")


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
    resolve_asset_path_fn: Callable[[str], Any],
    store_uploaded_image_fn: Callable[[str], Any],
) -> str:
    raw_asset = normalize_option_label(asset_value, field_name, max_length=80)
    if raw_asset:
        resolve_asset_path_fn(raw_asset)
        return raw_asset

    if isinstance(data_value, str) and data_value.strip():
        return store_uploaded_image_fn(data_value, prefix=upload_prefix).handle

    if fallback_asset:
        resolve_asset_path_fn(fallback_asset)
        return fallback_asset
    if fallback_data:
        return store_uploaded_image_fn(fallback_data, prefix=upload_prefix).handle

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
    inventory_models: list[str],
    strict_model_match: bool,
    fallback_image_asset: str,
    fallback_image_data: str,
    module_aliases: dict[str, str],
    feature_enabled: bool,
    alias_enabled: bool,
    resolve_inventory_selector_fn: Callable[..., str],
    resolve_asset_path_fn: Callable[[str], Any],
    store_uploaded_image_fn: Callable[[str], Any],
    warning_message_builder: Callable[[list[str]], list[str]],
) -> tuple[list[NormalizedControlNetUnit], list[str], list[str]]:
    warning_codes: list[str] = []

    raw_native_units = payload.get("controlnet_units")
    if raw_native_units is not None and not isinstance(raw_native_units, list):
        raise ValueError("controlnet_units must be an array.")

    raw_alias_units = _extract_alias_units(payload.get("alwayson_scripts"))
    if raw_alias_units and not alias_enabled:
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
        return [], warning_codes, warning_message_builder(warning_codes)

    if not feature_enabled:
        warning_codes.append(CONTROLNET_WARNING_FEATURE_DISABLED)
        return [], warning_codes, warning_message_builder(warning_codes)

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
            default_value=DEFAULT_CONTROLNET_MODULE,
        )
        model = resolve_inventory_selector_fn(
            _extract_unit_field(raw_unit, "model"),
            f"controlnet_units[{index}].model",
            default_value="",
            inventory_selectors=inventory_models,
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
            resolve_asset_path_fn=resolve_asset_path_fn,
            store_uploaded_image_fn=store_uploaded_image_fn,
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
            resolve_asset_path_fn=resolve_asset_path_fn,
            store_uploaded_image_fn=store_uploaded_image_fn,
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
    return normalized_units, warning_codes, warning_message_builder(warning_codes)
