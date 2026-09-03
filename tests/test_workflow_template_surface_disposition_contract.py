from __future__ import annotations

from dataclasses import replace
import json
import unittest

from rookieui.contracts import workflow_template_surface_disposition_contract as contract_module
from rookieui.contracts import current_workflow_template_delta as delta_module
from rookieui.contracts import workflow_template_member_delta_contract as member_delta_module
from rookieui.contracts import workflow_template_supported_graph_contract as supported_graph_module


class WorkflowTemplateSurfaceDispositionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(
            contract_module.DEFAULT_CONTRACT_PATH.read_text(encoding="utf-8")
        )

    def test_contract_is_exact_complete_and_canonical(self) -> None:
        contract = contract_module.load_surface_disposition_contract()

        self.assertEqual(contract.schema_version, contract_module.SCHEMA_VERSION)
        self.assertEqual((contract.from_version, contract.to_version), ("0.11.43", "0.11.54"))
        self.assertEqual((contract.from_json_version, contract.to_json_version), ("0.1.49", "0.1.66"))
        self.assertEqual(
            (contract.old_member_count, contract.new_member_count, contract.union_count),
            (518, 547, 549),
        )
        self.assertEqual(
            (
                contract.added_count,
                contract.changed_count,
                contract.removed_count,
                contract.archived_count,
                contract.unchanged_count,
                contract.entry_count,
            ),
            (31, 48, 2, 2, 468, 81),
        )
        self.assertEqual(
            dict(contract.disposition_counts),
            {
                "deferred": 1,
                "out-of-scope": 62,
                "reference-only": 16,
                "removed": 0,
                "superseded": 2,
                "supported": 0,
            },
        )
        self.assertEqual(contract_module.serialize_surface_disposition_contract(contract), self.payload)

    def test_contract_entries_pin_disposition_rationale_and_hash_shape(self) -> None:
        contract = contract_module.load_surface_disposition_contract()
        entries = {entry.id: entry for entry in contract.entries}

        self.assertEqual(
            (entries["api_bfl_flux_video_upscale"].change_kind, entries["api_bfl_flux_video_upscale"].disposition),
            ("added", "out-of-scope"),
        )
        self.assertEqual(
            (entries["image_sdxl_simple"].change_kind, entries["image_sdxl_simple"].disposition),
            ("added", "deferred"),
        )
        self.assertEqual(
            (entries["index.zh-TW"].change_kind, entries["index.zh-TW"].disposition),
            ("changed", "reference-only"),
        )
        self.assertEqual(
            (entries["3d_pixal3d_trellis2_image_to_model"].disposition, entries["3d_pixal3d_trellis2_image_to_model"].rationale),
            ("out-of-scope", "three-d-runtime-not-shipped"),
        )
        self.assertEqual(
            (entries["templates-car_product"].disposition, entries["templates-car_product"].rationale),
            ("reference-only", "example-template-not-runtime"),
        )
        archived = entries["api_veo2_i2v"]
        self.assertEqual((archived.change_kind, archived.disposition), ("archived", "superseded"))
        self.assertEqual(archived.old_sha256, archived.archived_sha256)
        self.assertIsNone(archived.new_sha256)
        self.assertFalse(any(entry.disposition == "supported" for entry in contract.entries))

    def test_contract_and_aggregate_ledgers_are_exactly_reconciled(self) -> None:
        contract = contract_module.load_surface_disposition_contract()
        by_kind = {
            kind: {entry.id for entry in contract.entries if entry.change_kind == kind}
            for kind in ("added", "archived", "changed", "removed")
        }
        by_disposition = {
            disposition: {
                entry.id for entry in contract.entries if entry.disposition == disposition
            }
            for disposition in contract.disposition_counts
        }
        self.assertEqual(by_kind["added"], set(delta_module.WORKFLOW_TEMPLATE_0_11_54_ADDED_SURFACES))
        self.assertEqual(by_kind["changed"], set(delta_module.WORKFLOW_TEMPLATE_0_11_54_CHANGED_SURFACES))
        self.assertEqual(by_kind["archived"], set(delta_module.WORKFLOW_TEMPLATE_0_11_54_SUPERSEDED_SURFACES))
        self.assertEqual(by_kind["removed"], set(delta_module.WORKFLOW_TEMPLATE_0_11_54_REMOVED_SURFACES))
        self.assertEqual(by_disposition["supported"], set(delta_module.WORKFLOW_TEMPLATE_0_11_54_SUPPORTED_SURFACES))
        self.assertEqual(by_disposition["deferred"], set(delta_module.WORKFLOW_TEMPLATE_0_11_54_DEFERRED_SURFACES))
        self.assertEqual(by_disposition["reference-only"], set(delta_module.WORKFLOW_TEMPLATE_0_11_54_REFERENCE_ONLY_SURFACES))
        self.assertEqual(by_disposition["superseded"], set(delta_module.WORKFLOW_TEMPLATE_0_11_54_SUPERSEDED_SURFACES))
        self.assertEqual(by_disposition["out-of-scope"], set(delta_module.WORKFLOW_TEMPLATE_0_11_54_OUT_OF_SCOPE_SURFACES))
        self.assertEqual(by_disposition["removed"], set(delta_module.WORKFLOW_TEMPLATE_0_11_54_REMOVED_SURFACES))

    def test_contract_exactly_matches_f333_member_delta_and_supported_graph(self) -> None:
        contract = contract_module.load_surface_disposition_contract()
        member_delta = member_delta_module.load_member_delta_contract()
        supported_graph = supported_graph_module.load_supported_graph_contract()

        def surface_id(member: str) -> str:
            self.assertTrue(member.startswith("templates/") and member.endswith(".json"))
            return member.removeprefix("templates/").removesuffix(".json")

        entries = {entry.id: entry for entry in contract.entries}
        self.assertEqual(
            {entry.id for entry in contract.entries if entry.change_kind == "added"},
            {surface_id(member) for member in member_delta.added_members},
        )
        self.assertEqual(
            {entry.id for entry in contract.entries if entry.change_kind == "changed"},
            {surface_id(member) for member in member_delta.changed_members},
        )
        self.assertEqual(
            {entry.id for entry in contract.entries if entry.change_kind in {"archived", "removed"}},
            {surface_id(member) for member in member_delta.removed_members},
        )
        non_invariant = {
            surface_id(member)
            for member in (
                *member_delta.added_members,
                *member_delta.changed_members,
                *member_delta.removed_members,
            )
        }
        self.assertEqual(set(entries), non_invariant)

        package_sources = {
            profile.source_id.removesuffix(".json")
            for profile in supported_graph.profiles
            if profile.source_kind == "workflow-template-package"
        }
        self.assertEqual(len(package_sources), 11)
        self.assertTrue(package_sources.isdisjoint(non_invariant))
        self.assertEqual(supported_graph.profile_count, 26)
        self.assertEqual(supported_graph.unique_source_count, 25)

    def test_contract_rejects_unknown_duplicate_unsorted_and_invariant_entries(self) -> None:
        unknown = dict(self.payload)
        unknown["unexpected"] = True
        with self.assertRaises(ValueError):
            contract_module.parse_surface_disposition_contract(unknown)

        duplicate = json.loads(json.dumps(self.payload))
        duplicate["entries"].insert(1, duplicate["entries"][0])
        duplicate["entry_count"] += 1
        with self.assertRaises(ValueError):
            contract_module.parse_surface_disposition_contract(duplicate)

        unsorted = json.loads(json.dumps(self.payload))
        unsorted["entries"][0], unsorted["entries"][1] = unsorted["entries"][1], unsorted["entries"][0]
        with self.assertRaises(ValueError):
            contract_module.parse_surface_disposition_contract(unsorted)

        invariant = json.loads(json.dumps(self.payload))
        changed = next(entry for entry in invariant["entries"] if entry["change_kind"] == "changed")
        changed["new_sha256"] = changed["old_sha256"]
        with self.assertRaises(ValueError):
            contract_module.parse_surface_disposition_contract(invariant)

        missing = json.loads(json.dumps(self.payload))
        del missing["source_report_sha256"]
        with self.assertRaises(ValueError):
            contract_module.parse_surface_disposition_contract(missing)

        unsafe_id = json.loads(json.dumps(self.payload))
        unsafe_id["entries"][0]["id"] = "../../private"
        with self.assertRaises(ValueError):
            contract_module.parse_surface_disposition_contract(unsafe_id)

        duplicate_member_text = contract_module.DEFAULT_CONTRACT_PATH.read_text(
            encoding="utf-8"
        ).replace('  "added_count": 31,', '  "added_count": 31,\n  "added_count": 31,', 1)
        with self.assertRaises(ValueError):
            contract_module.parse_surface_disposition_contract_text(duplicate_member_text)

    def test_contract_rejects_invalid_kind_disposition_rationale_hash_and_counts(self) -> None:
        cases = []
        for key, value in (
            ("change_kind", "unknown"),
            ("disposition", "supported"),
            ("rationale", "arbitrary"),
            ("new_sha256", "not-a-hash"),
        ):
            payload = json.loads(json.dumps(self.payload))
            payload["entries"][0][key] = value
            cases.append(payload)
        bad_count = json.loads(json.dumps(self.payload))
        bad_count["added_count"] += 1
        cases.append(bad_count)
        bad_source = json.loads(json.dumps(self.payload))
        bad_source["to_revision"] = "0" * 40
        cases.append(bad_source)

        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    contract_module.parse_surface_disposition_contract(payload)

    def test_contract_dataclasses_are_frozen(self) -> None:
        contract = contract_module.load_surface_disposition_contract()
        with self.assertRaises(AttributeError):
            contract.entries[0].id = "changed"  # type: ignore[misc]
        with self.assertRaises(ValueError):
            replace(contract.entries[0], disposition="supported")


if __name__ == "__main__":
    unittest.main()
