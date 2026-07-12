from __future__ import annotations

import unittest

from rookieui.api import routes
from rookieui.contracts.extras import EXTRAS_CONTRACT_VERSION
from rookieui.contracts.pnginfo import PNGINFO_CONTRACT_VERSION
from rookieui.contracts.prompt_workbench import PROMPT_WORKBENCH_CONTRACT_VERSION
from rookieui.contracts.queue import QUEUE_CONTRACT_VERSION
from rookieui.services.version import resolve_runtime_build_fingerprint, resolve_shell_version
from rookieui.security.route_guard import reset_registered_routes_for_tests
from tests.helpers.fake_prompt_server import FakePromptServerInstance


class RoutePayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_registered_routes_for_tests()

    def tearDown(self) -> None:
        reset_registered_routes_for_tests()

    def test_health_payload_shape(self) -> None:
        self.assertEqual(
            routes.build_health_payload(),
            {
                "service": "rookieui",
                "status": "ok",
                "deployment": {
                    "supported": True,
                    "mode": "single-user",
                    "detail": "RookieUI local single-user deployment boundary is active.",
                },
                "optional_aliases": {},
            },
        )

    def test_bootstrap_payload_lists_internal_routes(self) -> None:
        payload = routes.build_bootstrap_payload()
        self.assertEqual(payload["service"], "rookieui")
        self.assertEqual(payload["status"], "bootstrap-ready")
        self.assertEqual(payload["runtime"]["shell_version"], resolve_shell_version())
        self.assertEqual(payload["runtime"]["build_fingerprint"], resolve_runtime_build_fingerprint())
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
        self.assertIn("/rookieui/prompt-tools/config", payload["routes"])
        self.assertIn("/rookieui/prompt-tools/state", payload["routes"])
        self.assertIn("/rookieui/prompt-tools/history", payload["routes"])
        self.assertIn("/rookieui/prompt-tools/favorites", payload["routes"])
        self.assertIn("/rookieui/prompt-tools/blacklist", payload["routes"])
        self.assertIn("/rookieui/prompt-tools/providers", payload["routes"])
        self.assertIn("/rookieui/prompt-tools/export", payload["routes"])
        self.assertIn("/rookieui/prompt-tools/import", payload["routes"])
        self.assertIn("/rookieui/prompt-tools/translate", payload["routes"])
        self.assertIn("/rookieui/prompt-tools/assist", payload["routes"])
        self.assertIn("/rookieui/prompt-tools/catalog", payload["routes"])
        self.assertIn("/rookieui/prompt-tools/analyze", payload["routes"])
        self.assertIn("/rookieui/prompt-tools/upsample", payload["routes"])

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
        self.assertIn("chroma", preset_ids)
        self.assertIn("flux", preset_ids)
        self.assertIn("qwen_image", preset_ids)
        self.assertIn("klein_4b", preset_ids)
        self.assertIn("hidream_i1_full", preset_ids)
        self.assertIn("longcat_image", preset_ids)
        self.assertIn("z_image", preset_ids)
        self.assertIn("z_image_turbo", preset_ids)
        self.assertIn("anima", preset_ids)
        self.assertIn("ernie_image", preset_ids)
        self.assertIn("ernie_image_turbo", preset_ids)
        preset_lookup = {preset["id"]: preset for preset in payload["presets"]}
        self.assertEqual(preset_lookup["flux"]["profile"], "flux")
        self.assertEqual(preset_lookup["qwen_image"]["profile"], "qwen_image")
        self.assertEqual(preset_lookup["klein_4b"]["profile"], "klein_4b")
        self.assertEqual(preset_lookup["z_image_turbo"]["profile"], "z_image_turbo")
        self.assertEqual(preset_lookup["z_image_turbo"]["base_family"], "z_image")
        self.assertEqual(preset_lookup["ernie_image"]["profile"], "ernie_image")

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

    def test_prompt_tools_config_payload_exposes_contract(self) -> None:
        payload = routes.build_prompt_workbench_config_payload()

        self.assertEqual(payload["contract"]["version"], PROMPT_WORKBENCH_CONTRACT_VERSION)
        self.assertEqual(payload["contract"]["surface"], "prompt_tools_config")
        self.assertEqual(payload["blacklist"], {"enabled": False, "entries": [], "translation_entries": []})
        self.assertIn("danbooru_upsample", payload["host_actions"])
        self.assertEqual(payload["host_actions"]["danbooru_upsample"]["route_path"], "/rookieui/prompt-tools/upsample")

    def test_prompt_tools_provider_payload_exposes_catalog_contract(self) -> None:
        payload = routes.build_prompt_workbench_provider_catalog_payload()

        self.assertEqual(payload["contract"]["version"], PROMPT_WORKBENCH_CONTRACT_VERSION)
        self.assertEqual(payload["contract"]["surface"], "prompt_tools_providers")
        self.assertIn("openai", payload["surfaces"]["translation"]["shipped_provider_ids"])

    def test_prompt_tools_export_payload_masks_provider_secret_fields(self) -> None:
        payload = routes.build_prompt_workbench_export_payload()

        self.assertEqual(payload["contract"]["version"], PROMPT_WORKBENCH_CONTRACT_VERSION)
        self.assertEqual(payload["contract"]["surface"], "prompt_tools_export")
        self.assertEqual(payload["export"]["secret_policy"], "masked_provider_fields")  # pragma: allowlist secret
        self.assertIn("config", payload["export"]["includes"])

    def test_prompt_tools_catalog_snapshot_exposes_group_tags_and_prompt_library(self) -> None:
        payload = routes.build_prompt_workbench_catalog_snapshot(language="en")

        self.assertEqual(payload["contract"]["version"], PROMPT_WORKBENCH_CONTRACT_VERSION)
        self.assertEqual(payload["contract"]["surface"], "prompt_tools_catalog")
        self.assertTrue(payload["group_tags"]["groups"])
        self.assertTrue(payload["prompt_library"]["sections"])

    def test_register_routes_exposes_api_prefixed_rookieui_routes_for_fetch_api(self) -> None:
        prompt_server = FakePromptServerInstance()

        routes.register_routes(prompt_server)

        route_keys = {(method, path) for method, path, _ in prompt_server.app.router.routes}
        rookieui_route_keys = {
            (method, path)
            for method, path in route_keys
            if path.startswith("/rookieui/")
        }
        self.assertGreater(len(rookieui_route_keys), 30)
        for method, path in rookieui_route_keys:
            with self.subTest(method=method, path=path):
                self.assertIn((method, f"/api{path}"), route_keys)

        api_route_keys = {
            (method, path)
            for method, path in route_keys
            if path.startswith("/api/rookieui/")
        }
        self.assertEqual(len(api_route_keys), len(rookieui_route_keys))
