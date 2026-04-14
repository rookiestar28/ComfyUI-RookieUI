from __future__ import annotations

from rookieui.contracts.adetailer import (
    ADETAILER_CONTROLNET_MODES,
    ADETAILER_DETECTOR_PROVIDER_FAMILIES,
    ADETAILER_FALLBACK_ULTRALYTICS_DETECTORS,
    ADETAILER_INTEGRATED_DEFAULT_UNIT_COUNT,
    ADETAILER_MASK_FILTER_METHODS,
    ADETAILER_MASK_MERGE_MODES,
    ADETAILER_MEDIAPIPE_DETECTORS,
    ADETAILER_PROMPT_TOKENS,
    NormalizedADetailerControlNetRequest,
    NormalizedADetailerRequest,
    NormalizedADetailerUnitRequest,
    build_adetailer_integrated_contract_meta,
)
from rookieui.security.request_guard import normalize_option_label, normalize_prompt_text, resolve_inventory_selector
from rookieui.services.coercion import coerce_bool as _coerce_bool
from rookieui.services.coercion import coerce_float as _coerce_float
from rookieui.services.coercion import coerce_int as _coerce_int
from rookieui.services.compatibility import build_compatibility_payload
from rookieui.services.controlnet import (
    _normalize_controlnet_advanced_block,
    build_controlnet_model_list_payload,
    build_controlnet_module_list_payload,
)
from rookieui.services.model_inventory import resolve_primary_model_selector_context
from rookieui.services.adetailer_runtime import (
    build_detector_runtime_availability,
    detector_runtime_is_degraded,
    summarize_detector_runtime,
)
from rookieui.services.model_inventory import discover_model_inventory

ADETAILER_WARNING_UNIT_LIMIT_TRUNCATED = "ADETAILER_UNIT_LIMIT_TRUNCATED"
ADETAILER_WARNING_SKIP_IMG2IMG_IGNORED = "ADETAILER_SKIP_IMG2IMG_IGNORED"
ADETAILER_WARNING_NO_ACTIVE_UNITS = "ADETAILER_NO_ACTIVE_UNITS"
ADETAILER_WARNING_DETECTOR_NOT_IN_CATALOG = "ADETAILER_DETECTOR_NOT_IN_CATALOG"
ADETAILER_WARNING_DETECTOR_RUNTIME_FALLBACK_MASK = "ADETAILER_DETECTOR_RUNTIME_FALLBACK_MASK"
ADETAILER_WARNING_CONTROLNET_PASSTHROUGH_EMPTY = "ADETAILER_CONTROLNET_PASSTHROUGH_EMPTY"
ADETAILER_WARNING_CONTROLNET_CUSTOM_MODEL_MISSING = "ADETAILER_CONTROLNET_CUSTOM_MODEL_MISSING"
_ADETAILER_WARNING_MESSAGES = {
    ADETAILER_WARNING_UNIT_LIMIT_TRUNCATED: "ADetailer unit payload exceeded the supported 4-unit contract and was truncated.",
    ADETAILER_WARNING_SKIP_IMG2IMG_IGNORED: "ADetailer skip-img2img is only meaningful for img2img surfaces and was ignored.",
    ADETAILER_WARNING_NO_ACTIVE_UNITS: "ADetailer is enabled but no enabled unit has a detector selected.",
    ADETAILER_WARNING_DETECTOR_NOT_IN_CATALOG: "ADetailer detector is not present in the current host catalog; fallback mask behavior may be used.",
    ADETAILER_WARNING_DETECTOR_RUNTIME_FALLBACK_MASK: "ADetailer detector runtime degraded to RookieUI's fallback mask seam for the selected provider family.",
    ADETAILER_WARNING_CONTROLNET_PASSTHROUGH_EMPTY: "ADetailer ControlNet passthrough was requested but no primary ControlNet unit is enabled.",
    ADETAILER_WARNING_CONTROLNET_CUSTOM_MODEL_MISSING: "ADetailer custom ControlNet mode was requested without a ControlNet model.",
}
_ADETAILER_CONTROLNET_MODEL_SENTINELS = {"", "None"}
_ADETAILER_CHECKPOINT_SENTINELS = {"", "__host_default__", "Use same checkpoint"}
_ADETAILER_VAE_SENTINELS = {"", "Automatic", "Use same VAE"}
_ADETAILER_SCHEDULER_SENTINELS = {"", "Use same scheduler"}
_ADETAILER_SAMPLER_COMPATIBILITY_LABELS = {"DPM++ 2M Karras"}
_ADETAILER_DEFAULT_DETECTOR = "None"
_ADETAILER_CONTROLNET_DEFAULT_MODULE = "None"
_ADETAILER_WORLD_MARKER = "-world"
_ADETAILER_SEGM_MARKERS = ("-seg", "_seg", "segm")


