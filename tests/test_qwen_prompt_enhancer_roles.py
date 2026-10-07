from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from rookieui.contracts.models import ModelInventorySnapshot
from rookieui.contracts.qwen_image_21_assets import qwen_image_21_asset_role
from rookieui.services.img2img import normalize_img2img_request
from rookieui.services.model_inventory import resolve_aux_text_encoder_selector_context, resolve_text_encoder_selector_context
from rookieui.services.txt2img import _resolve_diffusion_text_encoder_selector, normalize_txt2img_request

ENHANCERS = (
    "qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors",
    "qwen3.5_9b_qwen_image_2.1_pe_i2i.int8_convrot.safetensors",
)


class QwenPromptEnhancerRoleTests(unittest.TestCase):
    def test_dedicated_enhancers_have_a_role_separate_from_generation_encoders(self) -> None:
        for basename in ENHANCERS:
            for selector in (basename, "nested/" + basename, "NESTED\\" + basename.upper()):
                with self.subTest(selector=selector):
                    self.assertEqual(qwen_image_21_asset_role(selector), "prompt_enhancers")
        self.assertEqual(qwen_image_21_asset_role("qwen3_4b.safetensors"), "")
        self.assertEqual(qwen_image_21_asset_role("qwen3.5_9b_generic.safetensors"), "")

    def test_pe_only_inventory_never_supplies_main_or_aux_generation_defaults(self) -> None:
        for enhancer in ENHANCERS:
            for profile in ("qwen_image", "qwen_image_edit", "qwen_image_edit_2509", "qwen_image_21",
                            "qwen_image_21_edit", "z_image", "z_image_turbo", "ernie_image", "sd15"):
                with self.subTest(enhancer=enhancer, profile=profile):
                    inventory = ModelInventorySnapshot(source="host", text_encoders=[enhancer], default_text_encoder=enhancer)
                    self.assertEqual(resolve_text_encoder_selector_context(profile, inventory), "")
                    self.assertEqual(resolve_aux_text_encoder_selector_context(profile, inventory), "")

    def test_pe_first_inventory_keeps_valid_family_encoders_and_fallbacks(self) -> None:
        for enhancer in ENHANCERS:
            for profile, legitimate in (
                ("qwen_image", "qwen_2.5_vl_7b_fp8_scaled.safetensors"),
                ("qwen_image_edit", "qwen_2.5_vl_7b_fp8_scaled.safetensors"),
                ("qwen_image_21", "qwen3vl_8b_int8_convrot.safetensors"),
                ("z_image", "qwen3_4b.safetensors"), ("sd15", "generic_clip.safetensors"),
            ):
                with self.subTest(enhancer=enhancer, profile=profile):
                    inventory = ModelInventorySnapshot(source="host", text_encoders=[enhancer, legitimate], default_text_encoder=enhancer)
                    self.assertEqual(resolve_text_encoder_selector_context(profile, inventory), legitimate)

    def test_stale_global_pe_default_cannot_bypass_an_empty_selector_list(self) -> None:
        for enhancer in ENHANCERS:
            inventory = ModelInventorySnapshot(source="host", default_text_encoder=enhancer)
            self.assertEqual(resolve_text_encoder_selector_context("qwen_image", inventory), "")
            self.assertEqual(resolve_text_encoder_selector_context("sd15", inventory), "")

    def test_explicit_enhancer_is_rejected_by_txt2img_diffusion_admission(self) -> None:
        for enhancer in ENHANCERS:
            inventory = ModelInventorySnapshot(source="host", diffusion_models=["qwen_image_2512_fp8_e4m3fn.safetensors"],
                                               text_encoders=[enhancer, "qwen_2.5_vl_7b_fp8_scaled.safetensors"], vae=["qwen_image_vae.safetensors"])
            with self.subTest(enhancer=enhancer), mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=inventory):
                with self.assertRaisesRegex(ValueError, "2.1"):
                    normalize_txt2img_request({"profile": "qwen_image", "prompt": "synthetic", "text_encoder_name": enhancer})

    def test_explicit_enhancer_is_rejected_by_img2img_diffusion_admission(self) -> None:
        for enhancer in ENHANCERS:
            inventory = ModelInventorySnapshot(source="host", diffusion_models=["qwen_image_edit_fp8_e4m3fn.safetensors"],
                                               text_encoders=[enhancer, "qwen_2.5_vl_7b_fp8_scaled.safetensors"], vae=["qwen_image_vae.safetensors"])
            with self.subTest(enhancer=enhancer), mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=inventory), \
                    mock.patch("rookieui.services.img2img.resolve_asset_path", return_value=Path("synthetic.png")):
                with self.assertRaisesRegex(ValueError, "2.1"):
                    normalize_img2img_request({"profile": "qwen_image_edit", "prompt": "synthetic", "image_asset": "synthetic.png",
                                              "text_encoder_name": enhancer})

    def test_composite_encoder_boundary_rejects_enhancers_in_every_slot(self) -> None:
        for enhancer in ENHANCERS:
            for bundle in (f"ordinary.safetensors|{enhancer}", f"{enhancer}|ordinary.safetensors"):
                for raw, default in ((bundle, ""), ("", bundle)):
                    with self.subTest(bundle=bundle, from_default=not raw), self.assertRaisesRegex(ValueError, "prompt enhancer"):
                        _resolve_diffusion_text_encoder_selector(raw, inventory_selectors=[], default_value=default, strict_match=False)

    def test_composite_encoder_boundary_preserves_valid_ordered_bundles(self) -> None:
        bundle = "clip_l.safetensors|t5xxl_fp16.safetensors"
        self.assertEqual(_resolve_diffusion_text_encoder_selector(
            bundle, inventory_selectors=bundle.split("|"), default_value="", strict_match=True), bundle)


if __name__ == "__main__":
    unittest.main()
