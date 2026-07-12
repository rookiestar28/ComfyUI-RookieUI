from __future__ import annotations

import unittest
from pathlib import Path

from scripts.check_public_release_boundary import find_forbidden_tracked_entries


class PublicReleaseBoundaryTests(unittest.TestCase):
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

    def test_ci_runs_boundary_after_host_lane_before_publish_job_can_succeed(self) -> None:
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertLess(workflow.index("Run required current-host contract lane"), workflow.index("Verify public release boundary"))
        self.assertIn(".venv/bin/python scripts/check_public_release_boundary.py", workflow)
        self.assertIn("needs: full-test-gate", workflow)


if __name__ == "__main__":
    unittest.main()