def _warning_messages_from_codes(codes: list[str]) -> list[str]:
    return [_ADETAILER_WARNING_MESSAGES[code] for code in codes if code in _ADETAILER_WARNING_MESSAGES]


def build_adetailer_warning_code_payload() -> dict[str, str]:
    return dict(_ADETAILER_WARNING_MESSAGES)


def build_adetailer_availability_payload() -> dict[str, object]:
    detectors, detector_source = _build_detector_entries()
    controlnet_models = build_controlnet_model_list_payload()
    detector_runtime = build_detector_runtime_availability()
    return {
        "execution_backend": "rookieui_comfy_native_refinement_pipeline",
        "runtime_stages": ["base_decode", "detect_mask", "inpaint_encode", "refine_sampler", "final_decode"],
        "detector_source": detector_source,
        "detector_count": len(detectors),
        "controlnet_model_count": len(list(controlnet_models.get("model_list", []))),
        "detector_runtime": detector_runtime,
        "detector_provider_families": list(ADETAILER_DETECTOR_PROVIDER_FAMILIES),
        "degraded_warning_codes": [
            ADETAILER_WARNING_DETECTOR_NOT_IN_CATALOG,
            ADETAILER_WARNING_DETECTOR_RUNTIME_FALLBACK_MASK,
            ADETAILER_WARNING_CONTROLNET_PASSTHROUGH_EMPTY,
            ADETAILER_WARNING_CONTROLNET_CUSTOM_MODEL_MISSING,
        ],
    }


def _classify_ultralytics_detector_family(detector: str) -> str:
    normalized = str(detector or "").strip().lower()
    if any(marker in normalized for marker in _ADETAILER_SEGM_MARKERS):
        return "ultralytics_segm"
    return "ultralytics_bbox"


def _supports_detector_class_filter(detector: str) -> bool:
    return _ADETAILER_WORLD_MARKER in str(detector or "").strip().lower()


