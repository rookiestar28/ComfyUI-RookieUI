from __future__ import annotations

import dataclasses
import json
from pathlib import Path
import re
import unittest
from unittest import mock

from rookieui.contracts import core_graph_contract
from rookieui.contracts import workflow_template_supported_graph_contract
from rookieui.contracts.family_template_manifest import (
    CURRENT_HOST_DEFERRED_PROFILE_IDS,
    FamilyTemplateManifestEntry,
    _ALL_MANIFEST_ENTRIES,
)
from rookieui.contracts.family_profile_projection import (
    build_family_profile_projection,
    build_family_profile_projection_entries,
    validate_runtime_adapter_bindings,
)
from rookieui.contracts.model_family_registry import list_model_family_registry_entries
from rookieui.contracts.models import ModelInventorySnapshot
from rookieui.services.img2img import normalize_img2img_request
from rookieui.services.txt2img import normalize_txt2img_request
from rookieui.services.workflow_translation import (
    translate_img2img_request,
    translate_txt2img_request,
)
from rookieui.services.workflow_builders import non_sd_templates


EXPECTED_SHIPPED_PROFILE_IDS = (
    "sd15",
    "sdxl",
    "pony",
    "illustrious",
    "noob",
    "anima",
    "chroma",
    "ernie_image",
    "ernie_image_turbo",
    "flux",
    "flux_krea_dev",
    "flux2_dev",
    "ideogram4",
    "krea2_turbo",
    "klein_4b",
    "klein_9b",
    "hidream_i1_dev_fp8",
    "hidream_i1_fast",
    "hidream_i1_full",
    "longcat_image",
    "qwen_image",
    "qwen_image_edit",
    "qwen_image_edit_2511",
    "firered_image_edit",
    "firered_image_edit_lightning",
    "flux_kontext_dev_edit",
    "flux2_image_edit",
    "klein_9b_kv_image_edit",
    "longcat_image_edit",
    "z_image",
    "z_image_turbo",
)

ROOT = Path(__file__).resolve().parents[1]
PROFILE_GRAPH_FIXTURE = ROOT / "tests" / "fixtures" / "current_host_profile_graph_contract.json"
CORE_GRAPH_FIXTURE = ROOT / "tests" / "fixtures" / "current_host_core_graph_contract.json"


