from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

from scripts import verify_host_reference_alignment as alignment
from tests.test_current_host_alignment import moss_graph


HOST_046 = alignment.ROOT / "tests/fixtures/host_046_alignment_contract.json"
V2_ENHANCERS = frozenset({"TextGenerate", "TextGenerateV2"})


def _subgraph(workflow: dict) -> dict:
    return workflow["definitions"]["subgraphs"][0]


def _node(workflow: dict, node_id: int) -> dict:
    return next(node for node in _subgraph(workflow)["nodes"] if node["id"] == node_id)


def with_enhancer(workflow: dict, kind: str, *, node_id: int = 11, image_input: str | None = None) -> dict:
    """Give the synthetic MOSS enhancer an image route like the published templates."""
    graph = copy.deepcopy(workflow)
    inner = _subgraph(graph)
    enhancer = next(node for node in inner["nodes"] if node["id"] == 11)
    enhancer["type"] = kind
    enhancer["properties"] = {"Node name for S&R": kind}
    enhancer["widgets_values"] = ["", 4096, "on", 0.7, 64, 0.95, 0.05, 1, 0, 0, False, True, "auto"]
    if node_id != 11:
        enhancer["id"] = node_id
        for link in inner["links"]:
            for field in ("origin_id", "target_id"):
                if link[field] == 11:
                    link[field] = node_id
    image_slot = len(inner["inputs"])
    inner["inputs"].append({"name": "image", "type": "IMAGE"})
    name = image_input or ("images.image1" if kind == "TextGenerateV2" else "image")
    link_id = max(link["id"] for link in inner["links"]) + 1
    enhancer["inputs"].append({"name": name, "link": link_id})
    inner["links"].append({"id": link_id, "origin_id": -10, "origin_slot": image_slot,
                           "target_id": node_id, "target_slot": len(enhancer["inputs"]) - 1})
    return graph


def renumber_links(workflow: dict, offset: int) -> dict:
    """Re-save simulation: every link ID changes while every edge stays the same."""
    graph = copy.deepcopy(workflow)
    inner = _subgraph(graph)
    for link in inner["links"]:
        link["id"] += offset
    for node in inner["nodes"]:
        for port in node["inputs"]:
            if port["link"] is not None:
                port["link"] += offset
    inner["nodes"].reverse()
    return graph


def add_seed(workflow: dict, value: int) -> dict:
    graph = copy.deepcopy(workflow)
    inner = _subgraph(graph)
    scalar = [port for port in inner["inputs"] if port["type"] not in {"IMAGE", "VIDEO", "AUDIO"}]
    inner["inputs"].insert(len(scalar), {"name": "seed", "type": "INT"})
    for link in inner["links"]:
        if link["origin_id"] == -10 and link["origin_slot"] >= len(scalar):
            link["origin_slot"] += 1
    graph["nodes"][0]["widgets_values"].append(value)
    graph["nodes"][0]["inputs"].append({"name": "seed", "link": None})
    return graph


def add_model_url(workflow: dict, url: str) -> dict:
    graph = copy.deepcopy(workflow)
    loader = _node(graph, 1)
    loader["properties"] = {"models": [{"name": loader["widgets_values"][0], "url": url,
                                        "directory": "diffusion_models"}]}
    return graph


TEXTGEN_SOURCE = b'''
from comfy_api.latest import ComfyExtension, io

class TextGenerateV2(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="TextGenerateV2", inputs=[])

class TextGenerate(TextGenerateV2):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="TextGenerate", is_deprecated=True, inputs=[])

class TextgenExtension(ComfyExtension):
    async def get_node_list(self):
        return [
            TextGenerateV2,
            TextGenerate,
        ]
'''

REPLACEMENT_SOURCE = b'''
async def register_replacements_textgenerate():
    await api.node_replacement.register(io.NodeReplace(
        new_node_id="TextGenerateV2",
        old_node_id="TextGenerate",
        input_mapping=[],
    ))
'''


def krea2_graph(kind: str) -> dict:
    nodes = [
        {"id": 1, "type": "PrimitiveStringMultiline", "inputs": [], "widgets_values": [""]},
        {"id": 2, "type": kind, "inputs": [{"name": "prompt", "link": 1}], "widgets_values": []},
        {"id": 3, "type": "ComfySwitchNode", "inputs": [{"name": "on_false", "link": 2},
                                                         {"name": "on_true", "link": 3}], "widgets_values": [True]},
    ]
    links = [{"id": 1, "origin_id": 1, "origin_slot": 0, "target_id": 2, "target_slot": 0},
             {"id": 2, "origin_id": 1, "origin_slot": 0, "target_id": 3, "target_slot": 0},
             {"id": 3, "origin_id": 2, "origin_slot": 0, "target_id": 3, "target_slot": 1}]
    return {"definitions": {"subgraphs": [{"id": "krea", "nodes": nodes, "links": links}]}, "nodes": [], "links": []}


