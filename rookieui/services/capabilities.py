from __future__ import annotations

from rookieui.contracts.capabilities import RookieUICapabilitiesSnapshot
from rookieui.security.asset_guard import normalize_metadata_text
from rookieui.services.version import build_runtime_metadata_payload


def _normalize_metadata_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [normalize_metadata_text(value) for value in values if isinstance(value, str) and value.strip()]


def _normalize_metadata_mapping(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {}
    normalized: dict[str, object] = {}
    for key, value in payload.items():
        normalized_key = normalize_metadata_text(key)
        if not normalized_key:
            continue
        if isinstance(value, str) and value.strip():
            normalized[normalized_key] = normalize_metadata_text(value)
            continue
        normalized_list = _normalize_metadata_list(value)
        if normalized_list:
            normalized[normalized_key] = normalized_list
    return normalized


def _normalize_loose_mapping(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {}
    normalized: dict[str, object] = {}
    for key, value in payload.items():
        normalized_key = normalize_metadata_text(key)
        if not normalized_key:
            continue
        if isinstance(value, str):
            normalized[normalized_key] = normalize_metadata_text(value)
        elif isinstance(value, bool):
            normalized[normalized_key] = value
        elif isinstance(value, (int, float)):
            normalized[normalized_key] = value
        elif isinstance(value, list):
            normalized[normalized_key] = [
                normalize_metadata_text(entry) if isinstance(entry, str) else entry
                for entry in value
                if isinstance(entry, (str, int, float, bool))
            ]
        elif isinstance(value, dict):
            nested = _normalize_loose_mapping(value)
            if nested:
                normalized[normalized_key] = nested
    return normalized


def _normalize_runtime_payload(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {
            "shell_version": "",
            "build_fingerprint": "",
        }
    return {
        "shell_version": normalize_metadata_text(payload.get("shell_version", "")),
        "build_fingerprint": normalize_metadata_text(payload.get("build_fingerprint", "")),
    }


def _normalize_prompt_semantics_payload(payload: dict[str, object]) -> dict[str, object]:
    normalized = {
        "contract_version": normalize_metadata_text(payload.get("contract_version", "")),
        "contract_scope": normalize_metadata_text(payload.get("contract_scope", "")),
        "rollout": {},
        "compiler_constraints": {},
        "warning_codes": {},
        "capabilities": [],
    }
    rollout = payload.get("rollout", {})
    normalized["rollout"] = _normalize_metadata_mapping(rollout)
    constraints = payload.get("compiler_constraints", {})
    if isinstance(constraints, dict):
        normalized["compiler_constraints"] = {
            "conditioning_nodes": _normalize_metadata_list(constraints.get("conditioning_nodes", [])),
            "execution_backend": normalize_metadata_text(constraints.get("execution_backend", "")),
        }
    normalized["warning_codes"] = _normalize_metadata_mapping(payload.get("warning_codes", {}))
    capabilities = payload.get("capabilities", [])
    if isinstance(capabilities, list):
        normalized_capabilities = []
        for capability in capabilities:
            if not isinstance(capability, dict):
                continue
            normalized_capabilities.append(
                {
                    "id": normalize_metadata_text(capability.get("id", "")),
                    "title": normalize_metadata_text(capability.get("title", "")),
                    "a1111_semantics": normalize_metadata_text(capability.get("a1111_semantics", "")),
                    "rookieui_contract": normalize_metadata_text(capability.get("rookieui_contract", "")),
                    "status": normalize_metadata_text(capability.get("status", "")),
                    "translation": normalize_metadata_text(capability.get("translation", "")),
                    "reference": normalize_metadata_text(capability.get("reference", "")),
                }
            )
        normalized["capabilities"] = normalized_capabilities
    return normalized


def _normalize_adetailer_payload(payload: dict[str, object]) -> dict[str, object]:
    normalized = {
        "contract": {},
        "behavior_source": normalize_metadata_text(payload.get("behavior_source", "")),
        "ui_reference": normalize_metadata_text(payload.get("ui_reference", "")),
        "execution_backend": normalize_metadata_text(payload.get("execution_backend", "")),
        "skip_img2img_surfaces": _normalize_metadata_list(payload.get("skip_img2img_surfaces", [])),
        "controlnet_modes": _normalize_metadata_list(payload.get("controlnet_modes", [])),
        "prompt_tokens": _normalize_metadata_list(payload.get("prompt_tokens", [])),
        "warning_code_contract": normalize_metadata_text(payload.get("warning_code_contract", "")),
        "availability": _normalize_loose_mapping(payload.get("availability", {})),
        "warning_codes": _normalize_loose_mapping(payload.get("warning_codes", {})),
        "routes": _normalize_metadata_list(payload.get("routes", [])),
    }
    contract = payload.get("contract", {})
    if isinstance(contract, dict):
        normalized["contract"] = {
            "version": normalize_metadata_text(contract.get("version", "")),
            "ui_variant": normalize_metadata_text(contract.get("ui_variant", "")),
            "unit_count": int(contract.get("unit_count", 0) or 0),
            "prompt_tokens": _normalize_metadata_list(contract.get("prompt_tokens", [])),
            "controlnet_modes": _normalize_metadata_list(contract.get("controlnet_modes", [])),
            "detector_provider_families": _normalize_metadata_list(contract.get("detector_provider_families", [])),
            "detector_result_contract": normalize_metadata_text(contract.get("detector_result_contract", "")),
            "controlnet_advanced_contract": _normalize_loose_mapping(contract.get("controlnet_advanced_contract", {})),
            "mask_filter_methods": _normalize_metadata_list(contract.get("mask_filter_methods", [])),
            "mask_merge_modes": _normalize_metadata_list(contract.get("mask_merge_modes", [])),
            "defaults": _normalize_loose_mapping(contract.get("defaults", {})),
        }
    return normalized


def build_capabilities_payload(
    *,
    routes: list[str],
    snapshot: RookieUICapabilitiesSnapshot | None = None,
) -> dict[str, object]:
    snapshot = snapshot if snapshot is not None else RookieUICapabilitiesSnapshot(routes=routes)
    payload = snapshot.to_payload()

    payload["service"] = normalize_metadata_text(payload["service"])
    payload["visibility"] = normalize_metadata_text(payload["visibility"])
    payload["shell_version"] = normalize_metadata_text(payload["shell_version"])
    payload["runtime"] = _normalize_runtime_payload(build_runtime_metadata_payload())
    payload["host_surfaces"] = [
        normalize_metadata_text(surface)
        for surface in payload.get("host_surfaces", [])
        if isinstance(surface, str) and surface.strip()
    ]

    tabs = []
    for tab in payload["tabs"]:
        tabs.append(
            {
                "id": normalize_metadata_text(tab["id"]),
                "title": normalize_metadata_text(tab["title"]),
                "state": normalize_metadata_text(tab["state"]),
                "enabled": tab["enabled"],
            }
        )
    payload["tabs"] = tabs
    parity = payload.get("parity", {})
    if isinstance(parity, dict):
        profiles = []
        for profile in parity.get("profiles", []):
            profiles.append(
                {
                    "id": normalize_metadata_text(profile["id"]),
                    "title": normalize_metadata_text(profile["title"]),
                    "base_family": normalize_metadata_text(profile["base_family"]),
                    "prompt_encoder": normalize_metadata_text(profile["prompt_encoder"]),
                    "default_width": profile["default_width"],
                    "default_height": profile["default_height"],
                    "default_steps": profile["default_steps"],
                    "default_cfg_scale": profile["default_cfg_scale"],
                    "default_sampler": normalize_metadata_text(profile["default_sampler"]),
                    "default_scheduler": normalize_metadata_text(profile["default_scheduler"]),
                    "default_clip_skip": profile["default_clip_skip"],
                    "supports_clip_skip": profile["supports_clip_skip"],
                    "notes": [normalize_metadata_text(note) for note in profile["notes"]],
                }
            )

        sampler_aliases = parity.get("sampler_aliases", {})
        payload["parity"] = {
            "profiles": profiles,
            "sampler_aliases": {
                "samplers": {
                    normalize_metadata_text(key): normalize_metadata_text(value)
                    for key, value in sampler_aliases.get("samplers", {}).items()
                },
                "scheduler_aliases": {
                    normalize_metadata_text(key): normalize_metadata_text(value)
                    for key, value in sampler_aliases.get("scheduler_aliases", {}).items()
                },
                "scheduler_overrides": {
                    normalize_metadata_text(key): normalize_metadata_text(value)
                    for key, value in sampler_aliases.get("scheduler_overrides", {}).items()
                },
                "supported_schedulers": [
                    normalize_metadata_text(value)
                    for value in sampler_aliases.get("supported_schedulers", [])
                ],
            },
        }
    prompt_semantics = payload.get("prompt_semantics", {})
    if isinstance(prompt_semantics, dict):
        payload["prompt_semantics"] = _normalize_prompt_semantics_payload(prompt_semantics)
    adetailer = payload.get("adetailer", {})
    if isinstance(adetailer, dict):
        payload["adetailer"] = _normalize_adetailer_payload(adetailer)
    return payload
