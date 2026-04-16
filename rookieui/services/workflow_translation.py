from __future__ import annotations

import os
import re
import json

from rookieui.contracts.controlnet import NormalizedControlNetUnit
from rookieui.contracts.generation import (
    NormalizedImg2ImgRequest,
    NormalizedTxt2ImgRequest,
    WorkflowTranslationResult,
)
from rookieui.contracts.adetailer import (
    NormalizedADetailerControlNetRequest,
    NormalizedADetailerUnitRequest,
)
from rookieui.services.parity_matrix import (
    get_parity_profile,
    get_sampler_alias_payload,
    normalize_sampler_name,
    normalize_scheduler_name,
)
from rookieui.services.model_inventory import discover_model_inventory
from rookieui.services.prompt_dsl import preprocess_prompt_bundle
from rookieui.services.controlnet_advanced_runtime import build_controlnet_apply_segments

_PROMPT_DSL_LEGACY_ENV = "ROOKIEUI_PROMPT_DSL_LEGACY"


def _is_legacy_prompt_dsl_enabled() -> bool:
    raw_value = str(os.getenv(_PROMPT_DSL_LEGACY_ENV, "")).strip().lower()
    return raw_value in {"1", "true", "yes", "on"}


class NodeIdAllocator:
    def __init__(self, *, start: int = 1) -> None:
        self._next = start
        self._used: set[int] = set()

    def next(self) -> str:
        # CRITICAL: all workflow node IDs must come from one allocator seam; mixed hardcoded/manual arithmetic caused collision risk as graph variants expanded.
        while self._next in self._used:
            self._next += 1
        node_id = self._next
        self._used.add(node_id)
        self._next += 1
        return str(node_id)

    def allocate_from(self, start: int) -> str:
        candidate = max(1, start)
        while candidate in self._used:
            candidate += 1
        self._used.add(candidate)
        if candidate == self._next:
            while self._next in self._used:
                self._next += 1
        return str(candidate)


def _to_node_ref(node: str | list[object]) -> list[object]:
    if isinstance(node, list) and len(node) == 2:
        return node
    return [str(node), 0]


def _build_checkpoint_loader_node(checkpoint_name: str) -> dict[str, object]:
    return {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": checkpoint_name,
        },
    }


def _build_unet_loader_node(unet_name: str) -> dict[str, object]:
    return {
        "class_type": "UNETLoader",
        "inputs": {
            "unet_name": unet_name,
            "weight_dtype": "default",
        },
    }


def _build_clip_loader_node(clip_name: str) -> dict[str, object]:
    return {
        "class_type": "CLIPLoader",
        "inputs": {
            "clip_name": clip_name,
            "type": "stable_diffusion",
            "device": "default",
        },
    }


def _build_dual_clip_loader_node(
    *,
    clip_name_1: str,
    clip_name_2: str,
    profile: str,
) -> dict[str, object]:
    clip_type = "flux" if profile in {"flux", "klein"} else "sdxl"
    return {
        "class_type": "DualCLIPLoader",
        "inputs": {
            "clip_name1": clip_name_1,
            "clip_name2": clip_name_2,
            "type": clip_type,
            "device": "default",
        },
    }


def _build_vae_loader_node(vae_name: str) -> dict[str, object]:
    return {
        "class_type": "VAELoader",
        "inputs": {
            "vae_name": vae_name,
        },
    }


def _append_conditioning_combine_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    conditioning_1: str,
    conditioning_2: str,
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "ConditioningCombine",
        "inputs": {
            "conditioning_1": [conditioning_1, 0],
            "conditioning_2": [conditioning_2, 0],
        },
    }
    return node_id


def _combine_conditioning_ids(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    conditioning_ids: list[str],
) -> str:
    if not conditioning_ids:
        raise ValueError("conditioning_ids must contain at least one node id.")
    merged_id = conditioning_ids[0]
    for conditioning_id in conditioning_ids[1:]:
        merged_id = _append_conditioning_combine_node(
            workflow,
            allocator=allocator,
            conditioning_1=merged_id,
            conditioning_2=conditioning_id,
        )
    return merged_id


def _coerce_semantic_feature(payload: dict[str, object], feature_name: str) -> bool:
    features = payload.get("features")
    if not isinstance(features, dict):
        return False
    return bool(features.get(feature_name))


def _requires_conditioning_compiler(semantic_payload: dict[str, object]) -> bool:
    # CRITICAL: compiler must honor the legacy rollback env switch even when semantic payloads are present; mixed parser/compiler modes cause hard-to-debug parity drift.
    if _is_legacy_prompt_dsl_enabled():
        return False
    return any(
        _coerce_semantic_feature(semantic_payload, feature_name)
        for feature_name in ("and_composition", "break_chunks", "prompt_scheduling", "alternate_prompt_scheduling")
    )


def _append_prompt_encode_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    clip_source: list[object],
    text: str,
    prompt_encoder: str,
    use_rookieui_prompt_encoder: bool = False,
    width: int | None = None,
    height: int | None = None,
) -> str:
    node_id = allocator.next()
    if prompt_encoder == "sdxl":
        resolved_width = int(width or 1024)
        resolved_height = int(height or 1024)
        workflow[node_id] = {
            "class_type": "RookieUIA1111CLIPTextEncodeSDXL" if use_rookieui_prompt_encoder else "CLIPTextEncodeSDXL",
            "inputs": {
                "clip": clip_source,
                "width": resolved_width,
                "height": resolved_height,
                "crop_w": 0,
                "crop_h": 0,
                "target_width": resolved_width,
                "target_height": resolved_height,
                "text_g": text,
                "text_l": text,
            },
        }
        return node_id

    workflow[node_id] = {
        "class_type": "RookieUIA1111CLIPTextEncode" if use_rookieui_prompt_encoder else "CLIPTextEncode",
        "inputs": {
            "text": text,
            "clip": clip_source,
        },
    }
    return node_id


def _append_conditioning_range_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    conditioning_id: str,
    start: float,
    end: float,
) -> str:
    start_value = round(max(0.0, min(1.0, float(start))), 4)
    end_value = round(max(0.0, min(1.0, float(end))), 4)
    if end_value <= start_value:
        return conditioning_id
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "ConditioningSetTimestepRange",
        "inputs": {
            "conditioning": [conditioning_id, 0],
            "start": start_value,
            "end": end_value,
        },
    }
    return node_id


