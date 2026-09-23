"""Fail-closed, content-free host qualification for Qwen Image 2.1.

The configuration, result files and synthetic image evidence belong in ignored private
workspace paths. This runner never prints prompts, model paths, response bodies, or
generated image bytes; results carry only safe case IDs, digests, statuses and statistics.

Phases:
  preflight  verify candidate, host process, served frontend, models and fixtures
  execute    run the frozen case matrix; objective gates pass as PENDING_REVIEW
  finalize   bind a recorded semantic review to the exact execute result and images
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    # CRITICAL: `python scripts/<runner>.py` puts only scripts/ on sys.path; preflight
    # imports the repository fingerprint helper and would otherwise fail on every host.
    sys.path.insert(0, str(ROOT))
CONFIG_SCHEMA = "Qwen21HostConfigV1"
RESULT_SCHEMA = "Qwen21HostQualificationV1"
REVIEW_SCHEMA = "Qwen21SemanticReviewV1"
# Git object IDs are SHA-1 (40 hex) in this repository and SHA-256 (64 hex) only in
# repositories created with that object format; file/content digests are always SHA-256.
GIT_OBJECT_ID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,47}$")
CLIENT_PREFIX = "rookieui-q21-"
REQUIRED_NODES = ("TextEncodeQwenImage21", "QwenImage21Cache", "UNETLoader", "CLIPLoader", "VAELoader")
REQUIRED_PROFILES = ("qwen_image_21", "qwen_image_21_edit")
MODEL_ROLES = ("diffusion_primary", "encoder_int8", "vae_bf16")
VARIANT_ROLES: tuple[str, ...] = ()
EXPECTED_FRONTEND_INDEX_SHA256 = {
    "H1": "38f822ff4d165ccc57e39587761928f95ab63e96c9cbff53041e91bf68f395cc",  # pragma: allowlist secret - public artifact digest
    "H2": "646c7d93ee00987398471b5abd58a17a238017a5385917a2394a2d05635b8302",  # pragma: allowlist secret - public artifact digest
}
EXPECTED_CORE_VERSION = "0.37.0"
EXPECTED_BUNDLED_FRONTEND_VERSION = "1.53.6"
MINIMUM_FREE_VRAM_BYTES = 48 * 1024**3
MODEL_CATALOGS = {
    "diffusion_primary": ("diffusion_models",),
    "encoder_int8": ("clip", "text_encoders"),
    "vae_bf16": ("vae",),
}
PRIMARY_DIFFUSION_SELECTOR = r"Qwen_Image\qwen_image_2.1_int8_convrot.safetensors"
PRIMARY_DIFFUSION_SHA256 = "cb74113cb03faecd79611b01fd7fd642f0aa60d6f0b95086abee214d75eaa57d"  # pragma: allowlist secret - public artifact digest
PRIMARY_DIFFUSION_SIZE = 7_256_783_064
LEGACY_ASSET_FIELDS = ("checkpoint_name", "text_encoder_name", "vae_name")
LEGACY_CATALOGS = frozenset({"checkpoints", "diffusion_models", "clip", "text_encoders", "vae"})
# An official 2.1 encoder basename that the owner-supplied host does not provide. Preflight
# proves it is absent before the negative row relies on it.
MISSING_OFFICIAL_ENCODER = "qwen3vl_8b_w4a8.safetensors"
BACKGROUND_REMOVAL_INSTRUCTION = "Remove the background from <image1> and keep the subject with transparent alpha."
SEED = 2421
CASE_IDS = (
    "Q21-T2I-SQUARE", "Q21-T2I-RECT", "Q21-EDIT-1-REF", "Q21-EDIT-2-REF",
    "Q21-EDIT-10-REF", "Q21-EDIT-CUSTOM", "Q21-REMOVE-BG", "Q21-TRANSFER",
    "Q21-NEGATIVE", "Q21-LEGACY",
)
RESUME_RERUN_CASE_IDS = ("Q21-REMOVE-BG", "Q21-TRANSFER")
IMAGE_CASES = frozenset({
    "Q21-T2I-SQUARE", "Q21-T2I-RECT", "Q21-EDIT-1-REF", "Q21-EDIT-2-REF", "Q21-EDIT-10-REF",
    "Q21-EDIT-CUSTOM", "Q21-REMOVE-BG",
})
T2I_CHECKLIST = ("single_red_round_subject_visible", "plain_light_background", "no_severe_artifacts")
EDIT_1_REF_CHECKLIST = ("circle_shape_and_position_retained", "subject_recolored_blue", "no_severe_artifacts")
# Frozen before any live execution; a reviewer answers exactly these items per image case.
SEMANTIC_CHECKLISTS: dict[str, tuple[str, ...]] = {
    "Q21-T2I-SQUARE": T2I_CHECKLIST,
    "Q21-T2I-RECT": T2I_CHECKLIST,
    "Q21-EDIT-1-REF": EDIT_1_REF_CHECKLIST,
    "Q21-EDIT-2-REF": (
        "promoted_green_triangle_is_primary_subject", "red_circle_from_image_2_added", "no_severe_artifacts",
    ),
    "Q21-EDIT-10-REF": (
        "at_least_four_distinct_reference_subjects_visible", "coherent_single_image", "no_severe_artifacts",
    ),
    "Q21-EDIT-CUSTOM": ("red_circle_visible", "green_triangle_visible", "no_severe_artifacts"),
    "Q21-REMOVE-BG": (
        "red_round_subject_recognizable", "blue_background_removed_to_transparency", "no_severe_artifacts",
    ),
}
PROMPTS = {
    "t2i": "A single flat red circle centered on a plain white background, simple vector illustration, no text.",
    "edit_1": "Recolor the circle in <image1> to solid blue. Keep its shape, size and position unchanged.",
    "edit_2": (
        "Place a small copy of the red circle from <image2> at the center of the triangle in <image1>. "
        "Keep the triangle and the background of <image1> unchanged."
    ),
    "edit_10": (
        "Arrange the colored shapes from <image1> through <image10> as a neat grid of small icons "
        "on a plain white background."
    ),
    "edit_custom": "Place the red circle from <image1> above the green triangle from <image2> on a plain white background.",
    "legacy": "A single flat red circle centered on a plain white background.",
}


class QualificationError(RuntimeError):
    """Expected fail-closed qualification error with a safe diagnostic code."""

    def __init__(self, code: str) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", code):
            raise ValueError("Invalid safe error code")
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ModelRole:
    selector: str
    path: Path
    sha256: str
    size: int
    catalogs: tuple[str, ...]


@dataclass(frozen=True)
class LegacyControl:
    control_id: str
    profile: str
    route: str
    request: Mapping[str, object]
    assets: Mapping[str, ModelRole]
    reference_fixtures: tuple[str, ...]
    expected_width: int | None
    expected_height: int | None


@dataclass(frozen=True)
class Config:
    host: str
    base_url: str
    candidate_tree: str
    core_root: Path
    rookieui_install_root: Path
    host_output_root: Path
    core_head: str
    frontend_index_sha256: str
    fixture_manifest: Path
    fixture_manifest_sha256: str
    process_pid: int
    process_created_utc: str
    process_command_sha256: str
    request_timeout_seconds: int
    poll_timeout_seconds: int
    models: Mapping[str, ModelRole]
    variants: Mapping[str, ModelRole]
    legacy_controls: tuple[LegacyControl, ...]
    legacy_unavailable: tuple[Mapping[str, str], ...]


@dataclass(frozen=True)
class ResumeContext:
    source_result_path: Path
    source_result_sha256: str
    source_host_identity_digest: str
    source_images: Path
    case_rows: Mapping[str, Mapping[str, Any]]
    completed_legacy_controls: tuple[Mapping[str, Any], ...]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _require_pattern(value: object, pattern: re.Pattern[str], code: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise QualificationError(code)
    return value


def _model_role(item: object, catalogs: tuple[str, ...], code: str) -> ModelRole:
    if (
        not isinstance(item, dict) or not isinstance(item.get("selector"), str) or not item["selector"]
        or not isinstance(item.get("path"), str) or not item["path"]
        or not isinstance(item.get("size"), int) or isinstance(item.get("size"), bool) or item["size"] <= 0
    ):
        raise QualificationError(code)
    return ModelRole(item["selector"], Path(item["path"]), _require_pattern(item.get("sha256"), SHA256_HEX, code),
                     item["size"], catalogs)


def _legacy_control(raw: object) -> LegacyControl:
    if not isinstance(raw, dict):
        raise QualificationError("config_legacy_control")
    control_id, profile, route = raw.get("id"), raw.get("profile"), raw.get("route")
    if not isinstance(control_id, str) or not SAFE_ID.fullmatch(control_id):
        raise QualificationError("config_legacy_control")
    if not isinstance(profile, str) or not SAFE_ID.fullmatch(profile) or profile in REQUIRED_PROFILES:
        raise QualificationError("config_legacy_control")
    if route not in ("txt2img", "img2img"):
        raise QualificationError("config_legacy_control")
    request = raw.get("request")
    if not isinstance(request, dict) or any(
        key in request for key in ("prompt", "client_id", "seed", "dry_run", "profile", *LEGACY_ASSET_FIELDS)
    ):
        raise QualificationError("config_legacy_request")
    raw_assets = raw.get("assets")
    if not isinstance(raw_assets, dict) or "checkpoint_name" not in raw_assets or not set(raw_assets) <= set(LEGACY_ASSET_FIELDS):
        raise QualificationError("config_legacy_assets")
    assets: dict[str, ModelRole] = {}
    for field, item in raw_assets.items():
        catalogs = item.get("catalogs") if isinstance(item, dict) else None
        if not isinstance(catalogs, list) or not catalogs or not set(catalogs) <= LEGACY_CATALOGS:
            raise QualificationError("config_legacy_assets")
        assets[field] = _model_role(item, tuple(catalogs), "config_legacy_assets")
    fixtures = raw.get("reference_fixtures", [])
    if not isinstance(fixtures, list) or not all(isinstance(item, str) and SAFE_ID.fullmatch(item) for item in fixtures):
        raise QualificationError("config_legacy_control")
    if (route == "img2img") != bool(fixtures):
        raise QualificationError("config_legacy_control")
    dimensions = []
    for key in ("expected_width", "expected_height"):
        value = raw.get(key)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or not 64 <= value <= 4096):
            raise QualificationError("config_legacy_control")
        dimensions.append(value)
    return LegacyControl(control_id, profile, route, dict(request), assets, tuple(fixtures), dimensions[0], dimensions[1])


def load_config(path: Path) -> Config:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise QualificationError("config_unreadable") from exc
    if not isinstance(raw, dict) or raw.get("schema") != CONFIG_SCHEMA:
        raise QualificationError("config_schema")
    host = raw.get("host")
    if host not in ("H1", "H2"):
        raise QualificationError("config_host")
    frontend_digest = _require_pattern(raw.get("frontend_index_sha256"), SHA256_HEX, "config_frontend")
    if frontend_digest != EXPECTED_FRONTEND_INDEX_SHA256[host]:
        raise QualificationError("config_frontend_identity")
    base_url = raw.get("base_url")
    if not isinstance(base_url, str):
        raise QualificationError("config_url")
    url = urllib.parse.urlsplit(base_url)
    if (
        url.scheme != "http" or url.hostname != "127.0.0.1" or url.port != 8188 or url.path not in ("", "/")
        or url.username or url.password or url.query or url.fragment
    ):
        raise QualificationError("config_url")
    raw_models = raw.get("models")
    if not isinstance(raw_models, dict) or set(raw_models) != set(MODEL_ROLES):
        raise QualificationError("config_models")
    models = {role: _model_role(raw_models[role], MODEL_CATALOGS[role], "config_model_role") for role in MODEL_ROLES}
    primary = models["diffusion_primary"]
    if (primary.selector, primary.sha256, primary.size) != (
        PRIMARY_DIFFUSION_SELECTOR, PRIMARY_DIFFUSION_SHA256, PRIMARY_DIFFUSION_SIZE,
    ):
        raise QualificationError("config_primary_diffusion_identity")
    raw_variants = raw.get("variants", {})
    if not isinstance(raw_variants, dict) or not set(raw_variants) <= set(VARIANT_ROLES):
        raise QualificationError("config_variants")
    variants = {role: _model_role(item, MODEL_CATALOGS[role], "config_variants") for role, item in raw_variants.items()}
    raw_legacy = raw.get("legacy_controls")
    if not isinstance(raw_legacy, list) or not raw_legacy:
        raise QualificationError("config_legacy_controls")
    legacy_controls = tuple(_legacy_control(item) for item in raw_legacy)
    if len({control.control_id for control in legacy_controls}) != len(legacy_controls):
        raise QualificationError("config_legacy_controls")
    raw_unavailable = raw.get("legacy_unavailable", [])
    if not isinstance(raw_unavailable, list) or not all(
        isinstance(item, dict) and set(item) == {"id", "profile", "reason"}
        and all(isinstance(value, str) and SAFE_ID.fullmatch(value) for value in item.values())
        for item in raw_unavailable
    ):
        raise QualificationError("config_legacy_unavailable")
    budgets = raw.get("budgets")
    if not isinstance(budgets, dict):
        raise QualificationError("config_budgets")
    request_timeout = budgets.get("request_timeout_seconds")
    poll_timeout = budgets.get("poll_timeout_seconds")
    if (
        not isinstance(request_timeout, int) or not 1 <= request_timeout <= 120
        or not isinstance(poll_timeout, int) or not 30 <= poll_timeout <= 3600
    ):
        raise QualificationError("config_budgets")
    pid = raw.get("process_pid")
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        raise QualificationError("config_process")
    created = raw.get("process_created_utc")
    if not isinstance(created, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z", created):
        raise QualificationError("config_process")
    if not all(isinstance(raw.get(key), str) and raw[key] for key in ("core_root", "rookieui_install_root", "host_output_root", "fixture_manifest")):
        raise QualificationError("config_paths")
    if Path(raw["rookieui_install_root"]).resolve() != (Path(raw["core_root"]) / "custom_nodes" / "comfyui-rookieui").resolve():
        raise QualificationError("config_install_root")
    return Config(
        host=host,
        base_url=base_url.rstrip("/"),
        candidate_tree=_require_pattern(raw.get("candidate_tree"), GIT_OBJECT_ID, "config_candidate"),
        core_root=Path(raw["core_root"]),
        rookieui_install_root=Path(raw["rookieui_install_root"]),
        host_output_root=Path(raw["host_output_root"]),
        core_head=_require_pattern(raw.get("core_head"), GIT_OBJECT_ID, "config_core"),
        frontend_index_sha256=frontend_digest,
        fixture_manifest=Path(raw["fixture_manifest"]),
        fixture_manifest_sha256=_require_pattern(raw.get("fixture_manifest_sha256"), SHA256_HEX, "config_fixture"),
        process_pid=pid,
        process_created_utc=created,
        process_command_sha256=_require_pattern(raw.get("process_command_sha256"), SHA256_HEX, "config_process"),
        request_timeout_seconds=request_timeout,
        poll_timeout_seconds=poll_timeout,
        models=models,
        variants=variants,
        legacy_controls=legacy_controls,
        legacy_unavailable=tuple(dict(item) for item in raw_unavailable),
    )


def expected_case_ids(config: Config) -> tuple[str, ...]:
    return CASE_IDS


def _model_role_digests(config: Config) -> dict[str, str]:
    return {role: asset.sha256 for role, asset in _all_models(config).items()}


def _variant_statuses(config: Config) -> dict[str, str]:
    return {role: ("CONFIGURED" if role in config.variants else "UNAVAILABLE_NOT_CONFIGURED")
            for role in VARIANT_ROLES}


def _host_identity_digest(config: Config) -> str:
    # CRITICAL: keep deferred so importing this runner does not load optional host adapters.
    from rookieui.services.version import resolve_runtime_build_fingerprint

    identity = {"pid": config.process_pid, "created": config.process_created_utc,
                "command_sha256": config.process_command_sha256, "core": config.core_head,
                "frontend": config.frontend_index_sha256,
                "rookieui": resolve_runtime_build_fingerprint()}
    return _digest(identity)


def _resolved_path_identity(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def _static_config_identity(config: Config) -> dict[str, object]:
    def asset_identity(asset: ModelRole) -> dict[str, object]:
        return {"selector": asset.selector, "path": _resolved_path_identity(asset.path),
                "sha256": asset.sha256, "size": asset.size, "catalogs": list(asset.catalogs)}

    controls = []
    for control in config.legacy_controls:
        controls.append({
            "id": control.control_id, "profile": control.profile, "route": control.route,
            "request": dict(control.request),
            "assets": {field: asset_identity(asset) for field, asset in sorted(control.assets.items())},
            "reference_fixtures": list(control.reference_fixtures),
            "expected_width": control.expected_width, "expected_height": control.expected_height,
        })
    return {
        "host": config.host, "base_url": config.base_url, "candidate_tree": config.candidate_tree,
        "core_root": _resolved_path_identity(config.core_root),
        "rookieui_install_root": _resolved_path_identity(config.rookieui_install_root),
        "host_output_root": _resolved_path_identity(config.host_output_root), "core_head": config.core_head,
        "frontend_index_sha256": config.frontend_index_sha256,
        "fixture_manifest": _resolved_path_identity(config.fixture_manifest),
        "fixture_manifest_sha256": config.fixture_manifest_sha256,
        "request_timeout_seconds": config.request_timeout_seconds,
        "poll_timeout_seconds": config.poll_timeout_seconds,
        "models": {role: asset_identity(asset) for role, asset in sorted(config.models.items())},
        "variants": {role: asset_identity(asset) for role, asset in sorted(config.variants.items())},
        "legacy_controls": controls,
        "legacy_unavailable": [dict(item) for item in config.legacy_unavailable],
    }


def _git(path: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, check=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        raise QualificationError("git_identity_unavailable") from exc
    return result.stdout.strip()


def _read_limited(response: Any, limit: int) -> bytes:
    body = response.read(limit + 1)
    if len(body) > limit:
        raise QualificationError("host_response_too_large")
    return body


def _get_bytes(config: Config, route: str, *, limit: int = 8 * 1024 * 1024) -> bytes:
    request = urllib.request.Request(config.base_url + route, headers={"User-Agent": "rookieui-qwen21-qualification"})
    try:
        with urllib.request.urlopen(request, timeout=config.request_timeout_seconds) as response:
            if response.status != 200:
                raise QualificationError("host_http_status")
            return _read_limited(response, limit)
    except urllib.error.HTTPError as exc:
        raise QualificationError("host_http_status") from exc
    except (OSError, ValueError) as exc:
        raise QualificationError("host_request_failed") from exc


def _get_json(config: Config, route: str) -> dict[str, Any]:
    try:
        payload = json.loads(_get_bytes(config, route))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise QualificationError("host_json_invalid") from exc
    if not isinstance(payload, dict):
        raise QualificationError("host_json_shape")
    return payload


def _post_json(config: Config, route: str, payload: Mapping[str, object]) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        config.base_url + route,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "rookieui-qwen21-qualification"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.request_timeout_seconds) as response:
            status, body = response.status, _read_limited(response, 8 * 1024 * 1024)
    except urllib.error.HTTPError as exc:
        status, body = exc.code, _read_limited(exc, 8 * 1024 * 1024)
    except (OSError, ValueError) as exc:
        # CRITICAL: a transport failure after a POST leaves the enqueue outcome unknown;
        # never retry automatically, because a retry can queue a duplicate GPU job.
        raise QualificationError("host_request_failed") from exc
    try:
        parsed = json.loads(body)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise QualificationError("host_json_invalid") from exc
    if not isinstance(parsed, dict):
        raise QualificationError("host_json_shape")
    return status, parsed


def _client_id() -> str:
    return CLIENT_PREFIX + uuid.uuid4().hex


def _control_submission_identity_valid(control: Mapping[str, Any]) -> bool:
    prompt_id = control.get("prompt_id")
    client_id = control.get("client_id")
    return (
        isinstance(prompt_id, str) and re.fullmatch(r"[0-9a-fA-F-]{20,80}", prompt_id) is not None
        and isinstance(client_id, str)
        and re.fullmatch(re.escape(CLIENT_PREFIX) + r"[0-9a-f]{32}", client_id) is not None
    )


def _queue_job(config: Config, prompt_id: str, client_id: str) -> dict[str, Any] | None:
    query = urllib.parse.urlencode({"client_id": client_id})
    route = "/rookieui/queue/" + urllib.parse.quote(prompt_id, safe="") + "?" + query
    job = _get_json(config, route).get("job")
    if job is not None and not isinstance(job, dict):
        raise QualificationError("queue_job_shape")
    return job


def _client_job_count(config: Config, client_id: str) -> int:
    jobs = _get_json(config, "/rookieui/queue?" + urllib.parse.urlencode({"client_id": client_id})).get("jobs")
    if not isinstance(jobs, list):
        raise QualificationError("queue_jobs_shape")
    return len(jobs)


def _vram_free(config: Config) -> int | None:
    devices = _get_json(config, "/system_stats").get("devices")
    if isinstance(devices, list) and devices and isinstance(devices[0], dict):
        value = devices[0].get("vram_free")
        return value if isinstance(value, int) and not isinstance(value, bool) else None
    return None


def _assert_generation_capacity(config: Config) -> int:
    """Refuse new model work unless the host and GPU meet the frozen capacity floor."""
    queue = _get_json(config, "/queue")
    running = queue.get("queue_running")
    pending = queue.get("queue_pending")
    if not isinstance(running, list) or not isinstance(pending, list):
        raise QualificationError("host_queue_shape")
    if running or pending:
        raise QualificationError("host_queue_busy")
    free = _vram_free(config)
    if free is None or isinstance(free, bool):
        raise QualificationError("host_vram_unavailable")
    if free < MINIMUM_FREE_VRAM_BYTES:
        raise QualificationError("host_vram_low")
    return free


def _fixture_entries(config: Config) -> list[dict[str, Any]]:
    try:
        entries = json.loads(config.fixture_manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise QualificationError("fixture_manifest_invalid") from exc
    if not isinstance(entries, list):
        raise QualificationError("fixture_manifest_invalid")
    return entries


def _fixture_bytes(config: Config, fixture_id: str) -> bytes:
    entry = next((item for item in _fixture_entries(config) if isinstance(item, dict) and item.get("id") == fixture_id), None)
    if not isinstance(entry, dict) or not isinstance(entry.get("filename"), str) or Path(entry["filename"]).name != entry["filename"]:
        raise QualificationError("fixture_entry_invalid")
    data = (config.fixture_manifest.parent / entry["filename"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != entry.get("sha256"):
        raise QualificationError("fixture_image_mismatch")
    return data


def _fixture_data_url(config: Config, fixture_id: str) -> str:
    return "data:image/png;base64," + base64.b64encode(_fixture_bytes(config, fixture_id)).decode("ascii")


def _common_payload(config: Config, client_id: str, diffusion: ModelRole) -> dict[str, object]:
    return {
        "negative_prompt": "",
        "checkpoint_name": diffusion.selector,
        "text_encoder_name": config.models["encoder_int8"].selector,
        "vae_name": config.models["vae_bf16"].selector,
        "steps": 25,
        "cfg_scale": 1.0,
        "sampler_name": "euler",
        "scheduler_name": "simple",
        "seed": SEED,
        "client_id": client_id,
    }


@dataclass(frozen=True)
class CasePlan:
    route: str
    payload: dict[str, object]
    width: int | None
    height: int | None
    fixtures: tuple[str, ...]
    promoted_order: tuple[int, ...] | None = None


def _case_plan(config: Config, case_id: str, client_id: str) -> CasePlan:
    diffusion = config.models["diffusion_primary"]
    common = _common_payload(config, client_id, diffusion)
    if case_id in ("Q21-T2I-SQUARE", "Q21-T2I-RECT"):
        width, height = (768, 1024) if case_id == "Q21-T2I-RECT" else (1024, 1024)
        payload = {**common, "prompt": PROMPTS["t2i"], "profile": "qwen_image_21", "width": width, "height": height, "batch_size": 1}
        return CasePlan("/rookieui/generate/txt2img", payload, width, height, ())
    fixtures: tuple[str, ...]
    prompt = PROMPTS["edit_1"]
    edit_task = "edit"
    promoted_order = None
    if case_id == "Q21-EDIT-1-REF":
        fixtures = ("ref_01",)
    elif case_id == "Q21-EDIT-2-REF":
        # Uploaded as Reference 1 = ref_01 and Reference 2 = ref_02, then Reference 2 is promoted.
        fixtures, prompt, promoted_order = ("ref_01", "ref_02"), PROMPTS["edit_2"], (1, 0)
    elif case_id == "Q21-EDIT-10-REF":
        fixtures, prompt = tuple(f"ref_{index:02d}" for index in range(1, 11)), PROMPTS["edit_10"]
    elif case_id == "Q21-EDIT-CUSTOM":
        fixtures, prompt = ("ref_01", "ref_02"), PROMPTS["edit_custom"]
    elif case_id == "Q21-REMOVE-BG":
        fixtures, prompt, edit_task = ("remove_background",), BACKGROUND_REMOVAL_INSTRUCTION, "background_removal"
    else:
        raise QualificationError("case_payload_unsupported")
    payload = {
        **common,
        "prompt": prompt,
        "profile": "qwen_image_21_edit",
        "mode": "img2img",
        "reference_images": [{"image_data": _fixture_data_url(config, item)} for item in fixtures],
        "main_reference_index": 0,
        "reference_resolution": 1024 if case_id == "Q21-EDIT-CUSTOM" else 0,
        "edit_task": edit_task,
        "denoise_strength": 1.0,
        "batch_size": 1,
    }
    if case_id == "Q21-EDIT-CUSTOM":
        payload.update({"output_size_mode": "custom", "width": 768, "height": 1024})
        return CasePlan("/rookieui/generate/img2img", payload, 768, 1024, fixtures)
    payload["output_size_mode"] = "reference"
    return CasePlan("/rookieui/generate/img2img", payload, 512, 512, fixtures, promoted_order)


def _workflow_nodes(workflow: Mapping[str, Any]) -> dict[str, list[tuple[str, dict[str, Any]]]]:
    nodes: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for node_id, node in workflow.items():
        if isinstance(node, dict) and isinstance(node.get("class_type"), str) and isinstance(node.get("inputs"), dict):
            nodes.setdefault(node["class_type"], []).append((str(node_id), node["inputs"]))
    return nodes


def _single(nodes: Mapping[str, list[tuple[str, dict[str, Any]]]], class_type: str) -> tuple[str, dict[str, Any]] | None:
    matches = nodes.get(class_type, [])
    return matches[0] if len(matches) == 1 else None


def _validate_graph(
    response: Mapping[str, Any], count: int, width: int | None, height: int | None,
    *, config: Config | None = None, case_id: str = "", expected_handles: list[str] | None = None,
) -> list[str]:
    workflow = response.get("workflow")
    if not isinstance(workflow, dict):
        return ["workflow_missing"]
    nodes = _workflow_nodes(workflow)
    for class_type in ("UNETLoader", "CLIPLoader", "VAELoader", "TextEncodeQwenImage21", "KSampler", "VAEDecode"):
        if _single(nodes, class_type) is None:
            return ["workflow_nodes_missing"]
    encode_id, encoder = _single(nodes, "TextEncodeQwenImage21")  # type: ignore[misc]
    slots = [key for key in encoder if key.startswith("images.image_")]
    if slots != [f"images.image_{index}" for index in range(1, count + 1)]:
        return ["workflow_reference_order"]
    latent = _single(nodes, "EmptyLatentImage")
    if count == 0 and (latent is None or (latent[1].get("width"), latent[1].get("height")) != (width, height)):
        return ["workflow_canvas_mismatch"]
    if config is None:
        return []
    diffusion = config.models["diffusion_primary"]
    expected_loaders = {
        "UNETLoader": ("unet_name", diffusion.selector),
        "CLIPLoader": ("clip_name", config.models["encoder_int8"].selector),
        "VAELoader": ("vae_name", config.models["vae_bf16"].selector),
    }
    for class_type, (field, selector) in expected_loaders.items():
        if _single(nodes, class_type)[1].get(field) != selector:  # type: ignore[index]
            return ["workflow_model_role_mismatch"]
    if encoder.get("resolution") != (1024 if count == 0 or case_id == "Q21-EDIT-CUSTOM" else 0):
        return ["workflow_resolution_mismatch"]
    _, sampler = _single(nodes, "KSampler")  # type: ignore[misc]
    if sampler.get("steps") != 25 or sampler.get("cfg") != 1.0 or sampler.get("seed") != SEED:
        return ["workflow_sampler_mismatch"]
    if sampler.get("positive") != [encode_id, 0] or sampler.get("negative") != [encode_id, 1]:
        return ["workflow_conditioning_slots"]
    if count == 0:
        return [] if sampler.get("latent_image") == [latent[0], 0] else ["workflow_txt2img_latent"]  # type: ignore[index]
    cache = _single(nodes, "QwenImage21Cache")
    if cache is None or (cache[1].get("device"), cache[1].get("dtype")) != ("auto", "default"):
        return ["workflow_cache_missing"]
    normalized = response.get("normalized_request")
    references = normalized.get("reference_image_assets") if isinstance(normalized, dict) else None
    if not isinstance(references, list) or len(references) != count:
        return ["workflow_reference_handles"]
    if expected_handles is not None and references != expected_handles:
        return ["workflow_reference_handles"]
    for index, handle in enumerate(references, 1):
        ref = encoder.get(f"images.image_{index}")
        loader = workflow.get(ref[0]) if isinstance(ref, list) and ref else None
        inputs = loader.get("inputs") if isinstance(loader, dict) else None
        if (
            not isinstance(inputs, dict) or loader.get("class_type") != "RookieUILoadAssetImage"
            or inputs.get("asset_handle") != handle or inputs.get("preserve_alpha") is not True
        ):
            return ["workflow_reference_binding"]
    if case_id == "Q21-EDIT-CUSTOM":
        if latent is None or (latent[1].get("width"), latent[1].get("height")) != (width, height):
            return ["workflow_custom_canvas"]
        if sampler.get("latent_image") != [latent[0], 0]:
            return ["workflow_custom_latent"]
    elif latent is not None or sampler.get("latent_image") != [encode_id, 2]:
        return ["workflow_reference_latent"]
    return []


def _decode_png(data: bytes, width: int | None, height: int | None) -> tuple[dict[str, Any], Image.Image]:
    if len(data) > 32 * 1024 * 1024 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise QualificationError("original_png_invalid")
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (OSError, ValueError) as exc:
        raise QualificationError("original_png_invalid") from exc
    if image.format != "PNG" or (width is not None and image.width != width) or (height is not None and image.height != height):
        raise QualificationError("original_dimensions_mismatch")
    rgba = image.convert("RGBA")
    low, high = rgba.getchannel("A").getextrema()
    summary = {"width": image.width, "height": image.height, "mode": image.mode, "alpha_min": low, "alpha_max": high}
    return summary, rgba


def _background_alpha_gate(image: Image.Image) -> dict[str, object]:
    """Frozen removal gate: outer 64px band clear, central 160px square opaque and red-dominant."""
    width, height = image.size
    if width < 320 or height < 320:
        raise QualificationError("background_dimensions_small")
    pixels = image.load()
    outer_total = outer_clear = center_total = center_opaque = center_red = 0
    left, top = (width - 160) // 2, (height - 160) // 2
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            if x < 64 or x >= width - 64 or y < 64 or y >= height - 64:
                outer_total += 1
                outer_clear += alpha <= 32
            if left <= x < left + 160 and top <= y < top + 160:
                center_total += 1
                if alpha >= 192:
                    center_opaque += 1
                    center_red += red > green and red > blue
    outer_fraction = outer_clear / outer_total
    center_fraction = center_opaque / center_total
    red_fraction = center_red / center_opaque if center_opaque else 0.0
    stats = {
        "outer_clear_fraction": round(outer_fraction, 4),
        "center_opaque_fraction": round(center_fraction, 4),
        "center_red_fraction": round(red_fraction, 4),
    }
    if outer_fraction < 0.75 or center_fraction < 0.75 or red_fraction < 0.5:
        raise QualificationError("background_alpha_gate")
    return stats


def _new_row(case_id: str) -> dict[str, Any]:
    return {"case_id": case_id, "selected": True, "dry_run_pass": False, "executed": False,
            "terminal_status": "not_submitted", "history_matched": False, "original_decoded": False,
            "semantic_review": "PENDING" if case_id in SEMANTIC_CHECKLISTS else "NOT_APPLICABLE",
            "child_exit": 1, "status": "FAIL"}


def _host_input_sha256(config: Config, handle: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}\.(?:png|jpg|webp)", handle):
        raise QualificationError("asset_handle_shape")
    path = config.rookieui_install_root / ".rookieui_runtime" / "input" / handle
    if not path.is_file():
        raise QualificationError("asset_handle_missing")
    return _sha256_file(path)


def _submit_and_collect(
    config: Config, route: str, payload: dict[str, object], client_id: str,
    expected: tuple[int | None, int | None], image_path: Path, row: dict[str, Any],
    validate_submitted: Any = None,
) -> tuple[dict[str, Any], Image.Image, bytes]:
    before = _client_job_count(config, client_id)
    if before != 0:
        raise QualificationError("client_id_not_fresh")
    started = time.monotonic()
    row["vram_free_before"] = _assert_generation_capacity(config)
    submit_status, submitted = _post_json(config, route, payload)
    submission = submitted.get("submission")
    prompt_id = submission.get("prompt_id") if isinstance(submission, dict) else None
    if submit_status != 200 or submitted.get("mode") != "queued" or not isinstance(prompt_id, str):
        raise QualificationError("submission_rejected")
    if not re.fullmatch(r"[0-9a-fA-F-]{20,80}", prompt_id):
        raise QualificationError("submission_id_shape")
    if validate_submitted is not None and validate_submitted(submitted):
        raise QualificationError("submitted_graph_mismatch")
    row.update({"executed": True, "prompt_id": prompt_id, "client_id": client_id})
    deadline = started + config.poll_timeout_seconds
    job = None
    while time.monotonic() < deadline:
        job = _queue_job(config, prompt_id, client_id)
        if job and job.get("status") in ("completed", "failed", "cancelled"):
            break
        time.sleep(2)
    row["elapsed_seconds"] = round(time.monotonic() - started, 1)
    if not job or job.get("id") != prompt_id or job.get("status") not in ("completed", "failed", "cancelled"):
        row["terminal_status"] = "timeout" if job else "missing"
        raise QualificationError("job_terminal_timeout")
    row["terminal_status"] = str(job["status"])
    row["history_matched"] = True
    vram_free_after = _vram_free(config)
    if not isinstance(vram_free_after, int) or isinstance(vram_free_after, bool):
        raise QualificationError("host_vram_unavailable")
    row["vram_free_after"] = vram_free_after
    if job["status"] != "completed":
        raise QualificationError("job_not_completed")
    # CRITICAL: aggregate history limits oldest global rows before client filtering; the exact
    # prompt-and-client lookup above remains authoritative after later jobs exceed that window.
    # A filtered queue is a visibility aid, not authentication. A different client ID
    # must not see this job before the selected output is accepted as job-bound.
    if _queue_job(config, prompt_id, _client_id()) is not None:
        raise QualificationError("cross_client_job_visible")
    outputs = job.get("reusable_outputs")
    filenames = job.get("output_filenames")
    if not isinstance(outputs, list) or len(outputs) != 1 or not isinstance(filenames, list) or outputs[0] not in filenames:
        raise QualificationError("job_output_missing")
    filename = outputs[0]
    if not isinstance(filename, str) or Path(filename).name != filename:
        raise QualificationError("job_output_filename")
    original = _get_bytes(config, "/view?" + urllib.parse.urlencode({"filename": filename, "type": "output", "subfolder": ""}),
                          limit=32 * 1024 * 1024)
    summary, image = _decode_png(original, *expected)
    row.update({"original_decoded": True, "width": summary["width"], "height": summary["height"],
                "alpha_summary": {"mode": summary["mode"], "min": summary["alpha_min"], "max": summary["alpha_max"]},
                "original_sha256": hashlib.sha256(original).hexdigest(), "output_handle": filename})
    image_path.parent.mkdir(parents=True, exist_ok=True)
    with image_path.open("xb") as evidence:
        evidence.write(original)
    return job, image, original


def _run_image_case(config: Config, case_id: str, private_images: Path, row: dict[str, Any]) -> None:
    client_id = _client_id()
    plan = _case_plan(config, case_id, client_id)
    count = len(plan.fixtures)
    dry_status, dry = _post_json(config, plan.route, {**plan.payload, "dry_run": True})
    if dry_status != 200 or not isinstance(dry.get("submission"), dict) or dry["submission"].get("mode") != "dry-run":
        raise QualificationError("dry_run_rejected")
    graph_errors = _validate_graph(dry, count, plan.width, plan.height, config=config, case_id=case_id)
    if graph_errors:
        raise QualificationError(graph_errors[0])
    handles: list[str] = []
    if count:
        normalized = dry.get("normalized_request")
        handles = list(normalized.get("reference_image_assets") or []) if isinstance(normalized, dict) else []
        if len(handles) != count or not all(isinstance(handle, str) and handle for handle in handles):
            raise QualificationError("dry_run_reference_handles")
        for handle, fixture in zip(handles, plan.fixtures):
            if _host_input_sha256(config, handle) != hashlib.sha256(_fixture_bytes(config, fixture)).hexdigest():
                raise QualificationError("reference_bytes_mismatch")
        if plan.promoted_order is not None:
            # Make-primary moves the selected reference into visible slot 1; the request
            # carries the new canonical order with main index 0, never a hidden index.
            handles = [handles[index] for index in plan.promoted_order]
            row["primary_promotion"] = "reference_2_to_image_1"
        # CRITICAL: reuse exactly the dry-run's host handles so a second upload cannot
        # silently change image_1/image_10 between graph inspection and submission.
        plan.payload["reference_images"] = [{"image_asset": handle} for handle in handles]
        promoted_status, promoted = _post_json(config, plan.route, {**plan.payload, "dry_run": True})
        if promoted_status != 200 or _validate_graph(
            promoted, count, plan.width, plan.height, config=config, case_id=case_id, expected_handles=handles,
        ):
            raise QualificationError("canonical_reference_order")
        row["input_handles"] = handles
    row["dry_run_pass"] = True

    def validate(submitted: Mapping[str, Any]) -> list[str]:
        return _validate_graph(submitted, count, plan.width, plan.height, config=config, case_id=case_id,
                               expected_handles=handles if count else None)

    _, image, _ = _submit_and_collect(
        config, plan.route, plan.payload, client_id, (plan.width, plan.height),
        private_images / (case_id + ".png"), row, validate,
    )
    if case_id == "Q21-REMOVE-BG":
        row["alpha_summary"] = {**row["alpha_summary"], **_background_alpha_gate(image)}
    row["semantic_checklist"] = list(SEMANTIC_CHECKLISTS[case_id])
    row["status"] = "PENDING_REVIEW"
    row["child_exit"] = 0


def _expect_rejected(config: Config, route: str, payload: dict[str, object], client_id: str, name: str) -> None:
    status, response = _post_json(config, route, payload)
    if status != 400 or response.get("status") != "invalid-request" or _client_job_count(config, client_id) != 0:
        raise QualificationError("negative_" + name)


def _run_negative_case(config: Config, row: dict[str, Any]) -> None:
    models = _get_json(config, "/rookieui/models")
    listed = {item for group in ("clip", "text_encoders") for item in models.get(group, []) if isinstance(item, str)}
    if any(item.replace("/", "\\").rsplit("\\", 1)[-1].lower() == MISSING_OFFICIAL_ENCODER for item in listed):
        raise QualificationError("negative_missing_model_present")
    rejections: list[str] = []
    for name, override in (
        ("wrong_diffusion_role", {"checkpoint_name": config.models["vae_bf16"].selector}),
        ("wrong_encoder_role", {"text_encoder_name": config.models["vae_bf16"].selector}),
        ("wrong_vae_role", {"vae_name": config.models["encoder_int8"].selector}),
        ("missing_official_model", {"text_encoder_name": MISSING_OFFICIAL_ENCODER}),
        ("invalid_resolution", {"reference_resolution": 31}),
        ("nonzero_primary", {"main_reference_index": 1}),
        ("legacy_profile_with_new_assets", {"profile": "qwen_image_edit_2511"}),
    ):
        client_id = _client_id()
        plan = _case_plan(config, "Q21-EDIT-2-REF", client_id)
        _expect_rejected(config, plan.route, {**plan.payload, **override}, client_id, name)
        rejections.append(name)
    for name, count in (("zero_references", 0), ("eleven_references", 11)):
        client_id = _client_id()
        plan = _case_plan(config, "Q21-EDIT-2-REF", client_id)
        plan.payload["reference_images"] = [
            {"image_data": _fixture_data_url(config, f"ref_{(index % 10) + 1:02d}")} for index in range(count)
        ]
        _expect_rejected(config, plan.route, plan.payload, client_id, name)
        rejections.append(name)
    row["rejections"] = rejections
    try:
        hermetic = subprocess.run(
            [sys.executable, "-m", "unittest",
             "tests.test_qwen_image_21.QwenImage21AdmissionTests.test_loaded_old_host_rejects_missing_qwen21_node",
             "tests.test_qwen_image_21_edit.QwenImage21EditTests.test_old_host_rejects_missing_cache_or_encoder"],
            cwd=ROOT, capture_output=True, check=False, timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise QualificationError("missing_node_hermetic_unavailable") from exc
    row["missing_node_hermetic_exit"] = hermetic.returncode
    if hermetic.returncode != 0:
        raise QualificationError("missing_node_hermetic_failed")
    row.update({"dry_run_pass": True, "status": "PASS", "child_exit": 0})


def _run_transfer_case(config: Config, source_row: Mapping[str, Any], image_path: Path, row: dict[str, Any]) -> None:
    if source_row.get("status") != "PENDING_REVIEW" or source_row.get("case_id") != "Q21-REMOVE-BG":
        raise QualificationError("transfer_source_unqualified")
    original = image_path.read_bytes()
    original_sha = hashlib.sha256(original).hexdigest()
    if original_sha != source_row.get("original_sha256"):
        raise QualificationError("transfer_source_changed")
    summary, _ = _decode_png(original, source_row.get("width"), source_row.get("height"))
    if summary["alpha_min"] >= 255:
        raise QualificationError("transfer_source_without_alpha")
    # Download path: the host output file behind the job's reusable handle is the same bytes.
    output_handle = source_row.get("output_handle")
    output_file = config.host_output_root / str(output_handle)
    if not isinstance(output_handle, str) or not output_file.is_file() or _sha256_file(output_file) != original_sha:
        raise QualificationError("download_bytes_mismatch")
    data_url = "data:image/png;base64," + base64.b64encode(original).decode("ascii")
    status, inspected = _post_json(config, "/rookieui/pnginfo/inspect", {"image_data": data_url})
    handle = inspected.get("asset_handle")
    if status != 200 or inspected.get("status") != "ok" or not isinstance(handle, str):
        raise QualificationError("pnginfo_inspection_failed")
    # RookieUI outputs embed A1111-style `parameters`; PNG Info must interpret that infotext,
    # not only ComfyUI graph JSON, and bind the stored copy as the transferable asset.
    payload = inspected.get("payload")
    metadata = inspected.get("metadata_items")
    if (
        inspected.get("source_type") != "a1111" or not isinstance(payload, dict) or payload.get("seed") != SEED
        or payload.get("steps") != 25 or payload.get("image_asset") != handle or not isinstance(metadata, dict)
    ):
        raise QualificationError("pnginfo_interpretation_mismatch")
    try:
        # SaveImageWithMetadata writes each extra_pnginfo key as its own JSON text chunk.
        rookieui_meta = json.loads(metadata.get("rookieui", ""))
    except (TypeError, json.JSONDecodeError) as exc:
        raise QualificationError("pnginfo_rookieui_metadata_missing") from exc
    if not isinstance(rookieui_meta, dict) or (rookieui_meta.get("profile"), rookieui_meta.get("edit_task"), rookieui_meta.get("seed")) != (
        "qwen_image_21_edit", "background_removal", SEED,
    ):
        raise QualificationError("pnginfo_rookieui_metadata_mismatch")
    if _host_input_sha256(config, handle) != original_sha:
        raise QualificationError("pnginfo_bytes_mismatch")
    stored_summary, _ = _decode_png(original, summary["width"], summary["height"])
    if (stored_summary["alpha_min"], stored_summary["alpha_max"]) != (summary["alpha_min"], summary["alpha_max"]):
        raise QualificationError("pnginfo_alpha_mismatch")
    client_id = _client_id()
    plan = _case_plan(config, "Q21-EDIT-1-REF", client_id)
    plan.payload.pop("reference_images", None)
    # CRITICAL: preview handoff sends original /view bytes as image_data; an output filename is
    # not a RookieUI runtime input handle and must not bypass the upload/normalization boundary.
    plan.payload["image_asset"] = ""
    plan.payload["image_data"] = data_url
    dry_status, dry = _post_json(config, plan.route, {**plan.payload, "dry_run": True})
    normalized = dry.get("normalized_request")
    transfer_handles = normalized.get("reference_image_assets") if isinstance(normalized, dict) else None
    if (
        dry_status != 200 or not isinstance(transfer_handles, list) or len(transfer_handles) != 1
        or not isinstance(transfer_handles[0], str)
    ):
        raise QualificationError("transfer_input_normalization_failed")
    transfer_handle = transfer_handles[0]
    if _host_input_sha256(config, transfer_handle) != original_sha:
        raise QualificationError("transfer_bytes_mismatch")
    if _validate_graph(
        dry, 1, summary["width"], summary["height"], config=config, case_id="Q21-EDIT-1-REF",
        expected_handles=transfer_handles,
    ):
        raise QualificationError("transfer_graph_failed")
    row.update({"dry_run_pass": True, "original_decoded": True, "width": summary["width"], "height": summary["height"],
                "alpha_summary": {"mode": summary["mode"], "min": summary["alpha_min"], "max": summary["alpha_max"]},
                "transfer_equivalence": "download_pnginfo_and_send_to_edit_exact_bytes",
                "input_handles": [handle, transfer_handle], "source_case_id": "Q21-REMOVE-BG",
                "source_original_sha256": original_sha, "original_sha256": original_sha,
                "status": "PASS", "child_exit": 0})


def _copy_resume_artifact(config: Config, source_images: Path, target_images: Path,
                          evidence_name: str, row: Mapping[str, Any]) -> None:
    source = _validate_resume_artifact(config, source_images, evidence_name, row)
    digest = row.get("original_sha256")
    data = source.read_bytes()
    if not isinstance(digest, str) or hashlib.sha256(data).hexdigest() != digest:
        raise QualificationError("resume_image_digest_mismatch")
    target = target_images / evidence_name
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    except FileExistsError as exc:
        raise QualificationError("resume_destination_exists") from exc
    if _sha256_file(target) != digest:
        raise QualificationError("resume_image_copy_mismatch")


def _run_legacy_case(config: Config, private_images: Path, row: dict[str, Any], *,
                     completed_controls: tuple[Mapping[str, Any], ...] = (),
                     source_images: Path | None = None) -> None:
    controls: list[dict[str, Any]] = []
    row["controls"] = controls
    row["unavailable_controls"] = [dict(item) for item in config.legacy_unavailable]
    if completed_controls and source_images is None:
        raise QualificationError("resume_source_not_resumable")
    if len(completed_controls) >= len(config.legacy_controls):
        raise QualificationError("resume_source_not_resumable")
    for index, control in enumerate(config.legacy_controls):
        if index < len(completed_controls):
            previous = copy.deepcopy(dict(completed_controls[index]))
            if previous.get("id") != control.control_id or previous.get("profile") != control.profile:
                raise QualificationError("resume_source_not_resumable")
            _copy_resume_artifact(
                config, source_images, private_images, f"Q21-LEGACY-{control.control_id}.png", previous,  # type: ignore[arg-type]
            )
            controls.append(previous)
            continue
        # CRITICAL: explicit pre-submit false distinguishes a safe capacity stop from an accepted child job.
        control_row: dict[str, Any] = {
            "id": control.control_id, "profile": control.profile, "status": "FAIL", "executed": False,
        }
        controls.append(control_row)
        try:
            client_id = _client_id()
            payload: dict[str, object] = {
                **control.request, "prompt": PROMPTS["legacy"], "negative_prompt": "", "profile": control.profile,
                "seed": SEED, "client_id": client_id,
                **{field: asset.selector for field, asset in control.assets.items()},
            }
            if control.route == "img2img":
                payload["reference_images"] = [{"image_data": _fixture_data_url(config, item)} for item in control.reference_fixtures]
                payload.setdefault("main_reference_index", 0)
            route = "/rookieui/generate/" + control.route
            dry_status, dry = _post_json(config, route, {**payload, "dry_run": True})
            if dry_status != 200 or not isinstance(dry.get("workflow"), dict):
                raise QualificationError("legacy_dry_run_rejected")
            selectors = {json.dumps(value) for node in dry["workflow"].values() if isinstance(node, dict)
                         for value in (node.get("inputs") or {}).values() if isinstance(value, str)}
            if not all(json.dumps(asset.selector) in selectors for asset in control.assets.values()):
                raise QualificationError("legacy_model_binding")
            if any(node.get("class_type") in ("TextEncodeQwenImage21", "QwenImage21Cache")
                   for node in dry["workflow"].values() if isinstance(node, dict)):
                raise QualificationError("legacy_graph_uses_qwen21_nodes")
            control_row["dry_run_pass"] = True
            _submit_and_collect(
                config, route, payload, client_id, (control.expected_width, control.expected_height),
                private_images / f"{row['case_id']}-{control.control_id}.png", control_row,
            )
        except QualificationError as exc:
            control_row.update({"status": "FAIL", "child_exit": 1, "error_code": exc.code})
            raise
        except Exception as exc:  # noqa: BLE001 - keep nested diagnostics content-free.
            control_row.update({
                "status": "FAIL", "child_exit": 1,
                "error_code": "unexpected_" + type(exc).__name__.lower(),
            })
            raise
        else:
            control_row.update({"status": "PASS", "child_exit": 0})
    row.update({"dry_run_pass": True, "executed": True, "status": "PASS", "child_exit": 0})


def _reuse_case_row(config: Config, resume: ResumeContext, private_images: Path, case_id: str) -> dict[str, Any]:
    source = resume.case_rows[case_id]
    row = copy.deepcopy(dict(source))
    if case_id in IMAGE_CASES:
        _copy_resume_artifact(config, resume.source_images, private_images, f"{case_id}.png", source)
    return row


def execute_cases(config: Config, private_images: Path, *, resume: ResumeContext | None = None,
                  rerun_case_ids: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    if private_images.exists():
        raise QualificationError("result_images_exist")
    if resume is None and rerun_case_ids:
        raise QualificationError("resume_arguments_invalid")
    if resume is not None and rerun_case_ids != RESUME_RERUN_CASE_IDS:
        raise QualificationError("resume_rerun_case_invalid")
    cases: list[dict[str, Any]] = []
    ordered = expected_case_ids(config)
    private_images.mkdir(parents=True, exist_ok=False)
    for case_id in ordered:
        if resume is not None and case_id not in rerun_case_ids and case_id != "Q21-LEGACY":
            try:
                cases.append(_reuse_case_row(config, resume, private_images, case_id))
            except QualificationError as exc:
                row = _new_row(case_id)
                row["error_code"] = exc.code
                cases.append(row)
                for remaining in ordered[len(cases):]:
                    pending = _new_row(remaining)
                    pending.update({"status": "NOT_RUN", "error_code": "prior_case_failed"})
                    cases.append(pending)
                break
            continue
        row = _new_row(case_id)
        try:
            if case_id in IMAGE_CASES:
                _run_image_case(config, case_id, private_images, row)
            elif case_id == "Q21-TRANSFER":
                source = next(item for item in cases if item["case_id"] == "Q21-REMOVE-BG")
                _run_transfer_case(config, source, private_images / "Q21-REMOVE-BG.png", row)
            elif case_id == "Q21-NEGATIVE":
                _run_negative_case(config, row)
            elif case_id == "Q21-LEGACY":
                _run_legacy_case(
                    config, private_images, row,
                    completed_controls=resume.completed_legacy_controls if resume else (),
                    source_images=resume.source_images if resume else None,
                )
            else:
                raise QualificationError("case_unregistered")
        except QualificationError as exc:
            row["error_code"] = exc.code
        except Exception as exc:  # noqa: BLE001 - failures remain content-free.
            row["error_code"] = "unexpected_" + type(exc).__name__.lower()
        cases.append(row)
        if row["status"] == "FAIL":
            for remaining in ordered[len(cases):]:
                pending = _new_row(remaining)
                pending.update({"status": "NOT_RUN", "error_code": "prior_case_failed"})
                cases.append(pending)
            break
    return cases


def _listener_pid() -> int:
    if os.name != "nt":
        raise QualificationError("host_platform_unsupported")
    try:
        result = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, check=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        raise QualificationError("host_pid_unavailable") from exc
    pids = set()
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0].upper() == "TCP" and fields[1].endswith(":8188") and fields[3].upper() == "LISTENING":
            pids.add(int(fields[4]))
    if len(pids) != 1:
        raise QualificationError("host_pid_ambiguous")
    return pids.pop()


def _process_identity(pid: int) -> tuple[str, str]:
    command = (
        f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId={pid}'; "
        "if ($null -eq $p) { exit 2 }; "
        "[pscustomobject]@{created=$p.CreationDate.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffffffZ'); "
        "command=$p.CommandLine} | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True, check=True, timeout=25)
        payload = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise QualificationError("host_process_identity_unavailable") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("created"), str) or not isinstance(payload.get("command"), str):
        raise QualificationError("host_process_identity_invalid")
    return payload["created"], hashlib.sha256(payload["command"].encode("utf-8")).hexdigest()


def _process_identity_if_alive(pid: int) -> tuple[str, str] | None:
    """Return a safe identity tuple for a prior host PID, or None when it has exited."""
    command = (
        f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId={pid}'; "
        "if ($null -eq $p) { Write-Output 'ABSENT' } else { "
        "[pscustomobject]@{created=$p.CreationDate.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffffffZ'); "
        "command=$p.CommandLine} | ConvertTo-Json -Compress }"
    )
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True,
                                check=True, timeout=25)
        if result.stdout.strip() == "ABSENT":
            return None
        payload = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise QualificationError("resume_process_probe_failed") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("created"), str) or not isinstance(payload.get("command"), str):
        raise QualificationError("resume_process_probe_failed")
    return payload["created"], hashlib.sha256(payload["command"].encode("utf-8")).hexdigest()


def _resume_host_output_path(config: Config, output_handle: object) -> Path:
    if not isinstance(output_handle, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}\.png", output_handle):
        raise QualificationError("resume_host_output_handle_invalid")
    root = config.host_output_root.resolve()
    path = root / output_handle
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise QualificationError("resume_host_output_unavailable") from exc
    if path.is_symlink() or not resolved.is_relative_to(root) or not resolved.is_file():
        raise QualificationError("resume_host_output_unavailable")
    return resolved


def _validate_resume_artifact(config: Config, source_images: Path, evidence_name: str,
                              row: Mapping[str, Any]) -> Path:
    digest = row.get("original_sha256")
    if not isinstance(digest, str) or not SHA256_HEX.fullmatch(digest):
        raise QualificationError("resume_source_not_resumable")
    output_path = _resume_host_output_path(config, row.get("output_handle"))
    if _sha256_file(output_path) != digest:
        raise QualificationError("resume_host_output_digest_mismatch")
    evidence = source_images / evidence_name
    try:
        resolved = evidence.resolve(strict=True)
    except OSError as exc:
        raise QualificationError("resume_image_unavailable") from exc
    if evidence.is_symlink() or not resolved.is_relative_to(source_images.resolve()) or not resolved.is_file():
        raise QualificationError("resume_image_unavailable")
    if _sha256_file(resolved) != digest:
        raise QualificationError("resume_image_digest_mismatch")
    return resolved


def _validate_resume(config: Config, source_config: Config, source_path: Path,
                     current_preflight: Mapping[str, Any]) -> ResumeContext:
    if _static_config_identity(config) != _static_config_identity(source_config):
        raise QualificationError("resume_config_mismatch")
    old_process = (source_config.process_pid, source_config.process_created_utc, source_config.process_command_sha256)
    new_process = (config.process_pid, config.process_created_utc, config.process_command_sha256)
    if old_process == new_process:
        raise QualificationError("resume_process_identity_mismatch")
    if _process_identity_if_alive(source_config.process_pid) == (
        source_config.process_created_utc, source_config.process_command_sha256,
    ):
        raise QualificationError("resume_old_process_active")
    _, execute = _load_json_bytes(source_path, "resume_result_unreadable")
    source_sha256 = _sha256_file(source_path)
    if execute.get("candidate_tree") != config.candidate_tree:
        raise QualificationError("resume_candidate_mismatch")
    old_identity = execute.get("host_identity_digest")
    current_identity = current_preflight.get("host_identity_digest")
    if (
        isinstance(old_identity, str) and SHA256_HEX.fullmatch(old_identity)
        and isinstance(current_identity, str) and SHA256_HEX.fullmatch(current_identity)
        and old_identity == current_identity
    ):
        raise QualificationError("resume_process_identity_mismatch")
    if (
        execute.get("schema") != RESULT_SCHEMA or execute.get("phase") != "execute" or execute.get("host") != config.host
        or execute.get("status") != "FAIL" or execute.get("error_code") != "case_matrix_not_accepted"
        or not isinstance(old_identity, str) or not SHA256_HEX.fullmatch(old_identity)
        or not isinstance(current_identity, str) or not SHA256_HEX.fullmatch(current_identity)
        or execute.get("served_frontend_digest") != current_preflight.get("served_frontend_digest")
        or execute.get("model_role_digests") != current_preflight.get("model_role_digests")
        or execute.get("fixture_digest") != current_preflight.get("fixture_digest")
        or execute.get("variants") != current_preflight.get("variants")
        or execute.get("execution_identity_segments") != [old_identity]
        or execute.get("served_frontend_digest") != config.frontend_index_sha256
        or execute.get("model_role_digests") != _model_role_digests(config)
        or execute.get("fixture_digest") != config.fixture_manifest_sha256
        or execute.get("variants") != _variant_statuses(config)
    ):
        raise QualificationError("resume_result_identity_mismatch")
    rows = execute.get("cases")
    expected = expected_case_ids(config)
    if not isinstance(rows, list) or [row.get("case_id") for row in rows if isinstance(row, dict)] != list(expected):
        raise QualificationError("resume_case_matrix_mismatch")
    rows_by_case: dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(rows):
        if (
            not isinstance(row, dict) or row.get("candidate_tree") != config.candidate_tree
            or row.get("host_identity_digest") != old_identity
            or row.get("served_frontend_digest") != config.frontend_index_sha256
            or row.get("model_role_digests") != _model_role_digests(config)
            or row.get("fixture_digest") != config.fixture_manifest_sha256
        ):
            raise QualificationError("resume_row_identity_mismatch")
        rows_by_case[expected[index]] = row
    for case_id in IMAGE_CASES:
        row = rows_by_case.get(case_id)
        if (
            not isinstance(row, dict) or row.get("status") != "PENDING_REVIEW" or row.get("child_exit") != 0
            or row.get("semantic_review") != "PENDING" or row.get("executed") is not True
            or row.get("history_matched") is not True or row.get("terminal_status") != "completed"
            or row.get("original_decoded") is not True
        ):
            raise QualificationError("resume_source_not_resumable")
        _validate_resume_artifact(config, source_path.parent / (source_path.stem + "-images"),
                                  f"{case_id}.png", row)
    for case_id in ("Q21-TRANSFER", "Q21-NEGATIVE"):
        row = rows_by_case.get(case_id)
        if not isinstance(row, dict) or row.get("status") != "PASS" or row.get("child_exit") != 0:
            raise QualificationError("resume_source_not_resumable")
    removal_row = rows_by_case.get("Q21-REMOVE-BG")
    transfer_row = rows_by_case.get("Q21-TRANSFER")
    if (
        not isinstance(removal_row, dict) or not isinstance(transfer_row, dict)
        or transfer_row.get("source_case_id") != "Q21-REMOVE-BG"
        or transfer_row.get("source_original_sha256") != removal_row.get("original_sha256")
        or transfer_row.get("original_sha256") != removal_row.get("original_sha256")
    ):
        raise QualificationError("resume_transfer_source_mismatch")
    legacy = rows_by_case.get("Q21-LEGACY")
    controls = legacy.get("controls") if isinstance(legacy, dict) else None
    if (
        not isinstance(legacy, dict) or legacy.get("status") != "FAIL" or legacy.get("child_exit") != 1
        or legacy.get("error_code") != "host_vram_low" or legacy.get("unavailable_controls") != [dict(x) for x in config.legacy_unavailable]
        or not isinstance(controls, list) or len(controls) != len(config.legacy_controls)
    ):
        raise QualificationError("resume_source_not_resumable")
    completed: list[Mapping[str, Any]] = []
    for index, (control, control_row) in enumerate(zip(config.legacy_controls, controls, strict=True)):
        if not isinstance(control_row, dict) or control_row.get("id") != control.control_id or control_row.get("profile") != control.profile:
            raise QualificationError("resume_source_not_resumable")
        if index < len(controls) - 1:
            if (
                control_row.get("status") != "PASS" or control_row.get("child_exit") != 0
                or control_row.get("dry_run_pass") is not True or control_row.get("executed") is not True
                or control_row.get("history_matched") is not True or control_row.get("terminal_status") != "completed"
                or control_row.get("host_identity_digest") != old_identity
                or not _control_submission_identity_valid(control_row) or control_row.get("error_code") is not None
            ):
                raise QualificationError("resume_source_not_resumable")
            _validate_resume_artifact(
                config, source_path.parent / (source_path.stem + "-images"),
                f"Q21-LEGACY-{control.control_id}.png", control_row,
            )
            completed.append(control_row)
        elif (
            control_row.get("status") != "FAIL" or control_row.get("dry_run_pass") is not True
            or control_row.get("executed") is not False or control_row.get("child_exit") != 1
            or control_row.get("error_code") != "host_vram_low"
            or control_row.get("host_identity_digest") != old_identity
            or control_row.get("prompt_id") is not None or control_row.get("history_matched") is True
            or control_row.get("output_handle") is not None or control_row.get("terminal_status") is not None
            or legacy.get("executed") is not False or legacy.get("prompt_id") is not None
        ):
            raise QualificationError("resume_source_not_resumable")
    if not completed:
        raise QualificationError("resume_source_not_resumable")
    return ResumeContext(
        source_result_path=source_path, source_result_sha256=source_sha256,
        source_host_identity_digest=old_identity,
        source_images=source_path.parent / (source_path.stem + "-images"),
        case_rows=rows_by_case, completed_legacy_controls=tuple(completed),
    )


def _all_models(config: Config) -> dict[str, ModelRole]:
    roles = {**config.models, **config.variants}
    for control in config.legacy_controls:
        for field, asset in control.assets.items():
            roles[f"legacy.{control.control_id}.{field}"] = asset
    return roles


def preflight(config: Config) -> dict[str, object]:
    if _git(ROOT, "rev-parse", "HEAD^{tree}") != config.candidate_tree:
        raise QualificationError("candidate_tree_mismatch")
    if _git(ROOT, "status", "--porcelain", "--untracked-files=no"):
        raise QualificationError("candidate_worktree_dirty")
    if _git(config.core_root, "rev-parse", "HEAD") != config.core_head:
        raise QualificationError("core_head_mismatch")
    if _listener_pid() != config.process_pid:
        raise QualificationError("host_pid_mismatch")
    if _process_identity(config.process_pid) != (config.process_created_utc, config.process_command_sha256):
        raise QualificationError("host_process_identity_mismatch")
    if _sha256_file(config.fixture_manifest) != config.fixture_manifest_sha256:
        raise QualificationError("fixture_digest_mismatch")
    for model in _all_models(config).values():
        if not model.path.is_file() or model.path.stat().st_size != model.size or _sha256_file(model.path) != model.sha256:
            raise QualificationError("model_digest_mismatch")
    if hashlib.sha256(_get_bytes(config, "/")).hexdigest() != config.frontend_index_sha256:
        raise QualificationError("frontend_digest_mismatch")
    from rookieui.services.version import resolve_runtime_build_fingerprint

    runtime = _get_json(config, "/rookieui/bootstrap").get("runtime")
    if not isinstance(runtime, dict) or runtime.get("build_fingerprint") != resolve_runtime_build_fingerprint():
        raise QualificationError("rookieui_fingerprint_mismatch")
    catalog = _get_json(config, "/rookieui/models")
    for model in _all_models(config).values():
        if not any(model.selector in catalog.get(group, []) for group in model.catalogs):
            raise QualificationError("model_selector_missing")
    for node in REQUIRED_NODES:
        if node not in _get_json(config, "/object_info/" + node):
            raise QualificationError("host_node_missing")
    presets = _get_json(config, "/rookieui/presets").get("presets")
    profiles = {row.get("id") for row in presets if isinstance(row, dict)} if isinstance(presets, list) else set()
    required = set(REQUIRED_PROFILES) | {control.profile for control in config.legacy_controls}
    if not required <= profiles:
        raise QualificationError("rookieui_profile_missing")
    runtime_stats = _get_json(config, "/system_stats").get("system")
    if not isinstance(runtime_stats, dict) or runtime_stats.get("comfyui_version") != EXPECTED_CORE_VERSION:
        raise QualificationError("host_core_runtime_mismatch")
    packages = runtime_stats.get("comfy_package_versions")
    bundled_frontend = next((item for item in packages if isinstance(item, dict)
                             and item.get("name") == "comfyui-frontend-package"), None) if isinstance(packages, list) else None
    if not isinstance(bundled_frontend, dict) or bundled_frontend.get("installed") != EXPECTED_BUNDLED_FRONTEND_VERSION:
        raise QualificationError("host_bundled_frontend_mismatch")
    queue = _get_json(config, "/queue")
    if not isinstance(queue.get("queue_running"), list) or not isinstance(queue.get("queue_pending"), list):
        raise QualificationError("host_queue_shape")
    if queue["queue_running"] or queue["queue_pending"]:
        raise QualificationError("host_queue_busy")
    return {
        "candidate_tree": config.candidate_tree,
        "host_identity_digest": _host_identity_digest(config),
        "served_frontend_digest": config.frontend_index_sha256,
        "model_role_digests": {role: model.sha256 for role, model in _all_models(config).items()},
        "fixture_digest": config.fixture_manifest_sha256,
        "variants": {role: ("CONFIGURED" if role in config.variants else "UNAVAILABLE_NOT_CONFIGURED") for role in VARIANT_ROLES},
    }


def _load_json_bytes(path: Path, code: str) -> tuple[bytes, dict[str, Any]]:
    try:
        data = path.read_bytes()
        payload = json.loads(data)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise QualificationError(code) from exc
    if not isinstance(payload, dict):
        raise QualificationError(code)
    return data, payload


def finalize(config: Config, execute_path: Path, review_path: Path) -> dict[str, object]:
    """Bind a recorded semantic review to the exact execute result and private images."""
    if _git(ROOT, "rev-parse", "HEAD^{tree}") != config.candidate_tree:
        raise QualificationError("candidate_tree_mismatch")
    execute_bytes, execute = _load_json_bytes(execute_path, "execute_result_unreadable")
    if (
        execute.get("schema") != RESULT_SCHEMA or execute.get("phase") != "execute" or execute.get("host") != config.host
        or execute.get("candidate_tree") != config.candidate_tree or execute.get("status") != "PENDING_REVIEW"
        or execute.get("served_frontend_digest") != config.frontend_index_sha256
        or execute.get("model_role_digests") != _model_role_digests(config)
        or execute.get("fixture_digest") != config.fixture_manifest_sha256
        or execute.get("variants") != _variant_statuses(config)
    ):
        raise QualificationError("execute_identity_mismatch")
    rows = execute.get("cases")
    if not isinstance(rows, list) or [row.get("case_id") for row in rows if isinstance(row, dict)] != list(expected_case_ids(config)):
        raise QualificationError("execute_case_matrix_mismatch")
    _validate_execute_lineage(execute, rows, config)
    _, review = _load_json_bytes(review_path, "review_unreadable")
    if (
        review.get("schema") != REVIEW_SCHEMA or review.get("host") != config.host
        or review.get("execute_result_sha256") != hashlib.sha256(execute_bytes).hexdigest()
        or not isinstance(review.get("cases"), dict)
    ):
        raise QualificationError("review_identity_mismatch")
    pending = [row for row in rows if row.get("status") == "PENDING_REVIEW"]
    if set(review["cases"]) != {row["case_id"] for row in pending}:
        raise QualificationError("review_case_set_mismatch")
    images = execute_path.parent / (execute_path.stem + "-images")
    final_rows: list[dict[str, Any]] = []
    for row in rows:
        final = dict(row)
        if row.get("status") == "PENDING_REVIEW":
            entry = review["cases"][row["case_id"]]
            checklist = entry.get("checklist") if isinstance(entry, dict) else None
            expected_items = SEMANTIC_CHECKLISTS.get(row["case_id"])
            if (
                not isinstance(entry, dict) or entry.get("original_sha256") != row.get("original_sha256")
                or not isinstance(checklist, dict) or expected_items is None or tuple(checklist) != expected_items
                or not all(isinstance(value, bool) for value in checklist.values())
            ):
                raise QualificationError("review_entry_invalid")
            image = images / (row["case_id"] + ".png")
            if not image.is_file() or _sha256_file(image) != row.get("original_sha256"):
                raise QualificationError("review_image_changed")
            passed = all(checklist.values())
            final.update({"semantic_review": "PASS" if passed else "FAIL",
                          "semantic_items_failed": [item for item, value in checklist.items() if not value],
                          "status": "PASS" if passed else "FAIL"})
        final_rows.append(final)
    return {**{key: execute[key] for key in (
        "candidate_tree", "host_identity_digest", "served_frontend_digest", "model_role_digests", "fixture_digest", "variants",
    )}, "execution_identity_segments": execute["execution_identity_segments"],
            "execute_result_sha256": hashlib.sha256(execute_bytes).hexdigest(), "cases": final_rows}


def _validate_execute_lineage(execute: Mapping[str, Any], rows: list[Mapping[str, Any]], config: Config) -> None:
    segments = execute.get("execution_identity_segments")
    current_identity = execute.get("host_identity_digest")
    expected_cases = expected_case_ids(config)
    expected_reused_cases = [case_id for case_id in expected_cases
                             if case_id not in (*RESUME_RERUN_CASE_IDS, "Q21-LEGACY")]
    legacy_ids = [control.control_id for control in config.legacy_controls]
    source_identity: str | None = None
    reused_legacy_ids: list[str] = []
    if (
        not isinstance(segments, list) or not 1 <= len(segments) <= 2
        or not all(isinstance(item, str) and SHA256_HEX.fullmatch(item) for item in segments)
        or len(set(segments)) != len(segments) or current_identity not in segments
        or current_identity != _host_identity_digest(config)
    ):
        raise QualificationError("execute_identity_lineage_invalid")
    resume = execute.get("resume")
    if len(segments) == 1:
        if resume is not None:
            raise QualificationError("execute_identity_lineage_invalid")
    else:
        if (
            not isinstance(resume, dict) or resume.get("source_host_identity_digest") != segments[0]
            or resume.get("current_host_identity_digest") != current_identity
            or not isinstance(resume.get("source_execute_result_sha256"), str)
            or not SHA256_HEX.fullmatch(resume["source_execute_result_sha256"])
            or resume.get("reused_case_ids") != expected_reused_cases
            or resume.get("rerun_case_ids") != list(RESUME_RERUN_CASE_IDS)
            or len(legacy_ids) < 2
            or resume.get("reused_legacy_control_ids") != legacy_ids[:-1]
            or resume.get("continued_legacy_control_ids") != legacy_ids[-1:]
        ):
            raise QualificationError("execute_identity_lineage_invalid")
        source_identity = segments[0]
        reused_legacy_ids = legacy_ids[:-1]
    for case_id, row in zip(expected_cases, rows, strict=True):
        expected_identity = (
            source_identity if source_identity is not None and case_id in expected_reused_cases else current_identity
        )
        if (
            not isinstance(row, dict) or row.get("host_identity_digest") not in segments
            or row.get("host_identity_digest") != expected_identity
            or row.get("candidate_tree") != execute.get("candidate_tree")
            or row.get("served_frontend_digest") != execute.get("served_frontend_digest")
            or row.get("model_role_digests") != execute.get("model_role_digests")
            or row.get("fixture_digest") != execute.get("fixture_digest")
        ):
            raise QualificationError("execute_row_identity_lineage_invalid")
        controls = row.get("controls", [])
        if not isinstance(controls, list):
            raise QualificationError("execute_control_identity_lineage_invalid")
        if case_id != "Q21-LEGACY":
            if controls:
                raise QualificationError("execute_control_identity_lineage_invalid")
            continue
        if (
            [control.get("id") for control in controls if isinstance(control, dict)] != legacy_ids
            or len(controls) != len(legacy_ids)
            or row.get("status") != "PASS" or row.get("child_exit") != 0
            or row.get("executed") is not True or row.get("dry_run_pass") is not True
            or row.get("unavailable_controls") != [dict(item) for item in config.legacy_unavailable]
        ):
            raise QualificationError("execute_control_identity_lineage_invalid")
        for index, control in enumerate(controls):
            expected_control_identity = source_identity if legacy_ids[index] in reused_legacy_ids else current_identity
            if (
                not isinstance(control, dict) or control.get("host_identity_digest") != expected_control_identity
                or control.get("profile") != config.legacy_controls[index].profile
                or control.get("status") != "PASS" or control.get("child_exit") != 0
                or control.get("dry_run_pass") is not True or control.get("executed") is not True
                or control.get("history_matched") is not True or control.get("terminal_status") != "completed"
                or not _control_submission_identity_valid(control) or control.get("error_code") is not None
                or not isinstance(control.get("original_sha256"), str)
                or not SHA256_HEX.fullmatch(control["original_sha256"])
                or not isinstance(control.get("output_handle"), str)
            ):
                raise QualificationError("execute_control_identity_lineage_invalid")

    removal_row = rows[expected_cases.index("Q21-REMOVE-BG")]
    transfer_row = rows[expected_cases.index("Q21-TRANSFER")]
    if (
        transfer_row.get("status") != "PASS" or transfer_row.get("child_exit") != 0
        or transfer_row.get("source_case_id") != "Q21-REMOVE-BG"
        or transfer_row.get("source_original_sha256") != removal_row.get("original_sha256")
        or transfer_row.get("original_sha256") != removal_row.get("original_sha256")
    ):
        raise QualificationError("execute_transfer_source_lineage_invalid")


def _write_new_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    try:
        with path.open("xb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    except FileExistsError as exc:
        raise QualificationError("result_exists") from exc


def _aggregate(rows: list[dict[str, Any]], expected: tuple[str, ...]) -> str:
    if [row.get("case_id") for row in rows] != list(expected):
        return "FAIL"
    statuses = {row.get("status") for row in rows}
    if statuses == {"PASS"} and all(row.get("child_exit") == 0 for row in rows):
        return "PASS"
    if statuses <= {"PASS", "PENDING_REVIEW"} and all(row.get("child_exit") == 0 for row in rows):
        return "PENDING_REVIEW"
    return "FAIL"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--phase", required=True, choices=("preflight", "execute", "finalize"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--execute-result", type=Path, help="finalize: the execute-phase result to bind")
    parser.add_argument("--review", type=Path, help="finalize: the recorded semantic review")
    parser.add_argument("--resume-result", type=Path, help="execute: exact-candidate failed result to continue")
    parser.add_argument("--resume-config", type=Path, help="execute: config bound to the prior host process")
    parser.add_argument("--rerun-case", action="append", choices=CASE_IDS,
                        help="execute: strict continuation accepts the ordered UI case and dependent transfer pair")
    args = parser.parse_args(argv)
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA, "phase": args.phase, "status": "FAIL",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(), "cases": [],
    }
    exit_code = 1
    try:
        if args.output.exists():
            raise QualificationError("result_exists")
        if (args.phase == "finalize") != bool(args.execute_result and args.review):
            raise QualificationError("arguments_invalid")
        has_resume = args.resume_result is not None or args.resume_config is not None
        if args.phase != "execute" and (has_resume or args.rerun_case):
            raise QualificationError("arguments_invalid")
        if args.phase == "execute":
            if (args.resume_result is None) != (args.resume_config is None):
                raise QualificationError("arguments_invalid")
            if args.resume_result is None and args.rerun_case:
                raise QualificationError("arguments_invalid")
            if args.resume_result is not None and tuple(args.rerun_case or ()) != RESUME_RERUN_CASE_IDS:
                raise QualificationError("resume_rerun_case_invalid")
        config = load_config(args.config)
        result["host"] = config.host
        if args.phase == "finalize":
            result.update(finalize(config, args.execute_result, args.review))
            result["status"] = _aggregate(result["cases"], expected_case_ids(config))
            if result["status"] != "PASS":
                raise QualificationError("case_matrix_not_accepted")
        else:
            result.update(preflight(config))
            if args.phase == "execute":
                resume = None
                if args.resume_result is not None and args.resume_config is not None:
                    source_config = load_config(args.resume_config)
                    resume = _validate_resume(config, source_config, args.resume_result, result)
                    current_identity = result["host_identity_digest"]
                    result["execution_identity_segments"] = [resume.source_host_identity_digest, current_identity]
                    result["resume"] = {
                        "source_execute_result_sha256": resume.source_result_sha256,
                        "source_host_identity_digest": resume.source_host_identity_digest,
                        "current_host_identity_digest": current_identity,
                        "reused_case_ids": [case_id for case_id in expected_case_ids(config)
                                             if case_id not in args.rerun_case and case_id != "Q21-LEGACY"],
                        "rerun_case_ids": list(args.rerun_case or []),
                        "reused_legacy_control_ids": [control["id"] for control in resume.completed_legacy_controls],
                        "continued_legacy_control_ids": [config.legacy_controls[len(resume.completed_legacy_controls)].control_id],
                    }
                else:
                    result["execution_identity_segments"] = [result["host_identity_digest"]]
                result["cases"] = execute_cases(
                    config, args.output.parent / (args.output.stem + "-images"),
                    resume=resume, rerun_case_ids=tuple(args.rerun_case or ()),
                )
                for row in result["cases"]:
                    row_identity = row.get("host_identity_digest", result["host_identity_digest"])
                    row["host_identity_digest"] = row_identity
                    row.update({key: result[key] for key in (
                        "candidate_tree", "served_frontend_digest", "model_role_digests",
                        "fixture_digest",
                    )})
                    for control in row.get("controls", []):
                        if isinstance(control, dict):
                            control.setdefault("host_identity_digest", result["host_identity_digest"])
                result["status"] = _aggregate(result["cases"], expected_case_ids(config))
                if result["status"] == "FAIL":
                    raise QualificationError("case_matrix_not_accepted")
            else:
                result["status"] = "PASS"
        exit_code = 0 if result["status"] == "PASS" else 2
    except QualificationError as exc:
        result["status"] = "FAIL"
        result["error_code"] = exc.code
    except Exception as exc:  # noqa: BLE001 - never serialize raw private host failures.
        result["status"] = "FAIL"
        result["error_code"] = "unexpected_" + type(exc).__name__.lower()
    try:
        _write_new_json(args.output, result)
    except QualificationError:
        print("qualification FAIL: result_exists", file=sys.stderr)
        return 1
    print(f"qualification {result['status']}: {result.get('error_code', 'ok')}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
