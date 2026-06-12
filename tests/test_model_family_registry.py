from __future__ import annotations

import unittest

from rookieui.contracts.family_template_manifest import OFFICIAL_TEMPLATE_SOURCE_VERSION
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
        self.assertIn("ernie_image", [entry["id"] for entry in payload["entries"]])
        self.assertIn("qwen_image_edit_multi_lora", [entry["id"] for entry in payload["entries"]])
        self.assertIn("firered_image_edit", [entry["id"] for entry in payload["entries"]])
        self.assertIn("firered_image_edit_lightning", [entry["id"] for entry in payload["entries"]])
        self.assertIn("flux_kontext_dev_edit", [entry["id"] for entry in payload["entries"]])
        self.assertIn("flux2_image_edit", [entry["id"] for entry in payload["entries"]])
        self.assertIn("klein_9b_kv_image_edit", [entry["id"] for entry in payload["entries"]])
        self.assertIn("longcat_image_edit", [entry["id"] for entry in payload["entries"]])
        self.assertIn("z_image_turbo", [entry["id"] for entry in payload["entries"]])

    def test_official_template_manifest_uses_current_workflow_template_basis(self) -> None:
        self.assertEqual(OFFICIAL_TEMPLATE_SOURCE_VERSION, "0.9.98")
        entries = list_model_family_registry_entries()
        stale_entries = [
            entry.id
            for entry in entries
            if "0.9.91" in " ".join((entry.compatibility_summary, *entry.notes, entry.official_template_path))
        ]

        self.assertEqual(stale_entries, [])
        source_paths = {entry.id: entry.official_template_path for entry in entries}
        self.assertEqual(source_paths["anima"], "reference/ComfyUI/blueprints/Text to Image (Anima).json")
        self.assertEqual(source_paths["flux"], "reference/ComfyUI/blueprints/Text to Image (Flux.1 Dev).json")
        self.assertEqual(
            source_paths["flux2_image_edit"],
            "reference/ComfyUI/blueprints/Image Edit (Flux.2 Dev).json",
        )

    def test_product_surface_candidates_are_not_exposed_as_current_profiles(self) -> None:
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

        for deferred_marker in (
            "Image Inpainting (Qwen-image)",
            "Image Outpainting (Qwen-Image)",
            "Image to Layers(Qwen-Image-Layered)",
            "Image Upscale(Z-image-Turbo)",
            "Remove Background (BiRefNet)",
            "SAM3",
            "MoGe",
            "Mediapipe",
            "Lotus Depth",
            "Hunyuan3d",
            "Stable Audio",
            "ACE-Step",
            "Wan 2.2",
            "LTX-2.3",
            "Wan2.1 VACE",
            "VOID",
            "SDPose",
            "Gemini",
        ):
            with self.subTest(deferred_marker=deferred_marker):
                self.assertNotIn(deferred_marker, manifest_text)

    def test_registry_tracks_translation_and_public_family_separately(self) -> None:
        flux_entry = get_model_family_registry_entry("flux")
        z_turbo_entry = get_model_family_registry_entry("zit")
        chroma_entry = get_model_family_registry_entry("chroma")
        ernie_entry = get_model_family_registry_entry("ernie_image")
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
        self.assertTrue(longcat_entry.flux_guidance_visible)
        self.assertEqual(longcat_entry.default_flux_guidance, 4.0)
        self.assertEqual(z_turbo_entry.id, "z_image_turbo")
        self.assertEqual(z_turbo_entry.public_base_family, "z_image")
        self.assertEqual(flux_entry.available_surface_flows, ("txt2img",))
        self.assertEqual(get_model_family_registry_entry("sd15").available_surface_flows, ("txt2img", "img2img"))

    def test_edit_profile_uses_img2img_surface_contract(self) -> None:
        qwen_edit_entry = get_model_family_registry_entry("qwen_image_edit")
        qwen_edit_multi_entry = get_model_family_registry_entry("qwen_image_edit_multi_lora")
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
        self.assertEqual(qwen_edit_multi_entry.public_base_family, "qwen_image_edit")
        self.assertEqual(qwen_edit_multi_entry.template_lora_chain_mode, "triple")
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
        qwen_edit_multi_preset = next(
            preset for preset in payload["presets"] if preset["id"] == "qwen_image_edit_multi_lora"
        )
        firered_preset = next(preset for preset in payload["presets"] if preset["id"] == "firered_image_edit")
        firered_lightning_preset = next(
            preset for preset in payload["presets"] if preset["id"] == "firered_image_edit_lightning"
        )
        kontext_edit_preset = next(preset for preset in payload["presets"] if preset["id"] == "flux_kontext_dev_edit")
        flux2_edit_preset = next(preset for preset in payload["presets"] if preset["id"] == "flux2_image_edit")
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
        self.assertEqual(qwen_edit_multi_preset["template_lora_chain_mode"], "triple")
        self.assertEqual(firered_preset["base_family"], "firered_image_edit")
        self.assertEqual(firered_preset["reference_input_mode"], "multi")
        self.assertEqual(firered_preset["max_direct_references"], 3)
        self.assertEqual(firered_lightning_preset["template_lora_chain_mode"], "single")
        self.assertEqual(kontext_edit_preset["reference_input_mode"], "multi")
        self.assertEqual(kontext_edit_preset["max_direct_references"], 3)
        self.assertEqual(flux2_edit_preset["reference_input_mode"], "single")
        self.assertEqual(flux2_edit_preset["edit_megapixels"], 1.0)
        self.assertEqual(klein_kv_edit_preset["reference_input_mode"], "multi")
        self.assertEqual(klein_kv_edit_preset["max_direct_references"], 3)
        self.assertEqual(longcat_edit_preset["flux_guidance"], 4.5)
        self.assertEqual(z_turbo_preset["profile"], "z_image_turbo")
        self.assertEqual(z_turbo_preset["base_family"], "z_image")
