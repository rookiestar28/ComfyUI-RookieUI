from __future__ import annotations

import unittest
from unittest import mock

from rookieui.contracts.prompt_dsl import PromptSemanticPlan
from rookieui.services.prompt_dsl import (
    PROMPT_WARNING_AND_DETECTED,
    PROMPT_WARNING_ALTERNATE_DETECTED,
    PROMPT_WARNING_ATTENTION_DETECTED,
    PROMPT_WARNING_BREAK_DETECTED,
    PROMPT_WARNING_EMBEDDING_DETECTED,
    PROMPT_WARNING_EMBEDDING_MISSING,
    PROMPT_WARNING_LEGACY_FALLBACK_ENABLED,
    PROMPT_WARNING_SCHEDULE_DETECTED,
    merge_lora_activations,
    normalize_prompt_attention_for_weighted_encode,
    preprocess_prompt_bundle,
)


class PromptDslTests(unittest.TestCase):
    def test_prompt_semantic_plan_empty_exposes_embeddings_contract_shape(self) -> None:
        empty = PromptSemanticPlan.empty("hero")

        self.assertIn("embeddings_textual_inversion", empty.features)
        self.assertIn("alternate_prompt_scheduling", empty.features)
        self.assertFalse(empty.features["embeddings_textual_inversion"])
        self.assertFalse(empty.features["alternate_prompt_scheduling"])
        self.assertEqual(empty.embeddings, [])
        payload = empty.to_payload()
        self.assertEqual(payload["embeddings"], [])

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

    def test_preprocess_prompt_bundle_canonicalizes_inventory_backed_bare_embedding_tokens(self) -> None:
        result = preprocess_prompt_bundle(
            "portrait badhandv4 masterpiece",
            "",
            inventory_loras=[],
            inventory_embeddings=["badhandv4.pt"],
            strict_match=False,
        )

        self.assertEqual(result.cleaned_prompt, "portrait embedding:badhandv4.pt masterpiece")
        self.assertIn(PROMPT_WARNING_EMBEDDING_DETECTED, result.warning_codes)
        self.assertTrue(result.prompt_semantics.features["embeddings_textual_inversion"])
        self.assertEqual(len(result.prompt_semantics.embeddings), 1)
        self.assertEqual(result.prompt_semantics.embeddings[0].syntax, "bare")
        self.assertTrue(result.prompt_semantics.embeddings[0].exists)
        self.assertEqual(result.prompt_semantics.embeddings[0].canonical_token, "embedding:badhandv4.pt")

    def test_preprocess_prompt_bundle_preserves_missing_explicit_embedding_as_plain_text(self) -> None:
        result = preprocess_prompt_bundle(
            "portrait embedding:missing_style dramatic light",
            "",
            inventory_loras=[],
            inventory_embeddings=["badhandv4.pt"],
            strict_match=False,
        )

        self.assertEqual(result.cleaned_prompt, "portrait missing_style dramatic light")
        self.assertIn(PROMPT_WARNING_EMBEDDING_DETECTED, result.warning_codes)
        self.assertIn(PROMPT_WARNING_EMBEDDING_MISSING, result.warning_codes)
        self.assertEqual(len(result.prompt_semantics.embeddings), 1)
        self.assertFalse(result.prompt_semantics.embeddings[0].exists)
        self.assertEqual(result.prompt_semantics.embeddings[0].syntax, "explicit")
        self.assertTrue(any("embedding:missing_style" in warning for warning in result.prompt_warnings))

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

    def test_preprocess_prompt_bundle_expands_alternate_prompt_scheduling(self) -> None:
        result = preprocess_prompt_bundle(
            "portrait [warm|cool] light",
            "",
            step_count=4,
            inventory_loras=[],
            strict_match=False,
        )

        semantics = result.prompt_semantics.to_payload()
        self.assertTrue(semantics["features"]["alternate_prompt_scheduling"])
        self.assertFalse(semantics["features"]["prompt_scheduling"])
        self.assertIn(PROMPT_WARNING_ALTERNATE_DETECTED, result.warning_codes)
        slices = semantics["branches"][0]["chunks"][0]["slices"]
        self.assertEqual(
            [slice_item["text"] for slice_item in slices],
            [
                "portrait warm light",
                "portrait cool light",
                "portrait warm light",
                "portrait cool light",
            ],
        )
        self.assertEqual(
            [(slice_item["start"], slice_item["end"]) for slice_item in slices],
            [(0.0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.0)],
        )

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

    def test_normalize_prompt_attention_for_weighted_encode_rewrites_square_brackets(self) -> None:
        normalized = normalize_prompt_attention_for_weighted_encode("portrait [soft light]")

        self.assertEqual(normalized, "portrait (soft light:0.9091)")

    def test_normalize_prompt_attention_for_weighted_encode_preserves_schedule_groups(self) -> None:
        normalized = normalize_prompt_attention_for_weighted_encode("[calm:chaos:0.4]")

        self.assertEqual(normalized, "[calm:chaos:0.4]")

    def test_normalize_prompt_attention_for_weighted_encode_preserves_alternate_groups(self) -> None:
        normalized = normalize_prompt_attention_for_weighted_encode("[warm|cool]")

        self.assertEqual(normalized, "[warm|cool]")

    def test_normalize_prompt_attention_for_weighted_encode_preserves_escaped_markers(self) -> None:
        normalized = normalize_prompt_attention_for_weighted_encode(r"literal \[brackets\] and \(parens\)")

        self.assertEqual(normalized, r"literal [brackets] and (parens)")

    def test_normalize_prompt_attention_for_weighted_encode_rejects_pathological_nesting(self) -> None:
        nested = "(" * 40 + "subject" + ")" * 40

        with self.assertRaisesRegex(ValueError, "maximum depth 32"):
            normalize_prompt_attention_for_weighted_encode(nested)
