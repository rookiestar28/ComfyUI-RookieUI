from __future__ import annotations

import unittest

from rookieui.api.routes import build_capabilities_snapshot
from rookieui.contracts.capabilities import RookieUICapabilitiesSnapshot
from rookieui.services.controlnet_advanced_runtime import CONTROLNET_ADVANCED_RUNTIME_STATE
from rookieui.services.capabilities import build_capabilities_payload
from rookieui.services.version import resolve_runtime_build_fingerprint, resolve_shell_version


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

    def test_capabilities_snapshot_exposes_model_family_registry(self) -> None:
        payload = build_capabilities_snapshot()

        self.assertEqual(payload["model_families"]["contract_version"], "f158-20260419")
        family_ids = [entry["id"] for entry in payload["model_families"]["entries"]]
        self.assertIn("sd15", family_ids)
        self.assertIn("chroma", family_ids)
        self.assertIn("flux", family_ids)
        self.assertIn("ernie_image", family_ids)
        self.assertIn("qwen_image_edit", family_ids)
        self.assertIn("z_image_turbo", family_ids)
        flux_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "flux")
        ernie_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "ernie_image")
        z_turbo_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "z_image_turbo")
        self.assertEqual(flux_entry["translation_base_family"], "sdxl")
        self.assertEqual(flux_entry["public_base_family"], "flux")
        self.assertFalse(flux_entry["text_encoder_visible"])
        self.assertTrue(flux_entry["template_lora_visible"])
        self.assertTrue(flux_entry["template_lora_override_allowed"])
        self.assertEqual(flux_entry["official_template_lora_label"], "Flux_2-Turbo-LoRA_comfyui.safetensors")
        self.assertFalse(flux_entry["shift_visible"])
        self.assertEqual(flux_entry["available_surface_flows"], ["txt2img"])
        self.assertEqual(ernie_entry["translation_base_family"], "sdxl")
        self.assertEqual(ernie_entry["public_base_family"], "ernie_image")
        self.assertFalse(ernie_entry["text_encoder_visible"])
        self.assertTrue(ernie_entry["prompt_enhancement_visible"])
        chroma_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "chroma")
        qwen_edit_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "qwen_image_edit")
        self.assertTrue(chroma_entry["shift_visible"])
        self.assertEqual(chroma_entry["default_shift"], 1.0)
        self.assertTrue(qwen_edit_entry["edit_megapixels_visible"])
        self.assertEqual(qwen_edit_entry["default_edit_megapixels"], 1.5)
        self.assertTrue(qwen_edit_entry["template_lora_visible"])
        self.assertTrue(qwen_edit_entry["template_lora_override_allowed"])
        self.assertEqual(
            qwen_edit_entry["official_template_lora_label"],
            "Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors",
        )
        self.assertEqual(qwen_edit_entry["available_surface_flows"], ["edit"])
        self.assertEqual(z_turbo_entry["public_base_family"], "z_image")
        sd15_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "sd15")
        self.assertEqual(sd15_entry["available_surface_flows"], ["txt2img", "img2img"])

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

    def test_capabilities_snapshot_exposes_runtime_build_fingerprint(self) -> None:
        payload = build_capabilities_snapshot()

        self.assertEqual(payload["runtime"]["shell_version"], resolve_shell_version())
        self.assertEqual(payload["runtime"]["build_fingerprint"], resolve_runtime_build_fingerprint())
