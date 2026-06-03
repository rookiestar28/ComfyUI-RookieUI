from __future__ import annotations

from collections.abc import Callable

from rookieui.contracts.controlnet import NormalizedControlNetUnit
from rookieui.contracts.family_template_manifest import (
    build_non_sd_runtime_adapter_map,
    list_non_sd_edit_manifest_entries,
    build_non_sd_txt2img_profile_ids,
)
from rookieui.contracts.generation import NormalizedImg2ImgRequest, NormalizedTxt2ImgRequest
from rookieui.contracts.model_family_registry import get_model_family_registry_entry
from rookieui.contracts.prompt_dsl import PromptLoraActivation
from rookieui.services.workflow_builders.core import (
    NodeIdAllocator,
    _build_clip_loader_node,
    _build_dual_clip_loader_node,
    _build_quadruple_clip_loader_node,
    _build_sampler_node,
    _build_unet_loader_node,
    _build_vae_loader_node,
    _normalize_encoder_selector_values,
    _to_node_ref,
)
from rookieui.services.workflow_builders.image_edit_foundation import (
    _append_flux2_advanced_sampler_bundle,
    _append_flux_kv_cache_node,
    _append_flux_reference_method_branch,
    _append_flux_kontext_image_scale_node,
    _append_mirrored_reference_latent_chains,
    _append_reference_latent_chain,
    _append_reference_vae_latents,
    _append_vae_encode_node,
    _build_flux_kontext_reference_bundle,
    _build_image_edit_reference_bundle,
)
from rookieui.services.workflow_builders.output import _build_decode_and_save
from rookieui.services.workflow_builders import prompt_conditioning

_ERNIE_PROMPT_ENHANCER_TEMPLATE = (
    '<s>[SYSTEM_PROMPT]你是一个专业的文生图 Prompt 增强助手。你将收到用户的简短图片描述及目标生成分辨率，'
    "请据此扩写为一段内容丰富、细节充分的视觉描述，以帮助文生图模型生成高质量的图片。仅输出增强后的描述，"
    '不要包含任何解释或前缀。[/SYSTEM_PROMPT][INST]{"prompt": "{prompt}", "width": {width}, "height": {height}}[/INST]'
)
_OFFICIAL_NON_SD_TXT2IMG_PROFILES = frozenset(build_non_sd_txt2img_profile_ids())
_OFFICIAL_NON_SD_EDIT_PROFILES = frozenset(entry.id for entry in list_non_sd_edit_manifest_entries())
_NON_SD_RUNTIME_ADAPTER_BY_PROFILE = build_non_sd_runtime_adapter_map()


def is_official_non_sd_txt2img_profile(profile_id: str) -> bool:
    return str(profile_id or "").strip().lower() in _OFFICIAL_NON_SD_TXT2IMG_PROFILES


def is_official_non_sd_edit_profile(profile_id: str) -> bool:
    return str(profile_id or "").strip().lower() in _OFFICIAL_NON_SD_EDIT_PROFILES


def _append_empty_latent_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    class_type: str,
    width: int | list[object],
    height: int | list[object],
    batch_size: int,
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": class_type,
        "inputs": {
            "width": width,
            "height": height,
            "batch_size": batch_size,
        },
    }
    return node_id


def _append_conditioning_zero_out_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    conditioning_id: str | list[object],
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "ConditioningZeroOut",
        "inputs": {
            "conditioning": _to_node_ref(conditioning_id),
        },
    }
    return node_id


def _read_controlnet_unit_value(unit: NormalizedControlNetUnit, key: str) -> object:
    return getattr(unit, key, None)


def _append_model_patch_loader_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    patch_name: str,
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "ModelPatchLoader",
        "inputs": {
            "name": patch_name,
        },
    }
    return node_id


def _append_get_image_size_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_source: list[object],
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "GetImageSize",
        "inputs": {
            "image": image_source,
        },
    }
    return node_id


def _append_image_scale_to_total_pixels_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_source: list[object],
    upscale_method: str,
    megapixels: float = 1.0,
    resolution_steps: int = 1,
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "ImageScaleToTotalPixels",
        "inputs": {
            "image": image_source,
            "upscale_method": upscale_method,
            "megapixels": float(megapixels),
            "resolution_steps": int(resolution_steps),
        },
    }
    return node_id


def _normalize_z_image_canny_threshold(value: object, *, default: float) -> float:
    try:
        threshold = float(value)
    except (TypeError, ValueError):
        return default
    if threshold > 1.0:
        threshold = threshold / 100.0
    return max(0.01, min(0.99, threshold))


def _resolve_z_image_canny_thresholds(unit: NormalizedControlNetUnit) -> tuple[float, float]:
    raw_low = _read_controlnet_unit_value(unit, "threshold_a")
    raw_high = _read_controlnet_unit_value(unit, "threshold_b")
    if float(raw_low or 0.0) == 64.0 and float(raw_high or 0.0) == 64.0:
        return 0.3, 0.4
    return (
        _normalize_z_image_canny_threshold(raw_low, default=0.3),
        _normalize_z_image_canny_threshold(raw_high, default=0.4),
    )


def _append_canny_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_source: list[object],
    unit: NormalizedControlNetUnit,
) -> str:
    low_threshold, high_threshold = _resolve_z_image_canny_thresholds(unit)
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "Canny",
        "inputs": {
            "image": image_source,
            "low_threshold": low_threshold,
            "high_threshold": high_threshold,
        },
    }
    return node_id


def _classify_z_image_controlnet_module(unit: NormalizedControlNetUnit) -> str:
    module = str(_read_controlnet_unit_value(unit, "module") or "none").strip().lower()
    if module in {"", "none", "controlnet", "passthrough", "reference"}:
        return "controlnet"
    if "canny" in module:
        return "canny"
    if "depth" in module:
        return "depth"
    if "pose" in module:
        return "pose"
    raise ValueError(
        f"Unsupported Z-Image Turbo ControlNet module '{module}'. Supported modules: none, canny, depth, openpose."
    )


