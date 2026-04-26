from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import re
from typing import Any, Iterable

_MAX_TOKEN_TEXT_LENGTH = 4096
_EXPLICIT_WEIGHT_RE = re.compile(r"^\((?P<body>.+):(?P<weight>[+-]?(?:\d+(?:\.\d+)?|\.\d+))\)$")


@dataclass(frozen=True)
class PromptWorkbenchToken:
    id: str
    raw_text: str
    normalized_text: str
    scope: str
    order_index: int
    disabled: bool = False
    selected: bool = False
    translated_text: str = ""
    keyword_family: str = "plain"
    weight: float | None = None

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_scope(scope: object) -> str:
    normalized = str(scope or "prompt").strip().lower()
    if normalized in {"negative", "negative_prompt", "img2img_negative", "txt2img_negative"}:
        return "negative"
    return "prompt"


def _normalize_token_text(value: object) -> str:
    return str(value or "").strip()[:_MAX_TOKEN_TEXT_LENGTH]


def _build_token_id(*, scope: str, order_index: int, raw_text: str) -> str:
    digest = hashlib.sha1(f"{scope}:{order_index}:{raw_text}".encode("utf-8")).hexdigest()[:10]
    return f"pw-{scope}-{order_index}-{digest}"


def _split_prompt_token_text(text: object) -> list[str]:
    source = str(text or "")
    tokens: list[str] = []
    current: list[str] = []
    escaped = False
    paren_depth = 0
    bracket_depth = 0
    angle_depth = 0

    for char in source:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            current.append(char)
            escaped = True
            continue
        if char == "<":
            angle_depth += 1
            current.append(char)
            continue
        if char == ">" and angle_depth:
            angle_depth -= 1
            current.append(char)
            continue
        if char == "(" and angle_depth == 0:
            paren_depth += 1
            current.append(char)
            continue
        if char == ")" and paren_depth and angle_depth == 0:
            paren_depth -= 1
            current.append(char)
            continue
        if char == "[" and angle_depth == 0:
            bracket_depth += 1
            current.append(char)
            continue
        if char == "]" and bracket_depth and angle_depth == 0:
            bracket_depth -= 1
            current.append(char)
            continue
        if char in {",", "\n"} and paren_depth == 0 and bracket_depth == 0 and angle_depth == 0:
            token = _normalize_token_text("".join(current))
            if token:
                tokens.append(token)
            current = []
            continue
        current.append(char)

    token = _normalize_token_text("".join(current))
    if token:
        tokens.append(token)
    return tokens


def _extract_weight(raw_text: str) -> float | None:
    match = _EXPLICIT_WEIGHT_RE.match(raw_text)
    if not match:
        return None
    try:
        return float(match.group("weight"))
    except ValueError:
        return None


def classify_prompt_workbench_token(raw_text: object) -> str:
    normalized = _normalize_token_text(raw_text)
    lower = normalized.lower()
    if lower == "break":
        return "break"
    if lower == "and" or lower.startswith("and "):
        return "and"
    if lower.startswith("<lora:"):
        return "lora"
    if lower.startswith("<lyco:") or lower.startswith("<lycoris:"):
        return "lycoris"
    if lower.startswith("embedding:"):
        return "embedding"
    if lower.startswith("[") and lower.endswith("]") and ":" in lower:
        return "schedule"
    if _extract_weight(normalized) is not None or (normalized.startswith("(") and normalized.endswith(")")):
        return "weighted"
    return "plain"


def parse_prompt_workbench_tokens(text: object, *, scope: object = "prompt") -> tuple[PromptWorkbenchToken, ...]:
    normalized_scope = _normalize_scope(scope)
    tokens: list[PromptWorkbenchToken] = []
    for index, raw_text in enumerate(_split_prompt_token_text(text)):
        normalized_text = _normalize_token_text(raw_text)
        tokens.append(
            PromptWorkbenchToken(
                id=_build_token_id(scope=normalized_scope, order_index=index, raw_text=normalized_text),
                raw_text=normalized_text,
                normalized_text=normalized_text.lower(),
                scope=normalized_scope,
                order_index=index,
                keyword_family=classify_prompt_workbench_token(normalized_text),
                weight=_extract_weight(normalized_text),
            )
        )
    return tuple(tokens)


