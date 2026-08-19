from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT_PATH = ROOT / "tests" / "fixtures" / "current_host_core_runtime_contract.json"
DEFAULT_SOURCE_ROOT = ROOT / "reference" / "ComfyUI"

SCHEMA_VERSION = "current-host-core-runtime-contract-v1"
CONTRACT_KIND = "candidate-core-runtime-semantics"
BASELINE_REVISION = "6f7cd7fceaaf60d2669b554936394a7412c6fde5"
SOURCE_REVISION = "c67885b14556cf3e4e061862925282d403d09862"

REQUIRED_CASE_IDS = (
    "core_source_basis",
    "disabled_empty_noise_and_latent_normalization",
    "img2img_inpaint_mask_latent_geometry",
    "controlnet_lifecycle_weights_masks",
    "sampler_vae_supported_graphs",
    "tokenizer_text_encoding_adapters",
    "changed_graph_source_dispositions",
)

REQUIRED_SOURCE_PATHS = (
    "comfy/controlnet.py",
    "comfy/latent_formats.py",
    "comfy/sample.py",
    "comfy/samplers.py",
    "comfy/sd.py",
    "comfy/text_encoders/bpe_tokenizer.py",
    "comfy/text_encoders/flux.py",
    "comfy/text_encoders/llama.py",
    "comfy/text_encoders/lumina2.py",
    "comfy_extras/nodes_custom_sampler.py",
    "comfy_extras/nodes_model_advanced.py",
    "comfy_extras/nodes_model_patch.py",
    "comfy_extras/nodes_textgen.py",
    "nodes.py",
)

REQUIRED_FORBIDDEN_SIDE_EFFECTS = (
    "reference-execution",
    "prompt-or-provider-payload-logging",
    "private-path-or-locator-disclosure",
    "silent-unsupported-substitution",
    "persistent-runtime-state-mutation",
)

_SOURCE_DISPOSITIONS = {
    "executable-runtime-risk",
    "covered-workflow-contract",
    "covered-runtime-unaffected",
    "not-emitted-upstream-only",
}

_EXPECTED_SOURCE_POLICIES: Mapping[str, tuple[str, tuple[str, ...]]] = MappingProxyType(
    {
        "comfy/controlnet.py": (
            "executable-runtime-risk",
            ("controlnet_lifecycle_weights_masks",),
        ),
        "comfy/latent_formats.py": (
            "executable-runtime-risk",
            ("disabled_empty_noise_and_latent_normalization",),
        ),
        "comfy/sample.py": (
            "executable-runtime-risk",
            (
                "disabled_empty_noise_and_latent_normalization",
                "sampler_vae_supported_graphs",
            ),
        ),
        "comfy/samplers.py": (
            "covered-workflow-contract",
            ("sampler_vae_supported_graphs",),
        ),
        "comfy/sd.py": (
            "covered-workflow-contract",
            ("sampler_vae_supported_graphs",),
        ),
        "comfy/text_encoders/bpe_tokenizer.py": (
            "executable-runtime-risk",
            ("tokenizer_text_encoding_adapters",),
        ),
        "comfy/text_encoders/flux.py": (
            "executable-runtime-risk",
            ("tokenizer_text_encoding_adapters",),
        ),
        "comfy/text_encoders/llama.py": (
            "executable-runtime-risk",
            ("tokenizer_text_encoding_adapters",),
        ),
        "comfy/text_encoders/lumina2.py": (
            "executable-runtime-risk",
            ("tokenizer_text_encoding_adapters",),
        ),
        "comfy_extras/nodes_custom_sampler.py": (
            "not-emitted-upstream-only",
            (
                "disabled_empty_noise_and_latent_normalization",
                "changed_graph_source_dispositions",
            ),
        ),
        "comfy_extras/nodes_model_advanced.py": (
            "covered-runtime-unaffected",
            (
                "changed_graph_source_dispositions",
                "sampler_vae_supported_graphs",
            ),
        ),
        "comfy_extras/nodes_model_patch.py": (
            "covered-workflow-contract",
            (
                "changed_graph_source_dispositions",
                "sampler_vae_supported_graphs",
            ),
        ),
        "comfy_extras/nodes_textgen.py": (
            "covered-runtime-unaffected",
            (
                "changed_graph_source_dispositions",
                "tokenizer_text_encoding_adapters",
            ),
        ),
        "nodes.py": (
            "executable-runtime-risk",
            (
                "disabled_empty_noise_and_latent_normalization",
                "sampler_vae_supported_graphs",
                "changed_graph_source_dispositions",
            ),
        ),
    }
)

