from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path, PurePosixPath
import re
from typing import Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MEMBER_DELTA_CONTRACT_PATH = (
    ROOT / "tests" / "fixtures" / "current_workflow_template_member_delta_contract.json"
)
SCHEMA_VERSION = "workflow-template-member-delta-contract-v1"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_BASELINE_ARTIFACT_SHA256 = "4f9f472f02d13f5f57d6af8d7d83ea062409c3d3cfe4c301d379eaadf9caabb3"
_CANDIDATE_ARTIFACT_SHA256 = "e579760ce1b71200ed5a05a52373dee88931f47d413c13f5767096f24941d40a"
_FROM_INVENTORY_SHA256 = "d13686fed5be5a28083a9a80ee8a662ea17695837f4177e49871c6a0dd72170d"
_TO_INVENTORY_SHA256 = "dbac20574a4163cbe7211d1620f615070ebb06a6e4b84dfe5865dc5b24424fce"
_TOP_LEVEL_FIELDS = {
    "added_members",
    "baseline_artifact_sha256",
    "candidate_artifact_sha256",
    "changed_members",
    "from_inventory_sha256",
    "from_json_version",
    "from_member_count",
    "from_members",
    "from_version",
    "invariant_members",
    "removed_members",
    "schema_version",
    "to_inventory_sha256",
    "to_json_version",
    "to_member_count",
    "to_members",
    "to_version",
}


@dataclass(frozen=True)
class WorkflowTemplateMemberDeltaContract:
    schema_version: str
    from_version: str
    to_version: str
    from_json_version: str
    to_json_version: str
    baseline_artifact_sha256: str
    candidate_artifact_sha256: str
    from_inventory_sha256: str
    to_inventory_sha256: str
    from_member_count: int
    to_member_count: int
    from_members: tuple[str, ...]
    to_members: tuple[str, ...]
    invariant_members: tuple[str, ...]
    added_members: tuple[str, ...]
    changed_members: tuple[str, ...]
    removed_members: tuple[str, ...]


def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON object contains duplicate member: {key}")
        result[key] = value
    return result


def _exact_fields(payload: Mapping[str, object]) -> None:
    unknown = sorted(set(payload) - _TOP_LEVEL_FIELDS)
    missing = sorted(_TOP_LEVEL_FIELDS - set(payload))
    if unknown:
        raise ValueError(f"member delta contract contains unknown fields: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"member delta contract is missing fields: {', '.join(missing)}")


def _exact_string(value: object, expected: str, context: str) -> str:
    if value != expected:
        raise ValueError(f"{context} must equal {expected}.")
    return expected


def _sha256(value: object, context: str) -> str:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{context} must be a lowercase SHA-256 digest.")
    return value


def _exact_sha256(value: object, expected: str, context: str) -> str:
    digest = _sha256(value, context)
    if digest != expected:
        raise ValueError(f"{context} does not match the exact inventory evidence.")
    return digest


def _count(value: object, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{context} must be a non-negative integer.")
    return value


def _members(value: object, context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be an array.")
    result: list[str] = []
    for member in value:
        if not isinstance(member, str) or not member.endswith(".json"):
            raise ValueError(f"{context} contains an invalid JSON member.")
        path = PurePosixPath(member)
        if path.is_absolute() or "\\" in member or any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError(f"{context} contains an unsafe member.")
        result.append(member)
    if tuple(result) != tuple(sorted(result)):
        raise ValueError(f"{context} must be sorted.")
    if len(result) != len(set(result)):
        raise ValueError(f"{context} contains duplicate members.")
    return tuple(result)


def parse_member_delta_contract_text(text: str) -> WorkflowTemplateMemberDeltaContract:
    try:
        raw = json.loads(text, object_pairs_hook=_reject_duplicates)
    except json.JSONDecodeError as exc:
        raise ValueError(f"member delta contract is invalid JSON: {exc.msg}") from exc
    if not isinstance(raw, dict):
        raise ValueError("member delta contract must be an object.")
    _exact_fields(raw)
    from_members = _members(raw["from_members"], "from_members")
    to_members = _members(raw["to_members"], "to_members")
    invariant = _members(raw["invariant_members"], "invariant_members")
    added = _members(raw["added_members"], "added_members")
    changed = _members(raw["changed_members"], "changed_members")
    removed = _members(raw["removed_members"], "removed_members")
    partition = (*invariant, *added, *changed, *removed)
    if len(partition) != len(set(partition)):
        raise ValueError("member disposition partition contains duplicate members.")
    if set(from_members) != set(invariant) | set(changed) | set(removed):
        raise ValueError("from_members does not match the disposition partition.")
    if set(to_members) != set(invariant) | set(changed) | set(added):
        raise ValueError("to_members does not match the disposition partition.")
    from_count = _count(raw["from_member_count"], "from_member_count")
    to_count = _count(raw["to_member_count"], "to_member_count")
    if from_count != len(from_members) or to_count != len(to_members):
        raise ValueError("member count does not match the exact inventory.")
    return WorkflowTemplateMemberDeltaContract(
        schema_version=_exact_string(raw["schema_version"], SCHEMA_VERSION, "schema_version"),
        from_version=_exact_string(raw["from_version"], "0.11.43", "from_version"),
        to_version=_exact_string(raw["to_version"], "0.11.54", "to_version"),
        from_json_version=_exact_string(raw["from_json_version"], "0.1.49", "from_json_version"),
        to_json_version=_exact_string(raw["to_json_version"], "0.1.66", "to_json_version"),
        baseline_artifact_sha256=_exact_sha256(raw["baseline_artifact_sha256"], _BASELINE_ARTIFACT_SHA256, "baseline_artifact_sha256"),
        candidate_artifact_sha256=_exact_sha256(raw["candidate_artifact_sha256"], _CANDIDATE_ARTIFACT_SHA256, "candidate_artifact_sha256"),
        from_inventory_sha256=_exact_sha256(raw["from_inventory_sha256"], _FROM_INVENTORY_SHA256, "from_inventory_sha256"),
        to_inventory_sha256=_exact_sha256(raw["to_inventory_sha256"], _TO_INVENTORY_SHA256, "to_inventory_sha256"),
        from_member_count=from_count,
        to_member_count=to_count,
        from_members=from_members,
        to_members=to_members,
        invariant_members=invariant,
        added_members=added,
        changed_members=changed,
        removed_members=removed,
    )


def serialize_member_delta_contract(contract: WorkflowTemplateMemberDeltaContract) -> str:
    return json.dumps(asdict(contract), indent=2, sort_keys=True) + "\n"


def load_member_delta_contract(
    path: Path = DEFAULT_MEMBER_DELTA_CONTRACT_PATH,
) -> WorkflowTemplateMemberDeltaContract:
    return parse_member_delta_contract_text(path.read_text(encoding="utf-8"))
