from __future__ import annotations

import asyncio
import types
import unittest
from unittest import mock

from rookieui.services.prompt_submission import submit_prompt_workflow


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
        self.assertEqual(queued_item[3]["rookieui_origin"], "rookieui")
        self.assertEqual(queued_item[3]["rookieui_surface"], "txt2img")
        self.assertEqual(queued_item[3]["preview_method"], "auto")

    def test_submit_prompt_workflow_requires_host_prompt_queue(self) -> None:
        with self.assertRaises(RuntimeError):
            asyncio.run(submit_prompt_workflow(None, {}))
