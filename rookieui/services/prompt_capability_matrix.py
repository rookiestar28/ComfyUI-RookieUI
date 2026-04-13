from __future__ import annotations

from typing import Any

_PROMPT_CAPABILITIES = (
    {
        "id": "and_composition",
        "title": "AND Composition",
        "a1111_semantics": "Composable multi-condition prompt branches via AND and optional branch weight suffix.",
        "rookieui_contract": "Currently shipped through graph-level multi-branch conditioning composition; exact A1111-native parity is pending parity-node cutover.",
        "status": "approximate",
        "translation": "graph_conditioning_combine",
        "reference": "reference/stable-diffusion-webui/modules/prompt_parser.py",
    },
    {
        "id": "break_chunks",
        "title": "BREAK Chunking",
        "a1111_semantics": "BREAK token splits prompt chunks for chunked conditioning behavior.",
        "rookieui_contract": "Currently approximated via graph-level chunk composition; exact A1111 tokenizer-side BREAK behavior is pending parity-node cutover.",
        "status": "approximate",
        "translation": "graph_break_chunk_approximation",
        "reference": "reference/stable-diffusion-webui/modules/prompt_parser.py",
    },
    {
        "id": "prompt_scheduling",
        "title": "Prompt Scheduling",
        "a1111_semantics": "Schedule syntax [from:to:at] swaps text by step-progress.",
        "rookieui_contract": "Currently approximated via schedule slices plus timestep-ranged conditioning; exact A1111-native prompt scheduling is pending parity-node cutover.",
        "status": "approximate",
        "translation": "graph_timestep_range_approximation",
        "reference": "reference/stable-diffusion-webui/modules/prompt_parser.py",
    },
    {
        "id": "attention_weighting",
        "title": "Attention Weighting",
        "a1111_semantics": "Parenthesis/bracket prompt attention and explicit (text:weight) weighting.",
        "rookieui_contract": "Syntax is preserved and diagnostics are available, but exact A1111-native token/emphasis behavior is pending parity-node cutover.",
        "status": "approximate",
        "translation": "encoder_passthrough_plus_diagnostics",
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
        "rookieui_contract": "Removed from prompt payload with explicit warning diagnostics.",
        "status": "guarded",
        "translation": "warning_and_strip",
        "reference": "reference/stable-diffusion-webui/modules/extra_networks.py",
    },
)


def build_prompt_capability_matrix_payload() -> dict[str, Any]:
    return {
        "contract_version": "r106-20260413",
        "contract_scope": "sd-family-truthful-precutover",
        "rollout": {
            "default_mode": "semantic_v2_approximate",
            "legacy_fallback_env": "ROOKIEUI_PROMPT_DSL_LEGACY",
            "warning_code_contract": "stable",
            "exact_parity_cutover": "planned",
        },
        "compiler_constraints": {
            "conditioning_nodes": [
                "ConditioningCombine",
                "ConditioningConcat",
                "ConditioningSetTimestepRange",
            ],
            "execution_backend": "ComfyUI graph translation (pre-cutover approximation)",
        },
        "capabilities": [dict(entry) for entry in _PROMPT_CAPABILITIES],
    }
