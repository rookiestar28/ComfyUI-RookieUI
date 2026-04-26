from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from unittest import mock

from rookieui.api import routes
from rookieui.contracts.prompt_workbench import PROMPT_WORKBENCH_CONTRACT_VERSION
from rookieui.services.prompt_workbench_danbooru import (
    PromptWorkbenchDanbooruExecutionError,
    PromptWorkbenchDanbooruHostUnavailableError,
)


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
                                    "openai": {
                                        "api_key": "test-openai-key",  # pragma: allowlist secret
                                        "base_url": "https://example.test/v1",
                                        "model": "gpt-4.1-mini",
                                    }
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
        self.assertEqual(response["payload"]["persistence"]["schema_version"], 1)
        self.assertNotIn("/", response["payload"]["persistence"]["storage"])

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
        self.assertEqual(history_get["payload"]["persistence"]["storage"], "rookieui_prompt_workbench_state")

    def test_prompt_tools_collection_routes_reject_unknown_actions(self) -> None:
        history_response = asyncio.run(
            routes.prompt_tools_history_update(
                _FakeJsonRequest(
                    {
                        "namespace": "txt2img_prompt",
                        "action": "typo_push",
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
                        "action": "auto_capture",
                        "item": {"prompt_text": "masterpiece", "label": "Base"},
                    }
                )
            )
        )

        self.assertEqual(history_response["status"], 400)
        self.assertEqual(history_response["payload"]["status"], "invalid-request")
        self.assertEqual(favorites_response["status"], 400)
        self.assertEqual(favorites_response["payload"]["status"], "invalid-request")

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

    def test_prompt_tools_providers_route_returns_catalog(self) -> None:
        response = asyncio.run(routes.prompt_tools_providers(_FakeJsonRequest()))

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["contract"]["surface"], "prompt_tools_providers")
        self.assertIn("openai", response["payload"]["surfaces"]["translation"]["shipped_provider_ids"])

    @mock.patch("rookieui.api.routes.execute_prompt_workbench_translate")
    def test_prompt_tools_translate_route_returns_execution_payload(self, mocked_execute: mock.Mock) -> None:
        mocked_execute.return_value = {
            "contract": {"surface": "prompt_tools_translate"},
            "provider_id": "openai",
            "provider_title": "OpenAI-Compatible Chat Translation",
            "mode": "single",
            "from_lang": "auto",
            "to_lang": "zh-TW",
            "translated_text": "translated prompt",
        }

        response = asyncio.run(
            routes.prompt_tools_translate(
                _FakeJsonRequest({"text": "masterpiece, city skyline", "to_lang": "zh-TW"})
            )
        )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["provider_id"], "openai")
        self.assertEqual(response["payload"]["translated_text"], "translated prompt")

    @mock.patch("rookieui.api.routes.execute_prompt_workbench_ai_assist")
    def test_prompt_tools_assist_route_returns_execution_payload(self, mocked_execute: mock.Mock) -> None:
        mocked_execute.return_value = {
            "contract": {"surface": "prompt_tools_assist"},
            "provider_id": "openai",
            "provider_title": "OpenAI-Compatible Chat Translation",
            "language": "en",
            "theme_style": "rookieui_classic",
            "instruction_preset": "Prompt preset",
            "image_description": "city skyline",
            "generated_prompt": "masterpiece, city skyline",
        }

        response = asyncio.run(
            routes.prompt_tools_assist(
                _FakeJsonRequest({"image_description": "city skyline"})
            )
        )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["provider_id"], "openai")
        self.assertEqual(response["payload"]["generated_prompt"], "masterpiece, city skyline")

    def test_prompt_tools_catalog_route_returns_catalog_payload(self) -> None:
        response = asyncio.run(routes.prompt_tools_catalog(_FakeJsonRequest(query={"language": "en"})))

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["contract"]["surface"], "prompt_tools_catalog")
        self.assertTrue(response["payload"]["group_tags"]["groups"])

    @mock.patch("rookieui.api.routes.execute_prompt_workbench_analysis")
    def test_prompt_tools_analyze_route_returns_analysis_payload(self, mocked_execute: mock.Mock) -> None:
        mocked_execute.return_value = {
            "contract": {"surface": "prompt_tools_analyze"},
            "analysis_mode": "syntax_inventory",
            "prompt": {"raw": "masterpiece", "cleaned": "masterpiece", "metrics": {"mode": "syntax_inventory_estimate"}},
            "negative_prompt": {"raw": "", "cleaned": "", "metrics": {"mode": "syntax_inventory_estimate"}},
            "warnings": [],
            "warning_codes": [],
            "lora_activations": [],
            "inventory_snapshot": {"embedding_count": 0, "lora_count": 0},
        }

        response = asyncio.run(routes.prompt_tools_analyze(_FakeJsonRequest({"prompt": "masterpiece"})))

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["contract"]["surface"], "prompt_tools_analyze")
        self.assertEqual(response["payload"]["analysis_mode"], "syntax_inventory")

    @mock.patch("rookieui.api.routes.execute_prompt_workbench_upsample", new_callable=mock.AsyncMock)
    def test_prompt_tools_upsample_route_returns_execution_payload(self, mocked_execute: mock.AsyncMock) -> None:
        mocked_execute.return_value = {
            "contract": {"surface": "prompt_tools_upsample"},
            "action_id": "danbooru_upsample",
            "final_prompt": "masterpiece, city skyline, enhanced tags",
            "generated_suffix": "enhanced tags",
            "host_node_alias": "DanbooruTagsUpsampler",
            "availability": {"status": "ready"},
            "warnings": [],
            "warning_codes": [],
        }

        response = asyncio.run(
            routes.prompt_tools_upsample(
                _FakeJsonRequest({"prompt": "masterpiece, city skyline"})
            )
        )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["status"], "ok")
        self.assertEqual(response["payload"]["action_id"], "danbooru_upsample")
        self.assertEqual(response["payload"]["generated_suffix"], "enhanced tags")

    @mock.patch("rookieui.api.routes.execute_prompt_workbench_upsample", new_callable=mock.AsyncMock)
    def test_prompt_tools_upsample_route_maps_host_unavailable(self, mocked_execute: mock.AsyncMock) -> None:
        mocked_execute.side_effect = PromptWorkbenchDanbooruHostUnavailableError("Host node missing")

        response = asyncio.run(routes.prompt_tools_upsample(_FakeJsonRequest({"prompt": "masterpiece"})))

        self.assertEqual(response["status"], 503)
        self.assertEqual(response["payload"]["status"], "host-unavailable")

    @mock.patch("rookieui.api.routes.execute_prompt_workbench_upsample", new_callable=mock.AsyncMock)
    def test_prompt_tools_upsample_route_maps_host_action_error(self, mocked_execute: mock.AsyncMock) -> None:
        mocked_execute.side_effect = PromptWorkbenchDanbooruExecutionError("Execution failed")

        response = asyncio.run(routes.prompt_tools_upsample(_FakeJsonRequest({"prompt": "masterpiece"})))

        self.assertEqual(response["status"], 502)
        self.assertEqual(response["payload"]["status"], "host-action-error")

    @mock.patch("rookieui.api.routes.execute_prompt_workbench_upsample", new_callable=mock.AsyncMock)
    def test_prompt_tools_upsample_route_maps_invalid_request(self, mocked_execute: mock.AsyncMock) -> None:
        mocked_execute.side_effect = ValueError("Prompt text required")

        response = asyncio.run(routes.prompt_tools_upsample(_FakeJsonRequest({"prompt": ""})))

        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"]["status"], "invalid-request")
