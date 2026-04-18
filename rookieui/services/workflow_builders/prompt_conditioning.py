from __future__ import annotations

import os

from rookieui.contracts.generation import (
    NormalizedImg2ImgRequest,
    NormalizedTxt2ImgRequest,
)
from rookieui.services.workflow_builders.core import (
    NodeIdAllocator,
    _normalize_encoder_selector_values,
)

_PROMPT_DSL_LEGACY_ENV = "ROOKIEUI_PROMPT_DSL_LEGACY"


def _is_legacy_prompt_dsl_enabled() -> bool:
    raw_value = str(os.getenv(_PROMPT_DSL_LEGACY_ENV, "")).strip().lower()
    return raw_value in {"1", "true", "yes", "on"}


def _append_conditioning_combine_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    conditioning_1: str,
    conditioning_2: str,
) -> str:
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "ConditioningCombine",
        "inputs": {
            "conditioning_1": [conditioning_1, 0],
            "conditioning_2": [conditioning_2, 0],
        },
    }
    return node_id


def _combine_conditioning_ids(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    conditioning_ids: list[str],
) -> str:
    if not conditioning_ids:
        raise ValueError("conditioning_ids must contain at least one node id.")
    merged_id = conditioning_ids[0]
    for conditioning_id in conditioning_ids[1:]:
        merged_id = _append_conditioning_combine_node(
            workflow,
            allocator=allocator,
            conditioning_1=merged_id,
            conditioning_2=conditioning_id,
        )
    return merged_id


def _coerce_semantic_feature(payload: dict[str, object], feature_name: str) -> bool:
    features = payload.get("features")
    if not isinstance(features, dict):
        return False
    return bool(features.get(feature_name))


def _requires_conditioning_compiler(semantic_payload: dict[str, object]) -> bool:
    # CRITICAL: compiler must honor the legacy rollback env switch even when semantic payloads are present; mixed parser/compiler modes cause hard-to-debug parity drift.
    if _is_legacy_prompt_dsl_enabled():
        return False
    return any(
        _coerce_semantic_feature(semantic_payload, feature_name)
        for feature_name in (
            "and_composition",
            "break_chunks",
            "prompt_scheduling",
            "alternate_prompt_scheduling",
        )
    )


def _append_prompt_encode_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    clip_source: list[object],
    text: str | list[object],
    prompt_encoder: str,
    use_rookieui_prompt_encoder: bool = False,
    width: int | None = None,
    height: int | None = None,
) -> str:
    node_id = allocator.next()
    if prompt_encoder == "sdxl":
        resolved_width = int(width or 1024)
        resolved_height = int(height or 1024)
        workflow[node_id] = {
            "class_type": "RookieUIA1111CLIPTextEncodeSDXL" if use_rookieui_prompt_encoder else "CLIPTextEncodeSDXL",
            "inputs": {
                "clip": clip_source,
                "width": resolved_width,
                "height": resolved_height,
                "crop_w": 0,
                "crop_h": 0,
                "target_width": resolved_width,
                "target_height": resolved_height,
                "text_g": text,
                "text_l": text,
            },
        }
        return node_id

    workflow[node_id] = {
        "class_type": "RookieUIA1111CLIPTextEncode" if use_rookieui_prompt_encoder else "CLIPTextEncode",
        "inputs": {
            "text": text,
            "clip": clip_source,
        },
    }
    return node_id


def _append_conditioning_range_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    conditioning_id: str,
    start: float,
    end: float,
) -> str:
    start_value = round(max(0.0, min(1.0, float(start))), 4)
    end_value = round(max(0.0, min(1.0, float(end))), 4)
    if end_value <= start_value:
        return conditioning_id
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "ConditioningSetTimestepRange",
        "inputs": {
            "conditioning": [conditioning_id, 0],
            "start": start_value,
            "end": end_value,
        },
    }
    return node_id


