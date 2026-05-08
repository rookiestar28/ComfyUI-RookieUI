from __future__ import annotations

import contextlib
import io
import sys
import unittest
from unittest import mock

from scripts import run_live_smoke_tests as live_smoke


def _build_semantic_payload(
    enabled_features: tuple[str, ...],
    *,
    branch_count: int = 1,
    embeddings: tuple[dict[str, object], ...] = (),
) -> dict[str, object]:
    return {
        "features": {
            feature_name: feature_name in enabled_features
            for feature_name in live_smoke.ALL_PROMPT_FEATURES
        },
        "branches": [{} for _ in range(branch_count)],
        "embeddings": list(embeddings),
    }


def _build_bootstrap_payload(*, build_fingerprint: str | None = None) -> dict[str, object]:
    return {
        "service": "rookieui",
        "status": "bootstrap-ready",
        "runtime": {
            "shell_version": "0.1.0",
            "build_fingerprint": build_fingerprint or live_smoke._LOCAL_RUNTIME_BUILD_FINGERPRINT,
        },
        "routes": [],
    }


class LiveSmokeFreshnessTests(unittest.TestCase):
    def test_normalize_base_url_keeps_direct_route_mode_unprefixed(self) -> None:
        self.assertEqual(
            live_smoke._normalize_base_url("http://127.0.0.1:8188/", route_mode="direct"),
            "http://127.0.0.1:8188",
        )

    def test_normalize_base_url_applies_hosted_api_route_mode_once(self) -> None:
        self.assertEqual(
            live_smoke._normalize_base_url("http://127.0.0.1:8188/", route_mode="hosted-api"),
            "http://127.0.0.1:8188/api",
        )
        self.assertEqual(
            live_smoke._normalize_base_url("http://127.0.0.1:8188/api/", route_mode="hosted-api"),
            "http://127.0.0.1:8188/api",
        )

    def test_parser_accepts_explicit_live_route_mode(self) -> None:
        args = live_smoke._build_parser().parse_args(["--route-mode", "hosted-api"])

        self.assertEqual(args.route_mode, "hosted-api")

    def test_validate_live_host_freshness_reports_build_fingerprint_drift(self) -> None:
        errors = live_smoke._validate_live_host_freshness(
            live_smoke.LiveHostFreshnessContext(
                host_build_fingerprint="sha256:stale-host",
                local_build_fingerprint=live_smoke._LOCAL_RUNTIME_BUILD_FINGERPRINT,
            )
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("sha256:stale-host", errors[0])
        self.assertIn(live_smoke._LOCAL_RUNTIME_BUILD_FINGERPRINT, errors[0])

    def test_main_report_only_returns_zero_on_stale_host_build_fingerprint(self) -> None:
        with (
            mock.patch.object(
                sys,
                "argv",
                ["run_live_smoke_tests.py", "--report-only"],
            ),
            mock.patch.object(
                live_smoke,
                "_load_bootstrap_payload",
                return_value=_build_bootstrap_payload(build_fingerprint="sha256:stale-host"),
            ),
            mock.patch.object(
                live_smoke,
                "_load_server_payloads",
                side_effect=AssertionError("stale host should stop before loading catalog payloads"),
            ),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = live_smoke.main()

        self.assertEqual(result, 0)

    def test_main_returns_failure_on_stale_host_build_fingerprint_without_report_only(self) -> None:
        with (
            mock.patch.object(
                sys,
                "argv",
                ["run_live_smoke_tests.py"],
            ),
            mock.patch.object(
                live_smoke,
                "_load_bootstrap_payload",
                return_value=_build_bootstrap_payload(build_fingerprint="sha256:stale-host"),
            ),
            mock.patch.object(
                live_smoke,
                "_load_server_payloads",
                side_effect=AssertionError("stale host should stop before loading catalog payloads"),
            ),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = live_smoke.main()

        self.assertEqual(result, 1)


class LiveSmokePromptParityTests(unittest.TestCase):
    def test_default_profiles_for_controlnet_use_sd_family_order(self) -> None:
        self.assertEqual(
            live_smoke._default_profiles_for_mode("controlnet"),
            "sd15,pony,illustrious,noob,sdxl",
        )

    def test_default_profiles_for_adetailer_use_sd_family_order(self) -> None:
        self.assertEqual(
            live_smoke._default_profiles_for_mode("adetailer"),
            "sd15,pony,illustrious,noob,sdxl",
        )

    def test_default_profiles_for_image_edit_use_first_wave_order(self) -> None:
        self.assertEqual(
            live_smoke._default_profiles_for_mode("image-edit"),
            (
                "qwen_image_edit,qwen_image_edit_multi_lora,firered_image_edit,"
                "firered_image_edit_lightning,flux_kontext_dev_edit,flux2_image_edit,"
                "klein_9b_kv_image_edit,longcat_image_edit"
            ),
        )

    def test_default_profiles_for_auxiliary_contracts_is_empty(self) -> None:
        self.assertEqual(live_smoke._default_profiles_for_mode("auxiliary-contracts"), "")

    def test_default_profiles_for_auxiliary_pipelines_is_empty(self) -> None:
        self.assertEqual(live_smoke._default_profiles_for_mode("auxiliary-pipelines"), "")

    def test_default_profiles_for_full_pipeline_is_empty(self) -> None:
        self.assertEqual(live_smoke._default_profiles_for_mode("full-pipeline"), "")

    def test_default_profiles_for_prompt_parity_use_sd_family_order(self) -> None:
        self.assertEqual(
            live_smoke._default_profiles_for_mode("prompt-parity"),
            "sd15,pony,illustrious,noob,sdxl",
        )

    def test_default_profiles_for_catalog_include_official_non_sd_matrix(self) -> None:
        self.assertEqual(
            live_smoke._default_profiles_for_mode("catalog"),
            (
                "anima,chroma,ernie_image,ernie_image_turbo,flux,klein_4b_distilled,klein_4b,"
                "klein_9b_distilled,klein_9b,hidream_i1_dev_fp8,hidream_i1_fast,hidream_i1_full,"
                "longcat_image,qwen_image,z_image,z_image_turbo,qwen_image_edit,"
                "qwen_image_edit_multi_lora,firered_image_edit,firered_image_edit_lightning,"
                "flux_kontext_dev_edit,flux2_image_edit,klein_9b_kv_image_edit,longcat_image_edit"
            ),
        )

    def test_build_prompt_parity_host_context_selects_healthy_sd_family_selectors(self) -> None:
        models_payload = {
            "checkpoints": [
                "SD15\\BravNew.safetensors",
                "SDXL\\Cutie_Slutty_Pony_v20.safetensors",
            ],
            "embeddings": ["EasyNegativeV2.safetensors"],
        }
        capabilities_payload = {
            "prompt_semantics": {
                "contract_version": live_smoke._LOCAL_PROMPT_CONTRACT_VERSION,
            }
        }

        context, errors = live_smoke._build_prompt_parity_host_context(
            models_payload,
            capabilities_payload,
            ["sd15", "pony", "sdxl"],
        )

        self.assertEqual(errors, [])
        assert context is not None
        self.assertEqual(context.sd15_checkpoint, "SD15\\BravNew.safetensors")
        self.assertEqual(context.sdxl_profile, "pony")
        self.assertEqual(context.sdxl_checkpoint, "SDXL\\Cutie_Slutty_Pony_v20.safetensors")
        self.assertEqual(context.embedding_name, "EasyNegativeV2.safetensors")

    def test_validate_prompt_parity_host_sync_reports_contract_drift(self) -> None:
        context = live_smoke.PromptParityHostContext(
            sd15_checkpoint="SD15\\BravNew.safetensors",
            sdxl_profile="pony",
            sdxl_checkpoint="SDXL\\Cutie_Slutty_Pony_v20.safetensors",
            embedding_name="EasyNegativeV2.safetensors",
            host_contract_version="r55-20260411",
            local_contract_version=live_smoke._LOCAL_PROMPT_CONTRACT_VERSION,
        )

        errors = live_smoke._validate_prompt_parity_host_sync(context)

        self.assertEqual(len(errors), 1)
        self.assertIn("host='r55-20260411'", errors[0])
        self.assertIn(f"workspace='{live_smoke._LOCAL_PROMPT_CONTRACT_VERSION}'", errors[0])

    def test_build_prompt_parity_cases_rewrites_embedding_expectations_from_live_inventory(self) -> None:
        context = live_smoke.PromptParityHostContext(
            sd15_checkpoint="SD15\\BravNew.safetensors",
            sdxl_profile="pony",
            sdxl_checkpoint="SDXL\\Cutie_Slutty_Pony_v20.safetensors",
            embedding_name="EasyNegativeV2.safetensors",
            host_contract_version=live_smoke._LOCAL_PROMPT_CONTRACT_VERSION,
            local_contract_version=live_smoke._LOCAL_PROMPT_CONTRACT_VERSION,
        )

        cases = live_smoke._build_prompt_parity_cases(context)
        embedding_case = next(case for case in cases if case.fixture.case_id == "sd15_embedding_bare")
        alternate_case = next(case for case in cases if case.fixture.case_id == "sd15_alternate_schedule")
        long_comma_case = next(case for case in cases if case.fixture.case_id == "sd15_long_comma_chunk")
        sdxl_case = next(
            case
            for case in cases
            if case.fixture.expected_encoder_class == "RookieUIA1111CLIPTextEncodeSDXL"
        )

        self.assertIn("embedding:EasyNegativeV2.safetensors", embedding_case.fixture.expected_cleaned_prompt)
        self.assertEqual(
            embedding_case.fixture.prompt,
            "portrait EasyNegativeV2.safetensors dramatic light",
        )
        self.assertEqual(
            embedding_case.fixture.expected_prompt_embeddings[0].canonical_token,
            "embedding:EasyNegativeV2.safetensors",
        )
        self.assertTrue(long_comma_case.execute)
        self.assertEqual(long_comma_case.fixture.expected_prompt_features, ())
        self.assertIn("alternate_prompt_scheduling", alternate_case.fixture.expected_prompt_features)
        self.assertEqual(sdxl_case.fixture.profile, "pony")
        self.assertIn("embedding:EasyNegativeV2.safetensors", sdxl_case.fixture.expected_cleaned_prompt)
        self.assertTrue(sdxl_case.execute)

    def test_validate_prompt_parity_case_response_detects_stock_encoder_drift(self) -> None:
        fixture = live_smoke._get_fixture("sd15_attention_brackets")
        case = live_smoke.LivePromptParityCase(
            fixture=fixture,
            checkpoint_name="SD15\\BravNew.safetensors",
        )
        response_payload = {
            "workflow_kind": "txt2img-sd15",
            "submission": {"accepted": False, "mode": "dry-run"},
            "normalized_request": {
                "prompt": fixture.expected_cleaned_prompt,
                "negative_prompt": fixture.expected_cleaned_negative_prompt,
                "prompt_warning_codes": list(fixture.expected_warning_codes),
                "prompt_semantics": _build_semantic_payload(fixture.expected_prompt_features),
                "negative_prompt_semantics": _build_semantic_payload(fixture.expected_negative_features),
            },
            "workflow": {
                "1": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": fixture.expected_cleaned_prompt, "clip": ["0", 1]},
                }
            },
        }

        errors = live_smoke._validate_prompt_parity_case_response(case, response_payload)

        self.assertTrue(any("pre-cutover RookieUI deployment" in error for error in errors))

    def test_validate_prompt_parity_case_response_accepts_matching_dry_run_payload(self) -> None:
        fixture = live_smoke._get_fixture("sd15_attention_brackets")
        case = live_smoke.LivePromptParityCase(
            fixture=fixture,
            checkpoint_name="SD15\\BravNew.safetensors",
        )
        response_payload = {
            "workflow_kind": "txt2img-sd15",
            "submission": {"accepted": False, "mode": "dry-run"},
            "normalized_request": {
                "prompt": fixture.expected_cleaned_prompt,
                "negative_prompt": fixture.expected_cleaned_negative_prompt,
                "prompt_warning_codes": list(fixture.expected_warning_codes),
                "prompt_semantics": _build_semantic_payload(fixture.expected_prompt_features),
                "negative_prompt_semantics": _build_semantic_payload(fixture.expected_negative_features),
            },
            "workflow": {
                "1": {
                    "class_type": fixture.expected_encoder_class,
                    "inputs": {"text": fixture.expected_cleaned_prompt, "clip": ["0", 1]},
                }
            },
        }

        errors = live_smoke._validate_prompt_parity_case_response(case, response_payload)

        self.assertEqual(errors, [])

    def test_build_prompt_parity_request_payload_uses_multi_step_for_compiled_cases(self) -> None:
        compiled_case = live_smoke.LivePromptParityCase(
            fixture=live_smoke._get_fixture("sd15_alternate_schedule"),
            checkpoint_name="SD15\\BravNew.safetensors",
        )
        simple_case = live_smoke.LivePromptParityCase(
            fixture=live_smoke._get_fixture("sd15_attention_brackets"),
            checkpoint_name="SD15\\BravNew.safetensors",
        )

        compiled_payload = live_smoke._build_prompt_parity_request_payload(compiled_case)
        simple_payload = live_smoke._build_prompt_parity_request_payload(simple_case)

        self.assertGreaterEqual(compiled_payload["steps"], 4)
        self.assertEqual(simple_payload["steps"], 1)

    def test_main_prompt_parity_report_only_returns_zero_on_contract_drift(self) -> None:
        context = live_smoke.PromptParityHostContext(
            sd15_checkpoint="SD15\\BravNew.safetensors",
            sdxl_profile="pony",
            sdxl_checkpoint="SDXL\\Cutie_Slutty_Pony_v20.safetensors",
            embedding_name=None,
            host_contract_version="r55-20260411",
            local_contract_version=live_smoke._LOCAL_PROMPT_CONTRACT_VERSION,
        )

        with (
            mock.patch.object(
                sys,
                "argv",
                ["run_live_smoke_tests.py", "--validation-mode", "prompt-parity", "--report-only"],
            ),
            mock.patch.object(
                live_smoke,
                "_load_bootstrap_payload",
                return_value=_build_bootstrap_payload(),
            ),
            mock.patch.object(
                live_smoke,
                "_load_server_payloads",
                return_value=({"checkpoints": []}, {"presets": []}),
            ),
            mock.patch.object(
                live_smoke,
                "_load_capabilities_payload",
                return_value={"prompt_semantics": {"contract_version": "r55-20260411"}},
            ),
            mock.patch.object(
                live_smoke,
                "_build_prompt_parity_host_context",
                return_value=(context, []),
            ),
            mock.patch.object(
                live_smoke,
                "_build_prompt_parity_cases",
                return_value=[],
            ),
            mock.patch.object(
                live_smoke,
                "_run_prompt_parity_dry_run_smoke",
                return_value=[],
            ),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = live_smoke.main()

        self.assertEqual(result, 0)


class LiveSmokePromptWorkbenchTests(unittest.TestCase):
    def test_default_profiles_for_prompt_workbench_is_empty(self) -> None:
        self.assertEqual(live_smoke._default_profiles_for_mode("prompt-workbench"), "")

    def test_build_prompt_workbench_host_context_accepts_expected_contract(self) -> None:
        config_payload = {
            "service": "rookieui",
            "status": "ok",
            "contract": {
                "surface": "prompt_tools_config",
                "version": live_smoke._LOCAL_PROMPT_WORKBENCH_CONTRACT_VERSION,
                "route_family": "/rookieui/prompt-tools",
                "state_schema_version": 1,
                "namespaces": list(live_smoke.PROMPT_WORKBENCH_NAMESPACES),
            },
            "config": {
                "language": "en",
                "theme_style": "rookieui_classic",
                "ai_assist": {"instruction_preset": "Write a Stable Diffusion prompt."},
            },
            "language_options": [{"code": "en", "title": "English"}],
            "theme_style_options": [{"id": "rookieui_classic", "title": "RookieUI Classic"}],
            "host_actions": {
                "danbooru_upsample": {
                    "action_id": "danbooru_upsample",
                    "route_path": "/rookieui/prompt-tools/upsample",
                    "available": True,
                    "resolved_node_alias": "DanbooruTagsUpsampler",
                    "availability": {"status": "ready", "detail": "ready"},
                }
            },
        }
        providers_payload = {
            "service": "rookieui",
            "status": "ok",
            "contract": {
                "surface": "prompt_tools_providers",
                "version": live_smoke._LOCAL_PROMPT_WORKBENCH_CONTRACT_VERSION,
            },
            "surfaces": {
                "translation": {
                    "default_provider": "mymemory_free",
                    "shipped_provider_ids": list(live_smoke.PROMPT_WORKBENCH_SHIPPED_TRANSLATION_PROVIDER_IDS),
                    "providers": [
                        {
                            "provider_id": "mymemory_free",
                            "availability": {"status": "ready"},
                        }
                    ],
                },
                "ai_assist": {
                    "default_provider": "",
                    "shipped_provider_ids": list(live_smoke.PROMPT_WORKBENCH_SHIPPED_AI_PROVIDER_IDS),
                    "providers": [
                        {
                            "provider_id": "openai",
                            "availability": {"status": "configuration_required"},
                        }
                    ],
                },
            },
        }

        context, errors = live_smoke._build_prompt_workbench_host_context(config_payload, providers_payload)

        self.assertEqual(errors, [])
        assert context is not None
        self.assertEqual(context.namespace, live_smoke.PROMPT_WORKBENCH_NAMESPACES[0])
        self.assertEqual(context.translation_default_provider, "mymemory_free")
        self.assertEqual(context.translation_default_availability, "ready")
        self.assertEqual(context.ai_assist_default_provider, "")
        self.assertEqual(context.ai_assist_default_availability, "unconfigured")
        self.assertTrue(context.danbooru_available)
        self.assertEqual(context.danbooru_availability, "ready")
        self.assertEqual(context.danbooru_resolved_node_alias, "DanbooruTagsUpsampler")


class LiveSmokeCatalogTests(unittest.TestCase):
    def test_build_txt2img_payload_resolves_profile_aware_ernie_selectors_from_models_payload(self) -> None:
        payload = live_smoke._build_txt2img_payload(
            "ernie_image",
            {
                "checkpoint_name": "ernie\\ernie-image.safetensors",
                "vae_name": "Automatic",
                "text_encoder_name": "",
                "prompt_enhancement_enabled": True,
            },
            "client-1",
            models_payload={
                "source": "host",
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": ["ernie\\ernie-image.safetensors"],
                "vae": ["flux2-vae.safetensors"],
                "text_encoders": ["Ministral3_3B_fp16.safetensors", "ernie-image-prompt-enhancer.safetensors"],
                "default_checkpoint": "realvisxl.safetensors",
                "default_vae": "flux2-vae.safetensors",
                "default_text_encoder": "Ministral3_3B_fp16.safetensors",
            },
        )

        self.assertEqual(payload["text_encoder_name"], "Ministral3_3B_fp16.safetensors")
        self.assertEqual(payload["vae_name"], "flux2-vae.safetensors")
        self.assertTrue(payload["prompt_enhancement_enabled"])

    def test_build_edit_payload_resolves_profile_aware_qwen_edit_selectors_from_models_payload(self) -> None:
        payload = live_smoke._build_edit_payload(
            "qwen_image_edit",
            {
                "checkpoint_name": "Qwen\\qwen_image_edit_fp8_e4m3fn.safetensors",
                "vae_name": "Automatic",
                "text_encoder_name": "",
                "edit_megapixels": 1.5,
            },
            "client-edit",
            models_payload={
                "source": "host",
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": ["Qwen\\qwen_image_edit_fp8_e4m3fn.safetensors"],
                "vae": ["qwen_image_vae.safetensors"],
                "text_encoders": ["qwen_2.5_vl_7b_fp8_scaled.safetensors"],
                "loras": ["Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors"],
                "default_checkpoint": "realvisxl.safetensors",
                "default_vae": "qwen_image_vae.safetensors",
                "default_text_encoder": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
            },
        )

        self.assertEqual(payload["mode"], "img2img")
        self.assertEqual(payload["text_encoder_name"], "qwen_2.5_vl_7b_fp8_scaled.safetensors")
        self.assertEqual(payload["vae_name"], "qwen_image_vae.safetensors")
        self.assertEqual(payload["edit_megapixels"], 1.5)
        self.assertEqual(payload["main_reference_index"], 0)
        self.assertEqual(len(payload["reference_images"]), 1)
        self.assertTrue(str(payload["reference_images"][0]["image_data"]).startswith("data:image/png;base64,"))
        self.assertNotIn("image_data", payload)

    def test_build_edit_payload_uses_ordered_multi_reference_contract_for_flux_kontext(self) -> None:
        payload = live_smoke._build_edit_payload(
            "flux_kontext_dev_edit",
            {
                "checkpoint_name": "Flux\\flux1-dev-kontext_fp8_scaled.safetensors",
                "vae_name": "Automatic",
                "text_encoder_name": "",
            },
            "client-ktext",
            models_payload={
                "source": "host",
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": ["Flux\\flux1-dev-kontext_fp8_scaled.safetensors"],
                "vae": ["ae.safetensors"],
                "text_encoders": ["clip_l.safetensors", "t5xxl_fp8_e4m3fn_scaled.safetensors"],
                "loras": [],
                "default_checkpoint": "realvisxl.safetensors",
                "default_vae": "ae.safetensors",
                "default_text_encoder": "clip_l.safetensors",
            },
        )

        self.assertEqual(payload["mode"], "img2img")
        self.assertEqual(payload["main_reference_index"], 2)
        self.assertEqual(len(payload["reference_images"]), 3)
        self.assertEqual(payload["text_encoder_name"], "")
        self.assertTrue(all(str(entry["image_data"]).startswith("data:image/png;base64,") for entry in payload["reference_images"]))
        self.assertNotIn("image_data", payload)

    def test_build_txt2img_payload_resolves_profile_aware_flux_template_lora(self) -> None:
        payload = live_smoke._build_txt2img_payload(
            "flux",
            {
                "checkpoint_name": "Flux\\flux1-dev.safetensors",
                "vae_name": "Automatic",
                "text_encoder_name": "",
                "template_lora_name": "",
            },
            "client-flux",
            models_payload={
                "source": "host",
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": ["Flux\\flux1-dev.safetensors"],
                "vae": ["ae.safetensors"],
                "text_encoders": ["clip_l.safetensors", "t5xxl_fp8_e4m3fn.safetensors"],
                "loras": ["Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors"],
                "default_checkpoint": "realvisxl.safetensors",
                "default_vae": "ae.safetensors",
                "default_text_encoder": "clip_l.safetensors",
            },
        )

        self.assertEqual(payload["text_encoder_name"], "")
        self.assertEqual(payload["vae_name"], "ae.safetensors")
        self.assertEqual(payload["template_lora_name"], "Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors")

    def test_validate_catalog_contract_accepts_ernie_image_with_blank_text_encoder_selector(self) -> None:
        errors, presets_by_id = live_smoke._validate_catalog_contract(
            {
                "diffusion_models": ["ernie\\ernie-image.safetensors"],
                "vae": ["ernie_vae.safetensors"],
                "text_encoders": ["Ministral3_3B_fp16.safetensors", "ernie-image-prompt-enhancer.safetensors"],
                "catalog": {"primary_model_category_by_family": {"ernie_image": "diffusion_models"}},
            },
            {
                "presets": [
                    {
                        "id": "ernie_image",
                        "checkpoint_name": "ernie\\ernie-image.safetensors",
                        "vae_name": "",
                        "text_encoder_name": "",
                        "prompt_enhancement_enabled": True,
                    }
                ]
            },
            ["ernie_image"],
        )

        self.assertEqual(errors, [])
        self.assertIn("ernie_image", presets_by_id)

    def test_validate_catalog_contract_accepts_ernie_image_with_ministral_text_encoder(self) -> None:
        errors, _ = live_smoke._validate_catalog_contract(
            {
                "diffusion_models": ["ernie\\ernie-image.safetensors"],
                "vae": ["ernie_vae.safetensors"],
                "text_encoders": ["Ministral3_3B_fp16.safetensors", "ernie-image-prompt-enhancer.safetensors"],
                "catalog": {"primary_model_category_by_family": {"ernie_image": "diffusion_models"}},
            },
            {
                "presets": [
                    {
                        "id": "ernie_image",
                        "checkpoint_name": "ernie\\ernie-image.safetensors",
                        "vae_name": "ernie_vae.safetensors",
                        "text_encoder_name": "Ministral3_3B_fp16.safetensors",
                        "prompt_enhancement_enabled": True,
                    }
                ]
            },
            ["ernie_image"],
        )

        self.assertEqual(errors, [])

    def test_validate_catalog_contract_reports_non_ernie_text_encoder_for_ernie_image(self) -> None:
        errors, _ = live_smoke._validate_catalog_contract(
            {
                "diffusion_models": ["ernie\\ernie-image.safetensors"],
                "vae": ["ernie_vae.safetensors"],
                "text_encoders": [
                    "clip_l.safetensors",
                    "Ministral3_3B_fp16.safetensors",
                    "ernie-image-prompt-enhancer.safetensors",
                ],
                "catalog": {"primary_model_category_by_family": {"ernie_image": "diffusion_models"}},
            },
            {
                "presets": [
                    {
                        "id": "ernie_image",
                        "checkpoint_name": "ernie\\ernie-image.safetensors",
                        "vae_name": "ernie_vae.safetensors",
                        "text_encoder_name": "clip_l.safetensors",
                        "prompt_enhancement_enabled": True,
                    }
                ]
            },
            ["ernie_image"],
        )

        joined_errors = "\n".join(errors)
        self.assertIn("family-aligned text encoder", joined_errors)
        self.assertIn("ERNIE/Ministral", joined_errors)

    def test_validate_catalog_contract_reports_missing_ernie_host_assets(self) -> None:
        errors, _ = live_smoke._validate_catalog_contract(
            {
                "diffusion_models": ["Anima\\animaCatTower_v02.safetensors"],
                "vae": ["Flux-Krea-vae.safetensors"],
                "text_encoders": ["clip_l.safetensors"],
                "catalog": {"primary_model_category_by_family": {"ernie_image": "diffusion_models"}},
            },
            {
                "presets": [
                    {
                        "id": "ernie_image",
                        "checkpoint_name": "Anima\\animaCatTower_v02.safetensors",
                        "vae_name": "",
                        "text_encoder_name": "",
                        "prompt_enhancement_enabled": False,
                    }
                ]
            },
            ["ernie_image"],
        )

        self.assertGreaterEqual(len(errors), 5)
        joined_errors = "\n".join(errors)
        self.assertIn("expected an ERNIE diffusion-model checkpoint", joined_errors)
        self.assertIn("host diffusion model catalog", joined_errors)
        self.assertIn("host VAE catalog", joined_errors)
        self.assertIn("host text encoder catalog", joined_errors)
        self.assertIn("prompt_enhancement_enabled=True", joined_errors)

    def test_validate_catalog_contract_accepts_flux_with_official_encoder_sequence(self) -> None:
        errors, _ = live_smoke._validate_catalog_contract(
            {
                "diffusion_models": ["Flux\\flux1-dev.safetensors"],
                "vae": ["ae.safetensors"],
                "text_encoders": ["clip_l.safetensors", "t5xxl_fp8_e4m3fn.safetensors"],
                "loras": ["Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors"],
                "catalog": {"primary_model_category_by_family": {"flux": "diffusion_models"}},
            },
            {
                "presets": [
                    {
                        "id": "flux",
                        "checkpoint_name": "Flux\\flux1-dev.safetensors",
                        "vae_name": "ae.safetensors",
                        "text_encoder_name": "clip_l.safetensors|t5xxl_fp8_e4m3fn.safetensors",
                        "template_lora_name": "Flux\\Flux_2-Turbo-LoRA_comfyui.safetensors",
                        "prompt_enhancement_enabled": False,
                    }
                ]
            },
            ["flux"],
        )

        self.assertEqual(errors, [])

    def test_validate_catalog_contract_requires_official_flux_template_lora(self) -> None:
        errors, _ = live_smoke._validate_catalog_contract(
            {
                "diffusion_models": ["Flux\\flux1-dev.safetensors"],
                "vae": ["ae.safetensors"],
                "text_encoders": ["clip_l.safetensors", "t5xxl_fp8_e4m3fn.safetensors"],
                "loras": ["Flux\\Flux_2-Lightning-4steps.safetensors"],
                "catalog": {"primary_model_category_by_family": {"flux": "diffusion_models"}},
            },
            {
                "presets": [
                    {
                        "id": "flux",
                        "checkpoint_name": "Flux\\flux1-dev.safetensors",
                        "vae_name": "ae.safetensors",
                        "text_encoder_name": "clip_l.safetensors|t5xxl_fp8_e4m3fn.safetensors",
                    }
                ]
            },
            ["flux"],
        )

        self.assertIn("profile 'flux' host LoRA catalog did not expose the official template-owned LoRA.", errors)

    def test_validate_catalog_contract_accepts_qwen_image_edit_with_official_lora(self) -> None:
        errors, _ = live_smoke._validate_catalog_contract(
            {
                "diffusion_models": ["Qwen\\qwen_image_edit_fp8_e4m3fn.safetensors"],
                "vae": ["qwen_image_vae.safetensors"],
                "text_encoders": ["qwen_2.5_vl_7b_fp8_scaled.safetensors"],
                "loras": ["Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors"],
                "catalog": {"primary_model_category_by_family": {"qwen_image_edit": "diffusion_models"}},
            },
            {
                "presets": [
                    {
                        "id": "qwen_image_edit",
                        "checkpoint_name": "Qwen\\qwen_image_edit_fp8_e4m3fn.safetensors",
                        "vae_name": "qwen_image_vae.safetensors",
                        "text_encoder_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                        "shift": 3.0,
                        "edit_megapixels": 1.5,
                    }
                ]
            },
            ["qwen_image_edit"],
        )

        self.assertEqual(errors, [])

    def test_validate_catalog_contract_accepts_qwen_image_edit_multi_lora_with_official_lora(self) -> None:
        errors, _ = live_smoke._validate_catalog_contract(
            {
                "diffusion_models": ["Qwen\\qwen_image_edit_fp8_e4m3fn.safetensors"],
                "vae": ["qwen_image_vae.safetensors"],
                "text_encoders": ["qwen_2.5_vl_7b_fp8_scaled.safetensors"],
                "loras": ["Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors"],
                "catalog": {"primary_model_category_by_family": {"qwen_image_edit_multi_lora": "diffusion_models"}},
            },
            {
                "presets": [
                    {
                        "id": "qwen_image_edit_multi_lora",
                        "checkpoint_name": "Qwen\\qwen_image_edit_fp8_e4m3fn.safetensors",
                        "vae_name": "qwen_image_vae.safetensors",
                        "text_encoder_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                        "shift": 3.0,
                        "edit_megapixels": 1.5,
                    }
                ]
            },
            ["qwen_image_edit_multi_lora"],
        )

        self.assertEqual(errors, [])

    def test_validate_image_edit_dry_run_response_pins_triple_template_lora_depth(self) -> None:
        case = live_smoke._build_image_edit_dry_run_case(
            "qwen_image_edit_multi_lora",
            {
                "checkpoint_name": "Qwen\\qwen_image_edit_fp8_e4m3fn.safetensors",
                "vae_name": "qwen_image_vae.safetensors",
                "text_encoder_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                "edit_megapixels": 1.5,
            },
            models_payload={
                "source": "host",
                "checkpoints": ["realvisxl.safetensors"],
                "diffusion_models": ["Qwen\\qwen_image_edit_fp8_e4m3fn.safetensors"],
                "vae": ["qwen_image_vae.safetensors"],
                "text_encoders": ["qwen_2.5_vl_7b_fp8_scaled.safetensors"],
                "loras": ["Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors"],
                "default_checkpoint": "realvisxl.safetensors",
                "default_vae": "qwen_image_vae.safetensors",
                "default_text_encoder": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
            },
        )

        errors = live_smoke._validate_image_edit_dry_run_response(
            case,
            {
                "workflow_kind": "img2img-qwen_image_edit_multi_lora",
                "normalized_request": {
                    "mode": "img2img",
                    "execution_mode": "edit",
                    "reference_image_assets": ["uploaded-reference"],
                    "main_reference_index": 0,
                    "mask_asset": "",
                },
                "workflow": {
                    "1": {"class_type": "RookieUILoadAssetImage"},
                    "2": {"class_type": "LoraLoaderModelOnly"},
                    "3": {"class_type": "LoraLoaderModelOnly"},
                    "4": {"class_type": "LoraLoaderModelOnly"},
                },
            },
        )

        self.assertEqual(errors, [])

    def test_run_execute_smoke_routes_qwen_image_edit_through_img2img_without_mask(self) -> None:
        submit_calls: list[tuple[str, dict[str, object]]] = []

        def _fake_request_json(
            method: str,
            url: str,
            *,
            payload: dict[str, object] | None = None,
            timeout_seconds: float,
        ) -> dict[str, object]:
            self.assertEqual(method, "POST")
            assert payload is not None
            submit_calls.append((url, payload))
            return {"submission": {"accepted": True, "prompt_id": "prompt-1"}}

        with (
            mock.patch.object(live_smoke, "_request_json", side_effect=_fake_request_json),
            mock.patch.object(
                live_smoke,
                "_poll_queue_job_until_terminal",
                return_value={"status": "completed"},
            ),
        ):
            errors = live_smoke._run_execute_smoke(
                "http://127.0.0.1:8188",
                ["qwen_image_edit"],
                {
                    "source": "host",
                    "checkpoints": ["realvisxl.safetensors"],
                    "diffusion_models": ["Qwen\\qwen_image_edit_fp8_e4m3fn.safetensors"],
                    "vae": ["qwen_image_vae.safetensors"],
                    "text_encoders": ["qwen_2.5_vl_7b_fp8_scaled.safetensors"],
                    "loras": ["Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors"],
                    "default_checkpoint": "realvisxl.safetensors",
                    "default_vae": "qwen_image_vae.safetensors",
                    "default_text_encoder": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                },
                {
                    "qwen_image_edit": {
                        "checkpoint_name": "Qwen\\qwen_image_edit_fp8_e4m3fn.safetensors",
                        "vae_name": "Automatic",
                        "text_encoder_name": "",
                        "shift": 3.0,
                        "edit_megapixels": 1.5,
                    }
                },
                request_timeout_seconds=5.0,
                poll_timeout_seconds=5.0,
                poll_interval_seconds=0.1,
            )

        self.assertEqual(errors, [])
        self.assertEqual(len(submit_calls), 1)
        submit_url, submit_payload = submit_calls[0]
        self.assertEqual(submit_url, "http://127.0.0.1:8188/rookieui/generate/img2img")
        self.assertEqual(submit_payload["mode"], "img2img")
        self.assertNotIn("mask_asset", submit_payload)
        self.assertEqual(submit_payload["main_reference_index"], 0)
        self.assertEqual(len(submit_payload["reference_images"]), 1)
        self.assertTrue(str(submit_payload["reference_images"][0]["image_data"]).startswith("data:image/png;base64,"))
        self.assertNotIn("image_data", submit_payload)

    def test_run_execute_smoke_routes_flux_kontext_image_edit_with_ordered_references(self) -> None:
        submit_calls: list[tuple[str, dict[str, object]]] = []

        def _fake_request_json(
            method: str,
            url: str,
            *,
            payload: dict[str, object] | None = None,
            timeout_seconds: float,
        ) -> dict[str, object]:
            self.assertEqual(method, "POST")
            assert payload is not None
            submit_calls.append((url, payload))
            return {"submission": {"accepted": True, "prompt_id": "prompt-2"}}

        with (
            mock.patch.object(live_smoke, "_request_json", side_effect=_fake_request_json),
            mock.patch.object(
                live_smoke,
                "_poll_queue_job_until_terminal",
                return_value={"status": "completed"},
            ),
        ):
            errors = live_smoke._run_execute_smoke(
                "http://127.0.0.1:8188",
                ["flux_kontext_dev_edit"],
                {
                    "source": "host",
                    "checkpoints": ["realvisxl.safetensors"],
                    "diffusion_models": ["Flux\\flux1-dev-kontext_fp8_scaled.safetensors"],
                    "vae": ["ae.safetensors"],
                    "text_encoders": ["clip_l.safetensors", "t5xxl_fp8_e4m3fn_scaled.safetensors"],
                    "loras": [],
                    "default_checkpoint": "realvisxl.safetensors",
                    "default_vae": "ae.safetensors",
                    "default_text_encoder": "clip_l.safetensors",
                },
                {
                    "flux_kontext_dev_edit": {
                        "checkpoint_name": "Flux\\flux1-dev-kontext_fp8_scaled.safetensors",
                        "vae_name": "Automatic",
                        "text_encoder_name": "",
                    }
                },
                request_timeout_seconds=5.0,
                poll_timeout_seconds=5.0,
                poll_interval_seconds=0.1,
            )

        self.assertEqual(errors, [])
        self.assertEqual(len(submit_calls), 1)
        submit_url, submit_payload = submit_calls[0]
        self.assertEqual(submit_url, "http://127.0.0.1:8188/rookieui/generate/img2img")
        self.assertEqual(submit_payload["mode"], "img2img")
        self.assertEqual(submit_payload["main_reference_index"], 2)
        self.assertEqual(len(submit_payload["reference_images"]), 3)
        self.assertTrue(all(str(entry["image_data"]).startswith("data:image/png;base64,") for entry in submit_payload["reference_images"]))
        self.assertNotIn("mask_asset", submit_payload)
        self.assertNotIn("image_data", submit_payload)


    def test_validate_catalog_contract_reports_wrong_chroma_family_fallback(self) -> None:
        errors, _ = live_smoke._validate_catalog_contract(
            {
                "diffusion_models": ["Anima\\animaCatTower_v02.safetensors"],
                "vae": ["Flux-Krea-vae.safetensors"],
                "text_encoders": ["t5xxl_fp8_e4m3fn.safetensors"],
                "catalog": {"primary_model_category_by_family": {"chroma": "diffusion_models"}},
            },
            {
                "presets": [
                    {
                        "id": "chroma",
                        "checkpoint_name": "Anima\\animaCatTower_v02.safetensors",
                        "vae_name": "Flux-Krea-vae.safetensors",
                        "text_encoder_name": "t5xxl_fp8_e4m3fn.safetensors",
                        "shift": 1.0,
                        "prompt_enhancement_enabled": False,
                    }
                ]
            },
            ["chroma"],
        )

        joined_errors = "\n".join(errors)
        self.assertIn("family-aligned diffusion-model checkpoint", joined_errors)
        self.assertIn("host diffusion model catalog did not expose the expected family selector", joined_errors)

    def test_validate_prompt_workbench_host_sync_reports_contract_drift(self) -> None:
        errors = live_smoke._validate_prompt_workbench_host_sync(
            live_smoke.PromptWorkbenchHostContext(
                namespace="txt2img_prompt",
                host_contract_version="r123f114f115-20260417",
                local_contract_version=live_smoke._LOCAL_PROMPT_WORKBENCH_CONTRACT_VERSION,
                translation_default_provider="mymemory_free",
                translation_default_availability="ready",
                ai_assist_default_provider="",
                ai_assist_default_availability="unconfigured",
                danbooru_available=False,
                danbooru_availability="host_missing",
                danbooru_resolved_node_alias="",
            )
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("host='r123f114f115-20260417'", errors[0])

    def test_main_prompt_workbench_report_only_returns_zero_on_lane_issues(self) -> None:
        with (
            mock.patch.object(
                sys,
                "argv",
                ["run_live_smoke_tests.py", "--validation-mode", "prompt-workbench", "--report-only"],
            ),
            mock.patch.object(
                live_smoke,
                "_load_bootstrap_payload",
                return_value=_build_bootstrap_payload(),
            ),
            mock.patch.object(
                live_smoke,
                "_load_server_payloads",
                return_value=({"checkpoints": []}, {"presets": []}),
            ),
            mock.patch.object(
                live_smoke,
                "_run_prompt_workbench_validation_lane",
                return_value=(["contract drift"], []),
            ),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = live_smoke.main()

        self.assertEqual(result, 0)

    def test_run_prompt_workbench_validation_lane_reports_missing_prompt_tools_routes(self) -> None:
        with mock.patch.object(
            live_smoke,
            "_load_bootstrap_payload",
            return_value={"routes": ["/rookieui/health"]},
        ):
            combined_errors, execution_errors = live_smoke._run_prompt_workbench_validation_lane(
                "http://127.0.0.1:8188",
                execute=False,
                request_timeout_seconds=10.0,
            )

        self.assertEqual(execution_errors, [])
        self.assertEqual(len(combined_errors), 1)
        self.assertIn("/rookieui/prompt-tools/config", combined_errors[0])

    def test_validate_prompt_workbench_upsample_payload_accepts_matching_contract(self) -> None:
        errors = live_smoke._validate_prompt_workbench_upsample_payload(
            {
                "service": "rookieui",
                "status": "ok",
                "contract": {
                    "surface": "prompt_tools_upsample",
                    "version": live_smoke._LOCAL_PROMPT_WORKBENCH_CONTRACT_VERSION,
                },
                "action_id": "danbooru_upsample",
                "final_prompt": "masterpiece, city skyline, enhanced tags",
                "generated_suffix": "enhanced tags",
                "host_node_alias": "DanbooruTagsUpsampler",
                "availability": {"status": "ready"},
                "warnings": [],
                "warning_codes": [],
            }
        )

        self.assertEqual(errors, [])


class LiveSmokeXYZPlotTests(unittest.TestCase):
    def test_default_profiles_for_xyz_plot_is_empty(self) -> None:
        self.assertEqual(live_smoke._default_profiles_for_mode("xyz-plot"), "")

    def test_validate_xyz_plot_axes_payload_accepts_matching_contract(self) -> None:
        errors = live_smoke._validate_xyz_plot_axes_payload(
            {
                "service": "rookieui",
                "status": "ok",
                "contract": {
                    "surface": "xyz_plot_axes",
                    "version": live_smoke._LOCAL_XYZ_PLOT_CONTRACT_VERSION,
                    "route_family": "/rookieui/xyz-plot",
                },
                "axis_order": ["steps", "cfg_scale", "seed", "checkpoint_name", "denoising_strength"],
                "axes": {
                    "steps": {"session_runner_support": True},
                    "cfg_scale": {"session_runner_support": True},
                    "seed": {"session_runner_support": True},
                    "checkpoint_name": {"session_runner_support": True},
                    "denoising_strength": {
                        "session_runner_support": True,
                        "mode_scopes": ["img2img"],
                    },
                },
            }
        )

        self.assertEqual(errors, [])

    def test_validate_xyz_plot_host_sync_reports_contract_drift(self) -> None:
        errors = live_smoke._validate_xyz_plot_host_sync(
            live_smoke.XYZPlotHostContext(
                checkpoint_name="SD15\\BravNew.safetensors",
                workflow_family="sd15",
                host_contract_version="r125-20260416",
                local_contract_version=live_smoke._LOCAL_XYZ_PLOT_CONTRACT_VERSION,
            )
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("host='r125-20260416'", errors[0])

    def test_validate_xyz_plot_estimate_payload_accepts_matching_response(self) -> None:
        errors = live_smoke._validate_xyz_plot_estimate_payload(
            {
                "service": "rookieui",
                "status": "ok",
                "contract": {
                    "surface": "xyz_plot_estimate",
                    "version": live_smoke._LOCAL_XYZ_PLOT_CONTRACT_VERSION,
                    "route_family": "/rookieui/xyz-plot",
                },
                "mode": "txt2img",
                "axes": [
                    {"axis_id": "steps"},
                    {"axis_id": "cfg_scale"},
                ],
                "estimate": {
                    "cell_count": 4,
                    "generated_image_count": 4,
                },
                "can_run": True,
                "warnings": [],
                "warning_codes": [],
            },
            mode="txt2img",
            expected_axis_ids=("steps", "cfg_scale"),
        )

        self.assertEqual(errors, [])

    def test_validate_xyz_plot_terminal_detail_payload_accepts_ready_grid_results(self) -> None:
        errors = live_smoke._validate_xyz_plot_terminal_detail_payload(
            {
                "service": "rookieui",
                "status": "ok",
                "contract": {
                    "surface": "xyz_plot_session_detail",
                    "version": live_smoke._LOCAL_XYZ_PLOT_CONTRACT_VERSION,
                    "route_family": "/rookieui/xyz-plot",
                },
                "session": {
                    "session_id": "xyz-1",
                    "client_id": "client-1",
                    "status": "completed",
                    "seed_policy": {
                        "keep_negative_one_seed": False,
                        "vary_seeds_x": False,
                        "vary_seeds_y": False,
                        "vary_seeds_z": False,
                        "fixed_base_seed": 101,
                        "fixed_axis_values": {},
                    },
                    "axes": [{"axis_id": "steps"}, {"axis_id": "cfg_scale"}],
                    "cells": [
                        {"resolved_seed": 101},
                        {"resolved_seed": 101},
                        {"resolved_seed": 101},
                        {"resolved_seed": 101},
                    ],
                    "summary": {"total_cells": 4, "completed_cells": 4},
                    "results": {
                        "status": "ready",
                        "main_grid": {
                            "asset_handle": "xyz_plot_grid_1.png",
                            "preview_data_url": "data:image/png;base64,abc",
                        },
                        "sub_grids": [],
                        "lone_images": [{}, {}, {}, {}],
                        "warnings": [],
                    },
                },
            },
            session_id="xyz-1",
            client_id="client-1",
        )

        self.assertEqual(errors, [])

    def test_main_xyz_plot_report_only_returns_zero_on_validation_errors(self) -> None:
        with (
            mock.patch.object(
                sys,
                "argv",
                ["run_live_smoke_tests.py", "--validation-mode", "xyz-plot", "--report-only"],
            ),
            mock.patch.object(
                live_smoke,
                "_load_bootstrap_payload",
                return_value=_build_bootstrap_payload(),
            ),
            mock.patch.object(
                live_smoke,
                "_load_server_payloads",
                return_value=({"default_checkpoint": "SD15\\BravNew.safetensors"}, {"presets": []}),
            ),
            mock.patch.object(
                live_smoke,
                "_run_xyz_plot_validation_lane",
                return_value=(["xyz error"], []),
            ),
            mock.patch.object(
                live_smoke,
                "_run_prompt_workbench_validation_lane",
                return_value=(["prompt-workbench error"], []),
            ),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = live_smoke.main()

        self.assertEqual(result, 0)

    def test_run_xyz_plot_validation_lane_reports_missing_route_family(self) -> None:
        with mock.patch.object(
            live_smoke,
            "_load_bootstrap_payload",
            return_value={"routes": ["/rookieui/health"]},
        ):
            combined_errors, execution_errors = live_smoke._run_xyz_plot_validation_lane(
                "http://127.0.0.1:8188",
                {"default_checkpoint": "SD15\\BravNew.safetensors"},
                execute=False,
                request_timeout_seconds=10.0,
                poll_timeout_seconds=10.0,
                poll_interval_seconds=0.5,
            )

        self.assertEqual(execution_errors, [])
        self.assertEqual(len(combined_errors), 1)
        self.assertIn("/rookieui/xyz-plot/axes", combined_errors[0])

    def test_run_xyz_plot_validation_lane_execute_uses_session_terminal_closure(self) -> None:
        axes_payload = {
            "service": "rookieui",
            "status": "ok",
            "contract": {
                "surface": "xyz_plot_axes",
                "version": live_smoke._LOCAL_XYZ_PLOT_CONTRACT_VERSION,
                "route_family": "/rookieui/xyz-plot",
            },
            "axes": {
                "steps": {"session_runner_support": True},
                "cfg_scale": {"session_runner_support": True},
                "seed": {"session_runner_support": True},
                "checkpoint_name": {"session_runner_support": True},
                "denoising_strength": {
                    "session_runner_support": True,
                    "mode_scopes": ["img2img"],
                },
            },
        }
        estimate_payload = {
            "service": "rookieui",
            "status": "ok",
            "contract": {
                "surface": "xyz_plot_estimate",
                "version": live_smoke._LOCAL_XYZ_PLOT_CONTRACT_VERSION,
                "route_family": "/rookieui/xyz-plot",
            },
            "mode": "txt2img",
            "axes": [{"axis_id": "steps"}, {"axis_id": "cfg_scale"}],
            "estimate": {"cell_count": 4, "generated_image_count": 4},
            "can_run": True,
            "warnings": [],
            "warning_codes": [],
        }
        img2img_estimate_payload = {
            **estimate_payload,
            "mode": "img2img",
            "axes": [{"axis_id": "steps"}, {"axis_id": "denoising_strength"}],
        }
        run_payload = {
            "service": "rookieui",
            "status": "ok",
            "contract": {
                "surface": "xyz_plot_run",
                "version": live_smoke._LOCAL_XYZ_PLOT_CONTRACT_VERSION,
                "route_family": "/rookieui/xyz-plot",
            },
            "session": {
                "session_id": "xyz-1",
                "client_id": "rookieui-live-xyz-sd15-1234000",
                "status": "in_progress",
                "seed_policy": {
                    "keep_negative_one_seed": False,
                    "vary_seeds_x": False,
                    "vary_seeds_y": False,
                    "vary_seeds_z": False,
                    "fixed_base_seed": 101,
                    "fixed_axis_values": {},
                },
                "axes": [{"axis_id": "steps"}, {"axis_id": "cfg_scale"}],
                "cells": [
                    {"prompt_id": "prompt-1", "resolved_seed": 101},
                    {},
                    {},
                    {},
                ],
                "summary": {"total_cells": 4},
                "results": {"status": "pending", "main_grid": {}, "sub_grids": [], "lone_images": [], "warnings": []},
            },
        }
        session_list_payload = {
            "service": "rookieui",
            "status": "ok",
            "contract": {
                "surface": "xyz_plot_session_list",
                "version": live_smoke._LOCAL_XYZ_PLOT_CONTRACT_VERSION,
                "route_family": "/rookieui/xyz-plot",
            },
            "sessions": [{"session_id": "xyz-1", "client_id": "rookieui-live-xyz-sd15-1234000"}],
        }
        empty_session_list_payload = {
            **session_list_payload,
            "sessions": [],
        }
        terminal_payload = {
            "service": "rookieui",
            "status": "ok",
            "contract": {
                "surface": "xyz_plot_session_detail",
                "version": live_smoke._LOCAL_XYZ_PLOT_CONTRACT_VERSION,
                "route_family": "/rookieui/xyz-plot",
            },
            "session": {
                "session_id": "xyz-1",
                "client_id": "rookieui-live-xyz-sd15-1234000",
                "status": "completed",
                "seed_policy": {
                    "keep_negative_one_seed": False,
                    "vary_seeds_x": False,
                    "vary_seeds_y": False,
                    "vary_seeds_z": False,
                    "fixed_base_seed": 101,
                    "fixed_axis_values": {},
                },
                "axes": [{"axis_id": "steps"}, {"axis_id": "cfg_scale"}],
                "cells": [
                    {"resolved_seed": 101},
                    {"resolved_seed": 101},
                    {"resolved_seed": 101},
                    {"resolved_seed": 101},
                ],
                "summary": {"total_cells": 4, "completed_cells": 4},
                "results": {
                    "status": "ready",
                    "main_grid": {
                        "asset_handle": "xyz_plot_grid_1.png",
                        "preview_data_url": "data:image/png;base64,abc",
                    },
                    "sub_grids": [],
                    "lone_images": [{}, {}, {}, {}],
                    "warnings": [],
                },
            },
        }

        with (
            mock.patch.object(
                live_smoke,
                "_load_bootstrap_payload",
                return_value={"routes": ["/rookieui/xyz-plot/axes"]},
            ),
            mock.patch.object(live_smoke, "_load_xyz_plot_axes_payload", return_value=axes_payload),
            mock.patch.object(
                live_smoke,
                "_request_json",
                side_effect=[
                    estimate_payload,
                    img2img_estimate_payload,
                    empty_session_list_payload,
                    run_payload,
                    session_list_payload,
                ],
            ),
            mock.patch.object(
                live_smoke,
                "_poll_queue_snapshot_until_job_visible",
                side_effect=AssertionError("xyz execute should not require queue snapshot polling"),
            ),
            mock.patch.object(
                live_smoke,
                "_poll_xyz_plot_session_until_terminal",
                return_value=(terminal_payload, []),
            ),
            mock.patch.object(
                live_smoke,
                "_run_shared_queue_post_state_smoke",
                side_effect=AssertionError("xyz execute should not use shared queue closure"),
            ),
            mock.patch.object(live_smoke.time, "time", return_value=1234.0),
        ):
            combined_errors, execution_errors = live_smoke._run_xyz_plot_validation_lane(
                "http://127.0.0.1:8188",
                {
                    "default_checkpoint": "SD15\\BravNew.safetensors",
                    "checkpoints": ["SD15\\BravNew.safetensors"],
                },
                execute=True,
                request_timeout_seconds=10.0,
                poll_timeout_seconds=10.0,
                poll_interval_seconds=0.5,
            )

        self.assertEqual(combined_errors, [])
        self.assertEqual(execution_errors, [])


class LiveSmokeAuxiliaryPipelineTests(unittest.TestCase):
    def test_build_auxiliary_pipeline_context_prefers_sd_family_checkpoint_over_non_sd_default(self) -> None:
        context = live_smoke._build_auxiliary_pipeline_context(
            {
                "default_checkpoint": "F5-TTS\\model_1250000.safetensors",
                "checkpoints": [
                    "F5-TTS\\model_1250000.safetensors",
                    "SD15\\BravNew.safetensors",
                ],
            }
        )

        self.assertEqual(context.checkpoint_name, "SD15\\BravNew.safetensors")
        self.assertEqual(context.workflow_family, "sd15")

    def test_validate_extras_execution_response_accepts_valid_payload(self) -> None:
        errors = live_smoke._validate_extras_execution_response(
            {
                "service": "rookieui",
                "status": "ok",
                "contract": {
                    "surface": "extras_run",
                    "version": live_smoke.EXTRAS_CONTRACT_VERSION,
                },
                "mode": "single_image",
                "normalized_request": {
                    "scale_mode": "scale_to",
                    "target_width": 128,
                    "target_height": 160,
                    "face_restoration": "codeformer",
                    "color_correction": True,
                },
                "warnings": [
                    "codeformer face restoration is unavailable; continuing without face restoration."
                ],
                "diagnostics": [
                    {
                        "face_restoration": "codeformer",
                        "restored_faces": 0,
                        "status": "unavailable",
                    }
                ],
                "output_assets": ["rookieui_extras_1.png"],
                "preview_asset": "rookieui_extras_1.png",
                "preview_data_url": "data:image/png;base64,abc",
            }
        )

        self.assertEqual(errors, [])

    def test_validate_extras_execution_response_rejects_missing_diagnostics(self) -> None:
        errors = live_smoke._validate_extras_execution_response(
            {
                "service": "rookieui",
                "status": "ok",
                "contract": {
                    "surface": "extras_run",
                    "version": live_smoke.EXTRAS_CONTRACT_VERSION,
                },
                "mode": "single_image",
                "normalized_request": {
                    "scale_mode": "scale_to",
                    "target_width": 128,
                    "target_height": 160,
                    "face_restoration": "codeformer",
                    "color_correction": True,
                },
                "warnings": [
                    "codeformer face restoration is unavailable; continuing without face restoration."
                ],
                "output_assets": ["rookieui_extras_1.png"],
                "preview_asset": "rookieui_extras_1.png",
                "preview_data_url": "data:image/png;base64,abc",
            }
        )

        self.assertIn("extras: diagnostics missing.", errors)

    def test_validate_pnginfo_parse_response_accepts_txt2img_case(self) -> None:
        context = live_smoke._build_auxiliary_pipeline_context({"default_checkpoint": "SD15\\BravNew.safetensors"})
        case = live_smoke._build_pnginfo_live_cases(context)[0]

        errors = live_smoke._validate_pnginfo_parse_response(
            case,
            {
                "service": "rookieui",
                "status": "ok",
                "contract": {
                    "surface": "pnginfo_parse_inspect",
                    "version": live_smoke.PNGINFO_CONTRACT_VERSION,
                },
                "source_type": "a1111",
                "target_form": "txt2img",
                "apply_targets": ["txt2img", "img2img"],
                "asset_handle": "pnginfo_input_1.png",
                "warnings": [],
                "missing_inputs": [],
                "payload": {
                    "prompt": "harbor dusk",
                    "negative_prompt": "blurry",
                    "profile": "sd15",
                    "checkpoint_name": "SD15\\BravNew.safetensors",
                },
            },
        )

        self.assertEqual(errors, [])

    def test_validate_pnginfo_parse_response_accepts_inspect_only_case(self) -> None:
        context = live_smoke._build_auxiliary_pipeline_context({"default_checkpoint": "SD15\\BravNew.safetensors"})
        case = live_smoke._build_pnginfo_live_cases(context)[1]

        errors = live_smoke._validate_pnginfo_parse_response(
            case,
            {
                "service": "rookieui",
                "status": "ok",
                "contract": {
                    "surface": "pnginfo_parse_inspect",
                    "version": live_smoke.PNGINFO_CONTRACT_VERSION,
                },
                "source_type": "comfyui",
                "target_form": "inspect_only",
                "apply_targets": [],
                "asset_handle": "pnginfo_input_2.png",
                "warnings": ["ComfyUI metadata is available for inspection only in RookieUI."],
                "payload": {},
            },
        )

        self.assertEqual(errors, [])

    def test_validate_pnginfo_apply_back_response_accepts_matching_dry_run_payload(self) -> None:
        context = live_smoke._build_auxiliary_pipeline_context({"default_checkpoint": "SD15\\BravNew.safetensors"})
        case = live_smoke._build_pnginfo_live_cases(context)[0]

        errors = live_smoke._validate_pnginfo_apply_back_response(
            case,
            {
                "submission": {"accepted": False, "mode": "dry-run"},
                "workflow_kind": "txt2img-sd15",
                "normalized_request": {
                    "prompt": "harbor dusk",
                    "negative_prompt": "blurry",
                    "checkpoint_name": "SD15\\BravNew.safetensors",
                },
            },
        )

        self.assertEqual(errors, [])

    def test_validate_queue_snapshot_response_accepts_visible_job(self) -> None:
        errors = live_smoke._validate_queue_snapshot_response(
            {
                "service": "rookieui",
                "status": "ok",
                "source": "host",
                "queue_remaining": 1,
                "contract": {
                    "surface": "queue_snapshot_and_job_lookup",
                    "version": live_smoke.QUEUE_CONTRACT_VERSION,
                },
                "jobs": [
                    {
                        "id": "prompt-1",
                        "status": "in_progress",
                    }
                ],
            },
            prompt_id="prompt-1",
            allowed_statuses=("pending", "in_progress", "completed"),
        )

        self.assertEqual(errors, [])

    def test_validate_queue_snapshot_response_accepts_empty_completed_snapshot_when_visibility_is_optional(self) -> None:
        errors = live_smoke._validate_queue_snapshot_response(
            {
                "service": "rookieui",
                "status": "ok",
                "source": "host",
                "queue_remaining": 0,
                "contract": {
                    "surface": "queue_snapshot_and_job_lookup",
                    "version": live_smoke.QUEUE_CONTRACT_VERSION,
                },
                "jobs": [],
            },
            prompt_id="prompt-1",
            allowed_statuses=("completed",),
            require_visible_job=False,
            expected_queue_remaining=0,
        )

        self.assertEqual(errors, [])

    def test_validate_queue_job_response_accepts_completed_job(self) -> None:
        errors = live_smoke._validate_queue_job_response(
            {
                "service": "rookieui",
                "status": "ok",
                "source": "host",
                "queue_remaining": 0,
                "contract": {
                    "surface": "queue_snapshot_and_job_lookup",
                    "version": live_smoke.QUEUE_CONTRACT_VERSION,
                },
                "job": {
                    "id": "prompt-1",
                    "status": "completed",
                    "reusable_outputs": ["history-image.png"],
                },
            },
            prompt_id="prompt-1",
        )

        self.assertEqual(errors, [])

    def test_run_shared_queue_post_state_smoke_accepts_completed_job_closure(self) -> None:
        with (
            mock.patch.object(
                live_smoke,
                "_poll_queue_snapshot_until_job_visible",
                return_value={
                    "service": "rookieui",
                    "status": "ok",
                    "source": "host",
                    "queue_remaining": 1,
                    "contract": {
                        "surface": "queue_snapshot_and_job_lookup",
                        "version": live_smoke.QUEUE_CONTRACT_VERSION,
                    },
                    "jobs": [{"id": "prompt-1", "status": "in_progress"}],
                },
            ),
            mock.patch.object(
                live_smoke,
                "_poll_queue_job_until_terminal",
                return_value={"id": "prompt-1", "status": "completed", "reusable_outputs": ["image.png"]},
            ),
            mock.patch.object(
                live_smoke,
                "_request_json",
                side_effect=[
                    {
                        "service": "rookieui",
                        "status": "ok",
                        "source": "host",
                        "queue_remaining": 0,
                        "contract": {
                            "surface": "queue_snapshot_and_job_lookup",
                            "version": live_smoke.QUEUE_CONTRACT_VERSION,
                        },
                        "job": {
                            "id": "prompt-1",
                            "status": "completed",
                            "reusable_outputs": ["image.png"],
                        },
                    },
                    {
                        "service": "rookieui",
                        "status": "ok",
                        "source": "host",
                        "queue_remaining": 0,
                        "contract": {
                            "surface": "queue_snapshot_and_job_lookup",
                            "version": live_smoke.QUEUE_CONTRACT_VERSION,
                        },
                        "jobs": [],
                    },
                ],
            ),
        ):
            errors = live_smoke._run_shared_queue_post_state_smoke(
                "http://127.0.0.1:8188",
                lane_label="controlnet execute",
                submit_result={"submission": {"accepted": True, "prompt_id": "prompt-1"}},
                client_id="rookieui-live-controlnet-sd15-1",
                request_timeout_seconds=5.0,
                poll_timeout_seconds=5.0,
                poll_interval_seconds=0.1,
            )

        self.assertEqual(errors, [])

    def test_main_auxiliary_pipelines_report_only_returns_zero_on_validation_errors(self) -> None:
        with (
            mock.patch.object(
                sys,
                "argv",
                ["run_live_smoke_tests.py", "--validation-mode", "auxiliary-pipelines", "--report-only"],
            ),
            mock.patch.object(
                live_smoke,
                "_load_bootstrap_payload",
                return_value=_build_bootstrap_payload(),
            ),
            mock.patch.object(
                live_smoke,
                "_load_server_payloads",
                return_value=({"default_checkpoint": "SD15\\BravNew.safetensors"}, {"presets": []}),
            ),
            mock.patch.object(
                live_smoke,
                "_run_extras_execution_smoke",
                return_value=["extras error"],
            ),
            mock.patch.object(
                live_smoke,
                "_run_pnginfo_dry_run_smoke",
                return_value=([], None, None),
            ),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = live_smoke.main()

        self.assertEqual(result, 0)

    def test_main_full_pipeline_report_only_returns_zero_on_lane_errors(self) -> None:
        with (
            mock.patch.object(
                sys,
                "argv",
                ["run_live_smoke_tests.py", "--validation-mode", "full-pipeline", "--report-only"],
            ),
            mock.patch.object(
                live_smoke,
                "_load_bootstrap_payload",
                return_value=_build_bootstrap_payload(),
            ),
            mock.patch.object(
                live_smoke,
                "_load_server_payloads",
                return_value=({"default_checkpoint": "SD15\\BravNew.safetensors", "checkpoints": []}, {"presets": []}),
            ),
            mock.patch.object(
                live_smoke,
                "_run_controlnet_validation_lane",
                return_value=(["controlnet error"], []),
            ),
            mock.patch.object(
                live_smoke,
                "_run_adetailer_validation_lane",
                return_value=(["adetailer error"], []),
            ),
            mock.patch.object(
                live_smoke,
                "_run_auxiliary_pipeline_validation_lane",
                return_value=(["auxiliary error"], []),
            ),
            mock.patch.object(
                live_smoke,
                "_run_xyz_plot_validation_lane",
                return_value=(["xyz error"], []),
            ),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = live_smoke.main()

        self.assertEqual(result, 0)

    def test_main_catalog_report_only_returns_zero_on_catalog_errors(self) -> None:
        with (
            mock.patch.object(
                sys,
                "argv",
                ["run_live_smoke_tests.py", "--report-only"],
            ),
            mock.patch.object(
                live_smoke,
                "_load_bootstrap_payload",
                return_value=_build_bootstrap_payload(),
            ),
            mock.patch.object(
                live_smoke,
                "_load_server_payloads",
                return_value=({"diffusion_models": [], "text_encoders": [], "catalog": {}}, {"presets": []}),
            ),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = live_smoke.main()

        self.assertEqual(result, 0)


class LiveSmokeAuxiliaryContractTests(unittest.TestCase):
    def test_validate_route_contract_payload_reports_contract_drift(self) -> None:
        probe = live_smoke.LiveRouteContractProbe(
            surface="extras_run",
            route_path="/rookieui/extras/run",
            local_contract_version="r119-20260417",
        )

        errors = live_smoke._validate_route_contract_payload(
            probe,
            {
                "service": "rookieui",
                "status": "ok",
                "contract": {
                    "surface": "extras_run",
                    "version": "r118-20260416",
                },
            },
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("host='r118-20260416'", errors[0])

    def test_validate_route_contract_payload_accepts_matching_payload(self) -> None:
        probe = live_smoke.LiveRouteContractProbe(
            surface="queue_snapshot_and_job_lookup",
            route_path="/rookieui/queue",
            local_contract_version="r119-20260417",
        )

        errors = live_smoke._validate_route_contract_payload(
            probe,
            {
                "service": "rookieui",
                "status": "ok",
                "contract": {
                    "surface": "queue_snapshot_and_job_lookup",
                    "version": "r119-20260417",
                },
            },
        )

        self.assertEqual(errors, [])

    def test_run_auxiliary_contract_smoke_validates_all_probe_responses(self) -> None:
        probes = [
            live_smoke.LiveRouteContractProbe(
                surface="queue_snapshot_and_job_lookup",
                route_path="/rookieui/queue",
                local_contract_version="r119-20260417",
            ),
            live_smoke.LiveRouteContractProbe(
                surface="pnginfo_parse_inspect",
                route_path="/rookieui/pnginfo/parse",
                local_contract_version="r119-20260417",
                method="POST",
                payload={"image_data": "data:image/png;base64,abc"},
            ),
        ]

        with (
            mock.patch.object(live_smoke, "_build_auxiliary_contract_probes", return_value=probes),
            mock.patch.object(
                live_smoke,
                "_request_json",
                side_effect=[
                    {
                        "service": "rookieui",
                        "status": "ok",
                        "contract": {
                            "surface": "queue_snapshot_and_job_lookup",
                            "version": "r119-20260417",
                        },
                    },
                    {
                        "service": "rookieui",
                        "status": "ok",
                        "contract": {
                            "surface": "pnginfo_parse_inspect",
                            "version": "r119-20260417",
                        },
                    },
                ],
            ),
        ):
            errors = live_smoke._run_auxiliary_contract_smoke(
                "http://127.0.0.1:8188",
                request_timeout_seconds=30.0,
            )

        self.assertEqual(errors, [])

    def test_main_auxiliary_contracts_report_only_returns_zero_on_contract_errors(self) -> None:
        with (
            mock.patch.object(
                sys,
                "argv",
                ["run_live_smoke_tests.py", "--validation-mode", "auxiliary-contracts", "--report-only"],
            ),
            mock.patch.object(
                live_smoke,
                "_load_bootstrap_payload",
                return_value=_build_bootstrap_payload(),
            ),
            mock.patch.object(
                live_smoke,
                "_run_auxiliary_contract_smoke",
                return_value=["surface 'queue_snapshot_and_job_lookup' contract mismatch"],
            ),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = live_smoke.main()

        self.assertEqual(result, 0)


class LiveSmokeControlNetTests(unittest.TestCase):
    def test_build_controlnet_host_context_selects_sd15_and_canny_defaults(self) -> None:
        context, errors = live_smoke._build_controlnet_host_context(
            {"checkpoints": ["SD15\\BravNew.safetensors"]},
            {
                "contract": {"version": live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION},
                "model_list": ["control_v11p_sd15_canny.safetensors"],
            },
            {
                "contract": {"version": live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION},
                "module_list": ["none", "canny"],
            },
            {
                "contract": {"version": live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION},
                "control_types": {
                    "Canny": {
                        "default_option": "canny",
                        "default_model": "control_v11p_sd15_canny.safetensors",
                    }
                },
            },
            ["sd15", "sdxl"],
        )

        self.assertEqual(errors, [])
        assert context is not None
        self.assertEqual(context.profile_id, "sd15")
        self.assertEqual(context.checkpoint_name, "SD15\\BravNew.safetensors")
        self.assertEqual(context.base_family, "sd15")
        self.assertEqual(context.control_type, "Canny")
        self.assertEqual(context.module_name, "canny")
        self.assertEqual(context.model_name, "control_v11p_sd15_canny.safetensors")

    def test_build_controlnet_host_context_prefers_sd15_model_over_sdxl_default(self) -> None:
        context, errors = live_smoke._build_controlnet_host_context(
            {"checkpoints": ["SD15\\BravNew.safetensors"]},
            {
                "contract": {"version": live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION},
                "model_list": [
                    "Xinsir-Controlnet-Canny-sdxl_V2.safetensors",
                    "control_v11p_sd15_canny.safetensors",
                ],
            },
            {
                "contract": {"version": live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION},
                "module_list": ["none", "canny"],
            },
            {
                "contract": {"version": live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION},
                "control_types": {
                    "Canny": {
                        "default_option": "canny",
                        "default_model": "Xinsir-Controlnet-Canny-sdxl_V2.safetensors",
                        "model_list": [
                            "Xinsir-Controlnet-Canny-sdxl_V2.safetensors",
                            "control_v11p_sd15_canny.safetensors",
                        ],
                    }
                },
            },
            ["sd15", "sdxl"],
        )

        self.assertEqual(errors, [])
        assert context is not None
        self.assertEqual(context.profile_id, "sd15")
        self.assertEqual(context.model_name, "control_v11p_sd15_canny.safetensors")

    def test_build_controlnet_host_context_falls_back_to_sdxl_when_sd15_model_missing(self) -> None:
        context, errors = live_smoke._build_controlnet_host_context(
            {"checkpoints": ["SD15\\BravNew.safetensors", "SDXL\\Cutie_Slutty_Pony_v20.safetensors"]},
            {
                "contract": {"version": live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION},
                "model_list": ["Xinsir-Controlnet-Canny-sdxl_V2.safetensors"],
            },
            {
                "contract": {"version": live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION},
                "module_list": ["none", "canny"],
            },
            {
                "contract": {"version": live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION},
                "control_types": {
                    "Canny": {
                        "default_option": "canny",
                        "default_model": "Xinsir-Controlnet-Canny-sdxl_V2.safetensors",
                        "model_list": ["Xinsir-Controlnet-Canny-sdxl_V2.safetensors"],
                    }
                },
            },
            ["sd15", "pony", "sdxl"],
        )

        self.assertEqual(errors, [])
        assert context is not None
        self.assertEqual(context.profile_id, "pony")
        self.assertEqual(context.checkpoint_name, "SDXL\\Cutie_Slutty_Pony_v20.safetensors")
        self.assertEqual(context.base_family, "sdxl")
        self.assertEqual(context.model_name, "Xinsir-Controlnet-Canny-sdxl_V2.safetensors")

    def test_validate_controlnet_host_sync_reports_contract_drift(self) -> None:
        errors = live_smoke._validate_controlnet_host_sync(
            live_smoke.ControlNetHostContext(
                profile_id="sd15",
                checkpoint_name="SD15\\BravNew.safetensors",
                base_family="sd15",
                control_type="Canny",
                module_name="canny",
                model_name="control_v11p_sd15_canny.safetensors",
                host_contract_version="r72-20260412",
                local_contract_version="r119-20260417",
            )
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("host='r72-20260412'", errors[0])

    def test_validate_controlnet_detect_response_accepts_fallback_backend(self) -> None:
        context = live_smoke.ControlNetHostContext(
            profile_id="sd15",
            checkpoint_name="SD15\\BravNew.safetensors",
            base_family="sd15",
            control_type="Canny",
            module_name="canny",
            model_name="control_v11p_sd15_canny.safetensors",
            host_contract_version=live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION,
            local_contract_version=live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION,
        )

        errors = live_smoke._validate_controlnet_detect_response(
            context,
            {
                "service": "rookieui",
                "status": "ok",
                "contract": {"version": live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION},
                "module": "canny",
                "requested_controlnet_model": "control_v11p_sd15_canny.safetensors",
                "detect_backend": "rookieui_internal_fallback",
                "warning_codes": ["CONTROLNET_PREPROCESSOR_HOST_FALLBACK"],
                "images": ["data:image/png;base64,abc"],
            },
        )

        self.assertEqual(errors, [])

    def test_validate_controlnet_dry_run_case_response_accepts_expected_topology(self) -> None:
        context = live_smoke.ControlNetHostContext(
            profile_id="sd15",
            checkpoint_name="SD15\\BravNew.safetensors",
            base_family="sd15",
            control_type="Canny",
            module_name="canny",
            model_name="control_v11p_sd15_canny.safetensors",
            host_contract_version=live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION,
            local_contract_version=live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION,
        )
        case = live_smoke._build_controlnet_dry_run_cases(context)[0]

        errors = live_smoke._validate_controlnet_dry_run_case_response(
            context,
            case,
            {
                "workflow_kind": "txt2img-sd15",
                "submission": {"accepted": False, "mode": "dry-run"},
                "normalized_request": {
                    "controlnet_units": [
                        {
                            "module": "canny",
                            "model": "control_v11p_sd15_canny.safetensors",
                            "control_type": "Canny",
                            "image_asset": "rookieui_controlnet_input_1.png",
                        }
                    ]
                },
                "workflow": {
                    "5": {"class_type": "RookieUIControlNetPreprocess", "inputs": {"module": "canny"}},
                    "6": {"class_type": "DiffControlNetLoader", "inputs": {}},
                    "7": {
                        "class_type": "RookieUIControlNetApplyNativeAdvanced",
                        "inputs": {"weight_preset": "soft", "layer_weights_json": "[0.2, 0.4, 0.8]"},
                    },
                    "8": {
                        "class_type": "RookieUIControlNetApplyNativeAdvanced",
                        "inputs": {"weight_preset": "soft", "layer_weights_json": "[0.2, 0.4, 0.8]"},
                    },
                },
            },
        )

        self.assertEqual(errors, [])

    def test_main_controlnet_report_only_returns_zero_on_contract_drift(self) -> None:
        context = live_smoke.ControlNetHostContext(
            profile_id="sd15",
            checkpoint_name="SD15\\BravNew.safetensors",
            base_family="sd15",
            control_type="Canny",
            module_name="canny",
            model_name="control_v11p_sd15_canny.safetensors",
            host_contract_version="r72-20260412",
            local_contract_version=live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION,
        )

        with (
            mock.patch.object(
                sys,
                "argv",
                ["run_live_smoke_tests.py", "--validation-mode", "controlnet", "--report-only"],
            ),
            mock.patch.object(
                live_smoke,
                "_load_bootstrap_payload",
                return_value=_build_bootstrap_payload(),
            ),
            mock.patch.object(
                live_smoke,
                "_load_server_payloads",
                return_value=({"checkpoints": []}, {"presets": []}),
            ),
            mock.patch.object(
                live_smoke,
                "_load_controlnet_payloads",
                return_value=({}, {}, {}),
            ),
            mock.patch.object(
                live_smoke,
                "_build_controlnet_host_context",
                return_value=(context, []),
            ),
            mock.patch.object(
                live_smoke,
                "_run_controlnet_detect_smoke",
                return_value=[],
            ),
            mock.patch.object(
                live_smoke,
                "_run_controlnet_dry_run_smoke",
                return_value=[],
            ),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = live_smoke.main()

        self.assertEqual(result, 0)


class LiveSmokeADetailerTests(unittest.TestCase):
    def test_build_adetailer_host_context_selects_ready_detector_and_inherits_controlnet_profile(self) -> None:
        controlnet_context = live_smoke.ControlNetHostContext(
            profile_id="pony",
            checkpoint_name="SDXL\\Cutie_Slutty_Pony_v20.safetensors",
            base_family="sdxl",
            control_type="Canny",
            module_name="canny",
            model_name="Xinsir-Controlnet-Canny-sdxl_V2.safetensors",
            host_contract_version=live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION,
            local_contract_version=live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION,
        )

        context, errors = live_smoke._build_adetailer_host_context(
            {
                "contract": {"version": live_smoke._LOCAL_ADETAILER_CONTRACT_VERSION},
                "controlnet_modes": ["none", "passthrough", "custom"],
                "controlnet_model_list": ["Xinsir-Controlnet-Canny-sdxl_V2.safetensors"],
                "controlnet_module_list": ["None", "canny"],
                "detectors": [
                    {"id": "None", "family": "none"},
                    {"id": "face_yolov8n.pt", "family": "ultralytics_bbox"},
                    {"id": "mediapipe_face_full", "family": "mediapipe_face"},
                ],
                "availability": {
                    "detector_runtime": {
                        "none": "disabled",
                        "ultralytics_bbox": "native_runtime_model_unavailable",
                        "mediapipe_face": "native_runtime_ready",
                    }
                },
            },
            controlnet_context,
        )

        self.assertEqual(errors, [])
        assert context is not None
        self.assertEqual(context.profile_id, "pony")
        self.assertEqual(context.base_family, "sdxl")
        self.assertEqual(context.checkpoint_name, "SDXL\\Cutie_Slutty_Pony_v20.safetensors")
        self.assertEqual(context.detector_name, "mediapipe_face_full")
        self.assertEqual(context.detector_family, "mediapipe_face")
        self.assertEqual(context.detector_runtime_state, "native_runtime_ready")
        self.assertEqual(context.controlnet_model, "Xinsir-Controlnet-Canny-sdxl_V2.safetensors")

    def test_validate_adetailer_host_sync_reports_contract_drift(self) -> None:
        errors = live_smoke._validate_adetailer_host_sync(
            live_smoke.ADetailerHostContext(
                profile_id="sd15",
                checkpoint_name="SD15\\BravNew.safetensors",
                base_family="sd15",
                detector_name="face_yolov8n.pt",
                detector_family="ultralytics_bbox",
                detector_runtime_state="native_runtime_model_unavailable",
                controlnet_control_type="Canny",
                controlnet_module="canny",
                controlnet_model="control_v11p_sd15_canny.safetensors",
                host_contract_version="r73-20260413",
                local_contract_version=live_smoke._LOCAL_ADETAILER_CONTRACT_VERSION,
            )
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("host='r73-20260413'", errors[0])

    def test_validate_adetailer_dry_run_case_response_accepts_refinement_topology(self) -> None:
        context = live_smoke.ADetailerHostContext(
            profile_id="sd15",
            checkpoint_name="SD15\\BravNew.safetensors",
            base_family="sd15",
            detector_name="mediapipe_face_full",
            detector_family="mediapipe_face",
            detector_runtime_state="native_runtime_ready",
            controlnet_control_type="Canny",
            controlnet_module="canny",
            controlnet_model="control_v11p_sd15_canny.safetensors",
            host_contract_version=live_smoke._LOCAL_ADETAILER_CONTRACT_VERSION,
            local_contract_version=live_smoke._LOCAL_ADETAILER_CONTRACT_VERSION,
        )
        case = live_smoke._build_adetailer_dry_run_cases(context)[0]

        errors = live_smoke._validate_adetailer_dry_run_case_response(
            context,
            case,
            {
                "workflow_kind": "txt2img-sd15",
                "submission": {"accepted": False, "mode": "dry-run"},
                "normalized_request": {
                    "controlnet_units": [{"model": "control_v11p_sd15_canny.safetensors"}],
                    "adetailer": {
                        "enabled": True,
                        "skip_img2img": False,
                        "warning_codes": [],
                        "units": [
                            {
                                "detector": "mediapipe_face_full",
                                "detector_family": "mediapipe_face",
                            }
                        ],
                        "diagnostics": {
                            "primary_controlnet_unit_count": 1,
                        },
                    },
                },
                "workflow": {
                    "1": {"class_type": "VAEDecode", "inputs": {}},
                    "2": {
                        "class_type": "RookieUIADetailerDetectMask",
                        "inputs": {"detector": "mediapipe_face_full", "detector_family": "mediapipe_face"},
                    },
                    "3": {"class_type": "RookieUIVAEEncodeForInpaint", "inputs": {}},
                    "4": {"class_type": "KSampler", "inputs": {}},
                    "5": {"class_type": "KSampler", "inputs": {}},
                    "6": {"class_type": "RookieUIControlNetApplyNativeAdvanced", "inputs": {}},
                    "7": {"class_type": "RookieUIControlNetApplyNativeAdvanced", "inputs": {}},
                    "8": {"class_type": "VAEDecode", "inputs": {}},
                    "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0]}},
                },
            },
        )

        self.assertEqual(errors, [])

    def test_validate_adetailer_dry_run_case_response_accepts_skip_img2img_topology(self) -> None:
        context = live_smoke.ADetailerHostContext(
            profile_id="sd15",
            checkpoint_name="SD15\\BravNew.safetensors",
            base_family="sd15",
            detector_name="mediapipe_face_full",
            detector_family="mediapipe_face",
            detector_runtime_state="native_runtime_ready",
            controlnet_control_type="Canny",
            controlnet_module="canny",
            controlnet_model="control_v11p_sd15_canny.safetensors",
            host_contract_version=live_smoke._LOCAL_ADETAILER_CONTRACT_VERSION,
            local_contract_version=live_smoke._LOCAL_ADETAILER_CONTRACT_VERSION,
        )
        case = live_smoke._build_adetailer_dry_run_cases(context)[-1]

        errors = live_smoke._validate_adetailer_dry_run_case_response(
            context,
            case,
            {
                "workflow_kind": "img2img-sd15",
                "submission": {"accepted": False, "mode": "dry-run"},
                "normalized_request": {
                    "adetailer": {
                        "enabled": True,
                        "skip_img2img": True,
                        "warning_codes": [],
                        "units": [
                            {
                                "detector": "mediapipe_face_full",
                                "detector_family": "mediapipe_face",
                            }
                        ],
                        "diagnostics": {
                            "primary_controlnet_unit_count": 0,
                        },
                    },
                },
                "workflow": {
                    "1": {"class_type": "VAEDecode", "inputs": {}},
                    "2": {"class_type": "KSampler", "inputs": {}},
                    "3": {"class_type": "SaveImage", "inputs": {"images": ["1", 0]}},
                },
            },
        )

        self.assertEqual(errors, [])

    def test_main_adetailer_report_only_returns_zero_on_contract_drift(self) -> None:
        controlnet_context = live_smoke.ControlNetHostContext(
            profile_id="sd15",
            checkpoint_name="SD15\\BravNew.safetensors",
            base_family="sd15",
            control_type="Canny",
            module_name="canny",
            model_name="control_v11p_sd15_canny.safetensors",
            host_contract_version=live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION,
            local_contract_version=live_smoke._LOCAL_CONTROLNET_CONTRACT_VERSION,
        )
        adetailer_context = live_smoke.ADetailerHostContext(
            profile_id="sd15",
            checkpoint_name="SD15\\BravNew.safetensors",
            base_family="sd15",
            detector_name="face_yolov8n.pt",
            detector_family="ultralytics_bbox",
            detector_runtime_state="native_runtime_model_unavailable",
            controlnet_control_type="Canny",
            controlnet_module="canny",
            controlnet_model="control_v11p_sd15_canny.safetensors",
            host_contract_version="r73-20260413",
            local_contract_version=live_smoke._LOCAL_ADETAILER_CONTRACT_VERSION,
        )

        with (
            mock.patch.object(
                sys,
                "argv",
                ["run_live_smoke_tests.py", "--validation-mode", "adetailer", "--report-only"],
            ),
            mock.patch.object(
                live_smoke,
                "_load_bootstrap_payload",
                return_value=_build_bootstrap_payload(),
            ),
            mock.patch.object(
                live_smoke,
                "_load_server_payloads",
                return_value=({"checkpoints": []}, {"presets": []}),
            ),
            mock.patch.object(
                live_smoke,
                "_load_controlnet_payloads",
                return_value=({}, {}, {}),
            ),
            mock.patch.object(
                live_smoke,
                "_load_adetailer_catalog_payload",
                return_value={},
            ),
            mock.patch.object(
                live_smoke,
                "_build_controlnet_host_context",
                return_value=(controlnet_context, []),
            ),
            mock.patch.object(
                live_smoke,
                "_build_adetailer_host_context",
                return_value=(adetailer_context, []),
            ),
            mock.patch.object(
                live_smoke,
                "_build_adetailer_dry_run_cases",
                return_value=[],
            ),
            mock.patch.object(
                live_smoke,
                "_run_adetailer_dry_run_smoke",
                return_value=[],
            ),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = live_smoke.main()

        self.assertEqual(result, 0)
