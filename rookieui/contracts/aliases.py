from __future__ import annotations

TEXT_ENCODER_LOCKED_PROFILES = frozenset({"sd15", "sdxl", "pony", "illustrious", "noob"})
HIRES_UPSCALE_METHODS = frozenset({"nearest-exact", "bilinear", "area", "bicubic", "bislerp"})

RESIZE_MODE_ALIASES = {
    "just resize": "just_resize",
    "just_resize": "just_resize",
    "crop and resize": "crop_and_resize",
    "crop_and_resize": "crop_and_resize",
    "resize and fill": "resize_and_fill",
    "resize_and_fill": "resize_and_fill",
    "just resize (latent upscale)": "latent_upscale",
    "latent_upscale": "latent_upscale",
}
DEFAULT_RESIZE_MODE = "crop_and_resize"

MASK_MODE_ALIASES = {
    "inpaint masked": "inpaint_masked",
    "inpaint_masked": "inpaint_masked",
    "inpaint not masked": "inpaint_not_masked",
    "inpaint_not_masked": "inpaint_not_masked",
}
DEFAULT_MASK_MODE = "inpaint_masked"

MASKED_CONTENT_ALIASES = {
    "fill": "fill",
    "original": "original",
    "latent noise": "latent_noise",
    "latent_noise": "latent_noise",
    "latent nothing": "latent_nothing",
    "latent_nothing": "latent_nothing",
}
DEFAULT_MASKED_CONTENT = "original"

INPAINT_AREA_ALIASES = {
    "whole picture": "whole_picture",
    "whole_picture": "whole_picture",
    "only masked": "only_masked",
    "only_masked": "only_masked",
}
DEFAULT_INPAINT_AREA = "only_masked"
