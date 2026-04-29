from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _case_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(cases, list):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id") or "").strip()
        if case_id:
            mapped[case_id] = case
    return mapped


def _numeric_summary(case: dict[str, Any]) -> dict[str, float]:
    summary = case.get("summary")
    if not isinstance(summary, dict):
        return {}
    numeric: dict[str, float] = {}
    for key, value in summary.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            numeric[str(key)] = float(value)
    return numeric


def build_tensor_diff_report(
    rookie_payload: dict[str, Any] | None,
    reference_payload: dict[str, Any] | None,
    *,
    tolerance: float = 1e-4,
) -> dict[str, Any]:
    if rookie_payload is None or reference_payload is None:
        return {
            "status": "skipped",
            "reason": "rookie and reference JSON summaries are required for live tensor comparison.",
            "case_count": 0,
            "max_abs_diff": None,
            "drifts": [],
        }

    rookie_cases = _case_map(rookie_payload)
    reference_cases = _case_map(reference_payload)
    all_case_ids = sorted(set(rookie_cases) | set(reference_cases))
    drifts: list[dict[str, Any]] = []
    max_abs_diff = 0.0
    compared = 0

    for case_id in all_case_ids:
        rookie_case = rookie_cases.get(case_id)
        reference_case = reference_cases.get(case_id)
        if rookie_case is None or reference_case is None:
            drifts.append(
                {
                    "case_id": case_id,
                    "field": "case_id",
                    "rookie": rookie_case is not None,
                    "reference": reference_case is not None,
                    "abs_diff": None,
                }
            )
            continue
        rookie_summary = _numeric_summary(rookie_case)
        reference_summary = _numeric_summary(reference_case)
        for field in sorted(set(rookie_summary) | set(reference_summary)):
            if field not in rookie_summary or field not in reference_summary:
                drifts.append(
                    {
                        "case_id": case_id,
                        "field": field,
                        "rookie": rookie_summary.get(field),
                        "reference": reference_summary.get(field),
                        "abs_diff": None,
                    }
                )
                continue
            diff = abs(float(rookie_summary[field]) - float(reference_summary[field]))
            max_abs_diff = max(max_abs_diff, diff)
            compared += 1
            if diff > float(tolerance):
                drifts.append(
                    {
                        "case_id": case_id,
                        "field": field,
                        "rookie": rookie_summary[field],
                        "reference": reference_summary[field],
                        "abs_diff": diff,
                    }
                )

    return {
        "status": "failed" if drifts else "passed",
        "tolerance": float(tolerance),
        "case_count": len(all_case_ids),
        "compared_fields": compared,
        "max_abs_diff": max_abs_diff,
        "drifts": drifts,
    }


def _load_json(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_report(report: dict[str, Any], output: str | None) -> None:
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare RookieUI and reference prompt encoder tensor summaries.")
    parser.add_argument("--rookie-json", default="", help="Path to a RookieUI tensor summary JSON report.")
    parser.add_argument("--reference-json", default="", help="Path to a reference tensor summary JSON report.")
    parser.add_argument("--output", default="", help="Optional path to write the diff report JSON.")
    parser.add_argument("--tolerance", type=float, default=1e-4, help="Maximum accepted absolute numeric drift.")
    args = parser.parse_args(argv)

    try:
        report = build_tensor_diff_report(
            _load_json(args.rookie_json),
            _load_json(args.reference_json),
            tolerance=args.tolerance,
        )
    except (OSError, json.JSONDecodeError) as exc:
        report = {
            "status": "error",
            "reason": str(exc),
            "case_count": 0,
            "max_abs_diff": None,
            "drifts": [],
        }
        _write_report(report, args.output)
        return 2

    _write_report(report, args.output)
    if report["status"] == "failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
