from __future__ import annotations

import importlib
import logging
import os
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

try:
    import numpy as np
except Exception:  # pragma: no cover - optional runtime dependency
    np = None

try:
    import torch
except Exception:  # pragma: no cover - optional runtime dependency
    torch = None

from rookieui.services.model_inventory import (
    discover_model_inventory,
    ensure_native_ultralytics_model_paths,
)

_LOGGER = logging.getLogger("ComfyUI-RookieUI")

ADETAILER_RUNTIME_DISABLED = "disabled"
ADETAILER_RUNTIME_READY = "native_runtime_ready"
ADETAILER_RUNTIME_DEPENDENCY_MISSING = "native_runtime_dependency_missing"
ADETAILER_RUNTIME_MODEL_UNAVAILABLE = "native_runtime_model_unavailable"
ADETAILER_RUNTIME_FALLBACK = "deterministic_mask_fallback"

_ULTRALYTICS_FAMILIES = {"ultralytics_bbox", "ultralytics_segm"}
_ULTRALYTICS_MODEL_CACHE_ENV = "ROOKIEUI_ADETAILER_MODEL_CACHE_MAX_ITEMS"
_OPENCV_FACE_CASCADE = None
_ULTRALYTICS_MODEL_CACHE: OrderedDict[str, Any] = OrderedDict()
_ULTRALYTICS_MODEL_CACHE_LOCK = threading.Lock()
_OPENCV_FACE_CASCADE_LOCK = threading.Lock()


def _read_positive_int_env(name: str, default: int) -> int:
    raw_value = str(os.getenv(name, str(default))).strip()
    if not raw_value:
        return default
    try:
        parsed_value = int(raw_value)
    except ValueError:
        return default
    return parsed_value if parsed_value > 0 else default


_ULTRALYTICS_MODEL_CACHE_MAX_ITEMS = _read_positive_int_env(_ULTRALYTICS_MODEL_CACHE_ENV, 4)


@dataclass(slots=True)
class ADetailerDetectorRunResult:
    mask: Any
    runtime_state: str
    used_fallback: bool = False
    detection_count: int = 0
    diagnostics: list[str] = field(default_factory=list)


def _load_folder_paths_module() -> Any | None:
    try:
        import folder_paths
    except Exception:  # pragma: no cover - host-only dependency
        return None
    return ensure_native_ultralytics_model_paths(folder_paths)


def _import_optional_module(name: str) -> Any | None:
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def _has_tensor_runtime() -> bool:
    return torch is not None and np is not None


def _has_ultralytics_runtime() -> bool:
    return _has_tensor_runtime() and _import_optional_module("ultralytics") is not None


def _has_face_runtime() -> bool:
    if not _has_tensor_runtime():
        return False
    return _import_optional_module("cv2") is not None or _import_optional_module("mediapipe") is not None


def build_detector_runtime_availability() -> dict[str, str]:
    inventory = discover_model_inventory()
    availability = {"none": ADETAILER_RUNTIME_DISABLED}
    if _has_ultralytics_runtime():
        availability["ultralytics_bbox"] = (
            ADETAILER_RUNTIME_READY if inventory.ultralytics_bbox else ADETAILER_RUNTIME_MODEL_UNAVAILABLE
        )
        availability["ultralytics_segm"] = (
            ADETAILER_RUNTIME_READY if inventory.ultralytics_segm else ADETAILER_RUNTIME_MODEL_UNAVAILABLE
        )
    else:
        availability["ultralytics_bbox"] = ADETAILER_RUNTIME_DEPENDENCY_MISSING
        availability["ultralytics_segm"] = ADETAILER_RUNTIME_DEPENDENCY_MISSING
    availability["mediapipe_face"] = ADETAILER_RUNTIME_READY if _has_face_runtime() else ADETAILER_RUNTIME_DEPENDENCY_MISSING
    return availability


def detector_runtime_is_degraded(detector_family: str) -> bool:
    runtime_state = build_detector_runtime_availability().get(str(detector_family or "").strip().lower())
    return runtime_state not in {ADETAILER_RUNTIME_DISABLED, ADETAILER_RUNTIME_READY}


def summarize_detector_runtime(detector_families: list[str]) -> str:
    active_families = [
        str(family or "").strip().lower()
        for family in detector_families
        if str(family or "").strip().lower() not in {"", "none"}
    ]
    if not active_families:
        return ADETAILER_RUNTIME_DISABLED
    availability = build_detector_runtime_availability()
    if all(availability.get(family) == ADETAILER_RUNTIME_READY for family in active_families):
        return "rookieui_native_detector_runtime"
    return "rookieui_native_detector_runtime_with_fallback"


