from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rookieui.contracts import candidate_core_037
from rookieui.contracts.host_source_basis import HOST_SOURCE_BASIS


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "core_037_candidate_contract.json"


class CandidateCore037Tests(unittest.TestCase):
    def test_candidate_is_separate_from_accepted_basis(self) -> None:
        contract = candidate_core_037.load_contract(FIXTURE)
        self.assertEqual(contract.candidate_revision, "e638023d54497dbe0579565e5de4bb7076899592")
        self.assertEqual(contract.accepted_revision, HOST_SOURCE_BASIS.core.revision)
        self.assertEqual(contract.core_version, "0.37.0")
        self.assertEqual(
            dict(contract.components),
            {"embedded_docs": "0.5.12", "frontend_package": "1.53.6", "workflow_templates": "0.11.66"},
        )
        self.assertEqual(len(contract.blueprint_profiles), 15)
        self.assertEqual(len(contract.source_artifacts), 9)
        self.assertEqual(
            candidate_core_037.serialize_contract(contract),
            FIXTURE.read_text(encoding="utf-8"),
        )
        self.assertNotEqual(contract.candidate_revision, HOST_SOURCE_BASIS.core.revision)

    def test_qwen_node_contract_and_missing_node_readiness(self) -> None:
        contract = candidate_core_037.load_contract(FIXTURE)
        self.assertEqual(
            contract.qwen_encoder_inputs,
            ("clip", "prompt", "negative_prompt", "vae", "resolution", "images"),
        )
        self.assertEqual(contract.qwen_encoder_outputs, ("CONDITIONING", "CONDITIONING", "LATENT"))
        self.assertEqual(contract.qwen_reference_slots, 16)
        self.assertEqual(contract.qwen_latent_channels, 64)
        self.assertEqual(contract.qwen_latent_stride, 16)
        self.assertEqual(contract.qwen_resolution_default, 1024)
        self.assertEqual(contract.qwen_resolution_min, 0)
        self.assertEqual(contract.qwen_resolution_max, 4096)
        self.assertEqual(contract.qwen_resolution_step, 32)

        txt_nodes = candidate_core_037.required_nodes("txt2img")
        edit_nodes = candidate_core_037.required_nodes("edit")
        self.assertIn("TextEncodeQwenImage21", txt_nodes)
        self.assertIn("QwenImage21Cache", edit_nodes)
        self.assertNotIn("QwenImage21Cache", txt_nodes)
        self.assertEqual(candidate_core_037.missing_required_nodes(txt_nodes, "txt2img"), ())
        self.assertEqual(
            candidate_core_037.missing_required_nodes(txt_nodes - {"TextEncodeQwenImage21"}, "txt2img"),
            ("TextEncodeQwenImage21",),
        )
        with self.assertRaises(ValueError):
            candidate_core_037.required_nodes("unknown")
        with self.assertRaises(TypeError):
            candidate_core_037.missing_required_nodes(None, "edit")

    def test_mutated_schema_type_slot_hash_and_paths_fail_closed(self) -> None:
        original = FIXTURE.read_text(encoding="utf-8")
        payload = json.loads(original)
        cases = {
            "duplicate-key": original.replace('  "schema_version":', '  "schema_version": "duplicate",\n  "schema_version":', 1),
            "unknown-key": json.dumps({**payload, "unknown": True}),
            "wrong-revision": json.dumps({**payload, "candidate_revision": "0" * 40}),
            "wrong-output-slot": json.dumps({**payload, "qwen_encoder_outputs": ["CONDITIONING", "LATENT", "CONDITIONING"]}),
            "wrong-input": json.dumps({**payload, "qwen_encoder_inputs": payload["qwen_encoder_inputs"][:-1]}),
            "wrong-hash": json.dumps({**payload, "source_artifacts": [{**payload["source_artifacts"][0], "sha256": "0" * 64}, *payload["source_artifacts"][1:]]}),
            "unsafe-path": json.dumps({**payload, "source_artifacts": [{**payload["source_artifacts"][0], "path": "../outside.py"}, *payload["source_artifacts"][1:]]}),
            "missing-source": json.dumps({**payload, "source_artifacts": payload["source_artifacts"][:-1]}),
            "missing-profile": json.dumps({**payload, "blueprint_profiles": payload["blueprint_profiles"][:-1]}),
        }
        for name, text in cases.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                candidate_core_037.parse_contract_text(text)

    def test_exact_pinned_source_and_all_blueprint_semantics(self) -> None:
        contract = candidate_core_037.load_contract(FIXTURE)
        report = candidate_core_037.verify_contract_sources(contract)
        if candidate_core_037.DEFAULT_SOURCE_ROOT.is_dir():
            self.assertEqual(report.status, "verified")
            self.assertEqual(report.verified_artifacts, 9)
            self.assertEqual(report.verified_blueprints, 15)
            self.assertEqual(report.runtime_facts, "verified")
        else:
            self.assertEqual(report.status, "unavailable-fixture-only")
            self.assertEqual(report.verified_artifacts, 0)
            self.assertEqual(report.verified_blueprints, 0)

        with tempfile.TemporaryDirectory() as directory:
            missing = candidate_core_037.verify_contract_sources(
                contract, source_root=Path(directory) / "absent"
            )
        self.assertEqual(missing.status, "unavailable-fixture-only")
        self.assertEqual(missing.verified_artifacts, 0)
        self.assertEqual(missing.verified_blueprints, 0)


if __name__ == "__main__":
    unittest.main()
