from __future__ import annotations

import sys
import types
import unittest
from unittest import mock

from rookieui.api.routes import build_capabilities_snapshot
from rookieui.contracts.capabilities import RookieUICapabilitiesSnapshot
from rookieui.contracts.models import ModelInventorySnapshot
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

    def test_capabilities_snapshot_exposes_z_image_controlnet_contract(self) -> None:
        class ModelPatchLoader:
            pass

        class QwenImageDiffsynthControlnet:
            pass

        class ModelSamplingAuraFlow:
            pass

        inventory = ModelInventorySnapshot(
            source="host",
            checkpoints=["realvisxl.safetensors"],
            controlnet=["sdxl-controlnet-depth.safetensors"],
            model_patches=[
                "Z-Image\\Z-Image-Turbo-Fun-Controlnet-Union-2.1.safetensors",
                "Qwen\\qwen-controlnet-union.safetensors",
            ],
        )
        nodes_module = types.SimpleNamespace(
            NODE_CLASS_MAPPINGS={
                "ModelPatchLoader": ModelPatchLoader,
                "QwenImageDiffsynthControlnet": QwenImageDiffsynthControlnet,
                "ModelSamplingAuraFlow": ModelSamplingAuraFlow,
            }
        )

        with (
            mock.patch("rookieui.services.z_image_controlnet.discover_model_inventory", return_value=inventory),
            mock.patch.dict(sys.modules, {"nodes": nodes_module}),
        ):
            payload = build_capabilities_snapshot()

        capability = payload["z_image_controlnet"]
        self.assertTrue(capability["available"])
        self.assertEqual(capability["source_model_category"], "model_patches")
        self.assertEqual(capability["forbidden_model_category"], "controlnet")
        self.assertEqual(capability["missing_nodes"], [])
        self.assertEqual(capability["diagnostics"], [])
        self.assertEqual(
            [entry["selector"] for entry in capability["model_patches"]],
            ["Z-Image\\Z-Image-Turbo-Fun-Controlnet-Union-2.1.safetensors"],
        )
        self.assertEqual(capability["model_patches"][0]["variant"], "union")
        self.assertTrue(capability["model_patches"][0]["turbo"])
        self.assertEqual(capability["model_patches"][0]["rookieui_support"], "turbo_union_single_control")
        self.assertEqual(capability["model_patches"][0]["recommendation"], "candidate")
        self.assertNotIn("sdxl-controlnet-depth.safetensors", str(capability["model_patches"]))
        self.assertEqual(capability["contract_version"], "z-image-control-map-20260713")
        self.assertEqual(
            capability["control_map_contract"],
            {
                "explicit_preprocessed_field": "preprocessed_control_map",
                "default_preprocessed": False,
                "built_in_preprocessors": ["canny"],
                "explicit_preprocessed_conditions": ["depth", "pose"],
                "raw_rejected_conditions": ["depth", "pose"],
            },
        )

    def test_capabilities_snapshot_classifies_z_image_controlnet_21_variant_matrix(self) -> None:
        inventory = ModelInventorySnapshot(
            source="host",
            model_patches=[
                "Z-Image-Fun-Controlnet-Union-2.1.safetensors",
                "Z-Image-Fun-Controlnet-Union-2.1-lite.safetensors",
                "Z-Image-Fun-Controlnet-Tile-2.1.safetensors",
                "Z-Image-Turbo-Fun-Controlnet-Union-2.1-8steps.safetensors",
                "Z-Image-Turbo-Fun-Controlnet-Union-2.1-2601-8steps.safetensors",
                "Z-Image-Turbo-Fun-Controlnet-Union-2.1-lite-2602-8steps.safetensors",
                "Z-Image-Turbo-Fun-Controlnet-Union-2.1-2602-8steps.safetensors",
                "Z-Image-Turbo-Fun-Controlnet-Tile-2.1-lite-2601-8steps.safetensors",
            ],
        )
        nodes_module = types.SimpleNamespace(
            NODE_CLASS_MAPPINGS={
                "ModelPatchLoader": object,
                "QwenImageDiffsynthControlnet": object,
                "ModelSamplingAuraFlow": object,
            }
        )

        with (
            mock.patch("rookieui.services.z_image_controlnet.discover_model_inventory", return_value=inventory),
            mock.patch.dict(sys.modules, {"nodes": nodes_module}),
        ):
            payload = build_capabilities_snapshot()

        entries = {entry["selector"]: entry for entry in payload["z_image_controlnet"]["model_patches"]}
        fun_union = entries["Z-Image-Fun-Controlnet-Union-2.1.safetensors"]
        fun_lite = entries["Z-Image-Fun-Controlnet-Union-2.1-lite.safetensors"]
        turbo_8steps = entries["Z-Image-Turbo-Fun-Controlnet-Union-2.1-8steps.safetensors"]
        turbo_2601 = entries["Z-Image-Turbo-Fun-Controlnet-Union-2.1-2601-8steps.safetensors"]
        turbo_lite_2602 = entries["Z-Image-Turbo-Fun-Controlnet-Union-2.1-lite-2602-8steps.safetensors"]
        turbo_2602 = entries["Z-Image-Turbo-Fun-Controlnet-Union-2.1-2602-8steps.safetensors"]
        turbo_tile_lite = entries["Z-Image-Turbo-Fun-Controlnet-Tile-2.1-lite-2601-8steps.safetensors"]

        self.assertEqual(fun_union["z_image_family"], "fun")
        self.assertEqual(fun_union["variant"], "union")
        self.assertFalse(fun_union["turbo"])
        self.assertEqual(fun_union["generation"], "2.1")
        self.assertEqual(fun_union["rookieui_support"], "deferred_non_turbo")
        self.assertEqual(fun_union["recommendation"], "deferred")
        self.assertIn("gray", fun_union["supported_conditions"])
        self.assertIn("inpaint", fun_union["supported_conditions"])
        self.assertTrue(fun_lite["lite"])

        self.assertEqual(turbo_8steps["distilled_steps"], 8)
        self.assertEqual(turbo_8steps["rookieui_support"], "turbo_union_single_control")
        self.assertNotIn("scribble", turbo_8steps["supported_conditions"])
        self.assertNotIn("gray", turbo_8steps["supported_conditions"])

        self.assertEqual(turbo_2601["release_tag"], "2601")
        self.assertIn("scribble", turbo_2601["supported_conditions"])
        self.assertNotIn("gray", turbo_2601["supported_conditions"])

        self.assertEqual(turbo_lite_2602["release_tag"], "2602")
        self.assertTrue(turbo_lite_2602["lite"])
        self.assertIn("scribble", turbo_lite_2602["supported_conditions"])
        self.assertIn("gray", turbo_lite_2602["supported_conditions"])
        self.assertEqual(turbo_lite_2602["recommendation"], "candidate")

        self.assertEqual(turbo_2602["recommendation"], "preferred")
        self.assertEqual(turbo_2602["source_control_context_scale_range"], [0.65, 1.0])

        self.assertEqual(turbo_tile_lite["variant"], "tile")
        self.assertEqual(turbo_tile_lite["supported_conditions"], ["tile"])
        self.assertEqual(turbo_tile_lite["rookieui_support"], "deferred_tile_surface")
        self.assertEqual(turbo_tile_lite["recommendation"], "deferred")

    def test_capabilities_snapshot_reports_z_image_controlnet_missing_dependencies(self) -> None:
        inventory = ModelInventorySnapshot(
            source="host",
            checkpoints=["realvisxl.safetensors"],
            controlnet=["Z-Image-Turbo-Fun-Controlnet-Union-2.1.safetensors"],
            model_patches=[],
        )
        nodes_module = types.SimpleNamespace(NODE_CLASS_MAPPINGS={"ModelPatchLoader": object})

        with (
            mock.patch("rookieui.services.z_image_controlnet.discover_model_inventory", return_value=inventory),
            mock.patch.dict(sys.modules, {"nodes": nodes_module}),
        ):
            payload = build_capabilities_snapshot()

        capability = payload["z_image_controlnet"]
        self.assertFalse(capability["available"])
        self.assertEqual(capability["model_patches"], [])
        self.assertEqual(
            capability["missing_nodes"],
            ["QwenImageDiffsynthControlnet", "ModelSamplingAuraFlow"],
        )
        self.assertIn("missing_model_patches:z_image_controlnet", capability["diagnostics"])
        self.assertIn("missing_node:QwenImageDiffsynthControlnet", capability["diagnostics"])
        self.assertIn("missing_node:ModelSamplingAuraFlow", capability["diagnostics"])
        self.assertNotIn("Z-Image-Turbo-Fun-Controlnet-Union-2.1.safetensors", str(capability["model_patches"]))

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

        self.assertEqual(
            payload["model_families"]["contract_version"],
            "model-family-20260713-effective-parameters",
        )
        family_ids = [entry["id"] for entry in payload["model_families"]["entries"]]
        self.assertIn("sd15", family_ids)
        self.assertIn("chroma", family_ids)
        self.assertIn("flux", family_ids)
        self.assertIn("ideogram4", family_ids)
        self.assertIn("krea2_turbo", family_ids)
        self.assertIn("flux_krea_dev", family_ids)
        self.assertIn("flux2_dev", family_ids)
        self.assertIn("ernie_image", family_ids)
        self.assertIn("qwen_image_edit", family_ids)
        self.assertNotIn("qwen_image_edit_multi_lora", family_ids)
        self.assertNotIn("klein_4b_distilled", family_ids)
        self.assertNotIn("klein_9b_distilled", family_ids)
        self.assertIn("qwen_image_edit_2511", family_ids)
        self.assertIn("firered_image_edit", family_ids)
        self.assertIn("firered_image_edit_lightning", family_ids)
        self.assertIn("flux_kontext_dev_edit", family_ids)
        self.assertIn("flux2_image_edit", family_ids)
        self.assertIn("klein_9b_kv_image_edit", family_ids)
        self.assertIn("longcat_image_edit", family_ids)
        self.assertIn("z_image_turbo", family_ids)
        flux_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "flux")
        flux_krea_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "flux_krea_dev")
        flux2_dev_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "flux2_dev")
        ideogram_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "ideogram4")
        flux2_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "flux2_dev")
        krea2_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "krea2_turbo")
        krea_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "krea2_turbo")
        ernie_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "ernie_image")
        qwen_image_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "qwen_image")
        z_turbo_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "z_image_turbo")
        self.assertEqual(flux_entry["translation_base_family"], "sdxl")
        self.assertEqual(flux_entry["public_base_family"], "flux")
        self.assertFalse(flux_entry["text_encoder_visible"])
        self.assertTrue(flux_entry["template_lora_visible"])
        self.assertTrue(flux_entry["template_lora_override_allowed"])
        self.assertEqual(flux_entry["official_template_lora_label"], "Flux_2-Turbo-LoRA_comfyui.safetensors")
        self.assertFalse(flux_entry["shift_visible"])
        self.assertEqual(flux_entry["available_surface_flows"], ["txt2img"])
        self.assertEqual(flux_krea_entry["public_base_family"], "flux")
        self.assertFalse(flux_krea_entry["template_lora_visible"])
        self.assertEqual(flux_krea_entry["available_surface_flows"], ["txt2img"])
        self.assertEqual(flux2_dev_entry["public_base_family"], "flux2")
        self.assertTrue(flux2_dev_entry["flux_guidance_visible"])
        self.assertEqual(flux2_dev_entry["default_flux_guidance"], 4.0)
        self.assertTrue(flux2_dev_entry["template_lora_visible"])
        self.assertEqual(flux2_dev_entry["official_template_lora_label"], "Flux_2-Turbo-LoRA_comfyui.safetensors")
        self.assertEqual(flux2_dev_entry["available_surface_flows"], ["txt2img"])
        self.assertEqual(ideogram_entry["public_base_family"], "ideogram4")
        self.assertEqual(ideogram_entry["default_steps"], 20)
        self.assertEqual(ideogram_entry["default_cfg_scale"], 7.0)
        self.assertEqual(ideogram_entry["default_ideogram_mode"], "default")
        self.assertEqual(ideogram_entry["ideogram_modes"], ["quality", "default", "turbo"])
        self.assertFalse(flux2_entry["default_template_lora_enabled"])
        self.assertEqual(flux2_entry["default_template_lora_strength"], 1.0)
        self.assertFalse(krea2_entry["default_template_lora_enabled"])
        self.assertEqual(krea2_entry["default_template_lora_strength"], 0.8)
        self.assertEqual(krea2_entry["default_template_lora_trigger_word"], "muted minimalist sketch style")
        self.assertFalse(ideogram_entry["text_encoder_visible"])
        self.assertEqual(krea_entry["public_base_family"], "krea2")
        self.assertEqual(krea_entry["default_steps"], 8)
        self.assertEqual(krea_entry["default_cfg_scale"], 1.0)
        self.assertTrue(krea_entry["template_lora_visible"])
        self.assertEqual(krea_entry["official_template_lora_label"], "krea2_darkbrush.safetensors")
        self.assertEqual(ernie_entry["translation_base_family"], "sdxl")
        self.assertEqual(ernie_entry["public_base_family"], "ernie_image")
        self.assertEqual(ernie_entry["default_steps"], 20)
        self.assertFalse(ernie_entry["text_encoder_visible"])
        self.assertTrue(ernie_entry["prompt_enhancement_visible"])
        self.assertEqual(qwen_image_entry["default_steps"], 50)
        self.assertEqual(qwen_image_entry["default_cfg_scale"], 4.0)
        self.assertEqual(qwen_image_entry["default_shift"], 3.1)
        self.assertEqual(
            qwen_image_entry["official_template_lora_label"],
            "Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors",
        )
        chroma_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "chroma")
        qwen_edit_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "qwen_image_edit")
        qwen_edit_2511_entry = next(
            entry for entry in payload["model_families"]["entries"] if entry["id"] == "qwen_image_edit_2511"
        )
        firered_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "firered_image_edit")
        firered_lightning_entry = next(
            entry for entry in payload["model_families"]["entries"] if entry["id"] == "firered_image_edit_lightning"
        )
        kontext_edit_entry = next(
            entry for entry in payload["model_families"]["entries"] if entry["id"] == "flux_kontext_dev_edit"
        )
        flux2_edit_entry = next(entry for entry in payload["model_families"]["entries"] if entry["id"] == "flux2_image_edit")
        klein_kv_edit_entry = next(
            entry for entry in payload["model_families"]["entries"] if entry["id"] == "klein_9b_kv_image_edit"
        )
        longcat_edit_entry = next(
            entry for entry in payload["model_families"]["entries"] if entry["id"] == "longcat_image_edit"
        )
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
        self.assertTrue(qwen_edit_entry["image_edit_profile"])
        self.assertEqual(qwen_edit_entry["request_contract_surface"], "img2img")
        self.assertEqual(qwen_edit_entry["reference_input_mode"], "single")
        self.assertEqual(qwen_edit_entry["max_direct_references"], 1)
        self.assertEqual(qwen_edit_entry["encoder_family"], "qwen_image_edit")
        self.assertEqual(qwen_edit_entry["template_lora_chain_mode"], "single")
        self.assertEqual(qwen_edit_entry["available_surface_flows"], ["img2img"])
        self.assertIn("Legacy Qwen-Image Edit", qwen_edit_entry["compatibility_summary"])
        self.assertTrue(qwen_edit_2511_entry["image_edit_profile"])
        self.assertEqual(qwen_edit_2511_entry["request_contract_surface"], "img2img")
        self.assertEqual(qwen_edit_2511_entry["reference_input_mode"], "multi")
        self.assertEqual(qwen_edit_2511_entry["max_direct_references"], 3)
        self.assertEqual(qwen_edit_2511_entry["encoder_family"], "qwen_image_edit_2511")
        self.assertEqual(qwen_edit_2511_entry["template_lora_chain_mode"], "none")
        self.assertTrue(qwen_edit_2511_entry["shift_visible"])
        self.assertEqual(qwen_edit_2511_entry["default_shift"], 3.1)
        self.assertFalse(qwen_edit_2511_entry["edit_megapixels_visible"])
        self.assertFalse(qwen_edit_2511_entry["template_lora_visible"])
        self.assertEqual(qwen_edit_2511_entry["available_surface_flows"], ["img2img"])
        self.assertTrue(firered_entry["image_edit_profile"])
        self.assertEqual(firered_entry["reference_input_mode"], "multi")
        self.assertEqual(firered_entry["max_direct_references"], 3)
        self.assertEqual(firered_entry["encoder_family"], "qwen_image_edit_plus")
        self.assertFalse(firered_entry["template_lora_visible"])
        self.assertTrue(firered_lightning_entry["template_lora_visible"])
        self.assertEqual(
            firered_lightning_entry["official_template_lora_label"],
            "FireRed-Image-Edit-1.0-Lightning-8steps-v1.0.safetensors",
        )
        self.assertEqual(firered_lightning_entry["template_lora_chain_mode"], "single")
        self.assertTrue(kontext_edit_entry["image_edit_profile"])
        self.assertEqual(kontext_edit_entry["reference_input_mode"], "multi")
        self.assertEqual(kontext_edit_entry["max_direct_references"], 3)
        self.assertEqual(kontext_edit_entry["encoder_family"], "flux_clip_text")
        self.assertTrue(kontext_edit_entry["flux_guidance_visible"])
        self.assertEqual(kontext_edit_entry["available_surface_flows"], ["img2img"])
        self.assertTrue(flux2_edit_entry["image_edit_profile"])
        self.assertEqual(flux2_edit_entry["reference_input_mode"], "single")
        self.assertEqual(flux2_edit_entry["default_width"], 1248)
        self.assertEqual(flux2_edit_entry["default_height"], 832)
        self.assertTrue(flux2_edit_entry["edit_megapixels_visible"])
        self.assertEqual(flux2_edit_entry["default_edit_megapixels"], 1.0)
        self.assertTrue(flux2_edit_entry["flux_guidance_visible"])
        self.assertTrue(klein_kv_edit_entry["image_edit_profile"])
        self.assertEqual(klein_kv_edit_entry["reference_input_mode"], "multi")
        self.assertEqual(klein_kv_edit_entry["max_direct_references"], 3)
        self.assertEqual(klein_kv_edit_entry["encoder_family"], "flux_clip_text")
        self.assertIn("Legacy Flux.2 Klein 9B KV", klein_kv_edit_entry["compatibility_summary"])
        self.assertTrue(longcat_edit_entry["image_edit_profile"])
        self.assertEqual(longcat_edit_entry["reference_input_mode"], "single")
        self.assertEqual(longcat_edit_entry["encoder_family"], "qwen_image_edit")
        self.assertTrue(longcat_edit_entry["flux_guidance_visible"])
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