_EXPECTED_CASES: Mapping[str, tuple[str, str, str]] = MappingProxyType(
    {
        "core_source_basis": (
            "pinned-source",
            "tests.test_current_host_runtime_semantics.CurrentHostCoreRuntimeContractTests.test_contract_source_rows_are_verified_from_pinned_git_objects",
            "Every runtime-risk row resolves to the frozen baseline and candidate Git blobs without importing or executing reference code.",
        ),
        "disabled_empty_noise_and_latent_normalization": (
            "noise-latent",
            "tests.test_current_host_runtime_semantics.CurrentHostCoreRuntimeBehaviorTests.test_stock_sampler_preserves_seed_denoise_scheduler_and_latent_link",
            "RookieUI preserves the stock KSampler latent seam and does not emit the changed custom disabled-noise path; Core retains empty-noise and latent-format normalization ownership.",
        ),
        "img2img_inpaint_mask_latent_geometry": (
            "img2img-inpaint",
            "tests.test_current_host_runtime_semantics.CurrentHostCoreRuntimeBehaviorTests.test_inpaint_runtime_preserves_cropped_mask_and_latent_geometry",
            "The RookieUI inpaint encoder preserves cropped mask geometry, latent dimensions, and deterministic seeded latent-noise behavior.",
        ),
        "controlnet_lifecycle_weights_masks": (
            "controlnet",
            "tests.test_current_host_runtime_semantics.CurrentHostCoreRuntimeBehaviorTests.test_controlnet_mask_protocol_executes_broadcast_effect_and_concat_geometry",
            "Current-host lifecycle doubles preserve clone ownership, previous-control restoration, weights, guidance segments, and effect/concat mask behavior.",
        ),
        "sampler_vae_supported_graphs": (
            "sampler-vae",
            "tests.test_family_profile_projection.FamilyProfileProjectionTests.test_all_shipped_profile_builders_match_candidate_graph_contract",
            "Every shipped profile preserves its content-free encode, latent, sampler, VAE, and decode topology against the frozen Core graph contract.",
        ),
        "tokenizer_text_encoding_adapters": (
            "tokenizer-text-encoding",
            "tests.test_current_host_runtime_semantics.CurrentHostCoreRuntimeBehaviorTests.test_tokenizer_capability_mismatch_uses_stock_tokens_without_prompt_logging",
            "RookieUI text adapters preserve weighted and stock-token paths, fail safely on optional word-ID capability mismatch, and do not execute upstream tokenizers in the contract lane.",
        ),
        "changed_graph_source_dispositions": (
            "changed-graph-sources",
            "tests.test_current_host_graph_contract.CurrentHostGraphContractTests.test_candidate_core_graph_separates_byte_and_covered_signature_drift",
            "All five changed graph-source artifacts retain covered signatures and receive an explicit runtime disposition without inferring incompatibility from byte drift.",
        ),
    }
)

_TOP_LEVEL_FIELDS = {
    "baseline_revision",
    "cases",
    "contract_kind",
    "schema_version",
    "serialization",
    "source_revision",
    "sources",
}
_SOURCE_FIELDS = {
    "baseline_blob",
    "baseline_sha256",
    "case_ids",
    "disposition",
    "path",
    "source_blob",
    "source_sha256",
}
_CASE_FIELDS = {
    "case_id",
    "evidence",
    "expected",
    "forbidden_side_effects",
    "surface",
}
_SERIALIZATION_FIELDS = {
    "array_order",
    "encoding",
    "newline_terminated",
    "sort_keys",
}
_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class RuntimeSource:
    path: str
    baseline_blob: str | None
    baseline_sha256: str | None
    source_blob: str
    source_sha256: str
    disposition: str
    case_ids: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeCase:
    case_id: str
    surface: str
    evidence: str
    expected: str
    forbidden_side_effects: tuple[str, ...]


