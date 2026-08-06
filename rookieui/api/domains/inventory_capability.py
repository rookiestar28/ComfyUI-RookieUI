from __future__ import annotations

from typing import Any

from rookieui.api import route_runtime
from rookieui.api.domains.health_bootstrap import (
    build_capabilities_snapshot,
    build_compatibility_snapshot,
    build_parity_snapshot,
)
from rookieui.services.model_inventory import discover_model_inventory
from rookieui.services.presets import build_preset_payload


def build_models_snapshot() -> dict[str, object]:
    return discover_model_inventory().to_payload()


def build_presets_snapshot() -> dict[str, object]:
    return build_preset_payload()


async def models(request: Any) -> Any:
    return route_runtime.json_response(build_models_snapshot(), request=request)


async def presets(request: Any) -> Any:
    return route_runtime.json_response(build_presets_snapshot(), request=request)


async def capabilities(request: Any) -> Any:
    return route_runtime.json_response(build_capabilities_snapshot(), request=request)


async def parity(request: Any) -> Any:
    return route_runtime.json_response(build_parity_snapshot(), request=request)


async def compatibility(request: Any) -> Any:
    return route_runtime.json_response(build_compatibility_snapshot(), request=request)
