"""Verify a frozen host source contract without executing upstream code."""
from __future__ import annotations

import argparse
import ast
import email.parser
import hashlib
import io
import json
import re
import stat
import sys
import zipfile
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_current_host_contract_lane import read_pinned_git_blob

CONTRACT_PATH = ROOT / "tests" / "fixtures" / "host_reference_alignment_contract.json"
MOSS_CONTRACT_PATH = ROOT / "tests" / "fixtures" / "host_moss_alignment_contract.json"
MAX_ARCHIVE_BYTES = 12 * 1024 * 1024
MAX_MEMBER_BYTES = 8 * 1024 * 1024
CURRENT_FIELDS = {"moss_templates", "baseline_distribution", "gallery_delta", "legacy_changes"}
HOST_046_SCHEMA = "host-046-alignment-v1"
HOST_046_FIELDS = {"moss_changes", "text_generate_tripwire"}
SCHEMA_LEVELS = {"host-reference-alignment-v1": 0, "host-moss-alignment-v1": 1, HOST_046_SCHEMA: 2}
# The Core-pinned frontend package is read from the standalone frontend repository at its own tag.
SOURCE_ROOTS = {"core": "core", "frontend": "frontend", "frontend_core_package": "frontend"}
MOSS_MODES = {"base", "sft", "base_layout", "sft_layout"}
LEGACY_ENHANCERS = frozenset({"TextGenerate"})
HOST_046_ENHANCERS = frozenset({"TextGenerate", "TextGenerateV2"})
MOSS_CHANGE_CLASSES = {"enhancer-node-class", "template-seed", "model-download-url"}
GALLERY_046_CHANGED = {"reference-only-note-change", "reference-only-executable-change"}
# Consumed host seams that must stay in the 0.46 source sample; the retired paths moved in FE 1.60+.
REQUIRED_046_SOURCES = frozenset({
    ("core", "comfy_extras/nodes_textgen.py"), ("core", "comfy_extras/nodes_replacements.py"),
    ("core", "app/node_replace_manager.py"), ("core", "server.py"), ("core", "execution.py"),
    ("core", "comfy/cli_args.py"), ("core", "comfy/model_management.py"),
    ("frontend", "package.json"), ("frontend", "src/scripts/app.ts"), ("frontend", "src/scripts/api.ts"),
    ("frontend", "src/scripts/pnginfo.ts"), ("frontend", "packages/api-client/src/ComfyApi.ts"),
    ("frontend", "packages/api-client/src/fetchWithRetry.ts"), ("frontend", "packages/api-client/src/retryPolicy.ts"),
    ("frontend", "packages/api-client/src/executionTypes.ts"),
    ("frontend", "src/platform/extensions/services/extensionService.ts"),
    ("frontend", "src/stores/workspace/sidebarTabStore.ts"),
    ("frontend", "packages/design-system/src/components/splitter/SplitterGroup.vue"),
    ("frontend_core_package", "package.json"), ("frontend_core_package", "src/scripts/app.ts"),
    ("frontend_core_package", "src/scripts/api.ts"),
})
RETIRED_046_SOURCES = frozenset({
    ("frontend", "src/services/extensionService.ts"),
    ("frontend", "src/platform/remote/comfyui/execution/types.ts"),
})


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field.")
        result[key] = value
    return result


def _relative_path(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or "\\" in value
        or ":" in value
        or any(ord(char) < 32 for char in value)
    ):
        raise ValueError("Unsafe contract artifact path.")
    return value


