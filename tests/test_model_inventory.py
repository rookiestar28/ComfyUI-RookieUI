from __future__ import annotations

import types
import unittest
from unittest import mock

from rookieui.services.model_inventory import (
    _reset_inventory_cache_for_tests,
    discover_model_inventory,
    ensure_native_ultralytics_model_paths,
    resolve_aux_text_encoder_selector_context,
    resolve_primary_model_selector_context,
    resolve_template_lora_selector_context,
    resolve_text_encoder_selector_context,
    resolve_vae_selector_context,
)
from rookieui.services.presets import build_preset_payload


class ModelInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_inventory_cache_for_tests()

    def test_discover_model_inventory_uses_host_folder_paths_when_available(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["dreamshaper.safetensors"],
                "clip": ["clip_l.safetensors"],
                "clip_vision": ["clip_vision_g.safetensors"],
                "controlnet": ["depth_v11.safetensors"],
                "diffusion_models": ["flux1-dev.safetensors"],
                "vae": ["vae-ft-mse.safetensors"],
                "text_encoders": ["clip_l.safetensors"],
                "embeddings": ["badhandv4.pt"],
                "loras": ["detail_tweaker.safetensors"],
                "ultralytics": ["face_yolov8m.pt", "person_yolov8m-seg.pt"],
                "unet": ["sdxl_unet.safetensors"],
                "upscale_models": ["4x_foolhardy.pth"],
            }.get(folder_name, [])
        )

        snapshot = discover_model_inventory(folder_paths_module=module)

        self.assertEqual(snapshot.source, "host")
        self.assertEqual(snapshot.default_checkpoint, "dreamshaper.safetensors")
        self.assertEqual(snapshot.default_vae, "vae-ft-mse.safetensors")
        self.assertEqual(snapshot.default_text_encoder, "clip_l.safetensors")
        self.assertEqual(snapshot.clip, ["clip_l.safetensors"])
        self.assertEqual(snapshot.clip_vision, ["clip_vision_g.safetensors"])
        self.assertEqual(snapshot.controlnet, ["depth_v11.safetensors"])
        self.assertEqual(snapshot.diffusion_models, ["flux1-dev.safetensors"])
        self.assertEqual(snapshot.embeddings, ["badhandv4.pt"])
        self.assertEqual(snapshot.loras, ["detail_tweaker.safetensors"])
        self.assertEqual(snapshot.ultralytics, ["face_yolov8m.pt", "person_yolov8m-seg.pt"])
        self.assertEqual(snapshot.ultralytics_bbox, ["face_yolov8m.pt"])
        self.assertEqual(snapshot.ultralytics_segm, ["person_yolov8m-seg.pt"])
        self.assertEqual(snapshot.unet, ["sdxl_unet.safetensors"])
        self.assertEqual(snapshot.upscale_models, ["4x_foolhardy.pth"])

    def test_ensure_native_ultralytics_model_paths_updates_extensions(self) -> None:
        module = types.SimpleNamespace(
            models_dir="C:\\models",
            supported_pt_extensions={".pt", ".pth"},
            folder_names_and_paths={},
        )

        def _add_model_folder_path(folder_name: str, full_folder_path: str, is_default: bool = False) -> None:
            module.folder_names_and_paths.setdefault(folder_name, ([full_folder_path], set()))

        module.add_model_folder_path = _add_model_folder_path

        ensure_native_ultralytics_model_paths(module)

        self.assertEqual(module.folder_names_and_paths["ultralytics"][1], {".pt", ".pth"})
        self.assertEqual(module.folder_names_and_paths["ultralytics_bbox"][1], {".pt", ".pth"})
        self.assertEqual(module.folder_names_and_paths["ultralytics_segm"][1], {".pt", ".pth"})

    def test_discover_model_inventory_falls_back_without_host_module(self) -> None:
        snapshot = discover_model_inventory(folder_paths_module=None)

        self.assertIn("__host_default__", snapshot.checkpoints)
        self.assertIn("Automatic", snapshot.vae)
        self.assertIn("Automatic", snapshot.text_encoders)
        self.assertEqual(snapshot.embeddings, [])
        self.assertEqual(snapshot.loras, [])
        self.assertEqual(snapshot.diffusion_models, [])
        self.assertEqual(snapshot.ultralytics_bbox, [])
        self.assertEqual(snapshot.ultralytics_segm, [])
        self.assertEqual(snapshot.upscale_models, [])

    def test_model_inventory_payload_exposes_catalog_groups(self) -> None:
        snapshot = discover_model_inventory(folder_paths_module=None)
        payload = snapshot.to_payload()

        self.assertIn("catalog", payload)
        self.assertIn("surface_groups", payload["catalog"])
        self.assertEqual(
            payload["catalog"]["primary_model_category_by_family"]["flux"],
            "diffusion_models",
        )
        self.assertEqual(
            payload["catalog"]["primary_model_category_by_family"]["pony"],
            "checkpoints",
        )
        self.assertEqual(
            payload["catalog"]["primary_model_category_by_family"]["klein"],
            "diffusion_models",
        )
        self.assertEqual(
            payload["catalog"]["primary_model_category_by_family"]["hidream"],
            "diffusion_models",
        )
        self.assertEqual(
            payload["catalog"]["primary_model_category_by_family"]["ernie_image"],
            "diffusion_models",
        )
        self.assertIn("checkpoints", payload["catalog"]["categories"])
        self.assertIn("upscale_models", payload["catalog"]["categories"])
        self.assertIn("ultralytics_bbox", payload["catalog"]["categories"])
        self.assertIn("ultralytics_segm", payload["catalog"]["categories"])

    def test_build_preset_payload_uses_inventory_defaults(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "vae": ["Automatic"],
                "text_encoders": ["Automatic"],
            }.get(folder_name, [])
        )

        with mock.patch(
            "rookieui.services.presets.discover_model_inventory",
            return_value=discover_model_inventory(folder_paths_module=module),
        ):
            payload = build_preset_payload()

        preset_ids = [preset["id"] for preset in payload["presets"]]
        self.assertIn("sd15", preset_ids)
        self.assertEqual(payload["presets"][0]["checkpoint_name"], "realvisxl.safetensors")

    def test_build_preset_payload_uses_profile_aware_diffusion_and_text_encoder_defaults(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": [
                    "flux1-dev.safetensors",
                    "qwen_image_2512_fp8_e4m3fn.safetensors",
                    "qwen_image_edit_fp8_e4m3fn.safetensors",
                    "z_image_bf16.safetensors",
                    "z_image_turbo_bf16.safetensors",
                    "Chroma1-HD-fp8mixed.safetensors",
                    "ernie\\ernie-image.safetensors",
                    "ernie\\ernie-image-turbo.safetensors",
                ],
                "vae": [
                    "qwen_image_vae.safetensors",
                    "ae.safetensors",
                    "flux2-vae.safetensors",
                    "ernie_vae.safetensors",
                ],
                "text_encoders": [
                    "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                    "clip_l.safetensors",
                    "qwen_3_4b.safetensors",
                    "t5xxl_fp8_e4m3fn_scaled.safetensors",
                    "Ministral3_3B_fp16.safetensors",
                ],
                "loras": [
                    "Flux_2-Turbo-LoRA_comfyui.safetensors",
                    "Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors",
                    "Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors",
                ],
            }.get(folder_name, [])
        )

        with mock.patch(
            "rookieui.services.presets.discover_model_inventory",
            return_value=discover_model_inventory(folder_paths_module=module),
        ):
            payload = build_preset_payload()

        preset_lookup = {preset["id"]: preset for preset in payload["presets"]}
        self.assertEqual(preset_lookup["flux"]["checkpoint_name"], "flux1-dev.safetensors")
        self.assertEqual(
            preset_lookup["flux"]["template_lora_name"],
            "Flux_2-Turbo-LoRA_comfyui.safetensors",
        )
        self.assertEqual(preset_lookup["qwen_image"]["checkpoint_name"], "qwen_image_2512_fp8_e4m3fn.safetensors")
        self.assertEqual(preset_lookup["z_image"]["checkpoint_name"], "z_image_bf16.safetensors")
        self.assertEqual(
            preset_lookup["z_image_turbo"]["checkpoint_name"],
            "z_image_turbo_bf16.safetensors",
        )
        self.assertEqual(preset_lookup["chroma"]["checkpoint_name"], "Chroma1-HD-fp8mixed.safetensors")
        self.assertEqual(
            preset_lookup["qwen_image"]["vae_name"],
            "qwen_image_vae.safetensors",
        )
        self.assertEqual(
            preset_lookup["z_image"]["vae_name"],
            "ae.safetensors",
        )
        self.assertEqual(
            preset_lookup["z_image_turbo"]["vae_name"],
            "ae.safetensors",
        )
        self.assertEqual(
            preset_lookup["qwen_image"]["text_encoder_name"],
            "qwen_2.5_vl_7b_fp8_scaled.safetensors",
        )
        self.assertEqual(
            preset_lookup["qwen_image"]["template_lora_name"],
            "Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors",
        )
        self.assertEqual(
            preset_lookup["qwen_image_edit"]["checkpoint_name"],
            "qwen_image_edit_fp8_e4m3fn.safetensors",
        )
        self.assertEqual(
            preset_lookup["qwen_image_edit"]["template_lora_name"],
            "Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors",
        )
        self.assertEqual(
            preset_lookup["z_image"]["text_encoder_name"],
            "qwen_3_4b.safetensors",
        )
        self.assertEqual(
            preset_lookup["z_image_turbo"]["text_encoder_name"],
            "qwen_3_4b.safetensors",
        )
        self.assertEqual(
            preset_lookup["chroma"]["text_encoder_name"],
            "t5xxl_fp8_e4m3fn_scaled.safetensors",
        )
        self.assertEqual(
            preset_lookup["ernie_image"]["checkpoint_name"],
            "ernie\\ernie-image.safetensors",
        )
        self.assertEqual(
            preset_lookup["ernie_image"]["vae_name"],
            "flux2-vae.safetensors",
        )
        self.assertEqual(
            preset_lookup["ernie_image"]["text_encoder_name"],
            "Ministral3_3B_fp16.safetensors",
        )
        self.assertEqual(
            preset_lookup["ernie_image_turbo"]["checkpoint_name"],
            "ernie\\ernie-image-turbo.safetensors",
        )

    def test_resolve_primary_model_selector_context_uses_profile_mapped_category(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": ["flux1-dev.safetensors"],
                "vae": ["Automatic"],
                "text_encoders": ["Automatic"],
            }.get(folder_name, [])
        )
        snapshot = discover_model_inventory(folder_paths_module=module)

        category_id, selectors, default_value = resolve_primary_model_selector_context("flux", snapshot)
        self.assertEqual(category_id, "diffusion_models")
        self.assertEqual(selectors, ["flux1-dev.safetensors"])
        self.assertEqual(default_value, "flux1-dev.safetensors")

    def test_resolve_primary_model_selector_context_falls_back_to_checkpoints(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": [],
                "vae": ["Automatic"],
                "text_encoders": ["Automatic"],
            }.get(folder_name, [])
        )
        snapshot = discover_model_inventory(folder_paths_module=module)

        category_id, selectors, default_value = resolve_primary_model_selector_context("flux", snapshot)
        self.assertEqual(category_id, "checkpoints")
        self.assertEqual(selectors, ["realvisxl.safetensors"])
        self.assertEqual(default_value, "realvisxl.safetensors")

    def test_resolve_text_encoder_selector_context_avoids_qwen_default_for_non_qwen_diffusion_profiles(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": ["z_image_bf16.safetensors", "qwen_image_2512_fp8_e4m3fn.safetensors"],
                "vae": ["Automatic"],
                "text_encoders": ["qwen_2.5_vl_7b_fp8_scaled.safetensors", "qwen_3_4b.safetensors"],
            }.get(folder_name, [])
        )
        snapshot = discover_model_inventory(folder_paths_module=module)

        qwen_selector = resolve_text_encoder_selector_context("qwen_image", snapshot)
        z_image_selector = resolve_text_encoder_selector_context("lumina", snapshot)

        self.assertEqual(qwen_selector, "qwen_2.5_vl_7b_fp8_scaled.safetensors")
        self.assertEqual(z_image_selector, "qwen_3_4b.safetensors")

    def test_resolve_vae_selector_context_avoids_qwen_default_for_non_qwen_diffusion_profiles(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": ["z_image_bf16.safetensors", "qwen_image_2512_fp8_e4m3fn.safetensors"],
                "vae": ["qwen_image_vae.safetensors", "ae.safetensors"],
                "text_encoders": ["Automatic"],
            }.get(folder_name, [])
        )
        snapshot = discover_model_inventory(folder_paths_module=module)

        qwen_selector = resolve_vae_selector_context("qwen_image", snapshot)
        z_image_selector = resolve_vae_selector_context("lumina", snapshot)

        self.assertEqual(qwen_selector, "qwen_image_vae.safetensors")
        self.assertEqual(z_image_selector, "ae.safetensors")

    def test_resolve_text_encoder_selector_context_disables_global_default_for_diffusion_profiles(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": ["z_image_bf16.safetensors", "qwen_image_2512_fp8_e4m3fn.safetensors"],
                "vae": ["Automatic"],
                "text_encoders": ["Automatic"],
            }.get(folder_name, [])
        )
        snapshot = discover_model_inventory(folder_paths_module=module)

        z_image_selector = resolve_text_encoder_selector_context("lumina", snapshot)
        self.assertEqual(z_image_selector, "")

    def test_resolve_vae_selector_context_disables_global_default_for_diffusion_profiles(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": ["z_image_bf16.safetensors", "qwen_image_2512_fp8_e4m3fn.safetensors"],
                "vae": ["Automatic"],
                "text_encoders": ["Automatic"],
            }.get(folder_name, [])
        )
        snapshot = discover_model_inventory(folder_paths_module=module)

        z_image_selector = resolve_vae_selector_context("lumina", snapshot)
        self.assertEqual(z_image_selector, "")

    def test_profile_matrix_uses_family_aligned_defaults_for_all_non_sd_diffusion_profiles(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": [
                    "flux\\flux1-dev.safetensors",
                    "qwen\\qwen_image_2512_fp8_e4m3fn.safetensors",
                    "klein\\flux-2-klein-base-4b.safetensors",
                    "klein\\flux-2-klein-9b-fp8.safetensors",
                    "chroma\\Chroma1-HD-fp8mixed.safetensors",
                    "hidream\\hidream_i1_full_fp8.safetensors",
                    "longcat\\longcat_image_bf16.safetensors",
                    "z\\z_image_bf16.safetensors",
                    "z\\z_image_turbo_bf16.safetensors",
                    "anima\\anima-preview3-base.safetensors",
                    "ernie\\ernie-image.safetensors",
                ],
                "vae": [
                    "qwen_image_vae.safetensors",
                    "ae.safetensors",
                    "flux2-vae.safetensors",
                    "full_encoder_small_decoder.safetensors",
                ],
                "text_encoders": [
                    "clip_l.safetensors",
                    "t5xxl_fp16.safetensors",
                    "t5xxl_fp8_e4m3fn_scaled.safetensors",
                    "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                    "qwen_3_4b.safetensors",
                    "qwen_3_8b_fp8mixed.safetensors",
                    "qwen_3_06b_base.safetensors",
                    "clip_l_hidream.safetensors",
                    "clip_g_hidream.safetensors",
                    "llama_3.1_8b_instruct_fp8_scaled.safetensors",
                    "Ministral3_3B_fp16.safetensors",
                    "ernie-image-prompt-enhancer.safetensors",
                ],
                "loras": [
                    "Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors",
                    "Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors",
                ],
            }.get(folder_name, [])
        )
        snapshot = discover_model_inventory(folder_paths_module=module)
        expectations = {
            "flux": {
                "model": "flux\\flux1-dev.safetensors",
                "text_encoder": "clip_l.safetensors|t5xxl_fp16.safetensors",
                "vae": "ae.safetensors",
            },
            "qwen_image": {
                "model": "qwen\\qwen_image_2512_fp8_e4m3fn.safetensors",
                "text_encoder": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                "vae": "qwen_image_vae.safetensors",
            },
            "klein": {
                "model": "klein\\flux-2-klein-base-4b.safetensors",
                "text_encoder": "qwen_3_4b.safetensors",
                "vae": "flux2-vae.safetensors",
            },
            "chroma": {
                "model": "chroma\\Chroma1-HD-fp8mixed.safetensors",
                "text_encoder": "t5xxl_fp8_e4m3fn_scaled.safetensors",
                "vae": "ae.safetensors",
            },
            "hidream_i1_full": {
                "model": "hidream\\hidream_i1_full_fp8.safetensors",
                "text_encoder": (
                    "clip_l_hidream.safetensors|clip_g_hidream.safetensors|"
                    "t5xxl_fp8_e4m3fn_scaled.safetensors|llama_3.1_8b_instruct_fp8_scaled.safetensors"
                ),
                "vae": "ae.safetensors",
            },
            "longcat_image": {
                "model": "longcat\\longcat_image_bf16.safetensors",
                "text_encoder": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                "vae": "ae.safetensors",
            },
            "lumina": {
                "model": "z\\z_image_bf16.safetensors",
                "text_encoder": "qwen_3_4b.safetensors",
                "vae": "ae.safetensors",
            },
            "zit": {
                "model": "z\\z_image_turbo_bf16.safetensors",
                "text_encoder": "qwen_3_4b.safetensors",
                "vae": "ae.safetensors",
            },
            "anima": {
                "model": "anima\\anima-preview3-base.safetensors",
                "text_encoder": "qwen_3_06b_base.safetensors",
                "vae": "qwen_image_vae.safetensors",
            },
            "ernie_image": {
                "model": "ernie\\ernie-image.safetensors",
                "text_encoder": "Ministral3_3B_fp16.safetensors",
                "vae": "flux2-vae.safetensors",
            },
        }

        for profile_id, expectation in expectations.items():
            with self.subTest(profile_id=profile_id):
                category_id, selectors, default_model = resolve_primary_model_selector_context(profile_id, snapshot)
                self.assertEqual(category_id, "diffusion_models")
                self.assertIn(default_model, selectors)
                self.assertEqual(default_model, expectation["model"])
                resolved_text_encoder = resolve_text_encoder_selector_context(profile_id, snapshot)
                resolved_vae = resolve_vae_selector_context(profile_id, snapshot)
                self.assertIn(resolved_vae, snapshot.vae)
                self.assertEqual(resolved_text_encoder, expectation["text_encoder"])
                self.assertEqual(resolved_vae, expectation["vae"])

        self.assertEqual(
            resolve_aux_text_encoder_selector_context("ernie_image", snapshot),
            "ernie-image-prompt-enhancer.safetensors",
        )
        self.assertEqual(
            resolve_template_lora_selector_context("flux", snapshot),
            "Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors",
        )
        self.assertEqual(
            resolve_template_lora_selector_context("qwen_image", snapshot),
            "Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors",
        )

    def test_resolve_template_lora_selector_context_requires_official_template_variants(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": [
                    "flux\\flux1-dev.safetensors",
                    "qwen\\qwen_image_2512_fp8_e4m3fn.safetensors",
                    "Qwen\\FireRed-Image-Edit-1.0-transformer.safetensors",
                    "qwen\\qwen_image_edit_fp8_e4m3fn.safetensors",
                ],
                "vae": ["qwen_image_vae.safetensors"],
                "text_encoders": ["qwen_2.5_vl_7b_fp8_scaled.safetensors"],
                "loras": [
                    "Flux\\Flux_2-Lightning-4steps.safetensors",
                    "Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors",
                    "Qwen-image\\Qwen-Image-Turbo-Lightning-4steps.safetensors",
                    "Qwen-image\\Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors",
                    "Qwen-image\\Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors",
                    "Qwen-image\\Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors",
                ],
            }.get(folder_name, [])
        )
        snapshot = discover_model_inventory(folder_paths_module=module)

        self.assertEqual(
            resolve_template_lora_selector_context("flux", snapshot),
            "Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors",
        )
        self.assertEqual(
            resolve_template_lora_selector_context("qwen_image", snapshot),
            "Qwen-image\\Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors",
        )
        self.assertEqual(
            resolve_template_lora_selector_context("qwen_image_edit", snapshot),
            "Qwen-image\\Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors",
        )

        category_id, selectors, default_model = resolve_primary_model_selector_context("qwen_image_edit", snapshot)
        self.assertEqual(category_id, "diffusion_models")
        self.assertIn(default_model, selectors)
        self.assertEqual(default_model, "qwen\\qwen_image_edit_fp8_e4m3fn.safetensors")

    def test_resolve_primary_model_selector_prefers_non_lightning_qwen_default(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": [
                    "qwen\\Qwen-Image-Lightning-8steps.safetensors",
                    "qwen\\qwen_image_2512_fp8_e4m3fn.safetensors",
                    "qwen\\qwen_image_2512_2step_distilled.safetensors",
                ],
                "vae": ["Automatic"],
                "text_encoders": ["qwen_3_4b.safetensors", "qwen_2.5_vl_7b_fp8_scaled.safetensors"],
            }.get(folder_name, [])
        )
        snapshot = discover_model_inventory(folder_paths_module=module)

        category_id, selectors, default_model = resolve_primary_model_selector_context("qwen_image", snapshot)
        self.assertEqual(category_id, "diffusion_models")
        self.assertIn(default_model, selectors)
        self.assertEqual(default_model, "qwen\\qwen_image_2512_fp8_e4m3fn.safetensors")

        text_encoder = resolve_text_encoder_selector_context("qwen_image", snapshot)
        self.assertEqual(text_encoder, "qwen_2.5_vl_7b_fp8_scaled.safetensors")

    def test_resolve_primary_model_selector_prefers_non_distilled_legacy_klein_alias_default(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": [
                    "klein\\flux-2-klein-4b.safetensors",
                    "klein\\flux-2-klein-base-4b.safetensors",
                    "klein\\flux-2-klein-base-9b-fp8.safetensors",
                ],
                "vae": ["flux2-vae.safetensors", "full_encoder_small_decoder.safetensors"],
                "text_encoders": ["qwen_3_4b.safetensors", "qwen_3_8b_fp8mixed.safetensors"],
            }.get(folder_name, [])
        )
        snapshot = discover_model_inventory(folder_paths_module=module)

        category_id, selectors, default_model = resolve_primary_model_selector_context("klein", snapshot)
        self.assertEqual(category_id, "diffusion_models")
        self.assertIn(default_model, selectors)
        self.assertEqual(default_model, "klein\\flux-2-klein-base-4b.safetensors")

        text_encoder = resolve_text_encoder_selector_context("klein", snapshot)
        self.assertEqual(text_encoder, "qwen_3_4b.safetensors")

    def test_discover_model_inventory_uses_ttl_cache_for_host_lookup(self) -> None:
        call_count = 0

        def _getter(folder_name: str) -> list[str]:
            nonlocal call_count
            call_count += 1
            return {
                "checkpoints": ["cache-checkpoint.safetensors"],
                "vae": ["Automatic"],
                "text_encoders": ["Automatic"],
            }.get(folder_name, [])

        module = types.SimpleNamespace(get_filename_list=_getter)
        with mock.patch(
            "rookieui.services.model_inventory._load_folder_paths_module",
            return_value=module,
        ):
            first = discover_model_inventory()
            second = discover_model_inventory()

        self.assertEqual(first.default_checkpoint, "cache-checkpoint.safetensors")
        self.assertEqual(second.default_checkpoint, "cache-checkpoint.safetensors")
        self.assertEqual(call_count, 12)
