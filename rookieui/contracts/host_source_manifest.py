from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Callable, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = ROOT / "tests" / "fixtures" / "current_host_source_manifest.json"
DEFAULT_SOURCE_ROOTS: Mapping[str, Path] = MappingProxyType(
    {
        "core": ROOT / "reference" / "ComfyUI",
        "desktop": ROOT / "reference" / "desktop",
        "frontend": ROOT / "reference" / "ComfyUI_frontend",
        "workflow_templates": ROOT / "reference" / "workflow_templates_source",
    }
)

SCHEMA_VERSION = "current-host-source-manifest-v3"
MANIFEST_KIND = "candidate-host-source-freeze"

_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")

_TOP_LEVEL_FIELDS = {
    "artifacts",
    "captured_at",
    "comparisons",
    "manifest_kind",
    "schema_version",
    "serialization",
    "subjects",
}
_SUBJECT_NAMES = {"core", "desktop", "frontend", "workflow_templates"}
_ARTIFACT_FIELDS = {
    "byte_drift",
    "bytes",
    "evidence",
    "path",
    "semantic_drift",
    "sha256",
    "subject",
}
_COMPARISON_FIELDS = {
    "byte_drift",
    "from_revision",
    "owner",
    "semantic_drift",
    "source_drift",
    "subject",
    "to_revision",
}
_SERIALIZATION_FIELDS = {
    "array_order",
    "encoding",
    "newline_terminated",
    "sort_keys",
}

_EXPECTED_SUBJECTS: Mapping[str, Mapping[str, object]] = MappingProxyType(
    {
        "core": MappingProxyType(
            {
                "kind": "git-host",
                "revision": "c67885b14556cf3e4e061862925282d403d09862",
                "components": {
                    "embedded_docs": "0.5.10",
                    "frontend_package": "1.49.6",
                    "workflow_templates": "0.11.43",
                },
                "status": "candidate-frozen",
            }
        ),
        "desktop": MappingProxyType(
            {
                "kind": "git-host-control",
                "revision": "e2d964b7456cea8423c7b9d3371c612313c06baa",
                "version": "0.9.4",
                "status": "unchanged-control",
            }
        ),
        "frontend": MappingProxyType(
            {
                "kind": "git-host",
                "revision": "569e65b30fbfe96743c7996e201a32bcf029a310",
                "version": "1.52.1",
                "status": "candidate-frozen",
            }
        ),
        "workflow_templates": MappingProxyType(
            {
                "kind": "git-package-source",
                "revision": "f54739874c88e5a1154275c4597b3860e5a617b4",
                "tag": "v0.11.43",
                "components": {
                    "assets": "0.1.29",
                    "core": "0.3.314",
                    "json": "0.1.49",
                    "media_api": "0.3.84",
                    "media_image": "0.3.160",
                    "media_other": "0.3.229",
                    "media_video": "0.3.101",
                    "meta": "0.11.43",
                },
                "artifact_status": "artifact-verification-pending",
            }
        ),
    }
)

_EXPECTED_ARTIFACT_POLICIES: Mapping[tuple[str, str], tuple[str, str, str]] = MappingProxyType(
    {
        ("core", "app/user_manager.py"): ("unchanged", "none", "direct-byte-hash"),
        ("core", "comfy_extras/nodes_custom_sampler.py"): (
            "changed",
            "covered-signature-compatible-runtime-disposition-complete",
            "direct-byte-hash",
        ),
        ("core", "comfy_extras/nodes_model_advanced.py"): (
            "changed",
            "covered-signature-compatible-runtime-disposition-complete",
            "direct-byte-hash",
        ),
        ("core", "comfy_extras/nodes_model_patch.py"): (
            "changed",
            "covered-signature-compatible-runtime-disposition-complete",
            "direct-byte-hash",
        ),
        ("core", "comfy_extras/nodes_textgen.py"): (
            "changed",
            "covered-signature-compatible-runtime-disposition-complete",
            "direct-byte-hash",
        ),
        ("core", "nodes.py"): (
            "changed",
            "covered-signature-compatible-runtime-disposition-complete",
            "direct-byte-hash",
        ),
        ("core", "requirements.txt"): ("changed", "none", "version-manifest-hash"),
        ("core", "server.py"): ("unchanged", "none", "direct-byte-hash"),
        ("desktop", "package.json"): ("unchanged", "none", "version-manifest-hash"),
        ("frontend", "package.json"): ("changed", "none", "version-manifest-hash"),
        ("frontend", "src/components/common/ExtensionSlot.vue"): (
            "unchanged",
            "none",
            "direct-byte-hash",
        ),
        ("frontend", "src/schemas/apiSchema.ts"): (
            "unchanged",
            "none",
            "direct-byte-hash",
        ),
        ("frontend", "src/stores/executionStore.ts"): (
            "changed",
            "runtime-event-contract-aligned",
            "direct-byte-hash",
        ),
        ("frontend", "src/stores/workspace/sidebarTabStore.ts"): (
            "unchanged",
            "none",
            "direct-byte-hash",
        ),
        ("frontend", "src/types/extensionTypes.ts"): (
            "unchanged",
            "none",
            "direct-byte-hash",
        ),
        ("workflow_templates", "pyproject.toml"): (
            "changed",
            "none",
            "version-manifest-hash",
        ),
    }
)

