from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from unittest import mock

from rookieui.api import routes
from rookieui.contracts.controlnet_integrated import (
    CONTROLNET_INTEGRATED_CONTRACT_VERSION,
    CONTROLNET_INTEGRATED_UI_VARIANT,
)
from rookieui.services.controlnet import (
    CONTROLNET_WARNING_ALIAS_NATIVE_OVERRIDE,
    CONTROLNET_WARNING_PREPROCESSOR_EMPTY_OUTPUT,
    CONTROLNET_WARNING_FEATURE_DISABLED,
    CONTROLNET_WARNING_PREPROCESSOR_HOST_FALLBACK,
    CONTROLNET_WARNING_PREPROCESSOR_UNAVAILABLE,
    build_controlnet_control_types_payload,
    build_controlnet_detect_payload,
    build_controlnet_model_list_payload,
    build_controlnet_module_list_payload,
    normalize_controlnet_units,
)
from rookieui.services.controlnet_runtime import ControlNetRuntimeResult
from rookieui.services.controlnet_advanced_runtime import CONTROLNET_ADVANCED_RUNTIME_STATE
from rookieui.services.img2img import normalize_img2img_request
from rookieui.services.txt2img import normalize_txt2img_request
from rookieui.services.workflow_translation import translate_img2img_request, translate_txt2img_request


