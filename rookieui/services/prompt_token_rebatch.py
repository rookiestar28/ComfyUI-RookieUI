from __future__ import annotations

from dataclasses import dataclass
import numbers
from typing import Any


_DEFAULT_MAX_LENGTH = 77
_DEFAULT_MAX_WORD_LENGTH = 8
_COMMA_PADDING_BACKTRACK = 20


@dataclass(frozen=True)
class SDTokenRebatchConfig:
    max_length: int
    start_token: object | None
    end_token: object | None
    pad_token: object | None
    comma_token: int | None
    max_word_length: int

    @property
    def content_capacity(self) -> int:
        reserved = int(self.start_token is not None) + int(self.end_token is not None)
        return max(1, int(self.max_length) - reserved)


def _entry_token(entry: Any) -> object | None:
    if isinstance(entry, (list, tuple)) and entry:
        return entry[0]
    return None


def _entry_weight(entry: Any) -> float:
    if isinstance(entry, (list, tuple)) and len(entry) > 1:
        try:
            return float(entry[1])
        except (TypeError, ValueError):
            return 1.0
    return 1.0


def _entry_word_id(entry: Any) -> int | None:
    if (
        isinstance(entry, (list, tuple))
        and len(entry) > 2
        and isinstance(entry[2], numbers.Integral)
    ):
        return int(entry[2])
    return None


def _strip_word_ids(channel_batches: list[list[Any]]) -> list[list[tuple[object, float]]]:
    return [
        [(_entry_token(entry), _entry_weight(entry)) for entry in batch]
        for batch in channel_batches
    ]


def _supports_word_ids(channel_batches: Any) -> bool:
    if not isinstance(channel_batches, list):
        return False
    for batch in channel_batches:
        if not isinstance(batch, list):
            return False
        for entry in batch:
            word_id = _entry_word_id(entry)
            if word_id is not None:
                return True
    return False


def _resolve_channel_tokenizer(clip: Any, channel_key: str | None) -> Any | None:
    tokenizer = getattr(clip, "tokenizer", None)
    if tokenizer is None:
        return None
    if channel_key:
        for attribute_name in (f"clip_{channel_key}", channel_key):
            channel = getattr(tokenizer, attribute_name, None)
            if channel is not None:
                return channel
    clip_name = getattr(tokenizer, "clip_name", None)
    if clip_name:
        channel = getattr(tokenizer, f"clip_{clip_name}", None)
        if channel is not None:
            return channel
    channel_attributes = [
        getattr(tokenizer, attribute_name)
        for attribute_name in dir(tokenizer)
        if attribute_name.startswith("clip_")
        and not attribute_name.startswith("__")
        and getattr(tokenizer, attribute_name, None) is not None
    ]
    if len(channel_attributes) == 1:
        return channel_attributes[0]
    return tokenizer


def _resolve_comma_token(channel_tokenizer: Any) -> int | None:
    comma_token = getattr(channel_tokenizer, "comma_token", None)
    if isinstance(comma_token, numbers.Integral):
        return int(comma_token)
    tokenizer = getattr(channel_tokenizer, "tokenizer", None)
    get_vocab = getattr(tokenizer, "get_vocab", None)
    if callable(get_vocab):
        vocab = get_vocab()
        for token_text in (",</w>", ","):
            token = vocab.get(token_text)
            if isinstance(token, numbers.Integral):
                return int(token)
    return None


def _infer_batch_layout(channel_batches: list[list[Any]]) -> tuple[int, object | None, object | None, object | None]:
    if not channel_batches:
        return _DEFAULT_MAX_LENGTH, None, None, None

    first_batch = next((batch for batch in channel_batches if batch), [])
    if not first_batch:
        return _DEFAULT_MAX_LENGTH, None, None, None

    max_length = len(first_batch)
    start_token = None
    end_token = None
    pad_token = None

    if _entry_word_id(first_batch[0]) == 0:
        start_token = _entry_token(first_batch[0])
    if _entry_word_id(first_batch[-1]) == 0:
        pad_token = _entry_token(first_batch[-1])

    positive_indices = [index for index, entry in enumerate(first_batch) if (_entry_word_id(entry) or 0) > 0]
    if positive_indices:
        end_index = positive_indices[-1] + 1
        if end_index < len(first_batch) and _entry_word_id(first_batch[end_index]) == 0:
            end_token = _entry_token(first_batch[end_index])
    elif len(first_batch) > 1 and _entry_word_id(first_batch[1]) == 0:
        end_token = _entry_token(first_batch[1])

    return max_length, start_token, end_token, pad_token


