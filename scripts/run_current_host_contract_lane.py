from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
# CRITICAL: keep repo root importable for direct script execution in CI and local venvs.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_MANIFEST = ROOT / "tests" / "fixtures" / "current_host_risk_contract.json"
REPORT_PATH = ROOT / ".tmp" / "current-host-contract-report.json"
REQUIRED_CASE_IDS = {
    "source_basis",
    "prompt_hook_mutation",
    "prompt_sensitive_queue",
    "route_alias_collision_retry",
    "route_multi_user_boundary",
    "sidebar_resource_cleanup",
    "sidebar_real_remount_visual",
}


def load_and_validate_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    from rookieui.contracts.host_source_basis import HOST_SOURCE_BASIS

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("fixture_version") != "current-host-risk-lane-v1":
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
        key = (str(artifact.get("source", "")), str(artifact.get("path", "")))
        if key in seen_paths or key[0] not in {"core", "frontend"} or not key[1]:
            raise ValueError("Current-host fixture contains an invalid or duplicate source artifact.")
        seen_paths.add(key)
        if not isinstance(artifact.get("bytes"), int) or artifact["bytes"] <= 0:
            raise ValueError("Current-host source artifact byte size must be positive.")
        if not re.fullmatch(r"[0-9a-f]{64}", str(artifact.get("sha256", ""))):
            raise ValueError("Current-host source artifact SHA-256 is invalid.")
    if payload.get("inference_required") is not False:
        raise ValueError("The current-host risk lane must not require model inference.")
    return {
        "fixture_version": payload["fixture_version"],
        "sources": expected_sources,
        "case_ids": sorted(REQUIRED_CASE_IDS),
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


def _run_command(command: list[str]) -> None:
    print(f"[current-host-contract] run: {' '.join(command)}", flush=True)
    if os.name == "nt":
        completed = subprocess.run(subprocess.list2cmdline(command), cwd=ROOT, shell=True, check=False)
    else:
        completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Current-host contract command failed ({completed.returncode}): {' '.join(command)}")


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
    report = load_and_validate_manifest()
    report.update({"lane_ran": True, "commands": [], "status": "running"})
    try:
        for command in build_lane_commands():
            _run_command(command)
            report["commands"].append({"command": command, "status": "passed"})
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        _write_report(report)
        return 1
    report["status"] = "passed"
    _write_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
