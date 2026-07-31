from __future__ import annotations

import unittest

from rookieui.contracts.prompt_encoder_detail_parity import (
    PROMPT_ENCODER_DETAIL_PARITY_STATUSES,
    build_prompt_encoder_detail_parity_payload,
)


class PromptEncoderDetailParityTests(unittest.TestCase):
    def test_matrix_freezes_phase_101_detail_dimensions(self) -> None:
        payload = build_prompt_encoder_detail_parity_payload()
        dimensions = {entry["dimension_id"]: entry for entry in payload["dimensions"]}

        self.assertEqual(
            set(dimensions),
            {
                "parser_mode_matrix",
                "a1111_default_parser",
                "full_parser",
                "comfy_plus_parser",
                "fixed_attention_parser",
                "old_emphasis",
                "mean_normalization_exactness",
                "textual_inversion_scan",
                "embedding_prefix_alias",
                "missing_embedding_behavior",
                "multi_vector_embedding_injection",
                "sdxl_dual_channel_embedding",
                "live_tensor_differential",
            },
        )
        self.assertEqual(dimensions["a1111_default_parser"]["status"], "implemented")
        self.assertEqual(dimensions["live_tensor_differential"]["status"], "implemented")

    def test_matrix_keeps_public_features_aligned(self) -> None:
        payload = build_prompt_encoder_detail_parity_payload()
        features = {entry["feature_id"]: entry for entry in payload["features"]}

        self.assertEqual(
            set(features),
            {
                "reference_baseline",
                "parser_modes",
                "conditioning_weights",
                "textual_inversion",
                "sdxl_textual_inversion",
                "tensor_differential",
                "acceptance_closure",
            },
        )
        self.assertEqual(features["reference_baseline"]["status"], "completed")
        self.assertEqual(features["parser_modes"]["covers"], ["parser_mode_matrix"])
        self.assertIn("sdxl_dual_channel_embedding", features["sdxl_textual_inversion"]["covers"])
        self.assertEqual(features["tensor_differential"]["status"], "completed")
        self.assertEqual(features["acceptance_closure"]["status"], "completed")

    def test_acceptance_closure_has_no_planned_phase_items(self) -> None:
        payload = build_prompt_encoder_detail_parity_payload()
        features = {entry["feature_id"]: entry for entry in payload["features"]}

        non_completed = [
            feature_id
            for feature_id, entry in sorted(features.items())
            if entry["status"] != "completed"
        ]

        self.assertEqual(non_completed, [])

    def test_matrix_uses_allowed_statuses_and_acceptance_signals(self) -> None:
        payload = build_prompt_encoder_detail_parity_payload()
        allowed_statuses = set(PROMPT_ENCODER_DETAIL_PARITY_STATUSES)

        for collection_name in ("dimensions", "features"):
            ids = [entry.get("dimension_id") or entry.get("feature_id") for entry in payload[collection_name]]
            self.assertEqual(len(ids), len(set(ids)))
            for entry in payload[collection_name]:
                self.assertIn(entry["status"], allowed_statuses)
                self.assertTrue(entry["acceptance_signal"])


if __name__ == "__main__":
    unittest.main()
