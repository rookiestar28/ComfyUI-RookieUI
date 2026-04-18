from __future__ import annotations

import unittest

from rookieui.contracts.model_family_registry import (
    MODEL_FAMILY_REGISTRY_CONTRACT_VERSION,
    build_model_family_registry_payload,
    build_primary_model_category_by_family,
    get_model_family_registry_entry,
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
        self.assertIn("z_image_turbo", [entry["id"] for entry in payload["entries"]])

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
        self.assertTrue(chroma_entry.shift_visible)
        self.assertEqual(chroma_entry.default_shift, 1.0)
        self.assertTrue(ernie_entry.prompt_enhancement_visible)
        self.assertTrue(ernie_entry.default_prompt_enhancement_enabled)
        self.assertTrue(longcat_entry.flux_guidance_visible)
        self.assertEqual(longcat_entry.default_flux_guidance, 4.0)
        self.assertEqual(z_turbo_entry.id, "z_image_turbo")
        self.assertEqual(z_turbo_entry.public_base_family, "z_image")

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
        z_turbo_preset = next(preset for preset in payload["presets"] if preset["id"] == "z_image_turbo")

        self.assertEqual(flux_preset["profile"], "flux")
        self.assertEqual(flux_preset["base_family"], "flux")
        self.assertIsNone(flux_preset["shift"])
        self.assertEqual(ernie_preset["profile"], "ernie_image")
        self.assertEqual(ernie_preset["base_family"], "ernie_image")
        self.assertTrue(ernie_preset["prompt_enhancement_enabled"])
        self.assertEqual(z_turbo_preset["profile"], "z_image_turbo")
        self.assertEqual(z_turbo_preset["base_family"], "z_image")