def _fallback_shape_for_family(detector_family: str, detector: str) -> tuple[float, float, float]:
    family = str(detector_family or "").strip().lower()
    detector_name = str(detector or "").strip().lower()
    if family == "mediapipe_face" or "face" in detector_name:
        return 0.34, 0.28, 0.08
    if family == "ultralytics_segm":
        return 0.44, 0.62, 0.04
    if "hand" in detector_name:
        return 0.26, 0.22, 0.10
    if "person" in detector_name:
        return 0.46, 0.74, 0.02
    return 0.38, 0.38, 0.05


def _build_fallback_mask_batch(
    image,
    *,
    detector: str,
    detector_family: str,
    confidence: float,
    x_offset: int,
    y_offset: int,
):
    batch_size, height, width = int(image.shape[0]), int(image.shape[1]), int(image.shape[2])
    ratio_x, ratio_y, confidence_floor = _fallback_shape_for_family(detector_family, detector)
    confidence_scale = max(confidence_floor, min(1.0, float(confidence)))
    yy, xx = torch.meshgrid(
        torch.linspace(-1.0, 1.0, height, dtype=image.dtype, device=image.device),
        torch.linspace(-1.0, 1.0, width, dtype=image.dtype, device=image.device),
        indexing="ij",
    )
    center_x = max(-0.95, min(0.95, float(x_offset) / max(1.0, width / 2.0)))
    center_y = max(-0.95, min(0.95, float(y_offset) / max(1.0, height / 2.0)))
    ellipse = (((xx - center_x) / max(0.01, ratio_x)) ** 2) + (((yy - center_y) / max(0.01, ratio_y)) ** 2)
    return (ellipse <= (1.0 + confidence_scale * 0.25)).to(dtype=image.dtype).unsqueeze(0).repeat(batch_size, 1, 1)


def _resolve_ultralytics_model_path(detector: str, detector_family: str) -> str | None:
    folder_paths_module = _load_folder_paths_module()
    if folder_paths_module is None:
        return None
    get_full_path = getattr(folder_paths_module, "get_full_path", None)
    if not callable(get_full_path):
        return None

    selector = str(detector or "").strip().replace("\\", "/")
    if not selector:
        return None

    candidates = [("ultralytics", selector)]
    family = str(detector_family or "").strip().lower()
    if family == "ultralytics_bbox":
        candidates.extend(
            [
                ("ultralytics_bbox", selector.removeprefix("bbox/")),
                ("ultralytics", selector if selector.startswith("bbox/") else f"bbox/{selector}"),
            ]
        )
    elif family == "ultralytics_segm":
        candidates.extend(
            [
                ("ultralytics_segm", selector.removeprefix("segm/")),
                ("ultralytics", selector if selector.startswith("segm/") else f"segm/{selector}"),
            ]
        )

    for folder_name, candidate in candidates:
        try:
            full_path = get_full_path(folder_name, candidate)
        except Exception:
            full_path = None
        if isinstance(full_path, str) and full_path.strip():
            return full_path
    return None


def _load_ultralytics_model(model_path: str) -> Any:
    # IMPORTANT: keep cache mutation serialized; overlapping detector requests share this process-global runtime cache.
    with _ULTRALYTICS_MODEL_CACHE_LOCK:
        cached = _ULTRALYTICS_MODEL_CACHE.get(model_path)
        if cached is not None:
            _ULTRALYTICS_MODEL_CACHE.move_to_end(model_path)
            return cached

        ultralytics_module = _import_optional_module("ultralytics")
        if ultralytics_module is None:
            raise RuntimeError("ultralytics is unavailable.")

        model = ultralytics_module.YOLO(model_path)
        _ULTRALYTICS_MODEL_CACHE[model_path] = model
        _ULTRALYTICS_MODEL_CACHE.move_to_end(model_path)
        while len(_ULTRALYTICS_MODEL_CACHE) > _ULTRALYTICS_MODEL_CACHE_MAX_ITEMS:
            _ULTRALYTICS_MODEL_CACHE.popitem(last=False)
        return model


def _parse_detector_class_filter(detector_classes: str) -> set[str]:
    values = {
        token.strip().lower()
        for token in str(detector_classes or "").split(",")
        if token and token.strip()
    }
    values.discard("all")
    return values


def _image_tensor_to_uint8_rgb(image_tensor) -> Any:
    image_np = image_tensor.detach().cpu().numpy()
    if image_np.dtype != np.uint8:
        image_np = np.clip(image_np, 0.0, 1.0)
        image_np = (image_np * 255.0).round().astype(np.uint8)
    return image_np