def _append_z_image_controlnet_image_adapter(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    unit: NormalizedControlNetUnit,
) -> tuple[list[object], list[object], list[object] | None]:
    image_asset = str(_read_controlnet_unit_value(unit, "image_asset") or "").strip()
    if not image_asset:
        raise ValueError("Z-Image Turbo ControlNet requires controlnet_units[0].image_asset.")
    image_id = allocator.next()
    workflow[image_id] = {
        "class_type": "RookieUILoadAssetImage",
        "inputs": {
            "asset_handle": image_asset,
        },
    }
    image_ref = [image_id, 0]

    mask_ref: list[object] | None = None
    mask_asset = str(_read_controlnet_unit_value(unit, "mask_asset") or "").strip()
    use_mask = bool(_read_controlnet_unit_value(unit, "use_mask"))
    if use_mask and mask_asset:
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

    module = _classify_z_image_controlnet_module(unit)
    if module == "canny":
        scale_id = _append_image_scale_to_total_pixels_node(
            workflow,
            allocator=allocator,
            image_source=image_ref,
            upscale_method="nearest-exact",
        )
        canny_id = _append_canny_node(
            workflow,
            allocator=allocator,
            image_source=[scale_id, 0],
            unit=unit,
        )
        canny_ref = [canny_id, 0]
        return canny_ref, canny_ref, mask_ref
    if module == "depth":
        # IMPORTANT: the 0.9.91 packaged Depth blueprint contains a Lotus subgraph, but its Qwen
        # ControlNet image edge is still the scaled input image; do not invent a Lotus runtime branch here.
        scale_id = _append_image_scale_to_total_pixels_node(
            workflow,
            allocator=allocator,
            image_source=image_ref,
            upscale_method="lanczos",
        )
        scale_ref = [scale_id, 0]
        return scale_ref, scale_ref, mask_ref
    return image_ref, image_ref, mask_ref


def _append_z_image_controlnet_model_patch_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    model_source: list[object],
    vae_source: list[object],
    control_image_source: list[object],
    mask_source: list[object] | None,
    unit: NormalizedControlNetUnit,
) -> list[object]:
    patch_name = str(_read_controlnet_unit_value(unit, "model") or "").strip()
    if not patch_name:
        raise ValueError("Z-Image Turbo ControlNet requires a model-patch selector.")
    patch_id = _append_model_patch_loader_node(
        workflow,
        allocator=allocator,
        patch_name=patch_name,
    )
    node_id = allocator.next()
    inputs: dict[str, object] = {
        "model": model_source,
        "model_patch": [patch_id, 0],
        "vae": vae_source,
        "image": control_image_source,
        "strength": float(_read_controlnet_unit_value(unit, "weight") or 1.0),
    }
    if mask_source is not None:
        inputs["mask"] = mask_source
    workflow[node_id] = {
        "class_type": "QwenImageDiffsynthControlnet",
        "inputs": inputs,
    }
    return [node_id, 0]


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


def _append_basic_guider_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    model_source: list[object],
    conditioning_id: str | list[object],
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "BasicGuider",
        "inputs": {
            "model": model_source,
            "conditioning": _to_node_ref(conditioning_id),
        },
    }
    return node_id


def _append_basic_scheduler_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    scheduler_name: str,
    steps: int,
    model_source: list[object],
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "BasicScheduler",
        "inputs": {
            "scheduler": scheduler_name,
            "steps": steps,
            "denoise": 1,
            "model": model_source,
        },
    }
    return node_id


def _append_flux2_scheduler_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    steps: int,
    width: int,
    height: int,
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "Flux2Scheduler",
        "inputs": {
            "steps": steps,
            "width": width,
            "height": height,
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


def _append_model_sampling_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    class_type: str,
    model_source: list[object],
    shift: float,
) -> list[object]:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": class_type,
        "inputs": {
            "shift": shift,
            "model": model_source,
        },
    }
    return [node_id, 0]


def _append_t5_tokenizer_options_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    clip_source: list[object],
) -> list[object]:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "T5TokenizerOptions",
        "inputs": {
            "min_padding": 0,
            "min_length": 0,
            "clip": clip_source,
        },
    }
    return [node_id, 0]


def _append_flux_guidance_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    conditioning_id: str | list[object],
    guidance: float,
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "FluxGuidance",
        "inputs": {
            "guidance": guidance,
            "conditioning": _to_node_ref(conditioning_id),
        },
    }
    return node_id


def _append_cfg_norm_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    model_source: list[object],
    strength: float = 1.0,
) -> list[object]:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "CFGNorm",
        "inputs": {
            "strength": strength,
            "model": model_source,
        },
    }
    return [node_id, 0]


def _append_lora_loader_model_only_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    model_source: list[object],
    lora_name: str,
    strength_model: float = 1.0,
) -> list[object]:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "LoraLoaderModelOnly",
        "inputs": {
            "lora_name": lora_name,
            "strength_model": strength_model,
            "model": model_source,
        },
    }
    return [node_id, 0]


def _append_model_only_lora_chain(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    model_source: list[object],
    template_lora_name: str = "",
    template_lora_names: list[str] | tuple[str, ...] | None = None,
    inline_lora_activations: list[PromptLoraActivation] | None = None,
) -> list[object]:
    chained_model_source = model_source
    effective_template_lora_names = [
        str(candidate or "").strip()
        for candidate in (
            template_lora_names
            if template_lora_names is not None
            else ([template_lora_name] if template_lora_name else [])
        )
        if str(candidate or "").strip()
    ]
    # CRITICAL: do not synthesize official template LoRA names here; ComfyUI Load LoRA raises on missing files.
    for effective_lora_name in effective_template_lora_names:
        chained_model_source = _append_lora_loader_model_only_node(
            workflow,
            allocator=allocator,
            model_source=chained_model_source,
            lora_name=effective_lora_name,
        )
    for activation in inline_lora_activations or []:
        chained_model_source = _append_lora_loader_model_only_node(
            workflow,
            allocator=allocator,
            model_source=chained_model_source,
            lora_name=activation.name,
            strength_model=activation.strength_model,
        )
    return chained_model_source


def _resolve_template_owned_lora_chain_names(template_lora_name: str, *, chain_mode: str) -> tuple[str, ...]:
    effective_template_lora_name = str(template_lora_name or "").strip()
    normalized_chain_mode = str(chain_mode or "").strip().lower() or "none"
    if not effective_template_lora_name:
        return ()
    if normalized_chain_mode == "single":
        return (effective_template_lora_name,)
    if normalized_chain_mode == "triple":
        return (effective_template_lora_name, effective_template_lora_name, effective_template_lora_name)
    if normalized_chain_mode == "none":
        return ()
    raise ValueError(f"Unsupported template-owned LoRA chain mode: {chain_mode}")


