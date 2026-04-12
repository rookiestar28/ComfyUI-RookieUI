from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


_NON_SD_DIFFUSION_PROFILES: tuple[str, ...] = (
    "flux",
    "qwen_image",
    "klein",
    "lumina",
    "zit",
    "wan",
    "anima",
)


def _env_flag(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run optional live RookieUI smoke checks against a real ComfyUI host. "
            "This lane validates profile-to-model/text-encoder alignment and can optionally "
            "submit/poll lightweight txt2img runs for non-SD diffusion profiles."
        )
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("ROOKIEUI_LIVE_BASE_URL", "http://127.0.0.1:8188"),
        help="ComfyUI host base URL (default: %(default)s).",
    )
    parser.add_argument(
        "--profiles",
        default=os.getenv("ROOKIEUI_LIVE_SMOKE_PROFILES", ",".join(_NON_SD_DIFFUSION_PROFILES)),
        help="Comma-separated profile IDs to validate (default: all non-SD diffusion profiles).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        default=_env_flag("ROOKIEUI_LIVE_SMOKE_EXECUTE", default=False),
        help="Submit/poll real txt2img runs in addition to catalog contract checks.",
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


def _parse_profiles(raw_profiles: str) -> list[str]:
    profiles = [segment.strip() for segment in raw_profiles.split(",") if segment.strip()]
    return list(dict.fromkeys(profiles))


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


def main() -> int:
    args = _build_parser().parse_args()
    base_url = _normalize_base_url(args.base_url)
    profiles = _parse_profiles(args.profiles)
    if not profiles:
        print("[live-smoke] ERROR: no profiles selected.", file=sys.stderr)
        return 1

    print(f"[live-smoke] base_url={base_url}")
    print(f"[live-smoke] profiles={','.join(profiles)}")
    print(f"[live-smoke] execute={'on' if args.execute else 'off'}")

    try:
        models_payload, presets_payload = _load_server_payloads(base_url, args.request_timeout_seconds)
    except Exception as exc:
        print(f"[live-smoke] ERROR: failed to load /models or /presets: {exc}", file=sys.stderr)
        return 1

    contract_errors, presets_by_id = _validate_catalog_contract(models_payload, presets_payload, profiles)
    if contract_errors:
        print("[live-smoke] ERROR: catalog contract validation failed:", file=sys.stderr)
        for error in contract_errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
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
            return 1
        print("[live-smoke] execution checks passed.")

    print("[live-smoke] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
