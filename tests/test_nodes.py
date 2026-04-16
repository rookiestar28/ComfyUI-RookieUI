from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from rookieui import nodes


class RookieUINodesTests(unittest.TestCase):
    def test_load_asset_mask_validate_inputs_accepts_partial_signature(self) -> None:
        with mock.patch.object(nodes, "resolve_asset_path", return_value=Path("C:/tmp/mask.png")):
            result = nodes.RookieUILoadAssetMask.VALIDATE_INPUTS("mask_asset.png")
        self.assertTrue(result)

    def test_load_asset_mask_validate_inputs_accepts_channel_keyword(self) -> None:
        with mock.patch.object(nodes, "resolve_asset_path", return_value=Path("C:/tmp/mask.png")):
            result = nodes.RookieUILoadAssetMask.VALIDATE_INPUTS(
                "mask_asset.png",
                channel="red",
                invert=True,
                blur_radius=8,
            )
        self.assertTrue(result)

    def test_load_asset_mask_validate_inputs_returns_error_message(self) -> None:
        with mock.patch.object(nodes, "resolve_asset_path", side_effect=ValueError("invalid asset handle")):
            result = nodes.RookieUILoadAssetMask.VALIDATE_INPUTS("bad")
        self.assertEqual(result, "invalid asset handle")

    def test_load_asset_mask_is_changed_accepts_partial_signature(self) -> None:
        with mock.patch.object(nodes.RookieUILoadAssetImage, "IS_CHANGED", return_value="digest") as mock_changed:
            changed = nodes.RookieUILoadAssetMask.IS_CHANGED("mask_asset.png")
        self.assertEqual(changed, "digest")
        mock_changed.assert_called_once_with("mask_asset.png")

    def test_controlnet_preprocess_node_is_registered(self) -> None:
        self.assertIn("RookieUIA1111CLIPTextEncode", nodes.NODE_CLASS_MAPPINGS)
        self.assertIn("RookieUIA1111CLIPTextEncodeSDXL", nodes.NODE_CLASS_MAPPINGS)
        self.assertIn("RookieUIControlNetPreprocess", nodes.NODE_CLASS_MAPPINGS)
        self.assertIn("RookieUIControlNetApplyNativeAdvanced", nodes.NODE_CLASS_MAPPINGS)
        self.assertEqual(
            nodes.NODE_DISPLAY_NAME_MAPPINGS["RookieUIControlNetApplyNativeAdvanced"],
            "RookieUI ControlNet Apply (Advanced)",
        )

    def test_a1111_clip_text_encode_rewrites_square_bracket_deemphasis(self) -> None:
        class _FakeClip:
            def __init__(self) -> None:
                self.tokenized: list[str] = []

            def tokenize(self, text):
                self.tokenized.append(text)
                return [text]

            def encode_from_tokens_scheduled(self, tokens, add_dict=None):
                return {"tokens": tokens, "add_dict": add_dict or {}}

        clip = _FakeClip()
        node = nodes.RookieUIA1111CLIPTextEncode()

        conditioning, = node.encode(clip, "portrait [soft light]")

        self.assertEqual(clip.tokenized, ["portrait (soft light:0.9091)"])
        self.assertEqual(conditioning["tokens"], ["portrait (soft light:0.9091)"])

    def test_a1111_clip_text_encode_preserves_explicit_weighting(self) -> None:
        class _FakeClip:
            def __init__(self) -> None:
                self.tokenized: list[str] = []

            def tokenize(self, text):
                self.tokenized.append(text)
                return [text]

            def encode_from_tokens_scheduled(self, tokens, add_dict=None):
                return {"tokens": tokens, "add_dict": add_dict or {}}

        clip = _FakeClip()
        node = nodes.RookieUIA1111CLIPTextEncode()

        conditioning, = node.encode(clip, "portrait (eyes:1.3)")

        self.assertEqual(clip.tokenized, ["portrait (eyes:1.3)"])
        self.assertEqual(conditioning["tokens"], ["portrait (eyes:1.3)"])

    def test_a1111_clip_text_encode_sdxl_rewrites_both_channels(self) -> None:
        class _FakeClip:
            def __init__(self) -> None:
                self.tokenized: list[str] = []

            def tokenize(self, text):
                self.tokenized.append(text)
                return {"g": [f"g::{text}"], "l": [f"l::{text}"]}

            def encode_from_tokens_scheduled(self, tokens, add_dict=None):
                return {"tokens": tokens, "add_dict": add_dict or {}}

        clip = _FakeClip()
        node = nodes.RookieUIA1111CLIPTextEncodeSDXL()

        conditioning, = node.encode(
            clip,
            1024,
            1024,
            0,
            0,
            1024,
            1024,
            "hero [soft]",
            "avoid [harsh]",
        )

        self.assertEqual(
            clip.tokenized,
            ["hero (soft:0.9091)", "avoid (harsh:0.9091)", ""],
        )
        self.assertEqual(conditioning["tokens"]["g"], ["g::hero (soft:0.9091)"])
        self.assertEqual(conditioning["tokens"]["l"], ["l::avoid (harsh:0.9091)"])
        self.assertEqual(conditioning["add_dict"]["target_width"], 1024)

    def test_adetailer_detect_mask_node_is_registered(self) -> None:
        self.assertIn("RookieUIADetailerDetectMask", nodes.NODE_CLASS_MAPPINGS)
        self.assertEqual(
            nodes.NODE_DISPLAY_NAME_MAPPINGS["RookieUIADetailerDetectMask"],
            "RookieUI ADetailer Detect Mask",
        )

    def test_adetailer_detect_mask_returns_zero_for_none_detector(self) -> None:
        if nodes.torch is None:
            self.skipTest("torch is unavailable in this environment")

        detector = nodes.RookieUIADetailerDetectMask()
        image = nodes.torch.ones((1, 16, 16, 3), dtype=nodes.torch.float32)

        mask, = detector.detect(image=image, detector="None")

        self.assertEqual(tuple(mask.shape), (1, 16, 16))
        self.assertAlmostEqual(float(mask.max()), 0.0, places=4)

    def test_adetailer_detect_mask_generates_detector_mask(self) -> None:
        if nodes.torch is None:
            self.skipTest("torch is unavailable in this environment")

        detector = nodes.RookieUIADetailerDetectMask()
        image = nodes.torch.ones((1, 32, 32, 3), dtype=nodes.torch.float32)

        mask, = detector.detect(
            image=image,
            detector="face_yolov8n.pt",
            detector_family="ultralytics_bbox",
            confidence=0.4,
            mask_min_ratio=0.0,
            mask_max_ratio=1.0,
            dilate_erode=2,
            mask_blur=1,
        )

        self.assertEqual(tuple(mask.shape), (1, 32, 32))
        self.assertGreater(float(mask.max()), 0.0)
        self.assertLessEqual(float(mask.max()), 1.0)

    def test_controlnet_preprocess_applies_mask_when_enabled(self) -> None:
        if nodes.torch is None:
            self.skipTest("torch is unavailable in this environment")

        preprocess = nodes.RookieUIControlNetPreprocess()
        image = nodes.torch.ones((1, 2, 2, 3), dtype=nodes.torch.float32)
        mask = nodes.torch.tensor([[[1.0, 0.0], [0.5, 0.0]]], dtype=nodes.torch.float32)

        output, = preprocess.preprocess(
            image=image,
            module="none",
            processor_res=512,
            threshold_a=64.0,
            threshold_b=64.0,
            use_mask=True,
            mask=mask,
        )

        self.assertAlmostEqual(float(output[0, 0, 0, 0]), 1.0, places=4)
        self.assertAlmostEqual(float(output[0, 0, 1, 0]), 0.0, places=4)
        self.assertAlmostEqual(float(output[0, 1, 1, 0]), 0.0, places=4)

    def test_controlnet_preprocess_unsupported_module_falls_back_to_passthrough(self) -> None:
        if nodes.torch is None:
            self.skipTest("torch is unavailable in this environment")

        preprocess = nodes.RookieUIControlNetPreprocess()
        image = nodes.torch.full((1, 2, 2, 3), 0.25, dtype=nodes.torch.float32)

        output, = preprocess.preprocess(
            image=image,
            module="not-a-real-module",
            processor_res=512,
            threshold_a=64.0,
            threshold_b=64.0,
            use_mask=False,
            mask=None,
        )

        self.assertAlmostEqual(float(output[0, 0, 0, 0]), 0.25, places=4)
        self.assertAlmostEqual(float(output[0, 1, 1, 2]), 0.25, places=4)


if __name__ == "__main__":
    unittest.main()
