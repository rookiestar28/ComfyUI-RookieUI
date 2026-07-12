from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

INSTALL_POLICY_FILES = (
    ".github/workflows/ci.yml",
    "scripts/pre_push_checks.sh",
    "scripts/run_full_tests_windows.ps1",
    "tests/TEST_SOP.md",
    "tests/E2E_TESTING_SOP.md",
)


def read_repo_file(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class TestSupplyChainInstallPolicy(unittest.TestCase):
    def test_validation_paths_use_lockfile_frozen_npm_ci(self):
        for path in INSTALL_POLICY_FILES:
            with self.subTest(path=path):
                text = read_repo_file(path)
                self.assertIn("npm ci", text)
                self.assertNotIn("npm install", text)

    def test_full_validation_wrappers_verify_dependency_identity_before_tests(self):
        wrapper_paths = (
            "scripts/run_full_tests_windows.ps1",
            "scripts/pre_push_checks.sh",
        )
        for path in wrapper_paths:
            with self.subTest(path=path):
                text = read_repo_file(path)
                self.assertIn("verify_node_modules_lock.mjs", text)
                self.assertNotIn("node_modules\\@playwright\\test\\package.json", text)
                self.assertNotIn("node_modules/@playwright/test/package.json", text)

        bash_text = read_repo_file("scripts/pre_push_checks.sh")
        self.assertGreaterEqual(bash_text.count("verify_npm_deps"), 3)

        powershell_text = read_repo_file("scripts/run_full_tests_windows.ps1")
        self.assertGreaterEqual(
            powershell_text.count("verify_node_modules_lock.mjs"),
            2,
        )
