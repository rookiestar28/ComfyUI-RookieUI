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
from rookieui.services.textual_inversion_resolver import resolve_textual_inversion_prompt

PROMPT_PARSER_MODE_OPTIONS = ("A1111", "full", "comfy++", "fixed attention")
_PROMPT_PARSER_MODE_ALIASES = {
    "": "A1111",
    "a1111": "A1111",
    "automatic1111": "A1111",
    "automatic 1111": "A1111",
    "parity": "A1111",
    "full": "full",
    "full parser": "full",
    "comfy++": "comfy++",
    "comfy_plus": "comfy++",
    "comfy plus": "comfy++",
    "fixed": "fixed attention",
    "fixed attention": "fixed attention",
    "fixed_attention": "fixed attention",
}


@dataclass(frozen=True)
class A1111PromptEncodingOptions:
    step_count: int = 10
    mean_normalization: bool = True
    use_old_emphasis_implementation: bool = False
    parser_mode: str = "A1111"
    embedding_names: str | tuple[str, ...] = ""
    embedding_directory: str = ""


def normalize_a1111_prompt_parser_mode(parser_mode: str | None) -> str:
    return _PROMPT_PARSER_MODE_ALIASES.get(str(parser_mode or "").strip().lower(), "A1111")


def _parser_mode_runs_a1111_semantic_compiler(parser_mode: str | None) -> bool:
    return normalize_a1111_prompt_parser_mode(parser_mode) in {"A1111", "full"}


def _parser_mode_uses_attention_weights(parser_mode: str | None) -> bool:
    return normalize_a1111_prompt_parser_mode(parser_mode) != "fixed attention"


def _normalize_prompt_text_for_parser(text: str, parser_mode: str | None) -> str:
    prompt_text = str(text or "")
    if normalize_a1111_prompt_parser_mode(parser_mode) != "full":
        return prompt_text
    cleaned = re.sub(r"[\x00-\x1f\x7f]+", " ", prompt_text)
    return " ".join(cleaned.split())


def _options_or_default(options: A1111PromptEncodingOptions | None) -> A1111PromptEncodingOptions:
    return options or A1111PromptEncodingOptions()


