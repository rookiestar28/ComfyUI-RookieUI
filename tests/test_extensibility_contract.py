from __future__ import annotations

from pathlib import Path
import unittest

from rookieui.contracts.extensibility import (
    EXTENSIBILITY_REFACTOR_CONTRACT_VERSION,
    boundary_target_module_paths,
    boundary_target_paths,
    build_extensibility_refactor_manifest,
)


class ExtensibilityContractTests(unittest.TestCase):
    def test_manifest_exposes_phase_59_boundaries(self) -> None:
        manifest = build_extensibility_refactor_manifest()

        self.assertEqual(manifest["version"], EXTENSIBILITY_REFACTOR_CONTRACT_VERSION)
        boundaries = manifest["boundaries"]
        self.assertEqual(
            [entry["feature_id"] for entry in boundaries],
            [
                "workflow_translation",
                "controlnet",
                "adetailer",
                "integrated_feature_bootstrap",
            ],
        )

    def test_manifest_uses_expected_validation_modes(self) -> None:
        manifest = build_extensibility_refactor_manifest()
        validation_by_feature = {entry["feature_id"]: tuple(entry["validation_modes"]) for entry in manifest["boundaries"]}

        self.assertEqual(validation_by_feature["workflow_translation"], ("full-gate", "translation-topology"))
        self.assertEqual(validation_by_feature["controlnet"], ("full-gate", "controlnet", "full-pipeline"))
        self.assertEqual(validation_by_feature["adetailer"], ("full-gate", "adetailer", "full-pipeline"))
        self.assertEqual(validation_by_feature["integrated_feature_bootstrap"], ("full-gate", "full-pipeline"))

    def test_manifest_facades_resolve_to_existing_files(self) -> None:
        resolved_paths = boundary_target_paths()
        repo_root = Path(__file__).resolve().parents[1]

        for resolved_path in resolved_paths:
            self.assertTrue(
                resolved_path.exists(),
                msg=f"Expected extensibility facade path '{resolved_path.relative_to(repo_root)}' to exist.",
            )

    def test_manifest_target_modules_resolve_to_existing_files(self) -> None:
        resolved_paths = boundary_target_module_paths()
        repo_root = Path(__file__).resolve().parents[1]

        for resolved_path in resolved_paths:
            self.assertTrue(
                resolved_path.exists(),
                msg=f"Expected extensibility target path '{resolved_path.relative_to(repo_root)}' to exist.",
            )
