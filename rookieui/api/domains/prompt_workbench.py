from __future__ import annotations

from typing import Any

from rookieui.api import route_runtime
from rookieui.security.asset_guard import normalize_metadata_text
from rookieui.services.async_runtime import run_bounded_blocking
from rookieui.services.prompt_workbench import (
    apply_prompt_workbench_blacklist_update,
    apply_prompt_workbench_config_update,
    apply_prompt_workbench_favorites_update,
    apply_prompt_workbench_history_update,
    apply_prompt_workbench_surface_state_update,
    build_prompt_workbench_blacklist_payload,
    build_prompt_workbench_catalog_snapshot,
    build_prompt_workbench_config_payload,
    build_prompt_workbench_favorites_payload,
    build_prompt_workbench_history_payload,
    build_prompt_workbench_export_payload,
    apply_prompt_workbench_import,
    build_prompt_workbench_provider_catalog_payload,
    build_prompt_workbench_surface_state_payload,
)
from rookieui.services.prompt_workbench_danbooru import (
    PromptWorkbenchDanbooruExecutionError,
    PromptWorkbenchDanbooruHostUnavailableError,
)


def _route_facade() -> Any:
    from rookieui.api import routes

    return routes


async def prompt_tools_config(request: Any) -> Any:
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **build_prompt_workbench_config_payload(),
        },
        request=request,
    )


async def prompt_tools_config_update(request: Any) -> Any:
    try:
        payload = await route_runtime.read_request_payload(request)
        result = apply_prompt_workbench_config_update(payload.get("config", payload))
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
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_state(request: Any) -> Any:
    namespace = route_runtime.read_request_query_value(request, "namespace")
    try:
        result = build_prompt_workbench_surface_state_payload(namespace)
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
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_state_update(request: Any) -> Any:
    try:
        payload = await route_runtime.read_request_payload(request)
        result = apply_prompt_workbench_surface_state_update(payload.get("namespace"), payload.get("state"))
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
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_history(request: Any) -> Any:
    namespace = route_runtime.read_request_query_value(request, "namespace")
    try:
        result = build_prompt_workbench_history_payload(namespace)
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
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_history_update(request: Any) -> Any:
    try:
        payload = await route_runtime.read_request_payload(request)
        result = apply_prompt_workbench_history_update(
            payload.get("namespace"),
            action=payload.get("action", "push"),
            payload=payload,
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
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_favorites(request: Any) -> Any:
    namespace = route_runtime.read_request_query_value(request, "namespace")
    try:
        result = build_prompt_workbench_favorites_payload(namespace)
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
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_favorites_update(request: Any) -> Any:
    try:
        payload = await route_runtime.read_request_payload(request)
        result = apply_prompt_workbench_favorites_update(
            payload.get("namespace"),
            action=payload.get("action", "push"),
            payload=payload,
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
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_blacklist(request: Any) -> Any:
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **build_prompt_workbench_blacklist_payload(),
        },
        request=request,
    )


async def prompt_tools_blacklist_update(request: Any) -> Any:
    try:
        payload = await route_runtime.read_request_payload(request)
        result = apply_prompt_workbench_blacklist_update(payload.get("blacklist", payload))
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
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_providers(request: Any) -> Any:
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **build_prompt_workbench_provider_catalog_payload(),
        },
        request=request,
    )


async def prompt_tools_export(request: Any) -> Any:
    # SECURITY: this browser-readable route must never accept a raw-secret export option.
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **build_prompt_workbench_export_payload(),
        },
        request=request,
    )


async def prompt_tools_import(request: Any) -> Any:
    try:
        payload = await route_runtime.read_request_payload(request)
        result = apply_prompt_workbench_import(payload.get("export", payload))
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
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_translate(request: Any) -> Any:
    try:
        payload = await route_runtime.read_request_payload(request)
        result = await run_bounded_blocking("provider", _route_facade().execute_prompt_workbench_translate, payload)
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
                "status": normalize_metadata_text("provider-error"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=502,
            request=request,
        )
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_assist(request: Any) -> Any:
    try:
        payload = await route_runtime.read_request_payload(request)
        result = await run_bounded_blocking("provider", _route_facade().execute_prompt_workbench_ai_assist, payload)
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
                "status": normalize_metadata_text("provider-error"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=502,
            request=request,
        )
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_catalog(request: Any) -> Any:
    language = route_runtime.read_request_query_value(request, "language")
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **build_prompt_workbench_catalog_snapshot(language=language),
        },
        request=request,
    )


async def prompt_tools_analyze(request: Any) -> Any:
    try:
        payload = await route_runtime.read_request_payload(request)
        result = _route_facade().execute_prompt_workbench_analysis(payload)
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
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_upsample(request: Any) -> Any:
    try:
        payload = await route_runtime.read_request_payload(request)
        result = await _route_facade().execute_prompt_workbench_upsample(payload)
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
    except PromptWorkbenchDanbooruHostUnavailableError as exc:
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("host-unavailable"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=503,
            request=request,
        )
    except PromptWorkbenchDanbooruExecutionError as exc:
        return route_runtime.json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("host-action-error"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=502,
            request=request,
        )
    return route_runtime.json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )
