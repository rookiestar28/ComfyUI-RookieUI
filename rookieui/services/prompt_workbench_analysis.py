from __future__ import annotations

from typing import Any

from rookieui.contracts.prompt_dsl import PromptSemanticPlan
from rookieui.contracts.prompt_workbench import build_prompt_workbench_contract_meta
from rookieui.services.model_inventory import discover_model_inventory
from rookieui.services.prompt_dsl import preprocess_prompt_bundle

_MAX_ANALYZE_TEXT_LENGTH = 16000


def _normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:_MAX_ANALYZE_TEXT_LENGTH]


def _normalize_step_count(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return max(1, min(value, 200))
    return 28


def _count_schedule_slices(semantic: PromptSemanticPlan) -> int:
    count = 0
    for branch in semantic.branches:
        for chunk in branch.chunks:
            count += len(chunk.slices)
    return count


def _build_syntax_metrics(
    *,
    text: str,
    semantics: PromptSemanticPlan,
    lora_count: int,
) -> dict[str, Any]:
    comma_segments = [segment for segment in text.split(",") if segment.strip()]
    return {
        "mode": "syntax_inventory_estimate",
        "exact_tokenizer_available": False,
        "character_count": len(text),
        "comma_segment_count": len(comma_segments),
        "branch_count": max(1, len(semantics.branches)) if text else 0,
        "schedule_slice_count": _count_schedule_slices(semantics),
        "attention_marker_count": len(semantics.attention),
        "embedding_count": len(semantics.embeddings),
        "lora_activation_count": lora_count,
    }


def analyze_prompt_workbench_payload(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Prompt-workbench analyze payload must be an object.")

    prompt = _normalize_text(payload.get("prompt"))
    negative_prompt = _normalize_text(payload.get("negative_prompt"))
    if not prompt and not negative_prompt:
        raise ValueError("Prompt-workbench analyze requests require prompt or negative_prompt.")

    inventory = discover_model_inventory()
    preprocess_result = preprocess_prompt_bundle(
        prompt,
        negative_prompt,
        step_count=_normalize_step_count(payload.get("steps")),
        inventory_loras=inventory.loras,
        inventory_embeddings=inventory.embeddings,
        strict_match=False,
    )
    prompt_metrics = _build_syntax_metrics(
        text=preprocess_result.cleaned_prompt,
        semantics=preprocess_result.prompt_semantics,
        lora_count=len(preprocess_result.lora_activations),
    )
    negative_metrics = _build_syntax_metrics(
        text=preprocess_result.cleaned_negative_prompt,
        semantics=preprocess_result.negative_prompt_semantics,
        lora_count=0,
    )
    result_payload = preprocess_result.to_payload()
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_analyze"),
        "analysis_mode": "syntax_inventory",
        "prompt": {
            "raw": prompt,
            "cleaned": preprocess_result.cleaned_prompt,
            "semantics": result_payload["prompt_semantics"],
            "metrics": prompt_metrics,
        },
        "negative_prompt": {
            "raw": negative_prompt,
            "cleaned": preprocess_result.cleaned_negative_prompt,
            "semantics": result_payload["negative_prompt_semantics"],
            "metrics": negative_metrics,
        },
        "lora_activations": result_payload["lora_activations"],
        "warnings": result_payload["prompt_warnings"],
        "warning_codes": result_payload["warning_codes"],
        "inventory_snapshot": {
            "embedding_count": len(inventory.embeddings),
            "lora_count": len(inventory.loras),
        },
    }