def _build_qwen_family_conditioning_nodes(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    request: NormalizedImg2ImgRequest,
    profile_entry: object,
    clip_source: list[object],
    vae_source: list[object],
    reference_image_node_ids: tuple[str, ...],
    main_image_node_id: str,
) -> tuple[str | list[object], str | list[object]]:
    encoder_family = str(getattr(profile_entry, "encoder_family", "") or "").strip().lower()
    if encoder_family == "qwen_image_edit_2511":
        positive_id = _append_qwen_image_edit_plus_encode_node(
            workflow,
            allocator=allocator,
            prompt_text=request.prompt,
            clip_source=clip_source,
            vae_source=vae_source,
            image_ids=reference_image_node_ids,
        )
        negative_id = _append_qwen_image_edit_plus_encode_node(
            workflow,
            allocator=allocator,
            prompt_text=request.negative_prompt,
            clip_source=clip_source,
            vae_source=vae_source,
            image_ids=reference_image_node_ids,
        )
        return (
            _append_flux_reference_method_branch(
                workflow,
                allocator=allocator,
                conditioning_source=positive_id,
                reference_method="index_timestep_zero",
            ),
            _append_flux_reference_method_branch(
                workflow,
                allocator=allocator,
                conditioning_source=negative_id,
                reference_method="index_timestep_zero",
            ),
        )
    if encoder_family == "qwen_image_edit_plus":
        positive_id = _append_qwen_image_edit_plus_encode_node(
            workflow,
            allocator=allocator,
            prompt_text=request.prompt,
            clip_source=clip_source,
            vae_source=vae_source,
            image_ids=reference_image_node_ids,
        )
        negative_id = _append_qwen_image_edit_plus_encode_node(
            workflow,
            allocator=allocator,
            prompt_text=request.negative_prompt,
            clip_source=clip_source,
            vae_source=vae_source,
            image_ids=reference_image_node_ids,
        )
        return positive_id, negative_id
    if encoder_family == "qwen_image_edit":
        positive_id = _append_qwen_image_edit_encode_node(
            workflow,
            allocator=allocator,
            prompt_text=request.prompt,
            clip_source=clip_source,
            vae_source=vae_source,
            image_id=main_image_node_id,
        )
        negative_id = _append_qwen_image_edit_encode_node(
            workflow,
            allocator=allocator,
            prompt_text=request.negative_prompt,
            clip_source=clip_source,
            vae_source=vae_source,
            image_id=main_image_node_id,
        )
        return positive_id, negative_id
    raise ValueError(f"Unsupported Qwen-family image-edit encoder family: {getattr(profile_entry, 'encoder_family', '')}")


def _append_string_replace_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    string_value: str | list[object],
    find_value: str,
    replace_value: str | list[object],
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "StringReplace",
        "inputs": {
            "string": string_value,
            "find": find_value,
            "replace": replace_value,
        },
    }
    return node_id


def _append_primitive_string_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    value: str,
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "PrimitiveStringMultiline",
        "inputs": {
            "value": value,
        },
    }
    return node_id


def _append_primitive_boolean_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    value: bool,
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "PrimitiveBoolean",
        "inputs": {
            "value": value,
        },
    }
    return node_id


def _append_text_generate_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    prompt_id: str | list[object],
    clip_source: list[object],
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "TextGenerate",
        "inputs": {
            "prompt": _to_node_ref(prompt_id),
            "max_length": 2048,
            "sampling_mode": "on",
            "sampling_mode.temperature": 0.6,
            "sampling_mode.top_k": 64,
            "sampling_mode.top_p": 0.8,
            "sampling_mode.min_p": 0.05,
            "sampling_mode.repetition_penalty": 1.05,
            "sampling_mode.seed": 0,
            "sampling_mode.presence_penalty": 0,
            "thinking": False,
            "use_default_template": True,
            "clip": clip_source,
        },
    }
    return node_id


def _append_switch_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    switch_id: str | list[object],
    on_false: str | list[object],
    on_true: str | list[object],
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "ComfySwitchNode",
        "inputs": {
            "switch": _to_node_ref(switch_id),
            "on_false": _to_node_ref(on_false),
            "on_true": _to_node_ref(on_true),
        },
    }
    return node_id


def _append_qwen_image_edit_encode_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    prompt_text: str,
    clip_source: list[object],
    vae_source: list[object],
    image_id: str | list[object],
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "TextEncodeQwenImageEdit",
        "inputs": {
            "prompt": prompt_text,
            "clip": clip_source,
            "vae": vae_source,
            "image": _to_node_ref(image_id),
        },
    }
    return node_id


def _append_qwen_image_edit_plus_encode_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    prompt_text: str,
    clip_source: list[object],
    vae_source: list[object],
    image_ids: tuple[str, ...],
) -> str:
    if len(image_ids) > 3:
        raise ValueError("TextEncodeQwenImageEditPlus supports at most 3 direct reference images.")
    node_id = allocator.next()
    inputs: dict[str, object] = {
        "prompt": prompt_text,
        "clip": clip_source,
        "vae": vae_source,
    }
    for image_index, image_id in enumerate(image_ids, start=1):
        inputs[f"image{image_index}"] = _to_node_ref(image_id)
    workflow[node_id] = {
        "class_type": "TextEncodeQwenImageEditPlus",
        "inputs": inputs,
    }
    return node_id


def _build_single_clip_source(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    clip_name: str,
    clip_type: str,
) -> list[object]:
    loader_id = allocator.next()
    workflow[loader_id] = _build_clip_loader_node(clip_name, clip_type=clip_type)
    return [loader_id, 0]


def _build_flux_dual_clip_source(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    clip_name_1: str,
    clip_name_2: str,
) -> list[object]:
    loader_id = allocator.next()
    workflow[loader_id] = _build_dual_clip_loader_node(
        clip_name_1=clip_name_1,
        clip_name_2=clip_name_2,
        clip_type="flux",
    )
    return [loader_id, 0]


