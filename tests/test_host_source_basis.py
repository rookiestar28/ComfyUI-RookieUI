from __future__ import annotations

import unittest

from rookieui.contracts import host_source_basis as source_basis
from rookieui.contracts.host_source_basis import (
    HOST_SOURCE_BASIS,
    WORKFLOW_TEMPLATE_ARTIFACTS,
    WORKFLOW_TEMPLATE_COMPONENT_ARTIFACTS,
    WORKFLOW_TEMPLATE_DELTA_0_11_2_TO_0_11_6,
)


class HostSourceBasisTests(unittest.TestCase):
    def test_host_envelopes_remain_distinct_and_exact(self) -> None:
        self.assertEqual(HOST_SOURCE_BASIS.core.revision, "5cc026f5b81b3f01fe7a1438a0fd4131d2ebda25")
        self.assertEqual(HOST_SOURCE_BASIS.core.frontend_package_version, "1.47.11")
        self.assertEqual(HOST_SOURCE_BASIS.core.workflow_templates_version, "0.11.20")
        self.assertEqual(HOST_SOURCE_BASIS.core.embedded_docs_version, "0.5.9")
        self.assertEqual(HOST_SOURCE_BASIS.frontend.revision, "e1718dacb7bd8afeff41f00069747ff55065bf50")
        self.assertEqual(HOST_SOURCE_BASIS.frontend.source_version, "1.49.2")
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
        self.assertEqual(
            WORKFLOW_TEMPLATE_ARTIFACTS["0.11.20"].sha256,
            "51a997f697eb04319185231744c76f0af2975c281557afee897650ea0dab775f",
        )
        for version, artifact in WORKFLOW_TEMPLATE_ARTIFACTS.items():
            with self.subTest(version=version):
                self.assertEqual(artifact.version, version)
                self.assertEqual(len(artifact.sha256), 64)
                self.assertNotIn("latest", artifact.filename.lower())

    def test_current_workflow_template_component_closure_is_exact(self) -> None:
        current = {
            artifact.package: (artifact.version, artifact.sha256)
            for artifact in WORKFLOW_TEMPLATE_COMPONENT_ARTIFACTS
            if artifact.basis_version == "0.11.20"
        }
        self.assertEqual(
            current,
            {
                "comfyui-workflow-templates-core": (
                    "0.3.285",
                    "565fe48a98b39e43c55275df152ea2292616b5b68a5a4884a564aaa76b8270be",
                ),
                "comfyui-workflow-templates-json": (
                    "0.1.19",
                    "d30ad6c6043a1fb022065a04f21bb88e34fff61af8605ef848b4462bb9a2091f",
                ),
                "comfyui-workflow-templates-media-assets-01": (
                    "0.1.13",
                    "7668f34f80fec894fe35d04f369d168cd1a90fb74d5694da5f728c563c49fe09",
                ),
                "comfyui-workflow-templates-media-api": (
                    "0.3.84",
                    "c2d6a5999ac39e4f37f47ae231c92557defe5addb2cc6ab5c11410b4d5a2910a",
                ),
                "comfyui-workflow-templates-media-image": (
                    "0.3.160",
                    "d4a5c5541c7088f6adb1c7da41f5d7c1c14a037eda6a61cd8b4b76c251faaa93",
                ),
                "comfyui-workflow-templates-media-other": (
                    "0.3.229",
                    "ce3d98fa9d84b914c335fe5c9bc903cfefbe1932b1bc3cb6baef7f371b4bd435",
                ),
                "comfyui-workflow-templates-media-video": (
                    "0.3.101",
                    "6270fd61c8c3931b6f0031abac7d4c90ced624de6c7918bff85b89e6c3d7493c",
                ),
            },
        )

    def test_current_workflow_surface_disposition_is_complete_and_disjoint(self) -> None:
        delta = getattr(source_basis, "WORKFLOW_TEMPLATE_DELTA_0_11_6_TO_0_11_20", None)
        self.assertIsNotNone(delta)
        self.assertEqual(delta.from_version, "0.11.6")
        self.assertEqual(delta.to_version, "0.11.20")
        self.assertEqual(
            (delta.added_count, delta.removed_count, delta.changed_count, delta.unchanged_count),
            (41, 6, 138, 332),
        )
        self.assertEqual(
            delta.source_report_sha256,
            "2dd6322d3f7c78c8f91b9f6c03864ae586e8a7f9c58507a8fa41b2c24c3ee306",
        )
        ledgers = tuple(
            set(values)
            for values in (delta.supported, delta.deferred, delta.removed, delta.reference_only)
        )
        for index, left in enumerate(ledgers):
            for right in ledgers[index + 1 :]:
                self.assertFalse(left & right)
        self.assertEqual(tuple(map(len, ledgers)), (4, 81, 6, 94))
        self.assertEqual(len(set().union(*ledgers)), 185)
        self.assertIn("image_krea2_turbo_t2i", ledgers[0])
        for deferred in (
            "image_anima_lllite_any_control_to_image",
            "image_joyai_image_edit",
            "image_krea2_turbo_int8_image_style_reference",
            "image_mage_flow_edit_int8",
        ):
            self.assertIn(deferred, ledgers[1])
        for reference_only in (
            "api_recraft_v4_1_text_to_vector",
            "video_wan_dancer",
        ):
            self.assertIn(reference_only, ledgers[3])

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
