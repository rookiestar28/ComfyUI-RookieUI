from __future__ import annotations

import base64
import io
import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Any

from rookieui.services.controlnet_profiles import (
    ControlNetPreprocessorProfile,
    get_preprocessor_profile,
    resolve_effective_processor_resolution,
)

try:
    import numpy as np
except Exception:  # pragma: no cover - optional runtime dependency
    np = None

try:
    import torch
except Exception:  # pragma: no cover - optional runtime dependency
    torch = None

try:
    from PIL import Image, ImageFilter
except Exception:  # pragma: no cover - optional runtime dependency
    Image = None
    ImageFilter = None

_LOGGER = logging.getLogger("ComfyUI-RookieUI")

_MISSING = object()
_PROMPT_SERVER_SHIM_LOCK = threading.Lock()
_PROMPT_SERVER_SHIM_REFCOUNTS: dict[int, int] = {}
_PROMPT_SERVER_SHIM_VALUES: dict[int, str] = {}

# Integrated preprocessor option catalog consumed by both backend payload validation and
# workflow/runtime dispatch. Keep this list deterministic to preserve UI filter order.
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

_PREPROCESSOR_OPTION_BASE_MODULE: dict[str, str] = {
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

_PREPROCESSOR_OPTION_PREFERRED_HOST_CANDIDATES: dict[str, tuple[str, ...]] = {
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

_PREPROCESSOR_OPTION_ALIASES: dict[str, str] = {
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

_PASSTHROUGH_MODULES = {
    "none",
    "reference",
    "ipadapter",
    "instantid",
    "t2iadapter",
}

_MODULE_HOST_PREPROCESSOR_CANDIDATES: dict[str, tuple[str, ...]] = {
    "blur": (),
    "canny": ("CannyEdgePreprocessor", "PyraCannyPreprocessor", "Canny"),
    "depth": (
        "MiDaS-DepthMapPreprocessor",
        "DepthAnythingV2Preprocessor",
        "DepthAnythingPreprocessor",
        "Zoe-DepthMapPreprocessor",
        "LeReS-DepthMapPreprocessor",
    ),
    "normalmap": (
        "MiDaS-NormalMapPreprocessor",
        "BAE-NormalMapPreprocessor",
        "DSINE-NormalMapPreprocessor",
    ),
    "openpose": ("OpenposePreprocessor", "DWPreprocessor", "AnimalPosePreprocessor", "DensePosePreprocessor"),
    "mlsd": ("M-LSDPreprocessor",),
    "lineart": (
        "LineArtPreprocessor",
        "LineartStandardPreprocessor",
        "AnimeLineArtPreprocessor",
        "AnyLineArtPreprocessor_aux",
        "Manga2Anime_LineArt_Preprocessor",
    ),
    "scribble": (
        "ScribblePreprocessor",
        "Scribble_XDoG_Preprocessor",
        "Scribble_PiDiNet_Preprocessor",
        "FakeScribblePreprocessor",
    ),
    "segmentation": (
        "OneFormer-COCO-SemSegPreprocessor",
        "OneFormer-ADE20K-SemSegPreprocessor",
        "UniFormer-SemSegPreprocessor",
        "SemSegPreprocessor",
        "AnimeFace_SemSegPreprocessor",
    ),
    "shuffle": ("ShufflePreprocessor",),
    "sketch": (
        "ScribblePreprocessor",
        "Scribble_XDoG_Preprocessor",
        "LineArtPreprocessor",
        "HEDPreprocessor",
    ),
    "softedge": ("HEDPreprocessor", "PiDiNetPreprocessor", "TEEDPreprocessor"),
    "tile": ("TilePreprocessor", "TTPlanet_TileSimple_Preprocessor", "TTPlanet_TileGF_Preprocessor"),
    "inpaint": ("InpaintPreprocessor",),
}

_MODULE_AIO_PREPROCESSOR_CANDIDATES: dict[str, tuple[str, ...]] = {
    "blur": ("ImageIntensityDetector",),
    "canny": ("CannyEdgePreprocessor", "PyraCannyPreprocessor"),
    # IMPORTANT: avoid AIO fallback for depth/normalmap families; broad AIO probing may initialize unrelated annotators
    # and trigger heavyweight auxiliary model bootstrap/download attempts that do not match user-selected processor intent.
    "depth": (),
    "normalmap": (),
    "openpose": ("OpenposePreprocessor", "DWPreprocessor"),
    "mlsd": ("M-LSDPreprocessor",),
    "lineart": ("LineArtPreprocessor", "LineartStandardPreprocessor", "AnimeLineArtPreprocessor"),
    "scribble": ("ScribblePreprocessor", "Scribble_XDoG_Preprocessor"),
    "segmentation": ("OneFormer-COCO-SemSegPreprocessor", "OneFormer-ADE20K-SemSegPreprocessor"),
    "shuffle": ("ShufflePreprocessor",),
    "sketch": ("ScribblePreprocessor", "LineArtPreprocessor"),
    "softedge": ("HEDPreprocessor", "PiDiNetPreprocessor"),
    "tile": ("TilePreprocessor",),
    "inpaint": ("none",),
}

_MODULE_AIO_KEYWORDS: dict[str, tuple[str, ...]] = {
    "blur": ("blur", "intensity"),
    "canny": ("canny",),
    "depth": ("depth_anything_v2", "depth_anything", "midas", "zoe", "leres", "depth"),
    "normalmap": ("normalmap", "normal", "dsine", "bae", "midas"),
    "openpose": ("openpose", "dw", "densepose", "animalpose", "pose"),
    "mlsd": ("m_lsd", "mlsd"),
    "lineart": ("lineart", "anime", "manga", "anyline"),
    "scribble": ("scribble", "xdog", "pidinet", "fake"),
    "segmentation": ("oneformer", "uniformer", "semseg", "segmentation", "seg"),
    "shuffle": ("shuffle",),
    "sketch": ("sketch", "scribble", "lineart", "hed"),
    "softedge": ("hed", "pidinet", "teed", "softedge", "soft_edge"),
    "tile": ("tile",),
    "inpaint": ("inpaint", "lama"),
}

_MODULE_HOST_NODE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "blur": ("blur", "intensity"),
    "canny": ("canny",),
    "depth": ("depthanythingv2", "depthanything", "midas", "zoe", "leres", "depth"),
    "normalmap": ("normalmap", "normal", "dsine", "bae"),
    "openpose": ("openpose", "dw", "densepose", "animalpose", "pose"),
    "mlsd": ("mlsd", "m_lsd"),
    "lineart": ("lineart", "anime", "manga", "anyline"),
    "scribble": ("scribble", "xdog", "pidinet", "fake"),
    "segmentation": ("oneformer", "uniformer", "semseg", "segmentation", "seg"),
    "shuffle": ("shuffle",),
    "sketch": ("sketch", "scribble", "lineart"),
    "softedge": ("hed", "pidinet", "teed", "softedge", "soft_edge"),
    "tile": ("tile",),
    "inpaint": ("inpaint", "lama"),
}

_HOST_NODE_EXCLUDE_TOKENS = (
    "provider_for_segs",
    "for_segs",
    "segs",
    "detectorprovider",
)

_MODULE_DYNAMIC_NODE_EXCLUDE_TOKENS: dict[str, tuple[str, ...]] = {
    # IMPORTANT: keep heavyweight depth/normal candidates out of generic dynamic probing; these nodes may trigger
    # large auxiliary model bootstrap/download flows when merely probed and are not the default integrated depth path.
    "depth": ("metric3d", "meshgraphormer"),
    "normalmap": ("metric3d",),
}

_MODULE_HOST_PREPROCESSOR_PRIORITIES: dict[str, tuple[str, ...]] = {
    # IMPORTANT: prefer deterministic host nodes first so depth preview does not oscillate across preprocessor families.
    "depth": (
        "DepthAnythingV2Preprocessor",
        "DepthAnythingPreprocessor",
        "MiDaS-DepthMapPreprocessor",
        "Zoe-DepthMapPreprocessor",
        "LeReS-DepthMapPreprocessor",
    ),
    "normalmap": (
        "MiDaS-NormalMapPreprocessor",
        "BAE-NormalMapPreprocessor",
        "DSINE-NormalMapPreprocessor",
    ),
}

_MODULE_HOST_PREPROCESSOR_PROBE_LIMITS: dict[str, int] = {
    # IMPORTANT: keep explicit overrides sparse; default behavior is already single-attempt deterministic probing.
    "depth": 1,
    "normalmap": 1,
}

_DEFAULT_HOST_PREPROCESSOR_PROBE_LIMIT = 1
ROOKIEUI_CONTROLNET_AIO_PREPROCESSOR_ENABLED_ENV = "ROOKIEUI_CONTROLNET_AIO_PREPROCESSOR_ENABLED"


@dataclass(frozen=True)
class ControlNetRuntimeResult:
    image: "torch.Tensor"
    backend: str
    processor_name: str
    used_fallback: bool
    diagnostics: tuple[str, ...] = ()
    secondary_outputs: dict[str, tuple[object, ...]] | None = None


def runtime_dependencies_available() -> bool:
    return all(dependency is not None for dependency in (np, torch, Image, ImageFilter))


def _normalize_module_token(module_value: object) -> str:
    token = str(module_value or "none").strip().lower()
    token = re.sub(r"[^a-z0-9]+", "_", token).strip("_")
    if not token:
        return "none"
    return _PREPROCESSOR_OPTION_ALIASES.get(token, token)


def normalize_preprocessor_option_key(module_value: object) -> str:
    token = _normalize_module_token(module_value)
    if token in _PREPROCESSOR_OPTION_BASE_MODULE:
        return token
    return token or "none"


def normalize_module_key(module_value: object) -> str:
    option_key = normalize_preprocessor_option_key(module_value)
    return _PREPROCESSOR_OPTION_BASE_MODULE.get(option_key, option_key or "none")


def _resolve_module_dispatch(module_value: object) -> tuple[str, str, tuple[str, ...]]:
    option_key = normalize_preprocessor_option_key(module_value)
    profile = get_preprocessor_profile(option_key)
    module_key = profile.base_module
    preferred_candidates = profile.preferred_host_nodes
    return option_key, module_key, preferred_candidates


def image_tensor_from_bytes(image_bytes: bytes) -> "torch.Tensor":
    _require_runtime_dependencies()
    image_obj = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    pixel_array = np.array(image_obj).astype(np.float32) / 255.0
    return torch.from_numpy(pixel_array).unsqueeze(0)


def mask_tensor_from_bytes(mask_bytes: bytes) -> "torch.Tensor":
    _require_runtime_dependencies()
    mask_obj = Image.open(io.BytesIO(mask_bytes)).convert("L")
    mask_array = np.array(mask_obj).astype(np.float32) / 255.0
    return torch.from_numpy(mask_array).unsqueeze(0)


def image_tensor_to_data_url(image_tensor: "torch.Tensor") -> str:
    _require_runtime_dependencies()
    normalized = _coerce_image_tensor(image_tensor)
    if normalized.shape[0] == 0:
        raise ValueError("image_tensor must include at least one frame.")
    frame = normalized[0].detach().cpu().numpy()
    frame_uint8 = np.clip(frame * 255.0, 0.0, 255.0).astype(np.uint8)
    image_obj = Image.fromarray(frame_uint8, mode="RGB")
    stream = io.BytesIO()
    image_obj.save(stream, format="PNG")
    encoded = base64.b64encode(stream.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def preprocess_controlnet_tensor(
    *,
    image_tensor: "torch.Tensor",
    module: object,
    processor_res: int,
    threshold_a: float,
    threshold_b: float,
    mask_tensor: "torch.Tensor | np.ndarray | Image.Image | None" = None,
    pixel_perfect: bool = False,
    target_width: int | None = None,
    target_height: int | None = None,
    resize_mode: str = "crop_and_resize",
) -> ControlNetRuntimeResult:
    _require_runtime_dependencies()
    selected_preprocessor, normalized_module, preferred_host_candidates = _resolve_module_dispatch(module)
    profile = get_preprocessor_profile(selected_preprocessor)
    source = _coerce_image_tensor(image_tensor)
    normalized_mask = _coerce_mask_tensor(mask_tensor, image_tensor=source) if mask_tensor is not None else None
    image_width, image_height = _image_tensor_dimensions(source)
    effective_processor_res = resolve_effective_processor_resolution(
        requested_processor_res=processor_res,
        pixel_perfect=pixel_perfect,
        image_width=image_width,
        image_height=image_height,
        target_width=target_width or image_width,
        target_height=target_height or image_height,
        resize_mode=resize_mode,
        profile=profile,
    )
    diagnostics: list[str] = []

    if normalized_module in _PASSTHROUGH_MODULES:
        return ControlNetRuntimeResult(
            image=source,
            backend="passthrough_module",
            processor_name=normalized_module,
            used_fallback=False,
            diagnostics=(),
            secondary_outputs={},
        )

    host_mappings = _resolve_host_node_class_mappings()
    prompt_server_instance = _resolve_prompt_server_instance()
    shim_applied, shim_value = _ensure_prompt_server_last_prompt_id(prompt_server_instance)
    if shim_applied:
        diagnostics.append("prompt_server_last_prompt_id_shim_applied")

    try:
        host_candidates = _resolve_host_preprocessor_candidates(
            normalized_module,
            host_mappings,
            preferred_candidates=preferred_host_candidates,
        )
        # DEBUG HOTSPOT: selected preprocessor option -> host candidate binding seam.
        # If UI selection appears ignored, inspect `selected_preprocessor` and first host candidate here.
        if selected_preprocessor != normalized_module:
            diagnostics.append(f"selected_preprocessor:{selected_preprocessor}")
        configured_probe_limit = _MODULE_HOST_PREPROCESSOR_PROBE_LIMITS.get(
            normalized_module,
            _DEFAULT_HOST_PREPROCESSOR_PROBE_LIMIT,
        )
        # DEBUG HOTSPOT: enforce single-attempt deterministic probing across all modules to avoid cross-family
        # annotator side effects (unexpected model bootstrap/download) when host preprocessor chains fan out.
        host_probe_limit = max(0, int(configured_probe_limit))
        host_probe_attempts = 0
        for node_name in host_candidates:
            if node_name not in host_mappings:
                continue
            if host_probe_attempts >= host_probe_limit:
                diagnostics.append(f"host_probe_limit_reached:{host_probe_limit}")
                break
            host_probe_attempts += 1
            try:
                processed, secondary_outputs = _run_profile_host_node_preprocessor(
                    node_name=node_name,
                    node_cls=host_mappings[node_name],
                    image_tensor=source,
                    mask_tensor=normalized_mask,
                    module_key=normalized_module,
                    processor_res=effective_processor_res,
                    threshold_a=threshold_a,
                    threshold_b=threshold_b,
                    aio_preprocessor_name=None,
                    profile=profile,
                )
                # DEBUG HOTSPOT: host execution succeeded but visual result may still be effectively blank.
                # Mark this seam explicitly so detect-layer warnings can distinguish "pipeline failure" vs "empty detection result".
                if _is_visually_empty_image_tensor(processed):
                    diagnostics.append(f"{node_name}:output_near_empty")
                return ControlNetRuntimeResult(
                    image=processed,
                    backend="comfy_host_preprocessor",
                    processor_name=node_name,
                    used_fallback=False,
                    diagnostics=tuple(diagnostics),
                    secondary_outputs=secondary_outputs,
                )
            except Exception as exc:  # pragma: no cover - runtime-dependent host node behavior
                diagnostics.append(f"{node_name}: {exc}")
                continue

        if _is_aio_preprocessor_enabled():
            aio_cls = host_mappings.get("AIO_Preprocessor")
            if aio_cls is not None:
                aio_name = _select_aio_preprocessor_name(aio_cls, normalized_module)
                if aio_name:
                    try:
                        processed, secondary_outputs = _run_profile_host_node_preprocessor(
                            node_name="AIO_Preprocessor",
                            node_cls=aio_cls,
                            image_tensor=source,
                            mask_tensor=normalized_mask,
                            module_key=normalized_module,
                            processor_res=effective_processor_res,
                            threshold_a=threshold_a,
                            threshold_b=threshold_b,
                            aio_preprocessor_name=aio_name,
                            profile=profile,
                        )
                        # DEBUG HOTSPOT: same near-empty visibility check for AIO branch; keep diagnostics symmetric with direct-host branch.
                        if _is_visually_empty_image_tensor(processed):
                            diagnostics.append(f"AIO_Preprocessor({aio_name}):output_near_empty")
                        return ControlNetRuntimeResult(
                            image=processed,
                            backend="comfy_host_preprocessor_aio",
                            processor_name=aio_name,
                            used_fallback=False,
                            diagnostics=tuple(diagnostics),
                            secondary_outputs=secondary_outputs,
                        )
                    except Exception as exc:  # pragma: no cover - runtime-dependent host node behavior
                        diagnostics.append(f"AIO_Preprocessor({aio_name}): {exc}")
        else:
            # DEBUG HOTSPOT: keep AIO gating explicit; querying AIO INPUT_TYPES can trigger broad annotator enumeration.
            diagnostics.append("aio_preprocessor_disabled")

        if diagnostics:
            # DEBUG HOTSPOT: if users report processor/model mismatch, this seam records the candidate chain that failed
            # before fallback so we can pinpoint over-eager node probing without reproducing full host bootstrap logs.
            _LOGGER.warning(
                "RookieUI ControlNet host preprocessor chain exhausted (module=%s): %s",
                normalized_module,
                " | ".join(diagnostics[:3]),
            )

        fallback = _apply_fallback_filters(
            source,
            module_key=normalized_module,
            processor_res=effective_processor_res,
            threshold_a=threshold_a,
            threshold_b=threshold_b,
        )
        return ControlNetRuntimeResult(
            image=fallback,
            backend="rookieui_internal_fallback",
            processor_name=normalized_module,
            used_fallback=True,
            diagnostics=tuple(diagnostics),
            secondary_outputs={},
        )
    finally:
        _restore_prompt_server_last_prompt_id(prompt_server_instance, shim_applied, shim_value)


def _require_runtime_dependencies() -> None:
    if runtime_dependencies_available():
        return
    missing: list[str] = []
    if np is None:
        missing.append("numpy")
    if torch is None:
        missing.append("torch")
    if Image is None or ImageFilter is None:
        missing.append("Pillow")
    raise RuntimeError(f"ControlNet runtime preprocessing requires {', '.join(missing)}.")


def _env_flag(name: str, *, default: bool) -> bool:
    raw_value = str(os.getenv(name, "1" if default else "0")).strip().lower()
    if raw_value in {"1", "true", "yes", "on"}:
        return True
    if raw_value in {"0", "false", "no", "off"}:
        return False
    return default


def _is_aio_preprocessor_enabled() -> bool:
    return _env_flag(ROOKIEUI_CONTROLNET_AIO_PREPROCESSOR_ENABLED_ENV, default=False)


def _image_tensor_dimensions(image_tensor: object) -> tuple[int | None, int | None]:
    shape = getattr(image_tensor, "shape", None)
    if not isinstance(shape, (tuple, list)) or len(shape) < 3:
        return None, None
    try:
        if len(shape) >= 4:
            return int(shape[2]), int(shape[1])
        return int(shape[1]), int(shape[0])
    except (TypeError, ValueError):
        return None, None


def _resolve_prompt_server_instance() -> Any | None:
    try:
        import server as comfy_server  # type: ignore
    except Exception:
        return None
    prompt_server_cls = getattr(comfy_server, "PromptServer", None)
    if prompt_server_cls is None:
        return None
    return getattr(prompt_server_cls, "instance", None)


def _ensure_prompt_server_last_prompt_id(server_instance: Any) -> tuple[bool, str]:
    if server_instance is None:
        return False, ""
    server_key = id(server_instance)
    with _PROMPT_SERVER_SHIM_LOCK:
        synthetic_prompt_id = _PROMPT_SERVER_SHIM_VALUES.get(server_key)
        if synthetic_prompt_id is not None:
            _PROMPT_SERVER_SHIM_REFCOUNTS[server_key] = _PROMPT_SERVER_SHIM_REFCOUNTS.get(server_key, 0) + 1
            return True, synthetic_prompt_id
        if hasattr(server_instance, "last_prompt_id"):
            return False, ""
        synthetic_prompt_id = f"rookieui-controlnet-detect-{int(time.time() * 1000)}"
        # IMPORTANT: keep shared PromptServer shim ownership serialized; overlapping detect requests share one host object.
        try:
            setattr(server_instance, "last_prompt_id", synthetic_prompt_id)
        except Exception:
            return False, ""
        _PROMPT_SERVER_SHIM_VALUES[server_key] = synthetic_prompt_id
        _PROMPT_SERVER_SHIM_REFCOUNTS[server_key] = _PROMPT_SERVER_SHIM_REFCOUNTS.get(server_key, 0) + 1
        return True, synthetic_prompt_id


def _restore_prompt_server_last_prompt_id(server_instance: Any, was_applied: bool, expected_value: str) -> None:
    if not was_applied or server_instance is None or not expected_value:
        return
    server_key = id(server_instance)
    with _PROMPT_SERVER_SHIM_LOCK:
        current_refs = _PROMPT_SERVER_SHIM_REFCOUNTS.get(server_key, 0)
        if current_refs <= 1:
            _PROMPT_SERVER_SHIM_REFCOUNTS.pop(server_key, None)
            _PROMPT_SERVER_SHIM_VALUES.pop(server_key, None)
        else:
            _PROMPT_SERVER_SHIM_REFCOUNTS[server_key] = current_refs - 1
            return
        current_value = getattr(server_instance, "last_prompt_id", _MISSING)
        if current_value != expected_value:
            return
        try:
            delattr(server_instance, "last_prompt_id")
        except Exception:
            return


def _resolve_host_node_class_mappings() -> dict[str, Any]:
    try:
        import nodes as comfy_nodes  # type: ignore
    except Exception:
        return {}
    mappings = getattr(comfy_nodes, "NODE_CLASS_MAPPINGS", {})
    return mappings if isinstance(mappings, dict) else {}


def _resolve_resize_filters() -> tuple[int, int]:
    resample_owner = getattr(Image, "Resampling", Image)
    return (
        getattr(resample_owner, "BILINEAR", Image.BILINEAR),
        getattr(resample_owner, "NEAREST", Image.NEAREST),
    )


def _coerce_image_tensor(image_value: Any) -> "torch.Tensor":
    _require_runtime_dependencies()
    if isinstance(image_value, torch.Tensor):
        tensor = image_value.detach().to(dtype=torch.float32)
    elif isinstance(image_value, np.ndarray):
        tensor = torch.from_numpy(image_value.astype(np.float32))
    elif isinstance(image_value, Image.Image):
        array = np.array(image_value.convert("RGB")).astype(np.float32) / 255.0
        tensor = torch.from_numpy(array)
    else:
        raise TypeError("Unsupported image tensor payload type.")

    if tensor.ndim == 3:
        if tensor.shape[-1] in {1, 3, 4}:
            tensor = tensor.unsqueeze(0)
        elif tensor.shape[0] in {1, 3, 4}:
            tensor = tensor.permute(1, 2, 0).unsqueeze(0)
        else:
            raise ValueError("Unsupported 3D image tensor shape.")
    elif tensor.ndim == 4:
        if tensor.shape[-1] in {1, 3, 4}:
            pass
        elif tensor.shape[1] in {1, 3, 4}:
            tensor = tensor.permute(0, 2, 3, 1)
        else:
            raise ValueError("Unsupported 4D image tensor shape.")
    else:
        raise ValueError("Image tensor must be 3D or 4D.")

    if tensor.shape[-1] == 4:
        rgb = tensor[:, :, :, :3]
        alpha = tensor[:, :, :, 3:4]
        # DEBUG HOTSPOT: some host preprocessors emit annotation strokes via alpha-only RGBA payloads.
        # Preserve visual content by promoting alpha matte to RGB when color channels are effectively empty.
        if float(rgb.abs().max().item()) <= 1e-6 and float(alpha.abs().max().item()) > 1e-6:
            tensor = alpha.repeat(1, 1, 1, 3)
        else:
            tensor = rgb

    tensor = _normalize_image_value_range(tensor)
    return torch.clamp(tensor, 0.0, 1.0)


def _is_visually_empty_image_tensor(image_tensor: "torch.Tensor", *, pixel_threshold: float = 0.01, ratio_threshold: float = 0.0005) -> bool:
    # DEBUG HOTSPOT: visual-emptiness heuristic seam for preprocess outputs.
    # Tune thresholds here when users report "completed but black preview" cases with host preprocessors.
    normalized = _coerce_image_tensor(image_tensor)
    if normalized.shape[0] == 0:
        return True
    luminance = normalized.max(dim=-1).values
    active_ratio = float((luminance > float(pixel_threshold)).float().mean().item())
    return active_ratio <= float(ratio_threshold)


def _normalize_image_value_range(tensor: "torch.Tensor") -> "torch.Tensor":
    minimum = float(tensor.min().item())
    maximum = float(tensor.max().item())
    if minimum >= 0.0 and maximum <= 1.0:
        return tensor
    fractional_delta = float((tensor - tensor.round()).abs().max().item())
    if minimum >= 0.0 and 1.0 < maximum <= 255.0 and fractional_delta <= 1e-4:
        return tensor / 255.0
    # IMPORTANT: host preprocessors may emit signed or non-8bit ranges; normalize by min/max to avoid black-frame previews.
    span = maximum - minimum
    if span <= 1e-6:
        return torch.zeros_like(tensor)
    return (tensor - minimum) / span


def _coerce_mask_tensor(mask_value: Any, *, image_tensor: "torch.Tensor") -> "torch.Tensor":
    _require_runtime_dependencies()
    if isinstance(mask_value, torch.Tensor):
        tensor = mask_value.detach().to(dtype=torch.float32)
    elif isinstance(mask_value, np.ndarray):
        tensor = torch.from_numpy(mask_value.astype(np.float32))
    elif isinstance(mask_value, Image.Image):
        tensor = torch.from_numpy(np.array(mask_value.convert("L")).astype(np.float32) / 255.0)
    else:
        raise TypeError("Unsupported mask tensor payload type.")

    if tensor.ndim == 4 and tensor.shape[-1] in {1, 3, 4}:
        tensor = tensor[:, :, :, 0]
    elif tensor.ndim == 4 and tensor.shape[1] == 1:
        tensor = tensor[:, 0, :, :]
    elif tensor.ndim == 3 and tensor.shape[-1] in {1, 3, 4}:
        tensor = tensor[:, :, 0].unsqueeze(0)
    elif tensor.ndim == 2:
        tensor = tensor.unsqueeze(0)
    elif tensor.ndim != 3:
        raise ValueError("Mask tensor must be 2D/3D (or 4D single-channel).")

    if tensor.shape[0] == 1 and image_tensor.shape[0] > 1:
        tensor = tensor.repeat(image_tensor.shape[0], 1, 1)
    elif tensor.shape[0] != image_tensor.shape[0]:
        tensor = tensor[:1].repeat(image_tensor.shape[0], 1, 1)

    resized = torch.nn.functional.interpolate(
        tensor.unsqueeze(1),
        size=(image_tensor.shape[1], image_tensor.shape[2]),
        mode="bilinear",
        align_corners=False,
    ).squeeze(1)
    return torch.clamp(resized, 0.0, 1.0)


def _extract_node_input_schema(node_cls: type[Any]) -> tuple[dict[str, object], dict[str, object]]:
    input_types = getattr(node_cls, "INPUT_TYPES", None)
    if not callable(input_types):
        return {}, {}
    try:
        spec = input_types()
    except Exception:
        return {}, {}
    if not isinstance(spec, dict):
        return {}, {}
    required = spec.get("required", {})
    optional = spec.get("optional", {})
    return (
        required if isinstance(required, dict) else {},
        optional if isinstance(optional, dict) else {},
    )


def _extract_default_from_schema(schema_entry: object) -> object:
    if isinstance(schema_entry, (list, tuple)) and len(schema_entry) > 1 and isinstance(schema_entry[1], dict):
        if "default" in schema_entry[1]:
            return schema_entry[1]["default"]
    if isinstance(schema_entry, (list, tuple)) and schema_entry:
        choices = schema_entry[0]
        if isinstance(choices, list) and choices:
            for candidate in choices:
                if str(candidate or "").strip().lower() not in {"", "none"}:
                    return candidate
            return choices[0]
    return _MISSING


def _resolve_node_function(instance: Any) -> Any:
    function_name = getattr(instance, "FUNCTION", None)
    if isinstance(function_name, str):
        method = getattr(instance, function_name, None)
        if callable(method):
            return method
    for candidate in ("execute", "estimate_pose", "preprocess", "detect", "run", "process"):
        method = getattr(instance, candidate, None)
        if callable(method):
            return method
    return None


def _build_node_parameter_value(
    parameter_name: str,
    *,
    image_tensor: "torch.Tensor",
    mask_tensor: "torch.Tensor | None",
    processor_res: int,
    threshold_a: float,
    threshold_b: float,
    aio_preprocessor_name: str | None,
    profile: ControlNetPreprocessorProfile | None = None,
) -> object:
    key = str(parameter_name or "").strip()
    if profile is not None and key in profile.parameter_defaults:
        return profile.parameter_defaults[key]
    if key == "image":
        return image_tensor
    if key == "mask":
        return mask_tensor if mask_tensor is not None else _MISSING
    if key in {"input_mask", "mask_image"}:
        return mask_tensor if mask_tensor is not None else _MISSING
    if key == "preprocessor":
        return aio_preprocessor_name if aio_preprocessor_name else _MISSING
    if key in {"resolution", "processor_res"}:
        return int(processor_res)
    if key == "low_threshold":
        return int(round(threshold_a))
    if key == "high_threshold":
        return int(round(threshold_b))
    if key == "threshold":
        return float(threshold_a)
    if key == "threshold_a":
        return float(threshold_a)
    if key == "threshold_b":
        return float(threshold_b)
    if key == "a":
        return float(threshold_a)
    if key == "bg_threshold":
        return float(max(0.0, min(1.0, threshold_b / 255.0)))
    if key == "score_threshold":
        return float(max(0.0, min(1.0, threshold_a / 255.0)))
    if key == "dist_threshold":
        return float(max(0.0, min(1.0, threshold_b / 255.0)))
    if key == "guassian_sigma":
        return float(max(0.1, min(32.0, threshold_a / 32.0)))
    if key == "intensity_threshold":
        return int(round(max(0.0, min(255.0, threshold_b))))
    if key in {"detect_hand", "detect_body", "detect_face"}:
        return True
    if key == "safe":
        return True
    if key == "coarse":
        return bool(threshold_a >= 128.0)
    if key == "seed":
        return 0
    if key in {"rm_nearest", "rm_background", "boost"}:
        return False
    if key == "merge_with_lineart":
        return True
    return _MISSING


def _run_host_node_preprocessor(
    *,
    node_name: str,
    node_cls: type[Any],
    image_tensor: "torch.Tensor",
    mask_tensor: "torch.Tensor | None",
    module_key: str,
    processor_res: int,
    threshold_a: float,
    threshold_b: float,
    aio_preprocessor_name: str | None,
) -> "torch.Tensor":
    output, _secondary = _run_host_node_preprocessor_payload(
        node_name=node_name,
        node_cls=node_cls,
        image_tensor=image_tensor,
        mask_tensor=mask_tensor,
        module_key=module_key,
        processor_res=processor_res,
        threshold_a=threshold_a,
        threshold_b=threshold_b,
        aio_preprocessor_name=aio_preprocessor_name,
        profile=None,
    )
    return output


def _run_profile_host_node_preprocessor(
    *,
    node_name: str,
    node_cls: type[Any],
    image_tensor: "torch.Tensor",
    mask_tensor: "torch.Tensor | None",
    module_key: str,
    processor_res: int,
    threshold_a: float,
    threshold_b: float,
    aio_preprocessor_name: str | None,
    profile: ControlNetPreprocessorProfile,
) -> tuple["torch.Tensor", dict[str, tuple[object, ...]]]:
    if profile.secondary_outputs:
        return _run_host_node_preprocessor_payload(
            node_name=node_name,
            node_cls=node_cls,
            image_tensor=image_tensor,
            mask_tensor=mask_tensor,
            module_key=module_key,
            processor_res=processor_res,
            threshold_a=threshold_a,
            threshold_b=threshold_b,
            aio_preprocessor_name=aio_preprocessor_name,
            profile=profile,
        )
    output = _run_host_node_preprocessor(
        node_name=node_name,
        node_cls=node_cls,
        image_tensor=image_tensor,
        mask_tensor=mask_tensor,
        module_key=module_key,
        processor_res=processor_res,
        threshold_a=threshold_a,
        threshold_b=threshold_b,
        aio_preprocessor_name=aio_preprocessor_name,
    )
    return output, {}


def _run_host_node_preprocessor_payload(
    *,
    node_name: str,
    node_cls: type[Any],
    image_tensor: "torch.Tensor",
    mask_tensor: "torch.Tensor | None",
    module_key: str,
    processor_res: int,
    threshold_a: float,
    threshold_b: float,
    aio_preprocessor_name: str | None,
    profile: ControlNetPreprocessorProfile | None,
) -> tuple["torch.Tensor", dict[str, tuple[object, ...]]]:
    required_schema, optional_schema = _extract_node_input_schema(node_cls)
    inputs: dict[str, object] = {}

    for required_name, required_spec in required_schema.items():
        resolved = _build_node_parameter_value(
            str(required_name),
            image_tensor=image_tensor,
            mask_tensor=mask_tensor,
            processor_res=processor_res,
            threshold_a=threshold_a,
            threshold_b=threshold_b,
            aio_preprocessor_name=aio_preprocessor_name,
            profile=profile,
        )
        if resolved is _MISSING:
            default_value = _extract_default_from_schema(required_spec)
            if default_value is not _MISSING:
                resolved = default_value
        if resolved is _MISSING:
            raise RuntimeError(f"{node_name} requires unsupported input `{required_name}` for module `{module_key}`.")
        inputs[str(required_name)] = resolved

    for optional_name in optional_schema.keys():
        resolved = _build_node_parameter_value(
            str(optional_name),
            image_tensor=image_tensor,
            mask_tensor=mask_tensor,
            processor_res=processor_res,
            threshold_a=threshold_a,
            threshold_b=threshold_b,
            aio_preprocessor_name=aio_preprocessor_name,
            profile=profile,
        )
        if resolved is not _MISSING:
            inputs[str(optional_name)] = resolved

    instance = node_cls()
    function = _resolve_node_function(instance)
    if function is None:
        raise RuntimeError(f"{node_name} does not expose an invokable function.")

    # DEBUG HOTSPOT: this invocation is the exact seam where host-runtime preprocessor classes differ by signature.
    result = function(**inputs)
    primary = _extract_primary_node_output_payload(result)
    secondary = _extract_declared_secondary_outputs(result, profile=profile)
    return _coerce_image_tensor(primary), secondary


def _extract_declared_secondary_outputs(
    result: object,
    *,
    profile: ControlNetPreprocessorProfile | None,
) -> dict[str, tuple[object, ...]]:
    if profile is None or not profile.secondary_outputs or not isinstance(result, dict):
        return {}
    ui_payload = result.get("ui")
    if not isinstance(ui_payload, dict):
        return {}

    secondary: dict[str, tuple[object, ...]] = {}
    for key in profile.secondary_outputs:
        raw_value = ui_payload.get(key)
        if isinstance(raw_value, (list, tuple)):
            values = tuple(raw_value[:16])
        elif raw_value is None:
            values = ()
        else:
            values = (raw_value,)
        if values:
            secondary[key] = values
    return secondary


def _extract_primary_node_output_payload(result: object) -> object:
    payload = result
    for _ in range(4):
        if isinstance(payload, dict):
            if "result" in payload:
                payload = payload["result"]
                continue
            if "image" in payload:
                payload = payload["image"]
                continue
            if "images" in payload:
                payload = payload["images"]
                continue
            raise RuntimeError("Host preprocessor returned a dict without `result`/`image` payload.")
        if isinstance(payload, (tuple, list)):
            if not payload:
                raise RuntimeError("Host preprocessor returned an empty result container.")
            payload = payload[0]
            continue
        return payload
    raise RuntimeError("Unable to resolve host preprocessor image payload.")


def _select_aio_preprocessor_name(aio_cls: type[Any], module_key: str) -> str | None:
    required_schema, optional_schema = _extract_node_input_schema(aio_cls)
    _ = required_schema
    choices = _extract_aio_preprocessor_choices(optional_schema.get("preprocessor"))
    if not choices:
        return None

    for candidate in _MODULE_AIO_PREPROCESSOR_CANDIDATES.get(module_key, ()):
        normalized_candidate = _normalize_processor_token(candidate)
        for choice in choices:
            if _normalize_processor_token(choice) == normalized_candidate:
                return choice

    ranked = _rank_preprocessor_choices_by_keywords(choices, _MODULE_AIO_KEYWORDS.get(module_key, ()))
    if ranked:
        # DEBUG HOTSPOT: if AIO choice differs from expected integrated defaults, inspect keyword ranking behavior at this seam.
        return ranked[0]
    return None


def _resolve_host_preprocessor_candidates(
    module_key: str,
    host_mappings: dict[str, Any],
    *,
    preferred_candidates: tuple[str, ...] = (),
) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()

    def _push(node_name: str) -> None:
        if node_name in seen:
            return
        seen.add(node_name)
        ordered.append(node_name)

    for node_name in preferred_candidates:
        _push(node_name)
    for node_name in _MODULE_HOST_PREPROCESSOR_CANDIDATES.get(module_key, ()):
        _push(node_name)
    for node_name in _discover_dynamic_host_preprocessors(module_key, host_mappings):
        _push(node_name)
    return _prioritize_module_candidates(module_key, tuple(ordered))


def _prioritize_module_candidates(module_key: str, candidates: tuple[str, ...]) -> tuple[str, ...]:
    preferred = _MODULE_HOST_PREPROCESSOR_PRIORITIES.get(module_key, ())
    if not preferred or not candidates:
        return candidates

    candidate_lookup = {name.lower(): name for name in candidates}
    ordered: list[str] = []
    seen: set[str] = set()

    for preferred_name in preferred:
        matched = candidate_lookup.get(preferred_name.lower())
        if matched is None or matched in seen:
            continue
        ordered.append(matched)
        seen.add(matched)

    for candidate_name in candidates:
        if candidate_name in seen:
            continue
        ordered.append(candidate_name)
        seen.add(candidate_name)
    return tuple(ordered)


def _discover_dynamic_host_preprocessors(module_key: str, host_mappings: dict[str, Any]) -> tuple[str, ...]:
    keywords = _MODULE_HOST_NODE_KEYWORDS.get(module_key, ())
    if not keywords:
        return ()
    module_excludes = _MODULE_DYNAMIC_NODE_EXCLUDE_TOKENS.get(module_key, ())

    ranked: list[tuple[int, str]] = []
    for node_name in host_mappings.keys():
        normalized_node = _normalize_processor_token(node_name)
        if "preprocessor" not in normalized_node:
            continue
        if any(excluded in normalized_node for excluded in _HOST_NODE_EXCLUDE_TOKENS):
            continue
        if any(excluded in normalized_node for excluded in module_excludes):
            continue
        keyword_score = 0
        for index, keyword in enumerate(keywords):
            if keyword in normalized_node:
                keyword_score += 100 - index
        if keyword_score <= 0:
            continue
        score = keyword_score
        if normalized_node.endswith("preprocessor"):
            score += 10
        ranked.append((score, node_name))

    ranked.sort(key=lambda item: (-item[0], item[1].lower()))
    return tuple(name for _score, name in ranked)


def _extract_aio_preprocessor_choices(schema_entry: object) -> list[str]:
    if not isinstance(schema_entry, (list, tuple)) or not schema_entry:
        return []
    first = schema_entry[0]
    if not isinstance(first, list):
        return []
    return [str(item) for item in first if isinstance(item, str) and str(item).strip()]


def _rank_preprocessor_choices_by_keywords(choices: list[str], keywords: tuple[str, ...]) -> list[str]:
    ranked: list[tuple[int, str]] = []
    for choice in choices:
        normalized_choice = _normalize_processor_token(choice)
        if normalized_choice in {"none", "disabled"}:
            continue
        score = 0
        for index, keyword in enumerate(keywords):
            if keyword in normalized_choice:
                score += 100 - index
        if score > 0:
            ranked.append((score, choice))
    ranked.sort(key=lambda item: (-item[0], item[1].lower()))
    return [choice for _score, choice in ranked]


def _normalize_processor_token(value: object) -> str:
    token = str(value or "").strip().lower()
    token = re.sub(r"[^a-z0-9]+", "_", token).strip("_")
    return token


def _apply_fallback_filters(
    image_tensor: "torch.Tensor",
    *,
    module_key: str,
    processor_res: int,
    threshold_a: float,
    threshold_b: float,
) -> "torch.Tensor":
    working = _coerce_image_tensor(image_tensor).detach().cpu()
    bilinear, _nearest = _resolve_resize_filters()
    processed_frames: list["torch.Tensor"] = []

    for frame in working:
        frame_array = np.clip(frame.numpy() * 255.0, 0.0, 255.0).astype(np.uint8)
        frame_image = Image.fromarray(frame_array, mode="RGB")
        frame_image, original_size = _resize_for_processor(frame_image, int(processor_res), bilinear)
        frame_image = _apply_fallback_module_filter(
            frame_image,
            module_key=module_key,
            threshold_a=threshold_a,
            threshold_b=threshold_b,
        )
        if frame_image.size != original_size:
            frame_image = frame_image.resize(original_size, bilinear)
        processed_frames.append(torch.from_numpy(np.array(frame_image).astype(np.float32) / 255.0))

    return torch.stack(processed_frames, dim=0)


def _resize_for_processor(image_obj: "Image.Image", processor_res: int, bilinear: int) -> tuple["Image.Image", tuple[int, int]]:
    original_size = image_obj.size
    width, height = original_size
    if processor_res <= 0 or min(width, height) <= 0:
        return image_obj, original_size
    scale = float(processor_res) / float(min(width, height))
    target_size = (max(1, int(round(width * scale))), max(1, int(round(height * scale))))
    if target_size == original_size:
        return image_obj, original_size
    return image_obj.resize(target_size, bilinear), original_size


def _apply_fallback_module_filter(
    image_obj: "Image.Image",
    *,
    module_key: str,
    threshold_a: float,
    threshold_b: float,
) -> "Image.Image":
    del threshold_b
    if module_key in _PASSTHROUGH_MODULES or module_key in {"tile", "inpaint", "shuffle"}:
        return image_obj.convert("RGB")
    if module_key in {"depth", "normalmap", "segmentation"}:
        return image_obj.convert("L").convert("RGB")
    if module_key in {"blur"}:
        radius = max(0.1, min(float(threshold_a), 128.0) / 32.0)
        return image_obj.filter(ImageFilter.GaussianBlur(radius=radius)).convert("RGB")
    if module_key in {"canny", "lineart", "scribble", "softedge", "mlsd", "sketch", "openpose"}:
        return image_obj.convert("L").filter(ImageFilter.FIND_EDGES).convert("RGB")
    return image_obj.convert("RGB")
