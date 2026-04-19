from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from rookieui.contracts.adetailer import NormalizedADetailerRequest
from rookieui.contracts.controlnet import NormalizedControlNetUnit
from rookieui.contracts.prompt_dsl import PromptLoraActivation


@dataclass(frozen=True)
class Txt2ImgRequest:
    prompt: str
    negative_prompt: str = ""
    profile: str = "sd15"
    dtype_profile: str | None = None
    lora_name: str | None = None
    lora_strength_model: float = 1.0
    lora_strength_clip: float = 1.0
    checkpoint_name: str = "__host_default__"
    vae_name: str = "Automatic"
    text_encoder_name: str = "Automatic"
    template_lora_name: str | None = None
    width: int | None = None
    height: int | None = None
    steps: int | None = None
    cfg_scale: float | None = None
    shift: float | None = None
    flux_guidance: float | None = None
    sampler_name: str | None = None
    scheduler_name: str | None = None
    prompt_enhancement_enabled: bool | None = None
    seed: int = -1
    seed_extra: bool = False
    batch_size: int = 1
    batch_count: int = 1
    clip_skip: int | None = None
    hires_enabled: bool = False
    hires_scale: float = 1.5
    hires_steps: int | None = None
    hires_denoise: float = 0.35
    hires_upscale_method: str = "bislerp"
    adetailer: dict[str, Any] = field(default_factory=dict)
    controlnet_units: list[dict[str, Any]] = field(default_factory=list)
    alwayson_scripts: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Img2ImgRequest:
    prompt: str
    negative_prompt: str = ""
    profile: str = "sd15"
    dtype_profile: str | None = None
    lora_name: str | None = None
    lora_strength_model: float = 1.0
    lora_strength_clip: float = 1.0
    checkpoint_name: str = "__host_default__"
    vae_name: str = "Automatic"
    text_encoder_name: str = "Automatic"
    template_lora_name: str | None = None
    image_asset: str = ""
    image_data: str = ""
    mask_asset: str = ""
    mask_data: str = ""
    mode: str = "img2img"
    batch_images: list[str] = field(default_factory=list)
    width: int | None = None
    height: int | None = None
    resize_mode: str = "crop_and_resize"
    steps: int | None = None
    cfg_scale: float | None = None
    shift: float | None = None
    flux_guidance: float | None = None
    edit_megapixels: float | None = None
    sampler_name: str | None = None
    scheduler_name: str | None = None
    prompt_enhancement_enabled: bool | None = None
    seed: int = -1
    seed_extra: bool = False
    batch_size: int = 1
    clip_skip: int | None = None
    denoise_strength: float = 0.75
    grow_mask_by: int = 6
    mask_blur: int = 4
    inpaint_mask_mode: str = "inpaint_masked"
    inpaint_masked_content: str = "original"
    inpaint_area: str = "only_masked"
    inpaint_padding: int = 32
    soft_inpainting_enabled: bool = False
    soft_inpainting_schedule_bias: float = 1.0
    soft_inpainting_preservation_strength: float = 0.5
    soft_inpainting_transition_contrast_boost: float = 4.0
    soft_inpainting_mask_influence: float = 0.0
    soft_inpainting_difference_threshold: float = 0.5
    soft_inpainting_difference_contrast: float = 2.0
    hires_enabled: bool = False
    hires_scale: float = 1.5
    hires_steps: int | None = None
    hires_denoise: float = 0.35
    hires_upscale_method: str = "bislerp"
    adetailer: dict[str, Any] = field(default_factory=dict)
    controlnet_units: list[dict[str, Any]] = field(default_factory=list)
    alwayson_scripts: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedTxt2ImgRequest:
    prompt: str
    negative_prompt: str
    profile: str
    base_family: str
    primary_model_category: str
    prompt_encoder: str
    dtype_profile: str
    lora_name: str
    lora_strength_model: float
    lora_strength_clip: float
    checkpoint_name: str
    vae_name: str
    text_encoder_name: str
    aux_text_encoder_name: str
    template_lora_name: str
    width: int
    height: int
    steps: int
    cfg_scale: float
    shift: float | None
    flux_guidance: float | None
    sampler_name: str
    scheduler_name: str
    prompt_enhancement_enabled: bool
    seed: int
    execution_seed: int
    seed_extra: bool
    batch_size: int
    batch_count: int
    clip_skip: int
    hires_enabled: bool
    hires_scale: float
    hires_steps: int
    hires_denoise: float
    hires_upscale_method: str
    adetailer: NormalizedADetailerRequest = field(default_factory=NormalizedADetailerRequest)
    lora_activations: list[PromptLoraActivation] = field(default_factory=list)
    prompt_warnings: list[str] = field(default_factory=list)
    prompt_warning_codes: list[str] = field(default_factory=list)
    controlnet_units: list[NormalizedControlNetUnit] = field(default_factory=list)
    controlnet_warnings: list[str] = field(default_factory=list)
    controlnet_warning_codes: list[str] = field(default_factory=list)
    prompt_semantics: dict[str, Any] = field(default_factory=dict)
    negative_prompt_semantics: dict[str, Any] = field(default_factory=dict)
    applied_defaults: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedImg2ImgRequest:
    prompt: str
    negative_prompt: str
    profile: str
    base_family: str
    primary_model_category: str
    prompt_encoder: str
    dtype_profile: str
    lora_name: str
    lora_strength_model: float
    lora_strength_clip: float
    checkpoint_name: str
    vae_name: str
    text_encoder_name: str
    aux_text_encoder_name: str
    template_lora_name: str
    image_asset: str
    mask_asset: str
    mode: str
    execution_mode: str
    batch_images: list[str]
    width: int
    height: int
    resize_mode: str
    steps: int
    cfg_scale: float
    shift: float | None
    flux_guidance: float | None
    edit_megapixels: float | None
    sampler_name: str
    scheduler_name: str
    prompt_enhancement_enabled: bool
    seed: int
    execution_seed: int
    seed_extra: bool
    batch_size: int
    clip_skip: int
    denoise_strength: float
    grow_mask_by: int
    mask_blur: int
    inpaint_mask_mode: str
    inpaint_masked_content: str
    inpaint_area: str
    inpaint_padding: int
    soft_inpainting_enabled: bool
    soft_inpainting_schedule_bias: float
    soft_inpainting_preservation_strength: float
    soft_inpainting_transition_contrast_boost: float
    soft_inpainting_mask_influence: float
    soft_inpainting_difference_threshold: float
    soft_inpainting_difference_contrast: float
    hires_enabled: bool
    hires_scale: float
    hires_steps: int
    hires_denoise: float
    hires_upscale_method: str
    adetailer: NormalizedADetailerRequest = field(default_factory=NormalizedADetailerRequest)
    lora_activations: list[PromptLoraActivation] = field(default_factory=list)
    prompt_warnings: list[str] = field(default_factory=list)
    prompt_warning_codes: list[str] = field(default_factory=list)
    controlnet_units: list[NormalizedControlNetUnit] = field(default_factory=list)
    controlnet_warnings: list[str] = field(default_factory=list)
    controlnet_warning_codes: list[str] = field(default_factory=list)
    prompt_semantics: dict[str, Any] = field(default_factory=dict)
    negative_prompt_semantics: dict[str, Any] = field(default_factory=dict)
    applied_defaults: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkflowTranslationResult:
    mode: str
    workflow_kind: str
    profile: str
    normalized_request: dict[str, Any]
    parity_profile: dict[str, Any]
    sampler_aliases: dict[str, Any]
    workflow: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)
