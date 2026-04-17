from __future__ import annotations

import unittest
from unittest import mock

from rookieui.services import xyz_plot_axes


class XYZPlotAxisRegistryTests(unittest.TestCase):
    def test_axis_payload_includes_dynamic_choices_from_inventory_and_compatibility(self) -> None:
        with (
            mock.patch.object(xyz_plot_axes, "_compatibility_sampler_choices", return_value=["euler", "dpmpp_2m"]),
            mock.patch.object(xyz_plot_axes, "_compatibility_scheduler_choices", return_value=["normal", "karras"]),
            mock.patch.object(
                xyz_plot_axes,
                "discover_model_inventory",
                return_value=mock.Mock(
                    checkpoints=["dreamshaper.safetensors"],
                    vae=["Automatic"],
                    upscale_models=["4x-UltraSharp"],
                ),
            ),
        ):
            payload = xyz_plot_axes.build_xyz_plot_axes_payload()

        self.assertEqual(payload["contract"]["surface"], "xyz_plot_axes")
        self.assertEqual(payload["axes"]["sampler"]["choices"], ["euler", "dpmpp_2m"])
        self.assertEqual(payload["axes"]["scheduler"]["choices"], ["normal", "karras"])
        self.assertEqual(payload["axes"]["checkpoint_name"]["choices"], ["dreamshaper.safetensors"])
        self.assertEqual(payload["axes"]["hires_upscaler"]["choices"], ["4x-UltraSharp"])

    def test_axis_summary_preserves_truthfulness_tiers(self) -> None:
        payload = xyz_plot_axes.build_xyz_plot_axes_payload()

        self.assertGreater(payload["summary"]["direct"], 0)
        self.assertGreater(payload["summary"]["adapted"], 0)
        self.assertGreater(payload["summary"]["not_supported_yet"], 0)
        self.assertEqual(payload["axes"]["refiner_checkpoint"]["truthfulness"], "gated")
        self.assertEqual(payload["axes"]["steps"]["truthfulness"], "runnable")

    def test_resolve_xyz_axis_contract_rejects_unknown_axis(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown xyz axis"):
            xyz_plot_axes.resolve_xyz_axis_contract("does_not_exist")
