from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
from typing import NamedTuple, Sequence


OBJECT_ID_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
DOCUMENT_EXTENSIONS = frozenset({".adoc", ".md", ".mdx", ".rst", ".txt"})
DOCUMENT_BASENAMES = frozenset(
    {
        "authors",
        "changelog",
        "code_of_conduct",
        "contributing",
        "copying",
        "license",
        "notice",
        "readme",
        "security",
    }
)
NODE_DEPENDENCY_PATHS = frozenset(
    {"package.json", "package-lock.json", "npm-shrinkwrap.json"}
)


class PushScopeError(RuntimeError):
    pass


class GateDecision(NamedTuple):
    scope: str
    audit_required: bool
    ranges: tuple[tuple[str, str], ...]
    commits: tuple[str, ...]


class PushUpdate(NamedTuple):
    local_ref: str
    local_object: str
    remote_ref: str
    remote_object: str


def _run_git(repo: Path, args: Sequence[str], *, input_text: str | None = None) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
        raise PushScopeError(f"{detail}: git {' '.join(args)}")
    return completed.stdout.strip()


def _run_git_bytes(repo: Path, args: Sequence[str]) -> bytes:
    completed = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=False
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise PushScopeError(f"{detail or 'git command failed'}: git {' '.join(args)}")
    return completed.stdout


def _is_zero_object(value: str) -> bool:
    return bool(value) and set(value) == {"0"} and len(value) in {40, 64}


def _validate_object_id(value: str, field: str) -> None:
    if not OBJECT_ID_RE.fullmatch(value):
        raise PushScopeError(f"invalid {field}: expected a 40- or 64-character object ID")


def _resolve_commit(repo: Path, object_id: str, field: str) -> str:
    _validate_object_id(object_id, field)
    resolved = _run_git(repo, ["rev-parse", "--verify", f"{object_id}^{{commit}}"])
    if not OBJECT_ID_RE.fullmatch(resolved):
        raise PushScopeError(f"invalid resolved {field} commit")
    return resolved


def _empty_tree(repo: Path) -> str:
    # IMPORTANT: a new remote ref has no trusted comparison base. Materialize the
    # canonical empty tree so the final snapshot, including dependency files, is classified.
    object_id = _run_git(repo, ["mktree"], input_text="")
    _validate_object_id(object_id, "empty-tree object")
    return object_id


def _parse_updates(raw_updates: str) -> tuple[PushUpdate, ...]:
    if not raw_updates.strip():
        raise PushScopeError("hook mode requires at least one Git pre-push update")
    updates: list[PushUpdate] = []
    for line_number, raw_line in enumerate(raw_updates.splitlines(), start=1):
        fields = raw_line.split()
        if len(fields) != 4:
            raise PushScopeError(
                f"malformed pre-push update at line {line_number}: expected four fields"
            )
        local_ref, local_object, remote_ref, remote_object = fields
        if not local_ref or not remote_ref:
            raise PushScopeError(f"malformed ref name at line {line_number}")
        _validate_object_id(local_object, f"local object at line {line_number}")
        _validate_object_id(remote_object, f"remote object at line {line_number}")
        updates.append(PushUpdate(local_ref, local_object, remote_ref, remote_object))
    return tuple(updates)


def _changed_paths(repo: Path, base: str, local: str) -> tuple[str, ...]:
    output = _run_git_bytes(
        repo,
        ["diff", "--name-only", "--no-renames", "-z", base, local, "--"],
    )
    return tuple(
        item.decode("utf-8", errors="surrogateescape")
        for item in output.split(b"\0")
        if item
    )


def _range_commits(repo: Path, base: str, local: str, *, new_ref: bool) -> tuple[str, ...]:
    if new_ref:
        output = _run_git(repo, ["rev-list", "--reverse", local, "--not", "--remotes"])
    else:
        output = _run_git(repo, ["rev-list", "--reverse", f"{base}..{local}"])
    commits = tuple(line for line in output.splitlines() if line)
    return commits or (local,)


