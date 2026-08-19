from __future__ import annotations

from dataclasses import replace
import json
import unittest

from rookieui.contracts import workflow_template_surface_disposition_contract as contract_module
from rookieui.contracts.host_source_basis import WORKFLOW_TEMPLATE_DELTA_0_11_31_TO_0_11_43


class WorkflowTemplateSurfaceDispositionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(
            contract_module.DEFAULT_CONTRACT_PATH.read_text(encoding="utf-8")
        )

    def test_contract_is_exact_complete_and_canonical(self) -> None:
        contract = contract_module.load_surface_disposition_contract()

        self.assertEqual(contract.schema_version, contract_module.SCHEMA_VERSION)
        self.assertEqual((contract.from_version, contract.to_version), ("0.11.31", "0.11.43"))
        self.assertEqual((contract.from_json_version, contract.to_json_version), ("0.1.30", "0.1.49"))
        self.assertEqual(
            (contract.old_member_count, contract.new_member_count, contract.union_count),
            (513, 518, 534),
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
            (21, 20, 16, 16, 477, 57),
        )
        self.assertEqual(
            dict(contract.disposition_counts),
            {
                "deferred": 2,
                "out-of-scope": 25,
                "reference-only": 14,
                "removed": 0,
                "superseded": 16,
                "supported": 0,
            },
        )
        self.assertEqual(contract_module.serialize_surface_disposition_contract(contract), self.payload)

    def test_contract_entries_pin_disposition_rationale_and_hash_shape(self) -> None:
        contract = contract_module.load_surface_disposition_contract()
        entries = {entry.id: entry for entry in contract.entries}

        self.assertEqual(
            (entries["api_qwen3_t2i"].change_kind, entries["api_qwen3_t2i"].disposition),
            ("added", "out-of-scope"),
        )
        self.assertEqual(
            (entries["image_qwen_image_layered"].change_kind, entries["image_qwen_image_layered"].disposition),
            ("changed", "deferred"),
        )
        self.assertEqual(
            (entries["index.zh-TW"].change_kind, entries["index.zh-TW"].disposition),
            ("changed", "reference-only"),
        )
        archived = entries["01_get_started_text_to_image"]
        self.assertEqual((archived.change_kind, archived.disposition), ("archived", "superseded"))
        self.assertEqual(archived.old_sha256, archived.archived_sha256)
        self.assertIsNone(archived.new_sha256)
        self.assertFalse(any(entry.disposition == "supported" for entry in contract.entries))

    def test_contract_and_aggregate_ledgers_are_exactly_reconciled(self) -> None:
        contract = contract_module.load_surface_disposition_contract()
        delta = WORKFLOW_TEMPLATE_DELTA_0_11_31_TO_0_11_43

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
        self.assertEqual(by_kind["added"], set(delta.added))
        self.assertEqual(by_kind["changed"], set(delta.changed))
        self.assertEqual(by_kind["archived"], set(delta.superseded))
        self.assertEqual(by_kind["removed"], set(delta.removed))
        self.assertEqual(by_disposition["supported"], set(delta.supported))
        self.assertEqual(by_disposition["deferred"], set(delta.deferred))
        self.assertEqual(by_disposition["reference-only"], set(delta.reference_only))
        self.assertEqual(by_disposition["superseded"], set(delta.superseded))
        self.assertEqual(by_disposition["out-of-scope"], set(delta.out_of_scope))
        self.assertEqual(by_disposition["removed"], set(delta.removed))

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
        ).replace('  "added_count": 21,', '  "added_count": 21,\n  "added_count": 21,', 1)
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
