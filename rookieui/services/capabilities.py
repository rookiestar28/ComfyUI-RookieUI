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


def _normalize_model_family_registry_payload(payload: dict[str, object]) -> dict[str, object]:
    normalized = {
        "contract_version": normalize_metadata_text(payload.get("contract_version", "")),
        "entries": [],
    }
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        return normalized

    normalized_entries = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        normalized_entries.append(
            {
                "id": normalize_metadata_text(entry.get("id", "")),
                "title": normalize_metadata_text(entry.get("title", "")),
                "translation_base_family": normalize_metadata_text(entry.get("translation_base_family", "")),
                "public_base_family": normalize_metadata_text(entry.get("public_base_family", "")),
                "prompt_encoder": normalize_metadata_text(entry.get("prompt_encoder", "")),
                "default_width": int(entry.get("default_width", 0) or 0),
                "default_height": int(entry.get("default_height", 0) or 0),
                "default_steps": int(entry.get("default_steps", 0) or 0),
                "default_cfg_scale": float(entry.get("default_cfg_scale", 0.0) or 0.0),
                "default_sampler": normalize_metadata_text(entry.get("default_sampler", "")),
                "default_scheduler": normalize_metadata_text(entry.get("default_scheduler", "")),
                "default_clip_skip": int(entry.get("default_clip_skip", 0) or 0),
                "supports_clip_skip": bool(entry.get("supports_clip_skip", False)),
                "primary_model_category": normalize_metadata_text(entry.get("primary_model_category", "")),
                "text_encoder_visible": bool(entry.get("text_encoder_visible", False)),
                "shift_visible": bool(entry.get("shift_visible", False)),
                "default_shift": (
                    float(entry.get("default_shift"))
                    if entry.get("default_shift") not in (None, "")
                    else None
                ),
                "flux_guidance_visible": bool(entry.get("flux_guidance_visible", False)),
                "default_flux_guidance": (
                    float(entry.get("default_flux_guidance"))
                    if entry.get("default_flux_guidance") not in (None, "")
                    else None
                ),
                "prompt_enhancement_visible": bool(entry.get("prompt_enhancement_visible", False)),
                "default_prompt_enhancement_enabled": bool(
                    entry.get("default_prompt_enhancement_enabled", False)
                ),
                "edit_megapixels_visible": bool(entry.get("edit_megapixels_visible", False)),
                "default_edit_megapixels": (
                    float(entry.get("default_edit_megapixels"))
                    if entry.get("default_edit_megapixels") not in (None, "")
                    else None
                ),
                "template_lora_visible": bool(entry.get("template_lora_visible", False)),
                "template_lora_override_allowed": bool(entry.get("template_lora_override_allowed", False)),
                "official_template_lora_label": normalize_metadata_text(
                    entry.get("official_template_lora_label", "")
                ),
                "image_edit_profile": bool(entry.get("image_edit_profile", False)),
                "request_contract_surface": normalize_metadata_text(entry.get("request_contract_surface", "")),
                "reference_input_mode": normalize_metadata_text(entry.get("reference_input_mode", "")),
                "max_direct_references": int(entry.get("max_direct_references", 0) or 0),
                "encoder_family": normalize_metadata_text(entry.get("encoder_family", "")),
                "template_lora_chain_mode": normalize_metadata_text(entry.get("template_lora_chain_mode", "")),
                "available_surface_flows": _normalize_metadata_list(
                    entry.get("available_surface_flows", [])
                ),
                "support_tier": normalize_metadata_text(entry.get("support_tier", "")),
                "compatibility_summary": normalize_metadata_text(entry.get("compatibility_summary", "")),
                "experimental": bool(entry.get("experimental", False)),
                "aliases": _normalize_metadata_list(entry.get("aliases", [])),
                "notes": _normalize_metadata_list(entry.get("notes", [])),
            }
        )
    normalized["entries"] = normalized_entries
    return normalized


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


