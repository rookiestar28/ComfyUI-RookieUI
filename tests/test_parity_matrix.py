from __future__ import annotations

import unittest

from rookieui.services.parity_matrix import (
    build_parity_payload,
    get_parity_profile,
    normalize_sampler_name,
    normalize_scheduler_name,
)


class ParityMatrixTests(unittest.TestCase):
    def test_build_parity_payload_lists_sd_family_profiles(self) -> None:
        payload = build_parity_payload()
        profile_ids = [profile["id"] for profile in payload["profiles"]]

        self.assertEqual(
            profile_ids,
            ["sd15", "sdxl", "pony", "illustrious", "noob", "flux", "qwen_image"],
        )

    def test_get_parity_profile_returns_sdxl_family_profile(self) -> None:
        profile = get_parity_profile("pony")

        self.assertEqual(profile.base_family, "sdxl")
        self.assertEqual(profile.prompt_encoder, "clip_text_encode_sdxl")

    def test_get_parity_profile_returns_flux_lane_profile(self) -> None:
        profile = get_parity_profile("flux")

        self.assertEqual(profile.base_family, "sdxl")
        self.assertEqual(profile.default_sampler, "euler")

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
