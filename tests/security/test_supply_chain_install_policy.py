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
