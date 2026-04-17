from __future__ import annotations

import unittest

from rookieui.services.xyz_plot_estimate import build_xyz_plot_estimate_payload
from rookieui.services.xyz_plot_values import parse_xyz_axis_values
from rookieui.services.xyz_plot_axes import resolve_xyz_axis_contract


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