class FamilyProfileProjectionTests(unittest.TestCase):
    def test_candidate_supported_sources_match_non_sd_profile_projection(self) -> None:
        contract = workflow_template_supported_graph_contract.load_supported_graph_contract()
        supported_ids = {profile.id for profile in contract.profiles}
        projected_ids = {
            projection["id"]
            for projection in build_family_profile_projection_entries(
                list_model_family_registry_entries()
            )
            if projection["id"] not in {"sd15", "sdxl", "pony", "illustrious", "noob"}
        }
        self.assertEqual(supported_ids, projected_ids)

    def test_current_host_profile_graph_contract_covers_all_shipped_profiles_in_order(self) -> None:
        contract = core_graph_contract.load_profile_graph_contract(PROFILE_GRAPH_FIXTURE)
        self.assertEqual(contract.schema_version, "current-host-profile-graph-contract-v1")
        self.assertEqual(contract.source_revision, "c67885b14556cf3e4e061862925282d403d09862")
        self.assertEqual(contract.profile_count, 31)
        self.assertEqual(tuple(profile.id for profile in contract.profiles), EXPECTED_SHIPPED_PROFILE_IDS)
        entries = list_model_family_registry_entries()
        self.assertEqual(
            tuple(profile.flow_kind for profile in contract.profiles),
            tuple(entry.flow_kind for entry in entries),
        )
        for profile in contract.profiles:
            with self.subTest(profile=profile.id):
                self.assertGreater(profile.node_count, 0)
                self.assertGreaterEqual(profile.edge_count, 0)
                self.assertTrue(profile.class_types)
                self.assertRegex(profile.topology_sha256, re.compile(r"^[0-9a-f]{64}$"))
                self.assertEqual(tuple(sorted(profile.class_types)), profile.class_types)

    def test_topology_digest_is_content_free_and_deterministic(self) -> None:
        first = {
            "20": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["1", 0]}},
            "10": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0],
                    "seed": 1,
                    "steps": 20,
                    "cfg": 7.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                },
            },
        }
        second = json.loads(json.dumps(first))
        second["10"]["inputs"].update(
            {"seed": 999, "steps": 8, "cfg": 1.0, "sampler_name": "heun"}
        )
        first_row = core_graph_contract.build_profile_graph_row("synthetic", "txt2img", first)
        second_row = core_graph_contract.build_profile_graph_row("synthetic", "txt2img", second)
        self.assertEqual(first_row.topology_sha256, second_row.topology_sha256)
        self.assertEqual(first_row.node_count, second_row.node_count)
        self.assertEqual(first_row.edge_count, second_row.edge_count)

    def test_all_shipped_profile_builders_match_candidate_graph_contract(self) -> None:
        core_contract = core_graph_contract.load_core_graph_contract(CORE_GRAPH_FIXTURE)
        profile_contract = core_graph_contract.load_profile_graph_contract(PROFILE_GRAPH_FIXTURE)
        expected_by_id = {profile.id: profile for profile in profile_contract.profiles}
        empty_inventory = ModelInventorySnapshot(source="fallback")
        ideogram_inventory = ModelInventorySnapshot(
            source="fallback",
            diffusion_models=[
                "synthetic/ideogram4_unconditional_fp8_scaled.safetensors",
                "synthetic/ideogram4_fp8_scaled.safetensors",
            ],
            vae=["synthetic/qwen_image_vae.safetensors"],
            text_encoders=[
                "synthetic/qwen3vl_8b_fp8_scaled.safetensors",
                "synthetic/qwen_3_4b.safetensors",
            ],
            default_vae="synthetic/qwen_image_vae.safetensors",
            default_text_encoder="synthetic/qwen_3_4b.safetensors",
        )

        with mock.patch(
            "rookieui.services.img2img.resolve_asset_path",
            return_value=Path(__file__),
        ):
            for entry in list_model_family_registry_entries():
                with self.subTest(profile=entry.id):
                    if entry.flow_kind == "txt2img":
                        inventory = (
                            ideogram_inventory
                            if entry.id == "ideogram4"
                            else empty_inventory
                        )
                        with mock.patch(
                            "rookieui.services.txt2img.discover_model_inventory",
                            return_value=inventory,
                        ):
                            request = normalize_txt2img_request(
                                {"profile": entry.id, "prompt": "synthetic graph contract"}
                            )
                        workflow = translate_txt2img_request(request).workflow
                    elif entry.flow_kind == "edit":
                        with mock.patch(
                            "rookieui.services.img2img.discover_model_inventory",
                            return_value=empty_inventory,
                        ):
                            request = normalize_img2img_request(
                                {
                                    "image_asset": "synthetic-contract-image.png",
                                    "mode": "img2img",
                                    "profile": entry.id,
                                    "prompt": "synthetic graph contract",
                                }
                            )
                        workflow = translate_img2img_request(request).workflow
                    else:
                        self.fail(f"Unsupported flow kind: {entry.flow_kind}")

                    local_node_classes = frozenset(
                        str(node.get("class_type", ""))
                        for node in workflow.values()
                        if isinstance(node, dict)
                        and str(node.get("class_type", "")).startswith("RookieUI")
                    )
                    core_graph_contract.validate_workflow_graph(
                        workflow,
                        core_contract,
                        local_node_classes=local_node_classes,
                    )
                    self.assertEqual(
                        core_graph_contract.build_profile_graph_row(
                            entry.id,
                            entry.flow_kind,
                            workflow,
                        ),
                        expected_by_id[entry.id],
                    )

    def test_manifest_entry_is_frozen_and_projection_covers_every_declared_field(self) -> None:
        self.assertTrue(dataclasses.is_dataclass(FamilyTemplateManifestEntry))
        self.assertTrue(FamilyTemplateManifestEntry.__dataclass_params__.frozen)

        entry = list_model_family_registry_entries()[0]
        projection = build_family_profile_projection(entry)
        declared_fields = {field.name for field in dataclasses.fields(FamilyTemplateManifestEntry)}

        self.assertEqual(set(projection), declared_fields)
        self.assertEqual(projection["id"], entry.id)
        self.assertEqual(projection["aliases"], list(entry.aliases))
        self.assertEqual(projection["available_surface_flows"], list(entry.available_surface_flows))

    def test_shipped_projection_preserves_manifest_order_and_deferred_filter(self) -> None:
        entries = list_model_family_registry_entries()
        projections = build_family_profile_projection_entries(entries)

        self.assertEqual(tuple(projection["id"] for projection in projections), EXPECTED_SHIPPED_PROFILE_IDS)
        self.assertEqual(
            set(projection["id"] for projection in projections) & set(CURRENT_HOST_DEFERRED_PROFILE_IDS),
            set(),
        )
        all_ids = {entry.id for entry in _ALL_MANIFEST_ENTRIES}
        self.assertTrue(CURRENT_HOST_DEFERRED_PROFILE_IDS <= all_ids)
        self.assertEqual(
            tuple(entry.id for entry in _ALL_MANIFEST_ENTRIES if entry.id not in CURRENT_HOST_DEFERRED_PROFILE_IDS),
            EXPECTED_SHIPPED_PROFILE_IDS,
        )

    def test_runtime_adapter_bindings_are_complete_and_deferred_builders_are_not_dispatchable(self) -> None:
        errors = validate_runtime_adapter_bindings(
            list_model_family_registry_entries(),
            adapter_by_profile=non_sd_templates._NON_SD_RUNTIME_ADAPTER_BY_PROFILE,
            txt2img_builders=non_sd_templates._NON_SD_RUNTIME_BUILDERS,
            edit_builders=non_sd_templates._NON_SD_EDIT_RUNTIME_BUILDERS,
            deferred_profile_ids=CURRENT_HOST_DEFERRED_PROFILE_IDS,
        )
        self.assertEqual(errors, ())

    def test_runtime_adapter_validator_reports_missing_callable(self) -> None:
        errors = validate_runtime_adapter_bindings(
            list_model_family_registry_entries(),
            adapter_by_profile={"anima": "missing"},
            txt2img_builders={},
            edit_builders={},
            deferred_profile_ids=CURRENT_HOST_DEFERRED_PROFILE_IDS,
        )
        self.assertIn("anima: adapter 'missing' has no callable txt2img builder", errors)


if __name__ == "__main__":
    unittest.main()
