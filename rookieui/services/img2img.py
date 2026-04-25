from __future__ import annotations

from rookieui.contracts.generation import Img2ImgRequest, NormalizedImg2ImgRequest
from rookieui.contracts.family_template_manifest import list_non_sd_edit_manifest_entries
from rookieui.contracts.model_family_registry import (
    get_model_family_registry_entry,
    model_family_supports_surface_flow,
)
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
    resolve_aux_text_encoder_selector_context,
    resolve_primary_model_selector_context,
    resolve_template_lora_selector_context,
    resolve_text_encoder_selector_context,
    resolve_vae_selector_context,
)
from rookieui.services.parity_matrix import (
    get_parity_profile,
    normalize_sampler_name,
    normalize_scheduler_name,
)
from rookieui.services.prompt_dsl import (
    collect_model_only_lora_drift_warnings,
    merge_lora_activations,
    preprocess_prompt_bundle,
)
from rookieui.services.adetailer import normalize_adetailer_payload
from rookieui.services.controlnet import normalize_controlnet_units
from rookieui.services.txt2img import (
    _coerce_cfg_scale,
    _coerce_dimension,
    _coerce_dtype_profile,
    _coerce_hires_steps,
    _coerce_lora_selector,
    _coerce_lora_strength,
    _coerce_optional_profile_float,
    _coerce_prompt_enhancement_enabled,
    _coerce_steps,
    _resolve_diffusion_text_encoder_selector,
    _resolve_template_lora_selector,
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
_MAX_REFERENCE_IMAGES = 16
_DEFAULT_HIRES_SCALE = 1.5
_DEFAULT_HIRES_DENOISE = 0.35
_DEFAULT_HIRES_UPSCALE_METHOD = "bislerp"
_MIN_SHIFT = 0.0
_MAX_SHIFT = 20.0
_MIN_FLUX_GUIDANCE = 0.0
_MAX_FLUX_GUIDANCE = 20.0
_MIN_EDIT_MEGAPIXELS = 0.25
_MAX_EDIT_MEGAPIXELS = 8.0

_IMG2IMG_MODE_ALIASES = {
    "img2img": "img2img",
    "edit": "edit",
    "sketch": "img2img",
    "inpaint": "inpaint",
    "inpaint_sketch": "inpaint",
    "inpaint_upload": "inpaint",
    "batch": "img2img",
}
_OFFICIAL_IMAGE_EDIT_PROFILES = frozenset(entry.id for entry in list_non_sd_edit_manifest_entries())


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


def _is_official_image_edit_profile(profile_id: str) -> bool:
    return str(profile_id or "").strip().lower() in _OFFICIAL_IMAGE_EDIT_PROFILES


def _enforce_image_edit_reference_contract(profile_entry: object, reference_image_assets: list[str]) -> None:
    max_direct_references = int(getattr(profile_entry, "max_direct_references", 0) or 0)
    if max_direct_references <= 0:
        return
    if len(reference_image_assets) <= max_direct_references:
        return
    image_label = "image" if max_direct_references == 1 else "images"
    raise ValueError(
        f"profile '{getattr(profile_entry, 'id', '')}' supports at most {max_direct_references} direct reference {image_label}."
    )


def _coerce_reference_image_assets(
    *,
    reference_images: object,
    legacy_image_asset: object,
    legacy_image_data: object,
) -> list[str]:
    if reference_images in (None, "") or reference_images == []:
        return [
            _resolve_input_asset(
                asset_value=legacy_image_asset,
                data_value=legacy_image_data,
                field_name="image_asset",
                data_field_name="image_data",
                upload_prefix="rookieui_img2img_input",
                required=True,
            )
        ]
    if not isinstance(reference_images, list):
        raise ValueError("reference_images must be an array of objects.")

    normalized_assets: list[str] = []
    for index, entry in enumerate(reference_images):
        if index >= _MAX_REFERENCE_IMAGES:
            raise ValueError(f"reference_images must contain at most {_MAX_REFERENCE_IMAGES} entries.")
        if not isinstance(entry, dict):
            raise ValueError("reference_images entries must be objects.")
        normalized_assets.append(
            _resolve_input_asset(
                asset_value=entry.get("image_asset"),
                data_value=entry.get("image_data"),
                field_name=f"reference_images[{index}].image_asset",
                data_field_name=f"reference_images[{index}].image_data",
                upload_prefix=f"rookieui_img2img_reference_{index + 1}",
                required=True,
            )
        )
    if not normalized_assets:
        raise ValueError("reference_images must contain at least one entry.")
    return normalized_assets


def normalize_img2img_request(payload: dict[str, object]) -> NormalizedImg2ImgRequest:
    if not isinstance(payload, dict):
        raise ValueError("Img2Img request payload must be an object.")

    request = Img2ImgRequest(**payload)
    prompt = normalize_prompt_text(request.prompt, "prompt", required=True)
    negative_prompt = normalize_prompt_text(request.negative_prompt, "negative_prompt")

    profile = get_parity_profile(normalize_option_label(request.profile, "profile", max_length=32))
    profile_entry = get_model_family_registry_entry(profile.id)
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

    requested_mode = normalize_option_label(request.mode, "mode", max_length=24).lower() or "img2img"
    execution_mode = _IMG2IMG_MODE_ALIASES.get(requested_mode)
    if execution_mode is None:
        raise ValueError("mode is unsupported.")
    is_image_edit_profile = _is_official_image_edit_profile(profile.id)
    if execution_mode == "edit" and not is_image_edit_profile:
        raise ValueError("mode 'edit' is reserved for official image-edit profiles.")
    if is_image_edit_profile:
        if requested_mode in {"inpaint", "inpaint_sketch", "inpaint_upload", "sketch", "batch"}:
            raise ValueError(f"mode '{requested_mode}' is unsupported for official image-edit profiles.")
        # IMPORTANT: image-edit profiles now belong to the canonical img2img contract even while the runtime
        # seam still routes through the existing dedicated edit builder during the transition chain.
        mode = "img2img"
        execution_mode = "edit"
        requested_surface_flow = "img2img"
    else:
        mode = requested_mode
        requested_surface_flow = "img2img" if execution_mode != "edit" else "edit"
    if not (is_image_edit_profile and requested_surface_flow == "img2img") and not model_family_supports_surface_flow(
        profile.id,
        requested_surface_flow,
    ):
        raise ValueError(f"profile '{profile.id}' is not currently exposed on the {requested_surface_flow} surface.")
    batch_images = _coerce_batch_images(request.batch_images)
    batch_image_seed = batch_images[0] if mode == "batch" and batch_images else ""

    reference_image_assets = _coerce_reference_image_assets(
        reference_images=request.reference_images,
        legacy_image_asset=request.image_asset,
        # CRITICAL: batch mode currently executes through single graph translation; seed image must deterministically fall back to first uploaded batch entry.
        legacy_image_data=request.image_data or batch_image_seed,
    )
    if is_image_edit_profile:
        _enforce_image_edit_reference_contract(profile_entry, reference_image_assets)
    main_reference_index = _coerce_int(request.main_reference_index, "main_reference_index")
    if main_reference_index < 0 or main_reference_index >= len(reference_image_assets):
        raise ValueError("main_reference_index is out of range for reference_images.")
    image_asset = reference_image_assets[main_reference_index]
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
    shift = _coerce_optional_profile_float(
        request.shift,
        profile_entry.default_shift,
        applied_defaults,
        field_name="shift",
        minimum=_MIN_SHIFT,
        maximum=_MAX_SHIFT,
    )
    flux_guidance = _coerce_optional_profile_float(
        request.flux_guidance,
        profile_entry.default_flux_guidance,
        applied_defaults,
        field_name="flux_guidance",
        minimum=_MIN_FLUX_GUIDANCE,
        maximum=_MAX_FLUX_GUIDANCE,
    )
    edit_megapixels = _coerce_optional_profile_float(
        request.edit_megapixels,
        profile_entry.default_edit_megapixels,
        applied_defaults,
        field_name="edit_megapixels",
        minimum=_MIN_EDIT_MEGAPIXELS,
        maximum=_MAX_EDIT_MEGAPIXELS,
    )

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
        if hires_steps == 0:
            hires_steps = steps
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
    text_encoder_default = resolve_text_encoder_selector_context(profile.id, inventory)
    aux_text_encoder_name = resolve_aux_text_encoder_selector_context(profile.id, inventory)
    template_lora_name = _resolve_template_lora_selector(
        request.template_lora_name,
        profile_id=profile.id,
        inventory_selectors=inventory.loras,
        strict_match=inventory_is_host,
    ) or resolve_template_lora_selector_context(profile.id, inventory)
    text_encoder_name = resolve_inventory_selector(
        raw_text_encoder_selector,
        "text_encoder_name",
        # IMPORTANT: keep diffusion-model profile defaults aligned to a compatible text encoder on normalization fallback.
        default_value=text_encoder_default,
        inventory_selectors=inventory.text_encoders,
        strict_match=inventory_is_host,
    )
    if profile.id in _TEXT_ENCODER_LOCKED_PROFILES:
        # IMPORTANT: SD1.5 and SDXL img2img/inpaint should not depend on a separate text-encoder selector in the RookieUI surface.
        text_encoder_name = ""
    if primary_model_category == "diffusion_models":
        text_encoder_name = _resolve_diffusion_text_encoder_selector(
            raw_text_encoder_selector,
            inventory_selectors=inventory.text_encoders,
            default_value=text_encoder_default,
            strict_match=inventory_is_host,
        )
        # CRITICAL: diffusion families do not support global text encoder/VAE defaults; unresolved/Automatic selectors must fail fast instead of producing mismatched decode artifacts.
        if _is_unresolved_inventory_selector(text_encoder_name):
            raise ValueError(
                f"text_encoder_name requires a family-specific host selector for profile '{profile.id}'."
            )
        if _is_unresolved_inventory_selector(vae_name):
            raise ValueError(
                f"vae_name requires a family-specific host selector for profile '{profile.id}'."
            )
        if profile.id in {"ernie_image", "ernie_image_turbo"} and not aux_text_encoder_name:
            raise ValueError(
                f"aux_text_encoder_name requires a family-specific host selector for profile '{profile.id}'."
            )
    missing_template_lora_warning = ""
    if (
        primary_model_category == "diffusion_models"
        and profile_entry.template_lora_visible
        and profile_entry.official_template_lora_label
        and not template_lora_name
    ):
        # DEBUG HOTSPOT: missing official template LoRA is a parity warning, not a generation blocker.
        missing_template_lora_warning = (
            f"Official {profile_entry.title} template LoRA "
            f"'{profile_entry.official_template_lora_label}' is missing from host inventory; "
            "generation will continue without template-owned LoRA parity. "
            "To add a LoRA manually in RookieUI, use <lora:model_name:1> in the prompt."
        )

    seed = validate_seed_range(_coerce_int(request.seed, "seed"))
    execution_seed = resolve_execution_seed(seed)
    seed_extra = _coerce_bool(request.seed_extra, "seed_extra")
    prompt_enhancement_enabled = _coerce_prompt_enhancement_enabled(
        request.prompt_enhancement_enabled,
        profile_entry.default_prompt_enhancement_enabled,
        applied_defaults,
    )

    prompt_warnings = list(prompt_preprocess.prompt_warnings)
    prompt_warning_codes = list(prompt_preprocess.warning_codes)
    if missing_template_lora_warning:
        prompt_warnings.append(missing_template_lora_warning)
        prompt_warning_codes.append("TEMPLATE_LORA_MISSING")
    if primary_model_category == "diffusion_models" and lora_activations:
        model_only_warnings, model_only_warning_codes = collect_model_only_lora_drift_warnings(lora_activations)
        prompt_warnings.extend(model_only_warnings)
        prompt_warning_codes.extend(model_only_warning_codes)

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
        aux_text_encoder_name=aux_text_encoder_name,
        template_lora_name=template_lora_name,
        image_asset=image_asset,
        reference_image_assets=reference_image_assets,
        main_reference_index=main_reference_index,
        mask_asset=mask_asset,
        mode=mode,
        execution_mode=execution_mode,
        batch_images=batch_images,
        width=width,
        height=height,
        resize_mode=resize_mode,
        steps=steps,
        cfg_scale=cfg_scale,
        shift=shift,
        flux_guidance=flux_guidance,
        edit_megapixels=edit_megapixels,
        sampler_name=sampler_name,
        scheduler_name=scheduler_name,
        prompt_enhancement_enabled=prompt_enhancement_enabled,
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
        prompt_warnings=list(dict.fromkeys(prompt_warnings)),
        prompt_warning_codes=list(dict.fromkeys(prompt_warning_codes)),
        controlnet_units=controlnet_units,
        controlnet_warnings=controlnet_warnings,
        controlnet_warning_codes=controlnet_warning_codes,
        prompt_semantics=prompt_preprocess.prompt_semantics.to_payload(),
        negative_prompt_semantics=prompt_preprocess.negative_prompt_semantics.to_payload(),
        applied_defaults=applied_defaults,
    )
