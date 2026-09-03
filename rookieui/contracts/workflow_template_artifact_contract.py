from __future__ import annotations

import hashlib
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


DEFAULT_MAX_ARTIFACT_BYTES = 128 * 1024 * 1024
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


@dataclass(frozen=True)
class ArtifactSpec:
    filename: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class VerifiedArtifact:
    filename: str
    bytes: int
    sha256: str


def _validate_spec(spec: ArtifactSpec) -> None:
    normalized = PurePosixPath(spec.filename)
    if (
        not spec.filename
        or "\\" in spec.filename
        or normalized.is_absolute()
        or len(normalized.parts) != 1
        or normalized.name != spec.filename
        or normalized.name in {".", ".."}
    ):
        raise ValueError("Artifact filename is unsafe or non-canonical.")
    if isinstance(spec.bytes, bool) or not isinstance(spec.bytes, int) or spec.bytes <= 0:
        raise ValueError("Artifact size must be a positive integer.")
    if not _SHA256_PATTERN.fullmatch(spec.sha256):
        raise ValueError("Artifact SHA-256 must be 64 lowercase hexadecimal characters.")


def _is_link_or_reparse(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError as exc:
        raise ValueError("Artifact path is missing.") from exc
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & _REPARSE_POINT
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_artifact(
    root: Path,
    spec: ArtifactSpec,
    *,
    max_bytes: int = DEFAULT_MAX_ARTIFACT_BYTES,
) -> VerifiedArtifact:
    _validate_spec(spec)
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError("Artifact resource limit must be a positive integer.")

    root_path = Path(root)
    if _is_link_or_reparse(root_path):
        raise ValueError("Artifact root must not be a link or reparse point.")
    resolved_root = root_path.resolve(strict=True)
    if not resolved_root.is_dir():
        raise ValueError("Artifact root must be a directory.")

    candidate = root_path / spec.filename
    # SECURITY: reject links and Windows reparse points before resolve(); resolving first
    # would hide the indirection and could make out-of-root bytes look authoritative.
    if _is_link_or_reparse(candidate):
        raise ValueError("Artifact must not be a link or reparse point.")
    resolved_candidate = candidate.resolve(strict=True)
    if not resolved_candidate.is_relative_to(resolved_root) or not resolved_candidate.is_file():
        raise ValueError("Artifact escaped its authoritative root.")

    actual_bytes = resolved_candidate.stat().st_size
    if actual_bytes > max_bytes:
        raise ValueError("Artifact exceeds the configured resource limit.")
    if actual_bytes != spec.bytes:
        raise ValueError("Artifact size mismatch.")
    actual_sha256 = _sha256_file(resolved_candidate)
    if actual_sha256 != spec.sha256:
        raise ValueError("Artifact SHA-256 mismatch.")
    return VerifiedArtifact(spec.filename, actual_bytes, actual_sha256)
