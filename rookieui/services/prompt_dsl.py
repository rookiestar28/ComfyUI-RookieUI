from __future__ import annotations

import os
import re

from rookieui.contracts.prompt_dsl import (
    PromptAttentionMarker,
    PromptBranchSemantic,
    PromptChunkSemantic,
    PromptLoraActivation,
    PromptPreprocessResult,
    PromptScheduleSlice,
    PromptSemanticPlan,
)
from rookieui.security.request_guard import normalize_prompt_text, resolve_inventory_selector
from rookieui.services.coercion import coerce_float, coerce_int

PROMPT_WARNING_AND_DETECTED = "PROMPT_AND_DETECTED"
PROMPT_WARNING_BREAK_DETECTED = "PROMPT_BREAK_DETECTED"
PROMPT_WARNING_SCHEDULE_DETECTED = "PROMPT_SCHEDULE_DETECTED"
PROMPT_WARNING_ATTENTION_DETECTED = "PROMPT_ATTENTION_DETECTED"
PROMPT_WARNING_GUARD_AND_BRANCH_LIMIT = "PROMPT_GUARD_AND_BRANCH_LIMIT"
PROMPT_WARNING_GUARD_BREAK_CHUNK_LIMIT = "PROMPT_GUARD_BREAK_CHUNK_LIMIT"
PROMPT_WARNING_GUARD_SCHEDULE_SLICE_LIMIT = "PROMPT_GUARD_SCHEDULE_SLICE_LIMIT"
PROMPT_WARNING_SCHEDULE_INVALID_THRESHOLD = "PROMPT_SCHEDULE_INVALID_THRESHOLD"
PROMPT_WARNING_EXTRA_NETWORK_UNSUPPORTED_REMOVED = "PROMPT_EXTRA_NETWORK_UNSUPPORTED_REMOVED"
PROMPT_WARNING_LEGACY_FALLBACK_ENABLED = "PROMPT_LEGACY_FALLBACK_ENABLED"

PROMPT_DSL_LEGACY_ENV = "ROOKIEUI_PROMPT_DSL_LEGACY"

_EXTRA_NETWORK_RE = re.compile(r"<(\w+):([^>]+)>")
_SCHEDULE_TOKEN_RE = re.compile(r"\[([^:\[\]]*):([^:\[\]]*):([^\[\]]+?)\]")
_EXPLICIT_ATTENTION_RE = re.compile(r"\(([^()]+):\s*([-+]?(?:\d+(?:\.\d+)?|\.\d+))\)")
_PAREN_ATTENTION_RE = re.compile(r"\(([^():][^()]*)\)")
_BRACKET_ATTENTION_RE = re.compile(r"\[([^\[\]:]+)\]")
_BRANCH_WEIGHT_RE = re.compile(r"^(.*?)(?:\s*:\s*([-+]?(?:\d+(?:\.\d+)?|\.\d+)))\s*$")

_MAX_AND_BRANCHES = 8
_MAX_BREAK_CHUNKS = 16
_MAX_SCHEDULE_SLICES = 24
_MAX_SCHEDULE_EXPANSIONS = 8

_WARNING_MESSAGES = {
    PROMPT_WARNING_AND_DETECTED: "A1111 AND composition was detected and parsed into branch semantics.",
    PROMPT_WARNING_BREAK_DETECTED: "A1111 BREAK token was detected and parsed into chunk semantics.",
    PROMPT_WARNING_SCHEDULE_DETECTED: "A1111 prompt scheduling syntax was detected and parsed into timestep slices.",
    PROMPT_WARNING_ATTENTION_DETECTED: "A1111 attention weighting syntax was detected and captured for semantic parity.",
    PROMPT_WARNING_GUARD_AND_BRANCH_LIMIT: "Prompt AND branch count exceeded guardrail; extra branches were truncated.",
    PROMPT_WARNING_GUARD_BREAK_CHUNK_LIMIT: "Prompt BREAK chunk count exceeded guardrail; extra chunks were truncated.",
    PROMPT_WARNING_GUARD_SCHEDULE_SLICE_LIMIT: "Prompt scheduling expansion exceeded guardrail; slices were truncated.",
    PROMPT_WARNING_SCHEDULE_INVALID_THRESHOLD: "Prompt scheduling threshold was invalid and fell back to linear full-range slice.",
    PROMPT_WARNING_EXTRA_NETWORK_UNSUPPORTED_REMOVED: "Unsupported A1111 extra network was removed from the prompt.",
    PROMPT_WARNING_LEGACY_FALLBACK_ENABLED: "Prompt semantic parser/compiler rollback switch is active (legacy mode).",
}


