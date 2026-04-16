from __future__ import annotations

from rookieui.contracts.adetailer import (
    ADETAILER_CONTROLNET_MODES,
    ADETAILER_DETECTOR_PROVIDER_FAMILIES,
    ADETAILER_FALLBACK_ULTRALYTICS_DETECTORS,
    ADETAILER_MASK_FILTER_METHODS,
    ADETAILER_MASK_MERGE_MODES,
    ADETAILER_MEDIAPIPE_DETECTORS,
    ADETAILER_PROMPT_TOKENS,
)

DEFAULT_ADETAILER_DETECTOR = "None"
DEFAULT_ADETAILER_CONTROLNET_MODULE = "None"
_ADETAILER_WORLD_MARKER = "-world"
_ADETAILER_SEGM_MARKERS = ("-seg", "_seg", "segm")


def _coerce_string_list(values: object) -> list[str]:
    if values in (None, ""):
        return []
    try:
        iterable = list(values)
    except TypeError:
        return []
    return [str(value).strip() for value in iterable if isinstance(value, str) and str(value).strip()]


def classify_ultralytics_detector_family(detector: str) -> str:
    normalized = str(detector or "").strip().lower()
    if any(marker in normalized for marker in _ADETAILER_SEGM_MARKERS):
        return "ultralytics_segm"
    return "ultralytics_bbox"


def supports_detector_class_filter(detector: str) -> bool:
    return _ADETAILER_WORLD_MARKER in str(detector or "").strip().lower()


def build_detector_entries(*, inventory: object) -> tuple[list[dict[str, object]], str]:
    ultralytics_models = [
        selector
        for selector in [
            *_coerce_string_list(getattr(inventory, "ultralytics_bbox", [])),
            *_coerce_string_list(getattr(inventory, "ultralytics_segm", [])),
        ]
        if selector
    ]
    source = str(getattr(inventory, "source", "fallback") or "fallback")
    if not ultralytics_models:
        ultralytics_models = list(ADETAILER_FALLBACK_ULTRALYTICS_DETECTORS)
        source = "fallback"

    entries: list[dict[str, object]] = [
        {
            "id": DEFAULT_ADETAILER_DETECTOR,
            "label": DEFAULT_ADETAILER_DETECTOR,
            "family": "none",
            "source": "builtin",
            "supports_class_filter": False,
        }
    ]

    for detector in ultralytics_models:
        detector_family = classify_ultralytics_detector_family(detector)
        entries.append(
            {
                "id": detector,
                "label": detector,
                "family": detector_family,
                "provider_family": detector_family,
                "source": source,
                "supports_class_filter": supports_detector_class_filter(detector),
                "supports_mask_refine": detector_family == "ultralytics_segm",
            }
        )

    for detector in ADETAILER_MEDIAPIPE_DETECTORS:
        entries.append(
            {
                "id": detector,
                "label": detector,
                "family": "mediapipe_face",
                "provider_family": "mediapipe_face",
                "source": "builtin",
                "supports_class_filter": False,
                "supports_mask_refine": False,
            }
        )
    return entries, source


def build_adetailer_availability_payload(
    *,
    detector_entries: list[dict[str, object]],
    detector_source: str,
    controlnet_models: list[str],
    detector_runtime: dict[str, object],
    degraded_warning_codes: list[str],
) -> dict[str, object]:
    return {
        "execution_backend": "rookieui_comfy_native_refinement_pipeline",
        "runtime_stages": ["base_decode", "detect_mask", "inpaint_encode", "refine_sampler", "final_decode"],
        "detector_source": detector_source,
        "detector_count": len(detector_entries),
        "controlnet_model_count": len(controlnet_models),
        "detector_runtime": detector_runtime,
        "detector_provider_families": list(ADETAILER_DETECTOR_PROVIDER_FAMILIES),
        "degraded_warning_codes": list(degraded_warning_codes),
    }


def build_adetailer_catalog_payload(
    *,
    contract_meta: dict[str, object],
    detector_entries: list[dict[str, object]],
    detector_source: str,
    compatibility_payload: dict[str, object],
    controlnet_models: list[str],
    controlnet_modules: list[str],
    inventory: object,
    availability_payload: dict[str, object],
    warning_code_payload: dict[str, str],
) -> dict[str, object]:
    checkpoint_choices = list(
        dict.fromkeys(
            [
                *_coerce_string_list(getattr(inventory, "checkpoints", [])),
                *_coerce_string_list(getattr(inventory, "diffusion_models", [])),
            ]
        )
    )

    # IMPORTANT: keep this payload Comfy-native and inventory-backed; future runtime work must build on this seam instead
    # of reintroducing A1111 script-owned detector/runtime state.
    return {
        "source": detector_source,
        "contract": contract_meta,
        "detector_list": [entry["id"] for entry in detector_entries],
        "detectors": detector_entries,
        "default_detector": DEFAULT_ADETAILER_DETECTOR,
        "prompt_tokens": list(ADETAILER_PROMPT_TOKENS),
        "skip_img2img_surfaces": ["img2img"],
        "controlnet_modes": list(ADETAILER_CONTROLNET_MODES),
        "controlnet_model_list": list(controlnet_models),
        "controlnet_default_model": "",
        "controlnet_module_list": list(controlnet_modules),
        "controlnet_default_module": DEFAULT_ADETAILER_CONTROLNET_MODULE,
        "checkpoint_choices": checkpoint_choices,
        "vae_choices": _coerce_string_list(getattr(inventory, "vae", [])),
        "sampler_choices": [entry["title"] for entry in compatibility_payload.get("samplers", []) if isinstance(entry, dict)],
        "scheduler_choices": [
            entry["title"] for entry in compatibility_payload.get("schedulers", []) if isinstance(entry, dict)
        ],
        "mask_filter_methods": list(ADETAILER_MASK_FILTER_METHODS),
        "mask_merge_modes": list(ADETAILER_MASK_MERGE_MODES),
        "availability": availability_payload,
        "warning_codes": warning_code_payload,
    }


def build_adetailer_capability_payload(
    *,
    contract_meta: dict[str, object],
    availability_payload: dict[str, object],
    warning_code_payload: dict[str, str],
) -> dict[str, object]:
    return {
        "contract": contract_meta,
        "behavior_source": "integrated_detailer_contract",
        "ui_reference": "localhost_7860_a1111_integrated_host",
        "execution_backend": "rookieui_comfy_native_refinement_pipeline",
        "skip_img2img_surfaces": ["img2img"],
        "controlnet_modes": list(ADETAILER_CONTROLNET_MODES),
        "prompt_tokens": list(ADETAILER_PROMPT_TOKENS),
        "warning_code_contract": "stable_f81",
        "availability": availability_payload,
        "warning_codes": warning_code_payload,
        "routes": ["/rookieui/adetailer/catalog"],
    }