def _commit_changed_paths(repo: Path, commits: Sequence[str]) -> tuple[str, ...]:
    changed: list[str] = []
    for commit in commits:
        output = _run_git_bytes(
            repo,
            [
                "diff-tree",
                "--root",
                "-m",
                "--no-commit-id",
                "--name-only",
                "--no-renames",
                "-r",
                "-z",
                commit,
            ],
        )
        changed.extend(
            item.decode("utf-8", errors="surrogateescape")
            for item in output.split(b"\0")
            if item
        )
    return tuple(changed)


def _is_document_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    name = normalized.rsplit("/", 1)[-1]
    lowered_name = name.casefold()
    suffix = Path(lowered_name).suffix
    stem = lowered_name.split(".", 1)[0]
    if stem in DOCUMENT_BASENAMES and (not suffix or suffix in DOCUMENT_EXTENSIONS):
        return True
    if "/" not in normalized and suffix in {".adoc", ".md", ".mdx", ".rst"}:
        return True
    if normalized.casefold().startswith(("docs/", "documentation/", ".github/")):
        return suffix in DOCUMENT_EXTENSIONS
    if normalized.casefold().startswith("tests/"):
        return lowered_name.endswith(("_sop.md", "_notice.md"))
    return False


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def classify_updates(repo: Path, raw_updates: str) -> GateDecision:
    repo = repo.resolve()
    updates = _parse_updates(raw_updates)
    ranges: list[tuple[str, str]] = []
    commits: list[str] = []
    changed_paths: set[str] = set()
    saw_new_ref = False

    for update in updates:
        if _is_zero_object(update.local_object):
            continue
        local = _resolve_commit(repo, update.local_object, "local object")
        if _is_zero_object(update.remote_object):
            base = _empty_tree(repo)
            saw_new_ref = True
        else:
            base = _resolve_commit(repo, update.remote_object, "remote object")
        ranges.append((base, local))
        range_commits = _range_commits(
            repo,
            base,
            local,
            new_ref=_is_zero_object(update.remote_object),
        )
        commits.extend(range_commits)
        changed_paths.update(_changed_paths(repo, base, local))
        changed_paths.update(_commit_changed_paths(repo, range_commits))

    if not ranges:
        return GateDecision("noop", False, (), ())

    audit_required = saw_new_ref or bool(changed_paths & NODE_DEPENDENCY_PATHS)
    docs_only = bool(changed_paths) and all(
        _is_document_path(path) for path in changed_paths
    )
    scope = "docs" if docs_only and not saw_new_ref else "comprehensive"
    return GateDecision(
        scope,
        audit_required,
        tuple(dict.fromkeys(ranges)),
        _dedupe(commits),
    )


def full_gate_decision(repo: Path) -> GateDecision:
    repo = repo.resolve()
    head = _resolve_commit(repo, _run_git(repo, ["rev-parse", "HEAD"]), "HEAD")
    return GateDecision("comprehensive", True, (), (head,))


def format_decision(decision: GateDecision) -> str:
    lines = [
        f"scope\t{decision.scope}",
        f"audit\t{'audit' if decision.audit_required else 'no-audit'}",
    ]
    lines.extend(f"range\t{base}\t{local}" for base, local in decision.ranges)
    lines.extend(f"commit\t{commit}" for commit in decision.commits)
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify immutable Git pre-push updates")
    parser.add_argument("--repo", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--hook-updates", type=Path)
    mode.add_argument("--full-gate", action="store_true")
    args = parser.parse_args()

    try:
        if args.full_gate:
            decision = full_gate_decision(args.repo)
        else:
            raw_updates = args.hook_updates.read_text(
                encoding="utf-8", errors="surrogateescape"
            )
            decision = classify_updates(args.repo, raw_updates)
    except (OSError, PushScopeError) as exc:
        parser.exit(2, f"pre-push scope error: {exc}\n")

    # IMPORTANT: write bytes rather than print. This stream is a machine contract parsed by a
    # bash `read` loop in scripts/pre_push_checks.sh, and `read` does not strip a carriage
    # return. Printing through text-mode stdout emits CRLF on Windows, which hands the parser
    # a scope value with a trailing CR and fails every push before the gate does any work.
    # Restoring print() reintroduces that on one platform only, invisibly to review and to
    # any test that compares the formatter's return value instead of the bytes on the pipe.
    sys.stdout.buffer.write(format_decision(decision).encode("utf-8"))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
