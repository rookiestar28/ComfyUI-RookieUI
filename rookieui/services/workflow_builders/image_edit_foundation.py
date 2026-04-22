from __future__ import annotations

from dataclasses import dataclass

from rookieui.services.workflow_builders.core import NodeIdAllocator, _to_node_ref

_REFERENCE_SCALE_MODES = frozenset({"none", "main_only", "all"})
_FLUX_REFERENCE_METHOD_ALIASES = {
    "offset": "offset",
    "index": "index",
    "uxo": "uxo/uno",
    "uso": "uxo/uno",
    "uno": "uxo/uno",
    "uxo/uno": "uxo/uno",
    "index_timestep_zero": "index_timestep_zero",
}


@dataclass(frozen=True)
class ImageEditReferenceBundle:
    ordered_assets: tuple[str, ...]
    image_node_ids: tuple[str, ...]
    main_reference_index: int
    main_image_node_id: str


def _append_asset_image_loader_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_asset: str,
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "RookieUILoadAssetImage",
        "inputs": {
            "asset": image_asset,
        },
    }
    return node_id


def _append_image_scale_to_total_pixels_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_id: str | list[object],
    megapixels: float,
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "ImageScaleToTotalPixels",
        "inputs": {
            "upscale_method": "lanczos",
            "megapixels": megapixels,
            "resolution_steps": 1,
            "image": _to_node_ref(image_id),
        },
    }
    return node_id


def _append_vae_encode_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_id: str | list[object],
    vae_source: list[object],
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "VAEEncode",
        "inputs": {
            "pixels": _to_node_ref(image_id),
            "vae": vae_source,
        },
    }
    return node_id


def _normalize_reference_scale_mode(scale_mode: str) -> str:
    normalized = str(scale_mode or "").strip().lower() or "none"
    if normalized not in _REFERENCE_SCALE_MODES:
        raise ValueError(f"Unsupported image-edit reference scale mode: {scale_mode}")
    return normalized


def _build_image_edit_reference_bundle(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    reference_assets: list[str],
    main_reference_index: int,
    megapixels: float | None = None,
    scale_mode: str = "none",
) -> ImageEditReferenceBundle:
    if not reference_assets:
        raise ValueError("reference_assets must contain at least one image.")
    if main_reference_index < 0 or main_reference_index >= len(reference_assets):
        raise ValueError("main_reference_index is out of range for reference_assets.")

    normalized_scale_mode = _normalize_reference_scale_mode(scale_mode)
    image_node_ids = [
        _append_asset_image_loader_node(
            workflow,
            allocator=allocator,
            image_asset=asset,
        )
        for asset in reference_assets
    ]
    if megapixels is not None:
        if normalized_scale_mode == "main_only":
            image_node_ids[main_reference_index] = _append_image_scale_to_total_pixels_node(
                workflow,
                allocator=allocator,
                image_id=image_node_ids[main_reference_index],
                megapixels=megapixels,
            )
        elif normalized_scale_mode == "all":
            image_node_ids = [
                _append_image_scale_to_total_pixels_node(
                    workflow,
                    allocator=allocator,
                    image_id=image_node_id,
                    megapixels=megapixels,
                )
                for image_node_id in image_node_ids
            ]

    return ImageEditReferenceBundle(
        ordered_assets=tuple(reference_assets),
        image_node_ids=tuple(image_node_ids),
        main_reference_index=main_reference_index,
        main_image_node_id=image_node_ids[main_reference_index],
    )


def _append_reference_vae_latents(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    image_node_ids: tuple[str, ...],
    vae_source: list[object],
) -> tuple[str, ...]:
    return tuple(
        _append_vae_encode_node(
            workflow,
            allocator=allocator,
            image_id=image_node_id,
            vae_source=vae_source,
        )
        for image_node_id in image_node_ids
    )


def _append_reference_latent_chain(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    conditioning_source: str | list[object],
    latent_node_ids: tuple[str, ...],
) -> list[object]:
    current_source = _to_node_ref(conditioning_source)
    for latent_node_id in latent_node_ids:
        node_id = allocator.next()
        workflow[node_id] = {
            "class_type": "ReferenceLatent",
            "inputs": {
                "conditioning": current_source,
                "latent": _to_node_ref(latent_node_id),
            },
        }
        current_source = [node_id, 0]
    return current_source


def _normalize_flux_reference_latents_method(method: str) -> str:
    normalized = str(method or "").strip().lower()
    normalized_method = _FLUX_REFERENCE_METHOD_ALIASES.get(normalized)
    if normalized_method is None:
        raise ValueError(f"Unsupported Flux multi-reference latent method: {method}")
    return normalized_method


def _append_flux_kontext_multi_reference_method_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    conditioning_source: str | list[object],
    method: str,
) -> str:
    normalized_method = _normalize_flux_reference_latents_method(method)
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "FluxKontextMultiReferenceLatentMethod",
        "inputs": {
            "conditioning": _to_node_ref(conditioning_source),
            "reference_latents_method": normalized_method,
        },
    }
    return node_id