def _check_bytes(raw: bytes, expected: Mapping[str, Any]) -> None:
    if len(raw) != expected["bytes"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
        raise ValueError("Contract artifact bytes drifted.")


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    if not isinstance(payload, dict) or payload.get("schema_version") not in SCHEMA_LEVELS:
        raise ValueError("Unsupported host reference contract.")
    level = SCHEMA_LEVELS[payload["schema_version"]]
    current = level >= 1
    fields = {
        "schema_version", "scope", "sources", "source_artifacts", "distributions",
        "legacy_templates", "qwen_templates", "core_components", "template_components",
    }
    if set(payload) != fields | (CURRENT_FIELDS if current else set()) | (HOST_046_FIELDS if level == 2 else set()):
        raise ValueError("Invalid contract fields.")
    if payload.get("scope") != "source-contract-only":
        raise ValueError("Source verification cannot declare live support.")
    expected_sources = {"core", "frontend"} | ({"frontend_core_package"} if level == 2 else set())
    if not isinstance(payload["sources"], dict) or set(payload["sources"]) != expected_sources:
        raise ValueError("Missing host source.")
    for field in ("source_artifacts", "distributions", "legacy_templates"):
        if not isinstance(payload[field], list) or any(not isinstance(item, dict) for item in payload[field]):
            raise ValueError("Invalid artifact collection.")
    if not isinstance(payload["qwen_templates"], dict) or any(not isinstance(item, dict) for item in payload["qwen_templates"].values()):
        raise ValueError("Invalid Qwen template collection.")
    for field in ("core_components", "template_components"):
        if not isinstance(payload[field], dict) or not payload[field] or any(
            not isinstance(name, str) or not isinstance(version, str)
            for name, version in payload[field].items()
        ):
            raise ValueError("Invalid component versions.")
    for source in payload["sources"].values():
        if not isinstance(source, dict) or set(source) != {"revision", "version"} or not re.fullmatch(r"[0-9a-f]{40}", source["revision"]):
            raise ValueError("Invalid source revision.")
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){2}", source["version"]):
            raise ValueError("Invalid source version.")
    seen: set[tuple[str, str]] = set()
    for item in payload["source_artifacts"]:
        key = (item["source"], _relative_path(item["path"]))
        if key[0] not in payload["sources"] or key in seen:
            raise ValueError("Invalid or duplicate source artifact.")
        seen.add(key)
    if not seen or len(payload["legacy_templates"]) != 11 or set(payload["qwen_templates"]) != {"txt2img", "edit"}:
        raise ValueError("Incomplete supported template coverage.")
    for item in payload["distributions"]:
        if "/" in _relative_path(item["filename"]):
            raise ValueError("Distribution must be a basename.")
    if len(payload["distributions"]) != 3 or {item["name"] for item in payload["distributions"]} != {
        "comfyui-workflow-templates", "comfyui-workflow-templates-core", "comfyui-workflow-templates-json",
    }:
        raise ValueError("Incomplete distribution coverage.")
    for item in [*payload["legacy_templates"], *payload["qwen_templates"].values()]:
        _relative_path(item["member"])
    for item in [*payload["source_artifacts"], *payload["distributions"], *payload["legacy_templates"], *payload["qwen_templates"].values()]:
        if type(item["bytes"]) is not int or item["bytes"] <= 0 or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise ValueError("Invalid artifact identity.")
    if len({item["profile"] for item in payload["legacy_templates"]}) != 11:
        raise ValueError("Duplicate legacy profile.")
    if current:
        # Each envelope compares its templates with the immediately preceding accepted envelope.
        baseline = load_contract(MOSS_CONTRACT_PATH) if level == 2 else load_contract()
        expected_distribution, = (item for item in baseline["distributions"] if item["name"].endswith("-json"))
        if payload["baseline_distribution"] != expected_distribution:
            raise ValueError("Legacy baseline identity drifted.")
        if not isinstance(payload["moss_templates"], dict) or set(payload["moss_templates"]) != MOSS_MODES:
            raise ValueError("Incomplete MOSS coverage.")
        for item in payload["moss_templates"].values():
            if not isinstance(item, dict) or set(item) != {"member", "bytes", "sha256", "graph_contract"}:
                raise ValueError("Invalid MOSS artifact fields.")
            _relative_path(item["member"])
            if type(item["bytes"]) is not int or item["bytes"] <= 0 or not isinstance(item["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
                raise ValueError("Invalid MOSS artifact identity.")
            if not isinstance(item["graph_contract"], dict):
                raise ValueError("Invalid MOSS graph contract.")
        profiles = {item["profile"] for item in baseline["legacy_templates"]}
        if not isinstance(payload["legacy_changes"], dict) or set(payload["legacy_changes"]) != profiles:
            raise ValueError("Incomplete legacy classification.")
        if {item["profile"]: item["member"] for item in payload["legacy_templates"]} != {item["profile"]: item["member"] for item in baseline["legacy_templates"]}:
            raise ValueError("Legacy member identity drifted.")
        if level == 2:
            _validate_host_046_fields(payload, baseline, seen)
        validate_gallery_delta(payload)
    return payload


def _validate_host_046_fields(
    payload: Mapping[str, Any], baseline: Mapping[str, Any], seen: set[tuple[str, str]],
) -> None:
    if not REQUIRED_046_SOURCES <= seen or RETIRED_046_SOURCES & seen:
        raise ValueError("Host source sample omits a consumed seam or keeps a retired path.")
    if payload["sources"]["frontend_core_package"]["version"] != payload["core_components"].get("comfyui-frontend-package"):
        raise ValueError("Core-pinned frontend package identity drifted.")
    for field in ("moss_templates", "qwen_templates"):
        if {key: item["member"] for key, item in payload[field].items()} != {
                key: item["member"] for key, item in baseline[field].items()}:
            raise ValueError("Admitted template member identity drifted.")
    changes = payload["moss_changes"]
    if not isinstance(changes, dict) or set(changes) != MOSS_MODES:
        raise ValueError("Incomplete MOSS change classification.")
    for rows in changes.values():
        if not isinstance(rows, list):
            raise ValueError("Invalid MOSS change classification.")
        for row in rows:
            if (not isinstance(row, dict) or set(row) != {"pointer", "classification", "before_sha256", "after_sha256"}
                    or row["classification"] not in MOSS_CHANGE_CLASSES or not isinstance(row["pointer"], str)
                    or any(not isinstance(row[key], str) or not re.fullmatch(r"[0-9a-f]{64}", row[key])
                           for key in ("before_sha256", "after_sha256"))):
                raise ValueError("Invalid MOSS change classification.")
    tripwire = payload["text_generate_tripwire"]
    if (not isinstance(tripwire, dict) or set(tripwire) != {"core", "krea2_enhancer"}
            or not isinstance(tripwire["core"], dict) or set(tripwire["core"]) != {"registered", "deprecated", "replacements"}
            or not isinstance(tripwire["core"]["registered"], list)):
        raise ValueError("Invalid TextGenerate tripwire.")
    # IMPORTANT: RookieUI's Krea-2 builder emits TextGenerate and fails closed before host
    # node replacement can run. A contract that records its removal or a migrated official
    # template is a migration trigger, not a requalification; refuse it here.
    if tripwire["krea2_enhancer"] != "TextGenerate" or "TextGenerate" not in tripwire["core"]["registered"]:
        raise ValueError("TextGenerate migration trigger reached; requalification is not sufficient.")


def read_distribution(path: Path, expected: Mapping[str, Any]) -> zipfile.ZipFile:
    """Return an owned in-memory archive after bounding all untrusted member reads."""
    with path.open("rb") as stream:
        raw = stream.read(MAX_ARCHIVE_BYTES + 1)
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise ValueError("Distribution exceeds byte limit.")
    _check_bytes(raw, expected)
    archive = zipfile.ZipFile(io.BytesIO(raw))
    try:
        members = archive.infolist()
        if len(members) > 4096 or len({item.filename for item in members}) != len(members):
            raise ValueError("Unsafe distribution member inventory.")
        if sum(item.file_size for item in members) > 64 * 1024 * 1024:
            raise ValueError("Distribution exceeds expanded byte limit.")
        for item in members:
            # IMPORTANT: ZipInfo normalizes backslashes on Windows. Validate
            # the original header spelling too, or unsafe paths become hidden.
            _relative_path(item.orig_filename.rstrip("/") if item.is_dir() else item.orig_filename)
            _relative_path(item.filename.rstrip("/") if item.is_dir() else item.filename)
            if (item.file_size > MAX_MEMBER_BYTES or item.flag_bits & 1 or stat.S_ISLNK(item.external_attr >> 16)
                    or item.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA}):
                raise ValueError("Unsafe distribution member.")
    except BaseException:
        archive.close()
        raise
    return archive


def validate_gallery_delta(contract: Mapping[str, Any]) -> None:
    delta = contract["gallery_delta"]
    if not isinstance(delta, dict) or set(delta) != {"added", "removed", "changed"}:
        raise ValueError("Invalid gallery delta.")
    legacy = {item["member"] for item in contract["legacy_templates"]}
    moss = {item["member"] for item in contract["moss_templates"].values()}
    qwen = {item["member"] for item in contract["qwen_templates"].values()}
    host_046 = contract.get("schema_version") == HOST_046_SCHEMA
    seen: set[str] = set()
    for kind, rows in delta.items():
        if not isinstance(rows, list):
            raise ValueError("Invalid gallery classification.")
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"member", "classification"}:
                raise ValueError("Invalid gallery classification.")
            member = _relative_path(row["member"])
            if host_046:
                admitted = ("moss-admitted" if member in moss else "legacy-compatible" if member in legacy
                            else "qwen-admitted" if member in qwen else None)
                if kind != "changed":
                    valid = admitted is None and row["classification"] == "reference-only"
                elif admitted:
                    valid = row["classification"] == admitted
                else:
                    valid = row["classification"] in GALLERY_046_CHANGED
            else:
                expected = "moss-candidate" if member in moss else "legacy-compatible" if member in legacy else "reference-only"
                valid = row["classification"] == expected and not (member in moss and kind != "added")
            if member in seen or not valid:
                raise ValueError("Ambiguous gallery classification.")
            seen.add(member)
    if not host_046 and not moss <= {row["member"] for row in delta["added"]}:
        raise ValueError("Missing MOSS gallery candidates.")


