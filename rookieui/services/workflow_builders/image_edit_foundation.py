from __future__ import annotations

from dataclasses import dataclass

from rookieui.services.workflow_builders.core import NodeIdAllocator, _to_node_ref

_REFERENCE_SCALE_MODES = frozenset({"none", "main_only", "all"})
_IMAGE_STITCH_DIRECTIONS = frozenset({"right", "down", "left", "up"})
_IMAGE_STITCH_COLORS = frozenset({"white", "black", "red", "green", "blue"})
_FLUX_REFERENCE_METHOD_ALIASES = {
    "offset": "offset",
    "index": "index",
    "uxo": "uxo/uno",
    "uso": "uxo/uno",
    "uno": "uxo/uno",
    "uxo/uno": "uxo/uno",
    "index_timestep_zero": "index_timestep_zero",
}


@dataclass(frozen=True)
class ImageEditReferenceBundle:
    ordered_assets: tuple[str, ...]
    image_node_ids: tuple[str, ...]
    main_reference_index: int
    main_image_node_id: str


@dataclass(frozen=True)
class FluxKontextReferenceBundle:
    stitched_image_node_id: str
    scaled_image_node_id: str
    latent_node_id: str


@dataclass(frozen=True)
class Flux2LatentCanvasBundle:
    image_size_node_id: str
    latent_node_id: str


@dataclass(frozen=True)
class Flux2AdvancedSamplerBundle:
    latent_canvas: Flux2LatentCanvasBundle
    noise_node_id: str
    guider_node_id: str
    sampler_select_node_id: str
    sigmas_node_id: str
    sampler_node_id: str


def _append_asset_image_loader_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_asset: str,
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "RookieUILoadAssetImage",
        "inputs": {
            # IMPORTANT: Comfy prompt validation calls VALIDATE_INPUTS with declared input names; this must stay aligned with RookieUILoadAssetImage.INPUT_TYPES.
            "asset_handle": image_asset,
        },
    }
    return node_id


def _append_image_scale_to_total_pixels_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_id: str | list[object],
    megapixels: float,
    resolution_steps: int = 1,
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "ImageScaleToTotalPixels",
        "inputs": {
            "upscale_method": "lanczos",
            "megapixels": megapixels,
            "resolution_steps": int(resolution_steps),
            "image": _to_node_ref(image_id),
        },
    }
    return node_id


def _append_vae_encode_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_id: str | list[object],
    vae_source: list[object],
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "VAEEncode",
        "inputs": {
            "pixels": _to_node_ref(image_id),
            "vae": vae_source,
        },
    }
    return node_id


def _normalize_reference_scale_mode(scale_mode: str) -> str:
    normalized = str(scale_mode or "").strip().lower() or "none"
    if normalized not in _REFERENCE_SCALE_MODES:
        raise ValueError(f"Unsupported image-edit reference scale mode: {scale_mode}")
    return normalized


def _normalize_image_stitch_direction(direction: str) -> str:
    normalized = str(direction or "").strip().lower() or "right"
    if normalized not in _IMAGE_STITCH_DIRECTIONS:
        raise ValueError(f"Unsupported image stitch direction: {direction}")
    return normalized


def _normalize_image_stitch_color(color: str) -> str:
    normalized = str(color or "").strip().lower() or "white"
    if normalized not in _IMAGE_STITCH_COLORS:
        raise ValueError(f"Unsupported image stitch color: {color}")
    return normalized


