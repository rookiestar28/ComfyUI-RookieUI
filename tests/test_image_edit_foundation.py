from __future__ import annotations

import unittest

from rookieui.services.workflow_builders.core import NodeIdAllocator
from rookieui.services.workflow_builders.image_edit_foundation import (
    _append_flux_kontext_multi_reference_method_node,
    _append_reference_latent_chain,
    _append_reference_vae_latents,
    _build_image_edit_reference_bundle,
)


class ImageEditFoundationTests(unittest.TestCase):
    def test_build_reference_bundle_preserves_order_and_scales_main_only(self) -> None:
        workflow: dict[str, object] = {}
        bundle = _build_image_edit_reference_bundle(
            workflow,
            allocator=NodeIdAllocator(start=1),
            reference_assets=["ref-a", "ref-b", "ref-c"],
            main_reference_index=1,
            megapixels=1.5,
            scale_mode="main_only",
        )

        self.assertEqual(bundle.ordered_assets, ("ref-a", "ref-b", "ref-c"))
        self.assertEqual(bundle.image_node_ids, ("1", "4", "3"))
        self.assertEqual(bundle.main_image_node_id, "4")
        self.assertEqual(workflow["1"]["class_type"], "RookieUILoadAssetImage")
        self.assertEqual(workflow["2"]["class_type"], "RookieUILoadAssetImage")
        self.assertEqual(workflow["3"]["class_type"], "RookieUILoadAssetImage")
        self.assertEqual(workflow["4"]["class_type"], "ImageScaleToTotalPixels")
        self.assertEqual(workflow["4"]["inputs"]["image"], ["2", 0])

    def test_build_reference_bundle_can_scale_all_references(self) -> None:
        workflow: dict[str, object] = {}
        bundle = _build_image_edit_reference_bundle(
            workflow,
            allocator=NodeIdAllocator(start=1),
            reference_assets=["ref-a", "ref-b"],
            main_reference_index=0,
            megapixels=1.0,
            scale_mode="all",
        )

        self.assertEqual(bundle.image_node_ids, ("3", "4"))
        self.assertEqual(workflow["3"]["class_type"], "ImageScaleToTotalPixels")
        self.assertEqual(workflow["4"]["class_type"], "ImageScaleToTotalPixels")

    def test_append_reference_vae_latents_builds_parallel_latent_nodes(self) -> None:
        workflow: dict[str, object] = {}
        latent_ids = _append_reference_vae_latents(
            workflow,
            allocator=NodeIdAllocator(start=10),
            image_node_ids=("2", "4"),
            vae_source=["9", 0],
        )

        self.assertEqual(latent_ids, ("10", "11"))
        self.assertEqual(workflow["10"]["inputs"]["pixels"], ["2", 0])
        self.assertEqual(workflow["11"]["inputs"]["pixels"], ["4", 0])
        self.assertEqual(workflow["10"]["inputs"]["vae"], ["9", 0])

    def test_append_reference_latent_chain_preserves_input_order(self) -> None:
        workflow: dict[str, object] = {}
        output = _append_reference_latent_chain(
            workflow,
            allocator=NodeIdAllocator(start=20),
            conditioning_source=["5", 0],
            latent_node_ids=("8", "9", "10"),
        )

        self.assertEqual(output, ["22", 0])
        self.assertEqual(workflow["20"]["inputs"]["conditioning"], ["5", 0])
        self.assertEqual(workflow["20"]["inputs"]["latent"], ["8", 0])
        self.assertEqual(workflow["21"]["inputs"]["conditioning"], ["20", 0])
        self.assertEqual(workflow["21"]["inputs"]["latent"], ["9", 0])
        self.assertEqual(workflow["22"]["inputs"]["conditioning"], ["21", 0])
        self.assertEqual(workflow["22"]["inputs"]["latent"], ["10", 0])

    def test_append_flux_reference_method_normalizes_uxo_alias(self) -> None:
        workflow: dict[str, object] = {}
        node_id = _append_flux_kontext_multi_reference_method_node(
            workflow,
            allocator=NodeIdAllocator(start=30),
            conditioning_source=["7", 0],
            method="uxo",
        )

        self.assertEqual(node_id, "30")
        self.assertEqual(workflow["30"]["class_type"], "FluxKontextMultiReferenceLatentMethod")
        self.assertEqual(workflow["30"]["inputs"]["conditioning"], ["7", 0])
        self.assertEqual(workflow["30"]["inputs"]["reference_latents_method"], "uxo/uno")

    def test_append_flux_reference_method_rejects_unknown_method(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported Flux multi-reference latent method"):
            _append_flux_kontext_multi_reference_method_node(
                {},
                allocator=NodeIdAllocator(start=1),
                conditioning_source=["7", 0],
                method="mystery",
            )
