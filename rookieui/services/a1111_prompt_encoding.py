from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable

try:
    import torch
except Exception:  # pragma: no cover - import guard for lean CI/route registration environments
    torch = None

from rookieui.contracts.prompt_dsl import (
    PromptBranchSemantic,
    PromptChunkSemantic,
    PromptScheduleSlice,
    PromptSemanticPlan,
)
from rookieui.services.prompt_dsl import (
    _build_prompt_semantic_plan,
    normalize_prompt_attention_for_weighted_encode,
)


@dataclass(frozen=True)
class A1111PromptEncodingOptions:
    step_count: int = 10
    mean_normalization: bool = True
    use_old_emphasis_implementation: bool = False


def build_a1111_prompt_encoding_plan(
    prompt_text: str,
    *,
    options: A1111PromptEncodingOptions | None = None,
) -> PromptSemanticPlan:
    resolved_options = options or A1111PromptEncodingOptions()
    plan, _warnings = _build_prompt_semantic_plan(
        str(prompt_text or ""),
        step_count=max(1, int(resolved_options.step_count or 10)),
    )
    return plan


def prompt_requires_single_node_compiler(plan: PromptSemanticPlan) -> bool:
    return any(
        bool(plan.features.get(feature_name))
        for feature_name in (
            "and_composition",
            "break_chunks",
            "prompt_scheduling",
            "alternate_prompt_scheduling",
        )
    )


def _clone_metadata(metadata: Any) -> dict[str, Any]:
    return metadata.copy() if isinstance(metadata, dict) else {}


def _set_conditioning_values(conditioning: list[Any], values: dict[str, Any]) -> list[Any]:
    updated: list[Any] = []
    for item in conditioning:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            updated.append(item)
            continue
        metadata = _clone_metadata(item[1])
        metadata.update(values)
        updated.append([item[0], metadata])
    return updated


def _combine_conditioning(conditioning_items: list[list[Any]]) -> list[Any]:
    combined: list[Any] = []
    for conditioning in conditioning_items:
        combined.extend(conditioning)
    return combined


def _concat_values(conditioning_to: Any, conditioning_from: Any) -> Any:
    if torch is not None and hasattr(conditioning_to, "shape") and hasattr(conditioning_from, "shape"):
        return torch.cat((conditioning_to, conditioning_from), 1)
    return ("concat", conditioning_to, conditioning_from)


def _concat_conditioning(conditioning_to: list[Any], conditioning_from: list[Any]) -> list[Any]:
    if not conditioning_to:
        return list(conditioning_from)
    if not conditioning_from:
        return list(conditioning_to)
    from_value = conditioning_from[0][0]
    out: list[Any] = []
    for item in conditioning_to:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            out.append(item)
            continue
        out.append([_concat_values(item[0], from_value), _clone_metadata(item[1])])
    return out


def _normalize_slice_text(text: str) -> str:
    return normalize_prompt_attention_for_weighted_encode(str(text or ""))


def strip_a1111_attention_weights(text: str) -> str:
    normalized = str(text or "")
    previous = None
    while previous != normalized:
        previous = normalized
        normalized = re.sub(r"\(([^():]+):\s*[-+]?(?:\d+(?:\.\d+)?|\.\d+)\)", r"\1", normalized)
        normalized = re.sub(r"\(([^()]+)\)", r"\1", normalized)
        normalized = re.sub(r"\[([^\[\]:|]+)\]", r"\1", normalized)
    return " ".join(normalized.split())


def _is_conditioning_pair_list(conditioning: Any) -> bool:
    return (
        isinstance(conditioning, list)
        and all(isinstance(item, (list, tuple)) and len(item) >= 2 for item in conditioning)
    )


