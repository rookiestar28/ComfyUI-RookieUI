
from typing import Any

from rookieui.api import route_runtime
from rookieui.security.asset_guard import normalize_metadata_text
from rookieui.services.xyz_plot import build_xyz_plot_axes_snapshot


def _route_facade() -> Any:
    from rookieui.api import routes

    return routes


async def xyz_plot_axes(request: Any) -> Any:
    payload = build_xyz_plot_axes_snapshot()
    payload["service"] = normalize_metadata_text("rookieui")
    payload["status"] = normalize_metadata_text("ok")
    return route_runtime.json_response(payload, request=request)


async def xyz_plot_estimate(request: Any) -> Any:
    try:
        payload = await route_runtime.read_request_payload(request)
        response_payload = _route_facade().build_xyz_plot_estimate_snapshot(payload)
    except ValueError as exc:
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )

    response_payload["service"] = normalize_metadata_text("rookieui")
    response_payload["status"] = normalize_metadata_text("ok")
    return route_runtime.json_response(response_payload, request=request)


async def xyz_plot_run(request: Any) -> Any:
    try:
        payload = await route_runtime.read_request_payload(request)
        response_payload = await _route_facade().execute_xyz_plot_run_snapshot(payload, route_runtime.get_prompt_server_for_submission())
    except ValueError as exc:
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )
    except RuntimeError as exc:
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("host-unavailable"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=503,
            request=request,
        )

    response_payload["service"] = normalize_metadata_text("rookieui")
    response_payload["status"] = normalize_metadata_text("ok")
    return route_runtime.json_response(response_payload, request=request)


async def xyz_plot_sessions(request: Any) -> Any:
    try:
        response_payload = await _route_facade().build_xyz_plot_session_list_snapshot(
            route_runtime.get_prompt_server_for_submission(),
            client_id=route_runtime.read_request_query_value(request, "client_id"),
        )
    except ValueError as exc:
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )

    response_payload["service"] = normalize_metadata_text("rookieui")
    response_payload["status"] = normalize_metadata_text("ok")
    return route_runtime.json_response(response_payload, request=request)


async def xyz_plot_session_detail(request: Any) -> Any:
    session_id = route_runtime.read_request_match_value(request, "session_id")
    if not session_id:
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text("session_id is required."),
            },
            status=400,
            request=request,
        )
    try:
        response_payload = await _route_facade().build_xyz_plot_session_detail_snapshot(
            session_id,
            route_runtime.get_prompt_server_for_submission(),
            client_id=route_runtime.read_request_query_value(request, "client_id"),
        )
    except ValueError as exc:
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )

    response_payload["service"] = normalize_metadata_text("rookieui")
    response_payload["status"] = normalize_metadata_text("ok")
    return route_runtime.json_response(response_payload, request=request)


async def xyz_plot_session_cancel(request: Any) -> Any:
    session_id = route_runtime.read_request_match_value(request, "session_id")
    if not session_id:
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text("session_id is required."),
            },
            status=400,
            request=request,
        )
    try:
        response_payload = await _route_facade().execute_xyz_plot_session_cancel_snapshot(
            session_id,
            route_runtime.get_prompt_server_for_submission(),
            client_id=route_runtime.read_request_query_value(request, "client_id"),
        )
    except ValueError as exc:
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )

    response_payload["service"] = normalize_metadata_text("rookieui")
    response_payload["status"] = normalize_metadata_text("ok")
    return route_runtime.json_response(response_payload, request=request)


async def pnginfo_inspect(request: Any) -> Any:
    return await pnginfo_parse(request)
