from __future__ import annotations

import unittest

from rookieui.services.coercion import coerce_bool, coerce_float, coerce_int


class CoercionTests(unittest.TestCase):
    def test_coerce_bool_strict_accepts_standard_inputs(self) -> None:
        self.assertTrue(coerce_bool(True, "flag"))
        self.assertTrue(coerce_bool("yes", "flag"))
        self.assertTrue(coerce_bool(1, "flag"))
        self.assertFalse(coerce_bool("", "flag"))
        self.assertFalse(coerce_bool(0, "flag"))

    def test_coerce_bool_strict_rejects_none(self) -> None:
        with self.assertRaisesRegex(ValueError, "flag must be a boolean"):
            coerce_bool(None, "flag")

    def test_coerce_bool_non_strict_falls_back_to_truthiness(self) -> None:
        self.assertTrue(coerce_bool("truthy-custom-token", "flag", strict=False))
        self.assertFalse(coerce_bool(None, "flag", strict=False))

    def test_coerce_int_default_and_required_behavior(self) -> None:
        self.assertEqual(coerce_int("", "steps", default=20), 20)
        with self.assertRaisesRegex(ValueError, "steps is required"):
            coerce_int("", "steps", required_if_empty=True)

    def test_coerce_float_precision_and_error_label(self) -> None:
        self.assertEqual(
            coerce_float("1.2349", "cfg_scale", via_str=True, precision=3),
            1.235,
        )
        with self.assertRaisesRegex(ValueError, "inline_lora_clip_strength must be numeric"):
            coerce_float("oops", "inline_lora_clip_strength", error_label="numeric")