def _merge_encode_metadata(
    base: dict[str, Any] | None,
    extra: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not extra:
        return base
    merged = _clone_metadata(base)
    for key, value in extra.items():
        if isinstance(value, list) and isinstance(merged.get(key), list):
            merged[key] = [*merged[key], *value]
        else:
            merged[key] = value
    return merged


def _resolve_textual_inversion_for_encode(
    text: str,
    options: A1111PromptEncodingOptions,
    *,
    channel: str | None = None,
) -> tuple[str, dict[str, Any]]:
    if not options.embedding_names and not options.embedding_directory:
        return str(text or ""), {}
    result = resolve_textual_inversion_prompt(
        str(text or ""),
        embedding_names=options.embedding_names,
        embedding_directory=options.embedding_directory,
        channel=channel,
    )
    return result.resolved_text, result.metadata()


def build_a1111_prompt_encoding_plan(
    prompt_text: str,
    *,
    options: A1111PromptEncodingOptions | None = None,
) -> PromptSemanticPlan:
    resolved_options = _options_or_default(options)
    normalized_prompt_text = _normalize_prompt_text_for_parser(prompt_text, resolved_options.parser_mode)
    plan, _warnings = _build_prompt_semantic_plan(
        normalized_prompt_text,
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


def _prepare_text_for_weighted_encode(text: str, options: A1111PromptEncodingOptions | None) -> str:
    resolved_options = _options_or_default(options)
    prepared_text = _normalize_prompt_text_for_parser(text, resolved_options.parser_mode)
    if not _parser_mode_uses_attention_weights(resolved_options.parser_mode):
        return prepared_text
    return _normalize_slice_text(prepared_text)


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


def _token_entry_weight(entry: Any) -> float | None:
    if not isinstance(entry, (list, tuple)) or len(entry) < 2:
        return None
    try:
        return float(entry[1])
    except (TypeError, ValueError):
        return None


def _is_token_entry(entry: Any) -> bool:
    return _token_entry_weight(entry) is not None


def _collect_token_weight_batches(token_payload: Any) -> list[list[float]]:
    batches: list[list[float]] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for channel_value in value.values():
                visit(channel_value)
            return
        if not isinstance(value, list):
            return
        if value and all(_is_token_entry(entry) for entry in value):
            batches.append([float(_token_entry_weight(entry) or 1.0) for entry in value])
            return
        for item in value:
            visit(item)

    visit(token_payload)
    return batches


def _unweight_token_payload(token_payload: Any) -> Any:
    if isinstance(token_payload, dict):
        return token_payload.__class__(
            {key: _unweight_token_payload(value) for key, value in token_payload.items()}
        )
    if isinstance(token_payload, list):
        if _is_token_entry(token_payload):
            updated = list(token_payload)
            updated[1] = 1.0
            return updated
        return [_unweight_token_payload(item) for item in token_payload]
    if isinstance(token_payload, tuple) and _is_token_entry(token_payload):
        updated = list(token_payload)
        updated[1] = 1.0
        return tuple(updated)
    return token_payload


def _token_weight_mean(weight_batches: list[list[float]]) -> float:
    weights = [weight for batch in weight_batches for weight in batch]
    if not weights:
        return 1.0
    return float(sum(weights) / len(weights))


def _scale_tensor_with_token_weights(value: Any, weight_batches: list[list[float]], restore_mean: bool) -> Any:
    if torch is None or not hasattr(value, "shape") or not weight_batches:
        return None
    try:
        shape = tuple(value.shape)
        if len(shape) < 2:
            return None
        batch_count = int(shape[0])
        token_count = int(shape[1])
        if batch_count <= 0 or token_count <= 0:
            return None
        rows: list[list[float]] = []
        for batch_index in range(batch_count):
            row = list(weight_batches[batch_index] if batch_index < len(weight_batches) else weight_batches[0])
            if len(row) < token_count:
                row.extend([1.0] * (token_count - len(row)))
            rows.append(row[:token_count])
        kwargs: dict[str, Any] = {}
        dtype = getattr(value, "dtype", None)
        device = getattr(value, "device", None)
        if dtype is not None:
            kwargs["dtype"] = dtype
        if device is not None:
            kwargs["device"] = device
        multipliers = torch.asarray(rows, **kwargs).reshape(
            batch_count,
            token_count,
            *([1] * (len(shape) - 2)),
        )
        original_mean = value.mean()
        scaled = value * multipliers
        if not restore_mean:
            return scaled
        new_mean = scaled.mean()
        if abs(float(new_mean)) <= 1e-12:
            return scaled
        return scaled * (original_mean / new_mean)
    except Exception:
        return None


def _scale_value_with_old_emphasis(value: Any, weight_batches: list[list[float]], restore_mean: bool) -> Any:
    tensor_value = _scale_tensor_with_token_weights(value, weight_batches, restore_mean)
    if tensor_value is not None:
        return tensor_value

    weight_mean = _token_weight_mean(weight_batches)
    scaled = _scale_value(value, weight_mean)
    if not restore_mean:
        return scaled
    original_mean = _value_mean(value)
    scaled_mean = _value_mean(scaled)
    if original_mean is None or scaled_mean is None or abs(scaled_mean) <= 1e-12:
        return scaled
    return _scale_value(scaled, original_mean / scaled_mean)


def _apply_old_emphasis_conditioning(
    conditioning: list[Any],
    *,
    weight_batches: list[list[float]],
    mean_normalization: bool,
) -> list[Any]:
    if not _is_conditioning_pair_list(conditioning) or not weight_batches:
        return conditioning
    weight_mean = round(_token_weight_mean(weight_batches), 6)
    updated: list[Any] = []
    for item in conditioning:
        metadata = _clone_metadata(item[1])
        metadata.update(
            {
                "rookieui_emphasis_implementation": "old",
                "rookieui_old_emphasis_weight_mean": weight_mean,
            }
        )
        updated.append(
            [
                _scale_value_with_old_emphasis(
                    item[0],
                    weight_batches,
                    bool(mean_normalization),
                ),
                metadata,
            ]
        )
    return updated


def _encode_text_with_old_emphasis(
    clip: Any,
    text: str,
    *,
    tokenizer: Callable[[Any, str], Any],
    options: A1111PromptEncodingOptions,
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    tokens = tokenizer(clip, text)
    weight_batches = _collect_token_weight_batches(tokens)
    if not weight_batches:
        return clip.encode_from_tokens_scheduled(tokens, add_dict=add_dict)
    conditioning = clip.encode_from_tokens_scheduled(_unweight_token_payload(tokens), add_dict=add_dict)
    return _apply_old_emphasis_conditioning(
        conditioning,
        weight_batches=weight_batches,
        mean_normalization=bool(options.mean_normalization),
    )


def _encode_text(
    clip: Any,
    text: str,
    *,
    tokenizer: Callable[[Any, str], Any],
    options: A1111PromptEncodingOptions | None = None,
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    resolved_options = _options_or_default(options)
    resolved_text, resolver_metadata = _resolve_textual_inversion_for_encode(text, resolved_options)
    encode_add_dict = _merge_encode_metadata(add_dict, resolver_metadata)
    normalized_text = _prepare_text_for_weighted_encode(resolved_text, resolved_options)
    if (
        bool(resolved_options.use_old_emphasis_implementation)
        and _parser_mode_uses_attention_weights(resolved_options.parser_mode)
    ):
        return _encode_text_with_old_emphasis(
            clip,
            normalized_text,
            tokenizer=tokenizer,
            options=resolved_options,
            add_dict=encode_add_dict,
        )
    tokens = tokenizer(clip, normalized_text)
    weighted = clip.encode_from_tokens_scheduled(tokens, add_dict=encode_add_dict)
    if (
        not bool(resolved_options.mean_normalization)
        or not _parser_mode_uses_attention_weights(resolved_options.parser_mode)
        or not _is_conditioning_pair_list(weighted)
    ):
        return weighted
    plain_text = strip_a1111_attention_weights(normalized_text)
    if not plain_text or plain_text == normalized_text:
        return weighted
    reference_tokens = tokenizer(clip, plain_text)
    reference = clip.encode_from_tokens_scheduled(reference_tokens, add_dict=encode_add_dict)
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
    resolved_options = _options_or_default(options)
    if not _parser_mode_runs_a1111_semantic_compiler(resolved_options.parser_mode):
        return _encode_text(clip, prompt_text, tokenizer=tokenizer, options=resolved_options, add_dict=add_dict)
    plan = build_a1111_prompt_encoding_plan(prompt_text, options=resolved_options)
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
                options=resolved_options,
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
    options: A1111PromptEncodingOptions | None = None,
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    conditioning = _encode_sdxl_pair(
        clip,
        text_g=_chunk_slice_text_at(chunk_g, start=start, end=end),
        text_l=_chunk_slice_text_at(chunk_l, start=start, end=end),
        tokenizer=tokenizer,
        options=options,
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
    options: A1111PromptEncodingOptions | None = None,
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
                options=options,
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
    options: A1111PromptEncodingOptions | None = None,
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    chunk_count = max(len(branch_g.chunks or []), len(branch_l.chunks or []), 1)
    compiled_chunks = [
        _compile_sdxl_chunk_pair(
            clip,
            chunk_g=_chunk_at(branch_g, index),
            chunk_l=_chunk_at(branch_l, index),
            tokenizer=tokenizer,
            options=options,
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
    resolved_options = _options_or_default(options)
    if not _parser_mode_runs_a1111_semantic_compiler(resolved_options.parser_mode):
        return _encode_sdxl_pair(
            clip,
            text_g=text_g,
            text_l=text_l,
            tokenizer=tokenizer,
            options=resolved_options,
            add_dict=add_dict,
        )

    plan_g = build_a1111_prompt_encoding_plan(text_g, options=resolved_options)
    plan_l = build_a1111_prompt_encoding_plan(text_l, options=resolved_options)
    if not prompt_requires_single_node_compiler(plan_g) and not prompt_requires_single_node_compiler(plan_l):
        return _encode_sdxl_pair(
            clip,
            text_g=plan_g.normalized_text,
            text_l=plan_l.normalized_text,
            tokenizer=tokenizer,
            options=resolved_options,
            add_dict=add_dict,
        )

    branch_count = max(len(plan_g.branches or []), len(plan_l.branches or []), 1)
    return _combine_conditioning(
        [
            _compile_sdxl_branch_pair(
                clip,
                branch_g=_branch_at(plan_g, index),
                branch_l=_branch_at(plan_l, index),
                tokenizer=tokenizer,
                options=resolved_options,
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
    options: A1111PromptEncodingOptions | None = None,
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    return _encode_sdxl_pair(clip, text_g=text_g, text_l=text_l, tokenizer=tokenizer, options=options, add_dict=add_dict)


def _encode_sdxl_pair(
    clip: Any,
    *,
    text_g: str,
    text_l: str,
    tokenizer: Callable[[Any, str, str], Any],
    options: A1111PromptEncodingOptions | None = None,
    add_dict: dict[str, Any] | None = None,
) -> list[Any]:
    resolved_options = _options_or_default(options)
    resolved_text_g, resolver_metadata_g = _resolve_textual_inversion_for_encode(
        text_g,
        resolved_options,
        channel="clip_g",
    )
    resolved_text_l, resolver_metadata_l = _resolve_textual_inversion_for_encode(
        text_l,
        resolved_options,
        channel="clip_l",
    )
    encode_add_dict = _merge_encode_metadata(
        _merge_encode_metadata(add_dict, resolver_metadata_g),
        resolver_metadata_l,
    )
    tokens = tokenizer(
        clip,
        _prepare_text_for_weighted_encode(resolved_text_g, resolved_options),
        _prepare_text_for_weighted_encode(resolved_text_l, resolved_options),
    )
    if (
        bool(resolved_options.use_old_emphasis_implementation)
        and _parser_mode_uses_attention_weights(resolved_options.parser_mode)
    ):
        weight_batches = _collect_token_weight_batches(tokens)
        if weight_batches:
            conditioning = clip.encode_from_tokens_scheduled(_unweight_token_payload(tokens), add_dict=encode_add_dict)
            return _apply_old_emphasis_conditioning(
                conditioning,
                weight_batches=weight_batches,
                mean_normalization=bool(resolved_options.mean_normalization),
            )
    return clip.encode_from_tokens_scheduled(tokens, add_dict=encode_add_dict)
