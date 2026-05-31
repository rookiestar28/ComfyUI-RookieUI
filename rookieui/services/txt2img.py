from __future__ import annotations

from rookieui.contracts.generation import NormalizedTxt2ImgRequest, Txt2ImgRequest
from rookieui.contracts.model_family_registry import get_model_family_registry_entry
from rookieui.contracts.aliases import (
    HIRES_UPSCALE_METHODS as _HIRES_UPSCALE_METHODS,
    TEXT_ENCODER_LOCKED_PROFILES as _TEXT_ENCODER_LOCKED_PROFILES,
)
from rookieui.security.request_guard import (
    normalize_option_label,
    normalize_prompt_text,
    resolve_execution_seed,
    resolve_inventory_selector,
    validate_seed_range,
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
from rookieui.services.coercion import (
    coerce_bool as _coerce_bool,
    coerce_float as _coerce_float,
    coerce_int as _coerce_int,
)
from rookieui.services.prompt_dsl import (
    collect_model_only_lora_drift_warnings,
    merge_lora_activations,
    preprocess_prompt_bundle,
)
from rookieui.services.adetailer import normalize_adetailer_payload
from rookieui.services.controlnet import normalize_controlnet_units

_MIN_DIMENSION = 64
_MAX_DIMENSION = 2048
_DIMENSION_STEP = 8
_MIN_STEPS = 1
_MAX_STEPS = 150
_MIN_CFG = 1.0
_MAX_CFG = 30.0
_MAX_BATCH_SIZE = 8
_MAX_BATCH_COUNT = 32
_MIN_LORA_STRENGTH = -4.0
_MAX_LORA_STRENGTH = 4.0
_MIN_HIRES_SCALE = 1.0
_MAX_HIRES_SCALE = 2.5
_MIN_HIRES_DENOISE = 0.1
_MAX_HIRES_DENOISE = 1.0
_DEFAULT_HIRES_SCALE = 1.5
_DEFAULT_HIRES_DENOISE = 0.35
_DEFAULT_HIRES_UPSCALE_METHOD = "bislerp"
_DEFAULT_DTYPE_PROFILE = "automatic"
_MIN_SHIFT = 0.0
_MAX_SHIFT = 20.0
_MIN_FLUX_GUIDANCE = 0.0
_MAX_FLUX_GUIDANCE = 20.0
_MIN_EDIT_MEGAPIXELS = 0.25
_MAX_EDIT_MEGAPIXELS = 8.0
_DTYPE_PROFILE_ALIASES = {
    "automatic": {"automatic"},
    "automatic_fp16_lora": {"automatic_fp16_lora", "automatic (fp16 lora)", "automatic fp16 lora"},
    "nf4": {"nf4"},
    "fp4": {"fp4"},
    "float8_e4m3fn": {"float8_e4m3fn", "float8-e4m3fn"},
    "float8_e5m2": {"float8_e5m2", "float8-e5m2"},
}


def _is_unresolved_inventory_selector(value: str) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized in {"", "automatic", "__host_default__"}


def _coerce_dimension(
    value: int | None,
    default_value: int,
    *,
    field_name: str,
    applied_defaults: list[str],
) -> int:
    if value is None:
        applied_defaults.append(field_name)
        value = default_value

    normalized = _coerce_int(value, field_name)
    if normalized < _MIN_DIMENSION or normalized > _MAX_DIMENSION:
        raise ValueError(f"{field_name} must be between {_MIN_DIMENSION} and {_MAX_DIMENSION}.")
    if normalized % _DIMENSION_STEP != 0:
        raise ValueError(f"{field_name} must be divisible by {_DIMENSION_STEP}.")
    return normalized


def _coerce_steps(value: int | None, default_value: int, applied_defaults: list[str]) -> int:
    if value is None:
        applied_defaults.append("steps")
        value = default_value

    normalized = _coerce_int(value, "steps")
    if normalized < _MIN_STEPS or normalized > _MAX_STEPS:
        raise ValueError(f"steps must be between {_MIN_STEPS} and {_MAX_STEPS}.")
    return normalized


def _coerce_cfg_scale(
    value: float | None,
    default_value: float,
    applied_defaults: list[str],
) -> float:
    if value is None:
        applied_defaults.append("cfg_scale")
        value = default_value

    normalized = round(_coerce_float(value, "cfg_scale"), 2)
    if normalized < _MIN_CFG or normalized > _MAX_CFG:
        raise ValueError(f"cfg_scale must be between {_MIN_CFG} and {_MAX_CFG}.")
    return normalized


def _coerce_optional_profile_float(
    value: float | None,
    default_value: float | None,
    applied_defaults: list[str],
    *,
    field_name: str,
    minimum: float,
    maximum: float,
) -> float | None:
    if default_value is None and (value is None or value == ""):
        return None
    if value is None or value == "":
        applied_defaults.append(field_name)
        value = default_value
    if value is None:
        return None
    normalized = round(_coerce_float(value, field_name), 3)
    if normalized < minimum or normalized > maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}.")
    return normalized


