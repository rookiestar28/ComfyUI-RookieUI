import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts" / "verify_node_modules_lock.mjs"


class ValidationDependencyStateTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(VERIFIER.is_file(), "dependency-state verifier is required")

    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _build_fixture(self, *, installed_vitest: str = "4.1.0") -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        self._write_json(
            root / "package.json",
            {
                "dependencies": {"vue": "^3.5.22"},
                "devDependencies": {
                    "@playwright/test": "^1.54.1",
                    "vitest": "^4.1.0",
                },
            },
        )
        self._write_json(
            root / "package-lock.json",
            {
                "lockfileVersion": 3,
                "packages": {
                    "": {},
                    "node_modules/vue": {"version": "3.5.22"},
                    "node_modules/@playwright/test": {"version": "1.54.1"},
                    "node_modules/vitest": {"version": "4.1.0"},
                },
            },
        )
        self._write_json(
            root / "node_modules" / "vue" / "package.json",
            {"name": "vue", "version": "3.5.22"},
        )
        self._write_json(
            root / "node_modules" / "@playwright" / "test" / "package.json",
            {"name": "@playwright/test", "version": "1.54.1"},
        )
        self._write_json(
            root / "node_modules" / "vitest" / "package.json",
            {"name": "vitest", "version": installed_vitest},
        )
        return root

    def _run_verifier(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["node", str(VERIFIER), "--root", str(root)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_matching_declared_dependencies_pass_including_scoped_packages(self):
        result = self._run_verifier(self._build_fixture())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("3 declared dependencies match package-lock.json", result.stdout)

    def test_installed_version_mismatch_fails_with_actionable_versions(self):
        result = self._run_verifier(self._build_fixture(installed_vitest="3.2.4"))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("vitest", result.stderr)
        self.assertIn("locked=4.1.0", result.stderr)
        self.assertIn("installed=3.2.4", result.stderr)

    def test_missing_installed_dependency_fails(self):
        root = self._build_fixture()
        (root / "node_modules" / "vue" / "package.json").unlink()

        result = self._run_verifier(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("vue", result.stderr)
        self.assertIn("installed=missing", result.stderr)


if __name__ == "__main__":
    unittest.main()