VALID_PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

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

    def test_txt2img_normalization_maps_a1111_alias_input_image_mask_payload(self) -> None:
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
                                "input_image": {
                                    "image": "alias-image",
                                    "mask": "alias-mask",
                                },
                            }
                        ]
                    }
                },
            }
        )

        self.assertEqual(len(request.controlnet_units), 1)
        self.assertEqual(request.controlnet_units[0].source, "alwayson_scripts.controlnet")
        self.assertEqual(request.controlnet_units[0].image_asset, "alias-image")
        self.assertEqual(request.controlnet_units[0].mask_asset, "alias-mask")
        self.assertTrue(request.controlnet_units[0].use_mask)

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

    def test_controlnet_normalization_enables_legacy_mask_asset_without_use_mask_flag(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "controlnet_units": [
                    {
                        "enabled": True,
                        "model": "control_v11p_sd15_canny.safetensors",
                        "image_asset": "source-image",
                        "mask_asset": "mask-image",
                    }
                ],
            }
        )

        self.assertEqual(len(request.controlnet_units), 1)
        self.assertTrue(request.controlnet_units[0].use_mask)

    def test_controlnet_normalization_respects_explicit_use_mask_false(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "controlnet_units": [
                    {
                        "enabled": True,
                        "model": "control_v11p_sd15_canny.safetensors",
                        "image_asset": "source-image",
                        "mask_asset": "mask-image",
                        "use_mask": False,
                    }
                ],
            }
        )

        self.assertEqual(len(request.controlnet_units), 1)
        self.assertFalse(request.controlnet_units[0].use_mask)

    def test_controlnet_normalization_maps_control_type_alias_and_fallback(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "controlnet_units": [
                    {
                        "enabled": True,
                        "model": "control_v11p_sd15_canny.safetensors",
                        "image_asset": "source-image",
                        "control_type": "ipadapter",
                    },
                    {
                        "enabled": True,
                        "model": "control_v11p_sd15_canny.safetensors",
                        "image_asset": "source-image-2",
                        "control_type": "not-a-real-type",
                    },
                ],
            }
        )

        self.assertEqual(len(request.controlnet_units), 2)
        self.assertEqual(request.controlnet_units[0].control_type, "IP-Adapter")
        self.assertEqual(request.controlnet_units[1].control_type, "All")

    def test_controlnet_normalization_accepts_reserved_advanced_block(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "controlnet_units": [
                    {
                        "enabled": True,
                        "model": "control_v11p_sd15_canny.safetensors",
                        "image_asset": "source-image",
                        "advanced": {
                            "enabled": True,
                            "weight_preset": "soft",
                            "layer_weights": [0.25, 0.5, 0.75],
                            "timestep_keyframes": [
                                {"start_percent": 0.0, "end_percent": 0.5, "strength_scale": 0.8},
                                {"start_percent": 0.5, "end_percent": 1.0, "strength_scale": 1.2},
                            ],
                            "mask_aware_apply": True,
                        },
                    }
                ],
            }
        )

        unit = request.controlnet_units[0]
        self.assertTrue(unit.advanced.enabled)
        self.assertEqual(unit.advanced.weight_preset, "soft")
        self.assertEqual(unit.advanced.layer_weights, [0.25, 0.5, 0.75])
        self.assertEqual(len(unit.advanced.timestep_keyframes), 2)
        self.assertTrue(unit.advanced.mask_aware_apply)

    def test_controlnet_normalization_strict_match_rejects_preprocessor_weight_from_model_selector(self) -> None:
        with self.assertRaisesRegex(ValueError, "must match a host inventory entry"):
            normalize_controlnet_units(
                {
                    "controlnet_units": [
                        {
                            "enabled": True,
                            "module": "depth",
                            "model": "depth_anything_v2_vitl.pth",
                            "image_asset": "source-image",
                        }
                    ]
                },
                inventory_models=[
                    "Xinsir-Controlnet-depth-sdxl.safetensors",
                    "depth_anything_v2_vitl.pth",
                ],
                strict_model_match=True,
            )


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
        self.assertIn("RookieUIControlNetApplyNativeAdvanced", class_types)
        controlnet_apply = [
            node for node in payload["workflow"].values() if node["class_type"] == "RookieUIControlNetApplyNativeAdvanced"
        ]
        self.assertEqual(len(controlnet_apply), 1)
        self.assertEqual(controlnet_apply[0]["inputs"]["start_percent"], 0.2)
        self.assertEqual(controlnet_apply[0]["inputs"]["end_percent"], 0.8)

    def test_txt2img_translation_wires_controlnet_preprocess_and_mask(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "controlnet_units": [
                    {
                        "enabled": True,
                        "module": "depth",
                        "model": "control_v11f1p_sd15_depth.safetensors",
                        "image_asset": "source-image",
                        "mask_asset": "mask-image",
                        "use_mask": True,
                        "processor_res": 640,
                        "threshold_a": 32,
                        "threshold_b": 16,
                    }
                ],
            }
        )

        payload = translate_txt2img_request(normalized).to_payload()
        workflow = payload["workflow"]
        preprocess_node_id = next(
            node_id for node_id, node in workflow.items() if node["class_type"] == "RookieUIControlNetPreprocess"
        )
        preprocess_node = workflow[preprocess_node_id]
        self.assertEqual(preprocess_node["inputs"]["module"], "depth")
        self.assertEqual(preprocess_node["inputs"]["processor_res"], 640)
        self.assertFalse(preprocess_node["inputs"]["pixel_perfect"])
        self.assertEqual(preprocess_node["inputs"]["target_width"], normalized.width)
        self.assertEqual(preprocess_node["inputs"]["target_height"], normalized.height)
        self.assertTrue(preprocess_node["inputs"]["use_mask"])
        self.assertIn("mask", preprocess_node["inputs"])

        mask_node = next(node for node in workflow.values() if node["class_type"] == "RookieUILoadAssetMask")
        self.assertEqual(mask_node["inputs"]["asset_handle"], "mask-image")

        apply_node = next(
            node for node in workflow.values() if node["class_type"] == "RookieUIControlNetApplyNativeAdvanced"
        )
        self.assertEqual(apply_node["inputs"]["image"], [preprocess_node_id, 0])
        self.assertEqual(apply_node["inputs"]["weight_preset"], "balanced")
        self.assertEqual(apply_node["inputs"]["layer_weights_json"], "[]")

    def test_txt2img_translation_preserves_zero_valid_controlnet_numeric_boundaries(self) -> None:
        scenarios = (
            (
                "zero",
                {
                    "weight": 0.0,
                    "guidance_start": 0.0,
                    "guidance_end": 0.0,
                    "threshold_a": 0.0,
                    "threshold_b": 0.0,
                },
                (0.0, 0.0, 0.0, 0.0, 0.0),
            ),
            (
                "minimum_positive",
                {
                    "weight": 0.001,
                    "guidance_start": 0.0001,
                    "guidance_end": 0.0001,
                    "threshold_a": 0.001,
                    "threshold_b": 0.001,
                },
                (0.001, 0.0001, 0.0001, 0.001, 0.001),
            ),
            ("missing_defaults", {}, (1.0, 0.0, 1.0, 64.0, 64.0)),
            (
                "maximum",
                {
                    "weight": 2.0,
                    "guidance_start": 1.0,
                    "guidance_end": 1.0,
                    "threshold_a": 255.0,
                    "threshold_b": 255.0,
                },
                (2.0, 1.0, 1.0, 255.0, 255.0),
            ),
        )

        for label, numeric_inputs, expected in scenarios:
            with self.subTest(label=label):
                normalized = normalize_txt2img_request(
                    {
                        "prompt": "city skyline",
                        "controlnet_units": [
                            {
                                "enabled": True,
                                "module": "canny",
                                "model": "control_v11p_sd15_canny.safetensors",
                                "image_asset": "source-image",
                                **numeric_inputs,
                            }
                        ],
                    }
                )
                payload = translate_txt2img_request(normalized).to_payload()
                preprocess_node = next(
                    node
                    for node in payload["workflow"].values()
                    if node["class_type"] == "RookieUIControlNetPreprocess"
                )
                apply_node = next(
                    node
                    for node in payload["workflow"].values()
                    if node["class_type"] == "RookieUIControlNetApplyNativeAdvanced"
                )
                unit_metadata = payload["normalized_request"]["controlnet_units"][0]
                expected_weight, expected_start, expected_end, expected_a, expected_b = expected

                self.assertEqual(apply_node["inputs"]["strength"], expected_weight)
                self.assertEqual(apply_node["inputs"]["start_percent"], expected_start)
                self.assertEqual(apply_node["inputs"]["end_percent"], expected_end)
                self.assertEqual(preprocess_node["inputs"]["threshold_a"], expected_a)
                self.assertEqual(preprocess_node["inputs"]["threshold_b"], expected_b)
                self.assertEqual(unit_metadata["weight"], expected_weight)
                self.assertEqual(unit_metadata["guidance_start"], expected_start)
                self.assertEqual(unit_metadata["guidance_end"], expected_end)
                self.assertEqual(unit_metadata["threshold_a"], expected_a)
                self.assertEqual(unit_metadata["threshold_b"], expected_b)

    def test_txt2img_translation_passes_controlnet_pixel_perfect_to_preprocess_node(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "width": 768,
                "height": 512,
                "controlnet_units": [
                    {
                        "enabled": True,
                        "module": "canny",
                        "model": "control_v11p_sd15_canny.safetensors",
                        "image_asset": "source-image",
                        "pixel_perfect": True,
                        "resize_mode": "resize_and_fill",
                        "processor_res": 320,
                    }
                ],
            }
        )

        workflow = translate_txt2img_request(normalized).to_payload()["workflow"]
        preprocess_node = next(node for node in workflow.values() if node["class_type"] == "RookieUIControlNetPreprocess")

        self.assertTrue(preprocess_node["inputs"]["pixel_perfect"])
        self.assertEqual(preprocess_node["inputs"]["target_width"], 768)
        self.assertEqual(preprocess_node["inputs"]["target_height"], 512)
        self.assertEqual(preprocess_node["inputs"]["resize_mode"], "resize_and_fill")

    def test_txt2img_translation_does_not_wire_mask_when_use_mask_disabled(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "controlnet_units": [
                    {
                        "enabled": True,
                        "module": "depth",
                        "model": "control_v11f1p_sd15_depth.safetensors",
                        "image_asset": "source-image",
                        "mask_asset": "mask-image",
                        "use_mask": False,
                    }
                ],
            }
        )

        payload = translate_txt2img_request(normalized).to_payload()
        workflow = payload["workflow"]
        preprocess_node = next(node for node in workflow.values() if node["class_type"] == "RookieUIControlNetPreprocess")
        self.assertFalse(preprocess_node["inputs"]["use_mask"])
        self.assertNotIn("mask", preprocess_node["inputs"])
        self.assertFalse(any(node["class_type"] == "RookieUILoadAssetMask" for node in workflow.values()))

    def test_txt2img_translation_splits_advanced_timestep_keyframes_into_native_apply_nodes(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "controlnet_units": [
                    {
                        "enabled": True,
                        "module": "canny",
                        "model": "control_v11p_sd15_canny.safetensors",
                        "image_asset": "source-image",
                        "weight": 0.75,
                        "guidance_start": 0.1,
                        "guidance_end": 0.9,
                        "advanced": {
                            "enabled": True,
                            "weight_preset": "soft",
                            "layer_weights": [0.2, 0.4, 0.8],
                            "timestep_keyframes": [
                                {"start_percent": 0.0, "end_percent": 0.5, "strength_scale": 0.5},
                                {"start_percent": 0.5, "end_percent": 1.0, "strength_scale": 1.25},
                            ],
                        },
                    }
                ],
            }
        )

        workflow = translate_txt2img_request(normalized).to_payload()["workflow"]
        apply_nodes = [
            node for node in workflow.values() if node["class_type"] == "RookieUIControlNetApplyNativeAdvanced"
        ]

        self.assertEqual(len(apply_nodes), 2)
        self.assertEqual(apply_nodes[0]["inputs"]["start_percent"], 0.1)
        self.assertEqual(apply_nodes[0]["inputs"]["end_percent"], 0.5)
        self.assertEqual(apply_nodes[0]["inputs"]["strength"], 0.375)
        self.assertEqual(apply_nodes[1]["inputs"]["start_percent"], 0.5)
        self.assertEqual(apply_nodes[1]["inputs"]["end_percent"], 0.9)
        self.assertEqual(apply_nodes[1]["inputs"]["strength"], 0.9375)
        self.assertEqual(apply_nodes[0]["inputs"]["weight_preset"], "soft")
        self.assertEqual(apply_nodes[0]["inputs"]["layer_weights_json"], "[0.2, 0.4, 0.8]")

    def test_txt2img_translation_keeps_mask_for_mask_aware_apply_without_preprocess_masking(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "controlnet_units": [
                    {
                        "enabled": True,
                        "module": "depth",
                        "model": "control_v11f1p_sd15_depth.safetensors",
                        "image_asset": "source-image",
                        "mask_asset": "mask-image",
                        "use_mask": False,
                        "advanced": {
                            "enabled": True,
                            "mask_aware_apply": True,
                        },
                    }
                ],
            }
        )

        workflow = translate_txt2img_request(normalized).to_payload()["workflow"]
        preprocess_node = next(node for node in workflow.values() if node["class_type"] == "RookieUIControlNetPreprocess")
        apply_node = next(
            node for node in workflow.values() if node["class_type"] == "RookieUIControlNetApplyNativeAdvanced"
        )

        self.assertFalse(preprocess_node["inputs"]["use_mask"])
        self.assertNotIn("mask", preprocess_node["inputs"])
        self.assertTrue(apply_node["inputs"]["mask_aware_apply"])
        self.assertIn("mask_optional", apply_node["inputs"])

    def test_txt2img_translation_rolls_back_to_base_apply_when_advanced_keyframes_collapse(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "controlnet_units": [
                    {
                        "enabled": True,
                        "module": "canny",
                        "model": "control_v11p_sd15_canny.safetensors",
                        "image_asset": "source-image",
                        "weight": 0.55,
                        "guidance_start": 0.2,
                        "guidance_end": 0.7,
                        "advanced": {
                            "enabled": True,
                            "weight_preset": "strong",
                            "timestep_keyframes": [
                                {"start_percent": 0.0, "end_percent": 0.1, "strength_scale": 1.0},
                                {"start_percent": 0.9, "end_percent": 1.0, "strength_scale": 0.0},
                            ],
                        },
                    }
                ],
            }
        )

        workflow = translate_txt2img_request(normalized).to_payload()["workflow"]
        apply_nodes = [
            node for node in workflow.values() if node["class_type"] == "RookieUIControlNetApplyNativeAdvanced"
        ]

        self.assertEqual(len(apply_nodes), 1)
        self.assertEqual(apply_nodes[0]["inputs"]["strength"], 0.55)
        self.assertEqual(apply_nodes[0]["inputs"]["start_percent"], 0.2)
        self.assertEqual(apply_nodes[0]["inputs"]["end_percent"], 0.7)
        self.assertEqual(apply_nodes[0]["inputs"]["weight_preset"], "strong")

    def test_img2img_translation_keeps_base_graph_when_no_controlnet_units(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait cleanup",
                "image_asset": "portrait-input",
            }
        )
        payload = translate_img2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in payload["workflow"].values()}
        self.assertNotIn("RookieUIControlNetApplyNativeAdvanced", class_types)

    def test_txt2img_controlnet_uses_unet_model_source_on_diffusion_model_path(self) -> None:
        with mock.patch(
            "rookieui.services.txt2img.discover_model_inventory",
            return_value=mock.Mock(
                source="host",
                checkpoints=["SDXL\\realvisxl.safetensors"],
                diffusion_models=["flux\\flux1-dev.safetensors"],
                vae=["flux_vae.safetensors"],
                text_encoders=["clip_l.safetensors"],
                loras=["Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors"],
                default_checkpoint="SDXL\\realvisxl.safetensors",
                default_vae="flux_vae.safetensors",
                default_text_encoder="clip_l.safetensors",
                controlnet=["control_v11p_sd15_canny.safetensors"],
            ),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "city skyline",
                    "profile": "flux",
                    "checkpoint_name": "flux/flux1-dev.safetensors",
                    "text_encoder_name": "clip_l.safetensors",
                    "vae_name": "flux_vae.safetensors",
                    "controlnet_units": [
                        {
                            "enabled": True,
                            "module": "canny",
                            "model": "control_v11p_sd15_canny.safetensors",
                            "image_asset": "source-image",
                        }
                    ],
                }
            )

        payload = translate_txt2img_request(normalized).to_payload()
        workflow = payload["workflow"]
        class_types = {node["class_type"] for node in workflow.values()}
        self.assertIn("UNETLoader", class_types)
        self.assertNotIn("CheckpointLoaderSimple", class_types)
        unet_node_id = next(node_id for node_id, node in workflow.items() if node["class_type"] == "UNETLoader")
        loader_node = next(node for node in workflow.values() if node["class_type"] == "DiffControlNetLoader")
        self.assertEqual(loader_node["inputs"]["model"], [unet_node_id, 0])

    def test_txt2img_adetailer_controlnet_none_keeps_refinement_without_controlnet_apply(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "portrait",
                "adetailer": {
                    "enabled": True,
                    "units": [
                        {
                            "enabled": True,
                            "detector": "face_yolov8n.pt",
                            "controlnet": {"mode": "none"},
                        }
                    ],
                },
            }
        )

        payload = translate_txt2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in payload["workflow"].values()}

        self.assertIn("RookieUIADetailerDetectMask", class_types)
        self.assertNotIn("RookieUIControlNetApplyNativeAdvanced", class_types)

    def test_txt2img_adetailer_controlnet_passthrough_uses_current_refinement_image(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "portrait",
                "controlnet_units": [
                    {
                        "enabled": True,
                        "module": "canny",
                        "model": "control_v11p_sd15_canny.safetensors",
                        "image_asset": "source-image",
                        "weight": 0.7,
                    }
                ],
                "adetailer": {
                    "enabled": True,
                    "units": [
                        {
                            "enabled": True,
                            "detector": "face_yolov8n.pt",
                            "controlnet": {"mode": "passthrough"},
                        }
                    ],
                },
            }
        )

        payload = translate_txt2img_request(normalized).to_payload()
        workflow = payload["workflow"]
        apply_nodes = [
            node for node in workflow.values() if node["class_type"] == "RookieUIControlNetApplyNativeAdvanced"
        ]
        preprocess_nodes = [(node_id, node) for node_id, node in workflow.items() if node["class_type"] == "RookieUIControlNetPreprocess"]
        decode_nodes = [(node_id, node) for node_id, node in workflow.items() if node["class_type"] == "VAEDecode"]

        self.assertEqual(len(apply_nodes), 2)
        self.assertEqual(len(preprocess_nodes), 2)
        self.assertEqual(apply_nodes[0]["inputs"]["strength"], 0.7)
        self.assertEqual(apply_nodes[1]["inputs"]["strength"], 0.7)
        self.assertEqual(preprocess_nodes[-1][1]["inputs"]["image"], [decode_nodes[0][0], 0])

    def test_txt2img_adetailer_controlnet_custom_is_isolated_to_detailer_context(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "portrait",
                "adetailer": {
                    "enabled": True,
                    "units": [
                        {
                            "enabled": True,
                            "detector": "face_yolov8n.pt",
                            "controlnet": {
                                "mode": "custom",
                                "module": "depth",
                                "model": "control_v11f1p_sd15_depth.safetensors",
                                "weight": 0.55,
                                "guidance_start": 0.15,
                                "guidance_end": 0.65,
                            },
                        }
                    ],
                },
            }
        )

        payload = translate_txt2img_request(normalized).to_payload()
        workflow = payload["workflow"]
        apply_nodes = [
            node for node in workflow.values() if node["class_type"] == "RookieUIControlNetApplyNativeAdvanced"
        ]
        loader_nodes = [node for node in workflow.values() if node["class_type"] == "DiffControlNetLoader"]
        preprocess_nodes = [(node_id, node) for node_id, node in workflow.items() if node["class_type"] == "RookieUIControlNetPreprocess"]
        decode_nodes = [(node_id, node) for node_id, node in workflow.items() if node["class_type"] == "VAEDecode"]

        self.assertEqual(len(apply_nodes), 1)
        self.assertEqual(apply_nodes[0]["inputs"]["strength"], 0.55)
        self.assertEqual(apply_nodes[0]["inputs"]["start_percent"], 0.15)
        self.assertEqual(apply_nodes[0]["inputs"]["end_percent"], 0.65)
        self.assertEqual(apply_nodes[0]["inputs"]["weight_preset"], "balanced")
        self.assertEqual(loader_nodes[0]["inputs"]["control_net_name"], "control_v11f1p_sd15_depth.safetensors")
        self.assertEqual(preprocess_nodes[0][1]["inputs"]["module"], "depth")
        self.assertEqual(preprocess_nodes[0][1]["inputs"]["image"], [decode_nodes[0][0], 0])


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
            routes.controlnet_detect(_FakeJsonRequest({"controlnet_module": "none", "image": VALID_PNG_DATA_URL}))
        )

        self.assertEqual(model_list["status"], 200)
        self.assertEqual(module_list["status"], 200)
        self.assertEqual(control_types["status"], 200)
        self.assertEqual(detect["status"], 200)
        self.assertIn("model_list", model_list["payload"])
        self.assertIn("module_list", module_list["payload"])
        self.assertIn("control_types", control_types["payload"])
        self.assertIn("images", detect["payload"])
        self.assertEqual(model_list["payload"]["contract"]["version"], CONTROLNET_INTEGRATED_CONTRACT_VERSION)
        self.assertEqual(module_list["payload"]["contract"]["version"], CONTROLNET_INTEGRATED_CONTRACT_VERSION)
        self.assertEqual(control_types["payload"]["contract"]["version"], CONTROLNET_INTEGRATED_CONTRACT_VERSION)
        self.assertEqual(detect["payload"]["contract"]["version"], CONTROLNET_INTEGRATED_CONTRACT_VERSION)
        self.assertEqual(
            control_types["payload"]["contract"]["ui_variant"],
            CONTROLNET_INTEGRATED_UI_VARIANT,
        )
        self.assertEqual(
            control_types["payload"]["contract"]["advanced_contract"]["runtime_state"],
            CONTROLNET_ADVANCED_RUNTIME_STATE,
        )
        self.assertEqual(control_types["payload"]["default_type"], "All")

    def test_detect_payload_supports_passthrough_none_module(self) -> None:
        payload = build_controlnet_detect_payload(
            {
                "controlnet_module": "none",
                "controlnet_input_images": [VALID_PNG_DATA_URL],
            }
        )
        self.assertEqual(payload["module"], "none")
        self.assertEqual(len(payload["images"]), 1)
        self.assertEqual(payload["contract"]["version"], CONTROLNET_INTEGRATED_CONTRACT_VERSION)

    def test_detect_payload_echoes_requested_controlnet_model(self) -> None:
        payload = build_controlnet_detect_payload(
            {
                "controlnet_module": "none",
                "controlnet_model": "xinsir-controlnet-depth-sdxl.safetensors",
                "controlnet_input_images": [VALID_PNG_DATA_URL],
            }
        )
        self.assertEqual(payload["requested_controlnet_model"], "xinsir-controlnet-depth-sdxl.safetensors")

    def test_model_list_payload_filters_out_preprocessor_weight_entries(self) -> None:
        fake_inventory = mock.Mock(
            source="host",
            checkpoints=[],
            diffusion_models=[],
            vae=[],
            text_encoders=[],
            loras=[],
            default_checkpoint="",
            default_vae="",
            default_text_encoder="",
            controlnet=[
                "Xinsir-Controlnet-depth-sdxl.safetensors",
                "depth_anything_v2_vitl.pth",
                "control_v11p_sd15_openpose.ckpt",
            ],
        )
        with mock.patch("rookieui.services.controlnet.discover_model_inventory", return_value=fake_inventory):
            payload = build_controlnet_model_list_payload()

        self.assertIn("Xinsir-Controlnet-depth-sdxl.safetensors", payload["model_list"])
        self.assertIn("control_v11p_sd15_openpose.ckpt", payload["model_list"])
        self.assertNotIn("depth_anything_v2_vitl.pth", payload["model_list"])

    def test_module_list_payload_accepts_env_extension_modules(self) -> None:
        with mock.patch.dict("os.environ", {"ROOKIEUI_CONTROLNET_EXTRA_MODULES": "OpenPose, custom-module,foo_bar"}):
            payload = build_controlnet_module_list_payload()

        self.assertIn("none", payload["module_list"])
        self.assertIn("openpose", payload["module_list"])
        self.assertIn("custom_module", payload["module_list"])
        self.assertIn("foo_bar", payload["module_list"])
        self.assertIn("lineart_anime", payload["module_list"])
        self.assertIn("depth_anything_v2", payload["module_list"])

    def test_control_types_payload_builds_full_dynamic_matrix(self) -> None:
        fake_inventory = mock.Mock(
            source="host",
            checkpoints=[],
            diffusion_models=[],
            vae=[],
            text_encoders=[],
            loras=[],
            default_checkpoint="",
            default_vae="",
            default_text_encoder="",
            controlnet=[
                "control_v11p_sd15_canny.safetensors",
                "control_v11f1p_sd15_depth.safetensors",
                "control_v11p_sd15_openpose.safetensors",
            ],
        )
        with mock.patch("rookieui.services.controlnet.discover_model_inventory", return_value=fake_inventory):
            payload = build_controlnet_control_types_payload()

        self.assertEqual(payload["default_type"], "All")
        self.assertEqual(payload["control_type_order"], payload["contract"]["control_type_order"])
        self.assertEqual(set(payload["control_type_order"]), set(payload["control_types"].keys()))
        self.assertIn("canny", payload["control_types"]["Canny"]["module_list"])
        self.assertEqual(
            payload["control_types"]["Canny"]["default_option"],
            "canny",
        )
        self.assertTrue(
            any("canny" in model.lower() for model in payload["control_types"]["Canny"]["model_list"]),
        )
        self.assertTrue(
            any("depth" in model.lower() for model in payload["control_types"]["Depth"]["model_list"]),
        )
        self.assertTrue(
            any("openpose" in model.lower() for model in payload["control_types"]["OpenPose"]["model_list"]),
        )
        self.assertIn("lineart_anime", payload["control_types"]["Lineart"]["module_list"])
        self.assertIn("lineart_standard", payload["control_types"]["Lineart"]["module_list"])
        self.assertEqual(payload["preprocessor_profiles"]["openpose_dw"]["control_type"], "OpenPose")
        self.assertEqual(payload["preprocessor_profiles"]["openpose_dw"]["secondary_outputs"], ["openpose_json"])
        self.assertEqual(
            payload["preprocessor_profiles"]["depth_anything_v2"]["preferred_host_nodes"],
            ["DepthAnythingV2Preprocessor"],
        )

    def test_detect_payload_preserves_selected_preprocessor_variant_for_runtime_dispatch(self) -> None:
        preprocess_mock = mock.Mock(
            return_value=ControlNetRuntimeResult(
                image=mock.Mock(),
                backend="comfy_host_preprocessor",
                processor_name="AnimeLineArtPreprocessor",
                used_fallback=False,
                diagnostics=(),
            )
        )
        with mock.patch("rookieui.services.controlnet.runtime_dependencies_available", return_value=True):
            with mock.patch("rookieui.services.controlnet.image_tensor_from_bytes", return_value=mock.Mock()):
                with mock.patch("rookieui.services.controlnet.preprocess_controlnet_tensor", preprocess_mock):
                    with mock.patch(
                        "rookieui.services.controlnet.image_tensor_to_data_url",
                        return_value="data:image/png;base64,cHJldmlldw==",
                    ):
                        payload = build_controlnet_detect_payload(
                            {
                                "controlnet_module": "lineart_anime",
                                "controlnet_input_images": [VALID_PNG_DATA_URL],
                            }
                        )

        preprocess_mock.assert_called_once()
        self.assertEqual(preprocess_mock.call_args.kwargs["module"], "lineart_anime")
        self.assertEqual(payload["module"], "lineart_anime")
        self.assertEqual(payload["processor"], "AnimeLineArtPreprocessor")
        self.assertEqual(payload["preprocessor_profile"]["option_key"], "lineart_anime")

    def test_detect_payload_applies_pixel_perfect_processor_resolution(self) -> None:
        preprocess_mock = mock.Mock(
            return_value=ControlNetRuntimeResult(
                image=mock.Mock(),
                backend="comfy_host_preprocessor",
                processor_name="CannyEdgePreprocessor",
                used_fallback=False,
                diagnostics=(),
            )
        )
        runtime_image = mock.Mock()
        runtime_image.shape = (1, 768, 1024, 3)
        with mock.patch("rookieui.services.controlnet.runtime_dependencies_available", return_value=True):
            with mock.patch("rookieui.services.controlnet.image_tensor_from_bytes", return_value=runtime_image):
                with mock.patch("rookieui.services.controlnet.preprocess_controlnet_tensor", preprocess_mock):
                    with mock.patch(
                        "rookieui.services.controlnet.image_tensor_to_data_url",
                        return_value="data:image/png;base64,cHJldmlldw==",
                    ):
                        payload = build_controlnet_detect_payload(
                            {
                                "controlnet_module": "canny",
                                "controlnet_input_images": [VALID_PNG_DATA_URL],
                                "controlnet_pixel_perfect": True,
                                "controlnet_resize_mode": "resize_and_fill",
                                "target_width": 512,
                                "target_height": 512,
                                "controlnet_processor_res": 999,
                            }
                        )

        preprocess_mock.assert_called_once()
        self.assertEqual(preprocess_mock.call_args.kwargs["processor_res"], 384)
        self.assertEqual(payload["processor_res"], 384)
        self.assertTrue(payload["pixel_perfect"])

    def test_detect_payload_preserves_bounded_openpose_json_metadata(self) -> None:
        preprocess_mock = mock.Mock(
            return_value=ControlNetRuntimeResult(
                image=mock.Mock(),
                backend="comfy_host_preprocessor",
                processor_name="DWPreprocessor",
                used_fallback=False,
                diagnostics=(),
                secondary_outputs={"openpose_json": ('[{"people":[]}]',)},
            )
        )
        with mock.patch("rookieui.services.controlnet.runtime_dependencies_available", return_value=True):
            with mock.patch("rookieui.services.controlnet.image_tensor_from_bytes", return_value=mock.Mock()):
                with mock.patch("rookieui.services.controlnet.preprocess_controlnet_tensor", preprocess_mock):
                    with mock.patch(
                        "rookieui.services.controlnet.image_tensor_to_data_url",
                        return_value="data:image/png;base64,cHJldmlldw==",
                    ):
                        payload = build_controlnet_detect_payload(
                            {
                                "controlnet_module": "openpose_dw",
                                "controlnet_input_images": [VALID_PNG_DATA_URL],
                            }
                        )

        self.assertEqual(payload["processor"], "DWPreprocessor")
        self.assertEqual(payload["secondary_outputs"]["openpose_json"], ['[{"people":[]}]'])
        self.assertEqual(payload["openpose_json"], ['[{"people":[]}]'])

    def test_detect_payload_supports_depth_module_dispatch(self) -> None:
        payload = build_controlnet_detect_payload(
            {
                "controlnet_module": "depth",
                "controlnet_input_images": [
                    "data:image/png;base64,"
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7+gW8AAAAASUVORK5CYII="
                ],
            }
        )
        self.assertEqual(payload["module"], "depth")
        if CONTROLNET_WARNING_PREPROCESSOR_UNAVAILABLE in payload["warning_codes"]:
            self.assertIn(CONTROLNET_WARNING_PREPROCESSOR_UNAVAILABLE, payload["warning_codes"])
            return
        self.assertIn(payload["detect_backend"], {"comfy_host_preprocessor", "comfy_host_preprocessor_aio", "rookieui_internal_fallback"})
        self.assertEqual(len(payload["images"]), 1)

    def test_detect_payload_uses_host_preprocessor_backend_when_runtime_succeeds(self) -> None:
        with mock.patch("rookieui.services.controlnet.runtime_dependencies_available", return_value=True):
            with mock.patch("rookieui.services.controlnet.image_tensor_from_bytes", return_value=mock.Mock()):
                with mock.patch(
                    "rookieui.services.controlnet.preprocess_controlnet_tensor",
                    return_value=ControlNetRuntimeResult(
                        image=mock.Mock(),
                        backend="comfy_host_preprocessor",
                        processor_name="MiDaS-DepthMapPreprocessor",
                        used_fallback=False,
                        diagnostics=(),
                    ),
                ):
                    with mock.patch("rookieui.services.controlnet.image_tensor_to_data_url", return_value="data:image/png;base64,cHJldmlldw=="):
                        payload = build_controlnet_detect_payload(
                            {
                                "controlnet_module": "depth",
                                "controlnet_input_images": [VALID_PNG_DATA_URL],
                            }
                        )

        self.assertEqual(payload["source"], "rookieui")
        self.assertEqual(payload["detect_backend"], "comfy_host_preprocessor")
        self.assertEqual(payload["processor"], "MiDaS-DepthMapPreprocessor")
        self.assertNotIn(CONTROLNET_WARNING_PREPROCESSOR_HOST_FALLBACK, payload["warning_codes"])

    def test_detect_payload_passes_mask_tensor_to_runtime_when_mask_is_present(self) -> None:
        runtime_image = mock.Mock(name="runtime_image_tensor")
        runtime_mask = mock.Mock(name="runtime_mask_tensor")
        preprocess_mock = mock.Mock(
            return_value=ControlNetRuntimeResult(
                image=runtime_image,
                backend="comfy_host_preprocessor",
                processor_name="InpaintPreprocessor",
                used_fallback=False,
                diagnostics=(),
            )
        )
        with mock.patch("rookieui.services.controlnet.runtime_dependencies_available", return_value=True):
            with mock.patch("rookieui.services.controlnet.image_tensor_from_bytes", return_value=runtime_image):
                with mock.patch("rookieui.services.controlnet.mask_tensor_from_bytes", return_value=runtime_mask):
                    with mock.patch("rookieui.services.controlnet.preprocess_controlnet_tensor", preprocess_mock):
                        with mock.patch(
                            "rookieui.services.controlnet.image_tensor_to_data_url",
                            return_value="data:image/png;base64,cHJldmlldw==",
                        ):
                            payload = build_controlnet_detect_payload(
                                {
                                    "controlnet_module": "inpaint",
                                    "controlnet_input_images": [VALID_PNG_DATA_URL],
                                    "controlnet_masks": [VALID_PNG_DATA_URL],
                                }
                            )

        self.assertEqual(payload["detect_backend"], "comfy_host_preprocessor")
        preprocess_mock.assert_called_once()
        self.assertIs(preprocess_mock.call_args.kwargs["mask_tensor"], runtime_mask)

    def test_detect_payload_emits_fallback_warning_when_runtime_fallback_is_used(self) -> None:
        with mock.patch("rookieui.services.controlnet.runtime_dependencies_available", return_value=True):
            with mock.patch("rookieui.services.controlnet.image_tensor_from_bytes", return_value=mock.Mock()):
                with mock.patch(
                    "rookieui.services.controlnet.preprocess_controlnet_tensor",
                    return_value=ControlNetRuntimeResult(
                        image=mock.Mock(),
                        backend="rookieui_internal_fallback",
                        processor_name="depth",
                        used_fallback=True,
                        diagnostics=("MiDaS-DepthMapPreprocessor: model missing",),
                    ),
                ):
                    with mock.patch("rookieui.services.controlnet.image_tensor_to_data_url", return_value="data:image/png;base64,cHJldmlldw=="):
                        payload = build_controlnet_detect_payload(
                            {
                                "controlnet_module": "depth",
                                "controlnet_input_images": [VALID_PNG_DATA_URL],
                            }
                        )

        self.assertEqual(payload["detect_backend"], "rookieui_internal_fallback")
        self.assertIn(CONTROLNET_WARNING_PREPROCESSOR_HOST_FALLBACK, payload["warning_codes"])
        self.assertEqual(len(payload["images"]), 1)

    def test_detect_payload_emits_empty_output_warning_when_runtime_reports_near_empty(self) -> None:
        with mock.patch("rookieui.services.controlnet.runtime_dependencies_available", return_value=True):
            with mock.patch("rookieui.services.controlnet.image_tensor_from_bytes", return_value=mock.Mock()):
                with mock.patch(
                    "rookieui.services.controlnet.preprocess_controlnet_tensor",
                    return_value=ControlNetRuntimeResult(
                        image=mock.Mock(),
                        backend="comfy_host_preprocessor",
                        processor_name="OpenposePreprocessor",
                        used_fallback=False,
                        diagnostics=("OpenposePreprocessor:output_near_empty",),
                    ),
                ):
                    with mock.patch("rookieui.services.controlnet.image_tensor_to_data_url", return_value="data:image/png;base64,cHJldmlldw=="):
                        payload = build_controlnet_detect_payload(
                            {
                                "controlnet_module": "openpose",
                                "controlnet_input_images": [VALID_PNG_DATA_URL],
                            }
                        )

        self.assertEqual(payload["detect_backend"], "comfy_host_preprocessor")
        self.assertIn(CONTROLNET_WARNING_PREPROCESSOR_EMPTY_OUTPUT, payload["warning_codes"])

    def test_detect_payload_forwards_selected_module_without_cross_module_override(self) -> None:
        test_modules = ["canny", "depth", "openpose", "lineart", "scribble", "softedge", "normalmap", "inpaint"]
        for module_name in test_modules:
            with self.subTest(module=module_name):
                preprocess_mock = mock.Mock(
                    return_value=ControlNetRuntimeResult(
                        image=mock.Mock(),
                        backend="comfy_host_preprocessor",
                        processor_name=f"{module_name}-processor",
                        used_fallback=False,
                        diagnostics=(),
                    )
                )
                with mock.patch("rookieui.services.controlnet.runtime_dependencies_available", return_value=True):
                    with mock.patch("rookieui.services.controlnet.image_tensor_from_bytes", return_value=mock.Mock()):
                        with mock.patch("rookieui.services.controlnet.preprocess_controlnet_tensor", preprocess_mock):
                            with mock.patch(
                                "rookieui.services.controlnet.image_tensor_to_data_url",
                                return_value="data:image/png;base64,cHJldmlldw==",
                            ):
                                payload = build_controlnet_detect_payload(
                                    {
                                        "controlnet_module": module_name,
                                        "controlnet_model": "unit-selected-model.safetensors",
                                        "controlnet_input_images": [VALID_PNG_DATA_URL],
                                    }
                                )

                self.assertEqual(payload["module"], module_name)
                self.assertEqual(payload["requested_controlnet_model"], "unit-selected-model.safetensors")
                preprocess_mock.assert_called_once()
                self.assertEqual(preprocess_mock.call_args.kwargs["module"], module_name)

    def test_controlnet_detect_route_returns_invalid_request_for_missing_image(self) -> None:
        response = asyncio.run(routes.controlnet_detect(_FakeJsonRequest({"controlnet_module": "depth"})))
        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"]["status"], "invalid-request")
        self.assertIn("controlnet_input_images or image is required", response["payload"]["detail"])
