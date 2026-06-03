from __future__ import annotations

from typing import Any

from rookieui.services.generation_metadata import build_a1111_parameters
from rookieui.services.workflow_builders.core import _to_node_ref


def _append_decode_node(
    workflow: dict[str, object],
    *,
    sampler_id: str | list[object],
    decode_id: str,
    vae_source: list[object],
) -> None:
    workflow[decode_id] = {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": _to_node_ref(sampler_id),
            "vae": vae_source,
        },
    }


def _append_save_node(
    workflow: dict[str, object],
    *,
    image_ref: list[object],
    save_id: str,
    request: Any | None = None,
) -> None:
    parameters = ""
    if request is not None and hasattr(request, "to_payload"):
        parameters = build_a1111_parameters(request.to_payload())
    workflow[save_id] = {
        "class_type": "RookieUISaveImageWithMetadata",
        "inputs": {
            "images": image_ref,
            "filename_prefix": "RookieUI",
            "parameters": parameters,
        },
    }


def _build_decode_and_save(
    workflow: dict[str, object],
    *,
    sampler_id: str | list[object],
    decode_id: str,
    save_id: str,
    vae_source: list[object],
    request: Any | None = None,
) -> None:
    _append_decode_node(
        workflow,
        sampler_id=sampler_id,
        decode_id=decode_id,
        vae_source=vae_source,
    )
    _append_save_node(
        workflow,
        image_ref=[decode_id, 0],
        save_id=save_id,
        request=request,
    )
