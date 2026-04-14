from __future__ import annotations

import unittest

from rookieui.services.controlnet_advanced_runtime import (
    CONTROLNET_ADVANCED_RUNTIME_STATE,
    build_controlnet_apply_segments,
    build_controlnet_stage_weights,
    stage_weights_require_wrapper,
)


class ControlNetAdvancedRuntimeTests(unittest.TestCase):
    def test_build_controlnet_apply_segments_returns_base_segment_when_advanced_disabled(self) -> None:
        segments = build_controlnet_apply_segments(
            weight=0.8,
            guidance_start=0.1,
            guidance_end=0.9,
            advanced={"enabled": False},
        )

        self.assertEqual(
            segments,
            [
                {
                    "strength": 0.8,
                    "start_percent": 0.1,
                    "end_percent": 0.9,
                }
            ],
        )

    def test_build_controlnet_apply_segments_intersects_keyframes_with_guidance_range(self) -> None:
        segments = build_controlnet_apply_segments(
            weight=0.75,
            guidance_start=0.1,
            guidance_end=0.9,
            advanced={
                "enabled": True,
                "timestep_keyframes": [
                    {"start_percent": 0.0, "end_percent": 0.5, "strength_scale": 0.5},
                    {"start_percent": 0.5, "end_percent": 1.0, "strength_scale": 1.25},
                ],
            },
        )

        self.assertEqual(
            segments,
            [
                {"strength": 0.375, "start_percent": 0.1, "end_percent": 0.5},
                {"strength": 0.9375, "start_percent": 0.5, "end_percent": 0.9},
            ],
        )

    def test_build_controlnet_apply_segments_rolls_back_to_base_segment_when_keyframes_collapse(self) -> None:
        segments = build_controlnet_apply_segments(
            weight=0.55,
            guidance_start=0.2,
            guidance_end=0.7,
            advanced={
                "enabled": True,
                "timestep_keyframes": [
                    {"start_percent": 0.0, "end_percent": 0.1, "strength_scale": 1.0},
                    {"start_percent": 0.9, "end_percent": 1.0, "strength_scale": 0.0},
                ],
            },
        )

        self.assertEqual(
            segments,
            [
                {
                    "strength": 0.55,
                    "start_percent": 0.2,
                    "end_percent": 0.7,
                }
            ],
        )

    def test_build_controlnet_stage_weights_uses_preset_and_explicit_overrides(self) -> None:
        stage_weights = build_controlnet_stage_weights(
            input_count=2,
            middle_count=1,
            output_count=3,
            weight_preset="soft",
            layer_weights=[0.2, 0.4],
        )

        self.assertEqual(stage_weights["output"][:2], [0.2, 0.4])
        self.assertEqual(len(stage_weights["output"]), 3)
        self.assertEqual(len(stage_weights["middle"]), 1)
        self.assertEqual(len(stage_weights["input"]), 2)
        self.assertTrue(stage_weights_require_wrapper(stage_weights))

    def test_runtime_state_constant_is_native(self) -> None:
        self.assertEqual(CONTROLNET_ADVANCED_RUNTIME_STATE, "rookieui_native_advanced_runtime")


if __name__ == "__main__":
    unittest.main()
