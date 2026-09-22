from __future__ import annotations

import hashlib
import json
import types
import unittest
from pathlib import Path
from unittest import mock

from rookieui.contracts.models import ModelInventorySnapshot
from rookieui.services.img2img import normalize_img2img_request
from rookieui.services.workflow_translation import translate_img2img_request


class QwenImage21EditTests(unittest.TestCase):
    def _inventory(self) -> ModelInventorySnapshot:
        return ModelInventorySnapshot(
            source="host",
            diffusion_models=["qwen_image_2.1_int8_convrot.safetensors"],
            text_encoders=["qwen3vl_8b_int8_convrot.safetensors"],
            vae=["qwen_image_2.1_vae_bf16.safetensors"],
        )

    def _normalize(self, count: int = 1, **overrides: object):
        payload: dict[str, object] = {
            "profile": "qwen_image_21_edit",
            "prompt": "Change <image1> with <image2> kept literal",
            "negative_prompt": "synthetic unwanted detail",
            "reference_images": [{"image_asset": f"ref-{i}"} for i in range(1, count + 1)],
            "seed": 42,
        }
        payload.update(overrides)
        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=self._inventory()), \
                mock.patch("rookieui.services.img2img.resolve_asset_path", return_value=Path("synthetic.png")):
            return normalize_img2img_request(payload)

    def test_one_two_ten_references_have_numeric_keys_and_rgba_loaders(self) -> None:
        for count in (1, 2, 10):
            with self.subTest(count=count):
                request = self._normalize(count)
                self.assertEqual(request.main_reference_index, 0)
                self.assertEqual(request.reference_resolution, 0)
                self.assertEqual(request.denoise_strength, 1.0)
                self.assertEqual(request.prompt, "Change <image1> with <image2> kept literal")
                self.assertIn("QWEN21_NEGATIVE_CFG_ONE", request.parameter_warning_codes)
                translation = translate_img2img_request(request)
                graph = translation.workflow
                by_class = {node["class_type"]: (node_id, node["inputs"]) for node_id, node in graph.items()}
                encode_id, encode = by_class["TextEncodeQwenImage21"]
                self.assertEqual([key for key in encode if key.startswith("images.image_")],
                                 [f"images.image_{i}" for i in range(1, count + 1)])
                for index in range(1, count + 1):
                    loader = graph[encode[f"images.image_{index}"][0]]
                    self.assertEqual(loader["inputs"], {
                        "asset_handle": f"ref-{index}", "preserve_alpha": True, "first_frame_only": True,
                    })
                self.assertEqual(encode["resolution"], 0)
                self.assertEqual(by_class["QwenImage21Cache"][1]["device"], "auto")
                self.assertEqual(by_class["QwenImage21Cache"][1]["dtype"], "default")
                sampler = by_class["KSampler"][1]
                self.assertEqual((sampler["positive"], sampler["negative"], sampler["latent_image"]),
                                 ([encode_id, 0], [encode_id, 1], [encode_id, 2]))
                self.assertEqual((sampler["steps"], sampler["cfg"], sampler["sampler_name"],
                                  sampler["scheduler"], sampler["denoise"]),
                                 (25, 1.0, "euler", "simple", 1.0))
                self.assertEqual(translation.generation_metadata["extra_pnginfo"]["rookieui"]["edit_task"], "edit")
                self.assertNotIn("ModelSamplingAuraFlow", by_class)
                self.assertNotIn("CFGNorm", by_class)

    def test_custom_canvas_resolution_and_background_task_are_metadata(self) -> None:
        request = self._normalize(2, reference_resolution=1024, output_size_mode="custom",
                                  width=768, height=1024, edit_task="background_removal")
        translation = translate_img2img_request(request)
        graph = translation.workflow
        by_class = {node["class_type"]: (node_id, node["inputs"]) for node_id, node in graph.items()}
        self.assertEqual(by_class["TextEncodeQwenImage21"][1]["resolution"], 1024)
        self.assertEqual(by_class["EmptyLatentImage"][1], {"width": 768, "height": 1024, "batch_size": 1})
        self.assertEqual(by_class["KSampler"][1]["latent_image"], [by_class["EmptyLatentImage"][0], 0])
        meta = translation.generation_metadata["extra_pnginfo"]["rookieui"]
        self.assertEqual((meta["edit_task"], meta["output_size_mode"], meta["reference_resolution"]),
                         ("background_removal", "custom", 1024))

    def test_zero_or_eleven_references_and_stale_primary_fail(self) -> None:
        for count in (0, 11):
            with self.subTest(count=count), self.assertRaises(ValueError):
                self._normalize(count)
        with self.assertRaisesRegex(ValueError, "primary reference first"):
            self._normalize(2, main_reference_index=1)

    def test_wrong_assets_and_profile_scoped_controls_fail(self) -> None:
        for override in (
            {"checkpoint_name": "qwen_image_2512_fp8_e4m3fn.safetensors"},
            {"text_encoder_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors"},
            {"vae_name": "qwen_image_vae.safetensors"},
            {"reference_resolution": 31}, {"reference_resolution": 4128},
            {"output_size_mode": "invalid"}, {"edit_task": "unknown"},
            {"output_size_mode": "custom", "width": 1000},
            {"shift": 3}, {"hires_enabled": True}, {"batch_size": 2},
            {"denoise_strength": 0.75}, {"lora_name": "legacy.safetensors"},
        ):
            with self.subTest(override=override), self.assertRaises(ValueError):
                self._normalize(**override)

    def test_old_host_rejects_missing_cache_or_encoder(self) -> None:
        request = self._normalize()
        for mapping in ({}, {"TextEncodeQwenImage21": object()}):
            with mock.patch.dict("sys.modules", {"nodes": types.SimpleNamespace(NODE_CLASS_MAPPINGS=mapping)}):
                with self.assertRaisesRegex(ValueError, "QwenImage21Cache"):
                    translate_img2img_request(request)

    def test_pinned_official_edit_template_contract_when_available(self) -> None:
        source = Path(__file__).resolve().parents[1] / "reference" / "docs" / "260922_qwen21_host_alignment" / "image_qwen_image_2_1_image_edit.json"
        if not source.is_file():
            self.skipTest("Private pinned reference bytes are absent from this checkout.")
        raw = source.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "d6dd8695469c20ca5e77b4bddf981b898ee0e034f0cfc5840c86f15b812ca081")  # pragma: allowlist secret
        graph = json.loads(raw)["definitions"]["subgraphs"][0]
        by_type = {node["type"]: node for node in graph["nodes"]}
        self.assertEqual(by_type["QwenImage21Cache"]["widgets_values"], ["auto", "default"])
        inputs = {entry["name"] for entry in by_type["TextEncodeQwenImage21"]["inputs"]}
        self.assertTrue({f"images.image_{i}" for i in range(1, 11)}.issubset(inputs))
