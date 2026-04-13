from __future__ import annotations

import re
from typing import Any

from rookieui.services.a1111_prompt_engine import (
    get_learned_conditioning_prompt_schedules,
    parse_prompt_attention,
    split_weighted_subprompts,
)

_TOKEN_BREAK_WEIGHT = -1.0
_DEFAULT_BRANCH_WEIGHT = 1.0


def _resolve_single_clip_tokenizer(clip: object) -> tuple[str, Any]:
    tokenizer = getattr(clip, "tokenizer", None)
    if tokenizer is None:
        raise ValueError("A1111 conditioning node requires a CLIP object with a tokenizer.")

    clip_name = str(getattr(tokenizer, "clip_name", "") or "").strip()
    clip_attr = str(getattr(tokenizer, "clip", "") or "").strip()
    inner = getattr(tokenizer, clip_attr, None) if clip_attr else None
    if inner is None and clip_name:
        inner = getattr(tokenizer, f"clip_{clip_name}", None)
    if inner is None:
        raise ValueError("A1111 conditioning node supports single-encoder CLIP tokenizers only.")

    resolved_clip_name = clip_name or clip_attr.replace("clip_", "", 1) or "l"
    return resolved_clip_name, inner


def _resolve_sdxl_clip_tokenizers(clip: object) -> tuple[Any, Any]:
    tokenizer = getattr(clip, "tokenizer", None)
    if tokenizer is None:
        raise ValueError("A1111 SDXL conditioning node requires a CLIP object with a tokenizer.")

    inner_l = getattr(tokenizer, "clip_l", None)
    inner_g = getattr(tokenizer, "clip_g", None)
    if inner_l is None or inner_g is None:
        raise ValueError("A1111 SDXL conditioning node requires dual-tokenizer CLIP inputs.")
    return inner_l, inner_g


def _pad_batch(batch: list[tuple[object, float]], inner_tokenizer: Any, amount: int) -> None:
    if amount <= 0:
        return
    pad_token = getattr(inner_tokenizer, "pad_token", None)
    pad_left = bool(getattr(inner_tokenizer, "pad_left", False))
    pad_values = [(pad_token, 1.0)] * int(amount)
    if pad_left:
        batch[:0] = pad_values
    else:
        batch.extend(pad_values)


def _tokenize_segment_text(inner_tokenizer: Any, segment_text: str, weight: float) -> list[list[tuple[object, float]]]:
    if not segment_text:
        return []

    embedding_identifier = str(getattr(inner_tokenizer, "embedding_identifier", "embedding:"))
    embedding_directory = getattr(inner_tokenizer, "embedding_directory", None)
    tokenizer_impl = getattr(inner_tokenizer, "tokenizer", None)
    if tokenizer_impl is None:
        raise ValueError("A1111 conditioning node requires a raw tokenizer implementation on the CLIP tokenizer.")

    token_groups: list[list[tuple[object, float]]] = []
    split = re.split(rf" {re.escape(embedding_identifier)}|\n{re.escape(embedding_identifier)}", segment_text)
    to_tokenize = [split[0]]
    for item in split[1:]:
        to_tokenize.append(f"{embedding_identifier}{item}")

    for word in (item for item in to_tokenize if item):
        if word.startswith(embedding_identifier) and embedding_directory is not None:
            embedding_name = word[len(embedding_identifier) :].strip("\n")
            try_get_embedding = getattr(inner_tokenizer, "_try_get_embedding", None)
            if callable(try_get_embedding):
                embedding, leftover = try_get_embedding(embedding_name)
                if embedding is not None:
                    if len(getattr(embedding, "shape", ())) == 1:
                        token_groups.append([(embedding, weight)])
                    else:
                        token_groups.append(
                            [(embedding[index], weight) for index in range(int(embedding.shape[0]))]
                        )
                if leftover:
                    word = leftover
                else:
                    continue

        tokenized = tokenizer_impl(word)["input_ids"]
        end = -1 if bool(getattr(inner_tokenizer, "tokenizer_adds_end_token", False)) else None
        tokens = tokenized[int(getattr(inner_tokenizer, "tokens_start", 0)) : end]
        if tokens:
            token_groups.append([(token, weight) for token in tokens])

    return token_groups


