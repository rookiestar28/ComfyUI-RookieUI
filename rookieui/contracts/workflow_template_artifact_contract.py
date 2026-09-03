from __future__ import annotations

import hashlib
import os
import re
import stat
import tarfile
import zipfile
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


@dataclass(frozen=True)
class WheelMember:
    name: str
    bytes: int
    compressed_bytes: int
    sha256: str | None
    is_directory: bool


@dataclass(frozen=True)
class WheelInventory:
    artifact: VerifiedArtifact
    member_count: int
    file_count: int
    total_uncompressed_bytes: int
    members: tuple[WheelMember, ...]


@dataclass(frozen=True)
class SdistInventory:
    artifact: VerifiedArtifact
    member_count: int
    file_count: int
    total_uncompressed_bytes: int
    members: tuple[WheelMember, ...]


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


def _validated_member_name(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (
        not name
        or "\x00" in name
        or "\\" in name
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or (path.parts and ":" in path.parts[0])
    ):
        raise ValueError(f"Wheel contains an unsafe member name: {name!r}.")
    return path


def inspect_wheel(
    root: Path,
    spec: ArtifactSpec,
    *,
    max_artifact_bytes: int = DEFAULT_MAX_ARTIFACT_BYTES,
    max_members: int = 10_000,
    max_index_bytes: int = 4 * 1024 * 1024,
    max_member_uncompressed_bytes: int = 64 * 1024 * 1024,
    max_total_uncompressed_bytes: int = 256 * 1024 * 1024,
) -> WheelInventory:
    """Inspect a verified wheel as inert bytes without extracting or importing it."""
    limits = {
        "member limit": max_members,
        "index limit": max_index_bytes,
        "member uncompressed limit": max_member_uncompressed_bytes,
        "total uncompressed limit": max_total_uncompressed_bytes,
    }
    for label, value in limits.items():
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"Wheel {label} must be a positive integer.")

    artifact = verify_artifact(root, spec, max_bytes=max_artifact_bytes)
    path = Path(root) / spec.filename
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError("Artifact is not a valid wheel ZIP archive.") from exc

    with archive:
        infos = archive.infolist()
        if len(infos) > max_members:
            raise ValueError("Wheel exceeds the configured member limit.")
        approximate_index_bytes = sum(46 + len(info.filename.encode("utf-8")) for info in infos)
        if approximate_index_bytes > max_index_bytes:
            raise ValueError("Wheel exceeds the configured index limit.")

        seen: dict[str, str] = {}
        regular_files: set[str] = set()
        total_uncompressed = 0
        members: list[WheelMember] = []
        for info in infos:
            member_path = _validated_member_name(info.filename)
            normalized = member_path.as_posix()
            if info.is_dir():
                normalized += "/"
            folded = normalized.rstrip("/").casefold()
            if folded in seen:
                raise ValueError(
                    f"Wheel contains a duplicate or case-insensitive collision: "
                    f"{seen[folded]!r} and {normalized!r}."
                )
            seen[folded] = normalized
            if info.flag_bits & 0x1:
                raise ValueError("Wheel contains an encrypted member.")
            if info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
                raise ValueError("Wheel contains an unsupported compression method.")
            mode = info.external_attr >> 16
            file_type = stat.S_IFMT(mode)
            is_directory = info.is_dir()
            if file_type == stat.S_IFLNK:
                raise ValueError("Wheel member must not be a link.")
            if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
                raise ValueError("Wheel member must be a regular file or directory.")
            if is_directory and file_type == stat.S_IFREG:
                raise ValueError("Wheel directory member has a regular-file mode.")
            if not is_directory and file_type == stat.S_IFDIR:
                raise ValueError("Wheel file member has a directory mode.")
            if info.file_size > max_member_uncompressed_bytes:
                raise ValueError("Wheel member exceeds the configured uncompressed limit.")
            total_uncompressed += info.file_size
            if total_uncompressed > max_total_uncompressed_bytes:
                raise ValueError("Wheel exceeds the configured total uncompressed limit.")
            for depth in range(1, len(member_path.parts)):
                parent = PurePosixPath(*member_path.parts[:depth]).as_posix().casefold()
                if parent in regular_files:
                    raise ValueError("Wheel regular-file member is an ancestor of another member.")

            digest: str | None = None
            if not is_directory:
                # SECURITY: keep upstream archives inert; read bounded bytes in-memory and never extract.
                payload = archive.read(info)
                if len(payload) != info.file_size:
                    raise ValueError("Wheel member size changed while reading.")
                digest = hashlib.sha256(payload).hexdigest()
                regular_files.add(folded)
            members.append(
                WheelMember(
                    name=normalized,
                    bytes=info.file_size,
                    compressed_bytes=info.compress_size,
                    sha256=digest,
                    is_directory=is_directory,
                )
            )

        for regular_file in regular_files:
            parts = PurePosixPath(regular_file).parts
            if any(
                PurePosixPath(*parts[:depth]).as_posix().casefold() in regular_files
                for depth in range(1, len(parts))
            ):
                raise ValueError("Wheel regular-file member is an ancestor of another member.")

    ordered = tuple(sorted(members, key=lambda item: item.name))
    return WheelInventory(
        artifact=artifact,
        member_count=len(ordered),
        file_count=sum(not member.is_directory for member in ordered),
        total_uncompressed_bytes=total_uncompressed,
        members=ordered,
    )