def _value_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def summarize_legacy_changes(profile: str, before: Any, after: Any) -> list[dict[str, str]]:
    """Allow only reviewed exact paths; every other executable value remains significant."""
    allowed = {
        "klein_4b": {"/definitions/subgraphs/0/name", "/definitions/subgraphs/1/name"},
        "klein_9b": {"/definitions/subgraphs/0/name"},
        "krea2_turbo": {"/definitions/subgraphs/0/nodes/11/widgets_values/0"},
    }.get(profile, set())
    changes = []

    def visit(left: Any, right: Any, pointer: str) -> None:
        if type(left) is not type(right):
            raise ValueError("Legacy executable structure drifted.")
        if isinstance(left, dict):
            if left.keys() != right.keys():
                raise ValueError("Legacy executable fields drifted.")
            for key in sorted(left):
                visit(left[key], right[key], pointer + "/" + key)
        elif isinstance(left, list):
            if len(left) != len(right):
                raise ValueError("Legacy executable collection drifted.")
            for index, (old, new) in enumerate(zip(left, right, strict=True)):
                visit(old, new, pointer + "/" + str(index))
        elif left != right:
            if pointer not in allowed or not isinstance(left, str):
                raise ValueError("Unclassified legacy executable change.")
            changes.append({"pointer": pointer, "before_sha256": _value_digest(left),
                            "after_sha256": _value_digest(right), "classification":
                            "optional-enhancer-instruction" if profile == "krea2_turbo" else "display-name"})

    visit(executable_projection(before), executable_projection(after), "")
    if profile == "krea2_turbo" and changes:
        graph = _Graph(executable_projection(after)["definitions"]["subgraphs"][0])
        instruction = graph.graph["nodes"][11]
        concatenate = graph.origin(graph.one("TextGenerate"), "prompt")[0]
        instruction_source, slot = graph.origin(concatenate, "string_a")
        if (instruction["type"] != "PrimitiveStringMultiline" or concatenate["type"] != "StringConcatenate"
                or instruction_source["id"] != instruction["id"] or slot != 0):
            raise ValueError("Instruction is not confined to the enhancer.")
        enhancer = graph.one("TextGenerate")
        if not any(node["type"] == "ComfySwitchNode" and graph.origin(node, "on_true") == (enhancer, 0)
                   for node in graph.nodes.values()):
            raise ValueError("Enhancer is not optional.")
    return changes


