from __future__ import annotations

import json
import io
import logging
import re
from typing import Any

from PIL import Image

from rookieui.contracts.aliases import (
    HIRES_UPSCALE_METHODS as _HIRES_UPSCALE_METHODS,
    INPAINT_AREA_ALIASES as _INPAINT_AREA_ALIASES,
    MASKED_CONTENT_ALIASES as _MASKED_CONTENT_ALIASES,
    MASK_MODE_ALIASES as _MASK_MODE_ALIASES,
    RESIZE_MODE_ALIASES as _RESIZE_MODE_ALIASES,
)
from rookieui.contracts.pnginfo import PNGInfoParseResult
from rookieui.security.request_guard import (
    normalize_infotext,
    normalize_prompt_text,
    resolve_inventory_selector,
)
from rookieui.services.asset_store import store_uploaded_image
from rookieui.services.model_inventory import discover_model_inventory
from rookieui.services.parity_matrix import (
    get_parity_profile,
    normalize_sampler_name,
    normalize_scheduler_name,
)
from rookieui.services.coercion import (
    coerce_bool,
    coerce_float,
    coerce_int,
)

_PARAM_RE = re.compile(r'\s*(\w[\w \-/]+):\s*("(?:\\.|[^\\"])+"|[^,]*)(?:,|$)')
_IMAGE_SIZE_RE = re.compile(r"^(\d+)x(\d+)$")
_SCHEDULER_SUFFIXES = (" karras", " exponential", " sgm uniform", " simple")
_INPAINT_MARKERS = {"Mask mode", "Masked content", "Inpaint area", "Masked area padding"}
_HIRES_MARKERS = {
    "Hires upscale",
    "Hires upscaler",
    "Hires steps",
    "Hires resize-1",
    "Hires resize-2",
}
_HIRES_UPSCALER_ALIASES = {
    "area": "area",
    "bicubic": "bicubic",
    "bilinear": "bilinear",
    "bislerp": "bislerp",
    "latent": "bislerp",
    "latent (area)": "area",
    "latent (bicubic)": "bicubic",
    "latent (bilinear)": "bilinear",
    "latent (bislerp)": "bislerp",
    "latent (nearest)": "nearest-exact",
    "latent (nearest-exact)": "nearest-exact",
    "nearest": "nearest-exact",
    "nearest exact": "nearest-exact",
    "nearest-exact": "nearest-exact",
}
_DEFAULT_HIRES_UPSCALE_METHOD = "bislerp"
_LOGGER = logging.getLogger("ComfyUI-RookieUI")


def _unquote_text(value: str) -> str:
    if len(value) < 2 or value[0] != '"' or value[-1] != '"':
        return value

    try:
        return json.loads(value)
    except Exception:
        _LOGGER.debug("RookieUI PNGInfo quoted text decode fallback triggered.", exc_info=True)
        return value


def _extract_image_source(payload: dict[str, object]) -> tuple[dict[str, str], str | None, str]:
    image_data = payload.get("image_data")
    if image_data in (None, ""):
        # IMPORTANT: PNG Info is image-first only; text-only inspection paths are intentionally retired to keep extraction behavior deterministic.
        raise ValueError("image_data is required.")

    stored_asset = store_uploaded_image(image_data, prefix="pnginfo")
    image = Image.open(io.BytesIO(stored_asset.path.read_bytes()))
    metadata_items: dict[str, str] = {}
    for key, value in image.info.items():
        if isinstance(key, str) and isinstance(value, str):
            metadata_items[key] = value

    if metadata_items.get("parameters"):
        return metadata_items, metadata_items["parameters"], stored_asset.handle
    if metadata_items.get("Comment"):
        return metadata_items, metadata_items["Comment"], stored_asset.handle
    return metadata_items, None, stored_asset.handle


