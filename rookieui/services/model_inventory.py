from __future__ import annotations

import logging
import ntpath
import os
import threading
import time
from typing import Any

from rookieui.contracts.model_family_registry import get_model_family_registry_entry
from rookieui.contracts.models import ModelInventorySnapshot, PRIMARY_MODEL_CATEGORY_BY_FAMILY

_HOST_MODEL_FOLDERS = (
    "checkpoints",
    "clip",
    "clip_vision",
    "controlnet",
    "diffusion_models",
    "embeddings",
    "loras",
    "text_encoders",
    "ultralytics",
    "unet",
    "upscale_models",
    "vae",
)
_INVENTORY_CACHE_TTL_SECONDS = 5.0
_inventory_cache_lock = threading.Lock()
_inventory_cache_snapshot: ModelInventorySnapshot | None = None
_inventory_cache_at: float = 0.0
_LOGGER = logging.getLogger("ComfyUI-RookieUI")
_PROFILE_DIFFUSION_MODEL_HINTS: dict[str, tuple[str, ...]] = {
    "anima": ("anima",),
    "chroma": ("chroma",),
    "ernie_image": ("ernie", "image"),
    "ernie_image_turbo": ("ernie", "turbo"),
    "flux": ("flux",),
    "hidream_i1_dev_fp8": ("hidream", "dev"),
    "hidream_i1_fast": ("hidream", "fast"),
    "hidream_i1_full": ("hidream", "full"),
    "klein_4b_distilled": ("klein", "4b"),
    "klein_4b": ("klein", "4b"),
    "klein_9b_distilled": ("klein", "9b"),
    "klein_9b": ("klein", "9b"),
    "longcat_image": ("longcat",),
    "qwen_image": ("qwen", "2512"),
    "z_image": ("z-image", "z_image", "zimage"),
    "z_image_turbo": ("z-image", "z_image", "zimage", "turbo"),
}
_PROFILE_DIFFUSION_MODEL_PRIORITY_HINTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "anima": (("anima",),),
    "chroma": (("chroma1",), ("chroma",)),
    "ernie_image": (("ernie", "image"), ("ernie",)),
    "ernie_image_turbo": (("ernie", "image", "turbo"), ("ernie", "turbo"), ("ernie",)),
    "flux": (("flux1", "dev"), ("flux1",), ("flux", "dev"), ("flux",)),
    "hidream_i1_dev_fp8": (("hidream", "dev", "fp8"), ("hidream", "i1", "dev"), ("hidream", "dev")),
    "hidream_i1_fast": (("hidream", "fast"), ("hidream", "i1", "fast")),
    "hidream_i1_full": (("hidream", "full"), ("hidream", "i1", "full"), ("hidream", "i1")),
    "klein_4b_distilled": (("flux", "2", "klein", "4b"), ("klein", "4b")),
    "klein_4b": (("klein", "base", "4b"), ("flux", "2", "klein", "base", "4b"), ("klein", "4b")),
    "klein_9b_distilled": (("flux", "2", "klein", "9b"), ("klein", "9b")),
    "klein_9b": (("klein", "base", "9b"), ("flux", "2", "klein", "base", "9b"), ("klein", "9b")),
    "longcat_image": (("longcat",),),
    "qwen_image": (("qwen", "image", "2512"), ("qwen", "2512", "fp8"), ("qwen", "2512"), ("qwen", "image")),
    "z_image": (("z_image",), ("z-image",), ("z", "image")),
    "z_image_turbo": (("z_image", "turbo"), ("z-image", "turbo"), ("z", "image", "turbo")),
}
_PROFILE_DIFFUSION_MODEL_DENY_HINTS: dict[str, tuple[str, ...]] = {
    "klein_4b_distilled": ("base", "9b"),
    "klein_4b": ("distill", "distilled", "9b"),
    "klein_9b_distilled": ("base", "4b"),
    "klein_9b": ("distill", "distilled", "4b"),
    "qwen_image": ("lightning", "lora", "2step", "4step", "8step", "distill", "distilled"),
}
_PROFILE_TEXT_ENCODER_HINTS: dict[str, tuple[str, ...]] = {
    "anima": ("anima",),
    "chroma": ("t5", "chroma"),
    "ernie_image": ("ernie", "ministral", "3_3b", "ministral3"),
    "ernie_image_turbo": ("ernie", "ministral", "3_3b", "ministral3"),
    "flux": ("clip_l", "t5"),
    "hidream_i1_dev_fp8": ("hidream", "clip"),
    "hidream_i1_fast": ("hidream", "clip"),
    "hidream_i1_full": ("hidream", "clip"),
    "klein_4b_distilled": ("qwen", "4b", "klein"),
    "klein_4b": ("qwen", "4b", "klein"),
    "klein_9b_distilled": ("qwen", "8b", "klein"),
    "klein_9b": ("qwen", "8b", "klein"),
    "longcat_image": ("longcat", "qwen", "2.5", "vl"),
    "qwen_image": ("qwen", "2.5", "vl"),
    "z_image": ("qwen", "3", "4b", "z"),
    "z_image_turbo": ("qwen", "3", "4b", "z"),
}
_PROFILE_TEXT_ENCODER_PRIORITY_HINTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "anima": (("qwen_3_06b",), ("anima",), ("qwen",)),
    "chroma": (("t5xxl", "fp8"), ("t5xxl",), ("chroma",), ("t5",)),
    "ernie_image": (("ministral3_3b",), ("ministral_3_3b",), ("ministral", "3", "3b"), ("ernie",)),
    "ernie_image_turbo": (("ministral3_3b",), ("ministral_3_3b",), ("ministral", "3", "3b"), ("ernie",)),
    "flux": (("clip_l",), ("clip", "l"), ("t5xxl",), ("flux",), ("t5",)),
    "hidream_i1_dev_fp8": (("clip_l_hidream",), ("hidream", "clip"), ("hidream",), ("llama",), ("t5xxl",)),
    "hidream_i1_fast": (("clip_l_hidream",), ("hidream", "clip"), ("hidream",), ("llama",), ("t5xxl",)),
    "hidream_i1_full": (("clip_l_hidream",), ("hidream", "clip"), ("hidream",), ("llama",), ("t5xxl",)),
    "klein_4b_distilled": (("qwen_3_4b",), ("klein", "4b"), ("klein",), ("qwen",)),
    "klein_4b": (("qwen_3_4b",), ("klein", "4b"), ("klein",), ("qwen",)),
    "klein_9b_distilled": (("qwen_3_8b",), ("klein", "9b"), ("klein",), ("qwen",)),
    "klein_9b": (("qwen_3_8b",), ("klein", "9b"), ("klein",), ("qwen",)),
    "longcat_image": (("qwen_2.5_vl_7b",), ("longcat",), ("qwen", "vl"), ("qwen",)),
    "qwen_image": (("qwen_2.5_vl_7b",), ("qwen_2.5_vl",), ("qwen", "image"), ("qwen",)),
    "z_image": (("qwen_3_4b",), ("z_image",), ("z-image",), ("lumina",), ("qwen",)),
    "z_image_turbo": (("qwen_3_4b",), ("z_image", "turbo"), ("z-image", "turbo"), ("lumina",), ("qwen",)),
}
_PROFILE_TEXT_ENCODER_SEQUENCE_PRIORITY_HINTS: dict[str, tuple[tuple[tuple[str, ...], ...], ...]] = {
    "flux": (
        (("clip_l",), ("t5xxl", "fp16")),
        (("clip_l",), ("t5xxl",)),
    ),
    "hidream_i1_dev_fp8": (
        (
            ("clip_l_hidream",),
            ("clip_g_hidream",),
            ("t5xxl", "fp8"),
            ("llama", "8b", "instruct"),
        ),
    ),
    "hidream_i1_fast": (
        (
            ("clip_l_hidream",),
            ("clip_g_hidream",),
            ("t5xxl", "fp8"),
            ("llama", "8b", "instruct"),
        ),
    ),
    "hidream_i1_full": (
        (
            ("clip_l_hidream",),
            ("clip_g_hidream",),
            ("t5xxl", "fp8"),
            ("llama", "8b", "instruct"),
        ),
    ),
}
_PROFILE_AUX_TEXT_ENCODER_PRIORITY_HINTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "ernie_image": (
        ("ernie", "prompt", "enhancer"),
        ("prompt", "enhancer"),
    ),
    "ernie_image_turbo": (
        ("ernie", "prompt", "enhancer"),
        ("prompt", "enhancer"),
    ),
}
_PROFILE_TEMPLATE_LORA_PRIORITY_HINTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "qwen_image": (
        ("wuli", "qwen", "image", "2512", "turbo", "lora"),
        ("qwen", "image", "2512", "turbo", "lora"),
        ("qwen", "image", "2512", "lora"),
    ),
}
_PROFILE_VAE_HINTS: dict[str, tuple[str, ...]] = {
    "anima": ("anima",),
    "chroma": ("ae", "chroma"),
    "ernie_image": ("ernie", "flux2"),
    "ernie_image_turbo": ("ernie", "flux2"),
    "flux": ("flux", "ae"),
    "hidream_i1_dev_fp8": ("ae", "hidream"),
    "hidream_i1_fast": ("ae", "hidream"),
    "hidream_i1_full": ("ae", "hidream"),
    "klein_4b_distilled": ("flux2", "vae", "klein", "4b"),
    "klein_4b": ("flux2", "vae", "klein", "4b"),
    "klein_9b_distilled": ("encoder", "decoder", "9b", "klein"),
    "klein_9b": ("encoder", "decoder", "9b", "klein"),
    "longcat_image": ("ae", "longcat"),
    "qwen_image": ("qwen", "qwen-image", "qwen_image"),
    "z_image": ("ae", "z-image", "z_image"),
    "z_image_turbo": ("ae", "z-image", "z_image", "turbo"),
}
_PROFILE_VAE_PRIORITY_HINTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "anima": (("qwen_image", "vae"), ("qwen", "image", "vae"), ("anima", "vae"), ("anima",)),
    "chroma": (("ae",), ("chroma",)),
    "ernie_image": (("flux2", "vae"), ("ernie", "vae"), ("ernie",)),
    "ernie_image_turbo": (("flux2", "vae"), ("ernie", "vae"), ("ernie",)),
    "flux": (("ae",), ("flux", "vae"), ("flux",)),
    "hidream_i1_dev_fp8": (("ae",), ("hidream",)),
    "hidream_i1_fast": (("ae",), ("hidream",)),
    "hidream_i1_full": (("ae",), ("hidream",)),
    "klein_4b_distilled": (("flux2", "vae"), ("klein", "4b"), ("flux2",)),
    "klein_4b": (("flux2", "vae"), ("klein", "4b"), ("flux2",)),
    "klein_9b_distilled": (("full", "encoder", "small", "decoder"), ("klein", "9b"), ("encoder", "decoder")),
    "klein_9b": (("full", "encoder", "small", "decoder"), ("klein", "9b"), ("encoder", "decoder")),
    "longcat_image": (("ae",), ("longcat",)),
    "qwen_image": (("qwen", "vae"), ("qwen", "image"), ("qwen",)),
    "z_image": (("ae",), ("z-image",), ("z_image",)),
    "z_image_turbo": (("ae",), ("z-image", "turbo"), ("z_image", "turbo"), ("z-image",), ("z_image",)),
}
_PROFILE_VAE_DENY_HINTS: dict[str, tuple[str, ...]] = {
    "chroma": ("qwen",),
    "ernie_image": ("qwen",),
    "ernie_image_turbo": ("qwen",),
    "flux": ("qwen",),
    "hidream_i1_dev_fp8": ("qwen",),
    "hidream_i1_fast": ("qwen",),
    "hidream_i1_full": ("qwen",),
    "longcat_image": ("qwen",),
    "z_image": ("qwen",),
    "z_image_turbo": ("qwen",),
}
_NATIVE_ULTRALYTICS_MODEL_FOLDERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ultralytics", ("ultralytics",)),
    ("ultralytics_bbox", ("ultralytics", "bbox")),
    ("ultralytics_segm", ("ultralytics", "segm")),
)


