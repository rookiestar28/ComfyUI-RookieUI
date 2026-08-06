from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

from rookieui.api import route_runtime
from rookieui.api.domains.controlnet import (
    adetailer_catalog,
    controlnet_control_types,
    controlnet_detect,
    controlnet_model_list,
    controlnet_module_list,
)
from rookieui.api.domains.generation import img2img, txt2img
from rookieui.api.domains.health_bootstrap import (
    bootstrap,
    configure_internal_route_paths,
    health,
)
from rookieui.api.domains.inventory_capability import capabilities, compatibility, models, parity, presets
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
from rookieui.api.domains.queue import queue, queue_prompt
from rookieui.api.domains.xyz_plot import (
    xyz_plot_axes,
    xyz_plot_estimate,
    xyz_plot_run,
    xyz_plot_session_cancel,
    xyz_plot_session_detail,
    xyz_plot_sessions,
)
from rookieui.security.route_guard import SafeRouteRegistrar


Handler = Callable[[Any], Any]
Method = Literal["GET", "POST"]


@dataclass(frozen=True, slots=True)
class RouteSpec:
    method: Method
    suffix: str
    handler: Handler
    domain: str
    diagnostic: bool = False
    optional_alias: bool = False


AUTHORITATIVE_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec("GET", "/health", health, "health_bootstrap", True),
    RouteSpec("GET", "/bootstrap", bootstrap, "health_bootstrap", True),
    RouteSpec("GET", "/capabilities", capabilities, "inventory_capability", True),
    RouteSpec("GET", "/parity", parity, "inventory_capability", True),
    RouteSpec("GET", "/compatibility", compatibility, "inventory_capability", True),
    RouteSpec("GET", "/models", models, "inventory_capability"),
    RouteSpec("GET", "/presets", presets, "inventory_capability"),
    RouteSpec("GET", "/controlnet/model_list", controlnet_model_list, "controlnet"),
    RouteSpec("GET", "/controlnet/module_list", controlnet_module_list, "controlnet"),
    RouteSpec("GET", "/controlnet/control_types", controlnet_control_types, "controlnet"),
    RouteSpec("GET", "/adetailer/catalog", adetailer_catalog, "controlnet"),
    RouteSpec("GET", "/queue", queue, "queue"),
    RouteSpec("GET", "/queue/{prompt_id}", queue_prompt, "queue"),
    RouteSpec("GET", "/prompt-tools/config", prompt_tools_config, "prompt_workbench"),
    RouteSpec("POST", "/prompt-tools/config", prompt_tools_config_update, "prompt_workbench"),
    RouteSpec("GET", "/prompt-tools/state", prompt_tools_state, "prompt_workbench"),
    RouteSpec("POST", "/prompt-tools/state", prompt_tools_state_update, "prompt_workbench"),
    RouteSpec("GET", "/prompt-tools/history", prompt_tools_history, "prompt_workbench"),
    RouteSpec("POST", "/prompt-tools/history", prompt_tools_history_update, "prompt_workbench"),
    RouteSpec("GET", "/prompt-tools/favorites", prompt_tools_favorites, "prompt_workbench"),
    RouteSpec("POST", "/prompt-tools/favorites", prompt_tools_favorites_update, "prompt_workbench"),
    RouteSpec("GET", "/prompt-tools/blacklist", prompt_tools_blacklist, "prompt_workbench"),
    RouteSpec("POST", "/prompt-tools/blacklist", prompt_tools_blacklist_update, "prompt_workbench"),
    RouteSpec("GET", "/prompt-tools/providers", prompt_tools_providers, "prompt_workbench"),
    RouteSpec("GET", "/prompt-tools/export", prompt_tools_export, "prompt_workbench"),
    RouteSpec("POST", "/prompt-tools/import", prompt_tools_import, "prompt_workbench"),
    RouteSpec("POST", "/prompt-tools/translate", prompt_tools_translate, "prompt_workbench"),
    RouteSpec("POST", "/prompt-tools/assist", prompt_tools_assist, "prompt_workbench"),
    RouteSpec("GET", "/prompt-tools/catalog", prompt_tools_catalog, "prompt_workbench"),
    RouteSpec("POST", "/prompt-tools/analyze", prompt_tools_analyze, "prompt_workbench"),
    RouteSpec("POST", "/prompt-tools/upsample", prompt_tools_upsample, "prompt_workbench"),
    RouteSpec("GET", "/xyz-plot/axes", xyz_plot_axes, "xyz_plot"),
    RouteSpec("POST", "/xyz-plot/estimate", xyz_plot_estimate, "xyz_plot"),
    RouteSpec("POST", "/xyz-plot/run", xyz_plot_run, "xyz_plot"),
    RouteSpec("GET", "/xyz-plot/sessions", xyz_plot_sessions, "xyz_plot"),
    RouteSpec("GET", "/xyz-plot/sessions/{session_id}", xyz_plot_session_detail, "xyz_plot"),
    RouteSpec("POST", "/xyz-plot/sessions/{session_id}/cancel", xyz_plot_session_cancel, "xyz_plot"),
    RouteSpec("POST", "/pnginfo/parse", pnginfo_parse, "pnginfo_extras"),
    RouteSpec("POST", "/pnginfo/inspect", pnginfo_inspect, "pnginfo_extras"),
    RouteSpec("POST", "/controlnet/detect", controlnet_detect, "controlnet"),
    RouteSpec("POST", "/generate/txt2img", txt2img, "generation"),
    RouteSpec("POST", "/generate/img2img", img2img, "generation"),
    RouteSpec("POST", "/extras/run", extras_run, "pnginfo_extras"),
)

