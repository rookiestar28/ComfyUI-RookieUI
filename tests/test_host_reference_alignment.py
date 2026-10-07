from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rookieui.contracts.models import ModelInventorySnapshot
from rookieui.services.img2img import normalize_img2img_request
from rookieui.services.queue_snapshot import _extract_output_filenames
from rookieui.services.txt2img import normalize_txt2img_request
from rookieui.services.workflow_translation import translate_img2img_request, translate_txt2img_request
from scripts.verify_host_reference_alignment import (
    CONTRACT_PATH, ROOT, executable_projection, load_contract, verify_distributions, verify_sources,
)


class HostReferenceAlignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        (ROOT / ".tmp").mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=ROOT / ".tmp")
        self.addCleanup(self.directory.cleanup)
        self.contract = load_contract()

    def test_frozen_source_subject_distinguishes_standalone_frontend_and_core_package(self) -> None:
        self.assertEqual(self.contract["sources"]["core"]["version"], "0.39.0")
        self.assertEqual(self.contract["sources"]["frontend"]["version"], "1.57.0")
        self.assertEqual(self.contract["core_components"]["comfyui-frontend-package"], "1.53.10")
        self.assertEqual(self.contract["core_components"]["comfyui-workflow-templates"], "0.11.76")
        self.assertEqual(self.contract["template_components"]["comfyui-workflow-templates-json"], "0.1.102")
        self.assertEqual(len(self.contract["source_artifacts"]), 34)
        for kind, item in self.contract["qwen_templates"].items():
            with self.subTest(kind=kind):
                graph = item["graph_contract"]
                self.assertEqual(graph["prompt_switch"], ["ComfySwitchNode", False, False])
                self.assertEqual(graph["direct_prompt"], ["GraphInput", "prompt"])
                self.assertEqual(graph["enhanced_prompt"], ["TextGenerate", 0])
                self.assertNotEqual(graph["encoder_loader"][0], graph["enhancer_loader"][0])
                self.assertEqual(graph["sampler_defaults"], [25, 1, "euler", "simple", 1])

    def test_manifest_rejects_unsafe_incomplete_and_ambiguous_subjects(self) -> None:
        variants = []
        for change in ("path", "revision", "coverage", "duplicate", "scope", "unknown"):
            data = copy.deepcopy(self.contract)
            if change == "path":
                data["source_artifacts"][0]["path"] = "../outside.py"
            elif change == "revision":
                data["sources"]["core"]["revision"] = "HEAD"
            elif change == "coverage":
                data["qwen_templates"].pop("edit")
            elif change == "duplicate":
                data["source_artifacts"].append(data["source_artifacts"][0])
            elif change == "scope":
                data["scope"] = "live-qualified"
            else:
                data["unknown"] = True
            variants.append(json.dumps(data))
        variants += ["[]", CONTRACT_PATH.read_text(encoding="utf-8").replace(
            '"scope": "source-contract-only"', '"scope": "source-contract-only", "scope": "other"', 1)]
        path = Path(self.directory.name) / "contract.json"
        for text in variants:
            with self.subTest(variant=variants.index(text)), self.assertRaises(ValueError):
                path.write_text(text, encoding="utf-8")
                load_contract(path)

    def test_source_absence_and_modified_bytes_never_become_fixture_only_success(self) -> None:
        absent = Path(self.directory.name) / "absent"
        with self.assertRaises(ValueError):
            verify_sources(self.contract, {"core": absent, "frontend": absent})
        with self.assertRaisesRegex(ValueError, "bytes drifted"):
            verify_sources(self.contract, {}, blob_reader=lambda _source, _path: b"changed")
        with self.assertRaises(FileNotFoundError):
            verify_distributions(self.contract, absent)

    def test_cli_returns_nonzero_when_source_is_unavailable(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/verify_host_reference_alignment.py"),
             "--core", self.directory.name, "--frontend", self.directory.name,
             "--artifacts", self.directory.name], capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("NOT_VERIFIED", result.stdout)
        self.assertNotIn(self.directory.name, result.stdout)
        self.assertNotIn('"status": "verified"', result.stdout)

    def test_note_projection_keeps_executable_defaults_and_links(self) -> None:
        original = {"nodes": [{"id": 1, "type": "KSampler", "widgets_values": [25]},
                              {"id": 2, "type": "MarkdownNote", "widgets_values": ["old note"]}],
                    "links": [[1, 1, 0, 3, 0]]}
        changed = copy.deepcopy(original)
        changed["nodes"][1]["widgets_values"] = ["new note"]
        self.assertEqual(executable_projection(original), executable_projection(changed))
        changed["nodes"][0]["widgets_values"] = [20]
        self.assertNotEqual(executable_projection(original), executable_projection(changed))
        changed = copy.deepcopy(original)
        changed["links"][0][2] = 1
        self.assertNotEqual(executable_projection(original), executable_projection(changed))

    def test_basic_generated_qwen_graphs_match_current_roles_slots_and_defaults(self) -> None:
        for kind in ("txt2img", "edit"):
            contract = self.contract["qwen_templates"][kind]["graph_contract"]
            inventory = ModelInventorySnapshot(source="host", diffusion_models=[contract["model"]],
                                               text_encoders=[contract["encoder_loader"][0], contract["enhancer_loader"][0]],
                                               vae=[contract["vae"]])
            payload = {"profile": "qwen_image_21" if kind == "txt2img" else "qwen_image_21_edit",
                       "prompt": "(literal:1.2)", "seed": 42}
            with self.subTest(kind=kind):
                if kind == "txt2img":
                    with mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=inventory):
                        request = normalize_txt2img_request(payload)
                    translation = translate_txt2img_request(request)
                else:
                    payload["reference_images"] = [{"image_asset": "synthetic.png"}]
                    with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=inventory), \
                            mock.patch("rookieui.services.img2img.resolve_asset_path", return_value=Path("synthetic.png")):
                        request = normalize_img2img_request(payload)
                    translation = translate_img2img_request(request)
                by_class = {node["class_type"]: (key, node["inputs"]) for key, node in translation.workflow.items()}
                self.assertNotIn("TextGenerate", by_class)
                self.assertEqual(by_class["CLIPLoader"][1]["clip_name"], contract["encoder_loader"][0])
                self.assertEqual(by_class["CLIPLoader"][1]["type"], contract["encoder_loader"][1])
                encode_id, encode = by_class["TextEncodeQwenImage21"]
                self.assertEqual(encode["prompt"], payload["prompt"])
                self.assertEqual(encode["resolution"], contract["resolution"])
                sampler = by_class["KSampler"][1]
                self.assertEqual(sampler["positive"], [encode_id, contract["positive"][1]])
                self.assertEqual(sampler["negative"], [encode_id, contract["negative"][1]])
                self.assertEqual([sampler[key] for key in ("steps", "cfg", "sampler_name", "scheduler", "denoise")],
                                 contract["sampler_defaults"])

    def test_enriched_media_fields_do_not_replace_canonical_output_selectors(self) -> None:
        images = [{"filename": "synthetic.png", "subfolder": "", "type": "output"}]
        ordinary = _extract_output_filenames({"7": {"images": images}})
        enriched = _extract_output_filenames({"7": {"images": [{**images[0], "id": "opaque-id",
                    "metadata": {"kind": "image", "width": 128, "height": 96}}]}})
        self.assertEqual(enriched, ordinary)
        self.assertEqual(enriched, (["synthetic.png"], ["synthetic.png"]))


if __name__ == "__main__":
    unittest.main()