def _build_detector_entries() -> tuple[list[dict[str, object]], str]:
    inventory = discover_model_inventory()
    ultralytics_models = [
        selector
        for selector in [*inventory.ultralytics_bbox, *inventory.ultralytics_segm]
        if isinstance(selector, str) and selector.strip()
    ]
    source = inventory.source
    if not ultralytics_models:
        ultralytics_models = list(ADETAILER_FALLBACK_ULTRALYTICS_DETECTORS)
        source = "fallback"

    entries: list[dict[str, object]] = [
        {
            "id": _ADETAILER_DEFAULT_DETECTOR,
            "label": _ADETAILER_DEFAULT_DETECTOR,
            "family": "none",
            "source": "builtin",
            "supports_class_filter": False,
        }
    ]

    for detector in ultralytics_models:
        detector_family = _classify_ultralytics_detector_family(detector)
        entries.append(
            {
                "id": detector,
                "label": detector,
                "family": detector_family,
                "provider_family": detector_family,
                "source": source,
                "supports_class_filter": _supports_detector_class_filter(detector),
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


def build_adetailer_catalog_payload() -> dict[str, object]:
    detectors, detector_source = _build_detector_entries()
    compatibility = build_compatibility_payload()
    controlnet_models = build_controlnet_model_list_payload()
    controlnet_modules = build_controlnet_module_list_payload()
    inventory = discover_model_inventory()

    checkpoint_choices = list(
        dict.fromkeys(
            [
                *[value for value in inventory.checkpoints if isinstance(value, str) and value.strip()],
                *[
                    value
                    for value in getattr(inventory, "diffusion_models", [])
                    if isinstance(value, str) and value.strip()
                ],
            ]
        )
    )

    # IMPORTANT: keep this payload Comfy-native and inventory-backed; future runtime work must build on this seam instead
    # of reintroducing A1111 script-owned detector/runtime state.
    return {
        "source": detector_source,
        "contract": build_adetailer_integrated_contract_meta(),
        "detector_list": [entry["id"] for entry in detectors],
        "detectors": detectors,
        "default_detector": _ADETAILER_DEFAULT_DETECTOR,
        "prompt_tokens": list(ADETAILER_PROMPT_TOKENS),
        "skip_img2img_surfaces": ["img2img"],
        "controlnet_modes": list(ADETAILER_CONTROLNET_MODES),
        "controlnet_model_list": list(controlnet_models.get("model_list", [])),
        "controlnet_default_model": "",
        "controlnet_module_list": list(controlnet_modules.get("module_list", [])),
        "controlnet_default_module": str(
            controlnet_modules.get("default_module", _ADETAILER_CONTROLNET_DEFAULT_MODULE)
        ),
        "checkpoint_choices": checkpoint_choices,
        "vae_choices": list(inventory.vae),
        "sampler_choices": [entry["title"] for entry in compatibility.get("samplers", []) if isinstance(entry, dict)],
        "scheduler_choices": [entry["title"] for entry in compatibility.get("schedulers", []) if isinstance(entry, dict)],
        "mask_filter_methods": list(ADETAILER_MASK_FILTER_METHODS),
        "mask_merge_modes": list(ADETAILER_MASK_MERGE_MODES),
        "availability": build_adetailer_availability_payload(),
        "warning_codes": build_adetailer_warning_code_payload(),
    }


def build_adetailer_capability_payload() -> dict[str, object]:
    return {
        "contract": build_adetailer_integrated_contract_meta(),
        "behavior_source": "integrated_detailer_contract",
        "ui_reference": "localhost_7860_a1111_integrated_host",
        "execution_backend": "rookieui_comfy_native_refinement_pipeline",
        "skip_img2img_surfaces": ["img2img"],
        "controlnet_modes": list(ADETAILER_CONTROLNET_MODES),
        "prompt_tokens": list(ADETAILER_PROMPT_TOKENS),
        "warning_code_contract": "stable_f81",
        "availability": build_adetailer_availability_payload(),
        "warning_codes": build_adetailer_warning_code_payload(),
        "routes": ["/rookieui/adetailer/catalog"],
    }


def _normalize_choice(value: object, field_name: str, valid_values: tuple[str, ...], default_value: str) -> str:
    normalized = normalize_option_label(value, field_name, max_length=64)
    if not normalized:
        return default_value
    if normalized not in valid_values:
        raise ValueError(f"{field_name} is unsupported.")
    return normalized


def _normalize_detector(value: object, *, detector_choices: list[str], strict_match: bool, field_name: str) -> str:
    normalized = normalize_option_label(value, field_name, max_length=128) or _ADETAILER_DEFAULT_DETECTOR
    if normalized == _ADETAILER_DEFAULT_DETECTOR:
        return normalized
    if strict_match and normalized not in detector_choices:
        raise ValueError(f"{field_name} is unsupported.")
    return normalized


def _resolve_detector_family(detector: str) -> str:
    if detector == _ADETAILER_DEFAULT_DETECTOR:
        return "none"
    if detector in ADETAILER_MEDIAPIPE_DETECTORS:
        return "mediapipe_face"
    return _classify_ultralytics_detector_family(detector)


def _normalize_controlnet_block(
    raw_block: object,
    *,
    controlnet_models: list[str],
    controlnet_modules: list[str],
    strict_model_match: bool,
    field_prefix: str,
) -> NormalizedADetailerControlNetRequest:
    if raw_block in (None, ""):
        raw_block = {}
    if not isinstance(raw_block, dict):
        raise ValueError(f"{field_prefix} must be an object.")

    mode = _normalize_choice(raw_block.get("mode"), f"{field_prefix}.mode", ADETAILER_CONTROLNET_MODES, "none")
    if mode != "custom":
        return NormalizedADetailerControlNetRequest(mode=mode)

    model = resolve_inventory_selector(
        raw_block.get("model"),
        f"{field_prefix}.model",
        default_value="",
        inventory_selectors=controlnet_models,
        strict_match=strict_model_match,
    )
    module = normalize_option_label(raw_block.get("module"), f"{field_prefix}.module", max_length=128) or _ADETAILER_CONTROLNET_DEFAULT_MODULE
    if module != _ADETAILER_CONTROLNET_DEFAULT_MODULE and module not in controlnet_modules:
        raise ValueError(f"{field_prefix}.module is unsupported.")

    weight = round(_coerce_float(raw_block.get("weight", 1.0), f"{field_prefix}.weight"), 3)
    if weight < 0.0 or weight > 1.0:
        raise ValueError(f"{field_prefix}.weight must be between 0.0 and 1.0.")
    guidance_start = round(_coerce_float(raw_block.get("guidance_start", 0.0), f"{field_prefix}.guidance_start"), 3)
    guidance_end = round(_coerce_float(raw_block.get("guidance_end", 1.0), f"{field_prefix}.guidance_end"), 3)
    if guidance_start < 0.0 or guidance_start > 1.0:
        raise ValueError(f"{field_prefix}.guidance_start must be between 0.0 and 1.0.")
    if guidance_end < 0.0 or guidance_end > 1.0:
        raise ValueError(f"{field_prefix}.guidance_end must be between 0.0 and 1.0.")
    if guidance_start > guidance_end:
        raise ValueError(f"{field_prefix}.guidance_start must not exceed guidance_end.")

    return NormalizedADetailerControlNetRequest(
        mode=mode,
        model="" if model in _ADETAILER_CONTROLNET_MODEL_SENTINELS else model,
        module=module,
        weight=weight,
        guidance_start=guidance_start,
        guidance_end=guidance_end,
        advanced=_normalize_controlnet_advanced_block(
            raw_block.get("advanced"),
            field_prefix=f"{field_prefix}.advanced",
        ),
    )


def normalize_adetailer_payload(
    payload: dict[str, object],
    *,
    profile_id: str,
    surface: str,
    strict_inventory_match: bool,
    primary_controlnet_unit_count: int = 0,
) -> NormalizedADetailerRequest:
    raw_block = payload.get("adetailer", {})
    if raw_block in (None, ""):
        raw_block = {}
    if not isinstance(raw_block, dict):
        raise ValueError("adetailer must be an object.")

    enabled = _coerce_bool(raw_block.get("enabled", False), "adetailer.enabled", strict=False)
    skip_img2img = _coerce_bool(raw_block.get("skip_img2img", False), "adetailer.skip_img2img", strict=False)
    warning_codes: list[str] = []
    if surface != "img2img" and skip_img2img:
        warning_codes.append(ADETAILER_WARNING_SKIP_IMG2IMG_IGNORED)
        skip_img2img = False

    raw_units = raw_block.get("units", [])
    if raw_units in (None, ""):
        raw_units = []
    if not isinstance(raw_units, list):
        raise ValueError("adetailer.units must be an array.")
    if len(raw_units) > ADETAILER_INTEGRATED_DEFAULT_UNIT_COUNT:
        warning_codes.append(ADETAILER_WARNING_UNIT_LIMIT_TRUNCATED)

    detector_entries, _ = _build_detector_entries()
    detector_choices = [str(entry["id"]) for entry in detector_entries]
    controlnet_model_list = list(build_controlnet_model_list_payload().get("model_list", []))
    controlnet_module_list = list(build_controlnet_module_list_payload().get("module_list", []))
    inventory = discover_model_inventory()
    _, primary_model_selectors, _ = resolve_primary_model_selector_context(profile_id, inventory)
    compatibility = build_compatibility_payload()
    sampler_choices = [entry["title"] for entry in compatibility.get("samplers", []) if isinstance(entry, dict)]
    scheduler_choices = [entry["title"] for entry in compatibility.get("schedulers", []) if isinstance(entry, dict)]

    units: list[NormalizedADetailerUnitRequest] = []
    for index in range(ADETAILER_INTEGRATED_DEFAULT_UNIT_COUNT):
        raw_unit = raw_units[index] if index < len(raw_units) and isinstance(raw_units[index], dict) else {}
        field_prefix = f"adetailer.units[{index}]"
        prompt_text = normalize_prompt_text(raw_unit.get("prompt", ""), f"{field_prefix}.prompt")
        negative_prompt_text = normalize_prompt_text(raw_unit.get("negative_prompt", ""), f"{field_prefix}.negative_prompt")
        raw_detector_value = raw_unit.get("detector")
        detector = _normalize_detector(
            raw_detector_value,
            detector_choices=detector_choices,
            strict_match=strict_inventory_match,
            field_name=f"{field_prefix}.detector",
        )
        detector_family = _resolve_detector_family(detector)
        detector_classes = normalize_option_label(raw_unit.get("detector_classes"), f"{field_prefix}.detector_classes", max_length=256)
        if not _supports_detector_class_filter(detector):
            detector_classes = ""

        confidence = round(_coerce_float(raw_unit.get("confidence", 0.3), f"{field_prefix}.confidence"), 3)
        if confidence < 0.0 or confidence > 1.0:
            raise ValueError(f"{field_prefix}.confidence must be between 0.0 and 1.0.")
        mask_filter_method = _normalize_choice(
            raw_unit.get("mask_filter_method"),
            f"{field_prefix}.mask_filter_method",
            ADETAILER_MASK_FILTER_METHODS,
            "Area",
        )
        mask_k = _coerce_int(raw_unit.get("mask_k", 0), f"{field_prefix}.mask_k")
        if mask_k < 0 or mask_k > 100:
            raise ValueError(f"{field_prefix}.mask_k must be between 0 and 100.")
        mask_min_ratio = round(_coerce_float(raw_unit.get("mask_min_ratio", 0.0), f"{field_prefix}.mask_min_ratio"), 4)
        mask_max_ratio = round(_coerce_float(raw_unit.get("mask_max_ratio", 1.0), f"{field_prefix}.mask_max_ratio"), 4)
        if mask_min_ratio < 0.0 or mask_min_ratio > 1.0:
            raise ValueError(f"{field_prefix}.mask_min_ratio must be between 0.0 and 1.0.")
        if mask_max_ratio < 0.0 or mask_max_ratio > 1.0:
            raise ValueError(f"{field_prefix}.mask_max_ratio must be between 0.0 and 1.0.")
        if mask_min_ratio > mask_max_ratio:
            raise ValueError(f"{field_prefix}.mask_min_ratio must not exceed mask_max_ratio.")
        x_offset = _coerce_int(raw_unit.get("x_offset", 0), f"{field_prefix}.x_offset")
        y_offset = _coerce_int(raw_unit.get("y_offset", 0), f"{field_prefix}.y_offset")
        dilate_erode = _coerce_int(raw_unit.get("dilate_erode", 4), f"{field_prefix}.dilate_erode")
        if dilate_erode < -128 or dilate_erode > 128:
            raise ValueError(f"{field_prefix}.dilate_erode must be between -128 and 128.")
        mask_merge_mode = _normalize_choice(
            raw_unit.get("mask_merge_mode"),
            f"{field_prefix}.mask_merge_mode",
            ADETAILER_MASK_MERGE_MODES,
            "None",
        )
        mask_blur = _coerce_int(raw_unit.get("mask_blur", 4), f"{field_prefix}.mask_blur")
        if mask_blur < 0 or mask_blur > 64:
            raise ValueError(f"{field_prefix}.mask_blur must be between 0 and 64.")
        denoising_strength = round(_coerce_float(raw_unit.get("denoising_strength", 0.4), f"{field_prefix}.denoising_strength"), 3)
        if denoising_strength < 0.0 or denoising_strength > 1.0:
            raise ValueError(f"{field_prefix}.denoising_strength must be between 0.0 and 1.0.")
        inpaint_only_masked = _coerce_bool(raw_unit.get("inpaint_only_masked", True), f"{field_prefix}.inpaint_only_masked", strict=False)
        inpaint_padding = _coerce_int(raw_unit.get("inpaint_padding", 32), f"{field_prefix}.inpaint_padding")
        if inpaint_padding < 0 or inpaint_padding > 256:
            raise ValueError(f"{field_prefix}.inpaint_padding must be between 0 and 256.")
        use_inpaint_size = _coerce_bool(raw_unit.get("use_inpaint_size", False), f"{field_prefix}.use_inpaint_size", strict=False)
        inpaint_width = _coerce_int(raw_unit.get("inpaint_width", 512), f"{field_prefix}.inpaint_width")
        inpaint_height = _coerce_int(raw_unit.get("inpaint_height", 512), f"{field_prefix}.inpaint_height")
        if inpaint_width < 64 or inpaint_width > 2048 or inpaint_width % 8 != 0:
            raise ValueError(f"{field_prefix}.inpaint_width must be between 64 and 2048 and divisible by 8.")
        if inpaint_height < 64 or inpaint_height > 2048 or inpaint_height % 8 != 0:
            raise ValueError(f"{field_prefix}.inpaint_height must be between 64 and 2048 and divisible by 8.")
        use_steps = _coerce_bool(raw_unit.get("use_steps", False), f"{field_prefix}.use_steps", strict=False)
        steps = _coerce_int(raw_unit.get("steps", 28), f"{field_prefix}.steps")
        if steps < 1 or steps > 150:
            raise ValueError(f"{field_prefix}.steps must be between 1 and 150.")
        use_cfg_scale = _coerce_bool(raw_unit.get("use_cfg_scale", False), f"{field_prefix}.use_cfg_scale", strict=False)
        cfg_scale = round(_coerce_float(raw_unit.get("cfg_scale", 7.0), f"{field_prefix}.cfg_scale"), 2)
        if cfg_scale < 1.0 or cfg_scale > 30.0:
            raise ValueError(f"{field_prefix}.cfg_scale must be between 1.0 and 30.0.")
        use_checkpoint = _coerce_bool(raw_unit.get("use_checkpoint", False), f"{field_prefix}.use_checkpoint", strict=False)
        raw_checkpoint_name = str(raw_unit.get("checkpoint_name") or "").strip()
        if not use_checkpoint or raw_checkpoint_name in _ADETAILER_CHECKPOINT_SENTINELS:
            # CRITICAL: ADetailer unit checkpoint overrides must stay sentinel-safe and profile-aware;
            # validating "__host_default__" or diffusion-model selectors against the legacy checkpoints list breaks SDXL/native-family generation.
            checkpoint_name = "Use same checkpoint"
        else:
            checkpoint_name = resolve_inventory_selector(
                raw_checkpoint_name,
                f"{field_prefix}.checkpoint_name",
                default_value="",
                inventory_selectors=primary_model_selectors,
                strict_match=strict_inventory_match,
            )
        use_vae = _coerce_bool(raw_unit.get("use_vae", False), f"{field_prefix}.use_vae", strict=False)
        raw_vae_name = str(raw_unit.get("vae_name") or "").strip()
        if not use_vae or raw_vae_name in _ADETAILER_VAE_SENTINELS:
            vae_name = "Use same VAE"
        else:
            vae_name = resolve_inventory_selector(
                raw_vae_name,
                f"{field_prefix}.vae_name",
                default_value="",
                inventory_selectors=inventory.vae,
                strict_match=strict_inventory_match,
            )
        if vae_name in _ADETAILER_VAE_SENTINELS:
            vae_name = "Use same VAE"
        use_sampler = _coerce_bool(raw_unit.get("use_sampler", False), f"{field_prefix}.use_sampler", strict=False)
        sampler_name = normalize_option_label(raw_unit.get("sampler_name"), f"{field_prefix}.sampler_name", max_length=96) or "DPM++ 2M Karras"
        if sampler_name not in sampler_choices and sampler_name not in _ADETAILER_SAMPLER_COMPATIBILITY_LABELS:
            raise ValueError(f"{field_prefix}.sampler_name is unsupported.")
        scheduler_name = normalize_option_label(raw_unit.get("scheduler_name"), f"{field_prefix}.scheduler_name", max_length=96) or "Use same scheduler"
        if scheduler_name not in _ADETAILER_SCHEDULER_SENTINELS and scheduler_name not in scheduler_choices:
            raise ValueError(f"{field_prefix}.scheduler_name is unsupported.")
        use_noise_multiplier = _coerce_bool(
            raw_unit.get("use_noise_multiplier", False),
            f"{field_prefix}.use_noise_multiplier",
            strict=False,
        )
        noise_multiplier = round(_coerce_float(raw_unit.get("noise_multiplier", 1.0), f"{field_prefix}.noise_multiplier"), 2)
        if noise_multiplier < 0.5 or noise_multiplier > 1.5:
            raise ValueError(f"{field_prefix}.noise_multiplier must be between 0.5 and 1.5.")
        use_clip_skip = _coerce_bool(raw_unit.get("use_clip_skip", False), f"{field_prefix}.use_clip_skip", strict=False)
        clip_skip = _coerce_int(raw_unit.get("clip_skip", 1), f"{field_prefix}.clip_skip")
        if clip_skip < 1 or clip_skip > 12:
            raise ValueError(f"{field_prefix}.clip_skip must be between 1 and 12.")
        restore_face = _coerce_bool(raw_unit.get("restore_face", False), f"{field_prefix}.restore_face", strict=False)

        controlnet = _normalize_controlnet_block(
            raw_unit.get("controlnet"),
            controlnet_models=controlnet_model_list,
            controlnet_modules=controlnet_module_list,
            strict_model_match=strict_inventory_match,
            field_prefix=f"{field_prefix}.controlnet",
        )
        units.append(
            NormalizedADetailerUnitRequest(
                enabled=_coerce_bool(raw_unit.get("enabled", True), f"{field_prefix}.enabled", strict=False),
                detector=detector,
                detector_family=detector_family,
                detector_classes=detector_classes,
                prompt=prompt_text,
                negative_prompt=negative_prompt_text,
                confidence=confidence,
                mask_filter_method=mask_filter_method,
                mask_k=mask_k,
                mask_min_ratio=mask_min_ratio,
                mask_max_ratio=mask_max_ratio,
                x_offset=x_offset,
                y_offset=y_offset,
                dilate_erode=dilate_erode,
                mask_merge_mode=mask_merge_mode,
                mask_blur=mask_blur,
                denoising_strength=denoising_strength,
                inpaint_only_masked=inpaint_only_masked,
                inpaint_padding=inpaint_padding,
                use_inpaint_size=use_inpaint_size,
                inpaint_width=inpaint_width,
                inpaint_height=inpaint_height,
                use_steps=use_steps,
                steps=steps,
                use_cfg_scale=use_cfg_scale,
                cfg_scale=cfg_scale,
                use_checkpoint=use_checkpoint,
                checkpoint_name=checkpoint_name,
                use_vae=use_vae,
                vae_name=vae_name,
                use_sampler=use_sampler,
                sampler_name=sampler_name,
                scheduler_name=scheduler_name,
                use_noise_multiplier=use_noise_multiplier,
                noise_multiplier=noise_multiplier,
                use_clip_skip=use_clip_skip,
                clip_skip=clip_skip,
                restore_face=restore_face,
                prompt_uses_main=not bool(prompt_text),
                negative_prompt_uses_main=not bool(negative_prompt_text),
                refinement_context_id=f"adetailer_unit_{index + 1}",
                controlnet=controlnet,
            )
        )

    active_units = [
        unit
        for unit in units
        if unit.enabled and str(unit.detector or "").strip() and str(unit.detector or "").strip() != _ADETAILER_DEFAULT_DETECTOR
    ]
    detector_runtime = build_detector_runtime_availability()
    if enabled and not active_units:
        warning_codes.append(ADETAILER_WARNING_NO_ACTIVE_UNITS)
    for unit in active_units:
        if unit.detector not in detector_choices:
            warning_codes.append(ADETAILER_WARNING_DETECTOR_NOT_IN_CATALOG)
        if detector_runtime_is_degraded(unit.detector_family):
            # DEBUG HOTSPOT: keep this warning aligned with `RookieUIADetailerDetectMask` and
            # `rookieui.services.adetailer_runtime`; removing it would hide real runtime degradation from users.
            warning_codes.append(ADETAILER_WARNING_DETECTOR_RUNTIME_FALLBACK_MASK)
        if unit.controlnet.mode == "passthrough" and primary_controlnet_unit_count <= 0:
            warning_codes.append(ADETAILER_WARNING_CONTROLNET_PASSTHROUGH_EMPTY)
        if unit.controlnet.mode == "custom" and not unit.controlnet.model:
            warning_codes.append(ADETAILER_WARNING_CONTROLNET_CUSTOM_MODEL_MISSING)

    warning_codes = list(dict.fromkeys(warning_codes))
    diagnostics = {
        "active_unit_count": len(active_units) if enabled else 0,
        "primary_controlnet_unit_count": max(0, int(primary_controlnet_unit_count)),
        "detector_runtime": summarize_detector_runtime([unit.detector_family for unit in active_units]) if enabled else "disabled",
        "detector_runtime_by_family": detector_runtime,
        "degraded": bool(
            set(warning_codes)
            & {
                ADETAILER_WARNING_DETECTOR_NOT_IN_CATALOG,
                ADETAILER_WARNING_DETECTOR_RUNTIME_FALLBACK_MASK,
                ADETAILER_WARNING_CONTROLNET_PASSTHROUGH_EMPTY,
                ADETAILER_WARNING_CONTROLNET_CUSTOM_MODEL_MISSING,
            }
        ),
    }

    return NormalizedADetailerRequest(
        enabled=enabled,
        skip_img2img=skip_img2img,
        units=units,
        warning_codes=warning_codes,
        warnings=_warning_messages_from_codes(warning_codes),
        diagnostics=diagnostics,
    )