def _build_hidream_quad_clip_source(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    clip_names: list[str],
) -> list[object]:
    loader_id = allocator.next()
    workflow[loader_id] = _build_quadruple_clip_loader_node(
        clip_name_1=clip_names[0],
        clip_name_2=clip_names[1],
        clip_name_3=clip_names[2],
        clip_name_4=clip_names[3],
    )
    return [loader_id, 0]


def _build_basic_positive_negative(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    clip_source: list[object],
    request: NormalizedTxt2ImgRequest,
    negative_mode: str,
) -> tuple[str, str]:
    positive_id = prompt_conditioning._append_prompt_encode_node(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        text=request.prompt,
        prompt_encoder="sd15",
    )
    if negative_mode == "zero_out":
        negative_id = _append_conditioning_zero_out_node(
            workflow,
            allocator=allocator,
            conditioning_id=positive_id,
        )
    else:
        negative_id = prompt_conditioning._append_prompt_encode_node(
            workflow,
            allocator=allocator,
            clip_source=clip_source,
            text=request.negative_prompt,
            prompt_encoder="sd15",
        )
    return positive_id, negative_id


def _build_anima_workflow(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    model_source = _append_model_only_lora_chain(
        workflow,
        allocator=allocator,
        model_source=[unet_id, 0],
        inline_lora_activations=request.lora_activations,
    )
    clip_source = _build_single_clip_source(
        workflow,
        allocator=allocator,
        clip_name=request.text_encoder_name,
        clip_type="stable_diffusion",
    )
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    positive_id, negative_id = _build_basic_positive_negative(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        request=request,
        negative_mode="encode",
    )
    latent_id = _append_empty_latent_node(
        workflow,
        allocator=allocator,
        class_type="EmptyLatentImage",
        width=request.width,
        height=request.height,
        batch_size=request.batch_size,
    )
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
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
        request=request,
    )
    return workflow


def _build_flux_workflow(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    encoder_values = _normalize_encoder_selector_values(request.text_encoder_name)
    if len(encoder_values) != 2:
        raise ValueError("Flux official template requires two ordered text encoders.")
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    model_source = _append_model_only_lora_chain(
        workflow,
        allocator=allocator,
        model_source=[unet_id, 0],
        template_lora_name=request.template_lora_name,
        inline_lora_activations=request.lora_activations,
    )
    clip_source = _build_flux_dual_clip_source(
        workflow,
        allocator=allocator,
        clip_name_1=encoder_values[0],
        clip_name_2=encoder_values[1],
    )
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    positive_id, negative_id = _build_basic_positive_negative(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        request=request,
        negative_mode="zero_out",
    )
    latent_id = _append_empty_latent_node(
        workflow,
        allocator=allocator,
        class_type="EmptySD3LatentImage",
        width=request.width,
        height=request.height,
        batch_size=request.batch_size,
    )
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
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
        request=request,
    )
    return workflow


def _build_hidream_workflow(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    encoder_values = _normalize_encoder_selector_values(request.text_encoder_name)
    if len(encoder_values) != 4:
        raise ValueError("HiDream official template requires four ordered text encoders.")
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    base_model_source = _append_model_only_lora_chain(
        workflow,
        allocator=allocator,
        model_source=[unet_id, 0],
        inline_lora_activations=request.lora_activations,
    )
    clip_source = _build_hidream_quad_clip_source(workflow, allocator=allocator, clip_names=encoder_values)
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    model_source = _append_model_sampling_node(
        workflow,
        allocator=allocator,
        class_type="ModelSamplingSD3",
        model_source=base_model_source,
        shift=float(request.shift or 0.0),
    )
    positive_id, negative_id = _build_basic_positive_negative(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        request=request,
        negative_mode="encode",
    )
    latent_id = _append_empty_latent_node(
        workflow,
        allocator=allocator,
        class_type="EmptySD3LatentImage",
        width=request.width,
        height=request.height,
        batch_size=request.batch_size,
    )
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
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
        request=request,
    )
    return workflow


def _build_chroma_workflow(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    base_model_source = _append_model_only_lora_chain(
        workflow,
        allocator=allocator,
        model_source=[unet_id, 0],
        inline_lora_activations=request.lora_activations,
    )
    clip_source = _build_single_clip_source(
        workflow,
        allocator=allocator,
        clip_name=request.text_encoder_name,
        clip_type="chroma",
    )
    tokenizer_source = _append_t5_tokenizer_options_node(workflow, allocator=allocator, clip_source=clip_source)
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    model_source = _append_model_sampling_node(
        workflow,
        allocator=allocator,
        class_type="ModelSamplingAuraFlow",
        model_source=base_model_source,
        shift=float(request.shift or 0.0),
    )
    positive_id, negative_id = _build_basic_positive_negative(
        workflow,
        allocator=allocator,
        clip_source=tokenizer_source,
        request=request,
        negative_mode="encode",
    )
    latent_id = _append_empty_latent_node(
        workflow,
        allocator=allocator,
        class_type="EmptySD3LatentImage",
        width=request.width,
        height=request.height,
        batch_size=request.batch_size,
    )
    noise_id = _append_random_noise_node(workflow, allocator=allocator, noise_seed=request.execution_seed)
    guider_id = _append_cfg_guider_node(
        workflow,
        allocator=allocator,
        cfg_scale=request.cfg_scale,
        model_source=model_source,
        positive_id=positive_id,
        negative_id=negative_id,
    )
    sampler_select_id = _append_ksampler_select_node(
        workflow,
        allocator=allocator,
        sampler_name=request.sampler_name,
    )
    scheduler_id = _append_basic_scheduler_node(
        workflow,
        allocator=allocator,
        scheduler_name=request.scheduler_name,
        steps=request.steps,
        model_source=model_source,
    )
    sampler_id = _append_sampler_custom_advanced_node(
        workflow,
        allocator=allocator,
        noise_id=noise_id,
        guider_id=guider_id,
        sampler_id=sampler_select_id,
        sigmas_id=scheduler_id,
        latent_id=latent_id,
    )
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
        request=request,
    )
    return workflow


