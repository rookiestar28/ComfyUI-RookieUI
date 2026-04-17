from __future__ import annotations

from typing import Any

from rookieui.services.xyz_plot_axes import build_xyz_plot_axes_payload
from rookieui.services.xyz_plot_estimate import build_xyz_plot_estimate_payload
from rookieui.services.xyz_plot_sessions import (
    build_xyz_plot_session_detail_payload,
    build_xyz_plot_session_list_payload,
    execute_xyz_plot_run,
    execute_xyz_plot_session_cancel,
)


def build_xyz_plot_axes_snapshot() -> dict[str, Any]:
    return build_xyz_plot_axes_payload()


def build_xyz_plot_estimate_snapshot(payload: object) -> dict[str, Any]:
    return build_xyz_plot_estimate_payload(payload)


async def execute_xyz_plot_run_snapshot(payload: object, prompt_server: Any) -> dict[str, Any]:
    return await execute_xyz_plot_run(payload, prompt_server)


async def build_xyz_plot_session_list_snapshot(prompt_server: Any, *, client_id: object = None) -> dict[str, Any]:
    return await build_xyz_plot_session_list_payload(prompt_server, client_id=client_id)


async def build_xyz_plot_session_detail_snapshot(
    session_id: object,
    prompt_server: Any,
    *,
    client_id: object = None,
) -> dict[str, Any]:
    return await build_xyz_plot_session_detail_payload(session_id, prompt_server, client_id=client_id)


async def execute_xyz_plot_session_cancel_snapshot(
    session_id: object,
    prompt_server: Any,
    *,
    client_id: object = None,
) -> dict[str, Any]:
    return await execute_xyz_plot_session_cancel(session_id, prompt_server, client_id=client_id)
