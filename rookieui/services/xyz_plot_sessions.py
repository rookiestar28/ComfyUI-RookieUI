from __future__ import annotations

import copy
import itertools
import json
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from rookieui.contracts.xyz_plot import build_xyz_plot_contract_meta
from rookieui.security.request_guard import normalize_client_id, normalize_option_label
from rookieui.services.coercion import coerce_int
from rookieui.services.img2img import normalize_img2img_request
from rookieui.services.prompt_submission import submit_prompt_workflow
from rookieui.services.queue_snapshot import build_queue_snapshot
from rookieui.services.txt2img import normalize_txt2img_request
from rookieui.services.workflow_translation import (
    translate_img2img_request,
    translate_txt2img_request,
)
from rookieui.services.xyz_plot_axes import build_xyz_plot_axes_payload, resolve_xyz_axis_contract
from rookieui.services.xyz_plot_estimate import XYZ_PLOT_MAX_TOTAL_CELLS
from rookieui.services.xyz_plot_values import parse_xyz_axis_values

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_STATE_LOCK = threading.RLock()
_XYZ_PLOT_SESSION_SCHEMA_VERSION = 1
_XYZ_PLOT_MAX_PARALLEL = 4
_XYZ_SLOT_LABELS = ("X", "Y", "Z")


def _xyz_plot_runtime_root() -> Path:
    override = os.environ.get("ROOKIEUI_XYZ_PLOT_RUNTIME_ROOT", "").strip()
    if override:
        return Path(override)
    return _WORKSPACE_ROOT / ".rookieui_runtime" / "xyz_plot"


def _xyz_plot_state_path() -> Path:
    return _xyz_plot_runtime_root() / "sessions.json"


def _ensure_xyz_plot_runtime_dir() -> None:
    _xyz_plot_runtime_root().mkdir(parents=True, exist_ok=True)


def _default_xyz_plot_store() -> dict[str, Any]:
    return {
        "schema_version": _XYZ_PLOT_SESSION_SCHEMA_VERSION,
        "sessions": {},
    }


def _load_xyz_plot_store() -> dict[str, Any]:
    _ensure_xyz_plot_runtime_dir()
    state_path = _xyz_plot_state_path()
    if not state_path.exists():
        return _default_xyz_plot_store()
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_xyz_plot_store()
    if not isinstance(payload, dict) or int(payload.get("schema_version", 0) or 0) != _XYZ_PLOT_SESSION_SCHEMA_VERSION:
        return _default_xyz_plot_store()
    sessions = payload.get("sessions", {})
    return {
        "schema_version": _XYZ_PLOT_SESSION_SCHEMA_VERSION,
        "sessions": sessions if isinstance(sessions, dict) else {},
    }


def _save_xyz_plot_store(store: dict[str, Any]) -> None:
    _ensure_xyz_plot_runtime_dir()
    _xyz_plot_state_path().write_text(json.dumps(store, indent=2, ensure_ascii=True), encoding="utf-8")


def _normalize_xyz_mode(raw_mode: object) -> str:
    normalized_mode = str(raw_mode or "").strip().lower()
    if normalized_mode not in {"txt2img", "img2img"}:
        raise ValueError("xyz_plot mode must be txt2img or img2img.")
    return normalized_mode


def _normalize_max_parallel(raw_value: object) -> int:
    max_parallel = coerce_int(raw_value, "max_parallel", via_str=True, default=1)
    if max_parallel < 1 or max_parallel > _XYZ_PLOT_MAX_PARALLEL:
        raise ValueError(f"max_parallel must be between 1 and {_XYZ_PLOT_MAX_PARALLEL}.")
    return max_parallel


def _axis_runtime_payload(axis_id: str) -> dict[str, Any]:
    payload = build_xyz_plot_axes_payload().get("axes", {})
    if not isinstance(payload, dict):
        return {}
    axis_payload = payload.get(axis_id, {})
    return axis_payload if isinstance(axis_payload, dict) else {}


