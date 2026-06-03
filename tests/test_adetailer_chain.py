from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from unittest import mock

from rookieui.api import routes


class _FakeJsonRequest:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    async def json(self) -> dict[str, object]:
        return self._payload


class ADetailerChainRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._asset_path_patcher = mock.patch(
            "rookieui.services.controlnet.resolve_asset_path",
            return_value=Path(__file__),
        )
        self._asset_path_patcher.start()

    def tearDown(self) -> None:
        self._asset_path_patcher.stop()

    def test_txt2img_dry_run_emits_adetailer_runtime_chain_with_passthrough_controlnet(self) -> None:
        response = asyncio.run(
            routes.txt2img(
                _FakeJsonRequest(
                    {
                        "prompt": "portrait",
                        "negative_prompt": "blur",
                        "dry_run": True,
                        "controlnet_units": [
                            {
                                "enabled": True,
                                "module": "canny",
                                "model": "control_v11p_sd15_canny.safetensors",
                                "image_asset": "source-image",
                            }
                        ],
                        "adetailer": {
                            "enabled": True,
                            "units": [
                                {
                                    "enabled": True,
                                    "detector": "face_yolov8n.pt",
                                    "prompt": "face [PROMPT]",
                                    "controlnet": {"mode": "passthrough"},
                                }
                            ],
                        },
                    }
                )
            )
        )

        self.assertEqual(response["status"], 200)
        payload = response["payload"]
        workflow = payload["workflow"]
        class_types = [node["class_type"] for node in workflow.values()]
        self.assertIn("RookieUIADetailerDetectMask", class_types)
        self.assertIn("RookieUIVAEEncodeForInpaint", class_types)
        self.assertEqual(class_types.count("RookieUIControlNetApplyNativeAdvanced"), 2)
        self.assertEqual(class_types.count("KSampler"), 2)
        self.assertIn(
            "ADETAILER_DETECTOR_RUNTIME_FALLBACK_MASK",
            payload["normalized_request"]["adetailer"]["warning_codes"],
        )
        self.assertEqual(payload["normalized_request"]["adetailer"]["diagnostics"]["primary_controlnet_unit_count"], 1)
        save_node = next(node for node in workflow.values() if node["class_type"] == "RookieUISaveImageWithMetadata")
        final_decode_id = [node_id for node_id, node in workflow.items() if node["class_type"] == "VAEDecode"][-1]
        self.assertEqual(save_node["inputs"]["images"], [final_decode_id, 0])

    def test_txt2img_dry_run_keeps_base_graph_clean_when_adetailer_disabled(self) -> None:
        response = asyncio.run(
            routes.txt2img(
                _FakeJsonRequest(
                    {
                        "prompt": "portrait",
                        "dry_run": True,
                        "adetailer": {
                            "enabled": False,
                            "units": [{"enabled": True, "detector": "face_yolov8n.pt"}],
                        },
                    }
                )
            )
        )

        self.assertEqual(response["status"], 200)
        workflow = response["payload"]["workflow"]
        class_types = [node["class_type"] for node in workflow.values()]
        self.assertNotIn("RookieUIADetailerDetectMask", class_types)
        self.assertNotIn("RookieUIVAEEncodeForInpaint", class_types)
        self.assertEqual(class_types.count("KSampler"), 1)
        self.assertEqual(response["payload"]["normalized_request"]["adetailer"]["diagnostics"]["active_unit_count"], 0)

    def test_txt2img_dry_run_rolls_back_adetailer_local_controlnet_when_advanced_keyframes_collapse(self) -> None:
        response = asyncio.run(
            routes.txt2img(
                _FakeJsonRequest(
                    {
                        "prompt": "portrait",
                        "negative_prompt": "blur",
                        "dry_run": True,
                        "adetailer": {
                            "enabled": True,
                            "units": [
                                {
                                    "enabled": True,
                                    "detector": "face_yolov8n.pt",
                                    "prompt": "face [PROMPT]",
                                    "controlnet": {
                                        "mode": "custom",
                                        "model": "control_v11f1p_sd15_depth.safetensors",
                                        "module": "depth",
                                        "weight": 0.6,
                                        "guidance_start": 0.15,
                                        "guidance_end": 0.65,
                                        "advanced": {
                                            "enabled": True,
                                            "weight_preset": "soft",
                                            "timestep_keyframes": [
                                                {"start_percent": 0.0, "end_percent": 0.1, "strength_scale": 1.0},
                                                {"start_percent": 0.9, "end_percent": 1.0, "strength_scale": 0.0},
                                            ],
                                        },
                                    },
                                }
                            ],
                        },
                    }
                )
            )
        )

        self.assertEqual(response["status"], 200)
        workflow = response["payload"]["workflow"]
        apply_nodes = [
            node for node in workflow.values() if node["class_type"] == "RookieUIControlNetApplyNativeAdvanced"
        ]
        self.assertEqual(len(apply_nodes), 1)
        self.assertEqual(apply_nodes[0]["inputs"]["strength"], 0.6)
        self.assertEqual(apply_nodes[0]["inputs"]["start_percent"], 0.15)
        self.assertEqual(apply_nodes[0]["inputs"]["end_percent"], 0.65)
        self.assertEqual(apply_nodes[0]["inputs"]["weight_preset"], "soft")
        self.assertIn("RookieUIADetailerDetectMask", [node["class_type"] for node in workflow.values()])


if __name__ == "__main__":
    unittest.main()
