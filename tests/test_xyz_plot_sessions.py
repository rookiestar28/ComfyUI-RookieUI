from __future__ import annotations

import asyncio
from contextlib import ExitStack
import os
import tempfile
import types
import unittest
from unittest import mock

from rookieui.services import xyz_plot_sessions


class _FakePromptQueue:
    def __init__(self) -> None:
        self.items: list[tuple[object, ...]] = []
        self.history: dict[str, dict[str, object]] = {}

    def put(self, item: tuple[object, ...]) -> None:
        self.items.append(item)

    def get_current_queue_volatile(self) -> tuple[list[tuple[object, ...]], list[tuple[object, ...]]]:
        return ([], list(self.items))

    def get_history(self, max_items: int | None = None, offset: int = 0) -> dict[str, dict[str, object]]:
        _ = max_items
        _ = offset
        return dict(self.history)

    def delete_queue_item(self, prompt_id: str) -> bool:
        before = len(self.items)
        self.items = [item for item in self.items if item[1] != prompt_id]
        return len(self.items) != before


class _FakePromptServer:
    def __init__(self) -> None:
        self.prompt_queue = _FakePromptQueue()


class XYZPlotSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.runtime_dir.cleanup)
        self.env_patcher = mock.patch.dict(
            os.environ,
            {"ROOKIEUI_XYZ_PLOT_RUNTIME_ROOT": self.runtime_dir.name},
            clear=False,
        )
        self.env_patcher.start()
        self.addCleanup(self.env_patcher.stop)
        xyz_plot_sessions.reset_xyz_plot_session_store_for_tests()

    def _patch_generation_pipeline(self) -> tuple[mock._patch, mock._patch, mock._patch, mock._patch]:
        fake_translation = types.SimpleNamespace(
            workflow={"7": {"class_type": "SaveImage"}},
            profile="sd15",
        )
        return (
            mock.patch.object(xyz_plot_sessions, "normalize_txt2img_request", return_value={"normalized": True}),
            mock.patch.object(xyz_plot_sessions, "translate_txt2img_request", return_value=fake_translation),
            mock.patch.object(xyz_plot_sessions, "normalize_img2img_request", return_value={"normalized": True}),
            mock.patch.object(xyz_plot_sessions, "translate_img2img_request", return_value=fake_translation),
        )

    def test_execute_xyz_plot_run_creates_session_and_submits_first_cell(self) -> None:
        prompt_server = _FakePromptServer()
        with ExitStack() as stack:
            for patcher in self._patch_generation_pipeline():
                stack.enter_context(patcher)
            stack.enter_context(
                mock.patch.object(
                    xyz_plot_sessions,
                    "submit_prompt_workflow",
                    mock.AsyncMock(return_value={"prompt_id": "prompt-1", "number": 1}),
                )
            )
            payload = asyncio.run(
                xyz_plot_sessions.execute_xyz_plot_run(
                    {
                        "mode": "txt2img",
                        "base_request": {"prompt": "cat, dog", "steps": 20},
                        "axes": [
                            {"axis_id": "steps", "values": "10,20"},
                            {"axis_id": "cfg_scale", "values": "5,6"},
                        ],
                    },
                    prompt_server,
                )
            )

        self.assertEqual(payload["session"]["status"], "in_progress")
        self.assertEqual(payload["session"]["summary"]["total_cells"], 4)
        self.assertEqual(payload["session"]["summary"]["submitted_cells"], 1)
        self.assertEqual(payload["session"]["cells"][0]["prompt_id"], "prompt-1")
        self.assertEqual(payload["session"]["cells"][1]["status"], "pending")

    def test_session_detail_advances_next_pending_cell_when_capacity_frees_up(self) -> None:
        prompt_server = _FakePromptServer()
        submit_mock = mock.AsyncMock(side_effect=[{"prompt_id": "prompt-1", "number": 1}, {"prompt_id": "prompt-2", "number": 2}])
        with ExitStack() as stack:
            for patcher in self._patch_generation_pipeline():
                stack.enter_context(patcher)
            stack.enter_context(mock.patch.object(xyz_plot_sessions, "submit_prompt_workflow", submit_mock))
            run_payload = asyncio.run(
                xyz_plot_sessions.execute_xyz_plot_run(
                    {
                        "mode": "txt2img",
                        "base_request": {"prompt": "cat", "steps": 20},
                        "axes": [{"axis_id": "steps", "values": "10,20"}],
                    },
                    prompt_server,
                )
            )
            session_id = run_payload["session"]["session_id"]
            prompt_server.prompt_queue.items = []
            prompt_server.prompt_queue.history["prompt-1"] = {
                "prompt": (
                    1,
                    "prompt-1",
                    {"7": {"class_type": "SaveImage"}},
                    {"create_time": 101, "rookieui_origin": "rookieui"},
                    ["7"],
                    {},
                ),
                "outputs": {},
                "status": {"status_str": "success", "messages": []},
            }
            detail_payload = asyncio.run(
                xyz_plot_sessions.build_xyz_plot_session_detail_payload(session_id, prompt_server)
            )

        self.assertEqual(detail_payload["session"]["summary"]["completed_cells"], 1)
        self.assertEqual(detail_payload["session"]["summary"]["submitted_cells"], 2)
        self.assertEqual(detail_payload["session"]["cells"][1]["prompt_id"], "prompt-2")

    def test_cancel_marks_pending_cells_cancelled_and_removes_queued_jobs_when_possible(self) -> None:
        prompt_server = _FakePromptServer()
        with ExitStack() as stack:
            for patcher in self._patch_generation_pipeline():
                stack.enter_context(patcher)
            stack.enter_context(
                mock.patch.object(
                    xyz_plot_sessions,
                    "submit_prompt_workflow",
                    mock.AsyncMock(return_value={"prompt_id": "prompt-1", "number": 1}),
                )
            )
            run_payload = asyncio.run(
                xyz_plot_sessions.execute_xyz_plot_run(
                    {
                        "mode": "txt2img",
                        "base_request": {"prompt": "cat", "steps": 20},
                        "axes": [{"axis_id": "steps", "values": "10,20"}],
                    },
                    prompt_server,
                )
            )
            session_id = run_payload["session"]["session_id"]
            prompt_server.prompt_queue.items = [
                (
                    1,
                    "prompt-1",
                    {"7": {"class_type": "SaveImage"}},
                    {"create_time": 101, "rookieui_origin": "rookieui"},
                    ["7"],
                    {},
                )
            ]
            cancel_payload = asyncio.run(
                xyz_plot_sessions.execute_xyz_plot_session_cancel(session_id, prompt_server)
            )

        self.assertTrue(cancel_payload["session"]["cancel_requested"])
        self.assertEqual(cancel_payload["session"]["cells"][0]["status"], "cancelled")
        self.assertEqual(cancel_payload["session"]["cells"][1]["status"], "cancelled")

    def test_rejects_non_runner_ready_axis(self) -> None:
        prompt_server = _FakePromptServer()
        with self.assertRaisesRegex(ValueError, "not session-runnable yet"):
            asyncio.run(
                xyz_plot_sessions.execute_xyz_plot_run(
                    {
                        "mode": "txt2img",
                        "base_request": {"prompt": "cat", "steps": 20},
                        "axes": [{"axis_id": "var_seed", "values": "1,2"}],
                    },
                    prompt_server,
                )
            )