_EXPECTED_COMPARISONS: Mapping[str, tuple[str, str, str, str, str, str]] = MappingProxyType(
    {
        "core": (
            "6f7cd7fceaaf60d2669b554936394a7412c6fde5",
            "c67885b14556cf3e4e061862925282d403d09862",
            "revision-and-component",
            "mixed",
            "graph-and-runtime-contract-compatible",
            "runtime-compatibility-alignment",
        ),
        "desktop": (
            "e2d964b7456cea8423c7b9d3371c612313c06baa",
            "e2d964b7456cea8423c7b9d3371c612313c06baa",
            "none",
            "unchanged",
            "none",
            "source-freeze",
        ),
        "frontend": (
            "2c2ae612769bef6a8a05f197a97c08a8e5c88e9d",
            "569e65b30fbfe96743c7996e201a32bcf029a310",
            "revision-and-version",
            "mixed",
            "sidebar-and-runtime-event-compatible",
            "frontend-compatibility-alignment",
        ),
        "workflow_templates": (
            "a832a091491ce5b6341f4e4ca548b7ab536b6acd",
            "f54739874c88e5a1154275c4597b3860e5a617b4",
            "revision-and-component",
            "changed",
            "semantic-review-pending",
            "workflow-template-alignment",
        ),
    }
)


@dataclass(frozen=True)
class SourceSubject:
    kind: str
    revision: str
    components: Mapping[str, str]
    status: str | None = None
    version: str | None = None
    tag: str | None = None
    artifact_status: str | None = None


@dataclass(frozen=True)
class SourceArtifact:
    subject: str
    path: str
    bytes: int
    sha256: str
    byte_drift: str
    semantic_drift: str
    evidence: str


@dataclass(frozen=True)
class SourceComparison:
    subject: str
    from_revision: str
    to_revision: str
    source_drift: str
    byte_drift: str
    semantic_drift: str
    owner: str


@dataclass(frozen=True)
class SerializationContract:
    encoding: str
    sort_keys: bool
    array_order: str
    newline_terminated: bool


@dataclass(frozen=True)
class HostSourceManifest:
    schema_version: str
    manifest_kind: str
    captured_at: str
    subjects: Mapping[str, SourceSubject]
    artifacts: tuple[SourceArtifact, ...]
    comparisons: tuple[SourceComparison, ...]
    serialization: SerializationContract


@dataclass(frozen=True)
class VerifiedSourceArtifact:
    subject: str
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class SourceVerificationReport:
    status: str
    artifacts: tuple[VerifiedSourceArtifact, ...]


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
    value: dict[str, object], expected: set[str], context: str
) -> None:
    actual = set(value)
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


def _require_revision(value: object, context: str) -> str:
    revision = _require_string(value, context)
    if not _REVISION_PATTERN.fullmatch(revision):
        raise ValueError(f"{context} revision must be 40 lowercase hexadecimal characters.")
    return revision


def _require_version(value: object, context: str) -> str:
    version = _require_string(value, context)
    if not _VERSION_PATTERN.fullmatch(version):
        raise ValueError(f"{context} version is invalid.")
    return version


def _require_exact_value(value: object, expected: object, context: str) -> None:
    if value != expected:
        raise ValueError(f"{context} must equal the frozen candidate value.")


