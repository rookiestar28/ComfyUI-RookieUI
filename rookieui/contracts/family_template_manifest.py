from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MODEL_FAMILY_REGISTRY_CONTRACT_VERSION = "f168-20260423"
OFFICIAL_TEMPLATE_SOURCE_PACKAGE = "comfyui-workflow-templates"
OFFICIAL_TEMPLATE_SOURCE_VERSION = "0.9.98"


@dataclass(frozen=True)
class FamilyTemplateManifestEntry:
    id: str
    title: str
    translation_base_family: str
    public_base_family: str
    prompt_encoder: str
    default_width: int
    default_height: int
    default_steps: int
    default_cfg_scale: float
    default_sampler: str
    default_scheduler: str
    default_clip_skip: int
    supports_clip_skip: bool
    primary_model_category: str
    text_encoder_visible: bool
    shift_visible: bool
    default_shift: float | None
    flux_guidance_visible: bool
    default_flux_guidance: float | None
    prompt_enhancement_visible: bool
    default_prompt_enhancement_enabled: bool
    edit_megapixels_visible: bool
    default_edit_megapixels: float | None
    template_lora_visible: bool
    template_lora_override_allowed: bool
    official_template_lora_label: str
    support_tier: str
    compatibility_summary: str
    experimental: bool = False
    aliases: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)
    image_edit_profile: bool = False
    request_contract_surface: str = ""
    reference_input_mode: str = "none"
    max_direct_references: int = 0
    encoder_family: str = ""
    template_lora_chain_mode: str = "none"
    flow_kind: str = "txt2img"
    available_surface_flows: tuple[str, ...] = ("txt2img", "img2img")
    runtime_adapter_id: str = ""
    official_template_path: str = ""
    diffusion_model_hints: tuple[str, ...] = ()
    diffusion_model_priority_hints: tuple[tuple[str, ...], ...] = ()
    diffusion_model_deny_hints: tuple[str, ...] = ()
    text_encoder_hints: tuple[str, ...] = ()
    text_encoder_priority_hints: tuple[tuple[str, ...], ...] = ()
    text_encoder_sequence_priority_hints: tuple[tuple[tuple[str, ...], ...], ...] = ()
    aux_text_encoder_priority_hints: tuple[tuple[str, ...], ...] = ()
    template_lora_priority_hints: tuple[tuple[str, ...], ...] = ()
    vae_hints: tuple[str, ...] = ()
    vae_priority_hints: tuple[tuple[str, ...], ...] = ()
    vae_deny_hints: tuple[str, ...] = ()

    def to_registry_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "translation_base_family": self.translation_base_family,
            "public_base_family": self.public_base_family,
            "prompt_encoder": self.prompt_encoder,
            "default_width": self.default_width,
            "default_height": self.default_height,
            "default_steps": self.default_steps,
            "default_cfg_scale": self.default_cfg_scale,
            "default_sampler": self.default_sampler,
            "default_scheduler": self.default_scheduler,
            "default_clip_skip": self.default_clip_skip,
            "supports_clip_skip": self.supports_clip_skip,
            "primary_model_category": self.primary_model_category,
            "text_encoder_visible": self.text_encoder_visible,
            "shift_visible": self.shift_visible,
            "default_shift": self.default_shift,
            "flux_guidance_visible": self.flux_guidance_visible,
            "default_flux_guidance": self.default_flux_guidance,
            "prompt_enhancement_visible": self.prompt_enhancement_visible,
            "default_prompt_enhancement_enabled": self.default_prompt_enhancement_enabled,
            "edit_megapixels_visible": self.edit_megapixels_visible,
            "default_edit_megapixels": self.default_edit_megapixels,
            "template_lora_visible": self.template_lora_visible,
            "template_lora_override_allowed": self.template_lora_override_allowed,
            "official_template_lora_label": self.official_template_lora_label,
            "support_tier": self.support_tier,
            "compatibility_summary": self.compatibility_summary,
            "experimental": self.experimental,
            "aliases": list(self.aliases),
            "notes": list(self.notes),
            "image_edit_profile": self.image_edit_profile,
            "request_contract_surface": self.request_contract_surface,
            "reference_input_mode": self.reference_input_mode,
            "max_direct_references": self.max_direct_references,
            "encoder_family": self.encoder_family,
            "template_lora_chain_mode": self.template_lora_chain_mode,
            "available_surface_flows": list(self.available_surface_flows),
        }

    def to_preset_payload(
        self,
        *,
        checkpoint_name: str,
        vae_name: str,
        text_encoder_name: str,
        template_lora_name: str,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": "SD1.5" if self.id == "sd15" else ("SDXL" if self.id == "sdxl" else self.title),
            "profile": self.id,
            "base_family": self.public_base_family,
            "checkpoint_name": checkpoint_name,
            "vae_name": vae_name,
            "text_encoder_name": text_encoder_name,
            "template_lora_name": template_lora_name,
            "width": self.default_width,
            "height": self.default_height,
            "steps": self.default_steps,
            "cfg_scale": self.default_cfg_scale,
            "shift": self.default_shift,
            "flux_guidance": self.default_flux_guidance,
            "sampler_name": self.default_sampler,
            "scheduler_name": self.default_scheduler,
            "clip_skip": self.default_clip_skip,
            "prompt_enhancement_enabled": self.default_prompt_enhancement_enabled,
            "edit_megapixels": self.default_edit_megapixels,
            "image_edit_profile": self.image_edit_profile,
            "request_contract_surface": self.request_contract_surface,
            "reference_input_mode": self.reference_input_mode,
            "max_direct_references": self.max_direct_references,
            "encoder_family": self.encoder_family,
            "template_lora_chain_mode": self.template_lora_chain_mode,
        }


def _parity_entry(
    *,
    id: str,
    title: str,
    translation_base_family: str,
    default_width: int,
    default_height: int,
    default_steps: int,
    default_cfg_scale: float,
    default_sampler: str,
    default_scheduler: str,
    default_clip_skip: int,
    supports_clip_skip: bool,
    compatibility_summary: str,
    notes: tuple[str, ...],
) -> FamilyTemplateManifestEntry:
    prompt_encoder = "clip_text_encode" if translation_base_family == "sd15" else "clip_text_encode_sdxl"
    return FamilyTemplateManifestEntry(
        id=id,
        title=title,
        translation_base_family=translation_base_family,
        public_base_family=translation_base_family,
        prompt_encoder=prompt_encoder,
        default_width=default_width,
        default_height=default_height,
        default_steps=default_steps,
        default_cfg_scale=default_cfg_scale,
        default_sampler=default_sampler,
        default_scheduler=default_scheduler,
        default_clip_skip=default_clip_skip,
        supports_clip_skip=supports_clip_skip,
        primary_model_category="checkpoints",
        text_encoder_visible=False,
        shift_visible=False,
        default_shift=None,
        flux_guidance_visible=False,
        default_flux_guidance=None,
        prompt_enhancement_visible=False,
        default_prompt_enhancement_enabled=False,
        edit_megapixels_visible=False,
        default_edit_megapixels=None,
        template_lora_visible=False,
        template_lora_override_allowed=False,
        official_template_lora_label="",
        support_tier="parity",
        compatibility_summary=compatibility_summary,
        notes=notes,
    )


