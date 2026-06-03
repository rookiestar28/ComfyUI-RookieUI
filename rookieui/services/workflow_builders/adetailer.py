from __future__ import annotations

import re

from rookieui.contracts.adetailer import NormalizedADetailerUnitRequest
from rookieui.contracts.controlnet import NormalizedControlNetUnit
from rookieui.contracts.generation import (
    NormalizedImg2ImgRequest,
    NormalizedTxt2ImgRequest,
)
from rookieui.services.model_inventory import discover_model_inventory
from rookieui.services.parity_matrix import (
    normalize_sampler_name,
    normalize_scheduler_name,
)
from rookieui.services.prompt_dsl import preprocess_prompt_bundle
from rookieui.services.workflow_builders.controlnet import _apply_controlnet_unit_entries
from rookieui.services.workflow_builders.core import (
    NodeIdAllocator,
    _build_checkpoint_loader_node,
    _build_sampler_node,
    _build_vae_loader_node,
)
from rookieui.services.workflow_builders.output import (
    _append_decode_node,
    _append_save_node,
)
from rookieui.services.workflow_builders.prompt_conditioning import (
    _compile_prompt_semantic_conditioning,
    _resolve_conditioning_prompt_encoder,
    _uses_sd_family_prompt_parity,
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
        request=request,
    )
