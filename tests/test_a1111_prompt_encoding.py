from __future__ import annotations

import unittest
from copy import deepcopy

from rookieui import nodes
from rookieui.services.a1111_prompt_encoding import (
    A1111PromptEncodingOptions,
    _merge_encode_metadata,
    build_a1111_prompt_encoding_plan,
    encode_a1111_sdxl_prompt_conditioning,
    encode_a1111_sdxl_prompt_text_conditioning,
)


_OMITTED_METADATA = object()


def _scheduled_metadata(pooled_output, add_dict):
    metadata = {"pooled_output": pooled_output}
    # Match host dict.update: omission is valid, but explicit None must fail.
    metadata.update({} if add_dict is _OMITTED_METADATA else add_dict)
    return metadata


class _FakeClip:
    def __init__(self) -> None:
        self.tokenized: list[tuple[str, bool]] = []
        self.encoded: list[object] = []

    def tokenize(self, text, return_word_ids=False):
        self.tokenized.append((text, bool(return_word_ids)))
        if return_word_ids:
            return {"l": [[("BOS", 1.0, 0), (text, 1.0, 1), ("EOS", 1.0, 0)]]}
        return {"l": [[("BOS", 1.0), (text, 1.0), ("EOS", 1.0)]]}

    def encode_from_tokens_scheduled(self, tokens, add_dict=_OMITTED_METADATA):
        self.encoded.append(tokens)
        text = tokens["l"][0][1][0]
        return [[f"cond::{text}", _scheduled_metadata(f"pooled::{text}", add_dict)]]


class _FakeSDXLClip(_FakeClip):
    def tokenize(self, text, return_word_ids=False):
        self.tokenized.append((text, bool(return_word_ids)))
        if text == "":
            return {
                "g": [[("BOS", 1.0), ("EOS", 1.0), ("EOS", 1.0)]],
                "l": [[("BOS", 1.0), ("EOS", 1.0), ("EOS", 1.0)]],
            }
        if return_word_ids:
            return {
                "g": [[("BOS", 1.0, 0), (f"g::{text}", 1.0, 1), ("EOS", 1.0, 0)]],
                "l": [[("BOS", 1.0, 0), (f"l::{text}", 1.0, 1), ("EOS", 1.0, 0)]],
            }
        return {
            "g": [[("BOS", 1.0), (f"g::{text}", 1.0), ("EOS", 1.0)]],
            "l": [[("BOS", 1.0), (f"l::{text}", 1.0), ("EOS", 1.0)]],
        }

    def encode_from_tokens_scheduled(self, tokens, add_dict=_OMITTED_METADATA):
        self.encoded.append(tokens)
        g_text = tokens["g"][0][1][0]
        l_text = tokens["l"][0][1][0]
        return [[f"cond::{g_text}|{l_text}", _scheduled_metadata(f"pooled::{g_text}", add_dict)]]