def _template_entry(
    *,
    id: str,
    title: str,
    public_base_family: str,
    default_width: int,
    default_height: int,
    default_steps: int,
    default_cfg_scale: float,
    default_sampler: str,
    default_scheduler: str,
    compatibility_summary: str,
    aliases: tuple[str, ...] = (),
    notes: tuple[str, ...] = (),
    image_edit_profile: bool = False,
    request_contract_surface: str = "",
    reference_input_mode: str = "none",
    max_direct_references: int = 0,
    encoder_family: str = "",
    template_lora_chain_mode: str = "none",
    shift_visible: bool = False,
    default_shift: float | None = None,
    flux_guidance_visible: bool = False,
    default_flux_guidance: float | None = None,
    prompt_enhancement_visible: bool = False,
    default_prompt_enhancement_enabled: bool = False,
    edit_megapixels_visible: bool = False,
    default_edit_megapixels: float | None = None,
    template_lora_visible: bool = False,
    template_lora_override_allowed: bool = False,
    official_template_lora_label: str = "",
    flow_kind: str = "txt2img",
    available_surface_flows: tuple[str, ...] = ("txt2img",),
    runtime_adapter_id: str = "",
    official_template_path: str = "",
    diffusion_model_hints: tuple[str, ...] = (),
    diffusion_model_priority_hints: tuple[tuple[str, ...], ...] = (),
    diffusion_model_deny_hints: tuple[str, ...] = (),
    text_encoder_hints: tuple[str, ...] = (),
    text_encoder_priority_hints: tuple[tuple[str, ...], ...] = (),
    text_encoder_sequence_priority_hints: tuple[tuple[tuple[str, ...], ...], ...] = (),
    aux_text_encoder_priority_hints: tuple[tuple[str, ...], ...] = (),
    template_lora_priority_hints: tuple[tuple[str, ...], ...] = (),
    vae_hints: tuple[str, ...] = (),
    vae_priority_hints: tuple[tuple[str, ...], ...] = (),
    vae_deny_hints: tuple[str, ...] = (),
) -> FamilyTemplateManifestEntry:
    return FamilyTemplateManifestEntry(
        id=id,
        title=title,
        translation_base_family="sdxl",
        public_base_family=public_base_family,
        prompt_encoder="clip_text_encode_sdxl",
        default_width=default_width,
        default_height=default_height,
        default_steps=default_steps,
        default_cfg_scale=default_cfg_scale,
        default_sampler=default_sampler,
        default_scheduler=default_scheduler,
        default_clip_skip=1,
        supports_clip_skip=False,
        primary_model_category="diffusion_models",
        text_encoder_visible=False,
        shift_visible=shift_visible,
        default_shift=default_shift,
        flux_guidance_visible=flux_guidance_visible,
        default_flux_guidance=default_flux_guidance,
        prompt_enhancement_visible=prompt_enhancement_visible,
        default_prompt_enhancement_enabled=default_prompt_enhancement_enabled,
        edit_megapixels_visible=edit_megapixels_visible,
        default_edit_megapixels=default_edit_megapixels,
        template_lora_visible=template_lora_visible,
        template_lora_override_allowed=template_lora_override_allowed,
        official_template_lora_label=official_template_lora_label,
        support_tier="family-adapted",
        compatibility_summary=compatibility_summary,
        experimental=True,
        aliases=aliases,
        notes=notes,
        image_edit_profile=image_edit_profile,
        request_contract_surface=request_contract_surface,
        reference_input_mode=reference_input_mode,
        max_direct_references=max_direct_references,
        encoder_family=encoder_family,
        template_lora_chain_mode=template_lora_chain_mode,
        flow_kind=flow_kind,
        available_surface_flows=available_surface_flows,
        runtime_adapter_id=runtime_adapter_id,
        official_template_path=official_template_path,
        diffusion_model_hints=diffusion_model_hints,
        diffusion_model_priority_hints=diffusion_model_priority_hints,
        diffusion_model_deny_hints=diffusion_model_deny_hints,
        text_encoder_hints=text_encoder_hints,
        text_encoder_priority_hints=text_encoder_priority_hints,
        text_encoder_sequence_priority_hints=text_encoder_sequence_priority_hints,
        aux_text_encoder_priority_hints=aux_text_encoder_priority_hints,
        template_lora_priority_hints=template_lora_priority_hints,
        vae_hints=vae_hints,
        vae_priority_hints=vae_priority_hints,
        vae_deny_hints=vae_deny_hints,
    )


