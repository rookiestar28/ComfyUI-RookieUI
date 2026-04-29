from __future__ import annotations

from pathlib import Path
import json
import shutil
import unittest

from scripts.run_prompt_encoder_tensor_diff import build_tensor_diff_report, main


class PromptEncoderTensorDiffTests(unittest.TestCase):
    def test_build_tensor_diff_report_skips_without_inputs(self) -> None:
        report = build_tensor_diff_report(None, None)

        self.assertEqual(report["status"], "skipped")
        self.assertIn("rookie", report["reason"])

    def test_build_tensor_diff_report_compares_matching_numeric_summaries(self) -> None:
        rookie = {
            "cases": [
                {"case_id": "simple", "summary": {"mean": 1.0002, "std": 0.5, "sum": 10.0}},
            ]
        }
        reference = {
            "cases": [
                {"case_id": "simple", "summary": {"mean": 1.0, "std": 0.5, "sum": 10.0}},
            ]
        }

        report = build_tensor_diff_report(rookie, reference, tolerance=0.001)

        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["case_count"], 1)
        self.assertAlmostEqual(report["max_abs_diff"], 0.0002)

    def test_build_tensor_diff_report_flags_drift_over_tolerance(self) -> None:
        rookie = {"cases": [{"case_id": "simple", "summary": {"mean": 1.25}}]}
        reference = {"cases": [{"case_id": "simple", "summary": {"mean": 1.0}}]}

        report = build_tensor_diff_report(rookie, reference, tolerance=0.001)

        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["drifts"][0]["field"], "mean")

    def test_cli_writes_skipped_report_without_private_inputs(self) -> None:
        output_dir = Path(".tmp") / "test_prompt_encoder_tensor_diff"
        if output_dir.exists():
            shutil.rmtree(output_dir)
        try:
            output_dir.mkdir(parents=True)
            output_path = output_dir / "report.json"

            exit_code = main(["--output", str(output_path)])

            self.assertEqual(exit_code, 0)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "skipped")
        finally:
            if output_dir.exists():
                shutil.rmtree(output_dir)


if __name__ == "__main__":
    unittest.main()