def _append_conditioning_weight_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    conditioning_id: str,
    weight: float,
) -> str:
    normalized_weight = round(float(weight), 3)
    if abs(normalized_weight - 1.0) < 1e-6:
        return conditioning_id
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "ConditioningSetAreaStrength",
        "inputs": {
            "conditioning": [conditioning_id, 0],
            "strength": max(0.0, min(10.0, normalized_weight)),
        },
    }
    return node_id


def _compile_prompt_semantic_conditioning(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    clip_source: list[object],
    prompt_text: str,
    semantic_payload: dict[str, object],
    prompt_encoder: str,
    use_rookieui_prompt_encoder: bool = False,
    width: int | None = None,
    height: int | None = None,
) -> str:
    if not _requires_conditioning_compiler(semantic_payload):
        return _append_prompt_encode_node(
            workflow,
            allocator=allocator,
            clip_source=clip_source,
            text=prompt_text,
            prompt_encoder=prompt_encoder,
            use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
            width=width,
            height=height,
        )

    branches = semantic_payload.get("branches")
    if not isinstance(branches, list) or not branches:
        return _append_prompt_encode_node(
            workflow,
            allocator=allocator,
            clip_source=clip_source,
            text=prompt_text,
            prompt_encoder=prompt_encoder,
            use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
            width=width,
            height=height,
        )

    compiled_branch_ids: list[str] = []
    for raw_branch in branches:
        if not isinstance(raw_branch, dict):
            continue
        branch_text = str(raw_branch.get("text") or prompt_text).strip() or prompt_text
        raw_chunks = raw_branch.get("chunks")
        chunks = raw_chunks if isinstance(raw_chunks, list) and raw_chunks else [{"text": branch_text, "slices": []}]
        compiled_chunk_ids: list[str] = []

        for raw_chunk in chunks:
            if not isinstance(raw_chunk, dict):
                continue
            chunk_text = str(raw_chunk.get("text") or branch_text).strip() or branch_text
            raw_slices = raw_chunk.get("slices")
            slices = raw_slices if isinstance(raw_slices, list) and raw_slices else [{"text": chunk_text, "start": 0.0, "end": 1.0}]
            compiled_slice_ids: list[str] = []

            for raw_slice in slices:
                if not isinstance(raw_slice, dict):
                    continue
                slice_text = str(raw_slice.get("text") or chunk_text).strip() or chunk_text
                encoded_id = _append_prompt_encode_node(
                    workflow,
                    allocator=allocator,
                    clip_source=clip_source,
                    text=slice_text,
                    prompt_encoder=prompt_encoder,
                    use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
                    width=width,
                    height=height,
                )
                start = float(raw_slice.get("start", 0.0))
                end = float(raw_slice.get("end", 1.0))
                compiled_slice_ids.append(
                    _append_conditioning_range_node(
                        workflow,
                        allocator=allocator,
                        conditioning_id=encoded_id,
                        start=start,
                        end=end,
                    )
                )

            if compiled_slice_ids:
                compiled_chunk_ids.append(
                    _combine_conditioning_ids(
                        workflow,
                        allocator=allocator,
                        conditioning_ids=compiled_slice_ids,
                    )
                )

        if not compiled_chunk_ids:
            compiled_chunk_ids.append(
                _append_prompt_encode_node(
                    workflow,
                    allocator=allocator,
                    clip_source=clip_source,
                    text=branch_text,
                    prompt_encoder=prompt_encoder,
                    use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
                    width=width,
                    height=height,
                )
            )

        branch_id = _combine_conditioning_ids(
            workflow,
            allocator=allocator,
            conditioning_ids=compiled_chunk_ids,
        )
        branch_weight = float(raw_branch.get("weight", 1.0))
        compiled_branch_ids.append(
            _append_conditioning_weight_node(
                workflow,
                allocator=allocator,
                conditioning_id=branch_id,
                weight=branch_weight,
            )
        )

    if not compiled_branch_ids:
        return _append_prompt_encode_node(
            workflow,
            allocator=allocator,
            clip_source=clip_source,
            text=prompt_text,
            prompt_encoder=prompt_encoder,
            use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
            width=width,
            height=height,
        )
    return _combine_conditioning_ids(
        workflow,
        allocator=allocator,
        conditioning_ids=compiled_branch_ids,
    )


def _build_sd15_conditioning(
    workflow: dict[str, object],
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
    *,
    allocator: NodeIdAllocator,
    clip_source: list[object],
) -> tuple[str, str]:
    use_rookieui_prompt_encoder = _uses_sd_family_prompt_parity(request)
    if request.clip_skip > 1:
        clip_node_id = allocator.next()
        workflow[clip_node_id] = {
            "class_type": "CLIPSetLastLayer",
            "inputs": {
                "clip": ["1", 1],
                "stop_at_clip_layer": -request.clip_skip,
            },
        }
        clip_source = [clip_node_id, 0]
    positive_id = _compile_prompt_semantic_conditioning(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        prompt_text=request.prompt,
        semantic_payload=request.prompt_semantics if isinstance(request.prompt_semantics, dict) else {},
        prompt_encoder="sd15",
        use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
    )
    negative_id = _compile_prompt_semantic_conditioning(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        prompt_text=request.negative_prompt,
        semantic_payload=request.negative_prompt_semantics if isinstance(request.negative_prompt_semantics, dict) else {},
        prompt_encoder="sd15",
        use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
    )
    return positive_id, negative_id


def _build_sdxl_conditioning(
    workflow: dict[str, object],
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
    *,
    allocator: NodeIdAllocator,
    width: int,
    height: int,
    clip_source: list[object],
) -> tuple[str, str]:
    prompt_encoder_mode = _resolve_conditioning_prompt_encoder(request)
    use_rookieui_prompt_encoder = _uses_sd_family_prompt_parity(request)
    positive_id = _compile_prompt_semantic_conditioning(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        prompt_text=request.prompt,
        semantic_payload=request.prompt_semantics if isinstance(request.prompt_semantics, dict) else {},
        prompt_encoder=prompt_encoder_mode,
        use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
        width=width,
        height=height,
    )
    negative_id = _compile_prompt_semantic_conditioning(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        prompt_text=request.negative_prompt,
        semantic_payload=request.negative_prompt_semantics if isinstance(request.negative_prompt_semantics, dict) else {},
        prompt_encoder=prompt_encoder_mode,
        use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
        width=width,
        height=height,
    )
    return positive_id, negative_id


def _uses_sd_family_prompt_parity(
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
) -> bool:
    # CRITICAL: SD-family prompt parity must stay on RookieUI-owned encoder nodes; reverting these profiles to stock encoders silently drops A1111 attention semantics back to approximation-only behavior.
    return request.profile in {"sd15", "sdxl", "pony", "illustrious", "noob"}


