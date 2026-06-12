from __future__ import annotations

import asyncio
import types
import unittest
from unittest import mock

from rookieui.api import routes
from rookieui.contracts.queue import QUEUE_CONTRACT_VERSION
from rookieui.services.queue_snapshot import build_queue_snapshot


class _FakePromptQueue:
    def get_current_queue_volatile(self) -> tuple[list[tuple[object, ...]], list[tuple[object, ...]]]:
        return (
            [
                (
                    1,
                    "prompt-running",
                    {"1": {"class_type": "SaveImage"}},
                    {"create_time": 101, "rookieui_origin": "rookieui", "client_id": "browser-1"},
                    ["1"],
                    {},
                ),
                (
                    5,
                    "host-canvas-running",
                    {"1": {"class_type": "SaveImage"}},
                    {"create_time": 103},
                    ["1"],
                    {},
                ),
            ],
            [
                (
                    2,
                    "prompt-pending",
                    {"1": {"class_type": "SaveImage"}},
                    {"create_time": 99, "rookieui_origin": "rookieui", "client_id": "browser-1"},
                    ["1"],
                    {},
                ),
                (
                    9,
                    "other-client-pending",
                    {"1": {"class_type": "SaveImage"}},
                    {"create_time": 95, "rookieui_origin": "rookieui", "client_id": "browser-2"},
                    ["1"],
                    {},
                ),
                (
                    6,
                    "host-canvas-pending",
                    {"1": {"class_type": "SaveImage"}},
                    {"create_time": 98},
                    ["1"],
                    {},
                ),
            ],
        )

    def get_history(self, max_items: int | None = None, offset: int = 0) -> dict[str, dict[str, object]]:
        _ = max_items
        _ = offset
        return {
            "prompt-history": {
                "prompt": (
                    3,
                    "prompt-history",
                    {"1": {"class_type": "SaveImage"}},
                    {"create_time": 111, "rookieui_origin": "rookieui", "client_id": "browser-1"},
                    ["1"],
                    {},
                ),
                "outputs": {
                    "7": {
                        "images": [
                            {
                                "filename": "history-image.png",
                                "type": "output",
                                "subfolder": "",
                                "id": "asset-history-1",
                            },
                        ]
                    }
                },
                "status": {"status_str": "success", "messages": []},
            },
            "host-canvas-history": {
                "prompt": (
                    4,
                    "host-canvas-history",
                    {"1": {"class_type": "SaveImage"}},
                    {"create_time": 112},
                    ["1"],
                    {},
                ),
                "outputs": {
                    "7": {
                        "images": [
                            {"filename": "host-history-image.png", "type": "output", "subfolder": ""},
                        ]
                    }
                },
                "status": {"status_str": "success", "messages": []},
            },
            "other-client-history": {
                "prompt": (
                    10,
                    "other-client-history",
                    {"1": {"class_type": "SaveImage"}},
                    {"create_time": 113, "rookieui_origin": "rookieui", "client_id": "browser-2"},
                    ["1"],
                    {},
                ),
                "outputs": {},
                "status": {"status_str": "success", "messages": []},
            },
        }


class _FakePromptServer:
    def __init__(self) -> None:
        self.prompt_queue = _FakePromptQueue()

    def get_queue_info(self) -> dict[str, object]:
        return {"exec_info": {"queue_remaining": 99}}


class _FakeJsonRequest:
    def __init__(
        self,
        *,
        query: dict[str, object] | None = None,
        match_info: dict[str, object] | None = None,
    ) -> None:
        self.query = query or {}
        self.match_info = match_info or {}

    async def json(self) -> dict[str, object]:
        return {}


class QueueSnapshotTests(unittest.TestCase):
    def test_build_queue_snapshot_returns_fallback_without_host(self) -> None:
        payload = build_queue_snapshot(None)

        self.assertEqual(payload["source"], "fallback")
        self.assertEqual(payload["queue_remaining"], 0)
        self.assertEqual(payload["contract"]["version"], QUEUE_CONTRACT_VERSION)
        self.assertEqual(payload["jobs"], [])

    def test_build_queue_snapshot_normalizes_running_pending_and_history(self) -> None:
        payload = build_queue_snapshot(_FakePromptServer())

        self.assertEqual(payload["source"], "host")
        self.assertEqual(payload["queue_remaining"], 3)
        self.assertEqual(len(payload["jobs"]), 5)
        self.assertEqual(payload["jobs"][0]["status"], "in_progress")
        self.assertEqual(payload["jobs"][1]["status"], "pending")
        self.assertEqual(payload["jobs"][2]["id"], "other-client-pending")
        history_job = next(job for job in payload["jobs"] if job["id"] == "prompt-history")
        self.assertEqual(history_job["output_filenames"], ["history-image.png"])
        self.assertEqual(history_job["reusable_outputs"], ["history-image.png"])
        job_ids = [job["id"] for job in payload["jobs"]]
        self.assertNotIn("host-canvas-running", job_ids)
        self.assertNotIn("host-canvas-history", job_ids)

    def test_build_queue_snapshot_filters_by_client_id(self) -> None:
        payload = build_queue_snapshot(_FakePromptServer(), client_id="browser-1")

        self.assertEqual(payload["source"], "host")
        self.assertEqual(payload["queue_remaining"], 2)
        self.assertEqual(len(payload["jobs"]), 3)
        job_ids = [job["id"] for job in payload["jobs"]]
        self.assertNotIn("other-client-pending", job_ids)
        self.assertNotIn("other-client-history", job_ids)

    def test_queue_route_returns_snapshot_payload(self) -> None:
        with mock.patch.object(
            routes,
            "_get_prompt_server_for_submission",
            return_value=_FakePromptServer(),
        ):
            response = asyncio.run(routes.queue(_FakeJsonRequest()))

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["status"], "ok")
        self.assertEqual(response["payload"]["contract"]["version"], QUEUE_CONTRACT_VERSION)
        self.assertEqual(response["payload"]["queue_remaining"], 3)
        history_job = next(job for job in response["payload"]["jobs"] if job["id"] == "prompt-history")
        self.assertEqual(history_job["output_filenames"], ["history-image.png"])

    def test_queue_route_applies_client_id_filter(self) -> None:
        with mock.patch.object(
            routes,
            "_get_prompt_server_for_submission",
            return_value=_FakePromptServer(),
        ):
            response = asyncio.run(routes.queue(_FakeJsonRequest(query={"client_id": "browser-1"})))

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["status"], "ok")
        self.assertEqual(response["payload"]["contract"]["version"], QUEUE_CONTRACT_VERSION)
        self.assertEqual(response["payload"]["queue_remaining"], 2)
        job_ids = [job["id"] for job in response["payload"]["jobs"]]
        self.assertNotIn("other-client-pending", job_ids)

    def test_queue_prompt_route_returns_job_payload(self) -> None:
        with mock.patch.object(
            routes,
            "_get_prompt_server_for_submission",
            return_value=_FakePromptServer(),
        ):
            response = asyncio.run(
                routes.queue_prompt(
                    _FakeJsonRequest(
                        query={"client_id": "browser-1"},
                        match_info={"prompt_id": "prompt-history"},
                    )
                )
            )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["status"], "ok")
        self.assertEqual(response["payload"]["contract"]["version"], QUEUE_CONTRACT_VERSION)
        self.assertEqual(response["payload"]["job"]["id"], "prompt-history")