def _build_token_batches(inner_tokenizer: Any, prompt_text: str) -> list[list[tuple[object, float]]]:
    parsed = parse_prompt_attention(prompt_text)

    max_length = int(getattr(inner_tokenizer, "max_length", 77))
    max_word_length = int(getattr(inner_tokenizer, "max_word_length", max_length))
    start_token = getattr(inner_tokenizer, "start_token", None)
    end_token = getattr(inner_tokenizer, "end_token", None)
    pad_to_max_length = bool(getattr(inner_tokenizer, "pad_to_max_length", True))

    batches: list[list[tuple[object, float]]] = []
    current_batch: list[tuple[object, float]] = []
    if start_token is not None:
        current_batch.append((start_token, 1.0))

    def finalize_batch(*, allow_empty: bool) -> None:
        nonlocal current_batch
        has_payload = len(current_batch) > (1 if start_token is not None else 0)
        if not has_payload and not allow_empty:
            return
        batch = list(current_batch)
        if end_token is not None:
            batch.append((end_token, 1.0))
        if pad_to_max_length and len(batch) < max_length:
            _pad_batch(batch, inner_tokenizer, max_length - len(batch))
        batches.append(batch)
        current_batch = []
        if start_token is not None:
            current_batch.append((start_token, 1.0))

    for segment in parsed:
        segment_text = segment.text
        weight = segment.weight
        if segment_text == "BREAK" and float(weight) == _TOKEN_BREAK_WEIGHT:
            # CRITICAL: BREAK must force a tokenizer-side chunk boundary here; replacing this with a graph-only combine reopens the exact parity bug we are cutting over.
            finalize_batch(allow_empty=True)
            continue

        token_groups = _tokenize_segment_text(inner_tokenizer, segment_text, float(weight))
        for token_group in token_groups:
            working_group = list(token_group)
            is_large = len(working_group) >= max_word_length
            has_end_token = 1 if end_token is not None else 0
            while working_group:
                remaining = max_length - len(current_batch) - has_end_token
                if len(working_group) > remaining:
                    if is_large and remaining > 0:
                        current_batch.extend(working_group[:remaining])
                        working_group = working_group[remaining:]
                    finalize_batch(allow_empty=True)
                    continue

                current_batch.extend(working_group)
                working_group = []

    finalize_batch(allow_empty=not batches)
    if not batches:
        empty_batch: list[tuple[object, float]] = []
        if start_token is not None:
            empty_batch.append((start_token, 1.0))
        if end_token is not None:
            empty_batch.append((end_token, 1.0))
        if pad_to_max_length and len(empty_batch) < max_length:
            _pad_batch(empty_batch, inner_tokenizer, max_length - len(empty_batch))
        batches.append(empty_batch)

    return batches


def _build_single_encoder_tokens(clip: object, prompt_text: str) -> dict[str, list[list[tuple[object, float]]]]:
    clip_name, inner_tokenizer = _resolve_single_clip_tokenizer(clip)
    return {clip_name: _build_token_batches(inner_tokenizer, prompt_text)}


def _build_sdxl_tokens(clip: object, text_g: str, text_l: str) -> dict[str, list[list[tuple[object, float]]]]:
    inner_l, inner_g = _resolve_sdxl_clip_tokenizers(clip)
    g_batches = _build_token_batches(inner_g, text_g)
    l_batches = _build_token_batches(inner_l, text_l)
    empty_g = list(_build_token_batches(inner_g, "")[0])
    empty_l = list(_build_token_batches(inner_l, "")[0])

    while len(l_batches) < len(g_batches):
        l_batches.append(list(empty_l))
    while len(g_batches) < len(l_batches):
        g_batches.append(list(empty_g))

    return {"g": g_batches, "l": l_batches}