def _build_klein_workflow(request: NormalizedTxt2ImgRequest, *, distilled: bool) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    model_source = _append_model_only_lora_chain(
        workflow,
        allocator=allocator,
        model_source=[unet_id, 0],
        inline_lora_activations=request.lora_activations,
    )
    clip_source = _build_single_clip_source(
        workflow,
        allocator=allocator,
        clip_name=request.text_encoder_name,
        clip_type="flux2",
    )
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    positive_id, negative_id = _build_basic_positive_negative(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        request=request,
        negative_mode="zero_out" if distilled else "encode",
    )
    latent_id = _append_empty_latent_node(
        workflow,
        allocator=allocator,
        class_type="EmptyFlux2LatentImage",
        width=request.width,
        height=request.height,
        batch_size=request.batch_size,
    )
    noise_id = _append_random_noise_node(workflow, allocator=allocator, noise_seed=request.execution_seed)
    guider_id = _append_cfg_guider_node(
        workflow,
        allocator=allocator,
        cfg_scale=request.cfg_scale,
        model_source=model_source,
        positive_id=positive_id,
        negative_id=negative_id,
    )
    sampler_select_id = _append_ksampler_select_node(
        workflow,
        allocator=allocator,
        sampler_name=request.sampler_name,
    )
    scheduler_id = _append_flux2_scheduler_node(
        workflow,
        allocator=allocator,
        steps=request.steps,
        width=request.width,
        height=request.height,
    )
    sampler_id = _append_sampler_custom_advanced_node(
        workflow,
        allocator=allocator,
        noise_id=noise_id,
        guider_id=guider_id,
        sampler_id=sampler_select_id,
        sigmas_id=scheduler_id,
        latent_id=latent_id,
    )
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
        request=request,
    )
    return workflow


def _build_flux2_dev_workflow(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    profile_entry = get_model_family_registry_entry(request.profile)
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    model_source = _append_model_only_lora_chain(
        workflow,
        allocator=allocator,
        model_source=[unet_id, 0],
        template_lora_name=request.template_lora_name,
        inline_lora_activations=request.lora_activations,
    )
    clip_source = _build_single_clip_source(
        workflow,
        allocator=allocator,
        clip_name=request.text_encoder_name,
        clip_type="flux2",
    )
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    positive_id = prompt_conditioning._append_prompt_encode_node(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        text=request.prompt,
        prompt_encoder="sd15",
    )
    positive_id = _append_flux_guidance_node(
        workflow,
        allocator=allocator,
        conditioning_id=positive_id,
        guidance=float(request.flux_guidance or profile_entry.default_flux_guidance or 0.0),
    )
    latent_id = _append_empty_latent_node(
        workflow,
        allocator=allocator,
        class_type="EmptyFlux2LatentImage",
        width=request.width,
        height=request.height,
        batch_size=request.batch_size,
    )
    noise_id = _append_random_noise_node(workflow, allocator=allocator, noise_seed=request.execution_seed)
    guider_id = _append_basic_guider_node(
        workflow,
        allocator=allocator,
        model_source=model_source,
        conditioning_id=positive_id,
    )
    sampler_select_id = _append_ksampler_select_node(
        workflow,
        allocator=allocator,
        sampler_name=request.sampler_name,
    )
    scheduler_id = _append_flux2_scheduler_node(
        workflow,
        allocator=allocator,
        steps=request.steps,
        width=request.width,
        height=request.height,
    )
    sampler_id = _append_sampler_custom_advanced_node(
        workflow,
        allocator=allocator,
        noise_id=noise_id,
        guider_id=guider_id,
        sampler_id=sampler_select_id,
        sigmas_id=scheduler_id,
        latent_id=latent_id,
    )
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
        request=request,
    )
    return workflow


def _build_qwen_image_workflow(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    model_source = _append_model_only_lora_chain(
        workflow,
        allocator=allocator,
        model_source=[unet_id, 0],
        template_lora_name=request.template_lora_name,
        inline_lora_activations=request.lora_activations,
    )
    clip_source = _build_single_clip_source(
        workflow,
        allocator=allocator,
        clip_name=request.text_encoder_name,
        clip_type="qwen_image",
    )
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    model_source = _append_model_sampling_node(
        workflow,
        allocator=allocator,
        class_type="ModelSamplingAuraFlow",
        model_source=model_source,
        shift=float(request.shift or 0.0),
    )
    positive_id, negative_id = _build_basic_positive_negative(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        request=request,
        negative_mode="zero_out",
    )
    latent_id = _append_empty_latent_node(
        workflow,
        allocator=allocator,
        class_type="EmptySD3LatentImage",
        width=request.width,
        height=request.height,
        batch_size=request.batch_size,
    )
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
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
        request=request,
    )
    return workflow


def _build_z_image_workflow(request: NormalizedTxt2ImgRequest, *, turbo: bool) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    enabled_controlnet_units = [unit for unit in request.controlnet_units if unit.enabled]
    control_image_size_source: list[object] | None = None
    if enabled_controlnet_units and not turbo:
        raise ValueError("Z-Image ControlNet is currently supported only for z_image_turbo.")
    if len(enabled_controlnet_units) > 1:
        raise ValueError("Z-Image Turbo ControlNet currently supports exactly one enabled unit.")
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    base_model_source = _append_model_only_lora_chain(
        workflow,
        allocator=allocator,
        model_source=[unet_id, 0],
        inline_lora_activations=request.lora_activations,
    )
    clip_source = _build_single_clip_source(
        workflow,
        allocator=allocator,
        clip_name=request.text_encoder_name,
        clip_type="lumina2",
    )
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    if enabled_controlnet_units:
        control_image_ref, control_image_size_source, mask_ref = _append_z_image_controlnet_image_adapter(
            workflow,
            allocator=allocator,
            unit=enabled_controlnet_units[0],
        )
        base_model_source = _append_z_image_controlnet_model_patch_node(
            workflow,
            allocator=allocator,
            model_source=base_model_source,
            vae_source=[vae_id, 0],
            control_image_source=control_image_ref,
            mask_source=mask_ref,
            unit=enabled_controlnet_units[0],
        )
    model_source = _append_model_sampling_node(
        workflow,
        allocator=allocator,
        class_type="ModelSamplingAuraFlow",
        model_source=base_model_source,
        shift=float(request.shift or 0.0),
    )
    positive_id, negative_id = _build_basic_positive_negative(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        request=request,
        negative_mode="zero_out" if turbo else "encode",
    )
    latent_width: int | list[object] = request.width
    latent_height: int | list[object] = request.height
    if control_image_size_source is not None:
        size_id = _append_get_image_size_node(
            workflow,
            allocator=allocator,
            image_source=control_image_size_source,
        )
        latent_width = [size_id, 0]
        latent_height = [size_id, 1]
    latent_id = _append_empty_latent_node(
        workflow,
        allocator=allocator,
        class_type="EmptySD3LatentImage",
        width=latent_width,
        height=latent_height,
        batch_size=request.batch_size,
    )
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
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
        request=request,
    )
    return workflow


