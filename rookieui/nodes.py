from __future__ import annotations

import hashlib
import logging
import math

try:
    import numpy as np
except Exception:  # pragma: no cover - import guard for thin entrypoint
    np = None

try:
    import torch
except Exception:  # pragma: no cover - import guard for thin entrypoint
    torch = None

try:
    from PIL import Image, ImageFilter, ImageOps, ImageSequence
except Exception:  # pragma: no cover - import guard for thin entrypoint
    Image = None
    ImageFilter = None
    ImageOps = None
    ImageSequence = None

from rookieui.services.asset_store import resolve_asset_path
from rookieui.services.a1111_conditioning import build_a1111_conditioning
from rookieui.services.controlnet_runtime import (
    CONTROLNET_PREPROCESSOR_OPTION_ORDER,
    normalize_module_key,
    preprocess_controlnet_tensor,
)

try:
    from comfy import model_management
except Exception:  # pragma: no cover - host-only import path
    model_management = None

_LOGGER = logging.getLogger("ComfyUI-RookieUI")


def _get_intermediate_dtype():
    if torch is None:
        return None
    if model_management is None:
        return torch.float32
    getter = getattr(model_management, "intermediate_dtype", None)
    if callable(getter):
        return getter()
    return torch.float32


def _require_runtime_dependencies() -> None:
    # CRITICAL: do not hard-import image/tensor deps at module load; RookieUI must still register routes in lean test/CI environments.
    missing = []
    if np is None:
        missing.append("numpy")
    if torch is None:
        missing.append("torch")
    if Image is None or ImageFilter is None or ImageOps is None or ImageSequence is None:
        missing.append("Pillow")
    if missing:
        raise RuntimeError(
            f"RookieUI asset nodes require {', '.join(missing)} to be installed in the active environment."
        )


def _load_image_with_alpha(path):
    _require_runtime_dependencies()
    img = Image.open(path)
    output_images = []
    output_masks = []
    width = None
    height = None
    dtype = _get_intermediate_dtype()

    for frame in ImageSequence.Iterator(img):
        frame = ImageOps.exif_transpose(frame)
        if frame.mode == "I":
            frame = frame.point(lambda value: value * (1 / 255))
        rgb_frame = frame.convert("RGB")

        if width is None:
            width, height = rgb_frame.size

        if rgb_frame.size != (width, height):
            continue

        image_array = np.array(rgb_frame).astype(np.float32) / 255.0
        image_tensor = torch.from_numpy(image_array)[None,]
        if "A" in frame.getbands():
            mask_array = np.array(frame.getchannel("A")).astype(np.float32) / 255.0
            mask_tensor = 1.0 - torch.from_numpy(mask_array)
        elif frame.mode == "P" and "transparency" in frame.info:
            mask_array = np.array(frame.convert("RGBA").getchannel("A")).astype(np.float32) / 255.0
            mask_tensor = 1.0 - torch.from_numpy(mask_array)
        else:
            mask_tensor = torch.zeros((64, 64), dtype=torch.float32, device="cpu")
        output_images.append(image_tensor.to(dtype=dtype))
        output_masks.append(mask_tensor.unsqueeze(0).to(dtype=dtype))
        if img.format == "MPO":
            break

    if len(output_images) > 1:
        return torch.cat(output_images, dim=0), torch.cat(output_masks, dim=0)
    return output_images[0], output_masks[0]


class RookieUILoadAssetImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "asset_handle": ("STRING", {"default": ""}),
            },
        }

    CATEGORY = "RookieUI/assets"
    RETURN_TYPES = ("IMAGE", "MASK")
    FUNCTION = "load_asset"

    def load_asset(self, asset_handle):
        _require_runtime_dependencies()
        path = resolve_asset_path(asset_handle)
        return _load_image_with_alpha(path)

    @classmethod
    def VALIDATE_INPUTS(cls, asset_handle):
        try:
            resolve_asset_path(asset_handle)
        except ValueError as exc:
            return str(exc)
        return True

    @classmethod
    def IS_CHANGED(cls, asset_handle):
        path = resolve_asset_path(asset_handle)
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            digest.update(stream.read())
        return digest.hexdigest()


