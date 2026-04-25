from __future__ import annotations

import types
import unittest

from rookieui.services import route_bootstrap
from tests.helpers.fake_prompt_server import FakePromptServerInstance


class RouteBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        route_bootstrap._reset_registration_state_for_tests()

    def tearDown(self) -> None:
        route_bootstrap._reset_registration_state_for_tests()

    def test_registers_routes_when_prompt_server_is_ready(self) -> None:
        prompt_server = FakePromptServerInstance()
        server_module = types.SimpleNamespace(
            PromptServer=types.SimpleNamespace(instance=prompt_server)
        )

        try:
            import sys

            sys.modules["server"] = server_module
            route_bootstrap.register_routes_once()
        finally:
            sys.modules.pop("server", None)

        route_keys = {(method, path) for method, path, _handler in prompt_server.app.router.routes}
        self.assertIn(("POST", "/rookieui/generate/txt2img"), route_keys)
        self.assertIn(("POST", "/api/rookieui/generate/txt2img"), route_keys)
        self.assertIn(("GET", "/rookieui/models"), route_keys)
        self.assertIn(("GET", "/api/rookieui/models"), route_keys)
        self.assertIn(("POST", "/rookieui/controlnet/detect"), route_keys)
        self.assertIn(("POST", "/api/rookieui/controlnet/detect"), route_keys)
        self.assertIn(("GET", "/controlnet/model_list"), route_keys)

    def test_register_routes_once_is_idempotent(self) -> None:
        prompt_server = FakePromptServerInstance()
        server_module = types.SimpleNamespace(
            PromptServer=types.SimpleNamespace(instance=prompt_server)
        )

        try:
            import sys

            sys.modules["server"] = server_module
            route_bootstrap.register_routes_once()
            route_bootstrap.register_routes_once()
        finally:
            sys.modules.pop("server", None)

        route_keys = [(method, path) for method, path, _handler in prompt_server.app.router.routes]
        self.assertEqual(
            len(route_keys),
            len(set(route_keys)),
            "register_routes_once() must not duplicate route registrations",
        )
        self.assertIn(("POST", "/rookieui/generate/txt2img"), route_keys)
        self.assertIn(("POST", "/api/rookieui/generate/txt2img"), route_keys)
