"""Verify a frozen host source contract without executing upstream code."""
from __future__ import annotations

import argparse
import ast
import email.parser
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_current_host_contract_lane import read_pinned_git_blob

CONTRACT_PATH = ROOT / "tests" / "fixtures" / "host_reference_alignment_contract.json"
MAX_ARCHIVE_BYTES = 12 * 1024 * 1024
MAX_MEMBER_BYTES = 8 * 1024 * 1024


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
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version", "scope", "sources", "source_artifacts", "distributions",
        "legacy_templates", "qwen_templates", "core_components", "template_components",
    }:
        raise ValueError("Invalid contract fields.")
    if payload.get("schema_version") != "host-reference-alignment-v1":
        raise ValueError("Unsupported host reference contract.")
    if payload.get("scope") != "source-contract-only":
        raise ValueError("Source verification cannot declare live support.")
    if not isinstance(payload["sources"], dict) or set(payload["sources"]) != {"core", "frontend"}:
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
    return payload


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
               read_pinned_git_blob(roots[source], contract["sources"][source]["revision"], path))
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
    return count


def verify_distributions(contract: Mapping[str, Any], directory: Path) -> int:
    wheels: dict[str, Path] = {}
    for item in contract["distributions"]:
        filename = _relative_path(item["filename"])
        if "/" in filename:
            raise ValueError("Distribution must be a basename.")
        path = directory / filename
        if path.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ValueError("Distribution exceeds byte limit.")
        _check_bytes(path.read_bytes(), item)
        with zipfile.ZipFile(path) as archive:
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
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len({member.filename for member in members}) != len(members) or sum(member.file_size for member in members) > 64 * 1024 * 1024:
            raise ValueError("Unsafe distribution member inventory.")
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
            elif summarize_qwen_graph(workflow) != item["graph_contract"]:
                raise ValueError("Qwen graph role/default link drifted.")
    return len(contract["legacy_templates"]) + len(contract["qwen_templates"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", required=True, type=Path)
    parser.add_argument("--frontend", required=True, type=Path)
    parser.add_argument("--artifacts", required=True, type=Path)
    args = parser.parse_args()
    try:
        contract = load_contract()
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
