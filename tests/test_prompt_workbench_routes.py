from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from unittest import mock

from rookieui.api import routes
from rookieui.contracts.prompt_workbench import PROMPT_WORKBENCH_CONTRACT_VERSION


class _FakeJsonRequest:
    def __init__(
        self,
        payload: dict[str, object] | None = None,
        *,
        query: dict[str, object] | None = None,
    ) -> None:
        self._payload = payload or {}
        self.query = query or {}

    async def json(self) -> dict[str, object]:
        return self._payload


class PromptWorkbenchRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.runtime_dir.cleanup)
        self.env_patcher = mock.patch.dict(
            os.environ,
            {"ROOKIEUI_PROMPT_WORKBENCH_RUNTIME_ROOT": self.runtime_dir.name},
            clear=False,
        )
        self.env_patcher.start()
        self.addCleanup(self.env_patcher.stop)

    def test_prompt_tools_config_route_returns_masked_bootstrap_payload(self) -> None:
        asyncio.run(
            routes.prompt_tools_config_update(
                _FakeJsonRequest(
                    {
                        "config": {
                            "translation": {
                                "default_provider": "openai",
                                "providers": {
                                    "openai": {"api_key": "sk-secret", "endpoint": "https://example.test"}
                                },
                            }
                        }
                    }
                )
            )
        )

        response = asyncio.run(routes.prompt_tools_config(_FakeJsonRequest()))

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["contract"]["version"], PROMPT_WORKBENCH_CONTRACT_VERSION)
        self.assertEqual(response["payload"]["config"]["translation"]["providers"]["openai"]["api_key"], "********")

    def test_prompt_tools_state_route_rejects_invalid_namespace(self) -> None:
        response = asyncio.run(routes.prompt_tools_state(_FakeJsonRequest(query={"namespace": "invalid"})))

        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"]["status"], "invalid-request")

    def test_prompt_tools_history_and_favorites_routes_round_trip_entries(self) -> None:
        history_response = asyncio.run(
            routes.prompt_tools_history_update(
                _FakeJsonRequest(
                    {
                        "namespace": "txt2img_prompt",
                        "action": "push",
                        "item": {"prompt_text": "masterpiece", "label": "Base"},
                    }
                )
            )
        )
        favorites_response = asyncio.run(
            routes.prompt_tools_favorites_update(
                _FakeJsonRequest(
                    {
                        "namespace": "txt2img_prompt",
                        "action": "push",
                        "item": {"prompt_text": "cinematic lighting", "label": "Lighting"},
                    }
                )
            )
        )
        history_get = asyncio.run(
            routes.prompt_tools_history(_FakeJsonRequest(query={"namespace": "txt2img_prompt"}))
        )
        favorites_get = asyncio.run(
            routes.prompt_tools_favorites(_FakeJsonRequest(query={"namespace": "txt2img_prompt"}))
        )

        self.assertEqual(history_response["payload"]["status"], "ok")
        self.assertEqual(favorites_response["payload"]["status"], "ok")
        self.assertEqual(history_get["payload"]["items"][0]["label"], "Base")
        self.assertEqual(favorites_get["payload"]["items"][0]["label"], "Lighting")

    def test_prompt_tools_blacklist_route_round_trips_state(self) -> None:
        update_response = asyncio.run(
            routes.prompt_tools_blacklist_update(
                _FakeJsonRequest({"blacklist": {"enabled": True, "entries": ["bad anatomy", "blurry"]}})
            )
        )
        get_response = asyncio.run(routes.prompt_tools_blacklist(_FakeJsonRequest()))

        self.assertEqual(update_response["payload"]["status"], "ok")
        self.assertTrue(get_response["payload"]["blacklist"]["enabled"])
        self.assertEqual(get_response["payload"]["blacklist"]["entries"], ["bad anatomy", "blurry"])
