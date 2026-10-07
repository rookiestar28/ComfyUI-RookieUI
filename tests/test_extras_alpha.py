from __future__ import annotations

import base64
import hashlib
import io
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image, PngImagePlugin

from rookieui.services import asset_store
from rookieui.services.extras import _ComfyUpscalerBackend, execute_extras_request, normalize_extras_request


class _RgbUpscaler:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.modes: list[str] = []

    def upscale(self, image: Image.Image, model_name: str, target_size: tuple[int, int]) -> Image.Image:
        self.modes.append(image.mode)
        if self.fail:
            raise RuntimeError("synthetic backend failure")
        return Image.new("RGB", target_size, "red" if model_name == "first.pth" else "blue")


class _RgbRestorer:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def restore(self, image: Image.Image, _method: str, _weight: float) -> tuple[Image.Image, int]:
        if self.fail:
            raise RuntimeError("synthetic restoration failure")
        if image.mode != "RGB":
            raise ValueError("Restorer requires RGB.")
        return Image.new("RGB", image.size, "green"), 1


class _RgbaUpscaler(_RgbUpscaler):
    def upscale(self, image: Image.Image, model_name: str, target_size: tuple[int, int]) -> Image.Image:
        result = super().upscale(image, model_name, target_size)
        result.putalpha(191)
        return result


