from __future__ import annotations

import logging
import ntpath
import os
import sys
import threading
import time
from typing import Any

from rookieui.contracts.family_template_manifest import (
    build_aux_text_encoder_priority_hints_by_profile,
    build_diffusion_model_deny_hints_by_profile,
    build_diffusion_model_hints_by_profile,
    build_diffusion_model_priority_hints_by_profile,
    build_template_lora_priority_hints_by_profile,
    build_text_encoder_hints_by_profile,
    build_text_encoder_priority_hints_by_profile,
    build_text_encoder_sequence_hints_by_profile,
    build_vae_deny_hints_by_profile,
    build_vae_hints_by_profile,
    build_vae_priority_hints_by_profile,
)
from rookieui.contracts.model_family_registry import get_model_family_registry_entry
from rookieui.contracts.models import ModelInventorySnapshot, PRIMARY_MODEL_CATEGORY_BY_FAMILY

_HOST_MODEL_FOLDERS = (
    "audio_encoders",
    "background_removal",
    "checkpoints",
    "classifiers",
    "clip",
    "clip_vision",
    "configs",
    "controlnet",
    "detection",
    "diffusers",
    "diffusion_models",
    "embeddings",
    "frame_interpolation",
    "geometry_estimation",
    "gligen",
    "hypernetworks",
    "latent_upscale_models",
    "loras",
    "model_patches",
    "optical_flow",
    "photomaker",
    "style_models",
    "text_encoders",
    "ultralytics",
    "unet",
    "upscale_models",
    "vae",
    "vae_approx",
)
_INVENTORY_CACHE_TTL_SECONDS = 5.0
_inventory_cache_lock = threading.Lock()
_inventory_cache_snapshot: ModelInventorySnapshot | None = None
_inventory_cache_at: float = 0.0
_LOGGER = logging.getLogger("ComfyUI-RookieUI")
_PROFILE_DIFFUSION_MODEL_HINTS = build_diffusion_model_hints_by_profile()
_PROFILE_DIFFUSION_MODEL_PRIORITY_HINTS = build_diffusion_model_priority_hints_by_profile()
_PROFILE_DIFFUSION_MODEL_DENY_HINTS = build_diffusion_model_deny_hints_by_profile()
_PROFILE_TEXT_ENCODER_HINTS = build_text_encoder_hints_by_profile()
_PROFILE_TEXT_ENCODER_PRIORITY_HINTS = build_text_encoder_priority_hints_by_profile()
_PROFILE_TEXT_ENCODER_SEQUENCE_PRIORITY_HINTS = build_text_encoder_sequence_hints_by_profile()
_PROFILE_AUX_TEXT_ENCODER_PRIORITY_HINTS = build_aux_text_encoder_priority_hints_by_profile()
_PROFILE_TEMPLATE_LORA_PRIORITY_HINTS = build_template_lora_priority_hints_by_profile()
_PROFILE_VAE_HINTS = build_vae_hints_by_profile()
_PROFILE_VAE_PRIORITY_HINTS = build_vae_priority_hints_by_profile()
_PROFILE_VAE_DENY_HINTS = build_vae_deny_hints_by_profile()
_NATIVE_ULTRALYTICS_MODEL_FOLDERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ultralytics", ("ultralytics",)),
    ("ultralytics_bbox", ("ultralytics", "bbox")),
    ("ultralytics_segm", ("ultralytics", "segm")),
)
_HOST_NODE_INPUT_FALLBACKS: dict[str, tuple[tuple[str, str], ...]] = {
    # IMPORTANT: these are the ComfyUI node input fields that users actually see in core loader nodes;
    # keep them aligned with host node APIs so empty folder_paths lookups do not collapse UI selectors.
    "checkpoints": (("CheckpointLoaderSimple", "ckpt_name"),),
    "controlnet": (("ControlNetLoader", "control_net_name"),),
    "diffusion_models": (("UNETLoader", "unet_name"),),
    "loras": (("LoraLoader", "lora_name"),),
    "model_patches": (("ModelPatchLoader", "name"),),
    "upscale_models": (("UpscaleModelLoader", "model_name"),),
    "vae": (("VAELoader", "vae_name"),),
}


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
        # IMPORTANT: standalone/test imports may not have a real ComfyUI folder_paths module;
        # callers must continue into node INPUT_TYPES fallback before using sentinel defaults.
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


def _extract_node_input_choices(input_spec: Any, field_name: str) -> list[str]:
    required_inputs = input_spec.get("required") if isinstance(input_spec, dict) else None
    field_spec = required_inputs.get(field_name) if isinstance(required_inputs, dict) else None
    if isinstance(field_spec, (list, tuple)) and field_spec:
        choices = field_spec[0]
    else:
        choices = field_spec
    if isinstance(choices, (list, tuple)):
        return [str(choice) for choice in choices if isinstance(choice, str) and choice.strip()]
    return []