def _resolve_conditioning_prompt_encoder(
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
) -> str:
    configured_prompt_encoder = str(request.prompt_encoder or "").strip().lower()
    if configured_prompt_encoder in {"clip_text_encode", "sd15"}:
        return "sd15"
    if configured_prompt_encoder in {"clip_text_encode_sdxl", "sdxl"}:
        text_encoder_values = _normalize_encoder_selector_values(request.text_encoder_name)
        if request.primary_model_category == "diffusion_models" and len(text_encoder_values) <= 1:
            # CRITICAL: CLIPTextEncodeSDXL requires both "l" and "g" token channels;
            # diffusion-model presets often run single text encoders, so forcing SDXL encoding here causes KeyError('l') at runtime.
            return "sd15"
        return "sdxl"
    return "sdxl"


def _build_sampler_node(
    workflow: dict[str, object],
    *,
    node_id: str,
    positive_id: str | list[object],
    negative_id: str | list[object],
    latent_id: str | list[object],
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
    denoise: float,
    model_source: list[object],
    seed: int | None = None,
    steps: int | None = None,
    cfg_scale: float | None = None,
    sampler_name: str | None = None,
    scheduler_name: str | None = None,
) -> None:
    workflow[node_id] = {
        "class_type": "KSampler",
        "inputs": {
            "model": model_source,
            "positive": _to_node_ref(positive_id),
            "negative": _to_node_ref(negative_id),
            "latent_image": _to_node_ref(latent_id),
            "seed": request.execution_seed if seed is None else seed,
            "steps": request.steps if steps is None else steps,
            "cfg": request.cfg_scale if cfg_scale is None else cfg_scale,
            "sampler_name": request.sampler_name if sampler_name is None else sampler_name,
            "scheduler": request.scheduler_name if scheduler_name is None else scheduler_name,
            "denoise": denoise,
        },
    }


def _append_decode_node(
    workflow: dict[str, object],
    *,
    sampler_id: str | list[object],
    decode_id: str,
    vae_source: list[object],
) -> None:
    workflow[decode_id] = {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": _to_node_ref(sampler_id),
            "vae": vae_source,
        },
    }


def _append_save_node(
    workflow: dict[str, object],
    *,
    image_ref: list[object],
    save_id: str,
) -> None:
    workflow[save_id] = {
        "class_type": "SaveImage",
        "inputs": {
            "images": image_ref,
            "filename_prefix": "RookieUI",
        },
    }


def _build_decode_and_save(
    workflow: dict[str, object],
    *,
    sampler_id: str | list[object],
    decode_id: str,
    save_id: str,
    vae_source: list[object],
) -> None:
    _append_decode_node(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        vae_source=vae_source,
    )
    _append_save_node(
        workflow,
        image_ref=[decode_id, 0],
        save_id=save_id,
    )


def _is_adetailer_unit_active(unit: NormalizedADetailerUnitRequest) -> bool:
    detector = str(unit.detector or "").strip().lower()
    return bool(unit.enabled and detector and detector != "none")


def _resolve_adetailer_prompt_text(unit_prompt: str, main_prompt: str) -> str:
    raw_prompt = str(unit_prompt or "").strip()
    main = str(main_prompt or "").strip()
    if not raw_prompt:
        return main
    segments = [segment.strip() for segment in re.split(r"\s*\[SEP\]\s*", raw_prompt)]
    for segment in segments:
        if not segment or "[SKIP]" in segment:
            continue
        return segment.replace("[PROMPT]", main).strip() or main
    return main


def _resolve_adetailer_sampler_override(
    unit: NormalizedADetailerUnitRequest,
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
) -> tuple[str, str]:
    if not unit.use_sampler:
        return request.sampler_name, request.scheduler_name

    raw_sampler = str(unit.sampler_name or "").strip()
    raw_scheduler = str(unit.scheduler_name or "").strip()
    sampler_for_scheduler = raw_sampler
    sampler_for_comfy = raw_sampler
    if raw_sampler.lower().endswith(" karras"):
        sampler_for_comfy = raw_sampler[: -len(" karras")].strip()
    normalized_sampler = normalize_sampler_name(sampler_for_comfy) or request.sampler_name
    if raw_scheduler.lower() in {"", "use same scheduler"}:
        normalized_scheduler = normalize_scheduler_name(
            sampler_for_scheduler,
            "",
            default_scheduler=request.scheduler_name,
        )
    else:
        normalized_scheduler = normalize_scheduler_name(
            sampler_for_scheduler,
            raw_scheduler,
            default_scheduler=request.scheduler_name,
        )
    return normalized_sampler, normalized_scheduler


def _append_adetailer_unit_conditioning(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
    unit: NormalizedADetailerUnitRequest,
    clip_source: list[object],
    prompt_encoder_mode: str,
    width: int,
    height: int,
) -> tuple[str, str]:
    prompt_text = _resolve_adetailer_prompt_text(unit.prompt, request.prompt)
    negative_text = _resolve_adetailer_prompt_text(unit.negative_prompt, request.negative_prompt)
    inventory = discover_model_inventory()
    prompt_bundle = preprocess_prompt_bundle(
        prompt_text,
        negative_text,
        inventory_loras=inventory.loras,
        inventory_embeddings=inventory.embeddings,
        strict_match=False,
    )
    use_rookieui_prompt_encoder = _uses_sd_family_prompt_parity(request)
    positive_id = _compile_prompt_semantic_conditioning(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        prompt_text=prompt_bundle.cleaned_prompt,
        semantic_payload=prompt_bundle.prompt_semantics.to_payload(),
        prompt_encoder=prompt_encoder_mode,
        use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
        width=width,
        height=height,
    )
    negative_id = _compile_prompt_semantic_conditioning(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        prompt_text=prompt_bundle.cleaned_negative_prompt,
        semantic_payload=prompt_bundle.negative_prompt_semantics.to_payload(),
        prompt_encoder=prompt_encoder_mode,
        use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
        width=width,
        height=height,
    )
    return positive_id, negative_id


