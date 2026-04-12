from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


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
    control_type: str = "All"
    use_mask: bool = False
    allow_preview: bool = False

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)
