from __future__ import annotations

import json
from typing import Any


def build_xyz_plot_text_summary(session: dict[str, Any], *, grid_role: str, z_binding: dict[str, Any] | None = None) -> str:
    axis_parts = []
    for axis in session.get("axes", []):
        if not isinstance(axis, dict):
            continue
        axis_parts.append(f"{axis.get('slot', '?')}={axis.get('title', axis.get('axis_id', '?'))}")
    header = f"RookieUI XYZ Plot [{grid_role}]"
    if z_binding is not None:
        header = f"{header} - {z_binding.get('title', 'Z')}: {z_binding.get('label', '')}"
    seed_policy = session.get("seed_policy", {})
    seed_summary = ""
    if isinstance(seed_policy, dict):
        if bool(seed_policy.get("keep_negative_one_seed", False)):
            seed_summary = " | Seed policy: keep -1"
        elif seed_policy.get("fixed_base_seed") is not None:
            seed_summary = f" | Seed policy: fixed base seed {seed_policy.get('fixed_base_seed')}"
    return f"{header} | Session {session.get('session_id', '')} | Axes: {', '.join(axis_parts)}{seed_summary}"


def build_xyz_plot_png_metadata(
    session: dict[str, Any],
    *,
    grid_role: str,
    z_binding: dict[str, Any] | None = None,
    signature: str,
) -> dict[str, str]:
    payload = {
        "session_id": session.get("session_id", ""),
        "mode": session.get("mode", ""),
        "grid_role": grid_role,
        "signature": signature,
        "surface": "xyz_plot",
        "axes": [
            {
                "slot": axis.get("slot"),
                "axis_id": axis.get("axis_id"),
                "title": axis.get("title"),
                "values": [entry.get("label") for entry in axis.get("parsed_values", []) if isinstance(entry, dict)],
            }
            for axis in session.get("axes", [])
            if isinstance(axis, dict)
        ],
        "grid_options": session.get("grid_options", {}),
        "seed_policy": session.get("seed_policy", {}),
    }
    if z_binding is not None:
        payload["z_binding"] = {
            "slot": z_binding.get("slot"),
            "axis_id": z_binding.get("axis_id"),
            "title": z_binding.get("title"),
            "label": z_binding.get("label"),
        }
    return {
        "parameters": build_xyz_plot_text_summary(session, grid_role=grid_role, z_binding=z_binding),
        "rookieui_surface": "xyz_plot",
        "rookieui_xyz_plot": json.dumps(payload, ensure_ascii=True, sort_keys=True),
    }
