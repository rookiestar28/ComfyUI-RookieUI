from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

from scripts import verify_host_reference_alignment as alignment


CURRENT = alignment.ROOT / "tests/fixtures/host_moss_alignment_contract.json"


def moss_graph(mode: str) -> dict:
    """Small authored graph exercising promoted controls and actual edge routing."""
    layout = mode.endswith("_layout")
    family = mode.split("_")[0]
    names = ["value", "switch", "text", "width", "height", "steps", "cfg",
             "sampler_name", "scheduler", "switch_1", "unet_name", "clip_name", "vae_name"]
    values = ["synthetic", not layout, "", 1024, 1024, 25, 2.5, "er_sde", "simple",
              family == "base" or layout, f"moss_image_{family}_int8_convrot.safetensors",
              "qwen3.5_9b_w4a8_gptq.safetensors", "flux2-vae_small.safetensors"]
    graph = {"id": "synthetic-moss", "inputNode": {"id": -10},
             "inputs": [{"name": name, "type": "STRING"} for name in names], "nodes": [], "links": []}
    nodes = {}

    def node(key, kind, widgets=()):
        item = {"id": key, "type": kind, "inputs": [], "widgets_values": list(widgets)}
        graph["nodes"].append(item)
        nodes[key] = item

    def edge(target, name, origin, slot=0):
        link_id = len(graph["links"]) + 1
        target_slot = len(nodes[target]["inputs"])
        nodes[target]["inputs"].append({"name": name, "link": link_id})
        graph["links"].append({"id": link_id, "origin_id": origin, "origin_slot": slot,
                               "target_id": target, "target_slot": target_slot})

    def promoted(target, name, source=None):
        edge(target, name, -10, names.index(source or name))

    for key, kind, widgets in [
        (1, "UNETLoader", [values[10], "default"]), (2, "CLIPLoader", [values[11], "moss_image", "default"]),
        (3, "VAELoader", [values[12]]), (4, "CLIPTextEncode", [""]), (5, "CLIPTextEncode", [""]),
        (6, "EmptyFlux2LatentImage", [1024, 1024, 1]),
        (7, "KSampler", [0, "randomize", 25, 2.5, "er_sde", "simple", 1]),
        (11, "TextGenerate", []), (13, "PreviewAny", []), (16, "ComfySwitchNode", [False]),
        (17, "PrimitiveStringMultiline", [""]), (15, "SkipLayerGuidanceDiTSimple", ["", "22", 0, 0.5]),
        (32, "ComfySwitchNode", [False]),
    ]:
        node(key, kind, widgets)
    promoted(1, "unet_name")
    promoted(2, "clip_name")
    promoted(3, "vae_name")
    edge(4, "clip", 2)
    edge(5, "clip", 2)
    edge(4, "text", 13)
    promoted(5, "text")
    edge(13, "source", 16)
    edge(16, "on_false", 17)
    edge(16, "on_true", 11)
    promoted(16, "switch")
    promoted(17, "value")
    edge(11, "clip", 2)
    edge(11, "prompt", 17)
    edge(15, "model", 1)
    edge(32, "on_false", 1)
    edge(32, "on_true", 15)
    promoted(32, "switch", "switch_1")
    for name, origin in [("model", 32), ("positive", 4), ("negative", 5), ("latent_image", 6)]:
        edge(7, name, origin)
    for name in ["steps", "cfg", "sampler_name", "scheduler"]:
        promoted(7, name)
    for name in ["width", "height"]:
        promoted(6, name)
    wrapper = {"id": 18, "type": graph["id"], "widgets_values": values,
               "inputs": [{"name": name, "link": None} for name in names]}
    selector = {"id": 19, "type": "ResolutionSelector", "widgets_values": ["1:1 (Square)", 1, 16], "inputs": []}
    workflow = {"definitions": {"subgraphs": [graph]}, "nodes": [wrapper, selector], "links": []}

    def root_edge(target, name, origin, slot=0):
        target_slot = next((i for i, port in enumerate(target["inputs"]) if port["name"] == name), len(target["inputs"]))
        link_id = len(workflow["links"]) + 100
        if target_slot == len(target["inputs"]):
            target["inputs"].append({"name": name, "link": link_id})
        else:
            target["inputs"][target_slot]["link"] = link_id
        workflow["links"].append([link_id, origin, slot, target["id"], target_slot, "ANY"])

    root_edge(wrapper, "width", 19)
    root_edge(wrapper, "height", 19, 1)
    if layout:
        boxes = {"id": 25, "type": "CreateBoundingBoxes", "inputs": []}
        compiler = {"id": 27, "type": "MOSSImageLayoutPrompt", "inputs": []}
        preview = {"id": 26, "type": "PreviewAny", "inputs": []}
        workflow["nodes"].extend([boxes, compiler, preview])
        root_edge(compiler, "element", 25, 2)
        root_edge(preview, "source", 27)
        root_edge(wrapper, "value", 26)
        for target in [boxes, compiler]:
            root_edge(target, "width", 19)
            root_edge(target, "height", 19, 1)
    return workflow


