from __future__ import annotations

import re

from rookieui.contracts.generation import (
    NormalizedImg2ImgRequest,
    NormalizedTxt2ImgRequest,
)


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


def _build_clip_loader_node(clip_name: str, *, clip_type: str = "stable_diffusion") -> dict[str, object]:
    return {
        "class_type": "CLIPLoader",
        "inputs": {
            "clip_name": clip_name,
            "type": clip_type,
            "device": "default",
        },
    }


def _build_dual_clip_loader_node(
    *,
    clip_name_1: str,
    clip_name_2: str,
    clip_type: str,
) -> dict[str, object]:
    return {
        "class_type": "DualCLIPLoader",
        "inputs": {
            "clip_name1": clip_name_1,
            "clip_name2": clip_name_2,
            "type": clip_type,
            "device": "default",
        },
    }


def _build_quadruple_clip_loader_node(
    *,
    clip_name_1: str,
    clip_name_2: str,
    clip_name_3: str,
    clip_name_4: str,
) -> dict[str, object]:
    return {
        "class_type": "QuadrupleCLIPLoader",
        "inputs": {
            "clip_name1": clip_name_1,
            "clip_name2": clip_name_2,
            "clip_name3": clip_name_3,
            "clip_name4": clip_name_4,
        },
    }


def _build_vae_loader_node(vae_name: str) -> dict[str, object]:
    return {
        "class_type": "VAELoader",
        "inputs": {
            "vae_name": vae_name,
        },
    }


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


def _resolve_clip_loader_type(profile_id: str) -> str:
    normalized_profile = str(profile_id or "").strip().lower()
    if normalized_profile == "chroma":
        return "chroma"
    if normalized_profile in {
        "ernie_image",
        "ernie_image_turbo",
        "klein_4b_distilled",
        "klein_4b",
        "klein_9b_distilled",
        "klein_9b",
    }:
        return "flux2"
    if normalized_profile == "qwen_image":
        return "qwen_image"
    if normalized_profile in {"z_image", "z_image_turbo"}:
        return "lumina2"
    if normalized_profile == "longcat_image":
        return "longcat_image"
    return "stable_diffusion"


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
    if len(text_encoder_values) not in {1, 2, 4}:
        raise ValueError(
            "text_encoder_name supports one, two, or four selectors for diffusion_models path."
        )

    clip_loader_id = allocator.next()
    if len(text_encoder_values) == 1:
        workflow[clip_loader_id] = _build_clip_loader_node(
            text_encoder_values[0],
            clip_type=_resolve_clip_loader_type(request.profile),
        )
    elif len(text_encoder_values) == 2:
        workflow[clip_loader_id] = _build_dual_clip_loader_node(
            clip_name_1=text_encoder_values[0],
            clip_name_2=text_encoder_values[1],
            clip_type="flux",
        )
    else:
        workflow[clip_loader_id] = _build_quadruple_clip_loader_node(
            clip_name_1=text_encoder_values[0],
            clip_name_2=text_encoder_values[1],
            clip_name_3=text_encoder_values[2],
            clip_name_4=text_encoder_values[3],
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
