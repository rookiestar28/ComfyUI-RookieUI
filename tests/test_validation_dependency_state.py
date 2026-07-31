import json
import os
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
                    "node_modules/vitest": {"version": "4.1.0", "bin": {"vitest": "vitest.mjs"}},
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
        shim_suffix = ".cmd" if os.name == "nt" else ""
        shim = root / "node_modules" / ".bin" / f"vitest{shim_suffix}"
        shim.parent.mkdir(parents=True, exist_ok=True)
        shim.write_text("@echo off\n" if shim_suffix else "#!/bin/sh\n", encoding="utf-8")
        if not shim_suffix:
            shim.chmod(0o755)
        return root

    def _add_platform_native_fixture(self, root: Path, *, installed: bool) -> str:
        details = json.loads(
            subprocess.check_output(
                [
                    "node",
                    "-e",
                    (
                        "const h=process.report.getReport().header;"
                        "console.log(JSON.stringify({platform:process.platform,arch:process.arch,"
                        "libc:h.glibcVersionRuntime?'gnu':'musl'}))"
                    ),
                ],
                cwd=ROOT,
                text=True,
            )
        )
        platform_name = details["platform"]
        arch = details["arch"]
        if platform_name == "win32":
            package_name = f"@rolldown/binding-win32-{arch}-msvc"
        elif platform_name == "linux":
            package_name = f"@rolldown/binding-linux-{arch}-{details['libc']}"
        elif platform_name == "darwin":
            package_name = f"@rolldown/binding-darwin-{arch}"
        else:
            self.skipTest(f"platform-native verifier fixture is unavailable for {platform_name}/{arch}")

        lock_path = root / "package-lock.json"
        lockfile = json.loads(lock_path.read_text(encoding="utf-8"))
        lockfile["packages"][f"node_modules/{package_name}"] = {
            "version": "1.0.3",
            "optional": True,
            "os": [platform_name],
            "cpu": [arch],
        }
        self._write_json(lock_path, lockfile)
        if installed:
            self._write_json(
                root / "node_modules" / Path(*package_name.split("/")) / "package.json",
                {"name": package_name, "version": "1.0.3"},
            )
        return package_name

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
        self.assertIn("3 declared dependencies, 1 executable shims", result.stdout)

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

    def test_missing_platform_native_optional_dependency_fails(self):
        root = self._build_fixture()
        package_name = self._add_platform_native_fixture(root, installed=False)

        result = self._run_verifier(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(package_name, result.stderr)
        self.assertIn("platform-native", result.stderr)

    def test_missing_current_platform_executable_shim_fails(self):
        root = self._build_fixture()
        shim_suffix = ".cmd" if os.name == "nt" else ""
        (root / "node_modules" / ".bin" / f"vitest{shim_suffix}").unlink()

        result = self._run_verifier(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("vitest", result.stderr)
        self.assertIn("executable shim", result.stderr)


if __name__ == "__main__":
    unittest.main()
