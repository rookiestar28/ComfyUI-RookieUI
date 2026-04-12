from __future__ import annotations

import base64
import io
import logging
import re
from dataclasses import dataclass
from typing import Any

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
        "Metric3D-DepthMapPreprocessor",
        "MeshGraphormer-DepthMapPreprocessor",
    ),
    "normalmap": (
        "MiDaS-NormalMapPreprocessor",
        "BAE-NormalMapPreprocessor",
        "DSINE-NormalMapPreprocessor",
        "Metric3D-NormalMapPreprocessor",
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
    "depth": (
        "MiDaS-DepthMapPreprocessor",
        "DepthAnythingV2Preprocessor",
        "DepthAnythingPreprocessor",
        "Zoe-DepthMapPreprocessor",
        "LeReS-DepthMapPreprocessor",
    ),
    "normalmap": ("MiDaS-NormalMapPreprocessor", "BAE-NormalMapPreprocessor", "DSINE-NormalMapPreprocessor"),
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
    "depth": ("depthanythingv2", "depthanything", "midas", "zoe", "leres", "meshgraphormer", "metric3d", "depth"),
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


@dataclass(frozen=True)
class ControlNetRuntimeResult:
    image: "torch.Tensor"
    backend: str
    processor_name: str
    used_fallback: bool
    diagnostics: tuple[str, ...] = ()


def runtime_dependencies_available() -> bool:
    return all(dependency is not None for dependency in (np, torch, Image, ImageFilter))


def normalize_module_key(module_value: object) -> str:
    token = str(module_value or "none").strip().lower().replace(" ", "_")
    token = token.replace("-", "_")
    aliases = {
        "ip_adapter": "ipadapter",
        "instant_id": "instantid",
        "t2i_adapter": "t2iadapter",
        "normal_map": "normalmap",
    }
    return aliases.get(token, token or "none")


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
) -> ControlNetRuntimeResult:
    _require_runtime_dependencies()
    normalized_module = normalize_module_key(module)
    source = _coerce_image_tensor(image_tensor)
    normalized_mask = _coerce_mask_tensor(mask_tensor, image_tensor=source) if mask_tensor is not None else None
    diagnostics: list[str] = []

    if normalized_module in _PASSTHROUGH_MODULES:
        return ControlNetRuntimeResult(
            image=source,
            backend="passthrough_module",
            processor_name=normalized_module,
            used_fallback=False,
            diagnostics=(),
        )

    host_mappings = _resolve_host_node_class_mappings()

    for node_name in _resolve_host_preprocessor_candidates(normalized_module, host_mappings):
        if node_name not in host_mappings:
            continue
        try:
            processed = _run_host_node_preprocessor(
                node_name=node_name,
                node_cls=host_mappings[node_name],
                image_tensor=source,
                mask_tensor=normalized_mask,
                module_key=normalized_module,
                processor_res=processor_res,
                threshold_a=threshold_a,
                threshold_b=threshold_b,
                aio_preprocessor_name=None,
            )
            return ControlNetRuntimeResult(
                image=processed,
                backend="comfy_host_preprocessor",
                processor_name=node_name,
                used_fallback=False,
                diagnostics=tuple(diagnostics),
            )
        except Exception as exc:  # pragma: no cover - runtime-dependent host node behavior
            diagnostics.append(f"{node_name}: {exc}")
            continue

    aio_cls = host_mappings.get("AIO_Preprocessor")
    if aio_cls is not None:
        aio_name = _select_aio_preprocessor_name(aio_cls, normalized_module)
        if aio_name:
            try:
                processed = _run_host_node_preprocessor(
                    node_name="AIO_Preprocessor",
                    node_cls=aio_cls,
                    image_tensor=source,
                    mask_tensor=normalized_mask,
                    module_key=normalized_module,
                    processor_res=processor_res,
                    threshold_a=threshold_a,
                    threshold_b=threshold_b,
                    aio_preprocessor_name=aio_name,
                )
                return ControlNetRuntimeResult(
                    image=processed,
                    backend="comfy_host_preprocessor_aio",
                    processor_name=aio_name,
                    used_fallback=False,
                    diagnostics=tuple(diagnostics),
                )
            except Exception as exc:  # pragma: no cover - runtime-dependent host node behavior
                diagnostics.append(f"AIO_Preprocessor({aio_name}): {exc}")

    fallback = _apply_fallback_filters(
        source,
        module_key=normalized_module,
        processor_res=processor_res,
        threshold_a=threshold_a,
        threshold_b=threshold_b,
    )
    return ControlNetRuntimeResult(
        image=fallback,
        backend="rookieui_internal_fallback",
        processor_name=normalized_module,
        used_fallback=True,
        diagnostics=tuple(diagnostics),
    )


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
        tensor = tensor[:, :, :, :3]

    if tensor.max().item() > 1.0 or tensor.min().item() < 0.0:
        tensor = torch.clamp(tensor, 0.0, 255.0) / 255.0
    return torch.clamp(tensor, 0.0, 1.0)


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
) -> object:
    key = str(parameter_name or "").strip()
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
        )
        if resolved is not _MISSING:
            inputs[str(optional_name)] = resolved

    instance = node_cls()
    function = _resolve_node_function(instance)
    if function is None:
        raise RuntimeError(f"{node_name} does not expose an invokable function.")

    # DEBUG HOTSPOT: this invocation is the exact seam where host-runtime preprocessor classes differ by signature.
    result = function(**inputs)
    if isinstance(result, tuple):
        primary = result[0]
    else:
        primary = result
    return _coerce_image_tensor(primary)


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
        # DEBUG HOTSPOT: if AIO choice differs from expected Forge-like defaults, inspect keyword ranking behavior at this seam.
        return ranked[0]
    return None


def _resolve_host_preprocessor_candidates(module_key: str, host_mappings: dict[str, Any]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()

    def _push(node_name: str) -> None:
        if node_name in seen:
            return
        seen.add(node_name)
        ordered.append(node_name)

    for node_name in _MODULE_HOST_PREPROCESSOR_CANDIDATES.get(module_key, ()):
        _push(node_name)
    for node_name in _discover_dynamic_host_preprocessors(module_key, host_mappings):
        _push(node_name)
    return tuple(ordered)


def _discover_dynamic_host_preprocessors(module_key: str, host_mappings: dict[str, Any]) -> tuple[str, ...]:
    keywords = _MODULE_HOST_NODE_KEYWORDS.get(module_key, ())
    if not keywords:
        return ()

    ranked: list[tuple[int, str]] = []
    for node_name in host_mappings.keys():
        normalized_node = _normalize_processor_token(node_name)
        if "preprocessor" not in normalized_node:
            continue
        if any(excluded in normalized_node for excluded in _HOST_NODE_EXCLUDE_TOKENS):
            continue
        score = 0
        if normalized_node.endswith("preprocessor"):
            score += 10
        for index, keyword in enumerate(keywords):
            if keyword in normalized_node:
                score += 100 - index
        if score <= 0:
            continue
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
