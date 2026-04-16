from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    # CRITICAL: keep repo root on sys.path when running `python scripts/run_live_smoke_tests.py`; otherwise the smoke lane cannot import the local RookieUI package or golden fixtures outside editable-install contexts.
    sys.path.insert(0, str(_REPO_ROOT))

from rookieui.services.parity_matrix import get_parity_profile
from rookieui.services.prompt_capability_matrix import build_prompt_capability_matrix_payload
from tests.prompt_parity_fixtures import (
    ALL_PROMPT_FEATURES,
    ExpectedEmbeddingRef,
    PROMPT_PARITY_GOLDEN_CASES,
    PromptParityGoldenCase,
)


_NON_SD_DIFFUSION_PROFILES: tuple[str, ...] = (
    "flux",
    "qwen_image",
    "klein",
    "lumina",
    "zit",
    "wan",
    "anima",
)
_SD_PROMPT_PARITY_PROFILES: tuple[str, ...] = ("sd15", "pony", "illustrious", "noob", "sdxl")
_SDXL_PROMPT_PARITY_PROFILES: tuple[str, ...] = ("pony", "illustrious", "noob", "sdxl")
_LOCAL_PROMPT_CONTRACT_VERSION = str(build_prompt_capability_matrix_payload().get("contract_version", "")).strip()


@dataclass(frozen=True)
class PromptParityHostContext:
    sd15_checkpoint: str
    sdxl_profile: str
    sdxl_checkpoint: str
    embedding_name: str | None
    host_contract_version: str
    local_contract_version: str


@dataclass(frozen=True)
class LivePromptParityCase:
    fixture: PromptParityGoldenCase
    checkpoint_name: str
    execute: bool = False


def _env_flag(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_profiles_for_mode(validation_mode: str) -> str:
    if validation_mode == "prompt-parity":
        return ",".join(_SD_PROMPT_PARITY_PROFILES)
    return ",".join(_NON_SD_DIFFUSION_PROFILES)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run optional live RookieUI smoke checks against a real ComfyUI host. "
            "This lane validates profile-to-model/text-encoder alignment and can optionally "
            "submit/poll lightweight txt2img runs for non-SD diffusion profiles."
        )
    )
    parser.add_argument(
        "--validation-mode",
        choices=("catalog", "prompt-parity"),
        default=os.getenv("ROOKIEUI_LIVE_VALIDATION_MODE", "catalog").strip().lower() or "catalog",
        help="Validation lane to run (default: %(default)s).",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("ROOKIEUI_LIVE_BASE_URL", "http://127.0.0.1:8188"),
        help="ComfyUI host base URL (default: %(default)s).",
    )
    parser.add_argument(
        "--profiles",
        default=os.getenv("ROOKIEUI_LIVE_SMOKE_PROFILES", "").strip(),
        help="Comma-separated profile IDs to validate (mode-specific defaults apply when omitted).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        default=_env_flag("ROOKIEUI_LIVE_SMOKE_EXECUTE", default=False),
        help="Submit/poll real txt2img runs in addition to catalog contract checks.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        default=_env_flag("ROOKIEUI_LIVE_REPORT_ONLY", default=False),
        help="Report stale-host or parity mismatches without failing the process.",
    )
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=float(os.getenv("ROOKIEUI_LIVE_REQUEST_TIMEOUT_SECONDS", "30")),
        help="HTTP request timeout in seconds (default: %(default)s).",
    )
    parser.add_argument(
        "--poll-timeout-seconds",
        type=float,
        default=float(os.getenv("ROOKIEUI_LIVE_POLL_TIMEOUT_SECONDS", "180")),
        help="Per-profile queue poll timeout in seconds when --execute is enabled (default: %(default)s).",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=float(os.getenv("ROOKIEUI_LIVE_POLL_INTERVAL_SECONDS", "2")),
        help="Queue polling interval in seconds when --execute is enabled (default: %(default)s).",
    )
    return parser


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _request_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout_seconds: float,
) -> dict[str, Any]:
    request_data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        request_data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=request_data, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:  # pragma: no cover - runtime path depends on host state.
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover - runtime path depends on host reachability.
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc


def _load_server_payloads(base_url: str, timeout_seconds: float) -> tuple[dict[str, Any], dict[str, Any]]:
    models = _request_json(
        "GET",
        f"{base_url}/rookieui/models",
        timeout_seconds=timeout_seconds,
    )
    presets = _request_json(
        "GET",
        f"{base_url}/rookieui/presets",
        timeout_seconds=timeout_seconds,
    )
    return models, presets