def _build_image_edit_reference_bundle(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    reference_assets: list[str],
    main_reference_index: int,
    megapixels: float | None = None,
    scale_mode: str = "none",
    resolution_steps: int = 1,
) -> ImageEditReferenceBundle:
    if not reference_assets:
        raise ValueError("reference_assets must contain at least one image.")
    if main_reference_index < 0 or main_reference_index >= len(reference_assets):
        raise ValueError("main_reference_index is out of range for reference_assets.")

    normalized_scale_mode = _normalize_reference_scale_mode(scale_mode)
    image_node_ids = [
        _append_asset_image_loader_node(
            workflow,
            allocator=allocator,
            image_asset=asset,
        )
        for asset in reference_assets
    ]
    if megapixels is not None:
        if normalized_scale_mode == "main_only":
            image_node_ids[main_reference_index] = _append_image_scale_to_total_pixels_node(
                workflow,
                allocator=allocator,
                image_id=image_node_ids[main_reference_index],
                megapixels=megapixels,
                resolution_steps=resolution_steps,
            )
        elif normalized_scale_mode == "all":
            image_node_ids = [
                _append_image_scale_to_total_pixels_node(
                    workflow,
                    allocator=allocator,
                    image_id=image_node_id,
                    megapixels=megapixels,
                    resolution_steps=resolution_steps,
                )
                for image_node_id in image_node_ids
            ]

    return ImageEditReferenceBundle(
        ordered_assets=tuple(reference_assets),
        image_node_ids=tuple(image_node_ids),
        main_reference_index=main_reference_index,
        main_image_node_id=image_node_ids[main_reference_index],
    )


def _append_reference_vae_latents(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_node_ids: tuple[str, ...],
    vae_source: list[object],
) -> tuple[str, ...]:
    return tuple(
        _append_vae_encode_node(
            workflow,
            allocator=allocator,
            image_id=image_node_id,
            vae_source=vae_source,
        )
        for image_node_id in image_node_ids
    )


def _append_reference_latent_chain(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    conditioning_source: str | list[object],
    latent_node_ids: tuple[str, ...],
) -> list[object]:
    current_source = _to_node_ref(conditioning_source)
    for latent_node_id in latent_node_ids:
        node_id = allocator.next()
        workflow[node_id] = {
            "class_type": "ReferenceLatent",
            "inputs": {
                "conditioning": current_source,
                "latent": _to_node_ref(latent_node_id),
            },
        }
        current_source = [node_id, 0]
    return current_source


def _append_mirrored_reference_latent_chains(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    positive_conditioning_source: str | list[object],
    negative_conditioning_source: str | list[object],
    latent_node_ids: tuple[str, ...],
) -> tuple[list[object], list[object]]:
    positive_source = _append_reference_latent_chain(
        workflow,
        allocator=allocator,
        conditioning_source=positive_conditioning_source,
        latent_node_ids=latent_node_ids,
    )
    negative_source = _append_reference_latent_chain(
        workflow,
        allocator=allocator,
        conditioning_source=negative_conditioning_source,
        latent_node_ids=latent_node_ids,
    )
    return positive_source, negative_source


def _normalize_flux_reference_latents_method(method: str) -> str:
    normalized = str(method or "").strip().lower()
    normalized_method = _FLUX_REFERENCE_METHOD_ALIASES.get(normalized)
    if normalized_method is None:
        raise ValueError(f"Unsupported Flux multi-reference latent method: {method}")
    return normalized_method


def _append_flux_kontext_multi_reference_method_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    conditioning_source: str | list[object],
    method: str,
) -> str:
    normalized_method = _normalize_flux_reference_latents_method(method)
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "FluxKontextMultiReferenceLatentMethod",
        "inputs": {
            "conditioning": _to_node_ref(conditioning_source),
            "reference_latents_method": normalized_method,
        },
    }
    return node_id


def _append_flux_guidance_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    conditioning_source: str | list[object],
    guidance: float,
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "FluxGuidance",
        "inputs": {
            "guidance": guidance,
            "conditioning": _to_node_ref(conditioning_source),
        },
    }
    return node_id


def _append_flux_reference_method_branch(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    conditioning_source: str | list[object],
    guidance: float | None = None,
    reference_method: str | None = None,
) -> list[object]:
    current_source: str | list[object] = conditioning_source
    if guidance is not None:
        current_source = _append_flux_guidance_node(
            workflow,
            allocator=allocator,
            conditioning_source=current_source,
            guidance=guidance,
        )
    if reference_method:
        current_source = _append_flux_kontext_multi_reference_method_node(
            workflow,
            allocator=allocator,
            conditioning_source=current_source,
            method=reference_method,
        )
    return _to_node_ref(current_source)