class RookieUILoadAssetMask:
    _color_channels = ["alpha", "red", "green", "blue"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "asset_handle": ("STRING", {"default": ""}),
                "channel": (cls._color_channels,),
                "invert": ("BOOLEAN", {"default": False}),
                "blur_radius": ("INT", {"default": 0, "min": 0, "max": 64, "step": 1}),
            },
        }

    CATEGORY = "RookieUI/assets"
    RETURN_TYPES = ("MASK",)
    FUNCTION = "load_asset_mask"

    def load_asset_mask(self, asset_handle, channel, invert=False, blur_radius=0):
        _require_runtime_dependencies()
        path = resolve_asset_path(asset_handle)
        image = ImageOps.exif_transpose(Image.open(path))
        if image.getbands() != ("R", "G", "B", "A"):
            if image.mode == "I":
                image = image.point(lambda value: value * (1 / 255))
            image = image.convert("RGBA")

        color = channel[0].upper()
        if color in image.getbands():
            mask = np.array(image.getchannel(color)).astype(np.float32) / 255.0
            mask = torch.from_numpy(mask)
            if color == "A":
                # IMPORTANT: alpha channels represent transparency; invert once to convert into a denoise mask.
                mask = 1.0 - mask
        else:
            mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")

        if blur_radius > 0:
            # CRITICAL: perform blur in PIL space for deterministic, dependency-light mask smoothing across host environments.
            mask_image = Image.fromarray((mask.numpy() * 255.0).astype(np.uint8), mode="L")
            mask_image = mask_image.filter(ImageFilter.GaussianBlur(radius=int(blur_radius)))
            mask = torch.from_numpy(np.array(mask_image).astype(np.float32) / 255.0)

        if invert:
            mask = 1.0 - mask
        return (mask.unsqueeze(0),)

    @classmethod
    def VALIDATE_INPUTS(cls, asset_handle, channel="alpha", invert=False, blur_radius=0):
        # CRITICAL: ComfyUI may validate inner nodes with partial argument sets; keep mask node validation signature tolerant to missing/non-positional channel inputs.
        try:
            resolve_asset_path(asset_handle)
        except ValueError as exc:
            return str(exc)
        return True

    @classmethod
    def IS_CHANGED(cls, asset_handle, channel="alpha", invert=False, blur_radius=0):
        return RookieUILoadAssetImage.IS_CHANGED(asset_handle)


class RookieUIControlNetPreprocess:
    _module_choices = CONTROLNET_PREPROCESSOR_OPTION_ORDER
    _module_aliases = {
        "ip-adapter": "ipadapter",
        "ip_adapter": "ipadapter",
        "instant-id": "instantid",
        "instant_id": "instantid",
        "t2i-adapter": "t2iadapter",
        "t2i_adapter": "t2iadapter",
        "normal_map": "normalmap",
    }

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "module": (list(cls._module_choices),),
                "processor_res": ("INT", {"default": 512, "min": 64, "max": 2048, "step": 1}),
                "threshold_a": ("FLOAT", {"default": 64.0, "min": 0.0, "max": 255.0, "step": 0.01}),
                "threshold_b": ("FLOAT", {"default": 64.0, "min": 0.0, "max": 255.0, "step": 0.01}),
                "use_mask": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "mask": ("MASK",),
            },
        }

    CATEGORY = "RookieUI/controlnet"
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "preprocess"

    @classmethod
    def _normalize_module(cls, module_value: object) -> str:
        normalized = normalize_module_key(module_value)
        normalized = cls._module_aliases.get(normalized, normalized)
        if normalized not in cls._module_choices:
            # IMPORTANT: keep unsupported modules as passthrough instead of hard-failing generation; route-level warnings already capture downgrade semantics.
            return "none"
        return normalized

    @staticmethod
    def _normalize_mask(mask_tensor: "torch.Tensor", *, batch_size: int, height: int, width: int) -> "torch.Tensor":
        if mask_tensor.ndim == 2:
            mask_tensor = mask_tensor.unsqueeze(0)
        if mask_tensor.ndim == 4 and mask_tensor.shape[1] == 1:
            mask_tensor = mask_tensor[:, 0, :, :]
        if mask_tensor.ndim != 3:
            raise ValueError("ControlNet mask tensor must be 2D/3D (or 4D single-channel).")

        if mask_tensor.shape[0] == 1 and batch_size > 1:
            mask_tensor = mask_tensor.repeat(batch_size, 1, 1)
        elif mask_tensor.shape[0] != batch_size:
            mask_tensor = mask_tensor[:1].repeat(batch_size, 1, 1)

        resized = torch.nn.functional.interpolate(
            mask_tensor.unsqueeze(1).to(dtype=torch.float32),
            size=(height, width),
            mode="bilinear",
            align_corners=False,
        ).squeeze(1)
        return torch.clamp(resized, 0.0, 1.0)

    def preprocess(self, image, module="none", processor_res=512, threshold_a=64.0, threshold_b=64.0, use_mask=False, mask=None):
        _require_runtime_dependencies()
        module_key = self._normalize_module(module)
        runtime_mask = mask if use_mask and mask is not None else None
        runtime_result = preprocess_controlnet_tensor(
            image_tensor=image,
            module=module_key,
            processor_res=int(processor_res),
            threshold_a=float(threshold_a),
            threshold_b=float(threshold_b),
            mask_tensor=runtime_mask,
        )
        output = runtime_result.image.to(dtype=image.dtype, device=image.device)
        if runtime_result.used_fallback and runtime_result.diagnostics:
            # DEBUG HOTSPOT: when users report unexpected preprocessor outputs, inspect this log for failed host-node invocation chain before fallback.
            _LOGGER.debug(
                "RookieUIControlNetPreprocess host preprocessor fallback engaged (module=%s, diagnostics=%s).",
                module_key,
                " | ".join(runtime_result.diagnostics[:3]),
            )

        if use_mask and mask is not None:
            normalized_mask = self._normalize_mask(
                mask.detach().to(device=output.device),
                batch_size=output.shape[0],
                height=output.shape[1],
                width=output.shape[2],
            ).to(dtype=output.dtype, device=output.device)
            output = output * normalized_mask.unsqueeze(-1)

        return (output,)


