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

    def _build_qwen_2511_edit_inventory(self) -> ModelInventorySnapshot:
        return ModelInventorySnapshot(
            source="host",
            checkpoints=["__host_default__"],
            diffusion_models=[
                "Qwen\\qwen_image_edit_fp8_e4m3fn.safetensors",
                "Qwen\\qwen_image_edit_2511_bf16.safetensors",
            ],
            vae=["qwen_image_vae.safetensors"],
            text_encoders=["qwen_2.5_vl_7b_fp8_scaled.safetensors"],
            loras=["Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors"],
            default_checkpoint="__host_default__",
            default_vae="qwen_image_vae.safetensors",
            default_text_encoder="qwen_2.5_vl_7b_fp8_scaled.safetensors",
        )

    def _build_qwen_plus_inventory(self) -> ModelInventorySnapshot:
        return ModelInventorySnapshot(
            source="host",
            checkpoints=["__host_default__"],
            diffusion_models=[
                "Qwen\\qwen_image_edit_fp8_e4m3fn.safetensors",
                "Qwen\\FireRed-Image-Edit-1.1-transformer.safetensors",
            ],
            vae=["qwen_image_vae.safetensors"],
            text_encoders=["qwen_2.5_vl_7b_fp8_scaled.safetensors"],
            loras=[
                "Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors",
                "Qwen\\FireRed-Image-Edit-1.0-Lightning-8steps-v1.0.safetensors",
            ],
            default_checkpoint="__host_default__",
            default_vae="qwen_image_vae.safetensors",
            default_text_encoder="qwen_2.5_vl_7b_fp8_scaled.safetensors",
        )

    def _build_flux_kontext_edit_inventory(self) -> ModelInventorySnapshot:
        return ModelInventorySnapshot(
            source="host",
            checkpoints=["__host_default__"],
            diffusion_models=["Flux\\flux1-dev-kontext_fp8_scaled.safetensors"],
            vae=["ae.safetensors"],
            text_encoders=["clip_l.safetensors", "t5xxl_fp8_e4m3fn_scaled.safetensors"],
            loras=[],
            default_checkpoint="__host_default__",
            default_vae="ae.safetensors",
            default_text_encoder="clip_l.safetensors",
        )

    def _build_flux2_edit_inventory(self) -> ModelInventorySnapshot:
        return ModelInventorySnapshot(
            source="host",
            checkpoints=["__host_default__"],
            diffusion_models=["Flux\\flux2_dev_fp8mixed.safetensors"],
            vae=["full_encoder_small_decoder.safetensors"],
            text_encoders=["mistral_3_small_flux2_bf16.safetensors"],
            loras=["Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors"],
            default_checkpoint="__host_default__",
            default_vae="full_encoder_small_decoder.safetensors",
            default_text_encoder="mistral_3_small_flux2_bf16.safetensors",
        )

    def _build_klein_kv_edit_inventory(self) -> ModelInventorySnapshot:
        return ModelInventorySnapshot(
            source="host",
            checkpoints=["__host_default__"],
            diffusion_models=["Klein\\flux-2-klein-9b-kv-fp8.safetensors"],
            vae=["flux2-vae.safetensors"],
            text_encoders=["qwen_3_8b_fp8mixed.safetensors"],
            loras=[],
            default_checkpoint="__host_default__",
            default_vae="flux2-vae.safetensors",
            default_text_encoder="qwen_3_8b_fp8mixed.safetensors",
        )

    def _build_longcat_edit_inventory(self) -> ModelInventorySnapshot:
        return ModelInventorySnapshot(
            source="host",
            checkpoints=["__host_default__"],
            diffusion_models=["Longcat\\longcat_image_edit_bf16.safetensors"],
            vae=["ae.safetensors"],
            text_encoders=["qwen_2.5_vl_7b_fp8_scaled.safetensors"],
            loras=[],
            default_checkpoint="__host_default__",
            default_vae="ae.safetensors",
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

    def test_normalize_img2img_request_treats_hires_steps_zero_as_same_as_base_steps(self) -> None:
        request = normalize_img2img_request(
            {
                "prompt": "city skyline",
                "image_asset": "input-image",
                "steps": 24,
                "hires_enabled": True,
                "hires_steps": 0,
            }
        )

        self.assertEqual(request.hires_steps, 24)

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

    def test_translate_img2img_request_chains_inline_and_selected_loras(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait cleanup <lora:detail_tweaker.safetensors:0.8> <lora:cinematic_helper.safetensors:0.5>",
                "image_asset": "portrait-input",
                "lora_name": "hero_boost.safetensors",
                "lora_strength_model": 0.7,
                "lora_strength_clip": 0.6,
            }
        )

        result = translate_img2img_request(normalized).to_payload()

        self.assertEqual(result["workflow"]["90"]["class_type"], "LoraLoader")
        self.assertEqual(result["workflow"]["90"]["inputs"]["lora_name"], "detail_tweaker.safetensors")
        self.assertEqual(result["workflow"]["91"]["inputs"]["lora_name"], "cinematic_helper.safetensors")
        self.assertEqual(result["workflow"]["92"]["inputs"]["lora_name"], "hero_boost.safetensors")
        sampler_nodes = [node for node in result["workflow"].values() if node["class_type"] == "KSampler"]
        self.assertEqual(len(sampler_nodes), 1)
        self.assertEqual(sampler_nodes[0]["inputs"]["model"], ["92", 0])

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

    def test_normalize_img2img_request_canonicalizes_image_edit_profile_to_img2img_mode_without_mask(self) -> None:
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

        self.assertEqual(normalized.mode, "img2img")
        self.assertEqual(normalized.execution_mode, "edit")
        self.assertEqual(normalized.mask_asset, "")
        self.assertEqual(normalized.profile, "qwen_image_edit")
        self.assertEqual(normalized.reference_image_assets, ["portrait-input"])
        self.assertEqual(normalized.main_reference_index, 0)
        self.assertEqual(
            normalized.template_lora_name,
            "Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors",
        )

    def test_normalize_img2img_request_accepts_image_edit_profile_on_img2img_mode(self) -> None:
        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=self._build_qwen_edit_inventory()):
            normalized = normalize_img2img_request(
                {
                    "prompt": "refresh the storefront signage",
                    "negative_prompt": "blurry",
                    "image_asset": "portrait-input",
                    "profile": "qwen_image_edit",
                    "mode": "img2img",
                }
            )

        self.assertEqual(normalized.mode, "img2img")
        self.assertEqual(normalized.execution_mode, "edit")
        self.assertEqual(normalized.image_asset, "portrait-input")

    def test_normalize_img2img_request_normalizes_ordered_reference_images(self) -> None:
        normalized = normalize_img2img_request(
            {
                "prompt": "portrait cleanup",
                "negative_prompt": "blurry",
                "mode": "img2img",
                "reference_images": [
                    {"image_asset": "reference-a"},
                    {"image_asset": "reference-b"},
                ],
                "main_reference_index": 1,
            }
        )

        self.assertEqual(normalized.reference_image_assets, ["reference-a", "reference-b"])
        self.assertEqual(normalized.main_reference_index, 1)
        self.assertEqual(normalized.image_asset, "reference-b")

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

    def test_missing_official_template_lora_warns_and_allows_img2img_generation(self) -> None:
        inventory = ModelInventorySnapshot(
            source="host",
            checkpoints=["__host_default__"],
            diffusion_models=["Qwen\\qwen_image_edit_fp8_e4m3fn.safetensors"],
            vae=["qwen_image_vae.safetensors"],
            text_encoders=["qwen_2.5_vl_7b_fp8_scaled.safetensors"],
            loras=[],
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
                }
            )

        self.assertEqual(normalized.template_lora_name, "")
        self.assertIn("TEMPLATE_LORA_MISSING", normalized.prompt_warning_codes)
        warning_text = "\n".join(normalized.prompt_warnings)
        self.assertIn("<lora:model_name:1>", warning_text)
        workflow = translate_img2img_request(normalized).to_payload()["workflow"]
        lora_nodes = [node for node in workflow.values() if node["class_type"] == "LoraLoaderModelOnly"]
        self.assertEqual(lora_nodes, [])

    def test_normalize_img2img_request_rejects_inpaint_mode_for_image_edit_profile(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported for official image-edit profiles"):
            normalize_img2img_request(
                {
                    "prompt": "refresh the storefront signage",
                    "image_asset": "portrait-input",
                    "profile": "qwen_image_edit",
                    "mode": "inpaint",
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

        encoder_nodes = [
            node
            for node in result["workflow"].values()
            if node["class_type"] == "RookieUIA1111CLIPTextEncode"
            and str(node["inputs"].get("text") or "").strip()
        ]
        self.assertTrue(encoder_nodes)
        self.assertTrue(all(node["inputs"].get("a1111_engine") == "text_only" for node in encoder_nodes))

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
                    "mode": "img2img",
                }
            )

        result = translate_img2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}

        self.assertEqual(result["workflow_kind"], "img2img-qwen_image_edit")
        self.assertIn("ImageScaleToTotalPixels", class_types)
        self.assertIn("TextEncodeQwenImageEdit", class_types)
        self.assertIn("LoraLoaderModelOnly", class_types)
        self.assertIn("ModelSamplingAuraFlow", class_types)
        self.assertNotIn("RookieUILoadAssetMask", class_types)
        self.assertEqual(
            len([node for node in result["workflow"].values() if node["class_type"] == "TextEncodeQwenImageEdit"]),
            2,
        )

    def test_normalize_img2img_request_rejects_qwen_edit_reference_count_above_manifest_limit(self) -> None:
        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=self._build_qwen_edit_inventory()):
            with self.assertRaisesRegex(ValueError, "supports at most 1 direct reference image"):
                normalize_img2img_request(
                    {
                        "prompt": "refresh the storefront signage",
                        "negative_prompt": "blurry",
                        "profile": "qwen_image_edit",
                        "mode": "img2img",
                        "reference_images": [
                            {"image_asset": "portrait-input"},
                            {"image_asset": "secondary-reference"},
                        ],
                        "main_reference_index": 0,
                    }
                )

    def test_normalize_img2img_request_accepts_firered_multi_reference_contract(self) -> None:
        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=self._build_qwen_plus_inventory()):
            normalized = normalize_img2img_request(
                {
                    "prompt": "merge the travelers into one poster frame",
                    "negative_prompt": "blurry",
                    "profile": "firered_image_edit",
                    "mode": "img2img",
                    "reference_images": [
                        {"image_asset": "traveler-a"},
                        {"image_asset": "traveler-b"},
                        {"image_asset": "traveler-c"},
                    ],
                    "main_reference_index": 1,
                }
            )

        self.assertEqual(normalized.profile, "firered_image_edit")
        self.assertEqual(normalized.mode, "img2img")
        self.assertEqual(normalized.execution_mode, "edit")
        self.assertEqual(normalized.image_asset, "traveler-b")
        self.assertEqual(normalized.reference_image_assets, ["traveler-a", "traveler-b", "traveler-c"])
        self.assertEqual(normalized.main_reference_index, 1)

    def test_normalize_img2img_request_resolves_qwen_2511_edit_selectors_and_references(self) -> None:
        with mock.patch(
            "rookieui.services.img2img.discover_model_inventory",
            return_value=self._build_qwen_2511_edit_inventory(),
        ):
            normalized = normalize_img2img_request(
                {
                    "prompt": "preserve the character and change the outfit",
                    "negative_prompt": "blurry",
                    "profile": "qwen_image_edit_2511",
                    "mode": "img2img",
                    "reference_images": [
                        {"image_asset": "character-main"},
                        {"image_asset": "style-reference"},
                        {"image_asset": "pose-reference"},
                    ],
                    "main_reference_index": 0,
                }
            )

        self.assertEqual(normalized.profile, "qwen_image_edit_2511")
        self.assertEqual(normalized.mode, "img2img")
        self.assertEqual(normalized.execution_mode, "edit")
        self.assertEqual(normalized.checkpoint_name, "Qwen\\qwen_image_edit_2511_bf16.safetensors")
        self.assertEqual(normalized.text_encoder_name, "qwen_2.5_vl_7b_fp8_scaled.safetensors")
        self.assertEqual(normalized.vae_name, "qwen_image_vae.safetensors")
        self.assertEqual(normalized.template_lora_name, "")
        self.assertEqual(normalized.shift, 3.1)
        self.assertIsNone(normalized.edit_megapixels)
        self.assertEqual(normalized.steps, 40)
        self.assertEqual(normalized.cfg_scale, 4.0)
        self.assertEqual(normalized.reference_image_assets, ["character-main", "style-reference", "pose-reference"])
        self.assertEqual(normalized.main_reference_index, 0)

    def test_normalize_img2img_request_rejects_qwen_2511_reference_count_above_manifest_limit(self) -> None:
        with mock.patch(
            "rookieui.services.img2img.discover_model_inventory",
            return_value=self._build_qwen_2511_edit_inventory(),
        ):
            with self.assertRaisesRegex(ValueError, "supports at most 3 direct reference image"):
                normalize_img2img_request(
                    {
                        "prompt": "preserve the character and change the outfit",
                        "profile": "qwen_image_edit_2511",
                        "mode": "img2img",
                        "reference_images": [
                            {"image_asset": "character-main"},
                            {"image_asset": "style-reference"},
                            {"image_asset": "pose-reference"},
                            {"image_asset": "extra-reference"},
                        ],
                        "main_reference_index": 0,
                    }
                )

    def test_normalize_img2img_request_rejects_firered_reference_count_above_manifest_limit(self) -> None:
        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=self._build_qwen_plus_inventory()):
            with self.assertRaisesRegex(ValueError, "supports at most 3 direct reference image"):
                normalize_img2img_request(
                    {
                        "prompt": "merge the travelers into one poster frame",
                        "negative_prompt": "blurry",
                        "profile": "firered_image_edit",
                        "mode": "img2img",
                        "reference_images": [
                            {"image_asset": "traveler-a"},
                            {"image_asset": "traveler-b"},
                            {"image_asset": "traveler-c"},
                            {"image_asset": "traveler-d"},
                        ],
                        "main_reference_index": 0,
                    }
                )

    def test_normalize_img2img_request_accepts_flux_kontext_edit_multi_reference_contract(self) -> None:
        with mock.patch(
            "rookieui.services.img2img.discover_model_inventory",
            return_value=self._build_flux_kontext_edit_inventory(),
        ):
            normalized = normalize_img2img_request(
                {
                    "prompt": "blend the two references into one cinematic edit",
                    "profile": "flux_kontext_dev_edit",
                    "mode": "img2img",
                    "reference_images": [
                        {"image_asset": "kontext-a"},
                        {"image_asset": "kontext-b"},
                    ],
                    "main_reference_index": 1,
                }
            )

        self.assertEqual(normalized.profile, "flux_kontext_dev_edit")
        self.assertEqual(normalized.mode, "img2img")
        self.assertEqual(normalized.execution_mode, "edit")
        self.assertEqual(normalized.image_asset, "kontext-b")
        self.assertEqual(normalized.reference_image_assets, ["kontext-a", "kontext-b"])
        self.assertEqual(normalized.main_reference_index, 1)
        self.assertEqual(normalized.text_encoder_name, "clip_l.safetensors|t5xxl_fp8_e4m3fn_scaled.safetensors")

    def test_normalize_img2img_request_rejects_flux_kontext_reference_count_above_manifest_limit(self) -> None:
        with mock.patch(
            "rookieui.services.img2img.discover_model_inventory",
            return_value=self._build_flux_kontext_edit_inventory(),
        ):
            with self.assertRaisesRegex(ValueError, "supports at most 3 direct reference image"):
                normalize_img2img_request(
                    {
                        "prompt": "blend the four references into one cinematic edit",
                        "profile": "flux_kontext_dev_edit",
                        "mode": "img2img",
                        "reference_images": [
                            {"image_asset": "kontext-a"},
                            {"image_asset": "kontext-b"},
                            {"image_asset": "kontext-c"},
                            {"image_asset": "kontext-d"},
                        ],
                        "main_reference_index": 0,
                    }
                )

    def test_normalize_img2img_request_rejects_longcat_image_edit_reference_count_above_manifest_limit(self) -> None:
        with mock.patch(
            "rookieui.services.img2img.discover_model_inventory",
            return_value=self._build_longcat_edit_inventory(),
        ):
            with self.assertRaisesRegex(ValueError, "supports at most 1 direct reference image"):
                normalize_img2img_request(
                    {
                        "prompt": "turn the portrait into a glossy editorial cat poster",
                        "profile": "longcat_image_edit",
                        "mode": "img2img",
                        "reference_images": [
                            {"image_asset": "longcat-main"},
                            {"image_asset": "longcat-extra"},
                        ],
                        "main_reference_index": 0,
                    }
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
                    "mode": "img2img",
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

    def test_translate_img2img_request_builds_qwen_image_edit_multi_lora_workflow(self) -> None:
        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=self._build_qwen_edit_inventory()):
            normalized = normalize_img2img_request(
                {
                    "prompt": "refresh the storefront signage",
                    "negative_prompt": "blurry",
                    "image_asset": "portrait-input",
                    "profile": "qwen_image_edit_multi_lora",
                    "mode": "img2img",
                }
            )

        result = translate_img2img_request(normalized).to_payload()
        workflow = result["workflow"]
        self.assertEqual(result["workflow_kind"], "img2img-qwen_image_edit_multi_lora")
        model_sampling_node = next(node for node in workflow.values() if node["class_type"] == "ModelSamplingAuraFlow")
        chained_model_ref = model_sampling_node["inputs"]["model"]
        chain_depth = 0
        while workflow[chained_model_ref[0]]["class_type"] == "LoraLoaderModelOnly":
            node = workflow[chained_model_ref[0]]
            self.assertEqual(node["inputs"]["lora_name"], "Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors")
            chain_depth += 1
            chained_model_ref = node["inputs"]["model"]
        self.assertEqual(chain_depth, 3)
        self.assertEqual(workflow[chained_model_ref[0]]["class_type"], "UNETLoader")

    def test_translate_img2img_request_builds_firered_image_edit_workflow_with_three_references(self) -> None:
        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=self._build_qwen_plus_inventory()):
            normalized = normalize_img2img_request(
                {
                    "prompt": "merge the travelers into one poster frame",
                    "negative_prompt": "blurry",
                    "profile": "firered_image_edit",
                    "mode": "img2img",
                    "reference_images": [
                        {"image_asset": "traveler-a"},
                        {"image_asset": "traveler-b"},
                        {"image_asset": "traveler-c"},
                    ],
                    "main_reference_index": 1,
                }
            )

        result = translate_img2img_request(normalized).to_payload()
        workflow = result["workflow"]
        class_types = {node["class_type"] for node in workflow.values()}
        scale_node_ids = sorted(
            [node_id for node_id, node in workflow.items() if node["class_type"] == "ImageScaleToTotalPixels"],
            key=int,
        )
        encode_nodes = [node for node in workflow.values() if node["class_type"] == "TextEncodeQwenImageEditPlus"]

        self.assertEqual(result["workflow_kind"], "img2img-firered_image_edit")
        self.assertIn("TextEncodeQwenImageEditPlus", class_types)
        self.assertNotIn("RookieUILoadAssetMask", class_types)
        self.assertNotIn("LoraLoaderModelOnly", class_types)
        self.assertEqual(len(scale_node_ids), 3)
        self.assertEqual(len(encode_nodes), 2)
        self.assertEqual(encode_nodes[0]["inputs"]["image1"], [scale_node_ids[0], 0])
        self.assertEqual(encode_nodes[0]["inputs"]["image2"], [scale_node_ids[1], 0])
        self.assertEqual(encode_nodes[0]["inputs"]["image3"], [scale_node_ids[2], 0])
        vae_encode_node = next(node for node in workflow.values() if node["class_type"] == "VAEEncode")
        self.assertEqual(vae_encode_node["inputs"]["pixels"], [scale_node_ids[1], 0])
        sampler_node = next(node for node in workflow.values() if node["class_type"] == "KSampler")
        self.assertEqual(sampler_node["inputs"]["steps"], 40)
        self.assertEqual(sampler_node["inputs"]["cfg"], 4.0)

    def test_translate_img2img_request_builds_qwen_2511_official_edit_workflow(self) -> None:
        with mock.patch(
            "rookieui.services.img2img.discover_model_inventory",
            return_value=self._build_qwen_2511_edit_inventory(),
        ):
            normalized = normalize_img2img_request(
                {
                    "prompt": "preserve the character and change the outfit",
                    "negative_prompt": "blurry",
                    "profile": "qwen_image_edit_2511",
                    "mode": "img2img",
                    "reference_images": [
                        {"image_asset": "character-main"},
                        {"image_asset": "style-reference"},
                        {"image_asset": "pose-reference"},
                    ],
                    "main_reference_index": 0,
                }
            )

        result = translate_img2img_request(normalized).to_payload()
        workflow = result["workflow"]
        class_types = {node["class_type"] for node in workflow.values()}
        encode_nodes = [node for node in workflow.values() if node["class_type"] == "TextEncodeQwenImageEditPlus"]
        reference_method_nodes = [
            node for node in workflow.values() if node["class_type"] == "FluxKontextMultiReferenceLatentMethod"
        ]
        scale_id = next(
            node_id for node_id, node in workflow.items() if node["class_type"] == "FluxKontextImageScale"
        )
        load_ids = {
            node["inputs"]["asset_handle"]: node_id
            for node_id, node in workflow.items()
            if node["class_type"] == "RookieUILoadAssetImage"
        }
        sampler_node = next(node for node in workflow.values() if node["class_type"] == "KSampler")
        model_sampling_node = next(node for node in workflow.values() if node["class_type"] == "ModelSamplingAuraFlow")
        vae_encode_node = next(node for node in workflow.values() if node["class_type"] == "VAEEncode")

        self.assertEqual(result["workflow_kind"], "img2img-qwen_image_edit_2511")
        self.assertIn("CFGNorm", class_types)
        self.assertIn("VAEDecode", class_types)
        self.assertNotIn("LoraLoaderModelOnly", class_types)
        self.assertNotIn("ImageScaleToTotalPixels", class_types)
        self.assertEqual(len(encode_nodes), 2)
        self.assertEqual(len(reference_method_nodes), 2)
        self.assertEqual(reference_method_nodes[0]["inputs"]["reference_latents_method"], "index_timestep_zero")
        self.assertEqual(encode_nodes[0]["inputs"]["image1"], [scale_id, 0])
        self.assertEqual(encode_nodes[0]["inputs"]["image2"], [load_ids["style-reference"], 0])
        self.assertEqual(encode_nodes[0]["inputs"]["image3"], [load_ids["pose-reference"], 0])
        self.assertEqual(vae_encode_node["inputs"]["pixels"], [scale_id, 0])
        self.assertEqual(model_sampling_node["inputs"]["shift"], 3.1)
        self.assertEqual(sampler_node["inputs"]["steps"], 40)
        self.assertEqual(sampler_node["inputs"]["cfg"], 4.0)
        self.assertEqual(workflow[sampler_node["inputs"]["positive"][0]]["class_type"], "FluxKontextMultiReferenceLatentMethod")
        self.assertEqual(workflow[sampler_node["inputs"]["negative"][0]]["class_type"], "FluxKontextMultiReferenceLatentMethod")

    def test_translate_img2img_request_builds_qwen_2511_workflow_with_single_reference(self) -> None:
        with mock.patch(
            "rookieui.services.img2img.discover_model_inventory",
            return_value=self._build_qwen_2511_edit_inventory(),
        ):
            normalized = normalize_img2img_request(
                {
                    "prompt": "preserve the character and change the outfit",
                    "negative_prompt": "blurry",
                    "profile": "qwen_image_edit_2511",
                    "mode": "img2img",
                    "image_asset": "character-main",
                }
            )

        workflow = translate_img2img_request(normalized).to_payload()["workflow"]
        encode_nodes = [node for node in workflow.values() if node["class_type"] == "TextEncodeQwenImageEditPlus"]

        self.assertEqual(len(encode_nodes), 2)
        self.assertIn("image1", encode_nodes[0]["inputs"])
        self.assertNotIn("image2", encode_nodes[0]["inputs"])
        self.assertNotIn("image3", encode_nodes[0]["inputs"])

    def test_translate_img2img_request_builds_firered_lightning_workflow_with_template_lora(self) -> None:
        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=self._build_qwen_plus_inventory()):
            normalized = normalize_img2img_request(
                {
                    "prompt": "turn the portrait into a dramatic editorial frame",
                    "negative_prompt": "blurry",
                    "profile": "firered_image_edit_lightning",
                    "mode": "img2img",
                    "reference_images": [{"image_asset": "portrait-input"}],
                    "main_reference_index": 0,
                }
            )

        result = translate_img2img_request(normalized).to_payload()
        workflow = result["workflow"]
        lora_nodes = [node for node in workflow.values() if node["class_type"] == "LoraLoaderModelOnly"]
        sampler_node = next(node for node in workflow.values() if node["class_type"] == "KSampler")

        self.assertEqual(result["workflow_kind"], "img2img-firered_image_edit_lightning")
        self.assertEqual(len(lora_nodes), 1)
        self.assertEqual(
            lora_nodes[0]["inputs"]["lora_name"],
            "Qwen\\FireRed-Image-Edit-1.0-Lightning-8steps-v1.0.safetensors",
        )
        self.assertEqual(sampler_node["inputs"]["steps"], 8)
        self.assertEqual(sampler_node["inputs"]["cfg"], 1.0)

    def test_translate_img2img_request_builds_flux_kontext_dev_image_edit_workflow(self) -> None:
        with mock.patch(
            "rookieui.services.img2img.discover_model_inventory",
            return_value=self._build_flux_kontext_edit_inventory(),
        ):
            normalized = normalize_img2img_request(
                {
                    "prompt": "merge the studio portrait with the silk texture reference",
                    "profile": "flux_kontext_dev_edit",
                    "mode": "img2img",
                    "reference_images": [
                        {"image_asset": "kontext-a"},
                        {"image_asset": "kontext-b"},
                    ],
                    "main_reference_index": 1,
                }
            )

        result = translate_img2img_request(normalized).to_payload()
        workflow = result["workflow"]
        class_types = {node["class_type"] for node in workflow.values()}
        asset_node_ids = {
            node["inputs"]["asset_handle"]: node_id
            for node_id, node in workflow.items()
            if node["class_type"] == "RookieUILoadAssetImage"
        }
        stitch_node = next(node for node in workflow.values() if node["class_type"] == "ImageStitch")
        clip_node = next(node for node in workflow.values() if node["class_type"] == "DualCLIPLoader")
        sampler_node = next(node for node in workflow.values() if node["class_type"] == "KSampler")

        self.assertEqual(result["workflow_kind"], "img2img-flux_kontext_dev_edit")
        self.assertIn("FluxKontextImageScale", class_types)
        self.assertIn("ReferenceLatent", class_types)
        self.assertIn("ConditioningZeroOut", class_types)
        self.assertNotIn("RookieUILoadAssetMask", class_types)
        self.assertEqual(stitch_node["inputs"]["image1"], [asset_node_ids["kontext-b"], 0])
        self.assertEqual(stitch_node["inputs"]["image2"], [asset_node_ids["kontext-a"], 0])
        self.assertEqual(clip_node["inputs"]["clip_name1"], "clip_l.safetensors")
        self.assertEqual(clip_node["inputs"]["clip_name2"], "t5xxl_fp8_e4m3fn_scaled.safetensors")
        self.assertEqual(sampler_node["inputs"]["steps"], 20)
        self.assertEqual(sampler_node["inputs"]["cfg"], 1.0)

    def test_translate_img2img_request_builds_flux2_image_edit_workflow(self) -> None:
        with mock.patch(
            "rookieui.services.img2img.discover_model_inventory",
            return_value=self._build_flux2_edit_inventory(),
        ):
            normalized = normalize_img2img_request(
                {
                    "prompt": "refresh the product photo lighting",
                    "profile": "flux2_image_edit",
                    "mode": "img2img",
                    "image_asset": "flux2-source",
                }
            )

        result = translate_img2img_request(normalized).to_payload()
        workflow = result["workflow"]
        class_types = {node["class_type"] for node in workflow.values()}
        scale_node = next(node for node in workflow.values() if node["class_type"] == "ImageScaleToTotalPixels")
        clip_node = next(node for node in workflow.values() if node["class_type"] == "CLIPLoader")
        noise_node = next(node for node in workflow.values() if node["class_type"] == "RandomNoise")

        self.assertEqual(result["workflow_kind"], "img2img-flux2_image_edit")
        self.assertIn("BasicGuider", class_types)
        self.assertIn("SamplerCustomAdvanced", class_types)
        self.assertIn("Flux2Scheduler", class_types)
        self.assertIn("EmptyFlux2LatentImage", class_types)
        self.assertNotIn("CFGGuider", class_types)
        self.assertNotIn("RookieUILoadAssetMask", class_types)
        self.assertEqual(scale_node["inputs"]["megapixels"], 1.0)
        self.assertEqual(clip_node["inputs"]["clip_name"], "mistral_3_small_flux2_bf16.safetensors")
        self.assertEqual(clip_node["inputs"]["type"], "flux2")
        self.assertEqual(noise_node["inputs"]["noise_seed"], result["normalized_request"]["execution_seed"])

    def test_translate_img2img_request_builds_klein_9b_kv_image_edit_workflow(self) -> None:
        with mock.patch(
            "rookieui.services.img2img.discover_model_inventory",
            return_value=self._build_klein_kv_edit_inventory(),
        ):
            normalized = normalize_img2img_request(
                {
                    "prompt": "combine the outfit reference with the portrait",
                    "profile": "klein_9b_kv_image_edit",
                    "mode": "img2img",
                    "reference_images": [
                        {"image_asset": "klein-main"},
                        {"image_asset": "klein-style"},
                    ],
                    "main_reference_index": 0,
                }
            )

        result = translate_img2img_request(normalized).to_payload()
        workflow = result["workflow"]
        class_types = {node["class_type"] for node in workflow.values()}
        cfg_guider = next(node for node in workflow.values() if node["class_type"] == "CFGGuider")
        kv_cache_node_id = next(node_id for node_id, node in workflow.items() if node["class_type"] == "FluxKVCache")
        reference_latents = [node for node in workflow.values() if node["class_type"] == "ReferenceLatent"]

        self.assertEqual(result["workflow_kind"], "img2img-klein_9b_kv_image_edit")
        self.assertIn("SamplerCustomAdvanced", class_types)
        self.assertIn("Flux2Scheduler", class_types)
        self.assertIn("ImageScaleToTotalPixels", class_types)
        self.assertNotIn("BasicGuider", class_types)
        self.assertNotIn("RookieUILoadAssetMask", class_types)
        self.assertEqual(len(reference_latents), 4)
        self.assertEqual(cfg_guider["inputs"]["cfg"], 1.0)
        self.assertEqual(cfg_guider["inputs"]["model"], [kv_cache_node_id, 0])
        self.assertTrue(
            all(
                node["inputs"]["asset_handle"].startswith("klein-")
                for node in workflow.values()
                if node["class_type"] == "RookieUILoadAssetImage"
            )
        )
        self.assertEqual(
            next(node for node in workflow.values() if node["class_type"] == "Flux2Scheduler")["inputs"]["steps"],
            4,
        )

    def test_translate_img2img_request_builds_longcat_image_edit_workflow(self) -> None:
        with mock.patch(
            "rookieui.services.img2img.discover_model_inventory",
            return_value=self._build_longcat_edit_inventory(),
        ):
            normalized = normalize_img2img_request(
                {
                    "prompt": "turn the portrait into a longcat magazine cover",
                    "negative_prompt": "blurry",
                    "profile": "longcat_image_edit",
                    "mode": "img2img",
                    "image_asset": "longcat-source",
                }
            )

        result = translate_img2img_request(normalized).to_payload()
        workflow = result["workflow"]
        class_types = {node["class_type"] for node in workflow.values()}
        scale_node = next(node for node in workflow.values() if node["class_type"] == "ImageScaleToTotalPixels")
        clip_node = next(node for node in workflow.values() if node["class_type"] == "CLIPLoader")

        self.assertEqual(result["workflow_kind"], "img2img-longcat_image_edit")
        self.assertIn("FluxGuidance", class_types)
        self.assertIn("FluxKontextMultiReferenceLatentMethod", class_types)
        self.assertIn("TextEncodeQwenImageEdit", class_types)
        self.assertIn("KSampler", class_types)
        self.assertNotIn("RookieUILoadAssetMask", class_types)
        self.assertEqual(scale_node["inputs"]["resolution_steps"], 16)
        self.assertEqual(clip_node["inputs"]["clip_name"], "qwen_2.5_vl_7b_fp8_scaled.safetensors")
        self.assertEqual(clip_node["inputs"]["type"], "longcat_image")
        self.assertEqual(
            next(node for node in workflow.values() if node["class_type"] == "RookieUILoadAssetImage")["inputs"][
                "asset_handle"
            ],
            "longcat-source",
        )
        self.assertEqual(
            len([node for node in workflow.values() if node["class_type"] == "FluxKontextMultiReferenceLatentMethod"]),
            2,
        )
        self.assertEqual(len([node for node in workflow.values() if node["class_type"] == "TextEncodeQwenImageEdit"]), 2)

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

    def test_img2img_route_accepts_full_frontend_submit_payload(self) -> None:
        response = asyncio.run(
            routes.img2img(
                _FakeJsonRequest(
                    {
                        "prompt": "forest shrine variation",
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
                    }
                )
            )
        )

        self.assertEqual(response["status"], 200)
        normalized = response["payload"]["normalized_request"]
        self.assertEqual(normalized["profile"], "sd15")
        self.assertEqual(normalized["mode"], "img2img")
        self.assertIsNone(normalized["edit_megapixels"])

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

    def test_img2img_route_accepts_image_edit_profile_without_mask_on_img2img_contract(self) -> None:
        with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=self._build_qwen_edit_inventory()):
            response = asyncio.run(
                routes.img2img(
                    _FakeJsonRequest(
                        {
                            "prompt": "refresh the storefront signage",
                            "image_asset": "img-source",
                            "profile": "qwen_image_edit",
                            "mode": "img2img",
                            "dry_run": True,
                        }
                    )
                )
            )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["workflow_kind"], "img2img-qwen_image_edit")

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
