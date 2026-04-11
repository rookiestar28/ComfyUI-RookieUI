from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from rookieui.services import asset_store


class AssetStoreCleanupTests(unittest.TestCase):
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

    def test_cleanup_removes_stale_runtime_assets(self) -> None:
        stale = self.input_root / "stale.png"
        fresh = self.input_root / "fresh.png"
        stale.write_bytes(b"stale")
        fresh.write_bytes(b"fresh")

        now = time.time()
        two_hours_ago = now - (2 * 3600)
        stale.touch()
        fresh.touch()
        stale.chmod(0o666)
        fresh.chmod(0o666)
        os.utime(stale, (two_hours_ago, two_hours_ago))
        os.utime(fresh, (now, now))

        with mock.patch.object(asset_store, "_RUNTIME_RETENTION_HOURS", 1):
            asset_store._ensure_runtime_dirs()

        self.assertFalse(stale.exists())
        self.assertTrue(fresh.exists())

    def test_cleanup_keeps_only_latest_assets_when_overflowed(self) -> None:
        now = time.time()
        for index in range(4):
            path = self.output_root / f"output_{index}.png"
            path.write_bytes(f"f{index}".encode("ascii"))
            timestamp = now - (100 - index)
            os.utime(path, (timestamp, timestamp))

        with (
            mock.patch.object(asset_store, "_RUNTIME_RETENTION_HOURS", 9999),
            mock.patch.object(asset_store, "_RUNTIME_MAX_FILES_PER_DIR", 2),
        ):
            asset_store._ensure_runtime_dirs()

        remaining = sorted(path.name for path in self.output_root.iterdir() if path.is_file())
        self.assertEqual(remaining, ["output_2.png", "output_3.png"])
