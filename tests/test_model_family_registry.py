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
        self.assertIn("flux", [entry["id"] for entry in payload["entries"]])

    def test_registry_tracks_translation_and_public_family_separately(self) -> None:
        flux_entry = get_model_family_registry_entry("flux")

        self.assertEqual(flux_entry.translation_base_family, "sdxl")
        self.assertEqual(flux_entry.public_base_family, "flux")
        self.assertTrue(flux_entry.text_encoder_visible)
        self.assertEqual(flux_entry.primary_model_category, "diffusion_models")

    def test_primary_model_category_map_is_registry_derived(self) -> None:
        category_map = build_primary_model_category_by_family()

        self.assertEqual(category_map["pony"], "checkpoints")
        self.assertEqual(category_map["wan"], "diffusion_models")

    def test_compatibility_newer_family_profiles_are_registry_derived(self) -> None:
        payload = build_compatibility_payload()
        qwen_entry = next(entry for entry in payload["newer_family_profiles"] if entry["id"] == "qwen_image")

        self.assertTrue(qwen_entry["experimental"])
        self.assertIn("non-Lightning", qwen_entry["summary"])

    def test_presets_use_public_family_identity_for_newer_families(self) -> None:
        payload = build_preset_payload()
        flux_preset = next(preset for preset in payload["presets"] if preset["id"] == "flux")

        self.assertEqual(flux_preset["profile"], "flux")
        self.assertEqual(flux_preset["base_family"], "flux")
