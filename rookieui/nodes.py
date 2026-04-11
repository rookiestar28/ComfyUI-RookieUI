from __future__ import annotations

import hashlib
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

try:
    from comfy import model_management
except Exception:  # pragma: no cover - host-only import path
    model_management = None


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
    "RookieUIVAEEncodeForInpaint": RookieUIVAEEncodeForInpaint,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RookieUILoadAssetImage": "RookieUI Load Asset Image",
    "RookieUILoadAssetMask": "RookieUI Load Asset Mask",
    "RookieUIVAEEncodeForInpaint": "RookieUI VAE Encode (A1111 Inpaint)",
}
