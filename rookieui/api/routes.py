from __future__ import annotations

import logging
from typing import Any

from rookieui.contracts.extras import build_extras_contract_meta
from rookieui.contracts.pnginfo import build_pnginfo_contract_meta
from rookieui.contracts.queue import build_queue_contract_meta
from rookieui.services.model_inventory import discover_model_inventory
from rookieui.services.extras import execute_extras_request, normalize_extras_request
from rookieui.services.parity_matrix import build_parity_payload
from rookieui.services.presets import build_preset_payload
from rookieui.services.img2img import normalize_img2img_request
from rookieui.services.pnginfo import parse_pnginfo_payload
from rookieui.services.queue_snapshot import build_queue_job_snapshot, build_queue_snapshot
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
    execute_prompt_workbench_ai_assist,
    execute_prompt_workbench_analysis,
    execute_prompt_workbench_translate,
    execute_prompt_workbench_upsample,
)
from rookieui.services.prompt_workbench_danbooru import (
    PromptWorkbenchDanbooruExecutionError,
    PromptWorkbenchDanbooruHostUnavailableError,
)
from rookieui.services.xyz_plot import (
    build_xyz_plot_axes_snapshot,
    build_xyz_plot_estimate_snapshot,
    build_xyz_plot_session_detail_snapshot,
    build_xyz_plot_session_list_snapshot,
    execute_xyz_plot_run_snapshot,
    execute_xyz_plot_session_cancel_snapshot,
)
from rookieui.services.prompt_submission import submit_prompt_workflow
from rookieui.services.txt2img import normalize_txt2img_request
from rookieui.services.workflow_translation import (
    translate_img2img_request,
    translate_txt2img_request,
)
from rookieui.services.coercion import coerce_bool
from rookieui.services.capabilities import build_capabilities_payload
from rookieui.services.compatibility import build_compatibility_payload
from rookieui.services.version import build_runtime_metadata_payload
from rookieui.services.controlnet import (
    build_controlnet_control_types_payload,
    build_controlnet_detect_payload,
    build_controlnet_model_list_payload,
    build_controlnet_module_list_payload,
)
from rookieui.services.adetailer import build_adetailer_catalog_payload
from rookieui.security.asset_guard import normalize_metadata_text
from rookieui.security.request_guard import normalize_client_id, normalize_option_label
from rookieui.security.route_guard import API_INTERNAL_ROUTE_PREFIX, INTERNAL_ROUTE_PREFIX, SafeRouteRegistrar

