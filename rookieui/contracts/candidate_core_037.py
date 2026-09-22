"""Pinned, read-only compatibility evidence for the ComfyUI Core 0.37 candidate.

This contract is deliberately separate from the accepted host source basis. It
does not enable a runtime capability or advance any accepted source revision.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Collection, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "core_037_candidate_contract.json"
DEFAULT_SOURCE_ROOT = ROOT / "reference" / "ComfyUI"
ACCEPTED_REVISION = "30bdda1ef13a3a34fce2cd2fec633f15d832122a"
CANDIDATE_REVISION = "e638023d54497dbe0579565e5de4bb7076899592"
SCHEMA_VERSION = "core-037-candidate-v1"
FIXTURE_SHA256 = "01ac010b2aa3c67bcad5f434402beb272f09207a6a4b4ddafff681997de2586a"

_TOP_FIELDS = frozenset(
    {
        "accepted_revision", "blueprint_profiles", "candidate_revision", "components",
        "core_version", "qwen_encoder_inputs", "qwen_encoder_outputs",
        "qwen_latent_channels", "qwen_latent_stride", "qwen_reference_slots",
        "qwen_resolution_default", "qwen_resolution_max", "qwen_resolution_min",
        "qwen_resolution_step", "schema_version", "source_artifacts",
    }
)
_COMPONENTS = {
    "embedded_docs": "0.5.12",
    "frontend_package": "1.53.6",
    "workflow_templates": "0.11.66",
}
_SCALARS = {
    "accepted_revision": ACCEPTED_REVISION,
    "candidate_revision": CANDIDATE_REVISION,
    "core_version": "0.37.0",
    "schema_version": SCHEMA_VERSION,
    "qwen_latent_channels": 64,
    "qwen_latent_stride": 16,
    "qwen_reference_slots": 16,
    "qwen_resolution_default": 1024,
    "qwen_resolution_max": 4096,
    "qwen_resolution_min": 0,
    "qwen_resolution_step": 32,
}
_ENCODER_INPUTS = ("clip", "prompt", "negative_prompt", "vae", "resolution", "images")
_ENCODER_OUTPUTS = ("CONDITIONING", "CONDITIONING", "LATENT")
_SOURCE_PATHS = (
    "comfy/controlnet.py", "comfy/sample.py", "comfy_extras/nodes_model_advanced.py",
    "comfy_extras/nodes_qwen.py", "comfyui_version.py", "execution.py", "nodes.py",
    "requirements.txt", "server.py",
)
_PROFILE_NAMES = (
    "anima", "ernie_image", "ernie_image_turbo", "firered_image_edit",
    "firered_image_edit_lightning", "flux", "flux2_dev", "flux2_image_edit",
    "flux_krea_dev", "ideogram4", "longcat_image_edit", "qwen_image",
    "qwen_image_edit_2511", "z_image", "z_image_turbo",
)
_REQUIRED_NODES = MappingProxyType(
    {
        "txt2img": frozenset(
            {"UNETLoader", "CLIPLoader", "VAELoader", "TextEncodeQwenImage21",
             "KSampler", "VAEDecode"}
        ),
        "edit": frozenset(
            {"UNETLoader", "CLIPLoader", "VAELoader", "TextEncodeQwenImage21",
             "QwenImage21Cache", "KSampler", "VAEDecode"}
        ),
    }
)


@dataclass(frozen=True)
class SourceArtifact:
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class BlueprintProfile:
    profile: str
    path: str
    accepted_sha256: str
    candidate_sha256: str


@dataclass(frozen=True)
class CoreCandidateContract:
    accepted_revision: str
    candidate_revision: str
    core_version: str
    components: Mapping[str, str]
    source_artifacts: tuple[SourceArtifact, ...]
    blueprint_profiles: tuple[BlueprintProfile, ...]
    qwen_encoder_inputs: tuple[str, ...]
    qwen_encoder_outputs: tuple[str, ...]
    qwen_reference_slots: int
    qwen_latent_channels: int
    qwen_latent_stride: int
    qwen_resolution_default: int
    qwen_resolution_min: int
    qwen_resolution_max: int
    qwen_resolution_step: int


@dataclass(frozen=True)
class VerificationReport:
    status: str
    verified_artifacts: int
    verified_blueprints: int
    runtime_facts: str


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate candidate contract field: {key}")
        result[key] = value
    return result


def _safe_repo_path(path: object, prefix: str | None = None) -> str:
    if not isinstance(path, str) or not path or "\\" in path:
        raise ValueError("invalid candidate source path")
    parts = PurePosixPath(path).parts
    if path.startswith("/") or any(part in (".", "..") for part in parts):
        raise ValueError("unsafe candidate source path")
    if prefix is not None and parts[0] != prefix:
        raise ValueError("candidate source path is outside its expected directory")
    return path


def parse_contract_text(text: str) -> CoreCandidateContract:
    """Reject a stale or edited freeze rather than silently accepting drift."""
    try:
        payload = json.loads(text, object_pairs_hook=_unique_pairs)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError("invalid candidate contract JSON") from error
    if not isinstance(payload, dict) or payload.keys() != _TOP_FIELDS:
        raise ValueError("unexpected candidate contract fields")
    for key, expected in _SCALARS.items():
        if type(payload[key]) is not type(expected) or payload[key] != expected:
            raise ValueError(f"unexpected candidate contract {key}")
    if payload["components"] != _COMPONENTS:
        raise ValueError("unexpected bundled component versions")
    if payload["qwen_encoder_inputs"] != list(_ENCODER_INPUTS):
        raise ValueError("unexpected Qwen encoder input slots")
    if payload["qwen_encoder_outputs"] != list(_ENCODER_OUTPUTS):
        raise ValueError("unexpected Qwen encoder output slots")

    sources = payload["source_artifacts"]
    profiles = payload["blueprint_profiles"]
    if not isinstance(sources, list) or not isinstance(profiles, list):
        raise ValueError("candidate source inventories must be lists")
    if len(sources) != len(_SOURCE_PATHS) or len(profiles) != len(_PROFILE_NAMES):
        raise ValueError("incomplete candidate source inventory")
    for expected, row in zip(_SOURCE_PATHS, sources):
        if not isinstance(row, dict) or row.keys() != {"path", "bytes", "sha256"}:
            raise ValueError("invalid candidate source artifact")
        if _safe_repo_path(row["path"]) != expected or type(row["bytes"]) is not int:
            raise ValueError("unexpected candidate source artifact")
        if row["bytes"] <= 0 or not isinstance(row["sha256"], str) or len(row["sha256"]) != 64:
            raise ValueError("invalid candidate source fingerprint")
    for expected, row in zip(_PROFILE_NAMES, profiles):
        if not isinstance(row, dict) or row.keys() != {
            "profile", "path", "accepted_sha256", "candidate_sha256"
        }:
            raise ValueError("invalid candidate blueprint profile")
        if row["profile"] != expected:
            raise ValueError("unexpected candidate blueprint profile")
        _safe_repo_path(row["path"], prefix="blueprints")
        for key in ("accepted_sha256", "candidate_sha256"):
            if not isinstance(row[key], str) or len(row[key]) != 64:
                raise ValueError("invalid candidate blueprint fingerprint")

    # CRITICAL: a source freeze is evidence only for this exact vetted byte set;
    # accepting a rewritten manifest could falsely promote a changed host source.
    canonical = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != FIXTURE_SHA256:
        raise ValueError("candidate source freeze fingerprint changed")
    return CoreCandidateContract(
        accepted_revision=payload["accepted_revision"],
        candidate_revision=payload["candidate_revision"],
        core_version=payload["core_version"],
        components=MappingProxyType(dict(payload["components"])),
        source_artifacts=tuple(SourceArtifact(**row) for row in sources),
        blueprint_profiles=tuple(BlueprintProfile(**row) for row in profiles),
        qwen_encoder_inputs=tuple(payload["qwen_encoder_inputs"]),
        qwen_encoder_outputs=tuple(payload["qwen_encoder_outputs"]),
        qwen_reference_slots=payload["qwen_reference_slots"],
        qwen_latent_channels=payload["qwen_latent_channels"],
        qwen_latent_stride=payload["qwen_latent_stride"],
        qwen_resolution_default=payload["qwen_resolution_default"],
        qwen_resolution_min=payload["qwen_resolution_min"],
        qwen_resolution_max=payload["qwen_resolution_max"],
        qwen_resolution_step=payload["qwen_resolution_step"],
    )


def load_contract(path: Path = DEFAULT_FIXTURE) -> CoreCandidateContract:
    return parse_contract_text(path.read_text(encoding="utf-8"))


def serialize_contract(contract: CoreCandidateContract) -> str:
    payload: dict[str, object] = {
        "accepted_revision": contract.accepted_revision,
        "blueprint_profiles": [vars(row) for row in contract.blueprint_profiles],
        "candidate_revision": contract.candidate_revision,
        "components": dict(contract.components),
        "core_version": contract.core_version,
        "qwen_encoder_inputs": list(contract.qwen_encoder_inputs),
        "qwen_encoder_outputs": list(contract.qwen_encoder_outputs),
        "qwen_latent_channels": contract.qwen_latent_channels,
        "qwen_latent_stride": contract.qwen_latent_stride,
        "qwen_reference_slots": contract.qwen_reference_slots,
        "qwen_resolution_default": contract.qwen_resolution_default,
        "qwen_resolution_max": contract.qwen_resolution_max,
        "qwen_resolution_min": contract.qwen_resolution_min,
        "qwen_resolution_step": contract.qwen_resolution_step,
        "schema_version": SCHEMA_VERSION,
        "source_artifacts": [vars(row) for row in contract.source_artifacts],
    }
    return json.dumps(payload, sort_keys=True, indent=2) + "\n"


def required_nodes(flow: str) -> frozenset[str]:
    try:
        return _REQUIRED_NODES[flow]
    except (KeyError, TypeError) as error:
        raise ValueError(f"unknown Qwen workflow: {flow}") from error


def missing_required_nodes(available_nodes: Collection[str], flow: str) -> tuple[str, ...]:
    if available_nodes is None:
        raise TypeError("available_nodes is required")
    return tuple(sorted(required_nodes(flow).difference(available_nodes)))


def _git_blob(source_root: Path, revision: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(source_root), "show", f"{revision}:{path}"],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(f"pinned ComfyUI source unavailable: {revision[:12]}:{path}")
    return result.stdout


def _assert_fingerprint(data: bytes, expected_bytes: int | None, expected_hash: str) -> None:
    if expected_bytes is not None and len(data) != expected_bytes:
        raise ValueError("pinned ComfyUI source size changed")
    if hashlib.sha256(data).hexdigest() != expected_hash:
        raise ValueError("pinned ComfyUI source fingerprint changed")


def _changed_paths(old: object, new: object, prefix: str = "") -> set[str]:
    if isinstance(old, dict) and isinstance(new, dict):
        return set().union(*(
            _changed_paths(old.get(key), new.get(key), f"{prefix}/{key}")
            for key in old.keys() | new.keys()
        )) if old or new else set()
    if isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
        return set().union(*(
            _changed_paths(left, right, f"{prefix}/{index}")
            for index, (left, right) in enumerate(zip(old, new))
        )) if old else set()
    return {prefix} if old != new else set()


def verify_contract_sources(
    contract: CoreCandidateContract, source_root: Path = DEFAULT_SOURCE_ROOT
) -> VerificationReport:
    """Inspect pinned Git blobs; never execute code in the reference repository."""
    if not source_root.is_dir():
        return VerificationReport("unavailable-fixture-only", 0, 0, "unavailable")
    if contract.accepted_revision != ACCEPTED_REVISION or contract.candidate_revision != CANDIDATE_REVISION:
        raise ValueError("candidate contract revision changed")
    blobs: dict[str, bytes] = {}
    for artifact in contract.source_artifacts:
        data = _git_blob(source_root, contract.candidate_revision, artifact.path)
        _assert_fingerprint(data, artifact.bytes, artifact.sha256)
        blobs[artifact.path] = data

    for profile in contract.blueprint_profiles:
        old = _git_blob(source_root, contract.accepted_revision, profile.path)
        new = _git_blob(source_root, contract.candidate_revision, profile.path)
        _assert_fingerprint(old, None, profile.accepted_sha256)
        _assert_fingerprint(new, None, profile.candidate_sha256)
        try:
            old_json, new_json = json.loads(old), json.loads(new)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("invalid pinned Core blueprint") from error
        if _changed_paths(old_json, new_json) != {"/definitions/subgraphs/0/category"}:
            raise ValueError(f"Core blueprint semantic drift: {profile.profile}")

    facts = {
        "comfyui_version.py": ("0.37.0",),
        "requirements.txt": ("comfyui-frontend-package==1.53.6", "comfyui-workflow-templates==0.11.66", "comfyui-embedded-docs==0.5.12"),
        "comfy_extras/nodes_qwen.py": ("TextEncodeQwenImage21", "QwenImage21Cache", "range(1, 17)", "64", "16"),
        "server.py": ("asset_manager",),
        "execution.py": ("validate_loops", "register_executed_outputs", "emit_cached_output"),
        "comfy/controlnet.py": ("fast_disk=False",),
        "comfy/sample.py": ("fix_empty_latent_channels",),
        "nodes.py": ("downscale_ratio_spacial",),
    }
    for path, tokens in facts.items():
        content = blobs[path].decode("utf-8")
        if any(token not in content for token in tokens):
            raise ValueError(f"pinned Core runtime fact absent: {path}")
    return VerificationReport("verified", len(contract.source_artifacts), len(contract.blueprint_profiles), "verified")
