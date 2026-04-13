from __future__ import annotations

import unittest

from rookieui.services.a1111_prompt_engine import (
    get_learned_conditioning_prompt_schedules,
    parse_prompt_attention,
    split_weighted_subprompts,
)


class A1111PromptEngineTests(unittest.TestCase):
    def test_parse_prompt_attention_matches_reference_examples(self) -> None:
        parsed = parse_prompt_attention("a (((house:1.3)) [on] a (hill:0.5), sun, (((sky))).")

        self.assertEqual(
            [(entry.text, entry.weight) for entry in parsed],
            [
                ("a ", 1.0),
                ("house", 1.5730000000000004),
                (" ", 1.1),
                ("on", 1.0),
                (" a ", 1.1),
                ("hill", 0.55),
                (", sun, ", 1.1),
                ("sky", 1.4641000000000006),
                (".", 1.1),
            ],
        )

    def test_parse_prompt_attention_emits_break_as_control_token(self) -> None:
        parsed = parse_prompt_attention("hero BREAK villain")
        self.assertEqual(
            [(entry.text, entry.weight) for entry in parsed],
            [("hero", 1.0), ("BREAK", -1.0), ("villain", 1.0)],
        )

    def test_split_weighted_subprompts_matches_a1111_weight_suffix_behavior(self) -> None:
        parsed = split_weighted_subprompts("hero AND villain:0.7 AND skyline")
        self.assertEqual(
            [(entry.text, entry.weight) for entry in parsed],
            [("hero", 1.0), (" villain", 0.7), (" skyline", 1.0)],
        )

    def test_schedule_parser_matches_reference_examples(self) -> None:
        schedules = get_learned_conditioning_prompt_schedules(
            [
                "a [b:3]",
                "a [b : c : 1] d",
                "a[b:[c:d:2]:1]e",
                "[fe|]male",
            ],
            10,
        )

        self.assertEqual(
            [[(entry.end_at_step, entry.text) for entry in schedule] for schedule in schedules],
            [
                [(3, "a "), (10, "a b")],
                [(1, "a b  d"), (10, "a  c  d")],
                [(1, "abe"), (2, "ace"), (10, "ade")],
                [
                    (1, "female"),
                    (2, "male"),
                    (3, "female"),
                    (4, "male"),
                    (5, "female"),
                    (6, "male"),
                    (7, "female"),
                    (8, "male"),
                    (9, "female"),
                    (10, "male"),
                ],
            ],
        )

    def test_schedule_parser_preserves_reference_hires_timeline_rules(self) -> None:
        half = get_learned_conditioning_prompt_schedules(["a [b:.5] c"], 10, 10)
        one_point_five = get_learned_conditioning_prompt_schedules(["a [b:1.5] c"], 10, 10)

        self.assertEqual(
            [(entry.end_at_step, entry.text) for entry in half[0]],
            [(10, "a b c")],
        )
        self.assertEqual(
            [(entry.end_at_step, entry.text) for entry in one_point_five[0]],
            [(5, "a  c"), (10, "a b c")],
        )

    def test_schedule_parser_keeps_unbalanced_brackets_literal(self) -> None:
        schedules = get_learned_conditioning_prompt_schedules(["a [unbalanced"], 10)
        self.assertEqual([(entry.end_at_step, entry.text) for entry in schedules[0]], [(10, "a [unbalanced")])
