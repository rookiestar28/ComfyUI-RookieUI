from __future__ import annotations

from rookieui.contracts.generation import (
    NormalizedImg2ImgRequest,
    NormalizedTxt2ImgRequest,
    WorkflowTranslationResult,
)
from rookieui.services.parity_matrix import get_parity_profile, get_sampler_alias_payload


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


def _build_checkpoint_loader_node(checkpoint_name: str) -> dict[str, object]:
    return {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": checkpoint_name,
        },
    }


def _build_sd15_conditioning(
    workflow: dict[str, object],
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
    *,
    allocator: NodeIdAllocator,
    clip_source: list[object],
) -> tuple[str, str]:
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
    positive_id = allocator.next()

    negative_id = allocator.next()
    workflow[positive_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": request.prompt,
            "clip": clip_source,
        },
    }
    workflow[negative_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": request.negative_prompt,
            "clip": clip_source,
        },
    }
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
    positive_id = allocator.next()
    negative_id = allocator.next()
    common_inputs = {
        "clip": clip_source,
        "width": width,
        "height": height,
        "crop_w": 0,
        "crop_h": 0,
        "target_width": width,
        "target_height": height,
    }
    workflow[positive_id] = {
        "class_type": "CLIPTextEncodeSDXL",
        "inputs": {
            **common_inputs,
            "text_g": request.prompt,
            "text_l": request.prompt,
        },
    }
    workflow[negative_id] = {
        "class_type": "CLIPTextEncodeSDXL",
        "inputs": {
            **common_inputs,
            "text_g": request.negative_prompt,
            "text_l": request.negative_prompt,
        },
    }
    return positive_id, negative_id


def _build_sampler_node(
    workflow: dict[str, object],
    *,
    node_id: str,
    positive_id: str,
    negative_id: str,
    latent_id: str,
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
    denoise: float,
    model_source: list[object],
    seed: int | None = None,
    steps: int | None = None,
) -> None:
    workflow[node_id] = {
        "class_type": "KSampler",
        "inputs": {
            "model": model_source,
            "positive": [positive_id, 0],
            "negative": [negative_id, 0],
            "latent_image": [latent_id, 0],
            "seed": request.execution_seed if seed is None else seed,
            "steps": request.steps if steps is None else steps,
            "cfg": request.cfg_scale,
            "sampler_name": request.sampler_name,
            "scheduler": request.scheduler_name,
            "denoise": denoise,
        },
    }


def _build_decode_and_save(
    workflow: dict[str, object],
    *,
    sampler_id: str,
    decode_id: str,
    save_id: str,
    vae_source: list[object],
) -> None:
    workflow[decode_id] = {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": [sampler_id, 0],
            "vae": vae_source,
        },
    }
    workflow[save_id] = {
        "class_type": "SaveImage",
        "inputs": {
            "images": [decode_id, 0],
            "filename_prefix": "RookieUI",
        },
    }


def _resolve_model_sources(
    workflow: dict[str, object],
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
    *,
    allocator: NodeIdAllocator,
    checkpoint_id: str,
) -> tuple[list[object], list[object], list[object]]:
    model_source: list[object] = [checkpoint_id, 0]
    clip_source: list[object] = [checkpoint_id, 1]
    vae_source: list[object] = [checkpoint_id, 2]

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
    checkpoint_id = allocator.next()
    workflow[checkpoint_id] = _build_checkpoint_loader_node(request.checkpoint_name)
    model_source, clip_source, vae_source = _resolve_model_sources(
        workflow,
        request,
        allocator=allocator,
        checkpoint_id=checkpoint_id,
    )
    positive_id, negative_id = _build_sd15_conditioning(
        workflow,
        request,
        allocator=allocator,
        clip_source=clip_source,
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
        positive_id=positive_id,
        negative_id=negative_id,
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
            positive_id=positive_id,
            negative_id=negative_id,
            latent_id=upscale_id,
            request=request,
            denoise=request.hires_denoise,
            model_source=model_source,
            seed=request.execution_seed,
            steps=request.hires_steps,
        )
        final_sampler_id = hires_sampler_id
    _build_decode_and_save(
        workflow,
        sampler_id=final_sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=vae_source,
    )
    return workflow