def _value_mean(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    mean = getattr(value, "mean", None)
    if callable(mean):
        try:
            return float(mean().item())
        except AttributeError:
            try:
                return float(mean())
            except (TypeError, ValueError):
                return None
        except (TypeError, ValueError):
            return None
    return None


def _scale_value(value: Any, scale: float) -> Any:
    if isinstance(value, (int, float)):
        return float(value) * float(scale)
    try:
        return value * float(scale)
    except Exception:
        return value


def _mean_normalize_conditioning(weighted: list[Any], reference: list[Any]) -> list[Any]:
    normalized: list[Any] = []
    for index, item in enumerate(weighted):
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            normalized.append(item)
            continue
        reference_value = reference[index][0] if index < len(reference) else None
        weighted_mean = _value_mean(item[0])
        reference_mean = _value_mean(reference_value)
        if weighted_mean is None or reference_mean is None or abs(weighted_mean) <= 1e-12:
            normalized.append(item)
            continue
        normalized.append([_scale_value(item[0], reference_mean / weighted_mean), _clone_metadata(item[1])])
    return normalized


def _encode_text(
    clip: Any,
    text: str,
    *,
    tokenizer: Callable[[Any, str], Any],
    options: A1111PromptEncodingOptions | None = None,
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    normalized_text = _normalize_slice_text(text)
    tokens = tokenizer(clip, normalized_text)
    weighted = clip.encode_from_tokens_scheduled(tokens, add_dict=add_dict)
    resolved_options = options or A1111PromptEncodingOptions()
    if not bool(resolved_options.mean_normalization) or not _is_conditioning_pair_list(weighted):
        return weighted
    plain_text = strip_a1111_attention_weights(normalized_text)
    if not plain_text or plain_text == normalized_text:
        return weighted
    reference_tokens = tokenizer(clip, plain_text)
    reference = clip.encode_from_tokens_scheduled(reference_tokens, add_dict=add_dict)
    if not _is_conditioning_pair_list(reference):
        return weighted
    return _mean_normalize_conditioning(weighted, reference)


def _compile_slice(
    clip: Any,
    slice_item: PromptScheduleSlice,
    *,
    tokenizer: Callable[[Any, str], Any],
    options: A1111PromptEncodingOptions | None = None,
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    conditioning = _encode_text(clip, slice_item.text, tokenizer=tokenizer, options=options, add_dict=add_dict)
    start = round(max(0.0, min(1.0, float(slice_item.start))), 4)
    end = round(max(0.0, min(1.0, float(slice_item.end))), 4)
    if start <= 0.0 and end >= 1.0:
        return conditioning
    return _set_conditioning_values(conditioning, {"start_percent": start, "end_percent": end})


def _compile_chunk(
    clip: Any,
    chunk: PromptChunkSemantic,
    *,
    tokenizer: Callable[[Any, str], Any],
    options: A1111PromptEncodingOptions | None = None,
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    slices = chunk.slices or [PromptScheduleSlice(text=chunk.text)]
    return _combine_conditioning(
        [
            _compile_slice(
                clip,
                slice_item,
                tokenizer=tokenizer,
                options=options,
                add_dict=add_dict,
            )
            for slice_item in slices
        ]
    )


def _compile_branch(
    clip: Any,
    branch: PromptBranchSemantic,
    *,
    tokenizer: Callable[[Any, str], Any],
    options: A1111PromptEncodingOptions | None = None,
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    chunks = branch.chunks or [PromptChunkSemantic(text=branch.text, slices=[PromptScheduleSlice(text=branch.text)])]
    compiled_chunks = [
        _compile_chunk(clip, chunk, tokenizer=tokenizer, options=options, add_dict=add_dict)
        for chunk in chunks
    ]
    branch_conditioning = compiled_chunks[0] if compiled_chunks else []
    for chunk_conditioning in compiled_chunks[1:]:
        branch_conditioning = _concat_conditioning(branch_conditioning, chunk_conditioning)
    branch_weight = round(float(branch.weight), 3)
    if abs(branch_weight - 1.0) > 1e-6:
        branch_conditioning = _set_conditioning_values(branch_conditioning, {"strength": max(0.0, min(10.0, branch_weight))})
    return branch_conditioning


def encode_a1111_prompt_conditioning(
    clip: Any,
    prompt_text: str,
    *,
    tokenizer: Callable[[Any, str], Any],
    options: A1111PromptEncodingOptions | None = None,
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    plan = build_a1111_prompt_encoding_plan(prompt_text, options=options)
    if not prompt_requires_single_node_compiler(plan):
        return _encode_text(clip, plan.normalized_text, tokenizer=tokenizer, options=options, add_dict=add_dict)

    branches = plan.branches or [
        PromptBranchSemantic(
            text=plan.normalized_text,
            chunks=[PromptChunkSemantic(text=plan.normalized_text, slices=[PromptScheduleSlice(text=plan.normalized_text)])],
        )
    ]
    return _combine_conditioning(
        [
            _compile_branch(
                clip,
                branch,
                tokenizer=tokenizer,
                options=options,
                add_dict=add_dict,
            )
            for branch in branches
        ]
    )


def encode_a1111_prompt_text_conditioning(
    clip: Any,
    prompt_text: str,
    *,
    tokenizer: Callable[[Any, str], Any],
    options: A1111PromptEncodingOptions | None = None,
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    return _encode_text(clip, prompt_text, tokenizer=tokenizer, options=options, add_dict=add_dict)


def _collect_boundary_points(plan: PromptSemanticPlan) -> set[float]:
    boundaries: set[float] = {0.0, 1.0}
    for branch in plan.branches:
        for chunk in branch.chunks:
            for slice_item in chunk.slices:
                boundaries.add(round(max(0.0, min(1.0, float(slice_item.start))), 4))
                boundaries.add(round(max(0.0, min(1.0, float(slice_item.end))), 4))
    return boundaries


def _boundaries_to_intervals(boundaries: set[float]) -> list[tuple[float, float]]:
    sorted_boundaries = sorted(boundaries or {0.0, 1.0})
    return [
        (sorted_boundaries[index], sorted_boundaries[index + 1])
        for index in range(len(sorted_boundaries) - 1)
        if sorted_boundaries[index + 1] > sorted_boundaries[index]
    ]


def _slice_text_at(plan: PromptSemanticPlan, *, start: float, end: float) -> str:
    midpoint = (float(start) + float(end)) / 2.0
    for branch in plan.branches:
        for chunk in branch.chunks:
            for slice_item in chunk.slices:
                if float(slice_item.start) <= midpoint < float(slice_item.end):
                    return slice_item.text
            if chunk.text:
                return chunk.text
    return plan.normalized_text


def _fallback_branch(plan: PromptSemanticPlan) -> PromptBranchSemantic:
    return PromptBranchSemantic(
        text=plan.normalized_text,
        chunks=[PromptChunkSemantic(text=plan.normalized_text, slices=[PromptScheduleSlice(text=plan.normalized_text)])],
    )


def _branch_at(plan: PromptSemanticPlan, index: int) -> PromptBranchSemantic:
    if plan.branches:
        if index < len(plan.branches):
            return plan.branches[index]
        if len(plan.branches) == 1:
            return plan.branches[0]
    return _fallback_branch(plan)


def _chunk_at(branch: PromptBranchSemantic, index: int) -> PromptChunkSemantic:
    if branch.chunks:
        if index < len(branch.chunks):
            return branch.chunks[index]
        if len(branch.chunks) == 1:
            return branch.chunks[0]
    return PromptChunkSemantic(text=branch.text, slices=[PromptScheduleSlice(text=branch.text)])


def _chunk_boundary_points(chunk: PromptChunkSemantic) -> set[float]:
    boundaries: set[float] = {0.0, 1.0}
    for slice_item in chunk.slices:
        boundaries.add(round(max(0.0, min(1.0, float(slice_item.start))), 4))
        boundaries.add(round(max(0.0, min(1.0, float(slice_item.end))), 4))
    return boundaries


def _chunk_slice_text_at(chunk: PromptChunkSemantic, *, start: float, end: float) -> str:
    midpoint = (float(start) + float(end)) / 2.0
    for slice_item in chunk.slices:
        if float(slice_item.start) <= midpoint < float(slice_item.end):
            return slice_item.text
    return chunk.text


def _compile_sdxl_slice_pair(
    clip: Any,
    *,
    chunk_g: PromptChunkSemantic,
    chunk_l: PromptChunkSemantic,
    start: float,
    end: float,
    tokenizer: Callable[[Any, str, str], Any],
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    conditioning = _encode_sdxl_pair(
        clip,
        text_g=_chunk_slice_text_at(chunk_g, start=start, end=end),
        text_l=_chunk_slice_text_at(chunk_l, start=start, end=end),
        tokenizer=tokenizer,
        add_dict=add_dict,
    )
    if start > 0.0 or end < 1.0:
        conditioning = _set_conditioning_values(conditioning, {"start_percent": start, "end_percent": end})
    return conditioning


def _compile_sdxl_chunk_pair(
    clip: Any,
    *,
    chunk_g: PromptChunkSemantic,
    chunk_l: PromptChunkSemantic,
    tokenizer: Callable[[Any, str, str], Any],
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    intervals = _boundaries_to_intervals(_chunk_boundary_points(chunk_g) | _chunk_boundary_points(chunk_l))
    return _combine_conditioning(
        [
            _compile_sdxl_slice_pair(
                clip,
                chunk_g=chunk_g,
                chunk_l=chunk_l,
                start=start,
                end=end,
                tokenizer=tokenizer,
                add_dict=add_dict,
            )
            for start, end in intervals
        ]
    )


def _compile_sdxl_branch_pair(
    clip: Any,
    *,
    branch_g: PromptBranchSemantic,
    branch_l: PromptBranchSemantic,
    tokenizer: Callable[[Any, str, str], Any],
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    chunk_count = max(len(branch_g.chunks or []), len(branch_l.chunks or []), 1)
    compiled_chunks = [
        _compile_sdxl_chunk_pair(
            clip,
            chunk_g=_chunk_at(branch_g, index),
            chunk_l=_chunk_at(branch_l, index),
            tokenizer=tokenizer,
            add_dict=add_dict,
        )
        for index in range(chunk_count)
    ]
    branch_conditioning = compiled_chunks[0] if compiled_chunks else []
    for chunk_conditioning in compiled_chunks[1:]:
        branch_conditioning = _concat_conditioning(branch_conditioning, chunk_conditioning)

    branch_weight = float(branch_g.weight)
    if abs(branch_weight - 1.0) <= 1e-6:
        branch_weight = float(branch_l.weight)
    branch_weight = round(branch_weight, 3)
    if abs(branch_weight - 1.0) > 1e-6:
        branch_conditioning = _set_conditioning_values(branch_conditioning, {"strength": max(0.0, min(10.0, branch_weight))})
    return branch_conditioning


def encode_a1111_sdxl_prompt_conditioning(
    clip: Any,
    *,
    text_g: str,
    text_l: str,
    tokenizer: Callable[[Any, str, str], Any],
    options: A1111PromptEncodingOptions | None = None,
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    plan_g = build_a1111_prompt_encoding_plan(text_g, options=options)
    plan_l = build_a1111_prompt_encoding_plan(text_l, options=options)
    if not prompt_requires_single_node_compiler(plan_g) and not prompt_requires_single_node_compiler(plan_l):
        return _encode_sdxl_pair(clip, text_g=plan_g.normalized_text, text_l=plan_l.normalized_text, tokenizer=tokenizer, add_dict=add_dict)

    branch_count = max(len(plan_g.branches or []), len(plan_l.branches or []), 1)
    return _combine_conditioning(
        [
            _compile_sdxl_branch_pair(
                clip,
                branch_g=_branch_at(plan_g, index),
                branch_l=_branch_at(plan_l, index),
                tokenizer=tokenizer,
                add_dict=add_dict,
            )
            for index in range(branch_count)
        ]
    )


def encode_a1111_sdxl_prompt_text_conditioning(
    clip: Any,
    *,
    text_g: str,
    text_l: str,
    tokenizer: Callable[[Any, str, str], Any],
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    return _encode_sdxl_pair(clip, text_g=text_g, text_l=text_l, tokenizer=tokenizer, add_dict=add_dict)


def _encode_sdxl_pair(
    clip: Any,
    *,
    text_g: str,
    text_l: str,
    tokenizer: Callable[[Any, str, str], Any],
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    tokens = tokenizer(
        clip,
        _normalize_slice_text(text_g),
        _normalize_slice_text(text_l),
    )
    return clip.encode_from_tokens_scheduled(tokens, add_dict=add_dict)
