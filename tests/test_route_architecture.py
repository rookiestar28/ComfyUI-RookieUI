from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ROUTES_SOURCE = ROOT / "rookieui" / "api" / "routes.py"


class RouteArchitectureTests(unittest.TestCase):
    """Ownership gates for route extraction; these intentionally fail before extraction."""

    def test_authoritative_route_spec_and_explicit_domains_exist(self) -> None:
        from rookieui.api import route_spec

        expected_domains = {
            "health_bootstrap",
            "inventory_capability",
            "generation",
            "prompt_workbench",
            "controlnet",
            "xyz_plot",
            "pnginfo_extras",
            "queue",
        }
        self.assertEqual(
            {spec.domain for spec in route_spec.AUTHORITATIVE_ROUTE_SPECS},
            expected_domains,
        )
        self.assertEqual(len(route_spec.AUTHORITATIVE_ROUTE_SPECS), 43)
        self.assertEqual(len(route_spec.OPTIONAL_ALIAS_ROUTE_SPECS), 4)

    def test_route_matrix_preserves_baseline_contract(self) -> None:
        from rookieui.api import route_spec

        expected = [
            ("GET", "/health", "health", "health_bootstrap", True, "none"),
            ("GET", "/bootstrap", "bootstrap", "health_bootstrap", True, "none"),
            ("GET", "/capabilities", "capabilities", "inventory_capability", True, "none"),
            ("GET", "/parity", "parity", "inventory_capability", True, "none"),
            ("GET", "/compatibility", "compatibility", "inventory_capability", True, "none"),
            ("GET", "/models", "models", "inventory_capability", False, "none"),
            ("GET", "/presets", "presets", "inventory_capability", False, "none"),
            ("GET", "/controlnet/model_list", "controlnet_model_list", "controlnet", False, "none"),
            ("GET", "/controlnet/module_list", "controlnet_module_list", "controlnet", False, "none"),
            ("GET", "/controlnet/control_types", "controlnet_control_types", "controlnet", False, "none"),
            ("GET", "/adetailer/catalog", "adetailer_catalog", "controlnet", False, "none"),
            ("GET", "/queue", "queue", "queue", False, "none"),
            ("GET", "/queue/{prompt_id}", "queue_prompt", "queue", False, "none"),
            ("GET", "/prompt-tools/config", "prompt_tools_config", "prompt_workbench", False, "none"),
            ("POST", "/prompt-tools/config", "prompt_tools_config_update", "prompt_workbench", False, "none"),
            ("GET", "/prompt-tools/state", "prompt_tools_state", "prompt_workbench", False, "none"),
            ("POST", "/prompt-tools/state", "prompt_tools_state_update", "prompt_workbench", False, "none"),
            ("GET", "/prompt-tools/history", "prompt_tools_history", "prompt_workbench", False, "none"),
            ("POST", "/prompt-tools/history", "prompt_tools_history_update", "prompt_workbench", False, "none"),
            ("GET", "/prompt-tools/favorites", "prompt_tools_favorites", "prompt_workbench", False, "none"),
            ("POST", "/prompt-tools/favorites", "prompt_tools_favorites_update", "prompt_workbench", False, "none"),
            ("GET", "/prompt-tools/blacklist", "prompt_tools_blacklist", "prompt_workbench", False, "none"),
            ("POST", "/prompt-tools/blacklist", "prompt_tools_blacklist_update", "prompt_workbench", False, "none"),
            ("GET", "/prompt-tools/providers", "prompt_tools_providers", "prompt_workbench", False, "none"),
            ("GET", "/prompt-tools/export", "prompt_tools_export", "prompt_workbench", False, "none"),
            ("POST", "/prompt-tools/import", "prompt_tools_import", "prompt_workbench", False, "none"),
            ("POST", "/prompt-tools/translate", "prompt_tools_translate", "prompt_workbench", False, "none"),
            ("POST", "/prompt-tools/assist", "prompt_tools_assist", "prompt_workbench", False, "none"),
            ("GET", "/prompt-tools/catalog", "prompt_tools_catalog", "prompt_workbench", False, "none"),
            ("POST", "/prompt-tools/analyze", "prompt_tools_analyze", "prompt_workbench", False, "none"),
            ("POST", "/prompt-tools/upsample", "prompt_tools_upsample", "prompt_workbench", False, "none"),
            ("GET", "/xyz-plot/axes", "xyz_plot_axes", "xyz_plot", False, "none"),
            ("POST", "/xyz-plot/estimate", "xyz_plot_estimate", "xyz_plot", False, "none"),
            ("POST", "/xyz-plot/run", "xyz_plot_run", "xyz_plot", False, "none"),
            ("GET", "/xyz-plot/sessions", "xyz_plot_sessions", "xyz_plot", False, "none"),
            ("GET", "/xyz-plot/sessions/{session_id}", "xyz_plot_session_detail", "xyz_plot", False, "none"),
            ("POST", "/xyz-plot/sessions/{session_id}/cancel", "xyz_plot_session_cancel", "xyz_plot", False, "none"),
            ("POST", "/pnginfo/parse", "pnginfo_parse", "pnginfo_extras", False, "none"),
            ("POST", "/pnginfo/inspect", "pnginfo_inspect", "pnginfo_extras", False, "none"),
            ("POST", "/controlnet/detect", "controlnet_detect", "controlnet", False, "none"),
            ("POST", "/generate/txt2img", "txt2img", "generation", False, "none"),
            ("POST", "/generate/img2img", "img2img", "generation", False, "none"),
            ("POST", "/extras/run", "extras_run", "pnginfo_extras", False, "none"),
            ("GET", "/controlnet/model_list", "controlnet_model_list", "controlnet", False, "collision-isolated; disabled in multi-user mode"),
            ("GET", "/controlnet/module_list", "controlnet_module_list", "controlnet", False, "collision-isolated; disabled in multi-user mode"),
            ("GET", "/controlnet/control_types", "controlnet_control_types", "controlnet", False, "collision-isolated; disabled in multi-user mode"),
            ("POST", "/controlnet/detect", "controlnet_detect", "controlnet", False, "collision-isolated; disabled in multi-user mode"),
        ]
        actual = [
            (
                row["method"],
                row["logical_suffix"],
                row["handler_identity"],
                row["domain"],
                row["diagnostic"],
                row["optional_alias"],
            )
            for row in route_spec.build_route_matrix()
        ]
        self.assertEqual(actual, expected)
        for row in route_spec.build_route_matrix():
            expected_prefixes = (
                [row["logical_suffix"]]
                if row["optional_alias"] != "none"
                else ["/rookieui", "/api/rookieui"]
            )
            self.assertEqual(row["physical_prefixes"], expected_prefixes)

    def test_route_spec_handlers_are_owned_by_domain_modules(self) -> None:
        from rookieui.api import route_spec

        for spec in (*route_spec.AUTHORITATIVE_ROUTE_SPECS, *route_spec.OPTIONAL_ALIAS_ROUTE_SPECS):
            with self.subTest(method=spec.method, suffix=spec.suffix):
                self.assertTrue(
                    spec.handler.__module__.startswith("rookieui.api.domains."),
                    spec.handler.__module__,
                )

    def test_routes_is_the_only_router_composition_root(self) -> None:
        tree = ast.parse(ROUTES_SOURCE.read_text(encoding="utf-8"))
        register = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "register_routes"
        )
        calls = {
            node.func.attr
            for node in ast.walk(register)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"add_get", "add_post"}
        }
        self.assertEqual(calls, set(), "register_routes must delegate to the declarative spec")

    def test_each_domain_module_is_importable_without_host_startup(self) -> None:
        modules = (
            "health_bootstrap",
            "inventory_capability",
            "generation",
            "prompt_workbench",
            "controlnet",
            "xyz_plot",
            "pnginfo_extras",
            "queue",
        )
        for module in modules:
            with self.subTest(module=module):
                __import__(f"rookieui.api.domains.{module}")


if __name__ == "__main__":
    unittest.main()