def _build_rebatch_config(
    clip: Any,
    channel_key: str | None,
    channel_batches: list[list[Any]],
) -> SDTokenRebatchConfig | None:
    channel_tokenizer = _resolve_channel_tokenizer(clip, channel_key)
    inferred_max_length, inferred_start, inferred_end, inferred_pad = _infer_batch_layout(channel_batches)

    max_length = int(getattr(channel_tokenizer, "max_length", inferred_max_length) or inferred_max_length)
    if max_length <= 0:
        return None

    start_token = getattr(channel_tokenizer, "start_token", inferred_start)
    end_token = getattr(channel_tokenizer, "end_token", inferred_end)
    pad_token = getattr(channel_tokenizer, "pad_token", inferred_pad)
    max_word_length = int(
        getattr(channel_tokenizer, "max_word_length", _DEFAULT_MAX_WORD_LENGTH) or _DEFAULT_MAX_WORD_LENGTH
    )
    if max_word_length <= 0:
        max_word_length = _DEFAULT_MAX_WORD_LENGTH

    return SDTokenRebatchConfig(
        max_length=max_length,
        start_token=start_token,
        end_token=end_token,
        pad_token=pad_token,
        comma_token=_resolve_comma_token(channel_tokenizer),
        max_word_length=max_word_length,
    )


def _group_content_entries(channel_batches: list[list[Any]]) -> list[list[Any]]:
    groups: list[list[Any]] = []
    current_group: list[Any] = []
    current_word_id: int | None = None

    for batch in channel_batches:
        for entry in batch:
            word_id = _entry_word_id(entry)
            if word_id is None or word_id <= 0:
                continue
            if current_group and word_id != current_word_id:
                groups.append(current_group)
                current_group = []
            current_group.append(entry)
            current_word_id = word_id

    if current_group:
        groups.append(current_group)
    return groups


def _find_last_comma_index(content_entries: list[Any], comma_token: int | None) -> int:
    if comma_token is None:
        return -1
    for index in range(len(content_entries) - 1, -1, -1):
        token = _entry_token(content_entries[index])
        if isinstance(token, numbers.Integral) and int(token) == comma_token:
            return index
    return -1


def _finalize_rebatched_batch(
    content_entries: list[Any],
    config: SDTokenRebatchConfig,
) -> list[tuple[object, float]]:
    batch: list[tuple[object, float]] = []
    if config.start_token is not None:
        batch.append((config.start_token, 1.0))

    for entry in content_entries:
        batch.append((_entry_token(entry), _entry_weight(entry)))

    if config.end_token is not None:
        batch.append((config.end_token, 1.0))

    pad_token = config.pad_token if config.pad_token is not None else config.end_token
    while len(batch) < config.max_length and pad_token is not None:
        batch.append((pad_token, 1.0))

    return batch[: config.max_length]


