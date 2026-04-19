from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from unittest import mock

from rookieui.api import routes
from rookieui.contracts.models import ModelInventorySnapshot
from rookieui.services.img2img import normalize_img2img_request
from rookieui.services.workflow_translation import translate_img2img_request


class _FakeJsonRequest:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    async def json(self) -> dict[str, object]:
        return self._payload


class Img2ImgTranslationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._asset_path_patcher = mock.patch(
            "rookieui.services.img2img.resolve_asset_path",
            return_value=Path(__file__),
        )
        self._asset_path_patcher.start()

    def tearDown(self) -> None:
        self._asset_path_patcher.stop()

    def _build_qwen_edit_inventory(self) -> ModelInventorySnapshot:
        return ModelInventorySnapshot(
            source="host",
            checkpoints=["__host_default__"],
            diffusion_models=["Qwen\\qwen_image_edit_fp8_e4m3fn.safetensors"],
            vae=["qwen_image_vae.safetensors"],
            text_encoders=["qwen_2.5_vl_7b_fp8_scaled.safetensors"],
            loras=["Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors"],
            default_checkpoint="__host_default__",
            default_vae="qwen_image_vae.safetensors",
            default_text_encoder="qwen_2.5_vl_7b_fp8_scaled.safetensors",
        )

    def test_normalize_img2img_request_applies_sd15_defaults(self) -> None:
        request = normalize_img2img_request(
            {
                "prompt": "city skyline",
                "image_asset": "input-image",
            }
        )

        self.assertEqual(request.profile, "sd15")
        self.assertEqual(request.mode, "img2img")
        self.assertEqual(request.execution_mode, "img2img")
        self.assertEqual(request.batch_images, [])
        self.assertEqual(request.sampler_name, "euler_ancestral")
        self.assertEqual(request.denoise_strength, 0.75)
        self.assertEqual(request.seed, -1)
        self.assertGreaterEqual(request.execution_seed, 0)
        self.assertEqual(request.primary_model_category, "checkpoints")
        self.assertIn("scheduler_name", request.applied_defaults)
        self.assertEqual(request.dtype_profile, "automatic")
        self.assertEqual(request.lora_name, "")

    def test_normalize_img2img_request_applies_hires_defaults_when_enabled(self) -> None:
        request = normalize_img2img_request(
            {
                "prompt": "city skyline",
                "image_asset": "input-image",
                "steps": 28,
                "hires_enabled": True,
            }
        )

        self.assertTrue(request.hires_enabled)
        self.assertEqual(request.hires_scale, 1.5)
        self.assertEqual(request.hires_steps, 14)
        self.assertEqual(request.hires_denoise, 0.35)
        self.assertEqual(request.hires_upscale_method, "bislerp")

    def test_normalize_img2img_request_accepts_hires_denoise_upper_bound(self) -> None:
        request = normalize_img2img_request(
            {
                "prompt": "city skyline",
                "image_asset": "input-image",
                "hires_enabled": True,
                "hires_denoise": 1.0,
            }
        )

        self.assertEqual(request.hires_denoise, 1.0)

    def test_normalize_img2img_request_normalizes_adetailer_block(self) -> None:
        request = normalize_img2img_request(
            {
                "prompt": "city skyline",
                "image_asset": "input-image",
                "adetailer": {
                    "enabled": True,
                    "skip_img2img": True,
                    "units": [
                        {
                            "enabled": True,
                            "detector": "mediapipe_face_full",
                            "controlnet": {
                                "mode": "custom",
                                "module": "none",
                                "model": "",
                            },
                        }
                    ],
                },
            }
        )

        self.assertTrue(request.adetailer.enabled)
        self.assertTrue(request.adetailer.skip_img2img)
        self.assertEqual(request.adetailer.units[0].detector, "mediapipe_face_full")
        self.assertEqual(request.adetailer.units[0].controlnet.mode, "custom")

    def test_normalize_img2img_request_does_not_require_hires_values_when_disabled(self) -> None:
        request = normalize_img2img_request(
            {
                "prompt": "city skyline",
                "image_asset": "input-image",
                "hires_enabled": False,
                "hires_scale": "",
                "hires_steps": "",
                "hires_denoise": "",
                "hires_upscale_method": "",
            }
        )

        self.assertFalse(request.hires_enabled)
        self.assertEqual(request.hires_scale, 1.5)
        self.assertEqual(request.hires_steps, 14)
        self.assertEqual(request.hires_denoise, 0.35)
        self.assertEqual(request.hires_upscale_method, "bislerp")

    def test_normalize_img2img_request_accepts_supported_dtype_profile(self) -> None:
        request = normalize_img2img_request(
            {
                "prompt": "city skyline",
                "image_asset": "input-image",
                "dtype_profile": "float8-e4m3fn",
            }
        )

        self.assertEqual(request.dtype_profile, "float8_e4m3fn")

    def test_translate_img2img_request_builds_lora_loader_when_selected(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait cleanup",
                "image_asset": "portrait-input",
                "lora_name": "detail_tweaker.safetensors",
                "lora_strength_model": 0.8,
                "lora_strength_clip": 0.6,
            }
        )

        result = translate_img2img_request(normalized).to_payload()

        self.assertEqual(result["normalized_request"]["lora_name"], "detail_tweaker.safetensors")
        self.assertEqual(result["workflow"]["90"]["class_type"], "LoraLoader")
        self.assertEqual(result["workflow"]["90"]["inputs"]["strength_model"], 0.8)
        self.assertEqual(result["workflow"]["90"]["inputs"]["strength_clip"], 0.6)
        sampler_nodes = [node for node in result["workflow"].values() if node["class_type"] == "KSampler"]
        self.assertEqual(len(sampler_nodes), 1)
        self.assertEqual(sampler_nodes[0]["inputs"]["model"], ["90", 0])

    def test_normalize_img2img_request_requires_mask_for_inpaint(self) -> None:
        with self.assertRaisesRegex(ValueError, "mask_asset or mask_data is required"):
            normalize_img2img_request(
                {
                    "prompt": "portrait cleanup",
                    "image_asset": "portrait-input",
                    "mode": "inpaint",
                }
            )

    def test_normalize_img2img_request_maps_sketch_mode_to_img2img_execution(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait cleanup",
                "image_asset": "portrait-input",
                "mode": "sketch",
            }
        )

        self.assertEqual(normalized.mode, "sketch")
        self.assertEqual(normalized.execution_mode, "img2img")

    def test_normalize_img2img_request_maps_inpaint_upload_to_inpaint_execution(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait cleanup",
                "image_asset": "portrait-input",
                "mask_asset": "portrait-mask",
                "mode": "inpaint_upload",
            }
        )

        self.assertEqual(normalized.mode, "inpaint_upload")
        self.assertEqual(normalized.execution_mode, "inpaint")

    def test_normalize_img2img_request_rejects_non_sd_profile_not_exposed_for_img2img_surface(self) -> None:
        with self.assertRaisesRegex(ValueError, "not currently exposed on the img2img surface"):
            normalize_img2img_request(
                {
                    "prompt": "portrait cleanup",
                    "image_asset": "portrait-input",
                    "profile": "flux",
                }
            )

    def test_normalize_img2img_request_accepts_edit_mode_without_mask(self) -> None:
        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=self._build_qwen_edit_inventory()):
            normalized = normalize_img2img_request(
                {
                    "prompt": "refresh the storefront signage",
                    "negative_prompt": "blurry",
                    "image_asset": "portrait-input",
                    "profile": "qwen_image_edit",
                    "mode": "edit",
                }
            )

        self.assertEqual(normalized.mode, "edit")
        self.assertEqual(normalized.execution_mode, "edit")
        self.assertEqual(normalized.mask_asset, "")
        self.assertEqual(normalized.profile, "qwen_image_edit")
        self.assertEqual(
            normalized.template_lora_name,
            "Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors",
        )

    def test_normalize_img2img_request_accepts_template_lora_override_for_qwen_edit(self) -> None:
        inventory = ModelInventorySnapshot(
            source="host",
            checkpoints=["__host_default__"],
            diffusion_models=["Qwen\\qwen_image_edit_fp8_e4m3fn.safetensors"],
            vae=["qwen_image_vae.safetensors"],
            text_encoders=["qwen_2.5_vl_7b_fp8_scaled.safetensors"],
            loras=[
                "Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors",
                "Qwen-Image\\My-Custom-Qwen-Edit-LoRA.safetensors",
            ],
            default_checkpoint="__host_default__",
            default_vae="qwen_image_vae.safetensors",
            default_text_encoder="qwen_2.5_vl_7b_fp8_scaled.safetensors",
        )

        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=inventory):
            normalized = normalize_img2img_request(
                {
                    "prompt": "refresh the storefront signage",
                    "negative_prompt": "blurry",
                    "image_asset": "portrait-input",
                    "profile": "qwen_image_edit",
                    "mode": "edit",
                    "template_lora_name": "Qwen-Image/My-Custom-Qwen-Edit-LoRA.safetensors",
                }
            )

        self.assertEqual(
            normalized.template_lora_name,
            "Qwen-Image\\My-Custom-Qwen-Edit-LoRA.safetensors",
        )

    def test_normalize_img2img_request_rejects_edit_profile_on_legacy_img2img_surface(self) -> None:
        with self.assertRaisesRegex(ValueError, "not currently exposed on the img2img surface"):
            normalize_img2img_request(
                {
                    "prompt": "refresh the storefront signage",
                    "image_asset": "portrait-input",
                    "profile": "qwen_image_edit",
                    "mode": "img2img",
                }
            )

    def test_normalize_img2img_request_exposes_prompt_semantics_and_warning_codes(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait BREAK [soft:sharp:0.5]",
                "image_asset": "portrait-input",
            }
        )

        self.assertIn("PROMPT_BREAK_DETECTED", normalized.prompt_warning_codes)
        self.assertTrue(normalized.prompt_semantics["features"]["break_chunks"])
        self.assertTrue(normalized.prompt_semantics["features"]["prompt_scheduling"])
        self.assertEqual(len(normalized.prompt_semantics["branches"]), 1)

    def test_normalize_img2img_request_exposes_alternate_prompt_scheduling_semantics(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait [warm|cool] light",
                "image_asset": "portrait-input",
                "steps": 4,
            }
        )

        self.assertIn("PROMPT_ALTERNATE_DETECTED", normalized.prompt_warning_codes)
        self.assertTrue(normalized.prompt_semantics["features"]["alternate_prompt_scheduling"])
        self.assertEqual(len(normalized.prompt_semantics["branches"][0]["chunks"][0]["slices"]), 4)

    def test_normalize_img2img_request_canonicalizes_inventory_backed_embedding_tokens(self) -> None:
        fake_inventory = ModelInventorySnapshot(
            source="host",
            checkpoints=["SD15\\dreamshaper.safetensors"],
            vae=["Automatic"],
            text_encoders=["Automatic"],
            embeddings=["badhandv4.pt"],
            loras=[],
            default_checkpoint="SD15\\dreamshaper.safetensors",
            default_vae="Automatic",
            default_text_encoder="Automatic",
        )

        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=fake_inventory):
            normalized = normalize_img2img_request(
                {
                    "prompt": "portrait badhandv4 cleanup",
                    "image_asset": "portrait-input",
                }
            )

        self.assertEqual(normalized.prompt, "portrait embedding:badhandv4.pt cleanup")
        self.assertIn("PROMPT_EMBEDDING_DETECTED", normalized.prompt_warning_codes)
        self.assertTrue(normalized.prompt_semantics["features"]["embeddings_textual_inversion"])
        self.assertEqual(normalized.prompt_semantics["embeddings"][0]["canonical_token"], "embedding:badhandv4.pt")

    def test_normalize_img2img_request_accepts_human_readable_inpaint_aliases(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait cleanup",
                "image_asset": "portrait-input",
                "mask_asset": "portrait-mask",
                "mode": "inpaint",
                "resize_mode": "Just resize",
                "inpaint_mask_mode": "Inpaint not masked",
                "inpaint_masked_content": "Latent noise",
                "inpaint_area": "Whole picture",
            }
        )

        self.assertEqual(normalized.resize_mode, "just_resize")
        self.assertEqual(normalized.inpaint_mask_mode, "inpaint_not_masked")
        self.assertEqual(normalized.inpaint_masked_content, "latent_noise")
        self.assertEqual(normalized.inpaint_area, "whole_picture")

    def test_normalize_img2img_request_accepts_host_default_sentinels_on_live_inventory(self) -> None:
        fake_inventory = ModelInventorySnapshot(
            source="host",
            checkpoints=["SD15\\dreamshaper.safetensors"],
            vae=["SD15\\vae-ft-mse-840000.safetensors"],
            text_encoders=["clip_l.safetensors"],
            controlnet=[],
            default_checkpoint="SD15\\dreamshaper.safetensors",
            default_vae="SD15\\vae-ft-mse-840000.safetensors",
            default_text_encoder="clip_l.safetensors",
        )

        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=fake_inventory):
            normalized = normalize_img2img_request(
                {
                    "prompt": "portrait cleanup",
                    "image_asset": "portrait-input",
                    "profile": "sd15",
                    "checkpoint_name": "__host_default__",
                    "vae_name": "Automatic",
                    "text_encoder_name": "Automatic",
                }
            )

        self.assertEqual(normalized.checkpoint_name, "SD15\\dreamshaper.safetensors")
        self.assertEqual(normalized.vae_name, "SD15\\vae-ft-mse-840000.safetensors")
        self.assertEqual(normalized.text_encoder_name, "")

    def test_normalize_img2img_request_keeps_adetailer_same_checkpoint_sentinel_for_sdxl_host_inventory(self) -> None:
        fake_inventory = ModelInventorySnapshot(
            source="host",
            checkpoints=["SDXL\\realvisxl.safetensors"],
            diffusion_models=["flux\\flux1-dev.safetensors"],
            vae=["sdxl_vae.safetensors"],
            text_encoders=["clip_l.safetensors"],
            controlnet=[],
            default_checkpoint="SDXL\\realvisxl.safetensors",
            default_vae="sdxl_vae.safetensors",
            default_text_encoder="clip_l.safetensors",
        )

        with (
            mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=fake_inventory),
            mock.patch("rookieui.services.adetailer.discover_model_inventory", return_value=fake_inventory),
        ):
            normalized = normalize_img2img_request(
                {
                    "prompt": "portrait cleanup",
                    "image_asset": "portrait-input",
                    "profile": "sdxl",
                    "checkpoint_name": "SDXL\\realvisxl.safetensors",
                    "adetailer": {
                        "enabled": True,
                        "units": [
                            {
                                "enabled": True,
                                "detector": "face_yolov8n.pt",
                                "use_checkpoint": False,
                                "checkpoint_name": "__host_default__",
                            }
                        ],
                    },
                }
            )

        self.assertFalse(normalized.adetailer.units[0].use_checkpoint)
        self.assertEqual(normalized.adetailer.units[0].checkpoint_name, "Use same checkpoint")

    def test_normalize_img2img_request_uses_batch_image_as_source_fallback(self) -> None:
        with mock.patch(
            "rookieui.services.img2img.store_uploaded_image",
            return_value=mock.Mock(handle="rookieui_img2img_input_batch_stub"),
        ):
            normalized = normalize_img2img_request(
                {
                    "prompt": "portrait cleanup",
                    "mode": "batch",
                    "batch_images": [
                        "data:image/png;base64,ZmFrZQ==",
                    ],
                }
            )

        self.assertEqual(normalized.mode, "batch")
        self.assertEqual(normalized.execution_mode, "img2img")
        self.assertEqual(len(normalized.batch_images), 1)
        self.assertEqual(normalized.image_asset, "rookieui_img2img_input_batch_stub")

    def test_normalize_img2img_request_rejects_unbounded_seed(self) -> None:
        with self.assertRaisesRegex(ValueError, "seed must be -1 or between 0 and"):
            normalize_img2img_request(
                {
                    "prompt": "portrait cleanup",
                    "image_asset": "portrait-input",
                    "seed": 2**80,
                }
            )

    def test_normalize_img2img_request_reports_field_error_for_invalid_denoise(self) -> None:
        with self.assertRaisesRegex(ValueError, "denoise_strength must be a float"):
            normalize_img2img_request(
                {
                    "prompt": "portrait cleanup",
                    "image_asset": "portrait-input",
                    "denoise_strength": "oops",
                }
            )

    def test_normalize_img2img_request_clears_text_encoder_for_sd15(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait cleanup",
                "image_asset": "portrait-input",
                "profile": "sd15",
                "text_encoder_name": "Qwen2.5-VL.safetensors",
            }
        )

        self.assertEqual(normalized.text_encoder_name, "")

    def test_normalize_img2img_request_clears_text_encoder_for_sdxl(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait cleanup",
                "image_asset": "portrait-input",
                "profile": "sdxl",
                "text_encoder_name": "Automatic",
            }
        )

        self.assertEqual(normalized.text_encoder_name, "")

    def test_normalize_img2img_request_resolves_host_checkpoint_selector(self) -> None:
        with mock.patch(
            "rookieui.services.img2img.discover_model_inventory",
            return_value=mock.Mock(
                source="host",
                checkpoints=["SD15\\beautifulRealistic_v40.safetensors"],
                vae=["Automatic"],
                text_encoders=["Automatic"],
                loras=[],
                default_checkpoint="SD15\\beautifulRealistic_v40.safetensors",
                default_vae="Automatic",
                default_text_encoder="Automatic",
            ),
        ):
            request = normalize_img2img_request(
                {
                    "prompt": "portrait cleanup",
                    "image_asset": "portrait-input",
                    "checkpoint_name": "SD15/beautifulRealistic_v40.safetensors",
                }
            )

        self.assertEqual(request.checkpoint_name, "SD15\\beautifulRealistic_v40.safetensors")

    def test_translate_img2img_request_builds_sd15_inpaint_workflow(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait cleanup",
                "image_asset": "portrait-input",
                "mask_asset": "portrait-mask",
                "mode": "inpaint",
                "clip_skip": 2,
            }
        )

        result = translate_img2img_request(normalized).to_payload()

        self.assertEqual(result["workflow_kind"], "inpaint-sd15")
        self.assertEqual(result["workflow"]["2"]["class_type"], "CLIPSetLastLayer")
        class_types = {node["class_type"] for node in result["workflow"].values()}
        self.assertIn("RookieUILoadAssetMask", class_types)
        self.assertIn("RookieUIVAEEncodeForInpaint", class_types)

    def test_translate_img2img_request_keeps_sketch_workflow_kind_with_img2img_graph(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait cleanup",
                "image_asset": "portrait-input",
                "mode": "sketch",
            }
        )

        result = translate_img2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}
        self.assertEqual(result["workflow_kind"], "sketch-sd15")
        self.assertIn("VAEEncode", class_types)
        self.assertNotIn("RookieUILoadAssetMask", class_types)

    def test_translate_img2img_request_compiles_prompt_semantics_conditioning_chain(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait AND cinematic BREAK [soft:sharp:0.5]",
                "image_asset": "portrait-input",
            }
        )

        result = translate_img2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}
        self.assertIn("ConditioningCombine", class_types)
        self.assertIn("ConditioningSetTimestepRange", class_types)

    def test_translate_img2img_request_compiles_alternate_prompt_scheduling(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait [warm|cool] light",
                "image_asset": "portrait-input",
                "steps": 4,
            }
        )

        result = translate_img2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}

        self.assertIn("ConditioningCombine", class_types)
        self.assertIn("ConditioningSetTimestepRange", class_types)

    def test_translate_img2img_request_uses_legacy_roll_back_switch(self) -> None:
        with mock.patch.dict("os.environ", {"ROOKIEUI_PROMPT_DSL_LEGACY": "1"}, clear=False):
            normalized = normalize_img2img_request(
                {
                    "prompt": "portrait AND cinematic BREAK [soft:sharp:0.5]",
                    "image_asset": "portrait-input",
                }
            )
            result = translate_img2img_request(normalized).to_payload()

        class_types = {node["class_type"] for node in result["workflow"].values()}
        self.assertNotIn("ConditioningCombine", class_types)
        self.assertNotIn("ConditioningSetTimestepRange", class_types)
        self.assertIn("PROMPT_LEGACY_FALLBACK_ENABLED", result["normalized_request"]["prompt_warning_codes"])

    def test_translate_img2img_request_builds_sdxl_img2img_workflow(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "fashion editorial",
                "profile": "pony",
                "image_asset": "pony-input",
            }
        )

        result = translate_img2img_request(normalized).to_payload()

        self.assertEqual(result["workflow_kind"], "img2img-sdxl")
        self.assertEqual(result["workflow"]["2"]["class_type"], "RookieUIA1111CLIPTextEncodeSDXL")
        self.assertEqual(result["workflow"]["4"]["class_type"], "RookieUILoadAssetImage")
        sampler_nodes = [node for node in result["workflow"].values() if node["class_type"] == "KSampler"]
        self.assertEqual(len(sampler_nodes), 1)
        self.assertEqual(sampler_nodes[0]["inputs"]["denoise"], 0.75)
        self.assertEqual(sampler_nodes[0]["inputs"]["seed"], result["normalized_request"]["execution_seed"])

    def test_translate_img2img_request_builds_qwen_image_edit_workflow(self) -> None:
        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=self._build_qwen_edit_inventory()):
            normalized = normalize_img2img_request(
                {
                    "prompt": "refresh the storefront signage",
                    "negative_prompt": "blurry",
                    "image_asset": "portrait-input",
                    "profile": "qwen_image_edit",
                    "mode": "edit",
                }
            )

        result = translate_img2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}

        self.assertEqual(result["workflow_kind"], "edit-qwen_image_edit")
        self.assertIn("ImageScaleToTotalPixels", class_types)
        self.assertIn("TextEncodeQwenImageEdit", class_types)
        self.assertIn("LoraLoaderModelOnly", class_types)
        self.assertIn("ModelSamplingAuraFlow", class_types)
        self.assertNotIn("RookieUILoadAssetMask", class_types)
        self.assertEqual(
            len([node for node in result["workflow"].values() if node["class_type"] == "TextEncodeQwenImageEdit"]),
            2,
        )

    def test_translate_img2img_request_appends_inline_lora_after_template_owned_lora_for_qwen_edit(self) -> None:
        inventory = ModelInventorySnapshot(
            source="host",
            checkpoints=["__host_default__"],
            diffusion_models=["Qwen\\qwen_image_edit_fp8_e4m3fn.safetensors"],
            vae=["qwen_image_vae.safetensors"],
            text_encoders=["qwen_2.5_vl_7b_fp8_scaled.safetensors"],
            loras=[
                "Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors",
                "Qwen-Image\\RetailRefresh.safetensors",
            ],
            default_checkpoint="__host_default__",
            default_vae="qwen_image_vae.safetensors",
            default_text_encoder="qwen_2.5_vl_7b_fp8_scaled.safetensors",
        )

        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=inventory):
            normalized = normalize_img2img_request(
                {
                    "prompt": "refresh the storefront signage <lora:Qwen-Image/RetailRefresh.safetensors:0.6>",
                    "negative_prompt": "blurry",
                    "image_asset": "portrait-input",
                    "profile": "qwen_image_edit",
                    "mode": "edit",
                }
            )

        result = translate_img2img_request(normalized).to_payload()
        workflow = result["workflow"]
        lora_nodes = {
            node_id: node for node_id, node in workflow.items() if node["class_type"] == "LoraLoaderModelOnly"
        }

        self.assertEqual(len(lora_nodes), 2)
        template_node_id = next(
            node_id
            for node_id, node in lora_nodes.items()
            if node["inputs"]["lora_name"] == "Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors"
        )
        inline_node_id = next(
            node_id
            for node_id, node in lora_nodes.items()
            if node["inputs"]["lora_name"] == "Qwen-Image\\RetailRefresh.safetensors"
        )
        self.assertEqual(lora_nodes[template_node_id]["inputs"]["model"], ["8", 0])
        self.assertEqual(lora_nodes[inline_node_id]["inputs"]["model"], [template_node_id, 0])
        self.assertEqual(lora_nodes[inline_node_id]["inputs"]["strength_model"], 0.6)
        model_sampling_node = next(node for node in workflow.values() if node["class_type"] == "ModelSamplingAuraFlow")
        self.assertEqual(model_sampling_node["inputs"]["model"], [inline_node_id, 0])

    def test_translate_img2img_request_uses_rookieui_a1111_encode_for_sd15_attention_prompt(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait [soft light]",
                "image_asset": "portrait-input",
            }
        )

        result = translate_img2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}

        self.assertIn("RookieUIA1111CLIPTextEncode", class_types)

    def test_translate_img2img_request_passes_canonical_embedding_tokens_to_sd_family_encoder(self) -> None:
        fake_inventory = ModelInventorySnapshot(
            source="host",
            checkpoints=["SD15\\dreamshaper.safetensors"],
            vae=["Automatic"],
            text_encoders=["Automatic"],
            embeddings=["badhandv4.pt"],
            loras=[],
            default_checkpoint="SD15\\dreamshaper.safetensors",
            default_vae="Automatic",
            default_text_encoder="Automatic",
        )

        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=fake_inventory):
            normalized = normalize_img2img_request(
                {
                    "prompt": "portrait badhandv4 cleanup",
                    "image_asset": "portrait-input",
                }
            )

        result = translate_img2img_request(normalized).to_payload()
        encoder_nodes = [
            node
            for node in result["workflow"].values()
            if node["class_type"] == "RookieUIA1111CLIPTextEncode"
        ]

        self.assertTrue(encoder_nodes)
        self.assertTrue(any(node["inputs"]["text"] == "portrait embedding:badhandv4.pt cleanup" for node in encoder_nodes))

    def test_translate_img2img_request_applies_resize_mode_nodes(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "fashion editorial",
                "image_asset": "pony-input",
                "resize_mode": "crop_and_resize",
                "width": 768,
                "height": 960,
            }
        )

        result = translate_img2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}
        self.assertIn("ImageScale", class_types)

    def test_translate_img2img_request_applies_latent_upscale_resize_mode(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "fashion editorial",
                "image_asset": "pony-input",
                "resize_mode": "latent_upscale",
                "width": 768,
                "height": 960,
            }
        )

        result = translate_img2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}
        self.assertIn("LatentUpscale", class_types)

    def test_translate_img2img_request_applies_inpaint_mask_options(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait cleanup",
                "image_asset": "portrait-input",
                "mask_asset": "portrait-mask",
                "mode": "inpaint",
                "mask_blur": 12,
                "inpaint_mask_mode": "inpaint_not_masked",
                "inpaint_area": "only_masked",
                "inpaint_padding": 24,
                "grow_mask_by": 6,
            }
        )

        result = translate_img2img_request(normalized).to_payload()
        mask_nodes = [node for node in result["workflow"].values() if node["class_type"] == "RookieUILoadAssetMask"]
        self.assertEqual(len(mask_nodes), 1)
        self.assertEqual(mask_nodes[0]["inputs"]["invert"], True)
        self.assertEqual(mask_nodes[0]["inputs"]["blur_radius"], 12)
        encode_nodes = [node for node in result["workflow"].values() if node["class_type"] == "RookieUIVAEEncodeForInpaint"]
        self.assertEqual(len(encode_nodes), 1)
        self.assertEqual(encode_nodes[0]["inputs"]["grow_mask_by"], 24)

    def test_translate_img2img_request_applies_inpaint_masked_content_and_soft_inpainting(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait cleanup",
                "image_asset": "portrait-input",
                "mask_asset": "portrait-mask",
                "mode": "inpaint",
                "inpaint_masked_content": "latent_noise",
                "soft_inpainting_enabled": True,
                "soft_inpainting_schedule_bias": 1.6,
                "soft_inpainting_preservation_strength": 0.8,
                "soft_inpainting_transition_contrast_boost": 5.5,
                "soft_inpainting_mask_influence": 0.35,
                "soft_inpainting_difference_threshold": 0.7,
                "soft_inpainting_difference_contrast": 2.3,
            }
        )

        result = translate_img2img_request(normalized).to_payload()
        encode_nodes = [node for node in result["workflow"].values() if node["class_type"] == "RookieUIVAEEncodeForInpaint"]
        self.assertEqual(len(encode_nodes), 1)
        inputs = encode_nodes[0]["inputs"]
        self.assertEqual(inputs["masked_content"], "latent_noise")
        self.assertTrue(inputs["soft_inpainting_enabled"])
        self.assertEqual(inputs["soft_inpainting_schedule_bias"], 1.6)
        self.assertEqual(inputs["soft_inpainting_preservation_strength"], 0.8)
        self.assertEqual(inputs["soft_inpainting_transition_contrast_boost"], 5.5)
        self.assertEqual(inputs["soft_inpainting_mask_influence"], 0.35)
        self.assertEqual(inputs["soft_inpainting_difference_threshold"], 0.7)
        self.assertEqual(inputs["soft_inpainting_difference_contrast"], 2.3)

    def test_translate_img2img_request_builds_hires_second_pass(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "fashion editorial",
                "image_asset": "pony-input",
                "hires_enabled": True,
                "hires_scale": 1.8,
                "hires_steps": 12,
                "hires_denoise": 0.4,
            }
        )

        result = translate_img2img_request(normalized).to_payload()

        self.assertEqual(result["workflow_kind"], "img2img-sd15-hires")
        class_types = {node["class_type"] for node in result["workflow"].values()}
        self.assertIn("LatentUpscaleBy", class_types)
        self.assertEqual(result["normalized_request"]["hires_scale"], 1.8)
        self.assertEqual(result["normalized_request"]["hires_steps"], 12)

    def test_translate_img2img_request_respects_adetailer_skip_img2img(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait cleanup",
                "image_asset": "portrait-input",
                "adetailer": {
                    "enabled": True,
                    "skip_img2img": True,
                    "units": [{"enabled": True, "detector": "face_yolov8n.pt"}],
                },
            }
        )

        result = translate_img2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}

        self.assertNotIn("RookieUIADetailerDetectMask", class_types)
        self.assertEqual(
            len([node for node in result["workflow"].values() if node["class_type"] == "KSampler"]),
            1,
        )

    def test_translate_img2img_request_appends_adetailer_refinement_when_not_skipped(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait cleanup",
                "negative_prompt": "bad hands",
                "image_asset": "portrait-input",
                "adetailer": {
                    "enabled": True,
                    "skip_img2img": False,
                    "units": [
                        {
                            "enabled": True,
                            "detector": "hand_yolov8n.pt",
                            "prompt": "repair hands",
                            "denoising_strength": 0.35,
                            "inpaint_padding": 48,
                        }
                    ],
                },
            }
        )

        result = translate_img2img_request(normalized).to_payload()
        workflow = result["workflow"]
        mask_nodes = [node for node in workflow.values() if node["class_type"] == "RookieUIADetailerDetectMask"]
        inpaint_encode_nodes = [
            node for node in workflow.values() if node["class_type"] == "RookieUIVAEEncodeForInpaint"
        ]
        sampler_nodes = [node for node in workflow.values() if node["class_type"] == "KSampler"]
        save_node = [node for node in workflow.values() if node["class_type"] == "SaveImage"][0]
        decode_nodes = [(node_id, node) for node_id, node in workflow.items() if node["class_type"] == "VAEDecode"]

        self.assertEqual(len(mask_nodes), 1)
        self.assertEqual(mask_nodes[0]["inputs"]["detector"], "hand_yolov8n.pt")
        self.assertEqual(len(inpaint_encode_nodes), 1)
        self.assertEqual(inpaint_encode_nodes[0]["inputs"]["grow_mask_by"], 48)
        self.assertEqual(len(sampler_nodes), 2)
        self.assertEqual(sampler_nodes[-1]["inputs"]["denoise"], 0.35)
        self.assertEqual(save_node["inputs"]["images"], [decode_nodes[-1][0], 0])

    def test_img2img_route_returns_translation_payload(self) -> None:
        response = asyncio.run(
            routes.img2img(
                _FakeJsonRequest(
                    {
                        "prompt": "forest shrine variation",
                        "image_asset": "img-source",
                        "profile": "sd15",
                        "dry_run": True,
                    }
                )
            )
        )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["workflow_kind"], "img2img-sd15")
        self.assertIn("normalized_request", response["payload"])
        self.assertEqual(response["payload"]["normalized_request"]["dtype_profile"], "automatic")
        self.assertEqual(response["payload"]["submission"]["mode"], "dry-run")

    def test_img2img_route_rejects_invalid_asset_identifier(self) -> None:
        response = asyncio.run(
            routes.img2img(
                _FakeJsonRequest(
                    {
                        "prompt": "forest shrine variation",
                        "image_asset": "../unsafe-path",
                    }
                )
            )
        )

        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"]["status"], "invalid-request")

    def test_img2img_route_rejects_non_sd_profile_hidden_from_img2img_surface(self) -> None:
        response = asyncio.run(
            routes.img2img(
                _FakeJsonRequest(
                    {
                        "prompt": "forest shrine variation",
                        "image_asset": "img-source",
                        "profile": "flux",
                    }
                )
            )
        )

        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"]["status"], "invalid-request")
        self.assertIn("not currently exposed on the img2img surface", response["payload"]["detail"])

    def test_img2img_route_accepts_edit_mode_without_mask(self) -> None:
        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=self._build_qwen_edit_inventory()):
            response = asyncio.run(
                routes.img2img(
                    _FakeJsonRequest(
                        {
                            "prompt": "refresh the storefront signage",
                            "image_asset": "img-source",
                            "profile": "qwen_image_edit",
                            "mode": "edit",
                            "dry_run": True,
                        }
                    )
                )
            )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["workflow_kind"], "edit-qwen_image_edit")

    def test_img2img_route_rejects_unknown_asset_handle(self) -> None:
        with mock.patch(
            "rookieui.services.img2img.resolve_asset_path",
            side_effect=ValueError("Unknown RookieUI asset handle: input-image"),
        ):
            response = asyncio.run(
                routes.img2img(
                    _FakeJsonRequest(
                        {
                            "prompt": "forest shrine variation",
                            "image_asset": "input-image",
                        }
                    )
                )
            )

        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"]["status"], "invalid-request")
        self.assertIn("Unknown RookieUI asset handle", response["payload"]["detail"])

    def test_img2img_route_rejects_unsafe_checkpoint_selector(self) -> None:
        response = asyncio.run(
            routes.img2img(
                _FakeJsonRequest(
                    {
                        "prompt": "forest shrine variation",
                        "image_asset": "img-source",
                        "checkpoint_name": "../unsafe.ckpt",
                        "dry_run": True,
                    }
                )
            )
        )

        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"]["status"], "invalid-request")

    def test_img2img_route_returns_queued_submission_payload(self) -> None:
        with (
            mock.patch.object(
                routes,
                "_get_prompt_server_for_submission",
                return_value=object(),
            ),
            mock.patch.object(
                routes,
                "submit_prompt_workflow",
                new=mock.AsyncMock(
                    return_value={
                        "accepted": True,
                        "prompt_id": "prompt-456",
                        "number": 4,
                        "node_errors": {},
                    }
                ),
            ),
        ):
            response = asyncio.run(
                routes.img2img(
                    _FakeJsonRequest(
                        {
                            "prompt": "forest shrine variation",
                            "profile": "sd15",
                            "image_asset": "img-source",
                            "client_id": "browser-2",
                        }
                    )
                )
            )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["mode"], "queued")
        self.assertEqual(response["payload"]["submission"]["prompt_id"], "prompt-456")
