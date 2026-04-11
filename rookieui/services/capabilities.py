from __future__ import annotations

from rookieui.contracts.capabilities import RookieUICapabilitiesSnapshot
from rookieui.security.asset_guard import normalize_metadata_text


def _normalize_prompt_semantics_payload(payload: dict[str, object]) -> dict[str, object]:
    normalized = {
        "contract_version": normalize_metadata_text(payload.get("contract_version", "")),
        "contract_scope": normalize_metadata_text(payload.get("contract_scope", "")),
        "rollout": {},
        "compiler_constraints": {},
        "capabilities": [],
    }
    rollout = payload.get("rollout", {})
    if isinstance(rollout, dict):
        normalized["rollout"] = {
            key: normalize_metadata_text(value)
            for key, value in rollout.items()
            if isinstance(value, str) and value.strip()
        }
    constraints = payload.get("compiler_constraints", {})
    if isinstance(constraints, dict):
        normalized["compiler_constraints"] = {
            "conditioning_nodes": [
                normalize_metadata_text(value)
                for value in constraints.get("conditioning_nodes", [])
                if isinstance(value, str) and value.strip()
            ],
            "execution_backend": normalize_metadata_text(constraints.get("execution_backend", "")),
        }
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
    return payload