class _ExtraNetworkParams:
    def __init__(self, items: list[str]) -> None:
        self.items = items
        self.positional: list[str] = []
        self.named: dict[str, str] = {}
        for item in items:
            parts = item.split("=", 1)
            if len(parts) == 2:
                self.named[parts[0].strip().lower()] = parts[1].strip()
            else:
                self.positional.append(item.strip())


def _coerce_float(value: str, field_name: str) -> float:
    return coerce_float(value, field_name, error_label="numeric")


def _coerce_int(value: str, field_name: str) -> int:
    return coerce_int(value, field_name)


def _is_keyword_boundary(text: str, start: int, end: int) -> bool:
    left_ok = start == 0 or not text[start - 1].isalnum()
    right_ok = end >= len(text) or not text[end].isalnum()
    return left_ok and right_ok


def _split_top_level_keyword(text: str, keyword: str) -> list[str]:
    normalized_keyword = keyword.upper()
    if not text.strip():
        return [""]

    parts: list[str] = []
    start = 0
    depth_round = 0
    depth_square = 0
    index = 0
    while index < len(text):
        char = text[index]
        if char == "(":
            depth_round += 1
        elif char == ")":
            depth_round = max(depth_round - 1, 0)
        elif char == "[":
            depth_square += 1
        elif char == "]":
            depth_square = max(depth_square - 1, 0)

        next_index = index + len(normalized_keyword)
        token = text[index:next_index].upper()
        if depth_round == 0 and depth_square == 0 and token == normalized_keyword:
            if _is_keyword_boundary(text, index, next_index):
                parts.append(normalize_prompt_text(text[start:index], "prompt", required=False))
                start = next_index
                index = next_index
                continue
        index += 1

    parts.append(normalize_prompt_text(text[start:], "prompt", required=False))
    return parts


def _parse_branch_weight(branch_text: str) -> tuple[str, float]:
    candidate = normalize_prompt_text(branch_text, "prompt", required=False)
    if not candidate or candidate.endswith("]"):
        return candidate, 1.0

    match = _BRANCH_WEIGHT_RE.match(candidate)
    if not match:
        return candidate, 1.0

    base_text = normalize_prompt_text(match.group(1), "prompt", required=False)
    raw_weight = match.group(2)
    if not raw_weight:
        return candidate, 1.0
    return base_text, round(_coerce_float(raw_weight, "prompt_branch_weight"), 4)


def _normalize_schedule_threshold(raw_threshold: str) -> tuple[float | None, str | None]:
    try:
        threshold = _coerce_float(raw_threshold, "prompt_schedule_threshold")
    except ValueError:
        return None, PROMPT_WARNING_SCHEDULE_INVALID_THRESHOLD
    if threshold < 0:
        return 0.0, PROMPT_WARNING_SCHEDULE_INVALID_THRESHOLD
    if threshold <= 1:
        return threshold, None
    if threshold <= 100:
        return threshold / 100.0, None
    return 1.0, PROMPT_WARNING_SCHEDULE_INVALID_THRESHOLD


def _build_schedule_variant(source_text: str, match: re.Match[str], replacement: str) -> str:
    return normalize_prompt_text(
        f"{source_text[: match.start()]}{replacement}{source_text[match.end() :]}",
        "prompt",
        required=False,
    )


def _dedupe_slices(slices: list[PromptScheduleSlice]) -> list[PromptScheduleSlice]:
    seen: set[tuple[str, float, float]] = set()
    deduped: list[PromptScheduleSlice] = []
    for slice_item in slices:
        start = round(max(0.0, min(1.0, float(slice_item.start))), 4)
        end = round(max(0.0, min(1.0, float(slice_item.end))), 4)
        if end <= start:
            continue
        key = (slice_item.text, start, end)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(PromptScheduleSlice(text=slice_item.text, start=start, end=end))
    return deduped