INTERNAL_ROUTE_PATHS = [
    f"{INTERNAL_ROUTE_PREFIX}/health",
    f"{INTERNAL_ROUTE_PREFIX}/bootstrap",
    f"{INTERNAL_ROUTE_PREFIX}/capabilities",
    f"{INTERNAL_ROUTE_PREFIX}/parity",
    f"{INTERNAL_ROUTE_PREFIX}/compatibility",
    f"{INTERNAL_ROUTE_PREFIX}/models",
    f"{INTERNAL_ROUTE_PREFIX}/presets",
    f"{INTERNAL_ROUTE_PREFIX}/queue",
    f"{INTERNAL_ROUTE_PREFIX}/queue/{{prompt_id}}",
    f"{INTERNAL_ROUTE_PREFIX}/prompt-tools/config",
    f"{INTERNAL_ROUTE_PREFIX}/prompt-tools/state",
    f"{INTERNAL_ROUTE_PREFIX}/prompt-tools/history",
    f"{INTERNAL_ROUTE_PREFIX}/prompt-tools/favorites",
    f"{INTERNAL_ROUTE_PREFIX}/prompt-tools/blacklist",
    f"{INTERNAL_ROUTE_PREFIX}/prompt-tools/providers",
    f"{INTERNAL_ROUTE_PREFIX}/prompt-tools/export",
    f"{INTERNAL_ROUTE_PREFIX}/prompt-tools/import",
    f"{INTERNAL_ROUTE_PREFIX}/prompt-tools/translate",
    f"{INTERNAL_ROUTE_PREFIX}/prompt-tools/assist",
    f"{INTERNAL_ROUTE_PREFIX}/prompt-tools/catalog",
    f"{INTERNAL_ROUTE_PREFIX}/prompt-tools/analyze",
    f"{INTERNAL_ROUTE_PREFIX}/prompt-tools/upsample",
    f"{INTERNAL_ROUTE_PREFIX}/xyz-plot/axes",
    f"{INTERNAL_ROUTE_PREFIX}/xyz-plot/estimate",
    f"{INTERNAL_ROUTE_PREFIX}/xyz-plot/run",
    f"{INTERNAL_ROUTE_PREFIX}/xyz-plot/sessions",
    f"{INTERNAL_ROUTE_PREFIX}/xyz-plot/sessions/{{session_id}}",
    f"{INTERNAL_ROUTE_PREFIX}/xyz-plot/sessions/{{session_id}}/cancel",
    f"{INTERNAL_ROUTE_PREFIX}/pnginfo/parse",
    f"{INTERNAL_ROUTE_PREFIX}/pnginfo/inspect",
    f"{INTERNAL_ROUTE_PREFIX}/controlnet/model_list",
    f"{INTERNAL_ROUTE_PREFIX}/controlnet/module_list",
    f"{INTERNAL_ROUTE_PREFIX}/controlnet/control_types",
    f"{INTERNAL_ROUTE_PREFIX}/controlnet/detect",
    f"{INTERNAL_ROUTE_PREFIX}/adetailer/catalog",
    f"{INTERNAL_ROUTE_PREFIX}/generate/txt2img",
    f"{INTERNAL_ROUTE_PREFIX}/generate/img2img",
    f"{INTERNAL_ROUTE_PREFIX}/extras/run",
]
_LOGGER = logging.getLogger("ComfyUI-RookieUI")


def build_health_payload() -> dict[str, Any]:
    return {
        "service": normalize_metadata_text("rookieui"),
        "status": normalize_metadata_text("ok"),
    }


def build_bootstrap_payload() -> dict[str, Any]:
    return {
        "service": normalize_metadata_text("rookieui"),
        "status": normalize_metadata_text("bootstrap-ready"),
        "visibility": normalize_metadata_text("internal"),
        "runtime": {
            "shell_version": normalize_metadata_text(build_runtime_metadata_payload()["shell_version"]),
            "build_fingerprint": normalize_metadata_text(build_runtime_metadata_payload()["build_fingerprint"]),
        },
        "routes": list(INTERNAL_ROUTE_PATHS),
    }


def build_capabilities_snapshot() -> dict[str, object]:
    return build_capabilities_payload(routes=list(INTERNAL_ROUTE_PATHS))


def build_parity_snapshot() -> dict[str, object]:
    return build_parity_payload()


def build_compatibility_snapshot() -> dict[str, object]:
    return build_compatibility_payload()


def build_models_snapshot() -> dict[str, object]:
    return discover_model_inventory().to_payload()


def build_presets_snapshot() -> dict[str, object]:
    return build_preset_payload()


def build_adetailer_snapshot() -> dict[str, object]:
    return build_adetailer_catalog_payload()


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


def _get_prompt_server_for_submission() -> Any | None:
    try:
        from rookieui.services.route_bootstrap import _get_prompt_server_instance
    except Exception:
        _LOGGER.debug("RookieUI route helper import fallback triggered.", exc_info=True)
        return None
    return _get_prompt_server_instance()


def _json_response(payload: dict[str, Any], *, status: int = 200, request: Any | None = None) -> Any:
    try:
        from aiohttp import web
    except ImportError:
        return {"status": status, "payload": payload}
    if request is None or request.__class__.__module__.split(".", 1)[0] != "aiohttp":
        return {"status": status, "payload": payload}
    return web.json_response(payload, status=status)


async def health(request: Any) -> Any:
    return _json_response(build_health_payload(), request=request)


