from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest

from rookieui.contracts.family_template_manifest import (
    OFFICIAL_TEMPLATE_DEFERRED_SURFACE_MARKERS,
    get_family_template_manifest_entry,
    list_non_sd_manifest_entries,
)
from rookieui.contracts.host_source_basis import HOST_SOURCE_BASIS
from rookieui.services.ideogram4 import IDEOGRAM4_MODE_CONTRACTS


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
BUILDER_PATHS = (
    ROOT / "rookieui" / "services" / "workflow_builders" / "core.py",
    ROOT / "rookieui" / "services" / "workflow_builders" / "image_edit_foundation.py",
    ROOT / "rookieui" / "services" / "workflow_builders" / "non_sd_templates.py",
    ROOT / "rookieui" / "services" / "workflow_builders" / "output.py",
)
LOCAL_NODE_CLASSES = {
    "RookieUILoadAssetImage",
    "RookieUILoadAssetMask",
    "RookieUISaveImageWithMetadata",
}
DEFERRED_PROFILE_IDS = {
    "klein_4b_distilled",
    "klein_9b_distilled",
    "qwen_image_edit_multi_lora",
}


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _literal_emitted_classes_and_nodes() -> tuple[set[str], list[tuple[str, set[str]]]]:
    emitted: set[str] = set()
    literal_nodes: list[tuple[str, set[str]]] = []
    for path in BUILDER_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if (
                        keyword.arg == "class_type"
                        and isinstance(keyword.value, ast.Constant)
                        and isinstance(keyword.value.value, str)
                    ):
                        emitted.add(keyword.value.value)
            if not isinstance(node, ast.Dict):
                continue
            fields = {
                key.value: value
                for key, value in zip(node.keys, node.values)
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            class_value = fields.get("class_type")
            inputs_value = fields.get("inputs")
            if not (
                isinstance(class_value, ast.Constant)
                and isinstance(class_value.value, str)
                and isinstance(inputs_value, ast.Dict)
            ):
                continue
            input_keys = {
                key.value
                for key in inputs_value.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            emitted.add(class_value.value)
            literal_nodes.append((class_value.value, input_keys))
    return emitted, literal_nodes


class CurrentHostGraphContractTests(unittest.TestCase):
    def test_every_shipped_profile_has_exact_current_source_provenance(self) -> None:
        fixture = _load_fixture("comfyui_0_11_6_profile_sources.json")
        self.assertEqual(fixture["core_revision"], HOST_SOURCE_BASIS.core.revision)
        self.assertEqual(fixture["workflow_templates_json_version"], "0.1.3")
        expected_profiles = fixture["profiles"]
        entries = {entry.id: entry for entry in list_non_sd_manifest_entries()}
        self.assertEqual(set(entries), set(expected_profiles))
        for profile_id, source in expected_profiles.items():
            with self.subTest(profile_id=profile_id):
                self.assertEqual(entries[profile_id].official_template_path, source["locator"])
                self.assertIn(source["source_kind"], {"core-blueprint", "workflow-template-package"})
                self.assertEqual(len(source["sha256"]), 64)
                self.assertNotIn("latest", source["locator"].lower())

    def test_unverified_profiles_fail_closed_and_remain_deferred(self) -> None:
        shipped_ids = {entry.id for entry in list_non_sd_manifest_entries()}
        self.assertFalse(DEFERRED_PROFILE_IDS & shipped_ids)
        for profile_id in DEFERRED_PROFILE_IDS:
            with self.subTest(profile_id=profile_id):
                self.assertIn(profile_id, OFFICIAL_TEMPLATE_DEFERRED_SURFACE_MARKERS)
                with self.assertRaises(ValueError):
                    get_family_template_manifest_entry(profile_id)

    def test_all_literal_emitted_host_classes_and_inputs_match_current_contract(self) -> None:
        fixture = _load_fixture("comfyui_0_11_6_node_contract.json")
        self.assertEqual(fixture["source_revision"], HOST_SOURCE_BASIS.core.revision)
        contracts = fixture["classes"]
        emitted, literal_nodes = _literal_emitted_classes_and_nodes()
        self.assertFalse(emitted - set(contracts) - LOCAL_NODE_CLASSES)

        for class_type, emitted_inputs in literal_nodes:
            if class_type in LOCAL_NODE_CLASSES:
                continue
            with self.subTest(class_type=class_type, emitted_inputs=sorted(emitted_inputs)):
                source_inputs = contracts[class_type]["inputs"]
                allowed = set(source_inputs)
                required = {name for name, spec in source_inputs.items() if not spec["optional"]}
                dynamic_prefixes = {
                    f"{name}."
                    for name, spec in source_inputs.items()
                    if spec["type"] == "DYNAMICCOMBO"
                }
                unknown_inputs = {
                    name
                    for name in emitted_inputs - allowed
                    if not any(name.startswith(prefix) for prefix in dynamic_prefixes)
                }
                self.assertFalse(unknown_inputs)
                self.assertTrue(required <= emitted_inputs)

    def test_source_sensitive_ideogram_scheduler_defaults_are_current(self) -> None:
        contracts = _load_fixture("comfyui_0_11_6_node_contract.json")["classes"]
        scheduler_inputs = contracts["Ideogram4Scheduler"]["inputs"]
        self.assertEqual(scheduler_inputs["steps"]["default"], 20)
        self.assertEqual(scheduler_inputs["width"]["default"], 1024)
        self.assertEqual(scheduler_inputs["height"]["default"], 1024)
        default_contract = IDEOGRAM4_MODE_CONTRACTS["default"]
        self.assertEqual(default_contract.mu, scheduler_inputs["mu"]["default"])
        self.assertEqual(default_contract.std, scheduler_inputs["std"]["default"])


if __name__ == "__main__":
    unittest.main()
