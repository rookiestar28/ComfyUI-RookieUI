import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCANNER_PATH = ROOT / "scripts" / "check_supply_chain_hardening.py"


def load_scanner():
    spec = importlib.util.spec_from_file_location("check_supply_chain_hardening", SCANNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestSupplyChainScanner(unittest.TestCase):
    def test_known_clean_repo_has_no_findings(self):
        scanner = load_scanner()
        findings = scanner.run_checks(ROOT)
        self.assertEqual([], findings)

    def test_affected_npm_package_is_reported(self):
        scanner = load_scanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package-lock.json").write_text(
                json.dumps(
                    {
                        "lockfileVersion": 3,
                        "packages": {
                            "": {"name": "fixture"},
                            "node_modules/@tanstack/router-plugin": {
                                "version": "1.131.0"
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            findings = scanner.run_checks(root)

        self.assertTrue(any("@tanstack/router-plugin" in finding.detail for finding in findings))

    def test_unrelated_lightningcss_package_is_not_reported(self):
        scanner = load_scanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package-lock.json").write_text(
                json.dumps(
                    {
                        "lockfileVersion": 3,
                        "packages": {
                            "": {"name": "fixture"},
                            "node_modules/lightningcss": {"version": "1.30.2"},
                        },
                    }
                ),
                encoding="utf-8",
            )

            findings = scanner.run_checks(root)

        self.assertEqual([], findings)

    def test_affected_python_requirement_is_reported(self):
        scanner = load_scanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requirements.txt").write_text(
                "mistralai==2.4.6\npytorch-lightning==2.6.1\n",
                encoding="utf-8",
            )

            findings = scanner.run_checks(root)

        details = "\n".join(finding.detail for finding in findings)
        self.assertIn("mistralai==2.4.6", details)
        self.assertNotIn("pytorch-lightning==2.6.1", details)

    def test_ioc_file_is_reported(self):
        scanner = load_scanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vscode = root / ".vscode"
            vscode.mkdir()
            (vscode / "tasks.json").write_text(
                '{"label":"Shai-Hulud","command":"router_init.js"}',
                encoding="utf-8",
            )

            findings = scanner.run_checks(root)

        paths = "\n".join(finding.path for finding in findings)
        details = "\n".join(finding.detail for finding in findings)
        self.assertIn(".vscode", paths)
        self.assertIn("router_init.js", details)
