from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from rookieui.services.img2img import normalize_img2img_request
from rookieui.services.prompt_dsl import preprocess_prompt_bundle
from rookieui.services.txt2img import normalize_txt2img_request
from rookieui.services.workflow_translation import (
    translate_img2img_request,
    translate_txt2img_request,
)
from tests.prompt_parity_fixtures import (
    ALL_PROMPT_FEATURES,
    PROMPT_PARITY_GOLDEN_CASES,
    PromptParityGoldenCase,
    build_fixture_inventory,
)


class PromptParityFixtureHarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self._asset_path_patcher = mock.patch(
            "rookieui.services.img2img.resolve_asset_path",
            return_value=Path(__file__),
        )
        self._asset_path_patcher.start()

    def tearDown(self) -> None:
        self._asset_path_patcher.stop()

    def _assert_feature_state(
        self,
        payload: dict[str, object],
        enabled_features: tuple[str, ...],
        *,
        case_id: str,
    ) -> None:
        features = payload.get("features")
        self.assertIsInstance(features, dict, case_id)
        for feature_name in ALL_PROMPT_FEATURES:
            self.assertEqual(
                bool(features.get(feature_name)),
                feature_name in enabled_features,
                f"{case_id} feature {feature_name}",
            )

    def _assert_embedding_payload(
        self,
        payload: dict[str, object],
        expected_embeddings,
        *,
        case_id: str,
        lane: str,
    ) -> None:
        actual_embeddings = payload.get("embeddings")
        self.assertIsInstance(actual_embeddings, list, f"{case_id} {lane} embeddings payload")
        self.assertEqual(len(actual_embeddings), len(expected_embeddings), f"{case_id} {lane} embeddings count")
        for actual, expected in zip(actual_embeddings, expected_embeddings):
            self.assertEqual(actual["canonical_token"], expected.canonical_token, f"{case_id} {lane} canonical token")
            self.assertEqual(actual["exists"], expected.exists, f"{case_id} {lane} exists state")
            self.assertEqual(actual["syntax"], expected.syntax, f"{case_id} {lane} syntax")

    def _collect_encoder_texts(self, workflow: dict[str, object], encoder_class: str) -> list[str]:
        texts: list[str] = []
        for node in workflow.values():
            if not isinstance(node, dict) or node.get("class_type") != encoder_class:
                continue
            inputs = node.get("inputs")
            if not isinstance(inputs, dict):
                continue
            if encoder_class == "RookieUIA1111CLIPTextEncodeSDXL":
                for key in ("text_g", "text_l"):
                    value = inputs.get(key)
                    if isinstance(value, str):
                        texts.append(value)
            else:
                value = inputs.get("text")
                if isinstance(value, str):
                    texts.append(value)
        return texts

    def _assert_translation_topology(
        self,
        workflow: dict[str, object],
        case: PromptParityGoldenCase,
        *,
        lane: str,
    ) -> None:
        class_types = {
            node.get("class_type")
            for node in workflow.values()
            if isinstance(node, dict)
        }
        self.assertIn(case.expected_encoder_class, class_types, f"{case.case_id} {lane} encoder class")
        if case.expect_conditioning_combine:
            self.assertIn("ConditioningCombine", class_types, f"{case.case_id} {lane} combine topology")
        else:
            self.assertNotIn("ConditioningCombine", class_types, f"{case.case_id} {lane} combine topology")
        if case.expect_timestep_range:
            self.assertIn("ConditioningSetTimestepRange", class_types, f"{case.case_id} {lane} timestep topology")
        else:
            self.assertNotIn("ConditioningSetTimestepRange", class_types, f"{case.case_id} {lane} timestep topology")

        encoder_texts = self._collect_encoder_texts(workflow, case.expected_encoder_class)
        for fragment in case.expected_prompt_workflow_fragments + case.expected_negative_workflow_fragments:
            self.assertTrue(
                any(fragment in text for text in encoder_texts),
                f"{case.case_id} {lane} missing workflow text fragment: {fragment}",
            )

    def test_golden_prompt_parity_fixtures_preprocess_bundle(self) -> None:
        for case in PROMPT_PARITY_GOLDEN_CASES:
            with self.subTest(case=case.case_id):
                result = preprocess_prompt_bundle(
                    case.prompt,
                    case.negative_prompt,
                    inventory_loras=[],
                    inventory_embeddings=list(case.inventory_embeddings),
                    strict_match=False,
                )

                self.assertEqual(result.cleaned_prompt, case.expected_cleaned_prompt)
                self.assertEqual(result.cleaned_negative_prompt, case.expected_cleaned_negative_prompt)
                for warning_code in case.expected_warning_codes:
                    self.assertIn(warning_code, result.warning_codes)

                prompt_payload = result.prompt_semantics.to_payload()
                negative_payload = result.negative_prompt_semantics.to_payload()
                self._assert_feature_state(prompt_payload, case.expected_prompt_features, case_id=case.case_id)
                self._assert_feature_state(
                    negative_payload,
                    case.expected_negative_features,
                    case_id=f"{case.case_id}:negative",
                )
                self.assertEqual(len(prompt_payload["branches"]), case.expected_prompt_branch_count, case.case_id)
                self.assertEqual(len(negative_payload["branches"]), case.expected_negative_branch_count, case.case_id)
                self._assert_embedding_payload(
                    prompt_payload,
                    case.expected_prompt_embeddings,
                    case_id=case.case_id,
                    lane="prompt",
                )
                self._assert_embedding_payload(
                    negative_payload,
                    case.expected_negative_embeddings,
                    case_id=case.case_id,
                    lane="negative",
                )

    def test_golden_prompt_parity_fixtures_translate_txt2img(self) -> None:
        for case in PROMPT_PARITY_GOLDEN_CASES:
            with self.subTest(case=case.case_id):
                inventory = build_fixture_inventory(case)
                with mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=inventory):
                    normalized = normalize_txt2img_request(
                        {
                            "prompt": case.prompt,
                            "negative_prompt": case.negative_prompt,
                            "profile": case.profile,
                        }
                    )

                self.assertEqual(normalized.prompt, case.expected_cleaned_prompt)
                self.assertEqual(normalized.negative_prompt, case.expected_cleaned_negative_prompt)
                for warning_code in case.expected_warning_codes:
                    self.assertIn(warning_code, normalized.prompt_warning_codes)
                self._assert_feature_state(normalized.prompt_semantics, case.expected_prompt_features, case_id=case.case_id)
                self._assert_feature_state(
                    normalized.negative_prompt_semantics,
                    case.expected_negative_features,
                    case_id=f"{case.case_id}:negative",
                )
                self._assert_embedding_payload(
                    normalized.prompt_semantics,
                    case.expected_prompt_embeddings,
                    case_id=case.case_id,
                    lane="prompt",
                )
                self._assert_embedding_payload(
                    normalized.negative_prompt_semantics,
                    case.expected_negative_embeddings,
                    case_id=case.case_id,
                    lane="negative",
                )

                result = translate_txt2img_request(normalized).to_payload()
                self._assert_translation_topology(result["workflow"], case, lane="txt2img")

    def test_golden_prompt_parity_fixtures_translate_img2img(self) -> None:
        for case in PROMPT_PARITY_GOLDEN_CASES:
            with self.subTest(case=case.case_id):
                inventory = build_fixture_inventory(case)
                with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=inventory):
                    normalized = normalize_img2img_request(
                        {
                            "prompt": case.prompt,
                            "negative_prompt": case.negative_prompt,
                            "profile": case.profile,
                            "image_asset": "fixture-input",
                        }
                    )

                self.assertEqual(normalized.prompt, case.expected_cleaned_prompt)
                self.assertEqual(normalized.negative_prompt, case.expected_cleaned_negative_prompt)
                for warning_code in case.expected_warning_codes:
                    self.assertIn(warning_code, normalized.prompt_warning_codes)
                self._assert_feature_state(normalized.prompt_semantics, case.expected_prompt_features, case_id=case.case_id)
                self._assert_feature_state(
                    normalized.negative_prompt_semantics,
                    case.expected_negative_features,
                    case_id=f"{case.case_id}:negative",
                )
                self._assert_embedding_payload(
                    normalized.prompt_semantics,
                    case.expected_prompt_embeddings,
                    case_id=case.case_id,
                    lane="prompt",
                )
                self._assert_embedding_payload(
                    normalized.negative_prompt_semantics,
                    case.expected_negative_embeddings,
                    case_id=case.case_id,
                    lane="negative",
                )

                result = translate_img2img_request(normalized).to_payload()
                self._assert_translation_topology(result["workflow"], case, lane="img2img")
