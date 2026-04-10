from __future__ import annotations

import re
import secrets

MAX_PROMPT_LENGTH = 12000
MAX_SELECTOR_LENGTH = 255
MAX_CLIENT_ID_LENGTH = 128
MAX_INFOTEXT_LENGTH = 32000
RANDOM_SEED_SENTINEL = -1
MIN_SEED = RANDOM_SEED_SENTINEL
MAX_SEED = (2**63) - 1

_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def _coerce_text(raw_value: object, field_name: str) -> str:
    if raw_value is None:
        return ""
    if not isinstance(raw_value, str):
        raise ValueError(f"{field_name} must be a string.")
    return raw_value


def normalize_prompt_text(
    raw_value: object,
    field_name: str,
    *,
    required: bool = False,
    max_length: int = MAX_PROMPT_LENGTH,
) -> str:
    candidate = _coerce_text(raw_value, field_name)
    # IMPORTANT: prompt normalization must stay newline-preserving; collapsing
    # lines here would change A1111-style prompt semantics.
    normalized = candidate.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "").strip()
    if required and not normalized:
        raise ValueError(f"{field_name} is required.")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters.")
    return normalized


def normalize_host_selector(
    raw_value: object,
    field_name: str,
    *,
    default_value: str,
) -> str:
    candidate = _coerce_text(raw_value, field_name).replace("\x00", "").strip()
    if not candidate:
        return default_value
    _validate_logical_selector(candidate, field_name)
    return candidate.replace("\\", "/")


def _validate_logical_selector(candidate: str, field_name: str) -> None:
    if len(candidate) > MAX_SELECTOR_LENGTH:
        raise ValueError(f"{field_name} must be at most {MAX_SELECTOR_LENGTH} characters.")
    # CRITICAL: host selectors must stay logical-relative; absolute or traversal
    # values would turn Comfy inventory selectors into arbitrary path input.
    if candidate.startswith(("/", "\\")) or _WINDOWS_DRIVE_RE.match(candidate):
        raise ValueError(f"{field_name} must be a logical host selector.")

    normalized = candidate.replace("\\", "/")
    segments = normalized.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError(f"{field_name} must be a logical host selector.")
    if any(any(ord(char) < 32 for char in segment) for segment in segments):
        raise ValueError(f"{field_name} must not contain control characters.")


def build_host_selector_key(selector: str) -> str:
    return selector.replace("\\", "/").strip()


def resolve_inventory_selector(
    raw_value: object,
    field_name: str,
    *,
    default_value: str,
    inventory_selectors: list[str] | None = None,
    strict_match: bool = False,
) -> str:
    candidate = _coerce_text(raw_value, field_name).replace("\x00", "").strip()
    if not candidate:
        return default_value

    _validate_logical_selector(candidate, field_name)

    inventory_values = [value for value in (inventory_selectors or []) if isinstance(value, str) and value.strip()]
    if candidate in inventory_values:
        return candidate

    normalized_candidate = build_host_selector_key(candidate)
    if normalized_candidate in inventory_values:
        return normalized_candidate

    # IMPORTANT: Comfy host inventories may keep Windows-style separators; resolve slash-normalized imports back to the exact host entry.
    direct_matches = [
        value for value in inventory_values if build_host_selector_key(value) == normalized_candidate
    ]
    if len(direct_matches) == 1:
        return direct_matches[0]

    folded_candidate = normalized_candidate.lower()
    folded_matches = [
        value for value in inventory_values if build_host_selector_key(value).lower() == folded_candidate
    ]
    if len(folded_matches) == 1:
        return folded_matches[0]

    if strict_match and inventory_values:
        raise ValueError(f"{field_name} must match a host inventory entry.")

    return normalized_candidate


def normalize_option_label(
    raw_value: object,
    field_name: str,
    *,
    max_length: int = 80,
) -> str:
    candidate = _coerce_text(raw_value, field_name).replace("\x00", "").strip()
    if len(candidate) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters.")
    if any(ord(char) < 32 for char in candidate):
        raise ValueError(f"{field_name} must not contain control characters.")
    return candidate


def normalize_client_id(raw_value: object) -> str | None:
    if raw_value in (None, ""):
        return None
    candidate = normalize_option_label(raw_value, "client_id", max_length=MAX_CLIENT_ID_LENGTH)
    if not candidate:
        return None
    if any(char.isspace() for char in candidate):
        raise ValueError("client_id must not contain whitespace.")
    return candidate


def normalize_infotext(raw_value: object) -> str:
    return normalize_prompt_text(
        raw_value,
        "infotext",
        required=True,
        max_length=MAX_INFOTEXT_LENGTH,
    )


def validate_seed_range(seed: int, *, field_name: str = "seed") -> int:
    if seed < MIN_SEED or seed > MAX_SEED:
        raise ValueError(f"{field_name} must be -1 or between 0 and {MAX_SEED}.")
    return seed


def resolve_execution_seed(seed: int, *, field_name: str = "seed") -> int:
    validate_seed_range(seed, field_name=field_name)
    if seed == RANDOM_SEED_SENTINEL:
        # CRITICAL: A1111-style random seed sentinel must be resolved before Comfy KSampler validation, which rejects negative seeds.
        return secrets.randbelow(MAX_SEED + 1)
    return seed
