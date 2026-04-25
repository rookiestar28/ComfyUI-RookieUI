from __future__ import annotations

import asyncio
import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from rookieui.api import routes
from rookieui.services import asset_store


class _FakeJsonRequest:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    async def json(self) -> dict[str, object]:
        return self._payload


def _image_data_url(color: str = "white") -> str:
    image = Image.new("RGB", (32, 32), color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


class FrontendRoutePayloadMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.runtime_dir.cleanup)
        runtime_root = Path(self.runtime_dir.name)
        self.input_root = runtime_root / "input"
        self.output_root = runtime_root / "output"
        self.input_root.mkdir(parents=True, exist_ok=True)
        self.output_root.mkdir(parents=True, exist_ok=True)

        self.input_patcher = mock.patch.object(asset_store, "_INPUT_ROOT", self.input_root)
        self.output_patcher = mock.patch.object(asset_store, "_OUTPUT_ROOT", self.output_root)
        self.input_patcher.start()
        self.output_patcher.start()
        self.addCleanup(self.input_patcher.stop)
        self.addCleanup(self.output_patcher.stop)

        self.img2img_asset_patcher = mock.patch(
            "rookieui.services.img2img.resolve_asset_path",
            return_value=Path(__file__),
        )
        self.controlnet_asset_patcher = mock.patch(
            "rookieui.services.controlnet.resolve_asset_path",
            return_value=Path(__file__),
        )
        self.img2img_asset_patcher.start()
        self.controlnet_asset_patcher.start()
        self.addCleanup(self.img2img_asset_patcher.stop)
        self.addCleanup(self.controlnet_asset_patcher.stop)

    def test_route_handlers_accept_current_frontend_payload_shapes_without_traceback(self) -> None:
        cases = [
            (
                "txt2img",
                routes.txt2img,
                {
                    "prompt": "route matrix cat",
                    "negative_prompt": "low quality",
                    "profile": "sd15",
                    "dtype_profile": "Automatic",
                    "checkpoint_name": "__host_default__",
                    "vae_name": "Automatic",
                    "text_encoder_name": "Automatic",
                    "width": 512,
                    "height": 512,
                    "steps": 20,
                    "cfg_scale": 7.0,
                    "shift": None,
                    "flux_guidance": None,
                    "edit_megapixels": None,
                    "sampler_name": "Euler a",
                    "scheduler_name": "normal",
                    "prompt_enhancement_enabled": False,
                    "seed": -1,
                    "seed_extra": False,
                    "batch_size": 1,
                    "batch_count": 1,
                    "clip_skip": 1,
                    "hires_enabled": False,
                    "hires_scale": 1.5,
                    "hires_steps": None,
                    "hires_denoise": 0.35,
                    "hires_upscale_method": "bislerp",
                    "template_lora_name": "",
                    "lora_name": "",
                    "lora_strength_model": 1.0,
                    "lora_strength_clip": 1.0,
                    "adetailer": {"enabled": False, "units": []},
                    "controlnet_units": [],
                    "alwayson_scripts": {},
                    "dry_run": True,
                },
            ),
            (
                "img2img",
                routes.img2img,
                {
                    "prompt": "route matrix variation",
                    "negative_prompt": "low quality",
                    "profile": "sd15",
                    "dtype_profile": "Automatic",
                    "checkpoint_name": "__host_default__",
                    "vae_name": "Automatic",
                    "text_encoder_name": "Automatic",
                    "image_asset": "img-source",
                    "image_data": "",
                    "mask_asset": "",
                    "mask_data": "",
                    "reference_images": [],
                    "main_reference_index": 0,
                    "mode": "img2img",
                    "batch_images": [],
                    "width": 512,
                    "height": 512,
                    "resize_mode": "crop_and_resize",
                    "steps": 20,
                    "cfg_scale": 7.0,
                    "shift": None,
                    "flux_guidance": None,
                    "edit_megapixels": None,
                    "sampler_name": "Euler a",
                    "scheduler_name": "normal",
                    "prompt_enhancement_enabled": False,
                    "seed": -1,
                    "seed_extra": False,
                    "batch_size": 1,
                    "clip_skip": 1,
                    "denoise_strength": 0.75,
                    "grow_mask_by": 6,
                    "mask_blur": 4,
                    "inpaint_mask_mode": "inpaint_masked",
                    "inpaint_masked_content": "original",
                    "inpaint_area": "only_masked",
                    "inpaint_padding": 32,
                    "soft_inpainting_enabled": False,
                    "soft_inpainting_schedule_bias": 1.0,
                    "soft_inpainting_preservation_strength": 0.5,
                    "soft_inpainting_transition_contrast_boost": 4.0,
                    "soft_inpainting_mask_influence": 0.0,
                    "soft_inpainting_difference_threshold": 0.5,
                    "soft_inpainting_difference_contrast": 2.0,
                    "hires_enabled": False,
                    "hires_scale": 1.5,
                    "hires_steps": 10,
                    "hires_denoise": 0.35,
                    "hires_upscale_method": "bislerp",
                    "template_lora_name": "",
                    "lora_name": "",
                    "lora_strength_model": 1.0,
                    "lora_strength_clip": 1.0,
                    "adetailer": {"enabled": False, "units": []},
                    "controlnet_units": [],
                    "alwayson_scripts": {},
                    "dry_run": True,
                },
            ),
            (
                "extras",
                routes.extras_run,
                {
                    "mode": "single_image",
                    "image_data": _image_data_url("blue"),
                    "scale_mode": "scale_by",
                    "scale_by": 1.5,
                    "target_width": 1024,
                    "target_height": 1024,
                    "upscaler_1": "None",
                    "upscaler_2": "None",
                    "upscaler_2_visibility": 0.0,
                    "upscale_enabled": False,
                    "color_correction": False,
                    "face_restoration": "none",
                    "codeformer_weight": 0.5,
                },
            ),
            (
                "pnginfo",
                routes.pnginfo_inspect,
                {
                    "image_data": _image_data_url("green"),
                },
            ),
            (
                "controlnet_detect",
                routes.controlnet_detect,
                {
                    "controlnet_module": "none",
                    "controlnet_input_images": [_image_data_url("red")],
                    "controlnet_masks": [],
                    "pixel_perfect": True,
                    "resolution": 512,
                    "threshold_a": 64,
                    "threshold_b": 64,
                },
            ),
        ]

        for label, handler, payload in cases:
            with self.subTest(label=label):
                response = asyncio.run(handler(_FakeJsonRequest(payload)))

            self.assertIn(response["status"], {200, 400})
            self.assertIsInstance(response["payload"], dict)
            self.assertNotEqual(response["payload"].get("status"), "server-error")

    def test_generation_routes_return_json_invalid_request_for_unknown_frontend_fields(self) -> None:
        txt2img_response = asyncio.run(
            routes.txt2img(_FakeJsonRequest({"prompt": "cat", "unexpected_frontend_field": True, "dry_run": True}))
        )
        img2img_response = asyncio.run(
            routes.img2img(
                _FakeJsonRequest(
                    {
                        "prompt": "cat",
                        "image_asset": "img-source",
                        "unexpected_frontend_field": True,
                        "dry_run": True,
                    }
                )
            )
        )

        self.assertEqual(txt2img_response["status"], 400)
        self.assertEqual(txt2img_response["payload"]["status"], "invalid-request")
        self.assertEqual(img2img_response["status"], 400)
        self.assertEqual(img2img_response["payload"]["status"], "invalid-request")
