from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_LIVE_SMOKE_SCRIPT = _REPO_ROOT / "scripts" / "run_live_smoke_tests.py"


def _env_flag(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the repository host-embedded E2E contract by delegating to the canonical "
            "run_live_smoke_tests.py entrypoint in strict report-then-execute order."
        )
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("ROOKIEUI_LIVE_BASE_URL", "http://127.0.0.1:8188"),
        help="ComfyUI host base URL forwarded to the live-smoke runner (default: %(default)s).",
    )
    parser.add_argument(
        "--validation-mode",
        default=os.getenv("ROOKIEUI_HOST_EMBEDDED_VALIDATION_MODE", "full-pipeline").strip() or "full-pipeline",
        help="Validation mode forwarded to the live-smoke runner (default: %(default)s).",
    )
    parser.add_argument(
        "--profiles",
        default=os.getenv("ROOKIEUI_LIVE_SMOKE_PROFILES", "").strip(),
        help="Optional comma-separated profiles forwarded to the live-smoke runner.",
    )
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=float(os.getenv("ROOKIEUI_LIVE_REQUEST_TIMEOUT_SECONDS", "30")),
        help="HTTP request timeout forwarded to the live-smoke runner (default: %(default)s).",
    )
    parser.add_argument(
        "--poll-timeout-seconds",
        type=float,
        default=float(os.getenv("ROOKIEUI_LIVE_POLL_TIMEOUT_SECONDS", "180")),
        help="Queue poll timeout forwarded to the live-smoke runner (default: %(default)s).",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=float(os.getenv("ROOKIEUI_LIVE_POLL_INTERVAL_SECONDS", "2")),
        help="Queue poll interval forwarded to the live-smoke runner (default: %(default)s).",
    )
    parser.add_argument(
        "--skip-execute",
        action="store_true",
        default=_env_flag("ROOKIEUI_HOST_EMBEDDED_SKIP_EXECUTE", default=False),
        help="Run only the strict report pass and skip the execute pass.",
    )
    return parser


def _build_live_smoke_command(args: argparse.Namespace, *, execute: bool) -> list[str]:
    command = [
        sys.executable,
        str(_LIVE_SMOKE_SCRIPT),
        "--base-url",
        args.base_url,
        "--validation-mode",
        args.validation_mode,
        "--request-timeout-seconds",
        str(args.request_timeout_seconds),
        "--poll-timeout-seconds",
        str(args.poll_timeout_seconds),
        "--poll-interval-seconds",
        str(args.poll_interval_seconds),
    ]
    if args.profiles:
        command.extend(["--profiles", args.profiles])
    if execute:
        command.append("--execute")
    return command


def _run_live_smoke_step(label: str, command: list[str]) -> int:
    print(f"[host-e2e] {label}: {' '.join(command)}")
    completed = subprocess.run(command, cwd=str(_REPO_ROOT), check=False)
    return int(completed.returncode)


def main() -> int:
    args = _build_parser().parse_args()
    print(f"[host-e2e] base_url={args.base_url}")
    print(f"[host-e2e] validation_mode={args.validation_mode}")
    print(f"[host-e2e] profiles={args.profiles or '<none>'}")
    print(f"[host-e2e] execute={'off' if args.skip_execute else 'on'}")

    report_command = _build_live_smoke_command(args, execute=False)
    report_code = _run_live_smoke_step("report", report_command)
    if report_code != 0:
        print("[host-e2e] report pass failed.", file=sys.stderr)
        return report_code

    if args.skip_execute:
        print("[host-e2e] PASS (report-only contract)")
        return 0

    execute_command = _build_live_smoke_command(args, execute=True)
    execute_code = _run_live_smoke_step("execute", execute_command)
    if execute_code != 0:
        print("[host-e2e] execute pass failed.", file=sys.stderr)
        return execute_code

    print("[host-e2e] PASS")
    return 0


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    raise SystemExit(main())
