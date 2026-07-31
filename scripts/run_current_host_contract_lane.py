from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
# CRITICAL: keep repo root importable for direct script execution in CI and local venvs.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_MANIFEST = ROOT / "tests" / "fixtures" / "current_host_risk_contract.json"
REPORT_PATH = ROOT / ".tmp" / "current-host-contract-report.json"
DEFAULT_SOURCE_ROOTS: Mapping[str, Path] = {
    "core": ROOT / "reference" / "ComfyUI",
    "frontend": ROOT / "reference" / "ComfyUI_frontend",
    "desktop": ROOT / "reference" / "desktop",
}
REQUIRED_CASE_IDS = {
    "source_basis",
    "prompt_hook_mutation",
    "prompt_sensitive_queue",
    "route_alias_collision_retry",
    "route_multi_user_boundary",
    "sidebar_resource_cleanup",
    "sidebar_real_remount_visual",
}


def _read_git_revision(source_root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    revision = completed.stdout.strip().lower()
    if completed.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Authoritative reference revision is unavailable or invalid.")
    return revision


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_relative_artifact_path(value: object) -> str:
    candidate = str(value or "")
    normalized = PurePosixPath(candidate)
    if (
        not candidate
        or not normalized.parts
        or "\\" in candidate
        or candidate.startswith("/")
        or re.match(r"^[A-Za-z]:", candidate)
        or ".." in normalized.parts
    ):
        raise ValueError("Current-host source artifact path is unsafe.")
    return normalized.as_posix()


def load_and_validate_manifest(
    path: Path = DEFAULT_MANIFEST,
    *,
    source_roots: Mapping[str, Path] | None = None,
    revision_reader: Callable[[Path], str] | None = None,
) -> dict[str, Any]:
    from rookieui.contracts.host_source_basis import HOST_SOURCE_BASIS

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("fixture_version") != "current-host-risk-lane-v2":
        raise ValueError("Current-host fixture version is missing or unsupported.")
    expected_sources = {
        "core": HOST_SOURCE_BASIS.core.revision,
        "frontend": HOST_SOURCE_BASIS.frontend.revision,
        "desktop": HOST_SOURCE_BASIS.desktop.revision,
    }
    if payload.get("sources") != expected_sources:
        raise ValueError("Current-host fixture source revisions drifted from HOST_SOURCE_BASIS.")
    case_ids = payload.get("case_ids")
    if not isinstance(case_ids, list) or set(case_ids) != REQUIRED_CASE_IDS:
        raise ValueError("Current-host fixture does not contain the exact required risk cases.")
    artifacts = payload.get("source_artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 5:
        raise ValueError("Current-host fixture must identify exactly five authoritative source artifacts.")
    seen_paths: set[tuple[str, str]] = set()
    for artifact in artifacts:
        relative_path = _validate_relative_artifact_path(artifact.get("path"))
        key = (str(artifact.get("source", "")), relative_path)
        if key in seen_paths or key[0] not in {"core", "frontend"} or not key[1]:
            raise ValueError("Current-host fixture contains an invalid or duplicate source artifact.")
        seen_paths.add(key)
        if not isinstance(artifact.get("bytes"), int) or artifact["bytes"] <= 0:
            raise ValueError("Current-host source artifact byte size must be positive.")
        if not re.fullmatch(r"[0-9a-f]{64}", str(artifact.get("sha256", ""))):
            raise ValueError("Current-host source artifact SHA-256 is invalid.")
    if payload.get("inference_required") is not False:
        raise ValueError("The current-host risk lane must not require model inference.")

    resolved_roots = dict(DEFAULT_SOURCE_ROOTS if source_roots is None else source_roots)
    if source_roots is None:
        existing_roots = [root.is_dir() for root in resolved_roots.values()]
        # IMPORTANT: ignored reference repos are absent in public CI; a partial local
        # envelope is unsafe, while a fully absent envelope remains fixture-only.
        if any(existing_roots) and not all(existing_roots):
            raise ValueError("Authoritative reference source roots are only partially available.")
        if not any(existing_roots):
            return {
                "fixture_version": payload["fixture_version"],
                "sources": expected_sources,
                "case_ids": sorted(REQUIRED_CASE_IDS),
                "verified_artifacts": [],
                "reference_verification": "unavailable-fixture-only",
            }
    if set(resolved_roots) != set(expected_sources):
        raise ValueError("Current-host authoritative source roots are incomplete or unexpected.")
    read_revision = revision_reader or _read_git_revision
    for source, expected_revision in expected_sources.items():
        source_root = Path(resolved_roots[source])
        if not source_root.is_dir():
            raise ValueError(f"Authoritative {source} reference source is missing.")
        if read_revision(source_root) != expected_revision:
            raise ValueError(f"Authoritative {source} reference revision mismatched the source basis.")

    verified_artifacts: list[dict[str, Any]] = []
    for artifact in artifacts:
        source = str(artifact["source"])
        relative_path = _validate_relative_artifact_path(artifact["path"])
        source_root = Path(resolved_roots[source]).resolve()
        artifact_path = (source_root / Path(*PurePosixPath(relative_path).parts)).resolve()
        if not artifact_path.is_relative_to(source_root) or not artifact_path.is_file():
            raise ValueError(f"Authoritative {source} source artifact is missing or escaped its root.")
        actual_bytes = artifact_path.stat().st_size
        actual_sha256 = _sha256_file(artifact_path)
        if actual_bytes != artifact["bytes"] or actual_sha256 != artifact["sha256"]:
            raise ValueError(f"Authoritative {source} source artifact bytes or hash mismatched.")
        verified_artifacts.append(
            {
                "source": source,
                "path": relative_path,
                "bytes": actual_bytes,
                "sha256": actual_sha256,
            }
        )
    return {
        "fixture_version": payload["fixture_version"],
        "sources": expected_sources,
        "case_ids": sorted(REQUIRED_CASE_IDS),
        "verified_artifacts": verified_artifacts,
        "reference_verification": "verified",
    }


def build_lane_commands(root: Path = ROOT) -> list[list[str]]:
    _ = root
    npm = "npm.cmd" if os.name == "nt" else "npm"
    return [
        [
            sys.executable,
            "-m",
            "unittest",
            "tests.test_current_host_contract_lane",
            "tests.test_host_source_basis",
            "tests.test_prompt_submission",
            "tests.test_route_deployment_boundary",
        ],
        [
            npm,
            "exec",
            "--",
            "vitest",
            "run",
            "web/tests/rookieui_runtime_lifecycle.test.js",
            "web/tests/rookieui_sidebar_lifecycle.test.js",
        ],
        [npm, "exec", "--", "playwright", "test", "tests/e2e/specs/sidebar_lifecycle.spec.js"],
    ]


def _portable_command(command: list[str]) -> list[str]:
    rendered = list(command)
    if rendered and Path(rendered[0]).resolve() == Path(sys.executable).resolve():
        rendered[0] = "python"
    elif rendered and rendered[0].lower() in {"npm", "npm.cmd"}:
        rendered[0] = "npm"
    return rendered


def _command_id(command: list[str]) -> str | None:
    rendered = _portable_command(command)
    joined = " ".join(rendered)
    if rendered[:3] == ["python", "-m", "unittest"] and all(
        required in rendered
        for required in (
            "tests.test_current_host_contract_lane",
            "tests.test_host_source_basis",
            "tests.test_prompt_submission",
            "tests.test_route_deployment_boundary",
        )
    ):
        return "python-host-contracts"
    if joined.startswith("npm exec -- vitest run ") and all(
        required in joined
        for required in (
            "web/tests/rookieui_runtime_lifecycle.test.js",
            "web/tests/rookieui_sidebar_lifecycle.test.js",
        )
    ):
        return "frontend-lifecycle-contracts"
    if joined == "npm exec -- playwright test tests/e2e/specs/sidebar_lifecycle.spec.js":
        return "sidebar-remount-e2e"
    return None


def _validate_lane_commands(commands: list[list[str]]) -> list[str]:
    command_ids = [_command_id(command) for command in commands]
    expected = [
        "python-host-contracts",
        "frontend-lifecycle-contracts",
        "sidebar-remount-e2e",
    ]
    if command_ids != expected:
        raise ValueError("Current-host lane commands are missing, reordered, or unexpected.")
    return expected


def _run_command(command: list[str]) -> None:
    portable = _portable_command(command)
    print(f"[current-host-contract] run: {' '.join(portable)}", flush=True)
    if os.name == "nt":
        completed = subprocess.run(subprocess.list2cmdline(command), cwd=ROOT, shell=True, check=False)
    else:
        completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"Current-host contract command failed ({completed.returncode}): {' '.join(portable)}"
        )


def _write_report(report: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    REPORT_PATH.write_text(f"{rendered}\n", encoding="utf-8")
    print(f"[current-host-contract] report: {json.dumps(report, sort_keys=True)}")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write("## Required current-host contract lane\n\n```json\n")
            summary.write(rendered)
            summary.write("\n```\n")


def main() -> int:
    report: dict[str, Any] = {
        "fixture_version": None,
        "sources": {},
        "case_ids": [],
        "verified_artifacts": [],
        "reference_verification": "not-started",
        "lane_ran": False,
        "commands": [],
        "status": "running",
    }
    try:
        report.update(load_and_validate_manifest())
        commands = build_lane_commands()
        command_ids = _validate_lane_commands(commands)
        for command_id, command in zip(command_ids, commands, strict=True):
            command_report = {
                "id": command_id,
                "command": _portable_command(command),
                "status": "running",
            }
            report["commands"].append(command_report)
            try:
                _run_command(command)
            except Exception:
                command_report["status"] = "failed"
                raise
            command_report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        _write_report(report)
        return 1
    report["lane_ran"] = True
    report["status"] = "passed"
    _write_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