async def bootstrap(request: Any) -> Any:
    return _json_response(build_bootstrap_payload(), request=request)


async def capabilities(request: Any) -> Any:
    return _json_response(build_capabilities_snapshot(), request=request)


async def parity(request: Any) -> Any:
    return _json_response(build_parity_snapshot(), request=request)


async def compatibility(request: Any) -> Any:
    return _json_response(build_compatibility_snapshot(), request=request)


async def models(request: Any) -> Any:
    return _json_response(build_models_snapshot(), request=request)


async def presets(request: Any) -> Any:
    return _json_response(build_presets_snapshot(), request=request)


async def controlnet_model_list(request: Any) -> Any:
    payload = build_controlnet_model_list_payload()
    payload["service"] = normalize_metadata_text("rookieui")
    payload["status"] = normalize_metadata_text("ok")
    return _json_response(payload, request=request)


async def controlnet_module_list(request: Any) -> Any:
    payload = build_controlnet_module_list_payload()
    payload["service"] = normalize_metadata_text("rookieui")
    payload["status"] = normalize_metadata_text("ok")
    return _json_response(payload, request=request)


async def controlnet_control_types(request: Any) -> Any:
    payload = build_controlnet_control_types_payload()
    payload["service"] = normalize_metadata_text("rookieui")
    payload["status"] = normalize_metadata_text("ok")
    return _json_response(payload, request=request)


async def controlnet_detect(request: Any) -> Any:
    try:
        payload = await _read_request_payload(request)
        requested_module = normalize_metadata_text(str(payload.get("controlnet_module", "")).strip() or "none")
        requested_image_count = _count_detect_input_images(payload)
        _LOGGER.info(
            "RookieUI ControlNet detect request received (module=%s, images=%s).",
            requested_module,
            requested_image_count,
        )
        result = build_controlnet_detect_payload(payload)
    except ValueError as exc:
        _LOGGER.warning("RookieUI ControlNet detect rejected invalid request: %s", str(exc))
        return _json_response(
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
        _LOGGER.warning(
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
        _LOGGER.info(
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
    return _json_response(result, request=request)


async def adetailer_catalog(request: Any) -> Any:
    payload = build_adetailer_snapshot()
    payload["service"] = normalize_metadata_text("rookieui")
    payload["status"] = normalize_metadata_text("ok")
    return _json_response(payload, request=request)


async def queue(request: Any) -> Any:
    try:
        client_id = normalize_client_id(_read_request_query_value(request, "client_id"))
    except (TypeError, ValueError) as exc:
        # DEBUG HOTSPOT: frontend Extras payload drift must be contained as JSON invalid-request.
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )

    return _json_response(build_queue_snapshot_payload(client_id=client_id), request=request)


async def queue_prompt(request: Any) -> Any:
    prompt_id = _read_request_match_value(request, "prompt_id")
    if not prompt_id:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text("prompt_id is required."),
            },
            status=400,
            request=request,
        )
    try:
        client_id = normalize_client_id(_read_request_query_value(request, "client_id"))
        payload = build_queue_job_snapshot_payload(prompt_id, client_id=client_id)
    except ValueError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )
    return _json_response(payload, request=request)


async def prompt_tools_config(request: Any) -> Any:
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **build_prompt_workbench_config_payload(),
        },
        request=request,
    )


