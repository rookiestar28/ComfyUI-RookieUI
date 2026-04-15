from __future__ import annotations

import logging
import ntpath
import os
import threading
import time
from typing import Any

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
    "flux": ("flux",),
    "qwen_image": ("qwen",),
    "klein": ("klein", "flux.2", "flux2"),
    "lumina": ("lumina",),
    "zit": ("zit", "z-image", "zimage", "turbo"),
    "wan": ("wan",),
    "anima": ("anima",),
}
_PROFILE_DIFFUSION_MODEL_PRIORITY_HINTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "flux": (("flux2", "dev"), ("flux2",), ("flux",)),
    "qwen_image": (("qwen", "2512", "fp8"), ("qwen", "2512"), ("qwen", "image"), ("qwen",)),
    "klein": (("klein", "base"), ("flux2", "klein"), ("klein",)),
    "lumina": (("lumina2",), ("lumina",)),
    "zit": (("z_image_turbo",), ("z-image-turbo",), ("zimageturbo",), ("zit",), ("z-image",)),
    "wan": (("wan2.2", "high_noise"), ("wan2.2",), ("wan", "high_noise"), ("wan",)),
    "anima": (("anima",),),
}
_PROFILE_DIFFUSION_MODEL_DENY_HINTS: dict[str, tuple[str, ...]] = {
    "qwen_image": ("lightning", "lora", "2step", "4step", "8step", "distill", "distilled"),
    "wan": ("lightning", "lightx2v", "lora", "2step", "4step"),
}
_PROFILE_TEXT_ENCODER_HINTS: dict[str, tuple[str, ...]] = {
    "flux": ("flux", "t5"),
    "qwen_image": ("qwen",),
    "klein": ("klein", "flux.2", "flux2"),
    "lumina": ("lumina",),
    "zit": ("zit", "z-image", "zimage", "lumina"),
    "wan": ("wan",),
    "anima": ("anima",),
}
_PROFILE_TEXT_ENCODER_PRIORITY_HINTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "flux": (("mistral_3_small_flux2",), ("flux", "t5"), ("flux",), ("t5",)),
    "qwen_image": (("qwen_2.5_vl",), ("qwenimagete",), ("qwen",)),
    "klein": (("qwen_3_4b",), ("klein",), ("flux2",), ("t5",)),
    "lumina": (("lumina",), ("qwen_3_4b",), ("qwen",)),
    "zit": (("qwen_3_4b",), ("lumina",), ("qwen",)),
    "wan": (("umt5",), ("wan",), ("t5",)),
    "anima": (("qwen_3_06b",), ("anima",), ("qwen",)),
}
_PROFILE_VAE_HINTS: dict[str, tuple[str, ...]] = {
    "flux": ("flux", "ae"),
    "qwen_image": ("qwen", "qwen-image", "qwen_image"),
    "klein": ("klein", "flux.2", "flux2"),
    "lumina": ("lumina",),
    "zit": ("zit", "z-image", "zimage", "turbo", "lumina"),
    "wan": ("wan",),
    "anima": ("anima",),
}
_PROFILE_VAE_PRIORITY_HINTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "flux": (("flux", "vae"), ("flux",), ("ae",)),
    "qwen_image": (("qwen", "vae"), ("qwen", "image"), ("qwen",)),
    "klein": (("klein", "vae"), ("klein",), ("flux2", "vae"), ("flux2",)),
    "lumina": (("lumina", "vae"), ("lumina",)),
    "zit": (
        ("z_image_turbo", "vae"),
        ("z-image-turbo", "vae"),
        ("zit", "vae"),
        ("lumina", "vae"),
        ("lumina",),
        ("zimage",),
        ("zit",),
    ),
    "wan": (("wan2.2", "vae"), ("wan", "vae"), ("wan2.2",), ("wan",)),
    "anima": (("anima", "vae"), ("anima",)),
}
_PROFILE_VAE_DENY_HINTS: dict[str, tuple[str, ...]] = {
    "flux": ("qwen",),
    "klein": ("qwen",),
    "lumina": ("qwen",),
    "zit": ("qwen",),
    "wan": ("qwen",),
    "anima": ("qwen",),
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

    normalized_profile_id = str(profile_id or "").strip().lower()
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


def resolve_text_encoder_selector_context(
    profile_id: str,
    inventory: ModelInventorySnapshot,
) -> str:
    selectors = [value for value in (inventory.text_encoders or []) if isinstance(value, str) and value.strip()]
    if not selectors:
        return inventory.default_text_encoder

    normalized_profile_id = str(profile_id or "").strip().lower()
    if PRIMARY_MODEL_CATEGORY_BY_FAMILY.get(normalized_profile_id) == "diffusion_models":
        # CRITICAL: diffusion families require family-bound text encoder pairing; never fall back to a global/default selector.
        return _resolve_profile_text_encoder_default(normalized_profile_id, selectors)

    fallback_default = (
        inventory.default_text_encoder
        if inventory.default_text_encoder in selectors
        else selectors[0]
    )
    return fallback_default


def _resolve_profile_vae_default(
    profile_id: str,
    selectors: list[str],
) -> str:
    if not selectors:
        return ""

    normalized_profile_id = str(profile_id or "").strip().lower()
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
    normalized_profile_id = str(profile_id or "").strip().lower()
    if PRIMARY_MODEL_CATEGORY_BY_FAMILY.get(normalized_profile_id) != "diffusion_models":
        return fallback_default

    # CRITICAL: diffusion families require family-bound VAE pairing; never fall back to global/default selectors.
    return _resolve_profile_vae_default(normalized_profile_id, selectors)


def resolve_primary_model_selector_context(
    profile_id: str,
    inventory: ModelInventorySnapshot,
) -> tuple[str, list[str], str]:
    normalized_profile_id = str(profile_id or "").strip().lower()
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
