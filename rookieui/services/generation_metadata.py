from __future__ import annotations

from typing import Any, Mapping

from rookieui.security.request_guard import MAX_INFOTEXT_LENGTH, normalize_prompt_text

_SAMPLER_DISPLAY_NAMES = {
    "euler_ancestral": "Euler a",
    "euler": "Euler",
    "dpmpp_2m": "DPM++ 2M",
    "dpmpp_2m_sde": "DPM++ 2M SDE",
    "dpmpp_sde": "DPM++ SDE",
    "ddim": "DDIM",
    "uni_pc": "UniPC",
    "uni_pc_bh2": "UniPC BH2",
}

_SCHEDULER_DISPLAY_NAMES = {
    "normal": "Automatic",
    "karras": "Karras",
    "exponential": "Exponential",
    "sgm_uniform": "SGM Uniform",
    "simple": "Simple",
    "ddim_uniform": "DDIM Uniform",
    "beta": "Beta",
    "linear_quadratic": "Linear Quadratic",
    "kl_optimal": "KL Optimal",
}

_SELECTOR_DEFAULTS = {"", "automatic", "__host_default__"}


def _clean_text(value: object) -> str:
    return str(value or "").replace("\x00", "").strip()


def _format_number(value: object) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return _clean_text(value)


def _format_bool(value: object) -> str:
    return "True" if bool(value) else "False"


def _format_sampler(value: object) -> str:
    normalized = _clean_text(value).lower()
    return _SAMPLER_DISPLAY_NAMES.get(normalized, _clean_text(value))


def _format_scheduler(value: object) -> str:
    normalized = _clean_text(value).lower()
    return _SCHEDULER_DISPLAY_NAMES.get(normalized, _clean_text(value))


def _append_field(fields: list[tuple[str, str]], key: str, value: object, *, skip_empty: bool = True) -> None:
    text = _format_number(value)
    if skip_empty and not text:
        return
    fields.append((key, text))


def _append_selector_field(fields: list[tuple[str, str]], key: str, value: object) -> None:
    text = _clean_text(value)
    if text.lower() in _SELECTOR_DEFAULTS:
        return
    fields.append((key, text))


def _infer_surface(normalized_request: Mapping[str, Any]) -> str:
    execution_mode = _clean_text(normalized_request.get("execution_mode")).lower()
    mode = _clean_text(normalized_request.get("mode")).lower()
    if execution_mode or mode in {"img2img", "inpaint", "sketch", "inpaint_upload", "batch", "edit"}:
        return "img2img"
    return "txt2img"


