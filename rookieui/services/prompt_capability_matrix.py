from __future__ import annotations

from typing import Any

_PROMPT_CAPABILITIES = (
    {
        "id": "and_composition",
        "title": "AND Composition",
        "a1111_semantics": "Composable multi-condition prompt branches via AND and optional branch weight suffix.",
        "rookieui_contract": "Parsed and compiled to multi-branch conditioning composition for SD-family execution lanes.",
        "status": "supported",
        "translation": "conditioning_combine",
        "reference": "a1111_prompt_parser",
    },
    {
        "id": "break_chunks",
        "title": "BREAK Chunking",
        "a1111_semantics": "BREAK token splits prompt chunks for chunked conditioning behavior.",
        "rookieui_contract": "Parsed into prompt chunks and compiled with explicit chunk-composition nodes.",
        "status": "supported",
        "translation": "conditioning_concat",
        "reference": "a1111_prompt_parser",
    },
    {
        "id": "prompt_scheduling",
        "title": "Prompt Scheduling",
        "a1111_semantics": "Schedule syntax [from:to:at] swaps text by step-progress.",
        "rookieui_contract": "Parsed into schedule slices and compiled with timestep range conditioning.",
        "status": "supported",
        "translation": "conditioning_set_timestep_range",
        "reference": "a1111_prompt_parser",
    },
    {
        "id": "alternate_prompt_scheduling",
        "title": "Alternate Prompt Scheduling",
        "a1111_semantics": "Alternate syntax [a|b] cycles prompt text across sampling steps.",
        "rookieui_contract": "Parsed into per-step alternate slices and compiled with timestep range conditioning on SD-family prompt paths.",
        "status": "supported",
        "translation": "conditioning_set_timestep_range_cycle",
        "reference": "a1111_prompt_parser",
    },
    {
        "id": "attention_weighting",
        "title": "Attention Weighting",
        "a1111_semantics": "Parenthesis/bracket prompt attention and explicit (text:weight) weighting.",
        "rookieui_contract": "Structured detection with SD-family-first weighted text preservation.",
        "status": "supported",
        "translation": "weighted_text_tokens",
        "reference": "a1111_prompt_parser",
    },
    {
        "id": "embeddings_textual_inversion",
        "title": "Embeddings / Textual Inversion",
        "a1111_semantics": "Prompt-native textual inversion / embedding references resolved at tokenizer or encode time.",
        "rookieui_contract": "Inventory-aware prompt detection, canonical host token normalization, and missing-reference diagnostics on the shipped SD-family prompt path.",
        "status": "supported",
        "translation": "prompt_native_embedding_tokens",
        "reference": "a1111_textual_inversion",
    },
    {
        "id": "extra_network_lora",
        "title": "Extra Network (LoRA/LyCORIS)",
        "a1111_semantics": "Inline extra-network token <lora:...> / <lyco:...> merges into model graph.",
        "rookieui_contract": "Deterministic extraction + merged activation chain through LoraLoader nodes.",
        "status": "supported",
        "translation": "lora_loader_chain",
        "reference": "a1111_extra_networks",
    },
    {
        "id": "extra_network_other",
        "title": "Extra Network (Unsupported Families)",
        "a1111_semantics": "Non-LoRA extra network token families in prompt body.",
        "rookieui_contract": "Removed from prompt payload with explicit warning diagnostics.",
        "status": "guarded",
        "translation": "warning_and_strip",
        "reference": "a1111_extra_networks",
    },
)


def build_prompt_capability_matrix_payload() -> dict[str, Any]:
    return {
        "contract_version": "f105-20260416",
        "contract_scope": "sd-family-first",
        "rollout": {
            "default_mode": "semantic_v2",
            "legacy_fallback_env": "ROOKIEUI_PROMPT_DSL_LEGACY",
            "warning_code_contract": "stable",
        },
        "compiler_constraints": {
            "conditioning_nodes": [
                "ConditioningCombine",
                "ConditioningConcat",
                "ConditioningSetTimestepRange",
            ],
            "execution_backend": "ComfyUI graph translation",
        },
        "capabilities": [dict(entry) for entry in _PROMPT_CAPABILITIES],
    }
