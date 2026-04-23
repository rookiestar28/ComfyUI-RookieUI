from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from rookieui.contracts.xyz_plot import (
    XYZ_PLOT_SUPPORT_TIERS,
    XYZPlotAxisContract,
    build_xyz_plot_axis_support_payload,
    build_xyz_plot_contract_meta,
)
from rookieui.services.compatibility import build_compatibility_payload
from rookieui.services.model_inventory import discover_model_inventory

_XYZ_AXIS_COSTS = {
    "seed": "low",
    "steps": "high",
    "cfg_scale": "medium",
    "sampler": "high",
    "scheduler": "medium",
    "checkpoint_name": "very_high",
    "vae": "high",
    "clip_skip": "medium",
    "size": "high",
    "denoising_strength": "medium",
    "hires_steps": "high",
    "hires_upscaler": "high",
    "var_seed": "low",
    "var_strength": "medium",
    "prompt_sr": "medium",
    "prompt_order": "medium",
    "styles": "not_supported",
    "face_restore": "not_supported",
    "refiner_checkpoint": "not_supported",
    "refiner_switch_at": "not_supported",
    "token_merging_ratio": "not_supported",
    "rng_source": "not_supported",
    "fp8_mode": "not_supported",
}
_XYZ_SESSION_RUNNER_UNSUPPORTED_AXES = {"var_seed", "var_strength"}
_HIRES_UPSCALER_CHOICE_SPECS = (
    ("bilinear", "Latent", ["bilinear", "Bilinear"]),
    ("bicubic", "Latent (bicubic)", ["bicubic", "Bicubic"]),
    ("nearest-exact", "Latent (nearest-exact)", ["nearest-exact", "nearest exact", "Nearest Exact"]),
    ("area", "Area", ["area"]),
    ("bislerp", "Bislerp", ["bislerp"]),
)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _build_choice_entry(
    *,
    value: str,
    label: str,
    aliases: list[str] | None = None,
    allow_partial_match: bool = False,
) -> dict[str, Any]:
    return {
        "value": str(value).strip(),
        "label": str(label).strip(),
        "aliases": _dedupe_preserve_order([str(alias).strip() for alias in (aliases or []) if str(alias).strip()]),
        "allow_partial_match": bool(allow_partial_match),
    }


def _compatibility_sampler_choices() -> list[str]:
    payload = build_compatibility_payload()
    samplers = payload.get("samplers", [])
    if not isinstance(samplers, list):
        return []
    return [str(entry.get("id")).strip() for entry in samplers if isinstance(entry, dict) and str(entry.get("id")).strip()]


def _compatibility_scheduler_choices() -> list[str]:
    payload = build_compatibility_payload()
    schedulers = payload.get("schedulers", [])
    if not isinstance(schedulers, list):
        return []
    return [str(entry.get("id")).strip() for entry in schedulers if isinstance(entry, dict) and str(entry.get("id")).strip()]


def _compatibility_sampler_choice_entries() -> list[dict[str, Any]]:
    payload = build_compatibility_payload()
    samplers = payload.get("samplers", [])
    if not isinstance(samplers, list):
        return []
    entries: list[dict[str, Any]] = []
    for raw_entry in samplers:
        if not isinstance(raw_entry, dict):
            continue
        sampler_id = str(raw_entry.get("id", "")).strip()
        label = str(raw_entry.get("title", "") or sampler_id).strip()
        if not sampler_id or not label:
            continue
        aliases = [sampler_id, *[str(alias).strip() for alias in raw_entry.get("aliases", []) or []]]
        entries.append(_build_choice_entry(value=sampler_id, label=label, aliases=aliases))
    return entries


def _compatibility_scheduler_choice_entries() -> list[dict[str, Any]]:
    payload = build_compatibility_payload()
    schedulers = payload.get("schedulers", [])
    if not isinstance(schedulers, list):
        return []
    entries: list[dict[str, Any]] = []
    for raw_entry in schedulers:
        if not isinstance(raw_entry, dict):
            continue
        scheduler_id = str(raw_entry.get("id", "")).strip()
        raw_label = str(raw_entry.get("title", "") or scheduler_id).strip()
        if scheduler_id == "normal":
            raw_label = "Automatic"
        if not scheduler_id or not raw_label:
            continue
        aliases = [scheduler_id, *[str(alias).strip() for alias in raw_entry.get("aliases", []) or []]]
        entries.append(_build_choice_entry(value=scheduler_id, label=raw_label, aliases=aliases))
    return entries


def _checkpoint_choice_entries() -> list[dict[str, Any]]:
    inventory = discover_model_inventory()
    entries: list[dict[str, Any]] = []
    for selector in list(inventory.checkpoints or []):
        normalized_selector = str(selector).strip()
        if not normalized_selector:
            continue
        basename = PurePosixPath(normalized_selector.replace("\\", "/")).name
        aliases = [basename] if basename and basename != normalized_selector else []
        entries.append(
            _build_choice_entry(
                value=normalized_selector,
                label=normalized_selector,
                aliases=aliases,
                allow_partial_match=True,
            )
        )
    return entries


def _vae_choice_entries() -> list[dict[str, Any]]:
    inventory = discover_model_inventory()
    entries = [
        _build_choice_entry(value="Automatic", label="Automatic", aliases=["auto"]),
        _build_choice_entry(value="None", label="None"),
    ]
    for selector in list(inventory.vae or []):
        normalized_selector = str(selector).strip()
        if not normalized_selector or normalized_selector in {"Automatic", "None"}:
            continue
        entries.append(_build_choice_entry(value=normalized_selector, label=normalized_selector))
    return entries


