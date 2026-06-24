from __future__ import annotations

import hashlib
import json
import logging
import math
import os

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
    from PIL.PngImagePlugin import PngInfo
except Exception:  # pragma: no cover - import guard for thin entrypoint
    Image = None
    ImageFilter = None
    ImageOps = None
    ImageSequence = None
    PngInfo = None

from rookieui.services.asset_store import resolve_asset_path
from rookieui.services.adetailer_runtime import detect_adetailer_mask
from rookieui.services.controlnet_runtime import (
    CONTROLNET_PREPROCESSOR_OPTION_ORDER,
    normalize_module_key,
    preprocess_controlnet_tensor,
)
from rookieui.services.controlnet_advanced_runtime import (
    build_controlnet_stage_weights,
)
from rookieui.services.prompt_dsl import normalize_prompt_attention_for_weighted_encode
from rookieui.services.a1111_prompt_encoding import (
    A1111PromptEncodingOptions,
    PROMPT_PARSER_MODE_OPTIONS,
    encode_a1111_prompt_conditioning,
    encode_a1111_prompt_text_conditioning,
    encode_a1111_sdxl_prompt_conditioning,
    encode_a1111_sdxl_prompt_text_conditioning,
)
from rookieui.services.prompt_token_rebatch import (
    tokenize_channel_with_rookieui_rebatch,
    tokenize_with_rookieui_rebatch,
)

try:
    from comfy import model_management
except Exception:  # pragma: no cover - host-only import path
    model_management = None

try:
    import folder_paths
except Exception:  # pragma: no cover - host-only import path
    folder_paths = None

try:
    from comfy.cli_args import args as comfy_args
except Exception:  # pragma: no cover - host-only import path
    comfy_args = None

try:
    from comfy.controlnet import ControlBase
except Exception:  # pragma: no cover - host-only import path
    ControlBase = None

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


def _require_save_image_dependencies() -> None:
    missing = []
    if np is None:
        missing.append("numpy")
    if Image is None or PngInfo is None:
        missing.append("Pillow")
    if folder_paths is None:
        missing.append("ComfyUI folder_paths")
    if missing:
        raise RuntimeError(
            f"RookieUI save node requires {', '.join(missing)} to be installed in the active ComfyUI environment."
        )


def _metadata_disabled() -> bool:
    return bool(getattr(comfy_args, "disable_metadata", False))


def _require_tensor_dependency() -> None:
    if torch is None:
        raise RuntimeError("RookieUI tensor nodes require torch to be installed in the active environment.")


def _require_clip_input(clip) -> None:
    if clip is None:
        raise RuntimeError(
            "RookieUI prompt encode received an invalid clip input. "
            "If the clip comes from a checkpoint loader, the active host model may not expose a valid text encoder."
        )


class RookieUIA1111CLIPTextEncode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "dynamicPrompts": True}),
                "clip": ("CLIP",),
            },
            "optional": {
                "steps": ("INT", {"default": 10, "min": 1, "max": 10000}),
                "a1111_engine": (["parity", "text_only", "legacy"],),
                "parser": (list(PROMPT_PARSER_MODE_OPTIONS),),
                "embedding_directory": ("STRING", {"default": ""}),
                "embedding_names": ("STRING", {"multiline": True, "default": ""}),
                "mean_normalization": ("BOOLEAN", {"default": True}),
                "use_old_emphasis_implementation": ("BOOLEAN", {"default": False}),
            },
        }

    CATEGORY = "RookieUI/conditioning"
    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "encode"

    def encode(
        self,
        clip,
        text,
        steps=10,
        a1111_engine="parity",
        parser="A1111",
        embedding_directory="",
        embedding_names="",
        mean_normalization=True,
        use_old_emphasis_implementation=False,
    ):
        _require_clip_input(clip)
        engine_mode = str(a1111_engine or "parity").strip().lower()
        options = A1111PromptEncodingOptions(
            step_count=int(steps or 10),
            mean_normalization=bool(mean_normalization),
            use_old_emphasis_implementation=bool(use_old_emphasis_implementation),
            parser_mode=parser,
            embedding_names=str(embedding_names or ""),
            embedding_directory=str(embedding_directory or ""),
        )
        if engine_mode == "text_only":
            # IMPORTANT: workflow compiler sends pre-sliced prompt text with text_only to avoid nested A1111 schedule/AND/BREAK compilation.
            return (
                encode_a1111_prompt_text_conditioning(
                    clip,
                    text,
                    tokenizer=tokenize_with_rookieui_rebatch,
                    options=options,
                ),
            )
        if engine_mode != "legacy":
            return (
                encode_a1111_prompt_conditioning(
                    clip,
                    text,
                    tokenizer=tokenize_with_rookieui_rebatch,
                    options=options,
                ),
            )
        normalized_text = normalize_prompt_attention_for_weighted_encode(text)
        tokens = tokenize_with_rookieui_rebatch(clip, normalized_text)
        return (clip.encode_from_tokens_scheduled(tokens),)


