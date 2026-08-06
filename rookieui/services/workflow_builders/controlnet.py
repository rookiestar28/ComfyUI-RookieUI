from __future__ import annotations

import json

from rookieui.contracts.adetailer import NormalizedADetailerControlNetRequest
from rookieui.contracts.controlnet import NormalizedControlNetUnit
from rookieui.contracts.controlnet import CONTROLNET_UNION_TYPE_BY_CONTROL_TYPE
from rookieui.contracts.generation import (
    NormalizedImg2ImgRequest,
    NormalizedTxt2ImgRequest,
)
from rookieui.services.controlnet_advanced_runtime import (
    build_controlnet_apply_segments,
    resolve_controlnet_stage_profile,
)
from rookieui.services.workflow_builders.core import (
    NodeIdAllocator,
    _to_node_ref,
)


def _read_controlnet_unit_value(
    unit: NormalizedControlNetUnit | NormalizedADetailerControlNetRequest | dict[str, object],
    key: str,
) -> object:
    if isinstance(unit, dict):
        return unit.get(key)
    return getattr(unit, key, None)


def _float_or_default(value: object, default: float) -> float:
    # CRITICAL: numeric zero is an effective ControlNet value; only absence may select a default.
    return float(default if value is None else value)


def _int_or_default(value: object, default: int) -> int:
    return int(default if value is None else value)


def _read_controlnet_advanced_request(
    unit: NormalizedControlNetUnit | NormalizedADetailerControlNetRequest | dict[str, object],
) -> object:
    return _read_controlnet_unit_value(unit, "advanced")


def controlnet_union_type_for_control_type(control_type: object) -> str | None:
    """Return the exact current-host Union selector for a canonical UI type."""
    return CONTROLNET_UNION_TYPE_BY_CONTROL_TYPE.get(str(control_type or "").strip())


def _controlnet_unit_applies_to_pass(
    unit: NormalizedControlNetUnit | NormalizedADetailerControlNetRequest | dict[str, object],
    pass_scope: str | None,
) -> bool:
    if pass_scope is None:
        return True
    hr_option = str(_read_controlnet_unit_value(unit, "hr_option") or "both").strip().lower()
    if pass_scope == "base":
        return hr_option in {"both", "low_res_only"}
    if pass_scope == "hires":
        return hr_option in {"both", "high_res_only"}
    raise ValueError("Unsupported ControlNet pass scope.")