def _join_models_dir_path(models_dir: str, *relative_parts: str) -> str:
    # CRITICAL: folder_paths.models_dir may come from a Windows-style host snapshot even when tests run on Linux;
    # do not use the runner OS path module blindly or native detector paths will pick mixed separators.
    path_module = ntpath if "\\" in models_dir or (len(models_dir) >= 2 and models_dir[1] == ":") else os.path
    return path_module.normpath(path_module.join(models_dir, *relative_parts))


def ensure_native_ultralytics_model_paths(folder_paths_module: Any | None) -> Any | None:
    if folder_paths_module is None:
        return None

    models_dir = getattr(folder_paths_module, "models_dir", None)
    add_model_folder_path = getattr(folder_paths_module, "add_model_folder_path", None)
    folder_names_and_paths = getattr(folder_paths_module, "folder_names_and_paths", None)
    supported_pt_extensions = getattr(folder_paths_module, "supported_pt_extensions", None)
    if not isinstance(models_dir, str) or not callable(add_model_folder_path):
        return folder_paths_module

    # IMPORTANT: register native detector model folders here so RookieUI does not require an external detector pack
    # just to make host `folder_paths` aware of Ultralytics bbox/segm model locations.
    for folder_name, relative_parts in _NATIVE_ULTRALYTICS_MODEL_FOLDERS:
        full_path = _join_models_dir_path(models_dir, *relative_parts)
        try:
            add_model_folder_path(folder_name, full_path, is_default=True)
        except TypeError:
            add_model_folder_path(folder_name, full_path)
        if isinstance(folder_names_and_paths, dict) and folder_name in folder_names_and_paths:
            paths, extensions = folder_names_and_paths[folder_name]
            if isinstance(paths, list) and full_path in paths and isinstance(supported_pt_extensions, set):
                if not isinstance(extensions, set):
                    extensions = set()
                extensions.update(supported_pt_extensions)
                folder_names_and_paths[folder_name] = (paths, extensions)
    return folder_paths_module


