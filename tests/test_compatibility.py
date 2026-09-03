from __future__ import annotations

import asyncio
import types
import unittest
from unittest import mock

from rookieui.api import routes
from rookieui.services import compatibility
from rookieui.services.compatibility import build_compatibility_payload


class _FakeJsonRequest:
    async def json(self) -> dict[str, object]:
        return {}


class CompatibilityCatalogTests(unittest.TestCase):
    def test_build_compatibility_payload_lists_sampler_catalog(self) -> None:
        payload = build_compatibility_payload()

        sampler_ids = [entry["id"] for entry in payload["samplers"]]
        self.assertIn("euler_ancestral", sampler_ids)

    def test_live_sampler_registry_projects_new_sampler_without_fallback_expansion(self) -> None:
        host_module = types.SimpleNamespace(
            KSampler=types.SimpleNamespace(
                SAMPLERS=("euler", "euler_ancestral", "cfgpp_ud10_ab"),
            )
        )
        with mock.patch.object(compatibility, "_load_comfy_samplers_module", return_value=host_module):
            payload = compatibility.build_compatibility_payload()

        entries = {entry["id"]: entry for entry in payload["samplers"]}
        self.assertEqual(list(entries), ["euler", "euler_ancestral", "cfgpp_ud10_ab"])
        self.assertEqual(entries["cfgpp_ud10_ab"]["title"], "CFGPP UD10 AB")
        self.assertEqual(entries["cfgpp_ud10_ab"]["tier"], "extended")
        self.assertTrue(entries["euler_ancestral"]["default"])

    def test_sampler_validation_rejects_unknown_live_value_without_substitution(self) -> None:
        host_module = types.SimpleNamespace(
            KSampler=types.SimpleNamespace(SAMPLERS=("euler", "cfgpp_ud10_ab"))
        )
        with mock.patch.object(compatibility, "_load_comfy_samplers_module", return_value=host_module):
            self.assertEqual(compatibility.validate_sampler_name("cfgpp_ud10_ab"), "cfgpp_ud10_ab")
            with self.assertRaisesRegex(ValueError, "Unsupported RookieUI sampler"):
                compatibility.validate_sampler_name("not_a_sampler")

    def test_no_host_sampler_catalog_remains_the_frozen_fallback(self) -> None:
        with mock.patch.object(compatibility, "_load_comfy_samplers_module", return_value=None):
            payload = compatibility.build_compatibility_payload()

        self.assertEqual(
            [entry["id"] for entry in payload["samplers"]],
            [
                "euler",
                "euler_ancestral",
                "heun",
                "ddim",
                "res_multistep",
                "dpmpp_2m",
                "dpmpp_sde",
                "dpmpp_2m_sde",
                "uni_pc",
            ],
        )

    def test_build_compatibility_payload_lists_extended_scheduler_catalog(self) -> None:
        payload = build_compatibility_payload()

        scheduler_ids = [entry["id"] for entry in payload["schedulers"]]
        self.assertIn("ddim_uniform", scheduler_ids)
        self.assertIn("kl_optimal", scheduler_ids)

    def test_build_compatibility_payload_lists_secondary_newer_families(self) -> None:
        payload = build_compatibility_payload()

        family_ids = [entry["id"] for entry in payload["newer_family_profiles"]]
        self.assertIn("chroma", family_ids)
        self.assertIn("klein_4b", family_ids)
        self.assertIn("hidream_i1_full", family_ids)
        self.assertIn("longcat_image", family_ids)
        self.assertIn("z_image_turbo", family_ids)
        self.assertIn("anima", family_ids)
        self.assertIn("ernie_image", family_ids)

    def test_compatibility_route_returns_catalog_payload(self) -> None:
        response = asyncio.run(routes.compatibility(_FakeJsonRequest()))

        self.assertEqual(response["status"], 200)
        self.assertIn("samplers", response["payload"])
        self.assertIn("runtime_profiles", response["payload"])
        self.assertIn("dtype_profiles", response["payload"])
