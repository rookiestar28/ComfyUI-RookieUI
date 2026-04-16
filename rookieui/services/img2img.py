from __future__ import annotations

from rookieui.contracts.generation import Img2ImgRequest, NormalizedImg2ImgRequest
from rookieui.contracts.aliases import (
    DEFAULT_INPAINT_AREA as _DEFAULT_INPAINT_AREA,
    DEFAULT_MASKED_CONTENT as _DEFAULT_INPAINT_CONTENT,
    DEFAULT_MASK_MODE as _DEFAULT_MASK_MODE,
    DEFAULT_RESIZE_MODE as _DEFAULT_RESIZE_MODE,
    HIRES_UPSCALE_METHODS as _HIRES_UPSCALE_METHODS,
    INPAINT_AREA_ALIASES as _INPAINT_AREA_ALIASES,
    MASKED_CONTENT_ALIASES as _INPAINT_CONTENT_ALIASES,
    MASK_MODE_ALIASES as _MASK_MODE_ALIASES,
    RESIZE_MODE_ALIASES as _RESIZE_MODE_ALIASES,
    TEXT_ENCODER_LOCKED_PROFILES as _TEXT_ENCODER_LOCKED_PROFILES,
)
from rookieui.security.asset_guard import validate_asset_identifier
from rookieui.security.request_guard import (
    normalize_option_label,
    normalize_prompt_text,
    resolve_execution_seed,
    resolve_inventory_selector,
    validate_seed_range,
)
from rookieui.services.asset_store import resolve_asset_path, store_uploaded_image
from rookieui.services.coercion import (
    coerce_bool as _coerce_bool,
    coerce_float as _coerce_float,
    coerce_int as _coerce_int,
)
from rookieui.services.model_inventory import (
    discover_model_inventory,
    resolve_primary_model_selector_context,
    resolve_text_encoder_selector_context,
    resolve_vae_selector_context,
)
from rookieui.services.parity_matrix import (
    get_parity_profile,
    normalize_sampler_name,
    normalize_scheduler_name,
)
from rookieui.services.prompt_dsl import merge_lora_activations, preprocess_prompt_bundle
from rookieui.services.adetailer import normalize_adetailer_payload
from rookieui.services.controlnet import normalize_controlnet_units
from rookieui.services.txt2img import (
    _coerce_cfg_scale,
    _coerce_dimension,
    _coerce_dtype_profile,
    _coerce_hires_steps,
    _coerce_lora_selector,
    _coerce_lora_strength,
    _coerce_steps,
)

_MIN_DENOISE = 0.0
_MAX_DENOISE = 1.0
_MAX_BATCH_SIZE = 8
_MAX_BATCH_IMAGES = 64
_MIN_HIRES_SCALE = 1.0
_MAX_HIRES_SCALE = 2.5
_MIN_HIRES_DENOISE = 0.1
_MAX_HIRES_DENOISE = 1.0
_MAX_HIRES_STEPS = 150
_DEFAULT_HIRES_SCALE = 1.5
_DEFAULT_HIRES_DENOISE = 0.35
_DEFAULT_HIRES_UPSCALE_METHOD = "bislerp"

_IMG2IMG_MODE_ALIASES = {
    "img2img": "img2img",
    "sketch": "img2img",
    "inpaint": "inpaint",
    "inpaint_sketch": "inpaint",
    "inpaint_upload": "inpaint",
    "batch": "img2img",
}


def _is_unresolved_inventory_selector(value: str) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized in {"", "automatic", "__host_default__"}


def _normalize_choice(
    value: object,
    field_name: str,
    aliases: dict[str, str],
    default_value: str,
    applied_defaults: list[str],
) -> str:
    raw = normalize_option_label(value, field_name, max_length=64).lower()
    if not raw:
        applied_defaults.append(field_name)
        return default_value
    normalized = aliases.get(raw)
    if normalized is None:
        raise ValueError(f"{field_name} is unsupported.")
    return normalized


def _resolve_input_asset(
    *,
    asset_value: object,
    data_value: object,
    field_name: str,
    data_field_name: str,
    upload_prefix: str,
    required: bool,
) -> str:
    raw_asset = normalize_option_label(asset_value, field_name, max_length=80)
    if raw_asset:
        normalized_asset = validate_asset_identifier(raw_asset)
        resolve_asset_path(normalized_asset)
        return normalized_asset

    has_data = isinstance(data_value, str) and bool(data_value.strip())
    if has_data:
        # CRITICAL: img2img uploads must be converted to internal runtime handles; passing raw browser file paths/data to workflow nodes is unsafe and non-portable.
        return store_uploaded_image(data_value, prefix=upload_prefix).handle

    if required:
        raise ValueError(f"{field_name} or {data_field_name} is required.")
    return ""


