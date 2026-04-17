from __future__ import annotations

from typing import Any

from rookieui.services.xyz_plot_axes import build_xyz_plot_axes_payload
from rookieui.services.xyz_plot_estimate import build_xyz_plot_estimate_payload


def build_xyz_plot_axes_snapshot() -> dict[str, Any]:
    return build_xyz_plot_axes_payload()


def build_xyz_plot_estimate_snapshot(payload: object) -> dict[str, Any]:
    return build_xyz_plot_estimate_payload(payload)