def _load_capabilities_payload(base_url: str, timeout_seconds: float) -> dict[str, Any]:
    return _request_json(
        "GET",
        f"{base_url}/rookieui/capabilities",
        timeout_seconds=timeout_seconds,
    )


def _parse_profiles(raw_profiles: str) -> list[str]:
    profiles = [segment.strip() for segment in raw_profiles.split(",") if segment.strip()]
    return list(dict.fromkeys(profiles))


def _get_fixture(case_id: str) -> PromptParityGoldenCase:
    for fixture in PROMPT_PARITY_GOLDEN_CASES:
        if fixture.case_id == case_id:
            return fixture
    raise KeyError(f"Unknown prompt parity fixture: {case_id}")


def _iter_string_list(payload: object, key: str) -> list[str]:
    if not isinstance(payload, dict):
        return []
    values = payload.get(key)
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if isinstance(value, str) and str(value).strip()]


def _select_checkpoint_by_keywords(
    checkpoints: list[str],
    *,
    prefix: str,
    keywords: tuple[str, ...] = (),
) -> str:
    normalized_prefix = prefix.lower()
    candidates = [selector for selector in checkpoints if selector.lower().startswith(normalized_prefix)]
    if not candidates:
        return ""
    if keywords:
        for keyword in keywords:
            lowered_keyword = keyword.lower()
            for selector in candidates:
                if lowered_keyword in selector.lower():
                    return selector
    return candidates[0]


def _build_prompt_parity_host_context(
    models_payload: dict[str, Any],
    capabilities_payload: dict[str, Any],
    preferred_profiles: list[str],
) -> tuple[PromptParityHostContext | None, list[str]]:
    errors: list[str] = []
    checkpoints = _iter_string_list(models_payload, "checkpoints")
    embeddings = _iter_string_list(models_payload, "embeddings")
    host_prompt_semantics = capabilities_payload.get("prompt_semantics")
    host_contract_version = ""
    if isinstance(host_prompt_semantics, dict):
        host_contract_version = str(host_prompt_semantics.get("contract_version", "")).strip()

    sd15_checkpoint = _select_checkpoint_by_keywords(checkpoints, prefix="SD15\\")
    if not sd15_checkpoint:
        errors.append("live host did not expose any SD15 checkpoint selectors in /rookieui/models.checkpoints.")

    sdxl_profile = ""
    sdxl_checkpoint = ""
    preferred_sdxl_profiles = [
        profile_id
        for profile_id in preferred_profiles
        if profile_id in _SDXL_PROMPT_PARITY_PROFILES
    ] or list(_SDXL_PROMPT_PARITY_PROFILES)
    profile_keywords = {
        "pony": ("pony",),
        "illustrious": ("illustrious", "illu"),
        "noob": ("noob",),
        "sdxl": (),
    }
    for profile_id in preferred_sdxl_profiles:
        checkpoint_name = _select_checkpoint_by_keywords(
            checkpoints,
            prefix="SDXL\\",
            keywords=profile_keywords.get(profile_id, ()),
        )
        if checkpoint_name:
            sdxl_profile = profile_id
            sdxl_checkpoint = checkpoint_name
            break
    if not sdxl_profile or not sdxl_checkpoint:
        errors.append(
            "live host did not expose a healthy SDXL-family checkpoint selector for any of: "
            f"{', '.join(preferred_sdxl_profiles)}."
        )

    context = None
    if not errors:
        context = PromptParityHostContext(
            sd15_checkpoint=sd15_checkpoint,
            sdxl_profile=sdxl_profile,
            sdxl_checkpoint=sdxl_checkpoint,
            embedding_name=embeddings[0] if embeddings else None,
            host_contract_version=host_contract_version,
            local_contract_version=_LOCAL_PROMPT_CONTRACT_VERSION,
        )
    return context, errors