def _append_image_stitch_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_1_id: str | list[object],
    image_2_id: str | list[object],
    direction: str = "right",
    match_image_size: bool = True,
    spacing_width: int = 0,
    spacing_color: str = "white",
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "ImageStitch",
        "inputs": {
            "image1": _to_node_ref(image_1_id),
            "direction": _normalize_image_stitch_direction(direction),
            "match_image_size": bool(match_image_size),
            "spacing_width": int(spacing_width),
            "spacing_color": _normalize_image_stitch_color(spacing_color),
            "image2": _to_node_ref(image_2_id),
        },
    }
    return node_id


def _append_image_stitch_chain(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_node_ids: tuple[str, ...],
    direction: str = "right",
    match_image_size: bool = True,
    spacing_width: int = 0,
    spacing_color: str = "white",
) -> str:
    if not image_node_ids:
        raise ValueError("image_node_ids must contain at least one image.")
    current_image_id = image_node_ids[0]
    for image_node_id in image_node_ids[1:]:
        current_image_id = _append_image_stitch_node(
            workflow,
            allocator=allocator,
            image_1_id=current_image_id,
            image_2_id=image_node_id,
            direction=direction,
            match_image_size=match_image_size,
            spacing_width=spacing_width,
            spacing_color=spacing_color,
        )
    return current_image_id


def _append_flux_kontext_image_scale_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_id: str | list[object],
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "FluxKontextImageScale",
        "inputs": {
            "image": _to_node_ref(image_id),
        },
    }
    return node_id


def _build_flux_kontext_reference_bundle(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_node_ids: tuple[str, ...],
    vae_source: list[object],
    direction: str = "right",
    match_image_size: bool = True,
    spacing_width: int = 0,
    spacing_color: str = "white",
) -> FluxKontextReferenceBundle:
    stitched_image_node_id = _append_image_stitch_chain(
        workflow,
        allocator=allocator,
        image_node_ids=image_node_ids,
        direction=direction,
        match_image_size=match_image_size,
        spacing_width=spacing_width,
        spacing_color=spacing_color,
    )
    scaled_image_node_id = _append_flux_kontext_image_scale_node(
        workflow,
        allocator=allocator,
        image_id=stitched_image_node_id,
    )
    latent_node_id = _append_vae_encode_node(
        workflow,
        allocator=allocator,
        image_id=scaled_image_node_id,
        vae_source=vae_source,
    )
    return FluxKontextReferenceBundle(
        stitched_image_node_id=stitched_image_node_id,
        scaled_image_node_id=scaled_image_node_id,
        latent_node_id=latent_node_id,
    )


def _append_get_image_size_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_id: str | list[object],
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "GetImageSize",
        "inputs": {
            "image": _to_node_ref(image_id),
        },
    }
    return node_id


def _append_flux2_latent_canvas_bundle(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_id: str | list[object],
    batch_size: int,
) -> Flux2LatentCanvasBundle:
    image_size_node_id = _append_get_image_size_node(
        workflow,
        allocator=allocator,
        image_id=image_id,
    )
    latent_node_id = allocator.next()
    workflow[latent_node_id] = {
        "class_type": "EmptyFlux2LatentImage",
        "inputs": {
            "width": [image_size_node_id, 0],
            "height": [image_size_node_id, 1],
            "batch_size": batch_size,
        },
    }
    return Flux2LatentCanvasBundle(
        image_size_node_id=image_size_node_id,
        latent_node_id=latent_node_id,
    )


def _append_random_noise_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    noise_seed: int,
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "RandomNoise",
        "inputs": {
            "noise_seed": noise_seed,
        },
    }
    return node_id


def _append_basic_guider_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    model_source: list[object],
    conditioning_source: str | list[object],
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "BasicGuider",
        "inputs": {
            "model": model_source,
            "conditioning": _to_node_ref(conditioning_source),
        },
    }
    return node_id