def _load_folder_paths_module() -> Any:
    try:
        import folder_paths
    except ImportError:
        return None
    return ensure_native_ultralytics_model_paths(folder_paths)


def _safe_get_filename_list(folder_paths_module: Any, folder_name: str) -> list[str]:
    if folder_paths_module is None:
        return []

    getter = getattr(folder_paths_module, "get_filename_list", None)
    if not callable(getter):
        return []

    try:
        values = getter(folder_name)
    except Exception:
        _LOGGER.debug(
            "RookieUI inventory fallback for folder '%s' due to host getter exception.",
            folder_name,
            exc_info=True,
        )
        return []

    if not isinstance(values, list):
        return []
    return values


def _partition_ultralytics_models(selectors: list[str]) -> tuple[list[str], list[str]]:
    bbox: list[str] = []
    segm: list[str] = []
    for selector in selectors:
        normalized = _normalize_selector_token(selector)
        if "-seg" in normalized or "_seg" in normalized or "segm" in normalized:
            segm.append(selector)
        else:
            bbox.append(selector)
    return bbox, segm


def _build_inventory_snapshot(module: Any | None) -> ModelInventorySnapshot:
    # CRITICAL: keep these folder names aligned with ComfyUI host folder_paths keys; renaming them breaks host inventory discovery for non-checkpoint families.
    inventory_map = {
        folder_name: _safe_get_filename_list(module, folder_name)
        for folder_name in _HOST_MODEL_FOLDERS
    }

    checkpoints = inventory_map["checkpoints"]
    clip = inventory_map["clip"]
    clip_vision = inventory_map["clip_vision"]
    controlnet = inventory_map["controlnet"]
    diffusion_models = inventory_map["diffusion_models"]
    embeddings = inventory_map["embeddings"]
    loras = inventory_map["loras"]
    text_encoders = inventory_map["text_encoders"]
    ultralytics = inventory_map["ultralytics"]
    ultralytics_bbox, ultralytics_segm = _partition_ultralytics_models(ultralytics)
    unet = inventory_map["unet"]
    upscale_models = inventory_map["upscale_models"]
    vae = inventory_map["vae"]

    source = "host" if module is not None else "fallback"
    if not checkpoints:
        checkpoints = ["__host_default__"]
        source = "fallback" if module is None else "host"
    if not vae:
        vae = ["Automatic"]
    if not text_encoders:
        text_encoders = ["Automatic"]

    return ModelInventorySnapshot(
        source=source,
        checkpoints=checkpoints,
        clip=clip,
        clip_vision=clip_vision,
        controlnet=controlnet,
        diffusion_models=diffusion_models,
        vae=vae,
        text_encoders=text_encoders,
        embeddings=embeddings,
        loras=loras,
        ultralytics=ultralytics,
        ultralytics_bbox=ultralytics_bbox,
        ultralytics_segm=ultralytics_segm,
        unet=unet,
        upscale_models=upscale_models,
        default_checkpoint=checkpoints[0],
        default_vae=vae[0],
        default_text_encoder=text_encoders[0],
    )