def _coerce_batch_images(batch_images: object) -> list[str]:
    if batch_images in (None, ""):
        return []
    if not isinstance(batch_images, list):
        raise ValueError("batch_images must be an array of image data strings.")
    normalized: list[str] = []
    for index, entry in enumerate(batch_images):
        if index >= _MAX_BATCH_IMAGES:
            raise ValueError(f"batch_images must contain at most {_MAX_BATCH_IMAGES} entries.")
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError("batch_images entries must be non-empty strings.")
        normalized_entry = entry.strip()
        if not normalized_entry.startswith("data:image/"):
            raise ValueError("batch_images entries must be base64 image data URLs.")
        normalized.append(normalized_entry)
    return normalized


def normalize_img2img_request(payload: dict[str, object]) -> NormalizedImg2ImgRequest:
    if not isinstance(payload, dict):
        raise ValueError("Img2Img request payload must be an object.")

    request = Img2ImgRequest(**payload)
    prompt = normalize_prompt_text(request.prompt, "prompt", required=True)
    negative_prompt = normalize_prompt_text(request.negative_prompt, "negative_prompt")

    profile = get_parity_profile(normalize_option_label(request.profile, "profile", max_length=32))
    inventory = discover_model_inventory()
    inventory_is_host = inventory.source == "host"
    applied_defaults: list[str] = []
    dtype_profile = _coerce_dtype_profile(request.dtype_profile, applied_defaults)
    lora_name = _coerce_lora_selector(
        request.lora_name,
        inventory_selectors=inventory.loras,
        strict_match=inventory_is_host,
    )
    lora_strength_model = _coerce_lora_strength(request.lora_strength_model, "lora_strength_model")
    lora_strength_clip = _coerce_lora_strength(request.lora_strength_clip, "lora_strength_clip")
    steps = _coerce_steps(request.steps, profile.default_steps, applied_defaults)
    prompt_preprocess = preprocess_prompt_bundle(
        prompt,
        negative_prompt,
        step_count=steps,
        inventory_loras=inventory.loras,
        inventory_embeddings=inventory.embeddings,
        strict_match=inventory_is_host,
    )
    prompt = prompt_preprocess.cleaned_prompt
    negative_prompt = prompt_preprocess.cleaned_negative_prompt
    lora_activations = merge_lora_activations(
        prompt_preprocess.lora_activations,
        explicit_lora_name=lora_name,
        explicit_strength_model=lora_strength_model,
        explicit_strength_clip=lora_strength_clip,
    )

    mode = normalize_option_label(request.mode, "mode", max_length=24).lower() or "img2img"
    execution_mode = _IMG2IMG_MODE_ALIASES.get(mode)
    if execution_mode is None:
        raise ValueError("mode is unsupported.")
    batch_images = _coerce_batch_images(request.batch_images)
    batch_image_seed = batch_images[0] if mode == "batch" and batch_images else ""

    image_asset = _resolve_input_asset(
        asset_value=request.image_asset,
        # CRITICAL: batch mode currently executes through single graph translation; seed image must deterministically fall back to first uploaded batch entry.
        data_value=request.image_data or batch_image_seed,
        field_name="image_asset",
        data_field_name="image_data",
        upload_prefix="rookieui_img2img_input",
        required=True,
    )
    mask_asset = _resolve_input_asset(
        asset_value=request.mask_asset,
        data_value=request.mask_data,
        field_name="mask_asset",
        data_field_name="mask_data",
        upload_prefix="rookieui_inpaint_mask",
        required=execution_mode == "inpaint",
    )
    controlnet_units, controlnet_warning_codes, controlnet_warnings = normalize_controlnet_units(
        payload,
        inventory_models=inventory.controlnet,
        strict_model_match=inventory_is_host,
        fallback_image_asset=image_asset,
        fallback_image_data=request.image_data or batch_image_seed,
    )
    # IMPORTANT: keep ADetailer refinement intent on its own normalized block.
    # The main img2img request must stay reusable even when future detailer units add local ControlNet/inpaint overrides.
    adetailer = normalize_adetailer_payload(
        payload,
        profile_id=profile.id,
        surface="img2img",
        strict_inventory_match=inventory_is_host,
        primary_controlnet_unit_count=len([unit for unit in controlnet_units if unit.enabled]),
    )

    width = _coerce_dimension(
        request.width,
        profile.default_width,
        field_name="width",
        applied_defaults=applied_defaults,
    )
    height = _coerce_dimension(
        request.height,
        profile.default_height,
        field_name="height",
        applied_defaults=applied_defaults,
    )
    resize_mode = _normalize_choice(
        request.resize_mode,
        "resize_mode",
        _RESIZE_MODE_ALIASES,
        _DEFAULT_RESIZE_MODE,
        applied_defaults,
    )

    cfg_scale = _coerce_cfg_scale(request.cfg_scale, profile.default_cfg_scale, applied_defaults)

    sampler_input = normalize_option_label(request.sampler_name, "sampler_name")
    if not sampler_input:
        applied_defaults.append("sampler_name")
        sampler_input = profile.default_sampler
    sampler_name = normalize_sampler_name(sampler_input)

    scheduler_input = normalize_option_label(request.scheduler_name, "scheduler_name")
    scheduler_name = normalize_scheduler_name(
        sampler_input or profile.default_sampler,
        scheduler_input or None,
        default_scheduler=profile.default_scheduler,
    )
    if request.scheduler_name is None:
        applied_defaults.append("scheduler_name")

    clip_skip = request.clip_skip
    if clip_skip is None:
        applied_defaults.append("clip_skip")
        clip_skip = profile.default_clip_skip
    clip_skip = _coerce_int(clip_skip, "clip_skip")
    if clip_skip < 1 or clip_skip > 12:
        raise ValueError("clip_skip must be between 1 and 12.")
    if not profile.supports_clip_skip:
        clip_skip = 1

    # IMPORTANT: keep denoise coercion field-aware so invalid payloads report deterministic error surfaces across normalization paths.
    denoise_strength = round(_coerce_float(request.denoise_strength, "denoise_strength"), 3)
    if denoise_strength < _MIN_DENOISE or denoise_strength > _MAX_DENOISE:
        raise ValueError("denoise_strength must be between 0.0 and 1.0.")

    batch_size = _coerce_int(request.batch_size, "batch_size")
    if batch_size < 1 or batch_size > _MAX_BATCH_SIZE:
        raise ValueError(f"batch_size must be between 1 and {_MAX_BATCH_SIZE}.")

    grow_mask_by = _coerce_int(request.grow_mask_by, "grow_mask_by")
    if grow_mask_by < 0 or grow_mask_by > 64:
        raise ValueError("grow_mask_by must be between 0 and 64.")

    mask_blur = _coerce_int(request.mask_blur, "mask_blur")
    if mask_blur < 0 or mask_blur > 64:
        raise ValueError("mask_blur must be between 0 and 64.")

    inpaint_mask_mode = _normalize_choice(
        request.inpaint_mask_mode,
        "inpaint_mask_mode",
        _MASK_MODE_ALIASES,
        _DEFAULT_MASK_MODE,
        applied_defaults,
    )
    inpaint_masked_content = _normalize_choice(
        request.inpaint_masked_content,
        "inpaint_masked_content",
        _INPAINT_CONTENT_ALIASES,
        _DEFAULT_INPAINT_CONTENT,
        applied_defaults,
    )
    inpaint_area = _normalize_choice(
        request.inpaint_area,
        "inpaint_area",
        _INPAINT_AREA_ALIASES,
        _DEFAULT_INPAINT_AREA,
        applied_defaults,
    )
    inpaint_padding = _coerce_int(request.inpaint_padding, "inpaint_padding")
    if inpaint_padding < 0 or inpaint_padding > 256:
        raise ValueError("inpaint_padding must be between 0 and 256.")

    soft_inpainting_enabled = _coerce_bool(request.soft_inpainting_enabled, "soft_inpainting_enabled")
    soft_inpainting_schedule_bias = round(_coerce_float(request.soft_inpainting_schedule_bias, "soft_inpainting_schedule_bias"), 2)
    if soft_inpainting_schedule_bias < 0 or soft_inpainting_schedule_bias > 8:
        raise ValueError("soft_inpainting_schedule_bias must be between 0 and 8.")
    soft_inpainting_preservation_strength = round(
        _coerce_float(request.soft_inpainting_preservation_strength, "soft_inpainting_preservation_strength"), 2
    )
    if soft_inpainting_preservation_strength < 0 or soft_inpainting_preservation_strength > 8:
        raise ValueError("soft_inpainting_preservation_strength must be between 0 and 8.")
    soft_inpainting_transition_contrast_boost = round(
        _coerce_float(
            request.soft_inpainting_transition_contrast_boost,
            "soft_inpainting_transition_contrast_boost",
        ),
        2,
    )
    if soft_inpainting_transition_contrast_boost < 1 or soft_inpainting_transition_contrast_boost > 32:
        raise ValueError("soft_inpainting_transition_contrast_boost must be between 1 and 32.")
    soft_inpainting_mask_influence = round(_coerce_float(request.soft_inpainting_mask_influence, "soft_inpainting_mask_influence"), 2)
    if soft_inpainting_mask_influence < 0 or soft_inpainting_mask_influence > 1:
        raise ValueError("soft_inpainting_mask_influence must be between 0 and 1.")
    soft_inpainting_difference_threshold = round(
        _coerce_float(request.soft_inpainting_difference_threshold, "soft_inpainting_difference_threshold"),
        2,
    )
    if soft_inpainting_difference_threshold < 0 or soft_inpainting_difference_threshold > 8:
        raise ValueError("soft_inpainting_difference_threshold must be between 0 and 8.")
    soft_inpainting_difference_contrast = round(
        _coerce_float(request.soft_inpainting_difference_contrast, "soft_inpainting_difference_contrast"),
        2,
    )
    if soft_inpainting_difference_contrast < 0 or soft_inpainting_difference_contrast > 8:
        raise ValueError("soft_inpainting_difference_contrast must be between 0 and 8.")

    hires_enabled = _coerce_bool(request.hires_enabled, "hires_enabled")
    default_hires_steps = max(10, min(_MAX_HIRES_STEPS, round(steps * 0.5)))
    if hires_enabled:
        # CRITICAL: img2img hires validation must be gated behind hires_enabled; disabled hires controls must not block base img2img/inpaint requests.
        hires_scale = round(_coerce_float(request.hires_scale, "hires_scale"), 2)
        if hires_scale < _MIN_HIRES_SCALE or hires_scale > _MAX_HIRES_SCALE:
            raise ValueError(f"hires_scale must be between {_MIN_HIRES_SCALE} and {_MAX_HIRES_SCALE}.")
        hires_steps = _coerce_hires_steps(request.hires_steps, default_hires_steps, applied_defaults)
        hires_denoise = round(_coerce_float(request.hires_denoise, "hires_denoise"), 2)
        if hires_denoise < _MIN_HIRES_DENOISE or hires_denoise > _MAX_HIRES_DENOISE:
            raise ValueError(
                f"hires_denoise must be between {_MIN_HIRES_DENOISE} and {_MAX_HIRES_DENOISE}."
            )
        hires_upscale_method = normalize_option_label(
            request.hires_upscale_method,
            "hires_upscale_method",
            max_length=32,
        ) or _DEFAULT_HIRES_UPSCALE_METHOD
        if hires_upscale_method not in _HIRES_UPSCALE_METHODS:
            raise ValueError("hires_upscale_method is unsupported.")
    else:
        hires_scale = _DEFAULT_HIRES_SCALE
        hires_steps = default_hires_steps
        hires_denoise = _DEFAULT_HIRES_DENOISE
        hires_upscale_method = _DEFAULT_HIRES_UPSCALE_METHOD

    primary_model_category, primary_model_selectors, primary_model_default = resolve_primary_model_selector_context(
        profile.id, inventory
    )
    # CRITICAL: live img2img payloads inherit the same unresolved selector sentinels as txt2img;
    # strict host inventory matching must see canonical defaults, not placeholder strings.
    raw_checkpoint_selector = "" if _is_unresolved_inventory_selector(request.checkpoint_name) else request.checkpoint_name
    raw_vae_selector = "" if _is_unresolved_inventory_selector(request.vae_name) else request.vae_name
    raw_text_encoder_selector = (
        "" if _is_unresolved_inventory_selector(request.text_encoder_name) else request.text_encoder_name
    )
    checkpoint_name = resolve_inventory_selector(
        raw_checkpoint_selector,
        "checkpoint_name",
        default_value=primary_model_default,
        inventory_selectors=primary_model_selectors,
        strict_match=inventory_is_host,
    )
    vae_name = resolve_inventory_selector(
        raw_vae_selector,
        "vae_name",
        # CRITICAL: decode quality in img2img/inpaint depends on a profile-compatible VAE;
        # using a global default can yield normal sampler preview but broken final output.
        default_value=resolve_vae_selector_context(profile.id, inventory),
        inventory_selectors=inventory.vae,
        strict_match=inventory_is_host,
    )
    text_encoder_name = resolve_inventory_selector(
        raw_text_encoder_selector,
        "text_encoder_name",
        # IMPORTANT: keep diffusion-model profile defaults aligned to a compatible text encoder on normalization fallback.
        default_value=resolve_text_encoder_selector_context(profile.id, inventory),
        inventory_selectors=inventory.text_encoders,
        strict_match=inventory_is_host,
    )
    if profile.id in _TEXT_ENCODER_LOCKED_PROFILES:
        # IMPORTANT: SD1.5 and SDXL img2img/inpaint should not depend on a separate text-encoder selector in the RookieUI surface.
        text_encoder_name = ""
    if primary_model_category == "diffusion_models":
        # CRITICAL: diffusion families do not support global text encoder/VAE defaults; unresolved/Automatic selectors must fail fast instead of producing mismatched decode artifacts.
        if _is_unresolved_inventory_selector(text_encoder_name):
            raise ValueError(
                f"text_encoder_name requires a family-specific host selector for profile '{profile.id}'."
            )
        if _is_unresolved_inventory_selector(vae_name):
            raise ValueError(
                f"vae_name requires a family-specific host selector for profile '{profile.id}'."
            )

    seed = validate_seed_range(_coerce_int(request.seed, "seed"))
    execution_seed = resolve_execution_seed(seed)
    seed_extra = _coerce_bool(request.seed_extra, "seed_extra")

    return NormalizedImg2ImgRequest(
        prompt=prompt,
        negative_prompt=negative_prompt,
        profile=profile.id,
        base_family=profile.base_family,
        primary_model_category=primary_model_category,
        prompt_encoder=profile.prompt_encoder,
        dtype_profile=dtype_profile,
        lora_name=lora_name,
        lora_strength_model=lora_strength_model,
        lora_strength_clip=lora_strength_clip,
        checkpoint_name=checkpoint_name,
        vae_name=vae_name,
        text_encoder_name=text_encoder_name,
        image_asset=image_asset,
        mask_asset=mask_asset,
        mode=mode,
        execution_mode=execution_mode,
        batch_images=batch_images,
        width=width,
        height=height,
        resize_mode=resize_mode,
        steps=steps,
        cfg_scale=cfg_scale,
        sampler_name=sampler_name,
        scheduler_name=scheduler_name,
        seed=seed,
        execution_seed=execution_seed,
        seed_extra=seed_extra,
        batch_size=batch_size,
        clip_skip=clip_skip,
        denoise_strength=denoise_strength,
        grow_mask_by=grow_mask_by,
        mask_blur=mask_blur,
        inpaint_mask_mode=inpaint_mask_mode,
        inpaint_masked_content=inpaint_masked_content,
        inpaint_area=inpaint_area,
        inpaint_padding=inpaint_padding,
        soft_inpainting_enabled=soft_inpainting_enabled,
        soft_inpainting_schedule_bias=soft_inpainting_schedule_bias,
        soft_inpainting_preservation_strength=soft_inpainting_preservation_strength,
        soft_inpainting_transition_contrast_boost=soft_inpainting_transition_contrast_boost,
        soft_inpainting_mask_influence=soft_inpainting_mask_influence,
        soft_inpainting_difference_threshold=soft_inpainting_difference_threshold,
        soft_inpainting_difference_contrast=soft_inpainting_difference_contrast,
        hires_enabled=hires_enabled,
        hires_scale=hires_scale,
        hires_steps=hires_steps,
        hires_denoise=hires_denoise,
        hires_upscale_method=hires_upscale_method,
        adetailer=adetailer,
        lora_activations=lora_activations,
        prompt_warnings=prompt_preprocess.prompt_warnings,
        prompt_warning_codes=prompt_preprocess.warning_codes,
        controlnet_units=controlnet_units,
        controlnet_warnings=controlnet_warnings,
        controlnet_warning_codes=controlnet_warning_codes,
        prompt_semantics=prompt_preprocess.prompt_semantics.to_payload(),
        negative_prompt_semantics=prompt_preprocess.negative_prompt_semantics.to_payload(),
        applied_defaults=applied_defaults,
    )