def _parse_timestamp(value: object) -> str:
    captured_at = _require_string(value, "captured_at")
    try:
        parsed = datetime.fromisoformat(captured_at)
    except ValueError as exc:
        raise ValueError("captured_at must be an RFC 3339 timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("captured_at must include a timezone offset.")
    return captured_at


def _parse_subject(name: str, value: object) -> SourceSubject:
    payload = _require_mapping(value, f"subject {name}")
    expected_payload = _EXPECTED_SUBJECTS[name]
    expected_fields = set(expected_payload)
    _require_exact_fields(payload, expected_fields, f"subject {name}")

    kind = _require_string(payload["kind"], f"subject {name} kind")
    revision = _require_revision(payload["revision"], f"subject {name}")
    _require_exact_value(kind, expected_payload["kind"], f"subject {name} kind")
    _require_exact_value(revision, expected_payload["revision"], f"subject {name} revision")

    components: Mapping[str, str] = MappingProxyType({})
    if "components" in expected_payload:
        component_payload = _require_mapping(payload["components"], f"subject {name} components")
        expected_components = dict(expected_payload["components"])
        _require_exact_fields(
            component_payload,
            set(expected_components),
            f"subject {name} components",
        )
        parsed_components = {
            key: _require_version(component_payload[key], f"subject {name} component {key}")
            for key in sorted(component_payload)
        }
        _require_exact_value(
            parsed_components,
            expected_components,
            f"subject {name} components",
        )
        components = MappingProxyType(parsed_components)

    version = None
    if "version" in expected_payload:
        version = _require_version(payload["version"], f"subject {name}")
        _require_exact_value(version, expected_payload["version"], f"subject {name} version")

    status = None
    if "status" in expected_payload:
        status = _require_string(payload["status"], f"subject {name} status")
        _require_exact_value(status, expected_payload["status"], f"subject {name} status")

    tag = None
    if "tag" in expected_payload:
        tag = _require_string(payload["tag"], f"subject {name} tag")
        _require_exact_value(tag, expected_payload["tag"], f"subject {name} tag")

    artifact_status = None
    if "artifact_status" in expected_payload:
        artifact_status = _require_string(
            payload["artifact_status"], f"subject {name} artifact status"
        )
        _require_exact_value(
            artifact_status,
            expected_payload["artifact_status"],
            f"subject {name} artifact status",
        )

    return SourceSubject(
        kind=kind,
        revision=revision,
        components=components,
        status=status,
        version=version,
        tag=tag,
        artifact_status=artifact_status,
    )


def _validate_relative_path(value: object) -> str:
    candidate = _require_string(value, "artifact path")
    normalized = PurePosixPath(candidate)
    if (
        "\\" in candidate
        or candidate.startswith("/")
        or re.match(r"^[A-Za-z]:", candidate)
        or not normalized.parts
        or ".." in normalized.parts
        or normalized.as_posix() != candidate
    ):
        raise ValueError("artifact path is unsafe or non-canonical.")
    return candidate


def _parse_artifacts(value: object) -> tuple[SourceArtifact, ...]:
    if not isinstance(value, list):
        raise ValueError("artifacts must be an array.")
    artifacts: list[SourceArtifact] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(value):
        payload = _require_mapping(item, f"artifact {index}")
        _require_exact_fields(payload, _ARTIFACT_FIELDS, f"artifact {index}")
        subject = _require_string(payload["subject"], f"artifact {index} subject")
        path = _validate_relative_path(payload["path"])
        key = (subject, path)
        if key in seen:
            raise ValueError(f"artifact inventory contains duplicate key: {subject}/{path}")
        seen.add(key)
        if key not in _EXPECTED_ARTIFACT_POLICIES:
            raise ValueError(f"artifact inventory contains unknown key: {subject}/{path}")
        byte_count = payload["bytes"]
        if isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count <= 0:
            raise ValueError(f"artifact {subject}/{path} byte count must be positive.")
        sha256 = _require_string(payload["sha256"], f"artifact {subject}/{path} SHA-256")
        if not _SHA256_PATTERN.fullmatch(sha256):
            raise ValueError(f"artifact {subject}/{path} SHA-256 is invalid.")
        policy = (
            _require_string(payload["byte_drift"], f"artifact {subject}/{path} byte drift"),
            _require_string(
                payload["semantic_drift"],
                f"artifact {subject}/{path} semantic drift",
            ),
            _require_string(payload["evidence"], f"artifact {subject}/{path} evidence"),
        )
        expected_policy = _EXPECTED_ARTIFACT_POLICIES[key]
        if policy[0] != expected_policy[0]:
            raise ValueError(f"artifact {subject}/{path} byte drift policy is invalid.")
        if policy[1] != expected_policy[1]:
            raise ValueError(f"artifact {subject}/{path} semantic drift policy is invalid.")
        if policy[2] != expected_policy[2]:
            raise ValueError(f"artifact {subject}/{path} evidence policy is invalid.")
        artifacts.append(
            SourceArtifact(
                subject=subject,
                path=path,
                bytes=byte_count,
                sha256=sha256,
                byte_drift=policy[0],
                semantic_drift=policy[1],
                evidence=policy[2],
            )
        )

    expected_keys = tuple(sorted(_EXPECTED_ARTIFACT_POLICIES))
    actual_keys = tuple((artifact.subject, artifact.path) for artifact in artifacts)
    if actual_keys != expected_keys:
        raise ValueError("artifact inventory must contain the exact sorted fourteen-row set.")
    return tuple(artifacts)


def _parse_comparisons(value: object) -> tuple[SourceComparison, ...]:
    if not isinstance(value, list):
        raise ValueError("comparisons must be an array.")
    comparisons: list[SourceComparison] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        payload = _require_mapping(item, f"comparison {index}")
        _require_exact_fields(payload, _COMPARISON_FIELDS, f"comparison {index}")
        subject = _require_string(payload["subject"], f"comparison {index} subject")
        if subject in seen:
            raise ValueError(f"comparisons contain duplicate subject: {subject}")
        seen.add(subject)
        if subject not in _EXPECTED_COMPARISONS:
            raise ValueError(f"comparisons contain unknown subject: {subject}")
        values = (
            _require_revision(payload["from_revision"], f"comparison {subject} from"),
            _require_revision(payload["to_revision"], f"comparison {subject} to"),
            _require_string(payload["source_drift"], f"comparison {subject} source drift"),
            _require_string(payload["byte_drift"], f"comparison {subject} byte drift"),
            _require_string(
                payload["semantic_drift"], f"comparison {subject} semantic drift"
            ),
            _require_string(payload["owner"], f"comparison {subject} owner"),
        )
        if values != _EXPECTED_COMPARISONS[subject]:
            raise ValueError(f"comparison {subject} identity or drift policy is invalid.")
        comparisons.append(SourceComparison(subject, *values))
    if tuple(comparison.subject for comparison in comparisons) != tuple(
        sorted(_EXPECTED_COMPARISONS)
    ):
        raise ValueError("comparisons must contain the exact sorted subject set.")
    return tuple(comparisons)


def _parse_serialization(value: object) -> SerializationContract:
    payload = _require_mapping(value, "serialization")
    _require_exact_fields(payload, _SERIALIZATION_FIELDS, "serialization")
    expected = {
        "array_order": "subject-then-path",
        "encoding": "UTF-8",
        "newline_terminated": True,
        "sort_keys": True,
    }
    _require_exact_value(payload, expected, "serialization")
    return SerializationContract(
        encoding="UTF-8",
        sort_keys=True,
        array_order="subject-then-path",
        newline_terminated=True,
    )


def parse_manifest_text(text: str) -> HostSourceManifest:
    try:
        parsed = json.loads(text, object_pairs_hook=_reject_duplicate_members)
    except json.JSONDecodeError as exc:
        raise ValueError("Candidate host source manifest is not valid JSON.") from exc
    payload = _require_mapping(parsed, "manifest")
    _require_exact_fields(payload, _TOP_LEVEL_FIELDS, "manifest")
    _require_exact_value(payload["schema_version"], SCHEMA_VERSION, "schema_version")
    _require_exact_value(payload["manifest_kind"], MANIFEST_KIND, "manifest_kind")

    subject_payload = _require_mapping(payload["subjects"], "subjects")
    _require_exact_fields(subject_payload, _SUBJECT_NAMES, "subjects")
    subjects = MappingProxyType(
        {name: _parse_subject(name, subject_payload[name]) for name in sorted(subject_payload)}
    )
    return HostSourceManifest(
        schema_version=SCHEMA_VERSION,
        manifest_kind=MANIFEST_KIND,
        captured_at=_parse_timestamp(payload["captured_at"]),
        subjects=subjects,
        artifacts=_parse_artifacts(payload["artifacts"]),
        comparisons=_parse_comparisons(payload["comparisons"]),
        serialization=_parse_serialization(payload["serialization"]),
    )


def load_manifest(path: Path = DEFAULT_MANIFEST_PATH) -> HostSourceManifest:
    return parse_manifest_text(path.read_text(encoding="utf-8"))


def _manifest_payload(manifest: HostSourceManifest) -> dict[str, object]:
    subjects: dict[str, object] = {}
    for name, subject in sorted(manifest.subjects.items()):
        value: dict[str, object] = {
            "kind": subject.kind,
            "revision": subject.revision,
        }
        if subject.artifact_status is not None:
            value["artifact_status"] = subject.artifact_status
        if subject.components:
            value["components"] = dict(subject.components)
        if subject.status is not None:
            value["status"] = subject.status
        if subject.tag is not None:
            value["tag"] = subject.tag
        if subject.version is not None:
            value["version"] = subject.version
        subjects[name] = value
    return {
        "artifacts": [
            {
                "byte_drift": artifact.byte_drift,
                "bytes": artifact.bytes,
                "evidence": artifact.evidence,
                "path": artifact.path,
                "semantic_drift": artifact.semantic_drift,
                "sha256": artifact.sha256,
                "subject": artifact.subject,
            }
            for artifact in sorted(manifest.artifacts, key=lambda item: (item.subject, item.path))
        ],
        "captured_at": manifest.captured_at,
        "comparisons": [
            {
                "byte_drift": comparison.byte_drift,
                "from_revision": comparison.from_revision,
                "owner": comparison.owner,
                "semantic_drift": comparison.semantic_drift,
                "source_drift": comparison.source_drift,
                "subject": comparison.subject,
                "to_revision": comparison.to_revision,
            }
            for comparison in sorted(manifest.comparisons, key=lambda item: item.subject)
        ],
        "manifest_kind": manifest.manifest_kind,
        "schema_version": manifest.schema_version,
        "serialization": {
            "array_order": manifest.serialization.array_order,
            "encoding": manifest.serialization.encoding,
            "newline_terminated": manifest.serialization.newline_terminated,
            "sort_keys": manifest.serialization.sort_keys,
        },
        "subjects": subjects,
    }


def serialize_manifest(manifest: HostSourceManifest) -> str:
    # Re-parse to ensure manually constructed objects cannot bypass the frozen schema.
    rendered = json.dumps(
        _manifest_payload(manifest),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    canonical = f"{rendered}\n"
    parse_manifest_text(canonical)
    return canonical


def _read_git_revision(source_root: Path, revision_expression: str = "HEAD") -> str:
    completed = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", revision_expression],
        check=False,
        capture_output=True,
        text=True,
    )
    revision = completed.stdout.strip().lower()
    if completed.returncode != 0 or not _REVISION_PATTERN.fullmatch(revision):
        raise ValueError("Authoritative reference revision is unavailable or invalid.")
    return revision


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_source_artifacts(
    manifest: HostSourceManifest,
    *,
    source_roots: Mapping[str, Path] | None = None,
    revision_reader: Callable[[Path], str] | None = None,
) -> SourceVerificationReport:
    resolved_roots = dict(DEFAULT_SOURCE_ROOTS if source_roots is None else source_roots)
    if set(resolved_roots) != _SUBJECT_NAMES:
        raise ValueError("Authoritative reference source roots are incomplete or unexpected.")

    if source_roots is None:
        existing_roots = [Path(root).is_dir() for root in resolved_roots.values()]
        if any(existing_roots) and not all(existing_roots):
            raise ValueError("Authoritative reference source roots are only partially available.")
        if not any(existing_roots):
            return SourceVerificationReport("unavailable-fixture-only", ())

    canonical_roots: dict[str, Path] = {}
    for name in sorted(_SUBJECT_NAMES):
        source_root = Path(resolved_roots[name])
        if not source_root.is_dir():
            raise ValueError(f"Authoritative {name} reference source is missing.")
        canonical_root = source_root.resolve()
        canonical_roots[name] = canonical_root
        if revision_reader is not None:
            actual_revision = revision_reader(source_root)
        else:
            revision_expression = "v0.11.43^{commit}" if name == "workflow_templates" else "HEAD"
            actual_revision = _read_git_revision(source_root, revision_expression)
        if actual_revision != manifest.subjects[name].revision:
            raise ValueError(f"Authoritative {name} reference revision mismatched.")

    verified: list[VerifiedSourceArtifact] = []
    for artifact in manifest.artifacts:
        source_root = canonical_roots[artifact.subject]
        artifact_path = source_root.joinpath(*PurePosixPath(artifact.path).parts)
        try:
            resolved_artifact = artifact_path.resolve(strict=True)
        except FileNotFoundError as exc:
            raise ValueError(
                f"Authoritative {artifact.subject} source artifact is missing."
            ) from exc
        if not resolved_artifact.is_relative_to(source_root) or not resolved_artifact.is_file():
            raise ValueError(
                f"Authoritative {artifact.subject} source artifact escaped its root."
            )
        actual_bytes = resolved_artifact.stat().st_size
        actual_sha256 = _sha256_file(resolved_artifact)
        if actual_bytes != artifact.bytes or actual_sha256 != artifact.sha256:
            raise ValueError(
                f"Authoritative {artifact.subject} source artifact byte/hash mismatch."
            )
        verified.append(
            VerifiedSourceArtifact(
                subject=artifact.subject,
                path=artifact.path,
                bytes=actual_bytes,
                sha256=actual_sha256,
            )
        )
    return SourceVerificationReport("verified", tuple(verified))
