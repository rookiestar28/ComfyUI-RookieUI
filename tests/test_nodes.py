from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from rookieui import nodes


class RookieUINodesTests(unittest.TestCase):
    class _FakeTokenizerImpl:
        def __call__(self, text: str) -> dict[str, list[int]]:
            tokens = [index + 10 for index, _ in enumerate(text.split())]
            return {"input_ids": tokens or [42]}

        @staticmethod
        def get_vocab() -> dict[str, int]:
            return {",</w>": 999}

    class _FakeInnerTokenizer:
        def __init__(self) -> None:
            self.start_token = 101
            self.end_token = 102
            self.pad_token = 0
            self.max_length = 6
            self.max_word_length = 999
            self.tokens_start = 0
            self.tokenizer_adds_end_token = False
            self.pad_to_max_length = True
            self.pad_left = False
            self.embedding_identifier = "embedding:"
            self.embedding_directory = None
            self.tokenizer = RookieUINodesTests._FakeTokenizerImpl()

    class _FakeTokenizer:
        def __init__(self) -> None:
            self.clip_name = "l"
            self.clip = "clip_l"
            self.clip_l = RookieUINodesTests._FakeInnerTokenizer()

    class _FakeClip:
        def __init__(self) -> None:
            self.tokenizer = RookieUINodesTests._FakeTokenizer()

        def encode_from_tokens(
            self,
            tokens,
            return_pooled=True,
            return_dict=True,
        ) -> dict[str, object]:
            return {
                "cond": {"tokens": tokens},
                "pooled_output": "fake-pooled",
            }

    class _FakeSDXLTokenizer:
        def __init__(self) -> None:
            self.clip_l = RookieUINodesTests._FakeInnerTokenizer()
            self.clip_g = RookieUINodesTests._FakeInnerTokenizer()

    class _FakeSDXLClip:
        def __init__(self) -> None:
            self.tokenizer = RookieUINodesTests._FakeSDXLTokenizer()

        def encode_from_tokens(
            self,
            tokens,
            return_pooled=True,
            return_dict=True,
        ) -> dict[str, object]:
            return {
                "cond": {"tokens": tokens},
                "pooled_output": "fake-sdxl-pooled",
            }

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
        self.assertIn("RookieUIControlNetPreprocess", nodes.NODE_CLASS_MAPPINGS)

    def test_a1111_text_encode_node_is_registered(self) -> None:
        self.assertIn("RookieUIA1111TextEncode", nodes.NODE_CLASS_MAPPINGS)

    def test_a1111_text_encode_sdxl_node_is_registered(self) -> None:
        self.assertIn("RookieUIA1111TextEncodeSDXL", nodes.NODE_CLASS_MAPPINGS)

    def test_a1111_text_encode_node_keeps_break_as_tokenizer_chunk_boundary(self) -> None:
        conditioning, = nodes.RookieUIA1111TextEncode().encode(
            text="hero BREAK villain",
            clip=self._FakeClip(),
            steps=10,
        )

        self.assertEqual(len(conditioning), 1)
        token_batches = conditioning[0][0]["tokens"]["l"]
        self.assertEqual(len(token_batches), 2)

    def test_a1111_text_encode_node_emits_schedule_and_branch_metadata(self) -> None:
        conditioning, = nodes.RookieUIA1111TextEncode().encode(
            text="hero AND villain [soft:sharp:0.5]:0.7",
            clip=self._FakeClip(),
            steps=10,
        )

        self.assertEqual(len(conditioning), 3)
        self.assertEqual(conditioning[0][1]["start_percent"], 0.0)
        self.assertEqual(conditioning[0][1]["end_percent"], 1.0)
        self.assertNotIn("weight", conditioning[0][1])
        self.assertEqual(conditioning[1][1]["start_percent"], 0.0)
        self.assertEqual(conditioning[1][1]["end_percent"], 0.5)
        self.assertEqual(conditioning[1][1]["weight"], 0.7)
        self.assertEqual(conditioning[2][1]["start_percent"], 0.5)
        self.assertEqual(conditioning[2][1]["end_percent"], 1.0)
        self.assertEqual(conditioning[2][1]["weight"], 0.7)

    def test_a1111_text_encode_sdxl_node_keeps_break_as_dual_tokenizer_chunk_boundary(self) -> None:
        conditioning, = nodes.RookieUIA1111TextEncodeSDXL().encode(
            clip=self._FakeSDXLClip(),
            width=1024,
            height=1024,
            crop_w=0,
            crop_h=0,
            target_width=1024,
            target_height=1024,
            text_g="hero BREAK villain",
            text_l="hero BREAK villain",
            steps=10,
        )

        self.assertEqual(len(conditioning), 1)
        token_batches = conditioning[0][0]["tokens"]
        self.assertEqual(len(token_batches["l"]), 2)
        self.assertEqual(len(token_batches["g"]), 2)

    def test_a1111_text_encode_sdxl_node_emits_schedule_and_size_metadata(self) -> None:
        conditioning, = nodes.RookieUIA1111TextEncodeSDXL().encode(
            clip=self._FakeSDXLClip(),
            width=1152,
            height=896,
            crop_w=0,
            crop_h=0,
            target_width=1152,
            target_height=896,
            text_g="hero AND villain [soft:sharp:0.5]:0.7",
            text_l="hero AND villain [soft:sharp:0.5]:0.7",
            steps=10,
        )

        self.assertEqual(len(conditioning), 3)
        self.assertEqual(conditioning[0][1]["pooled_output"], "fake-sdxl-pooled")
        self.assertEqual(conditioning[0][1]["width"], 1152)
        self.assertEqual(conditioning[0][1]["height"], 896)
        self.assertEqual(conditioning[0][1]["target_width"], 1152)
        self.assertEqual(conditioning[0][1]["target_height"], 896)
        self.assertEqual(conditioning[1][1]["start_percent"], 0.0)
        self.assertEqual(conditioning[1][1]["end_percent"], 0.5)
        self.assertEqual(conditioning[1][1]["weight"], 0.7)

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
