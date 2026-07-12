from __future__ import annotations

import unittest

from rookieui.contracts.family_template_manifest import (
    OFFICIAL_TEMPLATE_CORE_BLUEPRINT_DEFERRED_SURFACE_MARKERS,
    OFFICIAL_TEMPLATE_DEFERRED_SURFACE_MARKERS,
    OFFICIAL_TEMPLATE_GALLERY_JSON_DEFERRED_SURFACE_MARKERS,
    OFFICIAL_TEMPLATE_GALLERY_JSON_REMOVED_MARKERS,
    OFFICIAL_TEMPLATE_SOURCE_VERSION,
)
from rookieui.contracts.model_family_registry import (
    MODEL_FAMILY_REGISTRY_CONTRACT_VERSION,
    build_model_family_registry_payload,
    build_primary_model_category_by_family,
    get_model_family_registry_entry,
    list_model_family_registry_entries,
    model_family_supports_surface_flow,
)
from rookieui.services.compatibility import build_compatibility_payload
from rookieui.services.presets import build_preset_payload


class ModelFamilyRegistryTests(unittest.TestCase):
    def test_registry_payload_exposes_contract_version_and_entries(self) -> None:
        payload = build_model_family_registry_payload()

        self.assertEqual(payload["contract_version"], MODEL_FAMILY_REGISTRY_CONTRACT_VERSION)
        self.assertEqual(payload["entries"][0]["id"], "sd15")
        self.assertIn("chroma", [entry["id"] for entry in payload["entries"]])
        self.assertIn("flux", [entry["id"] for entry in payload["entries"]])
        self.assertIn("ideogram4", [entry["id"] for entry in payload["entries"]])
        self.assertIn("krea2_turbo", [entry["id"] for entry in payload["entries"]])
        self.assertIn("ernie_image", [entry["id"] for entry in payload["entries"]])
        self.assertNotIn("qwen_image_edit_multi_lora", [entry["id"] for entry in payload["entries"]])
        self.assertNotIn("klein_4b_distilled", [entry["id"] for entry in payload["entries"]])
        self.assertNotIn("klein_9b_distilled", [entry["id"] for entry in payload["entries"]])
        self.assertIn("firered_image_edit", [entry["id"] for entry in payload["entries"]])
        self.assertIn("firered_image_edit_lightning", [entry["id"] for entry in payload["entries"]])
        self.assertIn("flux_kontext_dev_edit", [entry["id"] for entry in payload["entries"]])
        self.assertIn("flux2_image_edit", [entry["id"] for entry in payload["entries"]])
        self.assertIn("klein_9b_kv_image_edit", [entry["id"] for entry in payload["entries"]])
        self.assertIn("longcat_image_edit", [entry["id"] for entry in payload["entries"]])
        self.assertIn("z_image_turbo", [entry["id"] for entry in payload["entries"]])

    def test_registry_declares_exact_effective_parameter_policy_matrix(self) -> None:
        entries = list_model_family_registry_entries()
        scheduler_overrides = {
            entry.id: entry.scheduler_control_mode
            for entry in entries
            if entry.scheduler_control_mode != "generic"
        }
        negative_overrides = {
            entry.id: entry.negative_prompt_mode
            for entry in entries
            if entry.negative_prompt_mode != "encoded"
        }

        self.assertEqual(
            scheduler_overrides,
            {
                "flux2_dev": "flux2",
                "ideogram4": "ideogram4",
                "klein_4b": "flux2",
                "klein_9b": "flux2",
                "flux2_image_edit": "flux2",
                "klein_9b_kv_image_edit": "flux2",
            },
        )
        self.assertEqual(
            negative_overrides,
            {
                "ernie_image_turbo": "zeroed",
                "flux": "zeroed",
                "flux_krea_dev": "zeroed",
                "flux2_dev": "unused",
                "ideogram4": "zeroed",
                "krea2_turbo": "zeroed",
                "qwen_image": "zeroed",
                "flux_kontext_dev_edit": "zeroed",
                "flux2_image_edit": "unused",
                "klein_9b_kv_image_edit": "zeroed",
                "z_image_turbo": "zeroed",
            },
        )
        self.assertTrue(all(entry.scheduler_control_mode in {"generic", "flux2", "ideogram4"} for entry in entries))
        self.assertTrue(all(entry.negative_prompt_mode in {"encoded", "zeroed", "unused"} for entry in entries))

        payload_by_id = {entry["id"]: entry for entry in build_model_family_registry_payload()["entries"]}
        presets_by_id = {preset["id"]: preset for preset in build_preset_payload()["presets"]}
        for profile_id, scheduler_mode in scheduler_overrides.items():
            with self.subTest(profile_id=profile_id):
                self.assertEqual(payload_by_id[profile_id]["scheduler_control_mode"], scheduler_mode)
                self.assertEqual(presets_by_id[profile_id]["scheduler_name"], "")

    def test_official_template_manifest_uses_current_workflow_template_basis(self) -> None:
        self.assertEqual(OFFICIAL_TEMPLATE_SOURCE_VERSION, "0.11.6")
        entries = list_model_family_registry_entries()
        stale_source_markers = ("0.9.91", "0.9.98", "0.10.3")
        stale_entries = [
            entry.id
            for entry in entries
            if any(
                marker in " ".join((entry.compatibility_summary, *entry.notes, entry.official_template_path))
                for marker in stale_source_markers
            )
        ]

        self.assertEqual(stale_entries, [])
        source_paths = {entry.id: entry.official_template_path for entry in entries}
        self.assertEqual(source_paths["anima"], "reference/ComfyUI/blueprints/Text to Image (Anima).json")
        self.assertEqual(source_paths["flux"], "reference/ComfyUI/blueprints/Text to Image (Flux.1 Dev).json")
        self.assertEqual(source_paths["ideogram4"], "reference/ComfyUI/blueprints/Text to Image (Ideogram v4).json")
        self.assertEqual(
            source_paths["krea2_turbo"],
            "comfyui-workflow-templates-json==0.1.3:image_krea2_turbo_t2i.json",
        )
        self.assertEqual(
            source_paths["flux2_image_edit"],
            "reference/ComfyUI/blueprints/Image Edit (Flux.2 Dev).json",
        )

    def test_host_0_11_2_blueprint_product_surface_delta_is_tracked_as_deferred_or_follow_up(self) -> None:
        observed_host_blueprint_markers = (
            "Character Replacement (SCAIL-2 Base)",
            "Character Replacement (SCAIL-2 Extend)",
            "Image Depth Estimation (Depth Anything 3)",
            "Video Depth Estimation (Depth Anything 3)",
            "Image Edit (Bernini-R)",
            "Video Edit (Bernini-R)",
            "Image to Gaussian Splat (TripoSplat)",
            "Text to Image (Anima Base 1.0)",
        )

        for observed_marker in observed_host_blueprint_markers:
            with self.subTest(observed_marker=observed_marker):
                self.assertIn(observed_marker, OFFICIAL_TEMPLATE_CORE_BLUEPRINT_DEFERRED_SURFACE_MARKERS)
        self.assertNotIn("Text to Image (Ideogram v4)", OFFICIAL_TEMPLATE_CORE_BLUEPRINT_DEFERRED_SURFACE_MARKERS)

    def test_host_0_11_6_gallery_json_delta_is_tracked_separately(self) -> None:
        expected_deferred_gallery_markers = (
            "api_ideogram_v4_t2i",
            "api_krea2_t2i",
            "api_krea2_style_reference",
            "api_google_gemini_omni_flash_i2v",
            "api_google_gemini_omni_flash_t2v",
            "api_google_gemini_omni_flash_video_edit",
            "api_happyhorse1_1_i2v",
            "api_happyhorse1_1_r2v",
            "api_happyhorse1_1_t2v",
            "api_nano_banana_2_lite_image_edit",
            "api_nano_banana_2_lite_t2i",
            "api_seedance2_0_mini_r2v",
            "api_seedance2_0_mini_t2v",
            "api_seedance2_0_r2v_4k",
        )
        expected_removed_gallery_markers = (
            "api_ideogram_v3_t2i",
            "api_openai_sora_video",
            "api_stability_ai_audio_inpaint",
            "api_stability_ai_audio_to_audio",
            "api_stability_ai_i2i",
            "api_stability_ai_sd3.5_i2i",
            "api_stability_ai_sd3.5_t2i",
            "api_stability_ai_stable_image_ultra_t2i",
            "api_stability_ai_text_to_audio",
            "api_stability_upscale_fast",
        )

        self.assertGreater(len(OFFICIAL_TEMPLATE_CORE_BLUEPRINT_DEFERRED_SURFACE_MARKERS), 0)
        self.assertGreater(len(OFFICIAL_TEMPLATE_GALLERY_JSON_DEFERRED_SURFACE_MARKERS), 0)
        self.assertGreater(len(OFFICIAL_TEMPLATE_GALLERY_JSON_REMOVED_MARKERS), 0)
        self.assertFalse(
            set(OFFICIAL_TEMPLATE_CORE_BLUEPRINT_DEFERRED_SURFACE_MARKERS)
            & set(OFFICIAL_TEMPLATE_GALLERY_JSON_DEFERRED_SURFACE_MARKERS)
        )

        for marker in expected_deferred_gallery_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, OFFICIAL_TEMPLATE_GALLERY_JSON_DEFERRED_SURFACE_MARKERS)
                self.assertIn(marker, OFFICIAL_TEMPLATE_DEFERRED_SURFACE_MARKERS)
        for marker in expected_removed_gallery_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, OFFICIAL_TEMPLATE_GALLERY_JSON_REMOVED_MARKERS)
                self.assertIn(marker, OFFICIAL_TEMPLATE_DEFERRED_SURFACE_MARKERS)
        self.assertNotIn("image_ideogram4_t2i", OFFICIAL_TEMPLATE_GALLERY_JSON_DEFERRED_SURFACE_MARKERS)
        self.assertNotIn("image_krea2_turbo_t2i", OFFICIAL_TEMPLATE_GALLERY_JSON_DEFERRED_SURFACE_MARKERS)

    def test_deferred_product_surface_candidates_are_not_exposed_as_current_profiles(self) -> None:
        manifest_text = "\n".join(
            " ".join(
                (
                    entry.id,
                    entry.title,
                    entry.compatibility_summary,
                    entry.official_template_path,
                    *entry.aliases,
                    *entry.notes,
                )
            )
            for entry in list_model_family_registry_entries()
        )

        for deferred_marker in OFFICIAL_TEMPLATE_DEFERRED_SURFACE_MARKERS:
            with self.subTest(deferred_marker=deferred_marker):
                self.assertNotIn(deferred_marker, manifest_text)

    def test_registry_tracks_translation_and_public_family_separately(self) -> None:
        flux_entry = get_model_family_registry_entry("flux")
        z_turbo_entry = get_model_family_registry_entry("zit")
        chroma_entry = get_model_family_registry_entry("chroma")
        ernie_entry = get_model_family_registry_entry("ernie_image")
        ideogram_entry = get_model_family_registry_entry("ideogram v4")
        flux2_entry = get_model_family_registry_entry("flux2_dev")
        krea2_entry = get_model_family_registry_entry("krea2_turbo")
        krea_entry = get_model_family_registry_entry("krea 2")
        longcat_entry = get_model_family_registry_entry("longcat_image")

        self.assertEqual(flux_entry.translation_base_family, "sdxl")
        self.assertEqual(flux_entry.public_base_family, "flux")
        self.assertFalse(flux_entry.text_encoder_visible)
        self.assertEqual(flux_entry.primary_model_category, "diffusion_models")
        self.assertTrue(flux_entry.template_lora_visible)
        self.assertTrue(flux_entry.template_lora_override_allowed)
        self.assertEqual(flux_entry.official_template_lora_label, "Flux_2-Turbo-LoRA_comfyui.safetensors")
        self.assertTrue(chroma_entry.shift_visible)
        self.assertEqual(chroma_entry.default_shift, 1.0)
        self.assertTrue(ernie_entry.prompt_enhancement_visible)
        self.assertTrue(ernie_entry.default_prompt_enhancement_enabled)
        self.assertEqual(ideogram_entry.id, "ideogram4")
        self.assertEqual(ideogram_entry.public_base_family, "ideogram4")
        self.assertEqual(ideogram_entry.default_cfg_scale, 7.0)
        self.assertEqual(ideogram_entry.default_ideogram_mode, "default")
        self.assertEqual(ideogram_entry.ideogram_modes, ("quality", "default", "turbo"))
        self.assertFalse(ideogram_entry.text_encoder_visible)
        self.assertFalse(flux2_entry.default_template_lora_enabled)
        self.assertEqual(flux2_entry.default_template_lora_strength, 1.0)
        self.assertFalse(krea2_entry.default_template_lora_enabled)
        self.assertEqual(krea2_entry.default_template_lora_strength, 0.8)
        self.assertEqual(krea2_entry.default_template_lora_trigger_word, "muted minimalist sketch style")
        self.assertEqual(ideogram_entry.official_template_path, "reference/ComfyUI/blueprints/Text to Image (Ideogram v4).json")
        self.assertEqual(krea_entry.id, "krea2_turbo")
        self.assertEqual(krea_entry.public_base_family, "krea2")
        self.assertEqual(krea_entry.default_steps, 8)
        self.assertEqual(krea_entry.default_cfg_scale, 1.0)
        self.assertTrue(krea_entry.template_lora_visible)
        self.assertTrue(krea_entry.template_lora_override_allowed)
        self.assertTrue(longcat_entry.flux_guidance_visible)
        self.assertEqual(longcat_entry.default_flux_guidance, 4.0)
        self.assertEqual(z_turbo_entry.id, "z_image_turbo")
        self.assertEqual(z_turbo_entry.public_base_family, "z_image")
        self.assertEqual(flux_entry.available_surface_flows, ("txt2img",))
        self.assertEqual(get_model_family_registry_entry("sd15").available_surface_flows, ("txt2img", "img2img"))

    def test_edit_profile_uses_img2img_surface_contract(self) -> None:
        qwen_edit_entry = get_model_family_registry_entry("qwen_image_edit")
        firered_entry = get_model_family_registry_entry("firered image edit")
        firered_lightning_entry = get_model_family_registry_entry("firered image edit lightning")
        kontext_edit_entry = get_model_family_registry_entry("flux kontext edit")
        flux2_edit_entry = get_model_family_registry_entry("flux2 image edit")
        klein_kv_edit_entry = get_model_family_registry_entry("klein kv edit")
        longcat_edit_entry = get_model_family_registry_entry("longcat image edit")
        qwen_entry = get_model_family_registry_entry("qwen_image")

        self.assertEqual(qwen_edit_entry.flow_kind, "edit")
        self.assertEqual(qwen_edit_entry.available_surface_flows, ("img2img",))
        self.assertTrue(qwen_edit_entry.image_edit_profile)
        self.assertEqual(qwen_edit_entry.request_contract_surface, "img2img")
        self.assertEqual(qwen_edit_entry.reference_input_mode, "single")
        self.assertEqual(qwen_edit_entry.max_direct_references, 1)
        self.assertEqual(qwen_edit_entry.encoder_family, "qwen_image_edit")
        self.assertEqual(qwen_edit_entry.template_lora_chain_mode, "single")
        self.assertFalse(model_family_supports_surface_flow("qwen_image_edit", "txt2img"))
        self.assertTrue(model_family_supports_surface_flow("qwen_image_edit", "img2img"))
        self.assertFalse(model_family_supports_surface_flow("qwen_image_edit", "edit"))
        self.assertEqual(firered_entry.reference_input_mode, "multi")
        self.assertEqual(firered_entry.max_direct_references, 3)
        self.assertEqual(firered_entry.encoder_family, "qwen_image_edit_plus")
        self.assertFalse(firered_entry.template_lora_visible)
        self.assertTrue(model_family_supports_surface_flow("firered_image_edit", "img2img"))
        self.assertTrue(firered_lightning_entry.template_lora_visible)
        self.assertEqual(
            firered_lightning_entry.official_template_lora_label,
            "FireRed-Image-Edit-1.0-Lightning-8steps-v1.0.safetensors",
        )
        self.assertEqual(kontext_edit_entry.reference_input_mode, "multi")
        self.assertEqual(kontext_edit_entry.max_direct_references, 3)
        self.assertEqual(kontext_edit_entry.encoder_family, "flux_clip_text")
        self.assertTrue(kontext_edit_entry.flux_guidance_visible)
        self.assertTrue(model_family_supports_surface_flow("flux_kontext_dev_edit", "img2img"))
        self.assertEqual(flux2_edit_entry.reference_input_mode, "single")
        self.assertEqual(flux2_edit_entry.max_direct_references, 1)
        self.assertTrue(flux2_edit_entry.edit_megapixels_visible)
        self.assertTrue(flux2_edit_entry.flux_guidance_visible)
        self.assertEqual(klein_kv_edit_entry.reference_input_mode, "multi")
        self.assertEqual(klein_kv_edit_entry.max_direct_references, 3)
        self.assertEqual(klein_kv_edit_entry.encoder_family, "flux_clip_text")
        self.assertTrue(klein_kv_edit_entry.edit_megapixels_visible)
        self.assertEqual(longcat_edit_entry.reference_input_mode, "single")
        self.assertEqual(longcat_edit_entry.max_direct_references, 1)
        self.assertEqual(longcat_edit_entry.encoder_family, "qwen_image_edit")
        self.assertTrue(longcat_edit_entry.flux_guidance_visible)
        self.assertTrue(qwen_entry.template_lora_visible)
        self.assertTrue(qwen_entry.template_lora_override_allowed)
        self.assertEqual(
            qwen_entry.official_template_lora_label,
            "Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors",
        )
        self.assertTrue(qwen_edit_entry.template_lora_visible)
        self.assertTrue(qwen_edit_entry.template_lora_override_allowed)
        self.assertEqual(
            qwen_edit_entry.official_template_lora_label,
            "Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors",
        )

    def test_primary_model_category_map_is_registry_derived(self) -> None:
        category_map = build_primary_model_category_by_family()

        self.assertEqual(category_map["pony"], "checkpoints")
        self.assertEqual(category_map["klein"], "diffusion_models")
        self.assertEqual(category_map["hidream"], "diffusion_models")
        self.assertEqual(category_map["ideogram4"], "diffusion_models")
        self.assertEqual(category_map["krea2"], "diffusion_models")
        self.assertEqual(category_map["lumina"], "diffusion_models")
        self.assertEqual(category_map["ernie_image"], "diffusion_models")

    def test_compatibility_newer_family_profiles_are_registry_derived(self) -> None:
        payload = build_compatibility_payload()
        qwen_entry = next(entry for entry in payload["newer_family_profiles"] if entry["id"] == "qwen_image")
        ernie_entry = next(entry for entry in payload["newer_family_profiles"] if entry["id"] == "ernie_image")
        chroma_entry = next(entry for entry in payload["newer_family_profiles"] if entry["id"] == "chroma")

        self.assertTrue(qwen_entry["experimental"])
        self.assertIn("Qwen-Image 2512", qwen_entry["summary"])
        self.assertIn("ERNIE-Image", ernie_entry["summary"])
        self.assertIn("Chroma", chroma_entry["summary"])

    def test_presets_use_public_family_identity_for_newer_families(self) -> None:
        payload = build_preset_payload()
        flux_preset = next(preset for preset in payload["presets"] if preset["id"] == "flux")
        ernie_preset = next(preset for preset in payload["presets"] if preset["id"] == "ernie_image")
        qwen_preset = next(preset for preset in payload["presets"] if preset["id"] == "qwen_image")
        qwen_edit_preset = next(preset for preset in payload["presets"] if preset["id"] == "qwen_image_edit")
        firered_preset = next(preset for preset in payload["presets"] if preset["id"] == "firered_image_edit")
        firered_lightning_preset = next(
            preset for preset in payload["presets"] if preset["id"] == "firered_image_edit_lightning"
        )
        kontext_edit_preset = next(preset for preset in payload["presets"] if preset["id"] == "flux_kontext_dev_edit")
        flux2_edit_preset = next(preset for preset in payload["presets"] if preset["id"] == "flux2_image_edit")
        ideogram_preset = next(preset for preset in payload["presets"] if preset["id"] == "ideogram4")
        flux2_preset = next(preset for preset in payload["presets"] if preset["id"] == "flux2_dev")
        krea2_preset = next(preset for preset in payload["presets"] if preset["id"] == "krea2_turbo")
        krea_preset = next(preset for preset in payload["presets"] if preset["id"] == "krea2_turbo")
        klein_kv_edit_preset = next(preset for preset in payload["presets"] if preset["id"] == "klein_9b_kv_image_edit")
        longcat_edit_preset = next(preset for preset in payload["presets"] if preset["id"] == "longcat_image_edit")
        z_turbo_preset = next(preset for preset in payload["presets"] if preset["id"] == "z_image_turbo")

        self.assertEqual(flux_preset["profile"], "flux")
        self.assertEqual(flux_preset["base_family"], "flux")
        self.assertIsNone(flux_preset["shift"])
        self.assertIn("template_lora_name", flux_preset)
        self.assertEqual(ernie_preset["profile"], "ernie_image")
        self.assertEqual(ernie_preset["base_family"], "ernie_image")
        self.assertTrue(ernie_preset["prompt_enhancement_enabled"])
        self.assertIn("template_lora_name", qwen_preset)
        self.assertIn("template_lora_name", qwen_edit_preset)
        self.assertTrue(qwen_edit_preset["image_edit_profile"])
        self.assertEqual(qwen_edit_preset["request_contract_surface"], "img2img")
        self.assertEqual(qwen_edit_preset["reference_input_mode"], "single")
        self.assertEqual(qwen_edit_preset["max_direct_references"], 1)
        self.assertEqual(firered_preset["base_family"], "firered_image_edit")
        self.assertEqual(firered_preset["reference_input_mode"], "multi")
        self.assertEqual(firered_preset["max_direct_references"], 3)
        self.assertEqual(firered_lightning_preset["template_lora_chain_mode"], "single")
        self.assertEqual(kontext_edit_preset["reference_input_mode"], "multi")
        self.assertEqual(kontext_edit_preset["max_direct_references"], 3)
        self.assertEqual(flux2_edit_preset["reference_input_mode"], "single")
        self.assertEqual(flux2_edit_preset["edit_megapixels"], 1.0)
        self.assertEqual(ideogram_preset["profile"], "ideogram4")
        self.assertEqual(ideogram_preset["base_family"], "ideogram4")
        self.assertEqual(ideogram_preset["steps"], 20)
        self.assertEqual(ideogram_preset["cfg_scale"], 7.0)
        self.assertEqual(ideogram_preset["ideogram_mode"], "default")
        self.assertFalse(flux2_preset["template_lora_enabled"])
        self.assertEqual(flux2_preset["template_lora_strength"], 1.0)
        self.assertFalse(krea2_preset["template_lora_enabled"])
        self.assertEqual(krea2_preset["template_lora_strength"], 0.8)
        self.assertEqual(krea2_preset["template_lora_trigger_word"], "muted minimalist sketch style")
        self.assertEqual(krea_preset["profile"], "krea2_turbo")
        self.assertEqual(krea_preset["base_family"], "krea2")
        self.assertEqual(krea_preset["steps"], 8)
        self.assertEqual(krea_preset["cfg_scale"], 1.0)
        self.assertEqual(klein_kv_edit_preset["reference_input_mode"], "multi")
        self.assertEqual(klein_kv_edit_preset["max_direct_references"], 3)
        self.assertEqual(longcat_edit_preset["flux_guidance"], 4.5)
        self.assertEqual(z_turbo_preset["profile"], "z_image_turbo")
        self.assertEqual(z_turbo_preset["base_family"], "z_image")
