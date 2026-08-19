from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest
import zipfile

from rookieui.contracts import core_graph_contract
from rookieui.contracts import workflow_template_supported_graph_contract as supported_graph_contract
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
    ROOT / "rookieui" / "nodes.py",
    ROOT / "rookieui" / "services" / "workflow_builders" / "adetailer.py",
    ROOT / "rookieui" / "services" / "workflow_builders" / "core.py",
    ROOT / "rookieui" / "services" / "workflow_builders" / "controlnet.py",
    ROOT / "rookieui" / "services" / "workflow_builders" / "image_edit_foundation.py",
    ROOT / "rookieui" / "services" / "workflow_builders" / "non_sd_templates.py",
    ROOT / "rookieui" / "services" / "workflow_builders" / "output.py",
    ROOT / "rookieui" / "services" / "workflow_builders" / "prompt_conditioning.py",
    ROOT / "rookieui" / "services" / "workflow_builders" / "sd_family_graphs.py",
)
LOCAL_NODE_CLASSES = {
    "RookieUIADetailerDetectMask",
    "RookieUILoadAssetImage",
    "RookieUILoadAssetMask",
    "RookieUISaveImageWithMetadata",
    "RookieUIControlNetPreprocess",
    "RookieUIControlNetApplyNativeAdvanced",
    "RookieUIVAEEncodeForInpaint",
}
PROFILE_FIXTURE = "current_host_profile_sources.json"
NODE_FIXTURE = "current_host_node_contract.json"
CORE_GRAPH_FIXTURE = "current_host_core_graph_contract.json"
PROFILE_GRAPH_FIXTURE = "current_host_profile_graph_contract.json"
WORKFLOW_TEMPLATE_SUPPORTED_GRAPH_FIXTURE = (
    "current_workflow_template_supported_graph_contract.json"
)
CORE_REFERENCE = ROOT / "reference" / "ComfyUI"
TEMPLATE_JSON_WHEEL = (
    ROOT
    / "reference"
    / "workflow_templates_artifacts"
    / "0.11.43"
    / "comfyui_workflow_templates_json-0.1.49-py3-none-any.whl"
)
DEFERRED_PROFILE_IDS = {
    "krea2_image_edit",
    "krea2_style_reference",
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
            if not (isinstance(class_value, ast.Constant) and isinstance(class_value.value, str)):
                continue
            emitted.add(class_value.value)
            if not isinstance(inputs_value, ast.Dict):
                continue
            input_keys = {
                key.value
                for key in inputs_value.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            literal_nodes.append((class_value.value, input_keys))
    return emitted, literal_nodes


class CurrentHostGraphContractTests(unittest.TestCase):
    def test_workflow_template_candidate_supported_graph_contract_exists(self) -> None:
        self.assertTrue((FIXTURES / WORKFLOW_TEMPLATE_SUPPORTED_GRAPH_FIXTURE).is_file())

    def test_workflow_template_candidate_supported_graph_contract_is_exact(self) -> None:
        contract = supported_graph_contract.load_supported_graph_contract(
            FIXTURES / WORKFLOW_TEMPLATE_SUPPORTED_GRAPH_FIXTURE
        )
        self.assertEqual(
            contract.schema_version,
            "workflow-template-supported-graph-contract-v1",
        )
        self.assertEqual(contract.active_workflow_templates_version, "0.11.43")
        self.assertEqual(contract.candidate_workflow_templates_version, "0.11.43")
        self.assertEqual(contract.active_workflow_templates_json_version, "0.1.49")
        self.assertEqual(contract.candidate_workflow_templates_json_version, "0.1.49")
        self.assertEqual(
            contract.workflow_template_source_revision,
            "f54739874c88e5a1154275c4597b3860e5a617b4",
        )
        self.assertEqual(contract.workflow_template_source_tag, "v0.11.43")
        self.assertEqual(contract.active_core_revision, HOST_SOURCE_BASIS.core.revision)
        self.assertEqual(
            contract.candidate_core_revision,
            "c67885b14556cf3e4e061862925282d403d09862",
        )
        self.assertEqual(
            (
                contract.profile_count,
                contract.package_profile_count,
                contract.core_blueprint_profile_count,
                contract.unique_source_count,
            ),
            (26, 11, 15, 25),
        )
        self.assertEqual(
            tuple(profile.id for profile in contract.profiles),
            tuple(sorted(profile.id for profile in contract.profiles)),
        )
        self.assertTrue(all(profile.disposition == "invariant" for profile in contract.profiles))
        self.assertTrue(
            all(
                profile.baseline_sha256 == profile.candidate_sha256
                for profile in contract.profiles
            )
        )

    def test_workflow_template_candidate_mapping_matches_manifest_and_profile_graph(self) -> None:
        contract = supported_graph_contract.load_supported_graph_contract(
            FIXTURES / WORKFLOW_TEMPLATE_SUPPORTED_GRAPH_FIXTURE
        )
        by_id = {profile.id: profile for profile in contract.profiles}
        manifest_entries = {entry.id: entry for entry in list_non_sd_manifest_entries()}
        self.assertEqual(set(by_id), set(manifest_entries))
        profile_graph = core_graph_contract.load_profile_graph_contract(
            FIXTURES / PROFILE_GRAPH_FIXTURE
        )
        self.assertLessEqual(set(by_id), {profile.id for profile in profile_graph.profiles})
        for profile_id, entry in manifest_entries.items():
            locator = entry.official_template_path
            if locator.startswith("comfyui-workflow-templates-json=="):
                expected_source_id = locator.split(":", maxsplit=1)[1]
                expected_kind = "workflow-template-package"
            else:
                expected_source_id = Path(locator).stem
                expected_kind = "core-blueprint"
            with self.subTest(profile_id=profile_id):
                self.assertEqual(by_id[profile_id].source_id, expected_source_id)
                self.assertEqual(by_id[profile_id].source_kind, expected_kind)
                self.assertNotIn("reference", by_id[profile_id].source_id.lower())
                self.assertNotIn("/", by_id[profile_id].source_id)
                self.assertNotIn("\\", by_id[profile_id].source_id)

    def test_workflow_template_candidate_contract_is_canonical_and_fail_closed(self) -> None:
        path = FIXTURES / WORKFLOW_TEMPLATE_SUPPORTED_GRAPH_FIXTURE
        text = path.read_text(encoding="utf-8")
        contract = supported_graph_contract.parse_supported_graph_contract_text(text)
        self.assertEqual(
            supported_graph_contract.serialize_supported_graph_contract(contract),
            text,
        )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            supported_graph_contract.parse_supported_graph_contract_text(
                '{"schema_version":"workflow-template-supported-graph-contract-v1",'
                '"schema_version":"duplicate"}'
            )
        payload = json.loads(text)
        payload["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown"):
            supported_graph_contract.parse_supported_graph_contract_text(json.dumps(payload))
        payload = json.loads(text)
        payload["profile_count"] += 1
        with self.assertRaisesRegex(ValueError, "profile_count"):
            supported_graph_contract.parse_supported_graph_contract_text(json.dumps(payload))
        payload = json.loads(text)
        payload["profiles"][0]["disposition"] = "changed"
        with self.assertRaisesRegex(ValueError, "disposition"):
            supported_graph_contract.parse_supported_graph_contract_text(json.dumps(payload))
        payload = json.loads(text)
        payload["profiles"][0]["source_id"] = "C:\\private\\source.json"
        with self.assertRaisesRegex(ValueError, "source_id"):
            supported_graph_contract.parse_supported_graph_contract_text(json.dumps(payload))

    def test_candidate_core_graph_contract_is_complete_and_provenance_bound(self) -> None:
        contract = core_graph_contract.load_core_graph_contract(
            FIXTURES / CORE_GRAPH_FIXTURE
        )

        self.assertEqual(contract.schema_version, "current-host-core-graph-contract-v1")
        self.assertEqual(contract.baseline_revision, "6f7cd7fceaaf60d2669b554936394a7412c6fde5")
        self.assertEqual(contract.source_revision, "c67885b14556cf3e4e061862925282d403d09862")
        self.assertEqual(contract.inventory.source_file_count, 21)
        self.assertEqual(contract.inventory.class_count, 59)
        self.assertEqual(contract.inventory.input_count, 185)
        self.assertEqual(contract.inventory.changed_source_file_count, 5)
        self.assertEqual(contract.inventory.changed_class_count, 35)
        self.assertEqual(len(contract.source_files), 21)
        self.assertEqual(len(contract.classes), 59)
        self.assertEqual(
            sum(len(class_contract.inputs) for class_contract in contract.classes.values()),
            185,
        )
        self.assertIn("CLIPTextEncode", contract.classes)
        self.assertIn("CLIPTextEncodeSDXL", contract.classes)

        for class_type, class_contract in contract.classes.items():
            with self.subTest(class_type=class_type):
                self.assertEqual(class_contract.source_revision, contract.source_revision)
                self.assertRegex(class_contract.source_blob, re.compile(r"^[0-9a-f]{40}$"))
                self.assertRegex(class_contract.source_sha256, re.compile(r"^[0-9a-f]{64}$"))
                self.assertIn(class_contract.source_path, contract.source_files)
                self.assertIn(
                    class_type,
                    contract.source_files[class_contract.source_path].classes,
                )

    def test_candidate_core_graph_separates_byte_and_covered_signature_drift(self) -> None:
        contract = core_graph_contract.load_core_graph_contract(
            FIXTURES / CORE_GRAPH_FIXTURE
        )
        changed_counts = {
            "nodes.py": 22,
            "comfy_extras/nodes_custom_sampler.py": 8,
            "comfy_extras/nodes_model_advanced.py": 2,
            "comfy_extras/nodes_model_patch.py": 2,
            "comfy_extras/nodes_textgen.py": 1,
        }
        changed_paths = {
            path
            for path, source in contract.source_files.items()
            if source.byte_drift == "changed"
        }
        self.assertEqual(changed_paths, set(changed_counts))
        for path, expected_class_count in changed_counts.items():
            with self.subTest(path=path):
                source = contract.source_files[path]
                self.assertEqual(source.covered_signature_drift, "unchanged")
                self.assertEqual(len(source.classes), expected_class_count)
                self.assertTrue(
                    all(contract.classes[name].signature_drift == "unchanged" for name in source.classes)
                )
        self.assertEqual(
            sum(len(contract.source_files[path].classes) for path in changed_paths),
            35,
        )

    def test_candidate_core_graph_classifies_every_option_source_without_ambient_values(self) -> None:
        contract = core_graph_contract.load_core_graph_contract(
            FIXTURES / CORE_GRAPH_FIXTURE
        )
        allowed_kinds = {
            "not-applicable",
            "literal",
            "runtime-registry",
            "filesystem",
            "dynamic",
        }
        option_inputs = []
        for class_type, class_contract in contract.classes.items():
            for input_name, input_contract in class_contract.inputs.items():
                with self.subTest(class_type=class_type, input_name=input_name):
                    self.assertIn(input_contract.option_source.kind, allowed_kinds)
                    if input_contract.type in {"COMBO", "DYNAMICCOMBO"}:
                        option_inputs.append(input_contract)
                        self.assertNotEqual(input_contract.option_source.kind, "not-applicable")
                    else:
                        self.assertEqual(input_contract.option_source.kind, "not-applicable")
                    if input_contract.option_source.kind == "literal":
                        self.assertTrue(input_contract.option_source.values)
                    else:
                        self.assertEqual(input_contract.option_source.values, ())
        self.assertEqual(len(option_inputs), 35)
        self.assertEqual(contract.inventory.classified_option_count, 35)

    def test_candidate_contract_serialization_is_canonical_and_strict(self) -> None:
        graph_path = FIXTURES / CORE_GRAPH_FIXTURE
        profile_path = FIXTURES / PROFILE_GRAPH_FIXTURE
        graph_text = graph_path.read_text(encoding="utf-8")
        profile_text = profile_path.read_text(encoding="utf-8")
        self.assertEqual(
            core_graph_contract.serialize_core_graph_contract(
                core_graph_contract.parse_core_graph_contract_text(graph_text)
            ),
            graph_text,
        )
        self.assertEqual(
            core_graph_contract.serialize_profile_graph_contract(
                core_graph_contract.parse_profile_graph_contract_text(profile_text)
            ),
            profile_text,
        )
        self.assertTrue(graph_text.endswith("\n"))
        self.assertTrue(profile_text.endswith("\n"))

        with self.assertRaisesRegex(ValueError, "duplicate"):
            core_graph_contract.parse_core_graph_contract_text(
                '{"schema_version":"current-host-core-graph-contract-v1",'
                '"schema_version":"duplicate"}'
            )
        payload = json.loads(graph_text)
        payload["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown"):
            core_graph_contract.parse_core_graph_contract_text(json.dumps(payload))

    def test_candidate_contract_rejects_unknown_node_input_and_literal_enum(self) -> None:
        contract = core_graph_contract.load_core_graph_contract(
            FIXTURES / CORE_GRAPH_FIXTURE
        )
        valid = {
            "1": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["0", 0],
                    "positive": ["0", 0],
                    "negative": ["0", 0],
                    "latent_image": ["0", 0],
                    "seed": 1,
                    "steps": 20,
                    "cfg": 7.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                },
            },
            "2": {
                "class_type": "ImageScale",
                "inputs": {
                    "image": ["0", 0],
                    "upscale_method": "bilinear",
                    "width": 512,
                    "height": 512,
                    "crop": "disabled",
                },
            },
        }
        core_graph_contract.validate_workflow_graph(valid, contract)

        unknown_node = json.loads(json.dumps(valid))
        unknown_node["1"]["class_type"] = "UnknownCoreNode"
        with self.assertRaisesRegex(ValueError, "unknown node"):
            core_graph_contract.validate_workflow_graph(unknown_node, contract)

        unknown_input = json.loads(json.dumps(valid))
        unknown_input["1"]["inputs"]["surprise"] = True
        with self.assertRaisesRegex(ValueError, "unknown input"):
            core_graph_contract.validate_workflow_graph(unknown_input, contract)

        invalid_enum = json.loads(json.dumps(valid))
        invalid_enum["2"]["inputs"]["crop"] = "not-a-crop-mode"
        with self.assertRaisesRegex(ValueError, "literal option"):
            core_graph_contract.validate_workflow_graph(invalid_enum, contract)

        round_trip = json.loads(json.dumps(valid, sort_keys=True))
        self.assertEqual(round_trip, valid)

    def test_active_profile_fixture_matches_current_host_sources(self) -> None:
        self.assertFalse((FIXTURES / "comfyui_0_11_6_profile_sources.json").exists())
        fixture = _load_fixture(PROFILE_FIXTURE)
        self.assertEqual(fixture["core_revision"], HOST_SOURCE_BASIS.core.revision)
        self.assertEqual(
            fixture["workflow_templates_version"],
            HOST_SOURCE_BASIS.core.workflow_templates_version,
        )
        self.assertEqual(fixture["workflow_templates_json_version"], "0.1.49")
        expected_profiles = fixture["profiles"]
        entries = {entry.id: entry for entry in list_non_sd_manifest_entries()}
        self.assertEqual(set(entries), set(expected_profiles))
        for profile_id, source in expected_profiles.items():
            with self.subTest(profile_id=profile_id):
                self.assertEqual(entries[profile_id].official_template_path, source["locator"])
                self.assertIn(source["source_kind"], {"core-blueprint", "workflow-template-package"})
                self.assertEqual(len(source["sha256"]), 64)
                self.assertNotIn("latest", source["locator"].lower())

    def test_active_profile_hashes_match_local_current_sources_when_available(self) -> None:
        if not CORE_REFERENCE.exists() and not TEMPLATE_JSON_WHEEL.exists():
            return
        self.assertTrue(CORE_REFERENCE.is_dir())
        self.assertTrue(TEMPLATE_JSON_WHEEL.is_file())
        fixture = _load_fixture(PROFILE_FIXTURE)
        # SECURITY: inspect pinned source blobs and wheel members as inert bytes only.
        with zipfile.ZipFile(TEMPLATE_JSON_WHEEL) as template_archive:
            for profile_id, source in fixture["profiles"].items():
                locator = source["locator"]
                if locator.startswith("reference/ComfyUI/"):
                    relative_path = Path(locator).relative_to("reference/ComfyUI").as_posix()
                    completed = subprocess.run(
                        [
                            "git",
                            "-C",
                            str(CORE_REFERENCE),
                            "cat-file",
                            "blob",
                            f"{HOST_SOURCE_BASIS.core.revision}:{relative_path}",
                        ],
                        check=True,
                        capture_output=True,
                    )
                    content = completed.stdout
                else:
                    package, filename = locator.split(":", maxsplit=1)
                    self.assertEqual(package, "comfyui-workflow-templates-json==0.1.49")
                    member = f"comfyui_workflow_templates_json/templates/{filename}"
                    content = template_archive.read(member)
                with self.subTest(profile_id=profile_id, locator=locator):
                    self.assertEqual(hashlib.sha256(content).hexdigest(), source["sha256"])

    def test_unverified_profiles_fail_closed_and_remain_deferred(self) -> None:
        shipped_ids = {entry.id for entry in list_non_sd_manifest_entries()}
        self.assertFalse(DEFERRED_PROFILE_IDS & shipped_ids)
        for profile_id in DEFERRED_PROFILE_IDS:
            with self.subTest(profile_id=profile_id):
                self.assertIn(profile_id, OFFICIAL_TEMPLATE_DEFERRED_SURFACE_MARKERS)
                with self.assertRaises(ValueError):
                    get_family_template_manifest_entry(profile_id)

    def test_active_node_fixture_matches_current_host_builder_contract(self) -> None:
        self.assertFalse((FIXTURES / "comfyui_0_11_6_node_contract.json").exists())
        fixture = _load_fixture(NODE_FIXTURE)
        self.assertEqual(fixture["source_revision"], HOST_SOURCE_BASIS.core.revision)
        contracts = fixture["classes"]
        emitted, literal_nodes = _literal_emitted_classes_and_nodes()
        self.assertEqual(set(contracts), emitted - LOCAL_NODE_CLASSES)
        self.assertIn("TextGenerate", contracts)
        self.assertEqual(contracts["ControlNetLoader"]["source_path"], "nodes.py")
        self.assertEqual(contracts["DiffControlNetLoader"]["source_path"], "nodes.py")
        self.assertEqual(set(contracts["ControlNetLoader"]["inputs"]), {"control_net_name"})
        self.assertEqual(set(contracts["DiffControlNetLoader"]["inputs"]), {"model", "control_net_name"})

        for class_type, contract in contracts.items():
            with self.subTest(class_type=class_type):
                self.assertTrue(contract["inputs"])
                for spec in contract["inputs"].values():
                    self.assertIs(type(spec["optional"]), bool)
                    self.assertIsInstance(spec["type"], str)
                    self.assertTrue(spec["type"])

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

    def test_delegated_controlnet_builder_is_part_of_current_host_scan(self) -> None:
        self.assertIn(ROOT / "rookieui" / "services" / "workflow_builders" / "controlnet.py", BUILDER_PATHS)
        emitted, _ = _literal_emitted_classes_and_nodes()
        self.assertIn("ControlNetLoader", emitted)
        self.assertIn("DiffControlNetLoader", emitted)

    def test_all_graph_emitting_owners_are_part_of_current_host_scan(self) -> None:
        expected_paths = {
            ROOT / "rookieui" / "nodes.py",
            ROOT / "rookieui" / "services" / "workflow_builders" / "adetailer.py",
            ROOT / "rookieui" / "services" / "workflow_builders" / "core.py",
            ROOT / "rookieui" / "services" / "workflow_builders" / "controlnet.py",
            ROOT / "rookieui" / "services" / "workflow_builders" / "image_edit_foundation.py",
            ROOT / "rookieui" / "services" / "workflow_builders" / "non_sd_templates.py",
            ROOT / "rookieui" / "services" / "workflow_builders" / "output.py",
            ROOT / "rookieui" / "services" / "workflow_builders" / "prompt_conditioning.py",
            ROOT / "rookieui" / "services" / "workflow_builders" / "sd_family_graphs.py",
        }
        self.assertEqual(set(BUILDER_PATHS), expected_paths)

    def test_active_node_provenance_matches_pinned_active_core_when_available(self) -> None:
        if not CORE_REFERENCE.exists():
            return
        fixture = _load_fixture(NODE_FIXTURE)
        source_hashes: dict[str, str] = {}
        for class_type, contract in fixture["classes"].items():
            source_path = contract["source_path"]
            self.assertFalse(Path(source_path).is_absolute())
            self.assertNotIn("..", Path(source_path).parts)
            with self.subTest(class_type=class_type, source_path=source_path):
                if source_path not in source_hashes:
                    # SECURITY: read the accepted active source as an inert Git object; never import or execute reference code.
                    result = subprocess.run(
                        [
                            "git",
                            "-C",
                            str(CORE_REFERENCE),
                            "show",
                            f"{HOST_SOURCE_BASIS.core.revision}:{source_path}",
                        ],
                        check=False,
                        capture_output=True,
                    )
                    self.assertEqual(
                        result.returncode,
                        0,
                        msg=f"Pinned active Core object is unavailable: {source_path}",
                    )
                    source_hashes[source_path] = hashlib.sha256(result.stdout).hexdigest()
                self.assertEqual(source_hashes[source_path], contract["source_sha256"])

    def test_source_sensitive_ideogram_scheduler_defaults_are_current(self) -> None:
        contracts = _load_fixture(NODE_FIXTURE)["classes"]
        scheduler_inputs = contracts["Ideogram4Scheduler"]["inputs"]
        self.assertEqual(scheduler_inputs["steps"]["default"], 20)
        self.assertEqual(scheduler_inputs["width"]["default"], 1024)
        self.assertEqual(scheduler_inputs["height"]["default"], 1024)
        default_contract = IDEOGRAM4_MODE_CONTRACTS["default"]
        self.assertEqual(default_contract.mu, scheduler_inputs["mu"]["default"])
        self.assertEqual(default_contract.std, scheduler_inputs["std"]["default"])


if __name__ == "__main__":
    unittest.main()
