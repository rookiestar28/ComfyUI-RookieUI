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
                    "codeformer is not available inside the RookieUI workspace pipeline yet; the request will continue without face restoration."
                ],
                "output_assets": ["rookieui_extras_1.png"],
                "preview_asset": "rookieui_extras_1.png",
                "preview_data_url": "data:image/png;base64,abc",
            }
        )

        self.assertEqual(errors, [])

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
