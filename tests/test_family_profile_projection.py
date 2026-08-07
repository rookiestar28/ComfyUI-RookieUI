from __future__ import annotations

import dataclasses
import unittest

from rookieui.contracts.family_template_manifest import (
    CURRENT_HOST_DEFERRED_PROFILE_IDS,
    FamilyTemplateManifestEntry,
    _ALL_MANIFEST_ENTRIES,
)
from rookieui.contracts.family_profile_projection import (
    build_family_profile_projection,
    build_family_profile_projection_entries,
    validate_runtime_adapter_bindings,
)
from rookieui.contracts.model_family_registry import list_model_family_registry_entries
from rookieui.services.workflow_builders import non_sd_templates


EXPECTED_SHIPPED_PROFILE_IDS = (
    "sd15",
    "sdxl",
    "pony",
    "illustrious",
    "noob",
    "anima",
    "chroma",
    "ernie_image",
    "ernie_image_turbo",
    "flux",
    "flux_krea_dev",
    "flux2_dev",
    "ideogram4",
    "krea2_turbo",
    "klein_4b",
    "klein_9b",
    "hidream_i1_dev_fp8",
    "hidream_i1_fast",
    "hidream_i1_full",
    "longcat_image",
    "qwen_image",
    "qwen_image_edit",
    "qwen_image_edit_2511",
    "firered_image_edit",
    "firered_image_edit_lightning",
    "flux_kontext_dev_edit",
    "flux2_image_edit",
    "klein_9b_kv_image_edit",
    "longcat_image_edit",
    "z_image",
    "z_image_turbo",
)


class FamilyProfileProjectionTests(unittest.TestCase):
    def test_manifest_entry_is_frozen_and_projection_covers_every_declared_field(self) -> None:
        self.assertTrue(dataclasses.is_dataclass(FamilyTemplateManifestEntry))
        self.assertTrue(FamilyTemplateManifestEntry.__dataclass_params__.frozen)

        entry = list_model_family_registry_entries()[0]
        projection = build_family_profile_projection(entry)
        declared_fields = {field.name for field in dataclasses.fields(FamilyTemplateManifestEntry)}

        self.assertEqual(set(projection), declared_fields)
        self.assertEqual(projection["id"], entry.id)
        self.assertEqual(projection["aliases"], list(entry.aliases))
        self.assertEqual(projection["available_surface_flows"], list(entry.available_surface_flows))

    def test_shipped_projection_preserves_manifest_order_and_deferred_filter(self) -> None:
        entries = list_model_family_registry_entries()
        projections = build_family_profile_projection_entries(entries)

        self.assertEqual(tuple(projection["id"] for projection in projections), EXPECTED_SHIPPED_PROFILE_IDS)
        self.assertEqual(
            set(projection["id"] for projection in projections) & set(CURRENT_HOST_DEFERRED_PROFILE_IDS),
            set(),
        )
        all_ids = {entry.id for entry in _ALL_MANIFEST_ENTRIES}
        self.assertTrue(CURRENT_HOST_DEFERRED_PROFILE_IDS <= all_ids)
        self.assertEqual(
            tuple(entry.id for entry in _ALL_MANIFEST_ENTRIES if entry.id not in CURRENT_HOST_DEFERRED_PROFILE_IDS),
            EXPECTED_SHIPPED_PROFILE_IDS,
        )

    def test_runtime_adapter_bindings_are_complete_and_deferred_builders_are_not_dispatchable(self) -> None:
        errors = validate_runtime_adapter_bindings(
            list_model_family_registry_entries(),
            adapter_by_profile=non_sd_templates._NON_SD_RUNTIME_ADAPTER_BY_PROFILE,
            txt2img_builders=non_sd_templates._NON_SD_RUNTIME_BUILDERS,
            edit_builders=non_sd_templates._NON_SD_EDIT_RUNTIME_BUILDERS,
            deferred_profile_ids=CURRENT_HOST_DEFERRED_PROFILE_IDS,
        )
        self.assertEqual(errors, ())

    def test_runtime_adapter_validator_reports_missing_callable(self) -> None:
        errors = validate_runtime_adapter_bindings(
            list_model_family_registry_entries(),
            adapter_by_profile={"anima": "missing"},
            txt2img_builders={},
            edit_builders={},
            deferred_profile_ids=CURRENT_HOST_DEFERRED_PROFILE_IDS,
        )
        self.assertIn("anima: adapter 'missing' has no callable txt2img builder", errors)


if __name__ == "__main__":
    unittest.main()
