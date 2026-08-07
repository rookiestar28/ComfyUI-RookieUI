from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.check_public_release_boundary import (
    find_forbidden_tracked_content,
    find_forbidden_tracked_entries,
    inspect_boundary,
)


class PublicReleaseBoundaryTests(unittest.TestCase):
    @staticmethod
    def _run_cli(
        *args: str, root: Path | None = None
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        root = root or Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, str(root / "scripts" / "check_public_release_boundary.py"), *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
        )
        report_line = next(
            line for line in completed.stdout.splitlines() if line.startswith("[public-release-boundary] ")
        )
        return completed, json.loads(report_line.split(" ", 1)[1])

    def _new_repo(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Boundary Test"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "boundary@example.invalid"], cwd=root, check=True)
        return root

    @staticmethod
    def _git(root: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)

    def test_allows_normal_public_source_and_documentation(self) -> None:
        entries = [
            ("100644", "rookieui/api/routes.py"),
            ("100644", "docs/usage.md"),
            ("100755", "scripts/check_public_release_boundary.py"),
        ]
        self.assertEqual(find_forbidden_tracked_entries(entries), [])

    def test_rejects_internal_reference_session_and_roadmap_paths(self) -> None:
        entries = [
            ("100644", ".planning/private.md"),
            ("100644", "REFERENCE/docs/source.md"),
            ("100644", "nested/.sessions/runtime.md"),
            ("100644", "ROADMAP.md"),
        ]
        violations = find_forbidden_tracked_entries(entries)
        self.assertEqual([entry["path"] for entry in violations], [path for _mode, path in entries])

    def test_rejects_tracked_symlinks_as_archive_boundary_bypasses(self) -> None:
        violations = find_forbidden_tracked_entries([("120000", "docs/external-link")])
        self.assertEqual(violations, [{"path": "docs/external-link", "reason": "tracked-symlink"}])

    def test_rejects_internal_item_codes_in_tracked_text(self) -> None:
        private_code = b"F" + b"999"
        violations = find_forbidden_tracked_content(
            [("rookieui/contracts/public_payload.py", b'item_id = "' + private_code + b'"\n')]
        )

        self.assertEqual(
            violations,
            [{"path": "rookieui/contracts/public_payload.py", "reason": "internal-item-code"}],
        )

    def test_content_scan_allows_public_slugs_and_skips_binary_assets(self) -> None:
        self.assertEqual(
            find_forbidden_tracked_content(
                [
                    ("rookieui/contracts/public_payload.py", b'feature_id = "parser_modes"\n'),
                    ("assets/example.bin", b"\x00F999\x01"),
                ]
            ),
            [],
        )

    def test_ci_runs_boundary_after_host_lane_before_publish_job_can_succeed(self) -> None:
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertLess(workflow.index("Run required current-host contract lane"), workflow.index("Verify public release boundary"))
        self.assertIn(".venv/bin/python scripts/check_public_release_boundary.py", workflow)
        self.assertIn("needs: full-test-gate", workflow)

    def test_historical_tree_detects_forbidden_content_without_checkout(self) -> None:
        root = self._new_repo()
        scripts = root / "scripts"
        scripts.mkdir()
        shutil.copy2(
            Path(__file__).resolve().parents[1] / "scripts" / "check_public_release_boundary.py",
            scripts / "check_public_release_boundary.py",
        )

        source = root / "public.py"
        source.write_text('feature_name = "public"\n', encoding="utf-8")
        self._git(root, "add", "public.py")
        self._git(root, "commit", "-qm", "initial public tree")

        private_code = "F" + "999"
        source.write_text(f'private_marker = "{private_code}"\n', encoding="utf-8")
        self._git(root, "add", "public.py")
        self._git(root, "commit", "-qm", "historical forbidden tree")
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, encoding="utf-8"
        ).strip()

        source.write_text('feature_name = "public again"\n', encoding="utf-8")
        self._git(root, "add", "public.py")
        self._git(root, "commit", "-qm", "current clean tree")
        before_head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, encoding="utf-8"
        ).strip()
        self.assertNotEqual(revision, before_head)

        completed, report = self._run_cli("--tree-ish", revision, root=root)

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(report["inspection_mode"], "tree")
        self.assertEqual(report["requested_revision"], revision)
        self.assertEqual(report["status"], "failed")
        self.assertIn("internal-item-code", {entry["reason"] for entry in report["violations"]})
        self.assertEqual(
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True, encoding="utf-8"
            ).strip(),
            before_head,
        )

    def test_tree_mode_reports_resolved_head_identity(self) -> None:
        completed, report = self._run_cli("--tree-ish", "HEAD")
        expected_tree = subprocess.check_output(
            ["git", "rev-parse", "--verify", "HEAD^{tree}"], text=True, encoding="utf-8"
        ).strip()

        self.assertEqual(completed.returncode, 0)
        self.assertEqual(report["inspection_mode"], "tree")
        self.assertEqual(report["requested_revision"], "HEAD")
        self.assertEqual(report["resolved_tree"], expected_tree)
        self.assertEqual(report["status"], "passed")

    def test_invalid_tree_target_fails_closed(self) -> None:
        completed, report = self._run_cli("--tree-ish", "definitely-not-a-valid-revision")

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(report["inspection_mode"], "tree")
        self.assertEqual(report["status"], "error")
        self.assertEqual(report["error"], "invalid-tree-ish")

    def test_index_mode_reports_an_immutable_state_identifier(self) -> None:
        completed, report = self._run_cli("--index")

        self.assertEqual(completed.returncode, 0)
        self.assertEqual(report["inspection_mode"], "index")
        self.assertRegex(str(report["state_identifier"]), r"^index-sha256:[0-9a-f]{64}$")

    def test_full_gate_wrappers_require_committed_tree_boundary_scan(self) -> None:
        root = Path(__file__).resolve().parents[1]
        windows_wrapper = (root / "scripts" / "run_full_tests_windows.ps1").read_text(encoding="utf-8")
        linux_wrapper = (root / "scripts" / "pre_push_checks.sh").read_text(encoding="utf-8")

        self.assertIn("check_public_release_boundary.py --tree-ish HEAD", windows_wrapper)
        self.assertIn("check_public_release_boundary.py --tree-ish HEAD", linux_wrapper)

    def test_worktree_index_and_committed_tree_states_do_not_bleed(self) -> None:
        root = self._new_repo()
        source = root / "public.py"
        source.write_text('feature_name = "public"\n', encoding="utf-8")
        self._git(root, "add", "public.py")
        self._git(root, "commit", "-qm", "initial")
        clean_tree = inspect_boundary(mode="tree", treeish="HEAD", root=root)
        clean_index = inspect_boundary(mode="index", root=root)

        private_code = "F" + "999"
        source.write_text(f'private_marker = "{private_code}"\n', encoding="utf-8")
        (root / "untracked.py").write_text(f'private_marker = "{private_code}"\n', encoding="utf-8")
        self.assertEqual(inspect_boundary(mode="tree", treeish="HEAD", root=root)["status"], "passed")
        self.assertEqual(inspect_boundary(mode="index", root=root)["state_identifier"], clean_index["state_identifier"])

        self._git(root, "add", "public.py")
        staged = inspect_boundary(mode="index", root=root)
        self.assertEqual(staged["status"], "failed")
        self.assertNotEqual(staged["state_identifier"], clean_index["state_identifier"])
        self.assertEqual(inspect_boundary(mode="tree", treeish="HEAD", root=root)["state_identifier"], clean_tree["state_identifier"])

        self._git(root, "commit", "-qm", "stage private marker")
        self.assertEqual(inspect_boundary(mode="tree", treeish="HEAD", root=root)["status"], "failed")

    def test_index_scans_renamed_text_and_skips_binary_payloads(self) -> None:
        root = self._new_repo()
        (root / "source.py").write_text('feature_name = "public"\n', encoding="utf-8")
        self._git(root, "add", "source.py")
        self._git(root, "commit", "-qm", "initial")

        self._git(root, "mv", "source.py", "renamed.py")
        private_code = b"F" + b"999"
        (root / "renamed.py").write_bytes(b'private_marker = "' + private_code + b'"\n')
        (root / "asset.bin").write_bytes(b"\x00" + private_code + b"\x01")
        self._git(root, "add", "renamed.py", "asset.bin")

        report = inspect_boundary(mode="index", root=root)
        self.assertEqual(
            report["violations"],
            [{"path": "renamed.py", "reason": "internal-item-code"}],
        )


if __name__ == "__main__":
    unittest.main()
