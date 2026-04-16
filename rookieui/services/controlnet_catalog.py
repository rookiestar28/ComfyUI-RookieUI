from __future__ import annotations

import os
import re

from rookieui.contracts.controlnet_integrated import (
    CONTROLNET_INTEGRATED_CONTROL_TYPE_ORDER,
)
from rookieui.security.request_guard import normalize_option_label
from rookieui.services.controlnet_runtime import (
    CONTROLNET_PREPROCESSOR_OPTION_ORDER,
    normalize_preprocessor_option_key,
)

ROOKIEUI_CONTROLNET_EXTRA_MODULES_ENV = "ROOKIEUI_CONTROLNET_EXTRA_MODULES"

DEFAULT_CONTROLNET_MODULE = "none"
CONTROLNET_GENERATION_MODEL_EXTENSIONS = (".safetensors", ".ckpt", ".pt")

_CONTROLNET_BASE_MODULES = CONTROLNET_PREPROCESSOR_OPTION_ORDER

_CONTROL_TYPE_MODEL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "All": (),
    "Blur": ("blur",),
    "Canny": ("canny",),
    "Depth": ("depth",),
    "IP-Adapter": ("ipadapter", "ip-adapter", "ip_adapter"),
    "Inpaint": ("inpaint",),
    "Instant-ID": ("instantid", "instant-id", "instant_id"),
    "Lineart": ("lineart",),
    "MLSD": ("mlsd",),
    "NormalMap": ("normal", "normalmap"),
    "OpenPose": ("openpose", "pose"),
    "Reference": ("reference",),
    "Scribble": ("scribble",),
    "Segmentation": ("seg", "segmentation"),
    "Shuffle": ("shuffle",),
    "Sketch": ("sketch",),
    "SoftEdge": ("softedge", "hed", "soft_edge"),
    "T2I-Adapter": ("t2iadapter", "t2i-adapter", "t2i_adapter"),
    "Tile": ("tile",),
}

_CONTROL_TYPE_MODULE_HINTS: dict[str, tuple[str, ...]] = {
    "All": (),
    "Blur": ("blur",),
    "Canny": ("canny",),
    "Depth": ("depth",),
    "IP-Adapter": ("ipadapter",),
    "Inpaint": ("inpaint",),
    "Instant-ID": ("instantid",),
    "Lineart": ("lineart",),
    "MLSD": ("mlsd",),
    "NormalMap": ("normalmap", "normal"),
    "OpenPose": ("openpose",),
    "Reference": ("reference",),
    "Scribble": ("scribble",),
    "Segmentation": ("segmentation", "seg"),
    "Shuffle": ("shuffle",),
    "Sketch": ("sketch",),
    "SoftEdge": ("softedge", "hed"),
    "T2I-Adapter": ("t2iadapter",),
    "Tile": ("tile",),
}

_CONTROLNET_MODULE_ALIAS_PATCHES = {
    "ip_adapter": "ipadapter",
    "ip-adapter": "ipadapter",
    "instant_id": "instantid",
    "instant-id": "instantid",
    "t2i_adapter": "t2iadapter",
    "t2i-adapter": "t2iadapter",
    "normal_map": "normalmap",
}


