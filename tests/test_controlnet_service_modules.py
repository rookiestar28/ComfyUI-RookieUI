from __future__ import annotations

import importlib
import unittest


class ControlNetServiceModuleTests(unittest.TestCase):
    def test_controlnet_vertical_modules_import_without_cycles(self) -> None:
        module_names = (
            "rookieui.services.controlnet_warnings",
            "rookieui.services.controlnet_catalog",
            "rookieui.services.controlnet_normalization",
            "rookieui.services.controlnet_detect",
        )
        imported_modules = [importlib.import_module(module_name) for module_name in module_names]
        self.assertEqual(len(imported_modules), len(module_names))

    def test_controlnet_facade_keeps_public_functions(self) -> None:
        controlnet = importlib.import_module("rookieui.services.controlnet")
        self.assertTrue(callable(controlnet.normalize_controlnet_units))
        self.assertTrue(callable(controlnet.build_controlnet_module_list_payload))
        self.assertTrue(callable(controlnet.build_controlnet_model_list_payload))
        self.assertTrue(callable(controlnet.build_controlnet_control_types_payload))
        self.assertTrue(callable(controlnet.build_controlnet_detect_payload))