def _apply_controlnet_unit_entries(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    units: list[NormalizedControlNetUnit | dict[str, object]],
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
    positive_ref: str | list[object],
    negative_ref: str | list[object],
    model_source: list[object],
    vae_source: list[object],
    control_image_ref: list[object] | None = None,
    pass_scope: str | None = None,
) -> tuple[str | list[object], str | list[object]]:
    current_positive = positive_ref
    current_negative = negative_ref
    for unit in units:
        if not bool(_read_controlnet_unit_value(unit, "enabled")):
            continue
        if not _controlnet_unit_applies_to_pass(unit, pass_scope):
            continue
        image_asset = str(_read_controlnet_unit_value(unit, "image_asset") or "").strip()
        mask_asset = str(_read_controlnet_unit_value(unit, "mask_asset") or "").strip()
        use_mask = bool(_read_controlnet_unit_value(unit, "use_mask"))
        advanced = _read_controlnet_advanced_request(unit)
        control_type = str(_read_controlnet_unit_value(unit, "control_type") or "All").strip() or "All"
        control_mode = str(_read_controlnet_unit_value(unit, "control_mode") or "balanced").strip().lower() or "balanced"
        stage_profile = resolve_controlnet_stage_profile(control_mode=control_mode, advanced=advanced)
        module_name = str(_read_controlnet_unit_value(unit, "module") or "none").strip().lower() or "none"
        model_name = str(_read_controlnet_unit_value(unit, "model") or "").strip()
        prepared_map = bool(_read_controlnet_unit_value(unit, "preprocessed_control_map"))
        concat_mask = bool(_read_controlnet_unit_value(unit, "concat_mask"))
        if not model_name:
            continue
        if concat_mask and not mask_asset:
            raise ValueError("ControlNet concat_mask requires a real source mask asset.")

        if control_image_ref is None:
            if not image_asset:
                continue
            image_id = allocator.next()
            workflow[image_id] = {
                "class_type": "RookieUILoadAssetImage",
                "inputs": {
                    "asset_handle": image_asset,
                },
            }
            image_ref = [image_id, 0]
        else:
            # IMPORTANT: ADetailer-local ControlNet must preprocess the current refinement image;
            # rebinding this to the original unit source asset makes passthrough/custom act on stale pixels.
            image_ref = control_image_ref

        mask_ref: list[object] | None = None
        apply_mask_aware = bool(getattr(advanced, "enabled", False) and getattr(advanced, "mask_aware_apply", False))
        if ((use_mask and not prepared_map) or apply_mask_aware or concat_mask) and mask_asset:
            mask_id = allocator.next()
            workflow[mask_id] = {
                "class_type": "RookieUILoadAssetMask",
                "inputs": {
                    "asset_handle": mask_asset,
                    "channel": "red",
                    "invert": False,
                    "blur_radius": 0,
                },
            }
            mask_ref = [mask_id, 0]

        unit_control_image_ref = image_ref
        if not prepared_map:
            preprocess_id = allocator.next()
            preprocess_inputs: dict[str, object] = {
                "image": image_ref,
                "module": module_name,
                "processor_res": _int_or_default(_read_controlnet_unit_value(unit, "processor_res"), 512),
                "threshold_a": _float_or_default(_read_controlnet_unit_value(unit, "threshold_a"), 64.0),
                "threshold_b": _float_or_default(_read_controlnet_unit_value(unit, "threshold_b"), 64.0),
                "pixel_perfect": bool(_read_controlnet_unit_value(unit, "pixel_perfect")),
                "target_width": int(request.width),
                "target_height": int(request.height),
                "resize_mode": str(_read_controlnet_unit_value(unit, "resize_mode") or getattr(request, "resize_mode", "crop_and_resize")),
                "use_mask": bool(use_mask and mask_ref),
            }
            if use_mask and mask_ref is not None:
                preprocess_inputs["mask"] = mask_ref
            # IMPORTANT: keep preprocess node in the runtime path so integrated selector changes (module/threshold/use_mask) are not UI-only and always affect the emitted workflow.
            workflow[preprocess_id] = {
                "class_type": "RookieUIControlNetPreprocess",
                "inputs": preprocess_inputs,
            }
            unit_control_image_ref = [preprocess_id, 0]

        loader_id = allocator.next()
        if request.base_family in {"sd15", "sdxl"}:
            workflow[loader_id] = {
                "class_type": "DiffControlNetLoader",
                "inputs": {
                    "model": model_source,
                    "control_net_name": model_name,
                },
            }
        else:
            workflow[loader_id] = {
                "class_type": "ControlNetLoader",
                "inputs": {
                    "control_net_name": model_name,
                },
            }

        control_net_ref: list[object] = [loader_id, 0]
        union_type = controlnet_union_type_for_control_type(control_type)
        if union_type is not None:
            union_id = allocator.next()
            workflow[union_id] = {
                "class_type": "SetUnionControlNetType",
                "inputs": {
                    "control_net": control_net_ref,
                    "type": union_type,
                },
            }
            control_net_ref = [union_id, 0]

        apply_segments = build_controlnet_apply_segments(
            weight=_float_or_default(_read_controlnet_unit_value(unit, "weight"), 1.0),
            guidance_start=_float_or_default(_read_controlnet_unit_value(unit, "guidance_start"), 0.0),
            guidance_end=_float_or_default(_read_controlnet_unit_value(unit, "guidance_end"), 1.0),
            advanced=advanced,
        )
        for segment in apply_segments:
            apply_id = allocator.next()
            apply_inputs: dict[str, object] = {
                "positive": _to_node_ref(current_positive),
                "negative": _to_node_ref(current_negative),
                "control_net": control_net_ref,
                "image": unit_control_image_ref,
                "strength": float(segment["strength"]),
                "start_percent": float(segment["start_percent"]),
                "end_percent": float(segment["end_percent"]),
                "vae_optional": vae_source,
                "weight_preset": str(stage_profile["weight_preset"]),
                "layer_weights_json": json.dumps(list(stage_profile["layer_weights"])),
                "mask_aware_apply": apply_mask_aware,
                "control_mode": control_mode,
                "apply_to_negative": bool(stage_profile["apply_to_negative"]),
            }
            if apply_mask_aware and mask_ref is not None:
                apply_inputs["mask_optional"] = mask_ref
            if concat_mask:
                # Keep the source role explicit even when the same asset is also
                # used as an effect mask; the native apply node validates the VAE
                # and supplies the real host `extra_concat` tensor.
                apply_inputs["inpaint_mask_optional"] = mask_ref
            workflow[apply_id] = {
                "class_type": "RookieUIControlNetApplyNativeAdvanced",
                "inputs": apply_inputs,
            }
            # IMPORTANT: keep positive/negative references split by output slot; flattening both to slot 0 silently drops half the ControlNet conditioning update.
            current_positive = [apply_id, 0]
            current_negative = [apply_id, 1]

    return current_positive, current_negative


def _apply_controlnet_units(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
    positive_ref: str | list[object],
    negative_ref: str | list[object],
    model_source: list[object],
    vae_source: list[object],
    pass_scope: str | None = None,
) -> tuple[str | list[object], str | list[object]]:
    return _apply_controlnet_unit_entries(
        workflow,
        allocator=allocator,
        units=list(request.controlnet_units),
        request=request,
        positive_ref=positive_ref,
        negative_ref=negative_ref,
        model_source=model_source,
        vae_source=vae_source,
        control_image_ref=None,
        pass_scope=pass_scope,
    )


def _build_controlnet_pass_references(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
    positive_ref: str | list[object],
    negative_ref: str | list[object],
    model_source: list[object],
    vae_source: list[object],
) -> tuple[
    tuple[str | list[object], str | list[object]],
    tuple[str | list[object], str | list[object]],
]:
    if not request.hires_enabled:
        conditioned = _apply_controlnet_units(
            workflow,
            allocator=allocator,
            request=request,
            positive_ref=positive_ref,
            negative_ref=negative_ref,
            model_source=model_source,
            vae_source=vae_source,
        )
        return conditioned, conditioned

    base_conditioned = _apply_controlnet_units(
        workflow,
        allocator=allocator,
        request=request,
        positive_ref=positive_ref,
        negative_ref=negative_ref,
        model_source=model_source,
        vae_source=vae_source,
        pass_scope="base",
    )
    hires_conditioned = _apply_controlnet_units(
        workflow,
        allocator=allocator,
        request=request,
        positive_ref=positive_ref,
        negative_ref=negative_ref,
        model_source=model_source,
        vae_source=vae_source,
        pass_scope="hires",
    )
    return base_conditioned, hires_conditioned