def _parse_generation_parameters(text: str) -> dict[str, object]:
    prompt = ""
    negative_prompt = ""
    raw: dict[str, object] = {}
    done_with_prompt = False

    stripped = text.strip()
    if not stripped:
        raise ValueError("infotext is required.")

    *lines, last_line = stripped.split("\n")
    if len(_PARAM_RE.findall(last_line)) < 3:
        lines.append(last_line)
        last_line = ""

    for line in lines:
        candidate = line.strip()
        if candidate.startswith("Negative prompt:"):
            done_with_prompt = True
            candidate = candidate[16:].strip()
        if done_with_prompt:
            negative_prompt += ("" if not negative_prompt else "\n") + candidate
        else:
            prompt += ("" if not prompt else "\n") + candidate

    for key, value in _PARAM_RE.findall(last_line):
        parsed_value = _unquote_text(value)
        size_match = _IMAGE_SIZE_RE.match(parsed_value)
        if size_match:
            raw[f"{key}-1"] = size_match.group(1)
            raw[f"{key}-2"] = size_match.group(2)
            continue
        raw[key] = parsed_value

    raw["Prompt"] = prompt
    raw["Negative prompt"] = negative_prompt
    return raw


def _coerce_int(value: object, field_name: str, *, default: int | None = None) -> int:
    return coerce_int(
        value,
        field_name,
        default=default,
        via_str=True,
        required_if_empty=True,
    )


def _coerce_float(value: object, field_name: str, *, default: float | None = None) -> float:
    return coerce_float(
        value,
        field_name,
        default=default,
        via_str=True,
        precision=3,
        required_if_empty=True,
    )


def _coerce_bool(value: object, field_name: str, *, default: bool = False) -> bool:
    return coerce_bool(value, field_name, default=default, error_label="a boolean value")


def _normalize_label_with_aliases(
    value: object,
    *,
    default_value: str,
    aliases: dict[str, str],
) -> str:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return default_value
    return aliases.get(normalized, default_value)


def _normalize_sampler_label(raw_sampler: str | None, *, default_sampler: str) -> str:
    if not raw_sampler:
        return default_sampler

    candidate = raw_sampler.strip()
    normalized = candidate.lower()
    for suffix in _SCHEDULER_SUFFIXES:
        if normalized.endswith(suffix):
            candidate = candidate[: -len(suffix)]
            break

    mapped = normalize_sampler_name(candidate)
    return mapped or default_sampler


def _normalize_schedule_type(
    raw_sampler: str | None,
    raw_schedule: str | None,
    *,
    default_scheduler: str,
    warnings: list[str],
) -> str:
    schedule_candidate = (raw_schedule or "").strip()
    if schedule_candidate.lower() in {"", "automatic", "use same scheduler"}:
        schedule_candidate = ""

    try:
        return normalize_scheduler_name(
            raw_sampler,
            schedule_candidate or None,
            default_scheduler=default_scheduler,
        )
    except ValueError:
        warnings.append(
            f"Unsupported schedule type '{raw_schedule}' was mapped to '{default_scheduler}'."
        )
        return default_scheduler


def _has_hires_marker(raw_parameters: dict[str, object]) -> bool:
    return bool(_HIRES_MARKERS.intersection(raw_parameters))


def _normalize_hires_upscale_method(raw_upscaler: object, *, warnings: list[str]) -> str:
    label = str(raw_upscaler or "").strip()
    if not label:
        return _DEFAULT_HIRES_UPSCALE_METHOD

    normalized = re.sub(r"\s+", " ", label.replace("_", "-").strip().lower())
    if normalized in _HIRES_UPSCALE_METHODS:
        return normalized

    mapped = _HIRES_UPSCALER_ALIASES.get(normalized)
    if mapped:
        return mapped

    warnings.append(
        f"Imported Hires upscaler '{label}' is not available in RookieUI latent hires "
        f"and fell back to '{_DEFAULT_HIRES_UPSCALE_METHOD}'."
    )
    return _DEFAULT_HIRES_UPSCALE_METHOD


def _infer_profile(raw_parameters: dict[str, object]) -> str:
    model_name = " ".join(
        str(raw_parameters.get(key, "")).strip().lower()
        for key in ("Model", "Model name", "Checkpoint")
    )
    if "pony" in model_name:
        return "pony"
    if "illustrious" in model_name:
        return "illustrious"
    if "noob" in model_name:
        return "noob"
    if "sdxl" in model_name or re.search(r"xl(?:[._\-\s]|$)", model_name):
        return "sdxl"

    width = _coerce_int(raw_parameters.get("Size-1"), "Size-1", default=512)
    height = _coerce_int(raw_parameters.get("Size-2"), "Size-2", default=512)
    if max(width, height) >= 1024:
        return "sdxl"
    return "sd15"


