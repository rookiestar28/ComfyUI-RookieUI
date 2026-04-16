from __future__ import annotations

import asyncio
import base64
import io
import unittest

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from rookieui.api import routes
from rookieui.contracts.pnginfo import PNGINFO_CONTRACT_VERSION
from rookieui.security.request_guard import MAX_INFOTEXT_LENGTH
from rookieui.services.pnginfo import parse_pnginfo_payload


class _FakeJsonRequest:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    async def json(self) -> dict[str, object]:
        return self._payload


class PNGInfoParsingTests(unittest.TestCase):
    def _build_image_data_url(self, metadata: dict[str, str]) -> str:
        image = Image.new("RGB", (64, 64), color="white")
        pnginfo = PngInfo()
        for key, value in metadata.items():
            pnginfo.add_text(key, value)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", pnginfo=pnginfo)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def _build_a1111_parameters_image_data(self, parameters: str) -> str:
        return self._build_image_data_url({"parameters": parameters})

    def test_parse_pnginfo_payload_maps_txt2img_fields(self) -> None:
        result = parse_pnginfo_payload(
            {
                "image_data": self._build_a1111_parameters_image_data(
                    (
                    "masterpiece, city skyline\n"
                    "Negative prompt: blurry\n"
                    "Steps: 24, Sampler: Euler a, CFG scale: 6.5, Seed: 1234, Size: 768x768, "
                    "Model: dreamshaperXL.safetensors, Clip skip: 2"
                    )
                ),
            }
        ).to_payload()

        self.assertEqual(result["target_form"], "txt2img")
        self.assertEqual(result["source_type"], "a1111")
        self.assertEqual(result["payload"]["profile"], "sdxl")
        self.assertEqual(result["payload"]["sampler_name"], "euler_ancestral")
        self.assertEqual(result["payload"]["width"], 768)
        self.assertEqual(result["payload"]["clip_skip"], 2)

    def test_parse_pnginfo_payload_maps_inpaint_markers(self) -> None:
        result = parse_pnginfo_payload(
            {
                "image_data": self._build_a1111_parameters_image_data(
                    (
                        "portrait cleanup\n"
                        "Negative prompt: bad hands\n"
                        "Steps: 30, Sampler: DPM++ 2M Karras, CFG scale: 7, Seed: 42, "
                        "Denoising strength: 0.42, Mask mode: Inpaint masked, Masked content: original, "
                        "Inpaint area: Whole picture, Masked area padding: 16, Model: ponyDiffusion.safetensors"
                    )
                ),
            }
        ).to_payload()

        self.assertEqual(result["source"], "image.parameters")
        self.assertEqual(result["target_form"], "inpaint")
        self.assertEqual(result["payload"]["mode"], "inpaint")
        self.assertEqual(result["payload"]["profile"], "pony")
        self.assertEqual(result["payload"]["scheduler_name"], "karras")
        self.assertNotIn("image_asset", result["missing_inputs"])
        self.assertIn("mask_asset", result["missing_inputs"])

    def test_parse_pnginfo_payload_accepts_underscore_inpaint_aliases(self) -> None:
        result = parse_pnginfo_payload(
            {
                "image_data": self._build_a1111_parameters_image_data(
                    (
                        "portrait cleanup\n"
                        "Negative prompt: bad hands\n"
                        "Steps: 30, Sampler: DPM++ 2M Karras, CFG scale: 7, Seed: 42, "
                        "Denoising strength: 0.42, Resize mode: just_resize, Mask mode: inpaint_not_masked, "
                        "Masked content: latent_noise, Inpaint area: only_masked, Masked area padding: 16, "
                        "Model: ponyDiffusion.safetensors"
                    )
                ),
            }
        ).to_payload()

        self.assertEqual(result["payload"]["resize_mode"], "just_resize")
        self.assertEqual(result["payload"]["inpaint_mask_mode"], "inpaint_not_masked")
        self.assertEqual(result["payload"]["inpaint_masked_content"], "latent_noise")
        self.assertEqual(result["payload"]["inpaint_area"], "only_masked")

    def test_parse_pnginfo_payload_reads_a1111_image_metadata(self) -> None:
        image_data = self._build_image_data_url(
            {
                "parameters": (
                    "harbor dusk\n"
                    "Negative prompt: blurry\n"
                    "Steps: 28, Sampler: Euler a, CFG scale: 7, Seed: 9, Size: 512x512"
                )
            }
        )

        result = parse_pnginfo_payload({"image_data": image_data}).to_payload()

        self.assertEqual(result["source"], "image.parameters")
        self.assertEqual(result["source_type"], "a1111")
        self.assertEqual(result["target_form"], "txt2img")
        self.assertEqual(result["apply_targets"], ["txt2img", "img2img"])
        self.assertTrue(result["asset_handle"].startswith("pnginfo_"))
        self.assertEqual(result["metadata_items"]["parameters"].splitlines()[0], "harbor dusk")
        self.assertEqual(result["metadata_items"]["Prompt"], "harbor dusk")
        self.assertEqual(result["metadata_items"]["Negative prompt"], "blurry")

    def test_parse_pnginfo_payload_reads_comfy_metadata_as_inspect_only(self) -> None:
        image_data = self._build_image_data_url(
            {
                "prompt": "{\"1\": {\"class_type\": \"KSampler\"}}",
                "workflow": "{\"nodes\": []}",
            }
        )

        result = parse_pnginfo_payload({"image_data": image_data}).to_payload()

        self.assertEqual(result["source_type"], "comfyui")
        self.assertEqual(result["target_form"], "inspect_only")
        self.assertEqual(result["apply_targets"], [])
        self.assertIn("prompt", result["metadata_items"])
        self.assertIn("inspection only", result["warnings"][0].lower())

    def test_parse_pnginfo_payload_reports_unsupported_fields(self) -> None:
        result = parse_pnginfo_payload(
            {
                "image_data": self._build_a1111_parameters_image_data(
                    (
                    "cat portrait\n"
                    "Negative prompt: blurry\n"
                    "Steps: 20, Sampler: Euler a, CFG scale: 7, Seed: 5, Size: 512x512, "
                    "Version: 1.10.0, ENSD: 31337"
                    )
                ),
            }
        ).to_payload()

        self.assertIn("Version", result["unsupported_fields"])
        self.assertIn("ENSD", result["unsupported_fields"])

    def test_pnginfo_route_returns_round_trip_payload(self) -> None:
        response = asyncio.run(
            routes.pnginfo_parse(
                _FakeJsonRequest(
                    {
                        "image_data": self._build_a1111_parameters_image_data(
                            (
                            "masterpiece, harbor\n"
                            "Negative prompt: blurry\n"
                            "Steps: 28, Sampler: Euler a, CFG scale: 7, Seed: 9, Size: 512x512"
                            )
                        )
                    }
                )
            )
        )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["status"], "ok")
        self.assertEqual(response["payload"]["contract"]["version"], PNGINFO_CONTRACT_VERSION)
        self.assertEqual(response["payload"]["target_form"], "txt2img")

    def test_pnginfo_inspect_route_returns_round_trip_payload(self) -> None:
        response = asyncio.run(
            routes.pnginfo_inspect(
                _FakeJsonRequest(
                    {
                        "image_data": self._build_a1111_parameters_image_data(
                            (
                            "masterpiece, harbor\n"
                            "Negative prompt: blurry\n"
                            "Steps: 28, Sampler: Euler a, CFG scale: 7, Seed: 9, Size: 512x512"
                            )
                        )
                    }
                )
            )
        )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["status"], "ok")
        self.assertEqual(response["payload"]["contract"]["version"], PNGINFO_CONTRACT_VERSION)
        self.assertEqual(response["payload"]["source_type"], "a1111")

    def test_pnginfo_route_rejects_missing_image_data(self) -> None:
        response = asyncio.run(routes.pnginfo_parse(_FakeJsonRequest({"metadata": {}})))

        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"]["status"], "invalid-request")

    def test_pnginfo_route_rejects_text_only_payload(self) -> None:
        response = asyncio.run(
            routes.pnginfo_parse(
                _FakeJsonRequest({"infotext": "x" * (MAX_INFOTEXT_LENGTH + 1)})
            )
        )

        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"]["status"], "invalid-request")