def discover_model_inventory(*, folder_paths_module: Any | None = None) -> ModelInventorySnapshot:
    global _inventory_cache_snapshot, _inventory_cache_at

    if folder_paths_module is not None:
        # IMPORTANT: explicit module injection is used by tests and controlled call-sites; bypass runtime cache to avoid hidden cross-test coupling.
        return _build_inventory_snapshot(folder_paths_module)

    now = time.monotonic()
    with _inventory_cache_lock:
        if (
            _inventory_cache_snapshot is not None
            and (now - _inventory_cache_at) < _INVENTORY_CACHE_TTL_SECONDS
        ):
            return _inventory_cache_snapshot

    module = _load_folder_paths_module()
    snapshot = _build_inventory_snapshot(module)
    with _inventory_cache_lock:
        _inventory_cache_snapshot = snapshot
        _inventory_cache_at = now
    return snapshot


def _normalize_selector_token(value: str) -> str:
    return str(value or "").replace("\\", "/").strip().lower()


def _canonicalize_profile_id(profile_id: str) -> str:
    normalized_profile_id = str(profile_id or "").strip().lower()
    if not normalized_profile_id:
        return normalized_profile_id
    try:
        return get_model_family_registry_entry(normalized_profile_id).id
    except ValueError:
        return normalized_profile_id


