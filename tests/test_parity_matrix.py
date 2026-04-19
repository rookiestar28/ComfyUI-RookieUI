from __future__ import annotations

import unittest

from rookieui.services.parity_matrix import (
    build_parity_payload,
    get_parity_profile,
    normalize_sampler_name,
    normalize_scheduler_name,
)


class ParityMatrixTests(unittest.TestCase):
    def test_build_parity_payload_lists_current_model_family_profiles(self) -> None:
        payload = build_parity_payload()
        profile_ids = [profile["id"] for profile in payload["profiles"]]

        self.assertEqual(
            profile_ids,
            [
                "sd15",
                "sdxl",
                "pony",
                "illustrious",
                "noob",
                "anima",
                "chroma",
                "ernie_image",
                "ernie_image_turbo",
                "flux",
                "klein_4b_distilled",
                "klein_4b",
                "klein_9b_distilled",
                "klein_9b",
                "hidream_i1_dev_fp8",
                "hidream_i1_fast",
                "hidream_i1_full",
                "longcat_image",
                "qwen_image",
                "qwen_image_edit",
                "z_image",
                "z_image_turbo",
            ],
        )

    def test_get_parity_profile_returns_sdxl_family_profile(self) -> None:
        profile = get_parity_profile("pony")

        self.assertEqual(profile.base_family, "sdxl")
        self.assertEqual(profile.prompt_encoder, "clip_text_encode_sdxl")

    def test_get_parity_profile_returns_flux_lane_profile(self) -> None:
        profile = get_parity_profile("flux")

        self.assertEqual(profile.base_family, "sdxl")
        self.assertEqual(profile.default_sampler, "euler")

    def test_get_parity_profile_returns_secondary_turbo_lane_profile(self) -> None:
        profile = get_parity_profile("zit")

        self.assertEqual(profile.base_family, "sdxl")
        self.assertEqual(profile.id, "z_image_turbo")
        self.assertEqual(profile.default_steps, 8)
        self.assertEqual(profile.default_sampler, "res_multistep")
        self.assertEqual(profile.default_scheduler, "simple")

    def test_get_parity_profile_uses_non_lightning_qwen_baseline_defaults(self) -> None:
        profile = get_parity_profile("qwen_image")

        self.assertEqual(profile.default_width, 1328)
        self.assertEqual(profile.default_height, 1328)
        self.assertEqual(profile.default_steps, 2)
        self.assertEqual(profile.default_cfg_scale, 1.0)
        self.assertEqual(profile.default_sampler, "euler")
        self.assertEqual(profile.default_scheduler, "simple")

    def test_get_parity_profile_maps_legacy_lumina_alias_to_z_image_defaults(self) -> None:
        profile = get_parity_profile("lumina")

        self.assertEqual(profile.id, "z_image")
        self.assertEqual(profile.default_steps, 25)
        self.assertEqual(profile.default_cfg_scale, 4.0)
        self.assertEqual(profile.default_sampler, "res_multistep")
        self.assertEqual(profile.default_scheduler, "simple")

    def test_get_parity_profile_uses_ernie_host_defaults(self) -> None:
        profile = get_parity_profile("ernie_image")

        self.assertEqual(profile.base_family, "sdxl")
        self.assertEqual(profile.default_width, 1024)
        self.assertEqual(profile.default_height, 1024)
        self.assertEqual(profile.default_steps, 40)
        self.assertEqual(profile.default_cfg_scale, 4.0)
        self.assertEqual(profile.default_sampler, "euler")
        self.assertEqual(profile.default_scheduler, "simple")

    def test_normalize_sampler_name_handles_a1111_aliases(self) -> None:
        self.assertEqual(normalize_sampler_name("Euler a"), "euler_ancestral")
        self.assertEqual(normalize_sampler_name("DPM++ 2M"), "dpmpp_2m")

    def test_normalize_scheduler_name_uses_sampler_override(self) -> None:
        scheduler = normalize_scheduler_name(
            "DPM++ 2M Karras",
            None,
            default_scheduler="normal",
        )

        self.assertEqual(scheduler, "karras")

    def test_normalize_scheduler_name_maps_extended_scheduler_aliases(self) -> None:
        self.assertEqual(
            normalize_scheduler_name(
                "Euler",
                "DDIM",
                default_scheduler="normal",
            ),
            "ddim_uniform",
        )
        self.assertEqual(
            normalize_scheduler_name(
                "Euler",
                "KL Optimal",
                default_scheduler="normal",
            ),
            "kl_optimal",
        )
