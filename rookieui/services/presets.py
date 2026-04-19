from __future__ import annotations

from rookieui.contracts.models import PresetDefinition
from rookieui.contracts.model_family_registry import list_model_family_registry_entries
from rookieui.services.model_inventory import (
    discover_model_inventory,
    resolve_primary_model_selector_context,
    resolve_template_lora_selector_context,
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
        template_lora_default = resolve_template_lora_selector_context(profile_id, inventory)
        # IMPORTANT: presets must stay manifest-derived so new family/template intake does not fork
        # registry truth from the bootstrap/default-preset surface.
        presets.append(
            PresetDefinition(
                **entry.to_preset_payload(
                    checkpoint_name=primary_default if primary_models else inventory.default_checkpoint,
                    vae_name=vae_default,
                    text_encoder_name=text_encoder_default,
                    template_lora_name=template_lora_default,
                )
            ).to_payload()
        )
    return {
        "source": inventory.source,
        "presets": presets,
    }
