from __future__ import annotations

from rookieui.contracts.generation import NormalizedTxt2ImgRequest
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
from rookieui.services.workflow_builders.output import _build_decode_and_save
from rookieui.services.workflow_builders import prompt_conditioning

_ERNIE_PROMPT_ENHANCER_TEMPLATE = (
    '<s>[SYSTEM_PROMPT]你是一个专业的文生图 Prompt 增强助手。你将收到用户的简短图片描述及目标生成分辨率，'
    "请据此扩写为一段内容丰富、细节充分的视觉描述，以帮助文生图模型生成高质量的图片。仅输出增强后的描述，"
    '不要包含任何解释或前缀。[/SYSTEM_PROMPT][INST]{"prompt": "{prompt}", "width": {width}, "height": {height}}[/INST]'
)
_QWEN_TEMPLATE_LORA_NAME = "Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors"


def is_official_non_sd_txt2img_profile(profile_id: str) -> bool:
    return str(profile_id or "").strip().lower() in {
        "anima",
        "chroma",
        "ernie_image",
        "ernie_image_turbo",
        "flux",
        "hidream_i1_dev_fp8",
        "hidream_i1_fast",
        "hidream_i1_full",
        "klein_4b_distilled",
        "klein_4b",
        "klein_9b_distilled",
        "klein_9b",
        "longcat_image",
        "qwen_image",
        "z_image",
        "z_image_turbo",
    }


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
        model_source=[unet_id, 0],
    )
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
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
        model_source=[unet_id, 0],
    )
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
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
    clip_source = _build_hidream_quad_clip_source(workflow, allocator=allocator, clip_names=encoder_values)
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    model_source = _append_model_sampling_node(
        workflow,
        allocator=allocator,
        class_type="ModelSamplingSD3",
        model_source=[unet_id, 0],
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
    )
    return workflow


def _build_chroma_workflow(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
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
        model_source=[unet_id, 0],
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
    )
    return workflow


def _build_klein_workflow(request: NormalizedTxt2ImgRequest, *, distilled: bool) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
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
        model_source=[unet_id, 0],
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
    )
    return workflow


def _build_qwen_image_workflow(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    clip_source = _build_single_clip_source(
        workflow,
        allocator=allocator,
        clip_name=request.text_encoder_name,
        clip_type="qwen_image",
    )
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    model_source = _append_lora_loader_model_only_node(
        workflow,
        allocator=allocator,
        model_source=[unet_id, 0],
        lora_name=request.template_lora_name or _QWEN_TEMPLATE_LORA_NAME,
    )
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
    )
    return workflow


def _build_z_image_workflow(request: NormalizedTxt2ImgRequest, *, turbo: bool) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
    clip_source = _build_single_clip_source(
        workflow,
        allocator=allocator,
        clip_name=request.text_encoder_name,
        clip_type="lumina2",
    )
    vae_id = allocator.next()
    workflow[vae_id] = _build_vae_loader_node(request.vae_name)
    model_source = _append_model_sampling_node(
        workflow,
        allocator=allocator,
        class_type="ModelSamplingAuraFlow",
        model_source=[unet_id, 0],
        shift=float(request.shift or 0.0),
    )
    positive_id, negative_id = _build_basic_positive_negative(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        request=request,
        negative_mode="zero_out" if turbo else "encode",
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
    )
    return workflow


def _build_longcat_workflow(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
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
        model_source=[unet_id, 0],
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
    )
    return workflow


def _build_ernie_workflow(request: NormalizedTxt2ImgRequest, *, turbo: bool) -> dict[str, object]:
    allocator = NodeIdAllocator(start=1)
    workflow: dict[str, object] = {}
    if not request.aux_text_encoder_name:
        raise ValueError(f"Profile '{request.profile}' requires an auxiliary prompt-enhancer text encoder.")
    unet_id = allocator.next()
    workflow[unet_id] = _build_unet_loader_node(request.checkpoint_name)
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
        model_source=[unet_id, 0],
    )
    decode_id = allocator.next()
    save_id = allocator.next()
    _build_decode_and_save(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        save_id=save_id,
        vae_source=[vae_id, 0],
    )
    return workflow


def build_non_sd_txt2img_workflow(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    profile_id = str(request.profile or "").strip().lower()
    if profile_id == "anima":
        return _build_anima_workflow(request)
    if profile_id == "flux":
        return _build_flux_workflow(request)
    if profile_id == "chroma":
        return _build_chroma_workflow(request)
    if profile_id in {"klein_4b_distilled", "klein_9b_distilled"}:
        return _build_klein_workflow(request, distilled=True)
    if profile_id in {"klein_4b", "klein_9b"}:
        return _build_klein_workflow(request, distilled=False)
    if profile_id == "qwen_image":
        return _build_qwen_image_workflow(request)
    if profile_id == "longcat_image":
        return _build_longcat_workflow(request)
    if profile_id == "z_image":
        return _build_z_image_workflow(request, turbo=False)
    if profile_id == "z_image_turbo":
        return _build_z_image_workflow(request, turbo=True)
    if profile_id == "ernie_image":
        return _build_ernie_workflow(request, turbo=False)
    if profile_id == "ernie_image_turbo":
        return _build_ernie_workflow(request, turbo=True)
    if profile_id in {"hidream_i1_dev_fp8", "hidream_i1_fast", "hidream_i1_full"}:
        return _build_hidream_workflow(request)
    raise ValueError(f"Unsupported official non-SD txt2img profile: {request.profile}")
