from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_COMPONENTS = frozenset({".planning", "reference", ".reference", ".sessions"})
_INTERNAL_ITEM_CODE_BYTES = re.compile(rb"(?<![A-Za-z0-9_])(?:F|R)[0-9]{3}(?![A-Za-z0-9_])")
_INTERNAL_ITEM_CODE_GIT_PATTERN = r"(^|[^A-Za-z0-9_])(F|R)[0-9]{3}([^A-Za-z0-9_]|$)"


def find_forbidden_tracked_entries(entries: Iterable[tuple[str, str]]) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for mode, raw_path in entries:
        normalized_path = raw_path.replace("\\", "/")
        path = PurePosixPath(normalized_path)
        lowered_parts = tuple(part.lower() for part in path.parts)
        reason = ""
        if mode == "120000":
            reason = "tracked-symlink"
        elif any(part in FORBIDDEN_COMPONENTS for part in lowered_parts):
            reason = "internal-path"
        elif path.name.lower() == "roadmap.md" or path.name.lower().startswith("roadmap_"):
            reason = "roadmap-path"
        if reason:
            violations.append({"path": normalized_path, "reason": reason})
    return violations


def find_forbidden_tracked_content(entries: Iterable[tuple[str, bytes]]) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for raw_path, content in entries:
        # Binary assets are not interpreted as text; path and symlink rules still apply independently.
        if b"\0" in content[:8192]:
            continue
        if _INTERNAL_ITEM_CODE_BYTES.search(content):
            violations.append({"path": raw_path.replace("\\", "/"), "reason": "internal-item-code"})
    return violations


def scan_forbidden_tracked_content(root: Path = ROOT) -> list[dict[str, str]]:
    # CRITICAL: scan the Git index, not arbitrary working-tree files, so ignored internal records cannot affect release status.
    completed = subprocess.run(
        [
            "git",
            "grep",
            "--cached",
            "-I",
            "-l",
            "-E",
            _INTERNAL_ITEM_CODE_GIT_PATTERN,
            "--",
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    if completed.returncode not in {0, 1}:
        raise subprocess.CalledProcessError(
            completed.returncode,
            completed.args,
            output=completed.stdout,
            stderr=completed.stderr,
        )
    if completed.returncode == 1:
        return []
    return [
        {"path": path.strip().replace("\\", "/"), "reason": "internal-item-code"}
        for path in completed.stdout.splitlines()
        if path.strip()
    ]


def read_tracked_entries(root: Path = ROOT) -> list[tuple[str, str]]:
    completed = subprocess.run(
        ["git", "ls-files", "-s", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    entries: list[tuple[str, str]] = []
    for raw_entry in completed.stdout.decode("utf-8", errors="strict").split("\0"):
        if not raw_entry:
            continue
        metadata, path = raw_entry.split("\t", 1)
        mode = metadata.split(" ", 1)[0]
        entries.append((mode, path))
    return entries


def main() -> int:
    entries = read_tracked_entries()
    violations = [*find_forbidden_tracked_entries(entries), *scan_forbidden_tracked_content()]
    report = {
        "boundary_checked": True,
        "content_checked": True,
        "tracked_entries": len(entries),
        "violations": violations,
        "status": "failed" if violations else "passed",
    }
    print(f"[public-release-boundary] {json.dumps(report, sort_keys=True)}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
