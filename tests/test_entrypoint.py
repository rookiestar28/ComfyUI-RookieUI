from __future__ import annotations

import importlib.util
import pathlib
import re
import sys
import unittest


class EntryPointTests(unittest.TestCase):
    def test_entrypoint_exports_bootstrap_contract(self) -> None:
        root_dir = pathlib.Path(__file__).resolve().parents[1]
        module_path = root_dir / "__init__.py"
        spec = importlib.util.spec_from_file_location("rookieui_entrypoint_test", module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)

        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(spec.name, None)

        self.assertEqual(module.WEB_DIRECTORY, "./web")
        self.assertIn("RookieUILoadAssetImage", module.NODE_CLASS_MAPPINGS)
        self.assertIn("RookieUILoadAssetMask", module.NODE_CLASS_MAPPINGS)
        self.assertIn("RookieUILoadAssetImage", module.NODE_DISPLAY_NAME_MAPPINGS)
        self.assertIn("RookieUILoadAssetMask", module.NODE_DISPLAY_NAME_MAPPINGS)

    def test_pyproject_declares_current_comfy_web_metadata_without_dropping_legacy_web_directory(self) -> None:
        root_dir = pathlib.Path(__file__).resolve().parents[1]
        pyproject_text = (root_dir / "pyproject.toml").read_text(encoding="utf-8")
        # IMPORTANT: keep this test dependency-free on the supported Python 3.10 floor.
        comfy_section = re.search(
            r"(?ms)^\[tool\.comfy\]\s*$\n(?P<body>.*?)(?=^\[|\Z)",
            pyproject_text,
        )

        self.assertIsNotNone(comfy_section)
        self.assertRegex(comfy_section.group("body"), r'(?m)^web\s*=\s*"web"\s*$')
