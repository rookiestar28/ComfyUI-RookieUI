from __future__ import annotations

import unittest

from rookieui.services.workflow_builders.core import NodeIdAllocator
from rookieui.services.workflow_builders.image_edit_foundation import (
    _append_flux2_advanced_sampler_bundle,
    _append_flux_kontext_multi_reference_method_node,
    _append_flux_kv_cache_node,
    _append_flux_reference_method_branch,
    _append_image_stitch_chain,
    _append_mirrored_reference_latent_chains,
    _append_reference_latent_chain,
    _append_reference_vae_latents,
    _build_flux_kontext_reference_bundle,
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
        self.assertEqual(workflow["1"]["inputs"]["asset_handle"], "ref-a")
        self.assertEqual(workflow["2"]["inputs"]["asset_handle"], "ref-b")
        self.assertEqual(workflow["3"]["inputs"]["asset_handle"], "ref-c")
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

    def test_build_reference_bundle_passes_custom_resolution_steps(self) -> None:
        workflow: dict[str, object] = {}
        bundle = _build_image_edit_reference_bundle(
            workflow,
            allocator=NodeIdAllocator(start=1),
            reference_assets=["ref-a"],
            main_reference_index=0,
            megapixels=1.0,
            scale_mode="main_only",
            resolution_steps=16,
        )

        self.assertEqual(bundle.image_node_ids, ("2",))
        self.assertEqual(workflow["2"]["class_type"], "ImageScaleToTotalPixels")
        self.assertEqual(workflow["2"]["inputs"]["resolution_steps"], 16)

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

    def test_append_mirrored_reference_latent_chains_preserves_order_on_both_branches(self) -> None:
        workflow: dict[str, object] = {}
        positive_output, negative_output = _append_mirrored_reference_latent_chains(
            workflow,
            allocator=NodeIdAllocator(start=40),
            positive_conditioning_source=["5", 0],
            negative_conditioning_source=["6", 0],
            latent_node_ids=("8", "9"),
        )

        self.assertEqual(positive_output, ["41", 0])
        self.assertEqual(negative_output, ["43", 0])
        self.assertEqual(workflow["40"]["inputs"]["conditioning"], ["5", 0])
        self.assertEqual(workflow["41"]["inputs"]["conditioning"], ["40", 0])
        self.assertEqual(workflow["42"]["inputs"]["conditioning"], ["6", 0])
        self.assertEqual(workflow["43"]["inputs"]["conditioning"], ["42", 0])

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

    def test_append_image_stitch_chain_preserves_reference_order(self) -> None:
        workflow: dict[str, object] = {}
        stitched_id = _append_image_stitch_chain(
            workflow,
            allocator=NodeIdAllocator(start=50),
            image_node_ids=("10", "11", "12"),
            direction="down",
            match_image_size=False,
            spacing_width=8,
            spacing_color="black",
        )

        self.assertEqual(stitched_id, "51")
        self.assertEqual(workflow["50"]["class_type"], "ImageStitch")
        self.assertEqual(workflow["50"]["inputs"]["image1"], ["10", 0])
        self.assertEqual(workflow["50"]["inputs"]["image2"], ["11", 0])
        self.assertEqual(workflow["50"]["inputs"]["direction"], "down")
        self.assertFalse(workflow["50"]["inputs"]["match_image_size"])
        self.assertEqual(workflow["51"]["inputs"]["image1"], ["50", 0])
        self.assertEqual(workflow["51"]["inputs"]["image2"], ["12", 0])

    def test_build_flux_kontext_reference_bundle_stitches_scales_and_encodes(self) -> None:
        workflow: dict[str, object] = {}
        bundle = _build_flux_kontext_reference_bundle(
            workflow,
            allocator=NodeIdAllocator(start=60),
            image_node_ids=("3", "4"),
            vae_source=["9", 0],
        )

        self.assertEqual(bundle.stitched_image_node_id, "60")
        self.assertEqual(bundle.scaled_image_node_id, "61")
        self.assertEqual(bundle.latent_node_id, "62")
        self.assertEqual(workflow["60"]["class_type"], "ImageStitch")
        self.assertEqual(workflow["61"]["class_type"], "FluxKontextImageScale")
        self.assertEqual(workflow["61"]["inputs"]["image"], ["60", 0])
        self.assertEqual(workflow["62"]["class_type"], "VAEEncode")
        self.assertEqual(workflow["62"]["inputs"]["pixels"], ["61", 0])

    def test_append_flux_reference_method_branch_can_apply_guidance_then_method(self) -> None:
        workflow: dict[str, object] = {}
        output = _append_flux_reference_method_branch(
            workflow,
            allocator=NodeIdAllocator(start=70),
            conditioning_source=["5", 0],
            guidance=4.5,
            reference_method="index",
        )

        self.assertEqual(output, ["71", 0])
        self.assertEqual(workflow["70"]["class_type"], "FluxGuidance")
        self.assertEqual(workflow["71"]["class_type"], "FluxKontextMultiReferenceLatentMethod")
        self.assertEqual(workflow["71"]["inputs"]["conditioning"], ["70", 0])

    def test_append_flux_kv_cache_node_wraps_model_source(self) -> None:
        workflow: dict[str, object] = {}
        output = _append_flux_kv_cache_node(
            workflow,
            allocator=NodeIdAllocator(start=80),
            model_source=["9", 0],
        )

        self.assertEqual(output, ["80", 0])
        self.assertEqual(workflow["80"]["class_type"], "FluxKVCache")
        self.assertEqual(workflow["80"]["inputs"]["model"], ["9", 0])

    def test_append_flux2_advanced_sampler_bundle_builds_basic_guider_path(self) -> None:
        workflow: dict[str, object] = {}
        bundle = _append_flux2_advanced_sampler_bundle(
            workflow,
            allocator=NodeIdAllocator(start=90),
            model_source=["7", 0],
            size_image_id="12",
            positive_conditioning_source=["8", 0],
            steps=20,
            sampler_name="euler",
            noise_seed=1234,
        )

        self.assertEqual(bundle.latent_canvas.image_size_node_id, "90")
        self.assertEqual(bundle.latent_canvas.latent_node_id, "91")
        self.assertEqual(bundle.guider_node_id, "93")
        self.assertEqual(bundle.sigmas_node_id, "95")
        self.assertEqual(bundle.sampler_node_id, "96")
        self.assertEqual(workflow["90"]["class_type"], "GetImageSize")
        self.assertEqual(workflow["91"]["class_type"], "EmptyFlux2LatentImage")
        self.assertEqual(workflow["93"]["class_type"], "BasicGuider")
        self.assertEqual(workflow["95"]["class_type"], "Flux2Scheduler")
        self.assertEqual(workflow["96"]["class_type"], "SamplerCustomAdvanced")

    def test_append_flux2_advanced_sampler_bundle_builds_cfg_guider_path(self) -> None:
        workflow: dict[str, object] = {}
        bundle = _append_flux2_advanced_sampler_bundle(
            workflow,
            allocator=NodeIdAllocator(start=100),
            model_source=["7", 0],
            size_image_id="12",
            positive_conditioning_source=["8", 0],
            negative_conditioning_source=["9", 0],
            cfg_scale=1.0,
            steps=4,
            sampler_name="euler",
            noise_seed=4321,
        )

        self.assertEqual(bundle.guider_node_id, "103")
        self.assertEqual(workflow["103"]["class_type"], "CFGGuider")
        self.assertEqual(workflow["103"]["inputs"]["positive"], ["8", 0])
        self.assertEqual(workflow["103"]["inputs"]["negative"], ["9", 0])
        self.assertEqual(workflow["105"]["inputs"]["steps"], 4)
