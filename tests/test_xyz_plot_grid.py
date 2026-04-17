from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from rookieui.services import asset_store, xyz_plot_grid


class XYZPlotGridTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.runtime_dir.cleanup)
        runtime_root = Path(self.runtime_dir.name)
        self.input_root = runtime_root / "input"
        self.output_root = runtime_root / "output"
        self.input_root.mkdir(parents=True, exist_ok=True)
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.patchers = [
            mock.patch.object(asset_store, "_INPUT_ROOT", self.input_root),
            mock.patch.object(asset_store, "_OUTPUT_ROOT", self.output_root),
            mock.patch.object(asset_store, "_RUNTIME_CLEANUP_INTERVAL_SECONDS", 0),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        asset_store._reset_runtime_cleanup_state_for_tests()

    def _save_cell_image(self, color: str, *, prefix: str) -> str:
        image = Image.new("RGB", (32, 24), color=color)
        return asset_store.save_output_image(image, prefix=prefix).handle

    def test_build_xyz_plot_grid_results_creates_main_and_subgrid_assets_with_metadata(self) -> None:
        cell_handles = [
            self._save_cell_image("red", prefix="xyz_cell"),
            self._save_cell_image("blue", prefix="xyz_cell"),
            self._save_cell_image("green", prefix="xyz_cell"),
            self._save_cell_image("yellow", prefix="xyz_cell"),
        ]
        session = {
            "session_id": "xyz-demo",
            "mode": "txt2img",
            "axes": [
                {
                    "slot": "X",
                    "axis_id": "steps",
                    "title": "Steps",
                    "parsed_values": [{"label": "10"}, {"label": "20"}],
                },
                {
                    "slot": "Y",
                    "axis_id": "cfg_scale",
                    "title": "CFG Scale",
                    "parsed_values": [{"label": "5"}],
                },
                {
                    "slot": "Z",
                    "axis_id": "sampler",
                    "title": "Sampler",
                    "parsed_values": [{"label": "Euler"}, {"label": "DPM"}],
                },
            ],
            "grid_options": {
                "draw_legend": True,
                "include_sub_grids": True,
                "include_lone_images": True,
                "margin_size": 4,
            },
            "seed_policy": {
                "keep_negative_one_seed": False,
                "vary_seeds_x": False,
                "vary_seeds_y": False,
                "vary_seeds_z": False,
                "fixed_base_seed": 101,
                "fixed_axis_values": {"X": [111, 222]},
            },
            "cells": [
                {
                    "cell_id": "cell-1",
                    "status": "completed",
                    "axis_indices": {"X": 0, "Y": 0, "Z": 0},
                    "bindings": [],
                    "prompt_id": "p1",
                    "reusable_outputs": [cell_handles[0]],
                    "output_filenames": [cell_handles[0]],
                },
                {
                    "cell_id": "cell-2",
                    "status": "completed",
                    "axis_indices": {"X": 1, "Y": 0, "Z": 0},
                    "bindings": [],
                    "prompt_id": "p2",
                    "reusable_outputs": [cell_handles[1]],
                    "output_filenames": [cell_handles[1]],
                },
                {
                    "cell_id": "cell-3",
                    "status": "completed",
                    "axis_indices": {"X": 0, "Y": 0, "Z": 1},
                    "bindings": [],
                    "prompt_id": "p3",
                    "reusable_outputs": [cell_handles[2]],
                    "output_filenames": [cell_handles[2]],
                },
                {
                    "cell_id": "cell-4",
                    "status": "completed",
                    "axis_indices": {"X": 1, "Y": 0, "Z": 1},
                    "bindings": [],
                    "prompt_id": "p4",
                    "reusable_outputs": [cell_handles[3]],
                    "output_filenames": [cell_handles[3]],
                },
            ],
        }

        payload = xyz_plot_grid.build_xyz_plot_grid_results(session)

        self.assertEqual(payload["status"], "ready")
        self.assertTrue(payload["main_grid"]["asset_handle"].startswith("xyz_plot_grid_"))
        self.assertEqual(len(payload["sub_grids"]), 2)
        self.assertEqual(len(payload["lone_images"]), 4)
        main_path = asset_store.resolve_asset_path(payload["main_grid"]["asset_handle"])
        main_image = Image.open(main_path)
        metadata = json.loads(main_image.text["rookieui_xyz_plot"])
        self.assertEqual(metadata["session_id"], "xyz-demo")
        self.assertEqual(metadata["grid_role"], "main_grid")
        self.assertEqual(metadata["seed_policy"]["fixed_base_seed"], 101)
        self.assertEqual(metadata["seed_policy"]["fixed_axis_values"]["X"], [111, 222])

    def test_build_xyz_plot_grid_results_reports_incomplete_when_completed_cells_lack_assets(self) -> None:
        session = {
            "session_id": "xyz-incomplete",
            "mode": "txt2img",
            "axes": [
                {
                    "slot": "X",
                    "axis_id": "steps",
                    "title": "Steps",
                    "parsed_values": [{"label": "10"}],
                }
            ],
            "grid_options": {
                "draw_legend": True,
                "include_sub_grids": False,
                "include_lone_images": False,
                "margin_size": 0,
            },
            "cells": [
                {
                    "cell_id": "cell-1",
                    "status": "completed",
                    "axis_indices": {"X": 0},
                    "bindings": [],
                    "prompt_id": "p1",
                    "reusable_outputs": [],
                    "output_filenames": [],
                }
            ],
        }

        payload = xyz_plot_grid.build_xyz_plot_grid_results(session)

        self.assertEqual(payload["status"], "incomplete")
        self.assertIn("no reusable output asset", " ".join(payload["warnings"]).lower())

    def test_build_xyz_plot_grid_results_emits_partial_preview_for_running_session(self) -> None:
        first_handle = self._save_cell_image("red", prefix="xyz_cell")
        session = {
            "session_id": "xyz-running",
            "mode": "txt2img",
            "axes": [
                {
                    "slot": "X",
                    "axis_id": "steps",
                    "title": "Steps",
                    "parsed_values": [{"label": "10"}, {"label": "20"}],
                },
                {
                    "slot": "Y",
                    "axis_id": "cfg_scale",
                    "title": "CFG Scale",
                    "parsed_values": [{"label": "5"}],
                },
            ],
            "grid_options": {
                "draw_legend": True,
                "include_sub_grids": False,
                "include_lone_images": False,
                "margin_size": 4,
            },
            "cells": [
                {
                    "cell_id": "cell-1",
                    "status": "completed",
                    "axis_indices": {"X": 0, "Y": 0, "Z": 0},
                    "bindings": [],
                    "prompt_id": "p1",
                    "reusable_outputs": [first_handle],
                    "output_filenames": [first_handle],
                },
                {
                    "cell_id": "cell-2",
                    "status": "queued",
                    "axis_indices": {"X": 1, "Y": 0, "Z": 0},
                    "bindings": [],
                    "prompt_id": "p2",
                    "reusable_outputs": [],
                    "output_filenames": [],
                },
            ],
        }

        payload = xyz_plot_grid.build_xyz_plot_grid_results(session)

        self.assertEqual(payload["status"], "running")
        self.assertTrue(str(payload["main_grid"]["preview_data_url"]).startswith("data:image/png;base64,"))

    def test_build_xyz_plot_grid_results_resolves_live_host_output_filenames(self) -> None:
        host_output_root = Path(self.runtime_dir.name) / "host-output"
        host_output_root.mkdir(parents=True, exist_ok=True)
        host_output_file = host_output_root / "RookieUI_00089_.png"
        Image.new("RGB", (32, 24), color="purple").save(host_output_file, format="PNG")
        folder_paths_module = mock.Mock()
        folder_paths_module.get_output_directory.return_value = str(host_output_root)
        session = {
            "session_id": "xyz-live-host",
            "mode": "txt2img",
            "axes": [
                {
                    "slot": "X",
                    "axis_id": "steps",
                    "title": "Steps",
                    "parsed_values": [{"label": "10"}],
                }
            ],
            "grid_options": {
                "draw_legend": True,
                "include_sub_grids": False,
                "include_lone_images": True,
                "margin_size": 0,
            },
            "cells": [
                {
                    "cell_id": "cell-1",
                    "status": "completed",
                    "axis_indices": {"X": 0},
                    "bindings": [],
                    "prompt_id": "p1",
                    "reusable_outputs": ["RookieUI_00089_.png"],
                    "output_filenames": ["RookieUI_00089_.png"],
                }
            ],
        }

        with mock.patch.object(asset_store, "_load_folder_paths_module", return_value=folder_paths_module):
            payload = xyz_plot_grid.build_xyz_plot_grid_results(session)

        self.assertEqual(payload["status"], "ready")
        self.assertEqual(len(payload["lone_images"]), 1)
        self.assertTrue(payload["main_grid"]["asset_handle"].startswith("xyz_plot_grid_"))

    def test_build_xyz_plot_grid_results_mirrors_grids_to_host_output_with_axis_descriptor_framing(self) -> None:
        host_output_root = Path(self.runtime_dir.name) / "host-output"
        host_output_root.mkdir(parents=True, exist_ok=True)
        folder_paths_module = mock.Mock()
        folder_paths_module.get_output_directory.return_value = str(host_output_root)
        cell_handles = [
            self._save_cell_image("red", prefix="xyz_cell"),
            self._save_cell_image("blue", prefix="xyz_cell"),
            self._save_cell_image("green", prefix="xyz_cell"),
            self._save_cell_image("yellow", prefix="xyz_cell"),
        ]
        session = {
            "session_id": "xyz-host-grid",
            "mode": "txt2img",
            "axes": [
                {
                    "slot": "X",
                    "axis_id": "steps",
                    "title": "Steps",
                    "parsed_values": [{"label": "10"}, {"label": "20"}],
                },
                {
                    "slot": "Y",
                    "axis_id": "cfg_scale",
                    "title": "CFG Scale",
                    "parsed_values": [{"label": "5"}],
                },
                {
                    "slot": "Z",
                    "axis_id": "sampler",
                    "title": "Sampler",
                    "parsed_values": [{"label": "Euler"}, {"label": "DPM"}],
                },
            ],
            "grid_options": {
                "draw_legend": True,
                "include_sub_grids": True,
                "include_lone_images": False,
                "margin_size": 4,
            },
            "cells": [
                {
                    "cell_id": "cell-1",
                    "status": "completed",
                    "axis_indices": {"X": 0, "Y": 0, "Z": 0},
                    "bindings": [],
                    "prompt_id": "p1",
                    "reusable_outputs": [cell_handles[0]],
                    "output_filenames": [cell_handles[0]],
                },
                {
                    "cell_id": "cell-2",
                    "status": "completed",
                    "axis_indices": {"X": 1, "Y": 0, "Z": 0},
                    "bindings": [],
                    "prompt_id": "p2",
                    "reusable_outputs": [cell_handles[1]],
                    "output_filenames": [cell_handles[1]],
                },
                {
                    "cell_id": "cell-3",
                    "status": "completed",
                    "axis_indices": {"X": 0, "Y": 0, "Z": 1},
                    "bindings": [],
                    "prompt_id": "p3",
                    "reusable_outputs": [cell_handles[2]],
                    "output_filenames": [cell_handles[2]],
                },
                {
                    "cell_id": "cell-4",
                    "status": "completed",
                    "axis_indices": {"X": 1, "Y": 0, "Z": 1},
                    "bindings": [],
                    "prompt_id": "p4",
                    "reusable_outputs": [cell_handles[3]],
                    "output_filenames": [cell_handles[3]],
                },
            ],
        }

        with mock.patch.object(asset_store, "_load_folder_paths_module", return_value=folder_paths_module):
            payload = xyz_plot_grid.build_xyz_plot_grid_results(session)

        self.assertEqual(payload["status"], "ready")
        runtime_main_path = asset_store.resolve_asset_path(payload["main_grid"]["asset_handle"])
        runtime_subgrid_path = asset_store.resolve_asset_path(payload["sub_grids"][0]["asset_handle"])
        with Image.open(runtime_main_path) as runtime_main_image, Image.open(runtime_subgrid_path) as runtime_subgrid_image:
            self.assertGreater(runtime_main_image.width, (runtime_subgrid_image.width * 2) + 4)
        self.assertGreaterEqual(len(list(host_output_root.glob("xyz_plot_grid_*.png"))), 1)
        self.assertGreaterEqual(len(list(host_output_root.glob("xyz_plot_subgrid_*.png"))), 2)
