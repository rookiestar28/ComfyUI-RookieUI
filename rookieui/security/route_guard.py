from __future__ import annotations

from typing import Any

INTERNAL_ROUTE_PREFIX = "/rookieui"
_registered_route_keys: set[tuple[str, str]] = set()


def validate_internal_route_path(path: str) -> str:
    if not isinstance(path, str):
        raise TypeError("Route paths must be strings.")

    # CRITICAL: keep RookieUI routes under /rookieui/* so future feature
    # handlers do not accidentally escape into host-global route space.
    if not path.startswith(f"{INTERNAL_ROUTE_PREFIX}/"):
        raise ValueError("RookieUI routes must stay inside /rookieui/*.")

    if any(marker in path for marker in ("..", "\\", "?", "#")):
        raise ValueError("RookieUI routes cannot contain traversal or fragments.")

    if "//" in path:
        raise ValueError("RookieUI routes cannot contain empty path segments.")

    return path


class SafeRouteRegistrar:
    def __init__(self, router: Any) -> None:
        self._router = router

    def add_get(self, path: str, handler: Any) -> None:
        self._register("GET", "add_get", path, handler)

    def add_post(self, path: str, handler: Any) -> None:
        self._register("POST", "add_post", path, handler)

    def _register(self, method: str, registrar_name: str, path: str, handler: Any) -> None:
        normalized_path = validate_internal_route_path(path)
        route_key = (method, normalized_path)
        if route_key in _registered_route_keys:
            raise ValueError(f"RookieUI route already registered: {method} {normalized_path}")

        registrar = getattr(self._router, registrar_name, None)
        if registrar is None:
            raise AttributeError(f"Router does not support {registrar_name}.")

        registrar(normalized_path, handler)
        _registered_route_keys.add(route_key)


def reset_registered_routes_for_tests() -> None:
    _registered_route_keys.clear()