def _find_selector_by_hints(selectors: list[str], hints: tuple[str, ...]) -> str:
    if not hints:
        return ""
    for selector in selectors:
        folded_selector = _normalize_selector_token(selector)
        if any(hint in folded_selector for hint in hints):
            return selector
    return ""


def _find_selector_by_priority(
    selectors: list[str],
    priority_hints: tuple[tuple[str, ...], ...],
) -> str:
    if not priority_hints:
        return ""
    normalized_candidates = [
        (_normalize_selector_token(selector), selector)
        for selector in selectors
    ]
    for hint_group in priority_hints:
        if not hint_group:
            continue
        normalized_hints = tuple(hint.strip().lower() for hint in hint_group if hint and hint.strip())
        if not normalized_hints:
            continue
        for folded_selector, original_selector in normalized_candidates:
            if all(hint in folded_selector for hint in normalized_hints):
                return original_selector
    return ""


def _filter_selectors_by_deny_hints(
    selectors: list[str],
    deny_hints: tuple[str, ...],
) -> list[str]:
    if not selectors or not deny_hints:
        return list(selectors)
    filtered = [
        selector
        for selector in selectors
        if all(deny_hint not in _normalize_selector_token(selector) for deny_hint in deny_hints)
    ]
    return filtered or list(selectors)


def _filter_explicit_diffusion_selectors(selectors: list[str]) -> list[str]:
    return [
        selector
        for selector in selectors
        if _normalize_selector_token(selector) not in {"automatic", "__host_default__"}
    ]