def _normalize_control_type_alias_key(raw_value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", raw_value.strip().lower())


CONTROL_TYPE_ALIASES: dict[str, str] = {
    _normalize_control_type_alias_key(name): name for name in CONTROLNET_INTEGRATED_CONTROL_TYPE_ORDER
}
CONTROL_TYPE_ALIASES.update(
    {
        "normal": "NormalMap",
        "normalmap": "NormalMap",
        "openpose": "OpenPose",
        "ipadapter": "IP-Adapter",
        "instantid": "Instant-ID",
        "t2iadapter": "T2I-Adapter",
    }
)


def normalize_module_name(raw_value: object) -> str:
    normalized = normalize_option_label(raw_value, "controlnet_module", max_length=64).strip().lower()
    if not normalized:
        return ""
    token = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    token = _CONTROLNET_MODULE_ALIAS_PATCHES.get(token, token)
    # DEBUG HOTSPOT: module token normalization seam for Control-Type-filtered preprocessor variants.
    # Keep option keys intact here (for UI filtering) and defer base-module collapsing to runtime dispatch.
    return normalize_preprocessor_option_key(token)


def discover_controlnet_modules() -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def _push(module_name: object) -> None:
        try:
            normalized = normalize_module_name(module_name)
        except ValueError:
            return
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        ordered.append(normalized)

    for base_module in _CONTROLNET_BASE_MODULES:
        _push(base_module)

    raw_extra_modules = str(os.getenv(ROOKIEUI_CONTROLNET_EXTRA_MODULES_ENV, "")).strip()
    if raw_extra_modules:
        for candidate in re.split(r"[,\n;]+", raw_extra_modules):
            _push(candidate)

    if DEFAULT_CONTROLNET_MODULE not in seen:
        ordered.insert(0, DEFAULT_CONTROLNET_MODULE)
    return ordered


def build_module_alias_map(modules: list[str]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for module in modules:
        normalized = normalize_module_name(module)
        if not normalized:
            continue
        aliases[normalized] = normalized
        aliases[normalized.replace("_", "-")] = normalized
        aliases[normalized.replace("_", " ")] = normalized
    return aliases


def sanitize_controlnet_model_inventory(models: list[str]) -> list[str]:
    normalized_models = [str(model).strip() for model in models if isinstance(model, str) and str(model).strip()]
    if not normalized_models:
        return []
    # DEBUG HOTSPOT: control-model inventory filtering seam.
    # Exclude host annotator/preprocessor checkpoints (commonly *.pth under controlnet_aux ckpts)
    # so the ControlNet model selector stays generation-only and does not leak preprocessing weights.
    filtered = [
        model
        for model in normalized_models
        if str(model).strip().lower().endswith(CONTROLNET_GENERATION_MODEL_EXTENSIONS)
    ]
    return filtered if filtered else normalized_models


def filter_models_by_keywords(model_list: list[str], keywords: tuple[str, ...]) -> list[str]:
    if not keywords:
        return list(model_list)
    lowered_keywords = [keyword.lower() for keyword in keywords if keyword]
    if not lowered_keywords:
        return list(model_list)
    return [model for model in model_list if any(keyword in str(model).lower() for keyword in lowered_keywords)]


def build_type_module_list(control_type: str, module_list: list[str]) -> list[str]:
    if control_type == "All":
        return list(module_list)

    hints = _CONTROL_TYPE_MODULE_HINTS.get(control_type, ())
    if not hints:
        return list(module_list)

    filtered = [
        module for module in module_list if module == DEFAULT_CONTROLNET_MODULE or any(hint in module for hint in hints)
    ]
    if not filtered:
        return list(module_list)
    if DEFAULT_CONTROLNET_MODULE not in filtered:
        return [DEFAULT_CONTROLNET_MODULE, *filtered]
    return filtered


def select_default_model(model_list: list[str]) -> str:
    if not model_list:
        return ""
    for candidate in model_list:
        if "11" in str(candidate).lower():
            return str(candidate)
    return str(model_list[0])


def build_module_list_payload(*, contract_meta: dict[str, object], modules: list[str]) -> dict[str, object]:
    return {
        "source": "internal",
        "contract": contract_meta,
        "module_list": modules,
        "default_module": DEFAULT_CONTROLNET_MODULE,
    }


def build_model_list_payload(
    *,
    inventory_source: str,
    contract_meta: dict[str, object],
    model_list: list[str],
) -> dict[str, object]:
    return {
        "source": inventory_source,
        "contract": contract_meta,
        "model_list": model_list,
        "default_model": "",
    }


def build_control_types_payload(
    *,
    contract_meta: dict[str, object],
    module_list: list[str],
    model_list: list[str],
) -> dict[str, object]:
    control_types: dict[str, dict[str, object]] = {}

    for control_type in CONTROLNET_INTEGRATED_CONTROL_TYPE_ORDER:
        type_module_list = build_type_module_list(control_type, module_list)
        type_model_list = (
            filter_models_by_keywords(model_list, _CONTROL_TYPE_MODEL_KEYWORDS.get(control_type, ()))
            if control_type != "All"
            else list(model_list)
        )
        if not type_model_list:
            type_model_list = list(model_list)

        default_option = DEFAULT_CONTROLNET_MODULE
        if control_type != "All":
            default_option = next((module for module in type_module_list if module != DEFAULT_CONTROLNET_MODULE), DEFAULT_CONTROLNET_MODULE)

        control_types[control_type] = {
            "module_list": type_module_list,
            "model_list": type_model_list,
            "default_option": default_option,
            "default_model": select_default_model(type_model_list),
        }

    return {
        "source": "internal",
        "contract": contract_meta,
        "control_type_order": list(CONTROLNET_INTEGRATED_CONTROL_TYPE_ORDER),
        "default_type": "All",
        "control_types": control_types,
    }