def _safe_get_node_input_choices(class_name: str, field_name: str) -> list[str]:
    nodes_module = sys.modules.get("nodes")
    mappings = getattr(nodes_module, "NODE_CLASS_MAPPINGS", None)
    if not isinstance(mappings, dict):
        return []
    node_class = mappings.get(class_name)
    input_types = getattr(node_class, "INPUT_TYPES", None)
    if not callable(input_types):
        return []
    try:
        input_spec = input_types()
    except Exception:
        _LOGGER.debug(
            "RookieUI inventory fallback for node '%s.%s' due to host INPUT_TYPES exception.",
            class_name,
            field_name,
            exc_info=True,
        )
        return []
    return _extract_node_input_choices(input_spec, field_name)


def _resolve_host_folder_selectors(module: Any | None, folder_name: str) -> list[str]:
    values = _safe_get_filename_list(module, folder_name)
    if values:
        return values
    for class_name, field_name in _HOST_NODE_INPUT_FALLBACKS.get(folder_name, ()):
        values = _safe_get_node_input_choices(class_name, field_name)
        if values:
            # CRITICAL: ComfyUI can expose valid selector lists through loaded node INPUT_TYPES even when
            # direct folder_paths lookup is unavailable or stale; relying on folder_paths only empties SD/VAE menus.
            return values
    return []


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
        folder_name: _resolve_host_folder_selectors(module, folder_name)
        for folder_name in _HOST_MODEL_FOLDERS
    }

    audio_encoders = inventory_map["audio_encoders"]
    background_removal = inventory_map["background_removal"]
    checkpoints = inventory_map["checkpoints"]
    classifiers = inventory_map["classifiers"]
    clip = inventory_map["clip"]
    clip_vision = inventory_map["clip_vision"]
    configs = inventory_map["configs"]
    controlnet = inventory_map["controlnet"]
    detection = inventory_map["detection"]
    diffusers = inventory_map["diffusers"]
    diffusion_models = inventory_map["diffusion_models"]
    embeddings = inventory_map["embeddings"]
    frame_interpolation = inventory_map["frame_interpolation"]
    geometry_estimation = inventory_map["geometry_estimation"]
    gligen = inventory_map["gligen"]
    hypernetworks = inventory_map["hypernetworks"]
    latent_upscale_models = inventory_map["latent_upscale_models"]
    loras = inventory_map["loras"]
    model_patches = inventory_map["model_patches"]
    optical_flow = inventory_map["optical_flow"]
    photomaker = inventory_map["photomaker"]
    style_models = inventory_map["style_models"]
    text_encoders = inventory_map["text_encoders"]
    ultralytics = inventory_map["ultralytics"]
    ultralytics_bbox, ultralytics_segm = _partition_ultralytics_models(ultralytics)
    unet = inventory_map["unet"]
    if not diffusion_models and unet:
        # CRITICAL: ComfyUI host builds may expose UNETLoader models under `unet`;
        # non-SD presets read `diffusion_models`, so leaving this empty forces __host_default__ in the UI.
        diffusion_models = list(unet)
    upscale_models = inventory_map["upscale_models"]
    vae = inventory_map["vae"]
    vae_approx = inventory_map["vae_approx"]

    source = "host" if module is not None else "fallback"
    if not checkpoints:
        # IMPORTANT: seeing this sentinel in the UI means both folder_paths and node INPUT_TYPES
        # failed to expose CheckpointLoaderSimple choices; debug inventory discovery before blaming presets.
        checkpoints = ["__host_default__"]
        source = "fallback" if module is None else "host"
    if not vae:
        # IMPORTANT: Automatic-only VAE menus are the VAE-side equivalent of the checkpoint sentinel above.
        vae = ["Automatic"]
    if not text_encoders:
        text_encoders = ["Automatic"]

    return ModelInventorySnapshot(
        source=source,
        audio_encoders=audio_encoders,
        background_removal=background_removal,
        checkpoints=checkpoints,
        classifiers=classifiers,
        clip=clip,
        clip_vision=clip_vision,
        configs=configs,
        controlnet=controlnet,
        detection=detection,
        diffusers=diffusers,
        diffusion_models=diffusion_models,
        vae=vae,
        text_encoders=text_encoders,
        embeddings=embeddings,
        frame_interpolation=frame_interpolation,
        geometry_estimation=geometry_estimation,
        gligen=gligen,
        hypernetworks=hypernetworks,
        latent_upscale_models=latent_upscale_models,
        loras=loras,
        model_patches=model_patches,
        optical_flow=optical_flow,
        photomaker=photomaker,
        style_models=style_models,
        ultralytics=ultralytics,
        ultralytics_bbox=ultralytics_bbox,
        ultralytics_segm=ultralytics_segm,
        unet=unet,
        upscale_models=upscale_models,
        vae_approx=vae_approx,
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


def resolve_ideogram4_unconditional_selector_context(inventory: ModelInventorySnapshot) -> str:
    selectors = [
        value
        for value in (inventory.diffusion_models or [])
        if isinstance(value, str) and value.strip()
    ]
    # CRITICAL: return the exact host selector, including its relative subdirectory;
    # UNETLoader resolves only values enumerated by ComfyUI's diffusion_models inventory.
    return _find_selector_by_priority(selectors, (("ideogram4", "unconditional"),))


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
