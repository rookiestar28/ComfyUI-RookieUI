from __future__ import annotations

import unittest

from rookieui.api.routes import build_capabilities_snapshot
from rookieui.contracts.capabilities import RookieUICapabilitiesSnapshot
from rookieui.services.capabilities import build_capabilities_payload
from rookieui.services.version import resolve_shell_version


class CapabilitySnapshotTests(unittest.TestCase):
    def test_capabilities_snapshot_enables_sidebar_shell(self) -> None:
        payload = build_capabilities_snapshot()

        self.assertEqual(payload["service"], "rookieui")
        self.assertTrue(payload["features"]["sidebarShell"])
        self.assertTrue(payload["features"]["capabilityBootstrap"])
        self.assertTrue(payload["features"]["compatibilityLayer"])
        self.assertTrue(payload["features"]["img2img"])
        self.assertTrue(payload["features"]["controlnet"])
        self.assertTrue(payload["features"]["pngInfo"])
        self.assertTrue(payload["features"]["queue"])
        self.assertIn("/rookieui/capabilities", payload["routes"])

    def test_capabilities_snapshot_contains_overview_tab(self) -> None:
        payload = build_capabilities_snapshot()

        titles = [tab["title"] for tab in payload["tabs"]]
        self.assertIn("Txt2Img", titles)
        self.assertIn("Img2Img", titles)
        self.assertIn("Extras", titles)
        self.assertIn("PNG Info", titles)
        self.assertIn("Queue", titles)

    def test_capabilities_snapshot_exposes_parity_profiles(self) -> None:
        payload = build_capabilities_snapshot()

        profile_ids = [profile["id"] for profile in payload["parity"]["profiles"]]
        self.assertIn("sd15", profile_ids)
        self.assertIn("pony", profile_ids)

    def test_build_capabilities_payload_normalizes_host_surfaces(self) -> None:
        payload = build_capabilities_payload(
            routes=["/rookieui/capabilities"],
            snapshot=RookieUICapabilitiesSnapshot(
                host_surfaces=[" desktop ", "standalone-web", ""],
                routes=["/rookieui/capabilities"],
            ),
        )

        self.assertEqual(payload["host_surfaces"], ["desktop", "standalone-web"])

    def test_capabilities_snapshot_exposes_prompt_semantics_contract(self) -> None:
        payload = build_capabilities_snapshot()

        prompt_semantics = payload["prompt_semantics"]
        self.assertEqual(prompt_semantics["contract_version"], "f100-20260414")
        self.assertEqual(prompt_semantics["contract_scope"], "sd-family-default-exact-with-explicit-fallbacks")
        self.assertEqual(prompt_semantics["rollout"]["default_mode"], "a1111_parity_nodes_exact")
        self.assertEqual(prompt_semantics["rollout"]["legacy_fallback_mode"], "graph_compiler_approximate")
        self.assertEqual(
            prompt_semantics["rollout"]["exact_profile_ids"],
            ["sd15", "sdxl", "pony", "illustrious", "noob"],
        )
        self.assertEqual(
            prompt_semantics["rollout"]["approximate_profile_ids"],
            ["flux", "qwen_image", "klein", "lumina", "zit", "wan", "anima"],
        )
        self.assertIn("RookieUIA1111TextEncode", prompt_semantics["compiler_constraints"]["conditioning_nodes"])
        self.assertIn(
            "PROMPT_LEGACY_FALLBACK_ENABLED",
            prompt_semantics["warning_codes"]["fallback"],
        )
        self.assertIn(
            "PROMPT_EXTRA_NETWORK_UNSUPPORTED_REMOVED",
            prompt_semantics["warning_codes"]["unsupported"],
        )
        capability_ids = [entry["id"] for entry in prompt_semantics["capabilities"]]
        self.assertIn("and_composition", capability_ids)
        self.assertIn("break_chunks", capability_ids)
        self.assertIn("prompt_scheduling", capability_ids)
        self.assertIn("attention_weighting", capability_ids)

        capability_by_id = {entry["id"]: entry for entry in prompt_semantics["capabilities"]}
        self.assertEqual(capability_by_id["and_composition"]["status"], "exact")
        self.assertEqual(capability_by_id["break_chunks"]["status"], "exact")
        self.assertEqual(capability_by_id["prompt_scheduling"]["status"], "exact")
        self.assertEqual(capability_by_id["attention_weighting"]["status"], "exact")
        self.assertEqual(capability_by_id["extra_network_lora"]["status"], "exact")
        self.assertEqual(capability_by_id["extra_network_other"]["status"], "unsupported")

    def test_capabilities_snapshot_uses_pyproject_shell_version(self) -> None:
        payload = build_capabilities_snapshot()
        self.assertEqual(payload["shell_version"], resolve_shell_version())