def _resolve_profile_diffusion_model_default(
    profile_id: str,
    selectors: list[str],
) -> str:
    if not selectors:
        return ""
    # CRITICAL: when standard and accelerated variants coexist, defaults must prefer non-acceleration paths;
    # auto-selecting Lightning/distilled entries can silently force mismatched step/cfg defaults and degrade output quality.
    candidate_selectors = _filter_selectors_by_deny_hints(
        selectors,
        _PROFILE_DIFFUSION_MODEL_DENY_HINTS.get(profile_id, ()),
    )
    prioritized = _find_selector_by_priority(
        candidate_selectors,
        _PROFILE_DIFFUSION_MODEL_PRIORITY_HINTS.get(profile_id, ()),
    )
    if prioritized:
        return prioritized
    hints = _PROFILE_DIFFUSION_MODEL_HINTS.get(profile_id, ())
    matched = _find_selector_by_hints(candidate_selectors, hints)
    if matched:
        return matched
    return candidate_selectors[0]


def _resolve_profile_text_encoder_default(
    profile_id: str,
    selectors: list[str],
) -> str:
    if not selectors:
        return ""

    candidate_selectors = _filter_explicit_diffusion_selectors(selectors)
    if not candidate_selectors:
        return ""

    normalized_profile_id = _canonicalize_profile_id(profile_id)
    matched_by_priority = _find_selector_by_priority(
        candidate_selectors,
        _PROFILE_TEXT_ENCODER_PRIORITY_HINTS.get(normalized_profile_id, ()),
    )
    if matched_by_priority:
        return matched_by_priority
    profile_hints = _PROFILE_TEXT_ENCODER_HINTS.get(normalized_profile_id, ())
    matched_by_hint = _find_selector_by_hints(candidate_selectors, profile_hints)
    if matched_by_hint:
        return matched_by_hint
    return ""


def _find_text_encoder_sequence(
    profile_id: str,
    selectors: list[str],
) -> list[str]:
    sequence_hint_groups = _PROFILE_TEXT_ENCODER_SEQUENCE_PRIORITY_HINTS.get(profile_id, ())
    if not sequence_hint_groups:
        return []

    candidate_selectors = _filter_explicit_diffusion_selectors(selectors)
    if not candidate_selectors:
        return []

    normalized_candidates = [
        (_normalize_selector_token(selector), selector)
        for selector in candidate_selectors
    ]
    for sequence_hints in sequence_hint_groups:
        resolved_sequence: list[str] = []
        used_selectors: set[str] = set()
        for hint_group in sequence_hints:
            normalized_hints = tuple(hint.strip().lower() for hint in hint_group if hint and hint.strip())
            matched_selector = ""
            for folded_selector, original_selector in normalized_candidates:
                if original_selector in used_selectors:
                    continue
                if all(hint in folded_selector for hint in normalized_hints):
                    matched_selector = original_selector
                    break
            if not matched_selector:
                resolved_sequence = []
                break
            used_selectors.add(matched_selector)
            resolved_sequence.append(matched_selector)
        if resolved_sequence:
            return resolved_sequence
    return []


def resolve_text_encoder_selector_context(
    profile_id: str,
    inventory: ModelInventorySnapshot,
) -> str:
    selectors = [value for value in (inventory.text_encoders or []) if isinstance(value, str) and value.strip()]
    if not selectors:
        return inventory.default_text_encoder

    normalized_profile_id = _canonicalize_profile_id(profile_id)
    if PRIMARY_MODEL_CATEGORY_BY_FAMILY.get(normalized_profile_id) == "diffusion_models":
        # CRITICAL: diffusion families require family-bound text encoder pairing; never fall back to a global/default selector.
        resolved_sequence = _find_text_encoder_sequence(normalized_profile_id, selectors)
        if resolved_sequence:
            return "|".join(resolved_sequence)
        return _resolve_profile_text_encoder_default(normalized_profile_id, selectors)

    fallback_default = (
        inventory.default_text_encoder
        if inventory.default_text_encoder in selectors
        else selectors[0]
    )
    return fallback_default


