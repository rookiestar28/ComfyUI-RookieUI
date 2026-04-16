from __future__ import annotations

import unittest

from rookieui.services import prompt_token_rebatch


class PromptTokenRebatchTests(unittest.TestCase):
    def test_rebatch_channel_token_weights_moves_recent_comma_tail_to_next_batch(self) -> None:
        channel_batches = [
            [
                (100, 1.0, 0),
                (1, 1.0, 1),
                (2, 1.0, 2),
                (99, 1.0, 3),
                (3, 1.0, 4),
                (4, 1.0, 5),
                (101, 1.0, 0),
            ],
            [
                (100, 1.0, 0),
                (5, 1.0, 6),
                (101, 1.0, 0),
                (101, 1.0, 0),
                (101, 1.0, 0),
                (101, 1.0, 0),
                (101, 1.0, 0),
            ],
        ]

        rebatched = prompt_token_rebatch.rebatch_channel_token_weights(
            channel_batches,
            max_length=7,
            start_token=100,
            end_token=101,
            pad_token=101,
            comma_token=99,
            max_word_length=8,
        )

        self.assertEqual(
            rebatched,
            [
                [(100, 1.0), (1, 1.0), (2, 1.0), (99, 1.0), (101, 1.0), (101, 1.0), (101, 1.0)],
                [(100, 1.0), (3, 1.0), (4, 1.0), (5, 1.0), (101, 1.0), (101, 1.0), (101, 1.0)],
            ],
        )

    def test_rebatch_channel_token_weights_preserves_embedding_group_boundary(self) -> None:
        embed_a = object()
        embed_b = object()
        channel_batches = [
            [
                (100, 1.0, 0),
                (1, 1.0, 1),
                (2, 1.0, 2),
                (3, 1.0, 3),
                (4, 1.0, 4),
                (101, 1.0, 0),
                (101, 1.0, 0),
            ],
            [
                (100, 1.0, 0),
                (embed_a, 1.2, 5),
                (embed_b, 1.2, 5),
                (101, 1.0, 0),
                (101, 1.0, 0),
                (101, 1.0, 0),
                (101, 1.0, 0),
            ],
        ]

        rebatched = prompt_token_rebatch.rebatch_channel_token_weights(
            channel_batches,
            max_length=7,
            start_token=100,
            end_token=101,
            pad_token=101,
            comma_token=None,
            max_word_length=8,
        )

        self.assertEqual(rebatched[0], [(100, 1.0), (1, 1.0), (2, 1.0), (3, 1.0), (4, 1.0), (101, 1.0), (101, 1.0)])
        self.assertEqual(rebatched[1][0], (100, 1.0))
        self.assertIs(rebatched[1][1][0], embed_a)
        self.assertIs(rebatched[1][2][0], embed_b)
        self.assertEqual(rebatched[1][1][1], 1.2)
        self.assertEqual(rebatched[1][2][1], 1.2)

    def test_tokenize_channel_with_rookieui_rebatch_falls_back_without_word_ids(self) -> None:
        class _FakeClip:
            def tokenize(self, text):
                return {"l": [[(100, 1.0), (text, 1.0), (101, 1.0)]]}

        clip = _FakeClip()
        tokens = prompt_token_rebatch.tokenize_channel_with_rookieui_rebatch(clip, "hero", channel_key="l")

        self.assertEqual(tokens, [[(100, 1.0), ("hero", 1.0), (101, 1.0)]])

    def test_tokenize_with_rookieui_rebatch_handles_single_channel_dict_payload(self) -> None:
        class _FakeTokenizerChannel:
            max_length = 7
            start_token = 100
            end_token = 101
            pad_token = 101
            max_word_length = 8
            comma_token = 99

        class _FakeTokenizer:
            clip_name = "l"

            def __init__(self) -> None:
                self.clip_l = _FakeTokenizerChannel()

        class _FakeClip:
            def __init__(self) -> None:
                self.tokenizer = _FakeTokenizer()

            def tokenize(self, text, return_word_ids=False):
                if return_word_ids:
                    return {
                        "l": [
                            [(100, 1.0, 0), (1, 1.0, 1), (99, 1.0, 2), (2, 1.0, 3), (3, 1.0, 4), (4, 1.0, 5), (101, 1.0, 0)],
                            [(100, 1.0, 0), (5, 1.0, 6), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0)],
                        ]
                    }
                return {
                    "l": [
                        [(100, 1.0), (1, 1.0), (99, 1.0), (2, 1.0), (3, 1.0), (4, 1.0), (101, 1.0)],
                        [(100, 1.0), (5, 1.0), (101, 1.0), (101, 1.0), (101, 1.0), (101, 1.0), (101, 1.0)],
                    ]
                }

        tokens = prompt_token_rebatch.tokenize_with_rookieui_rebatch(_FakeClip(), "hero, detail shot")

        self.assertEqual(
            tokens,
            {
                "l": [
                    [(100, 1.0), (1, 1.0), (99, 1.0), (101, 1.0), (101, 1.0), (101, 1.0), (101, 1.0)],
                    [(100, 1.0), (2, 1.0), (3, 1.0), (4, 1.0), (5, 1.0), (101, 1.0), (101, 1.0)],
                ]
            },
        )


if __name__ == "__main__":
    unittest.main()
