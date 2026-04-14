from __future__ import annotations

import types
import unittest
from unittest import mock

from rookieui.contracts.models import ModelInventorySnapshot
from rookieui.services import adetailer_runtime
from rookieui.services.model_inventory import ensure_native_ultralytics_model_paths

try:
    import torch
except Exception:  # pragma: no cover - optional runtime dependency
    torch = None


class ADetailerRuntimeTests(unittest.TestCase):
    def test_ensure_native_ultralytics_model_paths_registers_split_catalogs(self) -> None:
        calls: list[tuple[str, str, bool | None]] = []
        module = types.SimpleNamespace(
            models_dir="C:\\models",
            supported_pt_extensions={".pt", ".pth", ".safetensors"},
            folder_names_and_paths={},
        )

        def _add_model_folder_path(folder_name: str, full_folder_path: str, is_default: bool = False) -> None:
            calls.append((folder_name, full_folder_path, is_default))
            module.folder_names_and_paths.setdefault(folder_name, ([full_folder_path], set()))

        module.add_model_folder_path = _add_model_folder_path

        ensure_native_ultralytics_model_paths(module)

        self.assertIn(("ultralytics", "C:\\models\\ultralytics", True), calls)
        self.assertIn(("ultralytics_bbox", "C:\\models\\ultralytics\\bbox", True), calls)
        self.assertIn(("ultralytics_segm", "C:\\models\\ultralytics\\segm", True), calls)
        self.assertEqual(module.folder_names_and_paths["ultralytics_bbox"][1], {".pt", ".pth", ".safetensors"})

    def test_build_detector_runtime_availability_reports_dependency_missing_without_optional_packages(self) -> None:
        inventory = ModelInventorySnapshot(
            source="host",
            ultralytics_bbox=["face_yolov8n.pt"],
            ultralytics_segm=["person_yolov8m-seg.pt"],
        )
        with mock.patch("rookieui.services.adetailer_runtime.discover_model_inventory", return_value=inventory):
            with mock.patch("rookieui.services.adetailer_runtime._import_optional_module", return_value=None):
                availability = adetailer_runtime.build_detector_runtime_availability()

        self.assertEqual(availability["none"], "disabled")
        self.assertEqual(availability["ultralytics_bbox"], "native_runtime_dependency_missing")
        self.assertEqual(availability["ultralytics_segm"], "native_runtime_dependency_missing")
        self.assertEqual(availability["mediapipe_face"], "native_runtime_dependency_missing")

    @unittest.skipIf(torch is None, "torch is unavailable in this environment")
    def test_detect_adetailer_mask_falls_back_when_runtime_is_unavailable(self) -> None:
        image = torch.zeros((1, 32, 32, 3), dtype=torch.float32)

        result = adetailer_runtime.detect_adetailer_mask(
            image,
            detector="face_yolov8n.pt",
            detector_family="ultralytics_bbox",
            detector_classes="",
            confidence=0.4,
            x_offset=0,
            y_offset=0,
        )

        self.assertTrue(result.used_fallback)
        self.assertEqual(result.runtime_state, "deterministic_mask_fallback")
        self.assertGreater(float(result.mask.mean().item()), 0.0)

    @unittest.skipIf(torch is None, "torch is unavailable in this environment")
    def test_detect_adetailer_mask_uses_ultralytics_bbox_runtime_when_available(self) -> None:
        image = torch.zeros((1, 32, 32, 3), dtype=torch.float32)

        box = types.SimpleNamespace(
            xyxy=torch.tensor([[4.0, 5.0, 20.0, 24.0]], dtype=torch.float32),
            cls=torch.tensor([0], dtype=torch.float32),
            conf=torch.tensor([0.92], dtype=torch.float32),
        )
        runtime_result = types.SimpleNamespace(
            boxes=[box],
            masks=None,
            names={0: "face"},
        )

        class _FakeModel:
            def __call__(self, *_args, **_kwargs):
                return [runtime_result]

        with mock.patch(
            "rookieui.services.adetailer_runtime.build_detector_runtime_availability",
            return_value={
                "none": "disabled",
                "ultralytics_bbox": "native_runtime_ready",
                "ultralytics_segm": "native_runtime_model_unavailable",
                "mediapipe_face": "native_runtime_dependency_missing",
            },
        ):
            with mock.patch("rookieui.services.adetailer_runtime._resolve_ultralytics_model_path", return_value="C:\\models\\face.pt"):
                with mock.patch("rookieui.services.adetailer_runtime._load_ultralytics_model", return_value=_FakeModel()):
                    result = adetailer_runtime.detect_adetailer_mask(
                        image,
                        detector="face_yolov8n.pt",
                        detector_family="ultralytics_bbox",
                        detector_classes="face",
                        confidence=0.4,
                        x_offset=0,
                        y_offset=0,
                    )

        self.assertFalse(result.used_fallback)
        self.assertEqual(result.runtime_state, "native_runtime_ready")
        self.assertGreater(float(result.mask.sum().item()), 0.0)
