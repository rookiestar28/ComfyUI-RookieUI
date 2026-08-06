"""Project-native ControlNet effect/source mask semantics.

This module deliberately owns only tensor-shape and mask arithmetic.  The native
apply node remains responsible for host lifecycle and conditioning-chain
ownership, while this seam keeps preprocessor, effect, and modern inpainting
source masks explicit and testable.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

try:
    import torch
except Exception:  # pragma: no cover - thin import path without host torch
    torch = None


def _require_torch() -> Any:
    if torch is None:
        raise RuntimeError("RookieUI ControlNet mask runtime requires torch to be installed.")
    return torch


def normalize_effect_mask(mask: Any, *, batch_size: int | None = None) -> Any:
    """Return a strict `[B,H,W]` float mask suitable for ControlNet outputs.

    ComfyUI's MASK contract is rank three.  A rank-four single-channel tensor is
    accepted because host integrations commonly expose `[B,1,H,W]`; every other
    rank/channel shape is rejected instead of being guessed as token/video data.
    A single mask batch is explicitly broadcast when a target batch is supplied.
    """

    if mask is None:
        return None
    torch_module = _require_torch()
    if not isinstance(mask, torch_module.Tensor):
        raise ValueError("ControlNet mask must be a torch tensor.")

    if mask.ndim == 3:
        normalized = mask
    elif mask.ndim == 4 and int(mask.shape[1]) == 1:
        normalized = mask[:, 0, :, :]
    else:
        raise ValueError("ControlNet mask must have shape [B,H,W] or [B,1,H,W].")

    if normalized.shape[0] <= 0 or normalized.shape[1] <= 0 or normalized.shape[2] <= 0:
        raise ValueError("ControlNet mask dimensions must be positive.")
    if not bool(torch_module.isfinite(normalized).all().item()):
        raise ValueError("ControlNet mask must contain only finite values.")

    if batch_size is not None:
        target_batch = int(batch_size)
        if target_batch <= 0:
            raise ValueError("ControlNet target batch size must be positive.")
        current_batch = int(normalized.shape[0])
        if current_batch == 1 and target_batch > 1:
            normalized = normalized.repeat(target_batch, 1, 1)
        elif current_batch != target_batch:
            raise ValueError(
                f"ControlNet mask batch {current_batch} does not match target batch {target_batch}."
            )

    return torch_module.clamp(normalized.to(dtype=torch_module.float32), 0.0, 1.0)


def is_all_zero_mask(mask: Any) -> bool:
    """Return whether a normalized effect mask is exactly zero everywhere."""

    torch_module = _require_torch()
    normalized = normalize_effect_mask(mask)
    return bool(torch_module.count_nonzero(normalized).item() == 0)


def _resize_mask_for_output(mask: Any, *, batch_size: int, height: int, width: int, device: Any) -> Any:
    torch_module = _require_torch()
    normalized = normalize_effect_mask(mask, batch_size=batch_size)
    resized = torch_module.nn.functional.interpolate(
        normalized.unsqueeze(1).to(device=device, dtype=torch_module.float32),
        size=(int(height), int(width)),
        mode="bilinear",
        align_corners=False,
    )
    return torch_module.clamp(resized.squeeze(1), 0.0, 1.0)


def apply_effect_mask_to_control(control: Mapping[str, list[Any]] | None, mask: Any) -> dict[str, list[Any]] | None:
    """Mask only newly generated ControlNet tensors without mutating `control`."""

    if control is None or mask is None:
        return control
    torch_module = _require_torch()
    normalized = normalize_effect_mask(mask)
    masked: dict[str, list[Any]] = {"input": [], "middle": [], "output": []}
    for key in ("input", "middle", "output"):
        for tensor in list(control.get(key, [])):
            if tensor is None:
                masked[key].append(None)
                continue
            if not isinstance(tensor, torch_module.Tensor) or tensor.ndim != 4:
                raise ValueError(
                    f"ControlNet {key} output must have rank 4 [B,C,H,W] for effect masking."
                )
            output_mask = _resize_mask_for_output(
                normalized,
                batch_size=int(tensor.shape[0]),
                height=int(tensor.shape[-2]),
                width=int(tensor.shape[-1]),
                device=tensor.device,
            )
            channel_mask = output_mask.unsqueeze(1).to(dtype=tensor.dtype, device=tensor.device)
            masked[key].append(tensor * channel_mask)
    return masked


def prepare_concat_mask(image: Any, source_mask: Any) -> tuple[Any, list[Any]]:
    """Prepare the current-host modern inpainting image and `extra_concat` mask."""

    torch_module = _require_torch()
    if not isinstance(image, torch_module.Tensor) or image.ndim != 4:
        raise ValueError("ControlNet concat_mask image must have rank 4 NHWC shape [B,H,W,C].")
    batch_size, height, width, channels = (int(value) for value in image.shape)
    if channels <= 0:
        raise ValueError("ControlNet concat_mask image must contain at least one channel.")

    normalized = normalize_effect_mask(source_mask, batch_size=batch_size)
    # This is the current host contract: invert the source mask in NCHW space,
    # resize/round it for the source image, zero masked pixels, and preserve the
    # unresized inverted mask as the extra concat conditioning tensor.
    inverted_source_mask = 1.0 - normalized.unsqueeze(1).to(device=image.device, dtype=torch_module.float32)
    image_mask = torch_module.nn.functional.interpolate(
        inverted_source_mask,
        size=(height, width),
        mode="bilinear",
        align_corners=False,
    ).round()
    image_mask_nhwc = image_mask.movedim(1, -1).repeat(1, 1, 1, channels)
    masked_image = image * image_mask_nhwc.to(device=image.device, dtype=image.dtype)
    return masked_image, [inverted_source_mask]
