from __future__ import annotations

import importlib
from pathlib import Path
import unittest

from rookieui.contracts.extensibility import build_extensibility_refactor_manifest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PYTHON_FACADE_LINE_BUDGETS = {
    "rookieui.services.workflow_translation": 750,
    "rookieui.services.controlnet": 160,
    "rookieui.services.adetailer": 140,
    "rookieui.services.integrated_feature_registry": 120,
}


def _module_path(module_name: str) -> Path:
    return (_REPO_ROOT / Path(*module_name.split("."))).with_suffix(".py")


class Phase59RefactorGuardrailTests(unittest.TestCase):
    def test_all_python_target_modules_import_without_cycles(self) -> None:
        manifest = build_extensibility_refactor_manifest()
        python_targets = [
            module_name
            for boundary in manifest["boundaries"]
            for module_name in boundary["target_modules"]
            if not str(module_name).endswith(".js")
        ]

        imported_modules = [importlib.import_module(module_name) for module_name in python_targets]
        self.assertEqual(len(imported_modules), len(python_targets))

    def test_phase59_python_facades_stay_within_size_budgets(self) -> None:
        # IMPORTANT: these budgets are the phase-59 anti-regression tripwire; if a facade grows past budget,
        # extract another seam instead of accreting helpers back into the monolith.
        for module_name, max_lines in _PYTHON_FACADE_LINE_BUDGETS.items():
            line_count = len(_module_path(module_name).read_text(encoding="utf-8").splitlines())
            self.assertLessEqual(
                line_count,
                max_lines,
                msg=f"Expected '{module_name}' to stay within {max_lines} lines after phase-59 refactor closeout.",
            )