def _build_longcat_workflow(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    base_model_source = _append_model_only_lora_chain(
        workflow,
        allocator=allocator,
        model_source=[unet_id, 0],
        inline_lora_activations=request.lora_activations,
    )
    clip_source = _build_single_clip_source(
        workflow,
        allocator=allocator,
        clip_name=request.text_encoder_name,
        clip_type="longcat_image",
    )
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    positive_id, negative_id = _build_basic_positive_negative(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        request=request,
        negative_mode="encode",
    )
    guided_positive_id = _append_flux_guidance_node(
        workflow,
        allocator=allocator,
        conditioning_id=positive_id,
        guidance=float(request.flux_guidance or 0.0),
    )
    guided_negative_id = _append_flux_guidance_node(
        workflow,
        allocator=allocator,
        conditioning_id=negative_id,
        guidance=float(request.flux_guidance or 0.0),
    )
    model_source = _append_cfg_norm_node(
        workflow,
        allocator=allocator,
        model_source=base_model_source,
    )
    latent_id = _append_empty_latent_node(
        workflow,
        allocator=allocator,
        class_type="EmptySD3LatentImage",
        width=request.width,
        height=request.height,
        batch_size=request.batch_size,
    )
    sampler_id = allocator.next()
    _build_sampler_node(
        workflow,
        node_id=sampler_id,
        positive_id=guided_positive_id,
        negative_id=guided_negative_id,
        latent_id=latent_id,
        request=request,
        denoise=1.0,
        model_source=model_source,
    )
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
        request=request,
    )
    return workflow


def _build_ernie_workflow(request: NormalizedTxt2ImgRequest, *, turbo: bool) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    if not request.aux_text_encoder_name:
        raise ValueError(f"Profile '{request.profile}' requires an auxiliary prompt-enhancer text encoder.")
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    model_source = _append_model_only_lora_chain(
        workflow,
        allocator=allocator,
        model_source=[unet_id, 0],
        inline_lora_activations=request.lora_activations,
    )
    main_clip_source = _build_single_clip_source(
        workflow,
        allocator=allocator,
        clip_name=request.text_encoder_name,
        clip_type="flux2",
    )
    prompt_enhancer_source = _build_single_clip_source(
        workflow,
        allocator=allocator,
        clip_name=request.aux_text_encoder_name,
        clip_type="flux2",
    )
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    prompt_text_id = _append_primitive_string_node(workflow, allocator=allocator, value=request.prompt)
    prompt_template_id = _append_string_replace_node(
        workflow,
        allocator=allocator,
        string_value=_ERNIE_PROMPT_ENHANCER_TEMPLATE,
        find_value="{prompt}",
        replace_value=[prompt_text_id, 0],
    )
    width_replace_id = _append_string_replace_node(
        workflow,
        allocator=allocator,
        string_value=[prompt_template_id, 0],
        find_value="{width}",
        replace_value=str(request.width),
    )
    prompt_payload_id = _append_string_replace_node(
        workflow,
        allocator=allocator,
        string_value=[width_replace_id, 0],
        find_value="{height}",
        replace_value=str(request.height),
    )
    generated_prompt_id = _append_text_generate_node(
        workflow,
        allocator=allocator,
        prompt_id=prompt_payload_id,
        clip_source=prompt_enhancer_source,
    )
    prompt_toggle_id = _append_primitive_boolean_node(
        workflow,
        allocator=allocator,
        value=request.prompt_enhancement_enabled,
    )
    selected_prompt_id = _append_switch_node(
        workflow,
        allocator=allocator,
        switch_id=prompt_toggle_id,
        on_false=prompt_text_id,
        on_true=generated_prompt_id,
    )
    positive_id = prompt_conditioning._append_prompt_encode_node(
        workflow,
        allocator=allocator,
        clip_source=main_clip_source,
        text=[selected_prompt_id, 0],
        prompt_encoder="sd15",
    )
    if turbo:
        negative_id = _append_conditioning_zero_out_node(
            workflow,
            allocator=allocator,
            conditioning_id=positive_id,
        )
    else:
        negative_id = prompt_conditioning._append_prompt_encode_node(
            workflow,
            allocator=allocator,
            clip_source=main_clip_source,
            text=request.negative_prompt,
            prompt_encoder="sd15",
        )
    latent_id = _append_empty_latent_node(
        workflow,
        allocator=allocator,
        class_type="EmptyFlux2LatentImage",
        width=request.width,
        height=request.height,
        batch_size=request.batch_size,
    )
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
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
        request=request,
    )
    return workflow


