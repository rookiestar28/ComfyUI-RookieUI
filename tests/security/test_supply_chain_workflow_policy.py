import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"


def read_workflow(name: str) -> str:
    return (WORKFLOW_ROOT / name).read_text(encoding="utf-8")


def read_job_block(workflow_text: str, job_id: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(job_id)}:\s*$.*?(?=^  [a-zA-Z0-9_-]+:\s*$|\Z)",
        workflow_text,
    )
    if match is None:
        raise AssertionError(f"Workflow job not found: {job_id}")
    return match.group(0)


class TestSupplyChainWorkflowPolicy(unittest.TestCase):
    def test_dependency_review_gate_is_present_for_dependency_diffs(self):
        text = read_workflow("dependency-review.yml")
        self.assertIn("pull_request:", text)
        self.assertIn("contents: read", text)
        self.assertRegex(
            text,
            re.compile(r"uses: actions/dependency-review-action@[a-f0-9]{40}\b"),
        )

    def test_registry_publish_is_downstream_of_the_exact_ci_gate(self):
        self.assertFalse(
            (WORKFLOW_ROOT / "publish.yml").exists(),
            "Registry publishing must not have an independently triggered workflow.",
        )

        text = read_workflow("ci.yml")
        publish_job = read_job_block(text, "publish-node")

        self.assertIn("needs: full-test-gate", publish_job)
        self.assertIn("github.event_name == 'push'", publish_job)
        self.assertIn("github.ref == 'refs/heads/main'", publish_job)
        self.assertIn(
            "github.repository == 'rookiestar28/ComfyUI-RookieUI'",
            publish_job,
        )
        self.assertNotIn("always()", publish_job)
        self.assertNotIn("actions/download-artifact", publish_job)
        self.assertNotRegex(publish_job, re.compile(r"^\s+ref:\s", re.MULTILINE))

    def test_ci_publish_job_pins_token_bearing_action_and_limits_permissions(self):
        publish_job = read_job_block(read_workflow("ci.yml"), "publish-node")

        self.assertIn("contents: read", publish_job)
        self.assertIn("issues: write", publish_job)
        self.assertIn(
            "personal_access_token: ${{ secrets.REGISTRY_ACCESS_TOKEN }}",
            publish_job,
        )
        self.assertRegex(
            publish_job,
            re.compile(r"uses: Comfy-Org/publish-node-action@[a-f0-9]{40}\b"),
        )
        self.assertNotIn("Comfy-Org/publish-node-action@v1", publish_job)

    def test_workflows_do_not_use_high_risk_triggers_or_oidc(self):
        for path in WORKFLOW_ROOT.glob("*.yml"):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotIn("pull_request_target:", text)
                self.assertNotRegex(text, re.compile(r"id-token:\s*write\b"))
