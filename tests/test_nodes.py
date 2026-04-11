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


if __name__ == "__main__":
    unittest.main()
