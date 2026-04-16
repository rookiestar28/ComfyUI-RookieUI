from __future__ import annotations

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
) -> None:
    workflow[save_id] = {
        "class_type": "SaveImage",
        "inputs": {
            "images": image_ref,
            "filename_prefix": "RookieUI",
        },
    }


def _build_decode_and_save(
    workflow: dict[str, object],
    *,
    sampler_id: str | list[object],
    decode_id: str,
    save_id: str,
    vae_source: list[object],
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
    )
