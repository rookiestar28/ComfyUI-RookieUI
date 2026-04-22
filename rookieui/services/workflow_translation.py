from __future__ import annotations

from rookieui.contracts.generation import (
    NormalizedImg2ImgRequest,
    NormalizedTxt2ImgRequest,
    WorkflowTranslationResult,
)
from rookieui.services import parity_matrix
from rookieui.services.workflow_builders.non_sd_templates import (
    build_non_sd_edit_workflow,
    build_non_sd_txt2img_workflow,
    is_official_non_sd_edit_profile,
    is_official_non_sd_txt2img_profile,
)
from rookieui.services.workflow_builders.sd_family_graphs import (
    _build_sd15_img2img_graph,
    _build_sd15_inpaint_graph,
    _build_sd15_txt2img_graph,
    _build_sdxl_img2img_graph,
    _build_sdxl_inpaint_graph,
    _build_sdxl_txt2img_graph,
)

# IMPORTANT: phase-59 refactor keeps this module as the stable workflow-translation facade.
# New builder ownership must move behind this file, not around it, so routes/tests keep one import surface.


def _should_use_official_non_sd_txt2img_template(request: NormalizedTxt2ImgRequest) -> bool:
    if request.primary_model_category != "diffusion_models":
        return False
    if not is_official_non_sd_txt2img_profile(request.profile):
        return False
    # IMPORTANT: official non-SD template builders currently own the base template path only.
    # Extended seams such as ControlNet, ADetailer, and Hires must stay on the legacy augmented graph until
    # those feature chains get explicit official-template parity builders instead of being silently dropped.
    return not (request.hires_enabled or bool(request.controlnet_units) or request.adetailer.enabled)


def build_txt2img_workflow(request: NormalizedTxt2ImgRequest) -> dict[str, object]:
    if _should_use_official_non_sd_txt2img_template(request):
        return build_non_sd_txt2img_workflow(request)
    if request.base_family == "sd15":
        return _build_sd15_txt2img_graph(request)
    if request.base_family == "sdxl":
        return _build_sdxl_txt2img_graph(request)
    raise ValueError(f"Unsupported RookieUI base family: {request.base_family}")


def build_img2img_workflow(request: NormalizedImg2ImgRequest) -> dict[str, object]:
    # IMPORTANT: keep execution_mode as the graph selector; user-facing mode labels (sketch/inpaint_upload/batch) are normalized upstream.
    if _should_use_official_non_sd_edit_template(request):
        return build_non_sd_edit_workflow(request)
    if request.base_family == "sd15":
        return _build_sd15_inpaint_graph(request) if request.execution_mode == "inpaint" else _build_sd15_img2img_graph(request)
    if request.base_family == "sdxl":
        return _build_sdxl_inpaint_graph(request) if request.execution_mode == "inpaint" else _build_sdxl_img2img_graph(request)
    raise ValueError(f"Unsupported RookieUI base family: {request.base_family}")


def _build_translation_result(
    *,
    request_payload: dict[str, object],
    workflow_kind: str,
    profile: str,
    workflow: dict[str, object],
) -> WorkflowTranslationResult:
    parity_profile = parity_matrix.get_parity_profile(profile)
    return WorkflowTranslationResult(
        mode="translation-only",
        workflow_kind=workflow_kind,
        profile=profile,
        normalized_request=request_payload,
        parity_profile=parity_profile.to_payload(),
        sampler_aliases=parity_matrix.get_sampler_alias_payload(),
        workflow=workflow,
    )


def translate_txt2img_request(request: NormalizedTxt2ImgRequest) -> WorkflowTranslationResult:
    workflow_kind = (
        f"txt2img-{request.profile}"
        if _should_use_official_non_sd_txt2img_template(request)
        else f"txt2img-{request.base_family}"
    )
    if request.hires_enabled:
        workflow_kind = f"{workflow_kind}-hires"
    return _build_translation_result(
        request_payload=request.to_payload(),
        workflow_kind=workflow_kind,
        profile=request.profile,
        workflow=build_txt2img_workflow(request),
    )


def translate_img2img_request(request: NormalizedImg2ImgRequest) -> WorkflowTranslationResult:
    workflow_kind = (
        f"img2img-{request.profile}"
        if _should_use_official_non_sd_edit_template(request)
        else f"{request.mode}-{request.base_family}"
    )
    if request.hires_enabled:
        workflow_kind = f"{workflow_kind}-hires"
    return _build_translation_result(
        request_payload=request.to_payload(),
        workflow_kind=workflow_kind,
        profile=request.profile,
        workflow=build_img2img_workflow(request),
    )


def _should_use_official_non_sd_edit_template(request: NormalizedImg2ImgRequest) -> bool:
    if request.execution_mode != "edit":
        return False
    if request.primary_model_category != "diffusion_models":
        return False
    if not is_official_non_sd_edit_profile(request.profile):
        return False
    # IMPORTANT: edit templates currently own only the canonical single-image path; keep adjunct seams on the legacy graph until explicit parity exists.
    return not (request.hires_enabled or bool(request.controlnet_units) or request.adetailer.enabled)