OPTIONAL_ALIAS_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec("GET", "/controlnet/model_list", controlnet_model_list, "controlnet", optional_alias=True),
    RouteSpec("GET", "/controlnet/module_list", controlnet_module_list, "controlnet", optional_alias=True),
    RouteSpec("GET", "/controlnet/control_types", controlnet_control_types, "controlnet", optional_alias=True),
    RouteSpec("POST", "/controlnet/detect", controlnet_detect, "controlnet", optional_alias=True),
)

INTERNAL_ROUTE_PATHS = [f"{route_runtime.INTERNAL_ROUTE_PREFIX}{spec.suffix}" for spec in AUTHORITATIVE_ROUTE_SPECS]
configure_internal_route_paths(INTERNAL_ROUTE_PATHS)


def build_route_matrix() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for order, spec in enumerate(AUTHORITATIVE_ROUTE_SPECS, start=1):
        rows.append(
            {
                "order": order,
                "logical_suffix": spec.suffix,
                "method": spec.method,
                "physical_prefixes": [route_runtime.INTERNAL_ROUTE_PREFIX, route_runtime.API_INTERNAL_ROUTE_PREFIX],
                "handler_identity": spec.handler.__name__,
                "handler_module": spec.handler.__module__,
                "domain": spec.domain,
                "diagnostic": spec.diagnostic,
                "optional_alias": "none",
            }
        )
    for order, spec in enumerate(OPTIONAL_ALIAS_ROUTE_SPECS, start=1):
        rows.append(
            {
                "order": order,
                "logical_suffix": spec.suffix,
                "method": spec.method,
                "physical_prefixes": [spec.suffix],
                "handler_identity": spec.handler.__name__,
                "handler_module": spec.handler.__module__,
                "domain": spec.domain,
                "diagnostic": spec.diagnostic,
                "optional_alias": "collision-isolated; disabled in multi-user mode",
            }
        )
    return rows


def _register_authoritative_spec(registrar: SafeRouteRegistrar, spec: RouteSpec) -> None:
    handler = route_runtime.deployment_guard(spec.handler, diagnostic=spec.diagnostic)
    for prefix in (route_runtime.INTERNAL_ROUTE_PREFIX, route_runtime.API_INTERNAL_ROUTE_PREFIX):
        path = f"{prefix}{spec.suffix}"
        if spec.method == "GET":
            registrar.add_get(path, handler)
        else:
            registrar.add_post(path, handler)


def _register_optional_aliases(prompt_server: Any) -> None:
    registrar = SafeRouteRegistrar(prompt_server.app.router, allowed_prefixes=("/controlnet",))
    for spec in OPTIONAL_ALIAS_ROUTE_SPECS:
        status_key = f"{spec.method} {spec.suffix}"
        if route_runtime._multi_user_mode_active:
            route_runtime.record_optional_alias_status(
                status_key,
                status="disabled",
                reason="unsupported-multi-user-mode",
            )
            continue
        try:
            if spec.method == "GET":
                registrar.add_get(spec.suffix, spec.handler)
            else:
                registrar.add_post(spec.suffix, spec.handler)
        except Exception:
            route_runtime.record_optional_alias_status(
                status_key,
                status="collision",
                reason="foreign-or-preexisting-route",
            )
            route_runtime.LOGGER.warning("Optional RookieUI compatibility alias unavailable: %s", status_key)
        else:
            route_runtime.record_optional_alias_status(
                status_key,
                status="registered",
                reason="rookieui-owned",
            )


def register_routes(prompt_server: Any) -> None:
    route_runtime.set_multi_user_mode()
    registrar = SafeRouteRegistrar(
        prompt_server.app.router,
        allowed_prefixes=(route_runtime.INTERNAL_ROUTE_PREFIX, route_runtime.API_INTERNAL_ROUTE_PREFIX),
    )
    for spec in AUTHORITATIVE_ROUTE_SPECS:
        _register_authoritative_spec(registrar, spec)
    _register_optional_aliases(prompt_server)
