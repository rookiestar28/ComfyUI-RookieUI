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


def _normalize_choice_catalog(raw_choices: object) -> list[dict[str, Any]]:
    if not isinstance(raw_choices, list):
        return []
    normalized_entries: list[dict[str, Any]] = []
    for raw_entry in raw_choices:
        if isinstance(raw_entry, dict):
            value = str(raw_entry.get("value", "")).strip()
            label = str(raw_entry.get("label", "") or value).strip()
            aliases = [
                str(alias).strip()
                for alias in raw_entry.get("aliases", []) or []
                if str(alias).strip()
            ]
            allow_partial_match = bool(raw_entry.get("allow_partial_match", False))
            if value and label:
                normalized_entries.append(
                    {
                        "value": value,
                        "label": label,
                        "aliases": aliases,
                        "allow_partial_match": allow_partial_match,
                    }
                )
            continue
        normalized_value = str(raw_entry).strip()
        if normalized_value:
            normalized_entries.append(
                {
                    "value": normalized_value,
                    "label": normalized_value,
                    "aliases": [],
                    "allow_partial_match": False,
                }
            )
    return normalized_entries


def _resolve_choice_token(
    token: str,
    choices: object,
    *,
    field_name: str,
) -> ParsedXYZAxisEntry:
    catalog = _normalize_choice_catalog(choices)
    if not catalog:
        return ParsedXYZAxisEntry(value=token, label=token)

    direct_matches = [
        entry
        for entry in catalog
        if token in {entry["label"], entry["value"], *entry["aliases"]}
    ]
    if len(direct_matches) == 1:
        return ParsedXYZAxisEntry(value=direct_matches[0]["value"], label=direct_matches[0]["label"])

    folded_token = token.casefold()
    folded_matches = [
        entry
        for entry in catalog
        if folded_token
        in {
            entry["label"].casefold(),
            entry["value"].casefold(),
            *[alias.casefold() for alias in entry["aliases"]],
        }
    ]
    if len(folded_matches) == 1:
        return ParsedXYZAxisEntry(value=folded_matches[0]["value"], label=folded_matches[0]["label"])

    partial_matches = [
        entry
        for entry in catalog
        if entry.get("allow_partial_match")
        and folded_token
        and (
            folded_token in entry["label"].casefold()
            or folded_token in entry["value"].casefold()
            or any(folded_token in alias.casefold() for alias in entry["aliases"])
        )
    ]
    if len(partial_matches) == 1:
        return ParsedXYZAxisEntry(value=partial_matches[0]["value"], label=partial_matches[0]["label"])

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


def _parse_prompt_sr_entries(tokens: list[str], *, field_name: str) -> list[ParsedXYZAxisEntry]:
    if not tokens:
        raise ValueError(f"{field_name} must contain at least one value.")
    source = tokens[0]
    parsed_entries: list[ParsedXYZAxisEntry] = []
    for token in tokens:
        _append_checked(
            parsed_entries,
            ParsedXYZAxisEntry(
                value={"source": source, "target": token},
                label=token,
            ),
            field_name=field_name,
        )
    return parsed_entries


def parse_xyz_axis_values(
    raw_value: object,
    axis: XYZPlotAxisContract,
    *,
    choices: object = None,
) -> list[ParsedXYZAxisEntry]:
    field_name = f"{axis.axis_id}_values"
    tokens = _split_csv_tokens(raw_value)
    if not tokens:
        raise ValueError(f"{field_name} must contain at least one value.")

    parsed_entries: list[ParsedXYZAxisEntry] = []
    mode = axis.value_input_mode
    if mode == "prompt_sr_csv":
        return _parse_prompt_sr_entries(tokens, field_name=field_name)

    if mode == "permutation_csv":
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
            resolved = _resolve_choice_token(token, choices, field_name=field_name)
            _append_checked(parsed_entries, resolved, field_name=field_name)
            continue
        if mode == "size_csv":
            size_value = _parse_size_value(token, field_name=field_name)
            label = f'{size_value["width"]}x{size_value["height"]}'
            _append_checked(parsed_entries, ParsedXYZAxisEntry(value=size_value, label=label), field_name=field_name)
            continue
        raise ValueError(f"{field_name} uses an unsupported input mode: {mode}")

    return parsed_entries