_MANIFEST_ENTRIES: tuple[FamilyTemplateManifestEntry, ...] = (
    _parity_entry(
        id="sd15",
        title="Stable Diffusion 1.5",
        translation_base_family="sd15",
        default_width=512,
        default_height=512,
        default_steps=28,
        default_cfg_scale=7.0,
        default_sampler="euler_ancestral",
        default_scheduler="normal",
        default_clip_skip=1,
        supports_clip_skip=True,
        compatibility_summary="Primary A1111 parity baseline for classic Stable Diffusion checkpoints.",
        notes=(
            "Primary A1111 baseline for classic Stable Diffusion checkpoints.",
            "Uses standard CLIP text encoding and optional clip-skip projection.",
        ),
    ),
    _parity_entry(
        id="sdxl",
        title="Stable Diffusion XL",
        translation_base_family="sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=28,
        default_cfg_scale=7.0,
        default_sampler="dpmpp_2m",
        default_scheduler="karras",
        default_clip_skip=1,
        supports_clip_skip=False,
        compatibility_summary="Primary SDXL parity baseline with dual-text-encoder semantics.",
        notes=(
            "Uses SDXL dual-text-encoder semantics through CLIPTextEncodeSDXL.",
            "Acts as the baseline for SDXL-derived families in RookieUI parity lanes.",
        ),
    ),
    _parity_entry(
        id="pony",
        title="Pony",
        translation_base_family="sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=28,
        default_cfg_scale=7.0,
        default_sampler="dpmpp_2m",
        default_scheduler="karras",
        default_clip_skip=1,
        supports_clip_skip=False,
        compatibility_summary="SDXL-derived parity lane with preserved Pony-facing defaults.",
        notes=("SDXL-derived parity lane with community-oriented defaults preserved as SDXL translation.",),
    ),
    _parity_entry(
        id="illustrious",
        title="Illustrious",
        translation_base_family="sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=28,
        default_cfg_scale=7.0,
        default_sampler="dpmpp_2m",
        default_scheduler="karras",
        default_clip_skip=1,
        supports_clip_skip=False,
        compatibility_summary="SDXL-derived parity lane retained as an explicit profile.",
        notes=("SDXL-derived parity lane retained as an explicit profile for A1111-style UX.",),
    ),
    _parity_entry(
        id="noob",
        title="Noob",
        translation_base_family="sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=28,
        default_cfg_scale=7.0,
        default_sampler="dpmpp_2m",
        default_scheduler="karras",
        default_clip_skip=1,
        supports_clip_skip=False,
        compatibility_summary="SDXL-derived parity lane retained for rookie-safe defaults.",
        notes=("SDXL-derived parity lane retained as an explicit profile for rookie-safe defaults.",),
    ),
    _template_entry(
        id="anima",
        title="Anima",
        public_base_family="anima",
        default_width=1024,
        default_height=1024,
        default_steps=30,
        default_cfg_scale=4.0,
        default_sampler="er_sde",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI Anima template preset routed through the non-SD template seam.",
        aliases=("anima preview3",),
        notes=(
            "Matches the official Anima text-to-image template defaults.",
            "Text Encoder selector stays hidden because the official template owns the fixed qwen_3_06b pairing.",
        ),
        runtime_adapter_id="anima",
        official_template_path="reference/ComfyUI/blueprints/Text to Image (Anima).json",
        diffusion_model_hints=("anima",),
        diffusion_model_priority_hints=(("anima",),),
        text_encoder_hints=("anima",),
        text_encoder_priority_hints=(("qwen_3_06b",), ("anima",), ("qwen",)),
        vae_hints=("anima",),
        vae_priority_hints=(("qwen_image", "vae"), ("qwen", "image", "vae"), ("anima", "vae"), ("anima",)),
    ),
    _template_entry(
        id="chroma",
        title="Chroma",
        public_base_family="chroma",
        default_width=1024,
        default_height=1024,
        default_steps=26,
        default_cfg_scale=3.5,
        default_sampler="euler",
        default_scheduler="beta",
        compatibility_summary="Official ComfyUI Chroma template preset routed through the non-SD template seam.",
        aliases=("chroma1",),
        notes=(
            "Matches the official Chroma text-to-image template defaults.",
            "Text Encoder selector stays hidden because the official template owns the fixed T5 encoder pairing.",
        ),
        shift_visible=True,
        default_shift=1.0,
        runtime_adapter_id="chroma",
        official_template_path="reference/workflow_templates/Chroma.json",
        diffusion_model_hints=("chroma",),
        diffusion_model_priority_hints=(("chroma1",), ("chroma",)),
        text_encoder_hints=("t5", "chroma"),
        text_encoder_priority_hints=(("t5xxl", "fp8"), ("t5xxl",), ("chroma",), ("t5",)),
        vae_hints=("ae", "chroma"),
        vae_priority_hints=(("ae",), ("chroma",)),
        vae_deny_hints=("qwen",),
    ),
    _template_entry(
        id="ernie_image",
        title="ERNIE-Image",
        public_base_family="ernie_image",
        default_width=1024,
        default_height=1024,
        default_steps=20,
        default_cfg_scale=4.0,
        default_sampler="euler",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI ERNIE-Image template preset on the current non-SD translation seam.",
        aliases=("ernie-image", "ernie image"),
        notes=(
            "Matches the official ERNIE-Image template defaults.",
            "Text Encoder selector stays hidden because the official template owns both the Ministral and prompt-enhancer pairing.",
        ),
        prompt_enhancement_visible=True,
        default_prompt_enhancement_enabled=True,
        runtime_adapter_id="ernie",
        official_template_path="reference/ComfyUI/blueprints/Text to Image (Ernie Image).json",
        diffusion_model_hints=("ernie", "image"),
        diffusion_model_priority_hints=(("ernie", "image"), ("ernie",)),
        text_encoder_hints=("ernie", "ministral", "3_3b", "ministral3"),
        text_encoder_priority_hints=(("ministral3_3b",), ("ministral_3_3b",), ("ministral", "3", "3b"), ("ernie",)),
        aux_text_encoder_priority_hints=(("ernie", "prompt", "enhancer"), ("prompt", "enhancer")),
        vae_hints=("ernie", "flux2"),
        vae_priority_hints=(("flux2", "vae"), ("ernie", "vae"), ("ernie",)),
        vae_deny_hints=("qwen",),
    ),
    _template_entry(
        id="ernie_image_turbo",
        title="ERNIE-Image Turbo",
        public_base_family="ernie_image",
        default_width=1024,
        default_height=1024,
        default_steps=8,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI ERNIE-Image Turbo template preset on the current non-SD translation seam.",
        aliases=("ernie-image-turbo", "ernie image turbo"),
        notes=(
            "Matches the official ERNIE-Image Turbo template defaults.",
            "Text Encoder selector stays hidden because the official template owns both the Ministral and prompt-enhancer pairing.",
        ),
        prompt_enhancement_visible=True,
        default_prompt_enhancement_enabled=True,
        runtime_adapter_id="ernie",
        official_template_path="reference/ComfyUI/blueprints/Text to Image (Ernie Image Turbo).json",
        diffusion_model_hints=("ernie", "turbo"),
        diffusion_model_priority_hints=(("ernie", "image", "turbo"), ("ernie", "turbo"), ("ernie",)),
        text_encoder_hints=("ernie", "ministral", "3_3b", "ministral3"),
        text_encoder_priority_hints=(("ministral3_3b",), ("ministral_3_3b",), ("ministral", "3", "3b"), ("ernie",)),
        aux_text_encoder_priority_hints=(("ernie", "prompt", "enhancer"), ("prompt", "enhancer")),
        vae_hints=("ernie", "flux2"),
        vae_priority_hints=(("flux2", "vae"), ("ernie", "vae"), ("ernie",)),
        vae_deny_hints=("qwen",),
    ),
    _template_entry(
        id="flux",
        title="Flux.1 Dev FP8",
        public_base_family="flux",
        default_width=1024,
        default_height=1024,
        default_steps=20,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI Flux.1 Dev FP8 template preset on the current non-SD translation seam.",
        aliases=("flux.1 dev fp8", "flux-1 dev fp8", "flux1 dev fp8"),
        notes=(
            "Matches the official Flux.1 Dev FP8 template defaults.",
            "Text Encoder selector stays hidden because the official template owns the dual-encoder bundle.",
            "Template LoRA stays explicit and defaults to the official turbo LoRA, but may be overridden with truthful drift messaging.",
        ),
        template_lora_visible=True,
        template_lora_override_allowed=True,
        official_template_lora_label="Flux_2-Turbo-LoRA_comfyui.safetensors",
        runtime_adapter_id="flux",
        official_template_path="reference/ComfyUI/blueprints/Text to Image (Flux.1 Dev).json",
        diffusion_model_hints=("flux",),
        diffusion_model_priority_hints=(("flux1", "dev"), ("flux1",), ("flux", "dev"), ("flux",)),
        text_encoder_hints=("clip_l", "t5"),
        text_encoder_priority_hints=(("clip_l",), ("clip", "l"), ("t5xxl",), ("flux",), ("t5",)),
        text_encoder_sequence_priority_hints=((("clip_l",), ("t5xxl", "fp16")), (("clip_l",), ("t5xxl",))),
        template_lora_priority_hints=(
            ("flux", "2", "turbo", "lora", "comfyui"),
            ("flux_2", "turbo", "lora", "comfyui"),
            ("flux", "turbo", "lora"),
        ),
        vae_hints=("flux", "ae"),
        vae_priority_hints=(("ae",), ("flux", "vae"), ("flux",)),
        vae_deny_hints=("qwen",),
    ),
    _template_entry(
        id="flux_krea_dev",
        title="Flux.1 Krea Dev",
        public_base_family="flux",
        default_width=1024,
        default_height=1024,
        default_steps=20,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI Flux.1 Krea Dev template preset on the current non-SD translation seam.",
        aliases=("flux.1 krea dev", "flux krea dev", "flux1 krea"),
        notes=(
            "Matches the official Flux.1 Krea Dev template defaults.",
            "Text Encoder selector stays hidden because the official template owns the clip_l/t5xxl pair.",
            "Krea does not use the Flux.2 Turbo template LoRA.",
        ),
        runtime_adapter_id="flux",
        official_template_path="reference/ComfyUI/blueprints/Text to Image (Flux.1 Krea Dev).json",
        diffusion_model_hints=("flux", "krea"),
        diffusion_model_priority_hints=(("flux1", "krea", "dev"), ("flux", "krea", "dev"), ("krea", "dev")),
        diffusion_model_deny_hints=("kontext", "flux2", "flux_2", "lora", "turbo"),
        text_encoder_hints=("clip_l", "t5"),
        text_encoder_priority_hints=(("clip_l",), ("clip", "l"), ("t5xxl",), ("flux",), ("t5",)),
        text_encoder_sequence_priority_hints=((("clip_l",), ("t5xxl", "fp16")), (("clip_l",), ("t5xxl",))),
        vae_hints=("flux", "ae"),
        vae_priority_hints=(("ae",), ("flux", "vae"), ("flux",)),
        vae_deny_hints=("qwen",),
    ),
    _template_entry(
        id="flux2_dev",
        title="Flux.2 Dev",
        public_base_family="flux2",
        default_width=1024,
        default_height=1024,
        default_steps=20,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="beta",
        compatibility_summary="Official ComfyUI Flux.2 Dev txt2img template preset on the dedicated Flux2 sampler seam.",
        aliases=("flux.2 dev", "flux2 dev", "flux 2 dev"),
        notes=(
            "Matches the official Flux.2 Dev txt2img template defaults.",
            "Text Encoder selector stays hidden because the official template owns the mistral_3_small_flux2 pairing.",
            "Template LoRA stays explicit and defaults to the official Flux.2 Turbo LoRA.",
        ),
        flux_guidance_visible=True,
        default_flux_guidance=4.0,
        template_lora_visible=True,
        template_lora_override_allowed=True,
        official_template_lora_label="Flux_2-Turbo-LoRA_comfyui.safetensors",
        runtime_adapter_id="flux2_dev",
        official_template_path="reference/ComfyUI/blueprints/Text to Image (Flux.2 Dev).json",
        diffusion_model_hints=("flux2", "dev"),
        diffusion_model_priority_hints=(("flux2", "dev", "fp8mixed"), ("flux", "2", "dev"), ("flux2", "dev")),
        diffusion_model_deny_hints=("klein", "image", "edit", "kontext"),
        text_encoder_hints=("mistral", "flux2"),
        text_encoder_priority_hints=(("mistral", "3", "small", "flux2"), ("mistral", "flux2"), ("mistral",)),
        template_lora_priority_hints=(
            ("flux", "2", "turbo", "lora", "comfyui"),
            ("flux_2", "turbo", "lora", "comfyui"),
        ),
        vae_hints=("encoder", "decoder", "flux2"),
        vae_priority_hints=(("full", "encoder", "small", "decoder"), ("flux2", "vae"), ("encoder", "decoder")),
    ),
    _template_entry(
        id="klein_4b_distilled",
        title="Flux.2 4B Distilled Klein",
        public_base_family="klein",
        default_width=1024,
        default_height=1024,
        default_steps=4,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="beta",
        compatibility_summary="Official ComfyUI Flux.2 4B Distilled Klein template preset on the current non-SD translation seam.",
        aliases=("flux.2 4b distilled klein", "klein 4b distilled"),
        notes=(
            "Matches the official Flux.2 4B Distilled Klein template defaults.",
            "Text Encoder selector stays hidden because the official template owns the fixed qwen_3_4b pairing.",
        ),
        runtime_adapter_id="klein_distilled",
        official_template_path="reference/workflow_templates/Flux.2 4B Distilled Klein.json",
        diffusion_model_hints=("klein", "4b"),
        diffusion_model_priority_hints=(("flux", "2", "klein", "4b"), ("klein", "4b")),
        diffusion_model_deny_hints=("base", "9b"),
        text_encoder_hints=("qwen", "4b", "klein"),
        text_encoder_priority_hints=(("qwen_3_4b",), ("klein", "4b"), ("klein",), ("qwen",)),
        vae_hints=("flux2", "vae", "klein", "4b"),
        vae_priority_hints=(("flux2", "vae"), ("klein", "4b"), ("flux2",)),
    ),
    _template_entry(
        id="klein_4b",
        title="Flux.2 4B Klein",
        public_base_family="klein",
        default_width=1024,
        default_height=1024,
        default_steps=20,
        default_cfg_scale=5.0,
        default_sampler="euler",
        default_scheduler="beta",
        compatibility_summary="Official ComfyUI Flux.2 4B Klein template preset on the current non-SD translation seam.",
        aliases=("klein", "flux.2", "flux2", "flux.2 4b klein", "klein 4b"),
        notes=(
            "Matches the official Flux.2 4B Klein template defaults.",
            "Text Encoder selector stays hidden because the official template owns the fixed qwen_3_4b pairing.",
        ),
        runtime_adapter_id="klein",
        official_template_path="reference/workflow_templates/Flux.2 4B Klein.json",
        diffusion_model_hints=("klein", "4b"),
        diffusion_model_priority_hints=(("klein", "base", "4b"), ("flux", "2", "klein", "base", "4b"), ("klein", "4b")),
        diffusion_model_deny_hints=("distill", "distilled", "9b"),
        text_encoder_hints=("qwen", "4b", "klein"),
        text_encoder_priority_hints=(("qwen_3_4b",), ("klein", "4b"), ("klein",), ("qwen",)),
        vae_hints=("flux2", "vae", "klein", "4b"),
        vae_priority_hints=(("flux2", "vae"), ("klein", "4b"), ("flux2",)),
    ),
    _template_entry(
        id="klein_9b_distilled",
        title="Flux.2 9B Distilled Klein",
        public_base_family="klein",
        default_width=1024,
        default_height=1024,
        default_steps=4,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="beta",
        compatibility_summary="Official ComfyUI Flux.2 9B Distilled Klein template preset on the current non-SD translation seam.",
        aliases=("flux.2 9b distilled klein", "klein 9b distilled"),
        notes=(
            "Matches the official Flux.2 9B Distilled Klein template defaults.",
            "Text Encoder selector stays hidden because the official template owns the fixed qwen_3_8b pairing.",
        ),
        runtime_adapter_id="klein_distilled",
        official_template_path="reference/workflow_templates/Flux.2 9B Distilled Klein.json",
        diffusion_model_hints=("klein", "9b"),
        diffusion_model_priority_hints=(("flux", "2", "klein", "9b"), ("klein", "9b")),
        diffusion_model_deny_hints=("base", "4b"),
        text_encoder_hints=("qwen", "8b", "klein"),
        text_encoder_priority_hints=(("qwen_3_8b",), ("klein", "9b"), ("klein",), ("qwen",)),
        vae_hints=("encoder", "decoder", "9b", "klein"),
        vae_priority_hints=(("full", "encoder", "small", "decoder"), ("klein", "9b"), ("encoder", "decoder")),
    ),
    _template_entry(
        id="klein_9b",
        title="Flux.2 9B Klein",
        public_base_family="klein",
        default_width=1024,
        default_height=1024,
        default_steps=20,
        default_cfg_scale=5.0,
        default_sampler="euler",
        default_scheduler="beta",
        compatibility_summary="Official ComfyUI Flux.2 9B Klein template preset on the current non-SD translation seam.",
        aliases=("flux.2 9b klein", "klein 9b"),
        notes=(
            "Matches the official Flux.2 9B Klein template defaults.",
            "Text Encoder selector stays hidden because the official template owns the fixed qwen_3_8b pairing.",
        ),
        runtime_adapter_id="klein",
        official_template_path="reference/workflow_templates/Flux.2 9B Klein.json",
        diffusion_model_hints=("klein", "9b"),
        diffusion_model_priority_hints=(("klein", "base", "9b"), ("flux", "2", "klein", "base", "9b"), ("klein", "9b")),
        diffusion_model_deny_hints=("distill", "distilled", "4b"),
        text_encoder_hints=("qwen", "8b", "klein"),
        text_encoder_priority_hints=(("qwen_3_8b",), ("klein", "9b"), ("klein",), ("qwen",)),
        vae_hints=("encoder", "decoder", "9b", "klein"),
        vae_priority_hints=(("full", "encoder", "small", "decoder"), ("klein", "9b"), ("encoder", "decoder")),
    ),
    _template_entry(
        id="hidream_i1_dev_fp8",
        title="HiDream i1 Dev FP8",
        public_base_family="hidream",
        default_width=1024,
        default_height=1024,
        default_steps=28,
        default_cfg_scale=1.0,
        default_sampler="lcm",
        default_scheduler="normal",
        compatibility_summary="Official ComfyUI HiDream i1 Dev FP8 template preset on the current non-SD translation seam.",
        aliases=("hidream i1 dev fp8",),
        notes=(
            "Matches the official HiDream i1 Dev FP8 template defaults.",
            "Text Encoder selector stays hidden because the official template owns the four-encoder bundle.",
        ),
        shift_visible=True,
        default_shift=6.0,
        runtime_adapter_id="hidream",
        official_template_path="reference/workflow_templates/Hidream i1 Dev FP8.json",
        diffusion_model_hints=("hidream", "dev"),
        diffusion_model_priority_hints=(("hidream", "dev", "fp8"), ("hidream", "i1", "dev"), ("hidream", "dev")),
        text_encoder_hints=("hidream", "clip"),
        text_encoder_priority_hints=(("clip_l_hidream",), ("hidream", "clip"), ("hidream",), ("llama",), ("t5xxl",)),
        text_encoder_sequence_priority_hints=(
            (("clip_l_hidream",), ("clip_g_hidream",), ("t5xxl", "fp8"), ("llama", "8b", "instruct")),
        ),
        vae_hints=("ae", "hidream"),
        vae_priority_hints=(("ae",), ("hidream",)),
        vae_deny_hints=("qwen",),
    ),
    _template_entry(
        id="hidream_i1_fast",
        title="HiDream i1 fast",
        public_base_family="hidream",
        default_width=1024,
        default_height=1024,
        default_steps=16,
        default_cfg_scale=1.0,
        default_sampler="lcm",
        default_scheduler="normal",
        compatibility_summary="Official ComfyUI HiDream i1 fast template preset on the current non-SD translation seam.",
        aliases=("hidream i1 fast",),
        notes=(
            "Matches the official HiDream i1 fast template defaults.",
            "Text Encoder selector stays hidden because the official template owns the four-encoder bundle.",
        ),
        shift_visible=True,
        default_shift=3.0,
        runtime_adapter_id="hidream",
        official_template_path="reference/workflow_templates/Hidream i1 fast.json",
        diffusion_model_hints=("hidream", "fast"),
        diffusion_model_priority_hints=(("hidream", "fast"), ("hidream", "i1", "fast")),
        text_encoder_hints=("hidream", "clip"),
        text_encoder_priority_hints=(("clip_l_hidream",), ("hidream", "clip"), ("hidream",), ("llama",), ("t5xxl",)),
        text_encoder_sequence_priority_hints=(
            (("clip_l_hidream",), ("clip_g_hidream",), ("t5xxl", "fp8"), ("llama", "8b", "instruct")),
        ),
        vae_hints=("ae", "hidream"),
        vae_priority_hints=(("ae",), ("hidream",)),
        vae_deny_hints=("qwen",),
    ),
    _template_entry(
        id="hidream_i1_full",
        title="HiDream i1 full",
        public_base_family="hidream",
        default_width=1024,
        default_height=1024,
        default_steps=50,
        default_cfg_scale=5.0,
        default_sampler="uni_pc",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI HiDream i1 full template preset on the current non-SD translation seam.",
        aliases=("hidream", "hidream i1", "hidream i1 full"),
        notes=(
            "Matches the official HiDream i1 full template defaults.",
            "Text Encoder selector stays hidden because the official template owns the four-encoder bundle.",
        ),
        shift_visible=True,
        default_shift=3.0,
        runtime_adapter_id="hidream",
        official_template_path="reference/workflow_templates/Hidream i1 full.json",
        diffusion_model_hints=("hidream", "full"),
        diffusion_model_priority_hints=(("hidream", "full"), ("hidream", "i1", "full"), ("hidream", "i1")),
        text_encoder_hints=("hidream", "clip"),
        text_encoder_priority_hints=(("clip_l_hidream",), ("hidream", "clip"), ("hidream",), ("llama",), ("t5xxl",)),
        text_encoder_sequence_priority_hints=(
            (("clip_l_hidream",), ("clip_g_hidream",), ("t5xxl", "fp8"), ("llama", "8b", "instruct")),
        ),
        vae_hints=("ae", "hidream"),
        vae_priority_hints=(("ae",), ("hidream",)),
        vae_deny_hints=("qwen",),
    ),
    _template_entry(
        id="longcat_image",
        title="Longcat BF16",
        public_base_family="longcat_image",
        default_width=1024,
        default_height=1024,
        default_steps=20,
        default_cfg_scale=4.0,
        default_sampler="euler",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI Longcat BF16 template preset on the current non-SD translation seam.",
        aliases=("longcat", "longcat image"),
        notes=(
            "Matches the official Longcat BF16 template defaults.",
            "Text Encoder selector stays hidden because the official template owns the fixed qwen_2.5_vl pairing.",
        ),
        flux_guidance_visible=True,
        default_flux_guidance=4.0,
        runtime_adapter_id="longcat",
        official_template_path="reference/workflow_templates/Longcat BF16.json",
        diffusion_model_hints=("longcat",),
        diffusion_model_priority_hints=(("longcat",),),
        text_encoder_hints=("longcat", "qwen", "2.5", "vl"),
        text_encoder_priority_hints=(("qwen_2.5_vl_7b",), ("longcat",), ("qwen", "vl"), ("qwen",)),
        vae_hints=("ae", "longcat"),
        vae_priority_hints=(("ae",), ("longcat",)),
        vae_deny_hints=("qwen",),
    ),
    _template_entry(
        id="qwen_image",
        title="Qwen-Image 2512",
        public_base_family="qwen_image",
        default_width=1328,
        default_height=1328,
        default_steps=50,
        default_cfg_scale=4.0,
        default_sampler="euler",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI Qwen-Image 2512 template preset on the current non-SD translation seam.",
        aliases=("qwen image", "qwen-image 2512", "qwen image 2512"),
        notes=(
            "Matches the official Qwen-Image 2512 template defaults.",
            "Text Encoder selector stays hidden because the official template owns the fixed qwen_2.5_vl pairing.",
            "Template LoRA stays explicit and defaults to the official 4-step Lightning LoRA, but may be overridden with truthful drift messaging.",
        ),
        shift_visible=True,
        default_shift=3.1,
        template_lora_visible=True,
        template_lora_override_allowed=True,
        official_template_lora_label="Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors",
        runtime_adapter_id="qwen_image",
        official_template_path="reference/ComfyUI/blueprints/Text to Image (Qwen-Image 2512).json",
        diffusion_model_hints=("qwen", "2512"),
        diffusion_model_priority_hints=(
            ("qwen", "image", "2512", "fp8", "e4m3fn"),
            ("qwen_image_2512", "fp8", "e4m3fn"),
            ("qwen", "image", "2512", "fp8"),
            ("qwen", "image", "2512"),
        ),
        diffusion_model_deny_hints=("lightning", "lora", "2step", "4step", "8step", "distill", "distilled"),
        text_encoder_hints=("qwen", "2.5", "vl"),
        text_encoder_priority_hints=(("qwen_2.5_vl_7b",), ("qwen_2.5_vl",), ("qwen", "image"), ("qwen",)),
        template_lora_priority_hints=(
            ("qwen", "image", "2512", "lightning", "4steps"),
            ("qwen", "image", "2512", "lora", "4steps"),
            ("qwen", "image", "2512", "lightning"),
        ),
        vae_hints=("qwen", "qwen-image", "qwen_image"),
        vae_priority_hints=(("qwen", "vae"), ("qwen", "image"), ("qwen",)),
    ),
    _template_entry(
        id="qwen_image_edit",
        title="Qwen-Image Edit",
        public_base_family="qwen_image_edit",
        default_width=1328,
        default_height=1328,
        default_steps=4,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="simple",
        compatibility_summary="Legacy Qwen-Image Edit compatibility preset retained on the dedicated edit-flow seam.",
        aliases=("qwen image edit", "qwen-image edit"),
        notes=(
            "Retains the pre-2511 Qwen-Image Edit compatibility defaults.",
            "Edit flow requires a source image but does not require a mask.",
            "Current 0.9.98 Qwen 2509 plus-encoder parity is not silently substituted for this saved-request lane.",
            "Template LoRA stays explicit and defaults to the official lightning LoRA, but may be overridden with truthful drift messaging.",
        ),
        image_edit_profile=True,
        request_contract_surface="img2img",
        reference_input_mode="single",
        max_direct_references=1,
        encoder_family="qwen_image_edit",
        template_lora_chain_mode="single",
        shift_visible=True,
        default_shift=3.0,
        edit_megapixels_visible=True,
        default_edit_megapixels=1.5,
        template_lora_visible=True,
        template_lora_override_allowed=True,
        official_template_lora_label="Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors",
        flow_kind="edit",
        available_surface_flows=("img2img",),
        runtime_adapter_id="qwen_image_edit",
        official_template_path="reference/workflow_templates/imageEdit/Qwen-image edit.json",
        diffusion_model_hints=("qwen", "image", "edit"),
        diffusion_model_priority_hints=(
            ("qwen", "image", "edit", "fp8", "e4m3fn"),
            ("qwen_image_edit", "fp8", "e4m3fn"),
            ("qwen", "image", "edit", "fp8"),
            ("qwen", "image", "edit"),
        ),
        diffusion_model_deny_hints=(
            "lightning",
            "lora",
            "turbo",
            "2512",
            "firered",
            "fire-red",
            "2509",
            "2511",
            "transformer",
        ),
        text_encoder_hints=("qwen", "2.5", "vl"),
        text_encoder_priority_hints=(("qwen_2.5_vl_7b",), ("qwen_2.5_vl",), ("qwen", "image"), ("qwen",)),
        template_lora_priority_hints=(
            ("qwen", "image", "edit", "lightning", "4steps"),
            ("qwen", "image", "edit", "lora", "4steps"),
            ("qwen", "edit", "lightning", "4steps"),
        ),
        vae_hints=("qwen", "qwen-image", "qwen_image"),
        vae_priority_hints=(("qwen", "vae"), ("qwen", "image"), ("qwen",)),
    ),
    _template_entry(
        id="qwen_image_edit_multi_lora",
        title="Qwen-Image Edit Multi-LoRA",
        public_base_family="qwen_image_edit",
        default_width=1328,
        default_height=1328,
        default_steps=4,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="simple",
        compatibility_summary="Legacy Qwen-Image Edit multi-LoRA compatibility preset retained on the dedicated edit-flow seam.",
        aliases=(
            "qwen image edit multi lora",
            "qwen-image edit multi lora",
            "qwen image edit triple lora",
        ),
        notes=(
            "Retains the pre-2511 Qwen-Image Edit multi-LoRA compatibility defaults.",
            "Edit flow requires a source image but does not require a mask.",
            "Template-owned lightning LoRA is stacked three times before any inline LoRA overrides.",
            "Current 0.9.98 Qwen 2509 plus-encoder parity is not silently substituted for this saved-request lane.",
        ),
        image_edit_profile=True,
        request_contract_surface="img2img",
        reference_input_mode="single",
        max_direct_references=1,
        encoder_family="qwen_image_edit",
        template_lora_chain_mode="triple",
        shift_visible=True,
        default_shift=3.0,
        edit_megapixels_visible=True,
        default_edit_megapixels=1.5,
        template_lora_visible=True,
        template_lora_override_allowed=True,
        official_template_lora_label="Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors",
        flow_kind="edit",
        available_surface_flows=("img2img",),
        runtime_adapter_id="qwen_image_edit",
        official_template_path="reference/workflow_templates/imageEdit/Qwen-image edit-multi-lora.json",
        diffusion_model_hints=("qwen", "image", "edit"),
        diffusion_model_priority_hints=(
            ("qwen", "image", "edit", "fp8", "e4m3fn"),
            ("qwen_image_edit", "fp8", "e4m3fn"),
            ("qwen", "image", "edit", "fp8"),
            ("qwen", "image", "edit"),
        ),
        diffusion_model_deny_hints=(
            "lightning",
            "lora",
            "turbo",
            "2512",
            "firered",
            "fire-red",
            "2509",
            "2511",
            "transformer",
        ),
        text_encoder_hints=("qwen", "2.5", "vl"),
        text_encoder_priority_hints=(("qwen_2.5_vl_7b",), ("qwen_2.5_vl",), ("qwen", "image"), ("qwen",)),
        template_lora_priority_hints=(
            ("qwen", "image", "edit", "lightning", "4steps"),
            ("qwen", "image", "edit", "lora", "4steps"),
            ("qwen", "edit", "lightning", "4steps"),
        ),
        vae_hints=("qwen", "qwen-image", "qwen_image"),
        vae_priority_hints=(("qwen", "vae"), ("qwen", "image"), ("qwen",)),
    ),
    _template_entry(
        id="qwen_image_edit_2511",
        title="Qwen-Image Edit 2511",
        public_base_family="qwen_image_edit",
        default_width=1328,
        default_height=1328,
        default_steps=40,
        default_cfg_scale=4.0,
        default_sampler="euler",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI Qwen-Image Edit 2511 template preset on the dedicated edit-flow seam.",
        aliases=("qwen image edit 2511", "qwen-image edit 2511", "qwen 2511 edit"),
        notes=(
            "Matches the official Qwen Image Edit 2511 template defaults.",
            "Edit flow requires one source image and accepts up to two optional direct references.",
            "Qwen 2511 uses the plus encoder and Flux reference-method nodes without a template-owned LoRA.",
        ),
        image_edit_profile=True,
        request_contract_surface="img2img",
        reference_input_mode="multi",
        max_direct_references=3,
        encoder_family="qwen_image_edit_2511",
        template_lora_chain_mode="none",
        shift_visible=True,
        default_shift=3.1,
        edit_megapixels_visible=False,
        default_edit_megapixels=None,
        template_lora_visible=False,
        template_lora_override_allowed=False,
        official_template_lora_label="",
        flow_kind="edit",
        available_surface_flows=("img2img",),
        runtime_adapter_id="qwen_image_edit",
        official_template_path="reference/ComfyUI/blueprints/Image Edit (Qwen 2511).json",
        diffusion_model_hints=("qwen", "image", "edit", "2511"),
        diffusion_model_priority_hints=(
            ("qwen_image_edit_2511", "bf16"),
            ("qwen", "image", "edit", "2511"),
            ("qwen", "2511", "edit"),
        ),
        diffusion_model_deny_hints=("lightning", "lora", "turbo", "2509", "2512", "firered", "fire-red", "fp8"),
        text_encoder_hints=("qwen", "2.5", "vl"),
        text_encoder_priority_hints=(("qwen_2.5_vl_7b",), ("qwen_2.5_vl",), ("qwen", "image"), ("qwen",)),
        vae_hints=("qwen", "qwen-image", "qwen_image"),
        vae_priority_hints=(("qwen", "vae"), ("qwen", "image"), ("qwen",)),
    ),
    _template_entry(
        id="firered_image_edit",
        title="FireRed Image Edit",
        public_base_family="firered_image_edit",
        default_width=1328,
        default_height=1328,
        default_steps=40,
        default_cfg_scale=4.0,
        default_sampler="euler",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI FireRed Image Edit 1.1 base template preset on the dedicated edit-flow seam.",
        aliases=("firered image edit", "fire red image edit", "firered", "fire red"),
        notes=(
            "Matches the official FireRed Image Edit base template branch defaults.",
            "Edit flow requires one to three ordered source images and does not require a mask.",
            "This base lane keeps the official non-lightning branch and does not require a template-owned LoRA.",
        ),
        image_edit_profile=True,
        request_contract_surface="img2img",
        reference_input_mode="multi",
        max_direct_references=3,
        encoder_family="qwen_image_edit_plus",
        template_lora_chain_mode="none",
        shift_visible=True,
        default_shift=3.1,
        edit_megapixels_visible=True,
        default_edit_megapixels=1.0,
        flow_kind="edit",
        available_surface_flows=("img2img",),
        runtime_adapter_id="qwen_image_edit",
        official_template_path="reference/ComfyUI/blueprints/Image Edit (FireRed Image Edit 1.1).json",
        diffusion_model_hints=("firered", "image", "edit"),
        diffusion_model_priority_hints=(
            ("firered", "image", "edit", "1.1", "transformer"),
            ("fire", "red", "image", "edit", "1.1", "transformer"),
        ),
        diffusion_model_deny_hints=("lightning", "lora", "qwen_image_edit", "2509", "2511", "1.0"),
        text_encoder_hints=("qwen", "2.5", "vl"),
        text_encoder_priority_hints=(("qwen_2.5_vl_7b",), ("qwen_2.5_vl",), ("qwen", "image"), ("qwen",)),
        vae_hints=("qwen", "qwen-image", "qwen_image"),
        vae_priority_hints=(("qwen", "vae"), ("qwen", "image"), ("qwen",)),
    ),
    _template_entry(
        id="firered_image_edit_lightning",
        title="FireRed Image Edit Lightning",
        public_base_family="firered_image_edit",
        default_width=1328,
        default_height=1328,
        default_steps=8,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI FireRed Image Edit 1.1 lightning template branch preset on the dedicated edit-flow seam.",
        aliases=(
            "firered image edit lightning",
            "fire red image edit lightning",
            "firered lightning",
            "fire red lightning",
        ),
        notes=(
            "Matches the official FireRed Image Edit lightning branch defaults.",
            "Edit flow requires one to three ordered source images and does not require a mask.",
            "Template LoRA stays explicit and defaults to the official FireRed lightning branch LoRA, but may be overridden with truthful drift messaging.",
        ),
        image_edit_profile=True,
        request_contract_surface="img2img",
        reference_input_mode="multi",
        max_direct_references=3,
        encoder_family="qwen_image_edit_plus",
        template_lora_chain_mode="single",
        shift_visible=True,
        default_shift=3.1,
        edit_megapixels_visible=True,
        default_edit_megapixels=1.0,
        template_lora_visible=True,
        template_lora_override_allowed=True,
        official_template_lora_label="FireRed-Image-Edit-1.0-Lightning-8steps-v1.0.safetensors",
        flow_kind="edit",
        available_surface_flows=("img2img",),
        runtime_adapter_id="qwen_image_edit",
        official_template_path="reference/ComfyUI/blueprints/Image Edit (FireRed Image Edit 1.1).json",
        diffusion_model_hints=("firered", "image", "edit"),
        diffusion_model_priority_hints=(
            ("firered", "image", "edit", "1.1", "transformer"),
            ("fire", "red", "image", "edit", "1.1", "transformer"),
        ),
        diffusion_model_deny_hints=("lightning", "lora", "qwen_image_edit", "2509", "2511", "1.0"),
        text_encoder_hints=("qwen", "2.5", "vl"),
        text_encoder_priority_hints=(("qwen_2.5_vl_7b",), ("qwen_2.5_vl",), ("qwen", "image"), ("qwen",)),
        template_lora_priority_hints=(
            ("firered", "image", "edit", "lightning", "8steps"),
            ("fire", "red", "image", "edit", "lightning", "8steps"),
        ),
        vae_hints=("qwen", "qwen-image", "qwen_image"),
        vae_priority_hints=(("qwen", "vae"), ("qwen", "image"), ("qwen",)),
    ),
    _template_entry(
        id="flux_kontext_dev_edit",
        title="Flux.1 Kontext Dev Edit",
        public_base_family="flux_kontext_dev_edit",
        default_width=1024,
        default_height=1024,
        default_steps=20,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI Flux.1 Kontext Dev image-edit template preset on the current non-SD translation seam.",
        aliases=("flux.1 kontext dev edit", "flux kontext edit", "kontext edit"),
        notes=(
            "Matches the official Flux.1 Kontext Dev image-edit template defaults.",
            "Edit flow supports ordered multi-reference stitching and does not require a mask.",
            "The main reference image is used as the first stitched anchor in RookieUI's bounded first-wave adapter.",
        ),
        image_edit_profile=True,
        request_contract_surface="img2img",
        reference_input_mode="multi",
        max_direct_references=3,
        encoder_family="flux_clip_text",
        template_lora_chain_mode="none",
        flux_guidance_visible=True,
        default_flux_guidance=2.5,
        flow_kind="edit",
        available_surface_flows=("img2img",),
        runtime_adapter_id="flux_kontext_dev_edit",
        official_template_path="reference/workflow_templates/imageEdit/Flux.1 Kontext Dev .json",
        diffusion_model_hints=("kontext", "flux1"),
        diffusion_model_priority_hints=(
            ("flux1", "kontext", "dev"),
            ("flux", "kontext", "dev"),
            ("kontext",),
        ),
        text_encoder_hints=("clip_l", "t5", "kontext"),
        text_encoder_priority_hints=(("clip_l",), ("clip", "l"), ("t5xxl", "fp8"), ("t5",)),
        text_encoder_sequence_priority_hints=(
            (("clip_l",), ("t5xxl", "fp8", "scaled")),
            (("clip_l",), ("t5xxl", "fp8")),
            (("clip_l",), ("t5xxl",)),
        ),
        vae_hints=("ae", "kontext", "flux"),
        vae_priority_hints=(("ae",), ("kontext",), ("flux", "vae"), ("flux",)),
        vae_deny_hints=("qwen",),
    ),
    _template_entry(
        id="flux2_image_edit",
        title="Flux.2 Image Edit",
        public_base_family="flux2_image_edit",
        default_width=1248,
        default_height=832,
        default_steps=20,
        default_cfg_scale=4.0,
        default_sampler="euler",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI Flux.2 image-edit template preset on the current non-SD translation seam.",
        aliases=("flux.2 image edit", "flux2 image edit"),
        notes=(
            "Matches the 0.9.98 Flux.2 image-edit template dimensions and core assets.",
            "Edit flow requires one ordered source image and does not require a mask.",
            "The optional turbo-LoRA branch remains out of scope until a dedicated profile is planned.",
        ),
        image_edit_profile=True,
        request_contract_surface="img2img",
        reference_input_mode="single",
        max_direct_references=1,
        encoder_family="flux_clip_text",
        template_lora_chain_mode="none",
        flux_guidance_visible=True,
        default_flux_guidance=4.0,
        edit_megapixels_visible=True,
        default_edit_megapixels=1.0,
        flow_kind="edit",
        available_surface_flows=("img2img",),
        runtime_adapter_id="flux2_image_edit",
        official_template_path="reference/ComfyUI/blueprints/Image Edit (Flux.2 Dev).json",
        diffusion_model_hints=("flux2", "edit"),
        diffusion_model_priority_hints=(("flux2", "dev"), ("flux", "2", "image", "edit"), ("flux2",)),
        diffusion_model_deny_hints=("klein", "kontext"),
        text_encoder_hints=("mistral", "flux2"),
        text_encoder_priority_hints=(("mistral", "3", "small", "flux2"), ("mistral", "flux2"), ("mistral",)),
        vae_hints=("full", "encoder", "small", "decoder", "flux2"),
        vae_priority_hints=(("full", "encoder", "small", "decoder"), ("flux2", "vae"), ("encoder", "decoder")),
    ),
    _template_entry(
        id="klein_9b_kv_image_edit",
        title="Flux.2 Klein 9B KV Image Edit",
        public_base_family="klein_9b_kv_image_edit",
        default_width=1024,
        default_height=1024,
        default_steps=4,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="simple",
        compatibility_summary="Legacy Flux.2 Klein 9B KV image-edit compatibility preset retained on the current non-SD translation seam.",
        aliases=("flux.2 klein 9b kv image edit", "klein 9b kv image edit", "klein kv edit"),
        notes=(
            "Retains the older Flux.2 Klein 9B KV image-edit template defaults.",
            "Edit flow supports ordered multi-reference images and does not require a mask.",
            "The first-wave adapter keeps a bounded three-reference cap even though the shared latent chain can extend further.",
            "The 0.9.98 blueprint set exposes a separate Flux.2 Klein 4B image-edit blueprint that remains deferred from this drift sweep.",
        ),
        image_edit_profile=True,
        request_contract_surface="img2img",
        reference_input_mode="multi",
        max_direct_references=3,
        encoder_family="flux_clip_text",
        template_lora_chain_mode="none",
        edit_megapixels_visible=True,
        default_edit_megapixels=1.0,
        flow_kind="edit",
        available_surface_flows=("img2img",),
        runtime_adapter_id="klein_9b_kv_image_edit",
        official_template_path="reference/workflow_templates/imageEdit/Flux.2 Klein 9b KV image edit.json",
        diffusion_model_hints=("klein", "9b", "kv"),
        diffusion_model_priority_hints=(("flux", "2", "klein", "9b", "kv"), ("klein", "9b", "kv"), ("klein", "kv")),
        diffusion_model_deny_hints=("4b", "distill", "distilled", "base"),
        text_encoder_hints=("qwen", "8b", "klein"),
        text_encoder_priority_hints=(("qwen_3_8b",), ("klein", "9b"), ("klein",), ("qwen",)),
        vae_hints=("flux2", "vae", "klein", "9b"),
        vae_priority_hints=(("flux2", "vae"), ("klein", "9b"), ("encoder", "decoder")),
    ),
    _template_entry(
        id="longcat_image_edit",
        title="Longcat Image Edit",
        public_base_family="longcat_image_edit",
        default_width=1024,
        default_height=1024,
        default_steps=50,
        default_cfg_scale=4.5,
        default_sampler="euler",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI Longcat image-edit template preset on the current non-SD translation seam.",
        aliases=("longcat image edit", "longcat edit"),
        notes=(
            "Matches the official Longcat image-edit template defaults.",
            "Edit flow requires one ordered source image and does not require a mask.",
            "Longcat edit keeps the Qwen-style edit encoder but applies Flux-family reference-method metadata before sampling.",
        ),
        image_edit_profile=True,
        request_contract_surface="img2img",
        reference_input_mode="single",
        max_direct_references=1,
        encoder_family="qwen_image_edit",
        template_lora_chain_mode="none",
        flux_guidance_visible=True,
        default_flux_guidance=4.5,
        edit_megapixels_visible=True,
        default_edit_megapixels=1.0,
        flow_kind="edit",
        available_surface_flows=("img2img",),
        runtime_adapter_id="longcat_image_edit",
        official_template_path="reference/ComfyUI/blueprints/Image Edit (LongCat Image Edit).json",
        diffusion_model_hints=("longcat", "edit"),
        diffusion_model_priority_hints=(("longcat", "image", "edit"), ("longcat", "edit"), ("longcat",)),
        text_encoder_hints=("longcat", "qwen", "2.5", "vl"),
        text_encoder_priority_hints=(("qwen_2.5_vl_7b",), ("longcat",), ("qwen", "vl"), ("qwen",)),
        vae_hints=("ae", "longcat"),
        vae_priority_hints=(("ae",), ("longcat",)),
        vae_deny_hints=("qwen",),
    ),
    _template_entry(
        id="z_image",
        title="Z-Image",
        public_base_family="z_image",
        default_width=1024,
        default_height=1024,
        default_steps=25,
        default_cfg_scale=4.0,
        default_sampler="res_multistep",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI Z-Image template preset on the current non-SD translation seam.",
        aliases=("lumina", "z-image", "z image", "lumina2"),
        notes=(
            "Matches the official Z-Image template defaults.",
            "Text Encoder selector stays hidden because the official template owns the fixed qwen_3_4b pairing.",
        ),
        shift_visible=True,
        default_shift=3.0,
        runtime_adapter_id="z_image",
        official_template_path="reference/ComfyUI/blueprints/Text to Image (Z-Image-Base).json",
        diffusion_model_hints=("z-image", "z_image", "zimage"),
        diffusion_model_priority_hints=(("z_image",), ("z-image",), ("z", "image")),
        text_encoder_hints=("qwen", "3", "4b", "z"),
        text_encoder_priority_hints=(("qwen_3_4b",), ("z_image",), ("z-image",), ("lumina",), ("qwen",)),
        vae_hints=("ae", "z-image", "z_image"),
        vae_priority_hints=(("ae",), ("z-image",), ("z_image",)),
        vae_deny_hints=("qwen",),
    ),
    _template_entry(
        id="z_image_turbo",
        title="Z-Image Turbo",
        public_base_family="z_image",
        default_width=1024,
        default_height=1024,
        default_steps=8,
        default_cfg_scale=1.0,
        default_sampler="res_multistep",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI Z-Image Turbo template preset on the current non-SD translation seam.",
        aliases=("zit", "z-image-turbo", "z image turbo"),
        notes=(
            "Matches the official Z-Image Turbo template defaults.",
            "Text Encoder selector stays hidden because the official template owns the fixed qwen_3_4b pairing.",
        ),
        shift_visible=True,
        default_shift=3.0,
        runtime_adapter_id="z_image",
        official_template_path="reference/ComfyUI/blueprints/Text to Image (Z-Image-Turbo).json",
        diffusion_model_hints=("z-image", "z_image", "zimage", "turbo"),
        diffusion_model_priority_hints=(("z_image", "turbo"), ("z-image", "turbo"), ("z", "image", "turbo")),
        text_encoder_hints=("qwen", "3", "4b", "z"),
        text_encoder_priority_hints=(("qwen_3_4b",), ("z_image", "turbo"), ("z-image", "turbo"), ("lumina",), ("qwen",)),
        vae_hints=("ae", "z-image", "z_image", "turbo"),
        vae_priority_hints=(("ae",), ("z-image", "turbo"), ("z_image", "turbo"), ("z-image",), ("z_image",)),
        vae_deny_hints=("qwen",),
    ),
)


