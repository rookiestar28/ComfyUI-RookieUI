from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

CONTROLNET_ADVANCED_WEIGHT_PRESETS = ("balanced", "soft", "strong")


@dataclass(frozen=True)
class NormalizedControlNetAdvancedRequest:
    enabled: bool = False
    weight_preset: str = "balanced"
    layer_weights: list[float] = field(default_factory=list)
    timestep_keyframes: list[dict[str, float]] = field(default_factory=list)
    mask_aware_apply: bool = False

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedControlNetUnit:
    enabled: bool
    module: str
    model: str
    weight: float
    guidance_start: float
    guidance_end: float
    resize_mode: str
    control_mode: str
    processor_res: int
    threshold_a: float
    threshold_b: float
    pixel_perfect: bool
    hr_option: str
    image_asset: str
    mask_asset: str
    source: str
    preprocessed_control_map: bool = False
    control_type: str = "All"
    use_mask: bool = False
    allow_preview: bool = False
    advanced: NormalizedControlNetAdvancedRequest = field(default_factory=NormalizedControlNetAdvancedRequest)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)
