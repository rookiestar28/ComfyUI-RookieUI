from __future__ import annotations

import logging
from typing import Any, Callable

from rookieui.security.request_guard import normalize_option_label
from rookieui.services.controlnet_catalog import DEFAULT_CONTROLNET_MODULE
from rookieui.services.controlnet_normalization import (
    _coerce_processor_res,
    _coerce_threshold,
    _normalize_choice,
)
from rookieui.services.controlnet_profiles import (
    get_preprocessor_profile,
    resolve_effective_processor_resolution,
)
from rookieui.services.controlnet_warnings import (
    CONTROLNET_WARNING_PREPROCESSOR_DISABLED,
    CONTROLNET_WARNING_PREPROCESSOR_EMPTY_OUTPUT,
    CONTROLNET_WARNING_PREPROCESSOR_HOST_FALLBACK,
    CONTROLNET_WARNING_PREPROCESSOR_UNAVAILABLE,
)


def _normalize_detect_images(payload: dict[str, object]) -> list[str]:
    raw_images = payload.get("controlnet_input_images")
    if isinstance(raw_images, list) and raw_images:
        images = [entry for entry in raw_images if isinstance(entry, str) and entry.strip()]
    else:
        single_image = payload.get("image")
        images = [single_image] if isinstance(single_image, str) and single_image.strip() else []
    if not images:
        raise ValueError("controlnet_input_images or image is required.")
    if len(images) > 8:
        raise ValueError("controlnet_input_images must contain at most 8 images.")
    return images


def _normalize_detect_masks(payload: dict[str, object], *, image_count: int) -> list[str]:
    raw_masks = payload.get("controlnet_masks")
    if raw_masks is None:
        return []
    if not isinstance(raw_masks, list):
        raise ValueError("controlnet_masks must be an array when provided.")
    masks = [entry for entry in raw_masks if isinstance(entry, str) and entry.strip()]
    if masks and len(masks) != image_count:
        raise ValueError("controlnet_masks must be empty or match controlnet_input_images length.")
    return masks


def _coerce_detect_bool(raw_value: object) -> bool:
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, (int, float)):
        return bool(raw_value)
    if isinstance(raw_value, str):
        return raw_value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _coerce_optional_int(raw_value: object) -> int | None:
    try:
        value = int(round(float(raw_value)))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _image_dimensions_from_tensor(image_tensor: Any) -> tuple[int | None, int | None]:
    shape = getattr(image_tensor, "shape", None)
    if not isinstance(shape, (tuple, list)) or len(shape) < 3:
        return None, None
    try:
        if len(shape) >= 4:
            return int(shape[2]), int(shape[1])
        return int(shape[1]), int(shape[0])
    except (TypeError, ValueError):
        return None, None


def _bounded_secondary_values(values: object) -> list[object]:
    if not isinstance(values, (list, tuple)):
        values = [values]
    bounded: list[object] = []
    for value in list(values)[:16]:
        if isinstance(value, str):
            bounded.append(value[:65536])
        else:
            bounded.append(value)
    return bounded