def list_family_template_manifest_entries() -> list[FamilyTemplateManifestEntry]:
    return list(_MANIFEST_ENTRIES)


def _normalized_aliases(entry: FamilyTemplateManifestEntry) -> tuple[str, ...]:
    return tuple(str(alias or "").strip().lower() for alias in entry.aliases if str(alias or "").strip())


def get_family_template_manifest_entry(family_id: str) -> FamilyTemplateManifestEntry:
    normalized = (family_id or "").strip().lower()
    if not normalized:
        normalized = "sd15"
    for entry in _MANIFEST_ENTRIES:
        if entry.id == normalized:
            return entry
        if normalized in _normalized_aliases(entry):
            return entry
    raise ValueError(f"Unsupported RookieUI model family: {family_id}")


def build_model_family_registry_payload() -> dict[str, object]:
    return {
        "contract_version": MODEL_FAMILY_REGISTRY_CONTRACT_VERSION,
        "entries": [entry.to_registry_payload() for entry in _MANIFEST_ENTRIES],
    }


def _normalized_surface_flow(surface_flow: str) -> str:
    return str(surface_flow or "").strip().lower()


def list_manifest_entries_for_surface_flow(surface_flow: str) -> list[FamilyTemplateManifestEntry]:
    normalized_surface_flow = _normalized_surface_flow(surface_flow)
    if not normalized_surface_flow:
        return list(_MANIFEST_ENTRIES)
    return [
        entry
        for entry in _MANIFEST_ENTRIES
        if normalized_surface_flow in {flow.strip().lower() for flow in entry.available_surface_flows}
    ]


