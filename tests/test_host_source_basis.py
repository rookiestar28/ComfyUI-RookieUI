from __future__ import annotations

import unittest

from rookieui.contracts.host_source_basis import (
    HOST_SOURCE_BASIS,
    WORKFLOW_TEMPLATE_ARTIFACTS,
    WORKFLOW_TEMPLATE_DELTA_0_11_2_TO_0_11_6,
)


class HostSourceBasisTests(unittest.TestCase):
    def test_host_envelopes_remain_distinct_and_exact(self) -> None:
        self.assertEqual(HOST_SOURCE_BASIS.core.revision, "69ea58697bb2f05124f5dc7e00ad111f7cfff645")
        self.assertEqual(HOST_SOURCE_BASIS.core.frontend_package_version, "1.45.20")
        self.assertEqual(HOST_SOURCE_BASIS.core.workflow_templates_version, "0.11.6")
        self.assertEqual(HOST_SOURCE_BASIS.frontend.revision, "b40fad0e755ddee5b09db3b93566f7e0a9f6967f")
        self.assertEqual(HOST_SOURCE_BASIS.frontend.source_version, "1.48.2")
        self.assertEqual(HOST_SOURCE_BASIS.desktop.revision, "e2d964b7456cea8423c7b9d3371c612313c06baa")
        self.assertEqual(HOST_SOURCE_BASIS.desktop.source_version, "0.9.4")
        self.assertEqual(HOST_SOURCE_BASIS.desktop.packaged_core_version, "0.22.3")
        self.assertEqual(HOST_SOURCE_BASIS.desktop.packaged_frontend_version, "1.43.18")
        self.assertNotEqual(
            HOST_SOURCE_BASIS.core.frontend_package_version,
            HOST_SOURCE_BASIS.frontend.source_version,
        )

    def test_workflow_template_artifacts_are_bound_to_exact_hashes(self) -> None:
        self.assertEqual(
            WORKFLOW_TEMPLATE_ARTIFACTS["0.11.2"].sha256,
            "7d24739323e234d23321ec717cc820c3ae7f207faa411560854d38278f496a58",
        )
        self.assertEqual(
            WORKFLOW_TEMPLATE_ARTIFACTS["0.11.6"].sha256,
            "67c290064ab9171637a863875da0726b5fe89cfb954645bf93e9098a8f2fdd21",
        )
        for version, artifact in WORKFLOW_TEMPLATE_ARTIFACTS.items():
            with self.subTest(version=version):
                self.assertEqual(artifact.version, version)
                self.assertEqual(len(artifact.sha256), 64)
                self.assertNotIn("latest", artifact.filename.lower())

    def test_exact_workflow_surface_delta_is_complete_and_disjoint(self) -> None:
        delta = WORKFLOW_TEMPLATE_DELTA_0_11_2_TO_0_11_6
        self.assertEqual(
            set(delta.added),
            {
                "api_bytedance_seed_audio1_0_t2a",
                "api_bytedance_seed_audio1_0_ta2a",
                "api_bytedance_seed_audio1_0_ti2a",
                "api_bytedance_seedream_5_0_pro_image_edit",
                "api_bytedance_seedream_5_0_pro_t2i",
                "image_krea2_turbo_t2i_int8",
                "image_z_image_turbo_int8",
            },
        )
        self.assertEqual(delta.changed, ("api_bytedance_seedream_5_0_lite_image_edit",))
        self.assertEqual(delta.removed, ())
        categories = (set(delta.added), set(delta.changed), set(delta.removed))
        self.assertFalse(categories[0] & categories[1])
        self.assertFalse(categories[0] & categories[2])
        self.assertFalse(categories[1] & categories[2])
        self.assertEqual(delta.supported, ())
        self.assertEqual(set(delta.deferred), set(delta.added) | set(delta.changed))


if __name__ == "__main__":
    unittest.main()