def write_archive(path: Path, members: dict[str, object]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in members.items():
            archive.writestr(name, json.dumps(value))


class Host046ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        (alignment.ROOT / ".tmp").mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=alignment.ROOT / ".tmp")
        self.addCleanup(self.directory.cleanup)

    def test_contract_is_additive_and_pins_three_distinct_host_subjects(self) -> None:
        contract = alignment.load_contract(HOST_046)
        moss = alignment.load_contract(alignment.MOSS_CONTRACT_PATH)
        original = alignment.load_contract()
        self.assertEqual(contract["schema_version"], "host-046-alignment-v1")
        self.assertEqual(contract["scope"], "source-contract-only")
        self.assertEqual(contract["sources"]["core"], {"version": "0.46.0",
                         "revision": "da8bd08e48deee74d9f6c3bc00aed365b00ec209"})  # pragma: allowlist secret - public Git commit id
        self.assertEqual(contract["sources"]["frontend"], {"version": "1.61.8",
                         "revision": "388973acb56af768df63749b90627ac767c31be0"})  # pragma: allowlist secret - public Git commit id
        self.assertEqual(contract["sources"]["frontend_core_package"], {"version": "1.59.11",
                         "revision": "28b679cb87e88f6328883feccfac737d3f7c4415"})  # pragma: allowlist secret - public Git commit id
        self.assertEqual(contract["core_components"]["comfyui-frontend-package"], "1.59.11")
        self.assertEqual(contract["core_components"]["comfyui-workflow-templates"], "0.11.118")
        self.assertEqual(contract["template_components"]["comfyui-workflow-templates-core"], "0.3.408")
        self.assertEqual(contract["template_components"]["comfyui-workflow-templates-json"], "0.1.143")
        baseline, = (item for item in moss["distributions"] if item["name"].endswith("-json"))
        self.assertEqual(contract["baseline_distribution"], baseline)
        self.assertEqual([len(contract["gallery_delta"][key]) for key in ("added", "removed", "changed")], [73, 8, 200])
        self.assertEqual(moss["sources"]["core"]["version"], "0.42.0")
        self.assertEqual(original["sources"]["core"]["version"], "0.39.0")

    def test_contract_classifies_only_the_researched_moss_and_legacy_differences(self) -> None:
        contract = alignment.load_contract(HOST_046)
        self.assertTrue(all(changes == [] for changes in contract["legacy_changes"].values()))
        kinds = {mode: [row["classification"] for row in rows] for mode, rows in contract["moss_changes"].items()}
        self.assertEqual(kinds, {"base": ["template-seed", "enhancer-node-class"],
                                 "sft": ["template-seed", "enhancer-node-class"],
                                 "base_layout": [], "sft_layout": ["model-download-url"]})
        enhancers = {mode: item["graph_contract"]["prompt_path"][-1] for mode, item in contract["moss_templates"].items()}
        self.assertEqual(enhancers, {"base": "TextGenerateV2", "sft": "TextGenerateV2",
                                     "base_layout": "TextGenerate", "sft_layout": "TextGenerate"})
        self.assertEqual(contract["text_generate_tripwire"]["krea2_enhancer"], "TextGenerate")
        self.assertIn("TextGenerate", contract["text_generate_tripwire"]["core"]["registered"])

    def test_source_sample_replaces_moved_frontend_paths_and_rejects_retired_ones(self) -> None:
        contract = alignment.load_contract(HOST_046)
        sampled = {(item["source"], item["path"]) for item in contract["source_artifacts"]}
        self.assertTrue(alignment.REQUIRED_046_SOURCES <= sampled)
        self.assertFalse(alignment.RETIRED_046_SOURCES & sampled)
        path = Path(self.directory.name) / "contract.json"
        original = json.loads(HOST_046.read_bytes())
        for mutation in ("retired", "required", "core-package-version", "tripwire-removed", "krea2-migrated",
                         "moss-change-label", "moss-mode", "gallery-label", "baseline", "source-key"):
            data = copy.deepcopy(original)
            if mutation == "retired":
                data["source_artifacts"].append({"source": "frontend", "path": "src/services/extensionService.ts",
                                                 "bytes": 1, "sha256": "0" * 64})
            elif mutation == "required":
                data["source_artifacts"] = [item for item in data["source_artifacts"]
                                            if item["path"] != "packages/api-client/src/ComfyApi.ts"]
            elif mutation == "core-package-version":
                data["sources"]["frontend_core_package"]["version"] = "1.59.6"
            elif mutation == "tripwire-removed":
                data["text_generate_tripwire"]["core"]["registered"].remove("TextGenerate")
            elif mutation == "krea2-migrated":
                data["text_generate_tripwire"]["krea2_enhancer"] = "TextGenerateV2"
            elif mutation == "moss-change-label":
                data["moss_changes"]["base"][0]["classification"] = "anything"
            elif mutation == "moss-mode":
                data["moss_changes"].pop("sft")
            elif mutation == "gallery-label":
                data["gallery_delta"]["added"][0]["classification"] = "moss-admitted"
            elif mutation == "baseline":
                data["baseline_distribution"]["sha256"] = "0" * 64
            else:
                data["sources"].pop("frontend_core_package")
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                alignment.load_contract(path)

    def test_frontend_core_package_is_read_from_its_own_pinned_revision(self) -> None:
        contract = alignment.load_contract(HOST_046)
        calls: list[tuple[Path, str, str]] = []

        def reader(root: Path, revision: str, path: str) -> bytes:
            calls.append((root, revision, path))
            raise ValueError("stop after routing")

        package = next(item for item in contract["source_artifacts"] if item["source"] == "frontend_core_package")
        only = {**contract, "source_artifacts": [package]}
        frontend = Path(self.directory.name) / "frontend"
        with mock.patch.object(alignment, "read_pinned_git_blob", reader), self.assertRaises(ValueError):
            alignment.verify_sources(only, {"core": Path("core"), "frontend": frontend})
        self.assertEqual(calls, [(frontend, contract["sources"]["frontend_core_package"]["revision"], package["path"])])

    def test_v2_enhancer_requires_exact_routes_and_is_rejected_by_older_schema(self) -> None:
        graph = with_enhancer(moss_graph("base"), "TextGenerateV2")
        summary = alignment.summarize_moss_graph(graph, enhancers=V2_ENHANCERS)
        self.assertEqual(summary["prompt_path"][-1], "TextGenerateV2")
        self.assertTrue(summary["prompt_switch"])
        with self.assertRaises(ValueError):
            alignment.summarize_moss_graph(graph)
        for mutation in ("image-name", "image-origin", "image-missing", "unknown-class"):
            changed = with_enhancer(moss_graph("base"), "TextGenerateV2",
                                    image_input="image" if mutation == "image-name" else None)
            if mutation == "image-origin":
                _subgraph(changed)["links"][-1]["origin_id"] = 17
            elif mutation == "image-missing":
                enhancer = _node(changed, 11)
                enhancer["inputs"] = [port for port in enhancer["inputs"] if port["name"] != "images.image1"]
            elif mutation == "unknown-class":
                _node(changed, 11)["type"] = "TextGenerateV3"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                alignment.summarize_moss_graph(changed, enhancers=V2_ENHANCERS)

    def test_moss_changes_classify_resaved_enhancer_seed_and_url_only(self) -> None:
        url = "https://example.invalid/diffusion_models/{}"
        before = add_model_url(add_seed(with_enhancer(moss_graph("sft"), "TextGenerate"), 1), url.format("moss_image_base_int8_convrot.safetensors"))
        after = add_model_url(add_seed(with_enhancer(moss_graph("sft"), "TextGenerateV2", node_id=27), 2), url.format("moss_image_sft_int8_convrot.safetensors"))
        after = renumber_links(after, 500)
        rows = alignment.summarize_moss_changes(before, after)
        self.assertEqual([row["classification"] for row in rows], ["template-seed", "model-download-url", "enhancer-node-class"])
        self.assertEqual(rows[0]["pointer"], "/root/nodes/18/widgets_values/13")
        self.assertEqual(rows[1]["pointer"], "/subgraphs/0/nodes/1/properties/models/0/url")
        self.assertEqual(alignment.summarize_moss_changes(before, renumber_links(before, 7)), [])

    def test_moss_changes_reject_every_other_executable_difference(self) -> None:
        before = add_seed(with_enhancer(moss_graph("base"), "TextGenerate"), 1)
        for mutation in ("slg-default", "sampler-widget", "enhancer-widget", "enhancer-input", "enhancer-mode",
                         "wrong-url-basename", "switch-route", "reverse-migration", "added-node", "subgraph-io"):
            after = with_enhancer(moss_graph("base"), "TextGenerateV2", node_id=34)
            after = add_seed(after, 1)
            source = before
            if mutation == "slg-default":
                after["nodes"][0]["widgets_values"][9] = False
            elif mutation == "sampler-widget":
                _node(after, 7)["widgets_values"][6] = 2
            elif mutation == "enhancer-widget":
                _node(after, 34)["widgets_values"][1] = 512
            elif mutation == "enhancer-input":
                _node(after, 34)["inputs"][0]["name"] = "clip_alt"
            elif mutation == "enhancer-mode":
                _node(after, 34)["mode"] = 4
            elif mutation == "wrong-url-basename":
                source = add_model_url(before, "https://example.invalid/a/moss_image_base_int8_convrot.safetensors")
                after = add_model_url(after, "https://example.invalid/a/other.safetensors")
            elif mutation == "switch-route":
                link = next(link for link in _subgraph(after)["links"] if link["target_id"] == 16 and link["origin_id"] == 34)
                link["origin_slot"] = 1
            elif mutation == "reverse-migration":
                source, after = after, before
            elif mutation == "added-node":
                _subgraph(after)["nodes"].append({"id": 99, "type": "KSampler", "inputs": [], "widgets_values": []})
            else:
                _subgraph(after)["inputs"][0]["type"] = "INT"
            with self.subTest(mutation=mutation), self.assertRaises((ValueError, KeyError)):
                alignment.summarize_moss_changes(source, after)

    def test_text_generate_tripwire_reads_registration_deprecation_and_replacement(self) -> None:
        summary = alignment.summarize_text_generate_sources(TEXTGEN_SOURCE, REPLACEMENT_SOURCE)
        self.assertEqual(summary, {"registered": ["TextGenerateV2", "TextGenerate"],
                                   "deprecated": {"TextGenerate": "TextGenerateV2"},
                                   "replacements": [["TextGenerate", "TextGenerateV2"]]})
        removed = TEXTGEN_SOURCE.replace(b"            TextGenerate,\n", b"")
        self.assertNotIn("TextGenerate", alignment.summarize_text_generate_sources(removed, REPLACEMENT_SOURCE)["registered"])
        self.assertEqual(alignment.summarize_text_generate_sources(TEXTGEN_SOURCE, b"")["replacements"], [])
        self.assertEqual(alignment.summarize_krea2_enhancer(krea2_graph("TextGenerate")), "TextGenerate")
        self.assertEqual(alignment.summarize_krea2_enhancer(krea2_graph("TextGenerateV2")), "TextGenerateV2")
        with self.assertRaises(ValueError):
            alignment.summarize_krea2_enhancer(krea2_graph("StringConcatenate"))

    def test_v2_gallery_labels_are_checked_against_actual_executable_content(self) -> None:
        contract = json.loads(HOST_046.read_bytes())
        contract["legacy_templates"] = []
        contract["legacy_changes"] = {}
        contract["moss_templates"] = {}
        contract["moss_changes"] = {}
        note = {"nodes": [{"id": 1, "type": "MarkdownNote", "widgets_values": ["old"]}], "links": []}
        noted = {"nodes": [{"id": 1, "type": "MarkdownNote", "widgets_values": ["new"]}], "links": []}
        graph = {"nodes": [{"id": 1, "type": "KSampler", "widgets_values": [20]}], "links": []}
        changed = {"nodes": [{"id": 1, "type": "KSampler", "widgets_values": [25]}], "links": []}
        contract["gallery_delta"] = {
            "added": [{"member": "added.json", "classification": "reference-only"}],
            "removed": [{"member": "removed.json", "classification": "reference-only"}],
            "changed": [{"member": "note.json", "classification": "reference-only-note-change"},
                        {"member": "graph.json", "classification": "reference-only-executable-change"}]}
        before_path = Path(self.directory.name) / "before.whl"
        after_path = Path(self.directory.name) / "after.whl"
        write_archive(before_path, {"removed.json": {}, "note.json": note, "graph.json": graph})
        write_archive(after_path, {"added.json": {}, "note.json": noted, "graph.json": changed})
        with zipfile.ZipFile(before_path) as before, zipfile.ZipFile(after_path) as after:
            alignment.verify_template_delta(contract, before, after)
            for index, label in ((0, "reference-only-executable-change"), (1, "reference-only-note-change")):
                wrong = copy.deepcopy(contract)
                wrong["gallery_delta"]["changed"][index]["classification"] = label
                with self.subTest(index=index), self.assertRaises(ValueError):
                    alignment.verify_template_delta(wrong, before, after)

    def test_older_contracts_keep_their_original_verification_rules(self) -> None:
        moss = alignment.load_contract(alignment.MOSS_CONTRACT_PATH)
        self.assertNotIn("moss_changes", moss)
        for mode, item in moss["moss_templates"].items():
            with self.subTest(mode=mode):
                self.assertEqual(item["graph_contract"]["prompt_path"][-1], "TextGenerate")
                self.assertEqual(alignment.summarize_moss_graph(moss_graph(mode)), item["graph_contract"])
        self.assertEqual(alignment.MOSS_CONTRACT_PATH, alignment.ROOT / "tests/fixtures/host_moss_alignment_contract.json")


if __name__ == "__main__":
    unittest.main()
