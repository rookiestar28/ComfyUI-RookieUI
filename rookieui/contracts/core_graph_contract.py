from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Mapping, TypeAlias


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORE_GRAPH_CONTRACT_PATH = (
    ROOT / "tests" / "fixtures" / "current_host_core_graph_contract.json"
)
DEFAULT_PROFILE_GRAPH_CONTRACT_PATH = (
    ROOT / "tests" / "fixtures" / "current_host_profile_graph_contract.json"
)

CORE_SCHEMA_VERSION = "current-host-core-graph-contract-v1"
PROFILE_SCHEMA_VERSION = "current-host-profile-graph-contract-v1"

JSONScalar: TypeAlias = str | int | float | bool | None

_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_OPTION_KINDS = {
    "not-applicable",
    "literal",
    "runtime-registry",
    "filesystem",
    "dynamic",
}
_DRIFT_VALUES = {"changed", "unchanged"}
_CORE_TOP_LEVEL_FIELDS = {
    "baseline_revision",
    "classes",
    "inventory",
    "schema_version",
    "source_files",
    "source_revision",
}
_INVENTORY_FIELDS = {
    "changed_class_count",
    "changed_source_file_count",
    "class_count",
    "classified_option_count",
    "input_count",
    "source_file_count",
}
_SOURCE_FILE_FIELDS = {
    "baseline_blob",
    "byte_drift",
    "classes",
    "covered_signature_drift",
    "source_blob",
    "source_sha256",
}
_CLASS_FIELDS = {
    "inputs",
    "signature_drift",
    "source_blob",
    "source_path",
    "source_revision",
    "source_sha256",
}
_INPUT_REQUIRED_FIELDS = {"optional", "option_source", "type"}
_INPUT_ALLOWED_FIELDS = _INPUT_REQUIRED_FIELDS | {"default"}
_PROFILE_TOP_LEVEL_FIELDS = {
    "profile_count",
    "profiles",
    "schema_version",
    "source_revision",
}
_PROFILE_FIELDS = {
    "class_types",
    "edge_count",
    "flow_kind",
    "id",
    "node_count",
    "topology_sha256",
}

DEFAULT_LOCAL_NODE_CLASSES = frozenset(
    {
        "RookieUIADetailerDetectMask",
        "RookieUIControlNetApplyNativeAdvanced",
        "RookieUIControlNetPreprocess",
        "RookieUILoadAssetImage",
        "RookieUILoadAssetMask",
        "RookieUISaveImageWithMetadata",
        "RookieUIVAEEncodeForInpaint",
    }
)


@dataclass(frozen=True)
class OptionSource:
    kind: str
    source: str | None = None
    values: tuple[JSONScalar, ...] = ()


@dataclass(frozen=True)
class CoreInputContract:
    optional: bool
    type: str
    option_source: OptionSource
    has_default: bool = False
    default: JSONScalar = None


@dataclass(frozen=True)
class CoreClassContract:
    source_revision: str
    source_path: str
    source_blob: str
    source_sha256: str
    signature_drift: str
    inputs: Mapping[str, CoreInputContract]


@dataclass(frozen=True)
class CoreSourceFileContract:
    baseline_blob: str
    source_blob: str
    source_sha256: str
    byte_drift: str
    covered_signature_drift: str
    classes: tuple[str, ...]


@dataclass(frozen=True)
class CoreGraphInventory:
    source_file_count: int
    class_count: int
    input_count: int
    changed_source_file_count: int
    changed_class_count: int
    classified_option_count: int


@dataclass(frozen=True)
class CoreGraphContract:
    schema_version: str
    baseline_revision: str
    source_revision: str
    inventory: CoreGraphInventory
    source_files: Mapping[str, CoreSourceFileContract]
    classes: Mapping[str, CoreClassContract]


@dataclass(frozen=True)
class ProfileGraphRow:
    id: str
    flow_kind: str
    node_count: int
    edge_count: int
    class_types: tuple[str, ...]
    topology_sha256: str