@dataclass(frozen=True)
class SerializationContract:
    encoding: str
    sort_keys: bool
    array_order: str
    newline_terminated: bool


@dataclass(frozen=True)
class CoreRuntimeContract:
    schema_version: str
    contract_kind: str
    baseline_revision: str
    source_revision: str
    sources: tuple[RuntimeSource, ...]
    cases: tuple[RuntimeCase, ...]
    serialization: SerializationContract


@dataclass(frozen=True)
class VerifiedRuntimeSource:
    path: str
    baseline_verified: bool
    candidate_verified: bool


@dataclass(frozen=True)
class RuntimeSourceVerificationReport:
    status: str
    sources: tuple[VerifiedRuntimeSource, ...]


def _reject_duplicate_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"JSON object contains duplicate member: {key}")
        payload[key] = value
    return payload


def _mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object.")
    return value


def _exact_fields(payload: dict[str, object], expected: set[str], context: str) -> None:
    unknown = sorted(set(payload) - expected)
    missing = sorted(expected - set(payload))
    if unknown:
        raise ValueError(f"{context} contains unknown fields: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{context} is missing fields: {', '.join(missing)}")


def _string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context} must be a non-empty string.")
    return value


def _revision(value: object, context: str) -> str:
    revision = _string(value, context)
    if not _REVISION_PATTERN.fullmatch(revision):
        raise ValueError(f"{context} must be a lowercase 40-character Git revision.")
    return revision


def _sha256(value: object, context: str) -> str:
    digest = _string(value, context)
    if not _SHA256_PATTERN.fullmatch(digest):
        raise ValueError(f"{context} must be a lowercase SHA-256 digest.")
    return digest


def _optional_object_id(value: object, context: str) -> str | None:
    if value is None:
        return None
    return _revision(value, context)


def _optional_sha256(value: object, context: str) -> str | None:
    if value is None:
        return None
    return _sha256(value, context)


def _relative_path(value: object, context: str) -> str:
    path = _string(value, context)
    normalized = PurePosixPath(path)
    if (
        not normalized.parts
        or path.startswith("/")
        or "\\" in path
        or re.match(r"^[A-Za-z]:", path)
        or ".." in normalized.parts
        or normalized.as_posix() != path
    ):
        raise ValueError(f"{context} must be a safe normalized repository-relative path.")
    return path