def supports_surface_flow(family_id: str, surface_flow: str) -> bool:
    entry = get_family_template_manifest_entry(family_id)
    normalized_surface_flow = _normalized_surface_flow(surface_flow)
    if not normalized_surface_flow:
        return True
    return normalized_surface_flow in {flow.strip().lower() for flow in entry.available_surface_flows}


def build_primary_model_category_by_family() -> dict[str, str]:
    category_map: dict[str, str] = {}
    for entry in _MANIFEST_ENTRIES:
        category_map[entry.id] = entry.primary_model_category
        public_base_family = str(entry.public_base_family or "").strip().lower()
        if public_base_family and public_base_family not in category_map:
            category_map[public_base_family] = entry.primary_model_category
        for alias in _normalized_aliases(entry):
            category_map[alias] = entry.primary_model_category
    return category_map


def list_non_sd_manifest_entries() -> list[FamilyTemplateManifestEntry]:
    return [entry for entry in _MANIFEST_ENTRIES if entry.support_tier != "parity"]


def list_non_sd_txt2img_manifest_entries() -> list[FamilyTemplateManifestEntry]:
    return [
        entry
        for entry in list_non_sd_manifest_entries()
        if entry.flow_kind == "txt2img"
    ]


def list_non_sd_edit_manifest_entries() -> list[FamilyTemplateManifestEntry]:
    return [
        entry
        for entry in list_non_sd_manifest_entries()
        if entry.flow_kind == "edit"
    ]