@dataclass(frozen=True)
class ProfileGraphContract:
    schema_version: str
    source_revision: str
    profile_count: int
    profiles: tuple[ProfileGraphRow, ...]


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


def _require_count(value: object, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{context} must be a non-negative integer.")
    return value


def _require_relative_path(value: object, context: str) -> str:
    path = _require_string(value, context)
    normalized = PurePosixPath(path)
    if (
        "\\" in path
        or path.startswith("/")
        or re.match(r"^[A-Za-z]:", path)
        or ".." in normalized.parts
        or normalized.as_posix() != path
    ):
        raise ValueError(f"{context} is unsafe or non-canonical.")
    return path


def _parse_option_source(value: object, context: str) -> OptionSource:
    payload = _require_mapping(value, context)
    kind = _require_string(payload.get("kind"), f"{context} kind")
    if kind not in _OPTION_KINDS:
        raise ValueError(f"{context} kind is invalid.")
    if kind == "not-applicable":
        _require_exact_fields(payload, {"kind"}, context)
        return OptionSource(kind=kind)
    if kind == "literal":
        _require_exact_fields(payload, {"kind", "values"}, context)
        raw_values = payload["values"]
        if not isinstance(raw_values, list) or not raw_values:
            raise ValueError(f"{context} literal values must be a non-empty array.")
        if any(not isinstance(item, (str, int, float, bool)) and item is not None for item in raw_values):
            raise ValueError(f"{context} literal values must contain JSON scalars.")
        return OptionSource(kind=kind, values=tuple(raw_values))
    _require_exact_fields(payload, {"kind", "source"}, context)
    source = _require_string(payload["source"], f"{context} source")
    if re.search(r"(?:^[A-Za-z]:|[/\\](?:Users|home)[/\\])", source):
        raise ValueError(f"{context} source must be public and locator-free.")
    return OptionSource(kind=kind, source=source)


def _parse_input(value: object, context: str) -> CoreInputContract:
    payload = _require_mapping(value, context)
    unknown = set(payload) - _INPUT_ALLOWED_FIELDS
    missing = _INPUT_REQUIRED_FIELDS - set(payload)
    if unknown:
        raise ValueError(f"{context} contains unknown fields: {', '.join(sorted(unknown))}")
    if missing:
        raise ValueError(f"{context} is missing fields: {', '.join(sorted(missing))}")
    optional = payload["optional"]
    if type(optional) is not bool:
        raise ValueError(f"{context} optional must be a boolean.")
    input_type = _require_string(payload["type"], f"{context} type")
    has_default = "default" in payload
    default = payload.get("default")
    if has_default and not isinstance(default, (str, int, float, bool)) and default is not None:
        raise ValueError(f"{context} default must be a JSON scalar.")
    option_source = _parse_option_source(payload["option_source"], f"{context} option_source")
    if input_type in {"COMBO", "DYNAMICCOMBO"}:
        if option_source.kind == "not-applicable":
            raise ValueError(f"{context} option source must be classified.")
    elif option_source.kind != "not-applicable":
        raise ValueError(f"{context} non-option input must use not-applicable.")
    return CoreInputContract(
        optional=optional,
        type=input_type,
        option_source=option_source,
        has_default=has_default,
        default=default,
    )


def _parse_inventory(value: object) -> CoreGraphInventory:
    payload = _require_mapping(value, "inventory")
    _require_exact_fields(payload, _INVENTORY_FIELDS, "inventory")
    return CoreGraphInventory(
        source_file_count=_require_count(payload["source_file_count"], "source_file_count"),
        class_count=_require_count(payload["class_count"], "class_count"),
        input_count=_require_count(payload["input_count"], "input_count"),
        changed_source_file_count=_require_count(
            payload["changed_source_file_count"], "changed_source_file_count"
        ),
        changed_class_count=_require_count(
            payload["changed_class_count"], "changed_class_count"
        ),
        classified_option_count=_require_count(
            payload["classified_option_count"], "classified_option_count"
        ),
    )


def parse_core_graph_contract_text(text: str) -> CoreGraphContract:
    try:
        parsed = json.loads(text, object_pairs_hook=_reject_duplicate_members)
    except json.JSONDecodeError as exc:
        raise ValueError("Core graph contract is not valid JSON.") from exc
    payload = _require_mapping(parsed, "core graph contract")
    _require_exact_fields(payload, _CORE_TOP_LEVEL_FIELDS, "core graph contract")
    if payload["schema_version"] != CORE_SCHEMA_VERSION:
        raise ValueError("Core graph contract schema_version is invalid.")
    baseline_revision = _require_revision(payload["baseline_revision"], "baseline_revision")
    source_revision = _require_revision(payload["source_revision"], "source_revision")
    inventory = _parse_inventory(payload["inventory"])

    source_payload = _require_mapping(payload["source_files"], "source_files")
    if tuple(source_payload) != tuple(sorted(source_payload)):
        raise ValueError("source_files must be ordered by canonical path.")
    source_files: dict[str, CoreSourceFileContract] = {}
    for raw_path, raw_source in source_payload.items():
        path = _require_relative_path(raw_path, "source file path")
        source = _require_mapping(raw_source, f"source file {path}")
        _require_exact_fields(source, _SOURCE_FILE_FIELDS, f"source file {path}")
        raw_classes = source["classes"]
        if not isinstance(raw_classes, list) or not raw_classes:
            raise ValueError(f"source file {path} classes must be a non-empty array.")
        classes = tuple(_require_string(item, f"source file {path} class") for item in raw_classes)
        if classes != tuple(sorted(classes)) or len(set(classes)) != len(classes):
            raise ValueError(f"source file {path} classes must be unique and sorted.")
        byte_drift = _require_string(source["byte_drift"], f"source file {path} byte_drift")
        signature_drift = _require_string(
            source["covered_signature_drift"],
            f"source file {path} covered_signature_drift",
        )
        if byte_drift not in _DRIFT_VALUES or signature_drift not in _DRIFT_VALUES:
            raise ValueError(f"source file {path} drift value is invalid.")
        source_files[path] = CoreSourceFileContract(
            baseline_blob=_require_revision(source["baseline_blob"], f"source file {path} baseline_blob"),
            source_blob=_require_revision(source["source_blob"], f"source file {path} source_blob"),
            source_sha256=_require_sha256(source["source_sha256"], f"source file {path} source_sha256"),
            byte_drift=byte_drift,
            covered_signature_drift=signature_drift,
            classes=classes,
        )

    class_payload = _require_mapping(payload["classes"], "classes")
    if tuple(class_payload) != tuple(sorted(class_payload)):
        raise ValueError("classes must be ordered by class type.")
    classes: dict[str, CoreClassContract] = {}
    for class_type, raw_class in class_payload.items():
        _require_string(class_type, "class type")
        class_value = _require_mapping(raw_class, f"class {class_type}")
        _require_exact_fields(class_value, _CLASS_FIELDS, f"class {class_type}")
        path = _require_relative_path(class_value["source_path"], f"class {class_type} source_path")
        raw_inputs = _require_mapping(class_value["inputs"], f"class {class_type} inputs")
        if tuple(raw_inputs) != tuple(sorted(raw_inputs)):
            raise ValueError(f"class {class_type} inputs must be ordered by name.")
        inputs = MappingProxyType(
            {
                name: _parse_input(value, f"class {class_type} input {name}")
                for name, value in raw_inputs.items()
            }
        )
        signature_drift = _require_string(
            class_value["signature_drift"], f"class {class_type} signature_drift"
        )
        if signature_drift not in _DRIFT_VALUES:
            raise ValueError(f"class {class_type} signature_drift is invalid.")
        classes[class_type] = CoreClassContract(
            source_revision=_require_revision(
                class_value["source_revision"], f"class {class_type} source_revision"
            ),
            source_path=path,
            source_blob=_require_revision(class_value["source_blob"], f"class {class_type} source_blob"),
            source_sha256=_require_sha256(
                class_value["source_sha256"], f"class {class_type} source_sha256"
            ),
            signature_drift=signature_drift,
            inputs=inputs,
        )

    contract = CoreGraphContract(
        schema_version=CORE_SCHEMA_VERSION,
        baseline_revision=baseline_revision,
        source_revision=source_revision,
        inventory=inventory,
        source_files=MappingProxyType(source_files),
        classes=MappingProxyType(classes),
    )
    _validate_core_graph_consistency(contract)
    return contract


def _validate_core_graph_consistency(contract: CoreGraphContract) -> None:
    inventory = contract.inventory
    input_count = sum(len(value.inputs) for value in contract.classes.values())
    changed_sources = tuple(
        value for value in contract.source_files.values() if value.byte_drift == "changed"
    )
    changed_classes = {
        class_type
        for source in changed_sources
        for class_type in source.classes
    }
    option_count = sum(
        input_value.type in {"COMBO", "DYNAMICCOMBO"}
        for class_value in contract.classes.values()
        for input_value in class_value.inputs.values()
    )
    actual = (
        len(contract.source_files),
        len(contract.classes),
        input_count,
        len(changed_sources),
        len(changed_classes),
        option_count,
    )
    expected = (
        inventory.source_file_count,
        inventory.class_count,
        inventory.input_count,
        inventory.changed_source_file_count,
        inventory.changed_class_count,
        inventory.classified_option_count,
    )
    if actual != expected:
        raise ValueError("Core graph inventory counts do not match contract contents.")
    assigned_classes: set[str] = set()
    for path, source in contract.source_files.items():
        for class_type in source.classes:
            if class_type in assigned_classes:
                raise ValueError(f"Class {class_type} is assigned to multiple source files.")
            assigned_classes.add(class_type)
            class_contract = contract.classes.get(class_type)
            if class_contract is None or class_contract.source_path != path:
                raise ValueError(f"Class {class_type} source-file relationship is invalid.")
            if class_contract.source_revision != contract.source_revision:
                raise ValueError(f"Class {class_type} source revision is invalid.")
            if (
                class_contract.source_blob != source.source_blob
                or class_contract.source_sha256 != source.source_sha256
            ):
                raise ValueError(f"Class {class_type} source provenance is inconsistent.")
    if assigned_classes != set(contract.classes):
        raise ValueError("Source-file inventory does not cover the exact class set.")


def _option_source_payload(value: OptionSource) -> dict[str, object]:
    if value.kind == "not-applicable":
        return {"kind": value.kind}
    if value.kind == "literal":
        return {"kind": value.kind, "values": list(value.values)}
    return {"kind": value.kind, "source": value.source}


def _core_graph_payload(contract: CoreGraphContract) -> dict[str, object]:
    return {
        "baseline_revision": contract.baseline_revision,
        "classes": {
            class_type: {
                "inputs": {
                    name: {
                        **({"default": value.default} if value.has_default else {}),
                        "optional": value.optional,
                        "option_source": _option_source_payload(value.option_source),
                        "type": value.type,
                    }
                    for name, value in class_value.inputs.items()
                },
                "signature_drift": class_value.signature_drift,
                "source_blob": class_value.source_blob,
                "source_path": class_value.source_path,
                "source_revision": class_value.source_revision,
                "source_sha256": class_value.source_sha256,
            }
            for class_type, class_value in contract.classes.items()
        },
        "inventory": {
            "changed_class_count": contract.inventory.changed_class_count,
            "changed_source_file_count": contract.inventory.changed_source_file_count,
            "class_count": contract.inventory.class_count,
            "classified_option_count": contract.inventory.classified_option_count,
            "input_count": contract.inventory.input_count,
            "source_file_count": contract.inventory.source_file_count,
        },
        "schema_version": contract.schema_version,
        "source_files": {
            path: {
                "baseline_blob": value.baseline_blob,
                "byte_drift": value.byte_drift,
                "classes": list(value.classes),
                "covered_signature_drift": value.covered_signature_drift,
                "source_blob": value.source_blob,
                "source_sha256": value.source_sha256,
            }
            for path, value in contract.source_files.items()
        },
        "source_revision": contract.source_revision,
    }


def serialize_core_graph_contract(contract: CoreGraphContract) -> str:
    return json.dumps(_core_graph_payload(contract), indent=2, sort_keys=True) + "\n"


def load_core_graph_contract(
    path: Path = DEFAULT_CORE_GRAPH_CONTRACT_PATH,
) -> CoreGraphContract:
    return parse_core_graph_contract_text(path.read_text(encoding="utf-8"))


def _parse_profile_row(value: object, index: int) -> ProfileGraphRow:
    payload = _require_mapping(value, f"profile {index}")
    _require_exact_fields(payload, _PROFILE_FIELDS, f"profile {index}")
    class_types_value = payload["class_types"]
    if not isinstance(class_types_value, list) or not class_types_value:
        raise ValueError(f"profile {index} class_types must be a non-empty array.")
    class_types = tuple(_require_string(item, f"profile {index} class type") for item in class_types_value)
    if class_types != tuple(sorted(set(class_types))):
        raise ValueError(f"profile {index} class_types must be unique and sorted.")
    return ProfileGraphRow(
        id=_require_string(payload["id"], f"profile {index} id"),
        flow_kind=_require_string(payload["flow_kind"], f"profile {index} flow_kind"),
        node_count=_require_count(payload["node_count"], f"profile {index} node_count"),
        edge_count=_require_count(payload["edge_count"], f"profile {index} edge_count"),
        class_types=class_types,
        topology_sha256=_require_sha256(
            payload["topology_sha256"], f"profile {index} topology_sha256"
        ),
    )


def parse_profile_graph_contract_text(text: str) -> ProfileGraphContract:
    try:
        parsed = json.loads(text, object_pairs_hook=_reject_duplicate_members)
    except json.JSONDecodeError as exc:
        raise ValueError("Profile graph contract is not valid JSON.") from exc
    payload = _require_mapping(parsed, "profile graph contract")
    _require_exact_fields(payload, _PROFILE_TOP_LEVEL_FIELDS, "profile graph contract")
    if payload["schema_version"] != PROFILE_SCHEMA_VERSION:
        raise ValueError("Profile graph contract schema_version is invalid.")
    raw_profiles = payload["profiles"]
    if not isinstance(raw_profiles, list):
        raise ValueError("profiles must be an array.")
    profiles = tuple(_parse_profile_row(item, index) for index, item in enumerate(raw_profiles))
    profile_count = _require_count(payload["profile_count"], "profile_count")
    if profile_count != len(profiles):
        raise ValueError("profile_count does not match profiles.")
    ids = tuple(profile.id for profile in profiles)
    if len(set(ids)) != len(ids):
        raise ValueError("profiles contain duplicate ids.")
    return ProfileGraphContract(
        schema_version=PROFILE_SCHEMA_VERSION,
        source_revision=_require_revision(payload["source_revision"], "source_revision"),
        profile_count=profile_count,
        profiles=profiles,
    )


def _profile_graph_payload(contract: ProfileGraphContract) -> dict[str, object]:
    return {
        "profile_count": contract.profile_count,
        "profiles": [
            {
                "class_types": list(profile.class_types),
                "edge_count": profile.edge_count,
                "flow_kind": profile.flow_kind,
                "id": profile.id,
                "node_count": profile.node_count,
                "topology_sha256": profile.topology_sha256,
            }
            for profile in contract.profiles
        ],
        "schema_version": contract.schema_version,
        "source_revision": contract.source_revision,
    }


def serialize_profile_graph_contract(contract: ProfileGraphContract) -> str:
    return json.dumps(_profile_graph_payload(contract), indent=2, sort_keys=True) + "\n"


def load_profile_graph_contract(
    path: Path = DEFAULT_PROFILE_GRAPH_CONTRACT_PATH,
) -> ProfileGraphContract:
    return parse_profile_graph_contract_text(path.read_text(encoding="utf-8"))


def _is_link(value: object, workflow: Mapping[str, object]) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], str)
        and value[0] in workflow
        and isinstance(value[1], int)
        and not isinstance(value[1], bool)
    )