def resolve_aux_text_encoder_selector_context(
    profile_id: str,
    inventory: ModelInventorySnapshot,
) -> str:
    selectors = [value for value in (inventory.text_encoders or []) if isinstance(value, str) and value.strip()]
    if not selectors:
        return ""
    normalized_profile_id = _canonicalize_profile_id(profile_id)
    if PRIMARY_MODEL_CATEGORY_BY_FAMILY.get(normalized_profile_id) != "diffusion_models":
        return ""
    candidate_selectors = _filter_explicit_diffusion_selectors(selectors)
    return _find_selector_by_priority(
        candidate_selectors,
        _PROFILE_AUX_TEXT_ENCODER_PRIORITY_HINTS.get(normalized_profile_id, ()),
    )


def _resolve_profile_vae_default(
    profile_id: str,
    selectors: list[str],
) -> str:
    if not selectors:
        return ""

    normalized_profile_id = _canonicalize_profile_id(profile_id)
    candidate_selectors = _filter_explicit_diffusion_selectors(selectors)
    if not candidate_selectors:
        return ""

    candidate_selectors = _filter_selectors_by_deny_hints(
        candidate_selectors,
        _PROFILE_VAE_DENY_HINTS.get(normalized_profile_id, ()),
    )
    prioritized = _find_selector_by_priority(
        candidate_selectors,
        _PROFILE_VAE_PRIORITY_HINTS.get(normalized_profile_id, ()),
    )
    if prioritized:
        return prioritized

    hints = _PROFILE_VAE_HINTS.get(normalized_profile_id, ())
    matched = _find_selector_by_hints(candidate_selectors, hints)
    if matched:
        return matched

    return ""


def resolve_vae_selector_context(
    profile_id: str,
    inventory: ModelInventorySnapshot,
) -> str:
    selectors = [value for value in (inventory.vae or []) if isinstance(value, str) and value.strip()]
    if not selectors:
        return inventory.default_vae

    fallback_default = inventory.default_vae if inventory.default_vae in selectors else selectors[0]
    normalized_profile_id = _canonicalize_profile_id(profile_id)
    if PRIMARY_MODEL_CATEGORY_BY_FAMILY.get(normalized_profile_id) != "diffusion_models":
        return fallback_default

    # CRITICAL: diffusion families require family-bound VAE pairing; never fall back to global/default selectors.
    return _resolve_profile_vae_default(normalized_profile_id, selectors)


def resolve_template_lora_selector_context(
    profile_id: str,
    inventory: ModelInventorySnapshot,
) -> str:
    selectors = [value for value in (inventory.loras or []) if isinstance(value, str) and value.strip()]
    if not selectors:
        return ""
    normalized_profile_id = _canonicalize_profile_id(profile_id)
    return _find_selector_by_priority(
        selectors,
        _PROFILE_TEMPLATE_LORA_PRIORITY_HINTS.get(normalized_profile_id, ()),
    )


def resolve_primary_model_selector_context(
    profile_id: str,
    inventory: ModelInventorySnapshot,
) -> tuple[str, list[str], str]:
    normalized_profile_id = _canonicalize_profile_id(profile_id)
    category_id = PRIMARY_MODEL_CATEGORY_BY_FAMILY.get(normalized_profile_id, "checkpoints")
    category_values = list(getattr(inventory, category_id, []) or [])

    # IMPORTANT: profile-driven selector category must be honored for non-SDXL presets
    # (Flux/Qwen/etc.); forcing checkpoints here breaks preset-aware model-path switching.
    if not category_values:
        category_id = "checkpoints"
        category_values = list(inventory.checkpoints or [])

    if not category_values:
        category_values = [inventory.default_checkpoint]

    default_value = (
        _resolve_profile_diffusion_model_default(normalized_profile_id, category_values)
        if category_id == "diffusion_models"
        else (category_values[0] if category_values else inventory.default_checkpoint)
    )
    return category_id, category_values, default_value


def _reset_inventory_cache_for_tests() -> None:
    global _inventory_cache_snapshot, _inventory_cache_at
    with _inventory_cache_lock:
        _inventory_cache_snapshot = None
        _inventory_cache_at = 0.0