class RookieUIA1111TextEncode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "dynamicPrompts": True}),
                "clip": ("CLIP",),
                "steps": ("INT", {"default": 20, "min": 1, "max": 10000, "step": 1}),
            },
        }

    CATEGORY = "RookieUI/conditioning"
    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "encode"

    def encode(self, text, clip, steps=20):
        if clip is None:
            raise RuntimeError(
                "ERROR: clip input is invalid: None\n\nIf the clip is from a checkpoint loader node your checkpoint does not contain a valid clip or text encoder model."
            )
        # CRITICAL: keep SD15 prompt semantics at the CLIP boundary here; reverting SD-family exact paths to graph-only ConditioningCombine nodes reopens BREAK/schedule drift.
        return (build_a1111_conditioning(clip, str(text), steps=int(steps)),)


class RookieUIVAEEncodeForInpaint:
    _masked_content_modes = ("fill", "original", "latent_noise", "latent_nothing")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pixels": ("IMAGE",),
                "vae": ("VAE",),
                "mask": ("MASK",),
                "grow_mask_by": ("INT", {"default": 6, "min": 0, "max": 64, "step": 1}),
                "masked_content": (cls._masked_content_modes,),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "soft_inpainting_enabled": ("BOOLEAN", {"default": False}),
                "soft_inpainting_schedule_bias": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 8.0, "step": 0.01}),
                "soft_inpainting_preservation_strength": (
                    "FLOAT",
                    {"default": 0.5, "min": 0.0, "max": 8.0, "step": 0.01},
                ),
                "soft_inpainting_transition_contrast_boost": (
                    "FLOAT",
                    {"default": 4.0, "min": 1.0, "max": 32.0, "step": 0.01},
                ),
                "soft_inpainting_mask_influence": (
                    "FLOAT",
                    {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "soft_inpainting_difference_threshold": (
                    "FLOAT",
                    {"default": 0.5, "min": 0.0, "max": 8.0, "step": 0.01},
                ),
                "soft_inpainting_difference_contrast": (
                    "FLOAT",
                    {"default": 2.0, "min": 0.0, "max": 8.0, "step": 0.01},
                ),
            },
        }

    CATEGORY = "RookieUI/latent"
    RETURN_TYPES = ("LATENT",)
    FUNCTION = "encode"

    @staticmethod
    def _apply_soft_inpainting_mask(
        mask: "torch.Tensor",
        *,
        schedule_bias: float,
        preservation_strength: float,
        transition_contrast_boost: float,
        mask_influence: float,
        difference_threshold: float,
        difference_contrast: float,
    ) -> "torch.Tensor":
        influence = float(max(0.0, min(1.0, mask_influence)))
        if influence <= 0.0:
            return mask

        threshold = float(max(0.0, min(1.0, difference_threshold / 8.0)))
        contrast = float(max(0.01, difference_contrast))
        transition = float(max(0.125, transition_contrast_boost / 4.0))
        preservation = float(max(0.0, min(1.0, preservation_strength / 8.0)))
        schedule = float(max(0.125, schedule_bias))

        transformed = torch.clamp((mask - threshold) * contrast + threshold, 0.0, 1.0)
        transformed = torch.pow(transformed, 1.0 / transition)
        blended = torch.lerp(mask, transformed, influence)
        if preservation > 0.0:
            blended = torch.lerp(blended, mask, preservation * 0.5)
        if abs(schedule - 1.0) > 1e-6:
            blended = torch.pow(torch.clamp(blended, 0.0, 1.0), 1.0 / schedule)
        return torch.clamp(blended, 0.0, 1.0)

    @staticmethod
    def _seeded_noise_like(tensor: "torch.Tensor", seed: int) -> "torch.Tensor":
        if torch is None:
            raise RuntimeError("torch is required for inpaint latent noise.")
        device = tensor.device
        device_arg = "cpu" if device.type == "cpu" else device.type
        generator = torch.Generator(device=device_arg)
        generator.manual_seed(int(seed) & 0xFFFFFFFFFFFFFFFF)
        return torch.randn(tensor.shape, generator=generator, device=device, dtype=tensor.dtype)

    def encode(
        self,
        pixels,
        vae,
        mask,
        grow_mask_by=6,
        masked_content="fill",
        seed=0,
        soft_inpainting_enabled=False,
        soft_inpainting_schedule_bias=1.0,
        soft_inpainting_preservation_strength=0.5,
        soft_inpainting_transition_contrast_boost=4.0,
        soft_inpainting_mask_influence=0.0,
        soft_inpainting_difference_threshold=0.5,
        soft_inpainting_difference_contrast=2.0,
    ):
        _require_runtime_dependencies()

        downscale_ratio = vae.spacial_compression_encode()
        x = (pixels.shape[1] // downscale_ratio) * downscale_ratio
        y = (pixels.shape[2] // downscale_ratio) * downscale_ratio
        mask = torch.nn.functional.interpolate(
            mask.reshape((-1, 1, mask.shape[-2], mask.shape[-1])),
            size=(pixels.shape[1], pixels.shape[2]),
            mode="bilinear",
        )

        pixels = pixels.clone()
        if pixels.shape[1] != x or pixels.shape[2] != y:
            x_offset = (pixels.shape[1] % downscale_ratio) // 2
            y_offset = (pixels.shape[2] % downscale_ratio) // 2
            pixels = pixels[:, x_offset : x + x_offset, y_offset : y + y_offset, :]
            mask = mask[:, :, x_offset : x + x_offset, y_offset : y + y_offset]

        if grow_mask_by == 0:
            mask_base = mask
        else:
            kernel_tensor = torch.ones((1, 1, grow_mask_by, grow_mask_by), dtype=mask.dtype, device=mask.device)
            padding = math.ceil((grow_mask_by - 1) / 2)
            mask_base = torch.clamp(torch.nn.functional.conv2d(mask.round(), kernel_tensor, padding=padding), 0, 1)

        if soft_inpainting_enabled:
            # CRITICAL: soft-inpainting controls must affect the generated noise mask; keeping them as UI-only no-ops breaks A1111 parity expectations.
            noise_mask = self._apply_soft_inpainting_mask(
                mask_base,
                schedule_bias=float(soft_inpainting_schedule_bias),
                preservation_strength=float(soft_inpainting_preservation_strength),
                transition_contrast_boost=float(soft_inpainting_transition_contrast_boost),
                mask_influence=float(soft_inpainting_mask_influence),
                difference_threshold=float(soft_inpainting_difference_threshold),
                difference_contrast=float(soft_inpainting_difference_contrast),
            )
        else:
            noise_mask = mask_base.round()

        masked_pixels = pixels.clone()
        if masked_content == "fill":
            keep_mask = (1.0 - noise_mask.round()).squeeze(1)
            for i in range(3):
                masked_pixels[:, :, :, i] -= 0.5
                masked_pixels[:, :, :, i] *= keep_mask
                masked_pixels[:, :, :, i] += 0.5
        latent = vae.encode(masked_pixels if masked_content == "fill" else pixels)

        latent_mask = torch.nn.functional.interpolate(
            noise_mask,
            size=(latent.shape[-2], latent.shape[-1]),
            mode="bilinear",
        )
        if masked_content == "latent_noise":
            noise = self._seeded_noise_like(latent, int(seed))
            latent = latent * (1.0 - latent_mask) + noise * latent_mask
        elif masked_content == "latent_nothing":
            latent = latent * (1.0 - latent_mask)

        return ({"samples": latent, "noise_mask": noise_mask[:, :, :x, :y]},)


NODE_CLASS_MAPPINGS = {
    "RookieUILoadAssetImage": RookieUILoadAssetImage,
    "RookieUILoadAssetMask": RookieUILoadAssetMask,
    "RookieUIControlNetPreprocess": RookieUIControlNetPreprocess,
    "RookieUIA1111TextEncode": RookieUIA1111TextEncode,
    "RookieUIVAEEncodeForInpaint": RookieUIVAEEncodeForInpaint,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RookieUILoadAssetImage": "RookieUI Load Asset Image",
    "RookieUILoadAssetMask": "RookieUI Load Asset Mask",
    "RookieUIControlNetPreprocess": "RookieUI ControlNet Preprocess",
    "RookieUIA1111TextEncode": "RookieUI A1111 Text Encode",
    "RookieUIVAEEncodeForInpaint": "RookieUI VAE Encode (A1111 Inpaint)",
}