def _build_sdxl_txt2img_graph(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    checkpoint_id = allocator.next()
    workflow[checkpoint_id] = _build_checkpoint_loader_node(request.checkpoint_name)
    model_source, clip_source, vae_source = _resolve_model_sources(
        workflow,
        request,
        allocator=allocator,
        checkpoint_id=checkpoint_id,
    )
    positive_id, negative_id = _build_sdxl_conditioning(
        workflow,
        request,
        allocator=allocator,
        width=request.width,
        height=request.height,
        clip_source=clip_source,
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
        positive_id=positive_id,
        negative_id=negative_id,
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
            positive_id=positive_id,
            negative_id=negative_id,
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
    _build_decode_and_save(
        workflow,
        sampler_id=final_sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=vae_source,
    )
    return workflow


def _build_sd15_img2img_graph(request: NormalizedImg2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    checkpoint_id = allocator.next()
    workflow[checkpoint_id] = _build_checkpoint_loader_node(request.checkpoint_name)
    model_source, clip_source, vae_source = _resolve_model_sources(
        workflow,
        request,
        allocator=allocator,
        checkpoint_id=checkpoint_id,
    )
    positive_id, negative_id = _build_sd15_conditioning(
        workflow,
        request,
        allocator=allocator,
        clip_source=clip_source,
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
        positive_id=positive_id,
        negative_id=negative_id,
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
            positive_id=positive_id,
            negative_id=negative_id,
            latent_id=upscale_id,
            request=request,
            denoise=request.hires_denoise,
            model_source=model_source,
            seed=request.execution_seed,
            steps=request.hires_steps,
        )
        final_sampler_id = hires_sampler_id
    _build_decode_and_save(
        workflow,
        sampler_id=final_sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=vae_source,
    )
    return workflow


def _build_sdxl_img2img_graph(request: NormalizedImg2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    checkpoint_id = allocator.next()
    workflow[checkpoint_id] = _build_checkpoint_loader_node(request.checkpoint_name)
    model_source, clip_source, vae_source = _resolve_model_sources(
        workflow,
        request,
        allocator=allocator,
        checkpoint_id=checkpoint_id,
    )
    positive_id, negative_id = _build_sdxl_conditioning(
        workflow,
        request,
        allocator=allocator,
        width=request.width,
        height=request.height,
        clip_source=clip_source,
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
        positive_id=positive_id,
        negative_id=negative_id,
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
            positive_id=positive_id,
            negative_id=negative_id,
            latent_id=upscale_id,
            request=request,
            denoise=request.hires_denoise,
            model_source=model_source,
            seed=request.execution_seed,
            steps=request.hires_steps,
        )
        final_sampler_id = hires_sampler_id
    _build_decode_and_save(
        workflow,
        sampler_id=final_sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=vae_source,
    )
    return workflow


def _build_sd15_inpaint_graph(request: NormalizedImg2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    checkpoint_id = allocator.next()
    workflow[checkpoint_id] = _build_checkpoint_loader_node(request.checkpoint_name)
    model_source, clip_source, vae_source = _resolve_model_sources(
        workflow,
        request,
        allocator=allocator,
        checkpoint_id=checkpoint_id,
    )
    positive_id, negative_id = _build_sd15_conditioning(
        workflow,
        request,
        allocator=allocator,
        clip_source=clip_source,
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
        positive_id=positive_id,
        negative_id=negative_id,
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
            positive_id=positive_id,
            negative_id=negative_id,
            latent_id=upscale_id,
            request=request,
            denoise=request.hires_denoise,
            model_source=model_source,
            seed=request.execution_seed,
            steps=request.hires_steps,
        )
        final_sampler_id = hires_sampler_id
    _build_decode_and_save(
        workflow,
        sampler_id=final_sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=vae_source,
    )
    return workflow


def _build_sdxl_inpaint_graph(request: NormalizedImg2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    checkpoint_id = allocator.next()
    workflow[checkpoint_id] = _build_checkpoint_loader_node(request.checkpoint_name)
    model_source, clip_source, vae_source = _resolve_model_sources(
        workflow,
        request,
        allocator=allocator,
        checkpoint_id=checkpoint_id,
    )
    positive_id, negative_id = _build_sdxl_conditioning(
        workflow,
        request,
        allocator=allocator,
        width=request.width,
        height=request.height,
        clip_source=clip_source,
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
        positive_id=positive_id,
        negative_id=negative_id,
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
            positive_id=positive_id,
            negative_id=negative_id,
            latent_id=upscale_id,
            request=request,
            denoise=request.hires_denoise,
            model_source=model_source,
            seed=request.execution_seed,
            steps=request.hires_steps,
        )
        final_sampler_id = hires_sampler_id
    _build_decode_and_save(
        workflow,
        sampler_id=final_sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=vae_source,
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