def validate_workflow_graph(
    workflow: Mapping[str, object],
    contract: CoreGraphContract,
    *,
    local_node_classes: frozenset[str] = DEFAULT_LOCAL_NODE_CLASSES,
) -> None:
    if not isinstance(workflow, Mapping) or not workflow:
        raise ValueError("workflow must be a non-empty mapping.")
    for node_id, raw_node in workflow.items():
        node = _require_mapping(raw_node, f"workflow node {node_id}")
        class_type = _require_string(node.get("class_type"), f"workflow node {node_id} class_type")
        inputs = _require_mapping(node.get("inputs"), f"workflow node {node_id} inputs")
        if class_type in local_node_classes:
            continue
        class_contract = contract.classes.get(class_type)
        if class_contract is None:
            raise ValueError(f"workflow node {node_id} uses unknown node {class_type}.")
        allowed = set(class_contract.inputs)
        dynamic_prefixes = tuple(
            f"{name}."
            for name, value in class_contract.inputs.items()
            if value.type == "DYNAMICCOMBO"
        )
        unknown = sorted(
            name
            for name in inputs
            if name not in allowed and not any(name.startswith(prefix) for prefix in dynamic_prefixes)
        )
        if unknown:
            raise ValueError(
                f"workflow node {node_id} has unknown input {unknown[0]} for {class_type}."
            )
        missing = sorted(
            name
            for name, value in class_contract.inputs.items()
            if not value.optional and name not in inputs
        )
        if missing:
            raise ValueError(
                f"workflow node {node_id} is missing required input {missing[0]} for {class_type}."
            )
        for name, value in inputs.items():
            input_contract = class_contract.inputs.get(name)
            if input_contract is None or _is_link(value, workflow):
                continue
            option_source = input_contract.option_source
            if option_source.kind == "literal" and value not in option_source.values:
                raise ValueError(
                    f"workflow node {node_id} input {name} is not a literal option for {class_type}."
                )
    # JSON round-trip is the serialization compatibility floor for candidate projections.
    if json.loads(json.dumps(workflow, sort_keys=True)) != workflow:
        raise ValueError("workflow is not JSON round-trip stable.")


