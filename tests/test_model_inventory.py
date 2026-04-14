from __future__ import annotations

import types
import unittest
from unittest import mock

from rookieui.services.model_inventory import (
    _reset_inventory_cache_for_tests,
    discover_model_inventory,
    ensure_native_ultralytics_model_paths,
    resolve_primary_model_selector_context,
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
            payload["catalog"]["primary_model_category_by_family"]["wan"],
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
                    "qwen-image.safetensors",
                    "lumina2.safetensors",
                    "ZIT\\zImageTurboNSFW_21BF16AIO.safetensors",
                ],
                "vae": [
                    "qwen_image_vae.safetensors",
                    "lumina_vae.safetensors",
                ],
                "text_encoders": [
                    "QwenImageTEModel_.safetensors",
                    "clip_l.safetensors",
                    "LuminaTEModel.safetensors",
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
        self.assertEqual(preset_lookup["qwen_image"]["checkpoint_name"], "qwen-image.safetensors")
        self.assertEqual(preset_lookup["lumina"]["checkpoint_name"], "lumina2.safetensors")
        self.assertEqual(
            preset_lookup["zit"]["checkpoint_name"],
            "ZIT\\zImageTurboNSFW_21BF16AIO.safetensors",
        )
        self.assertEqual(
            preset_lookup["qwen_image"]["vae_name"],
            "qwen_image_vae.safetensors",
        )
        self.assertEqual(
            preset_lookup["lumina"]["vae_name"],
            "lumina_vae.safetensors",
        )
        self.assertEqual(
            preset_lookup["zit"]["vae_name"],
            "lumina_vae.safetensors",
        )
        self.assertEqual(
            preset_lookup["qwen_image"]["text_encoder_name"],
            "QwenImageTEModel_.safetensors",
        )
        self.assertEqual(
            preset_lookup["lumina"]["text_encoder_name"],
            "LuminaTEModel.safetensors",
        )
        self.assertEqual(
            preset_lookup["zit"]["text_encoder_name"],
            "LuminaTEModel.safetensors",
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
                "diffusion_models": ["lumina2.safetensors", "qwen-image.safetensors"],
                "vae": ["Automatic"],
                "text_encoders": ["QwenImageTEModel_.safetensors", "LuminaTEModel.safetensors"],
            }.get(folder_name, [])
        )
        snapshot = discover_model_inventory(folder_paths_module=module)

        qwen_selector = resolve_text_encoder_selector_context("qwen_image", snapshot)
        zit_selector = resolve_text_encoder_selector_context("zit", snapshot)

        self.assertEqual(qwen_selector, "QwenImageTEModel_.safetensors")
        self.assertEqual(zit_selector, "LuminaTEModel.safetensors")

    def test_resolve_vae_selector_context_avoids_qwen_default_for_non_qwen_diffusion_profiles(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": ["lumina2.safetensors", "qwen-image.safetensors"],
                "vae": ["qwen_image_vae.safetensors", "lumina_vae.safetensors"],
                "text_encoders": ["Automatic"],
            }.get(folder_name, [])
        )
        snapshot = discover_model_inventory(folder_paths_module=module)

        qwen_selector = resolve_vae_selector_context("qwen_image", snapshot)
        zit_selector = resolve_vae_selector_context("zit", snapshot)

        self.assertEqual(qwen_selector, "qwen_image_vae.safetensors")
        self.assertEqual(zit_selector, "lumina_vae.safetensors")

    def test_resolve_text_encoder_selector_context_disables_global_default_for_diffusion_profiles(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": ["lumina2.safetensors", "qwen-image.safetensors"],
                "vae": ["Automatic"],
                "text_encoders": ["Automatic"],
            }.get(folder_name, [])
        )
        snapshot = discover_model_inventory(folder_paths_module=module)

        zit_selector = resolve_text_encoder_selector_context("zit", snapshot)
        self.assertEqual(zit_selector, "")

    def test_resolve_vae_selector_context_disables_global_default_for_diffusion_profiles(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": ["lumina2.safetensors", "qwen-image.safetensors"],
                "vae": ["Automatic"],
                "text_encoders": ["Automatic"],
            }.get(folder_name, [])
        )
        snapshot = discover_model_inventory(folder_paths_module=module)

        zit_selector = resolve_vae_selector_context("zit", snapshot)
        self.assertEqual(zit_selector, "")

    def test_profile_matrix_uses_family_aligned_defaults_for_all_non_sd_diffusion_profiles(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": [
                    "flux\\flux1-dev.safetensors",
                    "qwen\\qwen-image.safetensors",
                    "klein\\flux2_klein.safetensors",
                    "lumina\\lumina2.safetensors",
                    "zit\\zImageTurboNSFW_21BF16AIO.safetensors",
                    "wan\\wan2_2b.safetensors",
                    "anima\\animaPencilXL_v500.safetensors",
                ],
                "vae": [
                    "qwen_image_vae.safetensors",
                    "flux_vae.safetensors",
                    "klein_vae.safetensors",
                    "lumina_vae.safetensors",
                    "wan_vae.safetensors",
                    "anima_vae.safetensors",
                ],
                "text_encoders": [
                    "QwenImageTEModel_.safetensors",
                    "FluxT5XXL.safetensors",
                    "KleinT5XXL.safetensors",
                    "LuminaTEModel.safetensors",
                    "WanTextEncoder.safetensors",
                    "AnimaTextEncoder.safetensors",
                ],
            }.get(folder_name, [])
        )
        snapshot = discover_model_inventory(folder_paths_module=module)
        non_sd_profiles = ["flux", "qwen_image", "klein", "lumina", "zit", "wan", "anima"]

        for profile_id in non_sd_profiles:
            with self.subTest(profile_id=profile_id):
                category_id, selectors, default_model = resolve_primary_model_selector_context(profile_id, snapshot)
                self.assertEqual(category_id, "diffusion_models")
                self.assertIn(default_model, selectors)

                resolved_text_encoder = resolve_text_encoder_selector_context(profile_id, snapshot)
                self.assertIn(resolved_text_encoder, snapshot.text_encoders)
                resolved_vae = resolve_vae_selector_context(profile_id, snapshot)
                self.assertIn(resolved_vae, snapshot.vae)
                if profile_id == "qwen_image":
                    self.assertIn("qwen", resolved_text_encoder.lower())
                    self.assertIn("qwen", resolved_vae.lower())
                else:
                    self.assertNotIn("qwen", resolved_text_encoder.lower())
                    self.assertNotIn("qwen", resolved_vae.lower())

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

    def test_resolve_primary_model_selector_prefers_non_lightning_wan_default(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": [
                    "wan\\wan2.2_t2v_lightx2v_4steps.safetensors",
                    "wan\\wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors",
                    "wan\\wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
                ],
                "vae": ["Automatic"],
                "text_encoders": ["wan_text_encoder.safetensors", "umt5_xxl_fp8_e4m3fn_scaled.safetensors"],
            }.get(folder_name, [])
        )
        snapshot = discover_model_inventory(folder_paths_module=module)

        category_id, selectors, default_model = resolve_primary_model_selector_context("wan", snapshot)
        self.assertEqual(category_id, "diffusion_models")
        self.assertIn(default_model, selectors)
        self.assertEqual(default_model, "wan\\wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors")

        text_encoder = resolve_text_encoder_selector_context("wan", snapshot)
        self.assertEqual(text_encoder, "umt5_xxl_fp8_e4m3fn_scaled.safetensors")

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
