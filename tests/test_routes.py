from __future__ import annotations

import unittest

from rookieui.api import routes


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
        self.assertIn("/rookieui/generate/txt2img", payload["routes"])
        self.assertIn("/rookieui/generate/img2img", payload["routes"])
        self.assertIn("/rookieui/extras/run", payload["routes"])

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
        preset_lookup = {preset["id"]: preset for preset in payload["presets"]}
        self.assertEqual(preset_lookup["flux"]["profile"], "flux")
        self.assertEqual(preset_lookup["qwen_image"]["profile"], "qwen_image")
