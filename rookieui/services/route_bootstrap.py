from __future__ import annotations

import logging
import sys
import threading
import time
from typing import Any

_MAX_ATTEMPTS = 10
_INITIAL_DELAY_SECONDS = 0.25

_routes_registered = False
_retry_started = False
_registration_lock = threading.Lock()


def _get_prompt_server_instance() -> Any | None:
    server_module = sys.modules.get("server")
    if server_module is None:
        return None

    prompt_server = getattr(server_module, "PromptServer", None)
    if prompt_server is None:
        return None

    return getattr(prompt_server, "instance", None)


def _register_routes(prompt_server: Any) -> None:
    from rookieui.api.routes import register_routes

    register_routes(prompt_server)


def _retry_registration() -> None:
    global _routes_registered
    logger = logging.getLogger("ComfyUI-RookieUI")
    delay = _INITIAL_DELAY_SECONDS

    for attempt in range(_MAX_ATTEMPTS):
        if _routes_registered:
            return

        prompt_server = _get_prompt_server_instance()
        if prompt_server is not None:
            try:
                _register_routes(prompt_server)
                _routes_registered = True
                logger.info("Registered RookieUI routes on retry attempt %s.", attempt + 1)
                return
            except Exception:
                logger.exception("RookieUI route retry failed on attempt %s.", attempt + 1)

        time.sleep(delay)
        delay = min(delay * 2, 5.0)

    logger.error("Failed to register RookieUI routes after %s attempts.", _MAX_ATTEMPTS)


def _start_retry_thread() -> None:
    global _retry_started
    if _retry_started:
        return

    _retry_started = True
    thread = threading.Thread(
        target=_retry_registration,
        name="rookieui-route-retry",
        daemon=True,
    )
    thread.start()


def register_routes_once() -> None:
    global _routes_registered
    with _registration_lock:
        if _routes_registered:
            return

        server_module = sys.modules.get("server")
        if server_module is None:
            return

        prompt_server = _get_prompt_server_instance()
        if prompt_server is None:
            _start_retry_thread()
            return

        _register_routes(prompt_server)
        _routes_registered = True


def _reset_registration_state_for_tests() -> None:
    global _routes_registered, _retry_started
    _routes_registered = False
    _retry_started = False
    logger = logging.getLogger("ComfyUI-RookieUI")
    try:
        from rookieui.security.route_guard import reset_registered_routes_for_tests
    except Exception:
        logger.debug("RookieUI route_guard reset helper unavailable in test reset fallback.", exc_info=True)
        return
    reset_registered_routes_for_tests()
