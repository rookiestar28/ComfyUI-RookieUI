from __future__ import annotations

import unittest

from rookieui.security.request_guard import (
    MAX_INFOTEXT_LENGTH,
    MAX_PROMPT_LENGTH,
    MAX_SELECTOR_LENGTH,
    RANDOM_SEED_SENTINEL,
    build_host_selector_key,
    normalize_client_id,
    normalize_host_selector,
    normalize_infotext,
    normalize_prompt_text,
    resolve_execution_seed,
    resolve_inventory_selector,
    validate_seed_range,
)


class RequestGuardTests(unittest.TestCase):
    def test_normalize_prompt_text_preserves_multiline_semantics(self) -> None:
        normalized = normalize_prompt_text("  line one\r\nline two\x00  ", "prompt", required=True)

        self.assertEqual(normalized, "line one\nline two")

    def test_normalize_prompt_text_rejects_oversized_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "prompt must be at most"):
            normalize_prompt_text("x" * (MAX_PROMPT_LENGTH + 1), "prompt", required=True)

    def test_normalize_host_selector_accepts_relative_subfolder(self) -> None:
        selector = normalize_host_selector(
            "anime\\sdxl\\pony.safetensors",
            "checkpoint_name",
            default_value="__host_default__",
        )

        self.assertEqual(selector, "anime/sdxl/pony.safetensors")

    def test_resolve_inventory_selector_preserves_exact_host_entry(self) -> None:
        selector = resolve_inventory_selector(
            "SD15\\beautifulRealistic_v40.safetensors",
            "checkpoint_name",
            default_value="__host_default__",
            inventory_selectors=["SD15\\beautifulRealistic_v40.safetensors"],
            strict_match=True,
        )

        self.assertEqual(selector, "SD15\\beautifulRealistic_v40.safetensors")

    def test_resolve_inventory_selector_maps_slash_variant_back_to_host_entry(self) -> None:
        selector = resolve_inventory_selector(
            "SD15/beautifulRealistic_v40.safetensors",
            "checkpoint_name",
            default_value="__host_default__",
            inventory_selectors=["SD15\\beautifulRealistic_v40.safetensors"],
            strict_match=True,
        )

        self.assertEqual(selector, "SD15\\beautifulRealistic_v40.safetensors")
        self.assertEqual(build_host_selector_key(selector), "SD15/beautifulRealistic_v40.safetensors")

    def test_normalize_host_selector_rejects_traversal_and_absolute_paths(self) -> None:
        with self.assertRaisesRegex(ValueError, "logical host selector"):
            normalize_host_selector("../unsafe.ckpt", "checkpoint_name", default_value="__host_default__")

        with self.assertRaisesRegex(ValueError, "logical host selector"):
            normalize_host_selector("C:\\models\\unsafe.ckpt", "checkpoint_name", default_value="__host_default__")

    def test_normalize_host_selector_rejects_oversized_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "checkpoint_name must be at most"):
            normalize_host_selector(
                "a" * (MAX_SELECTOR_LENGTH + 1),
                "checkpoint_name",
                default_value="__host_default__",
            )

    def test_normalize_client_id_rejects_whitespace(self) -> None:
        with self.assertRaisesRegex(ValueError, "client_id must not contain whitespace"):
            normalize_client_id("browser session")

    def test_normalize_infotext_rejects_oversized_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "infotext must be at most"):
            normalize_infotext("x" * (MAX_INFOTEXT_LENGTH + 1))

    def test_validate_seed_range_rejects_unbounded_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "seed must be -1 or between 0 and"):
            validate_seed_range(2**80)

    def test_validate_seed_range_rejects_negative_values_other_than_random_sentinel(self) -> None:
        with self.assertRaisesRegex(ValueError, "seed must be -1 or between 0 and"):
            validate_seed_range(-2)

    def test_resolve_execution_seed_randomizes_a1111_sentinel(self) -> None:
        resolved = resolve_execution_seed(RANDOM_SEED_SENTINEL)

        self.assertGreaterEqual(resolved, 0)
