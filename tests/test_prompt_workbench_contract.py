from __future__ import annotations

import unittest

from rookieui.contracts.prompt_workbench import (
    PROMPT_WORKBENCH_CONTRACT_VERSION,
    PROMPT_WORKBENCH_NAMESPACES,
    PROMPT_WORKBENCH_PROVIDER_SECRET_FIELD_KEYS,
    PROMPT_WORKBENCH_ROUTE_FAMILY,
    PROMPT_WORKBENCH_STATE_SCHEMA_VERSION,
    PromptWorkbenchBootstrapSnapshot,
    build_default_prompt_workbench_surface_state,
    build_prompt_workbench_contract_meta,
    build_prompt_workbench_provider_catalog_payload,
)


class PromptWorkbenchContractTests(unittest.TestCase):
    def test_prompt_workbench_contract_meta_freezes_route_family_and_namespaces(self) -> None:
        payload = build_prompt_workbench_contract_meta()

        self.assertEqual(payload["version"], PROMPT_WORKBENCH_CONTRACT_VERSION)
        self.assertEqual(payload["route_family"], PROMPT_WORKBENCH_ROUTE_FAMILY)
        self.assertEqual(payload["state_schema_version"], PROMPT_WORKBENCH_STATE_SCHEMA_VERSION)
        self.assertEqual(payload["namespaces"], PROMPT_WORKBENCH_NAMESPACES)
        self.assertIn("api_key", payload["provider_secret_field_keys"])

    def test_default_surface_state_keeps_namespace_specific_editor_defaults(self) -> None:
        payload = build_default_prompt_workbench_surface_state("txt2img_prompt")

        self.assertEqual(payload["namespace"], "txt2img_prompt")
        self.assertFalse(payload["workbench_open"])
        self.assertEqual(payload["active_panel"], "editor")
        self.assertEqual(payload["draft_prompt"], "")

    def test_bootstrap_snapshot_includes_masking_rule_and_blacklist_defaults(self) -> None:
        payload = PromptWorkbenchBootstrapSnapshot().to_payload()

        self.assertEqual(payload["contract"]["provider_secret_field_keys"], PROMPT_WORKBENCH_PROVIDER_SECRET_FIELD_KEYS)
        self.assertEqual(payload["config"]["formatting_rules"]["dedupe_commas"], True)
        self.assertEqual(payload["blacklist"], {"enabled": False, "entries": []})

    def test_provider_catalog_truthfully_marks_shipped_and_reference_only_entries(self) -> None:
        payload = build_prompt_workbench_provider_catalog_payload()

        translation_surface = payload["surfaces"]["translation"]
        shipped_ids = translation_surface["shipped_provider_ids"]
        reference_only_ids = translation_surface["reference_only_provider_ids"]
        openai_entry = next(
            provider for provider in translation_surface["providers"] if provider["provider_id"] == "openai"
        )

        self.assertIn("openai", shipped_ids)
        self.assertIn("mymemory_free", shipped_ids)
        self.assertIn("google_free", reference_only_ids)
        self.assertEqual(openai_entry["title"], "OpenAI-Compatible Chat Translation")
        self.assertEqual(
            payload["surfaces"]["ai_assist"]["shipped_provider_ids"],
            ["openai"],
        )
