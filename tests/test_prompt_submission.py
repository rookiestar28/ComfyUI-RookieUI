from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path
import types
import unittest
from unittest import mock

from rookieui.services.prompt_submission import (
    ROOKIEUI_COMFY_USAGE_SOURCE,
    submit_prompt_workflow,
)


class _FakePromptQueue:
    def __init__(self) -> None:
        self.items: list[tuple[object, ...]] = []

    def put(self, item: tuple[object, ...]) -> None:
        self.items.append(item)


class _FakePromptServer:
    def __init__(self) -> None:
        self.number = 7
        self.prompt_queue = _FakePromptQueue()
        self.events: list[str] = []
        self.node_replace_manager = types.SimpleNamespace(
            apply_replacements=lambda _workflow: self.events.append("replace")
        )

    def trigger_on_prompt(self, envelope: dict[str, object]) -> dict[str, object]:
        self.events.append("hook")
        return envelope


class PromptSubmissionTests(unittest.TestCase):
    def test_submit_prompt_workflow_enqueues_valid_prompt(self) -> None:
        prompt_server = _FakePromptServer()
        execution_module = types.SimpleNamespace(
            validate_prompt=mock.AsyncMock(return_value=(True, None, ["7"], {}))
        )

        with mock.patch(
            "rookieui.services.prompt_submission._get_execution_module",
            return_value=execution_module,
        ):
            result = asyncio.run(
                submit_prompt_workflow(prompt_server, {"7": {"class_type": "SaveImage"}})
            )

        self.assertTrue(result["accepted"])
        self.assertEqual(result["number"], 7)
        self.assertEqual(len(prompt_server.prompt_queue.items), 1)
        queued_item = prompt_server.prompt_queue.items[0]
        self.assertEqual(len(queued_item), 6)
        self.assertEqual(queued_item[0], 7)
        self.assertEqual(queued_item[2], {"7": {"class_type": "SaveImage"}})
        self.assertEqual(queued_item[3]["rookieui_origin"], "rookieui")
        self.assertEqual(queued_item[3]["rookieui_surface"], "txt2img")
        self.assertEqual(queued_item[3]["preview_method"], "auto")
        self.assertEqual(queued_item[3]["comfy_usage_source"], ROOKIEUI_COMFY_USAGE_SOURCE)
        self.assertEqual(queued_item[4], ["7"])
        self.assertEqual(queued_item[5], {})
        self.assertEqual(prompt_server.events, ["hook", "replace"])

    def test_submit_prompt_workflow_merges_extra_metadata(self) -> None:
        prompt_server = _FakePromptServer()
        execution_module = types.SimpleNamespace(
            validate_prompt=mock.AsyncMock(return_value=(True, None, ["7"], {}))
        )

        with mock.patch(
            "rookieui.services.prompt_submission._get_execution_module",
            return_value=execution_module,
        ):
            asyncio.run(
                submit_prompt_workflow(
                    prompt_server,
                    {"7": {"class_type": "SaveImage"}},
                    surface="xyz_plot",
                    extra_metadata={"rookieui_xyz_session_id": "xyz-1"},
                )
            )

        queued_item = prompt_server.prompt_queue.items[0]
        self.assertEqual(queued_item[3]["rookieui_xyz_session_id"], "xyz-1")

    def test_submit_prompt_workflow_protects_comfy_usage_source(self) -> None:
        prompt_server = _FakePromptServer()
        execution_module = types.SimpleNamespace(
            validate_prompt=mock.AsyncMock(return_value=(True, None, ["7"], {}))
        )

        with mock.patch(
            "rookieui.services.prompt_submission._get_execution_module",
            return_value=execution_module,
        ):
            asyncio.run(
                submit_prompt_workflow(
                    prompt_server,
                    {"7": {"class_type": "SaveImage"}},
                    extra_metadata={"comfy_usage_source": "comfyui-api"},
                )
            )

        queued_item = prompt_server.prompt_queue.items[0]
        self.assertEqual(queued_item[3]["comfy_usage_source"], ROOKIEUI_COMFY_USAGE_SOURCE)

    def test_submit_prompt_workflow_preserves_embeddable_extra_pnginfo(self) -> None:
        prompt_server = _FakePromptServer()
        execution_module = types.SimpleNamespace(
            validate_prompt=mock.AsyncMock(return_value=(True, None, ["7"], {}))
        )

        with mock.patch(
            "rookieui.services.prompt_submission._get_execution_module",
            return_value=execution_module,
        ):
            asyncio.run(
                submit_prompt_workflow(
                    prompt_server,
                    {"7": {"class_type": "RookieUISaveImageWithMetadata"}},
                    extra_pnginfo={
                        "rookieui": {
                            "schema": "rookieui.generation_metadata.v1",
                            "surface": "txt2img",
                        }
                    },
                    extra_metadata={"extra_pnginfo": {"parameters": "must not override"}},
                )
            )

        queued_item = prompt_server.prompt_queue.items[0]
        self.assertEqual(
            queued_item[3]["extra_pnginfo"],
            {
                "rookieui": {
                    "schema": "rookieui.generation_metadata.v1",
                    "surface": "txt2img",
                }
            },
        )
        self.assertNotIn("parameters", queued_item[3]["extra_pnginfo"])

    def test_submit_prompt_workflow_requires_host_prompt_queue(self) -> None:
        with self.assertRaises(RuntimeError):
            asyncio.run(submit_prompt_workflow(None, {}))

    def test_submit_prompt_workflow_honors_host_envelope_order_and_sensitive_separation(self) -> None:
        prompt_server = _FakePromptServer()
        canonical_prompt_id = "12345678-1234-5678-9234-567812345678"

        def _trigger(envelope: dict[str, object]) -> dict[str, object]:
            prompt_server.events.append("hook")
            envelope["number"] = 42.5
            envelope["prompt_id"] = canonical_prompt_id
            envelope["partial_execution_targets"] = ["7"]
            envelope["client_id"] = "hook-client"
            envelope["prompt"]["7"]["inputs"] = {"hooked": True}
            return envelope

        prompt_server.trigger_on_prompt = _trigger

        async def _validate(
            prompt_id: str,
            workflow: dict[str, object],
            partial_execution_targets: list[str] | None,
        ) -> tuple[bool, None, list[str], dict[str, object]]:
            prompt_server.events.append("validate")
            self.assertEqual(prompt_server.events, ["hook", "replace", "validate"])
            self.assertEqual(prompt_id, canonical_prompt_id)
            self.assertEqual(workflow["7"]["inputs"], {"hooked": True})
            self.assertEqual(partial_execution_targets, ["7"])
            return True, None, ["7"], {"7": {"warning": "fixture"}}

        execution_module = types.SimpleNamespace(
            SENSITIVE_EXTRA_DATA_KEYS=("auth_token_comfy_org", "api_key_comfy_org"),
            validate_prompt=_validate,
        )
        with mock.patch(
            "rookieui.services.prompt_submission._get_execution_module",
            return_value=execution_module,
        ), mock.patch("rookieui.services.prompt_submission.time.time", return_value=1234.5):
            result = asyncio.run(
                submit_prompt_workflow(
                    prompt_server,
                    {"7": {"class_type": "SaveImage"}},
                    client_id="original-client",
                    extra_metadata={
                        "auth_token_comfy_org": "sentinel-auth-token",
                        "api_key_comfy_org": "sentinel-api-key",  # pragma: allowlist secret
                    },
                )
            )

        queued_item = prompt_server.prompt_queue.items[0]
        self.assertEqual(queued_item[0], 42.5)
        self.assertEqual(queued_item[1], canonical_prompt_id)
        self.assertEqual(queued_item[3]["client_id"], "hook-client")
        self.assertEqual(queued_item[3]["create_time"], 1_234_500)
        self.assertNotIn("auth_token_comfy_org", queued_item[3])
        self.assertNotIn("api_key_comfy_org", queued_item[3])
        self.assertEqual(
            queued_item[5],
            {
                "auth_token_comfy_org": "sentinel-auth-token",
                "api_key_comfy_org": "sentinel-api-key",  # pragma: allowlist secret
            },
        )
        self.assertEqual(result["node_errors"], {"7": {"warning": "fixture"}})
        self.assertEqual(prompt_server.number, 7)

    def test_submit_prompt_workflow_applies_front_to_allocated_number(self) -> None:
        prompt_server = _FakePromptServer()
        execution_module = types.SimpleNamespace(
            SENSITIVE_EXTRA_DATA_KEYS=(),
            validate_prompt=mock.AsyncMock(return_value=(True, None, ["7"], {})),
        )
        with mock.patch(
            "rookieui.services.prompt_submission._get_execution_module",
            return_value=execution_module,
        ):
            result = asyncio.run(
                submit_prompt_workflow(
                    prompt_server,
                    {"7": {"class_type": "SaveImage"}},
                    front=True,
                )
            )

        self.assertEqual(result["number"], -7)
        self.assertEqual(prompt_server.number, 8)

    def test_submit_prompt_workflow_rejects_noncanonical_prompt_id_without_queueing(self) -> None:
        prompt_server = _FakePromptServer()
        execution_module = types.SimpleNamespace(
            SENSITIVE_EXTRA_DATA_KEYS=(),
            validate_prompt=mock.AsyncMock(return_value=(True, None, ["7"], {})),
        )
        with mock.patch(
            "rookieui.services.prompt_submission._get_execution_module",
            return_value=execution_module,
        ):
            with self.assertRaisesRegex(ValueError, "canonical lowercase"):
                asyncio.run(
                    submit_prompt_workflow(
                        prompt_server,
                        {"7": {"class_type": "SaveImage"}},
                        prompt_id="12345678-1234-5678-9234-56781234567A",
                    )
                )

        self.assertEqual(prompt_server.prompt_queue.items, [])

    def test_submit_prompt_workflow_runs_source_derived_impact_switch_mutation(self) -> None:
        fixture_path = Path(__file__).resolve().parent / "fixtures" / "impact_on_prompt_switch_mutation.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        prompt_server = _FakePromptServer()

        def _impact_switch_handler(envelope: dict[str, object]) -> dict[str, object]:
            prompt_server.events.append("hook")
            prompt = envelope["prompt"]
            switch = prompt["2"]
            select_ref = switch["inputs"]["select"]
            selected = prompt[select_ref[0]]["inputs"]["value"]
            for input_name in ("input1", "input2"):
                if input_name != f"input{selected}":
                    del switch["inputs"][input_name]
            return envelope

        prompt_server.trigger_on_prompt = _impact_switch_handler
        execution_module = types.SimpleNamespace(
            SENSITIVE_EXTRA_DATA_KEYS=(),
            validate_prompt=mock.AsyncMock(return_value=(True, None, ["2"], {})),
        )
        with mock.patch(
            "rookieui.services.prompt_submission._get_execution_module",
            return_value=execution_module,
        ):
            asyncio.run(submit_prompt_workflow(prompt_server, copy.deepcopy(fixture["prompt"])))

        queued_prompt = prompt_server.prompt_queue.items[0][2]
        self.assertIn("input2", queued_prompt["2"]["inputs"])
        self.assertNotIn("input1", queued_prompt["2"]["inputs"])

    def test_submit_prompt_workflow_does_not_queue_validation_failure(self) -> None:
        prompt_server = _FakePromptServer()
        execution_module = types.SimpleNamespace(
            SENSITIVE_EXTRA_DATA_KEYS=(),
            validate_prompt=mock.AsyncMock(
                return_value=(False, {"type": "invalid_prompt"}, [], {"7": {"errors": []}})
            ),
        )
        with mock.patch(
            "rookieui.services.prompt_submission._get_execution_module",
            return_value=execution_module,
        ):
            with self.assertRaisesRegex(ValueError, "invalid_prompt"):
                asyncio.run(submit_prompt_workflow(prompt_server, {"7": {"class_type": "SaveImage"}}))

        self.assertEqual(prompt_server.prompt_queue.items, [])