def inspect_sdist(
    root: Path,
    spec: ArtifactSpec,
    *,
    max_artifact_bytes: int = DEFAULT_MAX_ARTIFACT_BYTES,
    max_members: int = 10_000,
    max_index_bytes: int = 4 * 1024 * 1024,
    max_member_uncompressed_bytes: int = 64 * 1024 * 1024,
    max_total_uncompressed_bytes: int = 256 * 1024 * 1024,
) -> SdistInventory:
    """Inspect a verified source archive as inert bytes without extracting it."""
    limits = {
        "member limit": max_members,
        "index limit": max_index_bytes,
        "member uncompressed limit": max_member_uncompressed_bytes,
        "total uncompressed limit": max_total_uncompressed_bytes,
    }
    for label, value in limits.items():
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"Source archive {label} must be a positive integer.")

    artifact = verify_artifact(root, spec, max_bytes=max_artifact_bytes)
    path = Path(root) / spec.filename
    try:
        archive = tarfile.open(path, mode="r:gz")
    except (OSError, tarfile.TarError) as exc:
        raise ValueError("Artifact is not a valid gzip source archive.") from exc

    with archive:
        infos = archive.getmembers()
        if len(infos) > max_members:
            raise ValueError("Source archive exceeds the configured member limit.")
        if sum(512 + len(info.name.encode("utf-8")) for info in infos) > max_index_bytes:
            raise ValueError("Source archive exceeds the configured index limit.")
        seen: dict[str, str] = {}
        regular_files: set[str] = set()
        total_uncompressed = 0
        members: list[WheelMember] = []
        for info in infos:
            member_path = _validated_member_name(info.name)
            normalized = member_path.as_posix()
            if info.isdir():
                normalized += "/"
            folded = normalized.rstrip("/").casefold()
            if folded in seen:
                raise ValueError(
                    "Source archive contains a duplicate or case-insensitive collision: "
                    f"{seen[folded]!r} and {normalized!r}."
                )
            seen[folded] = normalized
            if info.issym() or info.islnk():
                raise ValueError("Source archive member must not be a link.")
            if not (info.isfile() or info.isdir()):
                raise ValueError("Source archive member must be a regular file or directory.")
            if info.size > max_member_uncompressed_bytes:
                raise ValueError("Source archive member exceeds the uncompressed limit.")
            total_uncompressed += info.size
            if total_uncompressed > max_total_uncompressed_bytes:
                raise ValueError("Source archive exceeds the total uncompressed limit.")
            for depth in range(1, len(member_path.parts)):
                parent = PurePosixPath(*member_path.parts[:depth]).as_posix().casefold()
                if parent in regular_files:
                    raise ValueError(
                        "Source archive regular-file member is an ancestor of another member."
                    )
            digest: str | None = None
            if info.isfile():
                # SECURITY: source archives remain inert and are never extracted or imported.
                stream = archive.extractfile(info)
                if stream is None:
                    raise ValueError("Source archive regular file could not be read.")
                payload = stream.read(max_member_uncompressed_bytes + 1)
                if len(payload) != info.size:
                    raise ValueError("Source archive member size changed while reading.")
                digest = hashlib.sha256(payload).hexdigest()
                regular_files.add(folded)
            members.append(
                WheelMember(
                    name=normalized,
                    bytes=info.size,
                    compressed_bytes=0,
                    sha256=digest,
                    is_directory=info.isdir(),
                )
            )
        for regular_file in regular_files:
            parts = PurePosixPath(regular_file).parts
            if any(
                PurePosixPath(*parts[:depth]).as_posix().casefold() in regular_files
                for depth in range(1, len(parts))
            ):
                raise ValueError(
                    "Source archive regular-file member is an ancestor of another member."
                )
    ordered = tuple(sorted(members, key=lambda item: item.name))
    return SdistInventory(
        artifact=artifact,
        member_count=len(ordered),
        file_count=sum(not member.is_directory for member in ordered),
        total_uncompressed_bytes=total_uncompressed,
        members=ordered,
    )
