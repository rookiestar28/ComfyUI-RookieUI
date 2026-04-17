from __future__ import annotations

import base64
import hashlib
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from rookieui.services.asset_store import (
    build_data_url_from_path,
    mirror_output_asset_to_host_output,
    resolve_generated_output_path,
    save_output_image,
)
from rookieui.services.xyz_plot_estimate import XYZ_PLOT_MAX_GRID_MEGAPIXELS
from rookieui.services.xyz_plot_metadata import build_xyz_plot_png_metadata

_BACKGROUND_COLOR = (248, 248, 250)
_TEXT_COLOR = (32, 32, 32)
_BORDER_COLOR = (210, 210, 214)
_TITLE_BG_COLOR = (236, 236, 240)
_MIN_LABEL_PAD = 12
_CORNER_LINE_SPACING = 4
_PARTIAL_PREVIEW_PLACEHOLDER_SIZE = (256, 256)
_GRID_LABEL_FONT_SIZE = 22
_GRID_FONT_CANDIDATES = (
    "arial.ttf",
    "segoeui.ttf",
    "DejaVuSans.ttf",
    "LiberationSans-Regular.ttf",
)


def _safe_font(size: int = _GRID_LABEL_FONT_SIZE) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for font_name in _GRID_FONT_CANDIDATES:
        try:
            return ImageFont.truetype(font_name, size=size)
        except Exception:
            continue
    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont | ImageFont.FreeTypeFont) -> tuple[int, int]:
    if not text:
        return (0, 0)
    bbox = draw.textbbox((0, 0), text, font=font)
    return (max(0, bbox[2] - bbox[0]), max(0, bbox[3] - bbox[1]))


def _normalize_grid_cell(image: Image.Image, *, width: int, height: int) -> Image.Image:
    normalized = Image.new("RGB", (width, height), _BACKGROUND_COLOR)
    source = image.convert("RGB")
    x = (width - source.width) // 2
    y = (height - source.height) // 2
    normalized.paste(source, (x, y))
    return normalized


