from __future__ import annotations

import sys
from typing import Mapping

from rookieui.contracts.models import ModelInventorySnapshot
from rookieui.services.model_inventory import discover_model_inventory

Z_IMAGE_CONTROLNET_CONTRACT_VERSION = "f258-20260531"
Z_IMAGE_CONTROLNET_REQUIRED_NODES: tuple[str, ...] = (
    "ModelPatchLoader",
    "QwenImageDiffsynthControlnet",
    "ModelSamplingAuraFlow",
)
Z_IMAGE_CONTROLNET_FORBIDDEN_NODES: tuple[str, ...] = (
    "ControlNetLoader",
    "DiffControlNetLoader",
    "RookieUIControlNetApplyNativeAdvanced",
)
_Z_IMAGE_TOKENS = (
    "z-image",
    "z_image",
    "zimage",
    "z/image",
    "z\\image",
)
_CONTROLNET_TOKENS = (
    "controlnet",
    "control_net",
    "control-net",
)


def _normalize_selector_token(value: str) -> str:
    return str(value or "").replace("\\", "/").strip().lower()


def _looks_like_z_image_controlnet_patch(selector: str) -> bool:
    normalized = _normalize_selector_token(selector)
    return any(token in normalized for token in _Z_IMAGE_TOKENS) and any(
        token in normalized for token in _CONTROLNET_TOKENS
    )


def _classify_patch_variant(selector: str) -> str:
    normalized = _normalize_selector_token(selector)
    if "tile" in normalized:
        return "tile"
    if "canny" in normalized:
        return "canny"
    if "depth" in normalized:
        return "depth"
    if "pose" in normalized or "openpose" in normalized:
        return "pose"
    if "union" in normalized:
        return "union"
    return "unknown"


def _resolve_node_class_mappings(
    node_class_mappings: Mapping[str, object] | None,
) -> Mapping[str, object]:
    if node_class_mappings is not None:
        return node_class_mappings
    nodes_module = sys.modules.get("nodes")
    mappings = getattr(nodes_module, "NODE_CLASS_MAPPINGS", None)
    return mappings if isinstance(mappings, Mapping) else {}


def _build_patch_entries(selectors: list[str]) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for selector in selectors:
        if not isinstance(selector, str) or not selector.strip():
            continue
        if not _looks_like_z_image_controlnet_patch(selector):
            continue
        normalized = _normalize_selector_token(selector)
        entries.append(
            {
                "selector": selector,
                "model_category": "model_patches",
                "family": "z_image",
                "profile_hint": "z_image_turbo" if "turbo" in normalized else "z_image",
                "variant": _classify_patch_variant(selector),
                "turbo": "turbo" in normalized,
            }
        )
    return entries


def build_z_image_controlnet_capability_payload(
    *,
    inventory: ModelInventorySnapshot | None = None,
    node_class_mappings: Mapping[str, object] | None = None,
) -> dict[str, object]:
    inventory = inventory if inventory is not None else discover_model_inventory()
    mappings = _resolve_node_class_mappings(node_class_mappings)
    missing_nodes = [
        node_name for node_name in Z_IMAGE_CONTROLNET_REQUIRED_NODES if node_name not in mappings
    ]
    patch_entries = _build_patch_entries(list(inventory.model_patches or []))

    diagnostics = [f"missing_node:{node_name}" for node_name in missing_nodes]
    if not patch_entries:
        diagnostics.append("missing_model_patches:z_image_controlnet")

    return {
        "contract_version": Z_IMAGE_CONTROLNET_CONTRACT_VERSION,
        "source_model_category": "model_patches",
        "forbidden_model_category": "controlnet",
        "available": bool(patch_entries) and not missing_nodes,
        "required_nodes": list(Z_IMAGE_CONTROLNET_REQUIRED_NODES),
        "missing_nodes": missing_nodes,
        "model_patches": patch_entries,
        "diagnostics": diagnostics,
        "graph_contract": {
            "loader_node": "ModelPatchLoader",
            "patch_apply_node": "QwenImageDiffsynthControlnet",
            "sampling_node": "ModelSamplingAuraFlow",
            "forbidden_nodes": list(Z_IMAGE_CONTROLNET_FORBIDDEN_NODES),
        },
    }