def rebuild_prompt_from_tokens(tokens: Iterable[PromptWorkbenchToken]) -> str:
    return ", ".join(token.raw_text for token in tokens if not token.disabled and token.raw_text.strip())


def copy_prompt_workbench_token(tokens: Iterable[PromptWorkbenchToken], token_id: object) -> str:
    normalized_id = str(token_id or "").strip()
    for token in tokens:
        if token.id == normalized_id:
            return token.raw_text
    return ""


def set_prompt_workbench_token_disabled(
    tokens: Iterable[PromptWorkbenchToken],
    token_id: object,
    *,
    disabled: bool,
) -> tuple[PromptWorkbenchToken, ...]:
    normalized_id = str(token_id or "").strip()
    return tuple(replace(token, disabled=disabled) if token.id == normalized_id else token for token in tokens)


def delete_prompt_workbench_token(
    tokens: Iterable[PromptWorkbenchToken],
    token_id: object,
) -> tuple[PromptWorkbenchToken, ...]:
    normalized_id = str(token_id or "").strip()
    return _reindex_tokens(token for token in tokens if token.id != normalized_id)


def move_prompt_workbench_token(
    tokens: Iterable[PromptWorkbenchToken],
    token_id: object,
    *,
    direction: str,
) -> tuple[PromptWorkbenchToken, ...]:
    token_list = list(tokens)
    normalized_id = str(token_id or "").strip()
    index = next((idx for idx, token in enumerate(token_list) if token.id == normalized_id), -1)
    if index < 0:
        return tuple(token_list)
    offset = -1 if direction == "up" else 1
    next_index = index + offset
    if next_index < 0 or next_index >= len(token_list):
        return tuple(token_list)
    token_list[index], token_list[next_index] = token_list[next_index], token_list[index]
    return _reindex_tokens(token_list)


def adjust_prompt_workbench_token_weight(raw_text: object, *, delta: float) -> str:
    normalized = _normalize_token_text(raw_text)
    if not normalized:
        return ""
    match = _EXPLICIT_WEIGHT_RE.match(normalized)
    if match:
        next_weight = max(0.0, float(match.group("weight")) + delta)
        return f"({match.group('body')}:{_format_weight(next_weight)})"
    next_weight = 1.1 if delta >= 0 else 0.9
    return f"({normalized}:{_format_weight(next_weight)})"


def adjust_prompt_workbench_token_weight_by_id(
    tokens: Iterable[PromptWorkbenchToken],
    token_id: object,
    *,
    delta: float,
) -> tuple[PromptWorkbenchToken, ...]:
    normalized_id = str(token_id or "").strip()
    adjusted: list[PromptWorkbenchToken] = []
    for token in tokens:
        if token.id != normalized_id:
            adjusted.append(token)
            continue
        next_raw_text = adjust_prompt_workbench_token_weight(token.raw_text, delta=delta)
        adjusted.append(
            replace(
                token,
                raw_text=next_raw_text,
                normalized_text=next_raw_text.lower(),
                keyword_family=classify_prompt_workbench_token(next_raw_text),
                weight=_extract_weight(next_raw_text),
            )
        )
    return tuple(adjusted)


def _format_weight(value: float) -> str:
    rounded = round(value, 2)
    text = f"{rounded:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def _reindex_tokens(tokens: Iterable[PromptWorkbenchToken]) -> tuple[PromptWorkbenchToken, ...]:
    reindexed: list[PromptWorkbenchToken] = []
    for index, token in enumerate(tokens):
        reindexed.append(
            replace(
                token,
                id=_build_token_id(scope=token.scope, order_index=index, raw_text=token.raw_text),
                order_index=index,
            )
        )
    return tuple(reindexed)
