from __future__ import annotations

import asyncio
import unittest
from unittest import mock

from rookieui.api import routes
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

    def test_normalize_txt2img_request_keeps_text_encoder_for_flux_profile(self) -> None:
        normalized = normalize_txt2img_request(
            {
                "prompt": "fashion editorial",
                "profile": "flux",
                "text_encoder_name": "clip_g.safetensors",
            }
        )

        self.assertEqual(normalized.text_encoder_name, "clip_g.safetensors")

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
        self.assertIn("CLIPTextEncodeSDXL", class_types)
        self.assertIn("ConditioningSetTimestepRange", class_types)

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
                vae=["Automatic"],
                text_encoders=["Automatic"],
                loras=[],
                default_checkpoint="SDXL\\realvisxl.safetensors",
                default_vae="Automatic",
                default_text_encoder="Automatic",
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
        self.assertEqual(result["workflow"]["2"]["class_type"], "CLIPTextEncodeSDXL")
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
