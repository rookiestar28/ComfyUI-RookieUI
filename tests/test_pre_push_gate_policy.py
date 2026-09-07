from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "pre_push_scope.py"


def load_scope_module():
    spec = importlib.util.spec_from_file_location("rookieui_pre_push_scope", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrePushScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scope_module = load_scope_module()
        (ROOT / ".tmp").mkdir(exist_ok=True)

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(dir=ROOT / ".tmp")
        self.repo = Path(self.temp_dir.name)
        self._git("init", "-q")
        self._git("config", "user.name", "RookieUI Test")
        self._git("config", "user.email", "rookieui-test@example.invalid")
        (self.repo / "src").mkdir()
        (self.repo / ".github" / "workflows").mkdir(parents=True)
        (self.repo / "README.md").write_text("# Initial\n", encoding="utf-8")
        (self.repo / "package.json").write_text('{"private": true}\n', encoding="utf-8")
        (self.repo / "package-lock.json").write_text(
            '{"name": "fixture", "lockfileVersion": 3}\n', encoding="utf-8"
        )
        (self.repo / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        self._git("add", ".")
        self._git("commit", "-qm", "initial")
        self.initial = self._git("rev-parse", "HEAD")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

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

    def _commit(self, relative_path: str, content: str, message: str) -> str:
        path = self.repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self._git("add", relative_path)
        self._git("commit", "-qm", message)
        return self._git("rev-parse", "HEAD")

    def _update(self, local: str, remote: str) -> str:
        return f"refs/heads/main {local} refs/heads/main {remote}\n"

    def test_existing_ref_documentation_only_is_lightweight_without_audit(self) -> None:
        local = self._commit("README.md", "# Documented\n", "docs")

        decision = self.scope_module.classify_updates(
            self.repo, self._update(local, self.initial)
        )

        self.assertEqual(decision.scope, "docs")
        self.assertFalse(decision.audit_required)
        self.assertEqual(decision.commits, (local,))
        self.assertEqual(decision.ranges, ((self.initial, local),))

    def test_documentation_suffix_is_allowed_but_workflow_config_is_not(self) -> None:
        docs_commit = self._commit("docs/design.rst", "Design\n======\n", "docs rst")
        docs_decision = self.scope_module.classify_updates(
            self.repo, self._update(docs_commit, self.initial)
        )
        self.assertEqual(docs_decision.scope, "docs")

        workflow_commit = self._commit(
            ".github/workflows/ci.yml", "name: ci\n", "workflow config"
        )
        workflow_decision = self.scope_module.classify_updates(
            self.repo, self._update(workflow_commit, docs_commit)
        )
        self.assertEqual(workflow_decision.scope, "comprehensive")
        self.assertFalse(workflow_decision.audit_required)

    def test_text_dependency_and_test_fixture_paths_are_not_treated_as_docs(self) -> None:
        requirements_commit = self._commit(
            "requirements.txt", "aiohttp>=3.12\n", "python requirements"
        )
        requirements_decision = self.scope_module.classify_updates(
            self.repo, self._update(requirements_commit, self.initial)
        )
        self.assertEqual(requirements_decision.scope, "comprehensive")
        self.assertFalse(requirements_decision.audit_required)

        fixture_commit = self._commit(
            "tests/fixture.md", "behavior fixture\n", "test fixture"
        )
        fixture_decision = self.scope_module.classify_updates(
            self.repo, self._update(fixture_commit, requirements_commit)
        )
        self.assertEqual(fixture_decision.scope, "comprehensive")
        self.assertFalse(fixture_decision.audit_required)

    def test_behavior_change_is_comprehensive_but_does_not_require_hook_audit(self) -> None:
        local = self._commit("src/app.py", "VALUE = 2\n", "code")

        decision = self.scope_module.classify_updates(
            self.repo, self._update(local, self.initial)
        )

        self.assertEqual(decision.scope, "comprehensive")
        self.assertFalse(decision.audit_required)

    def test_node_dependency_metadata_change_requires_hook_audit(self) -> None:
        local = self._commit(
            "package-lock.json",
            '{"name": "fixture", "lockfileVersion": 3, "packages": {}}\n',
            "lock",
        )

        decision = self.scope_module.classify_updates(
            self.repo, self._update(local, self.initial)
        )

        self.assertEqual(decision.scope, "comprehensive")
        self.assertTrue(decision.audit_required)

    def test_multiple_ref_updates_are_unioned(self) -> None:
        docs_commit = self._commit("README.md", "# Documented\n", "docs")
        lock_commit = self._commit(
            "package.json", '{"private": true, "version": "1.0.0"}\n', "manifest"
        )
        updates = (
            f"refs/heads/main {docs_commit} refs/heads/main {self.initial}\n"
            f"refs/heads/deps {lock_commit} refs/heads/deps {docs_commit}\n"
        )

        decision = self.scope_module.classify_updates(self.repo, updates)

        self.assertEqual(decision.scope, "comprehensive")
        self.assertTrue(decision.audit_required)
        self.assertEqual(decision.commits, (docs_commit, lock_commit))
        self.assertEqual(len(decision.ranges), 2)

    def test_new_ref_is_fail_closed_to_comprehensive_with_audit(self) -> None:
        local = self._commit("README.md", "# New branch docs\n", "docs")
        zero = "0" * len(local)

        decision = self.scope_module.classify_updates(
            self.repo, self._update(local, zero)
        )

        self.assertEqual(decision.scope, "comprehensive")
        self.assertTrue(decision.audit_required)
        self.assertIn(self.initial, decision.commits)
        self.assertIn(local, decision.commits)
        self.assertEqual(len(decision.ranges), 1)
        self.assertNotEqual(decision.ranges[0][0], zero)

    def test_every_commit_introduced_by_an_existing_ref_is_boundary_checked(self) -> None:
        first = self._commit("README.md", "# First\n", "first docs")
        second = self._commit("README.md", "# Second\n", "second docs")

        decision = self.scope_module.classify_updates(
            self.repo, self._update(second, self.initial)
        )

        self.assertEqual(decision.scope, "docs")
        self.assertEqual(decision.commits, (first, second))

    def test_reverted_behavior_touch_still_selects_comprehensive_gate(self) -> None:
        self._commit("src/app.py", "VALUE = 2\n", "temporary code")
        final = self._commit("src/app.py", "VALUE = 1\n", "revert code")

        decision = self.scope_module.classify_updates(
            self.repo, self._update(final, self.initial)
        )

        self.assertEqual(decision.scope, "comprehensive")
        self.assertFalse(decision.audit_required)

    def test_reverted_dependency_touch_still_requires_hook_audit(self) -> None:
        self._commit(
            "package-lock.json",
            '{"name": "fixture", "lockfileVersion": 3, "packages": {}}\n',
            "temporary lock",
        )
        final = self._commit(
            "package-lock.json",
            '{"name": "fixture", "lockfileVersion": 3}\n',
            "revert lock",
        )

        decision = self.scope_module.classify_updates(
            self.repo, self._update(final, self.initial)
        )

        self.assertEqual(decision.scope, "comprehensive")
        self.assertTrue(decision.audit_required)

    def test_delete_only_update_is_noop(self) -> None:
        zero = "0" * len(self.initial)

        decision = self.scope_module.classify_updates(
            self.repo, self._update(zero, self.initial)
        )

        self.assertEqual(decision.scope, "noop")
        self.assertFalse(decision.audit_required)
        self.assertEqual(decision.commits, ())
        self.assertEqual(decision.ranges, ())

    def test_missing_or_malformed_hook_updates_fail_closed(self) -> None:
        with self.assertRaises(self.scope_module.PushScopeError):
            self.scope_module.classify_updates(self.repo, "")
        with self.assertRaises(self.scope_module.PushScopeError):
            self.scope_module.classify_updates(self.repo, "only three fields here\n")
        with self.assertRaises(self.scope_module.PushScopeError):
            self.scope_module.classify_updates(
                self.repo, self._update("f" * len(self.initial), self.initial)
            )

    def test_full_gate_decision_is_always_comprehensive_and_audited(self) -> None:
        decision = self.scope_module.full_gate_decision(self.repo)

        self.assertEqual(decision.scope, "comprehensive")
        self.assertTrue(decision.audit_required)
        self.assertEqual(decision.commits, (self.initial,))

    def test_machine_output_is_fixed_and_contains_no_changed_paths(self) -> None:
        local = self._commit("README.md", "# Documented\n", "docs")
        decision = self.scope_module.classify_updates(
            self.repo, self._update(local, self.initial)
        )

        lines = self.scope_module.format_decision(decision).splitlines()

        self.assertEqual(lines[0], "scope\tdocs")
        self.assertEqual(lines[1], "audit\tno-audit")
        self.assertIn(f"range\t{self.initial}\t{local}", lines)
        self.assertIn(f"commit\t{local}", lines)
        self.assertNotIn("README.md", "\n".join(lines))

    def test_subprocess_stream_is_lf_terminated_for_the_shell_parser(self) -> None:
        """The bash runner reads this stream with `read`, which does not strip carriage returns.

        IMPORTANT: this runs the script as a subprocess and inspects raw bytes on purpose.
        Every other check here calls format_decision in-process and compares splitlines(),
        which is indifferent to the line terminator. That is exactly how a CRLF stream reached
        the shell parser and made every Windows push fail with `invalid scope classifier
        output`, while the whole suite stayed green.
        """
        local = self._commit("src/app.py", "VALUE = 2\n", "behavior")
        updates = self.repo / "hook-updates.txt"
        updates.write_text(self._update(local, self.initial), encoding="utf-8")

        completed = subprocess.run(
            [
                sys.executable,
                str(MODULE_PATH),
                "--repo",
                str(self.repo),
                "--hook-updates",
                str(updates),
            ],
            check=True,
            capture_output=True,
        )

        raw = completed.stdout
        self.assertNotIn(
            b"\r",
            raw,
            "classifier stdout carries a carriage return; the shell parser reads the scope "
            f"value as e.g. 'comprehensive\\r' and rejects it. Raw bytes: {raw!r}",
        )

        records = [line.split(b"\t") for line in raw.split(b"\n") if line]
        self.assertEqual(records[0], [b"scope", b"comprehensive"])
        self.assertEqual(records[1], [b"audit", b"no-audit"])
        self.assertTrue(raw.endswith(b"\n"))


class PrePushWrapperContractTests(unittest.TestCase):
    def test_git_hook_forwards_ref_metadata_in_hook_mode(self) -> None:
        text = (ROOT / ".githooks" / "pre-push").read_text(encoding="utf-8")
        self.assertIn('scripts/pre_push_checks.sh --hook "$@"', text)

    def test_linux_full_gate_selects_explicit_full_mode(self) -> None:
        text = (ROOT / "scripts" / "run_full_tests_linux.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("scripts/pre_push_checks.sh --full-gate", text)

    def test_bash_runner_does_not_evaluate_classifier_output(self) -> None:
        text = (ROOT / "scripts" / "pre_push_checks.sh").read_text(encoding="utf-8")
        self.assertNotIn("eval ", text)
        self.assertIn('if [ "$AUDIT_REQUIRED" = "audit" ]', text)
        self.assertIn("npm run audit:ci", text)


if __name__ == "__main__":
    unittest.main()