class RookieUIA1111CLIPTextEncodeSDXL:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                "width": ("INT", {"default": 1024, "min": 0, "max": 16384}),
                "height": ("INT", {"default": 1024, "min": 0, "max": 16384}),
                "crop_w": ("INT", {"default": 0, "min": 0, "max": 16384}),
                "crop_h": ("INT", {"default": 0, "min": 0, "max": 16384}),
                "target_width": ("INT", {"default": 1024, "min": 0, "max": 16384}),
                "target_height": ("INT", {"default": 1024, "min": 0, "max": 16384}),
                "text_g": ("STRING", {"multiline": True, "dynamicPrompts": True}),
                "text_l": ("STRING", {"multiline": True, "dynamicPrompts": True}),
            },
            "optional": {
                "steps": ("INT", {"default": 10, "min": 1, "max": 10000}),
                "a1111_engine": (["parity", "text_only", "legacy"],),
                "parser": (list(PROMPT_PARSER_MODE_OPTIONS),),
                "embedding_directory": ("STRING", {"default": ""}),
                "embedding_names": ("STRING", {"multiline": True, "default": ""}),
                "mean_normalization": ("BOOLEAN", {"default": True}),
                "use_old_emphasis_implementation": ("BOOLEAN", {"default": False}),
            },
        }

    CATEGORY = "RookieUI/conditioning"
    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "encode"

    @staticmethod
    def _tokenize_sdxl_pair(clip, text_g: str, text_l: str):
        tokens_g = tokenize_channel_with_rookieui_rebatch(clip, text_g, channel_key="g")
        tokens_l = tokenize_channel_with_rookieui_rebatch(clip, text_l, channel_key="l")
        if not isinstance(tokens_g, list) or not isinstance(tokens_l, list):
            raise RuntimeError("RookieUI SDXL prompt encode requires a dual-token CLIP payload.")
        tokens = {"g": tokens_g, "l": tokens_l}
        empty = clip.tokenize("")
        while len(tokens["l"]) < len(tokens["g"]):
            tokens["l"] += empty["l"]
        while len(tokens["l"]) > len(tokens["g"]):
            tokens["g"] += empty["g"]
        return tokens

    def encode(
        self,
        clip,
        width,
        height,
        crop_w,
        crop_h,
        target_width,
        target_height,
        text_g,
        text_l,
        steps=10,
        a1111_engine="parity",
        parser="A1111",
        embedding_directory="",
        embedding_names="",
        mean_normalization=True,
        use_old_emphasis_implementation=False,
    ):
        _require_clip_input(clip)
        add_dict = {
            "width": width,
            "height": height,
            "crop_w": crop_w,
            "crop_h": crop_h,
            "target_width": target_width,
            "target_height": target_height,
        }
        engine_mode = str(a1111_engine or "parity").strip().lower()
        options = A1111PromptEncodingOptions(
            step_count=int(steps or 10),
            mean_normalization=bool(mean_normalization),
            use_old_emphasis_implementation=bool(use_old_emphasis_implementation),
            parser_mode=parser,
            embedding_names=str(embedding_names or ""),
            embedding_directory=str(embedding_directory or ""),
        )
        if engine_mode == "text_only":
            # IMPORTANT: workflow compiler sends pre-sliced prompt text with text_only to avoid nested A1111 schedule/AND/BREAK compilation.
            return (
                encode_a1111_sdxl_prompt_text_conditioning(
                    clip,
                    text_g=text_g,
                    text_l=text_l,
                    tokenizer=type(self)._tokenize_sdxl_pair,
                    options=options,
                    add_dict=add_dict,
                ),
            )
        if engine_mode != "legacy":
            return (
                encode_a1111_sdxl_prompt_conditioning(
                    clip,
                    text_g=text_g,
                    text_l=text_l,
                    tokenizer=type(self)._tokenize_sdxl_pair,
                    options=options,
                    add_dict=add_dict,
                ),
            )
        normalized_text_g = normalize_prompt_attention_for_weighted_encode(text_g)
        normalized_text_l = normalize_prompt_attention_for_weighted_encode(text_l)
        tokens = type(self)._tokenize_sdxl_pair(clip, normalized_text_g, normalized_text_l)
        return (
            clip.encode_from_tokens_scheduled(
                tokens,
                add_dict=add_dict,
            ),
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
                "pixel_perfect": ("BOOLEAN", {"default": False}),
                "target_width": ("INT", {"default": 512, "min": 64, "max": 8192, "step": 1}),
                "target_height": ("INT", {"default": 512, "min": 64, "max": 8192, "step": 1}),
                "resize_mode": (["crop_and_resize", "just_resize", "resize_and_fill"],),
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

    def preprocess(
        self,
        image,
        module="none",
        processor_res=512,
        threshold_a=64.0,
        threshold_b=64.0,
        pixel_perfect=False,
        target_width=512,
        target_height=512,
        resize_mode="crop_and_resize",
        use_mask=False,
        mask=None,
    ):
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
            pixel_perfect=bool(pixel_perfect),
            target_width=int(target_width),
            target_height=int(target_height),
            resize_mode=str(resize_mode or "crop_and_resize"),
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


class _RookieUIStageWeightedControlNet(ControlBase if ControlBase is not None else object):
    def __init__(self, base_control, *, weight_preset: str, layer_weights: list[float]) -> None:
        if ControlBase is None:  # pragma: no cover - guarded by apply node runtime check
            raise RuntimeError("ComfyUI controlnet runtime is unavailable in this environment.")
        super().__init__()
        self.base_control = base_control
        self.weight_preset = str(weight_preset or "balanced").strip().lower() or "balanced"
        self.layer_weights = [round(float(value), 4) for value in list(layer_weights or [])]
        self.latent_format = getattr(base_control, "latent_format", None)
        self.global_average_pooling = getattr(base_control, "global_average_pooling", False)
        self.compression_ratio = getattr(base_control, "compression_ratio", 8)
        self.upscale_algorithm = getattr(base_control, "upscale_algorithm", "nearest-exact")
        self.extra_args = getattr(base_control, "extra_args", {}).copy()
        self.extra_conds = list(getattr(base_control, "extra_conds", []))
        self.strength_type = getattr(base_control, "strength_type", None)
        self.concat_mask = getattr(base_control, "concat_mask", False)
        self.preprocess_image = getattr(base_control, "preprocess_image", lambda image: image)

    def copy(self):
        return type(self)(
            self.base_control.copy(),
            weight_preset=self.weight_preset,
            layer_weights=self.layer_weights,
        )

    def set_cond_hint(self, cond_hint, strength=1.0, timestep_percent_range=(0.0, 1.0), vae=None, extra_concat=[]):
        self.base_control.set_cond_hint(
            cond_hint,
            strength=strength,
            timestep_percent_range=timestep_percent_range,
            vae=vae,
            extra_concat=extra_concat,
        )
        return self

    def set_previous_controlnet(self, controlnet):
        self.previous_controlnet = controlnet
        return self

    def pre_run(self, model, percent_to_timestep_function):
        self.base_control.pre_run(model, percent_to_timestep_function)
        if self.previous_controlnet is not None:
            self.previous_controlnet.pre_run(model, percent_to_timestep_function)

    def cleanup(self):
        self.base_control.cleanup()
        if self.previous_controlnet is not None:
            self.previous_controlnet.cleanup()

    def get_models(self):
        out = list(self.base_control.get_models())
        if self.previous_controlnet is not None:
            out += self.previous_controlnet.get_models()
        return out

    def get_extra_hooks(self):
        out = list(self.base_control.get_extra_hooks())
        if self.previous_controlnet is not None:
            out += self.previous_controlnet.get_extra_hooks()
        return out

    def inference_memory_requirements(self, dtype):
        requirements = self.base_control.inference_memory_requirements(dtype)
        if self.previous_controlnet is not None:
            requirements += self.previous_controlnet.inference_memory_requirements(dtype)
        return requirements

    def _scale_control_outputs(self, control: dict[str, list["torch.Tensor"]] | None):
        if control is None:
            return None
        stage_weights = build_controlnet_stage_weights(
            input_count=len(list(control.get("input", []))),
            middle_count=len(list(control.get("middle", []))),
            output_count=len(list(control.get("output", []))),
            weight_preset=self.weight_preset,
            layer_weights=self.layer_weights,
        )
        scaled: dict[str, list["torch.Tensor" | None]] = {"input": [], "middle": [], "output": []}
        for key in ("input", "middle", "output"):
            weight_values = list(stage_weights.get(key, []))
            for index, value in enumerate(list(control.get(key, []))):
                if value is None:
                    scaled[key].append(None)
                    continue
                weight = float(weight_values[index]) if index < len(weight_values) else 1.0
                if abs(weight - 1.0) <= 1e-6:
                    scaled[key].append(value)
                    continue
                scaled[key].append(value * weight)
        return scaled

    def get_control(self, x_noisy, t, cond, batched_number, transformer_options):
        control_prev = None
        if self.previous_controlnet is not None:
            control_prev = self.previous_controlnet.get_control(x_noisy, t, cond, batched_number, transformer_options)

        self.base_control.previous_controlnet = None
        control = self.base_control.get_control(x_noisy, t, cond, batched_number, transformer_options)
        if control is None:
            return control_prev
        return self.control_merge(self._scale_control_outputs(control), control_prev, output_dtype=None)


class RookieUIControlNetApplyNativeAdvanced:
    _weight_presets = ("balanced", "soft", "strong")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "control_net": ("CONTROL_NET",),
                "image": ("IMAGE",),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01}),
                "start_percent": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.001}),
                "end_percent": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.001}),
                "weight_preset": (list(cls._weight_presets),),
                "layer_weights_json": ("STRING", {"default": "[]"}),
                "mask_aware_apply": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "mask_optional": ("MASK",),
                "vae_optional": ("VAE",),
            },
        }

    CATEGORY = "RookieUI/controlnet"
    RETURN_TYPES = ("CONDITIONING", "CONDITIONING")
    RETURN_NAMES = ("positive", "negative")
    FUNCTION = "apply_controlnet"

    @staticmethod
    def _require_controlnet_runtime() -> None:
        if ControlBase is None:
            raise RuntimeError("RookieUI advanced ControlNet apply requires a live ComfyUI controlnet runtime.")
        if torch is None:
            raise RuntimeError("RookieUI advanced ControlNet apply requires torch to be installed.")

    @staticmethod
    def _parse_layer_weights(raw_layer_weights: str) -> list[float]:
        text = str(raw_layer_weights or "").strip()
        if not text:
            return []
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("layer_weights_json must be valid JSON.") from exc
        if payload in (None, ""):
            return []
        if not isinstance(payload, list):
            raise ValueError("layer_weights_json must decode to an array.")
        return [round(float(value), 4) for value in payload]

    @staticmethod
    def _normalize_mask(mask):
        if mask is None:
            return None
        mask = mask.clone()
        if len(mask.shape) < 3:
            mask = mask.unsqueeze(0)
        return torch.clamp(mask, 0.0, 1.0)

    def apply_controlnet(
        self,
        positive,
        negative,
        control_net,
        image,
        strength,
        start_percent,
        end_percent,
        weight_preset="balanced",
        layer_weights_json="[]",
        mask_aware_apply=False,
        mask_optional=None,
        vae_optional=None,
    ):
        self._require_controlnet_runtime()
        if strength == 0:
            return (positive, negative)

        layer_weights = self._parse_layer_weights(layer_weights_json)
        control_hint = image.movedim(-1, 1)
        normalized_mask = self._normalize_mask(mask_optional) if mask_aware_apply else None
        cnets = {}
        out = []

        for conditioning in [positive, negative]:
            conditioned = []
            if conditioning is not None:
                for token, conditioning_state in conditioning:
                    cloned_state = conditioning_state.copy()
                    prev_cnet = cloned_state.get("control", None)
                    if prev_cnet in cnets:
                        c_net = cnets[prev_cnet]
                    else:
                        if control_net is None:
                            raise RuntimeError("control_net is None; ControlNet loader failed before advanced apply.")
                        c_net = control_net.copy()
                        if layer_weights or str(weight_preset).strip().lower() != "balanced":
                            c_net = _RookieUIStageWeightedControlNet(
                                c_net,
                                weight_preset=str(weight_preset).strip().lower(),
                                layer_weights=layer_weights,
                            )
                        c_net = c_net.set_cond_hint(
                            control_hint,
                            float(strength),
                            (float(start_percent), float(end_percent)),
                            vae=vae_optional,
                        )
                        c_net.set_previous_controlnet(prev_cnet)
                        cnets[prev_cnet] = c_net

                    cloned_state["control"] = c_net
                    cloned_state["control_apply_to_uncond"] = False
                    if normalized_mask is not None:
                        # IMPORTANT: mask-aware apply must stay attached only to the ControlNet-conditioned entries.
                        # Promoting this to a broader conditioning mutation leaks the mask into unrelated prompt lanes.
                        cloned_state["mask"] = normalized_mask
                        cloned_state["mask_strength"] = 1.0
                        cloned_state["set_area_to_bounds"] = False
                    conditioned.append([token, cloned_state])
            out.append(conditioned)
        return (out[0], out[1])


