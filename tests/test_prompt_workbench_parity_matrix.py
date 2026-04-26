from __future__ import annotations

import unittest

from rookieui.contracts.prompt_workbench_parity import (
    PROMPT_WORKBENCH_PARITY_CLASSES,
    PROMPT_WORKBENCH_TRANSLATION_PROVIDER_LAYER_ORDER,
    build_prompt_workbench_parity_matrix_payload,
)


class PromptWorkbenchParityMatrixTests(unittest.TestCase):
    def test_feature_matrix_freezes_required_prompt_all_in_one_concepts(self) -> None:
        payload = build_prompt_workbench_parity_matrix_payload()
        features = {entry["feature_id"]: entry for entry in payload["features"]}

        required_feature_ids = {
            "prompt_field_binding",
            "token_tag_model",
            "token_quick_actions",
            "quick_weight_adjustment",
            "automatic_translation",
            "manual_batch_translation",
            "translation_provider_matrix",
            "history",
            "favorites",
            "prompt_blacklist",
            "translation_blacklist",
            "batch_operations",
            "group_tags_catalog",
            "tagcomplete_lookup",
            "extra_network_highlighting",
            "themes",
            "settings",
            "prompt_field_visibility",
            "bilingual_token_display",
            "hotkeys",
            "workbench_i18n",
            "import_export",
            "a1111_gradio_textarea_hijack",
        }

        self.assertEqual(required_feature_ids, set(features))
        self.assertEqual(features["a1111_gradio_textarea_hijack"]["parity_class"], "out_of_scope")
        self.assertEqual(features["prompt_field_binding"]["parity_class"], "implemented")
        self.assertEqual(features["translation_provider_matrix"]["parity_class"], "optional_provider")

    def test_matrix_uses_only_allowed_parity_classes_and_unique_ids(self) -> None:
        payload = build_prompt_workbench_parity_matrix_payload()
        allowed_classes = set(PROMPT_WORKBENCH_PARITY_CLASSES)
        feature_ids = [entry["feature_id"] for entry in payload["features"]]
        provider_ids = [entry["provider_id"] for entry in payload["providers"]]

        self.assertEqual(len(feature_ids), len(set(feature_ids)))
        self.assertEqual(len(provider_ids), len(set(provider_ids)))
        for entry in payload["features"]:
            self.assertIn(entry["parity_class"], allowed_classes)
            self.assertTrue(entry["acceptance_signal"])
        for entry in payload["providers"]:
            self.assertIn(entry["parity_class"], allowed_classes)
            self.assertTrue(entry["acceptance_signal"])

    def test_translation_route_order_matches_planned_provider_mainline(self) -> None:
        payload = build_prompt_workbench_parity_matrix_payload()

        self.assertEqual(
            payload["translation_provider_layer_order"],
            list(PROMPT_WORKBENCH_TRANSLATION_PROVIDER_LAYER_ORDER),
        )
        self.assertEqual(
            payload["translation_provider_layer_order"],
            [
                "csv_tag_dictionary",
                "shipped_lightweight",
                "optional_openai_compatible",
                "optional_local_host_model",
            ],
        )

    def test_provider_matrix_classifies_baseline_optional_and_reference_only_routes(self) -> None:
        payload = build_prompt_workbench_parity_matrix_payload()
        providers = {entry["provider_id"]: entry for entry in payload["providers"]}

        self.assertEqual(providers["csv_tag_dictionary"]["provider_layer"], "csv_tag_dictionary")
        self.assertEqual(providers["csv_tag_dictionary"]["baseline_dependency"], "none")
        self.assertEqual(providers["mymemory_free"]["provider_layer"], "shipped_lightweight")
        self.assertEqual(providers["openai_compatible"]["provider_layer"], "optional_openai_compatible")
        self.assertEqual(providers["local_host_model"]["provider_layer"], "optional_local_host_model")
        self.assertEqual(providers["deepl"]["parity_class"], "reference_only")
        self.assertEqual(providers["google_free"]["parity_class"], "reference_only")
        self.assertEqual(providers["iflytekv2"]["parity_class"], "reference_only")

    def test_translate_gemma_is_not_a_provider_or_fallback(self) -> None:
        payload = build_prompt_workbench_parity_matrix_payload()
        serialized = repr(payload).lower()

        self.assertNotIn("translategemma", serialized)
        self.assertNotIn("translate_gemma", serialized)
        self.assertNotIn("gemma", serialized)


if __name__ == "__main__":
    unittest.main()
