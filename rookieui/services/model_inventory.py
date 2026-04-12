from __future__ import annotations

import logging
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
_PROFILE_TEXT_ENCODER_HINTS: dict[str, tuple[str, ...]] = {
    "flux": ("flux", "t5"),
    "qwen_image": ("qwen",),
    "klein": ("klein", "flux.2", "flux2"),
    "lumina": ("lumina",),
    "zit": ("zit", "z-image", "zimage", "lumina"),
    "wan": ("wan",),
    "anima": ("anima",),
}


def _load_folder_paths_module() -> Any:
    try:
        import folder_paths
    except ImportError:
        return None
    return folder_paths


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


def _resolve_profile_diffusion_model_default(
    profile_id: str,
    selectors: list[str],
) -> str:
    if not selectors:
        return ""
    hints = _PROFILE_DIFFUSION_MODEL_HINTS.get(profile_id, ())
    matched = _find_selector_by_hints(selectors, hints)
    if matched:
        return matched
    return selectors[0]


def resolve_text_encoder_selector_context(
    profile_id: str,
    inventory: ModelInventorySnapshot,
) -> str:
    selectors = [value for value in (inventory.text_encoders or []) if isinstance(value, str) and value.strip()]
    if not selectors:
        return inventory.default_text_encoder

    normalized_profile_id = str(profile_id or "").strip().lower()
    fallback_default = (
        inventory.default_text_encoder
        if inventory.default_text_encoder in selectors
        else selectors[0]
    )
    profile_hints = _PROFILE_TEXT_ENCODER_HINTS.get(normalized_profile_id, ())
    matched_by_hint = _find_selector_by_hints(selectors, profile_hints)
    if matched_by_hint:
        return matched_by_hint

    if (
        PRIMARY_MODEL_CATEGORY_BY_FAMILY.get(normalized_profile_id) == "diffusion_models"
        and normalized_profile_id != "qwen_image"
    ):
        # CRITICAL: non-Qwen diffusion presets must not silently inherit a global Qwen text-encoder default;
        # that pairing can hard-crash runtime with hidden-size mismatches (for example Lumina/ZiT + QwenImage TE).
        for selector in selectors:
            if "qwen" not in _normalize_selector_token(selector):
                return selector

    return fallback_default


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
