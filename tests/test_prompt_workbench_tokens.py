from __future__ import annotations

import unittest

from rookieui.services.prompt_workbench_tokens import (
    adjust_prompt_workbench_token_weight,
    adjust_prompt_workbench_token_weight_by_id,
    copy_prompt_workbench_token,
    delete_prompt_workbench_token,
    move_prompt_workbench_token,
    parse_prompt_workbench_tokens,
    rebuild_prompt_from_tokens,
    set_prompt_workbench_token_disabled,
)


class PromptWorkbenchTokenTests(unittest.TestCase):
    def test_parse_preserves_escaped_commas_and_special_prompt_syntax(self) -> None:
        tokens = parse_prompt_workbench_tokens(
            r"masterpiece, city\, skyline, <lora:detail_tweaker:0.8>, embedding:badhandv4.pt, "
            "BREAK, [day:night:0.5], (soft light:1.2)",
            scope="txt2img_prompt",
        )

        self.assertEqual(
            [token.raw_text for token in tokens],
            [
                "masterpiece",
                r"city\, skyline",
                "<lora:detail_tweaker:0.8>",
                "embedding:badhandv4.pt",
                "BREAK",
                "[day:night:0.5]",
                "(soft light:1.2)",
            ],
        )
        self.assertEqual(
            [token.keyword_family for token in tokens],
            ["plain", "plain", "lora", "embedding", "break", "schedule", "weighted"],
        )
        self.assertEqual(tokens[0].scope, "prompt")
        self.assertEqual(tokens[-1].weight, 1.2)

    def test_negative_scope_rebuild_skips_disabled_tokens(self) -> None:
        tokens = parse_prompt_workbench_tokens("bad anatomy, blurry, low quality", scope="negative_prompt")
        disabled = set_prompt_workbench_token_disabled(tokens, tokens[1].id, disabled=True)

        self.assertEqual(disabled[1].scope, "negative")
        self.assertTrue(disabled[1].disabled)
        self.assertEqual(rebuild_prompt_from_tokens(disabled), "bad anatomy, low quality")

    def test_move_delete_and_copy_token_actions_are_stable(self) -> None:
        tokens = parse_prompt_workbench_tokens("masterpiece, city skyline, cinematic lighting")

        moved = move_prompt_workbench_token(tokens, tokens[2].id, direction="up")
        self.assertEqual(
            [token.raw_text for token in moved],
            ["masterpiece", "cinematic lighting", "city skyline"],
        )
        self.assertEqual(copy_prompt_workbench_token(moved, moved[1].id), "cinematic lighting")

        deleted = delete_prompt_workbench_token(moved, moved[0].id)
        self.assertEqual([token.order_index for token in deleted], [0, 1])
        self.assertEqual(rebuild_prompt_from_tokens(deleted), "cinematic lighting, city skyline")

    def test_adjust_weight_supports_plain_and_explicit_weighted_tokens(self) -> None:
        self.assertEqual(adjust_prompt_workbench_token_weight("masterpiece", delta=0.1), "(masterpiece:1.1)")
        self.assertEqual(adjust_prompt_workbench_token_weight("masterpiece", delta=-0.1), "(masterpiece:0.9)")
        self.assertEqual(adjust_prompt_workbench_token_weight("(soft light:1.2)", delta=0.1), "(soft light:1.3)")
        self.assertEqual(adjust_prompt_workbench_token_weight("(soft light:1.2)", delta=-0.2), "(soft light:1)")

    def test_adjust_weight_by_id_updates_payload_metadata(self) -> None:
        tokens = parse_prompt_workbench_tokens("masterpiece, city skyline")
        adjusted = adjust_prompt_workbench_token_weight_by_id(tokens, tokens[1].id, delta=0.1)

        self.assertEqual(adjusted[1].raw_text, "(city skyline:1.1)")
        self.assertEqual(adjusted[1].keyword_family, "weighted")
        self.assertEqual(adjusted[1].weight, 1.1)
        self.assertEqual(rebuild_prompt_from_tokens(adjusted), "masterpiece, (city skyline:1.1)")


if __name__ == "__main__":
    unittest.main()
