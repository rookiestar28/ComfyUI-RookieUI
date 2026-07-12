import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


def read_json(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split(".")[:3])


class DependencyAdvisoryPolicyTests(unittest.TestCase):
    def test_locked_and_installed_ws_are_patched_without_root_override(self):
        package_json = read_json("package.json")
        lockfile = read_json("package-lock.json")
        installed = read_json("node_modules/ws/package.json")

        self.assertNotIn("overrides", package_json)
        locked_ws = lockfile["packages"]["node_modules/ws"]["version"]
        self.assertGreaterEqual(version_tuple(locked_ws), (8, 21, 0))
        self.assertEqual(installed["version"], locked_ws)

    def test_audit_script_uses_complete_graph_and_high_threshold(self):
        package_json = read_json("package.json")

        self.assertEqual(
            package_json["scripts"].get("audit:ci"),
            "npm audit --audit-level=high",
        )

    def test_full_wrappers_run_advisory_gate_before_frontend_tests(self):
        wrapper_paths = (
            "scripts/run_full_tests_windows.ps1",
            "scripts/pre_push_checks.sh",
        )
        for path in wrapper_paths:
            with self.subTest(path=path):
                text = (ROOT / path).read_text(encoding="utf-8")
                audit_index = text.index("npm run audit:ci")
                frontend_test_index = text.index("npm run test:types")
                self.assertLess(audit_index, frontend_test_index)

        ci_text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        linux_text = (ROOT / "scripts/run_full_tests_linux.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("bash scripts/run_full_tests_linux.sh", ci_text)
        self.assertIn("bash scripts/pre_push_checks.sh", linux_text)

    def test_audit_commands_forbid_policy_bypasses(self):
        forbidden = (
            "--omit",
            "--only=prod",
            "--production",
            "--force",
            "--audit=false",
            "--no-audit",
            "--audit-level=critical",
            "continue-on-error",
            "|| true",
            "; true",
        )
        paths = (
            "package.json",
            "scripts/run_full_tests_windows.ps1",
            "scripts/pre_push_checks.sh",
        )
        audit_lines = []
        for path in paths:
            text = (ROOT / path).read_text(encoding="utf-8")
            audit_lines.extend(line.lower() for line in text.splitlines() if "audit" in line)

        policy_text = "\n".join(audit_lines)
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, policy_text)


if __name__ == "__main__":
    unittest.main()