def _hires_upscaler_choice_entries() -> list[dict[str, Any]]:
    return [
        _build_choice_entry(value=value, label=label, aliases=aliases)
        for value, label, aliases in _HIRES_UPSCALER_CHOICE_SPECS
    ]


def _axis_choice_entries(axis_id: str) -> list[dict[str, Any]]:
    if axis_id == "sampler":
        return _compatibility_sampler_choice_entries()
    if axis_id == "scheduler":
        return _compatibility_scheduler_choice_entries()
    if axis_id == "checkpoint_name":
        return _checkpoint_choice_entries()
    if axis_id == "vae":
        return _vae_choice_entries()
    if axis_id == "hires_upscaler":
        return _hires_upscaler_choice_entries()
    return []


def _axis_dynamic_choices(axis_id: str) -> tuple[list[str], str]:
    inventory = discover_model_inventory()
    if axis_id == "sampler":
        return ([entry["label"] for entry in _compatibility_sampler_choice_entries()], "compatibility.samplers")
    if axis_id == "scheduler":
        return ([entry["label"] for entry in _compatibility_scheduler_choice_entries()], "compatibility.schedulers")
    if axis_id == "checkpoint_name":
        return (list(inventory.checkpoints or []), "model_inventory.checkpoints")
    if axis_id == "vae":
        return ([entry["label"] for entry in _vae_choice_entries()], "model_inventory.vae")
    if axis_id == "hires_upscaler":
        return ([entry["label"] for entry in _hires_upscaler_choice_entries()], "rookieui.fixed.hires_upscale_method")
    if axis_id == "clip_skip":
        return (["1", "2", "3", "4"], "rookieui.fixed.clip_skip")
    return ([], "")


def _build_axis_payload(axis: XYZPlotAxisContract) -> dict[str, Any]:
    choices, choice_source = _axis_dynamic_choices(axis.axis_id)
    choice_entries = _axis_choice_entries(axis.axis_id)
    return {
        "axis_id": axis.axis_id,
        "title": axis.title,
        "support_tier": axis.support_tier,
        "mode_scopes": list(axis.mode_scopes),
        "value_input_mode": axis.value_input_mode,
        "a1111_reference_label": axis.a1111_reference_label,
        "notes": list(axis.notes),
        "estimated_mutation_cost": _XYZ_AXIS_COSTS.get(axis.axis_id, "medium"),
        "choices": choices,
        "choice_entries": choice_entries,
        "choice_source": choice_source,
        "truthfulness": "runnable" if axis.support_tier in {"direct", "adapted"} else "gated",
        "session_runner_support": axis.support_tier in {"direct", "adapted"}
        and axis.axis_id not in _XYZ_SESSION_RUNNER_UNSUPPORTED_AXES,
    }


def get_xyz_plot_axis_contracts() -> dict[str, XYZPlotAxisContract]:
    support_payload = build_xyz_plot_axis_support_payload()
    axes_payload = support_payload.get("axes", {})
    if not isinstance(axes_payload, list):
        return {}
    contracts: dict[str, XYZPlotAxisContract] = {}
    for raw_axis in axes_payload:
        if not isinstance(raw_axis, dict):
            continue
        axis_id = str(raw_axis.get("axis_id", "")).strip()
        if not axis_id:
            continue
        contracts[axis_id] = XYZPlotAxisContract(
            axis_id=axis_id,
            title=str(raw_axis.get("title", axis_id)),
            support_tier=str(raw_axis.get("support_tier", "")),
            mode_scopes=tuple(raw_axis.get("mode_scopes", []) or ()),
            value_input_mode=str(raw_axis.get("value_input_mode", "")),
            a1111_reference_label=str(raw_axis.get("a1111_reference_label", "")),
            notes=tuple(raw_axis.get("notes", []) or ()),
        )
    return contracts


def resolve_xyz_axis_contract(axis_id: object) -> XYZPlotAxisContract:
    normalized_axis_id = str(axis_id or "").strip()
    contracts = get_xyz_plot_axis_contracts()
    contract = contracts.get(normalized_axis_id)
    if contract is None:
        raise ValueError(f"Unknown xyz axis: {normalized_axis_id or '<empty>'}.")
    return contract


def get_xyz_axis_choices(axis_id: object) -> list[str]:
    contract = resolve_xyz_axis_contract(axis_id)
    return _build_axis_payload(contract)["choices"]


def get_xyz_axis_choice_entries(axis_id: object) -> list[dict[str, Any]]:
    contract = resolve_xyz_axis_contract(axis_id)
    entries = _build_axis_payload(contract).get("choice_entries", [])
    return list(entries) if isinstance(entries, list) else []


def build_xyz_plot_axes_payload() -> dict[str, Any]:
    contracts = get_xyz_plot_axis_contracts()
    axes = {axis_id: _build_axis_payload(contract) for axis_id, contract in contracts.items()}
    summary = {tier: 0 for tier in XYZ_PLOT_SUPPORT_TIERS}
    for axis_payload in axes.values():
        tier = str(axis_payload.get("support_tier", ""))
        if tier in summary:
            summary[tier] += 1
    return {
        "contract": build_xyz_plot_contract_meta(surface="xyz_plot_axes"),
        "supported_modes": ["txt2img", "img2img"],
        "support_tiers": list(XYZ_PLOT_SUPPORT_TIERS),
        "summary": summary,
        "axes": axes,
    }