def _build_adetailer_custom_controlnet_unit(unit: NormalizedADetailerUnitRequest) -> dict[str, object]:
    controlnet = unit.controlnet
    return {
        "enabled": True,
        "module": controlnet.module,
        "model": controlnet.model,
        "weight": controlnet.weight,
        "guidance_start": controlnet.guidance_start,
        "guidance_end": controlnet.guidance_end,
        # IMPORTANT: keep the full advanced block when adapting ADetailer-local custom ControlNet
        # into the shared unit seam. Dropping it here silently desynchronizes local detailer behavior
        # from the primary ControlNet runtime even though both paths claim the same contract.
        "advanced": controlnet.advanced,
        "processor_res": 512,
        "threshold_a": 64.0,
        "threshold_b": 64.0,
        "image_asset": "",
        "mask_asset": "",
        "use_mask": False,
    }


def _resolve_adetailer_controlnet_units(
    unit: NormalizedADetailerUnitRequest,
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
) -> list[NormalizedControlNetUnit | dict[str, object]]:
    mode = str(unit.controlnet.mode or "none").strip().lower()
    if mode == "passthrough":
        # IMPORTANT: passthrough snapshots primary units for this refinement pass only;
        # do not mutate request.controlnet_units or the base generation path will drift.
        return [controlnet_unit for controlnet_unit in request.controlnet_units if controlnet_unit.enabled]
    if mode == "custom" and str(unit.controlnet.model or "").strip():
        return [_build_adetailer_custom_controlnet_unit(unit)]
    return []


def _append_adetailer_units(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
    base_image_ref: list[object],
    model_source: list[object],
    clip_source: list[object],
    vae_source: list[object],
    prompt_encoder_mode: str,
    width: int,
    height: int,
) -> list[object]:
    if not request.adetailer.enabled:
        return base_image_ref
    if isinstance(request, NormalizedImg2ImgRequest) and request.adetailer.skip_img2img:
        return base_image_ref

    current_image_ref = base_image_ref
    active_units = [unit for unit in request.adetailer.units if _is_adetailer_unit_active(unit)]
    if not active_units:
        return current_image_ref

    for index, unit in enumerate(active_units):
        detail_model_source = model_source
        detail_clip_source = clip_source
        detail_vae_source = vae_source
        if unit.use_checkpoint and unit.checkpoint_name and unit.checkpoint_name != "Use same checkpoint":
            checkpoint_id = allocator.next()
            workflow[checkpoint_id] = _build_checkpoint_loader_node(unit.checkpoint_name)
            detail_model_source = [checkpoint_id, 0]
            detail_clip_source = [checkpoint_id, 1]
            detail_vae_source = [checkpoint_id, 2]
        if unit.use_vae and unit.vae_name and unit.vae_name != "Use same VAE":
            vae_id = allocator.next()
            workflow[vae_id] = _build_vae_loader_node(unit.vae_name)
            detail_vae_source = [vae_id, 0]

        positive_id, negative_id = _append_adetailer_unit_conditioning(
            workflow,
            allocator=allocator,
            request=request,
            unit=unit,
            clip_source=detail_clip_source,
            prompt_encoder_mode=prompt_encoder_mode,
            width=unit.inpaint_width if unit.use_inpaint_size else width,
            height=unit.inpaint_height if unit.use_inpaint_size else height,
        )
        positive_ref, negative_ref = _apply_controlnet_unit_entries(
            workflow,
            allocator=allocator,
            units=_resolve_adetailer_controlnet_units(unit, request),
            request=request,
            positive_ref=positive_id,
            negative_ref=negative_id,
            model_source=detail_model_source,
            vae_source=detail_vae_source,
            control_image_ref=current_image_ref,
        )

        mask_id = allocator.next()
        encode_id = allocator.next()
        sampler_id = allocator.next()
        decode_id = allocator.next()
        grow_mask_by = max(0, int(unit.inpaint_padding if unit.inpaint_only_masked else unit.dilate_erode))
        workflow[mask_id] = {
            "class_type": "RookieUIADetailerDetectMask",
            "inputs": {
                "image": current_image_ref,
                "detector": unit.detector,
                "detector_family": unit.detector_family,
                "detector_classes": unit.detector_classes,
                "confidence": unit.confidence,
                "mask_filter_method": unit.mask_filter_method,
                "mask_k": unit.mask_k,
                "mask_min_ratio": unit.mask_min_ratio,
                "mask_max_ratio": unit.mask_max_ratio,
                "x_offset": unit.x_offset,
                "y_offset": unit.y_offset,
                "dilate_erode": unit.dilate_erode,
                "mask_merge_mode": unit.mask_merge_mode,
                "mask_blur": unit.mask_blur,
            },
        }
        workflow[encode_id] = {
            "class_type": "RookieUIVAEEncodeForInpaint",
            "inputs": {
                "pixels": current_image_ref,
                "vae": detail_vae_source,
                "mask": [mask_id, 0],
                "grow_mask_by": grow_mask_by,
                "masked_content": "original",
                "seed": request.execution_seed + index + 1,
                "soft_inpainting_enabled": False,
                "soft_inpainting_schedule_bias": 1.0,
                "soft_inpainting_preservation_strength": 0.5,
                "soft_inpainting_transition_contrast_boost": 4.0,
                "soft_inpainting_mask_influence": 0.0,
                "soft_inpainting_difference_threshold": 0.5,
                "soft_inpainting_difference_contrast": 2.0,
            },
        }
        sampler_name, scheduler_name = _resolve_adetailer_sampler_override(unit, request)
        # IMPORTANT: ADetailer refinement must stay after base decode and before final SaveImage;
        # moving it into the primary sampler/control path breaks the intended A1111-compatible execution ordering.
        _build_sampler_node(
            workflow,
            node_id=sampler_id,
            positive_id=positive_ref,
            negative_id=negative_ref,
            latent_id=encode_id,
            request=request,
            denoise=unit.denoising_strength,
            model_source=detail_model_source,
            seed=request.execution_seed + index + 1,
            steps=unit.steps if unit.use_steps else request.steps,
            cfg_scale=unit.cfg_scale if unit.use_cfg_scale else request.cfg_scale,
            sampler_name=sampler_name,
            scheduler_name=scheduler_name,
        )
        _append_decode_node(
            workflow,
            sampler_id=sampler_id,
            decode_id=decode_id,
            vae_source=detail_vae_source,
        )
        current_image_ref = [decode_id, 0]

    return current_image_ref


def _append_decode_adetailer_and_save(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    sampler_id: str | list[object],
    decode_id: str,
    save_id: str,
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
    model_source: list[object],
    clip_source: list[object],
    vae_source: list[object],
    width: int,
    height: int,
) -> None:
    _append_decode_node(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        vae_source=vae_source,
    )
    final_image_ref = _append_adetailer_units(
        workflow,
        allocator=allocator,
        request=request,
        base_image_ref=[decode_id, 0],
        model_source=model_source,
        clip_source=clip_source,
        vae_source=vae_source,
        prompt_encoder_mode=_resolve_conditioning_prompt_encoder(request),
        width=width,
        height=height,
    )
    _append_save_node(
        workflow,
        image_ref=final_image_ref,
        save_id=save_id,
    )


