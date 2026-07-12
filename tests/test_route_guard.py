from __future__ import annotations

import unittest

from rookieui.security.route_guard import (
    SafeRouteRegistrar,
    reset_registered_routes_for_tests,
    validate_internal_route_path,
)
from tests.helpers.fake_prompt_server import FakeRouter


class RouteGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_registered_routes_for_tests()

    def tearDown(self) -> None:
        reset_registered_routes_for_tests()

    def test_accepts_internal_route_path(self) -> None:
        self.assertEqual(validate_internal_route_path("/rookieui/health"), "/rookieui/health")
        self.assertEqual(validate_internal_route_path("/api/rookieui/health"), "/api/rookieui/health")

    def test_rejects_external_route_path(self) -> None:
        with self.assertRaises(ValueError):
            validate_internal_route_path("/api/public")

    def test_rejects_duplicate_route_registration_before_router_mutation(self) -> None:
        router = FakeRouter()
        registrar = SafeRouteRegistrar(router)

        registrar.add_get("/rookieui/health", object())
        registrar.add_get("/rookieui/health", object())

        self.assertEqual(len(router.routes), 1)

    def test_registration_state_is_scoped_per_router(self) -> None:
        first = FakeRouter()
        second = FakeRouter()
        SafeRouteRegistrar(first).add_get("/rookieui/health", object())
        SafeRouteRegistrar(second).add_get("/rookieui/health", object())
        self.assertEqual(len(first.routes), 1)
        self.assertEqual(len(second.routes), 1)

    def test_registers_internal_post_route(self) -> None:
        router = FakeRouter()
        registrar = SafeRouteRegistrar(router)

        registrar.add_post("/rookieui/generate/txt2img", object())

        self.assertEqual(router.routes[0][0], "POST")

    def test_rejects_malformed_internal_route_path(self) -> None:
        with self.assertRaises(ValueError):
            validate_internal_route_path("/rookieui/../health")

    def test_allows_explicit_compatibility_prefix_when_requested(self) -> None:
        router = FakeRouter()
        registrar = SafeRouteRegistrar(router, allowed_prefixes=("/controlnet",))

        registrar.add_get("/controlnet/model_list", object())

        self.assertEqual(len(router.routes), 1)
        self.assertEqual(router.routes[0][1], "/controlnet/model_list")