def _build_prompt_parity_cases(context: PromptParityHostContext) -> list[LivePromptParityCase]:
    sd15_attention = _get_fixture("sd15_attention_brackets")
    sd15_long_comma_chunk = _get_fixture("sd15_long_comma_chunk")
    sd15_break_schedule = _get_fixture("sd15_break_schedule")
    sd15_alternate_schedule = _get_fixture("sd15_alternate_schedule")
    sd15_and_multi_cond = _get_fixture("sd15_and_multi_cond")
    sd15_missing_explicit_embedding = _get_fixture("sd15_missing_explicit_embedding")

    cases = [
        LivePromptParityCase(sd15_attention, checkpoint_name=context.sd15_checkpoint, execute=True),
        LivePromptParityCase(sd15_long_comma_chunk, checkpoint_name=context.sd15_checkpoint, execute=True),
        LivePromptParityCase(sd15_break_schedule, checkpoint_name=context.sd15_checkpoint),
        LivePromptParityCase(sd15_alternate_schedule, checkpoint_name=context.sd15_checkpoint),
        LivePromptParityCase(sd15_and_multi_cond, checkpoint_name=context.sd15_checkpoint),
        LivePromptParityCase(sd15_missing_explicit_embedding, checkpoint_name=context.sd15_checkpoint),
    ]

    if context.embedding_name:
        embedding_fixture = replace(
            _get_fixture("sd15_embedding_bare"),
            prompt=f"portrait {context.embedding_name} dramatic light",
            inventory_embeddings=(context.embedding_name,),
            expected_cleaned_prompt=f"portrait embedding:{context.embedding_name} dramatic light",
            expected_prompt_embeddings=(
                ExpectedEmbeddingRef(
                    canonical_token=f"embedding:{context.embedding_name}",
                    exists=True,
                    syntax="bare",
                ),
            ),
            expected_prompt_workflow_fragments=(f"embedding:{context.embedding_name}",),
        )
        cases.append(
            LivePromptParityCase(
                embedding_fixture,
                checkpoint_name=context.sd15_checkpoint,
                execute=True,
            )
        )

        sdxl_fixture = replace(
            _get_fixture("pony_mixed_compound_with_negative_embedding"),
            profile=context.sdxl_profile,
            inventory_embeddings=(context.embedding_name,),
            prompt=f"((hero)) AND {context.embedding_name} BREAK [day:night:0.5]",
            negative_prompt=f"embedding:{context.embedding_name} [low quality]",
            expected_cleaned_prompt=f"((hero)) AND embedding:{context.embedding_name} BREAK [day:night:0.5]",
            expected_cleaned_negative_prompt=f"embedding:{context.embedding_name} [low quality]",
            expected_prompt_embeddings=(
                ExpectedEmbeddingRef(
                    canonical_token=f"embedding:{context.embedding_name}",
                    exists=True,
                    syntax="bare",
                ),
            ),
            expected_negative_embeddings=(
                ExpectedEmbeddingRef(
                    canonical_token=f"embedding:{context.embedding_name}",
                    exists=True,
                    syntax="explicit",
                ),
            ),
            expected_prompt_workflow_fragments=(f"embedding:{context.embedding_name}",),
            expected_negative_workflow_fragments=(f"embedding:{context.embedding_name}",),
        )
    else:
        sdxl_fixture = PromptParityGoldenCase(
            case_id=f"{context.sdxl_profile}_mixed_compound_without_embedding",
            profile=context.sdxl_profile,
            prompt="((hero)) BREAK [day:night:0.5]",
            negative_prompt="[low quality]",
            expected_cleaned_prompt="((hero)) BREAK [day:night:0.5]",
            expected_cleaned_negative_prompt="[low quality]",
            expected_warning_codes=(
                "PROMPT_BREAK_DETECTED",
                "PROMPT_SCHEDULE_DETECTED",
                "PROMPT_ATTENTION_DETECTED",
            ),
            expected_prompt_features=(
                "break_chunks",
                "prompt_scheduling",
                "attention_weighting",
            ),
            expected_negative_features=("attention_weighting",),
            expected_encoder_class="RookieUIA1111CLIPTextEncodeSDXL",
            expect_conditioning_combine=True,
            expect_timestep_range=True,
        )
    cases.append(
        LivePromptParityCase(
            sdxl_fixture,
            checkpoint_name=context.sdxl_checkpoint,
            execute=True,
        )
    )
    return cases