def _resolve_model_sources(
    workflow: dict[str, object],
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
    *,
    allocator: NodeIdAllocator,
) -> tuple[list[object], list[object], list[object]]:
    primary_model_category = str(request.primary_model_category or "checkpoints").strip().lower()
    # CRITICAL: loader routing must follow normalized primary_model_category; inferring from base_family/profile reintroduces preset-switch path drift.
    if primary_model_category == "diffusion_models":
        model_source, clip_source, vae_source = _resolve_diffusion_model_sources(
            workflow,
            request=request,
            allocator=allocator,
        )
    else:
        checkpoint_id = allocator.next()
        workflow[checkpoint_id] = _build_checkpoint_loader_node(request.checkpoint_name)
        model_source = [checkpoint_id, 0]
        clip_source = [checkpoint_id, 1]
        vae_source = [checkpoint_id, 2]

    lora_activations = list(request.lora_activations)
    if not lora_activations and request.lora_name:
        lora_activations = [
            {
                "name": request.lora_name,
                "strength_model": request.lora_strength_model,
                "strength_clip": request.lora_strength_clip,
            }
        ]

    if lora_activations:
        # IMPORTANT: prompt-side inline LoRA and sidebar-selected LoRA must converge here; collapsing back to one decorative prompt token would break the A1111 extra-network seam.
        for activation in lora_activations:
            node_id = allocator.allocate_from(90)
            workflow[node_id] = {
                "class_type": "LoraLoader",
                "inputs": {
                    "model": model_source,
                    "clip": clip_source,
                    "lora_name": activation["name"] if isinstance(activation, dict) else activation.name,
                    "strength_model": activation["strength_model"]
                    if isinstance(activation, dict)
                    else activation.strength_model,
                    "strength_clip": activation["strength_clip"]
                    if isinstance(activation, dict)
                    else activation.strength_clip,
                },
            }
            model_source = [node_id, 0]
            clip_source = [node_id, 1]

    return model_source, clip_source, vae_source


def _normalize_encoder_selector_values(raw_selector: str) -> list[str]:
    selector = str(raw_selector or "").strip()
    if not selector:
        return []
    return [token.strip() for token in re.split(r"[|,;+]", selector) if token.strip()]


def _require_explicit_diffusion_selector(value: str, field_name: str) -> str:
    selector = str(value or "").strip()
    lowered_selector = selector.lower()
    # IMPORTANT: diffusion-model path has no checkpoint-baked CLIP/VAE fallback;
    # allow only explicit host selectors or the workflow will fail late in host validation/runtime.
    if not selector or lowered_selector in {"automatic", "__host_default__"}:
        raise ValueError(
            f"{field_name} must be an explicit host selector when primary_model_category is diffusion_models."
        )
    return selector


def _resolve_diffusion_model_sources(
    workflow: dict[str, object],
    *,
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
    allocator: NodeIdAllocator,
) -> tuple[list[object], list[object], list[object]]:
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    model_source: list[object] = [unet_id, 0]

    text_encoder_selector = _require_explicit_diffusion_selector(
        request.text_encoder_name,
        "text_encoder_name",
    )
    text_encoder_values = _normalize_encoder_selector_values(text_encoder_selector)
    if not text_encoder_values:
        raise ValueError(
            "text_encoder_name must include at least one selector when primary_model_category is diffusion_models."
        )
    if len(text_encoder_values) > 2:
        raise ValueError(
            "text_encoder_name supports up to two selectors for diffusion_models path (single or dual CLIP)."
        )

    clip_loader_id = allocator.next()
    if len(text_encoder_values) == 1:
        workflow[clip_loader_id] = _build_clip_loader_node(text_encoder_values[0])
    else:
        workflow[clip_loader_id] = _build_dual_clip_loader_node(
            clip_name_1=text_encoder_values[0],
            clip_name_2=text_encoder_values[1],
            profile=request.profile,
        )
    clip_source: list[object] = [clip_loader_id, 0]

    vae_selector = _require_explicit_diffusion_selector(
        request.vae_name,
        "vae_name",
    )
    vae_loader_id = allocator.next()
    workflow[vae_loader_id] = _build_vae_loader_node(vae_selector)
    vae_source: list[object] = [vae_loader_id, 0]
    return model_source, clip_source, vae_source


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


def _append_img2img_resize_node(
    workflow: dict[str, object],
    *,
    source_image_id: str,
    request: NormalizedImg2ImgRequest,
    allocator: NodeIdAllocator,
) -> str:
    if request.resize_mode == "latent_upscale":
        return source_image_id

    crop_mode = "center" if request.resize_mode == "crop_and_resize" else "disabled"
    resize_id = allocator.next()
    # IMPORTANT: map A1111 img2img resize modes onto Comfy's stable ImageScale seam; "resize_and_fill" degrades to non-cropping resize for host-compatibility.
    workflow[resize_id] = {
        "class_type": "ImageScale",
        "inputs": {
            "image": [source_image_id, 0],
            "upscale_method": "lanczos",
            "width": request.width,
            "height": request.height,
            "crop": crop_mode,
        },
    }
    return resize_id


def _append_latent_resize_node(
    workflow: dict[str, object],
    *,
    latent_id: str,
    request: NormalizedImg2ImgRequest,
    allocator: NodeIdAllocator,
) -> str:
    if request.resize_mode != "latent_upscale":
        return latent_id

    upscale_id = allocator.next()
    workflow[upscale_id] = {
        "class_type": "LatentUpscale",
        "inputs": {
            "samples": [latent_id, 0],
            "upscale_method": request.hires_upscale_method,
            "width": request.width,
            "height": request.height,
            "crop": "disabled",
        },
    }
    return upscale_id


