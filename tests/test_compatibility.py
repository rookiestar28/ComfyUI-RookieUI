from __future__ import annotations

import asyncio
import unittest

from rookieui.api import routes
from rookieui.services.compatibility import build_compatibility_payload


class _FakeJsonRequest:
    async def json(self) -> dict[str, object]:
        return {}


class CompatibilityCatalogTests(unittest.TestCase):
    def test_build_compatibility_payload_lists_sampler_catalog(self) -> None:
        payload = build_compatibility_payload()

        sampler_ids = [entry["id"] for entry in payload["samplers"]]
        self.assertIn("euler_ancestral", sampler_ids)

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