def _string_tuple(value: object, context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be an array.")
    values = tuple(_string(item, f"{context} item") for item in value)
    if len(set(values)) != len(values):
        raise ValueError(f"{context} contains duplicate values.")
    return values


def parse_core_runtime_contract_text(text: str) -> CoreRuntimeContract:
    try:
        raw = json.loads(text, object_pairs_hook=_reject_duplicate_members)
    except json.JSONDecodeError as exc:
        raise ValueError("Core runtime contract is not valid JSON.") from exc
    payload = _mapping(raw, "contract")
    _exact_fields(payload, _TOP_LEVEL_FIELDS, "contract")

    schema_version = _string(payload["schema_version"], "schema_version")
    contract_kind = _string(payload["contract_kind"], "contract_kind")
    baseline_revision = _revision(payload["baseline_revision"], "baseline_revision")
    source_revision = _revision(payload["source_revision"], "source_revision")
    if schema_version != SCHEMA_VERSION or contract_kind != CONTRACT_KIND:
        raise ValueError("Core runtime contract schema or kind is unsupported.")
    if baseline_revision != BASELINE_REVISION or source_revision != SOURCE_REVISION:
        raise ValueError("Core runtime contract source identity is not the frozen candidate pair.")

    raw_sources = payload["sources"]
    if not isinstance(raw_sources, list):
        raise ValueError("sources must be an array.")
    sources: list[RuntimeSource] = []
    for index, raw_source in enumerate(raw_sources):
        source = _mapping(raw_source, f"source[{index}]")
        _exact_fields(source, _SOURCE_FIELDS, f"source[{index}]")
        path = _relative_path(source["path"], f"source[{index}].path")
        baseline_blob = _optional_object_id(source["baseline_blob"], f"source[{index}].baseline_blob")
        baseline_sha256 = _optional_sha256(source["baseline_sha256"], f"source[{index}].baseline_sha256")
        if (baseline_blob is None) != (baseline_sha256 is None):
            raise ValueError(f"source[{index}] baseline blob and SHA-256 must both be present or null.")
        source_blob = _revision(source["source_blob"], f"source[{index}].source_blob")
        source_sha256 = _sha256(source["source_sha256"], f"source[{index}].source_sha256")
        disposition = _string(source["disposition"], f"source[{index}].disposition")
        case_ids = _string_tuple(source["case_ids"], f"source[{index}].case_ids")
        if disposition not in _SOURCE_DISPOSITIONS:
            raise ValueError(f"source[{index}] disposition is unsupported.")
        if (disposition, case_ids) != _EXPECTED_SOURCE_POLICIES.get(path):
            raise ValueError(f"source[{index}] policy is not the frozen runtime disposition.")
        sources.append(
            RuntimeSource(
                path=path,
                baseline_blob=baseline_blob,
                baseline_sha256=baseline_sha256,
                source_blob=source_blob,
                source_sha256=source_sha256,
                disposition=disposition,
                case_ids=case_ids,
            )
        )
    if tuple(source.path for source in sources) != REQUIRED_SOURCE_PATHS:
        raise ValueError("Core runtime source inventory is incomplete, duplicated, or out of order.")

    raw_cases = payload["cases"]
    if not isinstance(raw_cases, list):
        raise ValueError("cases must be an array.")
    cases: list[RuntimeCase] = []
    for index, raw_case in enumerate(raw_cases):
        case = _mapping(raw_case, f"case[{index}]")
        _exact_fields(case, _CASE_FIELDS, f"case[{index}]")
        case_id = _string(case["case_id"], f"case[{index}].case_id")
        surface = _string(case["surface"], f"case[{index}].surface")
        evidence = _string(case["evidence"], f"case[{index}].evidence")
        expected = _string(case["expected"], f"case[{index}].expected")
        forbidden = _string_tuple(case["forbidden_side_effects"], f"case[{index}].forbidden_side_effects")
        if (surface, evidence, expected) != _EXPECTED_CASES.get(case_id):
            raise ValueError(f"case[{index}] does not match the frozen executable evidence contract.")
        if forbidden != REQUIRED_FORBIDDEN_SIDE_EFFECTS:
            raise ValueError(f"case[{index}] forbidden side effects are incomplete or out of order.")
        cases.append(RuntimeCase(case_id, surface, evidence, expected, forbidden))
    if tuple(case.case_id for case in cases) != REQUIRED_CASE_IDS:
        raise ValueError("Core runtime cases are incomplete, duplicated, or out of order.")

    known_cases = set(REQUIRED_CASE_IDS)
    referenced_cases = {case_id for source in sources for case_id in source.case_ids}
    if referenced_cases != known_cases - {"core_source_basis", "img2img_inpaint_mask_latent_geometry"}:
        raise ValueError("Core source rows contain incomplete or unknown semantic case references.")

    serialization_payload = _mapping(payload["serialization"], "serialization")
    _exact_fields(serialization_payload, _SERIALIZATION_FIELDS, "serialization")
    serialization = SerializationContract(
        encoding=_string(serialization_payload["encoding"], "serialization.encoding"),
        sort_keys=serialization_payload["sort_keys"],
        array_order=_string(serialization_payload["array_order"], "serialization.array_order"),
        newline_terminated=serialization_payload["newline_terminated"],
    )
    if not isinstance(serialization.sort_keys, bool) or not isinstance(serialization.newline_terminated, bool):
        raise ValueError("serialization boolean fields must be booleans.")
    if serialization != SerializationContract("utf-8", True, "declaration", True):
        raise ValueError("Core runtime serialization policy is unsupported.")

    return CoreRuntimeContract(
        schema_version=schema_version,
        contract_kind=contract_kind,
        baseline_revision=baseline_revision,
        source_revision=source_revision,
        sources=tuple(sources),
        cases=tuple(cases),
        serialization=serialization,
    )


def _payload(contract: CoreRuntimeContract) -> dict[str, object]:
    return {
        "baseline_revision": contract.baseline_revision,
        "cases": [
            {
                "case_id": case.case_id,
                "evidence": case.evidence,
                "expected": case.expected,
                "forbidden_side_effects": list(case.forbidden_side_effects),
                "surface": case.surface,
            }
            for case in contract.cases
        ],
        "contract_kind": contract.contract_kind,
        "schema_version": contract.schema_version,
        "serialization": {
            "array_order": contract.serialization.array_order,
            "encoding": contract.serialization.encoding,
            "newline_terminated": contract.serialization.newline_terminated,
            "sort_keys": contract.serialization.sort_keys,
        },
        "source_revision": contract.source_revision,
        "sources": [
            {
                "baseline_blob": source.baseline_blob,
                "baseline_sha256": source.baseline_sha256,
                "case_ids": list(source.case_ids),
                "disposition": source.disposition,
                "path": source.path,
                "source_blob": source.source_blob,
                "source_sha256": source.source_sha256,
            }
            for source in contract.sources
        ],
    }


def serialize_core_runtime_contract(contract: CoreRuntimeContract) -> str:
    return json.dumps(_payload(contract), indent=2, sort_keys=True) + "\n"


def load_core_runtime_contract(path: Path = DEFAULT_CONTRACT_PATH) -> CoreRuntimeContract:
    return parse_core_runtime_contract_text(path.read_text(encoding="utf-8"))


def _git(source_root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(source_root), *args],
        check=False,
        capture_output=True,
        timeout=30,
    )