def _expand_schedule_slices(chunk_text: str) -> tuple[list[PromptScheduleSlice], bool, list[str]]:
    initial_text = normalize_prompt_text(chunk_text, "prompt", required=False)
    current_slices = [PromptScheduleSlice(text=initial_text, start=0.0, end=1.0)]
    warning_codes: list[str] = []
    has_schedule = False

    for _ in range(_MAX_SCHEDULE_EXPANSIONS):
        expanded = False
        next_slices: list[PromptScheduleSlice] = []
        for slice_item in current_slices:
            match = _SCHEDULE_TOKEN_RE.search(slice_item.text)
            if not match:
                next_slices.append(slice_item)
                continue

            expanded = True
            has_schedule = True
            before_text = _build_schedule_variant(slice_item.text, match, match.group(1).strip())
            after_text = _build_schedule_variant(slice_item.text, match, match.group(2).strip())
            threshold, threshold_warning = _normalize_schedule_threshold(match.group(3).strip())
            if threshold_warning:
                warning_codes.append(threshold_warning)
            if threshold is None:
                next_slices.append(PromptScheduleSlice(text=after_text or before_text, start=slice_item.start, end=slice_item.end))
                continue

            start = float(slice_item.start)
            end = float(slice_item.end)
            cutoff = max(0.0, min(1.0, threshold))
            if cutoff > start:
                next_slices.append(PromptScheduleSlice(text=before_text, start=start, end=min(cutoff, end)))
            if cutoff < end:
                next_slices.append(PromptScheduleSlice(text=after_text, start=max(cutoff, start), end=end))
            if cutoff <= start and cutoff >= end:
                next_slices.append(PromptScheduleSlice(text=after_text or before_text, start=start, end=end))

        if not expanded:
            break
        current_slices = _dedupe_slices(next_slices)
        if len(current_slices) > _MAX_SCHEDULE_SLICES:
            warning_codes.append(PROMPT_WARNING_GUARD_SCHEDULE_SLICE_LIMIT)
            current_slices = current_slices[:_MAX_SCHEDULE_SLICES]
            break

    if not current_slices:
        current_slices = [PromptScheduleSlice(text=initial_text, start=0.0, end=1.0)]
    return current_slices, has_schedule, warning_codes


def _extract_attention_markers(prompt_text: str) -> list[PromptAttentionMarker]:
    scan_text = _SCHEDULE_TOKEN_RE.sub("", prompt_text)
    markers: list[PromptAttentionMarker] = []
    for match in _EXPLICIT_ATTENTION_RE.finditer(scan_text):
        markers.append(
            PromptAttentionMarker(
                token=match.group(0),
                weight=round(_coerce_float(match.group(2), "prompt_attention_weight"), 4),
                syntax="explicit",
            )
        )
    for match in _PAREN_ATTENTION_RE.finditer(scan_text):
        token = match.group(0)
        if _EXPLICIT_ATTENTION_RE.match(token):
            continue
        markers.append(PromptAttentionMarker(token=token, weight=1.1, syntax="paren"))
    for match in _BRACKET_ATTENTION_RE.finditer(scan_text):
        token = match.group(0)
        if _SCHEDULE_TOKEN_RE.match(token):
            continue
        markers.append(PromptAttentionMarker(token=token, weight=0.9, syntax="bracket"))
    return markers


