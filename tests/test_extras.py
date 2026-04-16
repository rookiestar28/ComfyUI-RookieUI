from __future__ import annotations

import asyncio
import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from rookieui.api import routes
from rookieui.contracts.extras import EXTRAS_CONTRACT_VERSION
from rookieui.services import asset_store
from rookieui.services.extras import execute_extras_request, normalize_extras_request


class _FakeJsonRequest:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    async def json(self) -> dict[str, object]:
        return self._payload


class ExtrasTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.runtime_dir.cleanup)
        runtime_root = Path(self.runtime_dir.name)
        self.input_root = runtime_root / "input"
        self.output_root = runtime_root / "output"
        self.input_root.mkdir(parents=True, exist_ok=True)
        self.output_root.mkdir(parents=True, exist_ok=True)

        self.input_patcher = mock.patch.object(asset_store, "_INPUT_ROOT", self.input_root)
        self.output_patcher = mock.patch.object(asset_store, "_OUTPUT_ROOT", self.output_root)
        self.input_patcher.start()
        self.output_patcher.start()
        self.addCleanup(self.input_patcher.stop)
        self.addCleanup(self.output_patcher.stop)

    def _build_image_data_url(self, color: str = "white") -> str:
        image = Image.new("RGB", (64, 64), color=color)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def test_normalize_extras_request_accepts_single_image_upload(self) -> None:
        request = normalize_extras_request(
            {
                "mode": "single_image",
                "image_data": self._build_image_data_url(),
                "scale_by": 2.0,
            }
        )

        self.assertEqual(request.mode, "single_image")
        self.assertEqual(len(request.source_assets), 1)
        self.assertEqual(request.scale_mode, "scale_by")

    def test_normalize_extras_request_accepts_numeric_boolean_payloads(self) -> None:
        request = normalize_extras_request(
            {
                "mode": "single_image",
                "image_data": self._build_image_data_url(),
                "upscale_enabled": 1,
                "color_correction": 0,
            }
        )

        self.assertTrue(request.upscale_enabled)
        self.assertFalse(request.color_correction)

    def test_execute_extras_request_writes_workspace_output(self) -> None:
        normalized = normalize_extras_request(
            {
                "mode": "single_image",
                "image_data": self._build_image_data_url(),
                "scale_mode": "scale_to",
                "target_width": 128,
                "target_height": 96,
                "color_correction": True,
            }
        )

        result = execute_extras_request(normalized).to_payload()

        self.assertEqual(result["mode"], "single_image")
        self.assertEqual(len(result["output_assets"]), 1)
        self.assertTrue(result["preview_asset"].startswith("rookieui_extras_"))
        self.assertTrue(result["preview_data_url"].startswith("data:image/png;base64,"))

    def test_extras_route_returns_execution_payload(self) -> None:
        response = asyncio.run(
            routes.extras_run(
                _FakeJsonRequest(
                    {
                        "mode": "single_image",
                        "image_data": self._build_image_data_url("blue"),
                        "scale_by": 1.5,
                    }
                )
            )
        )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["status"], "ok")
        self.assertEqual(response["payload"]["mode"], "single_image")
        self.assertEqual(response["payload"]["contract"]["version"], EXTRAS_CONTRACT_VERSION)
        self.assertEqual(len(response["payload"]["output_assets"]), 1)

    def test_extras_route_rejects_missing_image(self) -> None:
        response = asyncio.run(routes.extras_run(_FakeJsonRequest({"mode": "single_image"})))

        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"]["status"], "invalid-request")
