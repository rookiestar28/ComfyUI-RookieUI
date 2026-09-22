from __future__ import annotations

import json
import unittest
from pathlib import Path

from rookieui.contracts import candidate_frontend_155
from rookieui.contracts.host_source_basis import HOST_SOURCE_BASIS


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "frontend_155_candidate_contract.json"


class CandidateFrontend155Tests(unittest.TestCase):
    def test_candidate_keeps_accepted_frontend_separate(self) -> None:
        contract = candidate_frontend_155.load_contract(FIXTURE)
        self.assertEqual(contract.candidate_revision, "07c337679d250b5a7af810adb73e26449fc6e676")
        self.assertEqual(contract.accepted_revision, HOST_SOURCE_BASIS.frontend.revision)
        self.assertEqual(contract.candidate_version, "1.55.12")
        self.assertEqual(len(contract.artifacts), 4)
        paths = {item.path for item in contract.artifacts}
        self.assertIn("src/platform/remote/comfyui/types.ts", paths)
        self.assertIn("src/platform/remote/comfyui/execution/types.ts", paths)
        self.assertNotIn("src/schemas/apiSchema.ts", paths)
        self.assertEqual(candidate_frontend_155.serialize_contract(contract), FIXTURE.read_text(encoding="utf-8"))

    def test_missing_or_tampered_candidate_source_fails(self) -> None:
        contract = candidate_frontend_155.load_contract(FIXTURE)
        artifacts = {item.path: b"x" * item.bytes for item in contract.artifacts}
        with self.assertRaises(ValueError):
            candidate_frontend_155.verify_contract_sources(contract, blob_reader=artifacts.__getitem__)
        artifacts.pop(contract.artifacts[0].path)
        with self.assertRaises(ValueError):
            candidate_frontend_155.verify_contract_sources(contract, blob_reader=artifacts.__getitem__)

    def test_fixture_edits_and_removed_path_fail_closed(self) -> None:
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cases = [
            {**payload, "candidate_revision": "0" * 40},
            {**payload, "artifacts": payload["artifacts"][:-1]},
            {**payload, "artifacts": [{**payload["artifacts"][0], "sha256": "0" * 64}, *payload["artifacts"][1:]]},
            {**payload, "artifacts": [{**payload["artifacts"][0], "path": "src/schemas/apiSchema.ts"}, *payload["artifacts"][1:]]},
            {**payload, "artifacts": [{**payload["artifacts"][0], "path": "../escape.ts"}, *payload["artifacts"][1:]]},
        ]
        for mutated in cases:
            with self.subTest(mutated=mutated), self.assertRaises(ValueError):
                candidate_frontend_155.parse_contract_text(json.dumps(mutated))

    def test_exact_pinned_source_or_fixture_only_public_checkout(self) -> None:
        contract = candidate_frontend_155.load_contract(FIXTURE)
        report = candidate_frontend_155.verify_contract_sources(contract)
        if candidate_frontend_155.DEFAULT_SOURCE_ROOT.is_dir():
            self.assertEqual(report.status, "verified")
            self.assertEqual(report.verified_artifacts, 4)
        else:
            self.assertEqual(report.status, "unavailable-fixture-only")
            self.assertEqual(report.verified_artifacts, 0)


if __name__ == "__main__":
    unittest.main()