def _build_sd15_txt2img_graph(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    model_source, clip_source, vae_source = _resolve_model_sources(
        workflow,
        request,
        allocator=allocator,
    )
    positive_id, negative_id = _build_sd15_conditioning(
        workflow,
        request,
        allocator=allocator,
        clip_source=clip_source,
    )
    positive_ref, negative_ref = _apply_controlnet_units(
        workflow,
        allocator=allocator,
        request=request,
        positive_ref=positive_id,
        negative_ref=negative_id,
        model_source=model_source,
        vae_source=vae_source,
    )
    latent_id = allocator.next()
    sampler_id = allocator.next()

    workflow[latent_id] = {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "width": request.width,
            "height": request.height,
            "batch_size": request.batch_size,
        },
    }
    _build_sampler_node(
        workflow,
        node_id=sampler_id,
        positive_id=positive_ref,
        negative_id=negative_ref,
        latent_id=latent_id,
        request=request,
        denoise=1.0,
        model_source=model_source,
    )
    final_sampler_id = sampler_id
    decode_id = allocator.next()
    save_id = allocator.next()
    if request.hires_enabled:
        upscale_id = decode_id
        hires_sampler_id = save_id
        decode_id = allocator.next()
        save_id = allocator.next()
        workflow[upscale_id] = {
            "class_type": "LatentUpscaleBy",
            "inputs": {
                "samples": [sampler_id, 0],
                "upscale_method": request.hires_upscale_method,
                "scale_by": request.hires_scale,
            },
        }
        _build_sampler_node(
            workflow,
            node_id=hires_sampler_id,
            positive_id=positive_ref,
            negative_id=negative_ref,
            latent_id=upscale_id,
            request=request,
            denoise=request.hires_denoise,
            model_source=model_source,
            seed=request.execution_seed,
            steps=request.hires_steps,
        )
        final_sampler_id = hires_sampler_id
    _append_decode_adetailer_and_save(
        workflow,
        allocator=allocator,
        sampler_id=final_sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        request=request,
        model_source=model_source,
        clip_source=clip_source,
        vae_source=vae_source,
        width=request.width,
        height=request.height,
    )
    return workflow


def _build_sdxl_txt2img_graph(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    model_source, clip_source, vae_source = _resolve_model_sources(
        workflow,
        request,
        allocator=allocator,
    )
    positive_id, negative_id = _build_sdxl_conditioning(
        workflow,
        request,
        allocator=allocator,
        width=request.width,
        height=request.height,
        clip_source=clip_source,
    )
    positive_ref, negative_ref = _apply_controlnet_units(
        workflow,
        allocator=allocator,
        request=request,
        positive_ref=positive_id,
        negative_ref=negative_id,
        model_source=model_source,
        vae_source=vae_source,
    )
    latent_id = allocator.next()
    workflow[latent_id] = {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "width": request.width,
            "height": request.height,
            "batch_size": request.batch_size,
        },
    }
    sampler_id = allocator.next()
    _build_sampler_node(
        workflow,
        node_id=sampler_id,
        positive_id=positive_ref,
        negative_id=negative_ref,
        latent_id=latent_id,
        request=request,
        denoise=1.0,
        model_source=model_source,
    )
    final_sampler_id = sampler_id
    decode_id = allocator.next()
    save_id = allocator.next()
    if request.hires_enabled:
        upscale_id = decode_id
        hires_sampler_id = save_id
        workflow[upscale_id] = {
            "class_type": "LatentUpscaleBy",
            "inputs": {
                "samples": [sampler_id, 0],
                "upscale_method": request.hires_upscale_method,
                "scale_by": request.hires_scale,
            },
        }
        _build_sampler_node(
            workflow,
            node_id=hires_sampler_id,
            positive_id=positive_ref,
            negative_id=negative_ref,
            latent_id=upscale_id,
            request=request,
            denoise=request.hires_denoise,
            model_source=model_source,
            seed=request.execution_seed,
            steps=request.hires_steps,
        )
        final_sampler_id = hires_sampler_id
        decode_id = allocator.next()
        save_id = allocator.next()
    _append_decode_adetailer_and_save(
        workflow,
        allocator=allocator,
        sampler_id=final_sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        request=request,
        model_source=model_source,
        clip_source=clip_source,
        vae_source=vae_source,
        width=request.width,
        height=request.height,
    )
    return workflow


