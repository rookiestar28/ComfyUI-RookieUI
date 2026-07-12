from __future__ import annotations

import base64
import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

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

    def test_resolve_generated_output_path_prefers_runtime_asset_handles(self) -> None:
        generated = self.output_root / "runtime-grid.png"
        generated.write_bytes(b"runtime")

        resolved = asset_store.resolve_generated_output_path("runtime-grid.png")

        self.assertEqual(resolved, generated)

    def test_resolve_generated_output_path_falls_back_to_host_output_directory(self) -> None:
        host_output_root = Path(self.runtime_dir.name) / "host-output"
        host_output_root.mkdir(parents=True, exist_ok=True)
        host_output_file = host_output_root / "RookieUI_00089_.png"
        host_output_file.write_bytes(b"host")
        folder_paths_module = mock.Mock()
        folder_paths_module.get_output_directory.return_value = str(host_output_root)

        with mock.patch.object(asset_store, "_load_folder_paths_module", return_value=folder_paths_module):
            resolved = asset_store.resolve_generated_output_path("RookieUI_00089_.png")

        self.assertEqual(resolved, host_output_file.resolve())

    def test_resolve_generated_output_path_supports_relative_host_subfolders(self) -> None:
        host_output_root = Path(self.runtime_dir.name) / "host-output"
        nested_root = host_output_root / "xyz"
        nested_root.mkdir(parents=True, exist_ok=True)
        nested_file = nested_root / "RookieUI_00090_.png"
        nested_file.write_bytes(b"host")
        folder_paths_module = mock.Mock()
        folder_paths_module.get_output_directory.return_value = str(host_output_root)

        with mock.patch.object(asset_store, "_load_folder_paths_module", return_value=folder_paths_module):
            resolved = asset_store.resolve_generated_output_path("xyz/RookieUI_00090_.png")

        self.assertEqual(resolved, nested_file.resolve())

    def test_decode_image_data_rejects_oversized_content_before_storage(self) -> None:
        self.assertTrue(hasattr(asset_store, "MAX_IMAGE_UPLOAD_BYTES"))
        if not hasattr(asset_store, "MAX_IMAGE_UPLOAD_BYTES"):
            return

        encoded = base64.b64encode(b"12345").decode("ascii")
        with mock.patch.object(asset_store, "MAX_IMAGE_UPLOAD_BYTES", 4):
            with self.assertRaisesRegex(ValueError, "at most 4 bytes"):
                asset_store.decode_image_data(f"data:image/png;base64,{encoded}")

    def test_decode_image_data_rejects_oversized_dimensions(self) -> None:
        self.assertTrue(hasattr(asset_store, "MAX_IMAGE_DIMENSION"))
        if not hasattr(asset_store, "MAX_IMAGE_DIMENSION"):
            return

        buffer = io.BytesIO()
        Image.new("RGB", (5, 1), color="white").save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        with mock.patch.object(asset_store, "MAX_IMAGE_DIMENSION", 4):
            with self.assertRaisesRegex(ValueError, "dimensions"):
                asset_store.decode_image_data(f"data:image/png;base64,{encoded}")
