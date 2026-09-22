from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rookieui.contracts import candidate_template_01166
from rookieui.contracts.host_source_basis import HOST_SOURCE_BASIS


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/template_01166_candidate_contract.json"


class CandidateTemplate01166Tests(unittest.TestCase):
    def test_candidate_identity_and_complete_disposition_are_separate(self) -> None:
        contract = candidate_template_01166.load_contract(FIXTURE)
        self.assertEqual(HOST_SOURCE_BASIS.core.workflow_templates_version, "0.11.54")
        self.assertEqual(contract.artifacts["meta"].filename, "comfyui_workflow_templates-0.11.66-py3-none-any.whl")
        self.assertEqual(contract.required_components["comfyui-workflow-templates-json"], "0.1.92")
        self.assertEqual(len(contract.required_components), 8)
        self.assertEqual((contract.old_json_count, contract.new_json_count, contract.unchanged_count), (547, 580, 484))
        self.assertEqual(
            {kind: sum(row.change == kind for row in contract.affected_members) for kind in ("added", "removed", "changed")},
            {"added": 36, "removed": 3, "changed": 60},
        )
        self.assertEqual(len(contract.affected_members), 99)
        self.assertEqual(len(contract.preserved_profiles), 11)
        self.assertEqual(sum(row.profile == "krea2_turbo" for row in contract.preserved_profiles), 1)
        qwen = [row for row in contract.affected_members if "image_qwen_image_2_1_" in row.path]
        self.assertEqual(len(qwen), 3)
        self.assertTrue(all(row.disposition == "pending" for row in qwen))
        self.assertFalse(any(row.disposition == "supported" for row in contract.affected_members))
        self.assertEqual(candidate_template_01166.serialize_contract(contract), FIXTURE.read_text(encoding="utf-8"))

    def test_mutated_artifact_component_disposition_and_member_fail_closed(self) -> None:
        text = FIXTURE.read_text(encoding="utf-8")
        payload = json.loads(text)
        cases = {
            "duplicate": text.replace('  "schema_version":', '  "schema_version": "duplicate",\n  "schema_version":', 1),
            "wrong-artifact": json.dumps({**payload, "artifacts": {**payload["artifacts"], "json": {**payload["artifacts"]["json"], "sha256": "0" * 64}}}),
            "unresolved-component": json.dumps({**payload, "required_components": {**payload["required_components"], "comfyui-workflow-templates-media-image": "0.0.0"}}),
            "missing-component": json.dumps({**payload, "required_components": {k: v for k, v in payload["required_components"].items() if k != "comfyui-workflow-templates-media-image"}}),
            "premature-support": json.dumps({**payload, "affected_members": [{**payload["affected_members"][0], "disposition": "supported"}, *payload["affected_members"][1:]]}),
            "missing-member": json.dumps({**payload, "affected_members": payload["affected_members"][:-1]}),
            "wrong-qwen-path": json.dumps({**payload, "qwen_members": {**payload["qwen_members"], "edit": "templates/wrong.json"}}),
        }
        for name, changed in cases.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                candidate_template_01166.parse_contract_text(changed)

    def test_exact_wheels_delta_existing_profiles_and_qwen_git_match(self) -> None:
        contract = candidate_template_01166.load_contract(FIXTURE)
        report = candidate_template_01166.verify_candidate(contract)
        if candidate_template_01166.DEFAULT_ARTIFACT_ROOT.is_dir():
            self.assertEqual(report.status, "verified")
            self.assertEqual((report.artifacts, report.affected, report.preserved_profiles, report.qwen_git_matches, report.core_blueprints), (4, 99, 11, 3, 15))
        else:
            self.assertEqual(report.status, "unavailable-fixture-only")
        with tempfile.TemporaryDirectory() as directory:
            empty = candidate_template_01166.verify_candidate(contract, artifact_root=Path(directory) / "absent")
        self.assertEqual(empty.status, "unavailable-fixture-only")
        self.assertEqual(empty.artifacts, 0)

    def test_corrupted_or_incomplete_wheel_is_not_accepted(self) -> None:
        contract = candidate_template_01166.load_contract(FIXTURE)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / contract.artifacts["meta"].filename).write_bytes(b"not a wheel")
            with self.assertRaises(ValueError):
                candidate_template_01166.verify_candidate(contract, artifact_root=root)


if __name__ == "__main__":
    unittest.main()