def _build_axis_descriptor_lines(*axes: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for axis in axes:
        if not isinstance(axis, dict):
            continue
        slot = str(axis.get("slot", "")).strip() or "?"
        title = str(axis.get("title", axis.get("axis_id", ""))).strip()
        if not title:
            continue
        lines.append(f"{slot}: {title}")
    return lines


def _measure_corner_block(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
) -> tuple[int, int]:
    if not lines:
        return (0, 0)
    widths: list[int] = []
    heights: list[int] = []
    for line in lines:
        width, height = _measure_text(draw, line, font)
        widths.append(width)
        heights.append(height)
    total_height = sum(heights) + (_CORNER_LINE_SPACING * max(0, len(heights) - 1))
    return (
        max(widths) + (_MIN_LABEL_PAD * 2),
        total_height + (_MIN_LABEL_PAD * 2),
    )


def _draw_corner_block(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    *,
    left_pad: int,
    top_pad: int,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
) -> None:
    if not lines or left_pad <= 0 or top_pad <= 0:
        return
    draw.rectangle((0, 0, left_pad - 1, top_pad - 1), fill=_TITLE_BG_COLOR, outline=_BORDER_COLOR, width=1)
    line_sizes = [_measure_text(draw, line, font) for line in lines]
    total_height = sum(height for _, height in line_sizes) + (_CORNER_LINE_SPACING * max(0, len(line_sizes) - 1))
    draw_y = max(0.0, (top_pad - total_height) / 2)
    for line, (line_width, line_height) in zip(lines, line_sizes, strict=True):
        draw.text(
            (max(_MIN_LABEL_PAD / 2, (left_pad - line_width) / 2), draw_y),
            line,
            fill=_TEXT_COLOR,
            font=font,
        )
        draw_y += line_height + _CORNER_LINE_SPACING


def _compose_annotated_grid(
    cells: list[Image.Image],
    *,
    cols: int,
    rows: int,
    col_labels: list[str],
    row_labels: list[str],
    corner_lines: list[str],
    draw_legend: bool,
    margin_size: int,
) -> Image.Image:
    if not cells:
        raise ValueError("XYZ grid composition requires at least one cell image.")
    max_width = max(image.width for image in cells)
    max_height = max(image.height for image in cells)
    normalized_cells = [_normalize_grid_cell(image, width=max_width, height=max_height) for image in cells]
    margin = max(0, int(margin_size or 0))
    font = _safe_font()
    scratch = Image.new("RGB", (8, 8), _BACKGROUND_COLOR)
    draw = ImageDraw.Draw(scratch)
    top_pad = 0
    left_pad = 0
    if draw_legend:
        if col_labels:
            top_pad = max(_measure_text(draw, label, font)[1] for label in col_labels) + (_MIN_LABEL_PAD * 2)
        if row_labels:
            left_pad = max(_measure_text(draw, label, font)[0] for label in row_labels) + (_MIN_LABEL_PAD * 2)
        corner_width, corner_height = _measure_corner_block(draw, corner_lines, font)
        top_pad = max(top_pad, corner_height)
        left_pad = max(left_pad, corner_width)
    canvas_width = left_pad + (cols * max_width) + (margin * max(0, cols - 1))
    canvas_height = top_pad + (rows * max_height) + (margin * max(0, rows - 1))
    projected_mp = round((canvas_width * canvas_height) / 1_000_000, 3)
    if projected_mp >= XYZ_PLOT_MAX_GRID_MEGAPIXELS:
        raise ValueError(
            f"XYZ grid assembly would be {projected_mp} MP, exceeding the {XYZ_PLOT_MAX_GRID_MEGAPIXELS} MP guard."
        )
    canvas = Image.new("RGB", (canvas_width, canvas_height), _BACKGROUND_COLOR)
    draw = ImageDraw.Draw(canvas)
    for index, cell in enumerate(normalized_cells):
        col = index % cols
        row = index // cols
        x = left_pad + col * (max_width + margin)
        y = top_pad + row * (max_height + margin)
        canvas.paste(cell, (x, y))
        draw.rectangle((x, y, x + max_width - 1, y + max_height - 1), outline=_BORDER_COLOR, width=1)
    if draw_legend:
        _draw_corner_block(draw, corner_lines, left_pad=left_pad, top_pad=top_pad, font=font)
        for col, label in enumerate(col_labels):
            if not label:
                continue
            x = left_pad + col * (max_width + margin)
            label_w, label_h = _measure_text(draw, label, font)
            box_y0 = 0
            box_y1 = top_pad - 1
            draw.rectangle((x, box_y0, x + max_width - 1, box_y1), fill=_TITLE_BG_COLOR, outline=_BORDER_COLOR, width=1)
            draw.text((x + (max_width - label_w) / 2, max(0, (top_pad - label_h) / 2)), label, fill=_TEXT_COLOR, font=font)
        for row, label in enumerate(row_labels):
            if not label:
                continue
            y = top_pad + row * (max_height + margin)
            label_w, label_h = _measure_text(draw, label, font)
            box_x0 = 0
            box_x1 = left_pad - 1
            draw.rectangle((box_x0, y, box_x1, y + max_height - 1), fill=_TITLE_BG_COLOR, outline=_BORDER_COLOR, width=1)
            draw.text((max(0, (left_pad - label_w) / 2), y + (max_height - label_h) / 2), label, fill=_TEXT_COLOR, font=font)
    return canvas


def _serialize_image_to_digest(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def _build_data_url_from_image(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _resolve_first_output_asset(cell: dict[str, Any]) -> str:
    reusable_outputs = cell.get("reusable_outputs", [])
    if isinstance(reusable_outputs, list):
        for handle in reusable_outputs:
            if isinstance(handle, str) and handle.strip():
                return handle
    output_filenames = cell.get("output_filenames", [])
    if isinstance(output_filenames, list):
        for handle in output_filenames:
            if isinstance(handle, str) and handle.strip():
                return handle
    return ""


def _build_placeholder_cell(
    label: str,
    *,
    width: int,
    height: int,
) -> Image.Image:
    image = Image.new("RGB", (width, height), _BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width - 1, height - 1), outline=_BORDER_COLOR, width=1)
    font = _safe_font()
    lines = [part for part in str(label).split("\n") if part]
    if not lines:
        lines = ["Pending"]
    line_sizes = [_measure_text(draw, line, font) for line in lines]
    total_height = sum(height for _, height in line_sizes) + (_CORNER_LINE_SPACING * max(0, len(line_sizes) - 1))
    cursor_y = max(0.0, (height - total_height) / 2)
    for line, (line_width, line_height) in zip(lines, line_sizes, strict=True):
        draw.text(
            ((width - line_width) / 2, cursor_y),
            line,
            fill=_TEXT_COLOR,
            font=font,
        )
        cursor_y += line_height + _CORNER_LINE_SPACING
    return image


def _compose_partial_grid_preview(
    session: dict[str, Any],
    *,
    axes: list[dict[str, Any]],
    axis_labels: list[list[str]],
    indexed_cells: dict[tuple[int, int, int], dict[str, Any]],
    x_len: int,
    y_len: int,
    z_len: int,
    draw_legend: bool,
    margin_size: int,
) -> Image.Image | None:
    completed_images: list[Image.Image] = []
    for entry in indexed_cells.values():
        try:
            completed_images.append(Image.open(entry["path"]).convert("RGB"))
        except Exception:
            continue
    if not completed_images:
        return None
    max_width = max(image.width for image in completed_images)
    max_height = max(image.height for image in completed_images)
    preview_width = max(max_width, _PARTIAL_PREVIEW_PLACEHOLDER_SIZE[0])
    preview_height = max(max_height, _PARTIAL_PREVIEW_PLACEHOLDER_SIZE[1])
    sub_grid_images: list[Image.Image] = []
    for z_index in range(z_len):
        sub_cells: list[Image.Image] = []
        for y_index in range(y_len):
            for x_index in range(x_len):
                entry = indexed_cells.get((x_index, y_index, z_index))
                if entry is not None:
                    try:
                        sub_cells.append(Image.open(entry["path"]).convert("RGB"))
                        continue
                    except Exception:
                        pass
                binding_labels: list[str] = []
                if axis_labels and x_index < len(axis_labels[0]):
                    binding_labels.append(f"X {axis_labels[0][x_index]}")
                if len(axis_labels) > 1 and y_index < len(axis_labels[1]):
                    binding_labels.append(f"Y {axis_labels[1][y_index]}")
                if len(axis_labels) > 2 and z_index < len(axis_labels[2]):
                    binding_labels.append(f"Z {axis_labels[2][z_index]}")
                sub_cells.append(
                    _build_placeholder_cell(
                        "\n".join(binding_labels) if binding_labels else "Pending",
                        width=preview_width,
                        height=preview_height,
                    )
                )
        sub_grid_images.append(
            _compose_annotated_grid(
                sub_cells,
                cols=x_len,
                rows=y_len,
                col_labels=axis_labels[0] if axes else [],
                row_labels=axis_labels[1] if len(axes) > 1 else [],
                corner_lines=_build_axis_descriptor_lines(*(axis for axis in axes[:2] if isinstance(axis, dict))),
                draw_legend=draw_legend,
                margin_size=margin_size,
            )
        )
    if len(sub_grid_images) == 1:
        return sub_grid_images[0]
    return _compose_annotated_grid(
        sub_grid_images,
        cols=z_len,
        rows=1,
        col_labels=axis_labels[2] if len(axis_labels) > 2 else [],
        row_labels=[],
        corner_lines=_build_axis_descriptor_lines(axes[2] if len(axes) > 2 else {}),
        draw_legend=draw_legend,
        margin_size=margin_size,
    )


def build_xyz_plot_grid_results(session: dict[str, Any]) -> dict[str, Any]:
    axes = [axis for axis in session.get("axes", []) if isinstance(axis, dict)]
    if not axes:
        return {
            "status": "pending",
            "signature": "",
            "main_grid": {},
            "sub_grids": [],
            "lone_images": [],
            "warnings": ["XYZ session has no axis definitions."],
        }

    grid_options = session.get("grid_options", {})
    draw_legend = bool(grid_options.get("draw_legend", True))
    include_sub_grids = bool(grid_options.get("include_sub_grids", False))
    include_lone_images = bool(grid_options.get("include_lone_images", False))
    margin_size = int(grid_options.get("margin_size", 0) or 0)

    signature_source_parts = [
        str(session.get("session_id", "")),
        str(draw_legend),
        str(include_sub_grids),
        str(include_lone_images),
        str(margin_size),
    ]
    warnings: list[str] = []
    cell_assets: list[dict[str, Any]] = []
    completed_cells = 0
    terminal_only = True
    for cell in session.get("cells", []):
        if not isinstance(cell, dict):
            continue
        status = str(cell.get("status", "")).strip()
        asset_handle = _resolve_first_output_asset(cell)
        signature_source_parts.append(
            "|".join(
                [
                    str(cell.get("cell_id", "")),
                    status,
                    asset_handle,
                    str(cell.get("prompt_id", "")),
                ]
            )
        )
        if status == "completed":
            completed_cells += 1
            if not asset_handle:
                warnings.append(f"Completed cell {cell.get('cell_id', '')} has no reusable output asset.")
                continue
            cell_assets.append(
                {
                    "cell": cell,
                    "asset_handle": asset_handle,
                    "path": resolve_generated_output_path(asset_handle),
                }
            )
        elif status not in {"failed", "cancelled"}:
            terminal_only = False
    signature = hashlib.sha256("::".join(signature_source_parts).encode("utf-8")).hexdigest()

    axis_lengths = [len(axis.get("parsed_values", [])) for axis in axes]
    axis_labels = [[entry.get("label", "") for entry in axis.get("parsed_values", []) if isinstance(entry, dict)] for axis in axes]
    x_len = axis_lengths[0] if axis_lengths else 1
    y_len = axis_lengths[1] if len(axis_lengths) > 1 else 1
    z_len = axis_lengths[2] if len(axis_lengths) > 2 else 1

    indexed_cells: dict[tuple[int, int, int], dict[str, Any]] = {}
    for entry in cell_assets:
        axis_indices = entry["cell"].get("axis_indices", {})
        indexed_cells[
            (
                int(axis_indices.get("X", 0) or 0),
                int(axis_indices.get("Y", 0) or 0),
                int(axis_indices.get("Z", 0) or 0),
            )
        ] = entry

    if not completed_cells:
        return {
            "status": "pending",
            "signature": signature,
            "main_grid": {},
            "sub_grids": [],
            "lone_images": [],
            "warnings": warnings,
        }
    if not terminal_only:
        partial_grid_preview = _compose_partial_grid_preview(
            session,
            axes=axes,
            axis_labels=axis_labels,
            indexed_cells=indexed_cells,
            x_len=x_len,
            y_len=y_len,
            z_len=z_len,
            draw_legend=draw_legend,
            margin_size=margin_size,
        )
        # IMPORTANT: keep a running-session main_grid preview here; the primary txt2img/img2img preview now depends on this payload instead of waiting for terminal saved assets.
        return {
            "status": "running",
            "signature": signature,
            "main_grid": {
                "preview_data_url": _build_data_url_from_image(partial_grid_preview),
            }
            if partial_grid_preview is not None
            else {},
            "sub_grids": [],
            "lone_images": [],
            "warnings": warnings,
        }

    incomplete = False
    sub_grid_images: list[Image.Image] = []
    persisted_sub_grids: list[dict[str, Any]] = []
    for z_index in range(z_len):
        sub_cells: list[Image.Image] = []
        for y_index in range(y_len):
            for x_index in range(x_len):
                cell_entry = indexed_cells.get((x_index, y_index, z_index))
                if cell_entry is None:
                    incomplete = True
                    break
                sub_cells.append(Image.open(cell_entry["path"]).convert("RGB"))
            if incomplete:
                break
        if incomplete:
            break
        sub_grid = _compose_annotated_grid(
            sub_cells,
            cols=x_len,
            rows=y_len,
            col_labels=axis_labels[0] if axes else [],
            row_labels=axis_labels[1] if len(axes) > 1 else [],
            corner_lines=_build_axis_descriptor_lines(*(axis for axis in axes[:2] if isinstance(axis, dict))),
            draw_legend=draw_legend,
            margin_size=margin_size,
        )
        sub_grid_images.append(sub_grid)
        if include_sub_grids:
            z_binding = None
            if len(axes) > 2:
                z_axis = axes[2]
                z_binding = {
                    "slot": "Z",
                    "axis_id": z_axis.get("axis_id"),
                    "title": z_axis.get("title"),
                    "label": axis_labels[2][z_index],
                }
            metadata = build_xyz_plot_png_metadata(
                session,
                grid_role="sub_grid",
                z_binding=z_binding,
                signature=signature,
            )
            saved = save_output_image(sub_grid, prefix="xyz_plot_subgrid", metadata=metadata)
            host_output_filename = ""
            try:
                host_output_filename = mirror_output_asset_to_host_output(saved.path, filename=saved.handle)
            except Exception as exc:
                warnings.append(f"Failed to mirror XYZ sub-grid to host output: {exc}")
            persisted_sub_grids.append(
                {
                    "z_index": z_index,
                    "z_label": axis_labels[2][z_index] if len(axis_labels) > 2 else "",
                    "asset_handle": saved.handle,
                    "sha256": saved.sha256,
                    "host_output_filename": host_output_filename,
                }
            )
    if incomplete:
        warnings.append("XYZ session completed without a full set of reusable cell outputs; grid delivery is incomplete.")
        return {
            "status": "incomplete",
            "signature": signature,
            "main_grid": {},
            "sub_grids": persisted_sub_grids,
            "lone_images": [],
            "warnings": warnings,
        }

    if len(sub_grid_images) == 1:
        main_grid_image = sub_grid_images[0]
    else:
        main_grid_image = _compose_annotated_grid(
            sub_grid_images,
            cols=z_len,
            rows=1,
            col_labels=axis_labels[2] if len(axis_labels) > 2 else [],
            row_labels=[],
            corner_lines=_build_axis_descriptor_lines(axes[2] if len(axes) > 2 else {}),
            draw_legend=draw_legend,
            margin_size=margin_size,
        )
    main_metadata = build_xyz_plot_png_metadata(
        session,
        grid_role="main_grid",
        signature=f"{signature}:{_serialize_image_to_digest(main_grid_image)}",
    )
    saved_main = save_output_image(main_grid_image, prefix="xyz_plot_grid", metadata=main_metadata)
    host_output_filename = ""
    try:
        host_output_filename = mirror_output_asset_to_host_output(saved_main.path, filename=saved_main.handle)
    except Exception as exc:
        warnings.append(f"Failed to mirror XYZ main grid to host output: {exc}")
    main_grid_payload = {
        "asset_handle": saved_main.handle,
        "sha256": saved_main.sha256,
        "preview_data_url": build_data_url_from_path(Path(saved_main.path)),
        "host_output_filename": host_output_filename,
    }

    lone_images: list[dict[str, Any]] = []
    if include_lone_images:
        for entry in cell_assets:
            lone_images.append(
                {
                    "cell_id": entry["cell"].get("cell_id"),
                    "asset_handle": entry["asset_handle"],
                    "bindings": entry["cell"].get("bindings", []),
                }
            )

    return {
        "status": "ready",
        "signature": signature,
        "main_grid": main_grid_payload,
        "sub_grids": persisted_sub_grids,
        "lone_images": lone_images,
        "warnings": warnings,
    }
