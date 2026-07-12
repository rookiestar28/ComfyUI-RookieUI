from __future__ import annotations

from dataclasses import dataclass

from rookieui.security.request_guard import normalize_option_label


@dataclass(frozen=True)
class Ideogram4ModeContract:
    steps: int
    mu: float
    std: float


IDEOGRAM4_DEFAULT_MODE = "default"
IDEOGRAM4_MODE_CONTRACTS: dict[str, Ideogram4ModeContract] = {
    "quality": Ideogram4ModeContract(steps=48, mu=0.0, std=1.5),
    "default": Ideogram4ModeContract(steps=20, mu=0.0, std=1.75),
    "turbo": Ideogram4ModeContract(steps=12, mu=0.5, std=1.75),
}


def normalize_ideogram4_mode(value: object) -> str:
    normalized = normalize_option_label(value, "ideogram_mode", max_length=16).lower()
    if not normalized:
        return IDEOGRAM4_DEFAULT_MODE
    if normalized not in IDEOGRAM4_MODE_CONTRACTS:
        supported = ", ".join(IDEOGRAM4_MODE_CONTRACTS)
        raise ValueError(f"ideogram_mode must be one of: {supported}.")
    return normalized
