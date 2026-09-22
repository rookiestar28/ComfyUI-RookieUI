"""Pinned, read-only source evidence for the ComfyUI Frontend 1.55 candidate.

The accepted host source basis remains separate until integrated qualification.
Reference checkout bytes are read as Git objects; no reference code is executed.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "frontend_155_candidate_contract.json"
DEFAULT_SOURCE_ROOT = ROOT / "reference" / "ComfyUI_frontend"
ACCEPTED_REVISION = "8f3b1569e4241ebbb5a9333da2bd09465947c40c"
CANDIDATE_REVISION = "07c337679d250b5a7af810adb73e26449fc6e676"
CANDIDATE_VERSION = "1.55.12"
SCHEMA_VERSION = "frontend-155-candidate-v1"
FIXTURE_SHA256 = "af9310e194c119fba0e46634ccc6281068c8e41076d8a1fb77d024c30d054e9e"

SOURCE_PATHS = (
    "src/components/sidebar/SideToolbar.vue",
    "src/platform/remote/comfyui/execution/types.ts",
    "src/platform/remote/comfyui/types.ts",
    "src/scripts/api.ts",
)


@dataclass(frozen=True)
class SourceArtifact:
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class FrontendCandidateContract:
    accepted_revision: str
    candidate_revision: str
    candidate_version: str
    schema_version: str
    artifacts: tuple[SourceArtifact, ...]


@dataclass(frozen=True)
class VerificationReport:
    status: str
    verified_artifacts: int


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"duplicate frontend source field: {key}")
        payload[key] = value
    return payload


def parse_contract_text(text: str) -> FrontendCandidateContract:
    try:
        payload = json.loads(text, object_pairs_hook=_unique_pairs)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError("invalid frontend source contract") from error
    if not isinstance(payload, dict) or payload.keys() != {
        "accepted_revision", "candidate_revision", "candidate_version", "schema_version", "artifacts"
    }:
        raise ValueError("unexpected frontend source fields")
    expected = {
        "accepted_revision": ACCEPTED_REVISION,
        "candidate_revision": CANDIDATE_REVISION,
        "candidate_version": CANDIDATE_VERSION,
        "schema_version": SCHEMA_VERSION,
    }
    for key, value in expected.items():
        if payload[key] != value:
            raise ValueError(f"unexpected frontend source {key}")
    rows = payload["artifacts"]
    if not isinstance(rows, list) or len(rows) != len(SOURCE_PATHS):
        raise ValueError("incomplete frontend source inventory")
    artifacts = []
    for path, row in zip(SOURCE_PATHS, rows):
        if not isinstance(row, dict) or row.keys() != {"path", "bytes", "sha256"}:
            raise ValueError("invalid frontend source row")
        if row["path"] != path or type(row["bytes"]) is not int or row["bytes"] <= 0:
            raise ValueError("unexpected frontend source path or length")
        digest = row["sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid frontend source digest")
        artifacts.append(SourceArtifact(**row))

    # CRITICAL: path names alone cannot prove candidate source identity; reject any rewritten freeze.
    canonical = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != FIXTURE_SHA256:
        raise ValueError("frontend source freeze fingerprint changed")
    return FrontendCandidateContract(
        accepted_revision=ACCEPTED_REVISION,
        candidate_revision=CANDIDATE_REVISION,
        candidate_version=CANDIDATE_VERSION,
        schema_version=SCHEMA_VERSION,
        artifacts=tuple(artifacts),
    )


def serialize_contract(contract: FrontendCandidateContract) -> str:
    payload = {
        "accepted_revision": contract.accepted_revision,
        "candidate_revision": contract.candidate_revision,
        "candidate_version": contract.candidate_version,
        "schema_version": contract.schema_version,
        "artifacts": [vars(item) for item in contract.artifacts],
    }
    return json.dumps(payload, sort_keys=True, indent=2) + "\n"


def load_contract(path: Path = DEFAULT_FIXTURE) -> FrontendCandidateContract:
    return parse_contract_text(path.read_text(encoding="utf-8"))


def _read_git_blob(path: str, source_root: Path) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(source_root), "show", f"{CANDIDATE_REVISION}:{path}"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"candidate frontend source missing: {path}")
    return result.stdout


def verify_contract_sources(
    contract: FrontendCandidateContract,
    *,
    source_root: Path = DEFAULT_SOURCE_ROOT,
    blob_reader: Callable[[str], bytes] | None = None,
) -> VerificationReport:
    if blob_reader is None and not source_root.is_dir():
        return VerificationReport("unavailable-fixture-only", 0)
    read = blob_reader or (lambda path: _read_git_blob(path, source_root))
    for item in contract.artifacts:
        try:
            raw = read(item.path)
        except (KeyError, OSError) as error:
            raise ValueError(f"candidate frontend source missing: {item.path}") from error
        if not isinstance(raw, bytes) or len(raw) != item.bytes or hashlib.sha256(raw).hexdigest() != item.sha256:
            raise ValueError(f"candidate frontend source drift: {item.path}")
    return VerificationReport("verified", len(contract.artifacts))