class _ArrayTensor:
    def __init__(self, array: np.ndarray) -> None:
        self.array = array

    def __getitem__(self, key):
        return _ArrayTensor(self.array[key])

    def detach(self):
        return self

    def float(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.array


class ExtrasAlphaTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[1] / ".tmp"
        root.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(self.directory.cleanup)
        self.input_root = Path(self.directory.name) / "input"
        self.output_root = Path(self.directory.name) / "output"
        self.input_root.mkdir()
        self.output_root.mkdir()
        for name, value in (("_INPUT_ROOT", self.input_root), ("_OUTPUT_ROOT", self.output_root)):
            patcher = mock.patch.object(asset_store, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _rgba(self) -> Image.Image:
        image = Image.new("RGBA", (64, 48), (80, 120, 160, 255))
        alpha = Image.fromarray(np.tile(np.array([0, 64, 128, 255], dtype=np.uint8), (48, 16)))
        image.putalpha(alpha)
        return image

    def _source(self, image: Image.Image, name: str = "synthetic.png", *, orientation: int | None = None) -> str:
        info = PngImagePlugin.PngInfo()
        info.add_text("parameters", "synthetic metadata")
        options = {"pnginfo": info}
        if orientation is not None:
            exif = Image.Exif()
            exif[274] = orientation
            options["exif"] = exif
        image.save(self.input_root / name, **options)
        return name

    def _execute(self, handle: str, **options):
        upscaler = options.pop("backend", None)
        restorer = options.pop("restorer", None)
        request = normalize_extras_request({"image_asset": handle, "upscale_enabled": False, **options})
        result = execute_extras_request(request, upscaler_backend=upscaler, face_restoration_backend=restorer)
        with Image.open(asset_store.resolve_asset_path(result.output_assets[0])) as image:
            output = image.copy()
        return output, result

    def test_saved_png_keeps_source_alpha_without_resize(self) -> None:
        source = self._rgba()
        handle = self._source(source)
        before = hashlib.sha256((self.input_root / handle).read_bytes()).hexdigest()
        output, result = self._execute(handle)
        self.assertEqual(output.mode, "RGBA")
        self.assertEqual(output.tobytes(), source.tobytes())
        self.assertEqual(output.info["parameters"], "synthetic metadata")
        self.assertEqual(hashlib.sha256((self.input_root / handle).read_bytes()).hexdigest(), before)
        preview_bytes = base64.b64decode(result.preview_data_url.split(",", 1)[1])
        with Image.open(io.BytesIO(preview_bytes)) as preview:
            self.assertEqual(preview.mode, "RGBA")
            self.assertEqual(preview.tobytes(), output.tobytes())

    def test_la_palette_and_color_key_transparency_are_preserved(self) -> None:
        rgba = self._rgba()
        palette = Image.new("P", rgba.size)
        palette.putpalette([255, 0, 0, 0, 0, 255] + [0] * 762)
        palette.putdata([x % 2 for _y in range(48) for x in range(64)])
        palette.info["transparency"] = 0
        rgb = Image.new("RGB", rgba.size, "red")
        rgb.putpixel((1, 1), (0, 0, 255))
        rgb.info["transparency"] = (255, 0, 0)
        for index, source in enumerate((rgba.convert("LA"), palette, rgb)):
            with self.subTest(mode=source.mode):
                output, _ = self._execute(self._source(source, f"mode-{index}.png"))
                self.assertEqual(output.mode, "RGBA")
                self.assertEqual(output.getchannel("A").tobytes(), source.convert("RGBA").getchannel("A").tobytes())

    def test_exif_transpose_rotates_alpha_together_with_color(self) -> None:
        source = self._rgba()
        handle = self._source(source, orientation=6)
        output, _ = self._execute(handle)
        expected = source.transpose(Image.Transpose.ROTATE_270)
        self.assertEqual(output.mode, "RGBA")
        self.assertEqual(output.size, (48, 64))
        self.assertEqual(output.tobytes(), expected.tobytes())

    def test_resize_model_blend_restoration_correction_and_fallback_keep_alpha(self) -> None:
        source = self._rgba()
        handle = self._source(source)
        expected = source.getchannel("A").resize((128, 96), Image.Resampling.BILINEAR)
        cases = (
            {}, {"upscaler_1": "first.pth", "backend": _RgbUpscaler()},
            {"upscaler_1": "first.pth", "upscaler_2": "second.pth", "upscaler_2_visibility": 0.25, "backend": _RgbUpscaler()},
            {"upscaler_1": "first.pth", "backend": _RgbUpscaler(fail=True)},
            {"upscaler_1": "first.pth", "backend": _RgbaUpscaler()},
            {"upscaler_1": "first.pth"},
            {"face_restoration": "gfpgan", "restorer": _RgbRestorer(), "color_correction": True},
            {"face_restoration": "gfpgan", "color_correction": True},
            {"face_restoration": "gfpgan", "restorer": _RgbRestorer(fail=True)},
        )
        for options in cases:
            with self.subTest(options=list(options)):
                output, result = self._execute(handle, upscale_enabled=True, scale_mode="scale_to",
                                               target_width=128, target_height=96, **options)
                self.assertEqual(output.mode, "RGBA")
                self.assertEqual(output.size, (128, 96))
                self.assertEqual(output.getchannel("A").tobytes(), expected.tobytes())
                if options.get("backend"):
                    self.assertEqual(set(options["backend"].modes), {"RGB"})
                if options.get("backend") and options["backend"].fail:
                    self.assertTrue(any("fallback" in warning for warning in result.warnings))
                if options.get("upscaler_2"):
                    self.assertEqual(output.getpixel((0, 0))[:3], (191, 0, 63))

    def test_batch_keeps_alpha_per_image_and_leaves_opaque_rgb_as_rgb(self) -> None:
        rgba = self._source(self._rgba(), "alpha.png")
        rgb = self._source(Image.new("RGB", (64, 48), "white"), "opaque.png")
        request = normalize_extras_request({"mode": "batch_process", "batch_assets": [rgba, rgb], "upscale_enabled": False})
        result = execute_extras_request(request)
        modes = []
        for handle in result.output_assets:
            with Image.open(asset_store.resolve_asset_path(handle)) as image:
                modes.append(image.mode)
        self.assertEqual(modes, ["RGBA", "RGB"])

    def test_model_tensor_adapter_accepts_rgb_rgba_and_rejects_invalid_data(self) -> None:
        backend = _ComfyUpscalerBackend()
        for channels in (3, 4):
            array = np.full((1, 48, 64, channels), 0.5, dtype=np.float32)
            node = types.SimpleNamespace(upscale=lambda _model, _tensor: types.SimpleNamespace(result=(_ArrayTensor(array),)))
            module = types.SimpleNamespace(ImageUpscaleWithModel=lambda: node)
            with self.subTest(channels=channels), mock.patch.dict("sys.modules", {"torch": types.SimpleNamespace(from_numpy=_ArrayTensor),
                                "comfy_extras.nodes_upscale_model": module}), mock.patch.object(backend, "_load_model", return_value=object()):
                output = backend.upscale(self._rgba(), "synthetic.pth", (64, 48))
                self.assertEqual(output.mode, "RGB" if channels == 3 else "RGBA")
                self.assertEqual(output.getpixel((0, 0)), (127,) * channels)
        for array in (np.zeros((1, 48, 64, 2)), np.zeros((2, 48, 64, 3)), np.zeros((48, 64, 3)),
                      np.zeros((0, 48, 64, 3)), np.zeros((1, 0, 64, 3)), np.zeros((1, 48, 0, 3)),
                      np.full((1, 48, 64, 3), np.nan), np.full((1, 48, 64, 3), np.inf)):
            node = types.SimpleNamespace(upscale=lambda _model, _tensor: (_ArrayTensor(array),))
            module = types.SimpleNamespace(ImageUpscaleWithModel=lambda: node)
            with self.subTest(shape=array.shape), mock.patch.dict("sys.modules", {"torch": types.SimpleNamespace(from_numpy=_ArrayTensor),
                                "comfy_extras.nodes_upscale_model": module}), mock.patch.object(backend, "_load_model", return_value=object()):
                with self.assertRaisesRegex(ValueError, "upscaler output"):
                    backend.upscale(self._rgba(), "synthetic.pth", (64, 48))


if __name__ == "__main__":
    unittest.main()
