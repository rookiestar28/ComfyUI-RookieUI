from __future__ import annotations

import re
from dataclasses import dataclass, field


CONTROLNET_PREPROCESSOR_OPTION_ORDER: tuple[str, ...] = (
    "none",
    "blur",
    "canny",
    "depth",
    "depth_anything_v2",
    "depth_anything",
    "depth_midas",
    "depth_zoe",
    "depth_leres",
    "normalmap",
    "normal_midas",
    "normal_bae",
    "normal_dsine",
    "openpose",
    "openpose_full",
    "openpose_dw",
    "openpose_animal",
    "openpose_densepose",
    "mlsd",
    "lineart",
    "lineart_anime",
    "lineart_anime_denoise",
    "lineart_coarse",
    "lineart_realistic",
    "lineart_standard",
    "scribble",
    "scribble_xdog",
    "scribble_pidinet",
    "scribble_fake",
    "segmentation",
    "segmentation_oneformer_coco",
    "segmentation_oneformer_ade20k",
    "segmentation_uniformer",
    "segmentation_anime_face",
    "shuffle",
    "sketch",
    "sketch_scribble",
    "sketch_lineart",
    "sketch_hed",
    "softedge",
    "softedge_hed",
    "softedge_pidinet",
    "softedge_teed",
    "reference",
    "ipadapter",
    "instantid",
    "t2iadapter",
    "tile",
    "tile_simple",
    "tile_gf",
    "inpaint",
)

PREPROCESSOR_OPTION_ALIASES: dict[str, str] = {
    "ip_adapter": "ipadapter",
    "ip-adapter": "ipadapter",
    "instant_id": "instantid",
    "instant-id": "instantid",
    "t2i_adapter": "t2iadapter",
    "t2i-adapter": "t2iadapter",
    "normal_map": "normalmap",
    "openposefull": "openpose_full",
    "openpose_dwpose": "openpose_dw",
    "lineart_anime_denoised": "lineart_anime_denoise",
    "lineartstandard": "lineart_standard",
    "lineartrealistic": "lineart_realistic",
    "soft_edge": "softedge",
}

PREPROCESSOR_OPTION_BASE_MODULE: dict[str, str] = {
    "none": "none",
    "blur": "blur",
    "canny": "canny",
    "depth": "depth",
    "depth_anything_v2": "depth",
    "depth_anything": "depth",
    "depth_midas": "depth",
    "depth_zoe": "depth",
    "depth_leres": "depth",
    "normalmap": "normalmap",
    "normal_midas": "normalmap",
    "normal_bae": "normalmap",
    "normal_dsine": "normalmap",
    "openpose": "openpose",
    "openpose_full": "openpose",
    "openpose_dw": "openpose",
    "openpose_animal": "openpose",
    "openpose_densepose": "openpose",
    "mlsd": "mlsd",
    "lineart": "lineart",
    "lineart_anime": "lineart",
    "lineart_anime_denoise": "lineart",
    "lineart_coarse": "lineart",
    "lineart_realistic": "lineart",
    "lineart_standard": "lineart",
    "scribble": "scribble",
    "scribble_xdog": "scribble",
    "scribble_pidinet": "scribble",
    "scribble_fake": "scribble",
    "segmentation": "segmentation",
    "segmentation_oneformer_coco": "segmentation",
    "segmentation_oneformer_ade20k": "segmentation",
    "segmentation_uniformer": "segmentation",
    "segmentation_anime_face": "segmentation",
    "shuffle": "shuffle",
    "sketch": "sketch",
    "sketch_scribble": "sketch",
    "sketch_lineart": "sketch",
    "sketch_hed": "sketch",
    "softedge": "softedge",
    "softedge_hed": "softedge",
    "softedge_pidinet": "softedge",
    "softedge_teed": "softedge",
    "reference": "reference",
    "ipadapter": "ipadapter",
    "instantid": "instantid",
    "t2iadapter": "t2iadapter",
    "tile": "tile",
    "tile_simple": "tile",
    "tile_gf": "tile",
    "inpaint": "inpaint",
}

