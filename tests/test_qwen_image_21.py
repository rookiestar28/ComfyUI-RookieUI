from __future__ import annotations

import unittest
import types
import hashlib
import json
from pathlib import Path
from unittest import mock

from rookieui.contracts.models import ModelInventorySnapshot
from rookieui.contracts.qwen_image_21_assets import qwen_image_21_asset_role
from rookieui.services.model_inventory import (
    resolve_primary_model_selector_context,
    resolve_text_encoder_selector_context,
    resolve_vae_selector_context,
)
from rookieui.services.parity_matrix import get_parity_profile
from rookieui.services.presets import build_preset_payload
from rookieui.services.txt2img import normalize_txt2img_request
from rookieui.services.workflow_translation import translate_txt2img_request


class QwenImage21AdmissionTests(unittest.TestCase):
    def _inventory(self) -> ModelInventorySnapshot:
        return ModelInventorySnapshot(
            source="host",
            diffusion_models=["models/qwen_image_2.1_int8_convrot.safetensors"],
            text_encoders=["models/qwen3vl_8b_int8_convrot.safetensors"],
            vae=["models/qwen_image_2.1_vae_bf16.safetensors"],
        )

    def test_new_assets_do_not_become_legacy_qwen_defaults(self) -> None:
        inventory = ModelInventorySnapshot(
            source="host",
            diffusion_models=["qwen/qwen_image_2.1_int8_convrot.safetensors"],
            text_encoders=["qwen/qwen3vl_8b_int8_convrot.safetensors"],
            vae=["qwen/qwen_image_2.1_vae_bf16.safetensors"],
        )

        _, _, model = resolve_primary_model_selector_context("qwen_image", inventory)
        self.assertEqual(model, "")
        self.assertEqual(resolve_text_encoder_selector_context("qwen_image", inventory), "")
        self.assertEqual(resolve_vae_selector_context("qwen_image", inventory), "")

    def test_mixed_inventory_keeps_legacy_and_new_defaults_separate(self) -> None:
        inventory = ModelInventorySnapshot(
            source="host",
            diffusion_models=["qwen_image_2.1_int8_convrot.safetensors", "qwen_image_2512_fp8_e4m3fn.safetensors"],
            text_encoders=["qwen3vl_8b_int8_convrot.safetensors", "qwen_2.5_vl_7b_fp8_scaled.safetensors"],
            vae=["qwen_image_2.1_vae_bf16.safetensors", "qwen_image_vae.safetensors"],
        )
        self.assertEqual(resolve_primary_model_selector_context("qwen_image", inventory)[2],
                         "qwen_image_2512_fp8_e4m3fn.safetensors")
        self.assertEqual(resolve_primary_model_selector_context("qwen_image_21", inventory)[2],
                         "qwen_image_2.1_int8_convrot.safetensors")
        self.assertEqual(resolve_text_encoder_selector_context("qwen_image", inventory),
                         "qwen_2.5_vl_7b_fp8_scaled.safetensors")
        self.assertEqual(resolve_text_encoder_selector_context("qwen_image_21", inventory),
                         "qwen3vl_8b_int8_convrot.safetensors")
        self.assertEqual(resolve_vae_selector_context("qwen_image", inventory), "qwen_image_vae.safetensors")
        self.assertEqual(resolve_vae_selector_context("qwen_image_21", inventory),
                         "qwen_image_2.1_vae_bf16.safetensors")

    def test_legacy_qwen_does_not_choose_unrelated_or_denied_first_file(self) -> None:
        inventory = ModelInventorySnapshot(
            source="host",
            diffusion_models=["flux2_dev_fp8mixed.safetensors", "qwen_image_2.1_int8_convrot.safetensors"],
        )
        self.assertEqual(resolve_primary_model_selector_context("qwen_image", inventory)[2], "")

    def test_official_alternate_variant_filenames_have_correct_roles(self) -> None:
        self.assertEqual(qwen_image_21_asset_role("qwen_image_2.1_bf16.safetensors"), "diffusion_models")
        self.assertEqual(qwen_image_21_asset_role("qwen3vl_8b_bf16.safetensors"), "text_encoders")
        self.assertEqual(qwen_image_21_asset_role("qwen3vl_8b_w4a8.safetensors"), "text_encoders")

    def test_pinned_official_template_has_expected_node_semantics_when_available(self) -> None:
        source = Path(__file__).resolve().parents[1] / "reference" / "docs" / "260922_qwen21_host_alignment" / "image_qwen_image_2_1_t2i.json"
        if not source.is_file():
            self.skipTest("Private pinned reference bytes are absent from this checkout.")
        data = source.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(),
                         "d33a6b36d530756e26ef4e25beb17d950daaea09d295475cd65f97f5d0af3b41")  # pragma: allowlist secret
        graph = json.loads(data)["definitions"]["subgraphs"][0]
        by_type = {node["type"]: node for node in graph["nodes"]}
        self.assertEqual(set(by_type), {"UNETLoader", "CLIPLoader", "VAELoader",
                                        "TextEncodeQwenImage21", "EmptyLatentImage", "KSampler", "VAEDecode"})
        self.assertEqual(by_type["EmptyLatentImage"]["widgets_values"], [1024, 1024, 1])
        self.assertEqual(by_type["KSampler"]["widgets_values"][2:6], [25, 1, "euler", "simple"])

    def test_new_profile_is_distinct_from_legacy_qwen(self) -> None:
        profile = get_parity_profile("qwen_image_21")
        self.assertEqual(profile.id, "qwen_image_21")
        self.assertEqual(profile.default_steps, 25)
        self.assertEqual(profile.default_cfg_scale, 1.0)

    def test_exact_basename_role_ignores_parent_directory(self) -> None:
        self.assertEqual(qwen_image_21_asset_role("qwen21/old_qwen_image_2512.safetensors"), "")
        self.assertEqual(
            qwen_image_21_asset_role("nested\\qwen_image_2.1_int8_convrot.safetensors"),
            "diffusion_models",
        )

    def test_new_profile_uses_exact_defaults_and_official_graph(self) -> None:
        with mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=self._inventory()):
            request = normalize_txt2img_request({
                "profile": "qwen_image_21", "prompt": "(literal:1.2)",
                "negative_prompt": "unwanted", "width": 1024, "height": 768,
                "batch_size": 2, "seed": 42,
            })
        self.assertEqual(request.prompt, "(literal:1.2)")
        self.assertEqual(request.negative_prompt, "unwanted")
        self.assertEqual((request.steps, request.cfg_scale, request.sampler_name, request.scheduler_name),
                         (25, 1.0, "euler", "simple"))
        self.assertEqual((request.width, request.height, request.batch_size, request.seed), (1024, 768, 2, 42))
        self.assertEqual(request.negative_prompt_mode, "encoded")
        self.assertIn("QWEN21_NEGATIVE_CFG_ONE", request.parameter_warning_codes)
        self.assertIsNone(request.shift)
        translation = translate_txt2img_request(request)
        graph = translation.workflow
        self.assertEqual(translation.generation_metadata["extra_pnginfo"]["rookieui"]["profile"],
                         "qwen_image_21")
        self.assertEqual(translation.generation_metadata["extra_pnginfo"]["rookieui"]["seed"], 42)
        self.assertEqual(translation.generation_metadata["extra_pnginfo"]["rookieui"]["height"], 768)
        by_class = {node["class_type"]: (node_id, node["inputs"]) for node_id, node in graph.items()}
        self.assertEqual(by_class["CLIPLoader"][1]["type"], "qwen_image")
        self.assertEqual(by_class["TextEncodeQwenImage21"][1]["prompt"], "(literal:1.2)")
        self.assertEqual(by_class["TextEncodeQwenImage21"][1]["negative_prompt"], "unwanted")
        self.assertEqual(by_class["EmptyLatentImage"][1], {"width": 1024, "height": 768, "batch_size": 2})
        self.assertEqual(by_class["KSampler"][1]["positive"], [by_class["TextEncodeQwenImage21"][0], 0])
        self.assertEqual(by_class["KSampler"][1]["negative"], [by_class["TextEncodeQwenImage21"][0], 1])
        self.assertEqual(by_class["KSampler"][1]["denoise"], 1.0)
        self.assertNotIn("ModelSamplingAuraFlow", by_class)
        self.assertNotIn("CFGNorm", by_class)

    def test_wrong_generation_and_wrong_roles_fail_before_enqueue(self) -> None:
        wrong = (
            {"checkpoint_name": "old/qwen_image_2512_fp8_e4m3fn.safetensors"},
            {"text_encoder_name": "old/qwen_2.5_vl_7b_fp8_scaled.safetensors"},
            {"vae_name": "old/qwen_image_vae.safetensors"},
        )
        with mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=self._inventory()):
            for override in wrong:
                with self.subTest(override=override), self.assertRaises(ValueError):
                    normalize_txt2img_request({"profile": "qwen_image_21", "prompt": "synthetic", **override})
            for override in ({"lora_name": "synthetic.safetensors"}, {"hires_enabled": True},
                             {"shift": 3.1}, {"template_lora_enabled": True}):
                with self.subTest(override=override), self.assertRaises(ValueError):
                    normalize_txt2img_request({"profile": "qwen_image_21", "prompt": "synthetic", **override})

    def test_loaded_old_host_rejects_missing_qwen21_node(self) -> None:
        with mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=self._inventory()):
            request = normalize_txt2img_request({"profile": "qwen_image_21", "prompt": "synthetic"})
        with mock.patch.dict("sys.modules", {"nodes": types.SimpleNamespace(NODE_CLASS_MAPPINGS={})}):
            with self.assertRaisesRegex(ValueError, "TextEncodeQwenImage21"):
                translate_txt2img_request(request)

    def test_absent_qwen21_assets_do_not_show_unrelated_preset_default(self) -> None:
        inventory = ModelInventorySnapshot(
            source="host", checkpoints=["sdxl/realvisxl.safetensors"],
            diffusion_models=["qwen_image_2512_fp8_e4m3fn.safetensors"],
            text_encoders=["qwen_2.5_vl_7b_fp8_scaled.safetensors"],
            vae=["qwen_image_vae.safetensors"],
            default_checkpoint="sdxl/realvisxl.safetensors",
        )
        with mock.patch("rookieui.services.presets.discover_model_inventory", return_value=inventory):
            presets = build_preset_payload()["presets"]
        qwen21 = next(preset for preset in presets if preset["id"] == "qwen_image_21")
        self.assertEqual((qwen21["checkpoint_name"], qwen21["text_encoder_name"], qwen21["vae_name"]),
                         ("", "", ""))

    def test_explicit_filename_cannot_bypass_empty_host_inventory(self) -> None:
        inventory = ModelInventorySnapshot(source="host")
        with mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=inventory):
            with self.assertRaises(ValueError):
                normalize_txt2img_request({
                    "profile": "qwen_image_21", "prompt": "synthetic",
                    "checkpoint_name": "qwen_image_2.1_int8_convrot.safetensors",
                    "text_encoder_name": "qwen3vl_8b_int8_convrot.safetensors",
                    "vae_name": "qwen_image_2.1_vae_bf16.safetensors",
                })