def _append_conditioning_weight_node(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    conditioning_id: str,
    weight: float,
) -> str:
    normalized_weight = round(float(weight), 3)
    if abs(normalized_weight - 1.0) < 1e-6:
        return conditioning_id
    node_id = allocator.next()
    workflow[node_id] = {
        "class_type": "ConditioningSetAreaStrength",
        "inputs": {
            "conditioning": [conditioning_id, 0],
            "strength": max(0.0, min(10.0, normalized_weight)),
        },
    }
    return node_id


def _compile_prompt_semantic_conditioning(
    workflow: dict[str, object],
    *,
    allocator: NodeIdAllocator,
    clip_source: list[object],
    prompt_text: str,
    semantic_payload: dict[str, object],
    prompt_encoder: str,
    use_rookieui_prompt_encoder: bool = False,
    width: int | None = None,
    height: int | None = None,
) -> str:
    if not _requires_conditioning_compiler(semantic_payload):
        return _append_prompt_encode_node(
            workflow,
            allocator=allocator,
            clip_source=clip_source,
            text=prompt_text,
            prompt_encoder=prompt_encoder,
            use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
            width=width,
            height=height,
        )

    branches = semantic_payload.get("branches")
    if not isinstance(branches, list) or not branches:
        return _append_prompt_encode_node(
            workflow,
            allocator=allocator,
            clip_source=clip_source,
            text=prompt_text,
            prompt_encoder=prompt_encoder,
            use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
            width=width,
            height=height,
        )

    compiled_branch_ids: list[str] = []
    for raw_branch in branches:
        if not isinstance(raw_branch, dict):
            continue
        branch_text = str(raw_branch.get("text") or prompt_text).strip() or prompt_text
        raw_chunks = raw_branch.get("chunks")
        chunks = raw_chunks if isinstance(raw_chunks, list) and raw_chunks else [{"text": branch_text, "slices": []}]
        compiled_chunk_ids: list[str] = []

        for raw_chunk in chunks:
            if not isinstance(raw_chunk, dict):
                continue
            chunk_text = str(raw_chunk.get("text") or branch_text).strip() or branch_text
            raw_slices = raw_chunk.get("slices")
            slices = raw_slices if isinstance(raw_slices, list) and raw_slices else [{"text": chunk_text, "start": 0.0, "end": 1.0}]
            compiled_slice_ids: list[str] = []

            for raw_slice in slices:
                if not isinstance(raw_slice, dict):
                    continue
                slice_text = str(raw_slice.get("text") or chunk_text).strip() or chunk_text
                encoded_id = _append_prompt_encode_node(
                    workflow,
                    allocator=allocator,
                    clip_source=clip_source,
                    text=slice_text,
                    prompt_encoder=prompt_encoder,
                    use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
                    width=width,
                    height=height,
                )
                start = float(raw_slice.get("start", 0.0))
                end = float(raw_slice.get("end", 1.0))
                compiled_slice_ids.append(
                    _append_conditioning_range_node(
                        workflow,
                        allocator=allocator,
                        conditioning_id=encoded_id,
                        start=start,
                        end=end,
                    )
                )

            if compiled_slice_ids:
                compiled_chunk_ids.append(
                    _combine_conditioning_ids(
                        workflow,
                        allocator=allocator,
                        conditioning_ids=compiled_slice_ids,
                    )
                )

        if not compiled_chunk_ids:
            compiled_chunk_ids.append(
                _append_prompt_encode_node(
                    workflow,
                    allocator=allocator,
                    clip_source=clip_source,
                    text=branch_text,
                    prompt_encoder=prompt_encoder,
                    use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
                    width=width,
                    height=height,
                )
            )

        branch_id = _combine_conditioning_ids(
            workflow,
            allocator=allocator,
            conditioning_ids=compiled_chunk_ids,
        )
        branch_weight = float(raw_branch.get("weight", 1.0))
        compiled_branch_ids.append(
            _append_conditioning_weight_node(
                workflow,
                allocator=allocator,
                conditioning_id=branch_id,
                weight=branch_weight,
            )
        )

    if not compiled_branch_ids:
        return _append_prompt_encode_node(
            workflow,
            allocator=allocator,
            clip_source=clip_source,
            text=prompt_text,
            prompt_encoder=prompt_encoder,
            use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
            width=width,
            height=height,
        )
    return _combine_conditioning_ids(
        workflow,
        allocator=allocator,
        conditioning_ids=compiled_branch_ids,
    )


