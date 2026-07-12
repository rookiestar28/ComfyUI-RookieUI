from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from rookieui.contracts.model_family_registry import build_primary_model_category_by_family

PRIMARY_MODEL_CATEGORY_BY_FAMILY: dict[str, str] = build_primary_model_category_by_family()


@dataclass(frozen=True)
class ModelInventorySnapshot:
    source: str
    audio_encoders: list[str] = field(default_factory=list)
    background_removal: list[str] = field(default_factory=list)
    checkpoints: list[str] = field(default_factory=list)
    classifiers: list[str] = field(default_factory=list)
    clip: list[str] = field(default_factory=list)
    clip_vision: list[str] = field(default_factory=list)
    configs: list[str] = field(default_factory=list)
    controlnet: list[str] = field(default_factory=list)
    detection: list[str] = field(default_factory=list)
    diffusers: list[str] = field(default_factory=list)
    diffusion_models: list[str] = field(default_factory=list)
    vae: list[str] = field(default_factory=list)
    text_encoders: list[str] = field(default_factory=list)
    embeddings: list[str] = field(default_factory=list)
    frame_interpolation: list[str] = field(default_factory=list)
    geometry_estimation: list[str] = field(default_factory=list)
    gligen: list[str] = field(default_factory=list)
    hypernetworks: list[str] = field(default_factory=list)
    latent_upscale_models: list[str] = field(default_factory=list)
    loras: list[str] = field(default_factory=list)
    model_patches: list[str] = field(default_factory=list)
    optical_flow: list[str] = field(default_factory=list)
    photomaker: list[str] = field(default_factory=list)
    style_models: list[str] = field(default_factory=list)
    ultralytics: list[str] = field(default_factory=list)
    ultralytics_bbox: list[str] = field(default_factory=list)
    ultralytics_segm: list[str] = field(default_factory=list)
    unet: list[str] = field(default_factory=list)
    upscale_models: list[str] = field(default_factory=list)
    vae_approx: list[str] = field(default_factory=list)
    default_checkpoint: str = "__host_default__"
    default_vae: str = "Automatic"
    default_text_encoder: str = "Automatic"

    def build_catalog_payload(self) -> dict[str, Any]:
        return {
            "surface_groups": [
                {
                    "id": "sd_generation",
                    "title": "SD Generation",
                    "categories": [
                        "checkpoints",
                        "vae",
                        "text_encoders",
                        "embeddings",
                        "loras",
                    ],
                },
                {
                    "id": "conditioning",
                    "title": "Conditioning",
                    "categories": [
                        "clip",
                        "clip_vision",
                        "controlnet",
                    ],
                },
                {
                    "id": "diffusion",
                    "title": "Diffusion Backends",
                    "categories": [
                        "diffusion_models",
                        "unet",
                    ],
                },
                {
                    "id": "extras",
                    "title": "Postprocessing",
                    "categories": [
                        "upscale_models",
                        "latent_upscale_models",
                        "background_removal",
                        "ultralytics",
                        "ultralytics_bbox",
                        "ultralytics_segm",
                    ],
                },
                {
                    "id": "host_diagnostics",
                    "title": "Host Diagnostics",
                    "categories": [
                        "audio_encoders",
                        "classifiers",
                        "configs",
                        "detection",
                        "diffusers",
                        "frame_interpolation",
                        "geometry_estimation",
                        "gligen",
                        "hypernetworks",
                        "model_patches",
                        "optical_flow",
                        "photomaker",
                        "style_models",
                        "vae_approx",
                    ],
                },
            ],
            "primary_model_category_by_family": dict(PRIMARY_MODEL_CATEGORY_BY_FAMILY),
            "categories": {
                "audio_encoders": {
                    "title": "Audio Encoders",
                    "items": self.audio_encoders,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "checkpoints": {
                    "title": "Checkpoints",
                    "items": self.checkpoints,
                    "default_value": self.default_checkpoint,
                    "sidebar_visible": True,
                },
                "background_removal": {
                    "title": "Background Removal",
                    "items": self.background_removal,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "classifiers": {
                    "title": "Classifiers",
                    "items": self.classifiers,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "clip": {
                    "title": "CLIP",
                    "items": self.clip,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "clip_vision": {
                    "title": "CLIP Vision",
                    "items": self.clip_vision,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "configs": {
                    "title": "Configs",
                    "items": self.configs,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "controlnet": {
                    "title": "ControlNet",
                    "items": self.controlnet,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "detection": {
                    "title": "Detection",
                    "items": self.detection,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "diffusers": {
                    "title": "Diffusers",
                    "items": self.diffusers,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "diffusion_models": {
                    "title": "Diffusion Models",
                    "items": self.diffusion_models,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "embeddings": {
                    "title": "Embeddings",
                    "items": self.embeddings,
                    "default_value": "",
                    "sidebar_visible": True,
                },
                "frame_interpolation": {
                    "title": "Frame Interpolation",
                    "items": self.frame_interpolation,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "geometry_estimation": {
                    "title": "Geometry Estimation",
                    "items": self.geometry_estimation,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "gligen": {
                    "title": "GLIGEN",
                    "items": self.gligen,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "hypernetworks": {
                    "title": "Hypernetworks",
                    "items": self.hypernetworks,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "loras": {
                    "title": "LoRAs",
                    "items": self.loras,
                    "default_value": "",
                    "sidebar_visible": True,
                },
                "latent_upscale_models": {
                    "title": "Latent Upscale Models",
                    "items": self.latent_upscale_models,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "model_patches": {
                    "title": "Model Patches",
                    "items": self.model_patches,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "optical_flow": {
                    "title": "Optical Flow",
                    "items": self.optical_flow,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "photomaker": {
                    "title": "PhotoMaker",
                    "items": self.photomaker,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "style_models": {
                    "title": "Style Models",
                    "items": self.style_models,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "text_encoders": {
                    "title": "Text Encoders",
                    "items": self.text_encoders,
                    "default_value": self.default_text_encoder,
                    "sidebar_visible": True,
                },
                "ultralytics": {
                    "title": "Ultralytics",
                    "items": self.ultralytics,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "ultralytics_bbox": {
                    "title": "Ultralytics BBox",
                    "items": self.ultralytics_bbox,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "ultralytics_segm": {
                    "title": "Ultralytics Segm",
                    "items": self.ultralytics_segm,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "unet": {
                    "title": "UNet",
                    "items": self.unet,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "upscale_models": {
                    "title": "Upscale Models",
                    "items": self.upscale_models,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "vae_approx": {
                    "title": "VAE Approx",
                    "items": self.vae_approx,
                    "default_value": "",
                    "sidebar_visible": False,
                },
                "vae": {
                    "title": "VAE",
                    "items": self.vae,
                    "default_value": self.default_vae,
                    "sidebar_visible": True,
                },
            },
        }

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["catalog"] = self.build_catalog_payload()
        return payload


@dataclass(frozen=True)
class PresetDefinition:
    id: str
    title: str
    profile: str
    base_family: str
    checkpoint_name: str
    vae_name: str
    text_encoder_name: str
    template_lora_name: str
    template_lora_enabled: bool
    template_lora_strength: float
    template_lora_trigger_word: str
    width: int
    height: int
    steps: int
    cfg_scale: float
    sampler_name: str
    scheduler_name: str
    clip_skip: int
    scheduler_control_mode: str = "generic"
    negative_prompt_mode: str = "encoded"
    shift: float | None = None
    flux_guidance: float | None = None
    prompt_enhancement_enabled: bool = False
    edit_megapixels: float | None = None
    image_edit_profile: bool = False
    request_contract_surface: str = ""
    reference_input_mode: str = "none"
    max_direct_references: int = 0
    encoder_family: str = ""
    template_lora_chain_mode: str = "none"
    ideogram_mode: str = ""

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)
