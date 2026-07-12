from __future__ import annotations

import asyncio
import sys
import types
import unittest

from rookieui.api import routes
from rookieui.security.route_guard import reset_registered_routes_for_tests
from tests.helpers.fake_prompt_server import FakeApp, FakePromptServerInstance, FakeRouter


class _StrictRouter(FakeRouter):
    def _add(self, method: str, path: str, handler: object) -> None:
        if any(existing_method == method and existing_path == path for existing_method, existing_path, _ in self.routes):
            raise RuntimeError(f"route collision: {method} {path}")
        self.routes.append((method, path, handler))

    def add_get(self, path: str, handler: object) -> None:
        self._add("GET", path, handler)

    def add_post(self, path: str, handler: object) -> None:
        self._add("POST", path, handler)


class _FailOnceRouter(_StrictRouter):
    def __init__(self, fail_path: str) -> None:
        super().__init__()
        self.fail_path = fail_path
        self.failed = False

    def _add(self, method: str, path: str, handler: object) -> None:
        if path == self.fail_path and not self.failed:
            self.failed = True
            raise RuntimeError(f"transient route failure: {path}")
        super()._add(method, path, handler)


class RouteDeploymentBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_registered_routes_for_tests()
        routes._reset_route_runtime_state_for_tests()

    def tearDown(self) -> None:
        reset_registered_routes_for_tests()
        routes._reset_route_runtime_state_for_tests()
        sys.modules.pop("comfy.cli_args", None)

    def test_optional_alias_collision_preserves_foreign_route_and_authoritative_routes(self) -> None:
        foreign_handler = object()
        router = _StrictRouter(routes=[("GET", "/controlnet/model_list", foreign_handler)])
        prompt_server = FakePromptServerInstance(app=FakeApp(router=router))

        routes.register_routes(prompt_server)
        routes.register_routes(prompt_server)

        route_map = {(method, path): handler for method, path, handler in router.routes}
        self.assertIn(("GET", "/rookieui/health"), route_map)
        self.assertIn(("GET", "/api/rookieui/health"), route_map)
        self.assertIn(("POST", "/rookieui/generate/txt2img"), route_map)
        self.assertIs(route_map[("GET", "/controlnet/model_list")], foreign_handler)
        self.assertEqual(len(router.routes), len({(method, path) for method, path, _ in router.routes}))
        alias_status = routes.get_optional_alias_route_status()
        self.assertEqual(alias_status["GET /controlnet/model_list"]["status"], "collision")
        self.assertEqual(alias_status["POST /controlnet/detect"]["status"], "registered")

    def test_multi_user_mode_keeps_diagnostics_but_blocks_stateful_handlers(self) -> None:
        sys.modules["comfy.cli_args"] = types.SimpleNamespace(args=types.SimpleNamespace(multi_user=True))
        router = _StrictRouter()
        prompt_server = FakePromptServerInstance(app=FakeApp(router=router))
        routes.register_routes(prompt_server)

        route_map = {(method, path): handler for method, path, handler in router.routes}
        health_response = asyncio.run(route_map[("GET", "/rookieui/health")](None))
        blocked_response = asyncio.run(route_map[("POST", "/rookieui/generate/txt2img")](None))

        self.assertEqual(health_response["status"], 200)
        self.assertFalse(health_response["payload"]["deployment"]["supported"])
        self.assertEqual(health_response["payload"]["deployment"]["mode"], "multi-user")
        self.assertEqual(blocked_response["status"], 409)
        self.assertEqual(blocked_response["payload"]["status"], "unsupported-host-mode")
        self.assertIn("single-user", blocked_response["payload"]["detail"])
        self.assertNotIn(("GET", "/controlnet/model_list"), route_map)

    def test_retry_completes_partial_authoritative_registration_without_duplicates(self) -> None:
        router = _FailOnceRouter("/rookieui/capabilities")
        prompt_server = FakePromptServerInstance(app=FakeApp(router=router))

        with self.assertRaisesRegex(RuntimeError, "transient route failure"):
            routes.register_routes(prompt_server)
        routes.register_routes(prompt_server)

        route_keys = [(method, path) for method, path, _ in router.routes]
        self.assertEqual(len(route_keys), len(set(route_keys)))
        self.assertIn(("GET", "/rookieui/health"), route_keys)
        self.assertIn(("GET", "/api/rookieui/health"), route_keys)
        self.assertIn(("GET", "/rookieui/capabilities"), route_keys)
        self.assertIn(("POST", "/api/rookieui/generate/txt2img"), route_keys)


if __name__ == "__main__":
    unittest.main()