def _infer_target_form(raw_parameters: dict[str, object]) -> str:
    has_img2img_marker = "Denoising strength" in raw_parameters
    has_inpaint_marker = bool(_INPAINT_MARKERS.intersection(raw_parameters))
    if has_img2img_marker and has_inpaint_marker:
        return "inpaint"
    # IMPORTANT: A1111 Hires.fix txt2img infotext also includes Denoising strength;
    # keep it out of the img2img path when hires markers are present.
    if has_img2img_marker and _has_hires_marker(raw_parameters):
        return "txt2img"
    if has_img2img_marker:
        return "img2img"
    return "txt2img"


def _inspect_comfy_metadata(
    *,
    source: str,
    metadata_items: dict[str, str],
    asset_handle: str,
) -> PNGInfoParseResult:
    summary_keys = ("prompt", "workflow", "parameters", "Comment")
    filtered_metadata = {
        key: value
        for key, value in metadata_items.items()
        if key in summary_keys
    }
    warnings = []
    if "prompt" in filtered_metadata:
        warnings.append("ComfyUI metadata is available for inspection only in RookieUI.")

    return PNGInfoParseResult(
        source=source,
        source_type="comfyui",
        target_form="inspect_only",
        payload={},
        raw_parameters={},
        metadata_items=filtered_metadata,
        apply_targets=[],
        asset_handle=asset_handle,
        unsupported_fields=[],
        missing_inputs=[],
        warnings=warnings,
    )


