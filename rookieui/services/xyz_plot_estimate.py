from __future__ import annotations

import itertools
from typing import Any

from rookieui.contracts.xyz_plot import build_xyz_plot_contract_meta
from rookieui.services.coercion import coerce_int
from rookieui.services.xyz_plot_axes import get_xyz_axis_choices, resolve_xyz_axis_contract
from rookieui.services.xyz_plot_values import ParsedXYZAxisEntry, parse_xyz_axis_values

XYZ_PLOT_MAX_TOTAL_CELLS = 4096
XYZ_PLOT_MAX_GRID_MEGAPIXELS = 200.0

_DEFAULT_BASE_WIDTH = 512
_DEFAULT_BASE_HEIGHT = 512
_DEFAULT_BASE_STEPS = 20
_DEFAULT_BASE_HIRES_STEPS = 0


def _normalize_xyz_mode(raw_mode: object) -> str:
    normalized_mode = str(raw_mode or "").strip().lower()
    if normalized_mode not in {"txt2img", "img2img"}:
        raise ValueError("xyz_plot mode must be txt2img or img2img.")
    return normalized_mode


def _coerce_base_dimension(payload: dict[str, Any], key: str, *, default: int) -> int:
    value = coerce_int(payload.get(key), key, via_str=True, default=default)
    if value <= 0:
        raise ValueError(f"{key} must be positive.")
    return value


def _coerce_non_negative_int(payload: dict[str, Any], key: str, *, default: int) -> int:
    value = coerce_int(payload.get(key), key, via_str=True, default=default)
    if value < 0:
        raise ValueError(f"{key} must be non-negative.")
    return value


def _normalize_estimate_axes(raw_axes: object, *, mode: str) -> list[dict[str, Any]]:
    if not isinstance(raw_axes, list):
        raise ValueError("xyz_plot axes must be a list.")
    normalized_axes: list[dict[str, Any]] = []
    seen_axis_ids: set[str] = set()
    for index, raw_axis in enumerate(raw_axes):
        if not isinstance(raw_axis, dict):
            raise ValueError("xyz_plot axis entries must be objects.")
        axis_id = str(raw_axis.get("axis_id", "")).strip()
        if not axis_id:
            raise ValueError(f"xyz_plot axis #{index + 1} is missing axis_id.")
        if axis_id in seen_axis_ids:
            raise ValueError(f"xyz_plot axis {axis_id} was provided more than once.")
        contract = resolve_xyz_axis_contract(axis_id)
        if mode not in contract.mode_scopes:
            raise ValueError(f"xyz_plot axis {axis_id} is not supported for {mode}.")
        parsed_values = parse_xyz_axis_values(
            raw_axis.get("values", ""),
            contract,
            choices=get_xyz_axis_choices(axis_id),
        )
        normalized_axes.append(
            {
                "axis_id": axis_id,
                "contract": contract,
                "parsed_values": parsed_values,
            }
        )
        seen_axis_ids.add(axis_id)
    return normalized_axes


def _estimate_cell_steps(base_steps: int, base_hires_steps: int, axis_value_map: dict[str, ParsedXYZAxisEntry]) -> int:
    steps = base_steps
    if "steps" in axis_value_map:
        steps = int(axis_value_map["steps"].value)
    hires_steps = base_hires_steps
    if "hires_steps" in axis_value_map:
        hires_steps = int(axis_value_map["hires_steps"].value)
    return max(0, steps) + max(0, hires_steps)


def _estimate_cell_dimensions(
    base_width: int,
    base_height: int,
    axis_value_map: dict[str, ParsedXYZAxisEntry],
) -> tuple[int, int]:
    width = base_width
    height = base_height
    if "size" in axis_value_map:
        size_value = axis_value_map["size"].value
        if isinstance(size_value, dict):
            width = int(size_value.get("width", base_width))
            height = int(size_value.get("height", base_height))
    return width, height


