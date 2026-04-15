from __future__ import annotations

from rookieui.contracts.parity import A1111ParityProfile, SamplerAliasMap


_PARITY_PROFILES: tuple[A1111ParityProfile, ...] = (
    A1111ParityProfile(
        id="sd15",
        title="Stable Diffusion 1.5",
        base_family="sd15",
        prompt_encoder="clip_text_encode",
        default_width=512,
        default_height=512,
        default_steps=28,
        default_cfg_scale=7.0,
        default_sampler="euler_ancestral",
        default_scheduler="normal",
        default_clip_skip=1,
        supports_clip_skip=True,
        notes=[
            "Primary A1111 baseline for classic Stable Diffusion checkpoints.",
            "Uses standard CLIP text encoding and optional clip-skip projection.",
        ],
    ),
    A1111ParityProfile(
        id="sdxl",
        title="Stable Diffusion XL",
        base_family="sdxl",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=28,
        default_cfg_scale=7.0,
        default_sampler="dpmpp_2m",
        default_scheduler="karras",
        default_clip_skip=1,
        supports_clip_skip=False,
        notes=[
            "Uses SDXL dual-text-encoder semantics through CLIPTextEncodeSDXL.",
            "Acts as the baseline for SDXL-derived families in RookieUI parity lanes.",
        ],
    ),
    A1111ParityProfile(
        id="pony",
        title="Pony",
        base_family="sdxl",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=28,
        default_cfg_scale=7.0,
        default_sampler="dpmpp_2m",
        default_scheduler="karras",
        default_clip_skip=1,
        supports_clip_skip=False,
        notes=[
            "SDXL-derived parity lane with community-oriented defaults preserved as SDXL translation.",
        ],
    ),
    A1111ParityProfile(
        id="illustrious",
        title="Illustrious",
        base_family="sdxl",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=28,
        default_cfg_scale=7.0,
        default_sampler="dpmpp_2m",
        default_scheduler="karras",
        default_clip_skip=1,
        supports_clip_skip=False,
        notes=[
            "SDXL-derived parity lane retained as an explicit profile for A1111-style UX.",
        ],
    ),
    A1111ParityProfile(
        id="noob",
        title="Noob",
        base_family="sdxl",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=28,
        default_cfg_scale=7.0,
        default_sampler="dpmpp_2m",
        default_scheduler="karras",
        default_clip_skip=1,
        supports_clip_skip=False,
        notes=[
            "SDXL-derived parity lane retained as an explicit profile for rookie-safe defaults.",
        ],
    ),
    A1111ParityProfile(
        id="flux",
        title="Flux",
        base_family="sdxl",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=896,
        default_height=1152,
        default_steps=20,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="beta",
        default_clip_skip=1,
        supports_clip_skip=False,
        notes=[
            "Secondary newer-family lane routed through current SDXL graph translation seam.",
            "Keeps Text Encoder selector visible for family-specific host model routing.",
        ],
    ),
    A1111ParityProfile(
        id="qwen_image",
        title="Qwen-Image",
        base_family="sdxl",
        prompt_encoder="clip_text_encode_sdxl",
        # CRITICAL: RookieUI baseline does not auto-enable Lightning/acceleration LoRA;
        # keep Qwen defaults on the non-LoRA standard path to avoid low-quality/unstable outputs.
        default_width=1328,
        default_height=1328,
        default_steps=50,
        default_cfg_scale=4.0,
        default_sampler="euler",
        default_scheduler="simple",
        default_clip_skip=1,
        supports_clip_skip=False,
        notes=[
            "Secondary newer-family lane routed through current SDXL graph translation seam.",
            "Uses non-Lightning baseline defaults; Lightning variants remain opt-in via explicit LoRA/model selection.",
            "Keeps Text Encoder selector visible for family-specific host model routing.",
        ],
    ),
    A1111ParityProfile(
        id="klein",
        title="Klein (Flux.2)",
        base_family="sdxl",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=896,
        default_height=1152,
        default_steps=20,
        default_cfg_scale=1.0,
        default_sampler="euler",
        default_scheduler="beta",
        default_clip_skip=1,
        supports_clip_skip=False,
        notes=[
            "Secondary newer-family lane following the current Flux-style adapter defaults.",
            "Keeps Text Encoder selector visible for family-specific host model routing.",
        ],
    ),
    A1111ParityProfile(
        id="lumina",
        title="Lumina",
        base_family="sdxl",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=16,
        default_cfg_scale=2.0,
        default_sampler="dpmpp_2m",
        default_scheduler="normal",
        default_clip_skip=1,
        supports_clip_skip=False,
        notes=[
            "Secondary newer-family lane routed through the existing SDXL translation seam.",
            "Keeps Text Encoder selector visible for family-specific host model routing.",
        ],
    ),
    A1111ParityProfile(
        id="zit",
        title="ZiT (Z-Image-Turbo)",
        base_family="sdxl",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=8,
        default_cfg_scale=1.0,
        default_sampler="res_multistep",
        default_scheduler="simple",
        default_clip_skip=1,
        supports_clip_skip=False,
        notes=[
            "Secondary turbo-family lane with low-step defaults for rapid iteration.",
            "Keeps Text Encoder selector visible for family-specific host model routing.",
        ],
    ),
    A1111ParityProfile(
        id="wan",
        title="Wan",
        base_family="sdxl",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=832,
        default_height=1216,
        default_steps=20,
        # IMPORTANT: Wan Lightning 4-step paths use low cfg (around 1.0), but RookieUI default flow is non-Lightning.
        default_cfg_scale=6.0,
        default_sampler="euler",
        default_scheduler="simple",
        default_clip_skip=1,
        supports_clip_skip=False,
        notes=[
            "Secondary newer-family lane routed through the existing SDXL translation seam.",
            "Uses non-Lightning baseline defaults; acceleration LoRA remains explicit opt-in.",
            "Keeps Text Encoder selector visible for family-specific host model routing.",
        ],
    ),
    A1111ParityProfile(
        id="anima",
        title="Anima",
        base_family="sdxl",
        prompt_encoder="clip_text_encode_sdxl",
        default_width=1024,
        default_height=1024,
        default_steps=20,
        default_cfg_scale=2.0,
        default_sampler="dpmpp_2m",
        default_scheduler="karras",
        default_clip_skip=1,
        supports_clip_skip=False,
        notes=[
            "Secondary newer-family lane routed through the existing SDXL translation seam.",
            "Keeps Text Encoder selector visible for family-specific host model routing.",
        ],
    ),
)