class A1111PromptEncodingTests(unittest.TestCase):
    def test_scheduled_clip_fakes_reject_explicit_none_but_allow_omission(self) -> None:
        for clip in (_FakeClip(), _FakeSDXLClip()):
            with self.subTest(clip=type(clip).__name__):
                tokens = clip.tokenize("portrait")
                self.assertTrue(clip.encode_from_tokens_scheduled(tokens))
                self.assertTrue(clip.encode_from_tokens_scheduled(tokens, add_dict={}))
                with self.assertRaises(TypeError):
                    clip.encode_from_tokens_scheduled(tokens, add_dict=None)

    def test_merge_encode_metadata_always_returns_a_fresh_mapping(self) -> None:
        for base in (None, {}, {"width": 1024, "tags": ["base"]}):
            for extra in (None, {}, {"height": 768, "tags": ["extra"]}):
                with self.subTest(base=base, extra=extra):
                    original_base, original_extra = deepcopy(base), deepcopy(extra)
                    merged = _merge_encode_metadata(base, extra)
                    self.assertIsInstance(merged, dict)
                    self.assertIsNot(merged, base)
                    self.assertIsNot(merged, extra)
                    expected = {**(base or {}), **(extra or {})}
                    if base and extra and "tags" in base and "tags" in extra:
                        expected["tags"] = [*base["tags"], *extra["tags"]]
                    self.assertEqual(merged, expected)
                    merged["new_key"] = True
                    self.assertEqual(base, original_base)
                    self.assertEqual(extra, original_extra)

    def test_merge_encode_metadata_preserves_list_order_and_replacement_without_mutation(self) -> None:
        base = {"tags": ["base"], "width": 1024, "replace": ["old"]}
        extra = {"tags": ["first", "second"], "height": 768, "replace": "new"}
        original_base, original_extra = deepcopy(base), deepcopy(extra)
        merged = _merge_encode_metadata(base, extra)
        self.assertEqual(list(merged), ["tags", "width", "replace", "height"])
        self.assertEqual(merged, {"tags": ["base", "first", "second"], "width": 1024, "height": 768, "replace": "new"})
        merged["tags"].append("later")
        self.assertEqual(base, original_base)
        self.assertEqual(extra, original_extra)

    def test_sd15_empty_and_negative_text_use_the_host_mapping_contract_in_all_engines(self) -> None:
        node = nodes.RookieUIA1111CLIPTextEncode()
        for engine in ("parity", "text_only", "legacy"):
            for text in ("", "low quality, blurry"):
                with self.subTest(engine=engine, text=text):
                    conditioning, = node.encode(_FakeClip(), text, a1111_engine=engine)
                    self.assertEqual(conditioning, [[f"cond::{text}", {"pooled_output": f"pooled::{text}"}]])

    def test_sdxl_services_without_dimension_metadata_use_the_host_mapping_contract(self) -> None:
        for encoder in (encode_a1111_sdxl_prompt_conditioning, encode_a1111_sdxl_prompt_text_conditioning):
            for text_g, text_l in (("portrait", "low quality"), ("", "")):
                with self.subTest(encoder=encoder.__name__, text_g=text_g, text_l=text_l):
                    conditioning = encoder(
                        _FakeSDXLClip(), text_g=text_g, text_l=text_l,
                        tokenizer=nodes.RookieUIA1111CLIPTextEncodeSDXL._tokenize_sdxl_pair,
                    )
                    self.assertEqual(len(conditioning), 1)
                    self.assertEqual(set(conditioning[0][1]), {"pooled_output"})

    def test_sdxl_dimension_metadata_is_preserved_in_all_engines(self) -> None:
        dimensions = {"width": 1024, "height": 768, "crop_w": 16, "crop_h": 32, "target_width": 1280, "target_height": 960}
        for engine in ("parity", "text_only", "legacy"):
            with self.subTest(engine=engine):
                conditioning, = nodes.RookieUIA1111CLIPTextEncodeSDXL().encode(
                    _FakeSDXLClip(), **dimensions, text_g="portrait", text_l="low quality", a1111_engine=engine,
                )
                self.assertEqual({key: conditioning[0][1][key] for key in dimensions}, dimensions)

    def test_nodes_expose_parser_mode_matrix(self) -> None:
        expected_modes = ["A1111", "full", "comfy++", "fixed attention"]

        sd15_modes = nodes.RookieUIA1111CLIPTextEncode.INPUT_TYPES()["optional"]["parser"][0]
        sdxl_modes = nodes.RookieUIA1111CLIPTextEncodeSDXL.INPUT_TYPES()["optional"]["parser"][0]

        self.assertEqual(sd15_modes, expected_modes)
        self.assertEqual(sdxl_modes, expected_modes)

    def test_build_a1111_prompt_encoding_plan_freezes_multicond_reference_contract(self) -> None:
        plan = build_a1111_prompt_encoding_plan(
            "(hero:1.2) BREAK [day:night:0.5] AND villain:0.7",
            options=A1111PromptEncodingOptions(step_count=4),
        )

        self.assertTrue(plan.features["and_composition"])
        self.assertTrue(plan.features["break_chunks"])
        self.assertTrue(plan.features["prompt_scheduling"])
        self.assertEqual([branch.weight for branch in plan.branches], [1.0, 0.7])
        self.assertEqual(plan.branches[0].chunks[0].slices[0].text, "(hero:1.2)")
        self.assertEqual(
            [slice_item.text for slice_item in plan.branches[0].chunks[1].slices],
            ["day", "night"],
        )
        self.assertEqual(
            [(slice_item.start, slice_item.end) for slice_item in plan.branches[0].chunks[1].slices],
            [(0.0, 0.5), (0.5, 1.0)],
        )

    def test_sd15_node_compiles_schedule_and_branch_weight_inside_single_encoder_node(self) -> None:
        clip = _FakeClip()
        node = nodes.RookieUIA1111CLIPTextEncode()

        conditioning, = node.encode(clip, "[day:night:0.5] AND villain:0.7", steps=4)

        self.assertEqual(
            conditioning,
            [
                ["cond::day", {"pooled_output": "pooled::day", "start_percent": 0.0, "end_percent": 0.5}],
                ["cond::night", {"pooled_output": "pooled::night", "start_percent": 0.5, "end_percent": 1.0}],
                ["cond::villain", {"pooled_output": "pooled::villain", "strength": 0.7}],
            ],
        )

    def test_sd15_node_concats_break_chunks_inside_single_encoder_node(self) -> None:
        clip = _FakeClip()
        node = nodes.RookieUIA1111CLIPTextEncode()

        conditioning, = node.encode(clip, "hero BREAK background")

        self.assertEqual(len(conditioning), 1)
        self.assertEqual(conditioning[0][0], ("concat", "cond::hero", "cond::background"))

    def test_sdxl_node_compiles_dual_channel_schedule_inside_single_encoder_node(self) -> None:
        clip = _FakeSDXLClip()
        node = nodes.RookieUIA1111CLIPTextEncodeSDXL()

        conditioning, = node.encode(
            clip,
            1024,
            768,
            0,
            0,
            1024,
            768,
            "[day:night:0.5]",
            "low quality",
            steps=4,
        )

        self.assertEqual(len(conditioning), 2)
        self.assertEqual(conditioning[0][0], "cond::g::day|l::low quality")
        self.assertEqual(conditioning[0][1]["start_percent"], 0.0)
        self.assertEqual(conditioning[0][1]["width"], 1024)
        self.assertEqual(conditioning[1][0], "cond::g::night|l::low quality")
        self.assertEqual(conditioning[1][1]["end_percent"], 1.0)

    def test_sdxl_node_compiles_and_break_inside_single_encoder_node(self) -> None:
        clip = _FakeSDXLClip()
        node = nodes.RookieUIA1111CLIPTextEncodeSDXL()

        conditioning, = node.encode(
            clip,
            1024,
            768,
            0,
            0,
            1024,
            768,
            "hero BREAK background AND villain:0.5",
            "low quality",
            steps=4,
        )

        self.assertEqual(len(conditioning), 2)
        self.assertEqual(
            conditioning[0][0],
            ("concat", "cond::g::hero|l::low quality", "cond::g::background|l::low quality"),
        )
        self.assertEqual(conditioning[1][0], "cond::g::villain|l::low quality")
        self.assertEqual(conditioning[1][1]["strength"], 0.5)

    def test_node_can_fallback_to_legacy_tokenization_path(self) -> None:
        clip = _FakeClip()
        node = nodes.RookieUIA1111CLIPTextEncode()

        conditioning, = node.encode(clip, "[day:night:0.5]", a1111_engine="legacy")

        self.assertEqual(conditioning, [["cond::[day:night:0.5]", {"pooled_output": "pooled::[day:night:0.5]"}]])
        self.assertEqual(clip.tokenized[0], ("[day:night:0.5]", False))

    def test_text_only_mode_prevents_inner_schedule_compilation(self) -> None:
        clip = _FakeClip()
        node = nodes.RookieUIA1111CLIPTextEncode()

        conditioning, = node.encode(clip, "[day:night:0.5]", a1111_engine="text_only", steps=4)

        self.assertEqual(conditioning, [["cond::[day:night:0.5]", {"pooled_output": "pooled::[day:night:0.5]"}]])
        self.assertTrue(clip.tokenized)
        self.assertEqual({call[0] for call in clip.tokenized}, {"[day:night:0.5]"})

    def test_full_parser_normalizes_control_whitespace_before_encoding(self) -> None:
        clip = _FakeClip()
        node = nodes.RookieUIA1111CLIPTextEncode()

        conditioning, = node.encode(clip, "hero\r\n\tportrait", parser="full")

        self.assertEqual(conditioning, [["cond::hero portrait", {"pooled_output": "pooled::hero portrait"}]])
        self.assertEqual(clip.tokenized[0], ("hero portrait", False))

    def test_comfy_plus_parser_keeps_a1111_schedule_literal(self) -> None:
        clip = _FakeClip()
        node = nodes.RookieUIA1111CLIPTextEncode()

        conditioning, = node.encode(clip, "[day:night:0.5]", parser="comfy++", steps=4)

        self.assertEqual(conditioning, [["cond::[day:night:0.5]", {"pooled_output": "pooled::[day:night:0.5]"}]])
        self.assertEqual({call[0] for call in clip.tokenized}, {"[day:night:0.5]"})

    def test_fixed_attention_parser_preserves_literal_attention_markers(self) -> None:
        clip = _FakeClip()
        node = nodes.RookieUIA1111CLIPTextEncode()

        conditioning, = node.encode(clip, "portrait [soft light]", parser="fixed attention")

        self.assertEqual(conditioning, [["cond::portrait [soft light]", {"pooled_output": "pooled::portrait [soft light]"}]])
        self.assertEqual({call[0] for call in clip.tokenized}, {"portrait [soft light]"})

    def test_sdxl_comfy_plus_parser_keeps_dual_channel_schedule_literal(self) -> None:
        clip = _FakeSDXLClip()
        node = nodes.RookieUIA1111CLIPTextEncodeSDXL()

        conditioning, = node.encode(
            clip,
            1024,
            768,
            0,
            0,
            1024,
            768,
            "[day:night:0.5]",
            "low [quality:artifact:0.5]",
            parser="comfy++",
            steps=4,
        )

        self.assertEqual(conditioning[0][0], "cond::g::[day:night:0.5]|l::low [quality:artifact:0.5]")
        tokenized_texts = {call[0] for call in clip.tokenized}
        self.assertTrue({"[day:night:0.5]", "low [quality:artifact:0.5]"}.issubset(tokenized_texts))
        self.assertNotIn("day", tokenized_texts)
        self.assertNotIn("night", tokenized_texts)

    def test_sdxl_node_resolves_textual_inversion_per_clip_channel(self) -> None:
        clip = _FakeSDXLClip()
        node = nodes.RookieUIA1111CLIPTextEncodeSDXL()

        conditioning, = node.encode(
            clip,
            1024,
            768,
            0,
            0,
            1024,
            768,
            "local_style",
            "local_style",
            embedding_names="local_style.safetensors::vectors=2::channels=clip_l",
        )

        self.assertEqual(conditioning[0][0], "cond::g::local_style|l::embedding:local_style.safetensors")
        self.assertEqual(
            conditioning[0][1]["rookieui_textual_inversion_embeddings"],
            ["embedding:local_style.safetensors"],
        )
        self.assertEqual(
            conditioning[0][1]["rookieui_textual_inversion_channel_mismatch"],
            ["local_style"],
        )
        self.assertEqual(
            conditioning[0][1]["rookieui_textual_inversion_fixes"],
            [{"offset": 0, "name": "local_style.safetensors", "token": "embedding:local_style.safetensors", "vectors": 2}],
        )

    def test_mean_normalization_scales_weighted_conditioning_against_plain_reference(self) -> None:
        class _FakeClip:
            def __init__(self) -> None:
                self.encoded_texts: list[str] = []

            def tokenize(self, text, return_word_ids=False):
                return {"l": [[("BOS", 1.0), (text, 1.0), ("EOS", 1.0)]]}

            def encode_from_tokens_scheduled(self, tokens, add_dict=_OMITTED_METADATA):
                text = tokens["l"][0][1][0]
                self.encoded_texts.append(text)
                value = 20.0 if text == "hero (eyes:1.3)" else 5.0
                return [[value, _scheduled_metadata(f"pooled::{text}", add_dict)]]

        clip = _FakeClip()
        node = nodes.RookieUIA1111CLIPTextEncode()

        conditioning, = node.encode(clip, "hero (eyes:1.3)", mean_normalization=True)

        self.assertEqual(clip.encoded_texts, ["hero (eyes:1.3)", "hero eyes"])
        self.assertEqual(conditioning, [[5.0, {"pooled_output": "pooled::hero (eyes:1.3)"}]])

    def test_mean_normalization_can_be_disabled(self) -> None:
        class _FakeClip:
            def __init__(self) -> None:
                self.encoded_texts: list[str] = []

            def tokenize(self, text, return_word_ids=False):
                return {"l": [[("BOS", 1.0), (text, 1.0), ("EOS", 1.0)]]}

            def encode_from_tokens_scheduled(self, tokens, add_dict=_OMITTED_METADATA):
                text = tokens["l"][0][1][0]
                self.encoded_texts.append(text)
                value = 20.0 if text == "hero (eyes:1.3)" else 5.0
                return [[value, _scheduled_metadata(f"pooled::{text}", add_dict)]]

        clip = _FakeClip()
        node = nodes.RookieUIA1111CLIPTextEncode()

        conditioning, = node.encode(clip, "hero (eyes:1.3)", mean_normalization=False)

        self.assertEqual(clip.encoded_texts, ["hero (eyes:1.3)"])
        self.assertEqual(conditioning, [[20.0, {"pooled_output": "pooled::hero (eyes:1.3)"}]])

    def test_old_emphasis_encodes_unweighted_tokens_then_applies_multipliers(self) -> None:
        class _WeightedClip:
            def __init__(self) -> None:
                self.encoded_token_weights: list[list[float]] = []

            def tokenize(self, text, return_word_ids=False):
                if text != "hero (eyes:1.3)":
                    return {"l": [[("BOS", 1.0), (text, 1.0), ("EOS", 1.0)]]}
                if return_word_ids:
                    return {
                        "l": [[("BOS", 1.0, 0), ("hero", 1.0, 1), ("eyes", 1.3, 2), ("EOS", 1.0, 0)]]
                    }
                return {"l": [[("BOS", 1.0), ("hero", 1.0), ("eyes", 1.3), ("EOS", 1.0)]]}

            def encode_from_tokens_scheduled(self, tokens, add_dict=_OMITTED_METADATA):
                self.encoded_token_weights.append([float(entry[1]) for entry in tokens["l"][0]])
                return [[10.0, _scheduled_metadata("pooled::old", add_dict)]]

        clip = _WeightedClip()
        node = nodes.RookieUIA1111CLIPTextEncode()

        conditioning, = node.encode(
            clip,
            "hero (eyes:1.3)",
            use_old_emphasis_implementation=True,
            mean_normalization=False,
        )

        self.assertEqual(clip.encoded_token_weights, [[1.0, 1.0, 1.0, 1.0]])
        self.assertAlmostEqual(conditioning[0][0], 10.75)
        self.assertEqual(conditioning[0][1]["rookieui_emphasis_implementation"], "old")
        self.assertAlmostEqual(conditioning[0][1]["rookieui_old_emphasis_weight_mean"], 1.075)

    def test_node_resolves_textual_inversion_aliases_from_embedding_names(self) -> None:
        clip = _FakeClip()
        node = nodes.RookieUIA1111CLIPTextEncode()

        conditioning, = node.encode(
            clip,
            "portrait badhandv4 embedding:missing_style",
            embedding_names="badhandv4.pt::vectors=2",
        )

        self.assertEqual(
            conditioning[0][0],
            "cond::portrait embedding:badhandv4.pt missing_style",
        )
        self.assertEqual(
            conditioning[0][1]["rookieui_textual_inversion_embeddings"],
            ["embedding:badhandv4.pt"],
        )
        self.assertEqual(
            conditioning[0][1]["rookieui_textual_inversion_missing"],
            ["embedding:missing_style"],
        )
        self.assertEqual(
            conditioning[0][1]["rookieui_textual_inversion_fixes"],
            [{"offset": 1, "name": "badhandv4.pt", "token": "embedding:badhandv4.pt", "vectors": 2}],
        )


if __name__ == "__main__":
    unittest.main()
