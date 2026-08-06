"""Compatibility facade and guarded route composition entry point.

Route implementations live in :mod:`rookieui.api.domains`; this module keeps
the historical import surface stable for ComfyUI startup and existing callers.
Only :func:`register_routes` delegates to the declarative route specification.
"""

from __future__ import annotations

from typing import Any

from rookieui.api import route_runtime, route_spec
from rookieui.api.domains.controlnet import (
    adetailer_catalog,
    build_adetailer_snapshot,
    controlnet_control_types,
    controlnet_detect,
    controlnet_model_list,
    controlnet_module_list,
)
from rookieui.api.domains.generation import img2img, txt2img
from rookieui.api.domains.health_bootstrap import (
    build_bootstrap_payload,
    build_capabilities_snapshot,
    build_compatibility_snapshot,
    build_health_payload,
    build_parity_snapshot,
    health,
    bootstrap,
)
from rookieui.api.domains.inventory_capability import (
    capabilities,
    compatibility,
    build_models_snapshot,
    build_presets_snapshot,
    models,
    parity,
    presets,
)
from rookieui.api.domains.pnginfo_extras import extras_run, pnginfo_inspect, pnginfo_parse
from rookieui.api.domains.prompt_workbench import (
    prompt_tools_analyze,
    prompt_tools_assist,
    prompt_tools_blacklist,
    prompt_tools_blacklist_update,
    prompt_tools_catalog,
    prompt_tools_config,
    prompt_tools_config_update,
    prompt_tools_export,
    prompt_tools_favorites,
    prompt_tools_favorites_update,
    prompt_tools_history,
    prompt_tools_history_update,
    prompt_tools_import,
    prompt_tools_providers,
    prompt_tools_state,
    prompt_tools_state_update,
    prompt_tools_translate,
    prompt_tools_upsample,
)
from rookieui.api.domains.queue import (
    build_queue_job_snapshot_payload,
    build_queue_snapshot_payload,
    queue,
    queue_prompt,
)
from rookieui.api.domains.xyz_plot import (
    xyz_plot_axes,
    xyz_plot_estimate,
    xyz_plot_run,
    xyz_plot_session_cancel,
    xyz_plot_session_detail,
    xyz_plot_sessions,
)
from rookieui.contracts.extras import build_extras_contract_meta
from rookieui.contracts.pnginfo import build_pnginfo_contract_meta
from rookieui.contracts.queue import build_queue_contract_meta
from rookieui.security.route_guard import API_INTERNAL_ROUTE_PREFIX, INTERNAL_ROUTE_PREFIX
from rookieui.services.adetailer import build_adetailer_catalog_payload
from rookieui.services.async_runtime import run_bounded_blocking
from rookieui.services.capabilities import build_capabilities_payload
from rookieui.services.compatibility import build_compatibility_payload
from rookieui.services.controlnet import (
    build_controlnet_control_types_payload,
    build_controlnet_detect_payload,
    build_controlnet_model_list_payload,
    build_controlnet_module_list_payload,
)
from rookieui.services.extras import execute_extras_request, normalize_extras_request
from rookieui.services.model_inventory import discover_model_inventory
from rookieui.services.parity_matrix import build_parity_payload
from rookieui.services.presets import build_preset_payload
from rookieui.services.prompt_workbench import (
    build_prompt_workbench_blacklist_payload,
    build_prompt_workbench_catalog_snapshot,
    build_prompt_workbench_config_payload,
    build_prompt_workbench_favorites_payload,
    build_prompt_workbench_history_payload,
    build_prompt_workbench_export_payload,
    build_prompt_workbench_provider_catalog_payload,
    execute_prompt_workbench_ai_assist,
    execute_prompt_workbench_analysis,
    execute_prompt_workbench_translate,
    execute_prompt_workbench_upsample,
)
from rookieui.services.prompt_submission import submit_prompt_workflow
from rookieui.services.xyz_plot import (
    build_xyz_plot_axes_snapshot,
    build_xyz_plot_estimate_snapshot,
    build_xyz_plot_session_detail_snapshot,
    build_xyz_plot_session_list_snapshot,
    execute_xyz_plot_run_snapshot,
    execute_xyz_plot_session_cancel_snapshot,
)


INTERNAL_ROUTE_PATHS = route_spec.INTERNAL_ROUTE_PATHS
_SAFE_DIAGNOSTIC_SUFFIXES = route_runtime.SAFE_DIAGNOSTIC_SUFFIXES
_LOGGER = route_runtime.LOGGER

# Private compatibility seams retained for host/test integrations that used the
# former monolith directly. They delegate to the guarded runtime module and do
# not register routes themselves.
_detect_multi_user_mode = route_runtime.detect_multi_user_mode
_deployment_payload = route_runtime.deployment_payload
_unsupported_multi_user_handler = route_runtime.unsupported_multi_user_handler
_deployment_guard = route_runtime.deployment_guard


def register_routes(prompt_server: Any) -> None:
    route_spec.register_routes(prompt_server)


def get_optional_alias_route_status() -> dict[str, dict[str, str]]:
    return route_runtime.get_optional_alias_route_status()


def _reset_route_runtime_state_for_tests() -> None:
    route_runtime.reset_route_runtime_state_for_tests()


def _get_prompt_server_for_submission() -> Any | None:
    return route_runtime.get_prompt_server_for_submission()


def _json_response(payload: dict[str, Any], *, status: int = 200, request: Any | None = None) -> Any:
    return route_runtime.json_response(payload, status=status, request=request)


async def _read_request_payload(request: Any) -> dict[str, object]:
    return await route_runtime.read_request_payload(request)


def _read_request_query_value(request: Any, key: str) -> object | None:
    return route_runtime.read_request_query_value(request, key)


def _read_request_match_value(request: Any, key: str) -> str:
    return route_runtime.read_request_match_value(request, key)


def _count_detect_input_images(payload: dict[str, object]) -> int:
    return route_runtime.count_detect_input_images(payload)


def _register_controlnet_alias_routes(prompt_server: Any) -> None:
    route_spec._register_optional_aliases(prompt_server)


def _register_rookieui_route_pair(
    registrar: Any,
    method: str,
    suffix: str,
    handler: Any,
) -> None:
    spec = route_spec.RouteSpec(
        method=method,  # type: ignore[arg-type]
        suffix=suffix,
        handler=handler,
        domain="compatibility",
        diagnostic=suffix in _SAFE_DIAGNOSTIC_SUFFIXES,
    )
    route_spec._register_authoritative_spec(registrar, spec)


def _register_rookieui_get(registrar: Any, suffix: str, handler: Any) -> None:
    _register_rookieui_route_pair(registrar, "GET", suffix, handler)


def _register_rookieui_post(registrar: Any, suffix: str, handler: Any) -> None:
    _register_rookieui_route_pair(registrar, "POST", suffix, handler)


def build_route_matrix() -> list[dict[str, object]]:
    return route_spec.build_route_matrix()


def __getattr__(name: str) -> Any:
    if name == "_multi_user_mode_active":
        return route_runtime._multi_user_mode_active
    if name == "_optional_alias_route_status":
        return route_runtime._optional_alias_route_status
    raise AttributeError(name)