class RookieUIADetailerDetectMask:
    _mask_filter_methods = ("Area", "Confidence")
    _mask_merge_modes = ("None", "Merge", "Merge and Invert")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "detector": ("STRING", {"default": "None"}),
                "detector_family": ("STRING", {"default": "none"}),
                "detector_classes": ("STRING", {"default": ""}),
                "confidence": ("FLOAT", {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.01}),
                "mask_filter_method": (cls._mask_filter_methods,),
                "mask_k": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1}),
                "mask_min_ratio": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "mask_max_ratio": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "x_offset": ("INT", {"default": 0, "min": -2048, "max": 2048, "step": 1}),
                "y_offset": ("INT", {"default": 0, "min": -2048, "max": 2048, "step": 1}),
                "dilate_erode": ("INT", {"default": 4, "min": -128, "max": 128, "step": 1}),
                "mask_merge_mode": (cls._mask_merge_modes,),
                "mask_blur": ("INT", {"default": 4, "min": 0, "max": 64, "step": 1}),
            },
        }

    CATEGORY = "RookieUI/adetailer"
    RETURN_TYPES = ("MASK",)
    FUNCTION = "detect"

    @staticmethod
    def _apply_mask_morphology(mask: "torch.Tensor", dilate_erode: int) -> "torch.Tensor":
        radius = abs(int(dilate_erode))
        if radius <= 0:
            return mask
        kernel = max(1, radius * 2 + 1)
        source = mask.unsqueeze(1)
        if dilate_erode > 0:
            result = torch.nn.functional.max_pool2d(source, kernel_size=kernel, stride=1, padding=radius)
        else:
            result = 1.0 - torch.nn.functional.max_pool2d(1.0 - source, kernel_size=kernel, stride=1, padding=radius)
        return torch.clamp(result.squeeze(1), 0.0, 1.0)

    @staticmethod
    def _apply_mask_blur(mask: "torch.Tensor", blur_radius: int) -> "torch.Tensor":
        radius = int(blur_radius)
        if radius <= 0:
            return mask
        kernel = max(1, radius * 2 + 1)
        blurred = torch.nn.functional.avg_pool2d(
            mask.unsqueeze(1),
            kernel_size=kernel,
            stride=1,
            padding=radius,
        ).squeeze(1)
        return torch.clamp(blurred, 0.0, 1.0)

    def detect(
        self,
        image,
        detector="None",
        detector_family="none",
        detector_classes="",
        confidence=0.3,
        mask_filter_method="Area",
        mask_k=0,
        mask_min_ratio=0.0,
        mask_max_ratio=1.0,
        x_offset=0,
        y_offset=0,
        dilate_erode=4,
        mask_merge_mode="None",
        mask_blur=4,
    ):
        _require_tensor_dependency()
        if image.ndim != 4:
            raise ValueError("ADetailer detector image tensor must be NHWC.")

        detector_key = str(detector or "").strip()
        batch_size, height, width = int(image.shape[0]), int(image.shape[1]), int(image.shape[2])
        if not detector_key or detector_key.lower() == "none":
            return (torch.zeros((batch_size, height, width), dtype=image.dtype, device=image.device),)

        # IMPORTANT: this node is the detector-mask seam used by the graph translator;
        # do not bypass the runtime service or ADetailer silently collapses back into a no-op.
        detector_result = detect_adetailer_mask(
            image,
            detector=detector_key,
            detector_family=str(detector_family),
            detector_classes=str(detector_classes),
            confidence=float(confidence),
            x_offset=int(x_offset),
            y_offset=int(y_offset),
        )
        mask = detector_result.mask

        mask_area = float(mask[0].mean().item()) if batch_size else 0.0
        min_ratio = max(0.0, min(1.0, float(mask_min_ratio)))
        max_ratio = max(min_ratio, min(1.0, float(mask_max_ratio)))
        if mask_area < min_ratio or mask_area > max_ratio:
            _LOGGER.debug(
                "RookieUI ADetailer mask filtered by ratio (detector=%s, area=%.4f, min=%.4f, max=%.4f).",
                detector_key,
                mask_area,
                min_ratio,
                max_ratio,
            )
            return (torch.zeros_like(mask),)

        mask = self._apply_mask_morphology(mask, int(dilate_erode))
        mask = self._apply_mask_blur(mask, int(mask_blur))
        if str(mask_merge_mode or "").strip().lower() == "merge and invert":
            mask = 1.0 - mask
        return (torch.clamp(mask, 0.0, 1.0),)


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


