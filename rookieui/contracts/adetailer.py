from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from rookieui.contracts.controlnet import NormalizedControlNetAdvancedRequest
from rookieui.contracts.controlnet_integrated import build_controlnet_integrated_contract_meta

ADETAILER_INTEGRATED_CONTRACT_VERSION = "r74f77-20260414"
ADETAILER_INTEGRATED_UI_VARIANT = "a1111_integrated_detailer"
ADETAILER_INTEGRATED_DEFAULT_UNIT_COUNT = 4
ADETAILER_PROMPT_TOKENS = ("[PROMPT]", "[SEP]", "[SKIP]")
ADETAILER_CONTROLNET_MODES = ("none", "passthrough", "custom")
ADETAILER_DETECTOR_PROVIDER_FAMILIES = ("none", "ultralytics_bbox", "ultralytics_segm", "mediapipe_face")
ADETAILER_MASK_FILTER_METHODS = ("Area", "Confidence")
ADETAILER_MASK_MERGE_MODES = ("None", "Merge", "Merge and Invert")
ADETAILER_MEDIAPIPE_DETECTORS = (
    "mediapipe_face_short",
    "mediapipe_face_full",
    "mediapipe_face_mesh",
    "mediapipe_face_mesh_eyes_only",
)
ADETAILER_FALLBACK_ULTRALYTICS_DETECTORS = (
    "face_yolov8n.pt",
    "face_yolov8n_v2.pt",
    "face_yolov8s.pt",
    "hand_yolov8n.pt",
    "hand_yolov8s.pt",
    "person_yolov8n-seg.pt",
    "person_yolov8s-seg.pt",
    "person_yolov8m-seg.pt",
    "deepfashion2_yolov8s-seg.pt",
    "yolov8x-worldv2.pt",
)
ADETAILER_UNIT_DEFAULTS = {
    "detector": "None",
    "detector_classes": "",
    "confidence": 0.3,
    "mask_filter_method": "Area",
    "mask_k": 0,
    "mask_min_ratio": 0.0,
    "mask_max_ratio": 1.0,
    "x_offset": 0,
    "y_offset": 0,
    "dilate_erode": 4,
    "mask_merge_mode": "None",
    "mask_blur": 4,
    "denoising_strength": 0.4,
    "inpaint_only_masked": True,
    "inpaint_padding": 32,
    "use_inpaint_size": False,
    "inpaint_width": 512,
    "inpaint_height": 512,
    "use_steps": False,
    "steps": 28,
    "use_cfg_scale": False,
    "cfg_scale": 7.0,
    "use_checkpoint": False,
    "checkpoint_name": "Use same checkpoint",
    "use_vae": False,
    "vae_name": "Use same VAE",
    "use_sampler": False,
    "sampler_name": "DPM++ 2M Karras",
    "scheduler_name": "Use same scheduler",
    "use_noise_multiplier": False,
    "noise_multiplier": 1.0,
    "use_clip_skip": False,
    "clip_skip": 1,
    "restore_face": False,
}


def build_adetailer_integrated_contract_meta() -> dict[str, object]:
    return {
        "version": ADETAILER_INTEGRATED_CONTRACT_VERSION,
        "ui_variant": ADETAILER_INTEGRATED_UI_VARIANT,
        "unit_count": ADETAILER_INTEGRATED_DEFAULT_UNIT_COUNT,
        "prompt_tokens": list(ADETAILER_PROMPT_TOKENS),
        "controlnet_modes": list(ADETAILER_CONTROLNET_MODES),
        "detector_provider_families": list(ADETAILER_DETECTOR_PROVIDER_FAMILIES),
        "detector_result_contract": "rookieui_detection_regions_v1",
        "controlnet_advanced_contract": dict(build_controlnet_integrated_contract_meta()["advanced_contract"]),
        "mask_filter_methods": list(ADETAILER_MASK_FILTER_METHODS),
        "mask_merge_modes": list(ADETAILER_MASK_MERGE_MODES),
        "defaults": dict(ADETAILER_UNIT_DEFAULTS),
    }


@dataclass(frozen=True)
class NormalizedADetailerControlNetRequest:
    mode: str = "none"
    model: str = ""
    module: str = "None"
    weight: float = 1.0
    guidance_start: float = 0.0
    guidance_end: float = 1.0
    advanced: NormalizedControlNetAdvancedRequest = field(default_factory=NormalizedControlNetAdvancedRequest)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedADetailerUnitRequest:
    enabled: bool = True
    detector: str = "None"
    detector_family: str = "none"
    detector_classes: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    confidence: float = 0.3
    mask_filter_method: str = "Area"
    mask_k: int = 0
    mask_min_ratio: float = 0.0
    mask_max_ratio: float = 1.0
    x_offset: int = 0
    y_offset: int = 0
    dilate_erode: int = 4
    mask_merge_mode: str = "None"
    mask_blur: int = 4
    denoising_strength: float = 0.4
    inpaint_only_masked: bool = True
    inpaint_padding: int = 32
    use_inpaint_size: bool = False
    inpaint_width: int = 512
    inpaint_height: int = 512
    use_steps: bool = False
    steps: int = 28
    use_cfg_scale: bool = False
    cfg_scale: float = 7.0
    use_checkpoint: bool = False
    checkpoint_name: str = "Use same checkpoint"
    use_vae: bool = False
    vae_name: str = "Use same VAE"
    use_sampler: bool = False
    sampler_name: str = "DPM++ 2M Karras"
    scheduler_name: str = "Use same scheduler"
    use_noise_multiplier: bool = False
    noise_multiplier: float = 1.0
    use_clip_skip: bool = False
    clip_skip: int = 1
    restore_face: bool = False
    prompt_uses_main: bool = True
    negative_prompt_uses_main: bool = True
    refinement_context_id: str = ""
    controlnet: NormalizedADetailerControlNetRequest = field(default_factory=NormalizedADetailerControlNetRequest)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedADetailerRequest:
    enabled: bool = False
    skip_img2img: bool = False
    units: list[NormalizedADetailerUnitRequest] = field(default_factory=list)
    warning_codes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)
