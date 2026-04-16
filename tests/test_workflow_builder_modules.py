from __future__ import annotations

import importlib
import unittest

from rookieui.contracts.extensibility import build_extensibility_refactor_manifest


class WorkflowBuilderModuleTests(unittest.TestCase):
    def test_workflow_builder_target_modules_import_without_cycles(self) -> None:
        manifest = build_extensibility_refactor_manifest()
        workflow_boundary = next(
            boundary
            for boundary in manifest["boundaries"]
            if boundary["feature_id"] == "workflow_translation"
        )
        imported_modules = [
            importlib.import_module(module_name)
            for module_name in workflow_boundary["target_modules"]
        ]
        self.assertEqual(len(imported_modules), len(workflow_boundary["target_modules"]))

    def test_workflow_translation_facade_keeps_public_entrypoints(self) -> None:
        workflow_translation = importlib.import_module("rookieui.services.workflow_translation")
        self.assertTrue(callable(workflow_translation.build_txt2img_workflow))
        self.assertTrue(callable(workflow_translation.build_img2img_workflow))
        self.assertTrue(callable(workflow_translation.translate_txt2img_request))
        self.assertTrue(callable(workflow_translation.translate_img2img_request))
