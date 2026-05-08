from __future__ import annotations

import unittest
from unittest import mock

from rookieui.services import xyz_plot_axes


class XYZPlotAxisRegistryTests(unittest.TestCase):
    def test_axis_payload_includes_dynamic_choices_from_inventory_and_compatibility(self) -> None:
        with (
            mock.patch.object(
                xyz_plot_axes,
                "build_compatibility_payload",
                return_value={
                    "samplers": [
                        {"id": "euler_ancestral", "title": "Euler a", "aliases": ["euler a"]},
                        {"id": "dpmpp_2m", "title": "DPM++ 2M", "aliases": []},
                    ],
                    "schedulers": [
                        {"id": "normal", "title": "Normal", "aliases": ["automatic"]},
                        {"id": "karras", "title": "Karras", "aliases": []},
                    ],
                },
            ),
            mock.patch.object(
                xyz_plot_axes,
                "discover_model_inventory",
                return_value=mock.Mock(
                    checkpoints=["dreamshaper.safetensors"],
                    diffusion_models=[],
                    vae=["anime.vae.safetensors"],
                    upscale_models=["4x-UltraSharp"],
                ),
            ),
        ):
            payload = xyz_plot_axes.build_xyz_plot_axes_payload()

        self.assertEqual(payload["contract"]["surface"], "xyz_plot_axes")
        self.assertEqual(payload["axes"]["sampler"]["choices"], ["Euler a", "DPM++ 2M"])
        self.assertEqual(payload["axes"]["scheduler"]["choices"], ["Automatic", "Karras"])
        self.assertEqual(payload["axes"]["checkpoint_name"]["choices"], ["dreamshaper.safetensors"])
        self.assertEqual(payload["axes"]["vae"]["choices"][:3], ["Automatic", "None", "anime.vae.safetensors"])
        self.assertEqual(
            payload["axes"]["hires_upscaler"]["choices"],
            ["Latent", "Latent (bicubic)", "Latent (nearest-exact)", "Area", "Bislerp"],
        )
        self.assertEqual(payload["axes"]["hires_upscaler"]["choice_source"], "rookieui.fixed.hires_upscale_method")

    def test_checkpoint_name_axis_includes_diffusion_model_inventory_entries(self) -> None:
        with mock.patch.object(
            xyz_plot_axes,
            "discover_model_inventory",
            return_value=mock.Mock(
                checkpoints=["SD15\\dreamshaper.safetensors"],
                diffusion_models=[
                    "Qwen\\qwen_image_2512_fp8_e4m3fn.safetensors",
                    "Z-Image\\z_image_bf16.safetensors",
                ],
                vae=[],
                upscale_models=[],
            ),
        ):
            payload = xyz_plot_axes.build_xyz_plot_axes_payload()

        checkpoint_axis = payload["axes"]["checkpoint_name"]
        expected_choices = [
            "SD15\\dreamshaper.safetensors",
            "Qwen\\qwen_image_2512_fp8_e4m3fn.safetensors",
            "Z-Image\\z_image_bf16.safetensors",
        ]
        self.assertEqual(checkpoint_axis["choices"], expected_choices)
        self.assertEqual(
            [entry["value"] for entry in checkpoint_axis["choice_entries"]],
            expected_choices,
        )
        self.assertIn("qwen_image_2512_fp8_e4m3fn.safetensors", checkpoint_axis["choice_entries"][1]["aliases"])
        self.assertIn("z_image_bf16.safetensors", checkpoint_axis["choice_entries"][2]["aliases"])
        self.assertEqual(checkpoint_axis["choice_source"], "model_inventory.checkpoints+diffusion_models")

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
