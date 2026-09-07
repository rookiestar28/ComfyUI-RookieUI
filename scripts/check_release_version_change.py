#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


_FULL_OID = re.compile(r"[0-9a-fA-F]{40}")
_SAFE_VERSION = re.compile(r"[0-9A-Za-z][0-9A-Za-z._+!-]{0,127}")
_ZERO_OID = "0" * 40
_PROJECT_FILE = "pyproject.toml"


class ReleaseVersionGateError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ReleaseVersionDecision:
    previous_version: str
    current_version: str
    should_publish: bool


def _run_git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    # SECURITY: event revisions must stay validated argv values; shell interpolation would turn
    # externally supplied workflow context into executable syntax.
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
    )


def _validate_repository(root: Path) -> Path:
    resolved = root.resolve()
    if not resolved.is_dir():
        raise ReleaseVersionGateError("invalid-repository", "Repository root is not a directory.")

    completed = _run_git(resolved, "rev-parse", "--show-toplevel")
    if completed.returncode != 0:
        raise ReleaseVersionGateError("invalid-repository", "Repository root is not a Git worktree.")
    try:
        discovered = Path(completed.stdout.decode("utf-8", errors="strict").strip()).resolve()
    except UnicodeDecodeError as exc:
        raise ReleaseVersionGateError("invalid-repository", "Git returned a non-UTF-8 worktree path.") from exc
    if discovered != resolved:
        raise ReleaseVersionGateError("invalid-repository", "Repository argument must be the Git worktree root.")
    return resolved


def _validate_commit(root: Path, revision: str, label: str) -> str:
    if revision == _ZERO_OID or _FULL_OID.fullmatch(revision) is None:
        raise ReleaseVersionGateError(
            "invalid-revision",
            f"{label} revision must be a non-zero full Git object id.",
        )
    normalized = revision.lower()
    completed = _run_git(root, "cat-file", "-e", f"{normalized}^{{commit}}")
    if completed.returncode != 0:
        raise ReleaseVersionGateError("missing-revision", f"{label} revision is not an available commit.")
    return normalized


def _read_project_version(root: Path, revision: str, label: str) -> str:
    completed = _run_git(root, "cat-file", "blob", f"{revision}:{_PROJECT_FILE}")
    if completed.returncode != 0:
        raise ReleaseVersionGateError(
            "missing-project-metadata",
            f"{label} revision does not contain {_PROJECT_FILE}.",
        )
    try:
        document = completed.stdout.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise ReleaseVersionGateError(
            "invalid-project-metadata",
            f"{label} {_PROJECT_FILE} is not valid UTF-8.",
        ) from exc
    try:
        metadata = tomllib.loads(document)
    except tomllib.TOMLDecodeError as exc:
        raise ReleaseVersionGateError(
            "invalid-project-metadata",
            f"{label} {_PROJECT_FILE} is not valid TOML.",
        ) from exc

    project = metadata.get("project")
    version = project.get("version") if isinstance(project, dict) else None
    if not isinstance(version, str) or _SAFE_VERSION.fullmatch(version) is None:
        raise ReleaseVersionGateError(
            "invalid-project-version",
            f"{label} [project].version must be a non-empty, single-line package version.",
        )
    return version


def classify_release_version_change(root: Path, base: str, head: str) -> ReleaseVersionDecision:
    repository = _validate_repository(root)
    base_oid = _validate_commit(repository, base, "base")
    head_oid = _validate_commit(repository, head, "head")
    previous_version = _read_project_version(repository, base_oid, "base")
    current_version = _read_project_version(repository, head_oid, "head")
    return ReleaseVersionDecision(
        previous_version=previous_version,
        current_version=current_version,
        should_publish=previous_version != current_version,
    )


def _write_github_output(path: Path, decision: ReleaseVersionDecision) -> None:
    try:
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(f"should_publish={'true' if decision.should_publish else 'false'}\n")
            stream.write(f"previous_version={decision.previous_version}\n")
            stream.write(f"current_version={decision.current_version}\n")
    except OSError as exc:
        raise ReleaseVersionGateError("github-output-write-failed", "Could not write GitHub job output.") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare immutable push revisions and authorize Registry publication only for a version change."
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Git worktree root.")
    parser.add_argument("--base", required=True, help="Push event base commit (full object id).")
    parser.add_argument("--head", required=True, help="Push event head commit (full object id).")
    parser.add_argument("--github-output", type=Path, help="Optional GitHub Actions output file.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        decision = classify_release_version_change(args.repo, args.base, args.head)
        if args.github_output is not None:
            _write_github_output(args.github_output, decision)
    except ReleaseVersionGateError as exc:
        print(json.dumps({"status": "error", "error": exc.code}, sort_keys=True))
        print(f"[release-version] ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({"status": "ok", **asdict(decision)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
