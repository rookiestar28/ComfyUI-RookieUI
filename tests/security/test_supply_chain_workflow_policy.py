import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"


def read_workflow(name: str) -> str:
    return (WORKFLOW_ROOT / name).read_text(encoding="utf-8")


class TestSupplyChainWorkflowPolicy(unittest.TestCase):
    def test_dependency_review_gate_is_present_for_dependency_diffs(self):
        text = read_workflow("dependency-review.yml")
        self.assertIn("pull_request:", text)
        self.assertIn("contents: read", text)
        self.assertRegex(
            text,
            re.compile(r"uses: actions/dependency-review-action@[a-f0-9]{40}\b"),
        )

    def test_publish_workflow_pins_token_bearing_action(self):
        text = read_workflow("publish.yml")
        self.assertIn("personal_access_token: ${{ secrets.REGISTRY_ACCESS_TOKEN }}", text)
        self.assertRegex(
            text,
            re.compile(r"uses: Comfy-Org/publish-node-action@[a-f0-9]{40}\b"),
        )
        self.assertNotIn("Comfy-Org/publish-node-action@v1", text)

    def test_workflows_do_not_use_high_risk_triggers_or_oidc(self):
        for path in WORKFLOW_ROOT.glob("*.yml"):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotIn("pull_request_target:", text)
                self.assertNotRegex(text, re.compile(r"id-token:\s*write\b"))