class CurrentHostAlignmentTests(unittest.TestCase):
    def setUp(self):
        (alignment.ROOT / ".tmp").mkdir(exist_ok=True)

    def test_current_contract_is_additive_and_source_only(self):
        current = alignment.load_contract(CURRENT)
        old = alignment.load_contract()
        self.assertEqual(old["sources"]["core"]["version"], "0.39.0")
        self.assertEqual(current["sources"]["core"]["version"], "0.42.0")
        self.assertEqual(current["sources"]["frontend"]["version"], "1.59.1")
        self.assertEqual(current["core_components"]["comfyui-frontend-package"], "1.57.1")
        self.assertEqual(current["scope"], "source-contract-only")
        self.assertEqual([len(current["gallery_delta"][key]) for key in ["added", "removed", "changed"]], [45, 2, 52])
        self.assertEqual(len(current["moss_templates"]), 4)

    def test_root_switches_and_model_routes_are_verified_in_all_four_modes(self):
        contract = json.loads(CURRENT.read_bytes())
        for mode, item in contract["moss_templates"].items():
            with self.subTest(mode=mode):
                graph = moss_graph(mode)
                expected = item["graph_contract"]
                self.assertEqual(alignment.summarize_moss_graph(graph), expected)
                changed = copy.deepcopy(graph)
                # Root override must win over the unchanged inner switch widget.
                changed["nodes"][0]["widgets_values"][1] = not expected["prompt_switch"]
                self.assertNotEqual(alignment.summarize_moss_graph(changed), expected)
                changed = copy.deepcopy(graph)
                changed["nodes"][0]["widgets_values"][9] = not expected["slg_switch"]
                self.assertNotEqual(alignment.summarize_moss_graph(changed), expected)
                changed = copy.deepcopy(graph)
                next(n for n in changed["definitions"]["subgraphs"][0]["nodes"] if n["id"] == 2)["widgets_values"][1] = "qwen_image"
                self.assertNotEqual(alignment.summarize_moss_graph(changed), expected)

    def test_moss_invalid_edges_boolean_aliases_and_layout_size_mismatch_fail(self):
        for mutation in ["target", "slot", "boolean", "layout-slot", "layout-size"]:
            with self.subTest(mutation=mutation), self.assertRaises((ValueError, KeyError)):
                graph = moss_graph("base_layout")
                inner = graph["definitions"]["subgraphs"][0]
                if mutation == "target":
                    inner["links"][0]["target_id"] = 999
                elif mutation == "slot":
                    next(link for link in inner["links"] if link["target_id"] == 7 and link["origin_id"] == 4)["origin_slot"] = 1
                elif mutation == "boolean":
                    graph["nodes"][0]["widgets_values"][1] = 0
                elif mutation == "layout-slot":
                    next(link for link in graph["links"] if link[1] == 25)[2] = 1
                else:
                    next(link for link in graph["links"] if link[3] == 27 and link[4] == 1)[2] = 1
                alignment.summarize_moss_graph(graph)

    def test_archive_rejects_duplicate_unsafe_and_oversize_members_before_reading(self):
        with tempfile.TemporaryDirectory(dir=alignment.ROOT / ".tmp") as directory:
            path = Path(directory) / "test.whl"
            for names in [("same", "same"), ("../outside",), ("/absolute",), ("a\\b",), ("big",)]:
                with self.subTest(names=names):
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)
                        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                            for name in names:
                                archive.writestr(name, b"x" * (alignment.MAX_MEMBER_BYTES + 1) if name == "big" else b"{}")
                    raw = path.read_bytes()
                    if names == ("a\\b",):
                        # Windows ZipInfo normalizes separators while writing;
                        # inject the unsafe spelling into both ZIP headers.
                        raw = raw.replace(b"a/b", b"a\\b")
                        path.write_bytes(raw)
                    identity = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
                    with self.assertRaises(ValueError):
                        alignment.read_distribution(path, identity)

    def test_exact_legacy_difference_allowlist_preserves_all_other_values(self):
        before = {"definitions": {"subgraphs": [{"name": "Old", "nodes": []}]}}
        after = copy.deepcopy(before)
        after["definitions"]["subgraphs"][0]["name"] = "New"
        changes = alignment.summarize_legacy_changes("klein_4b", before, after)
        self.assertEqual(changes[0]["classification"], "display-name")
        after["definitions"]["subgraphs"][0]["nodes"].append({"type": "KSampler", "widgets_values": [99]})
        with self.assertRaises(ValueError):
            alignment.summarize_legacy_changes("klein_4b", before, after)
        with self.assertRaises(ValueError):
            alignment.summarize_legacy_changes("chroma", before, {"changed": True})

    def test_gallery_is_compared_with_actual_archive_members_and_classification(self):
        contract = json.loads(CURRENT.read_bytes())
        contract["legacy_templates"] = []
        contract["gallery_delta"] = {"added": [{"member": item["member"], "classification": "moss-candidate"}
                                              for item in contract["moss_templates"].values()], "removed": [], "changed": []}
        with tempfile.TemporaryDirectory(dir=alignment.ROOT / ".tmp") as directory:
            before = Path(directory) / "before.whl"
            after = Path(directory) / "after.whl"
            with zipfile.ZipFile(before, "w") as archive:
                archive.writestr("preserved.json", "{}")
            with zipfile.ZipFile(after, "w") as archive:
                archive.writestr("preserved.json", "{}")
                for item in contract["moss_templates"].values():
                    archive.writestr(item["member"], "{}")
            with zipfile.ZipFile(before) as left, zipfile.ZipFile(after) as right:
                alignment.verify_template_delta(contract, left, right)
                wrong = copy.deepcopy(contract)
                wrong["gallery_delta"]["added"][0]["classification"] = "reference-only"
                with self.assertRaises(ValueError):
                    alignment.verify_template_delta(wrong, left, right)
            with zipfile.ZipFile(after, "a") as archive:
                archive.writestr("unclassified.json", "{}")
            with zipfile.ZipFile(before) as left, zipfile.ZipFile(after) as right, self.assertRaises(ValueError):
                alignment.verify_template_delta(contract, left, right)

    def test_current_manifest_rejects_missing_modes_baseline_drift_and_duplicate_members(self):
        original = json.loads(CURRENT.read_bytes())
        with tempfile.TemporaryDirectory(dir=alignment.ROOT / ".tmp") as directory:
            path = Path(directory) / "contract.json"
            for mutation in ["mode", "baseline", "member", "gallery"]:
                data = copy.deepcopy(original)
                if mutation == "mode":
                    data["moss_templates"].pop("base")
                elif mutation == "baseline":
                    data["baseline_distribution"]["sha256"] = "0" * 64
                elif mutation == "member":
                    data["moss_templates"]["base"]["member"] = "../outside.json"
                else:
                    data["gallery_delta"]["added"].append(data["gallery_delta"]["added"][0])
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    alignment.load_contract(path)


if __name__ == "__main__":
    unittest.main()