def build_non_sd_txt2img_profile_ids() -> tuple[str, ...]:
    return tuple(entry.id for entry in list_non_sd_txt2img_manifest_entries())


def build_non_sd_edit_profile_ids() -> tuple[str, ...]:
    return tuple(entry.id for entry in list_non_sd_edit_manifest_entries())


def build_non_sd_catalog_profile_ids() -> tuple[str, ...]:
    return build_non_sd_txt2img_profile_ids() + build_non_sd_edit_profile_ids()


def build_non_sd_runtime_adapter_map() -> dict[str, str]:
    return {
        entry.id: entry.runtime_adapter_id
        for entry in list_non_sd_manifest_entries()
        if entry.runtime_adapter_id
    }


def build_non_sd_shift_expectations() -> dict[str, float]:
    return {
        entry.id: float(entry.default_shift)
        for entry in list_non_sd_txt2img_manifest_entries()
        if entry.shift_visible and entry.default_shift is not None
    }


def build_non_sd_flux_guidance_expectations() -> dict[str, float]:
    return {
        entry.id: float(entry.default_flux_guidance)
        for entry in list_non_sd_txt2img_manifest_entries()
        if entry.flux_guidance_visible and entry.default_flux_guidance is not None
    }


def build_non_sd_prompt_enhancement_expectations() -> dict[str, bool]:
    return {
        entry.id: bool(entry.default_prompt_enhancement_enabled)
        for entry in list_non_sd_txt2img_manifest_entries()
        if entry.prompt_enhancement_visible
    }


