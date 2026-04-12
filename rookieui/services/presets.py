from __future__ import annotations

from rookieui.contracts.models import PresetDefinition
from rookieui.services.model_inventory import (
    discover_model_inventory,
    resolve_primary_model_selector_context,
    resolve_text_encoder_selector_context,
    resolve_vae_selector_context,
)
from rookieui.services.parity_matrix import get_parity_profile

_UI_PRESET_BLUEPRINTS: tuple[dict[str, object], ...] = (
    {
        "id": "sd15",
        "title": "SD1.5",
        "profile": "sd15",
        "base_family": "sd15",
    },
    {
        "id": "sdxl",
        "title": "SDXL",
        "profile": "sdxl",
        "base_family": "sdxl",
    },
    {
        "id": "flux",
        "title": "Flux",
        "profile": "flux",
        "base_family": "flux",
        "width": 896,
        "height": 1152,
        "steps": 20,
        "cfg_scale": 1.0,
        "sampler_name": "euler",
        "scheduler_name": "beta",
    },
    {
        "id": "qwen_image",
        "title": "Qwen-Image",
        "profile": "qwen_image",
        "base_family": "qwen_image",
        # CRITICAL: keep UI preset aligned with non-Lightning baseline because RookieUI does not auto-attach acceleration LoRA.
        "width": 1328,
        "height": 1328,
        "steps": 50,
        "cfg_scale": 4.0,
        "sampler_name": "euler",
        "scheduler_name": "simple",
    },
    {
        "id": "klein",
        "title": "Klein",
        "profile": "klein",
        "base_family": "klein",
        "width": 896,
        "height": 1152,
        "steps": 20,
        "cfg_scale": 1.0,
        "sampler_name": "euler",
        "scheduler_name": "beta",
    },
    {
        "id": "lumina",
        "title": "Lumina",
        "profile": "lumina",
        "base_family": "lumina",
        "width": 1024,
        "height": 1024,
        "steps": 16,
        "cfg_scale": 2.0,
        "sampler_name": "dpmpp_2m",
        "scheduler_name": "normal",
    },
    {
        "id": "zit",
        "title": "ZiT",
        "profile": "zit",
        "base_family": "zit",
        "width": 1024,
        "height": 1024,
        "steps": 8,
        "cfg_scale": 1.0,
        "sampler_name": "res_multistep",
        "scheduler_name": "simple",
    },
    {
        "id": "wan",
        "title": "Wan",
        "profile": "wan",
        "base_family": "wan",
        "width": 832,
        "height": 1216,
        "steps": 20,
        "cfg_scale": 6.0,
        "sampler_name": "euler",
        "scheduler_name": "simple",
    },
    {
        "id": "anima",
        "title": "Anima",
        "profile": "anima",
        "base_family": "anima",
        "width": 1024,
        "height": 1024,
        "steps": 20,
        "cfg_scale": 2.0,
        "sampler_name": "dpmpp_2m",
        "scheduler_name": "karras",
    },
)


def build_preset_payload() -> dict[str, object]:
    inventory = discover_model_inventory()
    presets: list[dict[str, object]] = []
    for blueprint in _UI_PRESET_BLUEPRINTS:
        profile_id = str(blueprint["profile"])
        profile = get_parity_profile(profile_id)
        _, primary_models, primary_default = resolve_primary_model_selector_context(profile_id, inventory)
        text_encoder_default = resolve_text_encoder_selector_context(profile_id, inventory)
        vae_default = resolve_vae_selector_context(profile_id, inventory)
        presets.append(
            PresetDefinition(
                id=str(blueprint["id"]),
                title=str(blueprint["title"]),
                profile=profile_id,
                base_family=str(blueprint.get("base_family", profile.base_family)),
                checkpoint_name=primary_default if primary_models else inventory.default_checkpoint,
                vae_name=vae_default,
                text_encoder_name=text_encoder_default,
                width=int(blueprint.get("width", profile.default_width)),
                height=int(blueprint.get("height", profile.default_height)),
                steps=int(blueprint.get("steps", profile.default_steps)),
                cfg_scale=float(blueprint.get("cfg_scale", profile.default_cfg_scale)),
                sampler_name=str(blueprint.get("sampler_name", profile.default_sampler)),
                scheduler_name=str(blueprint.get("scheduler_name", profile.default_scheduler)),
                clip_skip=int(blueprint.get("clip_skip", profile.default_clip_skip)),
            ).to_payload()
        )
    return {
        "source": inventory.source,
        "presets": presets,
    }