PREPROCESSOR_OPTION_PREFERRED_HOST_CANDIDATES: dict[str, tuple[str, ...]] = {
    "depth_anything_v2": ("DepthAnythingV2Preprocessor",),
    "depth_anything": ("DepthAnythingPreprocessor",),
    "depth_midas": ("MiDaS-DepthMapPreprocessor",),
    "depth_zoe": ("Zoe-DepthMapPreprocessor",),
    "depth_leres": ("LeReS-DepthMapPreprocessor",),
    "normal_midas": ("MiDaS-NormalMapPreprocessor",),
    "normal_bae": ("BAE-NormalMapPreprocessor",),
    "normal_dsine": ("DSINE-NormalMapPreprocessor",),
    "openpose_full": ("OpenposePreprocessor",),
    "openpose_dw": ("DWPreprocessor",),
    "openpose_animal": ("AnimalPosePreprocessor",),
    "openpose_densepose": ("DensePosePreprocessor",),
    "lineart_anime": ("AnimeLineArtPreprocessor",),
    "lineart_anime_denoise": ("AnimeLineArtPreprocessor",),
    "lineart_coarse": ("AnyLineArtPreprocessor_aux",),
    "lineart_realistic": ("LineArtPreprocessor",),
    "lineart_standard": ("LineartStandardPreprocessor",),
    "scribble_xdog": ("Scribble_XDoG_Preprocessor",),
    "scribble_pidinet": ("Scribble_PiDiNet_Preprocessor",),
    "scribble_fake": ("FakeScribblePreprocessor",),
    "segmentation_oneformer_coco": ("OneFormer-COCO-SemSegPreprocessor",),
    "segmentation_oneformer_ade20k": ("OneFormer-ADE20K-SemSegPreprocessor",),
    "segmentation_uniformer": ("UniFormer-SemSegPreprocessor",),
    "segmentation_anime_face": ("AnimeFace_SemSegPreprocessor",),
    "sketch_scribble": ("ScribblePreprocessor", "Scribble_XDoG_Preprocessor"),
    "sketch_lineart": ("LineArtPreprocessor",),
    "sketch_hed": ("HEDPreprocessor",),
    "softedge_hed": ("HEDPreprocessor",),
    "softedge_pidinet": ("PiDiNetPreprocessor",),
    "softedge_teed": ("TEEDPreprocessor",),
    "tile_simple": ("TTPlanet_TileSimple_Preprocessor",),
    "tile_gf": ("TTPlanet_TileGF_Preprocessor",),
}

_CONTROL_TYPE_BY_BASE_MODULE: dict[str, str] = {
    "none": "All",
    "blur": "Blur",
    "canny": "Canny",
    "depth": "Depth",
    "normalmap": "NormalMap",
    "openpose": "OpenPose",
    "mlsd": "MLSD",
    "lineart": "Lineart",
    "scribble": "Scribble",
    "segmentation": "Segmentation",
    "shuffle": "Shuffle",
    "sketch": "Sketch",
    "softedge": "SoftEdge",
    "reference": "Reference",
    "ipadapter": "IP-Adapter",
    "instantid": "Instant-ID",
    "t2iadapter": "T2I-Adapter",
    "tile": "Tile",
    "inpaint": "Inpaint",
}

_PASSTHROUGH_OPTIONS = {"none", "reference", "ipadapter", "instantid", "t2iadapter"}
_POSE_OPTIONS = {"openpose_full", "openpose_dw", "openpose_animal"}
_NO_THRESHOLD_BASES = {"depth", "normalmap", "openpose", "segmentation", "shuffle", "tile", "inpaint"}


@dataclass(frozen=True)
class ControlNetPreprocessorProfile:
    option_key: str
    base_module: str
    control_type: str
    label: str
    preferred_host_nodes: tuple[str, ...] = ()
    parameter_labels: dict[str, str] = field(default_factory=dict)
    parameter_defaults: dict[str, object] = field(default_factory=dict)
    ui_fields: tuple[str, ...] = ("processor_res", "threshold_a", "threshold_b", "pixel_perfect")
    secondary_outputs: tuple[str, ...] = ()
    supports_pixel_perfect: bool = True
    supports_mask: bool = True
    model_keywords: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "option_key": self.option_key,
            "base_module": self.base_module,
            "control_type": self.control_type,
            "label": self.label,
            "preferred_host_nodes": list(self.preferred_host_nodes),
            "parameter_labels": dict(self.parameter_labels),
            "parameter_defaults": dict(self.parameter_defaults),
            "ui_fields": list(self.ui_fields),
            "secondary_outputs": list(self.secondary_outputs),
            "supports_pixel_perfect": self.supports_pixel_perfect,
            "supports_mask": self.supports_mask,
            "model_keywords": list(self.model_keywords),
        }


def normalize_preprocessor_option_token(module_value: object) -> str:
    token = str(module_value or "none").strip().lower()
    token = re.sub(r"[^a-z0-9]+", "_", token).strip("_")
    if not token:
        return "none"
    return PREPROCESSOR_OPTION_ALIASES.get(token, token)


def _profile_label(option_key: str) -> str:
    if option_key == "none":
        return "None"
    return option_key


def _model_keywords(control_type: str, base_module: str) -> tuple[str, ...]:
    if control_type == "All":
        return ()
    if control_type == "OpenPose":
        return ("openpose", "pose")
    if control_type == "NormalMap":
        return ("normal", "normalmap")
    if control_type == "IP-Adapter":
        return ("ipadapter", "ip-adapter", "ip_adapter")
    if control_type == "Instant-ID":
        return ("instantid", "instant-id", "instant_id")
    if control_type == "T2I-Adapter":
        return ("t2iadapter", "t2i-adapter", "t2i_adapter")
    return (base_module,)


