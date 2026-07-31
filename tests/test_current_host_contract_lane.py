from __future__ import annotations

import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rookieui.contracts.host_source_basis import HOST_SOURCE_BASIS
from scripts.run_current_host_contract_lane import (
    REQUIRED_CASE_IDS,
    build_lane_commands,
    load_and_validate_manifest,
    main,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tests" / "fixtures" / "current_host_risk_contract.json"
CI_PATH = ROOT / ".github" / "workflows" / "ci.yml"
EXPECTED_SOURCES = {
    "core": "5cc026f5b81b3f01fe7a1438a0fd4131d2ebda25",
    "frontend": "e1718dacb7bd8afeff41f00069747ff55065bf50",
    "desktop": "e2d964b7456cea8423c7b9d3371c612313c06baa",
}
EXPECTED_ARTIFACTS = {
    ("core", "server.py"): (
        64758,
        "74573b10465505b88b618da86059878e3a56418f84c7dae4073c8824aee35a6c",
    ),
    ("core", "app/user_manager.py"): (
        20149,
        "28c89ca744702721839c586e9851a5abf9ff6057234be779dc1b72a2be9ef308",
    ),
    ("frontend", "src/types/extensionTypes.ts"): (
        3753,
        "bbd1f4b8d05fd3f49f39082b536680ba20e737cef2266220af7adfb23a87f307",
    ),
    ("frontend", "src/components/common/ExtensionSlot.vue"): (
        766,
        "f2f0e957102c8ab56830eb58caa297466f3bf8ad3b8b4096f482c03c1d8b3f3a",
    ),
    ("frontend", "src/stores/workspace/sidebarTabStore.ts"): (
        5835,
        "de4f2eb9b9d0edebafc9b0ca679f3565893b40d5a658eb37f19301d1811d2bb7",
    ),
}


class CurrentHostContractLaneTests(unittest.TestCase):
    def test_manifest_pins_exact_source_basis_and_artifacts(self) -> None:
        report = load_and_validate_manifest(MANIFEST_PATH)
        self.assertEqual(report["fixture_version"], "current-host-risk-lane-v2")
        self.assertEqual(report["sources"], EXPECTED_SOURCES)
        self.assertEqual(report["sources"]["core"], HOST_SOURCE_BASIS.core.revision)
        self.assertEqual(report["sources"]["frontend"], HOST_SOURCE_BASIS.frontend.revision)
        self.assertEqual(report["sources"]["desktop"], HOST_SOURCE_BASIS.desktop.revision)
        self.assertEqual(set(report["case_ids"]), REQUIRED_CASE_IDS)

        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        artifacts = manifest["source_artifacts"]
        self.assertEqual(len(artifacts), 5)
        actual_artifacts = {}
        for artifact in artifacts:
            self.assertRegex(artifact["sha256"], re.compile(r"^[0-9a-f]{64}$"))
            self.assertGreater(artifact["bytes"], 0)
            self.assertIn(artifact["source"], {"core", "frontend"})
            actual_artifacts[(artifact["source"], artifact["path"])] = (
                artifact["bytes"],
                artifact["sha256"],
            )
        self.assertEqual(actual_artifacts, EXPECTED_ARTIFACTS)
        self.assertIn(
            report["reference_verification"],
            {"verified", "unavailable-fixture-only"},
        )
        if report["reference_verification"] == "verified":
            self.assertEqual(len(report["verified_artifacts"]), 5)
        else:
            self.assertEqual(report["verified_artifacts"], [])

    def test_validator_fails_closed_on_reference_revision_and_file_drift(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            manifest_path = temp_root / "manifest.json"
            source_roots = {
                name: temp_root / name for name in ("core", "frontend", "desktop")
            }
            for source_root in source_roots.values():
                source_root.mkdir()
            for artifact in manifest["source_artifacts"]:
                source = artifact["source"]
                relative_path = Path(artifact["path"])
                target = source_roots[source] / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                content = f"{source}:{artifact['path']}".encode()
                target.write_bytes(content)
                artifact["bytes"] = len(content)
                artifact["sha256"] = hashlib.sha256(content).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            revision_reader = lambda path: EXPECTED_SOURCES[path.name]
            report = load_and_validate_manifest(
                manifest_path,
                source_roots=source_roots,
                revision_reader=revision_reader,
            )
            self.assertEqual(len(report["verified_artifacts"]), 5)
            self.assertEqual(report["reference_verification"], "verified")

            with self.subTest("revision mismatch"):
                with self.assertRaisesRegex(ValueError, "revision"):
                    load_and_validate_manifest(
                        manifest_path,
                        source_roots=source_roots,
                        revision_reader=lambda path: "0" * 40 if path.name == "core" else EXPECTED_SOURCES[path.name],
                    )

            with self.subTest("byte/hash mismatch"):
                (source_roots["core"] / "server.py").write_bytes(b"drift")
                with self.assertRaisesRegex(ValueError, "artifact"):
                    load_and_validate_manifest(
                        manifest_path,
                        source_roots=source_roots,
                        revision_reader=revision_reader,
                    )

            with self.subTest("missing artifact"):
                (source_roots["core"] / "server.py").write_bytes(
                    b"core:server.py"
                )
                (source_roots["frontend"] / "src/types/extensionTypes.ts").unlink()
                with self.assertRaisesRegex(ValueError, "artifact"):
                    load_and_validate_manifest(
                        manifest_path,
                        source_roots=source_roots,
                        revision_reader=revision_reader,
                    )

    def test_validator_rejects_unsafe_artifact_paths_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            for name, mutate, expected_error in (
                (
                    "unsafe-path",
                    lambda value: value["source_artifacts"][0].update(
                        {"path": "../escape.py"}
                    ),
                    "path",
                ),
                (
                    "missing-case",
                    lambda value: value["case_ids"].pop(),
                    "risk cases",
                ),
                (
                    "duplicate-artifact",
                    lambda value: value["source_artifacts"].__setitem__(
                        1, value["source_artifacts"][0].copy()
                    ),
                    "duplicate",
                ),
            ):
                with self.subTest(name):
                    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
                    mutate(manifest)
                    manifest_path = Path(temporary_directory) / f"{name}.json"
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, expected_error):
                        load_and_validate_manifest(manifest_path, source_roots={})

    def test_default_reference_binding_distinguishes_absent_from_partial_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            source_roots = {
                name: temp_root / name for name in ("core", "frontend", "desktop")
            }
            with patch(
                "scripts.run_current_host_contract_lane.DEFAULT_SOURCE_ROOTS",
                source_roots,
            ):
                report = load_and_validate_manifest(MANIFEST_PATH)
                self.assertEqual(
                    report["reference_verification"],
                    "unavailable-fixture-only",
                )
                source_roots["core"].mkdir()
                with self.assertRaisesRegex(ValueError, "partially"):
                    load_and_validate_manifest(MANIFEST_PATH)

    def test_lane_commands_are_targeted_and_include_no_inference(self) -> None:
        commands = build_lane_commands(ROOT)
        rendered = "\n".join(" ".join(command) for command in commands)
        self.assertIn("tests.test_prompt_submission", rendered)
        self.assertIn("tests.test_route_deployment_boundary", rendered)
        self.assertIn("rookieui_runtime_lifecycle.test.js", rendered)
        self.assertIn("sidebar_lifecycle.spec.js", rendered)
        self.assertNotIn("run_live_smoke_tests", rendered)
        self.assertNotIn("model", rendered.lower())

    def test_report_cannot_claim_pass_for_skipped_or_failed_commands(self) -> None:
        base_report = {
            "fixture_version": "current-host-risk-lane-v2",
            "sources": EXPECTED_SOURCES,
            "case_ids": sorted(REQUIRED_CASE_IDS),
            "verified_artifacts": [],
        }

        skipped_reports = []
        with (
            patch(
                "scripts.run_current_host_contract_lane.load_and_validate_manifest",
                return_value=base_report,
            ),
            patch(
                "scripts.run_current_host_contract_lane.build_lane_commands",
                return_value=[],
            ),
            patch(
                "scripts.run_current_host_contract_lane._write_report",
                side_effect=lambda report: skipped_reports.append(report.copy()),
            ),
        ):
            self.assertEqual(main(), 1)
        self.assertFalse(skipped_reports[-1]["lane_ran"])
        self.assertEqual(skipped_reports[-1]["status"], "failed")

        failed_reports = []
        with (
            patch(
                "scripts.run_current_host_contract_lane.load_and_validate_manifest",
                return_value=base_report,
            ),
            patch(
                "scripts.run_current_host_contract_lane._run_command",
                side_effect=RuntimeError("deterministic failure"),
            ),
            patch(
                "scripts.run_current_host_contract_lane._write_report",
                side_effect=lambda report: failed_reports.append(json.loads(json.dumps(report))),
            ),
        ):
            self.assertEqual(main(), 1)
        self.assertFalse(failed_reports[-1]["lane_ran"])
        self.assertEqual(failed_reports[-1]["status"], "failed")
        self.assertEqual(failed_reports[-1]["commands"][0]["status"], "failed")

    def test_passing_report_uses_portable_command_identities(self) -> None:
        reports = []
        base_report = {
            "fixture_version": "current-host-risk-lane-v2",
            "sources": EXPECTED_SOURCES,
            "case_ids": sorted(REQUIRED_CASE_IDS),
            "verified_artifacts": [],
        }
        with (
            patch(
                "scripts.run_current_host_contract_lane.load_and_validate_manifest",
                return_value=base_report,
            ),
            patch("scripts.run_current_host_contract_lane._run_command"),
            patch(
                "scripts.run_current_host_contract_lane._write_report",
                side_effect=lambda report: reports.append(json.loads(json.dumps(report))),
            ),
        ):
            self.assertEqual(main(), 0)
        report = reports[-1]
        self.assertTrue(report["lane_ran"])
        self.assertEqual(report["status"], "passed")
        self.assertEqual(len(report["commands"]), 3)
        self.assertTrue(all(item["status"] == "passed" for item in report["commands"]))
        self.assertNotIn(str(ROOT), json.dumps(report))

    def test_ci_requires_lane_before_full_gate_and_publish(self) -> None:
        workflow = CI_PATH.read_text(encoding="utf-8")
        lane_marker = "Run required current-host contract lane"
        full_marker = "Run full test gate"
        self.assertIn(lane_marker, workflow)
        self.assertLess(workflow.index(full_marker), workflow.index(lane_marker))
        self.assertIn(".venv/bin/python scripts/run_current_host_contract_lane.py", workflow)
        self.assertRegex(workflow, re.compile(r"publish-node:[\s\S]+needs: full-test-gate"))


if __name__ == "__main__":
    unittest.main()
