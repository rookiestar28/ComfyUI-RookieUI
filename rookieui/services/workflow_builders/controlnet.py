from __future__ import annotations

import json

from rookieui.contracts.adetailer import NormalizedADetailerControlNetRequest
from rookieui.contracts.controlnet import NormalizedControlNetUnit
from rookieui.contracts.generation import (
    NormalizedImg2ImgRequest,
    NormalizedTxt2ImgRequest,
)
from rookieui.services.controlnet_advanced_runtime import build_controlnet_apply_segments
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


def _read_controlnet_advanced_request(
    unit: NormalizedControlNetUnit | NormalizedADetailerControlNetRequest | dict[str, object],
) -> object:
    return _read_controlnet_unit_value(unit, "advanced")


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
) -> tuple[str | list[object], str | list[object]]:
    current_positive = positive_ref
    current_negative = negative_ref
    for unit in units:
        if not bool(_read_controlnet_unit_value(unit, "enabled")):
            continue
        image_asset = str(_read_controlnet_unit_value(unit, "image_asset") or "").strip()
        mask_asset = str(_read_controlnet_unit_value(unit, "mask_asset") or "").strip()
        use_mask = bool(_read_controlnet_unit_value(unit, "use_mask"))
        advanced = _read_controlnet_advanced_request(unit)
        module_name = str(_read_controlnet_unit_value(unit, "module") or "none").strip().lower() or "none"
        model_name = str(_read_controlnet_unit_value(unit, "model") or "").strip()
        if not model_name:
            continue

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
        if (use_mask or apply_mask_aware) and mask_asset:
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

        preprocess_id = allocator.next()
        preprocess_inputs: dict[str, object] = {
            "image": image_ref,
            "module": module_name,
            "processor_res": int(_read_controlnet_unit_value(unit, "processor_res") or 512),
            "threshold_a": float(_read_controlnet_unit_value(unit, "threshold_a") or 64.0),
            "threshold_b": float(_read_controlnet_unit_value(unit, "threshold_b") or 64.0),
            "use_mask": bool(use_mask and mask_ref),
        }
        if use_mask and mask_ref is not None:
            preprocess_inputs["mask"] = mask_ref
        # IMPORTANT: keep preprocess node in the runtime path so integrated selector changes (module/threshold/use_mask) are not UI-only and always affect the emitted workflow.
        workflow[preprocess_id] = {
            "class_type": "RookieUIControlNetPreprocess",
            "inputs": preprocess_inputs,
        }

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

        apply_segments = build_controlnet_apply_segments(
            weight=float(_read_controlnet_unit_value(unit, "weight") or 1.0),
            guidance_start=float(_read_controlnet_unit_value(unit, "guidance_start") or 0.0),
            guidance_end=float(_read_controlnet_unit_value(unit, "guidance_end") or 1.0),
            advanced=advanced,
        )
        for segment in apply_segments:
            apply_id = allocator.next()
            apply_inputs: dict[str, object] = {
                "positive": _to_node_ref(current_positive),
                "negative": _to_node_ref(current_negative),
                "control_net": [loader_id, 0],
                "image": [preprocess_id, 0],
                "strength": float(segment["strength"]),
                "start_percent": float(segment["start_percent"]),
                "end_percent": float(segment["end_percent"]),
                "vae_optional": vae_source,
                "weight_preset": str(getattr(advanced, "weight_preset", "balanced") or "balanced"),
                "layer_weights_json": json.dumps(list(getattr(advanced, "layer_weights", []) or [])),
                "mask_aware_apply": apply_mask_aware,
            }
            if apply_mask_aware and mask_ref is not None:
                apply_inputs["mask_optional"] = mask_ref
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
    )
