from __future__ import annotations

import unittest

from rookieui.api import routes
from rookieui.contracts.extras import EXTRAS_CONTRACT_VERSION
from rookieui.contracts.pnginfo import PNGINFO_CONTRACT_VERSION
from rookieui.contracts.queue import QUEUE_CONTRACT_VERSION


class RoutePayloadTests(unittest.TestCase):
    def test_health_payload_shape(self) -> None:
        self.assertEqual(
            routes.build_health_payload(),
            {"service": "rookieui", "status": "ok"},
        )

    def test_bootstrap_payload_lists_internal_routes(self) -> None:
        payload = routes.build_bootstrap_payload()
        self.assertEqual(payload["service"], "rookieui")
        self.assertEqual(payload["status"], "bootstrap-ready")
        self.assertIn("/rookieui/health", payload["routes"])
        self.assertIn("/rookieui/bootstrap", payload["routes"])
        self.assertIn("/rookieui/capabilities", payload["routes"])
        self.assertIn("/rookieui/parity", payload["routes"])
        self.assertIn("/rookieui/compatibility", payload["routes"])
        self.assertIn("/rookieui/models", payload["routes"])
        self.assertIn("/rookieui/presets", payload["routes"])
        self.assertIn("/rookieui/queue", payload["routes"])
        self.assertIn("/rookieui/queue/{prompt_id}", payload["routes"])
        self.assertIn("/rookieui/pnginfo/parse", payload["routes"])
        self.assertIn("/rookieui/pnginfo/inspect", payload["routes"])
        self.assertIn("/rookieui/controlnet/model_list", payload["routes"])
        self.assertIn("/rookieui/controlnet/module_list", payload["routes"])
        self.assertIn("/rookieui/controlnet/control_types", payload["routes"])
        self.assertIn("/rookieui/controlnet/detect", payload["routes"])
        self.assertIn("/rookieui/adetailer/catalog", payload["routes"])
        self.assertIn("/rookieui/generate/txt2img", payload["routes"])
        self.assertIn("/rookieui/generate/img2img", payload["routes"])
        self.assertIn("/rookieui/extras/run", payload["routes"])

    def test_adetailer_snapshot_exposes_contract_and_detector_catalog(self) -> None:
        payload = routes.build_adetailer_snapshot()

        self.assertEqual(payload["contract"]["version"], "r74f77-20260414")
        self.assertEqual(payload["contract"]["unit_count"], 4)
        self.assertEqual(
            payload["contract"]["detector_provider_families"],
            ["none", "ultralytics_bbox", "ultralytics_segm", "mediapipe_face"],
        )
        self.assertEqual(payload["prompt_tokens"], ["[PROMPT]", "[SEP]", "[SKIP]"])
        self.assertIn("None", payload["detector_list"])
        self.assertIn("mediapipe_face_full", payload["detector_list"])
        self.assertIn("none", payload["controlnet_modes"])
        self.assertEqual(payload["availability"]["execution_backend"], "rookieui_comfy_native_refinement_pipeline")
        self.assertIn("detect_mask", payload["availability"]["runtime_stages"])
        self.assertIn("ADETAILER_DETECTOR_RUNTIME_FALLBACK_MASK", payload["warning_codes"])

    def test_parity_payload_lists_sampler_aliases(self) -> None:
        payload = routes.build_parity_snapshot()

        self.assertIn("profiles", payload)
        self.assertIn("sampler_aliases", payload)
        self.assertIn("euler a", payload["sampler_aliases"]["samplers"])
        self.assertIn("ddim", payload["sampler_aliases"]["scheduler_aliases"])

    def test_compatibility_payload_exposes_runtime_and_dtype_profiles(self) -> None:
        payload = routes.build_compatibility_snapshot()

        self.assertIn("samplers", payload)
        self.assertIn("schedulers", payload)
        self.assertIn("runtime_profiles", payload)
        self.assertIn("dtype_profiles", payload)

    def test_models_payload_exposes_shared_inventory(self) -> None:
        payload = routes.build_models_snapshot()

        self.assertIn("checkpoints", payload)
        self.assertIn("diffusion_models", payload)
        self.assertIn("controlnet", payload)
        self.assertIn("upscale_models", payload)
        self.assertIn("vae", payload)
        self.assertIn("text_encoders", payload)
        self.assertIn("embeddings", payload)
        self.assertIn("loras", payload)
        self.assertIn("catalog", payload)

    def test_presets_payload_exposes_sd_family_presets(self) -> None:
        payload = routes.build_presets_snapshot()

        preset_ids = [preset["id"] for preset in payload["presets"]]
        self.assertIn("sd15", preset_ids)
        self.assertIn("sdxl", preset_ids)
        self.assertIn("flux", preset_ids)
        self.assertIn("qwen_image", preset_ids)
        self.assertIn("klein", preset_ids)
        self.assertIn("lumina", preset_ids)
        self.assertIn("zit", preset_ids)
        self.assertIn("wan", preset_ids)
        self.assertIn("anima", preset_ids)
        preset_lookup = {preset["id"]: preset for preset in payload["presets"]}
        self.assertEqual(preset_lookup["flux"]["profile"], "flux")
        self.assertEqual(preset_lookup["qwen_image"]["profile"], "qwen_image")
        self.assertEqual(preset_lookup["klein"]["profile"], "klein")
        self.assertEqual(preset_lookup["zit"]["profile"], "zit")

    def test_queue_snapshot_payload_exposes_contract_envelope(self) -> None:
        payload = routes.build_queue_snapshot_payload()

        self.assertEqual(payload["service"], "rookieui")
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["contract"]["version"], QUEUE_CONTRACT_VERSION)

    def test_queue_job_snapshot_payload_exposes_contract_envelope(self) -> None:
        payload = routes.build_queue_job_snapshot_payload("prompt-1")

        self.assertEqual(payload["service"], "rookieui")
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["contract"]["version"], QUEUE_CONTRACT_VERSION)

    def test_pnginfo_contract_builder_matches_route_surface(self) -> None:
        contract = routes.build_pnginfo_contract_meta()

        self.assertEqual(contract["version"], PNGINFO_CONTRACT_VERSION)
        self.assertEqual(contract["surface"], "pnginfo_parse_inspect")

    def test_extras_contract_builder_matches_route_surface(self) -> None:
        contract = routes.build_extras_contract_meta()

        self.assertEqual(contract["version"], EXTRAS_CONTRACT_VERSION)
        self.assertEqual(contract["surface"], "extras_run")
