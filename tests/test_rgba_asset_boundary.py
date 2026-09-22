from __future__ import annotations

import base64
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
from PIL import Image

from rookieui import nodes
from rookieui.services import asset_store, img2img, pnginfo


class _Tensor(np.ndarray):
    def to(self, *, dtype):
        return np.asarray(self, dtype=dtype).view(_Tensor)

    def unsqueeze(self, dim):
        return np.expand_dims(self, axis=dim).view(_Tensor)

    def cpu(self):
        return self

    def numpy(self):
        return np.asarray(self)


class _Torch:
    float32 = np.float32

    @staticmethod
    def from_numpy(array):
        return np.asarray(array).view(_Tensor)

    @staticmethod
    def zeros(shape, *, dtype, device):
        _ = device
        return np.zeros(shape, dtype=dtype).view(_Tensor)

    @staticmethod
    def cat(values, *, dim):
        return np.concatenate(values, axis=dim).view(_Tensor)


class RgbaAssetBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def _load(self, image: Image.Image, *, preserve_alpha=False, first_frame_only=False):
        path = self.root / "source.png"
        image.save(path)
        with (
            mock.patch.object(nodes, "torch", _Torch),
            mock.patch.object(nodes, "resolve_asset_path", return_value=path),
        ):
            return nodes.RookieUILoadAssetImage().load_asset(
                "source.png", preserve_alpha=preserve_alpha, first_frame_only=first_frame_only
            )

    def test_default_rgb_and_inverse_alpha_mask_are_unchanged(self) -> None:
        source = Image.new("RGBA", (2, 1))
        source.putdata([(20, 40, 60, 255), (80, 100, 120, 64)])
        image, mask = self._load(source)
        self.assertEqual(image.shape, (1, 1, 2, 3))
        np.testing.assert_allclose(image[0, 0, 1], [80 / 255, 100 / 255, 120 / 255])
        np.testing.assert_allclose(mask[0, 0], [0, 1 - 64 / 255])

    def test_rgba_opt_in_preserves_partial_alpha_and_rgb_adds_opaque_alpha(self) -> None:
        source = Image.new("RGBA", (2, 1))
        source.putdata([(20, 40, 60, 0), (80, 100, 120, 128)])
        image, mask = self._load(source, preserve_alpha=True)
        self.assertEqual(image.shape, (1, 1, 2, 4))
        np.testing.assert_allclose(image[0, 0, :, 3], [0, 128 / 255])
        np.testing.assert_allclose(mask[0, 0], [1, 1 - 128 / 255])
        rgb, rgb_mask = self._load(Image.new("RGB", (2, 1), (30, 60, 90)), preserve_alpha=True)
        np.testing.assert_allclose(rgb[0, 0, :, 3], [1, 1])
        self.assertEqual(rgb_mask.shape, (1, 64, 64))

    def test_palette_transparency_and_exif_orientation(self) -> None:
        palette = Image.new("P", (2, 1))
        palette.putpalette([255, 0, 0, 0, 255, 0] + [0] * 762)
        palette.putdata([0, 1])
        palette.info["transparency"] = 1
        image, mask = self._load(palette, preserve_alpha=True)
        np.testing.assert_allclose(image[0, 0, :, 3], [1, 0])
        np.testing.assert_allclose(mask[0, 0], [0, 1])

        rotated = Image.new("RGBA", (2, 1))
        rotated.putdata([(10, 20, 30, 255), (40, 50, 60, 64)])
        exif = Image.Exif()
        exif[274] = 6
        path = self.root / "oriented.png"
        rotated.save(path, exif=exif)
        with (mock.patch.object(nodes, "torch", _Torch), mock.patch.object(nodes, "resolve_asset_path", return_value=path)):
            oriented, oriented_mask = nodes.RookieUILoadAssetImage().load_asset("oriented.png", preserve_alpha=True)
        self.assertEqual(oriented.shape, (1, 2, 1, 4))
        np.testing.assert_allclose(oriented[:, :, 0, 3].reshape(-1), [1, 64 / 255])
        self.assertEqual(oriented_mask.shape, (1, 2, 1))

    def test_first_frame_opt_in_does_not_change_default_animation_batch(self) -> None:
        frames = [Image.new("RGBA", (2, 1), (10, 20, 30, 255)), Image.new("RGBA", (2, 1), (40, 50, 60, 64))]
        path = self.root / "animated.gif"
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=100, loop=0)
        with (mock.patch.object(nodes, "torch", _Torch), mock.patch.object(nodes, "resolve_asset_path", return_value=path)):
            default, _ = nodes.RookieUILoadAssetImage().load_asset("animated.gif")
            first, _ = nodes.RookieUILoadAssetImage().load_asset(
                "animated.gif", preserve_alpha=True, first_frame_only=True
            )
        self.assertEqual(default.shape[0], 2)
        self.assertEqual(first.shape, (1, 1, 2, 4))

    def test_mode_flags_invalidate_cache_and_reject_non_boolean_values(self) -> None:
        path = self.root / "source.png"
        Image.new("RGBA", (1, 1), (1, 2, 3, 4)).save(path)
        with mock.patch.object(nodes, "resolve_asset_path", return_value=path):
            digest_default = nodes.RookieUILoadAssetImage.IS_CHANGED("source.png")
            digest_rgba = nodes.RookieUILoadAssetImage.IS_CHANGED("source.png", preserve_alpha=True)
            digest_first = nodes.RookieUILoadAssetImage.IS_CHANGED("source.png", first_frame_only=True)
            self.assertEqual(len({digest_default, digest_rgba, digest_first}), 3)
            self.assertEqual(
                nodes.RookieUILoadAssetImage.VALIDATE_INPUTS("source.png", preserve_alpha="true"),
                "preserve_alpha and first_frame_only must be booleans.",
            )

    def test_saved_png_round_trip_and_metadata_disable_switch(self) -> None:
        source = Image.new("RGBA", (2, 1))
        source.putdata([(11, 22, 33, 0), (44, 55, 66, 128)])
        tensor, _ = self._load(source, preserve_alpha=True)

        fake_paths = SimpleNamespace(
            get_output_directory=lambda: str(self.root),
            get_save_image_path=lambda prefix, root, width, height: (root, prefix, 1, "", prefix),
        )
        with mock.patch.object(nodes, "folder_paths", fake_paths):
            saver = nodes.RookieUISaveImageWithMetadata()
            named = saver.save_images(tensor, parameters="synthetic prompt\nSteps: 2, Seed: 1, Size: 2x1")
            with mock.patch.object(nodes, "_metadata_disabled", return_value=True):
                no_meta = saver.save_images(tensor, filename_prefix="NoMeta", parameters="private synthetic text")

        named_path = self.root / named["ui"]["images"][0]["filename"]
        no_meta_path = self.root / no_meta["ui"]["images"][0]["filename"]
        with Image.open(named_path) as saved:
            self.assertEqual(saved.mode, "RGBA")
            self.assertEqual(saved.size, (2, 1))
            self.assertEqual(list(saved.getdata()), list(source.getdata()))
            self.assertIn("synthetic prompt", saved.info["parameters"])
        with Image.open(no_meta_path) as saved:
            self.assertEqual(saved.mode, "RGBA")
            self.assertNotIn("parameters", saved.info)

    def test_original_output_bytes_survive_png_info_and_edit_import(self) -> None:
        source = Image.new("RGBA", (2, 1))
        source.putdata([(1, 2, 3, 0), (4, 5, 6, 128)])
        buffer = io.BytesIO()
        source.save(buffer, format="PNG")
        output_path = self.root / "final.png"
        output_path.write_bytes(buffer.getvalue())
        data_url = asset_store.build_data_url_from_path(output_path)
        input_root = self.root / "input"
        output_root = self.root / "output"
        with (
            mock.patch.object(asset_store, "_INPUT_ROOT", input_root),
            mock.patch.object(asset_store, "_OUTPUT_ROOT", output_root),
            mock.patch.object(asset_store, "_RUNTIME_CLEANUP_INTERVAL_SECONDS", 999999),
        ):
            asset_store._reset_runtime_cleanup_state_for_tests()
            _, _, png_handle = pnginfo._extract_image_source({"image_data": data_url})
            edit_handle = img2img._resolve_input_asset(
                asset_value="", data_value=data_url, field_name="image_asset",
                data_field_name="image_data", upload_prefix="rgba_edit", required=True,
            )
            self.assertEqual(asset_store.resolve_asset_path(png_handle).read_bytes(), output_path.read_bytes())
            self.assertEqual(asset_store.resolve_asset_path(edit_handle).read_bytes(), output_path.read_bytes())
            with self.assertRaises(ValueError):
                asset_store.resolve_asset_path("../final.png")
            with self.assertRaises(ValueError):
                asset_store.decode_image_data("data:image/png;base64," + base64.b64encode(b"bad").decode())


if __name__ == "__main__":
    unittest.main()
