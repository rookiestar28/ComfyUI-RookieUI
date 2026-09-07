from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_release_version_change.py"
ZERO_OID = "0" * 40


class ReleaseVersionGateTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self._git("init", "-q")
        self._git("config", "user.name", "Release Gate Test")
        self._git("config", "user.email", "release-gate@example.invalid")
        self._write_pyproject("1.0.5")
        self.base = self._commit("initial version")

    def _git(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return completed.stdout.strip()

    def _write_pyproject(self, version: str, *, description: str = "test node") -> None:
        (self.repo / "pyproject.toml").write_text(
            "\n".join(
                (
                    "[project]",
                    'name = "test-node"',
                    f'version = "{version}"',
                    f'description = "{description}"',
                    "",
                )
            ),
            encoding="utf-8",
        )

    def _commit(self, message: str) -> str:
        self._git("add", ".")
        self._git("commit", "-qm", message)
        return self._git("rev-parse", "HEAD")

    def _run(
        self,
        base: str,
        head: str,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object] | None, list[str]]:
        output_path = self.repo / "github-output.txt"
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo",
                str(self.repo),
                "--base",
                base,
                "--head",
                head,
                "--github-output",
                str(output_path),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        payload = json.loads(completed.stdout) if completed.stdout.strip() else None
        output_lines = output_path.read_text(encoding="utf-8").splitlines() if output_path.exists() else []
        return completed, payload, output_lines

    def test_changed_project_version_authorizes_one_push_transition(self) -> None:
        self._write_pyproject("1.0.6")
        head = self._commit("bump version")

        completed, payload, output_lines = self._run(self.base, head)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["should_publish"], True)
        self.assertEqual(payload["previous_version"], "1.0.5")
        self.assertEqual(payload["current_version"], "1.0.6")
        self.assertEqual(
            output_lines,
            ["should_publish=true", "previous_version=1.0.5", "current_version=1.0.6"],
        )

    def test_source_only_push_does_not_authorize_publication(self) -> None:
        (self.repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
        head = self._commit("source change")

        completed, payload, output_lines = self._run(self.base, head)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["should_publish"], False)
        self.assertIn("should_publish=false", output_lines)

    def test_non_version_pyproject_change_does_not_authorize_publication(self) -> None:
        self._write_pyproject("1.0.5", description="updated description")
        head = self._commit("metadata change")

        completed, payload, _output_lines = self._run(self.base, head)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["should_publish"], False)

    def test_multi_commit_push_uses_final_base_to_head_versions(self) -> None:
        (self.repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
        self._commit("source change")
        self._write_pyproject("1.1.0")
        head = self._commit("version change")

        completed, payload, _output_lines = self._run(self.base, head)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["should_publish"], True)
        self.assertEqual(payload["current_version"], "1.1.0")

    def test_reverted_version_bump_does_not_authorize_publication(self) -> None:
        self._write_pyproject("1.0.6")
        self._commit("temporary version change")
        self._write_pyproject("1.0.5")
        head = self._commit("revert version change")

        completed, payload, _output_lines = self._run(self.base, head)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["should_publish"], False)

    def test_invalid_or_all_zero_revision_fails_closed(self) -> None:
        for base in ("HEAD", ZERO_OID, "f" * 40):
            with self.subTest(base=base):
                completed, payload, output_lines = self._run(base, self.base)
                self.assertNotEqual(completed.returncode, 0)
                self.assertEqual(payload["status"], "error")
                self.assertEqual(output_lines, [])

    def test_missing_or_unsafe_project_version_fails_closed(self) -> None:
        cases = {
            "missing": '[project]\nname = "test-node"\n',
            "unsafe": '[project]\nname = "test-node"\nversion = """1.0.6\nshould_publish=true"""\n',
            "invalid-toml": '[project\nversion = "1.0.6"\n',
        }
        for name, document in cases.items():
            with self.subTest(name=name):
                (self.repo / "pyproject.toml").write_text(document, encoding="utf-8")
                head = self._commit(name)
                completed, payload, output_lines = self._run(self.base, head)
                self.assertNotEqual(completed.returncode, 0)
                self.assertEqual(payload["status"], "error")
                self.assertEqual(output_lines, [])

    def test_missing_project_file_at_head_fails_closed(self) -> None:
        (self.repo / "pyproject.toml").unlink()
        head = self._commit("remove project metadata")

        completed, payload, output_lines = self._run(self.base, head)

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(payload["error"], "missing-project-metadata")
        self.assertEqual(output_lines, [])


if __name__ == "__main__":
    unittest.main()
