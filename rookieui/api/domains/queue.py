from __future__ import annotations

from typing import Any

from rookieui.api import route_runtime
from rookieui.contracts.queue import build_queue_contract_meta
from rookieui.security.asset_guard import normalize_metadata_text
from rookieui.security.request_guard import normalize_client_id, normalize_option_label
from rookieui.services.queue_snapshot import build_queue_job_snapshot, build_queue_snapshot


def _get_prompt_server_for_submission() -> Any | None:
    from rookieui.api import routes

    return routes._get_prompt_server_for_submission()


def build_queue_snapshot_payload(*, client_id: str | None = None) -> dict[str, object]:
    payload = build_queue_snapshot(
        _get_prompt_server_for_submission(),
        client_id=client_id,
    )
    payload["service"] = normalize_metadata_text("rookieui")
    payload["status"] = normalize_metadata_text("ok")
    payload["contract"] = build_queue_contract_meta()
    return payload


def build_queue_job_snapshot_payload(
    prompt_id: str,
    *,
    client_id: str | None = None,
) -> dict[str, object]:
    normalized_prompt_id = normalize_option_label(prompt_id, "prompt_id", max_length=96)
    payload = build_queue_job_snapshot(
        _get_prompt_server_for_submission(),
        normalized_prompt_id,
        client_id=client_id,
    )
    payload["service"] = normalize_metadata_text("rookieui")
    payload["status"] = normalize_metadata_text("ok")
    payload["contract"] = build_queue_contract_meta()
    return payload


async def queue(request: Any) -> Any:
    try:
        client_id = normalize_client_id(route_runtime.read_request_query_value(request, "client_id"))
    except (TypeError, ValueError) as exc:
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )

    return route_runtime.json_response(build_queue_snapshot_payload(client_id=client_id), request=request)


async def queue_prompt(request: Any) -> Any:
    prompt_id = route_runtime.read_request_match_value(request, "prompt_id")
    if not prompt_id:
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text("prompt_id is required."),
            },
            status=400,
            request=request,
        )
    try:
        client_id = normalize_client_id(route_runtime.read_request_query_value(request, "client_id"))
        payload = build_queue_job_snapshot_payload(prompt_id, client_id=client_id)
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
    return route_runtime.json_response(payload, request=request)
