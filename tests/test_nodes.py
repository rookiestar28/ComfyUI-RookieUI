from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from rookieui import nodes


class RookieUINodesTests(unittest.TestCase):
    def test_load_asset_mask_validate_inputs_accepts_partial_signature(self) -> None:
        with mock.patch.object(nodes, "resolve_asset_path", return_value=Path("C:/tmp/mask.png")):
            result = nodes.RookieUILoadAssetMask.VALIDATE_INPUTS("mask_asset.png")
        self.assertTrue(result)

    def test_load_asset_mask_validate_inputs_accepts_channel_keyword(self) -> None:
        with mock.patch.object(nodes, "resolve_asset_path", return_value=Path("C:/tmp/mask.png")):
            result = nodes.RookieUILoadAssetMask.VALIDATE_INPUTS(
                "mask_asset.png",
                channel="red",
                invert=True,
                blur_radius=8,
            )
        self.assertTrue(result)

    def test_load_asset_mask_validate_inputs_returns_error_message(self) -> None:
        with mock.patch.object(nodes, "resolve_asset_path", side_effect=ValueError("invalid asset handle")):
            result = nodes.RookieUILoadAssetMask.VALIDATE_INPUTS("bad")
        self.assertEqual(result, "invalid asset handle")

    def test_load_asset_mask_is_changed_accepts_partial_signature(self) -> None:
        with mock.patch.object(nodes.RookieUILoadAssetImage, "IS_CHANGED", return_value="digest") as mock_changed:
            changed = nodes.RookieUILoadAssetMask.IS_CHANGED("mask_asset.png")
        self.assertEqual(changed, "digest")
        mock_changed.assert_called_once_with("mask_asset.png")

    def test_controlnet_preprocess_node_is_registered(self) -> None:
        self.assertIn("RookieUIControlNetPreprocess", nodes.NODE_CLASS_MAPPINGS)

    def test_controlnet_preprocess_applies_mask_when_enabled(self) -> None:
        if nodes.torch is None:
            self.skipTest("torch is unavailable in this environment")

        preprocess = nodes.RookieUIControlNetPreprocess()
        image = nodes.torch.ones((1, 2, 2, 3), dtype=nodes.torch.float32)
        mask = nodes.torch.tensor([[[1.0, 0.0], [0.5, 0.0]]], dtype=nodes.torch.float32)

        output, = preprocess.preprocess(
            image=image,
            module="none",
            processor_res=512,
            threshold_a=64.0,
            threshold_b=64.0,
            use_mask=True,
            mask=mask,
        )

        self.assertAlmostEqual(float(output[0, 0, 0, 0]), 1.0, places=4)
        self.assertAlmostEqual(float(output[0, 0, 1, 0]), 0.0, places=4)
        self.assertAlmostEqual(float(output[0, 1, 1, 0]), 0.0, places=4)

    def test_controlnet_preprocess_unsupported_module_falls_back_to_passthrough(self) -> None:
        if nodes.torch is None:
            self.skipTest("torch is unavailable in this environment")

        preprocess = nodes.RookieUIControlNetPreprocess()
        image = nodes.torch.full((1, 2, 2, 3), 0.25, dtype=nodes.torch.float32)

        output, = preprocess.preprocess(
            image=image,
            module="not-a-real-module",
            processor_res=512,
            threshold_a=64.0,
            threshold_b=64.0,
            use_mask=False,
            mask=None,
        )

        self.assertAlmostEqual(float(output[0, 0, 0, 0]), 0.25, places=4)
        self.assertAlmostEqual(float(output[0, 1, 1, 2]), 0.25, places=4)


if __name__ == "__main__":
    unittest.main()
