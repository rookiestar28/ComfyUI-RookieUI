from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUPPORTED_GRAPH_CONTRACT_PATH = (
    ROOT / "tests" / "fixtures" / "current_workflow_template_supported_graph_contract.json"
)

SCHEMA_VERSION = "workflow-template-supported-graph-contract-v1"
_SOURCE_KINDS = {"core-blueprint", "workflow-template-package"}
_DISPOSITIONS = {"invariant", "migrated"}
_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_TOP_LEVEL_FIELDS = {
    "active_core_revision",
    "active_workflow_templates_json_version",
    "active_workflow_templates_version",
    "candidate_core_revision",
    "candidate_workflow_templates_json_version",
    "candidate_workflow_templates_version",
    "core_blueprint_profile_count",
    "package_profile_count",
    "profile_count",
    "profiles",
    "schema_version",
    "unique_source_count",
    "workflow_template_source_revision",
    "workflow_template_source_tag",
}
_PROFILE_FIELDS = {
    "baseline_sha256",
    "candidate_sha256",
    "disposition",
    "id",
    "source_id",
    "source_kind",
}


@dataclass(frozen=True)
class SupportedGraphProfile:
    id: str
    source_kind: str
    source_id: str
    baseline_sha256: str
    candidate_sha256: str
    disposition: str


@dataclass(frozen=True)
class SupportedGraphContract:
    schema_version: str
    active_core_revision: str
    candidate_core_revision: str
    active_workflow_templates_version: str
    candidate_workflow_templates_version: str
    active_workflow_templates_json_version: str
    candidate_workflow_templates_json_version: str
    workflow_template_source_revision: str
    workflow_template_source_tag: str
    profile_count: int
    package_profile_count: int
    core_blueprint_profile_count: int
    unique_source_count: int
    profiles: tuple[SupportedGraphProfile, ...]


def _reject_duplicate_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"JSON object contains duplicate member: {key}")
        payload[key] = value
    return payload


def _require_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object.")
    return value


def _require_exact_fields(
    payload: Mapping[str, object], expected: set[str], context: str
) -> None:
    actual = set(payload)
    unknown = sorted(actual - expected)
    missing = sorted(expected - actual)
    if unknown:
        raise ValueError(f"{context} contains unknown fields: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{context} is missing fields: {', '.join(missing)}")


def _require_string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context} must be a non-empty string.")
    return value


def _require_exact_string(value: object, expected: str, context: str) -> str:
    actual = _require_string(value, context)
    if actual != expected:
        raise ValueError(f"{context} must equal {expected}.")
    return actual


def _require_revision(value: object, context: str) -> str:
    revision = _require_string(value, context)
    if not _REVISION_PATTERN.fullmatch(revision):
        raise ValueError(f"{context} must be a lowercase 40-character Git revision.")
    return revision


def _require_sha256(value: object, context: str) -> str:
    digest = _require_string(value, context)
    if not _SHA256_PATTERN.fullmatch(digest):
        raise ValueError(f"{context} must be a lowercase SHA-256 digest.")
    return digest


def _require_version(value: object, context: str) -> str:
    version = _require_string(value, context)
    if not _VERSION_PATTERN.fullmatch(version):
        raise ValueError(f"{context} must be a semantic version.")
    return version