class _Graph:
    def __init__(self, graph: dict[str, Any]) -> None:
        self.graph = graph
        self.nodes = {node["id"]: node for node in graph["nodes"]}
        self.links = {link["id"]: link for link in graph["links"]}
        if len(self.nodes) != len(graph["nodes"]) or len(self.links) != len(graph["links"]):
            raise ValueError("Duplicate graph identity.")
        if any(type(link[slot]) is not int or link[slot] < 0
               for link in self.links.values() for slot in ("origin_slot", "target_slot")):
            raise ValueError("Invalid graph output or input slot.")

    def one(self, kind: str) -> dict[str, Any]:
        node, = (node for node in self.nodes.values() if node["type"] == kind)
        return node

    def origin(self, node: dict[str, Any], name: str) -> tuple[dict[str, Any], int]:
        found = next(((index, port) for index, port in enumerate(node["inputs"]) if port["name"] == name), None)
        if found is None:
            raise ValueError("Missing graph input edge.")
        index, port = found
        link = self.links[port["link"]]
        if link["target_id"] != node["id"] or link["target_slot"] != index:
            raise ValueError("Invalid graph input edge.")
        if link["origin_id"] == self.graph.get("inputNode", {}).get("id"):
            port = self.graph["inputs"][link["origin_slot"]]
            return {"type": "GraphInput", "name": port["name"]}, link["origin_slot"]
        return self.nodes[link["origin_id"]], link["origin_slot"]


def summarize_moss_graph(
    workflow: dict[str, Any], *, enhancers: frozenset[str] = LEGACY_ENHANCERS,
) -> dict[str, Any]:
    subgraph, = workflow["definitions"]["subgraphs"]
    graph = _Graph(subgraph)
    root = _Graph({"nodes": workflow["nodes"], "links": [dict(zip(
        ("id", "origin_id", "origin_slot", "target_id", "target_slot", "type"), link, strict=True))
        for link in workflow["links"]]})
    wrapper = root.one(subgraph["id"])
    scalar = [port for port in subgraph["inputs"] if port["type"] not in {"IMAGE", "VIDEO", "AUDIO"}]
    defaults = dict(zip((port["name"] for port in scalar), wrapper["widgets_values"], strict=True))

    def promoted(node: dict[str, Any], name: str, expected: str | None = None) -> Any:
        source, _ = graph.origin(node, name)
        if source != {"type": "GraphInput", "name": expected or name}:
            raise ValueError("Unexpected promoted control route.")
        return defaults[source["name"]]

    def edge(node: dict[str, Any], name: str, kind: str, slot: int = 0) -> dict[str, Any]:
        origin, actual = graph.origin(node, name)
        if origin["type"] != kind or actual != slot:
            raise ValueError("Unexpected MOSS graph role or output slot.")
        return origin

    sampler = graph.one("KSampler")
    positive = edge(sampler, "positive", "CLIPTextEncode")
    negative = edge(sampler, "negative", "CLIPTextEncode")
    clip = edge(positive, "clip", "CLIPLoader")
    if edge(negative, "clip", "CLIPLoader") != clip or positive == negative:
        raise ValueError("Conditioning roles drifted.")
    promoted(negative, "text")
    preview = edge(positive, "text", "PreviewAny")
    prompt_switch = edge(preview, "source", "ComfySwitchNode")
    direct = edge(prompt_switch, "on_false", "PrimitiveStringMultiline")
    enhancer, enhancer_slot = graph.origin(prompt_switch, "on_true")
    if enhancer["type"] not in enhancers or enhancer_slot != 0:
        raise ValueError("Unexpected MOSS graph role or output slot.")
    if edge(enhancer, "clip", "CLIPLoader") != clip or edge(enhancer, "prompt", "PrimitiveStringMultiline") != direct:
        raise ValueError("Enhancer prompt or encoder route drifted.")
    if enhancer["type"] == "TextGenerateV2":
        image, _ = graph.origin(enhancer, "images.image1")
        if image != {"type": "GraphInput", "name": "image"}:
            raise ValueError("Enhancer image route drifted.")
    promoted(direct, "value")
    pe = promoted(prompt_switch, "switch")
    slg_switch = edge(sampler, "model", "ComfySwitchNode")
    model = edge(slg_switch, "on_false", "UNETLoader")
    slg = edge(slg_switch, "on_true", "SkipLayerGuidanceDiTSimple")
    if edge(slg, "model", "UNETLoader") != model:
        raise ValueError("SLG model role drifted.")
    slg_enabled = promoted(slg_switch, "switch", "switch_1")
    # IMPORTANT: promoted root values govern these switches; inner widgets can
    # retain different defaults. Reading widgets alone misqualifies Base/SFT.
    if type(pe) is not bool or type(slg_enabled) is not bool:
        raise ValueError("MOSS switches must be boolean.")
    latent = edge(sampler, "latent_image", "EmptyFlux2LatentImage")
    width = promoted(latent, "width")
    height = promoted(latent, "height")
    width_source, width_slot = root.origin(wrapper, "width")
    height_source, height_slot = root.origin(wrapper, "height")
    if width_source != height_source or width_source["type"] != "ResolutionSelector" or (width_slot, height_slot) != (0, 1):
        raise ValueError("Output size routes drifted.")
    value_port, = (port for port in wrapper["inputs"] if port["name"] == "value")
    layout = value_port["link"] is not None
    if layout:
        passthrough, slot = root.origin(wrapper, "value")
        compiler, compiler_slot = root.origin(passthrough, "source")
        boxes, boxes_slot = root.origin(compiler, "element")
        if (passthrough["type"], slot, compiler["type"], compiler_slot, boxes["type"], boxes_slot) != (
                "PreviewAny", 0, "MOSSImageLayoutPrompt", 0, "CreateBoundingBoxes", 2):
            raise ValueError("Layout conditioning route drifted.")
        for node in (compiler, boxes):
            if root.origin(node, "width") != (width_source, 0) or root.origin(node, "height") != (height_source, 1):
                raise ValueError("Layout and output dimensions differ.")
    return {"diffusion": promoted(model, "unet_name"),
            "clip": [promoted(clip, "clip_name"), clip["widgets_values"][1]],
            "vae": promoted(graph.one("VAELoader"), "vae_name"),
            "sampler_defaults": [promoted(sampler, "steps"), promoted(sampler, "cfg"),
                                 promoted(sampler, "sampler_name"), promoted(sampler, "scheduler"), sampler["widgets_values"][6]],
            "latent": [latent["type"], width, height, latent["widgets_values"][2]],
            "conditioning": [positive["type"], 0, negative["type"], 0],
            "prompt_path": [preview["type"], prompt_switch["type"], direct["type"], enhancer["type"]],
            "prompt_switch": pe, "slg_switch": slg_enabled, "slg_parameters": slg["widgets_values"],
            "slg_path": [slg_switch["type"], model["type"], slg["type"], model["type"]],
            "resolution": width_source["widgets_values"], "layout": layout}


