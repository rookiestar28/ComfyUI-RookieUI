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

        self.assertEqual(
            [path for _method, path, _handler in prompt_server.app.router.routes],
            [
                "/rookieui/health",
                "/rookieui/bootstrap",
                "/rookieui/capabilities",
                "/rookieui/parity",
                "/rookieui/compatibility",
                "/rookieui/models",
                "/rookieui/presets",
                "/rookieui/controlnet/model_list",
                "/rookieui/controlnet/module_list",
                "/rookieui/controlnet/control_types",
                "/rookieui/adetailer/catalog",
                "/rookieui/queue",
                "/rookieui/queue/{prompt_id}",
                "/rookieui/pnginfo/parse",
                "/rookieui/pnginfo/inspect",
                "/rookieui/controlnet/detect",
                "/rookieui/generate/txt2img",
                "/rookieui/generate/img2img",
                "/rookieui/extras/run",
                "/controlnet/model_list",
                "/controlnet/module_list",
                "/controlnet/control_types",
                "/controlnet/detect",
            ],
        )

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

        self.assertEqual(len(prompt_server.app.router.routes), 23)
