from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class CoreSourceBasis:
    revision: str
    frontend_package_version: str
    workflow_templates_version: str
    embedded_docs_version: str


@dataclass(frozen=True)
class FrontendSourceBasis:
    revision: str
    source_version: str


@dataclass(frozen=True)
class DesktopSourceBasis:
    revision: str
    source_version: str
    packaged_core_version: str
    packaged_frontend_version: str


@dataclass(frozen=True)
class HostSourceBasis:
    core: CoreSourceBasis
    frontend: FrontendSourceBasis
    desktop: DesktopSourceBasis


@dataclass(frozen=True)
class WorkflowTemplateArtifact:
    version: str
    filename: str
    sha256: str


@dataclass(frozen=True)
class WorkflowTemplateComponentArtifact:
    basis_version: str
    package: str
    version: str
    sha256: str


@dataclass(frozen=True)
class WorkflowTemplateSurfaceDelta:
    added: tuple[str, ...]
    changed: tuple[str, ...]
    removed: tuple[str, ...]
    supported: tuple[str, ...]
    deferred: tuple[str, ...]


# IMPORTANT: these are separate compatibility envelopes; do not collapse them
# into a mutable or synthetic "latest ComfyUI" version.
HOST_SOURCE_BASIS = HostSourceBasis(
    core=CoreSourceBasis(
        revision="69ea58697bb2f05124f5dc7e00ad111f7cfff645",
        frontend_package_version="1.45.20",
        workflow_templates_version="0.11.6",
        embedded_docs_version="0.5.7",
    ),
    frontend=FrontendSourceBasis(
        revision="b40fad0e755ddee5b09db3b93566f7e0a9f6967f",
        source_version="1.48.2",
    ),
    desktop=DesktopSourceBasis(
        revision="e2d964b7456cea8423c7b9d3371c612313c06baa",
        source_version="0.9.4",
        packaged_core_version="0.22.3",
        packaged_frontend_version="1.43.18",
    ),
)

WORKFLOW_TEMPLATE_ARTIFACTS: Mapping[str, WorkflowTemplateArtifact] = MappingProxyType(
    {
        "0.11.2": WorkflowTemplateArtifact(
            version="0.11.2",
            filename="comfyui_workflow_templates-0.11.2-py3-none-any.whl",
            sha256="7d24739323e234d23321ec717cc820c3ae7f207faa411560854d38278f496a58",
        ),
        "0.11.6": WorkflowTemplateArtifact(
            version="0.11.6",
            filename="comfyui_workflow_templates-0.11.6-py3-none-any.whl",
            sha256="67c290064ab9171637a863875da0726b5fe89cfb954645bf93e9098a8f2fdd21",
        ),
    }
)

WORKFLOW_TEMPLATE_CHANGED_COMPONENT_ARTIFACTS: tuple[WorkflowTemplateComponentArtifact, ...] = (
    WorkflowTemplateComponentArtifact(
        "0.11.2",
        "comfyui-workflow-templates-core",
        "0.3.267",
        "45fef4ad65dce589f986744fdfc5104b7a9181068b774050f628e035039e4590",
    ),
    WorkflowTemplateComponentArtifact(
        "0.11.6",
        "comfyui-workflow-templates-core",
        "0.3.269",
        "35ec88d4540273ec370f1527c75592b0d002cc2f7a873de73bedbb493141be14",
    ),
    WorkflowTemplateComponentArtifact(
        "0.11.2",
        "comfyui-workflow-templates-json",
        "0.1.2",
        "29f625b4cf05a47959af1788146d7a54590e2b2243550806ac3806df2470a66e",
    ),
    WorkflowTemplateComponentArtifact(
        "0.11.6",
        "comfyui-workflow-templates-json",
        "0.1.3",
        "12da5b0bb2c9a426383b93e07a5c374b46c40a262767f0ef3d794991970cccc7",
    ),
    WorkflowTemplateComponentArtifact(
        "0.11.2",
        "comfyui-workflow-templates-media-assets-01",
        "0.1.0",
        "b9f34b49d170064fa32823cc29332a66d964a7c9511e14ba454406bf3037d20a",
    ),
    WorkflowTemplateComponentArtifact(
        "0.11.6",
        "comfyui-workflow-templates-media-assets-01",
        "0.1.1",
        "16c1c2dab19a12ea0a144f115fa67aded94202f9a035104856f9b3688eaea56b",
    ),
)

_ADDED_SURFACES = (
    "api_bytedance_seed_audio1_0_t2a",
    "api_bytedance_seed_audio1_0_ta2a",
    "api_bytedance_seed_audio1_0_ti2a",
    "api_bytedance_seedream_5_0_pro_image_edit",
    "api_bytedance_seedream_5_0_pro_t2i",
    "image_krea2_turbo_t2i_int8",
    "image_z_image_turbo_int8",
)
_CHANGED_SURFACES = ("api_bytedance_seedream_5_0_lite_image_edit",)

# Artifact presence is evidence of a reference surface, not implementation
# support. F288 owns graph-signature validation before any surface can ship.
WORKFLOW_TEMPLATE_DELTA_0_11_2_TO_0_11_6 = WorkflowTemplateSurfaceDelta(
    added=_ADDED_SURFACES,
    changed=_CHANGED_SURFACES,
    removed=(),
    supported=(),
    deferred=(*_ADDED_SURFACES, *_CHANGED_SURFACES),
)