def _require_count(value: object, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{context} must be a non-negative integer.")
    return value


def _require_source_id(value: object, context: str) -> str:
    source_id = _require_string(value, context)
    lowered = source_id.lower()
    if (
        any(character in source_id for character in ("/", "\\", ":", "\x00"))
        or "reference" in lowered
        or "localhost" in lowered
        or "://" in source_id
    ):
        raise ValueError(f"{context} must be a content-free logical identifier.")
    return source_id


def _parse_profile(value: object, index: int) -> SupportedGraphProfile:
    context = f"profiles[{index}]"
    payload = _require_mapping(value, context)
    _require_exact_fields(payload, _PROFILE_FIELDS, context)
    profile_id = _require_string(payload["id"], f"{context}.id")
    if not re.fullmatch(r"[a-z0-9_]+", profile_id):
        raise ValueError(f"{context}.id must be a lowercase profile identifier.")
    source_kind = _require_string(payload["source_kind"], f"{context}.source_kind")
    if source_kind not in _SOURCE_KINDS:
        raise ValueError(f"{context}.source_kind is invalid.")
    source_id = _require_source_id(payload["source_id"], f"{context}.source_id")
    if source_kind == "workflow-template-package" and not source_id.endswith(".json"):
        raise ValueError(f"{context}.source_id must identify a JSON package member.")
    if source_kind == "core-blueprint" and source_id.endswith(".json"):
        raise ValueError(f"{context}.source_id must identify a logical Core blueprint.")
    baseline_sha256 = _require_sha256(
        payload["baseline_sha256"], f"{context}.baseline_sha256"
    )
    candidate_sha256 = _require_sha256(
        payload["candidate_sha256"], f"{context}.candidate_sha256"
    )
    disposition = _require_string(payload["disposition"], f"{context}.disposition")
    if disposition not in _DISPOSITIONS:
        raise ValueError(f"{context}.disposition is invalid.")
    if disposition == "invariant" and baseline_sha256 != candidate_sha256:
        raise ValueError(f"{context}.disposition invariant requires equal hashes.")
    if disposition == "migrated" and baseline_sha256 == candidate_sha256:
        raise ValueError(f"{context}.disposition migrated requires changed content.")
    return SupportedGraphProfile(
        id=profile_id,
        source_kind=source_kind,
        source_id=source_id,
        baseline_sha256=baseline_sha256,
        candidate_sha256=candidate_sha256,
        disposition=disposition,
    )


def parse_supported_graph_contract_text(text: str) -> SupportedGraphContract:
    try:
        raw = json.loads(text, object_pairs_hook=_reject_duplicate_members)
    except json.JSONDecodeError as exc:
        raise ValueError(f"supported graph contract is invalid JSON: {exc.msg}") from exc
    payload = _require_mapping(raw, "supported graph contract")
    _require_exact_fields(payload, _TOP_LEVEL_FIELDS, "supported graph contract")
    raw_profiles = payload["profiles"]
    if not isinstance(raw_profiles, list):
        raise ValueError("profiles must be an array.")
    profiles = tuple(_parse_profile(value, index) for index, value in enumerate(raw_profiles))
    profile_ids = tuple(profile.id for profile in profiles)
    if len(set(profile_ids)) != len(profile_ids):
        raise ValueError("profiles contains duplicate profile ids.")
    if profile_ids != tuple(sorted(profile_ids)):
        raise ValueError("profiles must be sorted by id.")

    profile_count = _require_count(payload["profile_count"], "profile_count")
    package_count = _require_count(
        payload["package_profile_count"], "package_profile_count"
    )
    core_count = _require_count(
        payload["core_blueprint_profile_count"], "core_blueprint_profile_count"
    )
    unique_source_count = _require_count(
        payload["unique_source_count"], "unique_source_count"
    )
    actual_package_count = sum(
        profile.source_kind == "workflow-template-package" for profile in profiles
    )
    actual_core_count = sum(profile.source_kind == "core-blueprint" for profile in profiles)
    actual_unique_count = len(
        {(profile.source_kind, profile.source_id) for profile in profiles}
    )
    if profile_count != len(profiles):
        raise ValueError("profile_count does not match profiles.")
    if package_count != actual_package_count:
        raise ValueError("package_profile_count does not match profiles.")
    if core_count != actual_core_count:
        raise ValueError("core_blueprint_profile_count does not match profiles.")
    if unique_source_count != actual_unique_count:
        raise ValueError("unique_source_count does not match profiles.")
    if (profile_count, package_count, core_count, unique_source_count) != (26, 11, 15, 25):
        raise ValueError("supported graph inventory must equal 26/11/15/25.")

    return SupportedGraphContract(
        schema_version=_require_exact_string(
            payload["schema_version"], SCHEMA_VERSION, "schema_version"
        ),
        active_core_revision=_require_exact_string(
            _require_revision(payload["active_core_revision"], "active_core_revision"),
            "c67885b14556cf3e4e061862925282d403d09862",
            "active_core_revision",
        ),
        candidate_core_revision=_require_exact_string(
            _require_revision(payload["candidate_core_revision"], "candidate_core_revision"),
            "c67885b14556cf3e4e061862925282d403d09862",
            "candidate_core_revision",
        ),
        active_workflow_templates_version=_require_exact_string(
            _require_version(
                payload["active_workflow_templates_version"],
                "active_workflow_templates_version",
            ),
            "0.11.43",
            "active_workflow_templates_version",
        ),
        candidate_workflow_templates_version=_require_exact_string(
            _require_version(
                payload["candidate_workflow_templates_version"],
                "candidate_workflow_templates_version",
            ),
            "0.11.43",
            "candidate_workflow_templates_version",
        ),
        active_workflow_templates_json_version=_require_exact_string(
            _require_version(
                payload["active_workflow_templates_json_version"],
                "active_workflow_templates_json_version",
            ),
            "0.1.49",
            "active_workflow_templates_json_version",
        ),
        candidate_workflow_templates_json_version=_require_exact_string(
            _require_version(
                payload["candidate_workflow_templates_json_version"],
                "candidate_workflow_templates_json_version",
            ),
            "0.1.49",
            "candidate_workflow_templates_json_version",
        ),
        workflow_template_source_revision=_require_exact_string(
            _require_revision(
                payload["workflow_template_source_revision"],
                "workflow_template_source_revision",
            ),
            "f54739874c88e5a1154275c4597b3860e5a617b4",
            "workflow_template_source_revision",
        ),
        workflow_template_source_tag=_require_exact_string(
            payload["workflow_template_source_tag"],
            "v0.11.43",
            "workflow_template_source_tag",
        ),
        profile_count=profile_count,
        package_profile_count=package_count,
        core_blueprint_profile_count=core_count,
        unique_source_count=unique_source_count,
        profiles=profiles,
    )


def serialize_supported_graph_contract(contract: SupportedGraphContract) -> str:
    return json.dumps(asdict(contract), indent=2, sort_keys=True) + "\n"


def load_supported_graph_contract(
    path: Path = DEFAULT_SUPPORTED_GRAPH_CONTRACT_PATH,
) -> SupportedGraphContract:
    return parse_supported_graph_contract_text(path.read_text(encoding="utf-8"))
