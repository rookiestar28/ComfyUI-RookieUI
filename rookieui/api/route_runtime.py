from __future__ import annotations

import logging
import sys
from typing import Any


LOGGER = logging.getLogger("ComfyUI-RookieUI")
INTERNAL_ROUTE_PREFIX = "/rookieui"
API_INTERNAL_ROUTE_PREFIX = f"/api{INTERNAL_ROUTE_PREFIX}"
SAFE_DIAGNOSTIC_SUFFIXES = frozenset(
    {"/health", "/bootstrap", "/capabilities", "/parity", "/compatibility"}
)
_multi_user_mode_active = False
_optional_alias_route_status: dict[str, dict[str, str]] = {}


def detect_multi_user_mode() -> bool:
    cli_args_module = sys.modules.get("comfy.cli_args")
    cli_args = getattr(cli_args_module, "args", None)
    return bool(getattr(cli_args, "multi_user", False))


def deployment_payload() -> dict[str, object]:
    if _multi_user_mode_active:
        return {
            "supported": False,
            "mode": "multi-user",
            "detail": "RookieUI supports local single-user ComfyUI hosts; stateful capabilities are disabled.",
        }
    return {
        "supported": True,
        "mode": "single-user",
        "detail": "RookieUI local single-user deployment boundary is active.",
    }


def get_optional_alias_route_status() -> dict[str, dict[str, str]]:
    return {key: dict(value) for key, value in _optional_alias_route_status.items()}


async def unsupported_multi_user_handler(request: Any) -> Any:
    return json_response(
        {
            "service": "rookieui",
            "status": "unsupported-host-mode",
            "detail": "RookieUI stateful routes require a local single-user ComfyUI host.",
            "deployment": deployment_payload(),
        },
        status=409,
        request=request,
    )


def deployment_guard(handler: Any, *, diagnostic: bool) -> Any:
    if not _multi_user_mode_active or diagnostic:
        return handler
    return unsupported_multi_user_handler


def set_multi_user_mode() -> bool:
    global _multi_user_mode_active
    _multi_user_mode_active = detect_multi_user_mode()
    return _multi_user_mode_active


def reset_route_runtime_state_for_tests() -> None:
    global _multi_user_mode_active
    _multi_user_mode_active = False
    _optional_alias_route_status.clear()


def record_optional_alias_status(key: str, *, status: str, reason: str) -> None:
    _optional_alias_route_status[key] = {"status": status, "reason": reason}


def json_response(
    payload: dict[str, Any],
    *,
    status: int = 200,
    request: Any | None = None,
) -> Any:
    try:
        from aiohttp import web
    except ImportError:
        return {"status": status, "payload": payload}
    if request is None or request.__class__.__module__.split(".", 1)[0] != "aiohttp":
        return {"status": status, "payload": payload}
    return web.json_response(payload, status=status)


async def read_request_payload(request: Any) -> dict[str, object]:
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


def read_request_query_value(request: Any, key: str) -> object | None:
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


def read_request_match_value(request: Any, key: str) -> str:
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


def count_detect_input_images(payload: dict[str, object]) -> int:
    raw_images = payload.get("controlnet_input_images")
    if isinstance(raw_images, list):
        return len([entry for entry in raw_images if isinstance(entry, str) and entry.strip()])
    single_image = payload.get("image")
    if isinstance(single_image, str) and single_image.strip():
        return 1
    return 0


def get_prompt_server_for_submission() -> Any | None:
    try:
        from rookieui.services.route_bootstrap import _get_prompt_server_instance
    except Exception:
        LOGGER.debug("RookieUI route helper import fallback triggered.", exc_info=True)
        return None
    return _get_prompt_server_instance()