def _uses_sd_family_prompt_parity(
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
) -> bool:
    # CRITICAL: SD-family prompt parity must stay on RookieUI-owned encoder nodes; reverting these profiles to stock encoders silently drops A1111 attention semantics back to approximation-only behavior.
    return request.profile in {"sd15", "sdxl", "pony", "illustrious", "noob"}


def _resolve_conditioning_prompt_encoder(
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
) -> str:
    configured_prompt_encoder = str(request.prompt_encoder or "").strip().lower()
    if configured_prompt_encoder in {"clip_text_encode", "sd15"}:
        return "sd15"
    if configured_prompt_encoder in {"clip_text_encode_sdxl", "sdxl"}:
        text_encoder_values = _normalize_encoder_selector_values(request.text_encoder_name)
        if request.primary_model_category == "diffusion_models" and len(text_encoder_values) <= 1:
            # CRITICAL: CLIPTextEncodeSDXL requires both "l" and "g" token channels;
            # diffusion-model presets often run single text encoders, so forcing SDXL encoding here causes KeyError('l') at runtime.
            return "sd15"
        return "sdxl"
    return "sdxl"


def _build_sd15_conditioning(
    workflow: dict[str, object],
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
    *,
    allocator: NodeIdAllocator,
    clip_source: list[object],
) -> tuple[str, str]:
    use_rookieui_prompt_encoder = _uses_sd_family_prompt_parity(request)
    if request.clip_skip > 1:
        clip_node_id = allocator.next()
        workflow[clip_node_id] = {
            "class_type": "CLIPSetLastLayer",
            "inputs": {
                "clip": ["1", 1],
                "stop_at_clip_layer": -request.clip_skip,
            },
        }
        clip_source = [clip_node_id, 0]
    positive_id = _compile_prompt_semantic_conditioning(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        prompt_text=request.prompt,
        semantic_payload=request.prompt_semantics if isinstance(request.prompt_semantics, dict) else {},
        prompt_encoder="sd15",
        use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
    )
    negative_id = _compile_prompt_semantic_conditioning(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        prompt_text=request.negative_prompt,
        semantic_payload=request.negative_prompt_semantics if isinstance(request.negative_prompt_semantics, dict) else {},
        prompt_encoder="sd15",
        use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
    )
    return positive_id, negative_id


def _build_sdxl_conditioning(
    workflow: dict[str, object],
    request: NormalizedTxt2ImgRequest | NormalizedImg2ImgRequest,
    *,
    allocator: NodeIdAllocator,
    width: int,
    height: int,
    clip_source: list[object],
) -> tuple[str, str]:
    prompt_encoder_mode = _resolve_conditioning_prompt_encoder(request)
    use_rookieui_prompt_encoder = _uses_sd_family_prompt_parity(request)
    positive_id = _compile_prompt_semantic_conditioning(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        prompt_text=request.prompt,
        semantic_payload=request.prompt_semantics if isinstance(request.prompt_semantics, dict) else {},
        prompt_encoder=prompt_encoder_mode,
        use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
        width=width,
        height=height,
    )
    negative_id = _compile_prompt_semantic_conditioning(
        workflow,
        allocator=allocator,
        clip_source=clip_source,
        prompt_text=request.negative_prompt,
        semantic_payload=request.negative_prompt_semantics if isinstance(request.negative_prompt_semantics, dict) else {},
        prompt_encoder=prompt_encoder_mode,
        use_rookieui_prompt_encoder=use_rookieui_prompt_encoder,
        width=width,
        height=height,
    )
    return positive_id, negative_id