def _coerce_hires_steps(
    value: int | None,
    default_value: int,
    applied_defaults: list[str],
) -> int:
    if value is None:
        applied_defaults.append("hires_steps")
        value = default_value
    normalized = _coerce_int(value, "hires_steps")
    # IMPORTANT: A1111 treats hires_steps=0 as "reuse the original step count"; XYZ parity
    # and shared txt2img/img2img normalization must preserve that sentinel instead of rejecting it.
    if normalized < 0 or normalized > _MAX_STEPS:
        raise ValueError(f"hires_steps must be between 0 and {_MAX_STEPS}.")
    return normalized


def _coerce_dtype_profile(value: str | None, applied_defaults: list[str]) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        applied_defaults.append("dtype_profile")
        return _DEFAULT_DTYPE_PROFILE

    normalized = normalize_option_label(value, "dtype_profile", max_length=48).lower().replace("-", "_")
    for profile_id, aliases in _DTYPE_PROFILE_ALIASES.items():
        if normalized == profile_id or normalized in {alias.replace("-", "_") for alias in aliases}:
            return profile_id

    raise ValueError("dtype_profile is unsupported.")


def _coerce_prompt_enhancement_enabled(
    value: object,
    default_value: bool,
    applied_defaults: list[str],
) -> bool:
    if value is None or value == "":
        applied_defaults.append("prompt_enhancement_enabled")
        return default_value
    return _coerce_bool(value, "prompt_enhancement_enabled")


def _resolve_diffusion_text_encoder_selector(
    raw_value: str,
    *,
    inventory_selectors: list[str],
    default_value: str,
    strict_match: bool,
) -> str:
    composite_value = str(raw_value or "").strip() or str(default_value or "").strip()
    if not composite_value:
        return ""
    selectors = [token.strip() for token in composite_value.split("|") if token.strip()]
    if not selectors:
        return ""
    resolved = [
        resolve_inventory_selector(
            selector,
            "text_encoder_name",
            default_value="",
            inventory_selectors=inventory_selectors,
            strict_match=strict_match,
        )
        for selector in selectors
    ]
    # CRITICAL: preserve ordered composite encoder bundles for official template-backed non-SD profiles;
    # collapsing them back to one selector breaks Flux dual-encoder and HiDream quadruple-encoder loader topology.
    return "|".join(resolved)


def _coerce_lora_selector(
    value: str | None,
    *,
    inventory_selectors: list[str] | None = None,
    strict_match: bool = False,
) -> str:
    return resolve_inventory_selector(
        value,
        "lora_name",
        default_value="",
        inventory_selectors=inventory_selectors,
        strict_match=strict_match,
    )


def _resolve_template_lora_selector(
    raw_value: str | None,
    *,
    profile_id: str,
    inventory_selectors: list[str] | None,
    strict_match: bool,
) -> str:
    normalized_value = str(raw_value or "").strip()
    if normalized_value:
        return resolve_inventory_selector(
            normalized_value,
            "template_lora_name",
            default_value="",
            inventory_selectors=inventory_selectors,
            strict_match=strict_match,
        )
    return ""


def _coerce_lora_strength(value: object, field_name: str) -> float:
    normalized = round(_coerce_float(value, field_name), 2)
    if normalized < _MIN_LORA_STRENGTH or normalized > _MAX_LORA_STRENGTH:
        raise ValueError(
            f"{field_name} must be between {_MIN_LORA_STRENGTH} and {_MAX_LORA_STRENGTH}."
        )
    return normalized


