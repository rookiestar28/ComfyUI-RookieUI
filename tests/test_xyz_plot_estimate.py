from __future__ import annotations

import unittest

from rookieui.services.xyz_plot_estimate import build_xyz_plot_estimate_payload
from rookieui.services.xyz_plot_values import parse_xyz_axis_values
from rookieui.services.xyz_plot_axes import get_xyz_axis_choice_entries, resolve_xyz_axis_contract


class XYZPlotValueParserTests(unittest.TestCase):
    def test_parse_int_range_and_count_syntax(self) -> None:
        axis = resolve_xyz_axis_contract("steps")

        entries = parse_xyz_axis_values("10-14(2),20-24[3]", axis)

        self.assertEqual([entry.value for entry in entries], [10, 12, 14, 20, 22, 24])

    def test_parse_float_range_and_size_values(self) -> None:
        cfg_axis = resolve_xyz_axis_contract("cfg_scale")
        size_axis = resolve_xyz_axis_contract("size")

        cfg_entries = parse_xyz_axis_values("5.0-6.0(0.5)", cfg_axis)
        size_entries = parse_xyz_axis_values("512x768, 1024x1024", size_axis)

        self.assertEqual([entry.value for entry in cfg_entries], [5.0, 5.5, 6.0])
        self.assertEqual(size_entries[0].value, {"width": 512, "height": 768})
        self.assertEqual(size_entries[1].label, "1024x1024")

    def test_parse_prompt_order_permutations(self) -> None:
        axis = resolve_xyz_axis_contract("prompt_order")

        entries = parse_xyz_axis_values("cat, dog, bird", axis)

        self.assertEqual(len(entries), 6)
        self.assertIn(["cat", "dog", "bird"], [entry.value for entry in entries])

    def test_parse_prompt_order_allows_single_token(self) -> None:
        axis = resolve_xyz_axis_contract("prompt_order")

        entries = parse_xyz_axis_values("cat", axis)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].value, ["cat"])

    def test_parse_prompt_sr_uses_first_token_as_search_source(self) -> None:
        axis = resolve_xyz_axis_contract("prompt_sr")

        entries = parse_xyz_axis_values("cat, dog, fox", axis)

        self.assertEqual(
            [entry.value for entry in entries],
            [
                {"source": "cat", "target": "cat"},
                {"source": "cat", "target": "dog"},
                {"source": "cat", "target": "fox"},
            ],
        )
        self.assertEqual([entry.label for entry in entries], ["cat", "dog", "fox"])

    def test_parse_sampler_accepts_a1111_label_and_resolves_to_canonical_id(self) -> None:
        axis = resolve_xyz_axis_contract("sampler")

        entries = parse_xyz_axis_values(
            "Euler a, dpmpp_2m",
            axis,
            choices=get_xyz_axis_choice_entries("sampler"),
        )

        self.assertEqual(
            [entry.value for entry in entries],
            ["euler_ancestral", "dpmpp_2m"],
        )
        self.assertEqual(
            [entry.label for entry in entries],
            ["Euler a", "DPM++ 2M"],
        )

    def test_parse_scheduler_accepts_automatic_label(self) -> None:
        axis = resolve_xyz_axis_contract("scheduler")

        entries = parse_xyz_axis_values(
            "Automatic, Karras",
            axis,
            choices=get_xyz_axis_choice_entries("scheduler"),
        )

        self.assertEqual([entry.value for entry in entries], ["normal", "karras"])
        self.assertEqual([entry.label for entry in entries], ["Automatic", "Karras"])

    def test_parse_checkpoint_accepts_unique_partial_fragment(self) -> None:
        axis = resolve_xyz_axis_contract("checkpoint_name")

        entries = parse_xyz_axis_values(
            "pony",
            axis,
            choices=[
                {
                    "value": "checkpoints/ponyDiffusion.safetensors",
                    "label": "checkpoints/ponyDiffusion.safetensors",
                    "aliases": ["ponyDiffusion.safetensors"],
                    "allow_partial_match": True,
                },
                {
                    "value": "checkpoints/sdxlBase.safetensors",
                    "label": "checkpoints/sdxlBase.safetensors",
                    "aliases": ["sdxlBase.safetensors"],
                    "allow_partial_match": True,
                },
            ],
        )

        self.assertEqual(entries[0].value, "checkpoints/ponyDiffusion.safetensors")
        self.assertEqual(entries[0].label, "checkpoints/ponyDiffusion.safetensors")

    def test_parse_hires_upscaler_accepts_a1111_facing_label_and_runtime_alias(self) -> None:
        axis = resolve_xyz_axis_contract("hires_upscaler")

        entries = parse_xyz_axis_values(
            "Latent, Bislerp",
            axis,
            choices=get_xyz_axis_choice_entries("hires_upscaler"),
        )

        self.assertEqual([entry.value for entry in entries], ["bilinear", "bislerp"])
        self.assertEqual([entry.label for entry in entries], ["Latent", "Bislerp"])


class XYZPlotEstimateTests(unittest.TestCase):
    def test_estimate_counts_cells_and_steps(self) -> None:
        payload = build_xyz_plot_estimate_payload(
            {
                "mode": "txt2img",
                "base_request": {"steps": 20, "width": 512, "height": 512},
                "axes": [
                    {"axis_id": "steps", "values": "10,20"},
                    {"axis_id": "cfg_scale", "values": "5.0-6.0(0.5)"},
                ],
            }
        )

        self.assertTrue(payload["can_run"])
        self.assertEqual(payload["estimate"]["cell_count"], 6)
        self.assertEqual(payload["estimate"]["generated_image_count"], 6)
        self.assertEqual(payload["estimate"]["total_step_estimate"], 90)

    def test_estimate_uses_size_axis_for_grid_megapixel_guard(self) -> None:
        payload = build_xyz_plot_estimate_payload(
            {
                "mode": "txt2img",
                "base_request": {"steps": 20, "width": 1024, "height": 1024},
                "axes": [
                    {"axis_id": "size", "values": "4096x4096,4096x4096,4096x4096,4096x4096,4096x4096,4096x4096,4096x4096,4096x4096,4096x4096,4096x4096,4096x4096,4096x4096,4096x4096"},
                ],
            }
        )

        self.assertFalse(payload["can_run"])
        self.assertIn("XYZ_GRID_TOO_LARGE", payload["warning_codes"])

    def test_estimate_rejects_mode_ineligible_axis(self) -> None:
        with self.assertRaisesRegex(ValueError, "not supported for txt2img"):
            build_xyz_plot_estimate_payload(
                {
                    "mode": "txt2img",
                    "axes": [{"axis_id": "denoising_strength", "values": "0.4,0.6"}],
                }
            )

    def test_estimate_treats_hires_steps_zero_as_same_as_current_steps(self) -> None:
        payload = build_xyz_plot_estimate_payload(
            {
                "mode": "txt2img",
                "base_request": {"steps": 24, "hires_enabled": True, "hires_steps": 0},
                "axes": [{"axis_id": "hires_steps", "values": "0,12"}],
            }
        )

        self.assertTrue(payload["can_run"])
        self.assertEqual(payload["estimate"]["cell_count"], 2)
        self.assertEqual(payload["estimate"]["total_step_estimate"], 84)