def _build_prompt_semantic_plan(prompt_text: str) -> tuple[PromptSemanticPlan, list[str]]:
    warnings: list[str] = []
    branches_raw = _split_top_level_keyword(prompt_text, "AND")
    if len(branches_raw) > _MAX_AND_BRANCHES:
        warnings.append(PROMPT_WARNING_GUARD_AND_BRANCH_LIMIT)
        branches_raw = branches_raw[:_MAX_AND_BRANCHES]
    if len(branches_raw) > 1:
        warnings.append(PROMPT_WARNING_AND_DETECTED)

    branch_semantics: list[PromptBranchSemantic] = []
    has_break = False
    has_schedule = False
    for raw_branch in branches_raw:
        branch_text, branch_weight = _parse_branch_weight(raw_branch)
        chunk_raw = _split_top_level_keyword(branch_text, "BREAK")
        if len(chunk_raw) > _MAX_BREAK_CHUNKS:
            warnings.append(PROMPT_WARNING_GUARD_BREAK_CHUNK_LIMIT)
            chunk_raw = chunk_raw[:_MAX_BREAK_CHUNKS]
        if len(chunk_raw) > 1:
            has_break = True

        chunks: list[PromptChunkSemantic] = []
        for raw_chunk in chunk_raw:
            normalized_chunk = normalize_prompt_text(raw_chunk, "prompt", required=False)
            slices, chunk_has_schedule, chunk_warnings = _expand_schedule_slices(normalized_chunk)
            has_schedule = has_schedule or chunk_has_schedule
            warnings.extend(chunk_warnings)
            chunks.append(
                PromptChunkSemantic(
                    text=normalized_chunk,
                    slices=slices,
                )
            )

        branch_semantics.append(
            PromptBranchSemantic(
                text=branch_text,
                weight=branch_weight,
                chunks=chunks,
            )
        )

    attention = _extract_attention_markers(prompt_text)
    if has_break:
        warnings.append(PROMPT_WARNING_BREAK_DETECTED)
    if has_schedule:
        warnings.append(PROMPT_WARNING_SCHEDULE_DETECTED)
    if attention:
        warnings.append(PROMPT_WARNING_ATTENTION_DETECTED)

    plan = PromptSemanticPlan(
        normalized_text=normalize_prompt_text(prompt_text, "prompt", required=False),
        features={
            "and_composition": len(branch_semantics) > 1,
            "break_chunks": has_break,
            "prompt_scheduling": has_schedule,
            "attention_weighting": bool(attention),
        },
        branches=branch_semantics,
        attention=attention,
        guardrail_hits=[
            code
            for code in warnings
            if code
            in {
                PROMPT_WARNING_GUARD_AND_BRANCH_LIMIT,
                PROMPT_WARNING_GUARD_BREAK_CHUNK_LIMIT,
                PROMPT_WARNING_GUARD_SCHEDULE_SLICE_LIMIT,
            }
        ],
    )
    return plan, list(dict.fromkeys(warnings))


def _build_inline_lora_activation(
    params: _ExtraNetworkParams,
    *,
    inventory_selectors: list[str] | None,
    strict_match: bool,
) -> PromptLoraActivation:
    if not params.positional or not params.positional[0]:
        raise ValueError("inline LoRA syntax requires a model name.")

    lora_name = resolve_inventory_selector(
        params.positional[0],
        "inline_lora_name",
        default_value="",
        inventory_selectors=inventory_selectors,
        strict_match=strict_match,
    )
    if not lora_name:
        raise ValueError("inline LoRA syntax requires a model name.")

    clip_strength = 1.0
    if len(params.positional) > 1 and params.positional[1]:
        clip_strength = _coerce_float(params.positional[1], "inline_lora_clip_strength")
    if "te" in params.named:
        clip_strength = _coerce_float(params.named["te"], "inline_lora_clip_strength")

    model_strength = clip_strength
    if len(params.positional) > 2 and params.positional[2]:
        model_strength = _coerce_float(params.positional[2], "inline_lora_model_strength")
    if "unet" in params.named:
        model_strength = _coerce_float(params.named["unet"], "inline_lora_model_strength")

    dyn_dim = None
    if len(params.positional) > 3 and params.positional[3]:
        dyn_dim = _coerce_int(params.positional[3], "inline_lora_dyn")
    if "dyn" in params.named:
        dyn_dim = _coerce_int(params.named["dyn"], "inline_lora_dyn")

    return PromptLoraActivation(
        name=lora_name,
        strength_model=round(model_strength, 3),
        strength_clip=round(clip_strength, 3),
        dyn_dim=dyn_dim,
        source="inline",
    )


def _extract_inline_activations(
    prompt_text: str,
    *,
    inventory_selectors: list[str] | None,
    strict_match: bool,
) -> tuple[str, list[PromptLoraActivation], list[str], list[str]]:
    activations: list[PromptLoraActivation] = []
    warnings: list[str] = []
    warning_codes: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        network_name = match.group(1).strip().lower()
        params = _ExtraNetworkParams([item.strip() for item in match.group(2).split(":") if item.strip()])
        if network_name in {"lora", "lyco"}:
            activations.append(
                _build_inline_lora_activation(
                    params,
                    inventory_selectors=inventory_selectors,
                    strict_match=strict_match,
                )
            )
            return ""

        warning_codes.append(PROMPT_WARNING_EXTRA_NETWORK_UNSUPPORTED_REMOVED)
        warnings.append(f"Unsupported A1111 extra network was removed from the prompt: <{network_name}:...>.")
        return ""

    cleaned = _EXTRA_NETWORK_RE.sub(_replace, prompt_text)
    cleaned = normalize_prompt_text(cleaned, "prompt", required=False)
    return cleaned, activations, warnings, warning_codes


