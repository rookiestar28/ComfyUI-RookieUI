from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_NAME = "rookieui.contracts.workflow_template_member_delta_contract"
FIXTURE = ROOT / "tests" / "fixtures" / "current_workflow_template_member_delta_contract.json"


class WorkflowTemplateMemberDeltaContractTests(unittest.TestCase):
    def _api(self):
        self.assertIsNotNone(importlib.util.find_spec(MODULE_NAME))
        return importlib.import_module(MODULE_NAME)

    def test_exact_candidate_member_partition_is_complete(self) -> None:
        api = self._api()
        self.assertTrue(FIXTURE.is_file())
        contract = api.load_member_delta_contract(FIXTURE)
        self.assertEqual(contract.schema_version, "workflow-template-member-delta-contract-v1")
        self.assertEqual((contract.from_version, contract.to_version), ("0.11.43", "0.11.54"))
        self.assertEqual(
            (contract.from_json_version, contract.to_json_version),
            ("0.1.49", "0.1.66"),
        )
        self.assertEqual(
            (
                contract.from_member_count,
                contract.to_member_count,
                len(contract.invariant_members),
                len(contract.added_members),
                len(contract.changed_members),
                len(contract.removed_members),
            ),
            (518, 547, 468, 31, 48, 2),
        )
        partitions = (
            contract.invariant_members,
            contract.added_members,
            contract.changed_members,
            contract.removed_members,
        )
        flattened = tuple(member for partition in partitions for member in partition)
        self.assertEqual(len(flattened), len(set(flattened)))
        self.assertEqual(len(contract.from_members), contract.from_member_count)
        self.assertEqual(len(contract.to_members), contract.to_member_count)
        self.assertEqual(
            set(contract.from_members),
            set(contract.invariant_members) | set(contract.changed_members) | set(contract.removed_members),
        )
        self.assertEqual(
            set(contract.to_members),
            set(contract.invariant_members) | set(contract.changed_members) | set(contract.added_members),
        )

    def test_contract_is_canonical_and_fails_closed(self) -> None:
        api = self._api()
        text = FIXTURE.read_text(encoding="utf-8")
        contract = api.parse_member_delta_contract_text(text)
        self.assertEqual(api.serialize_member_delta_contract(contract), text)

        payload = json.loads(text)
        payload["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown"):
            api.parse_member_delta_contract_text(json.dumps(payload))
        payload = json.loads(text)
        payload["added_members"].append(payload["invariant_members"][0])
        with self.assertRaisesRegex(ValueError, "partition|duplicate|sorted"):
            api.parse_member_delta_contract_text(json.dumps(payload))
        payload = json.loads(text)
        payload["from_inventory_sha256"] = "not-a-digest"
        with self.assertRaisesRegex(ValueError, "inventory"):
            api.parse_member_delta_contract_text(json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
