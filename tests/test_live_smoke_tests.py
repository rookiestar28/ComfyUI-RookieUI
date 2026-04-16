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
    def test_default_profiles_for_auxiliary_contracts_is_empty(self) -> None:
        self.assertEqual(live_smoke._default_profiles_for_mode("auxiliary-contracts"), "")

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