def merge_lora_activations(
    inline_activations: list[PromptLoraActivation],
    *,
    explicit_lora_name: str,
    explicit_strength_model: float,
    explicit_strength_clip: float,
) -> list[PromptLoraActivation]:
    merged = list(inline_activations)
    if not explicit_lora_name:
        return merged

    explicit_activation = PromptLoraActivation(
        name=explicit_lora_name,
        strength_model=round(float(explicit_strength_model), 3),
        strength_clip=round(float(explicit_strength_clip), 3),
        source="selector",
    )
    # IMPORTANT: keep the selector merge deterministic; explicit UI LoRA must override the matching inline token instead of silently stacking the same host LoRA twice.
    for index, activation in enumerate(merged):
        if activation.name == explicit_activation.name:
            merged[index] = explicit_activation
            return merged

    merged.append(explicit_activation)
    return merged


def _warning_messages_from_codes(codes: list[str]) -> list[str]:
    messages: list[str] = []
    for code in codes:
        message = _WARNING_MESSAGES.get(code)
        if message:
            messages.append(message)
    return messages


def _is_legacy_prompt_dsl_enabled() -> bool:
    raw_value = str(os.getenv(PROMPT_DSL_LEGACY_ENV, "")).strip().lower()
    return raw_value in {"1", "true", "yes", "on"}


def preprocess_prompt_bundle(
    prompt: str,
    negative_prompt: str,
    *,
    inventory_loras: list[str] | None = None,
    strict_match: bool = False,
) -> PromptPreprocessResult:
    cleaned_prompt, prompt_loras, prompt_warning_messages, prompt_warning_codes = _extract_inline_activations(
        prompt,
        inventory_selectors=inventory_loras,
        strict_match=strict_match,
    )
    (
        cleaned_negative_prompt,
        negative_loras,
        negative_warning_messages,
        negative_warning_codes,
    ) = _extract_inline_activations(
        negative_prompt,
        inventory_selectors=inventory_loras,
        strict_match=strict_match,
    )

    if _is_legacy_prompt_dsl_enabled():
        # CRITICAL: keep this environment switch as a deterministic parser/compiler rollback path for host/runtime incidents; removing it blocks emergency parity fallback.
        warning_codes = list(
            dict.fromkeys(
                [
                    PROMPT_WARNING_LEGACY_FALLBACK_ENABLED,
                    *prompt_warning_codes,
                    *negative_warning_codes,
                ]
            )
        )
        warnings = list(
            dict.fromkeys(
                [
                    *_warning_messages_from_codes(warning_codes),
                    *prompt_warning_messages,
                    *negative_warning_messages,
                ]
            )
        )
        return PromptPreprocessResult(
            cleaned_prompt=cleaned_prompt,
            cleaned_negative_prompt=cleaned_negative_prompt,
            lora_activations=[*prompt_loras, *negative_loras],
            prompt_warnings=warnings,
            warning_codes=warning_codes,
            prompt_semantics=PromptSemanticPlan.empty(cleaned_prompt),
            negative_prompt_semantics=PromptSemanticPlan.empty(cleaned_negative_prompt),
        )

    prompt_semantics, prompt_semantic_codes = _build_prompt_semantic_plan(cleaned_prompt)
    negative_prompt_semantics, negative_semantic_codes = _build_prompt_semantic_plan(cleaned_negative_prompt)
    warning_codes = list(
        dict.fromkeys(
            [
                *prompt_semantic_codes,
                *negative_semantic_codes,
                *prompt_warning_codes,
                *negative_warning_codes,
            ]
        )
    )
    warnings = list(
        dict.fromkeys(
            [
                *_warning_messages_from_codes(warning_codes),
                *prompt_warning_messages,
                *negative_warning_messages,
            ]
        )
    )

    return PromptPreprocessResult(
        cleaned_prompt=cleaned_prompt,
        cleaned_negative_prompt=cleaned_negative_prompt,
        lora_activations=[*prompt_loras, *negative_loras],
        prompt_warnings=warnings,
        warning_codes=warning_codes,
        prompt_semantics=prompt_semantics,
        negative_prompt_semantics=negative_prompt_semantics,
    )