def _validate_catalog_contract(
    models_payload: dict[str, Any],
    presets_payload: dict[str, Any],
    target_profiles: list[str],
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    errors: list[str] = []
    presets = presets_payload.get("presets", [])
    presets_by_id = {
        str(preset.get("id", "")).strip(): preset
        for preset in presets
        if isinstance(preset, dict) and str(preset.get("id", "")).strip()
    }
    diffusion_models = [
        str(model).strip()
        for model in models_payload.get("diffusion_models", [])
        if isinstance(model, str) and str(model).strip()
    ]
    text_encoders = [
        str(model).strip()
        for model in models_payload.get("text_encoders", [])
        if isinstance(model, str) and str(model).strip()
    ]
    category_by_family = (
        ((models_payload.get("catalog") or {}).get("primary_model_category_by_family"))
        if isinstance(models_payload.get("catalog"), dict)
        else {}
    )
    if not isinstance(category_by_family, dict):
        category_by_family = {}

    for profile_id in target_profiles:
        preset = presets_by_id.get(profile_id)
        if preset is None:
            errors.append(f"profile '{profile_id}' missing in /rookieui/presets payload.")
            continue
        if category_by_family.get(profile_id) != "diffusion_models":
            errors.append(
                f"profile '{profile_id}' expected category 'diffusion_models' but got "
                f"'{category_by_family.get(profile_id)}'."
            )

        checkpoint_name = str(preset.get("checkpoint_name", "")).strip()
        if checkpoint_name not in diffusion_models:
            errors.append(
                f"profile '{profile_id}' checkpoint '{checkpoint_name}' not found in /rookieui/models.diffusion_models."
            )

        text_encoder_name = str(preset.get("text_encoder_name", "")).strip()
        if text_encoder_name and text_encoder_name not in text_encoders:
            errors.append(
                f"profile '{profile_id}' text encoder '{text_encoder_name}' not found in /rookieui/models.text_encoders."
            )

        lowered_text_encoder = text_encoder_name.lower()
        # CRITICAL: non-Qwen diffusion profiles must not inherit Qwen text encoders; this exact mismatch caused runtime crashes.
        if profile_id == "qwen_image":
            if "qwen" not in lowered_text_encoder:
                errors.append(
                    f"profile '{profile_id}' expected a Qwen text encoder but got '{text_encoder_name}'."
                )
        elif "qwen" in lowered_text_encoder:
            errors.append(
                f"profile '{profile_id}' must not default to a Qwen text encoder ('{text_encoder_name}')."
            )

    return errors, presets_by_id


def _build_txt2img_payload(profile_id: str, preset: dict[str, Any], client_id: str) -> dict[str, Any]:
    return {
        "prompt": f"[rookieui live smoke] {profile_id}",
        "negative_prompt": "",
        "profile": profile_id,
        "checkpoint_name": str(preset.get("checkpoint_name", "")).strip(),
        "vae_name": str(preset.get("vae_name", "Automatic")).strip() or "Automatic",
        "text_encoder_name": str(preset.get("text_encoder_name", "")).strip(),
        "width": int(preset.get("width", 1024)),
        "height": int(preset.get("height", 1024)),
        "steps": 1,
        "cfg_scale": float(preset.get("cfg_scale", 1.0)),
        "sampler_name": str(preset.get("sampler_name", "euler")).strip() or "euler",
        "scheduler_name": str(preset.get("scheduler_name", "normal")).strip() or "normal",
        "batch_count": 1,
        "seed": 1,
        "hires_enabled": False,
        "client_id": client_id,
    }


def _build_prompt_parity_request_payload(case: LivePromptParityCase) -> dict[str, Any]:
    profile = get_parity_profile(case.fixture.profile)
    requested_steps = (
        max(4, profile.default_steps)
        if case.fixture.expect_conditioning_combine or case.fixture.expect_timestep_range
        else 1
    )
    return {
        "prompt": case.fixture.prompt,
        "negative_prompt": case.fixture.negative_prompt,
        "profile": case.fixture.profile,
        "checkpoint_name": case.checkpoint_name,
        "vae_name": "Automatic",
        "text_encoder_name": "Automatic",
        "width": profile.default_width,
        "height": profile.default_height,
        "steps": requested_steps,
        "cfg_scale": profile.default_cfg_scale,
        "sampler_name": profile.default_sampler,
        "scheduler_name": profile.default_scheduler,
        "batch_count": 1,
        "seed": 1,
        "hires_enabled": False,
        "dry_run": True,
    }


def _collect_encoder_texts(workflow: dict[str, Any], encoder_class: str) -> list[str]:
    texts: list[str] = []
    for node in workflow.values():
        if not isinstance(node, dict) or node.get("class_type") != encoder_class:
            continue
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue
        if encoder_class == "RookieUIA1111CLIPTextEncodeSDXL":
            for key in ("text_g", "text_l"):
                value = inputs.get(key)
                if isinstance(value, str):
                    texts.append(value)
            continue
        value = inputs.get("text")
        if isinstance(value, str):
            texts.append(value)
    return texts


def _append_feature_mismatch_errors(
    errors: list[str],
    payload: dict[str, Any],
    expected_features: tuple[str, ...],
    *,
    case_id: str,
    lane: str,
) -> None:
    features = payload.get("features")
    if not isinstance(features, dict):
        errors.append(f"{case_id} {lane}: semantic payload missing features map.")
        return
    for feature_name in ALL_PROMPT_FEATURES:
        actual_value = bool(features.get(feature_name))
        expected_value = feature_name in expected_features
        if actual_value != expected_value:
            errors.append(
                f"{case_id} {lane}: feature '{feature_name}' expected {expected_value} but got {actual_value}."
            )


def _append_embedding_mismatch_errors(
    errors: list[str],
    payload: dict[str, Any],
    expected_embeddings: tuple[ExpectedEmbeddingRef, ...],
    *,
    case_id: str,
    lane: str,
) -> None:
    actual_embeddings = payload.get("embeddings")
    if not isinstance(actual_embeddings, list):
        if expected_embeddings:
            errors.append(f"{case_id} {lane}: semantic payload missing embeddings list.")
        return
    if len(actual_embeddings) != len(expected_embeddings):
        errors.append(
            f"{case_id} {lane}: expected {len(expected_embeddings)} embeddings but got {len(actual_embeddings)}."
        )
        return
    for actual, expected in zip(actual_embeddings, expected_embeddings):
        if not isinstance(actual, dict):
            errors.append(f"{case_id} {lane}: embedding entry was not an object.")
            continue
        for key, expected_value in (
            ("canonical_token", expected.canonical_token),
            ("exists", expected.exists),
            ("syntax", expected.syntax),
        ):
            actual_value = actual.get(key)
            if actual_value != expected_value:
                errors.append(
                    f"{case_id} {lane}: embedding field '{key}' expected '{expected_value}' but got '{actual_value}'."
                )


def _validate_prompt_parity_case_response(case: LivePromptParityCase, response_payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    fixture = case.fixture
    submission = response_payload.get("submission")
    if not isinstance(submission, dict) or submission.get("mode") != "dry-run":
        errors.append(f"{fixture.case_id}: expected dry-run submission payload.")

    expected_workflow_kind = "txt2img-sdxl" if fixture.profile in _SDXL_PROMPT_PARITY_PROFILES else "txt2img-sd15"
    if response_payload.get("workflow_kind") != expected_workflow_kind:
        errors.append(
            f"{fixture.case_id}: expected workflow_kind '{expected_workflow_kind}' but got "
            f"'{response_payload.get('workflow_kind')}'."
        )

    normalized_request = response_payload.get("normalized_request")
    if not isinstance(normalized_request, dict):
        errors.append(f"{fixture.case_id}: response missing normalized_request.")
        return errors

    if normalized_request.get("prompt") != fixture.expected_cleaned_prompt:
        errors.append(
            f"{fixture.case_id}: expected cleaned prompt '{fixture.expected_cleaned_prompt}' but got "
            f"'{normalized_request.get('prompt')}'."
        )
    if normalized_request.get("negative_prompt") != fixture.expected_cleaned_negative_prompt:
        errors.append(
            f"{fixture.case_id}: expected cleaned negative prompt '{fixture.expected_cleaned_negative_prompt}' but got "
            f"'{normalized_request.get('negative_prompt')}'."
        )

    warning_codes = normalized_request.get("prompt_warning_codes")
    if not isinstance(warning_codes, list):
        errors.append(f"{fixture.case_id}: normalized_request.prompt_warning_codes missing.")
    else:
        for warning_code in fixture.expected_warning_codes:
            if warning_code not in warning_codes:
                errors.append(f"{fixture.case_id}: missing warning code '{warning_code}'.")

    prompt_semantics = normalized_request.get("prompt_semantics")
    negative_semantics = normalized_request.get("negative_prompt_semantics")
    if not isinstance(prompt_semantics, dict):
        errors.append(f"{fixture.case_id}: prompt_semantics missing.")
    else:
        _append_feature_mismatch_errors(
            errors,
            prompt_semantics,
            fixture.expected_prompt_features,
            case_id=fixture.case_id,
            lane="prompt",
        )
        if len(prompt_semantics.get("branches", [])) != fixture.expected_prompt_branch_count:
            errors.append(
                f"{fixture.case_id} prompt: expected {fixture.expected_prompt_branch_count} branches but got "
                f"{len(prompt_semantics.get('branches', []))}."
            )
        _append_embedding_mismatch_errors(
            errors,
            prompt_semantics,
            fixture.expected_prompt_embeddings,
            case_id=fixture.case_id,
            lane="prompt",
        )
    if not isinstance(negative_semantics, dict):
        errors.append(f"{fixture.case_id}: negative_prompt_semantics missing.")
    else:
        _append_feature_mismatch_errors(
            errors,
            negative_semantics,
            fixture.expected_negative_features,
            case_id=fixture.case_id,
            lane="negative",
        )
        if len(negative_semantics.get("branches", [])) != fixture.expected_negative_branch_count:
            errors.append(
                f"{fixture.case_id} negative: expected {fixture.expected_negative_branch_count} branches but got "
                f"{len(negative_semantics.get('branches', []))}."
            )
        _append_embedding_mismatch_errors(
            errors,
            negative_semantics,
            fixture.expected_negative_embeddings,
            case_id=fixture.case_id,
            lane="negative",
        )

    workflow = response_payload.get("workflow")
    if not isinstance(workflow, dict):
        errors.append(f"{fixture.case_id}: response missing workflow payload.")
        return errors

    class_types = {
        node.get("class_type")
        for node in workflow.values()
        if isinstance(node, dict)
    }
    if fixture.expected_encoder_class not in class_types:
        fallback_encoder = "CLIPTextEncodeSDXL" if fixture.expected_encoder_class.endswith("SDXL") else "CLIPTextEncode"
        if fallback_encoder in class_types:
            errors.append(
                f"{fixture.case_id}: expected '{fixture.expected_encoder_class}' but host emitted '{fallback_encoder}'. "
                "Live host appears to be running a pre-cutover RookieUI deployment."
            )
        else:
            errors.append(
                f"{fixture.case_id}: workflow missing expected encoder class '{fixture.expected_encoder_class}'."
            )
    if fixture.expect_conditioning_combine and "ConditioningCombine" not in class_types:
        errors.append(f"{fixture.case_id}: workflow missing ConditioningCombine.")
    if not fixture.expect_conditioning_combine and "ConditioningCombine" in class_types:
        errors.append(f"{fixture.case_id}: workflow unexpectedly emitted ConditioningCombine.")
    if fixture.expect_timestep_range and "ConditioningSetTimestepRange" not in class_types:
        errors.append(f"{fixture.case_id}: workflow missing ConditioningSetTimestepRange.")
    if not fixture.expect_timestep_range and "ConditioningSetTimestepRange" in class_types:
        errors.append(f"{fixture.case_id}: workflow unexpectedly emitted ConditioningSetTimestepRange.")

    encoder_texts = _collect_encoder_texts(workflow, fixture.expected_encoder_class)
    expected_fragments = fixture.expected_prompt_workflow_fragments + fixture.expected_negative_workflow_fragments
    for fragment in expected_fragments:
        if not any(fragment in text for text in encoder_texts):
            errors.append(f"{fixture.case_id}: workflow missing expected text fragment '{fragment}'.")
    return errors


def _run_prompt_parity_dry_run_smoke(
    base_url: str,
    cases: list[LivePromptParityCase],
    *,
    request_timeout_seconds: float,
) -> list[str]:
    errors: list[str] = []
    for case in cases:
        request_payload = _build_prompt_parity_request_payload(case)
        response_payload = _request_json(
            "POST",
            f"{base_url}/rookieui/generate/txt2img",
            payload=request_payload,
            timeout_seconds=request_timeout_seconds,
        )
        errors.extend(_validate_prompt_parity_case_response(case, response_payload))
    return errors


def _build_prompt_parity_execute_payload(case: LivePromptParityCase, client_id: str) -> dict[str, Any]:
    payload = _build_prompt_parity_request_payload(case)
    payload.pop("dry_run", None)
    payload["client_id"] = client_id
    return payload


def _run_prompt_parity_execute_smoke(
    base_url: str,
    cases: list[LivePromptParityCase],
    *,
    request_timeout_seconds: float,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> list[str]:
    errors: list[str] = []
    for case in [candidate for candidate in cases if candidate.execute]:
        client_id = f"rookieui-prompt-parity-{case.fixture.profile}-{case.fixture.case_id}"
        submit_result = _request_json(
            "POST",
            f"{base_url}/rookieui/generate/txt2img",
            payload=_build_prompt_parity_execute_payload(case, client_id),
            timeout_seconds=request_timeout_seconds,
        )
        submission = submit_result.get("submission") if isinstance(submit_result, dict) else None
        if not isinstance(submission, dict) or not bool(submission.get("accepted")):
            errors.append(
                f"{case.fixture.case_id}: execute submit failed, expected accepted submission payload."
            )
            continue
        prompt_id = str(submission.get("prompt_id", "")).strip()
        if not prompt_id:
            errors.append(f"{case.fixture.case_id}: execute submit missing prompt_id.")
            continue
        job = _poll_queue_job_until_terminal(
            base_url,
            prompt_id,
            client_id,
            request_timeout_seconds=request_timeout_seconds,
            poll_timeout_seconds=poll_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        terminal_status = str(job.get("status", "")).strip().lower()
        if terminal_status != "completed":
            errors.append(
                f"{case.fixture.case_id}: execute lane ended in status '{terminal_status}'."
            )
    return errors
def _poll_queue_job_until_terminal(
    base_url: str,
    prompt_id: str,
    client_id: str,
    *,
    request_timeout_seconds: float,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> dict[str, Any]:
    deadline = time.time() + poll_timeout_seconds
    encoded_prompt_id = urllib.parse.quote(prompt_id, safe="")
    encoded_client_id = urllib.parse.quote(client_id, safe="")
    queue_url = f"{base_url}/rookieui/queue/{encoded_prompt_id}?client_id={encoded_client_id}"
    while time.time() < deadline:
        payload = _request_json("GET", queue_url, timeout_seconds=request_timeout_seconds)
        job = payload.get("job")
        if isinstance(job, dict):
            status = str(job.get("status", "")).strip().lower()
            if status in {"completed", "failed", "cancelled"}:
                return job
        time.sleep(max(poll_interval_seconds, 0.1))
    raise RuntimeError(
        f"Queue polling timed out after {poll_timeout_seconds:.1f}s for prompt '{prompt_id}' and client '{client_id}'."
    )


def _run_execute_smoke(
    base_url: str,
    profiles: list[str],
    presets_by_id: dict[str, dict[str, Any]],
    *,
    request_timeout_seconds: float,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> list[str]:
    errors: list[str] = []
    for profile_id in profiles:
        preset = presets_by_id.get(profile_id)
        if preset is None:
            errors.append(f"profile '{profile_id}' missing preset; execute lane skipped.")
            continue
        client_id = f"rookieui-live-smoke-{profile_id}"
        request_payload = _build_txt2img_payload(profile_id, preset, client_id)
        submit_result = _request_json(
            "POST",
            f"{base_url}/rookieui/generate/txt2img",
            payload=request_payload,
            timeout_seconds=request_timeout_seconds,
        )
        submission = submit_result.get("submission") if isinstance(submit_result, dict) else None
        if not isinstance(submission, dict) or not bool(submission.get("accepted")):
            errors.append(
                f"profile '{profile_id}' submit failed: expected accepted submission payload, got '{submit_result}'."
            )
            continue
        prompt_id = str(submission.get("prompt_id", "")).strip()
        if not prompt_id:
            errors.append(f"profile '{profile_id}' submit missing prompt_id: '{submit_result}'.")
            continue
        job = _poll_queue_job_until_terminal(
            base_url,
            prompt_id,
            client_id,
            request_timeout_seconds=request_timeout_seconds,
            poll_timeout_seconds=poll_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        terminal_status = str(job.get("status", "")).strip().lower()
        if terminal_status != "completed":
            errors.append(
                f"profile '{profile_id}' execution ended in status '{terminal_status}': {json.dumps(job, ensure_ascii=True)}"
            )
    return errors


def _validate_prompt_parity_host_sync(context: PromptParityHostContext) -> list[str]:
    errors: list[str] = []
    if not context.host_contract_version:
        errors.append("live host /rookieui/capabilities payload did not expose prompt_semantics.contract_version.")
    elif context.host_contract_version != context.local_contract_version:
        errors.append(
            "live host prompt contract mismatch: "
            f"host='{context.host_contract_version}' workspace='{context.local_contract_version}'."
        )
    return errors


def main() -> int:
    args = _build_parser().parse_args()
    base_url = _normalize_base_url(args.base_url)
    profiles = _parse_profiles(args.profiles or _default_profiles_for_mode(args.validation_mode))
    if not profiles:
        print("[live-smoke] ERROR: no profiles selected.", file=sys.stderr)
        return 1

    print(f"[live-smoke] base_url={base_url}")
    print(f"[live-smoke] profiles={','.join(profiles)}")
    print(f"[live-smoke] validation_mode={args.validation_mode}")
    print(f"[live-smoke] execute={'on' if args.execute else 'off'}")
    print(f"[live-smoke] report_only={'on' if args.report_only else 'off'}")

    try:
        models_payload, presets_payload = _load_server_payloads(base_url, args.request_timeout_seconds)
    except Exception as exc:
        print(f"[live-smoke] ERROR: failed to load /models or /presets: {exc}", file=sys.stderr)
        return 1

    if args.validation_mode == "prompt-parity":
        try:
            capabilities_payload = _load_capabilities_payload(base_url, args.request_timeout_seconds)
        except Exception as exc:
            print(f"[live-smoke] ERROR: failed to load /capabilities: {exc}", file=sys.stderr)
            return 1

        context, context_errors = _build_prompt_parity_host_context(models_payload, capabilities_payload, profiles)
        if context_errors:
            print("[live-smoke] ERROR: prompt-parity host context validation failed:", file=sys.stderr)
            for error in context_errors:
                print(f"  - {error}", file=sys.stderr)
            return 0 if args.report_only else 1
        assert context is not None

        sync_errors = _validate_prompt_parity_host_sync(context)
        if sync_errors:
            print("[live-smoke] WARNING: prompt-parity host/workspace sync mismatch detected:", file=sys.stderr)
            for error in sync_errors:
                print(f"  - {error}", file=sys.stderr)

        cases = _build_prompt_parity_cases(context)
        try:
            dry_run_errors = _run_prompt_parity_dry_run_smoke(
                base_url,
                cases,
                request_timeout_seconds=args.request_timeout_seconds,
            )
        except Exception as exc:
            print(f"[live-smoke] ERROR: prompt-parity dry-run failed unexpectedly: {exc}", file=sys.stderr)
            return 0 if args.report_only else 1

        combined_errors = sync_errors + dry_run_errors
        if combined_errors:
            print("[live-smoke] WARNING: prompt-parity validation reported issues:", file=sys.stderr)
            for error in combined_errors:
                print(f"  - {error}", file=sys.stderr)
            if not args.report_only:
                return 1
        else:
            print("[live-smoke] prompt-parity dry-run checks passed.")

        if args.execute:
            if combined_errors:
                print("[live-smoke] execute lane skipped because prompt-parity dry-run was not green.")
            else:
                try:
                    execution_errors = _run_prompt_parity_execute_smoke(
                        base_url,
                        cases,
                        request_timeout_seconds=args.request_timeout_seconds,
                        poll_timeout_seconds=args.poll_timeout_seconds,
                        poll_interval_seconds=args.poll_interval_seconds,
                    )
                except Exception as exc:
                    print(f"[live-smoke] ERROR: prompt-parity execute lane failed unexpectedly: {exc}", file=sys.stderr)
                    return 0 if args.report_only else 1
                if execution_errors:
                    print("[live-smoke] ERROR: prompt-parity execute lane failed:", file=sys.stderr)
                    for error in execution_errors:
                        print(f"  - {error}", file=sys.stderr)
                    return 0 if args.report_only else 1
                print("[live-smoke] prompt-parity execute checks passed.")

        if combined_errors:
            print("[live-smoke] REPORT-ONLY COMPLETE")
        else:
            print("[live-smoke] PASS")
        return 0

    contract_errors, presets_by_id = _validate_catalog_contract(models_payload, presets_payload, profiles)
    if contract_errors:
        print("[live-smoke] ERROR: catalog contract validation failed:", file=sys.stderr)
        for error in contract_errors:
            print(f"  - {error}", file=sys.stderr)
        return 0 if args.report_only else 1
    print("[live-smoke] catalog contract checks passed.")

    if args.execute:
        try:
            execution_errors = _run_execute_smoke(
                base_url,
                profiles,
                presets_by_id,
                request_timeout_seconds=args.request_timeout_seconds,
                poll_timeout_seconds=args.poll_timeout_seconds,
                poll_interval_seconds=args.poll_interval_seconds,
            )
        except Exception as exc:
            print(f"[live-smoke] ERROR: execute lane failed unexpectedly: {exc}", file=sys.stderr)
            return 1
        if execution_errors:
            print("[live-smoke] ERROR: execution smoke failed:", file=sys.stderr)
            for error in execution_errors:
                print(f"  - {error}", file=sys.stderr)
            return 0 if args.report_only else 1
        print("[live-smoke] execution checks passed.")

    print("[live-smoke] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
