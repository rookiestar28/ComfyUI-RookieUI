from __future__ import annotations

import os
import re

from rookieui.contracts.prompt_dsl import (
    PromptAttentionMarker,
    PromptBranchSemantic,
    PromptEmbeddingReference,
    PromptChunkSemantic,
    PromptLoraActivation,
    PromptPreprocessResult,
    PromptScheduleSlice,
    PromptSemanticPlan,
)
from rookieui.security.request_guard import (
    build_host_selector_key,
    normalize_prompt_text,
    resolve_inventory_selector,
)
from rookieui.services.coercion import coerce_float, coerce_int

PROMPT_WARNING_AND_DETECTED = "PROMPT_AND_DETECTED"
PROMPT_WARNING_BREAK_DETECTED = "PROMPT_BREAK_DETECTED"
PROMPT_WARNING_SCHEDULE_DETECTED = "PROMPT_SCHEDULE_DETECTED"
PROMPT_WARNING_ALTERNATE_DETECTED = "PROMPT_ALTERNATE_DETECTED"
PROMPT_WARNING_ATTENTION_DETECTED = "PROMPT_ATTENTION_DETECTED"
PROMPT_WARNING_EMBEDDING_DETECTED = "PROMPT_EMBEDDING_DETECTED"
PROMPT_WARNING_EMBEDDING_MISSING = "PROMPT_EMBEDDING_MISSING"
PROMPT_WARNING_GUARD_AND_BRANCH_LIMIT = "PROMPT_GUARD_AND_BRANCH_LIMIT"
PROMPT_WARNING_GUARD_BREAK_CHUNK_LIMIT = "PROMPT_GUARD_BREAK_CHUNK_LIMIT"
PROMPT_WARNING_GUARD_SCHEDULE_SLICE_LIMIT = "PROMPT_GUARD_SCHEDULE_SLICE_LIMIT"
PROMPT_WARNING_SCHEDULE_INVALID_THRESHOLD = "PROMPT_SCHEDULE_INVALID_THRESHOLD"
PROMPT_WARNING_EXTRA_NETWORK_UNSUPPORTED_REMOVED = "PROMPT_EXTRA_NETWORK_UNSUPPORTED_REMOVED"
PROMPT_WARNING_LEGACY_FALLBACK_ENABLED = "PROMPT_LEGACY_FALLBACK_ENABLED"

PROMPT_DSL_LEGACY_ENV = "ROOKIEUI_PROMPT_DSL_LEGACY"

_EXTRA_NETWORK_RE = re.compile(r"<(\w+):([^>]+)>")
_EXPLICIT_ATTENTION_RE = re.compile(r"\(([^()]+):\s*([-+]?(?:\d+(?:\.\d+)?|\.\d+))\)")
_PAREN_ATTENTION_RE = re.compile(r"\(([^():][^()]*)\)")
_BRACKET_ATTENTION_RE = re.compile(r"\[([^\[\]:|]+)\]")
_EXPLICIT_EMBEDDING_RE = re.compile(r"(?<![\w./\\!$-])embedding:(?P<name>[\w.\-!$/\\]+)(?![\w./\\!$-])", re.IGNORECASE)
_BRANCH_WEIGHT_RE = re.compile(r"^(.*?)(?:\s*:\s*([-+]?(?:\d+(?:\.\d+)?|\.\d+)))\s*$")
_TOP_LEVEL_NUMERIC_RE = re.compile(r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)")
_A1111_DEEMPHASIS_WEIGHT = round(1.0 / 1.1, 4)
_ESCAPED_ATTENTION_MARKERS = {
    r"\(": "\0rookieui_paren_open\0",
    r"\)": "\0rookieui_paren_close\0",
    r"\[": "\0rookieui_bracket_open\0",
    r"\]": "\0rookieui_bracket_close\0",
}

_MAX_AND_BRANCHES = 8
_MAX_BREAK_CHUNKS = 16
_MAX_SCHEDULE_SLICES = 128
_MAX_SCHEDULE_EXPANSIONS = 16
_MAX_ATTENTION_GROUP_DEPTH = 32
_DEFAULT_PROMPT_STEP_COUNT = 10