def _normalize_z_image_controlnet_payload(payload: dict[str, object]) -> dict[str, object]:
    normalized: dict[str, object] = {
        "contract_version": normalize_metadata_text(payload.get("contract_version", "")),
        "source_model_category": normalize_metadata_text(payload.get("source_model_category", "")),
        "forbidden_model_category": normalize_metadata_text(payload.get("forbidden_model_category", "")),
        "available": bool(payload.get("available", False)),
        "required_nodes": _normalize_metadata_list(payload.get("required_nodes", [])),
        "missing_nodes": _normalize_metadata_list(payload.get("missing_nodes", [])),
        "model_patches": [],
        "diagnostics": _normalize_metadata_list(payload.get("diagnostics", [])),
        "graph_contract": {},
    }

    patch_entries = payload.get("model_patches", [])
    if isinstance(patch_entries, list):
        normalized_patches = []
        for patch_entry in patch_entries:
            if not isinstance(patch_entry, dict):
                continue
            normalized_patches.append(
                {
                    "selector": normalize_metadata_text(patch_entry.get("selector", "")),
                    "model_category": normalize_metadata_text(patch_entry.get("model_category", "")),
                    "family": normalize_metadata_text(patch_entry.get("family", "")),
                    "profile_hint": normalize_metadata_text(patch_entry.get("profile_hint", "")),
                    "variant": normalize_metadata_text(patch_entry.get("variant", "")),
                    "turbo": bool(patch_entry.get("turbo", False)),
                    "z_image_family": normalize_metadata_text(patch_entry.get("z_image_family", "")),
                    "generation": normalize_metadata_text(patch_entry.get("generation", "")),
                    "release_tag": (
                        normalize_metadata_text(patch_entry.get("release_tag", ""))
                        if patch_entry.get("release_tag") not in (None, "")
                        else None
                    ),
                    "distilled_steps": (
                        int(patch_entry.get("distilled_steps"))
                        if patch_entry.get("distilled_steps") not in (None, "")
                        else None
                    ),
                    "lite": bool(patch_entry.get("lite", False)),
                    "supported_conditions": _normalize_metadata_list(
                        patch_entry.get("supported_conditions", [])
                    ),
                    "source_control_context_scale_range": [
                        float(value)
                        for value in patch_entry.get("source_control_context_scale_range", [])
                        if isinstance(value, (int, float))
                    ],
                    "rookieui_support": normalize_metadata_text(patch_entry.get("rookieui_support", "")),
                    "recommendation": normalize_metadata_text(patch_entry.get("recommendation", "")),
                }
            )
        normalized["model_patches"] = normalized_patches

    graph_contract = payload.get("graph_contract", {})
    if isinstance(graph_contract, dict):
        normalized["graph_contract"] = {
            "loader_node": normalize_metadata_text(graph_contract.get("loader_node", "")),
            "patch_apply_node": normalize_metadata_text(graph_contract.get("patch_apply_node", "")),
            "sampling_node": normalize_metadata_text(graph_contract.get("sampling_node", "")),
            "forbidden_nodes": _normalize_metadata_list(graph_contract.get("forbidden_nodes", [])),
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
    model_families = payload.get("model_families", {})
    if isinstance(model_families, dict):
        payload["model_families"] = _normalize_model_family_registry_payload(model_families)
    prompt_semantics = payload.get("prompt_semantics", {})
    if isinstance(prompt_semantics, dict):
        payload["prompt_semantics"] = _normalize_prompt_semantics_payload(prompt_semantics)
    adetailer = payload.get("adetailer", {})
    if isinstance(adetailer, dict):
        payload["adetailer"] = _normalize_adetailer_payload(adetailer)
    z_image_controlnet = payload.get("z_image_controlnet", {})
    if isinstance(z_image_controlnet, dict):
        payload["z_image_controlnet"] = _normalize_z_image_controlnet_payload(z_image_controlnet)
    return payload