def _normalize_session_axes(raw_axes: object, *, mode: str) -> list[dict[str, Any]]:
    if not isinstance(raw_axes, list):
        raise ValueError("xyz_plot axes must be a list.")
    if not raw_axes:
        raise ValueError("xyz_plot sessions require at least one axis.")
    if len(raw_axes) > len(_XYZ_SLOT_LABELS):
        raise ValueError(f"xyz_plot supports at most {len(_XYZ_SLOT_LABELS)} axes per session.")
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
        runtime_axis = _axis_runtime_payload(axis_id)
        if not runtime_axis.get("session_runner_support", False):
            raise ValueError(f"xyz_plot axis {axis_id} is not session-runnable yet.")
        choices = runtime_axis.get("choices", [])
        parsed_values = parse_xyz_axis_values(raw_axis.get("values", ""), contract, choices=choices if isinstance(choices, list) else [])
        normalized_axes.append(
            {
                "slot": _XYZ_SLOT_LABELS[index],
                "axis_id": axis_id,
                "title": contract.title,
                "support_tier": contract.support_tier,
                "value_input_mode": contract.value_input_mode,
                "parsed_values": [entry.to_payload() for entry in parsed_values],
            }
        )
        seen_axis_ids.add(axis_id)
    return normalized_axes


def _apply_prompt_sr(prompt_text: str, replacement: dict[str, Any]) -> str:
    source = str(replacement.get("source", "")).strip()
    target = str(replacement.get("target", "")).strip()
    if not source:
        return prompt_text
    return prompt_text.replace(source, target)


def _apply_prompt_order(prompt_text: str, ordered_tokens: list[str]) -> str:
    if not prompt_text.strip():
        return prompt_text
    segments = [segment.strip() for segment in prompt_text.split(",") if segment.strip()]
    if any(token not in segments for token in ordered_tokens):
        raise ValueError("prompt_order tokens must all exist as comma-separated prompt segments.")
    remaining = [segment for segment in segments if segment not in ordered_tokens]
    return ", ".join(list(ordered_tokens) + remaining)


def _apply_axis_binding(request_payload: dict[str, Any], binding: dict[str, Any], *, mode: str) -> None:
    axis_id = str(binding.get("axis_id", "")).strip()
    axis_value = binding.get("value")
    if axis_id == "seed":
        request_payload["seed"] = int(axis_value)
        return
    if axis_id == "steps":
        request_payload["steps"] = int(axis_value)
        return
    if axis_id == "cfg_scale":
        request_payload["cfg_scale"] = float(axis_value)
        return
    if axis_id == "sampler":
        request_payload["sampler_name"] = str(axis_value)
        return
    if axis_id == "scheduler":
        request_payload["scheduler_name"] = str(axis_value)
        return
    if axis_id == "checkpoint_name":
        request_payload["checkpoint_name"] = str(axis_value)
        return
    if axis_id == "vae":
        request_payload["vae_name"] = str(axis_value)
        return
    if axis_id == "clip_skip":
        request_payload["clip_skip"] = int(axis_value)
        return
    if axis_id == "size" and isinstance(axis_value, dict):
        request_payload["width"] = int(axis_value.get("width", request_payload.get("width", 512)))
        request_payload["height"] = int(axis_value.get("height", request_payload.get("height", 512)))
        return
    if axis_id == "denoising_strength":
        if mode != "img2img":
            raise ValueError("denoising_strength is only valid for img2img.")
        request_payload["denoise_strength"] = float(axis_value)
        return
    if axis_id == "hires_steps":
        request_payload["hires_enabled"] = True
        request_payload["hires_steps"] = int(axis_value)
        return
    if axis_id == "hires_upscaler":
        request_payload["hires_enabled"] = True
        request_payload["hires_upscale_method"] = str(axis_value)
        return
    if axis_id == "prompt_sr" and isinstance(axis_value, dict):
        request_payload["prompt"] = _apply_prompt_sr(str(request_payload.get("prompt", "")), axis_value)
        request_payload["negative_prompt"] = _apply_prompt_sr(str(request_payload.get("negative_prompt", "")), axis_value)
        return
    if axis_id == "prompt_order" and isinstance(axis_value, list):
        request_payload["prompt"] = _apply_prompt_order(str(request_payload.get("prompt", "")), [str(token) for token in axis_value])
        return
    raise ValueError(f"xyz_plot axis {axis_id} cannot be applied by the session runner.")