_WARNING_MESSAGES = {
    PROMPT_WARNING_AND_DETECTED: "A1111 AND composition was detected and parsed into branch semantics.",
    PROMPT_WARNING_BREAK_DETECTED: "A1111 BREAK token was detected and parsed into chunk semantics.",
    PROMPT_WARNING_SCHEDULE_DETECTED: "A1111 prompt scheduling syntax was detected and parsed into timestep slices.",
    PROMPT_WARNING_ALTERNATE_DETECTED: "A1111 alternate prompt scheduling syntax was detected and parsed into per-step timestep slices.",
    PROMPT_WARNING_ATTENTION_DETECTED: "A1111 attention weighting syntax was detected and captured for semantic parity.",
    PROMPT_WARNING_EMBEDDING_DETECTED: "Textual inversion / embedding references were detected and normalized for the SD-family prompt path.",
    PROMPT_WARNING_EMBEDDING_MISSING: "A textual inversion / embedding reference did not match the host inventory and fell back to plain prompt text.",
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


def _is_escaped_character(text: str, index: int) -> bool:
    backslash_count = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslash_count += 1
        cursor -= 1
    return backslash_count % 2 == 1


def _split_top_level_delimiter(text: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth_round = 0
    depth_square = 0
    for index, char in enumerate(text):
        if _is_escaped_character(text, index):
            continue
        if char == "(":
            depth_round += 1
        elif char == ")":
            depth_round = max(depth_round - 1, 0)
        elif char == "[":
            depth_square += 1
        elif char == "]":
            depth_square = max(depth_square - 1, 0)
        elif char == delimiter and depth_round == 0 and depth_square == 0:
            parts.append(text[start:index])
            start = index + 1
    parts.append(text[start:])
    return parts


def _looks_like_alternate_prompt_group(content: str) -> bool:
    parts = _split_top_level_delimiter(content, "|")
    return len(parts) > 1


def _parse_prompt_schedule_group(content: str) -> tuple[str, str, str] | None:
    parts = _split_top_level_delimiter(content, ":")
    if len(parts) == 2:
        after_text, raw_threshold = parts
        before_text = ""
    elif len(parts) == 3:
        before_text, after_text, raw_threshold = parts
    else:
        return None
    if not _TOP_LEVEL_NUMERIC_RE.fullmatch(raw_threshold.strip()):
        return None
    return before_text, after_text, raw_threshold.strip()


def _looks_like_prompt_schedule_group(content: str) -> bool:
    return _parse_prompt_schedule_group(content) is not None


def _resolve_schedule_cutoff(
    raw_threshold: str,
    *,
    step_count: int,
) -> tuple[int | None, str | None]:
    try:
        threshold = _coerce_float(raw_threshold, "prompt_schedule_threshold")
    except ValueError:
        return None, PROMPT_WARNING_SCHEDULE_INVALID_THRESHOLD
    if threshold < 0:
        return 0, PROMPT_WARNING_SCHEDULE_INVALID_THRESHOLD
    if "." in raw_threshold:
        cutoff = int(float(threshold) * step_count)
    else:
        cutoff = int(float(threshold))
    return max(0, min(step_count, cutoff)), None


def _build_prompt_variant(
    source_text: str,
    *,
    start_index: int,
    end_index: int,
    replacement: str,
) -> str:
    return normalize_prompt_text(
        f"{source_text[:start_index]}{replacement}{source_text[end_index:]}",
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


def _merge_prompt_segments(
    segments: list[tuple[str, int, int]],
) -> list[tuple[str, int, int]]:
    if not segments:
        return []
    merged: list[tuple[str, int, int]] = []
    for text, start, end in segments:
        if end < start:
            continue
        if merged and merged[-1][0] == text and merged[-1][2] + 1 == start:
            previous_text, previous_start, _previous_end = merged[-1]
            merged[-1] = (previous_text, previous_start, end)
            continue
        merged.append((text, start, end))
    return merged


def _segments_to_slices(
    segments: list[tuple[str, int, int]],
    *,
    step_count: int,
) -> list[PromptScheduleSlice]:
    slices = [
        PromptScheduleSlice(
            text=text,
            start=round((start - 1) / step_count, 4),
            end=round(end / step_count, 4),
        )
        for text, start, end in _merge_prompt_segments(segments)
        if text or start <= end
    ]
    return _dedupe_slices(slices)


def _find_first_dynamic_prompt_group(
    text: str,
) -> tuple[str, int, int, tuple[str, ...]] | None:
    index = 0
    while index < len(text):
        if text[index] != "[" or _is_escaped_character(text, index):
            index += 1
            continue
        group_content, next_index = _extract_balanced_attention_group(text, index, "[", "]")
        if group_content is None:
            index += 1
            continue
        schedule_group = _parse_prompt_schedule_group(group_content)
        if schedule_group is not None:
            return ("schedule", index, next_index, schedule_group)
        alternate_parts = tuple(_split_top_level_delimiter(group_content, "|"))
        if len(alternate_parts) > 1:
            return ("alternate", index, next_index, alternate_parts)
        index = next_index
    return None


def _expand_schedule_slices(
    chunk_text: str,
    *,
    step_count: int | None = None,
) -> tuple[list[PromptScheduleSlice], bool, bool, list[str]]:
    initial_text = normalize_prompt_text(chunk_text, "prompt", required=False)
    effective_steps = max(1, int(step_count or _DEFAULT_PROMPT_STEP_COUNT))
    current_segments: list[tuple[str, int, int]] = [(initial_text, 1, effective_steps)]
    warning_codes: list[str] = []
    has_schedule = False
    has_alternate = False

    for _ in range(_MAX_SCHEDULE_EXPANSIONS):
        expanded = False
        next_segments: list[tuple[str, int, int]] = []
        for slice_text, start_step, end_step in current_segments:
            dynamic_group = _find_first_dynamic_prompt_group(slice_text)
            if dynamic_group is None:
                next_segments.append((slice_text, start_step, end_step))
                continue

            expanded = True
            group_kind, group_start, group_end, group_parts = dynamic_group
            if group_kind == "schedule":
                has_schedule = True
                before_text, after_text, raw_threshold = group_parts
                resolved_before = _build_prompt_variant(
                    slice_text,
                    start_index=group_start,
                    end_index=group_end,
                    replacement=before_text.strip(),
                )
                resolved_after = _build_prompt_variant(
                    slice_text,
                    start_index=group_start,
                    end_index=group_end,
                    replacement=after_text.strip(),
                )
                cutoff_step, threshold_warning = _resolve_schedule_cutoff(
                    raw_threshold,
                    step_count=effective_steps,
                )
                if threshold_warning:
                    warning_codes.append(threshold_warning)
                if cutoff_step is None:
                    next_segments.append((resolved_after or resolved_before, start_step, end_step))
                    continue
                if start_step <= cutoff_step:
                    next_segments.append((resolved_before, start_step, min(end_step, cutoff_step)))
                if end_step > cutoff_step:
                    next_segments.append((resolved_after, max(start_step, cutoff_step + 1), end_step))
                continue

            has_alternate = True
            alternate_parts = list(group_parts)
            if not alternate_parts:
                next_segments.append((slice_text, start_step, end_step))
                continue
            current_step = start_step
            while current_step <= end_step:
                active_option = alternate_parts[(current_step - 1) % len(alternate_parts)]
                run_end = current_step
                while run_end < end_step and alternate_parts[run_end % len(alternate_parts)] == active_option:
                    run_end += 1
                next_segments.append(
                    (
                        _build_prompt_variant(
                            slice_text,
                            start_index=group_start,
                            end_index=group_end,
                            replacement=active_option.strip(),
                        ),
                        current_step,
                        run_end,
                    )
                )
                current_step = run_end + 1

        if not expanded:
            break
        current_segments = _merge_prompt_segments(next_segments)
        if len(current_segments) > _MAX_SCHEDULE_SLICES:
            warning_codes.append(PROMPT_WARNING_GUARD_SCHEDULE_SLICE_LIMIT)
            current_segments = current_segments[:_MAX_SCHEDULE_SLICES]
            break

    if not current_segments:
        current_segments = [(initial_text, 1, effective_steps)]
    return (
        _segments_to_slices(current_segments, step_count=effective_steps),
        has_schedule,
        has_alternate,
        warning_codes,
    )


def _extract_attention_markers(prompt_text: str) -> list[PromptAttentionMarker]:
    scan_text = prompt_text
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
        markers.append(PromptAttentionMarker(token=token, weight=0.9, syntax="bracket"))
    return markers


def _normalize_embedding_lookup_key(value: str) -> str:
    return build_host_selector_key(str(value or "")).strip().lower()


def _strip_selector_extension(selector: str) -> str:
    root, extension = os.path.splitext(selector)
    if not extension:
        return selector
    if extension.lower() not in {".pt", ".bin", ".safetensors"}:
        return selector
    return root


def _iter_embedding_alias_variants(selector: str) -> set[str]:
    canonical = str(selector or "").strip()
    if not canonical:
        return set()

    normalized = build_host_selector_key(canonical)
    normalized_no_ext = _strip_selector_extension(normalized)
    basename = normalized.rsplit("/", 1)[-1]
    basename_no_ext = _strip_selector_extension(basename)

    variants = {
        canonical,
        normalized,
        normalized.replace("/", "\\"),
        normalized_no_ext,
        normalized_no_ext.replace("/", "\\"),
        basename,
        basename_no_ext,
    }
    return {variant for variant in variants if variant}


def _build_embedding_alias_lookup(
    inventory_selectors: list[str] | None,
) -> tuple[dict[str, str], re.Pattern[str] | None]:
    selector_values = (
        inventory_selectors
        if isinstance(inventory_selectors, (list, tuple, set))
        else []
    )
    alias_lookup: dict[str, str] = {}
    alias_variants: set[str] = set()
    for selector in selector_values:
        canonical = str(selector or "").strip()
        if not canonical:
            continue
        for alias in _iter_embedding_alias_variants(canonical):
            alias_lookup.setdefault(_normalize_embedding_lookup_key(alias), canonical)
            alias_variants.add(alias)

    if not alias_variants:
        return alias_lookup, None

    joined_aliases = "|".join(
        re.escape(alias)
        for alias in sorted(alias_variants, key=lambda value: len(_normalize_embedding_lookup_key(value)), reverse=True)
    )
    pattern = re.compile(
        rf"(?<!embedding:)(?<![\w./\\!$-])(?P<name>{joined_aliases})(?![\w./\\!$-])",
        re.IGNORECASE,
    )
    return alias_lookup, pattern


def _resolve_embedding_selector(alias_lookup: dict[str, str], token_name: str) -> str:
    return alias_lookup.get(_normalize_embedding_lookup_key(token_name), "")


def _extract_prompt_embeddings(
    prompt_text: str,
    *,
    inventory_selectors: list[str] | None,
) -> tuple[str, list[PromptEmbeddingReference], list[str], list[str]]:
    alias_lookup, bare_pattern = _build_embedding_alias_lookup(inventory_selectors)
    references: list[PromptEmbeddingReference] = []
    warning_messages: list[str] = []
    warning_codes: list[str] = []
    has_missing = False

    def _replace_explicit(match: re.Match[str]) -> str:
        nonlocal has_missing
        token = match.group(0)
        name = match.group("name")
        canonical_name = _resolve_embedding_selector(alias_lookup, name)
        if canonical_name:
            canonical_token = f"embedding:{canonical_name}"
            references.append(
                PromptEmbeddingReference(
                    token=token,
                    canonical_token=canonical_token,
                    name=canonical_name,
                    exists=True,
                    syntax="explicit",
                )
            )
            return canonical_token

        has_missing = True
        references.append(
            PromptEmbeddingReference(
                token=token,
                canonical_token=name,
                name=name,
                exists=False,
                syntax="explicit",
            )
        )
        warning_messages.append(
            f"Textual inversion embedding was not found in the host inventory and fell back to plain text: {token}"
        )
        return name

    normalized_prompt = _EXPLICIT_EMBEDDING_RE.sub(_replace_explicit, prompt_text)

    if bare_pattern is not None:
        def _replace_bare(match: re.Match[str]) -> str:
            token = match.group("name")
            canonical_name = _resolve_embedding_selector(alias_lookup, token)
            if not canonical_name:
                return token
            canonical_token = f"embedding:{canonical_name}"
            references.append(
                PromptEmbeddingReference(
                    token=token,
                    canonical_token=canonical_token,
                    name=canonical_name,
                    exists=True,
                    syntax="bare",
                )
            )
            return canonical_token

        normalized_prompt = bare_pattern.sub(_replace_bare, normalized_prompt)

    if references:
        warning_codes.append(PROMPT_WARNING_EMBEDDING_DETECTED)
    if has_missing:
        warning_codes.append(PROMPT_WARNING_EMBEDDING_MISSING)

    normalized_prompt = normalize_prompt_text(normalized_prompt, "prompt", required=False)
    return normalized_prompt, references, warning_messages, warning_codes


def _protect_escaped_attention_markers(text: str) -> str:
    protected = text
    for raw_marker, placeholder in _ESCAPED_ATTENTION_MARKERS.items():
        protected = protected.replace(raw_marker, placeholder)
    return protected


def _restore_escaped_attention_markers(text: str) -> str:
    restored = text
    for raw_marker, placeholder in _ESCAPED_ATTENTION_MARKERS.items():
        restored = restored.replace(placeholder, raw_marker[1:])
    return restored


def _extract_balanced_attention_group(
    text: str,
    start_index: int,
    opener: str,
    closer: str,
) -> tuple[str | None, int]:
    depth = 0
    for index in range(start_index, len(text)):
        char = text[index]
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[start_index + 1 : index], index + 1
    return None, start_index + 1


def _split_top_level_explicit_attention(content: str) -> tuple[str, str | None]:
    depth_round = 0
    depth_square = 0
    for index in range(len(content) - 1, -1, -1):
        char = content[index]
        if char == ")":
            depth_round += 1
        elif char == "(":
            depth_round = max(depth_round - 1, 0)
        elif char == "]":
            depth_square += 1
        elif char == "[":
            depth_square = max(depth_square - 1, 0)
        elif char == ":" and depth_round == 0 and depth_square == 0:
            suffix = content[index + 1 :].strip()
            if re.fullmatch(r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)", suffix or ""):
                return content[:index], suffix
    return content, None
def _rewrite_a1111_attention_groups(text: str, *, depth: int = 0) -> str:
    if depth > _MAX_ATTENTION_GROUP_DEPTH:
        raise ValueError(
            f"Prompt attention nesting exceeded maximum depth {_MAX_ATTENTION_GROUP_DEPTH}."
        )
    parts: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == "[":
            group_content, next_index = _extract_balanced_attention_group(text, index, "[", "]")
            if group_content is None:
                parts.append(char)
                index += 1
                continue
            if _looks_like_prompt_schedule_group(group_content) or _looks_like_alternate_prompt_group(group_content):
                rewritten_inner = _rewrite_a1111_attention_groups(group_content, depth=depth + 1)
                parts.append(f"[{rewritten_inner}]")
            else:
                rewritten_inner = _rewrite_a1111_attention_groups(group_content, depth=depth + 1)
                parts.append(f"({rewritten_inner}:{_A1111_DEEMPHASIS_WEIGHT})")
            index = next_index
            continue
        if char == "(":
            group_content, next_index = _extract_balanced_attention_group(text, index, "(", ")")
            if group_content is None:
                parts.append(char)
                index += 1
                continue
            rewritten_inner = _rewrite_a1111_attention_groups(group_content, depth=depth + 1)
            base_text, explicit_weight = _split_top_level_explicit_attention(rewritten_inner)
            if explicit_weight is None:
                parts.append(f"({rewritten_inner})")
            else:
                parts.append(f"({base_text}:{explicit_weight})")
            index = next_index
            continue
        parts.append(char)
        index += 1
    return "".join(parts)


def normalize_prompt_attention_for_weighted_encode(prompt_text: str) -> str:
    normalized = normalize_prompt_text(prompt_text, "prompt", required=False)
    if not normalized:
        return normalized
    protected = _protect_escaped_attention_markers(normalized)
    rewritten = _rewrite_a1111_attention_groups(protected)
    return _restore_escaped_attention_markers(rewritten)


def _build_prompt_semantic_plan(
    prompt_text: str,
    *,
    embeddings: list[PromptEmbeddingReference] | None = None,
    step_count: int | None = None,
) -> tuple[PromptSemanticPlan, list[str]]:
    warnings: list[str] = []
    normalized_embeddings = list(embeddings or [])
    branches_raw = _split_top_level_keyword(prompt_text, "AND")
    if len(branches_raw) > _MAX_AND_BRANCHES:
        warnings.append(PROMPT_WARNING_GUARD_AND_BRANCH_LIMIT)
        branches_raw = branches_raw[:_MAX_AND_BRANCHES]
    if len(branches_raw) > 1:
        warnings.append(PROMPT_WARNING_AND_DETECTED)

    branch_semantics: list[PromptBranchSemantic] = []
    has_break = False
    has_schedule = False
    has_alternate = False
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
            slices, chunk_has_schedule, chunk_has_alternate, chunk_warnings = _expand_schedule_slices(
                normalized_chunk,
                step_count=step_count,
            )
            has_schedule = has_schedule or chunk_has_schedule
            has_alternate = has_alternate or chunk_has_alternate
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
    if has_alternate:
        warnings.append(PROMPT_WARNING_ALTERNATE_DETECTED)
    if attention:
        warnings.append(PROMPT_WARNING_ATTENTION_DETECTED)

    plan = PromptSemanticPlan(
        normalized_text=normalize_prompt_text(prompt_text, "prompt", required=False),
        features={
            "and_composition": len(branch_semantics) > 1,
            "break_chunks": has_break,
            "prompt_scheduling": has_schedule,
            "alternate_prompt_scheduling": has_alternate,
            "attention_weighting": bool(attention),
            "embeddings_textual_inversion": bool(normalized_embeddings),
        },
        branches=branch_semantics,
        attention=attention,
        embeddings=normalized_embeddings,
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
    step_count: int | None = None,
    inventory_loras: list[str] | None = None,
    inventory_embeddings: list[str] | None = None,
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
    (
        cleaned_prompt,
        prompt_embeddings,
        prompt_embedding_messages,
        prompt_embedding_codes,
    ) = _extract_prompt_embeddings(
        cleaned_prompt,
        inventory_selectors=inventory_embeddings,
    )
    (
        cleaned_negative_prompt,
        negative_embeddings,
        negative_embedding_messages,
        negative_embedding_codes,
    ) = _extract_prompt_embeddings(
        cleaned_negative_prompt,
        inventory_selectors=inventory_embeddings,
    )

    if _is_legacy_prompt_dsl_enabled():
        # CRITICAL: keep this environment switch as a deterministic parser/compiler rollback path for host/runtime incidents; removing it blocks emergency parity fallback.
        warning_codes = list(
            dict.fromkeys(
                [
                    PROMPT_WARNING_LEGACY_FALLBACK_ENABLED,
                    *prompt_warning_codes,
                    *negative_warning_codes,
                    *prompt_embedding_codes,
                    *negative_embedding_codes,
                ]
            )
        )
        warnings = list(
            dict.fromkeys(
                [
                    *_warning_messages_from_codes(warning_codes),
                    *prompt_warning_messages,
                    *negative_warning_messages,
                    *prompt_embedding_messages,
                    *negative_embedding_messages,
                ]
            )
        )
        return PromptPreprocessResult(
            cleaned_prompt=cleaned_prompt,
            cleaned_negative_prompt=cleaned_negative_prompt,
            lora_activations=[*prompt_loras, *negative_loras],
            prompt_warnings=warnings,
            warning_codes=warning_codes,
            prompt_semantics=PromptSemanticPlan(
                normalized_text=cleaned_prompt,
                features={
                    **PromptSemanticPlan.empty(cleaned_prompt).features,
                    "embeddings_textual_inversion": bool(prompt_embeddings),
                },
                embeddings=prompt_embeddings,
            ),
            negative_prompt_semantics=PromptSemanticPlan(
                normalized_text=cleaned_negative_prompt,
                features={
                    **PromptSemanticPlan.empty(cleaned_negative_prompt).features,
                    "embeddings_textual_inversion": bool(negative_embeddings),
                },
                embeddings=negative_embeddings,
            ),
        )

    prompt_semantics, prompt_semantic_codes = _build_prompt_semantic_plan(
        cleaned_prompt,
        embeddings=prompt_embeddings,
        step_count=step_count,
    )
    negative_prompt_semantics, negative_semantic_codes = _build_prompt_semantic_plan(
        cleaned_negative_prompt,
        embeddings=negative_embeddings,
        step_count=step_count,
    )
    warning_codes = list(
        dict.fromkeys(
            [
                *prompt_semantic_codes,
                *negative_semantic_codes,
                *prompt_warning_codes,
                *negative_warning_codes,
                *prompt_embedding_codes,
                *negative_embedding_codes,
            ]
        )
    )
    warnings = list(
        dict.fromkeys(
            [
                *_warning_messages_from_codes(warning_codes),
                *prompt_warning_messages,
                *negative_warning_messages,
                *prompt_embedding_messages,
                *negative_embedding_messages,
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
