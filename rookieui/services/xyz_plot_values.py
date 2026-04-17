from __future__ import annotations

import csv
import io
import itertools
import re
from dataclasses import dataclass
from typing import Any

from rookieui.contracts.xyz_plot import XYZPlotAxisContract
from rookieui.services.coercion import coerce_float, coerce_int

_INT_RANGE_STEP_RE = re.compile(r"\s*([+-]?\d+)\s*-\s*([+-]?\d+)(?:\s*\(([+-]?\d+)\s*\))?\s*")
_FLOAT_RANGE_STEP_RE = re.compile(r"\s*([+-]?\d+(?:\.\d+)?)\s*-\s*([+-]?\d+(?:\.\d+)?)(?:\s*\(([+-]?\d+(?:\.\d+)?)\s*\))?\s*")
_INT_RANGE_COUNT_RE = re.compile(r"\s*([+-]?\d+)\s*-\s*([+-]?\d+)(?:\s*\[(\d+)\s*])?\s*")
_FLOAT_RANGE_COUNT_RE = re.compile(r"\s*([+-]?\d+(?:\.\d+)?)\s*-\s*([+-]?\d+(?:\.\d+)?)(?:\s*\[(\d+(?:\.\d+)?)\s*])?\s*")
_SIZE_VALUE_RE = re.compile(r"^\s*(\d+)\s*[xX]\s*(\d+)\s*$")

XYZ_PLOT_MAX_AXIS_VALUES = 128


@dataclass(frozen=True)
class ParsedXYZAxisEntry:
    value: Any
    label: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "label": self.label,
        }


def _split_csv_tokens(raw_value: object) -> list[str]:
    raw_text = str(raw_value or "").strip()
    if not raw_text:
        return []
    reader = csv.reader(io.StringIO(raw_text), skipinitialspace=True)
    try:
        row = next(reader)
    except StopIteration:
        return []
    return [token.strip() for token in row if token and token.strip()]


def _append_checked(entries: list[ParsedXYZAxisEntry], entry: ParsedXYZAxisEntry, *, field_name: str) -> None:
    entries.append(entry)
    if len(entries) > XYZ_PLOT_MAX_AXIS_VALUES:
        raise ValueError(f"{field_name} expands to too many values (max {XYZ_PLOT_MAX_AXIS_VALUES}).")


def _expand_int_range(token: str, *, field_name: str) -> list[int]:
    step_match = _INT_RANGE_STEP_RE.fullmatch(token)
    if step_match:
        start = coerce_int(step_match.group(1), field_name, via_str=True)
        end = coerce_int(step_match.group(2), field_name, via_str=True)
        raw_step = step_match.group(3)
        step = coerce_int(raw_step, field_name, via_str=True) if raw_step else (1 if end >= start else -1)
        if step == 0:
            raise ValueError(f"{field_name} range step must not be zero.")
        if start < end and step < 0:
            raise ValueError(f"{field_name} range step must be positive for ascending ranges.")
        if start > end and step > 0:
            raise ValueError(f"{field_name} range step must be negative for descending ranges.")
        return list(range(start, end + (1 if step > 0 else -1), step))

    count_match = _INT_RANGE_COUNT_RE.fullmatch(token)
    if count_match:
        start = coerce_int(count_match.group(1), field_name, via_str=True)
        end = coerce_int(count_match.group(2), field_name, via_str=True)
        count = coerce_int(count_match.group(3), field_name, via_str=True, default=0) or abs(end - start) + 1
        if count <= 0:
            raise ValueError(f"{field_name} range count must be greater than zero.")
        if count == 1:
            return [start]
        if count == abs(end - start) + 1:
            step = 1 if end >= start else -1
            return list(range(start, end + step, step))
        return [round(start + ((end - start) * index / (count - 1))) for index in range(count)]

    return [coerce_int(token, field_name, via_str=True)]


def _expand_float_range(token: str, *, field_name: str) -> list[float]:
    step_match = _FLOAT_RANGE_STEP_RE.fullmatch(token)
    if step_match:
        start = coerce_float(step_match.group(1), field_name, via_str=True, precision=6)
        end = coerce_float(step_match.group(2), field_name, via_str=True, precision=6)
        raw_step = step_match.group(3)
        step = (
            coerce_float(raw_step, field_name, via_str=True, precision=6)
            if raw_step
            else (1.0 if end >= start else -1.0)
        )
        if step == 0:
            raise ValueError(f"{field_name} range step must not be zero.")
        if start < end and step < 0:
            raise ValueError(f"{field_name} range step must be positive for ascending ranges.")
        if start > end and step > 0:
            raise ValueError(f"{field_name} range step must be negative for descending ranges.")
        values: list[float] = []
        current = start
        epsilon = abs(step) / 1000.0
        if step > 0:
            while current <= end + epsilon:
                values.append(round(current, 6))
                current += step
        else:
            while current >= end - epsilon:
                values.append(round(current, 6))
                current += step
        return values

    count_match = _FLOAT_RANGE_COUNT_RE.fullmatch(token)
    if count_match:
        start = coerce_float(count_match.group(1), field_name, via_str=True, precision=6)
        end = coerce_float(count_match.group(2), field_name, via_str=True, precision=6)
        raw_count = count_match.group(3)
        count = int(float(raw_count)) if raw_count else 0
        if count <= 0:
            span = abs(end - start)
            count = int(round(span)) + 1 if span >= 1.0 else 2
        if count <= 0:
            raise ValueError(f"{field_name} range count must be greater than zero.")
        if count == 1:
            return [round(start, 6)]
        return [round(start + ((end - start) * index / (count - 1)), 6) for index in range(count)]

    return [coerce_float(token, field_name, via_str=True, precision=6)]


