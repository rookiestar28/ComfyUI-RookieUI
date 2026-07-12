from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from rookieui.contracts.host_source_basis import HOST_SOURCE_BASIS
from scripts.run_current_host_contract_lane import (
    REQUIRED_CASE_IDS,
    build_lane_commands,
    load_and_validate_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tests" / "fixtures" / "current_host_risk_contract.json"
CI_PATH = ROOT / ".github" / "workflows" / "ci.yml"


class CurrentHostContractLaneTests(unittest.TestCase):
    def test_manifest_pins_exact_source_basis_and_artifacts(self) -> None:
        report = load_and_validate_manifest(MANIFEST_PATH)
        self.assertEqual(report["fixture_version"], "current-host-risk-lane-v1")
        self.assertEqual(report["sources"]["core"], HOST_SOURCE_BASIS.core.revision)
        self.assertEqual(report["sources"]["frontend"], HOST_SOURCE_BASIS.frontend.revision)
        self.assertEqual(report["sources"]["desktop"], HOST_SOURCE_BASIS.desktop.revision)
        self.assertEqual(set(report["case_ids"]), REQUIRED_CASE_IDS)

        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        artifacts = manifest["source_artifacts"]
        self.assertEqual(len(artifacts), 5)
        for artifact in artifacts:
            self.assertRegex(artifact["sha256"], re.compile(r"^[0-9a-f]{64}$"))
            self.assertGreater(artifact["bytes"], 0)
            self.assertIn(artifact["source"], {"core", "frontend"})

    def test_lane_commands_are_targeted_and_include_no_inference(self) -> None:
        commands = build_lane_commands(ROOT)
        rendered = "\n".join(" ".join(command) for command in commands)
        self.assertIn("tests.test_prompt_submission", rendered)
        self.assertIn("tests.test_route_deployment_boundary", rendered)
        self.assertIn("rookieui_runtime_lifecycle.test.js", rendered)
        self.assertIn("sidebar_lifecycle.spec.js", rendered)
        self.assertNotIn("run_live_smoke_tests", rendered)
        self.assertNotIn("model", rendered.lower())

    def test_ci_requires_lane_before_full_gate_and_publish(self) -> None:
        workflow = CI_PATH.read_text(encoding="utf-8")
        lane_marker = "Run required current-host contract lane"
        full_marker = "Run full test gate"
        self.assertIn(lane_marker, workflow)
        self.assertLess(workflow.index(full_marker), workflow.index(lane_marker))
        self.assertIn(".venv/bin/python scripts/run_current_host_contract_lane.py", workflow)
        self.assertRegex(workflow, re.compile(r"publish-node:[\s\S]+needs: full-test-gate"))


if __name__ == "__main__":
    unittest.main()
