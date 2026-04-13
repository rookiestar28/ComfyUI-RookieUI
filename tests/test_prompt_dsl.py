from __future__ import annotations

import unittest
from unittest import mock

from rookieui.services.prompt_dsl import (
    PROMPT_WARNING_AND_DETECTED,
    PROMPT_WARNING_ATTENTION_DETECTED,
    PROMPT_WARNING_BREAK_DETECTED,
    PROMPT_WARNING_LEGACY_FALLBACK_ENABLED,
    PROMPT_WARNING_SCHEDULE_DETECTED,
    merge_lora_activations,
    preprocess_prompt_bundle,
)


class PromptDslTests(unittest.TestCase):
    def test_preprocess_prompt_bundle_extracts_inline_lora_and_cleans_prompt_text(self) -> None:
        result = preprocess_prompt_bundle(
            "cinematic skyline <lora:detail_tweaker.safetensors:0.8>",
            "blurry",
            inventory_loras=["detail_tweaker.safetensors"],
            strict_match=True,
        )

        self.assertEqual(result.cleaned_prompt, "cinematic skyline")
        self.assertEqual(result.cleaned_negative_prompt, "blurry")
        self.assertEqual(len(result.lora_activations), 1)
        self.assertEqual(result.lora_activations[0].name, "detail_tweaker.safetensors")
        self.assertEqual(result.lora_activations[0].strength_clip, 0.8)
        self.assertEqual(result.lora_activations[0].strength_model, 0.8)

    def test_preprocess_prompt_bundle_supports_named_inline_lora_args(self) -> None:
        result = preprocess_prompt_bundle(
            "portrait <lora:detail_tweaker.safetensors:0.8:0.6:4>",
            "",
            inventory_loras=["detail_tweaker.safetensors"],
            strict_match=True,
        )

        activation = result.lora_activations[0]
        self.assertEqual(activation.name, "detail_tweaker.safetensors")
        self.assertEqual(activation.strength_clip, 0.8)
        self.assertEqual(activation.strength_model, 0.6)
        self.assertEqual(activation.dyn_dim, 4)

    def test_preprocess_prompt_bundle_builds_structured_prompt_semantics(self) -> None:
        result = preprocess_prompt_bundle(
            "(face detail:1.2) hero BREAK [calm:chaos:0.4] AND villain:0.7",
            "",
            inventory_loras=[],
            strict_match=False,
        )

        semantics = result.prompt_semantics.to_payload()
        self.assertTrue(semantics["features"]["and_composition"])
        self.assertTrue(semantics["features"]["break_chunks"])
        self.assertTrue(semantics["features"]["prompt_scheduling"])
        self.assertTrue(semantics["features"]["attention_weighting"])
        self.assertEqual(len(semantics["branches"]), 2)
        self.assertEqual(semantics["branches"][1]["weight"], 0.7)
        self.assertTrue(
            any(
                len(chunk["slices"]) >= 2
                for branch in semantics["branches"]
                for chunk in branch["chunks"]
            )
        )
        self.assertTrue(any(marker["syntax"] == "explicit" for marker in semantics["attention"]))
        self.assertIn(PROMPT_WARNING_AND_DETECTED, result.warning_codes)
        self.assertIn(PROMPT_WARNING_BREAK_DETECTED, result.warning_codes)
        self.assertIn(PROMPT_WARNING_SCHEDULE_DETECTED, result.warning_codes)
        self.assertIn(PROMPT_WARNING_ATTENTION_DETECTED, result.warning_codes)

    def test_preprocess_prompt_bundle_keeps_negative_prompt_semantics_payload(self) -> None:
        result = preprocess_prompt_bundle(
            "portrait",
            "bad anatomy BREAK [clean:messy:0.25]",
            inventory_loras=[],
            strict_match=False,
        )

        semantics = result.negative_prompt_semantics.to_payload()
        self.assertTrue(semantics["features"]["break_chunks"])
        self.assertTrue(semantics["features"]["prompt_scheduling"])
        self.assertEqual(len(semantics["branches"]), 1)
        self.assertEqual(len(semantics["branches"][0]["chunks"]), 2)

    def test_preprocess_prompt_bundle_honors_legacy_env_fallback_switch(self) -> None:
        with mock.patch.dict("os.environ", {"ROOKIEUI_PROMPT_DSL_LEGACY": "1"}, clear=False):
            result = preprocess_prompt_bundle(
                "hero AND villain BREAK [calm:chaos:0.4]",
                "",
                inventory_loras=[],
                strict_match=False,
            )

        semantics = result.prompt_semantics.to_payload()
        self.assertFalse(semantics["features"]["and_composition"])
        self.assertFalse(semantics["features"]["break_chunks"])
        self.assertFalse(semantics["features"]["prompt_scheduling"])
        self.assertIn(PROMPT_WARNING_LEGACY_FALLBACK_ENABLED, result.warning_codes)
        self.assertTrue(
            any("legacy graph fallback path" in warning for warning in result.prompt_warnings)
        )

    def test_merge_lora_activations_prefers_explicit_selector_for_matching_name(self) -> None:
        preprocessed = preprocess_prompt_bundle(
            "cinematic skyline <lora:detail_tweaker.safetensors:0.8>",
            "",
            inventory_loras=["detail_tweaker.safetensors"],
            strict_match=True,
        )

        merged = merge_lora_activations(
            preprocessed.lora_activations,
            explicit_lora_name="detail_tweaker.safetensors",
            explicit_strength_model=0.65,
            explicit_strength_clip=0.55,
        )

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].source, "selector")
        self.assertEqual(merged[0].strength_model, 0.65)
        self.assertEqual(merged[0].strength_clip, 0.55)

    def test_preprocess_prompt_bundle_rejects_unknown_inline_lora_in_strict_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, "inline_lora_name must match a host inventory entry"):
            preprocess_prompt_bundle(
                "cinematic skyline <lora:missing:0.8>",
                "",
                inventory_loras=["detail_tweaker.safetensors"],
                strict_match=True,
            )