def canonical_graph(workflow: Mapping[str, Any]) -> dict[str, Any]:
    """Executable identity: node roles, widgets and named input origins.

    Layout, notes, groups, link IDs and derived outputs are excluded so that a re-saved
    template with renumbered links compares equal when every executable edge is the same.
    """
    def link_map(rows: list[Any], listed: bool) -> dict[Any, tuple[Any, ...]]:
        links: dict[Any, tuple[Any, ...]] = {}
        for row in rows:
            values = tuple(row[:5]) if listed else tuple(
                row[key] for key in ("id", "origin_id", "origin_slot", "target_id", "target_slot"))
            if values[0] in links:
                raise ValueError("Duplicate graph identity.")
            links[values[0]] = values[1:]
        return links

    def nodes_of(graph: Mapping[str, Any], links: Mapping[Any, tuple[Any, ...]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for node in graph["nodes"]:
            if node.get("type") in {"MarkdownNote", "Note"}:
                continue
            key = str(node["id"])
            if key in result:
                raise ValueError("Duplicate graph identity.")
            inputs: dict[str, list[Any]] = {}
            for index, port in enumerate(node.get("inputs", [])):
                if port.get("link") is None:
                    continue
                origin_id, origin_slot, target_id, target_slot = links[port["link"]]
                if target_id != node["id"] or target_slot != index or port["name"] in inputs:
                    raise ValueError("Invalid graph input edge.")
                inputs[port["name"]] = [origin_id, origin_slot]
            result[key] = {"type": node["type"], "mode": node.get("mode", 0),
                           "widgets_values": node.get("widgets_values", []),
                           "properties": node.get("properties", {}), "inputs": inputs}
        return result

    subgraphs = [{
        "id": subgraph["id"],
        "inputs": [[port["name"], port["type"]] for port in subgraph["inputs"]],
        "outputs": [[port["name"], port["type"]] for port in subgraph.get("outputs", [])],
        "nodes": nodes_of(subgraph, link_map(subgraph["links"], False)),
    } for subgraph in workflow.get("definitions", {}).get("subgraphs", [])]
    return {"root": {"nodes": nodes_of(workflow, link_map(workflow["links"], True))}, "subgraphs": subgraphs}


def _enhancer_key(nodes: Mapping[str, Any]) -> str:
    keys = [key for key, node in nodes.items() if node["type"] in HOST_046_ENHANCERS]
    if len(keys) != 1:
        raise ValueError("MOSS enhancer identity drifted.")
    return keys[0]


def summarize_moss_changes(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[dict[str, str]]:
    """Classify a re-saved MOSS template against the previous envelope; anything else fails."""
    left, right = canonical_graph(before), canonical_graph(after)
    if len(left["subgraphs"]) != 1 or len(right["subgraphs"]) != 1:
        raise ValueError("MOSS subgraph identity drifted.")
    old_nodes, new_nodes = left["subgraphs"][0]["nodes"], right["subgraphs"][0]["nodes"]
    old_key, new_key = _enhancer_key(old_nodes), _enhancer_key(new_nodes)
    old, new = old_nodes[old_key], new_nodes[new_key]
    rows: list[dict[str, str]] = []
    if (old["type"], old_key) != (new["type"], new_key):
        # IMPORTANT: only the published TextGenerate -> TextGenerateV2 node replacement is
        # accepted: same widgets, mode and origins, with `image` renamed to `images.image1`.
        renamed = {("images.image1" if name == "image" else name): origin for name, origin in old["inputs"].items()}

        def properties(record: Mapping[str, Any]) -> dict[str, Any]:
            return {key: value for key, value in record["properties"].items() if key != "Node name for S&R"}

        if ((old["type"], new["type"]) != ("TextGenerate", "TextGenerateV2") or renamed != new["inputs"]
                or old["widgets_values"] != new["widgets_values"] or old["mode"] != new["mode"]
                or properties(old) != properties(new)
                or any(record["properties"].get("Node name for S&R", record["type"]) != record["type"]
                       for record in (old, new))):
            raise ValueError("Unclassified MOSS enhancer change.")
        rows.append({"pointer": "/subgraphs/0/nodes/enhancer", "classification": "enhancer-node-class",
                     "before_sha256": _value_digest(old), "after_sha256": _value_digest(new)})
        for nodes, key in ((old_nodes, old_key), (new_nodes, new_key)):
            del nodes[key]
            for record in nodes.values():
                record["inputs"] = {name: (["enhancer", origin[1]] if str(origin[0]) == key else origin)
                                    for name, origin in record["inputs"].items()}
    subgraph = left["subgraphs"][0]
    wrappers = [key for key, node in left["root"]["nodes"].items() if node["type"] == subgraph["id"]]
    if len(wrappers) != 1:
        raise ValueError("MOSS wrapper identity drifted.")
    scalar = [name for name, kind in subgraph["inputs"] if kind not in {"IMAGE", "VIDEO", "AUDIO"}]
    seeds = {f"/root/nodes/{wrappers[0]}/widgets_values/{index}" for index, name in enumerate(scalar) if name == "seed"}
    url_pointer = re.compile(r"^/subgraphs/0/nodes/([^/]+)/properties/models/([0-9]+)/url$")

    def classify(pointer: str, old_value: Any, new_value: Any) -> str:
        if pointer in seeds and type(old_value) is int and type(new_value) is int:
            return "template-seed"
        match = url_pointer.match(pointer)
        if match and isinstance(old_value, str) and isinstance(new_value, str):
            node = new_nodes[match.group(1)]
            model = node["properties"]["models"][int(match.group(2))]
            if new_value.rsplit("/", 1)[-1] == model["name"] and model["name"] in node["widgets_values"]:
                return "model-download-url"
        raise ValueError("Unclassified MOSS executable change.")

    def visit(old_value: Any, new_value: Any, pointer: str) -> None:
        if type(old_value) is not type(new_value):
            raise ValueError("MOSS executable structure drifted.")
        if isinstance(old_value, dict):
            if old_value.keys() != new_value.keys():
                raise ValueError("MOSS executable fields drifted.")
            for key in sorted(old_value):
                visit(old_value[key], new_value[key], f"{pointer}/{key}")
        elif isinstance(old_value, list):
            if len(old_value) != len(new_value):
                raise ValueError("MOSS executable collection drifted.")
            for index, (left_item, right_item) in enumerate(zip(old_value, new_value, strict=True)):
                visit(left_item, right_item, f"{pointer}/{index}")
        elif old_value != new_value:
            rows.append({"pointer": pointer, "classification": classify(pointer, old_value, new_value),
                         "before_sha256": _value_digest(old_value), "after_sha256": _value_digest(new_value)})

    visit(left, right, "")
    return sorted(rows, key=lambda row: row["pointer"])


def summarize_text_generate_sources(textgen: bytes, replacements: bytes) -> dict[str, Any]:
    """Read Core's TextGenerate registration as inert source; never import host code."""
    classes = [node for node in ast.parse(textgen.decode("utf-8")).body if isinstance(node, ast.ClassDef)]
    registered: list[str] = []
    deprecated: dict[str, str] = {}
    for node in classes:
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "get_node_list":
                for statement in ast.walk(item):
                    if isinstance(statement, ast.Return) and isinstance(statement.value, ast.List):
                        registered.extend(element.id for element in statement.value.elts if isinstance(element, ast.Name))
        if any(isinstance(keyword, ast.keyword) and keyword.arg == "is_deprecated"
               and isinstance(keyword.value, ast.Constant) and keyword.value.value is True for keyword in ast.walk(node)):
            bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
            deprecated[node.name] = bases[0] if bases else ""
    pairs: list[list[str]] = []
    for call in ast.walk(ast.parse(replacements.decode("utf-8"))):
        if isinstance(call, ast.Call):
            ids = {keyword.arg: keyword.value.value for keyword in call.keywords
                   if keyword.arg in {"old_node_id", "new_node_id"} and isinstance(keyword.value, ast.Constant)}
            if set(ids) == {"old_node_id", "new_node_id"} and str(ids["old_node_id"]).startswith("TextGenerate"):
                pairs.append([ids["old_node_id"], ids["new_node_id"]])
    return {"registered": registered, "deprecated": deprecated, "replacements": pairs}


def summarize_krea2_enhancer(workflow: Mapping[str, Any]) -> str:
    """Return the node class on the optional Krea-2 enhancer branch."""
    graph = _Graph(executable_projection(workflow)["definitions"]["subgraphs"][0])
    found = []
    for node in graph.nodes.values():
        if node["type"] == "ComfySwitchNode" and any(port["name"] == "on_true" for port in node["inputs"]):
            origin, _ = graph.origin(node, "on_true")
            if str(origin.get("type", "")).startswith("TextGenerate"):
                found.append(origin["type"])
    if len(found) != 1:
        raise ValueError("Krea-2 enhancer route drifted.")
    return found[0]


def executable_projection(workflow: Any) -> Any:
    """Ignore documentation nodes only; retain every executable value and edge."""
    if isinstance(workflow, dict):
        return {key: executable_projection(value) for key, value in workflow.items()}
    if isinstance(workflow, list):
        return [executable_projection(value) for value in workflow
                if not isinstance(value, dict) or value.get("type") not in {"MarkdownNote", "Note"}]
    return workflow


def summarize_qwen_graph(workflow: dict[str, Any]) -> dict[str, Any]:
    graph, = workflow["definitions"]["subgraphs"]
    nodes = {node["id"]: node for node in graph["nodes"]}
    links = {link["id"]: link for link in graph["links"]}

    def one(node_type: str) -> dict[str, Any]:
        node, = (node for node in nodes.values() if node["type"] == node_type)
        return node

    def origin(node: dict[str, Any], name: str) -> tuple[dict[str, Any], int]:
        index, port = next((index, port) for index, port in enumerate(node["inputs"]) if port["name"] == name)
        link = links[port["link"]]
        if link["target_id"] != node["id"] or link["target_slot"] != index:
            raise ValueError("Invalid graph input edge.")
        if link["origin_id"] == graph["inputNode"]["id"]:
            port = graph["inputs"][link["origin_slot"]]
            return {"type": "GraphInput", "name": port["name"]}, link["origin_slot"]
        return nodes[link["origin_id"]], link["origin_slot"]

    encoder = one("TextEncodeQwenImage21")
    sampler = one("KSampler")
    loader, clip_slot = origin(encoder, "clip")
    preview, _ = origin(encoder, "prompt")
    if preview["type"] != "PreviewAny":
        raise ValueError("Unexpected prompt passthrough.")
    switch, _ = origin(preview, "source")
    direct, _ = origin(switch, "on_false")
    enhanced, enhanced_slot = origin(switch, "on_true")
    pe_loader, _ = origin(enhanced, "clip")
    positive, positive_slot = origin(sampler, "positive")
    negative, negative_slot = origin(sampler, "negative")
    cache, _ = origin(sampler, "model")
    model, _ = origin(cache, "model")
    vae = one("VAELoader")
    wrapper, = (node for node in workflow["nodes"] if node["type"] == graph["id"])
    scalar_inputs = [port for port in graph["inputs"] if port["type"] != "IMAGE"]
    defaults = dict(zip((port["name"] for port in scalar_inputs), wrapper["widgets_values"], strict=True))
    refine_name = "switch_1" if "switch_1" in defaults else "switch"
    if type(switch["widgets_values"][0]) is not bool or type(defaults[refine_name]) is not bool:
        raise ValueError("Prompt enhancement switch must be boolean.")
    return {
        "encoder": encoder["type"], "encoder_loader": loader["widgets_values"][:2], "clip_slot": clip_slot,
        "model": model["widgets_values"][0], "vae": vae["widgets_values"][0],
        "positive": [positive["type"], positive_slot], "negative": [negative["type"], negative_slot],
        "sampler_defaults": [defaults["steps"], defaults["cfg"], *sampler["widgets_values"][4:7]],
        "cache": [cache["type"], *cache["widgets_values"]],
        "prompt_switch": [switch["type"], switch["widgets_values"][0], defaults[refine_name]],
        "direct_prompt": [direct["type"], direct.get("name")], "enhanced_prompt": [enhanced["type"], enhanced_slot],
        "enhancer_loader": pe_loader["widgets_values"][:2],
        "resolution": defaults.get("resolution", 1024),
    }


def verify_sources(
    contract: Mapping[str, Any], roots: Mapping[str, Path],
    *, blob_reader: Callable[[str, str], bytes] | None = None,
) -> int:
    count = 0
    sampled: dict[tuple[str, str], bytes] = {}
    for item in contract["source_artifacts"]:
        source, path = item["source"], _relative_path(item["path"])
        raw = (blob_reader(source, path) if blob_reader else
               read_pinned_git_blob(roots[SOURCE_ROOTS[source]], contract["sources"][source]["revision"], path))
        _check_bytes(raw, item)
        sampled[(source, path)] = raw
        count += 1
    version_tree = ast.parse(sampled[("core", "comfyui_version.py")].decode())
    version, = (node.value.value for node in version_tree.body
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
                and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets))
    if version != contract["sources"]["core"]["version"]:
        raise ValueError("Core version drifted.")
    frontend = json.loads(sampled[("frontend", "package.json")], object_pairs_hook=_unique_object)
    if frontend["version"] != contract["sources"]["frontend"]["version"]:
        raise ValueError("Frontend version drifted.")
    requirements = sampled[("core", "requirements.txt")].decode().splitlines()
    if any(f"{name}=={version}" not in requirements for name, version in contract["core_components"].items()):
        raise ValueError("Core component version drifted.")
    if "frontend_core_package" in contract["sources"]:
        package = json.loads(sampled[("frontend_core_package", "package.json")], object_pairs_hook=_unique_object)
        if package["version"] != contract["sources"]["frontend_core_package"]["version"]:
            raise ValueError("Core-pinned frontend package version drifted.")
    if "text_generate_tripwire" in contract:
        summary = summarize_text_generate_sources(sampled[("core", "comfy_extras/nodes_textgen.py")],
                                                  sampled[("core", "comfy_extras/nodes_replacements.py")])
        if summary != contract["text_generate_tripwire"]["core"]:
            raise ValueError("TextGenerate host contract drifted.")
    return count


def verify_distributions(contract: Mapping[str, Any], directory: Path) -> int:
    wheels: dict[str, Path] = {}
    for item in contract["distributions"]:
        filename = _relative_path(item["filename"])
        if "/" in filename:
            raise ValueError("Distribution must be a basename.")
        path = directory / filename
        with read_distribution(path, item) as archive:
            metadata_member, = (name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
            if archive.getinfo(metadata_member).file_size > MAX_MEMBER_BYTES:
                raise ValueError("Distribution metadata exceeds byte limit.")
            metadata = email.parser.BytesParser().parsebytes(archive.read(metadata_member))
            # Package identity follows PyPA normalization: wheel metadata may
            # use underscores where the index/distribution name uses hyphens.
            name = re.sub(r"[-_.]+", "-", str(metadata["Name"] or "")).lower()
            if name != item["name"] or metadata["Version"] != item["version"]:
                raise ValueError("Distribution version drifted.")
            if item["name"] == "comfyui-workflow-templates":
                requirements = metadata.get_all("Requires-Dist", [])
                if any(f"{name}=={version}" not in requirements for name, version in contract["template_components"].items()):
                    raise ValueError("Template component version drifted.")
        wheels[item["name"]] = path

    # CRITICAL: reference wheels are inert data. Never extract, import or install
    # them; verified bytes and bounded reads must precede graph inspection.
    path = wheels["comfyui-workflow-templates-json"]
    identity, = (item for item in contract["distributions"] if item["name"].endswith("-json"))
    host_046 = contract.get("schema_version") == HOST_046_SCHEMA
    with read_distribution(path, identity) as archive:
        for item in [*contract["legacy_templates"], *contract["qwen_templates"].values()]:
            member = _relative_path(item["member"])
            if archive.getinfo(member).file_size > MAX_MEMBER_BYTES:
                raise ValueError("Template exceeds byte limit.")
            raw = archive.read(member)
            _check_bytes(raw, item)
            workflow = json.loads(raw, object_pairs_hook=_unique_object)
            if "executable_sha256" in item:
                projected = json.dumps(executable_projection(workflow), sort_keys=True, separators=(",", ":")).encode()
                if hashlib.sha256(projected).hexdigest() != item["executable_sha256"]:
                    raise ValueError("Legacy executable template drifted.")
                if host_046 and item["profile"] == "krea2_turbo" and (
                        summarize_krea2_enhancer(workflow) != contract["text_generate_tripwire"]["krea2_enhancer"]):
                    raise ValueError("Official Krea-2 enhancer migrated; TextGenerate migration trigger reached.")
            elif summarize_qwen_graph(workflow) != item["graph_contract"]:
                raise ValueError("Qwen graph role/default link drifted.")
        if "moss_templates" in contract:
            for item in contract["moss_templates"].values():
                raw = archive.read(item["member"])
                _check_bytes(raw, item)
                enhancers = HOST_046_ENHANCERS if host_046 else LEGACY_ENHANCERS
                if summarize_moss_graph(json.loads(raw, object_pairs_hook=_unique_object),
                                        enhancers=enhancers) != item["graph_contract"]:
                    raise ValueError("MOSS graph role/default link drifted.")
            baseline = contract["baseline_distribution"]
            with read_distribution(directory / baseline["filename"], baseline) as before:
                verify_template_delta(contract, before, archive)
    return len(contract["legacy_templates"]) + len(contract["qwen_templates"]) + len(contract.get("moss_templates", {}))


def verify_template_delta(
    contract: Mapping[str, Any], before: zipfile.ZipFile, after: zipfile.ZipFile,
) -> None:
    """Compare real archive bytes; a manifest's declared delta cannot prove itself."""
    validate_gallery_delta(contract)
    old_names = {name for name in before.namelist() if name.endswith(".json")}
    new_names = {name for name in after.namelist() if name.endswith(".json")}
    actual = {"added": new_names - old_names, "removed": old_names - new_names,
              "changed": {name for name in old_names & new_names if before.read(name) != after.read(name)}}
    if any(actual[kind] != {row["member"] for row in rows} for kind, rows in contract["gallery_delta"].items()):
        raise ValueError("Unclassified gallery member delta.")
    for item in contract["legacy_templates"]:
        changes = summarize_legacy_changes(item["profile"],
            json.loads(before.read(item["member"]), object_pairs_hook=_unique_object),
            json.loads(after.read(item["member"]), object_pairs_hook=_unique_object))
        if changes != contract["legacy_changes"][item["profile"]]:
            raise ValueError("Legacy classification identity drifted.")
    if contract.get("schema_version") != HOST_046_SCHEMA:
        return

    def pair(member: str) -> tuple[Any, Any]:
        return (json.loads(before.read(member), object_pairs_hook=_unique_object),
                json.loads(after.read(member), object_pairs_hook=_unique_object))

    for row in contract["gallery_delta"]["changed"]:
        if row["classification"] in GALLERY_046_CHANGED:
            left, right = pair(row["member"])
            same = executable_projection(left) == executable_projection(right)
            if row["classification"] != ("reference-only-note-change" if same else "reference-only-executable-change"):
                raise ValueError("Gallery executable classification drifted.")
    for mode, item in contract["moss_templates"].items():
        if summarize_moss_changes(*pair(item["member"])) != contract["moss_changes"][mode]:
            raise ValueError("MOSS change classification drifted.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", required=True, type=Path)
    parser.add_argument("--frontend", required=True, type=Path)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    args = parser.parse_args()
    try:
        contract = load_contract(args.contract)
        source_count = verify_sources(contract, {"core": args.core, "frontend": args.frontend})
        template_count = verify_distributions(contract, args.artifacts)
    except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration, zipfile.BadZipFile) as error:
        print(f"Host reference contract: NOT_VERIFIED ({type(error).__name__}).")
        return 1
    print(json.dumps({"status": "verified", "scope": contract["scope"],
                      "sources": contract["sources"], "source_artifacts": source_count,
                      "template_members": template_count, "live_inference": "not-evaluated"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
