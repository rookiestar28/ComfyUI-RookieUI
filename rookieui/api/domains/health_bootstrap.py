from __future__ import annotations

from typing import Any

from rookieui.api import route_runtime
from rookieui.security.asset_guard import normalize_metadata_text
from rookieui.services.capabilities import build_capabilities_payload
from rookieui.services.compatibility import build_compatibility_payload
from rookieui.services.parity_matrix import build_parity_payload
from rookieui.services.version import build_runtime_metadata_payload


INTERNAL_ROUTE_PATHS: list[str] = []


def configure_internal_route_paths(paths: list[str]) -> None:
    INTERNAL_ROUTE_PATHS.clear()
    INTERNAL_ROUTE_PATHS.extend(paths)


def build_health_payload() -> dict[str, Any]:
    return {
        "service": normalize_metadata_text("rookieui"),
        "status": normalize_metadata_text(
            "unsupported-host-mode" if route_runtime._multi_user_mode_active else "ok"
        ),
        "deployment": route_runtime.deployment_payload(),
        "optional_aliases": route_runtime.get_optional_alias_route_status(),
    }


def build_bootstrap_payload() -> dict[str, Any]:
    runtime = build_runtime_metadata_payload()
    return {
        "service": normalize_metadata_text("rookieui"),
        "status": normalize_metadata_text("bootstrap-ready"),
        "visibility": normalize_metadata_text("internal"),
        "runtime": {
            "shell_version": normalize_metadata_text(runtime["shell_version"]),
            "build_fingerprint": normalize_metadata_text(runtime["build_fingerprint"]),
        },
        "routes": list(INTERNAL_ROUTE_PATHS),
        "deployment": route_runtime.deployment_payload(),
        "optional_aliases": route_runtime.get_optional_alias_route_status(),
    }


def build_capabilities_snapshot() -> dict[str, object]:
    payload = build_capabilities_payload(routes=list(INTERNAL_ROUTE_PATHS))
    payload["deployment"] = route_runtime.deployment_payload()
    payload["optional_aliases"] = route_runtime.get_optional_alias_route_status()
    return payload


def build_parity_snapshot() -> dict[str, object]:
    return build_parity_payload()


def build_compatibility_snapshot() -> dict[str, object]:
    return build_compatibility_payload()


async def health(request: Any) -> Any:
    return route_runtime.json_response(build_health_payload(), request=request)


async def bootstrap(request: Any) -> Any:
    return route_runtime.json_response(build_bootstrap_payload(), request=request)
