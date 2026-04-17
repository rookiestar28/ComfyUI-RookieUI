from __future__ import annotations

import asyncio
import unittest
from unittest import mock

from rookieui.api import routes


class _FakeJsonRequest:
    def __init__(
        self,
        payload: dict[str, object] | None = None,
        *,
        query: dict[str, object] | None = None,
        match_info: dict[str, object] | None = None,
    ) -> None:
        self._payload = payload or {}
        self.query: dict[str, object] = query or {}
        self.match_info: dict[str, object] = match_info or {}

    async def json(self) -> dict[str, object]:
        return self._payload


class XYZPlotRouteTests(unittest.TestCase):
    def test_xyz_plot_axes_route_returns_registry_payload(self) -> None:
        response = asyncio.run(routes.xyz_plot_axes(_FakeJsonRequest()))

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["contract"]["surface"], "xyz_plot_axes")
        self.assertIn("steps", response["payload"]["axes"])

    @mock.patch("rookieui.api.routes.build_xyz_plot_estimate_snapshot")
    def test_xyz_plot_estimate_route_returns_estimate_payload(self, mocked_estimate: mock.Mock) -> None:
        mocked_estimate.return_value = {
            "contract": {"surface": "xyz_plot_estimate"},
            "estimate": {"cell_count": 4},
            "can_run": True,
            "warnings": [],
            "warning_codes": [],
        }

        response = asyncio.run(
            routes.xyz_plot_estimate(
                _FakeJsonRequest(
                    {
                        "mode": "txt2img",
                        "axes": [{"axis_id": "steps", "values": "10,20"}],
                    }
                )
            )
        )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["estimate"]["cell_count"], 4)

    @mock.patch("rookieui.api.routes.build_xyz_plot_estimate_snapshot", side_effect=ValueError("bad estimate"))
    def test_xyz_plot_estimate_route_rejects_invalid_requests(self, _: mock.Mock) -> None:
        response = asyncio.run(routes.xyz_plot_estimate(_FakeJsonRequest({"mode": "txt2img"})))

        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"]["status"], "invalid-request")

    @mock.patch("rookieui.api.routes.execute_xyz_plot_run_snapshot")
    def test_xyz_plot_run_route_returns_session_payload(self, mocked_run: mock.Mock) -> None:
        mocked_run.return_value = {
            "contract": {"surface": "xyz_plot_run"},
            "session": {"session_id": "xyz-1", "status": "in_progress"},
        }

        response = asyncio.run(routes.xyz_plot_run(_FakeJsonRequest({"mode": "txt2img"})))

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["session"]["session_id"], "xyz-1")

    @mock.patch("rookieui.api.routes.build_xyz_plot_session_list_snapshot")
    def test_xyz_plot_sessions_route_returns_list_payload(self, mocked_list: mock.Mock) -> None:
        mocked_list.return_value = {
            "contract": {"surface": "xyz_plot_session_list"},
            "sessions": [{"session_id": "xyz-1"}],
        }

        response = asyncio.run(routes.xyz_plot_sessions(_FakeJsonRequest(query={"client_id": "browser-1"})))

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["sessions"][0]["session_id"], "xyz-1")

    def test_xyz_plot_session_detail_route_requires_session_id(self) -> None:
        response = asyncio.run(routes.xyz_plot_session_detail(_FakeJsonRequest()))

        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"]["status"], "invalid-request")

    @mock.patch("rookieui.api.routes.execute_xyz_plot_session_cancel_snapshot")
    def test_xyz_plot_session_cancel_route_returns_payload(self, mocked_cancel: mock.Mock) -> None:
        mocked_cancel.return_value = {
            "contract": {"surface": "xyz_plot_session_cancel"},
            "session": {"session_id": "xyz-1", "cancel_requested": True},
        }

        response = asyncio.run(
            routes.xyz_plot_session_cancel(_FakeJsonRequest(match_info={"session_id": "xyz-1"}))
        )

        self.assertEqual(response["status"], 200)
        self.assertTrue(response["payload"]["session"]["cancel_requested"])