def _empty_mask(height: int, width: int, *, dtype: Any, device: Any):
    return torch.zeros((height, width), dtype=dtype, device=device)


def _mask_from_bbox(
    bbox: tuple[float, float, float, float],
    *,
    height: int,
    width: int,
    dtype: Any,
    device: Any,
):
    x1, y1, x2, y2 = bbox
    xi1 = max(0, min(width, int(round(x1))))
    yi1 = max(0, min(height, int(round(y1))))
    xi2 = max(xi1, min(width, int(round(x2))))
    yi2 = max(yi1, min(height, int(round(y2))))
    mask = _empty_mask(height, width, dtype=dtype, device=device)
    if xi2 > xi1 and yi2 > yi1:
        mask[yi1:yi2, xi1:xi2] = 1.0
    return mask


def _mask_from_segm(mask_data: Any, *, height: int, width: int, dtype: Any, device: Any):
    if torch.is_tensor(mask_data):
        mask_tensor = mask_data.detach().to(device="cpu", dtype=torch.float32)
    else:
        mask_tensor = torch.from_numpy(np.asarray(mask_data, dtype=np.float32))
    if mask_tensor.ndim == 2:
        mask_tensor = mask_tensor.unsqueeze(0).unsqueeze(0)
    elif mask_tensor.ndim == 3:
        mask_tensor = mask_tensor.unsqueeze(0)
    resized = torch.nn.functional.interpolate(mask_tensor, size=(height, width), mode="bilinear", align_corners=False)
    return (resized.squeeze(0).squeeze(0) > 0.5).to(dtype=dtype, device=device)


def _run_ultralytics_detection(
    image_tensor,
    *,
    detector: str,
    detector_family: str,
    detector_classes: str,
    confidence: float,
):
    height, width = int(image_tensor.shape[0]), int(image_tensor.shape[1])
    dtype = image_tensor.dtype
    device = image_tensor.device
    model_path = _resolve_ultralytics_model_path(detector, detector_family)
    if not model_path:
        return None, ADETAILER_RUNTIME_MODEL_UNAVAILABLE, ["model_unavailable"]

    model = _load_ultralytics_model(model_path)
    result = model(_image_tensor_to_uint8_rgb(image_tensor), conf=float(confidence), verbose=False)[0]
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return _empty_mask(height, width, dtype=dtype, device=device), ADETAILER_RUNTIME_READY, []

    names = getattr(result, "names", {}) or {}
    class_filter = _parse_detector_class_filter(detector_classes)
    masks: list[Any] = []
    segm_data = getattr(getattr(result, "masks", None), "data", None)
    for index, box in enumerate(boxes):
        label = str(names.get(int(box.cls.item()), "")).strip().lower() if getattr(box, "cls", None) is not None else ""
        if class_filter and label not in class_filter:
            continue
        if detector_family == "ultralytics_segm" and segm_data is not None and len(segm_data) > index:
            masks.append(_mask_from_segm(segm_data[index], height=height, width=width, dtype=dtype, device=device))
        else:
            xyxy = box.xyxy[0].detach().cpu().tolist()
            masks.append(_mask_from_bbox(tuple(xyxy), height=height, width=width, dtype=dtype, device=device))

    if not masks:
        return _empty_mask(height, width, dtype=dtype, device=device), ADETAILER_RUNTIME_READY, []

    combined = torch.clamp(torch.stack(masks, dim=0).amax(dim=0), 0.0, 1.0)
    return combined, ADETAILER_RUNTIME_READY, []


def _load_cv2_face_cascade(cv2_module: Any) -> Any | None:
    global _OPENCV_FACE_CASCADE
    if _OPENCV_FACE_CASCADE is not None:
        return _OPENCV_FACE_CASCADE
    # IMPORTANT: keep singleton initialization under one lock so concurrent detect requests cannot observe partial setup.
    with _OPENCV_FACE_CASCADE_LOCK:
        if _OPENCV_FACE_CASCADE is not None:
            return _OPENCV_FACE_CASCADE
        data_root = getattr(getattr(cv2_module, "data", None), "haarcascades", "")
        if not data_root:
            return None
        cascade = cv2_module.CascadeClassifier(f"{data_root}haarcascade_frontalface_default.xml")
        if cascade.empty():
            return None
        _OPENCV_FACE_CASCADE = cascade
        return cascade