class RookieUISaveImageWithMetadata:
    def __init__(self) -> None:
        self.output_dir = folder_paths.get_output_directory() if folder_paths is not None else ""
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "RookieUI"}),
                "parameters": ("STRING", {"default": "", "multiline": True}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    # IMPORTANT: keep aligned with host SaveImage so output-node pass-through chains keep working.
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "RookieUI/output"

    def save_images(
        self,
        images,
        filename_prefix="RookieUI",
        parameters="",
        prompt=None,
        extra_pnginfo=None,
    ):
        _require_save_image_dependencies()
        filename_prefix = str(filename_prefix or "RookieUI") + self.prefix_append
        full_output_folder, filename, counter, subfolder, _filename_prefix = folder_paths.get_save_image_path(
            filename_prefix,
            self.output_dir,
            images[0].shape[1],
            images[0].shape[0],
        )
        results = []
        for batch_number, image in enumerate(images):
            array = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))
            metadata = None
            if not _metadata_disabled():
                metadata = PngInfo()
                infotext = str(parameters or "").replace("\x00", "").strip()
                if infotext:
                    # CRITICAL: A1111 expects `parameters` as raw infotext; ComfyUI SaveImage JSON-quotes all extra_pnginfo values.
                    metadata.add_text("parameters", infotext)
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if isinstance(extra_pnginfo, dict):
                    for key, value in extra_pnginfo.items():
                        metadata_key = str(key or "").strip()
                        if not metadata_key or metadata_key == "parameters":
                            continue
                        metadata.add_text(metadata_key, json.dumps(value))

            filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
            file = f"{filename_with_batch_num}_{counter:05}_.png"
            img.save(
                os.path.join(full_output_folder, file),
                pnginfo=metadata,
                compress_level=self.compress_level,
            )
            results.append(
                {
                    "filename": file,
                    "subfolder": subfolder,
                    "type": self.type,
                }
            )
            counter += 1
        return {"ui": {"images": results}, "result": (images,)}


