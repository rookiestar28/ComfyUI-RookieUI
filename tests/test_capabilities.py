from __future__ import annotations

import unittest

from rookieui.api.routes import build_capabilities_snapshot
from rookieui.contracts.capabilities import RookieUICapabilitiesSnapshot
from rookieui.services.controlnet_advanced_runtime import CONTROLNET_ADVANCED_RUNTIME_STATE
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
        self.assertTrue(payload["features"]["adetailer"])
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
        self.assertEqual(prompt_semantics["contract_version"], "f105-20260416")
        capability_ids = [entry["id"] for entry in prompt_semantics["capabilities"]]
        self.assertIn("and_composition", capability_ids)
        self.assertIn("break_chunks", capability_ids)
        self.assertIn("prompt_scheduling", capability_ids)
        self.assertIn("alternate_prompt_scheduling", capability_ids)
        self.assertIn("attention_weighting", capability_ids)
        self.assertIn("embeddings_textual_inversion", capability_ids)
        embeddings_entry = next(
            entry for entry in prompt_semantics["capabilities"] if entry["id"] == "embeddings_textual_inversion"
        )
        self.assertEqual(embeddings_entry["status"], "supported")

    def test_capabilities_snapshot_exposes_adetailer_contract(self) -> None:
        payload = build_capabilities_snapshot()

        adetailer = payload["adetailer"]
        self.assertEqual(adetailer["contract"]["version"], "r74f77-20260414")
        self.assertEqual(adetailer["contract"]["ui_variant"], "a1111_integrated_detailer")
        self.assertEqual(adetailer["contract"]["unit_count"], 4)
        self.assertEqual(
            adetailer["contract"]["detector_provider_families"],
            ["none", "ultralytics_bbox", "ultralytics_segm", "mediapipe_face"],
        )
        self.assertEqual(adetailer["contract"]["detector_result_contract"], "rookieui_detection_regions_v1")
        self.assertEqual(
            adetailer["contract"]["controlnet_advanced_contract"]["runtime_state"],
            CONTROLNET_ADVANCED_RUNTIME_STATE,
        )
        self.assertEqual(adetailer["prompt_tokens"], ["[PROMPT]", "[SEP]", "[SKIP]"])
        self.assertEqual(adetailer["controlnet_modes"], ["none", "passthrough", "custom"])
        self.assertIn("/rookieui/adetailer/catalog", adetailer["routes"])
        self.assertEqual(adetailer["contract"]["defaults"]["checkpoint_name"], "Use same checkpoint")
        self.assertEqual(adetailer["execution_backend"], "rookieui_comfy_native_refinement_pipeline")
        self.assertEqual(adetailer["warning_code_contract"], "stable_f81")
        self.assertIn("ADETAILER_CONTROLNET_CUSTOM_MODEL_MISSING", adetailer["warning_codes"])
        self.assertIn("detect_mask", adetailer["availability"]["runtime_stages"])
        self.assertEqual(
            adetailer["availability"]["detector_runtime"]["ultralytics_bbox"],
            "native_runtime_dependency_missing",
        )

    def test_capabilities_snapshot_uses_pyproject_shell_version(self) -> None:
        payload = build_capabilities_snapshot()
        self.assertEqual(payload["shell_version"], resolve_shell_version())
