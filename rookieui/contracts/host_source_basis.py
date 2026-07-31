from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from rookieui.contracts.current_workflow_template_delta import (
    WORKFLOW_TEMPLATE_0_11_20_DEFERRED_SURFACES,
    WORKFLOW_TEMPLATE_0_11_20_REFERENCE_ONLY_SURFACES,
    WORKFLOW_TEMPLATE_0_11_20_REMOVED_SURFACES,
    WORKFLOW_TEMPLATE_0_11_20_SUPPORTED_SURFACES,
)


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


@dataclass(frozen=True)
class WorkflowTemplateDeltaContract:
    from_version: str
    to_version: str
    added_count: int
    removed_count: int
    changed_count: int
    unchanged_count: int
    source_report_sha256: str
    supported: tuple[str, ...]
    deferred: tuple[str, ...]
    removed: tuple[str, ...]
    reference_only: tuple[str, ...]


# IMPORTANT: these are separate compatibility envelopes; do not collapse them
# into a mutable or synthetic "latest ComfyUI" version.
HOST_SOURCE_BASIS = HostSourceBasis(
    core=CoreSourceBasis(
        revision="5cc026f5b81b3f01fe7a1438a0fd4131d2ebda25",
        frontend_package_version="1.47.11",
        workflow_templates_version="0.11.20",
        embedded_docs_version="0.5.9",
    ),
    frontend=FrontendSourceBasis(
        revision="e1718dacb7bd8afeff41f00069747ff55065bf50",
        source_version="1.49.2",
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
        "0.11.20": WorkflowTemplateArtifact(
            version="0.11.20",
            filename="comfyui_workflow_templates-0.11.20-py3-none-any.whl",
            sha256="51a997f697eb04319185231744c76f0af2975c281557afee897650ea0dab775f",
        ),
    }
)

WORKFLOW_TEMPLATE_COMPONENT_ARTIFACTS: tuple[WorkflowTemplateComponentArtifact, ...] = (
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
    WorkflowTemplateComponentArtifact(
        "0.11.20",
        "comfyui-workflow-templates-core",
        "0.3.285",
        "565fe48a98b39e43c55275df152ea2292616b5b68a5a4884a564aaa76b8270be",
    ),
    WorkflowTemplateComponentArtifact(
        "0.11.20",
        "comfyui-workflow-templates-json",
        "0.1.19",
        "d30ad6c6043a1fb022065a04f21bb88e34fff61af8605ef848b4462bb9a2091f",
    ),
    WorkflowTemplateComponentArtifact(
        "0.11.20",
        "comfyui-workflow-templates-media-assets-01",
        "0.1.13",
        "7668f34f80fec894fe35d04f369d168cd1a90fb74d5694da5f728c563c49fe09",
    ),
    WorkflowTemplateComponentArtifact(
        "0.11.20",
        "comfyui-workflow-templates-media-api",
        "0.3.84",
        "c2d6a5999ac39e4f37f47ae231c92557defe5addb2cc6ab5c11410b4d5a2910a",
    ),
    WorkflowTemplateComponentArtifact(
        "0.11.20",
        "comfyui-workflow-templates-media-image",
        "0.3.160",
        "d4a5c5541c7088f6adb1c7da41f5d7c1c14a037eda6a61cd8b4b76c251faaa93",
    ),
    WorkflowTemplateComponentArtifact(
        "0.11.20",
        "comfyui-workflow-templates-media-other",
        "0.3.229",
        "ce3d98fa9d84b914c335fe5c9bc903cfefbe1932b1bc3cb6baef7f371b4bd435",
    ),
    WorkflowTemplateComponentArtifact(
        "0.11.20",
        "comfyui-workflow-templates-media-video",
        "0.3.101",
        "6270fd61c8c3931b6f0031abac7d4c90ced624de6c7918bff85b89e6c3d7493c",
    ),
)

# Backward-compatible name retained for consumers of the pre-0.11.20 ledger.
WORKFLOW_TEMPLATE_CHANGED_COMPONENT_ARTIFACTS = WORKFLOW_TEMPLATE_COMPONENT_ARTIFACTS

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
# support. Graph-signature validation is required before any surface can ship.
WORKFLOW_TEMPLATE_DELTA_0_11_2_TO_0_11_6 = WorkflowTemplateSurfaceDelta(
    added=_ADDED_SURFACES,
    changed=_CHANGED_SURFACES,
    removed=(),
    supported=(),
    deferred=(*_ADDED_SURFACES, *_CHANGED_SURFACES),
)

# IMPORTANT: the four ledgers classify the complete changed/added/removed
# 0.11.6 -> 0.11.20 JSON surface set; only `supported` is a runtime claim.
WORKFLOW_TEMPLATE_DELTA_0_11_6_TO_0_11_20 = WorkflowTemplateDeltaContract(
    from_version="0.11.6",
    to_version="0.11.20",
    added_count=41,
    removed_count=6,
    changed_count=138,
    unchanged_count=332,
    source_report_sha256="2dd6322d3f7c78c8f91b9f6c03864ae586e8a7f9c58507a8fa41b2c24c3ee306",
    supported=WORKFLOW_TEMPLATE_0_11_20_SUPPORTED_SURFACES,
    deferred=WORKFLOW_TEMPLATE_0_11_20_DEFERRED_SURFACES,
    removed=WORKFLOW_TEMPLATE_0_11_20_REMOVED_SURFACES,
    reference_only=WORKFLOW_TEMPLATE_0_11_20_REFERENCE_ONLY_SURFACES,
)
