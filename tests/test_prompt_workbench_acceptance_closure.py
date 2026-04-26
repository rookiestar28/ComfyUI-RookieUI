from __future__ import annotations

import unittest

from rookieui.api import routes
from rookieui.contracts.prompt_workbench_parity import build_prompt_workbench_parity_matrix_payload
from rookieui.services.prompt_workbench import (
    build_prompt_workbench_export_payload,
    build_prompt_workbench_provider_catalog_payload,
)


class PromptWorkbenchAcceptanceClosureTests(unittest.TestCase):
    def test_prompt_all_in_one_delivery_stages_are_executable_repository_facts(self) -> None:
        parity = build_prompt_workbench_parity_matrix_payload()
        features = {entry["feature_id"]: entry for entry in parity["features"]}

        self.assertEqual(features["a1111_gradio_textarea_hijack"]["parity_class"], "out_of_scope")
        self.assertEqual(features["workbench_i18n"]["delivery_stage"], "i18n_import_export")
        self.assertEqual(features["import_export"]["delivery_stage"], "i18n_import_export")
        self.assertIn("tests", features["workbench_i18n"]["acceptance_signal"])
        self.assertIn("secret", features["import_export"]["acceptance_signal"].lower())

        migrated_stages = {
            "host_integration",
            "token_editor",
            "translation_providers",
            "collections",
            "translation_blacklist",
            "catalog_highlighting",
            "settings",
            "bilingual_hotkeys",
            "i18n_import_export",
        }
        observed_stages = {entry["delivery_stage"] for entry in parity["features"]}
        self.assertLessEqual(migrated_stages, observed_stages)

    def test_prompt_tools_routes_and_provider_catalog_match_final_workbench_surface(self) -> None:
        route_paths = set(routes.build_bootstrap_payload()["routes"])
        required_routes = {
            "/rookieui/prompt-tools/config",
            "/rookieui/prompt-tools/state",
            "/rookieui/prompt-tools/history",
            "/rookieui/prompt-tools/favorites",
            "/rookieui/prompt-tools/blacklist",
            "/rookieui/prompt-tools/providers",
            "/rookieui/prompt-tools/export",
            "/rookieui/prompt-tools/import",
            "/rookieui/prompt-tools/translate",
            "/rookieui/prompt-tools/assist",
            "/rookieui/prompt-tools/catalog",
            "/rookieui/prompt-tools/analyze",
            "/rookieui/prompt-tools/upsample",
        }

        provider_payload = build_prompt_workbench_provider_catalog_payload()
        translation_surface = provider_payload["surfaces"]["translation"]
        provider_ids = {entry["provider_id"] for entry in translation_surface["providers"]}

        self.assertLessEqual(required_routes, route_paths)
        self.assertLessEqual({"csv_tag_dictionary", "mymemory_free", "openai"}, provider_ids)
        self.assertIn("local_host_model", translation_surface["deferred_provider_ids"])
        self.assertIn("google_free", translation_surface["reference_only_provider_ids"])

    def test_import_export_closure_keeps_provider_secrets_masked_by_default(self) -> None:
        export_payload = build_prompt_workbench_export_payload()

        self.assertEqual(export_payload["contract"]["surface"], "prompt_tools_export")
        self.assertEqual(export_payload["export"]["secret_policy"], "masked_provider_fields")  # pragma: allowlist secret
        self.assertIn("config", export_payload["export"]["includes"])
        self.assertIn("blacklist", export_payload["export"]["includes"])
        self.assertIn("surfaces", export_payload["export"]["includes"])


if __name__ == "__main__":
    unittest.main()
