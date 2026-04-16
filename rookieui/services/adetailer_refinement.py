from __future__ import annotations

from rookieui.contracts.adetailer import (
    ADETAILER_CONTROLNET_MODES,
    ADETAILER_MASK_FILTER_METHODS,
    ADETAILER_MASK_MERGE_MODES,
    ADETAILER_MEDIAPIPE_DETECTORS,
    NormalizedADetailerControlNetRequest,
    NormalizedADetailerUnitRequest,
)
from rookieui.security.request_guard import normalize_option_label, normalize_prompt_text, resolve_inventory_selector
from rookieui.services.coercion import coerce_bool as _coerce_bool
from rookieui.services.coercion import coerce_float as _coerce_float
from rookieui.services.coercion import coerce_int as _coerce_int
from rookieui.services.controlnet import _normalize_controlnet_advanced_block
from rookieui.services.adetailer_catalog import (
    DEFAULT_ADETAILER_CONTROLNET_MODULE,
    DEFAULT_ADETAILER_DETECTOR,
    classify_ultralytics_detector_family,
    supports_detector_class_filter,
)
from rookieui.services.adetailer_warnings import (
    ADETAILER_DEGRADED_WARNING_CODES,
    ADETAILER_WARNING_CONTROLNET_CUSTOM_MODEL_MISSING,
    ADETAILER_WARNING_CONTROLNET_PASSTHROUGH_EMPTY,
    ADETAILER_WARNING_DETECTOR_NOT_IN_CATALOG,
    ADETAILER_WARNING_DETECTOR_RUNTIME_FALLBACK_MASK,
    ADETAILER_WARNING_NO_ACTIVE_UNITS,
)

_ADETAILER_CONTROLNET_MODEL_SENTINELS = {"", "None"}
_ADETAILER_CHECKPOINT_SENTINELS = {"", "__host_default__", "Use same checkpoint"}
_ADETAILER_VAE_SENTINELS = {"", "Automatic", "Use same VAE"}
_ADETAILER_SCHEDULER_SENTINELS = {"", "Use same scheduler"}
_ADETAILER_SAMPLER_COMPATIBILITY_LABELS = {"DPM++ 2M Karras"}


def normalize_choice(value: object, field_name: str, valid_values: tuple[str, ...], default_value: str) -> str:
    normalized = normalize_option_label(value, field_name, max_length=64)
    if not normalized:
        return default_value
    if normalized not in valid_values:
        raise ValueError(f"{field_name} is unsupported.")
    return normalized


def normalize_detector(value: object, *, detector_choices: list[str], strict_match: bool, field_name: str) -> str:
    normalized = normalize_option_label(value, field_name, max_length=128) or DEFAULT_ADETAILER_DETECTOR
    if normalized == DEFAULT_ADETAILER_DETECTOR:
        return normalized
    if strict_match and normalized not in detector_choices:
        raise ValueError(f"{field_name} is unsupported.")
    return normalized


def resolve_detector_family(detector: str) -> str:
    if detector == DEFAULT_ADETAILER_DETECTOR:
        return "none"
    if detector in ADETAILER_MEDIAPIPE_DETECTORS:
        return "mediapipe_face"
    return classify_ultralytics_detector_family(detector)


