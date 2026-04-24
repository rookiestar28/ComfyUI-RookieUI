from __future__ import annotations

import unittest

from rookieui.services.controlnet_profiles import (
    calculate_pixel_perfect_resolution,
    get_preprocessor_profile,
    serialize_preprocessor_profiles,
)


class ControlNetPreprocessorProfileTests(unittest.TestCase):
    def test_depth_anything_v2_profile_freezes_adopted_host_boundary(self) -> None:
        profile = get_preprocessor_profile("depth_anything_v2")

        self.assertEqual(profile.option_key, "depth_anything_v2")
        self.assertEqual(profile.base_module, "depth")
        self.assertEqual(profile.control_type, "Depth")
        self.assertIn("DepthAnythingV2Preprocessor", profile.preferred_host_nodes)
        self.assertTrue(profile.supports_pixel_perfect)
        self.assertIn("processor_res", profile.ui_fields)

    def test_openpose_dw_profile_declares_pose_metadata_contract(self) -> None:
        profile = get_preprocessor_profile("openpose_dw")

        self.assertEqual(profile.base_module, "openpose")
        self.assertEqual(profile.control_type, "OpenPose")
        self.assertIn("DWPreprocessor", profile.preferred_host_nodes)
        self.assertIn("openpose_json", profile.secondary_outputs)
        self.assertEqual(profile.parameter_defaults["detect_hand"], "enable")
        self.assertNotIn("threshold_a", profile.ui_fields)

    def test_pixel_perfect_resolution_matches_controlnet_aux_resize_modes(self) -> None:
        self.assertEqual(
            calculate_pixel_perfect_resolution(
                image_width=1024,
                image_height=768,
                target_width=512,
                target_height=512,
                resize_mode="crop_and_resize",
            ),
            512,
        )
        self.assertEqual(
            calculate_pixel_perfect_resolution(
                image_width=1024,
                image_height=768,
                target_width=512,
                target_height=512,
                resize_mode="resize_and_fill",
            ),
            384,
        )

    def test_serialized_profiles_are_frontend_safe(self) -> None:
        profiles = serialize_preprocessor_profiles()

        self.assertEqual(profiles["openpose_dw"]["secondary_outputs"], ["openpose_json"])
        self.assertEqual(profiles["canny"]["parameter_labels"]["threshold_a"], "Low Threshold")
        self.assertEqual(profiles["none"]["ui_fields"], [])


if __name__ == "__main__":
    unittest.main()
