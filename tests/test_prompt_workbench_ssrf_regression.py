from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from rookieui.api import route_spec
from rookieui.security.route_guard import SafeRouteRegistrar
from rookieui.services import prompt_workbench_state as state


class PromptWorkbenchSSRFRouteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        fixture_root = Path(__file__).resolve().parents[1] / ".tmp" / "ssrf-fixtures"
        fixture_root.mkdir(parents=True, exist_ok=True)
        self.runtime = tempfile.TemporaryDirectory(dir=fixture_root)
        self.addCleanup(self.runtime.cleanup)
        self.env = mock.patch.dict(
            os.environ,
            {"ROOKIEUI_PROMPT_WORKBENCH_RUNTIME_ROOT": self.runtime.name},
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        self.fake_key = "synthetic-provider-fixture"  # pragma: allowlist secret
        self.sink_requests = 0
        self.sink_received_fake_credential = False
        sink_app = web.Application()
        sink_app.router.add_route("*", "/{tail:.*}", self._sink)
        self.sink = TestServer(sink_app)
        await self.sink.start_server()
        self.addAsyncCleanup(self.sink.close)
        app = web.Application()
        registrar = SafeRouteRegistrar(app.router, allowed_prefixes=("/rookieui", "/api/rookieui"))
        for spec in route_spec.AUTHORITATIVE_ROUTE_SPECS:
            if spec.suffix in {
                "/prompt-tools/config",
                "/prompt-tools/export",
                "/prompt-tools/import",
                "/prompt-tools/assist",
                "/prompt-tools/translate",
            }:
                route_spec._register_authoritative_spec(registrar, spec)
        self.client = TestClient(TestServer(app))
        await self.client.start_server()
        self.addAsyncCleanup(self.client.close)

    async def _sink(self, request: web.Request) -> web.Response:
        self.sink_requests += 1
        self.sink_received_fake_credential = (
            request.headers.get("Authorization") == f"Bearer {self.fake_key}"
        )
        return web.json_response(
            {
                "choices": [{"message": {"content": "synthetic result"}}],
                "responseData": {"translatedText": "synthetic result"},
            }
        )

    def _seed(self, surface: str, provider_id: str) -> None:
        settings = {"model": "fixture-model"}
        if provider_id == "openai":
            settings["api_key"] = self.fake_key
        state.save_prompt_workbench_store(
            {
                "config": {
                    surface: {
                        "default_provider": provider_id,
                        "providers": {provider_id: settings},
                    }
                }
            }
        )
        self.sink_requests = 0
        self.sink_received_fake_credential = False

    async def _execute(self, prefix: str, surface: str) -> int:
        if surface == "ai_assist":
            suffix = "assist"
            payload = {"image_description": "synthetic fixture"}
        else:
            suffix = "translate"
            payload = {"text": "synthetic fixture", "from_lang": "en", "to_lang": "es"}
        async with self.client.post(f"{prefix}/prompt-tools/{suffix}", json=payload) as response:
            await response.read()
            return response.status

    async def test_endpoint_replacement_is_rejected_without_persistence_or_egress(self) -> None:
        for prefix in ("/rookieui", "/api/rookieui"):
            for surface, provider_id in (
                ("ai_assist", "openai"),
                ("translation", "openai"),
                ("translation", "mymemory_free"),
            ):
                for operation in ("config", "import"):
                    with self.subTest(prefix=prefix, surface=surface, provider=provider_id, operation=operation):
                        self._seed(surface, provider_id)
                        path = Path(self.runtime.name) / "state.json"
                        original_bytes = path.read_bytes()
                        endpoint_path = "v1" if provider_id == "openai" else "get"
                        malicious = state.load_prompt_workbench_store()["config"]
                        provider_config = malicious[surface]["providers"][provider_id]
                        provider_config["base_url"] = str(self.sink.make_url(f"/{endpoint_path}"))
                        provider_config["allow_custom_endpoint"] = True
                        if operation == "import":
                            async with self.client.get(f"{prefix}/prompt-tools/export") as response:
                                exported = (await response.json())["export"]
                            exported["data"]["config"][surface]["providers"][provider_id].update(
                                {
                                    "base_url": provider_config["base_url"],
                                    "allow_custom_endpoint": True,
                                }
                            )
                            body = {"export": exported}
                        else:
                            body = {"config": malicious}
                        async with self.client.post(f"{prefix}/prompt-tools/{operation}", json=body) as response:
                            mutation_status = response.status
                            response_text = await response.text()
                        execution_status = await self._execute(prefix, surface) if mutation_status == 200 else None
                        # Content-free RED/GREEN evidence: never print requests, prompts or keys.
                        print(
                            f"SSRF fixture {prefix} {surface} {provider_id} {operation}: "
                            f"mutation={mutation_status} execution={execution_status} "
                            f"sink_requests={self.sink_requests} "
                            f"fake_credential_received={self.sink_received_fake_credential}"
                        )
                        self.assertEqual(mutation_status, 400)
                        self.assertEqual(path.read_bytes(), original_bytes)
                        self.assertEqual(self.sink_requests, 0)
                        self.assertNotIn(self.fake_key, response_text)

    async def test_legacy_custom_endpoint_fails_closed_without_rewriting_state(self) -> None:
        for surface, provider_id in (("ai_assist", "openai"), ("translation", "mymemory_free")):
            with self.subTest(surface=surface):
                self._seed(surface, provider_id)
                store = state.load_prompt_workbench_store()
                config = store["config"][surface]["providers"][provider_id]
                config["base_url"] = str(self.sink.make_url("/v1" if provider_id == "openai" else "/get"))
                config["allow_custom_endpoint"] = True
                state.save_prompt_workbench_store(store)
                path = Path(self.runtime.name) / "state.json"
                original_bytes = path.read_bytes()
                status = await self._execute("/rookieui", surface)
                print(f"SSRF legacy fixture {surface}: execution={status} sink_requests={self.sink_requests}")
                self.assertEqual(status, 502)
                self.assertEqual(self.sink_requests, 0)
                self.assertEqual(path.read_bytes(), original_bytes)

    async def test_masked_official_export_import_round_trip_preserves_credential(self) -> None:
        self._seed("ai_assist", "openai")
        async with self.client.get("/rookieui/prompt-tools/export") as response:
            exported = (await response.json())["export"]
        self.assertNotIn(self.fake_key, json.dumps(exported))
        async with self.client.post("/rookieui/prompt-tools/import", json={"export": exported}) as response:
            self.assertEqual(response.status, 200)
            self.assertNotIn(self.fake_key, await response.text())
        restored = state.load_prompt_workbench_store()["config"]["ai_assist"]["providers"]["openai"]
        self.assertTrue(restored["api_key"] == self.fake_key)
        self.assertEqual(self.sink_requests, 0)
