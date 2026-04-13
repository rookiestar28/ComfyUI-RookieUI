from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

_RE_ATTENTION = re.compile(
    r"""
\\\(|
\\\)|
\\\[|
\\]|
\\\\|
\\|
\(|
\[|
:\s*([+-]?[.\d]+)\s*\)|
\)|
]|
[^\\()\[\]:]+|
:
""",
    re.X,
)
_RE_BREAK = re.compile(r"\s*\bBREAK\b\s*", re.S)
_RE_AND = re.compile(r"\bAND\b")
_RE_WEIGHT = re.compile(r"^((?:\s|.)*?)(?:\s*:\s*([-+]?(?:\d+\.?|\d*\.\d+)))?\s*$")


@dataclass(frozen=True)
class PromptTextWeight:
    text: str
    weight: float

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScheduledPromptText:
    end_at_step: int
    text: str

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


def parse_prompt_attention(text: str) -> list[PromptTextWeight]:
    """Port of A1111-style prompt attention parsing without Comfy/A1111 runtime deps."""

    result: list[list[object]] = []
    round_brackets: list[int] = []
    square_brackets: list[int] = []

    round_bracket_multiplier = 1.1
    square_bracket_multiplier = 1 / 1.1

    def multiply_range(start_position: int, multiplier: float) -> None:
        for position in range(start_position, len(result)):
            result[position][1] = float(result[position][1]) * multiplier

    for match in _RE_ATTENTION.finditer(text):
        token = match.group(0)
        weight = match.group(1)

        if token.startswith("\\"):
            result.append([token[1:], 1.0])
        elif token == "(":
            round_brackets.append(len(result))
        elif token == "[":
            square_brackets.append(len(result))
        elif weight is not None and round_brackets:
            multiply_range(round_brackets.pop(), float(weight))
        elif token == ")" and round_brackets:
            multiply_range(round_brackets.pop(), round_bracket_multiplier)
        elif token == "]" and square_brackets:
            multiply_range(square_brackets.pop(), square_bracket_multiplier)
        else:
            # CRITICAL: BREAK must remain a tokenizer-side control token for parity work.
            # Do not lower this to graph-only metadata inside the parity engine path.
            parts = re.split(_RE_BREAK, token)
            for index, part in enumerate(parts):
                if index > 0:
                    result.append(["BREAK", -1.0])
                result.append([part, 1.0])

    for position in round_brackets:
        multiply_range(position, round_bracket_multiplier)
    for position in square_brackets:
        multiply_range(position, square_bracket_multiplier)

    if not result:
        result = [["", 1.0]]

    merged: list[PromptTextWeight] = []
    for token, weight in result:
        normalized_token = str(token)
        normalized_weight = float(weight)
        if merged and merged[-1].weight == normalized_weight:
            previous = merged[-1]
            merged[-1] = PromptTextWeight(text=previous.text + normalized_token, weight=normalized_weight)
            continue
        merged.append(PromptTextWeight(text=normalized_token, weight=normalized_weight))
    return merged


def split_weighted_subprompts(prompt_text: str) -> list[PromptTextWeight]:
    subprompts = _RE_AND.split(prompt_text)
    parsed: list[PromptTextWeight] = []
    for subprompt in subprompts:
        match = _RE_WEIGHT.search(subprompt)
        text, weight = match.groups() if match is not None else (subprompt, 1.0)
        parsed.append(PromptTextWeight(text=text, weight=float(weight) if weight is not None else 1.0))
    return parsed


def get_learned_conditioning_prompt_schedules(
    prompts: list[str],
    base_steps: int,
    hires_steps: int | None = None,
    use_old_scheduling: bool = False,
) -> list[list[ScheduledPromptText]]:
    if hires_steps is None or use_old_scheduling:
        int_offset = 0
        flt_offset = 0.0
        steps = base_steps
    else:
        int_offset = base_steps
        flt_offset = 1.0
        steps = hires_steps

    cache: dict[str, list[ScheduledPromptText]] = {}
    schedules: list[list[ScheduledPromptText]] = []
    for prompt in prompts:
        cached = cache.get(prompt)
        if cached is not None:
            schedules.append(cached)
            continue
        boundaries = sorted(
            _collect_schedule_steps(
                prompt,
                steps=steps,
                int_offset=int_offset,
                flt_offset=flt_offset,
                use_old_scheduling=use_old_scheduling,
            )
        )
        prompt_schedule = [
            ScheduledPromptText(
                end_at_step=step,
                text=_render_prompt_at_step(
                    prompt,
                    step=step,
                    steps=steps,
                    int_offset=int_offset,
                    flt_offset=flt_offset,
                    use_old_scheduling=use_old_scheduling,
                ),
            )
            for step in boundaries
        ]
        cache[prompt] = prompt_schedule
        schedules.append(prompt_schedule)
    return schedules


