from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_COMPONENTS = frozenset({".planning", "reference", ".reference", ".sessions"})
_INTERNAL_ITEM_CODE_BYTES = re.compile(rb"(?<![A-Za-z0-9_])(?:F|R)[0-9]{3}(?![A-Za-z0-9_])")
_REVISION = re.compile(r"[A-Za-z0-9._/@{}^~:+-]{1,256}")


class BoundaryInspectionError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


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


def _run_git(root: Path, args: Sequence[str], *, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        input=input_bytes,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise BoundaryInspectionError("git-object-read-failed")
    return completed


def _read_blob_objects(root: Path, object_ids: Sequence[str]) -> dict[str, bytes]:
    unique_ids = list(dict.fromkeys(object_ids))
    if not unique_ids:
        return {}
    completed = _run_git(root, ["cat-file", "--batch"], input_bytes=("\n".join(unique_ids) + "\n").encode("ascii"))
    output = completed.stdout
    offset = 0
    blobs: dict[str, bytes] = {}
    for requested_oid in unique_ids:
        header_end = output.find(b"\n", offset)
        if header_end < 0:
            raise BoundaryInspectionError("malformed-git-object")
        header = output[offset:header_end].decode("ascii", errors="strict").split()
        offset = header_end + 1
        if len(header) != 3 or header[0] != requested_oid or header[1] != "blob":
            raise BoundaryInspectionError("non-blob-git-object")
        try:
            size = int(header[2])
        except ValueError as error:
            raise BoundaryInspectionError("malformed-git-object") from error
        content_end = offset + size
        if content_end >= len(output) or output[content_end : content_end + 1] != b"\n":
            raise BoundaryInspectionError("malformed-git-object")
        blobs[requested_oid] = output[offset:content_end]
        offset = content_end + 1
    if offset != len(output):
        raise BoundaryInspectionError("malformed-git-object")
    return blobs


def _parse_index(root: Path) -> tuple[list[tuple[str, str]], list[tuple[str, bytes]], str]:
    raw_index = _run_git(root, ["ls-files", "-s", "-z"]).stdout
    metadata_entries: list[tuple[str, str, str]] = []
    for raw_entry in raw_index.decode("utf-8", errors="strict").split("\0"):
        if not raw_entry:
            continue
        metadata, path = raw_entry.split("\t", 1)
        mode, object_id, stage = metadata.split()
        if stage != "0":
            raise BoundaryInspectionError("unmerged-index")
        metadata_entries.append((mode, object_id, path))
    blob_ids = [object_id for mode, object_id, _path in metadata_entries if mode != "160000"]
    blobs = _read_blob_objects(root, blob_ids)
    paths = [(mode, path) for mode, _object_id, path in metadata_entries]
    content = [(path, blobs[object_id]) for mode, object_id, path in metadata_entries if mode != "160000"]
    identifier = f"index-sha256:{hashlib.sha256(raw_index).hexdigest()}"
    return paths, content, identifier


def _resolve_tree(root: Path, treeish: str) -> str:
    if treeish.startswith("-") or not _REVISION.fullmatch(treeish):
        raise BoundaryInspectionError("invalid-tree-ish")
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", f"{treeish}^{{tree}}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="ascii",
        errors="strict",
    )
    resolved = completed.stdout.strip()
    if completed.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40,64}", resolved):
        raise BoundaryInspectionError("invalid-tree-ish")
    return resolved


def _parse_tree(root: Path, treeish: str) -> tuple[list[tuple[str, str]], list[tuple[str, bytes]], str]:
    resolved_tree = _resolve_tree(root, treeish)
    raw_tree = _run_git(root, ["ls-tree", "-r", "-z", "--full-tree", resolved_tree]).stdout
    metadata_entries: list[tuple[str, str, str, str]] = []
    for raw_entry in raw_tree.decode("utf-8", errors="strict").split("\0"):
        if not raw_entry:
            continue
        metadata, path = raw_entry.split("\t", 1)
        mode, object_type, object_id = metadata.split()
        metadata_entries.append((mode, object_type, object_id, path))
    blob_ids = [object_id for _mode, object_type, object_id, _path in metadata_entries if object_type == "blob"]
    blobs = _read_blob_objects(root, blob_ids)
    paths = [(mode, path) for mode, _object_type, _object_id, path in metadata_entries]
    content = [
        (path, blobs[object_id])
        for _mode, object_type, object_id, path in metadata_entries
        if object_type == "blob"
    ]
    return paths, content, resolved_tree


def inspect_boundary(*, mode: str = "index", treeish: str | None = None, root: Path = ROOT) -> dict[str, object]:
    if mode == "index":
        path_entries, content_entries, identifier = _parse_index(root)
        identity: dict[str, object] = {"state_identifier": identifier}
    elif mode == "tree" and treeish is not None:
        path_entries, content_entries, resolved_tree = _parse_tree(root, treeish)
        identity = {"requested_revision": treeish, "resolved_tree": resolved_tree, "state_identifier": resolved_tree}
    else:
        raise BoundaryInspectionError("invalid-inspection-mode")
    violations = [
        *find_forbidden_tracked_entries(path_entries),
        *find_forbidden_tracked_content(content_entries),
    ]
    return {
        "boundary_checked": True,
        "content_checked": True,
        "inspection_mode": mode,
        **identity,
        "tracked_entries": len(path_entries),
        "content_entries": len(content_entries),
        "violations": violations,
        "status": "failed" if violations else "passed",
    }


def scan_forbidden_tracked_content(root: Path = ROOT) -> list[dict[str, str]]:
    report = inspect_boundary(mode="index", root=root)
    return [entry for entry in report["violations"] if entry["reason"] == "internal-item-code"]  # type: ignore[index]


def read_tracked_entries(root: Path = ROOT) -> list[tuple[str, str]]:
    entries, _content, _identifier = _parse_index(root)
    return entries


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the public Git boundary without checking out or executing content.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--index", action="store_true", help="Inspect the current Git index (default).")
    mode.add_argument("--tree-ish", metavar="REVISION", help="Inspect an immutable Git tree-ish.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    mode = "tree" if args.tree_ish is not None else "index"
    try:
        report = inspect_boundary(mode=mode, treeish=args.tree_ish)
    except (BoundaryInspectionError, UnicodeError, ValueError) as error:
        code = error.code if isinstance(error, BoundaryInspectionError) else "malformed-git-data"
        report = {
            "boundary_checked": False,
            "content_checked": False,
            "inspection_mode": mode,
            "error": code,
            "status": "error",
            "violations": [],
        }
        print(f"[public-release-boundary] {json.dumps(report, sort_keys=True)}")
        return 2
    print(f"[public-release-boundary] {json.dumps(report, sort_keys=True)}")
    return 1 if report["violations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
