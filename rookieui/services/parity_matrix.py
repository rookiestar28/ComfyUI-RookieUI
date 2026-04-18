from __future__ import annotations

from rookieui.contracts.model_family_registry import (
    get_model_family_registry_entry,
    list_model_family_registry_entries,
)
from rookieui.contracts.parity import A1111ParityProfile, SamplerAliasMap

def _build_parity_profile(entry_id: str) -> A1111ParityProfile:
    entry = get_model_family_registry_entry(entry_id)
    return A1111ParityProfile(
        id=entry.id,
        title=entry.title,
        base_family=entry.translation_base_family,
        prompt_encoder=entry.prompt_encoder,
        default_width=entry.default_width,
        default_height=entry.default_height,
        default_steps=entry.default_steps,
        default_cfg_scale=entry.default_cfg_scale,
        default_sampler=entry.default_sampler,
        default_scheduler=entry.default_scheduler,
        default_clip_skip=entry.default_clip_skip,
        supports_clip_skip=entry.supports_clip_skip,
        notes=list(entry.notes),
    )


_PARITY_PROFILES: tuple[A1111ParityProfile, ...] = tuple(
    _build_parity_profile(entry.id) for entry in list_model_family_registry_entries()
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
    return _build_parity_profile(profile_name)


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