def _collect_schedule_steps(
    text: str,
    *,
    steps: int,
    int_offset: int,
    flt_offset: float,
    use_old_scheduling: bool,
) -> set[int]:
    boundaries = {steps}
    index = 0
    while index < len(text):
        token = text[index]
        if token == "\\":
            index += 2
            continue
        if token != "[":
            index += 1
            continue
        match_index = _find_matching_square_bracket(text, index)
        if match_index is None:
            index += 1
            continue
        inner = text[index + 1 : match_index]
        kind, payload = _detect_bracket_semantics(inner)
        if kind == "alternate":
            boundaries.update(range(1, steps + 1))
            for option in payload:
                boundaries.update(
                    _collect_schedule_steps(
                        option,
                        steps=steps,
                        int_offset=int_offset,
                        flt_offset=flt_offset,
                        use_old_scheduling=use_old_scheduling,
                    )
                )
        elif kind == "schedule":
            before_text, after_text, threshold_text = payload
            threshold_step = _convert_schedule_threshold(
                threshold_text,
                steps=steps,
                int_offset=int_offset,
                flt_offset=flt_offset,
                use_old_scheduling=use_old_scheduling,
            )
            if threshold_step >= 1:
                boundaries.add(threshold_step)
            for branch_text in (before_text, after_text):
                boundaries.update(
                    _collect_schedule_steps(
                        branch_text,
                        steps=steps,
                        int_offset=int_offset,
                        flt_offset=flt_offset,
                        use_old_scheduling=use_old_scheduling,
                    )
                )
        else:
            boundaries.update(
                _collect_schedule_steps(
                    inner,
                    steps=steps,
                    int_offset=int_offset,
                    flt_offset=flt_offset,
                    use_old_scheduling=use_old_scheduling,
                )
            )
        index = match_index + 1
    return boundaries


def _render_prompt_at_step(
    text: str,
    *,
    step: int,
    steps: int,
    int_offset: int,
    flt_offset: float,
    use_old_scheduling: bool,
) -> str:
    rendered: list[str] = []
    index = 0
    while index < len(text):
        token = text[index]
        if token == "\\" and index + 1 < len(text):
            rendered.append(text[index : index + 2])
            index += 2
            continue
        if token != "[":
            rendered.append(token)
            index += 1
            continue
        match_index = _find_matching_square_bracket(text, index)
        if match_index is None:
            rendered.append(token)
            index += 1
            continue
        inner = text[index + 1 : match_index]
        kind, payload = _detect_bracket_semantics(inner)
        if kind == "alternate":
            options = payload
            selected = options[(step - 1) % len(options)] if options else ""
            rendered.append(
                _render_prompt_at_step(
                    selected,
                    step=step,
                    steps=steps,
                    int_offset=int_offset,
                    flt_offset=flt_offset,
                    use_old_scheduling=use_old_scheduling,
                )
            )
        elif kind == "schedule":
            before_text, after_text, threshold_text = payload
            threshold_step = _convert_schedule_threshold(
                threshold_text,
                steps=steps,
                int_offset=int_offset,
                flt_offset=flt_offset,
                use_old_scheduling=use_old_scheduling,
            )
            selected = before_text if step <= threshold_step else after_text
            rendered.append(
                _render_prompt_at_step(
                    selected,
                    step=step,
                    steps=steps,
                    int_offset=int_offset,
                    flt_offset=flt_offset,
                    use_old_scheduling=use_old_scheduling,
                )
            )
        else:
            rendered.append(
                "["
                + _render_prompt_at_step(
                    inner,
                    step=step,
                    steps=steps,
                    int_offset=int_offset,
                    flt_offset=flt_offset,
                    use_old_scheduling=use_old_scheduling,
                )
                + "]"
            )
        index = match_index + 1
    return "".join(rendered)


def _find_matching_square_bracket(text: str, start_index: int) -> int | None:
    depth = 0
    index = start_index
    while index < len(text):
        token = text[index]
        if token == "\\":
            index += 2
            continue
        if token == "[":
            depth += 1
        elif token == "]":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _detect_bracket_semantics(inner: str) -> tuple[str, tuple[str, ...] | list[str]]:
    alternate_parts = _split_top_level(inner, "|")
    if len(alternate_parts) > 1:
        return "alternate", alternate_parts

    schedule_parts = _split_top_level(inner, ":")
    if len(schedule_parts) in {2, 3} and _looks_like_schedule_threshold(schedule_parts[-1]):
        if len(schedule_parts) == 2:
            return "schedule", ("", schedule_parts[0], schedule_parts[1])
        return "schedule", (schedule_parts[0], schedule_parts[1], schedule_parts[2])
    return "literal", ()


def _split_top_level(text: str, separator: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    round_depth = 0
    square_depth = 0
    index = 0
    while index < len(text):
        token = text[index]
        if token == "\\" and index + 1 < len(text):
            current.append(text[index : index + 2])
            index += 2
            continue
        if token == "(":
            round_depth += 1
        elif token == ")" and round_depth > 0:
            round_depth -= 1
        elif token == "[":
            square_depth += 1
        elif token == "]" and square_depth > 0:
            square_depth -= 1
        if token == separator and round_depth == 0 and square_depth == 0:
            parts.append("".join(current))
            current = []
            index += 1
            continue
        current.append(token)
        index += 1
    parts.append("".join(current))
    return parts


def _looks_like_schedule_threshold(raw_threshold: str) -> bool:
    try:
        float(raw_threshold.strip())
    except ValueError:
        return False
    return True


def _convert_schedule_threshold(
    raw_threshold: str,
    *,
    steps: int,
    int_offset: int,
    flt_offset: float,
    use_old_scheduling: bool,
) -> int:
    value = float(raw_threshold)
    if use_old_scheduling:
        value = value * steps if value < 1 else value
    else:
        if "." in raw_threshold:
            value = (value - flt_offset) * steps
        else:
            value = value - int_offset
    return min(steps, int(value))
