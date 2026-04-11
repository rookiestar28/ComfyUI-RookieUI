from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from unittest import mock

from rookieui.api import routes
from rookieui.services.controlnet import (
    CONTROLNET_WARNING_ALIAS_NATIVE_OVERRIDE,
    CONTROLNET_WARNING_FEATURE_DISABLED,
    build_controlnet_detect_payload,
    normalize_controlnet_units,
)
from rookieui.services.img2img import normalize_img2img_request
from rookieui.services.txt2img import normalize_txt2img_request
from rookieui.services.workflow_translation import translate_img2img_request, translate_txt2img_request


class _FakeJsonRequest:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    async def json(self) -> dict[str, object]:
        return self._payload


class ControlNetNormalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._asset_path_patcher = mock.patch(
            "rookieui.services.controlnet.resolve_asset_path",
            return_value=Path(__file__),
        )
        self._asset_path_patcher.start()
        self._img_asset_path_patcher = mock.patch(
            "rookieui.services.img2img.resolve_asset_path",
            return_value=Path(__file__),
        )
        self._img_asset_path_patcher.start()

    def tearDown(self) -> None:
        self._asset_path_patcher.stop()
        self._img_asset_path_patcher.stop()

    def test_txt2img_normalization_accepts_native_controlnet_units(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "controlnet_units": [
                    {
                        "enabled": True,
                        "module": "canny",
                        "model": "control_v11p_sd15_canny.safetensors",
                        "weight": 0.85,
                        "guidance_start": 0.1,
                        "guidance_end": 0.9,
                        "image_asset": "source-image",
                    }
                ],
            }
        )

        self.assertEqual(len(request.controlnet_units), 1)
        unit = request.controlnet_units[0]
        self.assertTrue(unit.enabled)
        self.assertEqual(unit.module, "canny")
        self.assertEqual(unit.model, "control_v11p_sd15_canny.safetensors")
        self.assertEqual(unit.weight, 0.85)
        self.assertEqual(unit.guidance_start, 0.1)
        self.assertEqual(unit.guidance_end, 0.9)
        self.assertEqual(unit.image_asset, "source-image")

    def test_txt2img_normalization_maps_a1111_alias_payload(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "alwayson_scripts": {
                    "ControlNet": {
                        "args": [
                            {
                                "enabled": True,
                                "module": "canny",
                                "model": "control_v11p_sd15_canny.safetensors",
                                "weight": 1.0,
                                "image": "alias-image",
                            }
                        ]
                    }
                },
            }
        )

        self.assertEqual(len(request.controlnet_units), 1)
        self.assertEqual(request.controlnet_units[0].source, "alwayson_scripts.controlnet")
        self.assertEqual(request.controlnet_units[0].image_asset, "alias-image")

    def test_controlnet_normalization_prefers_native_units_over_alias_units(self) -> None:
        units, warning_codes, _ = normalize_controlnet_units(
            {
                "controlnet_units": [
                    {"enabled": True, "model": "control_v11p_sd15_canny.safetensors", "image_asset": "native-image"}
                ],
                "alwayson_scripts": {
                    "controlnet": {
                        "args": [
                            {"enabled": True, "model": "control_v11p_sd15_depth.safetensors", "image": "alias-image"}
                        ]
                    }
                },
            },
            inventory_models=["control_v11p_sd15_canny.safetensors", "control_v11p_sd15_depth.safetensors"],
            strict_model_match=True,
        )

        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].image_asset, "native-image")
        self.assertIn(CONTROLNET_WARNING_ALIAS_NATIVE_OVERRIDE, warning_codes)

    def test_controlnet_normalization_honors_feature_flag_disable(self) -> None:
        with mock.patch.dict("os.environ", {"ROOKIEUI_CONTROLNET_ENABLED": "0"}, clear=False):
            units, warning_codes, warnings = normalize_controlnet_units(
                {
                    "controlnet_units": [
                        {
                            "enabled": True,
                            "model": "control_v11p_sd15_canny.safetensors",
                            "image_asset": "source-image",
                        }
                    ]
                },
                inventory_models=["control_v11p_sd15_canny.safetensors"],
                strict_model_match=True,
            )

        self.assertEqual(units, [])
        self.assertIn(CONTROLNET_WARNING_FEATURE_DISABLED, warning_codes)
        self.assertTrue(any("disabled" in warning.lower() for warning in warnings))

    def test_img2img_controlnet_unit_reuses_main_source_when_unit_source_missing(self) -> None:
        request = normalize_img2img_request(
            {
                "prompt": "portrait cleanup",
                "image_asset": "portrait-input",
                "controlnet_units": [
                    {
                        "enabled": True,
                        "model": "control_v11p_sd15_canny.safetensors",
                    }
                ],
            }
        )

        self.assertEqual(len(request.controlnet_units), 1)
        self.assertEqual(request.controlnet_units[0].image_asset, "portrait-input")


class ControlNetWorkflowTranslationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._asset_path_patcher = mock.patch(
            "rookieui.services.controlnet.resolve_asset_path",
            return_value=Path(__file__),
        )
        self._asset_path_patcher.start()
        self._img_asset_path_patcher = mock.patch(
            "rookieui.services.img2img.resolve_asset_path",
            return_value=Path(__file__),
        )
        self._img_asset_path_patcher.start()

    def tearDown(self) -> None:
        self._asset_path_patcher.stop()
        self._img_asset_path_patcher.stop()

    def test_txt2img_translation_inserts_controlnet_nodes(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "controlnet_units": [
                    {
                        "enabled": True,
                        "module": "canny",
                        "model": "control_v11p_sd15_canny.safetensors",
                        "image_asset": "source-image",
                        "guidance_start": 0.2,
                        "guidance_end": 0.8,
                    }
                ],
            }
        )

        payload = translate_txt2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in payload["workflow"].values()}

        self.assertIn("DiffControlNetLoader", class_types)
        self.assertIn("ControlNetApplyAdvanced", class_types)
        controlnet_apply = [node for node in payload["workflow"].values() if node["class_type"] == "ControlNetApplyAdvanced"]
        self.assertEqual(len(controlnet_apply), 1)
        self.assertEqual(controlnet_apply[0]["inputs"]["start_percent"], 0.2)
        self.assertEqual(controlnet_apply[0]["inputs"]["end_percent"], 0.8)

    def test_img2img_translation_keeps_base_graph_when_no_controlnet_units(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait cleanup",
                "image_asset": "portrait-input",
            }
        )
        payload = translate_img2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in payload["workflow"].values()}
        self.assertNotIn("ControlNetApplyAdvanced", class_types)


class ControlNetRouteTests(unittest.TestCase):
    def test_bootstrap_routes_include_controlnet_surface(self) -> None:
        payload = routes.build_bootstrap_payload()
        self.assertIn("/rookieui/controlnet/model_list", payload["routes"])
        self.assertIn("/rookieui/controlnet/module_list", payload["routes"])
        self.assertIn("/rookieui/controlnet/control_types", payload["routes"])
        self.assertIn("/rookieui/controlnet/detect", payload["routes"])

    def test_controlnet_route_handlers_return_payloads(self) -> None:
        model_list = asyncio.run(routes.controlnet_model_list(None))
        module_list = asyncio.run(routes.controlnet_module_list(None))
        control_types = asyncio.run(routes.controlnet_control_types(None))
        detect = asyncio.run(
            routes.controlnet_detect(_FakeJsonRequest({"controlnet_module": "none", "image": "data:image/png;base64,ZmFrZQ=="}))
        )

        self.assertEqual(model_list["status"], 200)
        self.assertEqual(module_list["status"], 200)
        self.assertEqual(control_types["status"], 200)
        self.assertEqual(detect["status"], 200)
        self.assertIn("model_list", model_list["payload"])
        self.assertIn("module_list", module_list["payload"])
        self.assertIn("control_types", control_types["payload"])
        self.assertIn("images", detect["payload"])

    def test_detect_payload_supports_passthrough_none_module(self) -> None:
        payload = build_controlnet_detect_payload(
            {
                "controlnet_module": "none",
                "controlnet_input_images": ["data:image/png;base64,ZmFrZQ=="],
            }
        )
        self.assertEqual(payload["module"], "none")
        self.assertEqual(len(payload["images"]), 1)
