from __future__ import annotations

import unittest

from rookieui.contracts import xyz_plot


class XYZPlotContractTests(unittest.TestCase):
    def test_contract_meta_freezes_route_family_and_models(self) -> None:
        payload = xyz_plot.build_xyz_plot_contract_meta()

        self.assertEqual(payload["version"], xyz_plot.XYZ_PLOT_CONTRACT_VERSION)
        self.assertEqual(payload["route_family"], "/rookieui/xyz-plot")
        self.assertEqual(payload["supported_modes"], ["txt2img", "img2img"])
        self.assertEqual(payload["session_execution_model"], "queue_backed_rookieui_session_runner")
        self.assertEqual(payload["grid_delivery_model"], "rookieui_asset_store_grid_outputs")
        self.assertIn("/rookieui/xyz-plot/axes", payload["route_paths"])
        self.assertIn("/rookieui/xyz-plot/sessions/{session_id}/cancel", payload["route_paths"])

    def test_axis_support_payload_freezes_truthfulness_tiers(self) -> None:
        payload = xyz_plot.build_xyz_plot_axis_support_payload()
        axes = {entry["axis_id"]: entry for entry in payload["axes"]}

        self.assertEqual(payload["contract"]["surface"], "xyz_plot_axes_contract")
        self.assertEqual(axes["seed"]["support_tier"], "direct")
        self.assertEqual(axes["prompt_sr"]["support_tier"], "adapted")
        self.assertEqual(axes["face_restore"]["support_tier"], "not_supported_yet")
        self.assertEqual(axes["denoising_strength"]["mode_scopes"], ["img2img"])
        self.assertEqual(axes["hires_steps"]["mode_scopes"], ["txt2img"])
        self.assertEqual(axes["prompt_order"]["value_input_mode"], "permutation_csv")

    def test_axis_support_summary_matches_frozen_examples(self) -> None:
        payload = xyz_plot.build_xyz_plot_axis_support_payload()
        summary = payload["support_summary"]

        self.assertIn("seed", summary["direct"])
        self.assertIn("prompt_sr", summary["adapted"])
        self.assertIn("styles", summary["not_supported_yet"])
        self.assertIn("face_restore", summary["not_supported_yet"])

    def test_contract_payload_freezes_session_and_grid_delivery_models(self) -> None:
        payload = xyz_plot.build_xyz_plot_contract_payload()

        self.assertEqual(payload["contract"]["surface"], "xyz_plot_contract")
        self.assertEqual(payload["session_model"]["submission_path"], "reuse_existing_rookieui_generate_routes")
        self.assertEqual(payload["session_model"]["queue_ownership"], "session_owned_prompt_metadata")
        self.assertEqual(payload["grid_delivery"]["metadata_embedding"], "xyz_plot_axis_labels_and_values")
        self.assertTrue(payload["axis_support"])

    def test_adaptation_rules_pin_rookieui_native_direction(self) -> None:
        payload = xyz_plot.build_xyz_plot_contract_meta()
        adaptation_rules = payload["adaptation_rules"]

        self.assertTrue(any("Gradio script-slot" in rule for rule in adaptation_rules))
        self.assertTrue(any("queue-backed" in rule for rule in adaptation_rules))
        self.assertTrue(any("truthfully" in rule for rule in adaptation_rules))


if __name__ == "__main__":
    unittest.main()