def parse_pnginfo_payload(payload: dict[str, object]) -> PNGInfoParseResult:
    metadata_items, image_infotext, asset_handle = _extract_image_source(payload)
    if image_infotext:
        source = "image.parameters"
        infotext = normalize_infotext(image_infotext)
        source_type = "a1111"
    else:
        prompt_json = metadata_items.get("prompt")
        workflow_json = metadata_items.get("workflow")
        if prompt_json or workflow_json:
            return _inspect_comfy_metadata(
                source="image.metadata",
                metadata_items=metadata_items,
                asset_handle=asset_handle,
            )
        raise ValueError("No A1111 parameters metadata found in image_data.")

    raw_parameters = _parse_generation_parameters(infotext)
    profile_id = _infer_profile(raw_parameters)
    profile = get_parity_profile(profile_id)
    target_form = _infer_target_form(raw_parameters)
    inventory = discover_model_inventory()
    warnings: list[str] = []
    consumed_fields: set[str] = {"Prompt", "Negative prompt"}

    raw_sampler = str(raw_parameters.get("Sampler", "")).strip()
    if raw_sampler:
        consumed_fields.add("Sampler")

    raw_schedule = str(raw_parameters.get("Schedule type", "")).strip()
    if raw_schedule:
        consumed_fields.add("Schedule type")

    model_name = resolve_inventory_selector(
        raw_parameters.get("Model", "") or raw_parameters.get("Model name", ""),
        "checkpoint_name",
        default_value=inventory.default_checkpoint,
        inventory_selectors=inventory.checkpoints,
    )
    if raw_parameters.get("Model"):
        consumed_fields.add("Model")
    if raw_parameters.get("Model name"):
        consumed_fields.add("Model name")

    vae_name = resolve_inventory_selector(
        raw_parameters.get("VAE", ""),
        "vae_name",
        default_value=inventory.default_vae,
        inventory_selectors=inventory.vae,
    )
    if raw_parameters.get("VAE"):
        consumed_fields.add("VAE")

    if inventory.source == "host":
        if model_name not in inventory.checkpoints:
            model_name = inventory.default_checkpoint
            warnings.append("Imported checkpoint was not found in the current host inventory and fell back to the active default.")
        if vae_name not in inventory.vae:
            vae_name = inventory.default_vae
            warnings.append("Imported VAE was not found in the current host inventory and fell back to the active default.")

    payload_map: dict[str, object] = {
        "prompt": normalize_prompt_text(raw_parameters.get("Prompt", ""), "prompt"),
        "negative_prompt": normalize_prompt_text(
            raw_parameters.get("Negative prompt", ""),
            "negative_prompt",
        ),
        "profile": profile.id,
        "checkpoint_name": model_name,
        "vae_name": vae_name,
        "text_encoder_name": "Automatic",
        "steps": _coerce_int(raw_parameters.get("Steps"), "Steps", default=profile.default_steps),
        "cfg_scale": _coerce_float(
            raw_parameters.get("CFG scale"),
            "CFG scale",
            default=profile.default_cfg_scale,
        ),
        "sampler_name": _normalize_sampler_label(
            raw_sampler or profile.default_sampler,
            default_sampler=profile.default_sampler,
        ),
        "scheduler_name": _normalize_schedule_type(
            raw_sampler or profile.default_sampler,
            raw_schedule or None,
            default_scheduler=profile.default_scheduler,
            warnings=warnings,
        ),
        "seed": _coerce_int(raw_parameters.get("Seed"), "Seed", default=-1),
        "clip_skip": _coerce_int(
            raw_parameters.get("Clip skip"),
            "Clip skip",
            default=profile.default_clip_skip,
        ),
    }

    for field in ("Steps", "CFG scale", "Seed", "Clip skip"):
        if field in raw_parameters:
            consumed_fields.add(field)

    if target_form == "txt2img":
        payload_map["width"] = _coerce_int(
            raw_parameters.get("Size-1"),
            "Size-1",
            default=profile.default_width,
        )
        payload_map["height"] = _coerce_int(
            raw_parameters.get("Size-2"),
            "Size-2",
            default=profile.default_height,
        )
        consumed_fields.update({"Size-1", "Size-2"})
        if "Batch size" in raw_parameters:
            payload_map["batch_size"] = _coerce_int(raw_parameters.get("Batch size"), "Batch size", default=1)
            consumed_fields.add("Batch size")
        else:
            payload_map["batch_size"] = 1
        if _has_hires_marker(raw_parameters):
            payload_map["hires_enabled"] = True
            payload_map["hires_scale"] = _coerce_float(
                raw_parameters.get("Hires upscale"),
                "Hires upscale",
                default=1.5,
            )
            payload_map["hires_steps"] = _coerce_int(
                raw_parameters.get("Hires steps"),
                "Hires steps",
                default=0,
            )
            payload_map["hires_denoise"] = _coerce_float(
                raw_parameters.get("Denoising strength"),
                "Denoising strength",
                default=0.35,
            )
            payload_map["hires_upscale_method"] = _normalize_hires_upscale_method(
                raw_parameters.get("Hires upscaler"),
                warnings=warnings,
            )
            consumed_fields.update(
                {"Denoising strength", "Hires upscale", "Hires upscaler", "Hires steps"}
            )
    else:
        payload_map["mode"] = "inpaint" if target_form == "inpaint" else "img2img"
        payload_map["width"] = _coerce_int(
            raw_parameters.get("Size-1"),
            "Size-1",
            default=profile.default_width,
        )
        payload_map["height"] = _coerce_int(
            raw_parameters.get("Size-2"),
            "Size-2",
            default=profile.default_height,
        )
        payload_map["resize_mode"] = _normalize_label_with_aliases(
            raw_parameters.get("Resize mode"),
            default_value="crop_and_resize",
            aliases=_RESIZE_MODE_ALIASES,
        )
        payload_map["batch_size"] = _coerce_int(raw_parameters.get("Batch size"), "Batch size", default=1)
        payload_map["denoise_strength"] = _coerce_float(
            raw_parameters.get("Denoising strength"),
            "Denoising strength",
            default=0.75,
        )
        payload_map["grow_mask_by"] = _coerce_int(
            raw_parameters.get("Masked area padding"),
            "Masked area padding",
            default=32,
        )
        payload_map["mask_blur"] = _coerce_int(raw_parameters.get("Mask blur"), "Mask blur", default=4)
        payload_map["inpaint_mask_mode"] = _normalize_label_with_aliases(
            raw_parameters.get("Mask mode"),
            default_value="inpaint_masked",
            aliases=_MASK_MODE_ALIASES,
        )
        payload_map["inpaint_masked_content"] = _normalize_label_with_aliases(
            raw_parameters.get("Masked content"),
            default_value="original",
            aliases=_MASKED_CONTENT_ALIASES,
        )
        payload_map["inpaint_area"] = _normalize_label_with_aliases(
            raw_parameters.get("Inpaint area"),
            default_value="only_masked",
            aliases=_INPAINT_AREA_ALIASES,
        )
        payload_map["inpaint_padding"] = _coerce_int(
            raw_parameters.get("Masked area padding"),
            "Masked area padding",
            default=32,
        )
        payload_map["soft_inpainting_enabled"] = _coerce_bool(
            raw_parameters.get("Soft inpainting enabled"),
            "Soft inpainting enabled",
            default=False,
        )
        payload_map["soft_inpainting_schedule_bias"] = _coerce_float(
            raw_parameters.get("Soft inpainting schedule bias"),
            "Soft inpainting schedule bias",
            default=1.0,
        )
        payload_map["soft_inpainting_preservation_strength"] = _coerce_float(
            raw_parameters.get("Soft inpainting preservation strength"),
            "Soft inpainting preservation strength",
            default=0.5,
        )
        payload_map["soft_inpainting_transition_contrast_boost"] = _coerce_float(
            raw_parameters.get("Soft inpainting transition contrast boost"),
            "Soft inpainting transition contrast boost",
            default=4.0,
        )
        payload_map["soft_inpainting_mask_influence"] = _coerce_float(
            raw_parameters.get("Soft inpainting mask influence"),
            "Soft inpainting mask influence",
            default=0.0,
        )
        payload_map["soft_inpainting_difference_threshold"] = _coerce_float(
            raw_parameters.get("Soft inpainting difference threshold"),
            "Soft inpainting difference threshold",
            default=0.5,
        )
        payload_map["soft_inpainting_difference_contrast"] = _coerce_float(
            raw_parameters.get("Soft inpainting difference contrast"),
            "Soft inpainting difference contrast",
            default=2.0,
        )
        consumed_fields.update({"Size-1", "Size-2", "Resize mode", "Batch size", "Denoising strength", "Mask blur"})
        if "Masked area padding" in raw_parameters:
            consumed_fields.add("Masked area padding")
        consumed_fields.update(
            {
                "Soft inpainting enabled",
                "Soft inpainting schedule bias",
                "Soft inpainting preservation strength",
                "Soft inpainting transition contrast boost",
                "Soft inpainting mask influence",
                "Soft inpainting difference threshold",
                "Soft inpainting difference contrast",
            }
        )
        if target_form == "inpaint":
            consumed_fields.update(_INPAINT_MARKERS.intersection(raw_parameters))

    missing_inputs: list[str] = []
    if target_form in {"img2img", "inpaint"}:
        if asset_handle:
            payload_map["image_asset"] = asset_handle
        else:
            missing_inputs.append("image_asset")
            warnings.append("Source image asset must be selected manually after importing infotext.")
    if target_form == "inpaint":
        missing_inputs.append("mask_asset")
        warnings.append("Mask asset must be selected manually after importing infotext.")

    unsupported_fields = sorted(
        key
        for key in raw_parameters.keys()
        if key not in consumed_fields
    )

    display_metadata = dict(metadata_items)
    prompt_text = str(payload_map.get("prompt", "")).strip()
    negative_prompt_text = str(payload_map.get("negative_prompt", "")).strip()
    if prompt_text:
        display_metadata.setdefault("Prompt", prompt_text)
    if negative_prompt_text:
        display_metadata.setdefault("Negative prompt", negative_prompt_text)

    return PNGInfoParseResult(
        source=source,
        source_type=source_type,
        target_form=target_form,
        payload=payload_map,
        raw_parameters=raw_parameters,
        metadata_items=display_metadata,
        apply_targets=["txt2img", "img2img"] if source_type == "a1111" else [],
        asset_handle=asset_handle,
        unsupported_fields=unsupported_fields,
        missing_inputs=missing_inputs,
        warnings=warnings,
    )