def build_profile_graph_row(
    profile_id: str,
    flow_kind: str,
    workflow: Mapping[str, object],
) -> ProfileGraphRow:
    _require_string(profile_id, "profile id")
    _require_string(flow_kind, "flow kind")
    if not workflow:
        raise ValueError("workflow must not be empty.")
    class_by_node: dict[str, str] = {}
    for node_id, raw_node in workflow.items():
        node = _require_mapping(raw_node, f"workflow node {node_id}")
        class_by_node[str(node_id)] = _require_string(
            node.get("class_type"), f"workflow node {node_id} class_type"
        )
    edges: list[tuple[str, int, str, str]] = []
    for node_id, raw_node in workflow.items():
        node = _require_mapping(raw_node, f"workflow node {node_id}")
        inputs = _require_mapping(node.get("inputs"), f"workflow node {node_id} inputs")
        for input_name, value in inputs.items():
            if _is_link(value, workflow):
                edges.append((class_by_node[value[0]], value[1], class_by_node[str(node_id)], input_name))
    topology = {
        "edges": sorted(edges),
        "nodes": sorted(class_by_node.values()),
    }
    digest = hashlib.sha256(
        json.dumps(topology, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    return ProfileGraphRow(
        id=profile_id,
        flow_kind=flow_kind,
        node_count=len(workflow),
        edge_count=len(edges),
        class_types=tuple(sorted(set(class_by_node.values()))),
        topology_sha256=digest,
    )