def _read_object(source_root: Path, revision: str, path: str) -> tuple[str | None, bytes | None]:
    resolved = _git(source_root, "rev-parse", f"{revision}:{path}")
    if resolved.returncode != 0:
        return None, None
    object_id = resolved.stdout.decode("ascii", errors="strict").strip()
    if not _REVISION_PATTERN.fullmatch(object_id):
        raise ValueError("Pinned Core source resolved to an invalid Git object ID.")
    blob = _git(source_root, "cat-file", "blob", object_id)
    if blob.returncode != 0:
        raise ValueError("Pinned Core source blob is unavailable.")
    return object_id, blob.stdout


def verify_core_runtime_sources(
    contract: CoreRuntimeContract,
    *,
    source_root: Path = DEFAULT_SOURCE_ROOT,
) -> RuntimeSourceVerificationReport:
    if not source_root.exists():
        return RuntimeSourceVerificationReport("unavailable-fixture-only", ())
    if not source_root.is_dir():
        raise ValueError("Core source root is not a directory.")

    for revision in (contract.baseline_revision, contract.source_revision):
        commit = _git(source_root, "cat-file", "-e", f"{revision}^{{commit}}")
        if commit.returncode != 0:
            raise ValueError("Pinned Core commit object is unavailable.")

    verified: list[VerifiedRuntimeSource] = []
    for source in contract.sources:
        baseline_id, baseline_bytes = _read_object(
            source_root,
            contract.baseline_revision,
            source.path,
        )
        if source.baseline_blob is None:
            baseline_verified = baseline_id is None and baseline_bytes is None
        else:
            baseline_verified = (
                baseline_id == source.baseline_blob
                and baseline_bytes is not None
                and hashlib.sha256(baseline_bytes).hexdigest() == source.baseline_sha256
            )
        candidate_id, candidate_bytes = _read_object(
            source_root,
            contract.source_revision,
            source.path,
        )
        candidate_verified = (
            candidate_id == source.source_blob
            and candidate_bytes is not None
            and hashlib.sha256(candidate_bytes).hexdigest() == source.source_sha256
        )
        if not baseline_verified or not candidate_verified:
            raise ValueError(f"Pinned Core source evidence mismatch: {source.path}")
        verified.append(VerifiedRuntimeSource(source.path, baseline_verified, candidate_verified))
    return RuntimeSourceVerificationReport("verified", tuple(verified))
