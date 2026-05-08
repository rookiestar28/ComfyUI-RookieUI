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


class _FakeUpscalerBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[int, int], tuple[int, int]]] = []

    def upscale(self, image: Image.Image, model_name: str, target_size: tuple[int, int]) -> Image.Image:
        self.calls.append((model_name, image.size, target_size))
        color = "red" if model_name == "model-a.pth" else "blue"
        return Image.new("RGB", target_size, color=color)


class _FakeFaceRestorationBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, float, tuple[int, int]]] = []

    def restore(self, image: Image.Image, method: str, codeformer_weight: float) -> tuple[Image.Image, int]:
        self.calls.append((method, codeformer_weight, image.size))
        return Image.new("RGB", image.size, color="green"), 1


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

    def test_execute_extras_request_invokes_selected_upscaler_backend(self) -> None:
        backend = _FakeUpscalerBackend()
        normalized = normalize_extras_request(
            {
                "mode": "single_image",
                "image_data": self._build_image_data_url("white"),
                "scale_mode": "scale_to",
                "target_width": 128,
                "target_height": 96,
                "upscaler_1": "model-a.pth",
                "upscaler_2": "None",
            }
        )

        result = execute_extras_request(normalized, upscaler_backend=backend).to_payload()
        output_path = asset_store.resolve_asset_path(result["output_assets"][0])
        with Image.open(output_path) as output_image:
            output_size = output_image.size
            output_pixel = output_image.getpixel((0, 0))

        self.assertEqual(backend.calls, [("model-a.pth", (64, 64), (128, 96))])
        self.assertEqual(output_size, (128, 96))
        self.assertEqual(output_pixel, (255, 0, 0))
        self.assertFalse(any("PIL" in warning for warning in result["warnings"]))

    def test_execute_extras_request_blends_second_upscaler_by_visibility(self) -> None:
        backend = _FakeUpscalerBackend()
        normalized = normalize_extras_request(
            {
                "mode": "single_image",
                "image_data": self._build_image_data_url("white"),
                "scale_mode": "scale_to",
                "target_width": 128,
                "target_height": 96,
                "upscaler_1": "model-a.pth",
                "upscaler_2": "model-b.pth",
                "upscaler_2_visibility": 0.25,
            }
        )

        result = execute_extras_request(normalized, upscaler_backend=backend).to_payload()
        output_path = asset_store.resolve_asset_path(result["output_assets"][0])
        with Image.open(output_path) as output_image:
            output_size = output_image.size
            output_pixel = output_image.getpixel((0, 0))

        self.assertEqual(
            backend.calls,
            [
                ("model-a.pth", (64, 64), (128, 96)),
                ("model-b.pth", (64, 64), (128, 96)),
            ],
        )
        self.assertEqual(output_size, (128, 96))
        self.assertEqual(output_pixel, (191, 0, 63))

    def test_execute_extras_request_reports_pil_fallback_when_selected_upscaler_has_no_backend(self) -> None:
        normalized = normalize_extras_request(
            {
                "mode": "single_image",
                "image_data": self._build_image_data_url("white"),
                "scale_mode": "scale_to",
                "target_width": 128,
                "target_height": 96,
                "upscaler_1": "model-a.pth",
            }
        )

        result = execute_extras_request(normalized).to_payload()
        output_path = asset_store.resolve_asset_path(result["output_assets"][0])
        with Image.open(output_path) as output_image:
            output_size = output_image.size

        self.assertEqual(output_size, (128, 96))
        self.assertTrue(any("PIL" in warning and "model-a.pth" in warning for warning in result["warnings"]))

    def test_normalize_extras_request_keeps_face_restoration_runtime_pending(self) -> None:
        normalized = normalize_extras_request(
            {
                "mode": "single_image",
                "image_data": self._build_image_data_url("white"),
                "face_restoration": "CodeFormer",
            }
        )

        self.assertEqual(normalized.face_restoration, "codeformer")
        self.assertFalse(any("not available" in warning for warning in normalized.warnings))

    def test_execute_extras_request_invokes_face_restoration_backend(self) -> None:
        face_backend = _FakeFaceRestorationBackend()
        normalized = normalize_extras_request(
            {
                "mode": "single_image",
                "image_data": self._build_image_data_url("white"),
                "scale_mode": "scale_to",
                "target_width": 64,
                "target_height": 64,
                "face_restoration": "codeformer",
                "codeformer_weight": 0.75,
            }
        )

        result = execute_extras_request(normalized, face_restoration_backend=face_backend).to_payload()
        output_path = asset_store.resolve_asset_path(result["output_assets"][0])
        with Image.open(output_path) as output_image:
            output_pixel = output_image.getpixel((0, 0))

        self.assertEqual(face_backend.calls, [("codeformer", 0.75, (64, 64))])
        self.assertEqual(output_pixel, (0, 128, 0))
        self.assertFalse(any("not available" in warning for warning in result["warnings"]))
        self.assertEqual(result["diagnostics"][0]["face_restoration"], "codeformer")
        self.assertEqual(result["diagnostics"][0]["restored_faces"], 1)

    def test_execute_extras_request_reports_face_restoration_unavailable_without_backend(self) -> None:
        normalized = normalize_extras_request(
            {
                "mode": "single_image",
                "image_data": self._build_image_data_url("white"),
                "face_restoration": "gfpgan",
            }
        )

        result = execute_extras_request(normalized).to_payload()

        self.assertTrue(any("gfpgan" in warning and "unavailable" in warning for warning in result["warnings"]))
        self.assertEqual(result["diagnostics"][0]["face_restoration"], "gfpgan")
        self.assertEqual(result["diagnostics"][0]["restored_faces"], 0)

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