def _build_sd15_img2img_graph(request: NormalizedImg2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    model_source, clip_source, vae_source = _resolve_model_sources(
        workflow,
        request,
        allocator=allocator,
    )
    positive_id, negative_id = _build_sd15_conditioning(
        workflow,
        request,
        allocator=allocator,
        clip_source=clip_source,
    )
    positive_ref, negative_ref = _apply_controlnet_units(
        workflow,
        allocator=allocator,
        request=request,
        positive_ref=positive_id,
        negative_ref=negative_id,
        model_source=model_source,
        vae_source=vae_source,
    )
    image_id = allocator.next()
    workflow[image_id] = {
        "class_type": "RookieUILoadAssetImage",
        "inputs": {
            "asset_handle": request.image_asset,
        },
    }

    resized_image_id = _append_img2img_resize_node(
        workflow,
        source_image_id=image_id,
        request=request,
        allocator=allocator,
    )

    encode_id = allocator.next()
    workflow[encode_id] = {
        "class_type": "VAEEncode",
        "inputs": {
            "pixels": [resized_image_id, 0],
            "vae": vae_source,
        },
    }

    latent_id = _append_latent_resize_node(
        workflow,
        latent_id=encode_id,
        request=request,
        allocator=allocator,
    )

    sampler_id = allocator.next()
    _build_sampler_node(
        workflow,
        node_id=sampler_id,
        positive_id=positive_ref,
        negative_id=negative_ref,
        latent_id=latent_id,
        request=request,
        denoise=request.denoise_strength,
        model_source=model_source,
    )
    final_sampler_id = sampler_id
    decode_id = allocator.next()
    save_id = allocator.next()
    if request.hires_enabled:
        upscale_id = decode_id
        hires_sampler_id = save_id
        decode_id = allocator.next()
        save_id = allocator.next()
        workflow[upscale_id] = {
            "class_type": "LatentUpscaleBy",
            "inputs": {
                "samples": [sampler_id, 0],
                "upscale_method": request.hires_upscale_method,
                "scale_by": request.hires_scale,
            },
        }
        _build_sampler_node(
            workflow,
            node_id=hires_sampler_id,
            positive_id=positive_ref,
            negative_id=negative_ref,
            latent_id=upscale_id,
            request=request,
            denoise=request.hires_denoise,
            model_source=model_source,
            seed=request.execution_seed,
            steps=request.hires_steps,
        )
        final_sampler_id = hires_sampler_id
    _append_decode_adetailer_and_save(
        workflow,
        allocator=allocator,
        sampler_id=final_sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        request=request,
        model_source=model_source,
        clip_source=clip_source,
        vae_source=vae_source,
        width=request.width,
        height=request.height,
    )
    return workflow


def _build_sdxl_img2img_graph(request: NormalizedImg2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    model_source, clip_source, vae_source = _resolve_model_sources(
        workflow,
        request,
        allocator=allocator,
    )
    positive_id, negative_id = _build_sdxl_conditioning(
        workflow,
        request,
        allocator=allocator,
        width=request.width,
        height=request.height,
        clip_source=clip_source,
    )
    positive_ref, negative_ref = _apply_controlnet_units(
        workflow,
        allocator=allocator,
        request=request,
        positive_ref=positive_id,
        negative_ref=negative_id,
        model_source=model_source,
        vae_source=vae_source,
    )
    image_id = allocator.next()
    workflow[image_id] = {
        "class_type": "RookieUILoadAssetImage",
        "inputs": {
            "asset_handle": request.image_asset,
        },
    }

    resized_image_id = _append_img2img_resize_node(
        workflow,
        source_image_id=image_id,
        request=request,
        allocator=allocator,
    )

    encode_id = allocator.next()
    workflow[encode_id] = {
        "class_type": "VAEEncode",
        "inputs": {
            "pixels": [resized_image_id, 0],
            "vae": vae_source,
        },
    }

    latent_id = _append_latent_resize_node(
        workflow,
        latent_id=encode_id,
        request=request,
        allocator=allocator,
    )

    sampler_id = allocator.next()
    _build_sampler_node(
        workflow,
        node_id=sampler_id,
        positive_id=positive_ref,
        negative_id=negative_ref,
        latent_id=latent_id,
        request=request,
        denoise=request.denoise_strength,
        model_source=model_source,
    )
    final_sampler_id = sampler_id
    decode_id = allocator.next()
    save_id = allocator.next()
    if request.hires_enabled:
        upscale_id = decode_id
        hires_sampler_id = save_id
        decode_id = allocator.next()
        save_id = allocator.next()
        workflow[upscale_id] = {
            "class_type": "LatentUpscaleBy",
            "inputs": {
                "samples": [sampler_id, 0],
                "upscale_method": request.hires_upscale_method,
                "scale_by": request.hires_scale,
            },
        }
        _build_sampler_node(
            workflow,
            node_id=hires_sampler_id,
            positive_id=positive_ref,
            negative_id=negative_ref,
            latent_id=upscale_id,
            request=request,
            denoise=request.hires_denoise,
            model_source=model_source,
            seed=request.execution_seed,
            steps=request.hires_steps,
        )
        final_sampler_id = hires_sampler_id
    _append_decode_adetailer_and_save(
        workflow,
        allocator=allocator,
        sampler_id=final_sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        request=request,
        model_source=model_source,
        clip_source=clip_source,
        vae_source=vae_source,
        width=request.width,
        height=request.height,
    )
    return workflow


def _build_sd15_inpaint_graph(request: NormalizedImg2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    model_source, clip_source, vae_source = _resolve_model_sources(
        workflow,
        request,
        allocator=allocator,
    )
    positive_id, negative_id = _build_sd15_conditioning(
        workflow,
        request,
        allocator=allocator,
        clip_source=clip_source,
    )
    positive_ref, negative_ref = _apply_controlnet_units(
        workflow,
        allocator=allocator,
        request=request,
        positive_ref=positive_id,
        negative_ref=negative_id,
        model_source=model_source,
        vae_source=vae_source,
    )
    image_id = allocator.next()
    workflow[image_id] = {
        "class_type": "RookieUILoadAssetImage",
        "inputs": {
            "asset_handle": request.image_asset,
        },
    }

    resized_image_id = _append_img2img_resize_node(
        workflow,
        source_image_id=image_id,
        request=request,
        allocator=allocator,
    )

    mask_id = allocator.next()
    workflow[mask_id] = {
        "class_type": "RookieUILoadAssetMask",
        "inputs": {
            "asset_handle": request.mask_asset,
            "channel": "red",
            "invert": request.inpaint_mask_mode == "inpaint_not_masked",
            "blur_radius": request.mask_blur,
        },
    }

    grow_mask_by = request.grow_mask_by
    if request.inpaint_area == "only_masked":
        grow_mask_by = max(grow_mask_by, request.inpaint_padding)

    encode_id = allocator.next()
    workflow[encode_id] = {
        "class_type": "RookieUIVAEEncodeForInpaint",
        "inputs": {
            "pixels": [resized_image_id, 0],
            "vae": vae_source,
            "mask": [mask_id, 0],
            "grow_mask_by": grow_mask_by,
            "masked_content": request.inpaint_masked_content,
            "seed": request.execution_seed,
            "soft_inpainting_enabled": request.soft_inpainting_enabled,
            "soft_inpainting_schedule_bias": request.soft_inpainting_schedule_bias,
            "soft_inpainting_preservation_strength": request.soft_inpainting_preservation_strength,
            "soft_inpainting_transition_contrast_boost": request.soft_inpainting_transition_contrast_boost,
            "soft_inpainting_mask_influence": request.soft_inpainting_mask_influence,
            "soft_inpainting_difference_threshold": request.soft_inpainting_difference_threshold,
            "soft_inpainting_difference_contrast": request.soft_inpainting_difference_contrast,
        },
    }

    latent_id = _append_latent_resize_node(
        workflow,
        latent_id=encode_id,
        request=request,
        allocator=allocator,
    )

    sampler_id = allocator.next()
    _build_sampler_node(
        workflow,
        node_id=sampler_id,
        positive_id=positive_ref,
        negative_id=negative_ref,
        latent_id=latent_id,
        request=request,
        denoise=request.denoise_strength,
        model_source=model_source,
    )
    final_sampler_id = sampler_id
    decode_id = allocator.next()
    save_id = allocator.next()
    if request.hires_enabled:
        upscale_id = decode_id
        hires_sampler_id = save_id
        decode_id = allocator.next()
        save_id = allocator.next()
        workflow[upscale_id] = {
            "class_type": "LatentUpscaleBy",
            "inputs": {
                "samples": [sampler_id, 0],
                "upscale_method": request.hires_upscale_method,
                "scale_by": request.hires_scale,
            },
        }
        _build_sampler_node(
            workflow,
            node_id=hires_sampler_id,
            positive_id=positive_ref,
            negative_id=negative_ref,
            latent_id=upscale_id,
            request=request,
            denoise=request.hires_denoise,
            model_source=model_source,
            seed=request.execution_seed,
            steps=request.hires_steps,
        )
        final_sampler_id = hires_sampler_id
    _append_decode_adetailer_and_save(
        workflow,
        allocator=allocator,
        sampler_id=final_sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        request=request,
        model_source=model_source,
        clip_source=clip_source,
        vae_source=vae_source,
        width=request.width,
        height=request.height,
    )
    return workflow


def _build_sdxl_inpaint_graph(request: NormalizedImg2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    model_source, clip_source, vae_source = _resolve_model_sources(
        workflow,
        request,
        allocator=allocator,
    )
    positive_id, negative_id = _build_sdxl_conditioning(
        workflow,
        request,
        allocator=allocator,
        width=request.width,
        height=request.height,
        clip_source=clip_source,
    )
    positive_ref, negative_ref = _apply_controlnet_units(
        workflow,
        allocator=allocator,
        request=request,
        positive_ref=positive_id,
        negative_ref=negative_id,
        model_source=model_source,
        vae_source=vae_source,
    )
    image_id = allocator.next()
    workflow[image_id] = {
        "class_type": "RookieUILoadAssetImage",
        "inputs": {
            "asset_handle": request.image_asset,
        },
    }

    resized_image_id = _append_img2img_resize_node(
        workflow,
        source_image_id=image_id,
        request=request,
        allocator=allocator,
    )

    mask_id = allocator.next()
    workflow[mask_id] = {
        "class_type": "RookieUILoadAssetMask",
        "inputs": {
            "asset_handle": request.mask_asset,
            "channel": "red",
            "invert": request.inpaint_mask_mode == "inpaint_not_masked",
            "blur_radius": request.mask_blur,
        },
    }

    grow_mask_by = request.grow_mask_by
    if request.inpaint_area == "only_masked":
        grow_mask_by = max(grow_mask_by, request.inpaint_padding)

    encode_id = allocator.next()
    workflow[encode_id] = {
        "class_type": "RookieUIVAEEncodeForInpaint",
        "inputs": {
            "pixels": [resized_image_id, 0],
            "vae": vae_source,
            "mask": [mask_id, 0],
            "grow_mask_by": grow_mask_by,
            "masked_content": request.inpaint_masked_content,
            "seed": request.execution_seed,
            "soft_inpainting_enabled": request.soft_inpainting_enabled,
            "soft_inpainting_schedule_bias": request.soft_inpainting_schedule_bias,
            "soft_inpainting_preservation_strength": request.soft_inpainting_preservation_strength,
            "soft_inpainting_transition_contrast_boost": request.soft_inpainting_transition_contrast_boost,
            "soft_inpainting_mask_influence": request.soft_inpainting_mask_influence,
            "soft_inpainting_difference_threshold": request.soft_inpainting_difference_threshold,
            "soft_inpainting_difference_contrast": request.soft_inpainting_difference_contrast,
        },
    }

    latent_id = _append_latent_resize_node(
        workflow,
        latent_id=encode_id,
        request=request,
        allocator=allocator,
    )

    sampler_id = allocator.next()
    _build_sampler_node(
        workflow,
        node_id=sampler_id,
        positive_id=positive_ref,
        negative_id=negative_ref,
        latent_id=latent_id,
        request=request,
        denoise=request.denoise_strength,
        model_source=model_source,
    )
    final_sampler_id = sampler_id
    decode_id = allocator.next()
    save_id = allocator.next()
    if request.hires_enabled:
        upscale_id = decode_id
        hires_sampler_id = save_id
        decode_id = allocator.next()
        save_id = allocator.next()
        workflow[upscale_id] = {
            "class_type": "LatentUpscaleBy",
            "inputs": {
                "samples": [sampler_id, 0],
                "upscale_method": request.hires_upscale_method,
                "scale_by": request.hires_scale,
            },
        }
        _build_sampler_node(
            workflow,
            node_id=hires_sampler_id,
            positive_id=positive_ref,
            negative_id=negative_ref,
            latent_id=upscale_id,
            request=request,
            denoise=request.hires_denoise,
            model_source=model_source,
            seed=request.execution_seed,
            steps=request.hires_steps,
        )
        final_sampler_id = hires_sampler_id
    _append_decode_adetailer_and_save(
        workflow,
        allocator=allocator,
        sampler_id=final_sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        request=request,
        model_source=model_source,
        clip_source=clip_source,
        vae_source=vae_source,
        width=request.width,
        height=request.height,
    )
    return workflow


def build_txt2img_workflow(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    if request.base_family == "sd15":
        return _build_sd15_txt2img_graph(request)
    if request.base_family == "sdxl":
        return _build_sdxl_txt2img_graph(request)

    raise ValueError(f"Unsupported RookieUI base family: {request.base_family}")


def build_img2img_workflow(request: NormalizedImg2ImgRequest) -> dict[str, object]:
    # IMPORTANT: keep execution_mode as the graph selector; user-facing mode labels (sketch/inpaint_upload/batch) are normalized upstream.
    if request.base_family == "sd15":
        if request.execution_mode == "inpaint":
            return _build_sd15_inpaint_graph(request)
        return _build_sd15_img2img_graph(request)
    if request.base_family == "sdxl":
        if request.execution_mode == "inpaint":
            return _build_sdxl_inpaint_graph(request)
        return _build_sdxl_img2img_graph(request)

    raise ValueError(f"Unsupported RookieUI base family: {request.base_family}")


def translate_txt2img_request(request: NormalizedTxt2ImgRequest) -> WorkflowTranslationResult:
    parity_profile = get_parity_profile(request.profile)
    workflow_kind = f"txt2img-{request.base_family}"
    if request.hires_enabled:
        workflow_kind = f"{workflow_kind}-hires"
    return WorkflowTranslationResult(
        mode="translation-only",
        workflow_kind=workflow_kind,
        profile=request.profile,
        normalized_request=request.to_payload(),
        parity_profile=parity_profile.to_payload(),
        sampler_aliases=get_sampler_alias_payload(),
        workflow=build_txt2img_workflow(request),
    )


def translate_img2img_request(request: NormalizedImg2ImgRequest) -> WorkflowTranslationResult:
    parity_profile = get_parity_profile(request.profile)
    workflow_kind = f"{request.mode}-{request.base_family}"
    if request.hires_enabled:
        workflow_kind = f"{workflow_kind}-hires"
    return WorkflowTranslationResult(
        mode="translation-only",
        workflow_kind=workflow_kind,
        profile=request.profile,
        normalized_request=request.to_payload(),
        parity_profile=parity_profile.to_payload(),
        sampler_aliases=get_sampler_alias_payload(),
        workflow=build_img2img_workflow(request),
    )
