from __future__ import annotations

from typing import Any

from rookieui.services.prompt_dsl import (
    PROMPT_WARNING_AND_DETECTED,
    PROMPT_WARNING_ATTENTION_DETECTED,
    PROMPT_WARNING_BREAK_DETECTED,
    PROMPT_WARNING_EXTRA_NETWORK_UNSUPPORTED_REMOVED,
    PROMPT_WARNING_GUARD_AND_BRANCH_LIMIT,
    PROMPT_WARNING_GUARD_BREAK_CHUNK_LIMIT,
    PROMPT_WARNING_GUARD_SCHEDULE_SLICE_LIMIT,
    PROMPT_WARNING_LEGACY_FALLBACK_ENABLED,
    PROMPT_WARNING_SCHEDULE_DETECTED,
    PROMPT_WARNING_SCHEDULE_INVALID_THRESHOLD,
)

_EXACT_PROFILE_IDS = ("sd15", "sdxl", "pony", "illustrious", "noob")
_APPROXIMATE_PROFILE_IDS = ("flux", "qwen_image", "klein", "lumina", "zit", "wan", "anima")

_PROMPT_CAPABILITIES = (
    {
        "id": "and_composition",
        "title": "AND Composition",
        "a1111_semantics": "Composable multi-condition prompt branches via AND and optional branch weight suffix.",
        "rookieui_contract": "Default SD-family routes execute A1111-native branch parsing through RookieUI parity text-encode nodes. Legacy env rollback and secondary-family non-parity lanes explicitly downgrade from this exact path.",
        "status": "exact",
        "translation": "rookieui_a1111_text_encode_multi_cond",
        "reference": "reference/stable-diffusion-webui/modules/prompt_parser.py",
    },
    {
        "id": "break_chunks",
        "title": "BREAK Chunking",
        "a1111_semantics": "BREAK token splits prompt chunks for chunked conditioning behavior.",
        "rookieui_contract": "Default SD-family routes preserve tokenizer-side BREAK chunk boundaries inside RookieUI parity text-encode nodes. The legacy graph compiler remains an explicit fallback path only.",
        "status": "exact",
        "translation": "rookieui_a1111_text_encode_chunk_boundary",
        "reference": "reference/stable-diffusion-webui/modules/prompt_parser.py",
    },
    {
        "id": "prompt_scheduling",
        "title": "Prompt Scheduling",
        "a1111_semantics": "Schedule syntax [from:to:at] swaps text by step-progress.",
        "rookieui_contract": "Default SD-family routes build A1111-native schedule segments at the parity text-encode boundary. Graph timestep-range compilation is retained only for explicit fallback lanes.",
        "status": "exact",
        "translation": "rookieui_a1111_text_encode_schedule_segments",
        "reference": "reference/stable-diffusion-webui/modules/prompt_parser.py",
    },
    {
        "id": "attention_weighting",
        "title": "Attention Weighting",
        "a1111_semantics": "Parenthesis/bracket prompt attention and explicit (text:weight) weighting.",
        "rookieui_contract": "Default SD-family routes apply A1111-native attention parsing inside RookieUI parity text-encode nodes. Legacy rollback keeps only the older graph-compiler approximation path.",
        "status": "exact",
        "translation": "rookieui_a1111_text_encode_attention",
        "reference": "reference/stable-diffusion-webui/modules/prompt_parser.py",
    },
    {
        "id": "extra_network_lora",
        "title": "Extra Network (LoRA/LyCORIS)",
        "a1111_semantics": "Inline extra-network token <lora:...> / <lyco:...> merges into model graph.",
        "rookieui_contract": "Deterministic extraction + merged activation chain through LoraLoader nodes.",
        "status": "exact",
        "translation": "lora_loader_chain",
        "reference": "reference/stable-diffusion-webui/modules/extra_networks.py",
    },
    {
        "id": "extra_network_other",
        "title": "Extra Network (Unsupported Families)",
        "a1111_semantics": "Non-LoRA extra network token families in prompt body.",
        "rookieui_contract": "Unsupported families are stripped from the prompt payload with explicit warning diagnostics; RookieUI makes no exact execution claim for them.",
        "status": "unsupported",
        "translation": "warning_and_strip",
        "reference": "reference/stable-diffusion-webui/modules/extra_networks.py",
    },
)


def build_prompt_capability_matrix_payload() -> dict[str, Any]:
    return {
        "contract_version": "f100-20260414",
        "contract_scope": "sd-family-default-exact-with-explicit-fallbacks",
        "rollout": {
            "default_mode": "a1111_parity_nodes_exact",
            "legacy_fallback_env": "ROOKIEUI_PROMPT_DSL_LEGACY",
            "legacy_fallback_mode": "graph_compiler_approximate",
            "warning_code_contract": "stable",
            "exact_parity_cutover": "active_for_sd_family",
            "exact_profile_ids": list(_EXACT_PROFILE_IDS),
            "approximate_profile_ids": list(_APPROXIMATE_PROFILE_IDS),
        },
        "compiler_constraints": {
            "conditioning_nodes": [
                "RookieUIA1111TextEncode",
                "RookieUIA1111TextEncodeSDXL",
                "ConditioningCombine",
                "ConditioningConcat",
                "ConditioningSetTimestepRange",
            ],
            "execution_backend": "RookieUI A1111 parity text-encode nodes on default SD-family routes; legacy graph translation remains an explicit fallback path.",
        },
        "warning_codes": {
            "semantic_detection": [
                PROMPT_WARNING_AND_DETECTED,
                PROMPT_WARNING_BREAK_DETECTED,
                PROMPT_WARNING_SCHEDULE_DETECTED,
                PROMPT_WARNING_ATTENTION_DETECTED,
            ],
            "fallback": [PROMPT_WARNING_LEGACY_FALLBACK_ENABLED],
            "guardrails": [
                PROMPT_WARNING_GUARD_AND_BRANCH_LIMIT,
                PROMPT_WARNING_GUARD_BREAK_CHUNK_LIMIT,
                PROMPT_WARNING_GUARD_SCHEDULE_SLICE_LIMIT,
                PROMPT_WARNING_SCHEDULE_INVALID_THRESHOLD,
            ],
            "unsupported": [PROMPT_WARNING_EXTRA_NETWORK_UNSUPPORTED_REMOVED],
        },
        "capabilities": [dict(entry) for entry in _PROMPT_CAPABILITIES],
    }