def build_controlnet_detect_payload(
    payload: dict[str, object],
    *,
    module_aliases: dict[str, str],
    contract_meta: dict[str, object],
    preprocessor_enabled: bool,
    runtime_available: bool,
    warning_message_builder: Callable[[list[str]], list[str]],
    decode_image_data_fn: Callable[[str], tuple[bytes, str]],
    image_tensor_from_bytes_fn: Callable[[bytes], Any],
    mask_tensor_from_bytes_fn: Callable[[bytes], Any],
    preprocess_controlnet_tensor_fn: Callable[..., Any],
    image_tensor_to_data_url_fn: Callable[[Any], str],
    logger: logging.Logger,
) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError("ControlNet detect payload must be an object.")

    module = _normalize_choice(
        payload.get("controlnet_module"),
        field_name="controlnet_module",
        aliases=module_aliases,
        default_value=DEFAULT_CONTROLNET_MODULE,
    )
    requested_controlnet_model = normalize_option_label(
        payload.get("controlnet_model"),
        "controlnet_model",
        max_length=256,
    )
    input_images = _normalize_detect_images(payload)
    warning_codes: list[str] = []
    profile = get_preprocessor_profile(module)
    profile_payload = profile.to_payload()

    if module == DEFAULT_CONTROLNET_MODULE:
        return {
            "source": "rookieui",
            "detect_backend": "passthrough_none",
            "contract": contract_meta,
            "module": module,
            "requested_controlnet_model": requested_controlnet_model,
            "preprocessor_profile": profile_payload,
            "images": input_images,
            "warning_codes": warning_codes,
            "warnings": warning_message_builder(warning_codes),
        }

    processor_res = _coerce_processor_res(payload.get("controlnet_processor_res"), "controlnet_processor_res")
    threshold_a = _coerce_threshold(payload.get("controlnet_threshold_a"), "controlnet_threshold_a", 64.0)
    threshold_b = _coerce_threshold(payload.get("controlnet_threshold_b"), "controlnet_threshold_b", 64.0)
    pixel_perfect = _coerce_detect_bool(payload.get("controlnet_pixel_perfect"))
    resize_mode = str(payload.get("controlnet_resize_mode") or payload.get("resize_mode") or "crop_and_resize")
    target_width = _coerce_optional_int(payload.get("target_width") or payload.get("width"))
    target_height = _coerce_optional_int(payload.get("target_height") or payload.get("height"))
    input_masks = _normalize_detect_masks(payload, image_count=len(input_images))
    if len(input_masks) < len(input_images):
        input_masks.extend([""] * (len(input_images) - len(input_masks)))

    if not preprocessor_enabled:
        warning_codes.append(CONTROLNET_WARNING_PREPROCESSOR_DISABLED)
        return {
            "source": "rookieui",
            "detect_backend": "rookieui_internal_disabled",
            "contract": contract_meta,
            "module": module,
            "requested_controlnet_model": requested_controlnet_model,
            "preprocessor_profile": profile_payload,
            "images": input_images,
            "warning_codes": warning_codes,
            "warnings": warning_message_builder(warning_codes),
        }

    if not runtime_available:
        warning_codes.append(CONTROLNET_WARNING_PREPROCESSOR_UNAVAILABLE)
        return {
            "source": "rookieui",
            "detect_backend": "rookieui_internal_unavailable",
            "contract": contract_meta,
            "module": module,
            "requested_controlnet_model": requested_controlnet_model,
            "preprocessor_profile": profile_payload,
            "images": input_images,
            "warning_codes": warning_codes,
            "warnings": warning_message_builder(warning_codes),
        }

    output_images: list[str] = []
    backend_labels: list[str] = []
    processor_names: list[str] = []
    fallback_used = False
    fallback_diagnostics: list[str] = []
    near_empty_diagnostics: list[str] = []
    secondary_outputs: dict[str, list[object]] = {}
    effective_processor_res = processor_res
    for index, raw_image in enumerate(input_images):
        try:
            image_bytes, _ = decode_image_data_fn(raw_image)
            image_tensor = image_tensor_from_bytes_fn(image_bytes)
            image_width, image_height = _image_dimensions_from_tensor(image_tensor)
            effective_processor_res = resolve_effective_processor_resolution(
                requested_processor_res=processor_res,
                pixel_perfect=pixel_perfect,
                image_width=image_width,
                image_height=image_height,
                target_width=target_width or image_width,
                target_height=target_height or image_height,
                resize_mode=resize_mode,
                profile=profile,
            )
            mask_tensor = None
            raw_mask = input_masks[index]
            if raw_mask:
                mask_bytes, _ = decode_image_data_fn(raw_mask)
                mask_tensor = mask_tensor_from_bytes_fn(mask_bytes)
            runtime_result = preprocess_controlnet_tensor_fn(
                image_tensor=image_tensor,
                module=module,
                processor_res=effective_processor_res,
                threshold_a=threshold_a,
                threshold_b=threshold_b,
                mask_tensor=mask_tensor,
                pixel_perfect=pixel_perfect,
                target_width=target_width,
                target_height=target_height,
                resize_mode=resize_mode,
            )
            # DEBUG HOTSPOT: inspect per-image runtime seam first when preprocess output appears visually incorrect.
            # This captures backend/processor provenance before payload-level warning aggregation.
            backend_labels.append(runtime_result.backend)
            processor_names.append(runtime_result.processor_name)
            if runtime_result.used_fallback:
                fallback_used = True
                fallback_diagnostics.extend(list(runtime_result.diagnostics))
            else:
                # DEBUG HOTSPOT: successful-host-but-empty-output seam; this isolates black/blank previews
                # that are not runtime failures and should surface as targeted warnings.
                near_empty_diagnostics.extend(
                    [entry for entry in runtime_result.diagnostics if "output_near_empty" in str(entry)]
                )
            runtime_secondary = runtime_result.secondary_outputs or {}
            for output_key in profile.secondary_outputs:
                if output_key not in runtime_secondary:
                    continue
                secondary_outputs.setdefault(output_key, []).extend(_bounded_secondary_values(runtime_secondary[output_key]))
            output_images.append(image_tensor_to_data_url_fn(runtime_result.image))
        except Exception as exc:
            raise ValueError(f"controlnet_input_images[{index}] or controlnet_masks[{index}] is not a valid image payload.") from exc

    if fallback_used:
        warning_codes.append(CONTROLNET_WARNING_PREPROCESSOR_HOST_FALLBACK)
        if fallback_diagnostics:
            # DEBUG HOTSPOT: primary fallback triage seam for run-preprocessor regressions.
            # Prioritize markers like `prompt_server_last_prompt_id_shim_applied`, node exception text, and probe-limit diagnostics.
            logger.warning(
                "RookieUI ControlNet detect host preprocessor fallback engaged (module=%s): %s",
                module,
                " | ".join(fallback_diagnostics[:3]),
            )
    if near_empty_diagnostics:
        warning_codes.append(CONTROLNET_WARNING_PREPROCESSOR_EMPTY_OUTPUT)
        # DEBUG HOTSPOT: near-empty host output seam (often seen in pose/seg detectors on incompatible crops).
        logger.warning(
            "RookieUI ControlNet detect host preprocessor produced near-empty output (module=%s): %s",
            module,
            " | ".join(near_empty_diagnostics[:3]),
        )

    detect_backend = "rookieui_internal"
    if backend_labels:
        unique_backends = list(dict.fromkeys(backend_labels))
        detect_backend = unique_backends[0] if len(unique_backends) == 1 else "rookieui_internal_mixed"

    response_payload = {
        "source": "rookieui",
        "detect_backend": detect_backend,
        "contract": contract_meta,
        "module": module,
        "requested_controlnet_model": requested_controlnet_model,
        "preprocessor_profile": profile_payload,
        "processor_res": effective_processor_res,
        "pixel_perfect": pixel_perfect,
        "processor": processor_names[0] if processor_names else module,
        "images": output_images,
        "warning_codes": warning_codes,
        "warnings": warning_message_builder(warning_codes),
    }
    if secondary_outputs:
        response_payload["secondary_outputs"] = secondary_outputs
        if "openpose_json" in secondary_outputs:
            response_payload["openpose_json"] = secondary_outputs["openpose_json"]
    return response_payload
