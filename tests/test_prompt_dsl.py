from __future__ import annotations

import unittest

from rookieui.services.prompt_dsl import merge_lora_activations, preprocess_prompt_bundle


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

    def test_preprocess_prompt_bundle_warns_for_prompt_features_not_yet_translated(self) -> None:
        result = preprocess_prompt_bundle(
            "hero AND villain BREAK [calm:chaos:0.4]",
            "",
            inventory_loras=[],
            strict_match=False,
        )

        self.assertTrue(any("AND" in warning for warning in result.prompt_warnings))
        self.assertTrue(any("BREAK" in warning for warning in result.prompt_warnings))
        self.assertTrue(any("scheduling" in warning for warning in result.prompt_warnings))

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
