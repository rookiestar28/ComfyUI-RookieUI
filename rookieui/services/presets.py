from __future__ import annotations

from rookieui.contracts.models import PresetDefinition
from rookieui.contracts.model_family_registry import list_model_family_registry_entries
from rookieui.services.model_inventory import (
    discover_model_inventory,
    resolve_primary_model_selector_context,
    resolve_text_encoder_selector_context,
    resolve_vae_selector_context,
)

def build_preset_payload() -> dict[str, object]:
    inventory = discover_model_inventory()
    presets: list[dict[str, object]] = []
    for entry in list_model_family_registry_entries():
        profile_id = entry.id
        _, primary_models, primary_default = resolve_primary_model_selector_context(profile_id, inventory)
        text_encoder_default = resolve_text_encoder_selector_context(profile_id, inventory)
        vae_default = resolve_vae_selector_context(profile_id, inventory)
        presets.append(
            PresetDefinition(
                id=entry.id,
                title="SD1.5" if entry.id == "sd15" else ("SDXL" if entry.id == "sdxl" else entry.title),
                profile=profile_id,
                base_family=entry.public_base_family,
                checkpoint_name=primary_default if primary_models else inventory.default_checkpoint,
                vae_name=vae_default,
                text_encoder_name=text_encoder_default,
                width=entry.default_width,
                height=entry.default_height,
                steps=entry.default_steps,
                cfg_scale=entry.default_cfg_scale,
                shift=entry.default_shift,
                flux_guidance=entry.default_flux_guidance,
                sampler_name=entry.default_sampler,
                scheduler_name=entry.default_scheduler,
                clip_skip=entry.default_clip_skip,
                prompt_enhancement_enabled=entry.default_prompt_enhancement_enabled,
            ).to_payload()
        )
    return {
        "source": inventory.source,
        "presets": presets,
    }
