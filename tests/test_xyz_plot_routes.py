from __future__ import annotations

import asyncio
import unittest
from unittest import mock

from rookieui.api import routes


class _FakeJsonRequest:
    def __init__(self, payload: dict[str, object] | None = None) -> None:
        self._payload = payload or {}
        self.query: dict[str, object] = {}

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
