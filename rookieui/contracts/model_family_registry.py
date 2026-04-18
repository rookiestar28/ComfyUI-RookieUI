from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

MODEL_FAMILY_REGISTRY_CONTRACT_VERSION = "f72-20260418b"


@dataclass(frozen=True)
class ModelFamilyRegistryEntry:
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
    support_tier: str
    compatibility_summary: str
    experimental: bool = False
    aliases: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


_MODEL_FAMILY_REGISTRY: tuple[ModelFamilyRegistryEntry, ...] = (
    ModelFamilyRegistryEntry(
        id="sd15",
        title="Stable Diffusion 1.5",
        translation_base_family="sd15",
        public_base_family="sd15",
        prompt_encoder="clip_text_encode",
        default_width=512,
        default_height=512,
        default_steps=28,
        default_cfg_scale=7.0,
        default_sampler="euler_ancestral",
        default_scheduler="normal",
        default_clip_skip=1,
        supports_clip_skip=True,
        primary_model_category="checkpoints",
        text_encoder_visible=False,
        support_tier="parity",
        compatibility_summary="Primary A1111 parity baseline for classic Stable Diffusion checkpoints.",
        notes=(
            "Primary A1111 baseline for classic Stable Diffusion checkpoints.",
            "Uses standard CLIP text encoding and optional clip-skip projection.",
        ),
    ),
    ModelFamilyRegistryEntry(
        id="sdxl",
        title="Stable Diffusion XL",
        translation_base_family="sdxl",
        public_base_family="sdxl",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=28,
        default_cfg_scale=7.0,
        default_sampler="dpmpp_2m",
        default_scheduler="karras",
        default_clip_skip=1,
        supports_clip_skip=False,
        primary_model_category="checkpoints",
        text_encoder_visible=False,
        support_tier="parity",
        compatibility_summary="Primary SDXL parity baseline with dual-text-encoder semantics.",
        notes=(
            "Uses SDXL dual-text-encoder semantics through CLIPTextEncodeSDXL.",
            "Acts as the baseline for SDXL-derived families in RookieUI parity lanes.",
        ),
    ),
    ModelFamilyRegistryEntry(
        id="pony",
        title="Pony",
        translation_base_family="sdxl",
        public_base_family="sdxl",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=28,
        default_cfg_scale=7.0,
        default_sampler="dpmpp_2m",
        default_scheduler="karras",
        default_clip_skip=1,
        supports_clip_skip=False,
        primary_model_category="checkpoints",
        text_encoder_visible=False,
        support_tier="parity",
        compatibility_summary="SDXL-derived parity lane with preserved Pony-facing defaults.",
        notes=("SDXL-derived parity lane with community-oriented defaults preserved as SDXL translation.",),
    ),
    ModelFamilyRegistryEntry(
        id="illustrious",
        title="Illustrious",
        translation_base_family="sdxl",
        public_base_family="sdxl",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=28,
        default_cfg_scale=7.0,
        default_sampler="dpmpp_2m",
        default_scheduler="karras",
        default_clip_skip=1,
        supports_clip_skip=False,
        primary_model_category="checkpoints",
        text_encoder_visible=False,
        support_tier="parity",
        compatibility_summary="SDXL-derived parity lane retained as an explicit profile.",
        notes=("SDXL-derived parity lane retained as an explicit profile for A1111-style UX.",),
    ),
    ModelFamilyRegistryEntry(
        id="noob",
        title="Noob",
        translation_base_family="sdxl",
        public_base_family="sdxl",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=28,
        default_cfg_scale=7.0,
        default_sampler="dpmpp_2m",
        default_scheduler="karras",
        default_clip_skip=1,
        supports_clip_skip=False,
        primary_model_category="checkpoints",
        text_encoder_visible=False,
        support_tier="parity",
        compatibility_summary="SDXL-derived parity lane retained for rookie-safe defaults.",
        notes=("SDXL-derived parity lane retained as an explicit profile for rookie-safe defaults.",),
    ),
    ModelFamilyRegistryEntry(
        id="flux",
        title="Flux",
        translation_base_family="sdxl",
        public_base_family="flux",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=896,
        default_height=1152,
        default_steps=20,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="beta",
        default_clip_skip=1,
        supports_clip_skip=False,
        primary_model_category="diffusion_models",
        text_encoder_visible=True,
        support_tier="family-adapted",
        compatibility_summary="Experimental newer-family catalog entry routed through the current SDXL graph seam.",
        experimental=True,
        notes=(
            "Secondary newer-family lane routed through current SDXL graph translation seam.",
            "Keeps Text Encoder selector visible for family-specific host model routing.",
        ),
    ),
    ModelFamilyRegistryEntry(
        id="qwen_image",
        title="Qwen-Image",
        translation_base_family="sdxl",
        public_base_family="qwen_image",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=1328,
        default_height=1328,
        default_steps=50,
        default_cfg_scale=4.0,
        default_sampler="euler",
        default_scheduler="simple",
        default_clip_skip=1,
        supports_clip_skip=False,
        primary_model_category="diffusion_models",
        text_encoder_visible=True,
        support_tier="family-adapted",
        compatibility_summary="Experimental newer-family catalog entry using the non-Lightning Qwen baseline on the current SDXL seam.",
        experimental=True,
        aliases=("qwen image",),
        notes=(
            "Secondary newer-family lane routed through current SDXL graph translation seam.",
            "Uses non-Lightning baseline defaults; Lightning variants remain opt-in via explicit LoRA/model selection.",
            "Keeps Text Encoder selector visible for family-specific host model routing.",
        ),
    ),
    ModelFamilyRegistryEntry(
        id="klein",
        title="Klein (Flux.2)",
        translation_base_family="sdxl",
        public_base_family="klein",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=896,
        default_height=1152,
        default_steps=20,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="beta",
        default_clip_skip=1,
        supports_clip_skip=False,
        primary_model_category="diffusion_models",
        text_encoder_visible=True,
        support_tier="family-adapted",
        compatibility_summary="Experimental newer-family catalog entry following current Flux-style adapter defaults.",
        experimental=True,
        aliases=("flux.2",),
        notes=(
            "Secondary newer-family lane following the current Flux-style adapter defaults.",
            "Keeps Text Encoder selector visible for family-specific host model routing.",
        ),
    ),
    ModelFamilyRegistryEntry(
        id="lumina",
        title="Lumina",
        translation_base_family="sdxl",
        public_base_family="lumina",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=16,
        default_cfg_scale=2.0,
        default_sampler="dpmpp_2m",
        default_scheduler="normal",
        default_clip_skip=1,
        supports_clip_skip=False,
        primary_model_category="diffusion_models",
        text_encoder_visible=True,
        support_tier="family-adapted",
        compatibility_summary="Experimental newer-family catalog entry routed through the current SDXL seam.",
        experimental=True,
        notes=(
            "Secondary newer-family lane routed through the existing SDXL translation seam.",
            "Keeps Text Encoder selector visible for family-specific host model routing.",
        ),
    ),
    ModelFamilyRegistryEntry(
        id="zit",
        title="ZiT (Z-Image-Turbo)",
        translation_base_family="sdxl",
        public_base_family="zit",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=8,
        default_cfg_scale=1.0,
        default_sampler="res_multistep",
        default_scheduler="simple",
        default_clip_skip=1,
        supports_clip_skip=False,
        primary_model_category="diffusion_models",
        text_encoder_visible=True,
        support_tier="family-adapted",
        compatibility_summary="Experimental turbo-family catalog entry with low-step defaults on the current SDXL seam.",
        experimental=True,
        aliases=("z-image-turbo", "zit"),
        notes=(
            "Secondary turbo-family lane with low-step defaults for rapid iteration.",
            "Keeps Text Encoder selector visible for family-specific host model routing.",
        ),
    ),
    ModelFamilyRegistryEntry(
        id="wan",
        title="Wan",
        translation_base_family="sdxl",
        public_base_family="wan",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=832,
        default_height=1216,
        default_steps=20,
        default_cfg_scale=6.0,
        default_sampler="euler",
        default_scheduler="simple",
        default_clip_skip=1,
        supports_clip_skip=False,
        primary_model_category="diffusion_models",
        text_encoder_visible=True,
        support_tier="family-adapted",
        compatibility_summary="Experimental newer-family catalog entry using the non-Lightning Wan baseline on the current SDXL seam.",
        experimental=True,
        notes=(
            "Secondary newer-family lane routed through the existing SDXL translation seam.",
            "Uses non-Lightning baseline defaults; acceleration LoRA remains explicit opt-in.",
            "Keeps Text Encoder selector visible for family-specific host model routing.",
        ),
    ),
    ModelFamilyRegistryEntry(
        id="anima",
        title="Anima",
        translation_base_family="sdxl",
        public_base_family="anima",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=20,
        default_cfg_scale=2.0,
        default_sampler="dpmpp_2m",
        default_scheduler="karras",
        default_clip_skip=1,
        supports_clip_skip=False,
        primary_model_category="diffusion_models",
        text_encoder_visible=True,
        support_tier="family-adapted",
        compatibility_summary="Experimental newer-family catalog entry routed through the current SDXL seam.",
        experimental=True,
        notes=(
            "Secondary newer-family lane routed through the existing SDXL translation seam.",
            "Keeps Text Encoder selector visible for family-specific host model routing.",
        ),
    ),
    ModelFamilyRegistryEntry(
        id="ernie_image",
        title="ERNIE-Image",
        translation_base_family="sdxl",
        public_base_family="ernie_image",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=20,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="beta",
        default_clip_skip=1,
        supports_clip_skip=False,
        primary_model_category="diffusion_models",
        text_encoder_visible=True,
        support_tier="family-adapted",
        compatibility_summary="Experimental newer-family catalog entry for host-native ERNIE-Image support on the current diffusion-model workflow seam.",
        experimental=True,
        aliases=("ernie-image", "ernie image"),
        notes=(
            "Uses the host-native ERNIE / Ministral3 text encoder path rather than claiming A1111 prompt parity.",
            "Keeps Text Encoder selector visible because ERNIE-Image routing depends on explicit host text encoder pairing.",
        ),
    ),
)


def list_model_family_registry_entries() -> list[ModelFamilyRegistryEntry]:
    return list(_MODEL_FAMILY_REGISTRY)


def get_model_family_registry_entry(family_id: str) -> ModelFamilyRegistryEntry:
    normalized = (family_id or "").strip().lower()
    if not normalized:
        normalized = "sd15"
    for entry in _MODEL_FAMILY_REGISTRY:
        if entry.id == normalized:
            return entry
    raise ValueError(f"Unsupported RookieUI model family: {family_id}")


def build_model_family_registry_payload() -> dict[str, object]:
    return {
        "contract_version": MODEL_FAMILY_REGISTRY_CONTRACT_VERSION,
        "entries": [entry.to_payload() for entry in _MODEL_FAMILY_REGISTRY],
    }


def build_primary_model_category_by_family() -> dict[str, str]:
    return {entry.id: entry.primary_model_category for entry in _MODEL_FAMILY_REGISTRY}
