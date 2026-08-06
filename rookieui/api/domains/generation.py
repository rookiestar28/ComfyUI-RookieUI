from __future__ import annotations

from typing import Any

from rookieui.api import route_runtime
from rookieui.security.asset_guard import normalize_metadata_text
from rookieui.security.request_guard import normalize_client_id
from rookieui.services.coercion import coerce_bool
from rookieui.services.img2img import normalize_img2img_request
from rookieui.services.prompt_submission import submit_prompt_workflow
from rookieui.services.txt2img import normalize_txt2img_request
from rookieui.services.workflow_translation import translate_img2img_request, translate_txt2img_request


def _route_facade() -> Any:
    from rookieui.api import routes

    return routes


async def _submit_translation_payload(
    *,
    dry_run: bool,
    client_id: object,
    translation: Any,
    surface: str,
    request: Any | None = None,
) -> Any:
    response_payload = translation.to_payload()
    if dry_run:
        response_payload["submission"] = {
            "accepted": False,
            "mode": "dry-run",
        }
        return route_runtime.json_response(response_payload, request=request)

    try:
        submission = await _route_facade().submit_prompt_workflow(
            _route_facade()._get_prompt_server_for_submission(),
            response_payload["workflow"],
            client_id=client_id if isinstance(client_id, str) else None,
            origin="rookieui",
            surface=surface,
            profile=str(response_payload.get("profile", "")),
            extra_pnginfo=response_payload.get("generation_metadata", {}).get("extra_pnginfo"),
        )
    except RuntimeError as exc:
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("host-unavailable"),
                "detail": normalize_metadata_text(str(exc)),
                "translation": response_payload,
            },
            status=503,
            request=request,
        )
    except ValueError as exc:
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("submission-rejected"),
                "detail": normalize_metadata_text(str(exc)),
                "translation": response_payload,
            },
            status=400,
            request=request,
        )

    response_payload["mode"] = "queued"
    response_payload["submission"] = submission
    return route_runtime.json_response(response_payload, request=request)


async def txt2img(request: Any) -> Any:
    try:
        payload = await route_runtime.read_request_payload(request)
        request_payload = dict(payload)
        dry_run = coerce_bool(request_payload.pop("dry_run", False), "dry_run", strict=False)
        client_id = normalize_client_id(request_payload.pop("client_id", None))
        normalized = normalize_txt2img_request(request_payload)
        translation = translate_txt2img_request(normalized)
    except (TypeError, ValueError) as exc:
        # DEBUG HOTSPOT: route-entry payload drift must return JSON invalid-request, not an aiohttp traceback.
        _route_facade()._LOGGER.warning("RookieUI txt2img rejected invalid request: %s", str(exc))
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )

    return await _submit_translation_payload(
        dry_run=dry_run,
        client_id=client_id,
        translation=translation,
        surface="txt2img",
        request=request,
    )


async def img2img(request: Any) -> Any:
    try:
        payload = await route_runtime.read_request_payload(request)
        request_payload = dict(payload)
        dry_run = coerce_bool(request_payload.pop("dry_run", False), "dry_run", strict=False)
        client_id = normalize_client_id(request_payload.pop("client_id", None))
        normalized = normalize_img2img_request(request_payload)
        translation = translate_img2img_request(normalized)
    except (TypeError, ValueError) as exc:
        # DEBUG HOTSPOT: route-entry payload drift must return JSON invalid-request, not an aiohttp traceback.
        _route_facade()._LOGGER.warning("RookieUI img2img rejected invalid request: %s", str(exc))
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )

    return await _submit_translation_payload(
        dry_run=dry_run,
        client_id=client_id,
        translation=translation,
        surface="img2img",
        request=request,
    )