def normalize_txt2img_request(payload: dict[str, object]) -> NormalizedTxt2ImgRequest:
    if not isinstance(payload, dict):
        raise ValueError("Txt2Img request payload must be an object.")

    request = Txt2ImgRequest(**payload)
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
    cfg_scale = _coerce_cfg_scale(
        request.cfg_scale,
        profile.default_cfg_scale,
        applied_defaults,
    )
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
    # CRITICAL: txt2img receives the same frontend preset payload shape as non-SD edit flows.
    # Keep this field contract-visible so hidden/empty controls do not crash before validation.
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

    batch_size = _coerce_int(request.batch_size, "batch_size")
    batch_count = _coerce_int(request.batch_count, "batch_count")
    if batch_size < 1 or batch_size > _MAX_BATCH_SIZE:
        raise ValueError(f"batch_size must be between 1 and {_MAX_BATCH_SIZE}.")
    if batch_count < 1 or batch_count > _MAX_BATCH_COUNT:
        raise ValueError(f"batch_count must be between 1 and {_MAX_BATCH_COUNT}.")

    clip_skip = request.clip_skip
    if clip_skip is None:
        applied_defaults.append("clip_skip")
        clip_skip = profile.default_clip_skip
    clip_skip = _coerce_int(clip_skip, "clip_skip")
    if clip_skip < 1 or clip_skip > 12:
        raise ValueError("clip_skip must be between 1 and 12.")
    if not profile.supports_clip_skip:
        clip_skip = 1

    primary_model_category, primary_model_selectors, primary_model_default = resolve_primary_model_selector_context(
        profile.id, inventory
    )
    # CRITICAL: Z-Image ControlNet files are ComfyUI model patches; routing them through generic controlnet
    # inventory makes strict host validation reject the official Turbo graph before translation.
    controlnet_inventory_models = (
        inventory.model_patches
        if profile.id == "z_image_turbo" and primary_model_category == "diffusion_models"
        else inventory.controlnet
    )
    controlnet_units, controlnet_warning_codes, controlnet_warnings = normalize_controlnet_units(
        payload,
        inventory_models=controlnet_inventory_models,
        strict_model_match=inventory_is_host,
    )
    # IMPORTANT: keep ADetailer normalization detached from main ControlNet ownership here.
    # Later refinement runtime work depends on this seam so per-unit overrides do not pollute base generation units.
    adetailer = normalize_adetailer_payload(
        payload,
        profile_id=profile.id,
        surface="txt2img",
        strict_inventory_match=inventory_is_host,
        primary_controlnet_unit_count=len([unit for unit in controlnet_units if unit.enabled]),
    )

    # CRITICAL: host-backed defaults arrive as sentinel strings from request/dataclass/UI contracts;
    # convert them back to unresolved state before strict host matching or bare generate requests fail early.
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
        # CRITICAL: diffusion-model families need profile-aware VAE fallback;
        # a mismatched global VAE often only surfaces as corrupted final decode output.
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
        # IMPORTANT: use profile-aware default so diffusion-model presets do not inherit a mismatched global text encoder.
        default_value=text_encoder_default,
        inventory_selectors=inventory.text_encoders,
        strict_match=inventory_is_host,
    )
    if profile.id in _TEXT_ENCODER_LOCKED_PROFILES:
        # IMPORTANT: SD1.5 and SDXL use model-native text encoders in A1111-style flow; keep standalone selector disabled to prevent decorative mismatches.
        text_encoder_name = ""
    if primary_model_category == "diffusion_models":
        text_encoder_name = _resolve_diffusion_text_encoder_selector(
            raw_text_encoder_selector,
            inventory_selectors=inventory.text_encoders,
            default_value=text_encoder_default,
            strict_match=inventory_is_host,
        )
        # CRITICAL: diffusion families do not support global text encoder/VAE defaults; unresolved/Automatic selectors must fail fast instead of silently degrading final decode quality.
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
    hires_enabled = _coerce_bool(request.hires_enabled, "hires_enabled")
    default_hires_steps = max(10, min(_MAX_STEPS, round(steps * 0.5)))
    if hires_enabled:
        # CRITICAL: disabled hires controls must never block base txt2img requests.
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

    prompt_warnings = list(prompt_preprocess.prompt_warnings)
    prompt_warning_codes = list(prompt_preprocess.warning_codes)
    if missing_template_lora_warning:
        prompt_warnings.append(missing_template_lora_warning)
        prompt_warning_codes.append("TEMPLATE_LORA_MISSING")
    if primary_model_category == "diffusion_models" and lora_activations:
        model_only_warnings, model_only_warning_codes = collect_model_only_lora_drift_warnings(lora_activations)
        prompt_warnings.extend(model_only_warnings)
        prompt_warning_codes.extend(model_only_warning_codes)

    return NormalizedTxt2ImgRequest(
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
        width=width,
        height=height,
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
        batch_count=batch_count,
        clip_skip=clip_skip,
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
