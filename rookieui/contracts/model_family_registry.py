from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

MODEL_FAMILY_REGISTRY_CONTRACT_VERSION = "f151-20260418"


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
    shift_visible: bool
    default_shift: float | None
    flux_guidance_visible: bool
    default_flux_guidance: float | None
    prompt_enhancement_visible: bool
    default_prompt_enhancement_enabled: bool
    support_tier: str
    compatibility_summary: str
    experimental: bool = False
    aliases: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


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
) -> ModelFamilyRegistryEntry:
    prompt_encoder = "clip_text_encode" if translation_base_family == "sd15" else "clip_text_encode_sdxl"
    return ModelFamilyRegistryEntry(
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
    shift_visible: bool = False,
    default_shift: float | None = None,
    flux_guidance_visible: bool = False,
    default_flux_guidance: float | None = None,
    prompt_enhancement_visible: bool = False,
    default_prompt_enhancement_enabled: bool = False,
) -> ModelFamilyRegistryEntry:
    return ModelFamilyRegistryEntry(
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
        support_tier="family-adapted",
        compatibility_summary=compatibility_summary,
        experimental=True,
        aliases=aliases,
        notes=notes,
    )


_MODEL_FAMILY_REGISTRY: tuple[ModelFamilyRegistryEntry, ...] = (
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
    ),
    _template_entry(
        id="ernie_image",
        title="ERNIE-Image",
        public_base_family="ernie_image",
        default_width=1024,
        default_height=1024,
        default_steps=40,
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
        ),
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
    ),
    _template_entry(
        id="qwen_image",
        title="Qwen-Image 2512",
        public_base_family="qwen_image",
        default_width=1328,
        default_height=1328,
        default_steps=2,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="simple",
        compatibility_summary="Official ComfyUI Qwen-Image 2512 template preset on the current non-SD translation seam.",
        aliases=("qwen image", "qwen-image 2512", "qwen image 2512"),
        notes=(
            "Matches the official Qwen-Image 2512 template defaults.",
            "Text Encoder selector stays hidden because the official template owns the fixed qwen_2.5_vl pairing and template-baked LoRA.",
        ),
        shift_visible=True,
        default_shift=3.0,
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
    ),
)


def list_model_family_registry_entries() -> list[ModelFamilyRegistryEntry]:
    return list(_MODEL_FAMILY_REGISTRY)


def _normalized_aliases(entry: ModelFamilyRegistryEntry) -> tuple[str, ...]:
    return tuple(str(alias or "").strip().lower() for alias in entry.aliases if str(alias or "").strip())


def get_model_family_registry_entry(family_id: str) -> ModelFamilyRegistryEntry:
    normalized = (family_id or "").strip().lower()
    if not normalized:
        normalized = "sd15"
    for entry in _MODEL_FAMILY_REGISTRY:
        if entry.id == normalized:
            return entry
        if normalized in _normalized_aliases(entry):
            return entry
    raise ValueError(f"Unsupported RookieUI model family: {family_id}")


def build_model_family_registry_payload() -> dict[str, object]:
    return {
        "contract_version": MODEL_FAMILY_REGISTRY_CONTRACT_VERSION,
        "entries": [entry.to_payload() for entry in _MODEL_FAMILY_REGISTRY],
    }


def build_primary_model_category_by_family() -> dict[str, str]:
    category_map: dict[str, str] = {}
    for entry in _MODEL_FAMILY_REGISTRY:
        category_map[entry.id] = entry.primary_model_category
        public_base_family = str(entry.public_base_family or "").strip().lower()
        if public_base_family and public_base_family not in category_map:
            category_map[public_base_family] = entry.primary_model_category
        for alias in _normalized_aliases(entry):
            category_map[alias] = entry.primary_model_category
    return category_map
