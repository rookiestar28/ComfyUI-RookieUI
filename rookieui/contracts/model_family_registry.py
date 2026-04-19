from __future__ import annotations

from rookieui.contracts.family_template_manifest import (
    MODEL_FAMILY_REGISTRY_CONTRACT_VERSION,
    FamilyTemplateManifestEntry as ModelFamilyRegistryEntry,
    build_model_family_registry_payload,
    build_primary_model_category_by_family,
    get_family_template_manifest_entry,
    list_family_template_manifest_entries,
)


def list_model_family_registry_entries() -> list[ModelFamilyRegistryEntry]:
    return list_family_template_manifest_entries()


def get_model_family_registry_entry(family_id: str) -> ModelFamilyRegistryEntry:
    return get_family_template_manifest_entry(family_id)
