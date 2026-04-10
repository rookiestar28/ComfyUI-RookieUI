from __future__ import annotations

import unittest

from rookieui.security.asset_guard import normalize_metadata_text, validate_asset_identifier


class AssetGuardTests(unittest.TestCase):
    def test_accepts_safe_asset_identifier(self) -> None:
        self.assertEqual(validate_asset_identifier("sdxl-base_01"), "sdxl-base_01")

    def test_rejects_path_like_asset_identifier(self) -> None:
        with self.assertRaises(ValueError):
            validate_asset_identifier("../models/sdxl")

    def test_normalizes_metadata_text(self) -> None:
        self.assertEqual(
            normalize_metadata_text("  RookieUI\x00  internal   bootstrap  "),
            "RookieUI internal bootstrap",
        )
