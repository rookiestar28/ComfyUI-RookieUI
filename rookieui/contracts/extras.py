from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

EXTRAS_CONTRACT_VERSION = "r206f207f208f209-20260508"
EXTRAS_CONTRACT_SURFACE = "extras_run"


def build_extras_contract_meta() -> dict[str, object]:
    return {
        "version": EXTRAS_CONTRACT_VERSION,
        "surface": EXTRAS_CONTRACT_SURFACE,
        "execution_mode": "synchronous_postprocess",
        "supported_modes": ["single_image", "batch"],
        "supports_color_correction": True,
        "face_restoration_behavior": "runtime_adapter_or_guarded_warning",
    }


@dataclass(frozen=True)
class ExtrasRequest:
    mode: str = "single_image"
    image_asset: str = ""
    image_data: str = ""
    batch_assets: list[str] = field(default_factory=list)
    batch_images: list[str] = field(default_factory=list)
    upscale_enabled: bool = True
    scale_mode: str = "scale_by"
    scale_by: float = 2.0
    target_width: int = 1024
    target_height: int = 1024
    upscaler_1: str = "None"
    upscaler_2: str = "None"
    upscaler_2_visibility: float = 0.0
    color_correction: bool = False
    face_restoration: str = "none"
    codeformer_weight: float = 0.5

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedExtrasRequest:
    mode: str
    source_assets: list[str]
    upscale_enabled: bool
    scale_mode: str
    scale_by: float
    target_width: int
    target_height: int
    upscaler_1: str
    upscaler_2: str
    upscaler_2_visibility: float
    color_correction: bool
    face_restoration: str
    codeformer_weight: float
    warnings: list[str] = field(default_factory=list)
    applied_defaults: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExtrasExecutionResult:
    mode: str
    normalized_request: dict[str, Any]
    output_assets: list[str]
    preview_asset: str
    preview_data_url: str
    warnings: list[str] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)
