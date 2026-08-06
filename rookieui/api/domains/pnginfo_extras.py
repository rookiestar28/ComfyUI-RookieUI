
from typing import Any

from rookieui.api import route_runtime
from rookieui.contracts.extras import build_extras_contract_meta
from rookieui.contracts.pnginfo import build_pnginfo_contract_meta
from rookieui.security.asset_guard import normalize_metadata_text
from rookieui.services.async_runtime import run_bounded_blocking
from rookieui.services.pnginfo import parse_pnginfo_payload


def _route_facade() -> Any:
    from rookieui.api import routes

    return routes


async def pnginfo_parse(request: Any) -> Any:
    try:
        payload = await route_runtime.read_request_payload(request)
        result = parse_pnginfo_payload(payload)
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

    response_payload = result.to_payload()
    response_payload["service"] = normalize_metadata_text("rookieui")
    response_payload["status"] = normalize_metadata_text("ok")
    response_payload["contract"] = build_pnginfo_contract_meta()
    return route_runtime.json_response(response_payload, request=request)
async def pnginfo_inspect(request: Any) -> Any:
    return await pnginfo_parse(request)
async def extras_run(request: Any) -> Any:
    try:
        payload = await route_runtime.read_request_payload(request)
        def execute() -> Any:
            normalized = _route_facade().normalize_extras_request(payload)
            return _route_facade().execute_extras_request(normalized)

        result = await run_bounded_blocking("extras", execute)
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

    response_payload = result.to_payload()
    response_payload["service"] = normalize_metadata_text("rookieui")
    response_payload["status"] = normalize_metadata_text("ok")
    response_payload["contract"] = build_extras_contract_meta()
    return route_runtime.json_response(response_payload, request=request)
