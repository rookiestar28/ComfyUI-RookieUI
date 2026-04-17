from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

INTEGRATED_FEATURE_REGISTRY_VERSION = "f114-20260417"


@dataclass(frozen=True)
class IntegratedFeatureRegistryEntry:
    feature_id: str
    bootstrap_key: str
    route_paths: tuple[str, ...]
    validation_modes: tuple[str, ...]
    notes: str = ""

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


def _registry_entries() -> tuple[IntegratedFeatureRegistryEntry, ...]:
    return (
        IntegratedFeatureRegistryEntry(
            feature_id="capabilities",
            bootstrap_key="capabilities",
            route_paths=("/rookieui/capabilities",),
            validation_modes=("catalog", "full-pipeline"),
            notes="Top-level capability payload fetched during sidebar bootstrap.",
        ),
        IntegratedFeatureRegistryEntry(
            feature_id="compatibility",
            bootstrap_key="compatibility",
            route_paths=("/rookieui/compatibility",),
            validation_modes=("catalog", "full-pipeline"),
            notes="Sampler/scheduler/runtime compatibility catalog used by sidebar forms.",
        ),
        IntegratedFeatureRegistryEntry(
            feature_id="models",
            bootstrap_key="models",
            route_paths=("/rookieui/models",),
            validation_modes=("catalog", "full-pipeline"),
            notes="Shared model inventory snapshot consumed by multiple sidebar surfaces.",
        ),
        IntegratedFeatureRegistryEntry(
            feature_id="presets",
            bootstrap_key="presets",
            route_paths=("/rookieui/presets",),
            validation_modes=("catalog", "full-pipeline"),
            notes="Profile/preset metadata used during initial sidebar bootstrap.",
        ),
        IntegratedFeatureRegistryEntry(
            feature_id="controlnet_catalog",
            bootstrap_key="controlnetCatalog",
            route_paths=(
                "/rookieui/controlnet/model_list",
                "/rookieui/controlnet/module_list",
                "/rookieui/controlnet/control_types",
            ),
            validation_modes=("controlnet", "full-pipeline"),
            notes="Composed ControlNet catalog surface built from model/module/type routes.",
        ),
        IntegratedFeatureRegistryEntry(
            feature_id="adetailer_catalog",
            bootstrap_key="adetailerCatalog",
            route_paths=("/rookieui/adetailer/catalog",),
            validation_modes=("adetailer", "full-pipeline"),
            notes="Integrated ADetailer catalog and availability snapshot.",
        ),
        IntegratedFeatureRegistryEntry(
            feature_id="queue",
            bootstrap_key="queue",
            route_paths=("/rookieui/queue",),
            validation_modes=("auxiliary-pipelines", "full-pipeline"),
            notes="Client-scoped queue snapshot fetched after client-id resolution during bootstrap.",
        ),
        IntegratedFeatureRegistryEntry(
            feature_id="prompt_workbench",
            bootstrap_key="promptWorkbench",
            route_paths=("/rookieui/prompt-tools/config",),
            validation_modes=("prompt-workbench",),
            notes="Lightweight prompt-workbench bootstrap config; heavy history/favorites remain lazy-loaded.",
        ),
        IntegratedFeatureRegistryEntry(
            feature_id="xyz_plot",
            bootstrap_key="xyzPlot",
            route_paths=("/rookieui/xyz-plot/axes",),
            validation_modes=("xyz-plot",),
            notes="XYZ Plot axis registry bootstrap surface; estimate/session/grid routes stay lazy-loaded until requested.",
        ),
    )


def build_integrated_feature_registry_payload() -> dict[str, Any]:
    entries = _registry_entries()
    return {
        "version": INTEGRATED_FEATURE_REGISTRY_VERSION,
        "features": [entry.to_payload() for entry in entries],
    }


def build_integrated_bootstrap_route_map() -> dict[str, list[str]]:
    return {entry.bootstrap_key: list(entry.route_paths) for entry in _registry_entries()}


def build_integrated_feature_validation_map() -> dict[str, list[str]]:
    return {entry.feature_id: list(entry.validation_modes) for entry in _registry_entries()}
