from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT_PATH = (
    ROOT / "tests" / "fixtures" / "current_workflow_template_surface_disposition_contract.json"
)

SCHEMA_VERSION = "workflow-template-surface-disposition-contract-v1"
_CHANGE_KINDS = {"added", "archived", "changed", "removed"}
_DISPOSITIONS = {
    "deferred",
    "out-of-scope",
    "reference-only",
    "removed",
    "superseded",
    "supported",
}
_RATIONALE_DISPOSITIONS = {
    "audio-runtime-not-shipped": "out-of-scope",
    "catalog-metadata-not-runtime": "reference-only",
    "image-product-scope-not-shipped": "deferred",
    "provider-runtime-not-shipped": "out-of-scope",
    "upstream-archived-surface": "superseded",
    "video-runtime-not-shipped": "out-of-scope",
}
_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SURFACE_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_ENTRY_FIELDS = {
    "archived_sha256",
    "change_kind",
    "disposition",
    "id",
    "new_sha256",
    "old_sha256",
    "rationale",
}
_TOP_LEVEL_FIELDS = {
    "added_count",
    "archived_count",
    "changed_count",
    "disposition_counts",
    "entries",
    "entry_count",
    "from_json_version",
    "from_revision",
    "from_version",
    "new_member_count",
    "new_wheel_sha256",
    "old_member_count",
    "old_wheel_sha256",
    "removed_count",
    "schema_version",
    "source_report_sha256",
    "supported_package_profile_count",
    "supported_package_source_count",
    "to_json_version",
    "to_revision",
    "to_version",
    "unchanged_count",
    "union_count",
}


