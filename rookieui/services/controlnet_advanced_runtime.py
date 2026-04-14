from __future__ import annotations

from collections.abc import Mapping

from rookieui.contracts.controlnet import NormalizedControlNetAdvancedRequest

CONTROLNET_ADVANCED_RUNTIME_STATE = "rookieui_native_advanced_runtime"
_ADVANCED_WEIGHT_PRESET_RANGES: dict[str, tuple[float, float]] = {
    "balanced": (1.0, 1.0),
    "soft": (0.65, 1.0),
    "strong": (1.0, 1.35),
}


def _coerce_advanced_request(
    advanced: NormalizedControlNetAdvancedRequest | Mapping[str, object] | None,
) -> NormalizedControlNetAdvancedRequest:
    if advanced is None:
        return NormalizedControlNetAdvancedRequest()
    if isinstance(advanced, NormalizedControlNetAdvancedRequest):
        return advanced
    if not isinstance(advanced, Mapping):
        return NormalizedControlNetAdvancedRequest()
    return NormalizedControlNetAdvancedRequest(
        enabled=bool(advanced.get("enabled", False)),
        weight_preset=str(advanced.get("weight_preset", "balanced") or "balanced").strip().lower() or "balanced",
        layer_weights=[
            round(float(value), 4)
            for value in list(advanced.get("layer_weights", []) or [])
        ],
        timestep_keyframes=[
            {
                "start_percent": round(float(entry.get("start_percent", 0.0)), 4),
                "end_percent": round(float(entry.get("end_percent", 1.0)), 4),
                "strength_scale": round(float(entry.get("strength_scale", 1.0)), 4),
            }
            for entry in list(advanced.get("timestep_keyframes", []) or [])
            if isinstance(entry, Mapping)
        ],
        mask_aware_apply=bool(advanced.get("mask_aware_apply", False)),
    )


def build_controlnet_apply_segments(
    *,
    weight: float,
    guidance_start: float,
    guidance_end: float,
    advanced: NormalizedControlNetAdvancedRequest | Mapping[str, object] | None,
) -> list[dict[str, float]]:
    advanced_request = _coerce_advanced_request(advanced)
    base_start = round(max(0.0, min(1.0, float(guidance_start))), 4)
    base_end = round(max(base_start, min(1.0, float(guidance_end))), 4)
    base_strength = round(max(0.0, float(weight)), 4)

    if not advanced_request.enabled or not advanced_request.timestep_keyframes:
        return [
            {
                "strength": base_strength,
                "start_percent": base_start,
                "end_percent": base_end,
            }
        ]

    segments: list[dict[str, float]] = []
    sorted_keyframes = sorted(
        advanced_request.timestep_keyframes,
        key=lambda entry: (float(entry.get("start_percent", 0.0)), float(entry.get("end_percent", 1.0))),
    )
    for keyframe in sorted_keyframes:
        keyframe_start = round(max(base_start, float(keyframe.get("start_percent", 0.0))), 4)
        keyframe_end = round(min(base_end, float(keyframe.get("end_percent", 1.0))), 4)
        if keyframe_end <= keyframe_start:
            continue
        strength_scale = round(max(0.0, float(keyframe.get("strength_scale", 1.0))), 4)
        if strength_scale <= 0.0:
            continue
        segments.append(
            {
                "strength": round(base_strength * strength_scale, 4),
                "start_percent": keyframe_start,
                "end_percent": keyframe_end,
            }
        )
    if segments:
        return segments
    # IMPORTANT: when advanced keyframes collapse to nothing, keep the base ControlNet segment alive.
    # Returning [] here silently drops both primary and ADetailer-local ControlNet lanes from the workflow.
    return [
        {
            "strength": base_strength,
            "start_percent": base_start,
            "end_percent": base_end,
        }
    ]


def _build_weight_preset(total_length: int, preset: str) -> list[float]:
    if total_length <= 0:
        return []
    start_value, end_value = _ADVANCED_WEIGHT_PRESET_RANGES.get(preset, _ADVANCED_WEIGHT_PRESET_RANGES["balanced"])
    if total_length == 1:
        return [round(end_value, 4)]
    step = (end_value - start_value) / float(total_length - 1)
    return [round(start_value + (step * index), 4) for index in range(total_length)]


def build_controlnet_stage_weights(
    *,
    input_count: int,
    middle_count: int,
    output_count: int,
    weight_preset: str,
    layer_weights: list[float] | tuple[float, ...] | None,
) -> dict[str, list[float]]:
    total_count = max(0, int(output_count)) + max(0, int(middle_count)) + max(0, int(input_count))
    preset_weights = _build_weight_preset(total_count, str(weight_preset or "balanced").strip().lower())
    explicit_weights = [round(float(value), 4) for value in list(layer_weights or [])[:total_count]]
    for index, value in enumerate(explicit_weights):
        preset_weights[index] = value

    cursor = 0
    output_weights = preset_weights[cursor : cursor + max(0, int(output_count))]
    cursor += max(0, int(output_count))
    middle_weights = preset_weights[cursor : cursor + max(0, int(middle_count))]
    cursor += max(0, int(middle_count))
    # IMPORTANT: keep the flat layer-weight mapping deterministic at the shared runtime seam:
    # output -> middle -> input. Reordering this silently mutates both main and ADetailer-local ControlNet behavior.
    input_weights = preset_weights[cursor : cursor + max(0, int(input_count))]
    return {
        "input": input_weights,
        "middle": middle_weights,
        "output": output_weights,
    }


def stage_weights_require_wrapper(stage_weights: Mapping[str, list[float]]) -> bool:
    for values in stage_weights.values():
        for value in values:
            if abs(float(value) - 1.0) > 1e-6:
                return True
    return False
