from __future__ import annotations

from typing import Any

from rookieui.api import route_runtime
from rookieui.security.asset_guard import normalize_metadata_text
from rookieui.services.adetailer import build_adetailer_catalog_payload
from rookieui.services.controlnet import (
    build_controlnet_control_types_payload,
    build_controlnet_model_list_payload,
    build_controlnet_module_list_payload,
)
from rookieui.services.async_runtime import run_bounded_blocking


def _route_facade() -> Any:
    from rookieui.api import routes

    return routes


def build_adetailer_snapshot() -> dict[str, object]:
    return build_adetailer_catalog_payload()


async def controlnet_model_list(request: Any) -> Any:
    payload = build_controlnet_model_list_payload()
    payload["service"] = normalize_metadata_text("rookieui")
    payload["status"] = normalize_metadata_text("ok")
    return route_runtime.json_response(payload, request=request)


async def controlnet_module_list(request: Any) -> Any:
    payload = build_controlnet_module_list_payload()
    payload["service"] = normalize_metadata_text("rookieui")
    payload["status"] = normalize_metadata_text("ok")
    return route_runtime.json_response(payload, request=request)


async def controlnet_control_types(request: Any) -> Any:
    payload = build_controlnet_control_types_payload()
    payload["service"] = normalize_metadata_text("rookieui")
    payload["status"] = normalize_metadata_text("ok")
    return route_runtime.json_response(payload, request=request)


async def controlnet_detect(request: Any) -> Any:
    facade = _route_facade()
    try:
        payload = await route_runtime.read_request_payload(request)
        requested_module = normalize_metadata_text(str(payload.get("controlnet_module", "")).strip() or "none")
        requested_image_count = route_runtime.count_detect_input_images(payload)
        facade._LOGGER.info(
            "RookieUI ControlNet detect request received (module=%s, images=%s).",
            requested_module,
            requested_image_count,
        )
        result = await run_bounded_blocking("controlnet", facade.build_controlnet_detect_payload, payload)
    except ValueError as exc:
        facade._LOGGER.warning("RookieUI ControlNet detect rejected invalid request: %s", str(exc))
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )

    warning_codes = result.get("warning_codes") if isinstance(result, dict) else []
    output_images = result.get("images") if isinstance(result, dict) else []
    output_image_count = len(output_images) if isinstance(output_images, list) else 0
    detect_backend = normalize_metadata_text(str(result.get("detect_backend", "")).strip()) if isinstance(result, dict) else ""
    source_label = normalize_metadata_text(str(result.get("source", "")).strip()) if isinstance(result, dict) else ""
    processor_label = normalize_metadata_text(str(result.get("processor", "")).strip()) if isinstance(result, dict) else ""
    control_model_label = (
        normalize_metadata_text(str(result.get("requested_controlnet_model", "")).strip()) if isinstance(result, dict) else ""
    )
    if isinstance(warning_codes, list) and warning_codes:
        facade._LOGGER.warning(
            "RookieUI ControlNet detect completed with warnings (module=%s, images=%s, output_images=%s, source=%s, detect_backend=%s, processor=%s, control_model=%s, warning_codes=%s).",
            requested_module,
            requested_image_count,
            output_image_count,
            source_label,
            detect_backend,
            processor_label,
            control_model_label,
            ",".join(str(code) for code in warning_codes),
        )
    else:
        facade._LOGGER.info(
            "RookieUI ControlNet detect completed (module=%s, images=%s, output_images=%s, source=%s, detect_backend=%s, processor=%s, control_model=%s).",
            requested_module,
            requested_image_count,
            output_image_count,
            source_label,
            detect_backend,
            processor_label,
            control_model_label,
        )

    result["service"] = normalize_metadata_text("rookieui")
    result["status"] = normalize_metadata_text("ok")
    return route_runtime.json_response(result, request=request)


async def adetailer_catalog(request: Any) -> Any:
    payload = build_adetailer_snapshot()
    payload["service"] = normalize_metadata_text("rookieui")
    payload["status"] = normalize_metadata_text("ok")
    return route_runtime.json_response(payload, request=request)