def _require_sha256_or_none(value: object, context: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{context} must be null or a lowercase SHA-256 digest.")
    return value


@dataclass(frozen=True)
class SurfaceDispositionEntry:
    id: str
    change_kind: str
    disposition: str
    rationale: str
    old_sha256: str | None
    new_sha256: str | None
    archived_sha256: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not _SURFACE_PATTERN.fullmatch(self.id):
            raise ValueError("surface id must be a content-free logical identifier.")
        lowered = self.id.lower()
        if "reference" in lowered or "localhost" in lowered or "://" in self.id:
            raise ValueError("surface id must not contain a path, URL, or private locator.")
        if self.change_kind not in _CHANGE_KINDS:
            raise ValueError("surface change_kind is invalid.")
        if self.disposition not in _DISPOSITIONS:
            raise ValueError("surface disposition is invalid.")
        expected_disposition = _RATIONALE_DISPOSITIONS.get(self.rationale)
        if expected_disposition is None or self.disposition != expected_disposition:
            raise ValueError("surface rationale/disposition combination is invalid.")
        old_hash = _require_sha256_or_none(self.old_sha256, "old_sha256")
        new_hash = _require_sha256_or_none(self.new_sha256, "new_sha256")
        archived_hash = _require_sha256_or_none(self.archived_sha256, "archived_sha256")
        if self.change_kind == "added" and not (
            old_hash is None and new_hash is not None and archived_hash is None
        ):
            raise ValueError("added surface hash shape is invalid.")
        if self.change_kind == "changed" and not (
            old_hash is not None
            and new_hash is not None
            and old_hash != new_hash
            and archived_hash is None
        ):
            raise ValueError("changed surface hash shape is invalid.")
        if self.change_kind == "archived" and not (
            old_hash is not None
            and new_hash is None
            and archived_hash == old_hash
            and self.disposition == "superseded"
        ):
            raise ValueError("archived surface hash/disposition shape is invalid.")
        if self.change_kind == "removed" and not (
            old_hash is not None
            and new_hash is None
            and archived_hash is None
            and self.disposition == "removed"
        ):
            raise ValueError("removed surface hash/disposition shape is invalid.")


@dataclass(frozen=True)
class SurfaceDispositionContract:
    schema_version: str
    from_version: str
    to_version: str
    from_json_version: str
    to_json_version: str
    from_revision: str
    to_revision: str
    old_wheel_sha256: str
    new_wheel_sha256: str
    source_report_sha256: str
    old_member_count: int
    new_member_count: int
    union_count: int
    added_count: int
    changed_count: int
    removed_count: int
    archived_count: int
    unchanged_count: int
    entry_count: int
    supported_package_profile_count: int
    supported_package_source_count: int
    disposition_counts: Mapping[str, int]
    entries: tuple[SurfaceDispositionEntry, ...]


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
    unknown = sorted(set(payload) - expected)
    missing = sorted(expected - set(payload))
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


def _require_pattern(value: object, pattern: re.Pattern[str], context: str) -> str:
    actual = _require_string(value, context)
    if not pattern.fullmatch(actual):
        raise ValueError(f"{context} has an invalid format.")
    return actual


def _require_count(value: object, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{context} must be a non-negative integer.")
    return value


def _parse_entry(value: object, index: int) -> SurfaceDispositionEntry:
    context = f"entries[{index}]"
    payload = _require_mapping(value, context)
    _require_exact_fields(payload, _ENTRY_FIELDS, context)
    return SurfaceDispositionEntry(
        id=_require_string(payload["id"], f"{context}.id"),
        change_kind=_require_string(payload["change_kind"], f"{context}.change_kind"),
        disposition=_require_string(payload["disposition"], f"{context}.disposition"),
        rationale=_require_string(payload["rationale"], f"{context}.rationale"),
        old_sha256=_require_sha256_or_none(payload["old_sha256"], f"{context}.old_sha256"),
        new_sha256=_require_sha256_or_none(payload["new_sha256"], f"{context}.new_sha256"),
        archived_sha256=_require_sha256_or_none(
            payload["archived_sha256"], f"{context}.archived_sha256"
        ),
    )


def parse_surface_disposition_contract(value: object) -> SurfaceDispositionContract:
    payload = _require_mapping(value, "surface disposition contract")
    _require_exact_fields(payload, _TOP_LEVEL_FIELDS, "surface disposition contract")
    raw_entries = payload["entries"]
    if not isinstance(raw_entries, list):
        raise ValueError("entries must be an array.")
    entries = tuple(_parse_entry(entry, index) for index, entry in enumerate(raw_entries))
    entry_ids = tuple(entry.id for entry in entries)
    if len(set(entry_ids)) != len(entry_ids):
        raise ValueError("entries contains duplicate surface ids.")
    if entry_ids != tuple(sorted(entry_ids)):
        raise ValueError("entries must be sorted by id.")

    counts = {
        name: _require_count(payload[name], name)
        for name in (
            "added_count",
            "archived_count",
            "changed_count",
            "entry_count",
            "new_member_count",
            "old_member_count",
            "removed_count",
            "supported_package_profile_count",
            "supported_package_source_count",
            "unchanged_count",
            "union_count",
        )
    }
    expected_counts = {
        "added_count": 21,
        "archived_count": 16,
        "changed_count": 20,
        "entry_count": 57,
        "new_member_count": 518,
        "old_member_count": 513,
        "removed_count": 16,
        "supported_package_profile_count": 11,
        "supported_package_source_count": 11,
        "unchanged_count": 477,
        "union_count": 534,
    }
    if counts != expected_counts:
        raise ValueError("surface disposition aggregate counts are not exact.")
    actual_kind_counts = {
        kind: sum(entry.change_kind == kind for entry in entries) for kind in _CHANGE_KINDS
    }
    if actual_kind_counts != {"added": 21, "archived": 16, "changed": 20, "removed": 0}:
        raise ValueError("entry change-kind counts do not match the exact delta.")

    raw_disposition_counts = _require_mapping(
        payload["disposition_counts"], "disposition_counts"
    )
    _require_exact_fields(raw_disposition_counts, _DISPOSITIONS, "disposition_counts")
    disposition_counts = {
        name: _require_count(raw_disposition_counts[name], f"disposition_counts.{name}")
        for name in sorted(_DISPOSITIONS)
    }
    actual_disposition_counts = {
        disposition: sum(entry.disposition == disposition for entry in entries)
        for disposition in sorted(_DISPOSITIONS)
    }
    if disposition_counts != actual_disposition_counts:
        raise ValueError("disposition_counts does not match entries.")
    if disposition_counts != {
        "deferred": 2,
        "out-of-scope": 25,
        "reference-only": 14,
        "removed": 0,
        "superseded": 16,
        "supported": 0,
    }:
        raise ValueError("surface dispositions are not the accepted exact classification.")

    return SurfaceDispositionContract(
        schema_version=_require_exact_string(
            payload["schema_version"], SCHEMA_VERSION, "schema_version"
        ),
        from_version=_require_exact_string(payload["from_version"], "0.11.31", "from_version"),
        to_version=_require_exact_string(payload["to_version"], "0.11.43", "to_version"),
        from_json_version=_require_exact_string(
            payload["from_json_version"], "0.1.30", "from_json_version"
        ),
        to_json_version=_require_exact_string(
            payload["to_json_version"], "0.1.49", "to_json_version"
        ),
        from_revision=_require_exact_string(
            _require_pattern(payload["from_revision"], _REVISION_PATTERN, "from_revision"),
            "a832a091491ce5b6341f4e4ca548b7ab536b6acd",
            "from_revision",
        ),
        to_revision=_require_exact_string(
            _require_pattern(payload["to_revision"], _REVISION_PATTERN, "to_revision"),
            "f54739874c88e5a1154275c4597b3860e5a617b4",
            "to_revision",
        ),
        old_wheel_sha256=_require_exact_string(
            _require_pattern(payload["old_wheel_sha256"], _SHA256_PATTERN, "old_wheel_sha256"),
            "61ba5b43f2acd74b3db9395e9a4138f171a75f4a304fb3fc0fd8d77051beeaf9",
            "old_wheel_sha256",
        ),
        new_wheel_sha256=_require_exact_string(
            _require_pattern(payload["new_wheel_sha256"], _SHA256_PATTERN, "new_wheel_sha256"),
            "4f9f472f02d13f5f57d6af8d7d83ea062409c3d3cfe4c301d379eaadf9caabb3",
            "new_wheel_sha256",
        ),
        source_report_sha256=_require_exact_string(
            _require_pattern(
                payload["source_report_sha256"], _SHA256_PATTERN, "source_report_sha256"
            ),
            "c3d1d85129ebd7785b42c7b601ed6a5aa19658757ab8b3f8d10c3a639c1dd409",
            "source_report_sha256",
        ),
        old_member_count=counts["old_member_count"],
        new_member_count=counts["new_member_count"],
        union_count=counts["union_count"],
        added_count=counts["added_count"],
        changed_count=counts["changed_count"],
        removed_count=counts["removed_count"],
        archived_count=counts["archived_count"],
        unchanged_count=counts["unchanged_count"],
        entry_count=counts["entry_count"],
        supported_package_profile_count=counts["supported_package_profile_count"],
        supported_package_source_count=counts["supported_package_source_count"],
        disposition_counts=MappingProxyType(disposition_counts),
        entries=entries,
    )


def parse_surface_disposition_contract_text(text: str) -> SurfaceDispositionContract:
    try:
        payload = json.loads(text, object_pairs_hook=_reject_duplicate_members)
    except json.JSONDecodeError as error:
        raise ValueError(f"surface disposition contract is invalid JSON: {error.msg}") from error
    return parse_surface_disposition_contract(payload)


def serialize_surface_disposition_contract(
    contract: SurfaceDispositionContract,
) -> dict[str, object]:
    return {
        "added_count": contract.added_count,
        "archived_count": contract.archived_count,
        "changed_count": contract.changed_count,
        "disposition_counts": dict(contract.disposition_counts),
        "entries": [
            {
                "archived_sha256": entry.archived_sha256,
                "change_kind": entry.change_kind,
                "disposition": entry.disposition,
                "id": entry.id,
                "new_sha256": entry.new_sha256,
                "old_sha256": entry.old_sha256,
                "rationale": entry.rationale,
            }
            for entry in contract.entries
        ],
        "entry_count": contract.entry_count,
        "from_json_version": contract.from_json_version,
        "from_revision": contract.from_revision,
        "from_version": contract.from_version,
        "new_member_count": contract.new_member_count,
        "new_wheel_sha256": contract.new_wheel_sha256,
        "old_member_count": contract.old_member_count,
        "old_wheel_sha256": contract.old_wheel_sha256,
        "removed_count": contract.removed_count,
        "schema_version": contract.schema_version,
        "source_report_sha256": contract.source_report_sha256,
        "supported_package_profile_count": contract.supported_package_profile_count,
        "supported_package_source_count": contract.supported_package_source_count,
        "to_json_version": contract.to_json_version,
        "to_revision": contract.to_revision,
        "to_version": contract.to_version,
        "unchanged_count": contract.unchanged_count,
        "union_count": contract.union_count,
    }


def load_surface_disposition_contract(
    path: Path = DEFAULT_CONTRACT_PATH,
) -> SurfaceDispositionContract:
    return parse_surface_disposition_contract_text(path.read_text(encoding="utf-8"))
