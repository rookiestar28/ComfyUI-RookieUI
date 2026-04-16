from __future__ import annotations

import asyncio
import unittest
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

    def test_normalize_txt2img_request_profile_matrix_avoids_qwen_fallback_for_all_non_qwen_diffusion_profiles(self) -> None:
        mocked_inventory = mock.Mock(
            source="host",
            checkpoints=["SDXL\\realvisxl.safetensors"],
            diffusion_models=[
                "flux\\flux1-dev.safetensors",
                "qwen\\qwen-image.safetensors",
                "klein\\flux2_klein.safetensors",
                "lumina\\lumina2.safetensors",
                "zit\\zImageTurboNSFW_21BF16AIO.safetensors",
                "wan\\wan2_2b.safetensors",
                "anima\\animaPencilXL_v500.safetensors",
            ],
            vae=[
                "qwen_image_vae.safetensors",
                "flux_vae.safetensors",
                "klein_vae.safetensors",
                "lumina_vae.safetensors",
                "wan_vae.safetensors",
                "anima_vae.safetensors",
            ],
            text_encoders=[
                "QwenImageTEModel_.safetensors",
                "FluxT5XXL.safetensors",
                "KleinT5XXL.safetensors",
                "LuminaTEModel.safetensors",
                "WanTextEncoder.safetensors",
                "AnimaTextEncoder.safetensors",
            ],
            loras=[],
            default_checkpoint="SDXL\\realvisxl.safetensors",
            default_vae="qwen_image_vae.safetensors",
            default_text_encoder="QwenImageTEModel_.safetensors",
            controlnet=[],
        )
        profiles = ["flux", "qwen_image", "klein", "lumina", "zit", "wan", "anima"]
        checkpoint_by_profile = {
            "flux": "flux\\flux1-dev.safetensors",
            "qwen_image": "qwen\\qwen-image.safetensors",
            "klein": "klein\\flux2_klein.safetensors",
            "lumina": "lumina\\lumina2.safetensors",
            "zit": "zit\\zImageTurboNSFW_21BF16AIO.safetensors",
            "wan": "wan\\wan2_2b.safetensors",
            "anima": "anima\\animaPencilXL_v500.safetensors",
        }
        with mock.patch(
            "rookieui.services.txt2img.discover_model_inventory",
            return_value=mocked_inventory,
        ):
            for profile_id in profiles:
                with self.subTest(profile_id=profile_id):
                    normalized = normalize_txt2img_request(
                        {
                            "prompt": "matrix smoke",
                            "profile": profile_id,
                            "checkpoint_name": checkpoint_by_profile[profile_id],
                            "text_encoder_name": "",
                            "vae_name": "",
                        }
                    )
                    if profile_id == "qwen_image":
                        self.assertIn("qwen", normalized.text_encoder_name.lower())
                        self.assertIn("qwen", normalized.vae_name.lower())
                    else:
                        self.assertNotIn("qwen", normalized.text_encoder_name.lower())
                        self.assertNotIn("qwen", normalized.vae_name.lower())

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
                text_encoders=["flux_text_encoder.safetensors"],
                loras=[],
                default_checkpoint="SDXL\\realvisxl.safetensors",
                default_vae="flux_vae.safetensors",
                default_text_encoder="flux_text_encoder.safetensors",
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
        self.assertEqual(request.text_encoder_name, "flux_text_encoder.safetensors")

    def test_translate_txt2img_request_uses_unet_loader_for_diffusion_model_category(self) -> None:
        with mock.patch(
            "rookieui.services.txt2img.discover_model_inventory",
            return_value=mock.Mock(
                source="host",
                checkpoints=["SDXL\\realvisxl.safetensors"],
                diffusion_models=["flux\\flux1-dev.safetensors"],
                vae=["flux_vae.safetensors"],
                text_encoders=["clip_l.safetensors"],
                loras=[],
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
                    "text_encoder_name": "clip_l.safetensors",
                    "vae_name": "flux_vae.safetensors",
                }
            )

        result = translate_txt2img_request(normalized).to_payload()
        class_types = {node["class_type"] for node in result["workflow"].values()}
        self.assertIn("UNETLoader", class_types)
        self.assertIn("CLIPLoader", class_types)
        self.assertIn("VAELoader", class_types)
        self.assertIn("CLIPTextEncode", class_types)
        self.assertNotIn("RookieUIA1111CLIPTextEncode", class_types)
        self.assertNotIn("CLIPTextEncodeSDXL", class_types)
        self.assertNotIn("CheckpointLoaderSimple", class_types)

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
        save_nodes = [node for node in workflow.values() if node["class_type"] == "SaveImage"]
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
                        "prompt_id": "prompt-123",
                        "number": 3,
                        "node_errors": {},
                    }
                ),
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
