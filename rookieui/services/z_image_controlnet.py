from __future__ import annotations

import sys
from typing import Mapping

from rookieui.contracts.models import ModelInventorySnapshot
from rookieui.services.model_inventory import discover_model_inventory

Z_IMAGE_CONTROLNET_CONTRACT_VERSION = "f260-20260531"
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
_BASE_UNION_CONDITIONS = (
    "canny",
    "depth",
    "pose",
    "mlsd",
    "hed",
)
_CONTROL_CONTEXT_SCALE_RANGE = (0.65, 1.0)


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
    if "union" in normalized:
        return "union"
    if "canny" in normalized:
        return "canny"
    if "depth" in normalized:
        return "depth"
    if "pose" in normalized or "openpose" in normalized:
        return "pose"
    return "unknown"


def _classify_generation(selector: str) -> str:
    normalized = _normalize_selector_token(selector)
    if "2.0" in normalized:
        return "2.0"
    if "2.1" in normalized:
        return "2.1"
    return "unknown"


def _classify_release_tag(selector: str) -> str | None:
    normalized = _normalize_selector_token(selector)
    if "2602" in normalized:
        return "2602"
    if "2601" in normalized:
        return "2601"
    return None


def _classify_distilled_steps(selector: str) -> int | None:
    normalized = _normalize_selector_token(selector)
    if "8steps" in normalized or "8-steps" in normalized:
        return 8
    return None


def _classify_supported_conditions(*, turbo: bool, variant: str, release_tag: str | None) -> list[str]:
    if variant == "tile":
        return ["tile"]
    if variant != "union":
        return []
    conditions = list(_BASE_UNION_CONDITIONS)
    if not turbo:
        conditions.extend(["scribble", "gray", "inpaint"])
        return conditions
    if release_tag in {"2601", "2602"}:
        conditions.append("scribble")
    if release_tag == "2602":
        conditions.append("gray")
    return conditions


def _classify_rookieui_support(*, turbo: bool, variant: str) -> str:
    if variant == "tile":
        return "deferred_tile_surface"
    if not turbo:
        return "deferred_non_turbo"
    if variant == "union":
        return "turbo_union_single_control"
    return "deferred_unverified"


def _classify_recommendation(
    *,
    rookieui_support: str,
    release_tag: str | None,
    distilled_steps: int | None,
    lite: bool,
) -> str:
    if rookieui_support != "turbo_union_single_control":
        return "deferred"
    if release_tag == "2602" and distilled_steps == 8 and not lite:
        return "preferred"
    return "candidate"


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
        turbo = "turbo" in normalized
        variant = _classify_patch_variant(selector)
        release_tag = _classify_release_tag(selector)
        distilled_steps = _classify_distilled_steps(selector)
        lite = "lite" in normalized
        rookieui_support = _classify_rookieui_support(turbo=turbo, variant=variant)
        entries.append(
            {
                "selector": selector,
                "model_category": "model_patches",
                "family": "z_image",
                "profile_hint": "z_image_turbo" if turbo else "z_image",
                "variant": variant,
                "turbo": turbo,
                "z_image_family": "turbo" if turbo else "fun",
                "generation": _classify_generation(selector),
                "release_tag": release_tag,
                "distilled_steps": distilled_steps,
                "lite": lite,
                "supported_conditions": _classify_supported_conditions(
                    turbo=turbo,
                    variant=variant,
                    release_tag=release_tag,
                ),
                "source_control_context_scale_range": list(_CONTROL_CONTEXT_SCALE_RANGE),
                "rookieui_support": rookieui_support,
                "recommendation": _classify_recommendation(
                    rookieui_support=rookieui_support,
                    release_tag=release_tag,
                    distilled_steps=distilled_steps,
                    lite=lite,
                ),
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