async def prompt_tools_config_update(request: Any) -> Any:
    try:
        payload = await _read_request_payload(request)
        result = apply_prompt_workbench_config_update(payload.get("config", payload))
    except ValueError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_state(request: Any) -> Any:
    namespace = _read_request_query_value(request, "namespace")
    try:
        result = build_prompt_workbench_surface_state_payload(namespace)
    except ValueError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_state_update(request: Any) -> Any:
    try:
        payload = await _read_request_payload(request)
        result = apply_prompt_workbench_surface_state_update(payload.get("namespace"), payload.get("state"))
    except ValueError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_history(request: Any) -> Any:
    namespace = _read_request_query_value(request, "namespace")
    try:
        result = build_prompt_workbench_history_payload(namespace)
    except ValueError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_history_update(request: Any) -> Any:
    try:
        payload = await _read_request_payload(request)
        result = apply_prompt_workbench_history_update(
            payload.get("namespace"),
            action=payload.get("action", "push"),
            payload=payload,
        )
    except ValueError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_favorites(request: Any) -> Any:
    namespace = _read_request_query_value(request, "namespace")
    try:
        result = build_prompt_workbench_favorites_payload(namespace)
    except ValueError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_favorites_update(request: Any) -> Any:
    try:
        payload = await _read_request_payload(request)
        result = apply_prompt_workbench_favorites_update(
            payload.get("namespace"),
            action=payload.get("action", "push"),
            payload=payload,
        )
    except ValueError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_blacklist(request: Any) -> Any:
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **build_prompt_workbench_blacklist_payload(),
        },
        request=request,
    )


async def prompt_tools_blacklist_update(request: Any) -> Any:
    try:
        payload = await _read_request_payload(request)
        result = apply_prompt_workbench_blacklist_update(payload.get("blacklist", payload))
    except ValueError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_providers(request: Any) -> Any:
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **build_prompt_workbench_provider_catalog_payload(),
        },
        request=request,
    )


async def prompt_tools_export(request: Any) -> Any:
    include_secrets = coerce_bool(_read_request_query_value(request, "include_secrets"), "include_secrets", strict=False)
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **build_prompt_workbench_export_payload(include_secrets=include_secrets),
        },
        request=request,
    )


async def prompt_tools_import(request: Any) -> Any:
    try:
        payload = await _read_request_payload(request)
        result = apply_prompt_workbench_import(payload.get("export", payload))
    except ValueError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_translate(request: Any) -> Any:
    try:
        payload = await _read_request_payload(request)
        result = execute_prompt_workbench_translate(payload)
    except ValueError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )
    except RuntimeError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("provider-error"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=502,
            request=request,
        )
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_assist(request: Any) -> Any:
    try:
        payload = await _read_request_payload(request)
        result = execute_prompt_workbench_ai_assist(payload)
    except ValueError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )
    except RuntimeError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("provider-error"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=502,
            request=request,
        )
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_catalog(request: Any) -> Any:
    language = _read_request_query_value(request, "language")
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **build_prompt_workbench_catalog_snapshot(language=language),
        },
        request=request,
    )


async def prompt_tools_analyze(request: Any) -> Any:
    try:
        payload = await _read_request_payload(request)
        result = execute_prompt_workbench_analysis(payload)
    except ValueError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def prompt_tools_upsample(request: Any) -> Any:
    try:
        payload = await _read_request_payload(request)
        result = await execute_prompt_workbench_upsample(payload)
    except ValueError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )
    except PromptWorkbenchDanbooruHostUnavailableError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("host-unavailable"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=503,
            request=request,
        )
    except PromptWorkbenchDanbooruExecutionError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("host-action-error"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=502,
            request=request,
        )
    return _json_response(
        {
            "service": normalize_metadata_text("rookieui"),
            "status": normalize_metadata_text("ok"),
            **result,
        },
        request=request,
    )


