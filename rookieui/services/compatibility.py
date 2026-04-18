from __future__ import annotations

from typing import Any

from rookieui.contracts.compatibility import (
    CompatibilityCatalogSnapshot,
    CompatibilityOption,
    SamplerCatalogEntry,
    SchedulerCatalogEntry,
)
from rookieui.contracts.model_family_registry import list_model_family_registry_entries


_FALLBACK_SAMPLERS = [
    "euler",
    "euler_ancestral",
    "heun",
    "ddim",
    "res_multistep",
    "dpmpp_2m",
    "dpmpp_sde",
    "dpmpp_2m_sde",
    "uni_pc",
]
_SAMPLER_TITLE_OVERRIDES = {
    "euler": "Euler",
    "euler_ancestral": "Euler a",
    "heun": "Heun",
    "ddim": "DDIM",
    "res_multistep": "Res Multistep",
    "dpmpp_2m": "DPM++ 2M",
    "dpmpp_sde": "DPM++ SDE",
    "dpmpp_2m_sde": "DPM++ 2M SDE",
    "uni_pc": "UniPC",
    "uni_pc_bh2": "UniPC BH2",
}
_CORE_SAMPLERS = {
    "euler",
    "euler_ancestral",
    "ddim",
    "res_multistep",
    "dpmpp_2m",
    "dpmpp_sde",
    "dpmpp_2m_sde",
    "uni_pc",
}


def _load_comfy_samplers_module() -> Any:
    try:
        import comfy.samplers
    except ImportError:
        return None
    return comfy.samplers


def _coerce_catalog_values(values: object, fallback: list[str]) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return list(fallback)
    normalized = [str(value).strip() for value in values if str(value).strip()]
    return normalized or list(fallback)


def _titleize_sampler_id(sampler_id: str) -> str:
    if sampler_id in _SAMPLER_TITLE_OVERRIDES:
        return _SAMPLER_TITLE_OVERRIDES[sampler_id]
    return " ".join(part.upper() if part.isalpha() and len(part) <= 3 else part.title() for part in sampler_id.split("_"))


def _build_sampler_catalog() -> list[SamplerCatalogEntry]:
    comfy_samplers = _load_comfy_samplers_module()
    sampler_values = _coerce_catalog_values(
        getattr(getattr(comfy_samplers, "KSampler", None), "SAMPLERS", None),
        _FALLBACK_SAMPLERS,
    )
    return [
        SamplerCatalogEntry(
            id=sampler_id,
            title=_titleize_sampler_id(sampler_id),
            tier="core" if sampler_id in _CORE_SAMPLERS else "extended",
            default=sampler_id == "euler_ancestral",
            aliases=["euler a"] if sampler_id == "euler_ancestral" else [],
        )
        for sampler_id in sampler_values
    ]


def build_compatibility_payload() -> dict[str, object]:
    newer_family_profiles = [
        CompatibilityOption(
            id=entry.id,
            title=entry.title,
            summary=entry.compatibility_summary,
            experimental=entry.experimental,
            aliases=list(entry.aliases),
        )
        for entry in list_model_family_registry_entries()
        if entry.support_tier != "parity"
    ]
    snapshot = CompatibilityCatalogSnapshot(
        samplers=_build_sampler_catalog(),
        schedulers=[
            SchedulerCatalogEntry(
                id="normal",
                title="Normal",
                tier="core",
                default=True,
                aliases=["automatic"],
            ),
            SchedulerCatalogEntry(
                id="karras",
                title="Karras",
                tier="core",
                aliases=["dpm++ 2m karras", "euler karras"],
            ),
            SchedulerCatalogEntry(
                id="exponential",
                title="Exponential",
                tier="core",
            ),
            SchedulerCatalogEntry(
                id="sgm_uniform",
                title="SGM Uniform",
                tier="core",
                aliases=["sgmuniform"],
            ),
            SchedulerCatalogEntry(
                id="simple",
                title="Simple",
                tier="core",
            ),
            SchedulerCatalogEntry(
                id="ddim_uniform",
                title="DDIM Uniform",
                tier="extended",
                aliases=["ddim", "ddim uniform"],
            ),
            SchedulerCatalogEntry(
                id="beta",
                title="Beta",
                tier="extended",
            ),
            SchedulerCatalogEntry(
                id="linear_quadratic",
                title="Linear Quadratic",
                tier="extended",
                aliases=["linear quadratic"],
            ),
            SchedulerCatalogEntry(
                id="kl_optimal",
                title="KL Optimal",
                tier="extended",
                aliases=["kl optimal"],
            ),
        ],
        runtime_profiles=[
            CompatibilityOption(
                id="balanced",
                title="Balanced",
                summary="Default RookieUI runtime policy with no extra host-memory hints.",
                default=True,
            ),
            CompatibilityOption(
                id="always_offload",
                title="Always Offload",
                summary="Low-risk VRAM release policy for constrained hosts.",
            ),
            CompatibilityOption(
                id="async_queue",
                title="Async Queue",
                summary="Async swap intent without shared-memory pinning.",
            ),
            CompatibilityOption(
                id="async_shared",
                title="Async Shared",
                summary="Async plus shared-memory pinning hint for power users.",
                experimental=True,
            ),
        ],
        dtype_profiles=[
            CompatibilityOption(
                id="automatic",
                title="Automatic",
                summary="Use the host default diffusion weight dtype policy.",
                default=True,
            ),
            CompatibilityOption(
                id="automatic_fp16_lora",
                title="Automatic (fp16 LoRA)",
                summary="Keep the host default dtype while preferring fp16 LoRA execution.",
            ),
            CompatibilityOption(
                id="nf4",
                title="NF4",
                summary="Optional low-bit diffusion storage hint.",
                experimental=True,
            ),
            CompatibilityOption(
                id="fp4",
                title="FP4",
                summary="Optional fp4 diffusion storage hint.",
                experimental=True,
            ),
            CompatibilityOption(
                id="float8_e4m3fn",
                title="Float8 E4M3FN",
                summary="Optional float8-e4m3fn storage hint.",
                experimental=True,
                aliases=["float8-e4m3fn"],
            ),
            CompatibilityOption(
                id="float8_e5m2",
                title="Float8 E5M2",
                summary="Optional float8-e5m2 storage hint.",
                experimental=True,
                aliases=["float8-e5m2"],
            ),
        ],
        newer_family_profiles=newer_family_profiles,
    )
    return snapshot.to_payload()