NODE_CLASS_MAPPINGS = {
    "RookieUIA1111CLIPTextEncode": RookieUIA1111CLIPTextEncode,
    "RookieUIA1111CLIPTextEncodeSDXL": RookieUIA1111CLIPTextEncodeSDXL,
    "RookieUILoadAssetImage": RookieUILoadAssetImage,
    "RookieUILoadAssetMask": RookieUILoadAssetMask,
    "RookieUIControlNetPreprocess": RookieUIControlNetPreprocess,
    "RookieUIControlNetApplyNativeAdvanced": RookieUIControlNetApplyNativeAdvanced,
    "RookieUIADetailerDetectMask": RookieUIADetailerDetectMask,
    "RookieUIVAEEncodeForInpaint": RookieUIVAEEncodeForInpaint,
    "RookieUISaveImageWithMetadata": RookieUISaveImageWithMetadata,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RookieUIA1111CLIPTextEncode": "RookieUI A1111 CLIP Text Encode",
    "RookieUIA1111CLIPTextEncodeSDXL": "RookieUI A1111 CLIP Text Encode SDXL",
    "RookieUILoadAssetImage": "RookieUI Load Asset Image",
    "RookieUILoadAssetMask": "RookieUI Load Asset Mask",
    "RookieUIControlNetPreprocess": "RookieUI ControlNet Preprocess",
    "RookieUIControlNetApplyNativeAdvanced": "RookieUI ControlNet Apply (Advanced)",
    "RookieUIADetailerDetectMask": "RookieUI ADetailer Detect Mask",
    "RookieUIVAEEncodeForInpaint": "RookieUI VAE Encode (A1111 Inpaint)",
    "RookieUISaveImageWithMetadata": "RookieUI Save Image With Metadata",
}
