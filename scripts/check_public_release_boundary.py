from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_COMPONENTS = frozenset({".planning", "reference", ".reference", ".sessions"})


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
    violations = find_forbidden_tracked_entries(entries)
    report = {
        "boundary_checked": True,
        "tracked_entries": len(entries),
        "violations": violations,
        "status": "failed" if violations else "passed",
    }
    print(f"[public-release-boundary] {json.dumps(report, sort_keys=True)}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