def build_a1111_parameters(normalized_request: Mapping[str, Any]) -> str:
    """Build raw A1111-style infotext for generated PNG `parameters` chunks."""

    prompt = normalize_prompt_text(normalized_request.get("prompt", ""), "prompt")
    negative_prompt_mode = _clean_text(normalized_request.get("negative_prompt_mode") or "encoded").lower()
    negative_prompt = ""
    if negative_prompt_mode == "encoded":
        negative_prompt = normalize_prompt_text(
            normalized_request.get("negative_prompt", ""),
            "negative_prompt",
        )
    fields: list[tuple[str, str]] = []
    _append_field(fields, "Steps", normalized_request.get("steps"))
    sampler_name = _format_sampler(normalized_request.get("sampler_name"))
    if sampler_name:
        fields.append(("Sampler", sampler_name))
    scheduler_control_mode = _clean_text(normalized_request.get("scheduler_control_mode") or "generic").lower()
    if scheduler_control_mode == "generic":
        scheduler_name = _format_scheduler(normalized_request.get("scheduler_name"))
        if scheduler_name:
            fields.append(("Schedule type", scheduler_name))
    _append_field(fields, "CFG scale", normalized_request.get("cfg_scale"))
    _append_field(fields, "Seed", normalized_request.get("execution_seed", normalized_request.get("seed")))
    width = _clean_text(normalized_request.get("width"))
    height = _clean_text(normalized_request.get("height"))
    if width and height:
        fields.append(("Size", f"{width}x{height}"))
    _append_selector_field(fields, "Model", normalized_request.get("checkpoint_name"))
    _append_selector_field(fields, "VAE", normalized_request.get("vae_name"))
    _append_field(fields, "Clip skip", normalized_request.get("clip_skip"))

    surface = _infer_surface(normalized_request)
    if surface == "img2img":
        _append_field(fields, "Denoising strength", normalized_request.get("denoise_strength"))
        _append_field(fields, "Resize mode", normalized_request.get("resize_mode"))
        mode = _clean_text(normalized_request.get("execution_mode") or normalized_request.get("mode")).lower()
        if mode == "inpaint":
            _append_field(fields, "Mask blur", normalized_request.get("mask_blur"))
            _append_field(fields, "Mask mode", normalized_request.get("inpaint_mask_mode"))
            _append_field(fields, "Masked content", normalized_request.get("inpaint_masked_content"))
            _append_field(fields, "Inpaint area", normalized_request.get("inpaint_area"))
            _append_field(fields, "Masked area padding", normalized_request.get("inpaint_padding"))
            if bool(normalized_request.get("soft_inpainting_enabled")):
                _append_field(fields, "Soft inpainting enabled", _format_bool(True))
                _append_field(fields, "Soft inpainting schedule bias", normalized_request.get("soft_inpainting_schedule_bias"))
                _append_field(
                    fields,
                    "Soft inpainting preservation strength",
                    normalized_request.get("soft_inpainting_preservation_strength"),
                )
                _append_field(
                    fields,
                    "Soft inpainting transition contrast boost",
                    normalized_request.get("soft_inpainting_transition_contrast_boost"),
                )
                _append_field(fields, "Soft inpainting mask influence", normalized_request.get("soft_inpainting_mask_influence"))
                _append_field(
                    fields,
                    "Soft inpainting difference threshold",
                    normalized_request.get("soft_inpainting_difference_threshold"),
                )
                _append_field(
                    fields,
                    "Soft inpainting difference contrast",
                    normalized_request.get("soft_inpainting_difference_contrast"),
                )

    if bool(normalized_request.get("hires_enabled")):
        _append_field(fields, "Hires upscale", normalized_request.get("hires_scale"))
        _append_field(fields, "Hires steps", normalized_request.get("hires_steps"))
        _append_field(fields, "Hires upscaler", normalized_request.get("hires_upscale_method"))
        if surface != "img2img":
            _append_field(fields, "Denoising strength", normalized_request.get("hires_denoise"))

    batch_size = normalized_request.get("batch_size")
    if isinstance(batch_size, int) and batch_size > 1:
        _append_field(fields, "Batch size", batch_size)

    field_text = ", ".join(f"{key}: {value}" for key, value in fields)
    lines = [prompt]
    if negative_prompt:
        lines.append(f"Negative prompt: {negative_prompt}")
    if field_text:
        lines.append(field_text)
    infotext = "\n".join(lines).strip()
    if len(infotext) > MAX_INFOTEXT_LENGTH:
        raise ValueError("generated A1111 parameters metadata exceeds maximum infotext length.")
    return infotext


def build_rookieui_extra_pnginfo(
    normalized_request: Mapping[str, Any],
    *,
    workflow_kind: str,
    profile: str,
) -> dict[str, object]:
    surface = _infer_surface(normalized_request)
    scheduler_control_mode = _clean_text(normalized_request.get("scheduler_control_mode") or "generic").lower()
    negative_prompt_mode = _clean_text(normalized_request.get("negative_prompt_mode") or "encoded").lower()
    scheduler_name = _clean_text(normalized_request.get("scheduler_name"))
    if scheduler_control_mode != "generic":
        scheduler_name = scheduler_control_mode
    return {
        "rookieui": {
            "schema": "rookieui.generation_metadata.v1",
            "surface": surface,
            "workflow_kind": _clean_text(workflow_kind),
            "profile": _clean_text(profile),
            "width": normalized_request.get("width"),
            "height": normalized_request.get("height"),
            "steps": normalized_request.get("steps"),
            "sampler_name": _clean_text(normalized_request.get("sampler_name")),
            "scheduler_name": scheduler_name,
            "scheduler_control_mode": scheduler_control_mode,
            "negative_prompt_mode": negative_prompt_mode,
            "parameter_warning_codes": list(normalized_request.get("parameter_warning_codes", []) or []),
            "seed": normalized_request.get("execution_seed", normalized_request.get("seed")),
        }
    }


def build_generation_metadata_payload(
    normalized_request: Mapping[str, Any],
    *,
    workflow_kind: str,
    profile: str,
) -> dict[str, object]:
    return {
        "parameters": build_a1111_parameters(normalized_request),
        "extra_pnginfo": build_rookieui_extra_pnginfo(
            normalized_request,
            workflow_kind=workflow_kind,
            profile=profile,
        ),
    }