_SAMPLER_ALIAS_MAP = SamplerAliasMap(
    samplers={
        "euler a": "euler_ancestral",
        "euler": "euler",
        "dpm++ 2m": "dpmpp_2m",
        "dpm++ 2m sde": "dpmpp_2m_sde",
        "dpm++ sde": "dpmpp_sde",
        "ddim": "ddim",
        "uni_pc": "uni_pc",
        "uni_pc_bh2": "uni_pc_bh2",
    },
    scheduler_aliases={
        "automatic": "normal",
        "ddim": "ddim_uniform",
        "ddim_uniform": "ddim_uniform",
        "ddim uniform": "ddim_uniform",
        "beta": "beta",
        "linear_quadratic": "linear_quadratic",
        "linear quadratic": "linear_quadratic",
        "kl_optimal": "kl_optimal",
        "kl optimal": "kl_optimal",
    },
    scheduler_overrides={
        "dpm++ 2m karras": "karras",
        "dpm++ 2m sde karras": "karras",
        "euler karras": "karras",
    },
    supported_schedulers=[
        "normal",
        "karras",
        "exponential",
        "sgm_uniform",
        "simple",
        "ddim_uniform",
        "beta",
        "linear_quadratic",
        "kl_optimal",
    ],
)


def list_parity_profiles() -> list[A1111ParityProfile]:
    return list(_PARITY_PROFILES)


def build_parity_payload() -> dict[str, object]:
    return {
        "profiles": [profile.to_payload() for profile in _PARITY_PROFILES],
        "sampler_aliases": _SAMPLER_ALIAS_MAP.to_payload(),
    }


def get_parity_profile(profile_name: str) -> A1111ParityProfile:
    normalized = (profile_name or "").strip().lower()
    if not normalized:
        normalized = "sd15"

    for profile in _PARITY_PROFILES:
        if profile.id == normalized:
            return profile

    raise ValueError(f"Unsupported RookieUI parity profile: {profile_name}")


def normalize_sampler_name(name: str | None) -> str:
    normalized = (name or "").strip().lower()
    if not normalized:
        return ""
    return _SAMPLER_ALIAS_MAP.samplers.get(normalized, normalized.replace(" ", "_"))


def normalize_scheduler_name(
    sampler_name: str | None,
    scheduler_name: str | None,
    *,
    default_scheduler: str,
) -> str:
    normalized_scheduler = (scheduler_name or "").strip().lower().replace(" ", "_")
    normalized_sampler = (sampler_name or "").strip().lower()
    normalized_scheduler = _SAMPLER_ALIAS_MAP.scheduler_aliases.get(
        normalized_scheduler,
        normalized_scheduler,
    )

    if normalized_scheduler:
        if normalized_scheduler not in _SAMPLER_ALIAS_MAP.supported_schedulers:
            raise ValueError(f"Unsupported RookieUI scheduler: {scheduler_name}")
        return normalized_scheduler

    override = _SAMPLER_ALIAS_MAP.scheduler_overrides.get(normalized_sampler)
    if override:
        return override

    return default_scheduler


def get_sampler_alias_payload() -> dict[str, object]:
    return _SAMPLER_ALIAS_MAP.to_payload()
