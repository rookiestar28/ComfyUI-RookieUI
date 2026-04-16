from __future__ import annotations

from rookieui.contracts.generation import (
    NormalizedImg2ImgRequest,
    NormalizedTxt2ImgRequest,
    WorkflowTranslationResult,
)
from rookieui.services import parity_matrix
from rookieui.services.workflow_builders.adetailer import _append_decode_adetailer_and_save
from rookieui.services.workflow_builders.controlnet import _apply_controlnet_units
from rookieui.services.workflow_builders.core import (
    NodeIdAllocator,
    _append_img2img_resize_node,
    _append_latent_resize_node,
    _build_sampler_node,
    _resolve_model_sources,
)
from rookieui.services.workflow_builders import prompt_conditioning

# IMPORTANT: phase-59 refactor keeps this module as the stable workflow-translation facade.
# New builder ownership must move behind this file, not around it, so routes/tests keep one import surface.

def _build_sd15_txt2img_graph(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    model_source, clip_source, vae_source = _resolve_model_sources(
        workflow,
        request,
        allocator=allocator,
    )
    positive_id, negative_id = prompt_conditioning._build_sd15_conditioning(
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
    positive_id, negative_id = prompt_conditioning._build_sdxl_conditioning(
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
    positive_id, negative_id = prompt_conditioning._build_sd15_conditioning(
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
    positive_id, negative_id = prompt_conditioning._build_sdxl_conditioning(
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
    positive_id, negative_id = prompt_conditioning._build_sd15_conditioning(
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
    positive_id, negative_id = prompt_conditioning._build_sdxl_conditioning(
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
    parity_profile = parity_matrix.get_parity_profile(request.profile)
    workflow_kind = f"txt2img-{request.base_family}"
    if request.hires_enabled:
        workflow_kind = f"{workflow_kind}-hires"
    return WorkflowTranslationResult(
        mode="translation-only",
        workflow_kind=workflow_kind,
        profile=request.profile,
        normalized_request=request.to_payload(),
        parity_profile=parity_profile.to_payload(),
        sampler_aliases=parity_matrix.get_sampler_alias_payload(),
        workflow=build_txt2img_workflow(request),
    )


def translate_img2img_request(request: NormalizedImg2ImgRequest) -> WorkflowTranslationResult:
    parity_profile = parity_matrix.get_parity_profile(request.profile)
    workflow_kind = f"{request.mode}-{request.base_family}"
    if request.hires_enabled:
        workflow_kind = f"{workflow_kind}-hires"
    return WorkflowTranslationResult(
        mode="translation-only",
        workflow_kind=workflow_kind,
        profile=request.profile,
        normalized_request=request.to_payload(),
        parity_profile=parity_profile.to_payload(),
        sampler_aliases=parity_matrix.get_sampler_alias_payload(),
        workflow=build_img2img_workflow(request),
    )
