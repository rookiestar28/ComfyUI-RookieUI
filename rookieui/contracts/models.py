from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from rookieui.contracts.model_family_registry import build_primary_model_category_by_family

PRIMARY_MODEL_CATEGORY_BY_FAMILY: dict[str, str] = build_primary_model_category_by_family()


@dataclass(frozen=True)
class ModelInventorySnapshot:
    source: str
    checkpoints: list[str] = field(default_factory=list)
    clip: list[str] = field(default_factory=list)
    clip_vision: list[str] = field(default_factory=list)
    controlnet: list[str] = field(default_factory=list)
    diffusion_models: list[str] = field(default_factory=list)
    vae: list[str] = field(default_factory=list)
    text_encoders: list[str] = field(default_factory=list)
    embeddings: list[str] = field(default_factory=list)
    loras: list[str] = field(default_factory=list)
    ultralytics: list[str] = field(default_factory=list)
    ultralytics_bbox: list[str] = field(default_factory=list)
    ultralytics_segm: list[str] = field(default_factory=list)
    unet: list[str] = field(default_factory=list)
    upscale_models: list[str] = field(default_factory=list)
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
                        "ultralytics",
                        "ultralytics_bbox",
                        "ultralytics_segm",
                    ],
                },
            ],
            "primary_model_category_by_family": dict(PRIMARY_MODEL_CATEGORY_BY_FAMILY),
            "categories": {
                "checkpoints": {
                    "title": "Checkpoints",
                    "items": self.checkpoints,
                    "default_value": self.default_checkpoint,
                    "sidebar_visible": True,
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
                "controlnet": {
                    "title": "ControlNet",
                    "items": self.controlnet,
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
                "loras": {
                    "title": "LoRAs",
                    "items": self.loras,
                    "default_value": "",
                    "sidebar_visible": True,
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
    width: int
    height: int
    steps: int
    cfg_scale: float
    sampler_name: str
    scheduler_name: str
    clip_skip: int
    shift: float | None = None
    flux_guidance: float | None = None
    prompt_enhancement_enabled: bool = False
    edit_megapixels: float | None = None

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)