def build_non_sd_edit_megapixels_expectations() -> dict[str, float]:
    return {
        entry.id: float(entry.default_edit_megapixels)
        for entry in list_non_sd_edit_manifest_entries()
        if entry.edit_megapixels_visible and entry.default_edit_megapixels is not None
    }


def build_diffusion_model_priority_hints_by_profile() -> dict[str, tuple[tuple[str, ...], ...]]:
    return {
        entry.id: entry.diffusion_model_priority_hints
        for entry in list_non_sd_manifest_entries()
        if entry.diffusion_model_priority_hints
    }


def build_diffusion_model_hints_by_profile() -> dict[str, tuple[str, ...]]:
    return {
        entry.id: entry.diffusion_model_hints
        for entry in list_non_sd_manifest_entries()
        if entry.diffusion_model_hints
    }


def build_diffusion_model_deny_hints_by_profile() -> dict[str, tuple[str, ...]]:
    return {
        entry.id: entry.diffusion_model_deny_hints
        for entry in list_non_sd_manifest_entries()
        if entry.diffusion_model_deny_hints
    }


def build_text_encoder_priority_hints_by_profile() -> dict[str, tuple[tuple[str, ...], ...]]:
    return {
        entry.id: entry.text_encoder_priority_hints
        for entry in list_non_sd_manifest_entries()
        if entry.text_encoder_priority_hints
    }