def _build_weighted_schedule_segments(prompt_text: str, *, steps: int) -> list[dict[str, object]]:
    resolved_steps = max(int(steps), 1)
    output: list[dict[str, object]] = []
    for branch in split_weighted_subprompts(prompt_text):
        branch_text = branch.text
        branch_weight = branch.weight
        schedules = get_learned_conditioning_prompt_schedules([branch_text], resolved_steps)[0]
        schedule_start = 0
        for schedule in schedules:
            schedule_end = schedule.end_at_step
            schedule_text = schedule.text
            normalized_end = max(schedule_start + 1, int(schedule_end))
            output.append(
                {
                    "text": schedule_text,
                    "start_percent": round(float(schedule_start) / float(resolved_steps), 6),
                    "end_percent": round(float(min(resolved_steps, normalized_end)) / float(resolved_steps), 6),
                    "weight": float(branch_weight),
                }
            )
            schedule_start = normalized_end
    return output


def build_a1111_conditioning(clip: object, prompt_text: str, *, steps: int) -> list[list[object]]:
    output: list[list[object]] = []
    for segment in _build_weighted_schedule_segments(prompt_text, steps=steps):
        encoded = clip.encode_from_tokens(
            _build_single_encoder_tokens(clip, str(segment["text"])),
            return_pooled=True,
            return_dict=True,
        )
        cond = encoded.pop("cond")
        metadata = dict(encoded)
        metadata["start_percent"] = float(segment["start_percent"])
        metadata["end_percent"] = float(segment["end_percent"])
        if abs(float(segment["weight"]) - _DEFAULT_BRANCH_WEIGHT) > 1e-6:
            metadata["weight"] = float(segment["weight"])
        output.append([cond, metadata])

    return output


def build_a1111_conditioning_sdxl(
    clip: object,
    *,
    text_g: str,
    text_l: str,
    steps: int,
    width: int,
    height: int,
    crop_w: int = 0,
    crop_h: int = 0,
    target_width: int | None = None,
    target_height: int | None = None,
) -> list[list[object]]:
    segments_g = _build_weighted_schedule_segments(text_g, steps=steps)
    segments_l = _build_weighted_schedule_segments(text_l, steps=steps)
    if len(segments_g) != len(segments_l):
        raise ValueError("A1111 SDXL conditioning currently requires matching prompt schedule structure for text_g/text_l.")

    output: list[list[object]] = []
    resolved_target_width = int(width if target_width is None else target_width)
    resolved_target_height = int(height if target_height is None else target_height)
    for index, segment_g in enumerate(segments_g):
        segment_l = segments_l[index]
        if (
            float(segment_g["start_percent"]) != float(segment_l["start_percent"])
            or float(segment_g["end_percent"]) != float(segment_l["end_percent"])
            or abs(float(segment_g["weight"]) - float(segment_l["weight"])) > 1e-6
        ):
            raise ValueError("A1111 SDXL conditioning requires aligned schedule windows and branch weights for text_g/text_l.")

        encoded = clip.encode_from_tokens(
            _build_sdxl_tokens(clip, str(segment_g["text"]), str(segment_l["text"])),
            return_pooled=True,
            return_dict=True,
        )
        cond = encoded.pop("cond")
        metadata = dict(encoded)
        metadata["width"] = int(width)
        metadata["height"] = int(height)
        metadata["crop_w"] = int(crop_w)
        metadata["crop_h"] = int(crop_h)
        metadata["target_width"] = resolved_target_width
        metadata["target_height"] = resolved_target_height
        metadata["start_percent"] = float(segment_g["start_percent"])
        metadata["end_percent"] = float(segment_g["end_percent"])
        if abs(float(segment_g["weight"]) - _DEFAULT_BRANCH_WEIGHT) > 1e-6:
            metadata["weight"] = float(segment_g["weight"])
        output.append([cond, metadata])

    return output
