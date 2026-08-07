from __future__ import annotations

import copy
import unittest
from pathlib import Path

from scripts.architecture_conformance import (
    load_contract,
    normalize_repo_path,
    snapshot_repository,
    validate_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "tests" / "architecture_contract.json"


class ArchitectureConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_contract(CONTRACT_PATH)
        cls.snapshot = snapshot_repository(ROOT, cls.contract)

    def assert_violation(self, files: dict[str, str], code: str) -> None:
        violations = validate_snapshot(files, self.contract)
        self.assertIn(code, {violation.code for violation in violations}, violations)

    def test_current_repository_satisfies_the_architecture_contract(self) -> None:
        self.assertEqual(validate_snapshot(self.snapshot, self.contract), [])

    def test_normalizes_windows_and_posix_paths(self) -> None:
        self.assertEqual(normalize_repo_path(r"web\api\rookieui_queue_api.js"), "web/api/rookieui_queue_api.js")

    def test_rejects_backend_cross_domain_import(self) -> None:
        files = copy.deepcopy(self.snapshot)
        files["rookieui/api/domains/queue.py"] += "\nfrom rookieui.api.domains.generation import txt2img\n"
        self.assert_violation(files, "CROSS_DOMAIN_IMPORT")

    def test_rejects_backend_relative_sibling_imports_at_supported_depths(self) -> None:
        for statement in (
            "from .generation import txt2img",
            "from . import generation",
            "from ..domains.generation import txt2img",
        ):
            with self.subTest(statement=statement):
                files = copy.deepcopy(self.snapshot)
                files["rookieui/api/domains/queue.py"] += f"\n{statement}\n"
                self.assert_violation(files, "CROSS_DOMAIN_IMPORT")

    def test_allows_reviewed_backend_edge_through_relative_import(self) -> None:
        files = copy.deepcopy(self.snapshot)
        path = "rookieui/api/domains/inventory_capability.py"
        files[path] += "\nfrom .health_bootstrap import build_bootstrap\n"
        self.assertEqual(validate_snapshot(files, self.contract), [])

    def test_rejects_frontend_cross_domain_or_facade_import(self) -> None:
        files = copy.deepcopy(self.snapshot)
        files["web/api/rookieui_queue_api.js"] += '\nimport { fetchRookieUIModels } from "./rookieui_inventory_api.js";\n'
        self.assert_violation(files, "CROSS_DOMAIN_IMPORT")
        files = copy.deepcopy(self.snapshot)
        files["web/api/rookieui_queue_api.js"] += '\nimport * as facade from "../rookieui_api.js";\n'
        self.assert_violation(files, "FACADE_BACK_IMPORT")

    def test_rejects_frontend_side_effect_import_edges(self) -> None:
        files = copy.deepcopy(self.snapshot)
        files["web/api/rookieui_queue_api.js"] += '\nimport "./rookieui_inventory_api.js";\n'
        self.assert_violation(files, "CROSS_DOMAIN_IMPORT")
        files = copy.deepcopy(self.snapshot)
        files["web/api/rookieui_queue_api.js"] += '\nimport "../rookieui_api.js";\n'
        self.assert_violation(files, "FACADE_BACK_IMPORT")

    def test_rejects_all_supported_frontend_dependency_forms(self) -> None:
        statements = (
            'import inventory from "./rookieui_inventory_api.js";',
            'const inventory = await import("./rookieui_inventory_api.js");',
            'export { inventory } from "./rookieui_inventory_api.js";',
            'export * from "./rookieui_inventory_api.js";',
        )
        for statement in statements:
            with self.subTest(statement=statement):
                files = copy.deepcopy(self.snapshot)
                files["web/api/rookieui_queue_api.js"] += f"\n{statement}\n"
                self.assert_violation(files, "CROSS_DOMAIN_IMPORT")

    def test_allows_reviewed_and_bare_side_effect_dependencies(self) -> None:
        files = copy.deepcopy(self.snapshot)
        files["web/api/rookieui_queue_api.js"] += '\nimport "./rookieui_api_transport.js";\nimport "public-package";\n'
        self.assertEqual(validate_snapshot(files, self.contract), [])

    def test_ignores_import_like_comments_strings_and_templates(self) -> None:
        files = copy.deepcopy(self.snapshot)
        files["web/api/rookieui_queue_api.js"] += r'''
// import "./rookieui_inventory_api.js";
const quotedExample = 'import value from "./rookieui_inventory_api.js"';
const templateExample = `import "./rookieui_inventory_api.js"`;
/* export { value } from "./rookieui_inventory_api.js"; */
'''
        self.assertEqual(validate_snapshot(files, self.contract), [])

    def test_rejects_moving_domain_logic_to_an_unreviewed_dependency(self) -> None:
        files = copy.deepcopy(self.snapshot)
        files["web/hidden_queue_logic.js"] = "export const hidden = true;\n"
        files["web/api/rookieui_queue_api.js"] += '\nimport { hidden } from "../hidden_queue_logic.js";\n'
        self.assert_violation(files, "FORBIDDEN_DOMAIN_DEPENDENCY")

    def test_allows_accepted_facade_composition(self) -> None:
        files = copy.deepcopy(self.snapshot)
        self.assertNotIn("CROSS_DOMAIN_IMPORT", {item.code for item in validate_snapshot(files, self.contract)})
        self.assertNotIn("FACADE_BACK_IMPORT", {item.code for item in validate_snapshot(files, self.contract)})

    def test_rejects_handler_logic_in_composition_root(self) -> None:
        files = copy.deepcopy(self.snapshot)
        files["rookieui/api/route_spec.py"] += "\ndef accidental_handler(request):\n    return request\n"
        self.assert_violation(files, "COMPOSITION_HANDLER_LOGIC")

    def test_rejects_missing_required_composition_function(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["composition_roots"]["rookieui/api/route_spec.py"]["required_functions"] = ["register_routes"]
        files = copy.deepcopy(self.snapshot)
        files["rookieui/api/route_spec.py"] = files["rookieui/api/route_spec.py"].replace(
            "def register_routes(", "def removed_register_routes("
        )
        self.assertIn(
            "COMPOSITION_REQUIRED_FUNCTION_MISSING",
            {violation.code for violation in validate_snapshot(files, contract)},
        )

    def test_rejects_alternate_family_truth_and_incomplete_projection(self) -> None:
        files = copy.deepcopy(self.snapshot)
        files["rookieui/contracts/alternate_family.py"] = "FAMILY_TEMPLATE_MANIFEST = ()\n"
        self.assert_violation(files, "ALTERNATE_FAMILY_TRUTH")
        files = copy.deepcopy(self.snapshot)
        files["rookieui/contracts/family_profile_projection.py"] = files[
            "rookieui/contracts/family_profile_projection.py"
        ].replace("validate_runtime_adapter_bindings", "removed_adapter_binding_validator")
        self.assert_violation(files, "PROJECTION_CONTRACT_MISSING")

    def test_rejects_missing_controller_or_lifecycle_disposal(self) -> None:
        files = copy.deepcopy(self.snapshot)
        path = "web/sidebar_tabs/img2img/rookieui_img2img_lifecycle.js"
        files[path] = files[path].replace("destroy(...timerMaps)", "close(...timerMaps)")
        self.assert_violation(files, "DISPOSAL_CONTRACT_MISSING")

    def test_rejects_api_export_drift(self) -> None:
        files = copy.deepcopy(self.snapshot)
        files["web/api/rookieui_queue_api.js"] = files["web/api/rookieui_queue_api.js"].replace(
            "export async function fetchRookieUIQueue(", "async function fetchRookieUIQueue("
        )
        self.assert_violation(files, "API_FACADE_EXPORT_DRIFT")

    def test_rejects_reduced_typed_coverage_or_test_exclusion(self) -> None:
        files = copy.deepcopy(self.snapshot)
        files["tsconfig.json"] = files["tsconfig.json"].replace(
            '    "web/api/rookieui_queue_api.js",\n', ""
        )
        self.assert_violation(files, "TYPED_COVERAGE_REDUCED")
        files = copy.deepcopy(self.snapshot)
        files["package.json"] = files["package.json"].replace("vitest run", "vitest run --exclude architecture")
        self.assert_violation(files, "TEST_DISCOVERY_WEAKENED")

    def test_rejects_unlisted_or_packed_governed_source(self) -> None:
        files = copy.deepcopy(self.snapshot)
        files["web/api/rookieui_hidden_api.js"] = "export const hidden = true;\n"
        self.assert_violation(files, "UNLISTED_GOVERNED_FILE")
        files = copy.deepcopy(self.snapshot)
        path = "web/api/rookieui_queue_api.js"
        files[path] = files[path].replace("\n", "")
        self.assert_violation(files, "SOURCE_PACKING_DETECTED")

    def test_rejects_missing_existing_guard(self) -> None:
        files = copy.deepcopy(self.snapshot)
        del files["scripts/check_public_release_boundary.py"]
        self.assert_violation(files, "REQUIRED_GUARD_MISSING")

    def test_rejects_individual_and_combined_enforcement_artifact_removal(self) -> None:
        artifacts = [
            "scripts/architecture_conformance.py",
            "scripts/check_architecture_conformance.py",
            "tests/architecture_contract.json",
            "tests/test_architecture_conformance.py",
        ]
        contract = copy.deepcopy(self.contract)
        contract["required_enforcement_artifacts"] = artifacts
        for artifact in artifacts:
            with self.subTest(artifact=artifact):
                files = copy.deepcopy(self.snapshot)
                del files[artifact]
                self.assertIn(
                    "ENFORCEMENT_ARTIFACT_MISSING",
                    {violation.code for violation in validate_snapshot(files, contract)},
                )
        files = copy.deepcopy(self.snapshot)
        for artifact in artifacts:
            del files[artifact]
        self.assertIn(
            "ENFORCEMENT_ARTIFACT_MISSING",
            {violation.code for violation in validate_snapshot(files, contract)},
        )

    def test_full_wrappers_invoke_the_conformance_cli_independently(self) -> None:
        windows_wrapper = (ROOT / "scripts" / "run_full_tests_windows.ps1").read_text(encoding="utf-8")
        linux_wrapper = (ROOT / "scripts" / "pre_push_checks.sh").read_text(encoding="utf-8")
        self.assertIn("scripts/check_architecture_conformance.py", windows_wrapper)
        self.assertIn("scripts/check_architecture_conformance.py", linux_wrapper)


if __name__ == "__main__":
    unittest.main()