def _run_face_detection(image_tensor, *, confidence: float):
    cv2_module = _import_optional_module("cv2")
    if cv2_module is None:
        return None, ADETAILER_RUNTIME_DEPENDENCY_MISSING, ["opencv_missing"]

    cascade = _load_cv2_face_cascade(cv2_module)
    if cascade is None:
        return None, ADETAILER_RUNTIME_DEPENDENCY_MISSING, ["opencv_face_cascade_unavailable"]

    rgb = _image_tensor_to_uint8_rgb(image_tensor)
    gray = cv2_module.cvtColor(rgb, cv2_module.COLOR_RGB2GRAY)
    min_neighbors = max(3, int(round(3 + float(confidence) * 4)))
    detections = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=min_neighbors, minSize=(16, 16))
    height, width = int(image_tensor.shape[0]), int(image_tensor.shape[1])
    dtype = image_tensor.dtype
    device = image_tensor.device
    masks = [
        _mask_from_bbox((x, y, x + w, y + h), height=height, width=width, dtype=dtype, device=device)
        for (x, y, w, h) in detections
    ]
    if not masks:
        return _empty_mask(height, width, dtype=dtype, device=device), ADETAILER_RUNTIME_READY, []
    combined = torch.clamp(torch.stack(masks, dim=0).amax(dim=0), 0.0, 1.0)
    return combined, ADETAILER_RUNTIME_READY, []


def detect_adetailer_mask(
    image,
    *,
    detector: str,
    detector_family: str,
    detector_classes: str,
    confidence: float,
    x_offset: int,
    y_offset: int,
) -> ADetailerDetectorRunResult:
    if torch is None or np is None:
        raise RuntimeError("ADetailer detector runtime requires torch and numpy in the active environment.")
    if image.ndim != 4:
        raise ValueError("ADetailer detector image tensor must be NHWC.")

    detector_key = str(detector or "").strip()
    family = str(detector_family or "").strip().lower()
    batch_size, height, width = int(image.shape[0]), int(image.shape[1]), int(image.shape[2])
    if not detector_key or detector_key.lower() == "none" or family == "none":
        return ADetailerDetectorRunResult(
            mask=torch.zeros((batch_size, height, width), dtype=image.dtype, device=image.device),
            runtime_state=ADETAILER_RUNTIME_DISABLED,
        )

    detector_masks: list[Any] = []
    diagnostics: list[str] = []
    used_fallback = False
    detection_count = 0
    runtime_state = build_detector_runtime_availability().get(family, ADETAILER_RUNTIME_DEPENDENCY_MISSING)

    for batch_index in range(batch_size):
        image_tensor = image[batch_index]
        runtime_mask = None
        batch_diagnostics: list[str] = []
        batch_state = runtime_state

        try:
            if family in _ULTRALYTICS_FAMILIES and runtime_state == ADETAILER_RUNTIME_READY:
                runtime_mask, batch_state, batch_diagnostics = _run_ultralytics_detection(
                    image_tensor,
                    detector=detector_key,
                    detector_family=family,
                    detector_classes=detector_classes,
                    confidence=confidence,
                )
            elif family == "mediapipe_face" and runtime_state == ADETAILER_RUNTIME_READY:
                runtime_mask, batch_state, batch_diagnostics = _run_face_detection(
                    image_tensor,
                    confidence=confidence,
                )
        except Exception as exc:  # pragma: no cover - hardware/runtime-specific failures
            batch_state = ADETAILER_RUNTIME_FALLBACK
            batch_diagnostics = [f"runtime_exception:{type(exc).__name__}"]
            _LOGGER.warning(
                "RookieUI ADetailer detector runtime degraded for detector=%s family=%s.",
                detector_key,
                family,
                exc_info=True,
            )

        if runtime_mask is None and batch_state != ADETAILER_RUNTIME_READY:
            runtime_mask = _build_fallback_mask_batch(
                image_tensor.unsqueeze(0),
                detector=detector_key,
                detector_family=family,
                confidence=confidence,
                x_offset=x_offset,
                y_offset=y_offset,
            )[0]
            used_fallback = True
        elif runtime_mask is None:
            runtime_mask = _empty_mask(height, width, dtype=image.dtype, device=image.device)

        detection_count += int((runtime_mask > 0).any().item())
        detector_masks.append(torch.clamp(runtime_mask, 0.0, 1.0))
        diagnostics.extend(batch_diagnostics)

    if used_fallback:
        runtime_state = ADETAILER_RUNTIME_FALLBACK
    return ADetailerDetectorRunResult(
        mask=torch.stack(detector_masks, dim=0),
        runtime_state=runtime_state,
        used_fallback=used_fallback,
        detection_count=detection_count,
        diagnostics=diagnostics,
    )