def rebatch_channel_token_weights(
    channel_batches: list[list[Any]],
    *,
    max_length: int,
    start_token: object | None,
    end_token: object | None,
    pad_token: object | None,
    comma_token: int | None,
    max_word_length: int = _DEFAULT_MAX_WORD_LENGTH,
) -> list[list[tuple[object, float]]]:
    config = SDTokenRebatchConfig(
        max_length=int(max_length),
        start_token=start_token,
        end_token=end_token,
        pad_token=pad_token,
        comma_token=comma_token,
        max_word_length=max(1, int(max_word_length or _DEFAULT_MAX_WORD_LENGTH)),
    )

    groups = _group_content_entries(channel_batches)
    if not groups:
        return [_finalize_rebatched_batch([], config)]

    rebatched: list[list[tuple[object, float]]] = []
    content_entries: list[Any] = []
    last_comma = -1

    def _flush_current_batch() -> None:
        nonlocal content_entries, last_comma
        rebatched.append(_finalize_rebatched_batch(content_entries, config))
        content_entries = []
        last_comma = -1

    for group in groups:
        position = 0
        is_large_group = len(group) >= config.max_word_length or len(group) > config.content_capacity
        while position < len(group):
            if len(content_entries) == config.content_capacity:
                if (
                    config.comma_token is not None
                    and last_comma != -1
                    and len(content_entries) - last_comma <= _COMMA_PADDING_BACKTRACK
                ):
                    relocated_entries = content_entries[last_comma + 1 :]
                    content_entries = content_entries[: last_comma + 1]
                    _flush_current_batch()
                    content_entries = list(relocated_entries)
                    last_comma = _find_last_comma_index(content_entries, config.comma_token)
                else:
                    _flush_current_batch()

            remaining_capacity = config.content_capacity - len(content_entries)
            if not is_large_group and len(group) - position > remaining_capacity:
                _flush_current_batch()
                continue

            take_count = remaining_capacity if is_large_group else len(group) - position
            for entry in group[position : position + take_count]:
                content_entries.append(entry)
                token = _entry_token(entry)
                if isinstance(token, numbers.Integral) and config.comma_token is not None and int(token) == config.comma_token:
                    last_comma = len(content_entries) - 1
            position += take_count

    if content_entries or not rebatched:
        rebatched.append(_finalize_rebatched_batch(content_entries, config))

    return rebatched


def _extract_channel_batches(token_payload: Any, channel_key: str | None) -> Any:
    if channel_key is None:
        if isinstance(token_payload, dict):
            if len(token_payload) != 1:
                return None
            return next(iter(token_payload.values()))
        return token_payload
    if isinstance(token_payload, dict):
        return token_payload.get(channel_key)
    return token_payload


def rebatch_weighted_token_payload(
    clip: Any,
    token_payload: Any,
    *,
    channel_key: str | None = None,
) -> Any | None:
    channel_batches = _extract_channel_batches(token_payload, channel_key)
    if not _supports_word_ids(channel_batches):
        return None

    config = _build_rebatch_config(clip, channel_key, channel_batches)
    if config is None:
        return None

    rebatched_channel = rebatch_channel_token_weights(
        channel_batches,
        max_length=config.max_length,
        start_token=config.start_token,
        end_token=config.end_token,
        pad_token=config.pad_token,
        comma_token=config.comma_token,
        max_word_length=config.max_word_length,
    )
    if channel_key is None:
        if isinstance(token_payload, dict):
            only_key = next(iter(token_payload.keys()))
            return token_payload.__class__({only_key: rebatched_channel})
        return rebatched_channel
    return rebatched_channel


def tokenize_with_rookieui_rebatch(clip: Any, text: str) -> Any:
    fallback_tokens = clip.tokenize(text)
    try:
        word_id_tokens = clip.tokenize(text, return_word_ids=True)
    except TypeError:
        return fallback_tokens

    # IMPORTANT: host tokenizer contracts differ across ComfyUI builds; fall back to the stock path instead of hard-failing prompt encode.
    rebatched = rebatch_weighted_token_payload(clip, word_id_tokens)
    return rebatched if rebatched is not None else fallback_tokens


def tokenize_channel_with_rookieui_rebatch(clip: Any, text: str, *, channel_key: str) -> Any:
    fallback_tokens = _extract_channel_batches(clip.tokenize(text), channel_key)
    try:
        word_id_tokens = clip.tokenize(text, return_word_ids=True)
    except TypeError:
        return fallback_tokens

    # IMPORTANT: host tokenizer contracts differ across ComfyUI builds; fall back to the stock channel payload instead of hard-failing prompt encode.
    rebatched = rebatch_weighted_token_payload(clip, word_id_tokens, channel_key=channel_key)
    return rebatched if rebatched is not None else fallback_tokens