def _build_profile(option_key: str) -> ControlNetPreprocessorProfile:
    base_module = PREPROCESSOR_OPTION_BASE_MODULE.get(option_key, option_key or "none")
    control_type = _CONTROL_TYPE_BY_BASE_MODULE.get(base_module, "All")
    parameter_labels = {
        "processor_res": "Processor Res",
        "threshold_a": "Threshold A",
        "threshold_b": "Threshold B",
    }
    ui_fields = ("processor_res", "threshold_a", "threshold_b", "pixel_perfect")
    if option_key in _PASSTHROUGH_OPTIONS:
        ui_fields = ()
    elif base_module in _NO_THRESHOLD_BASES:
        ui_fields = ("processor_res", "pixel_perfect")
    if base_module == "canny":
        parameter_labels.update({"threshold_a": "Low Threshold", "threshold_b": "High Threshold"})
    if base_module == "openpose":
        parameter_labels["processor_res"] = "Pose Resolution"

    parameter_defaults: dict[str, object] = {}
    if option_key == "openpose_dw":
        parameter_defaults.update(
            {
                "detect_hand": "enable",
                "detect_body": "enable",
                "detect_face": "enable",
            }
        )

    secondary_outputs = ("openpose_json",) if option_key in _POSE_OPTIONS else ()
    return ControlNetPreprocessorProfile(
        option_key=option_key,
        base_module=base_module,
        control_type=control_type,
        label=_profile_label(option_key),
        preferred_host_nodes=PREPROCESSOR_OPTION_PREFERRED_HOST_CANDIDATES.get(option_key, ()),
        parameter_labels=parameter_labels,
        parameter_defaults=parameter_defaults,
        ui_fields=ui_fields,
        secondary_outputs=secondary_outputs,
        supports_pixel_perfect=option_key not in _PASSTHROUGH_OPTIONS,
        supports_mask=base_module in {"inpaint", "depth", "canny", "lineart", "scribble", "softedge", "openpose"},
        model_keywords=_model_keywords(control_type, base_module),
    )


_PREPROCESSOR_PROFILES: dict[str, ControlNetPreprocessorProfile] = {
    option_key: _build_profile(option_key) for option_key in CONTROLNET_PREPROCESSOR_OPTION_ORDER
}


def get_preprocessor_profile(module_value: object) -> ControlNetPreprocessorProfile:
    option_key = normalize_preprocessor_option_token(module_value)
    return _PREPROCESSOR_PROFILES.get(option_key) or _build_profile(option_key)


def iter_preprocessor_profiles() -> tuple[ControlNetPreprocessorProfile, ...]:
    return tuple(_PREPROCESSOR_PROFILES[option_key] for option_key in CONTROLNET_PREPROCESSOR_OPTION_ORDER)


def serialize_preprocessor_profiles() -> dict[str, dict[str, object]]:
    return {profile.option_key: profile.to_payload() for profile in iter_preprocessor_profiles()}


def clamp_processor_resolution(value: object, *, fallback: int = 512) -> int:
    try:
        numeric = int(round(float(value)))
    except (TypeError, ValueError):
        numeric = fallback
    return max(64, min(2048, numeric))


def calculate_pixel_perfect_resolution(
    *,
    image_width: int,
    image_height: int,
    target_width: int,
    target_height: int,
    resize_mode: str,
) -> int:
    raw_width = max(1, int(image_width))
    raw_height = max(1, int(image_height))
    target_width = max(1, int(target_width))
    target_height = max(1, int(target_height))

    height_scale = float(target_height) / float(raw_height)
    width_scale = float(target_width) / float(raw_width)
    normalized_mode = str(resize_mode or "").strip().lower()
    if normalized_mode in {"resize_and_fill", "outer_fit", "resize and fill"}:
        estimation = min(height_scale, width_scale) * float(min(raw_height, raw_width))
    else:
        estimation = max(height_scale, width_scale) * float(min(raw_height, raw_width))
    return clamp_processor_resolution(round(estimation))


def resolve_effective_processor_resolution(
    *,
    requested_processor_res: object,
    pixel_perfect: object,
    image_width: int | None,
    image_height: int | None,
    target_width: int | None,
    target_height: int | None,
    resize_mode: str,
    profile: ControlNetPreprocessorProfile | None = None,
) -> int:
    requested = clamp_processor_resolution(requested_processor_res)
    if not bool(pixel_perfect):
        return requested
    if profile is not None and not profile.supports_pixel_perfect:
        return requested
    if not image_width or not image_height or not target_width or not target_height:
        return requested
    return calculate_pixel_perfect_resolution(
        image_width=int(image_width),
        image_height=int(image_height),
        target_width=int(target_width),
        target_height=int(target_height),
        resize_mode=resize_mode,
    )