def build_text_encoder_hints_by_profile() -> dict[str, tuple[str, ...]]:
    return {
        entry.id: entry.text_encoder_hints
        for entry in list_non_sd_manifest_entries()
        if entry.text_encoder_hints
    }


def build_text_encoder_sequence_hints_by_profile() -> dict[str, tuple[tuple[tuple[str, ...], ...], ...]]:
    return {
        entry.id: entry.text_encoder_sequence_priority_hints
        for entry in list_non_sd_manifest_entries()
        if entry.text_encoder_sequence_priority_hints
    }


def build_aux_text_encoder_priority_hints_by_profile() -> dict[str, tuple[tuple[str, ...], ...]]:
    return {
        entry.id: entry.aux_text_encoder_priority_hints
        for entry in list_non_sd_manifest_entries()
        if entry.aux_text_encoder_priority_hints
    }


def build_template_lora_priority_hints_by_profile() -> dict[str, tuple[tuple[str, ...], ...]]:
    return {
        entry.id: entry.template_lora_priority_hints
        for entry in list_non_sd_manifest_entries()
        if entry.template_lora_priority_hints
    }


def build_vae_priority_hints_by_profile() -> dict[str, tuple[tuple[str, ...], ...]]:
    return {
        entry.id: entry.vae_priority_hints
        for entry in list_non_sd_manifest_entries()
        if entry.vae_priority_hints
    }


def build_vae_hints_by_profile() -> dict[str, tuple[str, ...]]:
    return {
        entry.id: entry.vae_hints
        for entry in list_non_sd_manifest_entries()
        if entry.vae_hints
    }


def build_vae_deny_hints_by_profile() -> dict[str, tuple[str, ...]]:
    return {
        entry.id: entry.vae_deny_hints
        for entry in list_non_sd_manifest_entries()
        if entry.vae_deny_hints
    }