def _resolve_choice_token(token: str, choices: list[str], *, field_name: str) -> str:
    if not choices:
        return token
    direct_match = [choice for choice in choices if choice == token]
    if len(direct_match) == 1:
        return direct_match[0]
    folded_token = token.casefold()
    folded_matches = [choice for choice in choices if choice.casefold() == folded_token]
    if len(folded_matches) == 1:
        return folded_matches[0]
    raise ValueError(f"{field_name} contains an unknown choice: {token}")


def _parse_size_value(token: str, *, field_name: str) -> dict[str, int]:
    match = _SIZE_VALUE_RE.fullmatch(token)
    if not match:
        raise ValueError(f"{field_name} size values must use WIDTHxHEIGHT syntax.")
    width = coerce_int(match.group(1), field_name, via_str=True)
    height = coerce_int(match.group(2), field_name, via_str=True)
    if width <= 0 or height <= 0:
        raise ValueError(f"{field_name} size values must be positive.")
    return {
        "width": width,
        "height": height,
    }


def _parse_csv_pairs(token: str, *, field_name: str) -> dict[str, str]:
    for separator in ("->", "=>", "|"):
        if separator in token:
            left, right = token.split(separator, 1)
            source = left.strip()
            target = right.strip()
            if not source or not target:
                break
            return {
                "source": source,
                "target": target,
            }
    raise ValueError(f"{field_name} pair values must use SOURCE->TARGET syntax.")


def parse_xyz_axis_values(
    raw_value: object,
    axis: XYZPlotAxisContract,
    *,
    choices: list[str] | None = None,
) -> list[ParsedXYZAxisEntry]:
    field_name = f"{axis.axis_id}_values"
    tokens = _split_csv_tokens(raw_value)
    if not tokens:
        raise ValueError(f"{field_name} must contain at least one value.")

    parsed_entries: list[ParsedXYZAxisEntry] = []
    mode = axis.value_input_mode
    available_choices = [choice for choice in (choices or []) if isinstance(choice, str) and choice.strip()]

    if mode == "permutation_csv":
        if len(tokens) < 2:
            raise ValueError(f"{field_name} must contain at least two tokens for permutation mode.")
        for permutation in itertools.permutations(tokens):
            label = ", ".join(part.strip() for part in permutation if part.strip())
            _append_checked(parsed_entries, ParsedXYZAxisEntry(value=list(permutation), label=label), field_name=field_name)
        return parsed_entries

    for token in tokens:
        if mode == "int_csv_or_range":
            for value in _expand_int_range(token, field_name=field_name):
                _append_checked(parsed_entries, ParsedXYZAxisEntry(value=value, label=str(value)), field_name=field_name)
            continue
        if mode == "float_csv_or_range":
            for value in _expand_float_range(token, field_name=field_name):
                _append_checked(parsed_entries, ParsedXYZAxisEntry(value=value, label=str(value)), field_name=field_name)
            continue
        if mode == "choices_or_csv":
            resolved = _resolve_choice_token(token, available_choices, field_name=field_name)
            _append_checked(parsed_entries, ParsedXYZAxisEntry(value=resolved, label=resolved), field_name=field_name)
            continue
        if mode == "size_csv":
            size_value = _parse_size_value(token, field_name=field_name)
            label = f'{size_value["width"]}x{size_value["height"]}'
            _append_checked(parsed_entries, ParsedXYZAxisEntry(value=size_value, label=label), field_name=field_name)
            continue
        if mode == "csv_pairs":
            pair_value = _parse_csv_pairs(token, field_name=field_name)
            label = f'{pair_value["source"]}->{pair_value["target"]}'
            _append_checked(parsed_entries, ParsedXYZAxisEntry(value=pair_value, label=label), field_name=field_name)
            continue
        raise ValueError(f"{field_name} uses an unsupported input mode: {mode}")

    return parsed_entries