def _append_cfg_guider_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    cfg_scale: float,
    model_source: list[object],
    positive_id: str | list[object],
    negative_id: str | list[object],
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "CFGGuider",
        "inputs": {
            "cfg": cfg_scale,
            "model": model_source,
            "positive": _to_node_ref(positive_id),
            "negative": _to_node_ref(negative_id),
        },
    }
    return node_id


def _append_ksampler_select_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    sampler_name: str,
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "KSamplerSelect",
        "inputs": {
            "sampler_name": sampler_name,
        },
    }
    return node_id


def _append_flux2_scheduler_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    steps: int | list[object],
    width: int | list[object],
    height: int | list[object],
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "Flux2Scheduler",
        "inputs": {
            "steps": steps if isinstance(steps, int) else _to_node_ref(steps),
            "width": _to_node_ref(width),
            "height": _to_node_ref(height),
        },
    }
    return node_id


def _append_sampler_custom_advanced_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    noise_id: str | list[object],
    guider_id: str | list[object],
    sampler_id: str | list[object],
    sigmas_id: str | list[object],
    latent_id: str | list[object],
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "SamplerCustomAdvanced",
        "inputs": {
            "noise": _to_node_ref(noise_id),
            "guider": _to_node_ref(guider_id),
            "sampler": _to_node_ref(sampler_id),
            "sigmas": _to_node_ref(sigmas_id),
            "latent_image": _to_node_ref(latent_id),
        },
    }
    return node_id


def _append_flux_kv_cache_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    model_source: list[object],
) -> list[object]:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "FluxKVCache",
        "inputs": {
            "model": model_source,
        },
    }
    return [node_id, 0]


def _append_flux2_advanced_sampler_bundle(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    model_source: list[object],
    size_image_id: str | list[object],
    positive_conditioning_source: str | list[object],
    steps: int,
    sampler_name: str,
    noise_seed: int,
    batch_size: int = 1,
    negative_conditioning_source: str | list[object] | None = None,
    cfg_scale: float | None = None,
) -> Flux2AdvancedSamplerBundle:
    latent_canvas = _append_flux2_latent_canvas_bundle(
        workflow,
        allocator=allocator,
        image_id=size_image_id,
        batch_size=batch_size,
    )
    noise_node_id = _append_random_noise_node(
        workflow,
        allocator=allocator,
        noise_seed=noise_seed,
    )
    if negative_conditioning_source is None:
        guider_node_id = _append_basic_guider_node(
            workflow,
            allocator=allocator,
            model_source=model_source,
            conditioning_source=positive_conditioning_source,
        )
    else:
        if cfg_scale is None:
            raise ValueError("cfg_scale is required when negative_conditioning_source is provided.")
        guider_node_id = _append_cfg_guider_node(
            workflow,
            allocator=allocator,
            cfg_scale=cfg_scale,
            model_source=model_source,
            positive_id=positive_conditioning_source,
            negative_id=negative_conditioning_source,
        )
    sampler_select_node_id = _append_ksampler_select_node(
        workflow,
        allocator=allocator,
        sampler_name=sampler_name,
    )
    sigmas_node_id = _append_flux2_scheduler_node(
        workflow,
        allocator=allocator,
        steps=steps,
        width=[latent_canvas.image_size_node_id, 0],
        height=[latent_canvas.image_size_node_id, 1],
    )
    sampler_node_id = _append_sampler_custom_advanced_node(
        workflow,
        allocator=allocator,
        noise_id=noise_node_id,
        guider_id=guider_node_id,
        sampler_id=sampler_select_node_id,
        sigmas_id=sigmas_node_id,
        latent_id=latent_canvas.latent_node_id,
    )
    return Flux2AdvancedSamplerBundle(
        latent_canvas=latent_canvas,
        noise_node_id=noise_node_id,
        guider_node_id=guider_node_id,
        sampler_select_node_id=sampler_select_node_id,
        sigmas_node_id=sigmas_node_id,
        sampler_node_id=sampler_node_id,
    )
