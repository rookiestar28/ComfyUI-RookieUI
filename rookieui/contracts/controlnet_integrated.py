from __future__ import annotations

from rookieui.contracts.controlnet import CONTROLNET_ADVANCED_WEIGHT_PRESETS
from rookieui.services.controlnet_advanced_runtime import CONTROLNET_ADVANCED_RUNTIME_STATE

CONTROLNET_INTEGRATED_CONTRACT_VERSION = "r72-20260412"
CONTROLNET_INTEGRATED_UI_VARIANT = "integrated_sidebar_controlnet"
CONTROLNET_INTEGRATED_DEFAULT_UNIT_COUNT = 3
CONTROLNET_ADVANCED_CONTRACT_VERSION = "r111-20260415"

CONTROLNET_INTEGRATED_CONTROL_TYPE_ORDER = (
    "All",
    "Blur",
    "Canny",
    "Depth",
    "IP-Adapter",
    "Inpaint",
    "Instant-ID",
    "Lineart",
    "MLSD",
    "NormalMap",
    "OpenPose",
    "Reference",
    "Scribble",
    "Segmentation",
    "Shuffle",
    "Sketch",
    "SoftEdge",
    "T2I-Adapter",
    "Tile",
)

CONTROLNET_INTEGRATED_DEFAULTS = {
    "module": "none",
    "model": "",
    "weight": 1.0,
    "guidance_start": 0.0,
    "guidance_end": 1.0,
    "resize_mode": "crop_and_resize",
    "control_mode": "balanced",
    "processor_res": 512,
    "threshold_a": 64.0,
    "threshold_b": 64.0,
    "pixel_perfect": False,
    "hr_option": "both",
}


def build_controlnet_integrated_contract_meta() -> dict[str, object]:
    return {
        "version": CONTROLNET_INTEGRATED_CONTRACT_VERSION,
        "ui_variant": CONTROLNET_INTEGRATED_UI_VARIANT,
        "unit_count": CONTROLNET_INTEGRATED_DEFAULT_UNIT_COUNT,
        "control_type_order": list(CONTROLNET_INTEGRATED_CONTROL_TYPE_ORDER),
        "defaults": dict(CONTROLNET_INTEGRATED_DEFAULTS),
        "advanced_contract": {
            "version": CONTROLNET_ADVANCED_CONTRACT_VERSION,
            "weight_presets": list(CONTROLNET_ADVANCED_WEIGHT_PRESETS),
            "supports_layer_weights": True,
            "supports_timestep_keyframes": True,
            "supports_mask_aware_apply": True,
            "runtime_state": CONTROLNET_ADVANCED_RUNTIME_STATE,
        },
        # IMPORTANT: reserve this extensibility signal so future integrated packs (e.g. ADetailer coupling) can extend without rebreaking base ControlNet contracts.
        "integrated_extension_slots": "reserved",
    }
