from __future__ import annotations

import re
import unittest
from pathlib import Path

from rookieui.contracts.prompt_workbench_ui_parity import build_prompt_workbench_ui_parity_payload


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SHELL = ROOT / "web" / "sidebar_tabs" / "rookieui_prompt_workbench_shell.js"
FRONTEND_CSS = ROOT / "web" / "rookieui_panes.css"
FRONTEND_UNIT = ROOT / "web" / "tests" / "rookieui_prompt_workbench_shell.test.js"
VISUAL_SPEC = ROOT / "tests" / "e2e" / "specs" / "prompt_workbench_ui_parity.spec.js"


EXPECTED_RUNTIME_SELECTORS = {
    "inline_surface_root": "[data-layout='prompt_all_in_one_inline']",
    "fold_unfold": "[data-pw-ui='fold-toggle']",
    "inline_toolbar_row": ".rookieui-shell__prompt-workbench-inline-tool",
    "counter_language_status": "[data-pw-ui='inline-counter']",
    "popover_anchor_buttons": "[data-pw-ui='inline-history-anchor']",
    "inline_append_dropdown": "[data-pw-ui='append-dropdown-popover']",
    "inline_suggestions": "[data-pw-ui='inline-suggestions']",
    "inline_token_tags": "[data-pw-token-ui='inline-token-tag']",
    "token_hover_quick_actions": ".rookieui-shell__prompt-workbench-token-quick-actions",
    "bilingual_token_row": ".rookieui-shell__prompt-workbench-token-local-language",
    "selection_batch_toolbar": "[data-pw-ui='selection-batch-toolbar']",
    "group_tags_tab_board": "[data-pw-ui='group-tags-tab-board']",
    "namespace_accessibility": "[aria-haspopup='dialog']",
}


def _selector_markers(selector: str) -> tuple[str, ...]:
    if selector.startswith("."):
        return (selector.removeprefix("."),)
    match = re.fullmatch(r"\[([^=]+)='([^']+)'\]", selector)
    if match:
        attribute, value = match.groups()
        if attribute == "data-pw-ui":
            return (
                f'dataset.pwUi = "{value}"',
                f'"{value}"',
                f"data-pw-ui='{value}'",
                f'data-pw-ui="{value}"',
            )
        if attribute == "data-pw-token-ui":
            return (
                f'dataset.pwTokenUi = "{value}"',
                f'"{value}"',
                f"data-pw-token-ui='{value}'",
                f'data-pw-token-ui="{value}"',
            )
        if attribute == "data-layout":
            return (
                f'dataset.layout = normalizedFixedScope ? "{value}"',
                f'data-layout="{value}"',
                f"data-layout='{value}'",
            )
        if attribute == "aria-haspopup":
            return (
                f'setAttribute("aria-haspopup", "{value}")',
                f"aria-haspopup='{value}'",
                f'aria-haspopup="{value}"',
            )
        return (
            value,
            selector,
        )
    return (selector,)


class PromptWorkbenchUiParityClosureTests(unittest.TestCase):
    def test_contract_selectors_match_shipped_ui_parity_surfaces(self) -> None:
        payload = build_prompt_workbench_ui_parity_payload()
        primitives = {entry["primitive_id"]: entry for entry in payload["primitives"]}

        for primitive_id, selector in EXPECTED_RUNTIME_SELECTORS.items():
            with self.subTest(primitive_id=primitive_id):
                primitive = primitives[primitive_id]
                self.assertEqual(primitive["target_selector"], selector)
                self.assertIn(primitive["parity_class"], {"implemented", "adapted_comfyui_native"})
                self.assertIn("unit_dom", primitive["evidence_required"])

    def test_shipped_frontend_and_unit_tests_cover_contract_selectors(self) -> None:
        source_text = "\n".join(
            [
                FRONTEND_SHELL.read_text(encoding="utf-8"),
                FRONTEND_CSS.read_text(encoding="utf-8"),
                FRONTEND_UNIT.read_text(encoding="utf-8"),
            ]
        )

        for primitive_id, selector in EXPECTED_RUNTIME_SELECTORS.items():
            with self.subTest(primitive_id=primitive_id):
                self.assertTrue(
                    any(marker in source_text for marker in _selector_markers(selector)),
                    f"missing selector coverage for {primitive_id}: {selector}",
                )

    def test_visual_evidence_spec_covers_current_and_reference_captures(self) -> None:
        spec_text = VISUAL_SPEC.read_text(encoding="utf-8")

        for required in (
            "reference-prompt-all-in-one-card.png",
            "current-rookieui-prompt-workbench-card.png",
            "current-rookieui-prompt-workbench-popover.png",
            "[data-reference='prompt-all-in-one-card']",
            'toHaveAttribute("data-layout", "prompt_all_in_one_inline")',
            "[data-pw-token-ui='inline-token-tag']",
            'toHaveAttribute("data-batch-layout", "inline-overlay")',
            'toHaveAttribute("data-active-surface", "history")',
            'toHaveAttribute("data-active-surface", "append")',
            'page.keyboard.press("Escape")',
        ):
            with self.subTest(required=required):
                self.assertIn(required, spec_text)


if __name__ == "__main__":
    unittest.main()
