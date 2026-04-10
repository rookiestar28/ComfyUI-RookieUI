from __future__ import annotations

import re

_ASSET_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def validate_asset_identifier(raw_value: str) -> str:
    if not isinstance(raw_value, str):
        raise TypeError("Asset identifiers must be strings.")

    candidate = raw_value.strip()
    # CRITICAL: asset identifiers stay logical-only; accepting path separators
    # here would let later features blur the boundary between ids and paths.
    if (
        not candidate
        or "/" in candidate
        or "\\" in candidate
        or ".." in candidate
        or not _ASSET_IDENTIFIER_RE.fullmatch(candidate)
    ):
        raise ValueError("Asset identifier must be a safe logical id.")

    return candidate


def normalize_metadata_text(raw_value: str, *, max_length: int = 120) -> str:
    if not isinstance(raw_value, str):
        raise TypeError("Metadata values must be strings.")

    if max_length < 1:
        raise ValueError("max_length must be positive.")

    normalized = " ".join(raw_value.replace("\x00", " ").split())
    return normalized[:max_length].rstrip()
