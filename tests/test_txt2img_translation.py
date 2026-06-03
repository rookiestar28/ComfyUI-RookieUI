from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from unittest import mock

from rookieui.api import routes
from rookieui.contracts.models import ModelInventorySnapshot
from rookieui.services.txt2img import normalize_txt2img_request
from rookieui.services.workflow_translation import translate_txt2img_request


class _FakeJsonRequest:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    async def json(self) -> dict[str, object]:
        return self._payload


class Txt2ImgTranslationTests(unittest.TestCase):
    def _z_image_turbo_inventory(self) -> ModelInventorySnapshot:
        return ModelInventorySnapshot(
            source="host",
            checkpoints=["SDXL\\realvisxl.safetensors"],
            diffusion_models=["zimage\\z_image_turbo_bf16.safetensors"],
            vae=["ae.safetensors"],
            text_encoders=["qwen_3_4b.safetensors"],
            controlnet=["sdxl-controlnet-depth.safetensors"],
            model_patches=["Z-Image\\Z-Image-Turbo-Fun-Controlnet-Union.safetensors"],
            default_checkpoint="SDXL\\realvisxl.safetensors",
            default_vae="ae.safetensors",
            default_text_encoder="qwen_3_4b.safetensors",
        )

    def test_normalize_txt2img_request_applies_sd15_defaults(self) -> None:
        request = normalize_txt2img_request({"prompt": "city skyline"})

        self.assertEqual(request.profile, "sd15")
        self.assertEqual(request.width, 512)
        self.assertEqual(request.height, 512)
        self.assertEqual(request.sampler_name, "euler_ancestral")
        self.assertEqual(request.seed, -1)
        self.assertGreaterEqual(request.execution_seed, 0)
        self.assertEqual(request.primary_model_category, "checkpoints")
        self.assertIn("width", request.applied_defaults)
        self.assertIn("scheduler_name", request.applied_defaults)
        self.assertEqual(request.dtype_profile, "automatic")
        self.assertEqual(request.lora_name, "")

    def test_normalize_txt2img_request_accepts_supported_dtype_profile(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "dtype_profile": "Automatic (fp16 LoRA)",
            }
        )

        self.assertEqual(request.dtype_profile, "automatic_fp16_lora")

    def test_normalize_txt2img_request_accepts_frontend_edit_megapixels_field(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "profile": "sd15",
                "edit_megapixels": None,
            }
        )

        self.assertIsNone(request.edit_megapixels)

    def test_translate_txt2img_request_embeds_raw_a1111_generation_parameters(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "forest shrine",
                "negative_prompt": "low detail",
                "profile": "sd15",
                "width": 640,
                "height": 768,
                "steps": 22,
                "cfg_scale": 6.5,
                "sampler_name": "Euler a",
                "scheduler_name": "Karras",
                "seed": 1234,
                "clip_skip": 2,
            }
        )

        result = translate_txt2img_request(request).to_payload()
        save_nodes = [
            node
            for node in result["workflow"].values()
            if node["class_type"] == "RookieUISaveImageWithMetadata"
        ]

        self.assertEqual(len(save_nodes), 1)
        parameters = save_nodes[0]["inputs"]["parameters"]
        self.assertIn("forest shrine", parameters)
        self.assertIn("Negative prompt: low detail", parameters)
        self.assertIn("Steps: 22", parameters)
        self.assertIn("Sampler: Euler a", parameters)
        self.assertIn("Schedule type: Karras", parameters)
        self.assertIn("CFG scale: 6.5", parameters)
        self.assertIn("Seed: 1234", parameters)
        self.assertIn("Size: 640x768", parameters)
        self.assertIn("Clip skip: 2", parameters)
        self.assertNotIn("rookieui_origin", parameters)
        self.assertNotIn("client_id", parameters)
        self.assertEqual(
            result["generation_metadata"]["extra_pnginfo"]["rookieui"]["schema"],
            "rookieui.generation_metadata.v1",
        )
        self.assertNotIn("parameters", result["generation_metadata"]["extra_pnginfo"])

    def test_normalize_txt2img_request_normalizes_adetailer_block(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "adetailer": {
                    "enabled": True,
                    "skip_img2img": True,
                    "units": [
                        {
                            "enabled": True,
                            "detector": "face_yolov8n.pt",
                            "prompt": "repair eyes",
                            "controlnet": {"mode": "passthrough"},
                        }
                    ],
                },
            }
        )

        self.assertTrue(request.adetailer.enabled)
        self.assertFalse(request.adetailer.skip_img2img)
        self.assertIn("ADETAILER_SKIP_IMG2IMG_IGNORED", request.adetailer.warning_codes)
        self.assertIn("ADETAILER_DETECTOR_RUNTIME_FALLBACK_MASK", request.adetailer.warning_codes)
        self.assertIn("ADETAILER_CONTROLNET_PASSTHROUGH_EMPTY", request.adetailer.warning_codes)
        self.assertEqual(
            request.adetailer.diagnostics["detector_runtime"],
            "rookieui_native_detector_runtime_with_fallback",
        )
        self.assertEqual(request.adetailer.units[0].detector, "face_yolov8n.pt")
        self.assertEqual(request.adetailer.units[0].controlnet.mode, "passthrough")

    def test_normalize_txt2img_request_accepts_z_image_turbo_controlnet_model_patch(self) -> None:
        with (
            mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=self._z_image_turbo_inventory()),
            mock.patch("rookieui.services.controlnet.resolve_asset_path", return_value=Path(__file__)),
        ):
            request = normalize_txt2img_request(
                {
                    "prompt": "city skyline",
                    "profile": "z_image_turbo",
                    "controlnet_units": [
                        {
                            "enabled": True,
                            "module": "none",
                            "model": "Z-Image\\Z-Image-Turbo-Fun-Controlnet-Union.safetensors",
                            "image_asset": "source-image",
                        }
                    ],
                }
            )

        self.assertEqual(request.profile, "z_image_turbo")
        self.assertEqual(request.controlnet_units[0].model, "Z-Image\\Z-Image-Turbo-Fun-Controlnet-Union.safetensors")

    def test_translate_txt2img_request_builds_z_image_turbo_model_patch_controlnet_graph(self) -> None:
        with (
            mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=self._z_image_turbo_inventory()),
            mock.patch("rookieui.services.controlnet.resolve_asset_path", return_value=Path(__file__)),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "city skyline",
                    "profile": "z_image_turbo",
                    "controlnet_units": [
                        {
                            "enabled": True,
                            "module": "none",
                            "model": "Z-Image\\Z-Image-Turbo-Fun-Controlnet-Union.safetensors",
                            "image_asset": "source-image",
                            "weight": 0.75,
                        }
                    ],
                }
            )

        result = translate_txt2img_request(normalized).to_payload()
        workflow = result["workflow"]
        class_types = {node["class_type"] for node in workflow.values()}

        self.assertEqual(result["workflow_kind"], "txt2img-z_image_turbo")
        self.assertIn("ModelPatchLoader", class_types)
        self.assertIn("QwenImageDiffsynthControlnet", class_types)
        self.assertIn("ModelSamplingAuraFlow", class_types)
        self.assertIn("EmptySD3LatentImage", class_types)
        self.assertIn("CLIPTextEncode", class_types)
        self.assertIn("ConditioningZeroOut", class_types)
        self.assertIn("KSampler", class_types)
        self.assertNotIn("ControlNetLoader", class_types)
        self.assertNotIn("DiffControlNetLoader", class_types)
        self.assertNotIn("RookieUIControlNetApplyNativeAdvanced", class_types)
        self.assertNotIn("RookieUIControlNetPreprocess", class_types)

        patch_loader_id, patch_loader = next(
            (node_id, node) for node_id, node in workflow.items() if node["class_type"] == "ModelPatchLoader"
        )
        qwen_control_id, qwen_control = next(
            (node_id, node) for node_id, node in workflow.items() if node["class_type"] == "QwenImageDiffsynthControlnet"
        )
        sampling_node_id, sampling_node = next(
            (node_id, node) for node_id, node in workflow.items() if node["class_type"] == "ModelSamplingAuraFlow"
        )
        get_size_id, get_size_node = next(
            (node_id, node) for node_id, node in workflow.items() if node["class_type"] == "GetImageSize"
        )
        latent_node = next(node for node in workflow.values() if node["class_type"] == "EmptySD3LatentImage")
        sampler_node = next(node for node in workflow.values() if node["class_type"] == "KSampler")

        self.assertEqual(patch_loader["inputs"]["name"], "Z-Image\\Z-Image-Turbo-Fun-Controlnet-Union.safetensors")
        self.assertEqual(qwen_control["inputs"]["model_patch"], [patch_loader_id, 0])
        self.assertEqual(qwen_control["inputs"]["strength"], 0.75)
        self.assertEqual(qwen_control["inputs"]["image"], get_size_node["inputs"]["image"])
        self.assertEqual(latent_node["inputs"]["width"], [get_size_id, 0])
        self.assertEqual(latent_node["inputs"]["height"], [get_size_id, 1])
        self.assertEqual(sampling_node["inputs"]["model"], [qwen_control_id, 0])
        self.assertEqual(sampler_node["inputs"]["model"], [sampling_node_id, 0])

    def test_translate_txt2img_request_builds_z_image_turbo_canny_adapter_shape(self) -> None:
        with (
            mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=self._z_image_turbo_inventory()),
            mock.patch("rookieui.services.controlnet.resolve_asset_path", return_value=Path(__file__)),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "city skyline",
                    "profile": "z_image_turbo",
                    "controlnet_units": [
                        {
                            "enabled": True,
                            "module": "canny",
                            "model": "Z-Image\\Z-Image-Turbo-Fun-Controlnet-Union.safetensors",
                            "image_asset": "source-image",
                            "threshold_a": 30,
                            "threshold_b": 40,
                        }
                    ],
                }
            )
        workflow = translate_txt2img_request(normalized).to_payload()["workflow"]
        scale_id, scale_node = next(
            (node_id, node) for node_id, node in workflow.items() if node["class_type"] == "ImageScaleToTotalPixels"
        )
        canny_id, canny_node = next((node_id, node) for node_id, node in workflow.items() if node["class_type"] == "Canny")
        get_size_id, get_size_node = next(
            (node_id, node) for node_id, node in workflow.items() if node["class_type"] == "GetImageSize"
        )
        qwen_control = next(node for node in workflow.values() if node["class_type"] == "QwenImageDiffsynthControlnet")
        latent_node = next(node for node in workflow.values() if node["class_type"] == "EmptySD3LatentImage")

        self.assertEqual(scale_node["inputs"]["upscale_method"], "nearest-exact")
        self.assertEqual(scale_node["inputs"]["megapixels"], 1.0)
        self.assertEqual(scale_node["inputs"]["resolution_steps"], 1)
        self.assertEqual(canny_node["inputs"]["image"], [scale_id, 0])
        self.assertEqual(canny_node["inputs"]["low_threshold"], 0.3)
        self.assertEqual(canny_node["inputs"]["high_threshold"], 0.4)
        self.assertEqual(qwen_control["inputs"]["image"], [canny_id, 0])
        self.assertEqual(get_size_node["inputs"]["image"], [canny_id, 0])
        self.assertEqual(latent_node["inputs"]["width"], [get_size_id, 0])
        self.assertEqual(latent_node["inputs"]["height"], [get_size_id, 1])

    def test_translate_txt2img_request_builds_z_image_turbo_depth_adapter_shape(self) -> None:
        with (
            mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=self._z_image_turbo_inventory()),
            mock.patch("rookieui.services.controlnet.resolve_asset_path", return_value=Path(__file__)),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "city skyline",
                    "profile": "z_image_turbo",
                    "controlnet_units": [
                        {
                            "enabled": True,
                            "module": "depth",
                            "model": "Z-Image\\Z-Image-Turbo-Fun-Controlnet-Union.safetensors",
                            "image_asset": "source-image",
                        }
                    ],
                }
            )
        workflow = translate_txt2img_request(normalized).to_payload()["workflow"]
        class_types = {node["class_type"] for node in workflow.values()}
        scale_id, scale_node = next(
            (node_id, node) for node_id, node in workflow.items() if node["class_type"] == "ImageScaleToTotalPixels"
        )
        qwen_control = next(node for node in workflow.values() if node["class_type"] == "QwenImageDiffsynthControlnet")
        get_size_node = next(node for node in workflow.values() if node["class_type"] == "GetImageSize")

        self.assertEqual(scale_node["inputs"]["upscale_method"], "lanczos")
        self.assertEqual(qwen_control["inputs"]["image"], [scale_id, 0])
        self.assertEqual(get_size_node["inputs"]["image"], [scale_id, 0])
        self.assertNotIn("RookieUIControlNetPreprocess", class_types)
        self.assertNotIn("LotusConditioning", class_types)

    def test_translate_txt2img_request_builds_z_image_turbo_pose_passthrough_shape(self) -> None:
        with (
            mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=self._z_image_turbo_inventory()),
            mock.patch("rookieui.services.controlnet.resolve_asset_path", return_value=Path(__file__)),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "city skyline",
                    "profile": "z_image_turbo",
                    "controlnet_units": [
                        {
                            "enabled": True,
                            "module": "openpose",
                            "model": "Z-Image\\Z-Image-Turbo-Fun-Controlnet-Union.safetensors",
                            "image_asset": "source-image",
                        }
                    ],
                }
            )
        workflow = translate_txt2img_request(normalized).to_payload()["workflow"]
        class_types = {node["class_type"] for node in workflow.values()}
        image_id, image_node = next(
            (node_id, node) for node_id, node in workflow.items() if node["class_type"] == "RookieUILoadAssetImage"
        )
        qwen_control = next(node for node in workflow.values() if node["class_type"] == "QwenImageDiffsynthControlnet")
        get_size_node = next(node for node in workflow.values() if node["class_type"] == "GetImageSize")

        self.assertEqual(image_node["inputs"]["asset_handle"], "source-image")
        self.assertEqual(qwen_control["inputs"]["image"], [image_id, 0])
        self.assertEqual(get_size_node["inputs"]["image"], [image_id, 0])
        self.assertNotIn("RookieUIControlNetPreprocess", class_types)
        self.assertNotIn("ImageScaleToTotalPixels", class_types)
        self.assertNotIn("Canny", class_types)

    def test_translate_txt2img_request_rejects_unsupported_z_image_turbo_controlnet_module(self) -> None:
        with (
            mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=self._z_image_turbo_inventory()),
            mock.patch("rookieui.services.controlnet.resolve_asset_path", return_value=Path(__file__)),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "city skyline",
                    "profile": "z_image_turbo",
                    "controlnet_units": [
                        {
                            "enabled": True,
                            "module": "lineart",
                            "model": "Z-Image\\Z-Image-Turbo-Fun-Controlnet-Union.safetensors",
                            "image_asset": "source-image",
                        }
                    ],
                }
            )

        with self.assertRaisesRegex(ValueError, "Unsupported Z-Image Turbo ControlNet module"):
            translate_txt2img_request(normalized)

    def test_normalize_txt2img_request_reports_adetailer_no_active_units(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "adetailer": {
                    "enabled": True,
                    "units": [{"enabled": True, "detector": "None"}],
                },
            }
        )

        self.assertIn("ADETAILER_NO_ACTIVE_UNITS", request.adetailer.warning_codes)
        self.assertEqual(request.adetailer.diagnostics["active_unit_count"], 0)

    def test_normalize_txt2img_request_reports_adetailer_custom_controlnet_without_model(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "adetailer": {
                    "enabled": True,
                    "units": [
                        {
                            "enabled": True,
                            "detector": "face_yolov8n.pt",
                            "controlnet": {"mode": "custom", "module": "none", "model": ""},
                        }
                    ],
                },
            }
        )

        self.assertIn("ADETAILER_CONTROLNET_CUSTOM_MODEL_MISSING", request.adetailer.warning_codes)
        self.assertTrue(request.adetailer.diagnostics["degraded"])

    def test_normalize_txt2img_request_rejects_unsupported_dtype_profile(self) -> None:
        with self.assertRaisesRegex(ValueError, "dtype_profile is unsupported"):
            normalize_txt2img_request(
                {
                    "prompt": "city skyline",
                    "dtype_profile": "mystery-lowbit",
                }
            )

    def test_translate_txt2img_request_builds_lora_loader_when_selected(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "lora_name": "detail_tweaker.safetensors",
                "lora_strength_model": 0.8,
                "lora_strength_clip": 0.6,
            }
        )

        result = translate_txt2img_request(normalized).to_payload()

        self.assertEqual(result["normalized_request"]["lora_name"], "detail_tweaker.safetensors")
        self.assertEqual(result["workflow"]["90"]["class_type"], "LoraLoader")
        self.assertEqual(result["workflow"]["90"]["inputs"]["strength_model"], 0.8)
        self.assertEqual(result["workflow"]["90"]["inputs"]["strength_clip"], 0.6)
        self.assertEqual(result["workflow"]["5"]["inputs"]["model"], ["90", 0])

    def test_normalize_txt2img_request_extracts_inline_lora_from_prompt(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "city skyline <lora:detail_tweaker.safetensors:0.8>",
            }
        )

        self.assertEqual(normalized.prompt, "city skyline")
        self.assertEqual(normalized.lora_name, "")
        self.assertEqual(len(normalized.lora_activations), 1)
        self.assertEqual(normalized.lora_activations[0].name, "detail_tweaker.safetensors")
        self.assertEqual(normalized.lora_activations[0].strength_model, 0.8)
        self.assertEqual(normalized.lora_activations[0].strength_clip, 0.8)

    def test_normalize_txt2img_request_exposes_prompt_semantics_and_warning_codes(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "hero AND villain BREAK [calm:chaos:0.4]",
            }
        )

        self.assertIn("PROMPT_AND_DETECTED", normalized.prompt_warning_codes)
        self.assertTrue(normalized.prompt_semantics["features"]["and_composition"])
        self.assertTrue(normalized.prompt_semantics["features"]["break_chunks"])
        self.assertTrue(normalized.prompt_semantics["features"]["prompt_scheduling"])
        self.assertEqual(len(normalized.prompt_semantics["branches"]), 2)

    def test_normalize_txt2img_request_exposes_alternate_prompt_scheduling_semantics(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "portrait [warm|cool] light",
                "steps": 4,
            }
        )

        self.assertIn("PROMPT_ALTERNATE_DETECTED", normalized.prompt_warning_codes)
        self.assertTrue(normalized.prompt_semantics["features"]["alternate_prompt_scheduling"])
        slices = normalized.prompt_semantics["branches"][0]["chunks"][0]["slices"]
        self.assertEqual([slice_item["text"] for slice_item in slices[:2]], ["portrait warm light", "portrait cool light"])
        self.assertEqual(len(slices), 4)

    def test_normalize_txt2img_request_canonicalizes_inventory_backed_embedding_tokens(self) -> None:
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

        with mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=fake_inventory):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "portrait badhandv4 dramatic light",
                }
            )

        self.assertEqual(normalized.prompt, "portrait embedding:badhandv4.pt dramatic light")
        self.assertIn("PROMPT_EMBEDDING_DETECTED", normalized.prompt_warning_codes)
        self.assertTrue(normalized.prompt_semantics["features"]["embeddings_textual_inversion"])
        self.assertEqual(normalized.prompt_semantics["embeddings"][0]["canonical_token"], "embedding:badhandv4.pt")
        self.assertTrue(normalized.prompt_semantics["embeddings"][0]["exists"])

    def test_normalize_txt2img_request_clears_text_encoder_for_sd15(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "profile": "sd15",
                "text_encoder_name": "Qwen2.5-VL.safetensors",
            }
        )

        self.assertEqual(normalized.text_encoder_name, "")

    def test_normalize_txt2img_request_clears_text_encoder_for_sdxl_family(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "fashion editorial",
                "profile": "sdxl",
                "text_encoder_name": "Automatic",
            }
        )

        self.assertEqual(normalized.text_encoder_name, "")

    def test_normalize_txt2img_request_accepts_host_default_sentinels_on_live_inventory(self) -> None:
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

        with mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=fake_inventory):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "city skyline",
                    "profile": "sd15",
                    "checkpoint_name": "__host_default__",
                    "vae_name": "Automatic",
                    "text_encoder_name": "Automatic",
                }
            )

        self.assertEqual(normalized.checkpoint_name, "SD15\\dreamshaper.safetensors")
        self.assertEqual(normalized.vae_name, "SD15\\vae-ft-mse-840000.safetensors")
        self.assertEqual(normalized.text_encoder_name, "")

    def test_normalize_txt2img_request_keeps_adetailer_same_checkpoint_sentinel_for_sdxl_host_inventory(self) -> None:
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
            mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=fake_inventory),
            mock.patch("rookieui.services.adetailer.discover_model_inventory", return_value=fake_inventory),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "fashion editorial",
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

    def test_normalize_txt2img_request_accepts_adetailer_diffusion_family_checkpoint_override(self) -> None:
        fake_inventory = ModelInventorySnapshot(
            source="host",
            checkpoints=["SDXL\\realvisxl.safetensors"],
            diffusion_models=["flux\\flux1-dev.safetensors", "lumina\\lumina2.safetensors"],
            vae=["flux_vae.safetensors"],
            text_encoders=["t5xxl.safetensors"],
            loras=["Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors"],
            controlnet=[],
            default_checkpoint="SDXL\\realvisxl.safetensors",
            default_vae="flux_vae.safetensors",
            default_text_encoder="t5xxl.safetensors",
        )

        with (
            mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=fake_inventory),
            mock.patch("rookieui.services.adetailer.discover_model_inventory", return_value=fake_inventory),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "fashion editorial",
                    "profile": "flux",
                    "checkpoint_name": "flux\\flux1-dev.safetensors",
                    "adetailer": {
                        "enabled": True,
                        "units": [
                            {
                                "enabled": True,
                                "detector": "face_yolov8n.pt",
                                "use_checkpoint": True,
                                "checkpoint_name": "flux\\flux1-dev.safetensors",
                            }
                        ],
                    },
                }
            )

        self.assertTrue(normalized.adetailer.units[0].use_checkpoint)
        self.assertEqual(normalized.adetailer.units[0].checkpoint_name, "flux\\flux1-dev.safetensors")

    def test_normalize_txt2img_request_keeps_text_encoder_for_flux_profile(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "fashion editorial",
                "profile": "flux",
                "text_encoder_name": "clip_g.safetensors",
            }
        )

        self.assertEqual(normalized.text_encoder_name, "clip_g.safetensors")

    def test_normalize_txt2img_request_accepts_template_lora_override_for_flux(self) -> None:
        with mock.patch(
            "rookieui.services.txt2img.discover_model_inventory",
            return_value=mock.Mock(
                source="host",
                checkpoints=["SDXL\\realvisxl.safetensors"],
                diffusion_models=["flux\\flux1-dev.safetensors"],
                vae=["flux_vae.safetensors"],
                text_encoders=["clip_l.safetensors", "t5xxl_fp16.safetensors"],
                loras=[
                    "Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors",
                    "Flux\\My-Custom-Flux-LoRA.safetensors",
                ],
                default_checkpoint="SDXL\\realvisxl.safetensors",
                default_vae="flux_vae.safetensors",
                default_text_encoder="clip_l.safetensors",
                controlnet=[],
            ),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "fashion editorial",
                    "profile": "flux",
                    "checkpoint_name": "flux/flux1-dev.safetensors",
                    "template_lora_name": "Flux/My-Custom-Flux-LoRA.safetensors",
                }
            )

        self.assertEqual(normalized.template_lora_name, "Flux\\My-Custom-Flux-LoRA.safetensors")

    def test_normalize_txt2img_request_uses_profile_aware_text_encoder_default_for_zit(self) -> None:
        with mock.patch(
            "rookieui.services.txt2img.discover_model_inventory",
            return_value=mock.Mock(
                source="host",
                checkpoints=["SDXL\\realvisxl.safetensors"],
                diffusion_models=["lumina2.safetensors", "ZIT\\zImageTurboNSFW_21BF16AIO.safetensors"],
                vae=["qwen_image_vae.safetensors", "lumina_vae.safetensors"],
                text_encoders=["QwenImageTEModel_.safetensors", "LuminaTEModel.safetensors"],
                loras=[],
                default_checkpoint="SDXL\\realvisxl.safetensors",
                default_vae="qwen_image_vae.safetensors",
                default_text_encoder="QwenImageTEModel_.safetensors",
                controlnet=[],
            ),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "fashion editorial",
                    "profile": "zit",
                    "checkpoint_name": "ZIT\\zImageTurboNSFW_21BF16AIO.safetensors",
                    "text_encoder_name": "",
                    "vae_name": "",
                }
            )

        self.assertEqual(normalized.text_encoder_name, "LuminaTEModel.safetensors")
        self.assertEqual(normalized.vae_name, "lumina_vae.safetensors")

    def test_normalize_txt2img_request_uses_profile_aware_text_encoder_default_for_ernie_image(self) -> None:
        with mock.patch(
            "rookieui.services.txt2img.discover_model_inventory",
            return_value=mock.Mock(
                source="host",
                checkpoints=["SDXL\\realvisxl.safetensors"],
                diffusion_models=["ernie\\ernie-image.safetensors"],
                vae=["flux2-vae.safetensors", "ernie_vae.safetensors"],
                text_encoders=[
                    "Ministral3_3B_fp16.safetensors",
                    "ernie-image-prompt-enhancer.safetensors",
                    "QwenImageTEModel_.safetensors",
                ],
                loras=[],
                default_checkpoint="SDXL\\realvisxl.safetensors",
                default_vae="qwen_image_vae.safetensors",
                default_text_encoder="QwenImageTEModel_.safetensors",
                controlnet=[],
            ),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "fashion editorial",
                    "profile": "ernie_image",
                    "checkpoint_name": "ernie/ernie-image.safetensors",
                    "text_encoder_name": "",
                    "vae_name": "",
                }
            )

        self.assertEqual(normalized.text_encoder_name, "Ministral3_3B_fp16.safetensors")
        self.assertEqual(normalized.aux_text_encoder_name, "ernie-image-prompt-enhancer.safetensors")
        self.assertEqual(normalized.vae_name, "flux2-vae.safetensors")

    def test_normalize_txt2img_request_uses_profile_aware_selectors_for_official_non_sd_templates(self) -> None:
        mocked_inventory = mock.Mock(
            source="host",
            checkpoints=["SDXL\\realvisxl.safetensors"],
            diffusion_models=[
                "flux\\flux1-dev.safetensors",
                "flux\\flux1-krea-dev_fp8_scaled.safetensors",
                "flux\\flux2_dev_fp8mixed.safetensors",
                "qwen\\qwen_image_2512_fp8_e4m3fn.safetensors",
                "klein\\flux-2-klein-4b.safetensors",
                "klein\\flux-2-klein-base-4b.safetensors",
                "klein\\flux-2-klein-9b-fp8.safetensors",
                "klein\\flux-2-klein-base-9b-fp8.safetensors",
                "anima\\anima-preview3-base.safetensors",
                "chroma\\Chroma1-HD-fp8mixed.safetensors",
                "ernie\\ernie-image.safetensors",
                "ernie\\ernie-image-turbo.safetensors",
                "hidream\\hidream_i1_dev_fp8.safetensors",
                "hidream\\hidream_i1_fast_fp8.safetensors",
                "hidream\\hidream_i1_full_fp8.safetensors",
                "longcat\\longcat_image_bf16.safetensors",
                "zimage\\z_image_bf16.safetensors",
                "zimage\\z_image_turbo_bf16.safetensors",
            ],
            vae=[
                "qwen_image_vae.safetensors",
                "ae.safetensors",
                "flux2-vae.safetensors",
                "full_encoder_small_decoder.safetensors",
            ],
            text_encoders=[
                "clip_l.safetensors",
                "clip_l_hidream.safetensors",
                "clip_g_hidream.safetensors",
                "ernie-image-prompt-enhancer.safetensors",
                "llama_3.1_8b_instruct_fp8_scaled.safetensors",
                "ministral-3-3b.safetensors",
                "mistral_3_small_flux2_bf16.safetensors",
                "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                "qwen_3_06b_base.safetensors",
                "qwen_3_4b.safetensors",
                "qwen_3_8b_fp8mixed.safetensors",
                "t5xxl_fp16.safetensors",
                "t5xxl_fp8_e4m3fn_scaled.safetensors",
            ],
            loras=[
                "Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors",
                "Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors",
            ],
            default_checkpoint="SDXL\\realvisxl.safetensors",
            default_vae="qwen_image_vae.safetensors",
            default_text_encoder="qwen_2.5_vl_7b_fp8_scaled.safetensors",
            controlnet=[],
        )
        expectations = {
            "flux": ("flux\\flux1-dev.safetensors", "clip_l.safetensors|t5xxl_fp16.safetensors", "ae.safetensors"),
            "flux_krea_dev": (
                "flux\\flux1-krea-dev_fp8_scaled.safetensors",
                "clip_l.safetensors|t5xxl_fp16.safetensors",
                "ae.safetensors",
            ),
            "flux2_dev": (
                "flux\\flux2_dev_fp8mixed.safetensors",
                "mistral_3_small_flux2_bf16.safetensors",
                "full_encoder_small_decoder.safetensors",
            ),
            "qwen_image": (
                "qwen\\qwen_image_2512_fp8_e4m3fn.safetensors",
                "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                "qwen_image_vae.safetensors",
            ),
            "klein_4b_distilled": ("klein\\flux-2-klein-4b.safetensors", "qwen_3_4b.safetensors", "flux2-vae.safetensors"),
            "klein_4b": ("klein\\flux-2-klein-base-4b.safetensors", "qwen_3_4b.safetensors", "flux2-vae.safetensors"),
            "klein_9b_distilled": (
                "klein\\flux-2-klein-9b-fp8.safetensors",
                "qwen_3_8b_fp8mixed.safetensors",
                "full_encoder_small_decoder.safetensors",
            ),
            "klein_9b": (
                "klein\\flux-2-klein-base-9b-fp8.safetensors",
                "qwen_3_8b_fp8mixed.safetensors",
                "full_encoder_small_decoder.safetensors",
            ),
            "anima": ("anima\\anima-preview3-base.safetensors", "qwen_3_06b_base.safetensors", "qwen_image_vae.safetensors"),
            "chroma": ("chroma\\Chroma1-HD-fp8mixed.safetensors", "t5xxl_fp8_e4m3fn_scaled.safetensors", "ae.safetensors"),
            "ernie_image": ("ernie\\ernie-image.safetensors", "ministral-3-3b.safetensors", "flux2-vae.safetensors"),
            "ernie_image_turbo": ("ernie\\ernie-image-turbo.safetensors", "ministral-3-3b.safetensors", "flux2-vae.safetensors"),
            "hidream_i1_dev_fp8": (
                "hidream\\hidream_i1_dev_fp8.safetensors",
                "clip_l_hidream.safetensors|clip_g_hidream.safetensors|"
                "t5xxl_fp8_e4m3fn_scaled.safetensors|llama_3.1_8b_instruct_fp8_scaled.safetensors",
                "ae.safetensors",
            ),
            "hidream_i1_fast": (
                "hidream\\hidream_i1_fast_fp8.safetensors",
                "clip_l_hidream.safetensors|clip_g_hidream.safetensors|"
                "t5xxl_fp8_e4m3fn_scaled.safetensors|llama_3.1_8b_instruct_fp8_scaled.safetensors",
                "ae.safetensors",
            ),
            "hidream_i1_full": (
                "hidream\\hidream_i1_full_fp8.safetensors",
                "clip_l_hidream.safetensors|clip_g_hidream.safetensors|"
                "t5xxl_fp8_e4m3fn_scaled.safetensors|llama_3.1_8b_instruct_fp8_scaled.safetensors",
                "ae.safetensors",
            ),
            "longcat_image": ("longcat\\longcat_image_bf16.safetensors", "qwen_2.5_vl_7b_fp8_scaled.safetensors", "ae.safetensors"),
            "z_image": ("zimage\\z_image_bf16.safetensors", "qwen_3_4b.safetensors", "ae.safetensors"),
            "z_image_turbo": ("zimage\\z_image_turbo_bf16.safetensors", "qwen_3_4b.safetensors", "ae.safetensors"),
        }
        with mock.patch(
            "rookieui.services.txt2img.discover_model_inventory",
            return_value=mocked_inventory,
        ):
            for profile_id, (expected_checkpoint, expected_text_encoder, expected_vae) in expectations.items():
                with self.subTest(profile_id=profile_id):
                    normalized = normalize_txt2img_request(
                        {
                            "prompt": "matrix smoke",
                            "profile": profile_id,
                            "checkpoint_name": expected_checkpoint,
                            "text_encoder_name": "",
                            "vae_name": "",
                        }
                    )
                    self.assertEqual(normalized.checkpoint_name, expected_checkpoint)
                    self.assertEqual(normalized.text_encoder_name, expected_text_encoder)
                    self.assertEqual(normalized.vae_name, expected_vae)
                    if profile_id == "flux":
                        self.assertEqual(normalized.template_lora_name, "Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors")
                    if profile_id == "flux_krea_dev":
                        self.assertEqual(normalized.template_lora_name, "")
                    if profile_id == "flux2_dev":
                        self.assertEqual(normalized.template_lora_name, "Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors")
                        self.assertEqual(normalized.flux_guidance, 4.0)
                    if profile_id in {"ernie_image", "ernie_image_turbo"}:
                        self.assertEqual(normalized.aux_text_encoder_name, "ernie-image-prompt-enhancer.safetensors")
                    if profile_id == "ernie_image":
                        self.assertEqual(normalized.steps, 20)
                    if profile_id == "qwen_image":
                        self.assertEqual(
                            normalized.template_lora_name,
                            "Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors",
                        )
                        self.assertEqual(normalized.steps, 50)
                        self.assertEqual(normalized.cfg_scale, 4.0)
                        self.assertEqual(normalized.shift, 3.1)

    def test_normalize_txt2img_request_accepts_template_lora_override_for_qwen_image(self) -> None:
        mocked_inventory = mock.Mock(
            source="host",
            checkpoints=["SDXL\\realvisxl.safetensors"],
            diffusion_models=["qwen\\qwen_image_2512_fp8_e4m3fn.safetensors"],
            vae=["qwen_image_vae.safetensors"],
            text_encoders=["qwen_2.5_vl_7b_fp8_scaled.safetensors"],
            loras=[
                "Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors",
                "Qwen-image\\My-Custom-Qwen-Image-LoRA.safetensors",
            ],
            default_checkpoint="SDXL\\realvisxl.safetensors",
            default_vae="qwen_image_vae.safetensors",
            default_text_encoder="qwen_2.5_vl_7b_fp8_scaled.safetensors",
            controlnet=[],
        )

        with mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=mocked_inventory):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "matrix smoke",
                    "profile": "qwen_image",
                    "checkpoint_name": "qwen/qwen_image_2512_fp8_e4m3fn.safetensors",
                    "text_encoder_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                    "vae_name": "qwen_image_vae.safetensors",
                    "template_lora_name": "Qwen-image/My-Custom-Qwen-Image-LoRA.safetensors",
                }
            )

        self.assertEqual(
            normalized.template_lora_name,
            "Qwen-image\\My-Custom-Qwen-Image-LoRA.safetensors",
        )

    def test_missing_official_template_lora_warns_and_allows_txt2img_generation(self) -> None:
        cases = [
            (
                "flux",
                "Flux\\flux1-dev.safetensors",
                "clip_l.safetensors|t5xxl_fp8_e4m3fn.safetensors",
                "ae.safetensors",
            ),
            (
                "qwen_image",
                "qwen\\qwen_image_2512_fp8_e4m3fn.safetensors",
                "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                "qwen_image_vae.safetensors",
            ),
        ]

        for profile_id, checkpoint_name, text_encoder_name, vae_name in cases:
            with self.subTest(profile_id=profile_id):
                mocked_inventory = mock.Mock(
                    source="host",
                    checkpoints=["SDXL\\realvisxl.safetensors"],
                    diffusion_models=[checkpoint_name],
                    vae=[vae_name],
                    text_encoders=text_encoder_name.split("|"),
                    loras=[],
                    default_checkpoint="SDXL\\realvisxl.safetensors",
                    default_vae=vae_name,
                    default_text_encoder=text_encoder_name.split("|")[0],
                    controlnet=[],
                )

                with mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=mocked_inventory):
                    normalized = normalize_txt2img_request(
                        {
                            "prompt": "matrix smoke",
                            "profile": profile_id,
                            "checkpoint_name": checkpoint_name,
                            "text_encoder_name": "",
                            "vae_name": vae_name,
                        }
                    )

                self.assertEqual(normalized.template_lora_name, "")
                self.assertIn("TEMPLATE_LORA_MISSING", normalized.prompt_warning_codes)
                warning_text = "\n".join(normalized.prompt_warnings)
                self.assertIn("<lora:model_name:1>", warning_text)
                workflow = translate_txt2img_request(normalized).to_payload()["workflow"]
                lora_nodes = [node for node in workflow.values() if node["class_type"] == "LoraLoaderModelOnly"]
                self.assertEqual(lora_nodes, [])

    def test_translate_txt2img_request_chains_inline_and_selected_loras(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "city skyline <lora:detail_tweaker.safetensors:0.8> <lora:cinematic_helper.safetensors:0.5>",
                "lora_name": "hero_boost.safetensors",
                "lora_strength_model": 0.7,
                "lora_strength_clip": 0.6,
            }
        )

        result = translate_txt2img_request(normalized).to_payload()

        self.assertEqual(result["workflow"]["90"]["class_type"], "LoraLoader")
        self.assertEqual(result["workflow"]["90"]["inputs"]["lora_name"], "detail_tweaker.safetensors")
        self.assertEqual(result["workflow"]["91"]["inputs"]["lora_name"], "cinematic_helper.safetensors")
        self.assertEqual(result["workflow"]["92"]["inputs"]["lora_name"], "hero_boost.safetensors")
        self.assertEqual(result["workflow"]["5"]["inputs"]["model"], ["92", 0])

    def test_translate_txt2img_request_compiles_prompt_semantics_for_sd15(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "hero AND villain BREAK [calm:chaos:0.4]",
            }
        )

        result = translate_txt2img_request(normalized).to_payload()
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

    def test_translate_txt2img_request_compiles_prompt_semantics_for_sdxl(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "[sunny:storm:0.5] fashion editorial",
                "profile": "pony",
            }
        )

        result = translate_txt2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}
        self.assertIn("RookieUIA1111CLIPTextEncodeSDXL", class_types)
        self.assertIn("ConditioningSetTimestepRange", class_types)

        encoder_nodes = [
            node
            for node in result["workflow"].values()
            if node["class_type"] == "RookieUIA1111CLIPTextEncodeSDXL"
            and str(node["inputs"].get("text_g") or "").strip()
        ]
        self.assertTrue(encoder_nodes)
        self.assertTrue(all(node["inputs"].get("a1111_engine") == "text_only" for node in encoder_nodes))

    def test_translate_txt2img_request_compiles_alternate_prompt_scheduling(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "portrait [warm|cool] light",
                "steps": 4,
            }
        )

        result = translate_txt2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}

        self.assertIn("ConditioningCombine", class_types)
        self.assertIn("ConditioningSetTimestepRange", class_types)

    def test_translate_txt2img_request_passes_canonical_embedding_tokens_to_sd_family_encoder(self) -> None:
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

        with mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=fake_inventory):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "portrait badhandv4 dramatic light",
                }
            )

        result = translate_txt2img_request(normalized).to_payload()
        encoder_nodes = [
            node
            for node in result["workflow"].values()
            if node["class_type"] == "RookieUIA1111CLIPTextEncode"
        ]

        self.assertTrue(encoder_nodes)
        self.assertTrue(
            any(node["inputs"]["text"] == "portrait embedding:badhandv4.pt dramatic light" for node in encoder_nodes)
        )

    def test_translate_txt2img_request_uses_legacy_roll_back_switch(self) -> None:
        with mock.patch.dict("os.environ", {"ROOKIEUI_PROMPT_DSL_LEGACY": "1"}, clear=False):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "hero AND villain BREAK [calm:chaos:0.4]",
                }
            )
            result = translate_txt2img_request(normalized).to_payload()

        class_types = {node["class_type"] for node in result["workflow"].values()}
        self.assertNotIn("ConditioningCombine", class_types)
        self.assertNotIn("ConditioningSetTimestepRange", class_types)
        self.assertIn("PROMPT_LEGACY_FALLBACK_ENABLED", result["normalized_request"]["prompt_warning_codes"])

    def test_translate_txt2img_request_keeps_node_ids_unique_with_hires_and_loras(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "city skyline <lora:detail_tweaker.safetensors:0.8> <lora:cinematic_helper.safetensors:0.5>",
                "lora_name": "hero_boost.safetensors",
                "lora_strength_model": 0.7,
                "lora_strength_clip": 0.6,
                "hires_enabled": True,
                "hires_steps": 12,
                "hires_scale": 1.8,
                "hires_denoise": 0.4,
            }
        )

        result = translate_txt2img_request(normalized).to_payload()
        workflow = result["workflow"]

        self.assertEqual(len(workflow), len(set(workflow.keys())))
        self.assertEqual(workflow["90"]["class_type"], "LoraLoader")
        self.assertEqual(workflow["91"]["class_type"], "LoraLoader")
        self.assertEqual(workflow["92"]["class_type"], "LoraLoader")
        self.assertEqual(workflow["7"]["class_type"], "KSampler")
        self.assertEqual(workflow["7"]["inputs"]["model"], ["92", 0])

    def test_normalize_txt2img_request_uses_sdxl_profile_defaults(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "studio portrait",
                "profile": "illustrious",
            }
        )

        self.assertEqual(request.base_family, "sdxl")
        self.assertEqual(request.width, 1024)
        self.assertEqual(request.height, 1024)
        self.assertEqual(request.scheduler_name, "karras")
        self.assertEqual(request.clip_skip, 1)

    def test_normalize_txt2img_request_preserves_multiline_prompt_and_normalizes_selectors(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "  masterpiece\r\ncity skyline\x00  ",
                "negative_prompt": "  blurry\r\nlowres  ",
                "checkpoint_name": "sdxl\\pony\\pony.safetensors",
            }
        )

        self.assertEqual(request.prompt, "masterpiece\ncity skyline")
        self.assertEqual(request.negative_prompt, "blurry\nlowres")
        self.assertEqual(request.checkpoint_name, "sdxl/pony/pony.safetensors")

    def test_normalize_txt2img_request_resolves_host_checkpoint_selector(self) -> None:
        with mock.patch(
            "rookieui.services.txt2img.discover_model_inventory",
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
            request = normalize_txt2img_request(
                {
                    "prompt": "city skyline",
                    "checkpoint_name": "SD15/beautifulRealistic_v40.safetensors",
                }
            )

        self.assertEqual(request.checkpoint_name, "SD15\\beautifulRealistic_v40.safetensors")

    def test_normalize_txt2img_request_resolves_profile_mapped_diffusion_model_selector(self) -> None:
        with mock.patch(
            "rookieui.services.txt2img.discover_model_inventory",
            return_value=mock.Mock(
                source="host",
                checkpoints=["SDXL\\realvisxl.safetensors"],
                diffusion_models=["flux\\flux1-dev.safetensors"],
                vae=["flux_vae.safetensors"],
                text_encoders=["clip_l.safetensors", "t5xxl_fp16.safetensors", "flux_text_encoder.safetensors"],
                loras=["Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors"],
                default_checkpoint="SDXL\\realvisxl.safetensors",
                default_vae="flux_vae.safetensors",
                default_text_encoder="clip_l.safetensors",
                controlnet=[],
            ),
        ):
            request = normalize_txt2img_request(
                {
                    "prompt": "fashion editorial",
                    "profile": "flux",
                    "checkpoint_name": "flux/flux1-dev.safetensors",
                }
            )

        self.assertEqual(request.checkpoint_name, "flux\\flux1-dev.safetensors")
        self.assertEqual(request.primary_model_category, "diffusion_models")
        self.assertEqual(request.vae_name, "flux_vae.safetensors")
        self.assertEqual(request.text_encoder_name, "clip_l.safetensors|t5xxl_fp16.safetensors")
        self.assertEqual(request.template_lora_name, "Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors")

    def test_translate_txt2img_request_uses_unet_loader_for_diffusion_model_category(self) -> None:
        with mock.patch(
            "rookieui.services.txt2img.discover_model_inventory",
            return_value=mock.Mock(
                source="host",
                checkpoints=["SDXL\\realvisxl.safetensors"],
                diffusion_models=["flux\\flux1-dev.safetensors"],
                vae=["flux_vae.safetensors"],
                text_encoders=["clip_l.safetensors", "t5xxl_fp16.safetensors"],
                loras=["Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors"],
                default_checkpoint="SDXL\\realvisxl.safetensors",
                default_vae="flux_vae.safetensors",
                default_text_encoder="clip_l.safetensors",
                controlnet=[],
            ),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "fashion editorial",
                    "profile": "flux",
                    "checkpoint_name": "flux/flux1-dev.safetensors",
                    "vae_name": "flux_vae.safetensors",
                }
            )

        result = translate_txt2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}
        self.assertIn("UNETLoader", class_types)
        self.assertIn("DualCLIPLoader", class_types)
        self.assertIn("VAELoader", class_types)
        self.assertIn("LoraLoaderModelOnly", class_types)
        self.assertIn("CLIPTextEncode", class_types)
        self.assertIn("ConditioningZeroOut", class_types)
        self.assertNotIn("RookieUIA1111CLIPTextEncode", class_types)
        self.assertNotIn("CLIPTextEncodeSDXL", class_types)
        self.assertNotIn("CheckpointLoaderSimple", class_types)

    def test_translate_txt2img_request_builds_flux_krea_dev_without_template_lora(self) -> None:
        with mock.patch(
            "rookieui.services.txt2img.discover_model_inventory",
            return_value=mock.Mock(
                source="host",
                checkpoints=["SDXL\\realvisxl.safetensors"],
                diffusion_models=["flux\\flux1-krea-dev_fp8_scaled.safetensors"],
                vae=["ae.safetensors"],
                text_encoders=["clip_l.safetensors", "t5xxl_fp16.safetensors"],
                loras=["Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors"],
                default_checkpoint="SDXL\\realvisxl.safetensors",
                default_vae="ae.safetensors",
                default_text_encoder="clip_l.safetensors",
                controlnet=[],
            ),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "fashion editorial",
                    "profile": "flux_krea_dev",
                    "checkpoint_name": "",
                    "vae_name": "",
                    "text_encoder_name": "",
                }
            )

        result = translate_txt2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}
        sampler_node = next(node for node in result["workflow"].values() if node["class_type"] == "KSampler")

        self.assertEqual(result["workflow_kind"], "txt2img-flux_krea_dev")
        self.assertEqual(normalized.checkpoint_name, "flux\\flux1-krea-dev_fp8_scaled.safetensors")
        self.assertEqual(normalized.template_lora_name, "")
        self.assertIn("DualCLIPLoader", class_types)
        self.assertIn("EmptySD3LatentImage", class_types)
        self.assertNotIn("LoraLoaderModelOnly", class_types)
        self.assertEqual(sampler_node["inputs"]["steps"], 20)
        self.assertEqual(sampler_node["inputs"]["cfg"], 1.0)

    def test_translate_txt2img_request_builds_flux2_dev_custom_sampler_graph(self) -> None:
        with mock.patch(
            "rookieui.services.txt2img.discover_model_inventory",
            return_value=mock.Mock(
                source="host",
                checkpoints=["SDXL\\realvisxl.safetensors"],
                diffusion_models=["flux\\flux2_dev_fp8mixed.safetensors"],
                vae=["full_encoder_small_decoder.safetensors"],
                text_encoders=["mistral_3_small_flux2_bf16.safetensors"],
                loras=["Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors"],
                default_checkpoint="SDXL\\realvisxl.safetensors",
                default_vae="full_encoder_small_decoder.safetensors",
                default_text_encoder="mistral_3_small_flux2_bf16.safetensors",
                controlnet=[],
            ),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "fashion editorial",
                    "profile": "flux2_dev",
                    "checkpoint_name": "",
                    "vae_name": "",
                    "text_encoder_name": "",
                }
            )

        result = translate_txt2img_request(normalized).to_payload()
        workflow = result["workflow"]
        class_types = {node["class_type"] for node in workflow.values()}
        lora_node = next(node for node in workflow.values() if node["class_type"] == "LoraLoaderModelOnly")
        clip_node = next(node for node in workflow.values() if node["class_type"] == "CLIPLoader")
        guidance_node = next(node for node in workflow.values() if node["class_type"] == "FluxGuidance")
        scheduler_node = next(node for node in workflow.values() if node["class_type"] == "Flux2Scheduler")
        latent_node = next(node for node in workflow.values() if node["class_type"] == "EmptyFlux2LatentImage")

        self.assertEqual(result["workflow_kind"], "txt2img-flux2_dev")
        self.assertEqual(normalized.checkpoint_name, "flux\\flux2_dev_fp8mixed.safetensors")
        self.assertEqual(normalized.text_encoder_name, "mistral_3_small_flux2_bf16.safetensors")
        self.assertEqual(normalized.vae_name, "full_encoder_small_decoder.safetensors")
        self.assertEqual(normalized.template_lora_name, "Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors")
        self.assertIn("BasicGuider", class_types)
        self.assertIn("RandomNoise", class_types)
        self.assertIn("KSamplerSelect", class_types)
        self.assertIn("SamplerCustomAdvanced", class_types)
        self.assertNotIn("KSampler", class_types)
        self.assertEqual(lora_node["inputs"]["lora_name"], "Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors")
        self.assertEqual(clip_node["inputs"]["type"], "flux2")
        self.assertEqual(guidance_node["inputs"]["guidance"], 4.0)
        self.assertEqual(scheduler_node["inputs"]["steps"], 20)
        self.assertEqual(latent_node["inputs"]["width"], 1024)
        self.assertEqual(latent_node["inputs"]["height"], 1024)

    def test_translate_txt2img_request_appends_inline_lora_after_template_owned_lora_for_flux(self) -> None:
        with mock.patch(
            "rookieui.services.txt2img.discover_model_inventory",
            return_value=mock.Mock(
                source="host",
                checkpoints=["SDXL\\realvisxl.safetensors"],
                diffusion_models=["flux\\flux1-dev.safetensors"],
                vae=["flux_vae.safetensors"],
                text_encoders=["clip_l.safetensors", "t5xxl_fp16.safetensors"],
                loras=[
                    "Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors",
                    "Flux\\CinematicBoost.safetensors",
                ],
                default_checkpoint="SDXL\\realvisxl.safetensors",
                default_vae="flux_vae.safetensors",
                default_text_encoder="clip_l.safetensors",
                controlnet=[],
            ),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "fashion editorial <lora:Flux/CinematicBoost.safetensors:0.55>",
                    "profile": "flux",
                    "checkpoint_name": "flux/flux1-dev.safetensors",
                    "vae_name": "flux_vae.safetensors",
                }
            )

        result = translate_txt2img_request(normalized).to_payload()
        workflow = result["workflow"]
        lora_nodes = {
            node_id: node for node_id, node in workflow.items() if node["class_type"] == "LoraLoaderModelOnly"
        }

        self.assertEqual(len(lora_nodes), 2)
        template_node_id = next(
            node_id
            for node_id, node in lora_nodes.items()
            if node["inputs"]["lora_name"] == "Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors"
        )
        inline_node_id = next(
            node_id
            for node_id, node in lora_nodes.items()
            if node["inputs"]["lora_name"] == "Flux\\CinematicBoost.safetensors"
        )
        self.assertEqual(lora_nodes[template_node_id]["inputs"]["model"], ["1", 0])
        self.assertEqual(lora_nodes[inline_node_id]["inputs"]["model"], [template_node_id, 0])
        self.assertEqual(lora_nodes[inline_node_id]["inputs"]["strength_model"], 0.55)
        sampler_node = next(node for node in workflow.values() if node["class_type"] == "KSampler")
        self.assertEqual(sampler_node["inputs"]["model"], [inline_node_id, 0])

    def test_normalize_txt2img_request_warns_when_non_sd_inline_lora_clip_strength_drifts(self) -> None:
        with mock.patch(
            "rookieui.services.txt2img.discover_model_inventory",
            return_value=mock.Mock(
                source="host",
                checkpoints=["SDXL\\realvisxl.safetensors"],
                diffusion_models=["flux\\flux1-dev.safetensors"],
                vae=["flux_vae.safetensors"],
                text_encoders=["clip_l.safetensors", "t5xxl_fp16.safetensors"],
                loras=[
                    "Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors",
                    "Flux\\CinematicBoost.safetensors",
                ],
                default_checkpoint="SDXL\\realvisxl.safetensors",
                default_vae="flux_vae.safetensors",
                default_text_encoder="clip_l.safetensors",
                controlnet=[],
            ),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "fashion editorial <lora:Flux/CinematicBoost.safetensors:0.55:0.8>",
                    "profile": "flux",
                    "checkpoint_name": "flux/flux1-dev.safetensors",
                    "vae_name": "flux_vae.safetensors",
                }
            )

        self.assertIn("PROMPT_NON_SD_INLINE_LORA_CLIP_STRENGTH_IGNORED", normalized.prompt_warning_codes)
        self.assertTrue(
            any("model-only" in warning.lower() and "CinematicBoost".lower() in warning.lower() for warning in normalized.prompt_warnings)
        )

    def test_translate_txt2img_request_uses_official_prompt_enhancement_chain_for_ernie_image(self) -> None:
        with mock.patch(
            "rookieui.services.txt2img.discover_model_inventory",
            return_value=mock.Mock(
                source="host",
                checkpoints=["SDXL\\realvisxl.safetensors"],
                diffusion_models=["ernie\\ernie-image.safetensors"],
                vae=["flux2-vae.safetensors"],
                text_encoders=["Ministral3_3B_fp16.safetensors", "ernie-image-prompt-enhancer.safetensors"],
                loras=[],
                default_checkpoint="SDXL\\realvisxl.safetensors",
                default_vae="flux2-vae.safetensors",
                default_text_encoder="Ministral3_3B_fp16.safetensors",
                controlnet=[],
            ),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "fashion editorial",
                    "profile": "ernie_image",
                    "checkpoint_name": "ernie/ernie-image.safetensors",
                    "text_encoder_name": "Ministral3_3B_fp16.safetensors",
                    "vae_name": "flux2-vae.safetensors",
                }
            )

        result = translate_txt2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}
        self.assertEqual(result["workflow_kind"], "txt2img-ernie_image")
        self.assertIn("UNETLoader", class_types)
        self.assertIn("CLIPLoader", class_types)
        self.assertIn("VAELoader", class_types)
        self.assertIn("CLIPTextEncode", class_types)
        self.assertIn("TextGenerate", class_types)
        self.assertIn("ComfySwitchNode", class_types)
        self.assertEqual(normalized.aux_text_encoder_name, "ernie-image-prompt-enhancer.safetensors")
        self.assertNotIn("CLIPTextEncodeSDXL", class_types)

    def test_translate_txt2img_request_appends_inline_lora_for_non_template_ernie_builder(self) -> None:
        with mock.patch(
            "rookieui.services.txt2img.discover_model_inventory",
            return_value=mock.Mock(
                source="host",
                checkpoints=["SDXL\\realvisxl.safetensors"],
                diffusion_models=["ernie\\ernie-image.safetensors"],
                vae=["flux2-vae.safetensors"],
                text_encoders=["Ministral3_3B_fp16.safetensors", "ernie-image-prompt-enhancer.safetensors"],
                loras=["Ernie\\PainterlyLift.safetensors"],
                default_checkpoint="SDXL\\realvisxl.safetensors",
                default_vae="flux2-vae.safetensors",
                default_text_encoder="Ministral3_3B_fp16.safetensors",
                controlnet=[],
            ),
        ):
            normalized = normalize_txt2img_request(
                {
                    "prompt": "fashion editorial <lora:Ernie/PainterlyLift.safetensors:0.4>",
                    "profile": "ernie_image",
                    "checkpoint_name": "ernie/ernie-image.safetensors",
                    "text_encoder_name": "Ministral3_3B_fp16.safetensors",
                    "vae_name": "flux2-vae.safetensors",
                }
            )

        result = translate_txt2img_request(normalized).to_payload()
        workflow = result["workflow"]
        lora_node_id, lora_node = next(
            (node_id, node)
            for node_id, node in workflow.items()
            if node["class_type"] == "LoraLoaderModelOnly"
        )
        self.assertEqual(lora_node["inputs"]["model"], ["1", 0])
        self.assertEqual(lora_node["inputs"]["lora_name"], "Ernie\\PainterlyLift.safetensors")
        self.assertEqual(lora_node["inputs"]["strength_model"], 0.4)
        sampler_node = next(node for node in workflow.values() if node["class_type"] == "KSampler")
        self.assertEqual(sampler_node["inputs"]["model"], [lora_node_id, 0])

    def test_normalize_txt2img_request_applies_hires_defaults(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "hires_enabled": True,
            }
        )

        self.assertTrue(request.hires_enabled)
        self.assertEqual(request.hires_scale, 1.5)
        self.assertEqual(request.hires_steps, 14)
        self.assertEqual(request.hires_upscale_method, "bislerp")

    def test_normalize_txt2img_request_accepts_hires_denoise_upper_bound(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "hires_enabled": True,
                "hires_denoise": 1.0,
            }
        )

        self.assertEqual(request.hires_denoise, 1.0)

    def test_normalize_txt2img_request_treats_hires_steps_zero_as_same_as_base_steps(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "city skyline",
                "steps": 24,
                "hires_enabled": True,
                "hires_steps": 0,
            }
        )

        self.assertEqual(request.hires_steps, 24)

    def test_normalize_txt2img_request_does_not_require_hires_values_when_disabled(self) -> None:
        request = normalize_txt2img_request(
            {
                "prompt": "city skyline",
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

    def test_normalize_txt2img_request_still_validates_hires_values_when_enabled(self) -> None:
        with self.assertRaisesRegex(ValueError, "hires_scale must be between"):
            normalize_txt2img_request(
                {
                    "prompt": "city skyline",
                    "hires_enabled": True,
                    "hires_scale": 0.5,
                }
            )

    def test_translate_txt2img_request_builds_sd15_workflow_with_clip_skip_node(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "neon alley",
                "clip_skip": 2,
                "sampler_name": "Euler a",
            }
        )

        result = translate_txt2img_request(normalized).to_payload()

        self.assertEqual(result["workflow_kind"], "txt2img-sd15")
        self.assertEqual(result["workflow"]["2"]["class_type"], "CLIPSetLastLayer")
        self.assertEqual(result["workflow"]["6"]["inputs"]["sampler_name"], "euler_ancestral")
        self.assertEqual(result["workflow"]["6"]["inputs"]["seed"], result["normalized_request"]["execution_seed"])

    def test_translate_txt2img_request_builds_sdxl_workflow(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "fashion editorial",
                "profile": "pony",
            }
        )

        result = translate_txt2img_request(normalized).to_payload()

        self.assertEqual(result["workflow_kind"], "txt2img-sdxl")
        self.assertEqual(result["workflow"]["2"]["class_type"], "RookieUIA1111CLIPTextEncodeSDXL")
        self.assertEqual(result["workflow"]["5"]["inputs"]["scheduler"], "karras")

    def test_translate_txt2img_request_builds_hires_workflow(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "fashion editorial",
                "profile": "sd15",
                "hires_enabled": True,
                "hires_steps": 12,
                "hires_scale": 1.8,
                "hires_denoise": 0.4,
            }
        )

        result = translate_txt2img_request(normalized).to_payload()

        self.assertEqual(result["workflow_kind"], "txt2img-sd15-hires")
        class_types = {node["class_type"] for node in result["workflow"].values()}
        self.assertIn("LatentUpscaleBy", class_types)
        sampler_nodes = [
            node for node in result["workflow"].values() if node["class_type"] == "KSampler"
        ]
        self.assertEqual(len(sampler_nodes), 2)

    def test_translate_txt2img_request_appends_adetailer_refinement_after_base_decode(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "master portrait",
                "negative_prompt": "blur",
                "profile": "sd15",
                "steps": 22,
                "cfg_scale": 6.5,
                "sampler_name": "Euler a",
                "scheduler_name": "normal",
                "adetailer": {
                    "enabled": True,
                    "units": [
                        {
                            "enabled": True,
                            "detector": "face_yolov8n.pt",
                            "prompt": "[SKIP] [SEP] face [PROMPT]",
                            "negative_prompt": "",
                            "confidence": 0.42,
                            "mask_k": 2,
                            "mask_min_ratio": 0.01,
                            "mask_max_ratio": 0.8,
                            "x_offset": 4,
                            "y_offset": -3,
                            "dilate_erode": 6,
                            "mask_blur": 5,
                            "use_steps": True,
                            "steps": 9,
                            "use_cfg_scale": True,
                            "cfg_scale": 8.5,
                            "use_sampler": True,
                            "sampler_name": "DPM++ 2M Karras",
                        }
                    ],
                },
            }
        )

        result = translate_txt2img_request(normalized).to_payload()
        workflow = result["workflow"]
        mask_nodes = [node for node in workflow.values() if node["class_type"] == "RookieUIADetailerDetectMask"]
        sampler_nodes = [node for node in workflow.values() if node["class_type"] == "KSampler"]
        decode_nodes = [(node_id, node) for node_id, node in workflow.items() if node["class_type"] == "VAEDecode"]
        save_nodes = [node for node in workflow.values() if node["class_type"] == "RookieUISaveImageWithMetadata"]
        encode_texts = [
            node["inputs"]["text"]
            for node in workflow.values()
            if node["class_type"] == "RookieUIA1111CLIPTextEncode" and "text" in node["inputs"]
        ]

        self.assertEqual(len(mask_nodes), 1)
        self.assertEqual(mask_nodes[0]["inputs"]["detector"], "face_yolov8n.pt")
        self.assertEqual(mask_nodes[0]["inputs"]["confidence"], 0.42)
        self.assertEqual(mask_nodes[0]["inputs"]["x_offset"], 4)
        self.assertEqual(len(sampler_nodes), 2)
        detailer_sampler = sampler_nodes[-1]
        self.assertEqual(detailer_sampler["inputs"]["steps"], 9)
        self.assertEqual(detailer_sampler["inputs"]["cfg"], 8.5)
        self.assertEqual(detailer_sampler["inputs"]["sampler_name"], "dpmpp_2m")
        self.assertEqual(detailer_sampler["inputs"]["scheduler"], "karras")
        self.assertIn("face master portrait", encode_texts)
        self.assertIn("blur", encode_texts)
        self.assertEqual(save_nodes[0]["inputs"]["images"], [decode_nodes[-1][0], 0])

    def test_translate_txt2img_request_uses_rookieui_a1111_encode_for_sd15_attention_prompt(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "portrait [soft light]",
            }
        )

        result = translate_txt2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}

        self.assertIn("RookieUIA1111CLIPTextEncode", class_types)

    def test_translate_txt2img_request_ignores_adetailer_none_detector_units(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "master portrait",
                "adetailer": {
                    "enabled": True,
                    "units": [{"enabled": True, "detector": "None"}],
                },
            }
        )

        result = translate_txt2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}

        self.assertNotIn("RookieUIADetailerDetectMask", class_types)
        self.assertEqual(
            len([node for node in result["workflow"].values() if node["class_type"] == "KSampler"]),
            1,
        )

    def test_txt2img_route_returns_translation_payload(self) -> None:
        response = asyncio.run(
            routes.txt2img(
                _FakeJsonRequest(
                    {
                        "prompt": "forest shrine",
                        "profile": "sd15",
                        "scheduler_name": "normal",
                        "dry_run": True,
                    }
                )
            )
        )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["workflow_kind"], "txt2img-sd15")
        self.assertIn("normalized_request", response["payload"])
        self.assertEqual(response["payload"]["normalized_request"]["dtype_profile"], "automatic")
        self.assertEqual(response["payload"]["submission"]["mode"], "dry-run")

    def test_txt2img_route_accepts_full_frontend_submit_payload(self) -> None:
        response = asyncio.run(
            routes.txt2img(
                _FakeJsonRequest(
                    {
                        "prompt": "forest shrine",
                        "negative_prompt": "low quality",
                        "profile": "sd15",
                        "dtype_profile": "Automatic",
                        "checkpoint_name": "__host_default__",
                        "vae_name": "Automatic",
                        "text_encoder_name": "Automatic",
                        "template_lora_name": "",
                        "lora_name": "",
                        "lora_strength_model": 1.0,
                        "lora_strength_clip": 1.0,
                        "width": 512,
                        "height": 512,
                        "steps": 20,
                        "cfg_scale": 7.0,
                        "shift": None,
                        "flux_guidance": None,
                        "edit_megapixels": None,
                        "sampler_name": "Euler a",
                        "scheduler_name": "normal",
                        "prompt_enhancement_enabled": None,
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
        self.assertIsNone(normalized["edit_megapixels"])

    def test_txt2img_route_keeps_legacy_truthy_dry_run_string_behavior(self) -> None:
        response = asyncio.run(
            routes.txt2img(
                _FakeJsonRequest(
                    {
                        "prompt": "forest shrine",
                        "dry_run": "force-dry-run",
                    }
                )
            )
        )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["submission"]["mode"], "dry-run")

    def test_txt2img_route_rejects_missing_prompt(self) -> None:
        response = asyncio.run(routes.txt2img(_FakeJsonRequest({"prompt": "   "})))

        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"]["status"], "invalid-request")

    def test_txt2img_route_rejects_invalid_client_id(self) -> None:
        response = asyncio.run(
            routes.txt2img(
                _FakeJsonRequest(
                    {
                        "prompt": "forest shrine",
                        "dry_run": True,
                        "client_id": "browser 1",
                    }
                )
            )
        )

        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"]["status"], "invalid-request")

    def test_txt2img_route_reports_host_unavailable_when_submission_requested(self) -> None:
        response = asyncio.run(routes.txt2img(_FakeJsonRequest({"prompt": "forest shrine"})))

        self.assertEqual(response["status"], 503)
        self.assertEqual(response["payload"]["status"], "host-unavailable")

    def test_txt2img_route_returns_queued_submission_payload(self) -> None:
        submit_mock = mock.AsyncMock(
            return_value={
                "accepted": True,
                "prompt_id": "prompt-123",
                "number": 3,
                "node_errors": {},
            }
        )
        with (
            mock.patch.object(
                routes,
                "_get_prompt_server_for_submission",
                return_value=object(),
            ),
            mock.patch.object(
                routes,
                "submit_prompt_workflow",
                new=submit_mock,
            ),
        ):
            response = asyncio.run(
                routes.txt2img(
                    _FakeJsonRequest(
                        {
                            "prompt": "forest shrine",
                            "profile": "sd15",
                            "client_id": "browser-1",
                        }
                    )
                )
            )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["mode"], "queued")
        self.assertEqual(response["payload"]["submission"]["prompt_id"], "prompt-123")
        submit_kwargs = submit_mock.await_args.kwargs
        self.assertIn("extra_pnginfo", submit_kwargs)
        self.assertEqual(
            submit_kwargs["extra_pnginfo"]["rookieui"]["schema"],
            "rookieui.generation_metadata.v1",
        )
        self.assertEqual(submit_kwargs["extra_pnginfo"]["rookieui"]["surface"], "txt2img")
        self.assertNotIn("parameters", submit_kwargs["extra_pnginfo"])

    def test_txt2img_route_supports_hires_dry_run_payload(self) -> None:
        response = asyncio.run(
            routes.txt2img(
                _FakeJsonRequest(
                    {
                        "prompt": "forest shrine",
                        "dry_run": True,
                        "hires_enabled": True,
                        "hires_steps": 12,
                    }
                )
            )
        )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["payload"]["workflow_kind"], "txt2img-sd15-hires")