def _build_z_image_workflow_for_profile(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    return _build_z_image_workflow(request, turbo=str(request.profile or "").strip().lower() == "z_image_turbo")


def _build_ernie_workflow_for_profile(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    return _build_ernie_workflow(
        request,
        turbo=str(request.profile or "").strip().lower() == "ernie_image_turbo",
    )


_NON_SD_RUNTIME_BUILDERS: dict[str, Callable[[NormalizedTxt2ImgRequest], dict[str, object]]] = {
    "anima": _build_anima_workflow,
    "flux": _build_flux_workflow,
    "hidream": _build_hidream_workflow,
    "chroma": _build_chroma_workflow,
    "flux2_dev": _build_flux2_dev_workflow,
    "klein": lambda request: _build_klein_workflow(request, distilled=False),
    "klein_distilled": lambda request: _build_klein_workflow(request, distilled=True),
    "qwen_image": _build_qwen_image_workflow,
    "longcat": _build_longcat_workflow,
    "z_image": _build_z_image_workflow_for_profile,
    "ernie": _build_ernie_workflow_for_profile,
}


def _build_qwen_family_image_edit_workflow(request: NormalizedImg2ImgRequest) -> dict[str, object]:
    profile_entry = get_model_family_registry_entry(request.profile)
    encoder_family = str(profile_entry.encoder_family or "").strip().lower()
    if encoder_family == "qwen_image_edit_2511":
        scale_mode = "none"
    else:
        scale_mode = "all" if encoder_family == "qwen_image_edit_plus" else "main_only"
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    references = _build_image_edit_reference_bundle(
        workflow,
        allocator=allocator,
        reference_assets=request.reference_image_assets,
        main_reference_index=request.main_reference_index,
        megapixels=float(request.edit_megapixels or profile_entry.default_edit_megapixels or 1.0),
        scale_mode=scale_mode,
    )
    if encoder_family == "qwen_image_edit_2511":
        scaled_main_image_id = _append_flux_kontext_image_scale_node(
            workflow,
            allocator=allocator,
            image_id=references.main_image_node_id,
        )
        reference_image_node_ids = tuple(
            scaled_main_image_id if index == references.main_reference_index else image_node_id
            for index, image_node_id in enumerate(references.image_node_ids)
        )
        latent_image_node_id = scaled_main_image_id
    else:
        reference_image_node_ids = references.image_node_ids
        latent_image_node_id = references.main_image_node_id
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    clip_source = _build_single_clip_source(
        workflow,
        allocator=allocator,
        clip_name=request.text_encoder_name,
        clip_type="qwen_image",
    )
    positive_id, negative_id = _build_qwen_family_conditioning_nodes(
        workflow,
        allocator=allocator,
        request=request,
        profile_entry=profile_entry,
        clip_source=clip_source,
        vae_source=[vae_id, 0],
        reference_image_node_ids=reference_image_node_ids,
        main_image_node_id=latent_image_node_id,
    )
    latent_id = _append_vae_encode_node(
        workflow,
        allocator=allocator,
        image_id=latent_image_node_id,
        vae_source=[vae_id, 0],
    )
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    model_source = _append_model_only_lora_chain(
        workflow,
        allocator=allocator,
        model_source=[unet_id, 0],
        template_lora_names=_resolve_template_owned_lora_chain_names(
            request.template_lora_name,
            chain_mode=profile_entry.template_lora_chain_mode,
        ),
        inline_lora_activations=request.lora_activations,
    )
    model_source = _append_model_sampling_node(
        workflow,
        allocator=allocator,
        class_type="ModelSamplingAuraFlow",
        model_source=model_source,
        shift=float(request.shift or 0.0),
    )
    model_source = _append_cfg_norm_node(
        workflow,
        allocator=allocator,
        model_source=model_source,
    )
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
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
        request=request,
    )
    return workflow


def _build_flux_kontext_dev_image_edit_workflow(request: NormalizedImg2ImgRequest) -> dict[str, object]:
    profile_entry = get_model_family_registry_entry(request.profile)
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    references = _build_image_edit_reference_bundle(
        workflow,
        allocator=allocator,
        reference_assets=request.reference_image_assets,
        main_reference_index=request.main_reference_index,
        scale_mode="none",
    )
    stitched_reference_ids = (references.main_image_node_id,) + tuple(
        image_node_id
        for index, image_node_id in enumerate(references.image_node_ids)
        if index != references.main_reference_index
    )
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    kontext_reference = _build_flux_kontext_reference_bundle(
        workflow,
        allocator=allocator,
        image_node_ids=stitched_reference_ids,
        vae_source=[vae_id, 0],
    )
    encoder_values = _normalize_encoder_selector_values(request.text_encoder_name)
    if len(encoder_values) != 2:
        raise ValueError("Flux Kontext image-edit profile requires two ordered text encoders.")
    clip_source = _build_flux_dual_clip_source(
        workflow,
        allocator=allocator,
        clip_name_1=encoder_values[0],
        clip_name_2=encoder_values[1],
    )
    positive_id = prompt_conditioning._append_prompt_encode_node(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        text=request.prompt,
        prompt_encoder="sd15",
    )
    negative_id = _append_conditioning_zero_out_node(
        workflow,
        allocator=allocator,
        conditioning_id=positive_id,
    )
    positive_id = _append_reference_latent_chain(
        workflow,
        allocator=allocator,
        conditioning_source=positive_id,
        latent_node_ids=(kontext_reference.latent_node_id,),
    )
    positive_id = _append_flux_guidance_node(
        workflow,
        allocator=allocator,
        conditioning_id=positive_id,
        guidance=float(request.flux_guidance or profile_entry.default_flux_guidance or 0.0),
    )
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    model_source = _append_model_only_lora_chain(
        workflow,
        allocator=allocator,
        model_source=[unet_id, 0],
        inline_lora_activations=request.lora_activations,
    )
    sampler_id = allocator.next()
    _build_sampler_node(
        workflow,
        node_id=sampler_id,
        positive_id=positive_id,
        negative_id=negative_id,
        latent_id=kontext_reference.latent_node_id,
        request=request,
        denoise=1.0,
        model_source=model_source,
    )
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
        request=request,
    )
    return workflow


def _build_flux2_image_edit_workflow(request: NormalizedImg2ImgRequest) -> dict[str, object]:
    profile_entry = get_model_family_registry_entry(request.profile)
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    references = _build_image_edit_reference_bundle(
        workflow,
        allocator=allocator,
        reference_assets=request.reference_image_assets,
        main_reference_index=request.main_reference_index,
        megapixels=float(request.edit_megapixels or profile_entry.default_edit_megapixels or 1.0),
        scale_mode="main_only",
    )
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    clip_source = _build_single_clip_source(
        workflow,
        allocator=allocator,
        clip_name=request.text_encoder_name,
        clip_type="flux2",
    )
    positive_id = prompt_conditioning._append_prompt_encode_node(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        text=request.prompt,
        prompt_encoder="sd15",
    )
    positive_id = _append_flux_guidance_node(
        workflow,
        allocator=allocator,
        conditioning_id=positive_id,
        guidance=float(request.flux_guidance or profile_entry.default_flux_guidance or 0.0),
    )
    reference_latent_id = _append_vae_encode_node(
        workflow,
        allocator=allocator,
        image_id=references.main_image_node_id,
        vae_source=[vae_id, 0],
    )
    positive_id = _append_reference_latent_chain(
        workflow,
        allocator=allocator,
        conditioning_source=positive_id,
        latent_node_ids=(reference_latent_id,),
    )
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    model_source = _append_model_only_lora_chain(
        workflow,
        allocator=allocator,
        model_source=[unet_id, 0],
        inline_lora_activations=request.lora_activations,
    )
    sampler_bundle = _append_flux2_advanced_sampler_bundle(
        workflow,
        allocator=allocator,
        model_source=model_source,
        size_image_id=references.main_image_node_id,
        positive_conditioning_source=positive_id,
        steps=request.steps,
        sampler_name=request.sampler_name,
        noise_seed=request.execution_seed,
        batch_size=request.batch_size,
    )
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_bundle.sampler_node_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
        request=request,
    )
    return workflow