def build_xyz_plot_estimate_payload(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("xyz_plot estimate payload must be an object.")

    mode = _normalize_xyz_mode(payload.get("mode"))
    base_request = payload.get("base_request", {})
    if not isinstance(base_request, dict):
        raise ValueError("xyz_plot base_request must be an object.")

    base_width = _coerce_base_dimension(base_request, "width", default=_DEFAULT_BASE_WIDTH)
    base_height = _coerce_base_dimension(base_request, "height", default=_DEFAULT_BASE_HEIGHT)
    base_steps = _coerce_non_negative_int(base_request, "steps", default=_DEFAULT_BASE_STEPS)
    base_hires_steps = _coerce_non_negative_int(base_request, "hires_steps", default=_DEFAULT_BASE_HIRES_STEPS)
    normalized_axes = _normalize_estimate_axes(payload.get("axes", []), mode=mode)

    axis_value_counts = [len(entry["parsed_values"]) for entry in normalized_axes] or [1]
    total_cells = 1
    for count in axis_value_counts:
        total_cells *= count
        if total_cells > XYZ_PLOT_MAX_TOTAL_CELLS:
            raise ValueError(f"xyz_plot expands to too many cells (max {XYZ_PLOT_MAX_TOTAL_CELLS}).")

    total_steps = 0
    max_cell_width = base_width
    max_cell_height = base_height
    axis_value_groups = [entry["parsed_values"] for entry in normalized_axes]
    if axis_value_groups:
        for combination in itertools.product(*axis_value_groups):
            axis_value_map = {
                normalized_axes[index]["axis_id"]: parsed_entry
                for index, parsed_entry in enumerate(combination)
            }
            total_steps += _estimate_cell_steps(base_steps, base_hires_steps, axis_value_map)
            cell_width, cell_height = _estimate_cell_dimensions(base_width, base_height, axis_value_map)
            max_cell_width = max(max_cell_width, cell_width)
            max_cell_height = max(max_cell_height, cell_height)
    else:
        total_steps = base_steps + base_hires_steps

    projected_grid_megapixels = round((total_cells * max_cell_width * max_cell_height) / 1_000_000, 3)
    can_run = projected_grid_megapixels < XYZ_PLOT_MAX_GRID_MEGAPIXELS
    warning_codes: list[str] = []
    warnings: list[str] = []
    if not can_run:
        warning_codes.append("XYZ_GRID_TOO_LARGE")
        warnings.append(
            f"Projected top-level grid would be {projected_grid_megapixels} MP, exceeding the {XYZ_PLOT_MAX_GRID_MEGAPIXELS} MP guard."
        )

    axis_payloads = []
    for axis_entry in normalized_axes:
        contract = axis_entry["contract"]
        parsed_values = axis_entry["parsed_values"]
        if contract.support_tier == "not_supported_yet":
            can_run = False
            warning_codes.append("XYZ_AXIS_NOT_SUPPORTED")
            warnings.append(f"Axis {contract.axis_id} is not truthfully supported yet.")
        axis_payloads.append(
            {
                "axis_id": contract.axis_id,
                "title": contract.title,
                "support_tier": contract.support_tier,
                "value_input_mode": contract.value_input_mode,
                "value_count": len(parsed_values),
                "parsed_values": [entry.to_payload() for entry in parsed_values],
            }
        )

    return {
        "contract": build_xyz_plot_contract_meta(surface="xyz_plot_estimate"),
        "mode": mode,
        "axes": axis_payloads,
        "estimate": {
            "cell_count": total_cells,
            "generated_image_count": total_cells,
            "total_step_estimate": total_steps,
            "projected_grid_megapixels": projected_grid_megapixels,
            "max_grid_megapixels": XYZ_PLOT_MAX_GRID_MEGAPIXELS,
            "base_resolution": {
                "width": base_width,
                "height": base_height,
            },
            "max_cell_resolution": {
                "width": max_cell_width,
                "height": max_cell_height,
            },
        },
        "can_run": can_run,
        "warnings": warnings,
        "warning_codes": warning_codes,
    }