async def pnginfo_parse(request: Any) -> Any:
    try:
        payload = await _read_request_payload(request)
        result = parse_pnginfo_payload(payload)
    except ValueError as exc:
        return _json_response(
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
    return _json_response(response_payload, request=request)


async def xyz_plot_axes(request: Any) -> Any:
    payload = build_xyz_plot_axes_snapshot()
    payload["service"] = normalize_metadata_text("rookieui")
    payload["status"] = normalize_metadata_text("ok")
    return _json_response(payload, request=request)


async def xyz_plot_estimate(request: Any) -> Any:
    try:
        payload = await _read_request_payload(request)
        response_payload = build_xyz_plot_estimate_snapshot(payload)
    except ValueError as exc:
        return _json_response(
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
    return _json_response(response_payload, request=request)


async def xyz_plot_run(request: Any) -> Any:
    try:
        payload = await _read_request_payload(request)
        response_payload = await execute_xyz_plot_run_snapshot(payload, _get_prompt_server_for_submission())
    except ValueError as exc:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text(str(exc)),
            },
            status=400,
            request=request,
        )
    except RuntimeError as exc:
        return _json_response(
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
    return _json_response(response_payload, request=request)


async def xyz_plot_sessions(request: Any) -> Any:
    try:
        response_payload = await build_xyz_plot_session_list_snapshot(
            _get_prompt_server_for_submission(),
            client_id=_read_request_query_value(request, "client_id"),
        )
    except ValueError as exc:
        return _json_response(
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
    return _json_response(response_payload, request=request)


async def xyz_plot_session_detail(request: Any) -> Any:
    session_id = _read_request_match_value(request, "session_id")
    if not session_id:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text("session_id is required."),
            },
            status=400,
            request=request,
        )
    try:
        response_payload = await build_xyz_plot_session_detail_snapshot(
            session_id,
            _get_prompt_server_for_submission(),
            client_id=_read_request_query_value(request, "client_id"),
        )
    except ValueError as exc:
        return _json_response(
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
    return _json_response(response_payload, request=request)


async def xyz_plot_session_cancel(request: Any) -> Any:
    session_id = _read_request_match_value(request, "session_id")
    if not session_id:
        return _json_response(
            {
                "service": normalize_metadata_text("rookieui"),
                "status": normalize_metadata_text("invalid-request"),
                "detail": normalize_metadata_text("session_id is required."),
            },
            status=400,
            request=request,
        )
    try:
        response_payload = await execute_xyz_plot_session_cancel_snapshot(
            session_id,
            _get_prompt_server_for_submission(),
            client_id=_read_request_query_value(request, "client_id"),
        )
    except ValueError as exc:
        return _json_response(
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
    return _json_response(response_payload, request=request)


async def pnginfo_inspect(request: Any) -> Any:
    return await pnginfo_parse(request)


async def _read_request_payload(request: Any) -> dict[str, object]:
    if request is None:
        return {}

    json_loader = getattr(request, "json", None)
    if callable(json_loader):
        payload = await json_loader()
        if isinstance(payload, dict):
            return payload
        raise ValueError("RookieUI generation payload must be an object.")

    payload = getattr(request, "payload", {})
    if isinstance(payload, dict):
        return payload

    raise ValueError("RookieUI generation payload must be an object.")


def _read_request_query_value(request: Any, key: str) -> object | None:
    if request is None:
        return None

    query = getattr(request, "query", None)
    if isinstance(query, dict):
        return query.get(key)

    rel_url = getattr(request, "rel_url", None)
    rel_query = getattr(rel_url, "query", None)
    if isinstance(rel_query, dict):
        return rel_query.get(key)
    if rel_query is not None and hasattr(rel_query, "get"):
        return rel_query.get(key)

    return None


def _count_detect_input_images(payload: dict[str, object]) -> int:
    raw_images = payload.get("controlnet_input_images")
    if isinstance(raw_images, list):
        return len([entry for entry in raw_images if isinstance(entry, str) and entry.strip()])
    single_image = payload.get("image")
    if isinstance(single_image, str) and single_image.strip():
        return 1
    return 0


def _read_request_match_value(request: Any, key: str) -> str:
    if request is None:
        return ""
    match_info = getattr(request, "match_info", None)
    if isinstance(match_info, dict):
        raw_value = match_info.get(key)
        return raw_value if isinstance(raw_value, str) else ""
    if match_info is not None and hasattr(match_info, "get"):
        raw_value = match_info.get(key)
        return raw_value if isinstance(raw_value, str) else ""
    return ""


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
        return _json_response(response_payload, request=request)

    try:
        submission = await submit_prompt_workflow(
            _get_prompt_server_for_submission(),
            response_payload["workflow"],
            client_id=client_id if isinstance(client_id, str) else None,
            origin="rookieui",
            surface=surface,
            profile=str(response_payload.get("profile", "")),
            extra_pnginfo=response_payload.get("generation_metadata", {}).get("extra_pnginfo"),
        )
    except RuntimeError as exc:
        return _json_response(
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
        return _json_response(
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
    return _json_response(response_payload, request=request)


async def txt2img(request: Any) -> Any:
    try:
        payload = await _read_request_payload(request)
        request_payload = dict(payload)
        dry_run = coerce_bool(request_payload.pop("dry_run", False), "dry_run", strict=False)
        client_id = normalize_client_id(request_payload.pop("client_id", None))
        normalized = normalize_txt2img_request(request_payload)
        translation = translate_txt2img_request(normalized)
    except (TypeError, ValueError) as exc:
        # DEBUG HOTSPOT: route-entry payload drift must return JSON invalid-request, not an aiohttp traceback.
        _LOGGER.warning("RookieUI txt2img rejected invalid request: %s", str(exc))
        return _json_response(
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
        payload = await _read_request_payload(request)
        request_payload = dict(payload)
        dry_run = coerce_bool(request_payload.pop("dry_run", False), "dry_run", strict=False)
        client_id = normalize_client_id(request_payload.pop("client_id", None))
        normalized = normalize_img2img_request(request_payload)
        translation = translate_img2img_request(normalized)
    except (TypeError, ValueError) as exc:
        # DEBUG HOTSPOT: route-entry payload drift must return JSON invalid-request, not an aiohttp traceback.
        _LOGGER.warning("RookieUI img2img rejected invalid request: %s", str(exc))
        return _json_response(
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


async def extras_run(request: Any) -> Any:
    try:
        payload = await _read_request_payload(request)
        normalized = normalize_extras_request(payload)
        result = execute_extras_request(normalized)
    except ValueError as exc:
        return _json_response(
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
    return _json_response(response_payload, request=request)


def _register_controlnet_alias_routes(prompt_server: Any) -> None:
    # CRITICAL: keep A1111 compatibility aliases scoped to explicit /controlnet/* paths only; do not broaden global route exposure.
    alias_registrar = SafeRouteRegistrar(
        prompt_server.app.router,
        allowed_prefixes=("/controlnet",),
    )
    alias_registrar.add_get("/controlnet/model_list", controlnet_model_list)
    alias_registrar.add_get("/controlnet/module_list", controlnet_module_list)
    alias_registrar.add_get("/controlnet/control_types", controlnet_control_types)
    alias_registrar.add_post("/controlnet/detect", controlnet_detect)


def _register_rookieui_route_pair(registrar: SafeRouteRegistrar, method: str, suffix: str, handler: Any) -> None:
    for prefix in (INTERNAL_ROUTE_PREFIX, API_INTERNAL_ROUTE_PREFIX):
        path = f"{prefix}{suffix}"
        if method == "GET":
            registrar.add_get(path, handler)
        elif method == "POST":
            registrar.add_post(path, handler)
        else:
            raise ValueError(f"Unsupported RookieUI route method: {method}")


def _register_rookieui_get(registrar: SafeRouteRegistrar, suffix: str, handler: Any) -> None:
    _register_rookieui_route_pair(registrar, "GET", suffix, handler)


def _register_rookieui_post(registrar: SafeRouteRegistrar, suffix: str, handler: Any) -> None:
    _register_rookieui_route_pair(registrar, "POST", suffix, handler)


def register_routes(prompt_server: Any) -> None:
    registrar = SafeRouteRegistrar(prompt_server.app.router, allowed_prefixes=(INTERNAL_ROUTE_PREFIX, API_INTERNAL_ROUTE_PREFIX))
    # CRITICAL: ComfyUI app.api.fetchApi('/rookieui/...') resolves to '/api/rookieui/...'.
    # Direct custom-node app.router registration does not get ComfyUI's automatic /api route clone.
    _register_rookieui_get(registrar, "/health", health)
    _register_rookieui_get(registrar, "/bootstrap", bootstrap)
    _register_rookieui_get(registrar, "/capabilities", capabilities)
    _register_rookieui_get(registrar, "/parity", parity)
    _register_rookieui_get(registrar, "/compatibility", compatibility)
    _register_rookieui_get(registrar, "/models", models)
    _register_rookieui_get(registrar, "/presets", presets)
    _register_rookieui_get(registrar, "/controlnet/model_list", controlnet_model_list)
    _register_rookieui_get(registrar, "/controlnet/module_list", controlnet_module_list)
    _register_rookieui_get(registrar, "/controlnet/control_types", controlnet_control_types)
    _register_rookieui_get(registrar, "/adetailer/catalog", adetailer_catalog)
    _register_rookieui_get(registrar, "/queue", queue)
    _register_rookieui_get(registrar, "/queue/{prompt_id}", queue_prompt)
    # IMPORTANT: keep prompt-workbench tooling under one coherent /prompt-tools/* family; scattering these routes
    # would reopen the phase-60 ownership contract before the workbench ships.
    _register_rookieui_get(registrar, "/prompt-tools/config", prompt_tools_config)
    _register_rookieui_post(registrar, "/prompt-tools/config", prompt_tools_config_update)
    _register_rookieui_get(registrar, "/prompt-tools/state", prompt_tools_state)
    _register_rookieui_post(registrar, "/prompt-tools/state", prompt_tools_state_update)
    _register_rookieui_get(registrar, "/prompt-tools/history", prompt_tools_history)
    _register_rookieui_post(registrar, "/prompt-tools/history", prompt_tools_history_update)
    _register_rookieui_get(registrar, "/prompt-tools/favorites", prompt_tools_favorites)
    _register_rookieui_post(registrar, "/prompt-tools/favorites", prompt_tools_favorites_update)
    _register_rookieui_get(registrar, "/prompt-tools/blacklist", prompt_tools_blacklist)
    _register_rookieui_post(registrar, "/prompt-tools/blacklist", prompt_tools_blacklist_update)
    _register_rookieui_get(registrar, "/prompt-tools/providers", prompt_tools_providers)
    _register_rookieui_get(registrar, "/prompt-tools/export", prompt_tools_export)
    _register_rookieui_post(registrar, "/prompt-tools/import", prompt_tools_import)
    _register_rookieui_post(registrar, "/prompt-tools/translate", prompt_tools_translate)
    _register_rookieui_post(registrar, "/prompt-tools/assist", prompt_tools_assist)
    _register_rookieui_get(registrar, "/prompt-tools/catalog", prompt_tools_catalog)
    _register_rookieui_post(registrar, "/prompt-tools/analyze", prompt_tools_analyze)
    _register_rookieui_post(registrar, "/prompt-tools/upsample", prompt_tools_upsample)
    _register_rookieui_get(registrar, "/xyz-plot/axes", xyz_plot_axes)
    _register_rookieui_post(registrar, "/xyz-plot/estimate", xyz_plot_estimate)
    _register_rookieui_post(registrar, "/xyz-plot/run", xyz_plot_run)
    _register_rookieui_get(registrar, "/xyz-plot/sessions", xyz_plot_sessions)
    _register_rookieui_get(registrar, "/xyz-plot/sessions/{session_id}", xyz_plot_session_detail)
    _register_rookieui_post(registrar, "/xyz-plot/sessions/{session_id}/cancel", xyz_plot_session_cancel)
    _register_rookieui_post(registrar, "/pnginfo/parse", pnginfo_parse)
    _register_rookieui_post(registrar, "/pnginfo/inspect", pnginfo_inspect)
    _register_rookieui_post(registrar, "/controlnet/detect", controlnet_detect)
    _register_rookieui_post(registrar, "/generate/txt2img", txt2img)
    _register_rookieui_post(registrar, "/generate/img2img", img2img)
    _register_rookieui_post(registrar, "/extras/run", extras_run)
    _register_controlnet_alias_routes(prompt_server)