def _build_session_cells(normalized_axes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total_cells = 1
    for axis in normalized_axes:
        total_cells *= len(axis["parsed_values"])
        if total_cells > XYZ_PLOT_MAX_TOTAL_CELLS:
            raise ValueError(f"xyz_plot expands to too many cells (max {XYZ_PLOT_MAX_TOTAL_CELLS}).")
    cells: list[dict[str, Any]] = []
    combinations = [axis["parsed_values"] for axis in normalized_axes]
    for order_index, combination in enumerate(itertools.product(*combinations)):
        bindings = []
        for axis, parsed_entry in zip(normalized_axes, combination, strict=True):
            bindings.append(
                {
                    "slot": axis["slot"],
                    "axis_id": axis["axis_id"],
                    "title": axis["title"],
                    "label": parsed_entry["label"],
                    "value": parsed_entry["value"],
                }
            )
        cells.append(
            {
                "cell_id": f"cell-{order_index + 1:04d}",
                "order_index": order_index,
                "status": "pending",
                "bindings": bindings,
                "prompt_id": "",
                "submission_number": None,
                "output_filenames": [],
                "reusable_outputs": [],
                "error_detail": "",
                "submitted_at": None,
                "updated_at": int(time.time() * 1000),
            }
        )
    return cells


def _build_session_summary(session: dict[str, Any]) -> dict[str, int]:
    summary = {
        "total_cells": len(session.get("cells", [])),
        "pending_cells": 0,
        "queued_cells": 0,
        "in_progress_cells": 0,
        "completed_cells": 0,
        "failed_cells": 0,
        "cancelled_cells": 0,
        "submitted_cells": 0,
    }
    for cell in session.get("cells", []):
        status = str(cell.get("status", "")).strip()
        if status == "pending":
            summary["pending_cells"] += 1
        elif status == "queued":
            summary["queued_cells"] += 1
            summary["submitted_cells"] += 1
        elif status == "in_progress":
            summary["in_progress_cells"] += 1
            summary["submitted_cells"] += 1
        elif status == "completed":
            summary["completed_cells"] += 1
            summary["submitted_cells"] += 1
        elif status == "failed":
            summary["failed_cells"] += 1
            summary["submitted_cells"] += 1
        elif status == "cancelled":
            summary["cancelled_cells"] += 1
    return summary


def _derive_session_status(session: dict[str, Any]) -> str:
    summary = _build_session_summary(session)
    if summary["in_progress_cells"] or summary["queued_cells"]:
        return "in_progress"
    if summary["pending_cells"] and not summary["submitted_cells"]:
        return "pending"
    if summary["pending_cells"] and session.get("cancel_requested"):
        return "cancelled"
    if summary["pending_cells"]:
        return "queued"
    if summary["failed_cells"]:
        return "failed"
    if summary["cancelled_cells"]:
        return "cancelled"
    return "completed"


def _serialize_session(session: dict[str, Any], *, surface: str, include_cells: bool) -> dict[str, Any]:
    session_payload = {
        "session_id": session["session_id"],
        "mode": session["mode"],
        "status": _derive_session_status(session),
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
        "client_id": session.get("client_id"),
        "max_parallel": session["max_parallel"],
        "cancel_requested": bool(session.get("cancel_requested", False)),
        "axes": session["axes"],
        "summary": _build_session_summary(session),
        "last_error": session.get("last_error", ""),
    }
    if include_cells:
        session_payload["cells"] = session["cells"]
    return {
        "contract": build_xyz_plot_contract_meta(surface=surface),
        "session": session_payload,
    }


def _best_effort_cancel_prompt(prompt_server: Any, prompt_id: str) -> bool:
    prompt_queue = getattr(prompt_server, "prompt_queue", None)
    if prompt_queue is None:
        return False
    for method_name in ("delete_queue_item", "delete_item", "remove_item", "remove_queue_item"):
        method = getattr(prompt_queue, method_name, None)
        if not callable(method):
            continue
        result = method(prompt_id)
        return True if result is None else bool(result)
    return False


async def _submit_cell_for_session(session: dict[str, Any], cell: dict[str, Any], prompt_server: Any) -> None:
    request_payload = copy.deepcopy(session["base_request"])
    for binding in cell.get("bindings", []):
        _apply_axis_binding(request_payload, binding, mode=session["mode"])
    if session["mode"] == "txt2img":
        normalized = normalize_txt2img_request(request_payload)
        translation = translate_txt2img_request(normalized)
    else:
        normalized = normalize_img2img_request(request_payload)
        translation = translate_img2img_request(normalized)
    submission = await submit_prompt_workflow(
        prompt_server,
        translation.workflow,
        client_id=session.get("client_id"),
        origin="rookieui",
        surface="xyz_plot",
        profile=str(getattr(translation, "profile", "") or ""),
        extra_metadata={
            "rookieui_xyz_session_id": session["session_id"],
            "rookieui_xyz_cell_id": cell["cell_id"],
            "rookieui_xyz_mode": session["mode"],
            "rookieui_xyz_cell_index": cell["order_index"],
        },
    )
    cell["prompt_id"] = str(submission.get("prompt_id", ""))
    cell["submission_number"] = submission.get("number")
    cell["status"] = "queued"
    cell["submitted_at"] = int(time.time() * 1000)
    cell["updated_at"] = int(time.time() * 1000)


def _lookup_queue_jobs(prompt_server: Any, *, client_id: str | None, history_limit: int) -> dict[str, dict[str, Any]]:
    snapshot = build_queue_snapshot(prompt_server, history_limit=history_limit, client_id=client_id)
    jobs = snapshot.get("jobs", [])
    if not isinstance(jobs, list):
        return {}
    return {
        str(job.get("id", "")): job
        for job in jobs
        if isinstance(job, dict) and str(job.get("id", "")).strip()
    }


async def _refresh_session_state(session: dict[str, Any], prompt_server: Any) -> None:
    jobs_by_id = _lookup_queue_jobs(
        prompt_server,
        client_id=session.get("client_id"),
        history_limit=max(64, len(session.get("cells", [])) * 2),
    )
    for cell in session.get("cells", []):
        prompt_id = str(cell.get("prompt_id", "")).strip()
        if session.get("cancel_requested") and cell.get("status") == "pending":
            cell["status"] = "cancelled"
            cell["updated_at"] = int(time.time() * 1000)
            continue
        if not prompt_id:
            continue
        job = jobs_by_id.get(prompt_id)
        if not job:
            continue
        cell["status"] = str(job.get("status", cell.get("status", ""))).strip() or cell.get("status", "queued")
        cell["output_filenames"] = list(job.get("output_filenames", [])) if isinstance(job.get("output_filenames"), list) else []
        cell["reusable_outputs"] = list(job.get("reusable_outputs", [])) if isinstance(job.get("reusable_outputs"), list) else []
        cell["updated_at"] = int(time.time() * 1000)

    active_count = len([cell for cell in session.get("cells", []) if str(cell.get("status", "")).strip() in {"queued", "in_progress"}])
    if session.get("cancel_requested"):
        session["updated_at"] = int(time.time() * 1000)
        return
    for cell in session.get("cells", []):
        if active_count >= session["max_parallel"]:
            break
        if str(cell.get("status", "")).strip() != "pending":
            continue
        try:
            await _submit_cell_for_session(session, cell, prompt_server)
        except Exception as exc:
            cell["status"] = "failed"
            cell["error_detail"] = str(exc)
            cell["updated_at"] = int(time.time() * 1000)
            session["cancel_requested"] = True
            session["last_error"] = str(exc)
            break
        active_count += 1
    session["updated_at"] = int(time.time() * 1000)


def _normalize_session_request(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("xyz_plot session payload must be an object.")
    base_request = payload.get("base_request", {})
    if not isinstance(base_request, dict):
        raise ValueError("xyz_plot base_request must be an object.")
    mode = _normalize_xyz_mode(payload.get("mode"))
    axes = _normalize_session_axes(payload.get("axes", []), mode=mode)
    return {
        "session_id": f"xyz-{secrets.token_hex(8)}",
        "mode": mode,
        "base_request": copy.deepcopy(base_request),
        "axes": axes,
        "cells": _build_session_cells(axes),
        "created_at": int(time.time() * 1000),
        "updated_at": int(time.time() * 1000),
        "client_id": normalize_client_id(payload.get("client_id")),
        "max_parallel": _normalize_max_parallel(payload.get("max_parallel")),
        "cancel_requested": False,
        "last_error": "",
    }


def _load_session_or_raise(store: dict[str, Any], session_id: object, *, client_id: str | None) -> dict[str, Any]:
    normalized_session_id = normalize_option_label(session_id, "session_id", max_length=80)
    raw_session = store.get("sessions", {}).get(normalized_session_id)
    if not isinstance(raw_session, dict):
        raise ValueError("xyz_plot session was not found.")
    if client_id is not None and raw_session.get("client_id") not in {None, "", client_id}:
        raise ValueError("xyz_plot session was not found.")
    return raw_session


async def execute_xyz_plot_run(payload: object, prompt_server: Any) -> dict[str, Any]:
    with _STATE_LOCK:
        store = _load_xyz_plot_store()
        session = _normalize_session_request(payload)
        await _refresh_session_state(session, prompt_server)
        store["sessions"][session["session_id"]] = session
        _save_xyz_plot_store(store)
        return _serialize_session(session, surface="xyz_plot_run", include_cells=True)


async def build_xyz_plot_session_list_payload(prompt_server: Any, *, client_id: object = None) -> dict[str, Any]:
    normalized_client_id = normalize_client_id(client_id)
    with _STATE_LOCK:
        store = _load_xyz_plot_store()
        sessions: list[dict[str, Any]] = []
        for session in store.get("sessions", {}).values():
            if not isinstance(session, dict):
                continue
            if normalized_client_id is not None and session.get("client_id") not in {None, "", normalized_client_id}:
                continue
            await _refresh_session_state(session, prompt_server)
            sessions.append(_serialize_session(session, surface="xyz_plot_session_list", include_cells=False)["session"])
        _save_xyz_plot_store(store)
        sessions.sort(key=lambda entry: int(entry.get("created_at", 0) or 0), reverse=True)
        return {
            "contract": build_xyz_plot_contract_meta(surface="xyz_plot_session_list"),
            "sessions": sessions,
        }


async def build_xyz_plot_session_detail_payload(session_id: object, prompt_server: Any, *, client_id: object = None) -> dict[str, Any]:
    normalized_client_id = normalize_client_id(client_id)
    with _STATE_LOCK:
        store = _load_xyz_plot_store()
        session = _load_session_or_raise(store, session_id, client_id=normalized_client_id)
        await _refresh_session_state(session, prompt_server)
        _save_xyz_plot_store(store)
        return _serialize_session(session, surface="xyz_plot_session_detail", include_cells=True)


async def execute_xyz_plot_session_cancel(session_id: object, prompt_server: Any, *, client_id: object = None) -> dict[str, Any]:
    normalized_client_id = normalize_client_id(client_id)
    with _STATE_LOCK:
        store = _load_xyz_plot_store()
        session = _load_session_or_raise(store, session_id, client_id=normalized_client_id)
        session["cancel_requested"] = True
        for cell in session.get("cells", []):
            status = str(cell.get("status", "")).strip()
            if status == "pending":
                cell["status"] = "cancelled"
            elif status == "queued":
                prompt_id = str(cell.get("prompt_id", "")).strip()
                if prompt_id and _best_effort_cancel_prompt(prompt_server, prompt_id):
                    cell["status"] = "cancelled"
            cell["updated_at"] = int(time.time() * 1000)
        await _refresh_session_state(session, prompt_server)
        _save_xyz_plot_store(store)
        return _serialize_session(session, surface="xyz_plot_session_cancel", include_cells=True)


def reset_xyz_plot_session_store_for_tests() -> None:
    with _STATE_LOCK:
        state_path = _xyz_plot_state_path()
        if state_path.exists():
            state_path.unlink()
