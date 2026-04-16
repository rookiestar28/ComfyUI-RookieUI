from __future__ import annotations

from dataclasses import dataclass
import unittest

from rookieui.services.prompt_token_rebatch import rebatch_channel_token_weights


@dataclass(frozen=True)
class _ReferenceTokenChunkCase:
    case_id: str
    channel_batches: list[list[tuple[object, float, int]]]
    max_length: int
    start_token: int
    end_token: int
    pad_token: int
    comma_token: int | None
    max_word_length: int
    expected_batches: list[list[tuple[object, float]]]


_REFERENCE_CASES = (
    _ReferenceTokenChunkCase(
        case_id="recent_comma_backtrack",
        channel_batches=[
            [(100, 1.0, 0), (1, 1.0, 1), (2, 1.0, 2), (99, 1.0, 3), (3, 1.0, 4), (4, 1.0, 5), (101, 1.0, 0)],
            [(100, 1.0, 0), (5, 1.0, 6), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0)],
        ],
        max_length=7,
        start_token=100,
        end_token=101,
        pad_token=101,
        comma_token=99,
        max_word_length=8,
        expected_batches=[
            [(100, 1.0), (1, 1.0), (2, 1.0), (99, 1.0), (101, 1.0), (101, 1.0), (101, 1.0)],
            [(100, 1.0), (3, 1.0), (4, 1.0), (5, 1.0), (101, 1.0), (101, 1.0), (101, 1.0)],
        ],
    ),
    _ReferenceTokenChunkCase(
        case_id="comma_too_far_no_backtrack",
        channel_batches=[
            [(100, 1.0, 0), *[(token, 1.0, token) for token in [99, *range(1, 25)]], (101, 1.0, 0)],
            [(100, 1.0, 0), (25, 1.0, 25), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0)],
        ],
        max_length=27,
        start_token=100,
        end_token=101,
        pad_token=101,
        comma_token=99,
        max_word_length=8,
        expected_batches=[
            [(100, 1.0), *[(token, 1.0) for token in [99, *range(1, 25)]], (101, 1.0)],
            [(100, 1.0), (25, 1.0), *[(101, 1.0)] * 25],
        ],
    ),
    _ReferenceTokenChunkCase(
        case_id="embedding_group_preserved",
        channel_batches=[
            [(100, 1.0, 0), (1, 1.0, 1), (2, 1.0, 2), (3, 1.0, 3), (4, 1.0, 4), (101, 1.0, 0), (101, 1.0, 0)],
            [(100, 1.0, 0), ("EMB_A", 1.2, 5), ("EMB_B", 1.2, 5), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0), (101, 1.0, 0)],
        ],
        max_length=7,
        start_token=100,
        end_token=101,
        pad_token=101,
        comma_token=None,
        max_word_length=8,
        expected_batches=[
            [(100, 1.0), (1, 1.0), (2, 1.0), (3, 1.0), (4, 1.0), (101, 1.0), (101, 1.0)],
            [(100, 1.0), ("EMB_A", 1.2), ("EMB_B", 1.2), (101, 1.0), (101, 1.0), (101, 1.0), (101, 1.0)],
        ],
    ),
    _ReferenceTokenChunkCase(
        case_id="large_group_continues_across_chunks",
        channel_batches=[
            [(100, 1.0, 0), *[(token, 1.0, 1) for token in range(1, 6)], (101, 1.0, 0)],
            [(100, 1.0, 0), *[(token, 1.0, 1) for token in range(6, 11)], (101, 1.0, 0)],
        ],
        max_length=7,
        start_token=100,
        end_token=101,
        pad_token=101,
        comma_token=None,
        max_word_length=8,
        expected_batches=[
            [(100, 1.0), (1, 1.0), (2, 1.0), (3, 1.0), (4, 1.0), (5, 1.0), (101, 1.0)],
            [(100, 1.0), (6, 1.0), (7, 1.0), (8, 1.0), (9, 1.0), (10, 1.0), (101, 1.0)],
        ],
    ),
)


class PromptTokenRebatchReferenceParityTests(unittest.TestCase):
    def test_reference_backed_token_chunk_cases_match_expected_batches(self) -> None:
        for case in _REFERENCE_CASES:
            with self.subTest(case=case.case_id):
                rebatched = rebatch_channel_token_weights(
                    case.channel_batches,
                    max_length=case.max_length,
                    start_token=case.start_token,
                    end_token=case.end_token,
                    pad_token=case.pad_token,
                    comma_token=case.comma_token,
                    max_word_length=case.max_word_length,
                )
                self.assertEqual(rebatched, case.expected_batches)


if __name__ == "__main__":
    unittest.main()
