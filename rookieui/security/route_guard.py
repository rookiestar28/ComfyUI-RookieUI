from __future__ import annotations

from typing import Any

INTERNAL_ROUTE_PREFIX = "/rookieui"
API_INTERNAL_ROUTE_PREFIX = f"/api{INTERNAL_ROUTE_PREFIX}"
_registered_routes_by_router: dict[int, tuple[Any, set[tuple[str, str]]]] = {}


def _registered_route_keys(router: Any) -> set[tuple[str, str]]:
    router_id = id(router)
    entry = _registered_routes_by_router.get(router_id)
    if entry is None or entry[0] is not router:
        route_keys: set[tuple[str, str]] = set()
        # IMPORTANT: retain the router identity with its keys so Python object-id
        # reuse cannot suppress registration on a later host router.
        _registered_routes_by_router[router_id] = (router, route_keys)
        return route_keys
    return entry[1]


def validate_route_path(path: str, *, allowed_prefixes: tuple[str, ...]) -> str:
    if not isinstance(path, str):
        raise TypeError("Route paths must be strings.")

    if not allowed_prefixes:
        raise ValueError("allowed_prefixes must not be empty.")

    # CRITICAL: keep RookieUI route registration constrained to explicit prefixes; broad route registration risks leaking handlers into host-global paths.
    if not any(path.startswith(f"{prefix}/") for prefix in allowed_prefixes):
        joined = ", ".join(allowed_prefixes)
        raise ValueError(f"RookieUI routes must stay inside one of: {joined}.")

    if any(marker in path for marker in ("..", "\\", "?", "#")):
        raise ValueError("RookieUI routes cannot contain traversal or fragments.")

    if "//" in path:
        raise ValueError("RookieUI routes cannot contain empty path segments.")

    return path


def validate_internal_route_path(path: str) -> str:
    return validate_route_path(path, allowed_prefixes=(INTERNAL_ROUTE_PREFIX, API_INTERNAL_ROUTE_PREFIX))


class SafeRouteRegistrar:
    def __init__(self, router: Any, *, allowed_prefixes: tuple[str, ...] | None = None) -> None:
        self._router = router
        self._allowed_prefixes = allowed_prefixes or (INTERNAL_ROUTE_PREFIX,)

    def add_get(self, path: str, handler: Any) -> None:
        self._register("GET", "add_get", path, handler)

    def add_post(self, path: str, handler: Any) -> None:
        self._register("POST", "add_post", path, handler)

    def _register(self, method: str, registrar_name: str, path: str, handler: Any) -> None:
        normalized_path = validate_route_path(path, allowed_prefixes=self._allowed_prefixes)
        route_key = (method, normalized_path)
        registered_route_keys = _registered_route_keys(self._router)
        if route_key in registered_route_keys:
            return

        registrar = getattr(self._router, registrar_name, None)
        if registrar is None:
            raise AttributeError(f"Router does not support {registrar_name}.")

        registrar(normalized_path, handler)
        registered_route_keys.add(route_key)


def reset_registered_routes_for_tests() -> None:
    _registered_routes_by_router.clear()