def _build_klein_9b_kv_image_edit_workflow(request: NormalizedImg2ImgRequest) -> dict[str, object]:
    profile_entry = get_model_family_registry_entry(request.profile)
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    references = _build_image_edit_reference_bundle(
        workflow,
        allocator=allocator,
        reference_assets=request.reference_image_assets,
        main_reference_index=request.main_reference_index,
        megapixels=float(request.edit_megapixels or profile_entry.default_edit_megapixels or 1.0),
        scale_mode="all",
    )
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    clip_source = _build_single_clip_source(
        workflow,
        allocator=allocator,
        clip_name=request.text_encoder_name,
        clip_type="flux2",
    )
    positive_id = prompt_conditioning._append_prompt_encode_node(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        text=request.prompt,
        prompt_encoder="sd15",
    )
    negative_id = _append_conditioning_zero_out_node(
        workflow,
        allocator=allocator,
        conditioning_id=positive_id,
    )
    reference_latent_ids = _append_reference_vae_latents(
        workflow,
        allocator=allocator,
        image_node_ids=references.image_node_ids,
        vae_source=[vae_id, 0],
    )
    positive_id, negative_id = _append_mirrored_reference_latent_chains(
        workflow,
        allocator=allocator,
        positive_conditioning_source=positive_id,
        negative_conditioning_source=negative_id,
        latent_node_ids=reference_latent_ids,
    )
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    model_source = _append_model_only_lora_chain(
        workflow,
        allocator=allocator,
        model_source=[unet_id, 0],
        inline_lora_activations=request.lora_activations,
    )
    model_source = _append_flux_kv_cache_node(
        workflow,
        allocator=allocator,
        model_source=model_source,
    )
    sampler_bundle = _append_flux2_advanced_sampler_bundle(
        workflow,
        allocator=allocator,
        model_source=model_source,
        size_image_id=references.main_image_node_id,
        positive_conditioning_source=positive_id,
        negative_conditioning_source=negative_id,
        cfg_scale=request.cfg_scale,
        steps=request.steps,
        sampler_name=request.sampler_name,
        noise_seed=request.execution_seed,
        batch_size=request.batch_size,
    )
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_bundle.sampler_node_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
        request=request,
    )
    return workflow


def _build_longcat_image_edit_workflow(request: NormalizedImg2ImgRequest) -> dict[str, object]:
    profile_entry = get_model_family_registry_entry(request.profile)
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    references = _build_image_edit_reference_bundle(
        workflow,
        allocator=allocator,
        reference_assets=request.reference_image_assets,
        main_reference_index=request.main_reference_index,
        megapixels=float(request.edit_megapixels or profile_entry.default_edit_megapixels or 1.0),
        scale_mode="main_only",
        resolution_steps=16,
    )
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    clip_source = _build_single_clip_source(
        workflow,
        allocator=allocator,
        clip_name=request.text_encoder_name,
        clip_type="longcat_image",
    )
    positive_id = _append_qwen_image_edit_encode_node(
        workflow,
        allocator=allocator,
        prompt_text=request.prompt,
        clip_source=clip_source,
        vae_source=[vae_id, 0],
        image_id=references.main_image_node_id,
    )
    negative_id = _append_qwen_image_edit_encode_node(
        workflow,
        allocator=allocator,
        prompt_text=request.negative_prompt,
        clip_source=clip_source,
        vae_source=[vae_id, 0],
        image_id=references.main_image_node_id,
    )
    guidance = float(request.flux_guidance or profile_entry.default_flux_guidance or 0.0)
    positive_id = _append_flux_reference_method_branch(
        workflow,
        allocator=allocator,
        conditioning_source=positive_id,
        guidance=guidance,
        reference_method="index",
    )
    negative_id = _append_flux_reference_method_branch(
        workflow,
        allocator=allocator,
        conditioning_source=negative_id,
        guidance=guidance,
        reference_method="index",
    )
    latent_id = _append_vae_encode_node(
        workflow,
        allocator=allocator,
        image_id=references.main_image_node_id,
        vae_source=[vae_id, 0],
    )
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    model_source = _append_model_only_lora_chain(
        workflow,
        allocator=allocator,
        model_source=[unet_id, 0],
        inline_lora_activations=request.lora_activations,
    )
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
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
        request=request,
    )
    return workflow


_NON_SD_EDIT_RUNTIME_BUILDERS: dict[str, Callable[[NormalizedImg2ImgRequest], dict[str, object]]] = {
    "qwen_image_edit": _build_qwen_family_image_edit_workflow,
    "flux_kontext_dev_edit": _build_flux_kontext_dev_image_edit_workflow,
    "flux2_image_edit": _build_flux2_image_edit_workflow,
    "klein_9b_kv_image_edit": _build_klein_9b_kv_image_edit_workflow,
    "longcat_image_edit": _build_longcat_image_edit_workflow,
}


def build_non_sd_txt2img_workflow(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    profile_id = str(request.profile or "").strip().lower()
    adapter_id = _NON_SD_RUNTIME_ADAPTER_BY_PROFILE.get(profile_id, "")
    builder = _NON_SD_RUNTIME_BUILDERS.get(adapter_id)
    if builder is None:
        raise ValueError(f"Unsupported official non-SD txt2img profile: {request.profile}")
    return builder(request)


def build_non_sd_edit_workflow(request: NormalizedImg2ImgRequest) -> dict[str, object]:
    profile_id = str(request.profile or "").strip().lower()
    adapter_id = _NON_SD_RUNTIME_ADAPTER_BY_PROFILE.get(profile_id, "")
    builder = _NON_SD_EDIT_RUNTIME_BUILDERS.get(adapter_id)
    if builder is not None:
        return builder(request)
    raise ValueError(f"Unsupported official non-SD edit profile: {request.profile}")
