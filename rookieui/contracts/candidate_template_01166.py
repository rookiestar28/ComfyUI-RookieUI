"""Inert package-source freeze for workflow-template candidate 0.11.66.

The candidate does not change the accepted template source basis or advertise
any of its newly shipped workflow examples as a RookieUI capability.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from dataclasses import asdict, dataclass
from email.parser import BytesParser
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from rookieui.contracts.candidate_core_037 import (
    DEFAULT_SOURCE_ROOT as DEFAULT_CORE_ROOT,
    load_contract as load_core_contract,
    verify_contract_sources,
)
from rookieui.contracts.workflow_template_artifact_contract import ArtifactSpec, WheelInventory, inspect_wheel


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = ROOT / "tests/fixtures/template_01166_candidate_contract.json"
DEFAULT_ARTIFACT_ROOT = ROOT / "reference/docs/260922_qwen21_host_alignment"
DEFAULT_TEMPLATE_GIT_ROOT = ROOT / "reference/workflow_templates_source"
CURRENT_PROFILE_SOURCES = ROOT / "tests/fixtures/current_host_profile_sources.json"
SCHEMA_VERSION = "template-01166-candidate-v1"
SOURCE_REVISION = "7ce126c4ec77f44cc7a60f93eec52a197efb9ce5"
FIXTURE_SHA256 = "734ecebd6c36b28aa1685b78c515484362afc91d95ad94f216c53d4927316b4f"
PREFIX = "comfyui_workflow_templates_json/templates/"
_ARTIFACTS = MappingProxyType({
    "old_json": ArtifactSpec("comfyui_workflow_templates_json-0.1.66-py3-none-any.whl", 3305529, "e579760ce1b71200ed5a05a52373dee88931f47d413c13f5767096f24941d40a"),
    "meta": ArtifactSpec("comfyui_workflow_templates-0.11.66-py3-none-any.whl", 10878, "2af993e84bb5a89e66ba84697540cf215093023c4a0c004ff4cc2be0237a198e"),
    "core": ArtifactSpec("comfyui_workflow_templates_core-0.3.357-py3-none-any.whl", 76627, "fa8daef2665a1d8594bef53a58ffbc47a0788fc3bbd8b68b4a6ad6c62b1b4033"),
    "json": ArtifactSpec("comfyui_workflow_templates_json-0.1.92-py3-none-any.whl", 3575217, "680dd90525faeeb41dbcd6724c6006513d607b7c3a418ab173fa850c83dc91b1"),
})
_REQUIRED_COMPONENTS = MappingProxyType({
    "comfyui-workflow-templates-core": "0.3.357",
    "comfyui-workflow-templates-json": "0.1.92",
    "comfyui-workflow-templates-media-api": "0.3.84",
    "comfyui-workflow-templates-media-video": "0.3.101",
    "comfyui-workflow-templates-media-image": "0.3.160",
    "comfyui-workflow-templates-media-other": "0.3.229",
    "comfyui-workflow-templates-media-assets-01": "0.1.47",
    "comfyui-workflow-templates-media-assets-02": "0.1.3",
})
_QWEN_MEMBERS = MappingProxyType({
    "txt2img": PREFIX + "image_qwen_image_2_1_t2i.json",
    "edit": PREFIX + "image_qwen_image_2_1_image_edit.json",
    "background-removal": PREFIX + "image_qwen_image_2_1_background_removal.json",
})
_TOP_FIELDS = frozenset({
    "affected_members", "artifacts", "new_json_count", "old_json_count",
    "preserved_profiles", "qwen_members", "required_components", "schema_version",
    "source_revision", "unchanged_count",
})
_ENTRY_FIELDS = frozenset({"path", "change", "disposition", "owner", "reason"})
_PROFILE_FIELDS = frozenset({"profile", "member"})


@dataclass(frozen=True)
class AffectedMember:
    path: str
    change: str
    disposition: str
    owner: str
    reason: str


@dataclass(frozen=True)
class PreservedProfile:
    profile: str
    member: str


@dataclass(frozen=True)
class TemplateCandidateContract:
    artifacts: Mapping[str, ArtifactSpec]
    required_components: Mapping[str, str]
    affected_members: tuple[AffectedMember, ...]
    preserved_profiles: tuple[PreservedProfile, ...]
    qwen_members: Mapping[str, str]
    old_json_count: int
    new_json_count: int
    unchanged_count: int
    source_revision: str


@dataclass(frozen=True)
class VerificationReport:
    status: str
    artifacts: int
    affected: int
    preserved_profiles: int
    qwen_git_matches: int
    core_blueprints: int


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate template candidate field: {key}")
        result[key] = value
    return result


def _safe_member(value: object) -> str:
    if not isinstance(value, str) or not value.startswith(PREFIX) or not value.endswith(".json"):
        raise ValueError("invalid template member path")
    if "\\" in value or "\x00" in value or "//" in value or "/../" in value or "/./" in value:
        raise ValueError("unsafe template member path")
    return value


def _expected_disposition(path: str, change: str) -> tuple[str, str, str]:
    base = path.rsplit("/", 1)[-1]
    if change == "removed":
        if not base.startswith("api_openai_dall_e_"):
            raise ValueError("unexpected removed template")
        return "removed", "none", "removed-provider-example"
    if base.startswith("image_qwen_image_2_1_"):
        return "pending", "future-txt2img" if base.endswith("_t2i.json") else "future-edit", "qwen-feature-not-yet-implemented"
    if base.startswith("index"):
        return "reference-only", "none", "catalog-data-not-runtime"
    if base.startswith("api_"):
        return "out-of-scope", "none", "provider-runtime-not-shipped"
    if base.startswith(("video_", "template_seedance")):
        return "out-of-scope", "none", "video-runtime-not-shipped"
    if base.startswith("audio_"):
        return "out-of-scope", "none", "audio-runtime-not-shipped"
    if base.startswith("3d_"):
        return "out-of-scope", "none", "three-d-runtime-not-shipped"
    if base.startswith(("image_", "hidream_")):
        return "reference-only", "none", "unplanned-image-example"
    if base.startswith(("utility_", "templates_mjm_")):
        return "out-of-scope", "none", "utility-runtime-not-shipped"
    raise ValueError(f"unclassified template member: {base}")


def parse_contract_text(text: str) -> TemplateCandidateContract:
    try:
        raw = json.loads(text, object_pairs_hook=_unique_pairs)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError("invalid template candidate JSON") from error
    if not isinstance(raw, dict) or raw.keys() != _TOP_FIELDS:
        raise ValueError("unexpected template candidate fields")
    if raw["schema_version"] != SCHEMA_VERSION or raw["source_revision"] != SOURCE_REVISION:
        raise ValueError("unexpected template candidate identity")
    if raw["required_components"] != dict(_REQUIRED_COMPONENTS):
        raise ValueError("unresolved required template component")
    if raw["qwen_members"] != dict(_QWEN_MEMBERS):
        raise ValueError("unexpected Qwen workflow source")
    if tuple(raw[key] for key in ("old_json_count", "new_json_count", "unchanged_count")) != (547, 580, 484):
        raise ValueError("template inventory counts changed")
    if not isinstance(raw["artifacts"], dict) or raw["artifacts"].keys() != _ARTIFACTS.keys():
        raise ValueError("incomplete template artifact freeze")
    for key, spec in _ARTIFACTS.items():
        row = raw["artifacts"][key]
        if not isinstance(row, dict) or row != asdict(spec):
            raise ValueError(f"template artifact identity changed: {key}")

    rows = raw["affected_members"]
    if not isinstance(rows, list) or len(rows) != 99:
        raise ValueError("incomplete template member dispositions")
    parsed: list[AffectedMember] = []
    for row in rows:
        if not isinstance(row, dict) or row.keys() != _ENTRY_FIELDS:
            raise ValueError("invalid affected member entry")
        path = _safe_member(row["path"])
        if row["change"] not in ("added", "removed", "changed"):
            raise ValueError("invalid template change kind")
        if (row["disposition"], row["owner"], row["reason"]) != _expected_disposition(path, row["change"]):
            raise ValueError("template support disposition changed")
        parsed.append(AffectedMember(**row))
    if tuple(row.path for row in parsed) != tuple(sorted(set(row.path for row in parsed))):
        raise ValueError("template dispositions must be unique and sorted")
    if tuple(sum(row.change == kind for row in parsed) for kind in ("added", "removed", "changed")) != (36, 3, 60):
        raise ValueError("template delta counts changed")
    if {row.path for row in parsed if row.disposition == "pending"} != set(_QWEN_MEMBERS.values()):
        raise ValueError("Qwen pending-source ownership changed")

    profiles = raw["preserved_profiles"]
    if not isinstance(profiles, list) or len(profiles) != 11:
        raise ValueError("incomplete preserved template profiles")
    for row in profiles:
        if not isinstance(row, dict) or row.keys() != _PROFILE_FIELDS:
            raise ValueError("invalid preserved profile")
        _safe_member(row["member"])
    if tuple(row["profile"] for row in profiles) != tuple(sorted(set(row["profile"] for row in profiles))):
        raise ValueError("preserved profiles must be unique and sorted")
    if sum(row["profile"] == "krea2_turbo" for row in profiles) != 1:
        raise ValueError("Krea 2 Turbo profile identity changed")
    if any(row["member"] in {entry.path for entry in parsed} for row in profiles):
        raise ValueError("an existing supported template unexpectedly changed")

    # CRITICAL: only this reviewed source/disposition freeze is admissible;
    # accepting an edited list could silently claim unsupported workflows.
    canonical = json.dumps(raw, sort_keys=True, indent=2) + "\n"
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != FIXTURE_SHA256:
        raise ValueError("template candidate freeze fingerprint changed")
    return TemplateCandidateContract(
        artifacts=MappingProxyType(dict(_ARTIFACTS)),
        required_components=MappingProxyType(dict(_REQUIRED_COMPONENTS)),
        affected_members=tuple(parsed),
        preserved_profiles=tuple(PreservedProfile(**row) for row in profiles),
        qwen_members=MappingProxyType(dict(_QWEN_MEMBERS)),
        old_json_count=547,
        new_json_count=580,
        unchanged_count=484,
        source_revision=SOURCE_REVISION,
    )


def load_contract(path: Path = DEFAULT_FIXTURE) -> TemplateCandidateContract:
    return parse_contract_text(path.read_text(encoding="utf-8"))


def serialize_contract(contract: TemplateCandidateContract) -> str:
    payload: dict[str, object] = {
        "affected_members": [asdict(row) for row in contract.affected_members],
        "artifacts": {key: asdict(row) for key, row in contract.artifacts.items()},
        "new_json_count": contract.new_json_count,
        "old_json_count": contract.old_json_count,
        "preserved_profiles": [asdict(row) for row in contract.preserved_profiles],
        "qwen_members": dict(contract.qwen_members),
        "required_components": dict(contract.required_components),
        "schema_version": SCHEMA_VERSION,
        "source_revision": contract.source_revision,
        "unchanged_count": contract.unchanged_count,
    }
    return json.dumps(payload, sort_keys=True, indent=2) + "\n"


def _metadata(path: Path, spec: ArtifactSpec) -> tuple[str, str, tuple[str, ...]]:
    name = spec.filename.split("-py3-none-any.whl", 1)[0] + ".dist-info/METADATA"
    with zipfile.ZipFile(path) as wheel:
        if name not in wheel.namelist():
            raise ValueError("template wheel metadata is missing")
        data = wheel.read(name)
    if len(data) > 1024 * 1024:
        raise ValueError("template wheel metadata is oversized")
    message = BytesParser().parsebytes(data)
    return message.get("Name", ""), message.get("Version", ""), tuple(message.get_all("Requires-Dist", []))


def _json_members(inventory: WheelInventory) -> dict[str, str]:
    return {
        row.name: row.sha256
        for row in inventory.members
        if row.name.startswith(PREFIX) and row.name.endswith(".json") and row.sha256 is not None
    }


def verify_candidate(
    contract: TemplateCandidateContract,
    *,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
    template_git_root: Path = DEFAULT_TEMPLATE_GIT_ROOT,
    core_root: Path = DEFAULT_CORE_ROOT,
) -> VerificationReport:
    """Verify all four inert wheels and pinned Git blobs without importing them."""
    if not artifact_root.is_dir():
        return VerificationReport("unavailable-fixture-only", 0, 0, 0, 0, 0)
    inventories = {
        key: inspect_wheel(artifact_root, spec)
        for key, spec in contract.artifacts.items()
    }
    expected_metadata = {
        "old_json": ("comfyui-workflow-templates-json", "0.1.66"),
        "meta": ("comfyui-workflow-templates", "0.11.66"),
        "core": ("comfyui-workflow-templates-core", "0.3.357"),
        "json": ("comfyui-workflow-templates-json", "0.1.92"),
    }
    metadata = {}
    for key, spec in contract.artifacts.items():
        actual = _metadata(artifact_root / spec.filename, spec)
        if (actual[0].replace("_", "-").lower(), actual[1]) != expected_metadata[key]:
            raise ValueError(f"template wheel metadata identity changed: {key}")
        metadata[key] = actual
    required: dict[str, str] = {}
    for line in metadata["meta"][2]:
        specifier, _, marker = line.partition(";")
        package, delimiter, version = specifier.strip().partition("==")
        if delimiter != "==" or package not in contract.required_components:
            raise ValueError("unresolved template requirement")
        if version != contract.required_components[package]:
            raise ValueError("template required component version changed")
        if not marker:
            if package in required:
                raise ValueError("duplicate base template requirement")
            required[package] = version
    if required != dict(contract.required_components):
        raise ValueError("incomplete required template component closure")

    old = _json_members(inventories["old_json"])
    new = _json_members(inventories["json"])
    old_names, new_names = set(old), set(new)
    added, removed = new_names - old_names, old_names - new_names
    changed = {name for name in old_names & new_names if old[name] != new[name]}
    unchanged = old_names & new_names - changed
    if (len(old), len(new), len(unchanged), len(added), len(removed), len(changed)) != (
        contract.old_json_count, contract.new_json_count, contract.unchanged_count, 36, 3, 60
    ):
        raise ValueError("template package member accounting changed")
    observed = {**{name: "added" for name in added}, **{name: "removed" for name in removed}, **{name: "changed" for name in changed}}
    if observed != {row.path: row.change for row in contract.affected_members}:
        raise ValueError("template member disposition inventory changed")

    profiles = json.loads(CURRENT_PROFILE_SOURCES.read_text(encoding="utf-8"))["profiles"]
    for item in contract.preserved_profiles:
        record = profiles.get(item.profile)
        if not isinstance(record, dict) or record["source_kind"] != "workflow-template-package":
            raise ValueError("supported package profile source is missing")
        if item.member != PREFIX + record["locator"].split(":", 1)[-1]:
            raise ValueError("supported package profile locator changed")
        if old.get(item.member) != record["sha256"] or new.get(item.member) != record["sha256"]:
            raise ValueError("supported package profile bytes changed")

    if not template_git_root.is_dir() or not core_root.is_dir():
        return VerificationReport("wheel-verified-source-unavailable", 4, 99, 11, 0, 0)
    with zipfile.ZipFile(artifact_root / contract.artifacts["json"].filename) as wheel:
        for member in contract.qwen_members.values():
            path = "templates/" + member.removeprefix(PREFIX)
            result = subprocess.run(
                ["git", "-C", str(template_git_root), "show", f"{contract.source_revision}:{path}"],
                capture_output=True,
                check=False,
            )
            if result.returncode or result.stdout != wheel.read(member):
                raise ValueError(f"Qwen pinned Git/package member mismatch: {path}")
    core_report = verify_contract_sources(load_core_contract(), source_root=core_root)
    if core_report.status != "verified" or core_report.verified_blueprints != 15:
        raise ValueError("Core blueprint candidate evidence unavailable")
    return VerificationReport("verified", 4, 99, 11, 3, 15)
