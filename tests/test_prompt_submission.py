from __future__ import annotations

import asyncio
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
        self.node_replace_manager = types.SimpleNamespace(
            apply_replacements=lambda _workflow: None
        )


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
