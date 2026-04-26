from __future__ import annotations

import unittest

from rookieui.contracts.prompt_workbench_ui_parity import (
    PROMPT_WORKBENCH_UI_EVIDENCE_TYPES,
    PROMPT_WORKBENCH_UI_PARITY_CLASSES,
    build_prompt_workbench_ui_parity_payload,
)


class PromptWorkbenchUiParityContractTests(unittest.TestCase):
    def test_contract_freezes_required_prompt_all_in_one_ui_primitives(self) -> None:
        payload = build_prompt_workbench_ui_parity_payload()
        primitives = {entry["primitive_id"]: entry for entry in payload["primitives"]}

        self.assertEqual(
            {
                "inline_surface_root",
                "fold_unfold",
                "inline_toolbar_row",
                "counter_language_status",
                "popover_anchor_buttons",
                "inline_append_dropdown",
                "inline_suggestions",
                "inline_token_tags",
                "token_hover_quick_actions",
                "bilingual_token_row",
                "selection_batch_toolbar",
                "group_tags_tab_board",
                "namespace_accessibility",
                "a1111_textarea_hijack",
            },
            set(primitives),
        )
        self.assertEqual(primitives["a1111_textarea_hijack"]["parity_class"], "out_of_scope")
        self.assertEqual(primitives["inline_surface_root"]["implementation_item"], "inline_surface_mount")
        self.assertEqual(primitives["inline_token_tags"]["implementation_item"], "inline_token_tags")
        self.assertEqual(primitives["namespace_accessibility"]["implementation_item"], "namespace_accessibility")

    def test_required_runtime_primitives_have_selectors_and_evidence(self) -> None:
        payload = build_prompt_workbench_ui_parity_payload()
        allowed_classes = set(PROMPT_WORKBENCH_UI_PARITY_CLASSES)
        allowed_evidence = set(PROMPT_WORKBENCH_UI_EVIDENCE_TYPES)

        for primitive in payload["primitives"]:
            self.assertIn(primitive["parity_class"], allowed_classes)
            self.assertTrue(primitive["reference_file"])
            self.assertTrue(primitive["reference_surface"])
            self.assertTrue(primitive["rookieui_target"])
            self.assertTrue(primitive["implementation_item"])
            self.assertTrue(primitive["evidence_required"])
            self.assertTrue(set(primitive["evidence_required"]) <= allowed_evidence)
            if primitive["parity_class"] != "out_of_scope":
                self.assertTrue(primitive["target_selector"])
                self.assertIn("unit_dom", primitive["evidence_required"])

    def test_contract_marks_reference_code_as_read_only_design_input(self) -> None:
        payload = build_prompt_workbench_ui_parity_payload()

        self.assertEqual(
            payload["contract"]["execution_policy"],
            "read_only_reference_code_no_execution",
        )
        self.assertIn(
            "current_capture",
            payload["contract"]["visual_claim_policy"],
        )


if __name__ == "__main__":
    unittest.main()
