from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

EXTENSIBILITY_REFACTOR_CONTRACT_VERSION = "r121-20260417"


@dataclass(frozen=True)
class ExtensibilityBoundary:
    feature_id: str
    facade_module: str
    target_modules: tuple[str, ...]
    validation_modes: tuple[str, ...]
    notes: str = ""

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


def build_extensibility_refactor_manifest() -> dict[str, Any]:
    boundaries = (
        ExtensibilityBoundary(
            feature_id="workflow_translation",
            facade_module="rookieui.services.workflow_translation",
            target_modules=(
                "rookieui.services.workflow_builders.core",
                "rookieui.services.workflow_builders.prompt_conditioning",
                "rookieui.services.workflow_builders.controlnet",
                "rookieui.services.workflow_builders.adetailer",
                "rookieui.services.workflow_builders.output",
            ),
            validation_modes=("full-gate", "translation-topology"),
            notes="Keep workflow_translation.py as the stable orchestration facade while builder ownership moves into workflow_builders/*.",
        ),
        ExtensibilityBoundary(
            feature_id="controlnet",
            facade_module="rookieui.services.controlnet",
            target_modules=(
                "rookieui.services.controlnet_catalog",
                "rookieui.services.controlnet_normalization",
                "rookieui.services.controlnet_detect",
                "rookieui.services.controlnet_warnings",
            ),
            validation_modes=("full-gate", "controlnet", "full-pipeline"),
            notes="Keep controlnet.py as the stable route-facing facade while catalog/normalization/detect ownership moves into focused modules.",
        ),
        ExtensibilityBoundary(
            feature_id="adetailer",
            facade_module="rookieui.services.adetailer",
            target_modules=(
                "rookieui.services.adetailer_catalog",
                "rookieui.services.adetailer_normalization",
                "rookieui.services.adetailer_refinement",
                "rookieui.services.adetailer_warnings",
            ),
            validation_modes=("full-gate", "adetailer", "full-pipeline"),
            notes="Keep adetailer.py as the stable route-facing facade while catalog/normalization/refinement ownership moves into focused modules.",
        ),
        ExtensibilityBoundary(
            feature_id="integrated_feature_bootstrap",
            facade_module="web/rookieui_extension.js",
            target_modules=(
                "rookieui.services.integrated_feature_registry",
                "web/rookieui_feature_registry.js",
            ),
            validation_modes=("full-gate", "full-pipeline"),
            notes="Preserve current bootstrap behavior while moving static feature fetch ownership into a lightweight internal registry seam.",
        ),
    )
    return {
        "version": EXTENSIBILITY_REFACTOR_CONTRACT_VERSION,
        "boundaries": [boundary.to_payload() for boundary in boundaries],
    }


def boundary_target_paths(repo_root: Path | None = None) -> list[Path]:
    root = repo_root or Path(__file__).resolve().parents[2]
    manifest = build_extensibility_refactor_manifest()
    resolved: list[Path] = []
    for boundary in manifest["boundaries"]:
        facade_module = str(boundary["facade_module"])
        if facade_module.endswith(".js"):
            resolved.append(root / facade_module)
            continue
        resolved.append((root / Path(*facade_module.split("."))).with_suffix(".py"))
    return resolved


def boundary_target_module_paths(repo_root: Path | None = None) -> list[Path]:
    root = repo_root or Path(__file__).resolve().parents[2]
    manifest = build_extensibility_refactor_manifest()
    resolved: list[Path] = []
    for boundary in manifest["boundaries"]:
        for target_module in boundary["target_modules"]:
            target = str(target_module)
            if target.endswith(".js"):
                resolved.append(root / target)
                continue
            resolved.append((root / Path(*target.split("."))).with_suffix(".py"))
    return resolved
