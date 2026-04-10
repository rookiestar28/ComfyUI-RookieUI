from __future__ import annotations

from PIL import Image, ImageOps

from rookieui.contracts.extras import (
    ExtrasExecutionResult,
    ExtrasRequest,
    NormalizedExtrasRequest,
)
from rookieui.security.asset_guard import validate_asset_identifier
from rookieui.security.request_guard import normalize_option_label, resolve_inventory_selector
from rookieui.services.asset_store import (
    build_data_url_from_path,
    resolve_asset_path,
    save_output_image,
    store_uploaded_image,
)
from rookieui.services.coercion import (
    coerce_bool as _coerce_bool,
    coerce_float as _coerce_float,
    coerce_int as _coerce_int,
)
from rookieui.services.model_inventory import discover_model_inventory

_DEFAULT_SCALE_BY = 2.0
_MIN_SCALE_BY = 1.0
_MAX_SCALE_BY = 8.0
_MIN_TARGET_DIMENSION = 64
_MAX_TARGET_DIMENSION = 4096
_UPSCALE_NONE = "None"

def _coerce_dimension(value: object, field_name: str) -> int:
    normalized = _coerce_int(value, field_name)
    if normalized < _MIN_TARGET_DIMENSION or normalized > _MAX_TARGET_DIMENSION:
        raise ValueError(
            f"{field_name} must be between {_MIN_TARGET_DIMENSION} and {_MAX_TARGET_DIMENSION}."
        )
    return normalized


def _collect_source_assets(request: ExtrasRequest) -> list[str]:
    assets: list[str] = []
    if request.image_data:
        assets.append(store_uploaded_image(request.image_data, prefix="extras_input").handle)
    elif request.image_asset:
        assets.append(validate_asset_identifier(request.image_asset))

    for raw_image in request.batch_images:
        assets.append(store_uploaded_image(raw_image, prefix="extras_batch").handle)
    for raw_asset in request.batch_assets:
        assets.append(validate_asset_identifier(raw_asset))
    return list(dict.fromkeys(assets))


def normalize_extras_request(payload: dict[str, object]) -> NormalizedExtrasRequest:
    if not isinstance(payload, dict):
        raise ValueError("Extras request payload must be an object.")

    request = ExtrasRequest(**payload)
    applied_defaults: list[str] = []
    warnings: list[str] = []

    mode = normalize_option_label(request.mode, "mode", max_length=32).lower() or "single_image"
    if mode not in {"single_image", "batch_process"}:
        raise ValueError("mode must be single_image or batch_process.")

    source_assets = _collect_source_assets(request)
    if mode == "single_image" and not source_assets:
        raise ValueError("image_asset or image_data is required for single_image mode.")
    if mode == "single_image":
        source_assets = source_assets[:1]
    if mode == "batch_process" and not source_assets:
        raise ValueError("batch_assets or batch_images is required for batch_process mode.")

    for asset_handle in source_assets:
        resolve_asset_path(asset_handle)

    scale_mode = normalize_option_label(request.scale_mode, "scale_mode", max_length=32).lower() or "scale_by"
    if scale_mode not in {"scale_by", "scale_to"}:
        raise ValueError("scale_mode must be scale_by or scale_to.")

    scale_by = round(_coerce_float(request.scale_by, "scale_by"), 2)
    if scale_by < _MIN_SCALE_BY or scale_by > _MAX_SCALE_BY:
        raise ValueError(f"scale_by must be between {_MIN_SCALE_BY} and {_MAX_SCALE_BY}.")

    target_width = _coerce_dimension(request.target_width, "target_width")
    target_height = _coerce_dimension(request.target_height, "target_height")

    inventory = discover_model_inventory()
    inventory_is_host = inventory.source == "host"
    upscaler_1 = resolve_inventory_selector(
        request.upscaler_1,
        "upscaler_1",
        default_value=_UPSCALE_NONE,
        inventory_selectors=[_UPSCALE_NONE, *inventory.upscale_models],
        strict_match=inventory_is_host,
    )
    upscaler_2 = resolve_inventory_selector(
        request.upscaler_2,
        "upscaler_2",
        default_value=_UPSCALE_NONE,
        inventory_selectors=[_UPSCALE_NONE, *inventory.upscale_models],
        strict_match=inventory_is_host,
    )
    upscaler_2_visibility = round(_coerce_float(request.upscaler_2_visibility, "upscaler_2_visibility"), 2)
    if upscaler_2_visibility < 0.0 or upscaler_2_visibility > 1.0:
        raise ValueError("upscaler_2_visibility must be between 0.0 and 1.0.")

    face_restoration = normalize_option_label(
        request.face_restoration,
        "face_restoration",
        max_length=24,
    ).lower() or "none"
    if face_restoration not in {"none", "codeformer", "gfpgan"}:
        raise ValueError("face_restoration must be none, codeformer, or gfpgan.")
    if face_restoration != "none":
        warnings.append(
            f"{face_restoration} is not available inside the RookieUI workspace pipeline yet; the request will continue without face restoration."
        )

    codeformer_weight = round(_coerce_float(request.codeformer_weight, "codeformer_weight"), 2)
    if codeformer_weight < 0.0 or codeformer_weight > 1.0:
        raise ValueError("codeformer_weight must be between 0.0 and 1.0.")

    return NormalizedExtrasRequest(
        mode=mode,
        source_assets=source_assets,
        upscale_enabled=_coerce_bool(request.upscale_enabled, "upscale_enabled"),
        scale_mode=scale_mode,
        scale_by=scale_by,
        target_width=target_width,
        target_height=target_height,
        upscaler_1=upscaler_1,
        upscaler_2=upscaler_2,
        upscaler_2_visibility=upscaler_2_visibility,
        color_correction=_coerce_bool(request.color_correction, "color_correction"),
        face_restoration=face_restoration,
        codeformer_weight=codeformer_weight,
        warnings=warnings,
        applied_defaults=applied_defaults,
    )


def _resize_image(image: Image.Image, request: NormalizedExtrasRequest) -> Image.Image:
    if not request.upscale_enabled:
        return image

    if request.scale_mode == "scale_to":
        target_size = (request.target_width, request.target_height)
    else:
        target_size = (
            max(_MIN_TARGET_DIMENSION, int(round(image.width * request.scale_by))),
            max(_MIN_TARGET_DIMENSION, int(round(image.height * request.scale_by))),
        )
    return image.resize(target_size, Image.Resampling.LANCZOS)


def execute_extras_request(request: NormalizedExtrasRequest) -> ExtrasExecutionResult:
    output_assets: list[str] = []
    preview_asset = ""
    preview_data_url = ""
    warnings = list(request.warnings)

    for asset_handle in request.source_assets:
        source_path = resolve_asset_path(asset_handle)
        image = Image.open(source_path)
        image = ImageOps.exif_transpose(image)
        metadata = {
            key: value
            for key, value in getattr(image, "info", {}).items()
            if isinstance(key, str) and isinstance(value, str)
        }

        processed = image.convert("RGB")
        processed = _resize_image(processed, request)
        if request.color_correction:
            processed = ImageOps.autocontrast(processed)

        saved = save_output_image(
            processed,
            prefix="rookieui_extras",
            metadata=metadata,
        )
        output_assets.append(saved.handle)
        if not preview_asset:
            preview_asset = saved.handle
            preview_data_url = build_data_url_from_path(saved.path)

    return ExtrasExecutionResult(
        mode=request.mode,
        normalized_request=request.to_payload(),
        output_assets=output_assets,
        preview_asset=preview_asset,
        preview_data_url=preview_data_url,
        warnings=warnings,
    )
