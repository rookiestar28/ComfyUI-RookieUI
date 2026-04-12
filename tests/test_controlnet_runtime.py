from __future__ import annotations

import unittest

from rookieui.services import controlnet_runtime as runtime


class _FakeAioDepth:
    @staticmethod
    def INPUT_TYPES() -> dict[str, object]:
        return {
            "required": {"image": ("IMAGE",)},
            "optional": {
                "preprocessor": (
                    ["none", "depth_anything_v2", "depth_midas"],
                    {"default": "none"},
                ),
                "resolution": ("INT", {"default": 512}),
            },
        }


class _FakeAioSoftEdge:
    @staticmethod
    def INPUT_TYPES() -> dict[str, object]:
        return {
            "required": {"image": ("IMAGE",)},
            "optional": {
                "preprocessor": (
                    ["none", "hed_safe", "lineart_standard"],
                    {"default": "none"},
                ),
                "resolution": ("INT", {"default": 512}),
            },
        }


class ControlNetRuntimeHeuristicsTests(unittest.TestCase):
    def test_select_aio_preprocessor_name_matches_normalized_explicit_candidates(self) -> None:
        selected = runtime._select_aio_preprocessor_name(_FakeAioDepth, "depth")
        self.assertEqual(selected, "depth_anything_v2")

    def test_select_aio_preprocessor_name_uses_keyword_ranking_when_explicit_candidates_miss(self) -> None:
        selected = runtime._select_aio_preprocessor_name(_FakeAioSoftEdge, "softedge")
        self.assertEqual(selected, "hed_safe")