def normalize_controlnet_block(
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

    mode = normalize_choice(raw_block.get("mode"), f"{field_prefix}.mode", ADETAILER_CONTROLNET_MODES, "none")
    if mode != "custom":
        return NormalizedADetailerControlNetRequest(mode=mode)

    model = resolve_inventory_selector(
        raw_block.get("model"),
        f"{field_prefix}.model",
        default_value="",
        inventory_selectors=controlnet_models,
        strict_match=strict_model_match,
    )
    module = (
        normalize_option_label(raw_block.get("module"), f"{field_prefix}.module", max_length=128)
        or DEFAULT_ADETAILER_CONTROLNET_MODULE
    )
    if module != DEFAULT_ADETAILER_CONTROLNET_MODULE and module not in controlnet_modules:
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


def build_normalized_unit_request(
    raw_unit: dict[str, object],
    *,
    index: int,
    detector_choices: list[str],
    strict_inventory_match: bool,
    controlnet_model_list: list[str],
    controlnet_module_list: list[str],
    primary_model_selectors: list[str],
    vae_choices: list[str],
    sampler_choices: list[str],
    scheduler_choices: list[str],
) -> NormalizedADetailerUnitRequest:
    field_prefix = f"adetailer.units[{index}]"
    prompt_text = normalize_prompt_text(raw_unit.get("prompt", ""), f"{field_prefix}.prompt")
    negative_prompt_text = normalize_prompt_text(raw_unit.get("negative_prompt", ""), f"{field_prefix}.negative_prompt")
    detector = normalize_detector(
        raw_unit.get("detector"),
        detector_choices=detector_choices,
        strict_match=strict_inventory_match,
        field_name=f"{field_prefix}.detector",
    )
    detector_family = resolve_detector_family(detector)
    detector_classes = normalize_option_label(raw_unit.get("detector_classes"), f"{field_prefix}.detector_classes", max_length=256)
    if not supports_detector_class_filter(detector):
        detector_classes = ""

    confidence = round(_coerce_float(raw_unit.get("confidence", 0.3), f"{field_prefix}.confidence"), 3)
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError(f"{field_prefix}.confidence must be between 0.0 and 1.0.")
    mask_filter_method = normalize_choice(
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
    mask_merge_mode = normalize_choice(
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
            inventory_selectors=vae_choices,
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
    use_noise_multiplier = _coerce_bool(raw_unit.get("use_noise_multiplier", False), f"{field_prefix}.use_noise_multiplier", strict=False)
    noise_multiplier = round(_coerce_float(raw_unit.get("noise_multiplier", 1.0), f"{field_prefix}.noise_multiplier"), 2)
    if noise_multiplier < 0.5 or noise_multiplier > 1.5:
        raise ValueError(f"{field_prefix}.noise_multiplier must be between 0.5 and 1.5.")
    use_clip_skip = _coerce_bool(raw_unit.get("use_clip_skip", False), f"{field_prefix}.use_clip_skip", strict=False)
    clip_skip = _coerce_int(raw_unit.get("clip_skip", 1), f"{field_prefix}.clip_skip")
    if clip_skip < 1 or clip_skip > 12:
        raise ValueError(f"{field_prefix}.clip_skip must be between 1 and 12.")
    restore_face = _coerce_bool(raw_unit.get("restore_face", False), f"{field_prefix}.restore_face", strict=False)

    controlnet = normalize_controlnet_block(
        raw_unit.get("controlnet"),
        controlnet_models=controlnet_model_list,
        controlnet_modules=controlnet_module_list,
        strict_model_match=strict_inventory_match,
        field_prefix=f"{field_prefix}.controlnet",
    )
    return NormalizedADetailerUnitRequest(
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


def finalize_adetailer_warnings_and_diagnostics(
    *,
    enabled: bool,
    units: list[NormalizedADetailerUnitRequest],
    detector_choices: list[str],
    primary_controlnet_unit_count: int,
    detector_runtime: dict[str, object],
    warning_codes: list[str],
    detector_runtime_is_degraded_fn,
    summarize_detector_runtime_fn,
) -> tuple[list[str], dict[str, object]]:
    active_units = [
        unit
        for unit in units
        if unit.enabled and str(unit.detector or "").strip() and str(unit.detector or "").strip() != DEFAULT_ADETAILER_DETECTOR
    ]
    if enabled and not active_units:
        warning_codes.append(ADETAILER_WARNING_NO_ACTIVE_UNITS)
    for unit in active_units:
        if unit.detector not in detector_choices:
            warning_codes.append(ADETAILER_WARNING_DETECTOR_NOT_IN_CATALOG)
        if detector_runtime_is_degraded_fn(unit.detector_family):
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
        "detector_runtime": summarize_detector_runtime_fn([unit.detector_family for unit in active_units]) if enabled else "disabled",
        "detector_runtime_by_family": detector_runtime,
        "degraded": bool(set(warning_codes) & set(ADETAILER_DEGRADED_WARNING_CODES)),
    }
    return warning_codes, diagnostics
