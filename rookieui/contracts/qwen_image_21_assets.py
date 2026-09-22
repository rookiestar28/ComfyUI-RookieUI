from __future__ import annotations

import ntpath

QWEN_IMAGE_21_PROFILE_IDS = frozenset({"qwen_image_21", "qwen_image_21_edit"})

_ROLE_BASENAMES = {
    "diffusion_models": frozenset({
        "qwen_image_2.1_int8_convrot.safetensors",
        "qwen_image_2.1_bf16.safetensors",
    }),
    "text_encoders": frozenset({
        "qwen3vl_8b_int8_convrot.safetensors",
        "qwen3vl_8b_bf16.safetensors",
        "qwen3vl_8b_w4a8.safetensors",
    }),
    "vae": frozenset({"qwen_image_2.1_vae_bf16.safetensors"}),
}


def qwen_image_21_asset_role(selector: str) -> str:
    basename = ntpath.basename(str(selector or "").replace("/", "\\")).lower()
    for role, basenames in _ROLE_BASENAMES.items():
        if basename in basenames:
            return role
    return ""


def require_qwen_image_21_asset_role(selector: str, role: str) -> str:
    if role not in _ROLE_BASENAMES:
        raise ValueError(f"Unsupported Qwen Image 2.1 asset role: {role}.")
    if qwen_image_21_asset_role(selector) != role:
        raise ValueError(f"{role} requires an official Qwen Image 2.1 {role} selector.")
    return selector
