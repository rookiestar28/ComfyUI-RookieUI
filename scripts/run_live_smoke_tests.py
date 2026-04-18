from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    # CRITICAL: keep repo root on sys.path when running `python scripts/run_live_smoke_tests.py`; otherwise the smoke lane cannot import the local RookieUI package or golden fixtures outside editable-install contexts.
    sys.path.insert(0, str(_REPO_ROOT))

from rookieui.contracts.extras import EXTRAS_CONTRACT_VERSION
from rookieui.contracts.pnginfo import PNGINFO_CONTRACT_VERSION
from rookieui.contracts.queue import QUEUE_CONTRACT_VERSION
from rookieui.contracts.adetailer import ADETAILER_INTEGRATED_CONTRACT_VERSION
from rookieui.contracts.controlnet_integrated import CONTROLNET_INTEGRATED_CONTRACT_VERSION
from rookieui.contracts.prompt_workbench import (
    PROMPT_WORKBENCH_CONTRACT_VERSION,
    PROMPT_WORKBENCH_NAMESPACES,
    PROMPT_WORKBENCH_SHIPPED_AI_PROVIDER_IDS,
    PROMPT_WORKBENCH_SHIPPED_TRANSLATION_PROVIDER_IDS,
)
from rookieui.contracts.xyz_plot import XYZ_PLOT_CONTRACT_VERSION
from rookieui.services.adetailer import (
    ADETAILER_WARNING_CONTROLNET_CUSTOM_MODEL_MISSING,
    ADETAILER_WARNING_CONTROLNET_PASSTHROUGH_EMPTY,
    ADETAILER_WARNING_DETECTOR_RUNTIME_FALLBACK_MASK,
)
from rookieui.services.adetailer_runtime import ADETAILER_RUNTIME_READY
from rookieui.services.parity_matrix import get_parity_profile
from rookieui.services.prompt_capability_matrix import build_prompt_capability_matrix_payload
from rookieui.services.version import resolve_runtime_build_fingerprint
from tests.prompt_parity_fixtures import (
    ALL_PROMPT_FEATURES,
    ExpectedEmbeddingRef,
    PROMPT_PARITY_GOLDEN_CASES,
    PromptParityGoldenCase,
)


_NON_SD_DIFFUSION_PROFILES: tuple[str, ...] = (
    "flux",
    "qwen_image",
    "klein",
    "lumina",
    "zit",
    "wan",
    "anima",
)
_CONTROLNET_VALIDATION_PROFILES: tuple[str, ...] = ("sd15", "pony", "illustrious", "noob", "sdxl")
_ADETAILER_VALIDATION_PROFILES: tuple[str, ...] = _CONTROLNET_VALIDATION_PROFILES
_SD_PROMPT_PARITY_PROFILES: tuple[str, ...] = ("sd15", "pony", "illustrious", "noob", "sdxl")
_SDXL_PROMPT_PARITY_PROFILES: tuple[str, ...] = ("pony", "illustrious", "noob", "sdxl")
_LOCAL_CONTROLNET_CONTRACT_VERSION = CONTROLNET_INTEGRATED_CONTRACT_VERSION
_LOCAL_ADETAILER_CONTRACT_VERSION = ADETAILER_INTEGRATED_CONTRACT_VERSION
_LOCAL_PROMPT_CONTRACT_VERSION = str(build_prompt_capability_matrix_payload().get("contract_version", "")).strip()
_LOCAL_PROMPT_WORKBENCH_CONTRACT_VERSION = PROMPT_WORKBENCH_CONTRACT_VERSION
_LOCAL_XYZ_PLOT_CONTRACT_VERSION = XYZ_PLOT_CONTRACT_VERSION
_LOCAL_RUNTIME_BUILD_FINGERPRINT = resolve_runtime_build_fingerprint()
_CONTROLNET_WARNING_PREPROCESSOR_DISABLED = "CONTROLNET_PREPROCESSOR_DISABLED"
_CONTROLNET_WARNING_PREPROCESSOR_UNAVAILABLE = "CONTROLNET_PREPROCESSOR_UNAVAILABLE"
_CONTROLNET_WARNING_PREPROCESSOR_HOST_FALLBACK = "CONTROLNET_PREPROCESSOR_HOST_FALLBACK"
_CONTROLNET_SD15_MODEL_MARKERS = ("sd15", "sd1.5", "sd-15", "sd_15")
_CONTROLNET_SDXL_MODEL_MARKERS = ("sdxl", "pony", "illustrious", "noob")
_CONTROLNET_ALLOWED_DETECT_BACKENDS = {
    "comfy_host_preprocessor",
    "comfy_host_preprocessor_aio",
    "rookieui_internal_fallback",
    "rookieui_internal_mixed",
    "rookieui_internal_disabled",
    "rookieui_internal_unavailable",
}


@dataclass(frozen=True)
class PromptParityHostContext:
    sd15_checkpoint: str
    sdxl_profile: str
    sdxl_checkpoint: str
    embedding_name: str | None
    host_contract_version: str
    local_contract_version: str


@dataclass(frozen=True)
class LivePromptParityCase:
    fixture: PromptParityGoldenCase
    checkpoint_name: str
    execute: bool = False


@dataclass(frozen=True)
class LiveRouteContractProbe:
    surface: str
    route_path: str
    local_contract_version: str
    method: str = "GET"
    payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class ControlNetHostContext:
    profile_id: str
    checkpoint_name: str
    base_family: str
    control_type: str
    module_name: str
    model_name: str
    host_contract_version: str
    local_contract_version: str


@dataclass(frozen=True)
class LiveControlNetDryRunCase:
    case_id: str
    route_path: str
    request_payload: dict[str, Any]
    expected_workflow_kind: str
    expected_apply_nodes: int
    expect_main_source_fallback: bool = False


@dataclass(frozen=True)
class ADetailerHostContext:
    profile_id: str
    checkpoint_name: str
    base_family: str
    detector_name: str
    detector_family: str
    detector_runtime_state: str
    controlnet_control_type: str
    controlnet_module: str
    controlnet_model: str
    host_contract_version: str
    local_contract_version: str


@dataclass(frozen=True)
class LiveADetailerDryRunCase:
    case_id: str
    route_path: str
    request_payload: dict[str, Any]
    expected_workflow_kind: str
    expected_sampler_nodes: int
    expected_apply_nodes: int
    expect_refinement_nodes: bool
    expect_primary_controlnet_count: int
    expect_skip_img2img: bool = False


@dataclass(frozen=True)
class AuxiliaryPipelineContext:
    checkpoint_name: str
    workflow_family: str


@dataclass(frozen=True)
class LivePNGInfoCase:
    case_id: str
    image_data: str
    expected_source_type: str
    expected_target_form: str
    expected_apply_targets: tuple[str, ...]
    expected_prompt: str = ""
    expected_negative_prompt: str = ""
    expected_profile: str | None = None
    expected_checkpoint_name: str | None = None
    expected_missing_inputs: tuple[str, ...] = ()
    expected_warning_fragment: str | None = None
    apply_back_route: str | None = None
    expected_workflow_kind: str | None = None


@dataclass(frozen=True)
class PromptWorkbenchHostContext:
    namespace: str
    host_contract_version: str
    local_contract_version: str
    translation_default_provider: str
    translation_default_availability: str
    ai_assist_default_provider: str
    ai_assist_default_availability: str


@dataclass(frozen=True)
class XYZPlotHostContext:
    checkpoint_name: str
    workflow_family: str
    host_contract_version: str
    local_contract_version: str


@dataclass(frozen=True)
class LiveHostFreshnessContext:
    host_build_fingerprint: str
    local_build_fingerprint: str


def _env_flag(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_profiles_for_mode(validation_mode: str) -> str:
    if validation_mode == "controlnet":
        return ",".join(_CONTROLNET_VALIDATION_PROFILES)
    if validation_mode == "adetailer":
        return ",".join(_ADETAILER_VALIDATION_PROFILES)
    if validation_mode == "prompt-workbench":
        return ""
    if validation_mode == "xyz-plot":
        return ""
    if validation_mode == "full-pipeline":
        return ""
    if validation_mode == "auxiliary-pipelines":
        return ""
    if validation_mode == "prompt-parity":
        return ",".join(_SD_PROMPT_PARITY_PROFILES)
    if validation_mode == "auxiliary-contracts":
        return ""
    return ",".join(_NON_SD_DIFFUSION_PROFILES)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run optional live RookieUI smoke checks against a real ComfyUI host. "
            "This lane validates profile-to-model/text-encoder alignment and can optionally "
            "submit/poll lightweight txt2img runs for non-SD diffusion profiles while also "
            "supporting auxiliary route contract checks."
        )
    )
    parser.add_argument(
        "--validation-mode",
        choices=(
            "catalog",
            "prompt-parity",
            "prompt-workbench",
            "xyz-plot",
            "auxiliary-contracts",
            "auxiliary-pipelines",
            "controlnet",
            "adetailer",
            "full-pipeline",
        ),
        default=os.getenv("ROOKIEUI_LIVE_VALIDATION_MODE", "catalog").strip().lower() or "catalog",
        help="Validation lane to run (default: %(default)s).",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("ROOKIEUI_LIVE_BASE_URL", "http://127.0.0.1:8188"),
        help="ComfyUI host base URL (default: %(default)s).",
    )
    parser.add_argument(
        "--profiles",
        default=os.getenv("ROOKIEUI_LIVE_SMOKE_PROFILES", "").strip(),
        help="Comma-separated profile IDs to validate (mode-specific defaults apply when omitted).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        default=_env_flag("ROOKIEUI_LIVE_SMOKE_EXECUTE", default=False),
        help="Submit/poll real txt2img runs in addition to catalog contract checks.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        default=_env_flag("ROOKIEUI_LIVE_REPORT_ONLY", default=False),
        help="Report stale-host or parity mismatches without failing the process.",
    )
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=float(os.getenv("ROOKIEUI_LIVE_REQUEST_TIMEOUT_SECONDS", "30")),
        help="HTTP request timeout in seconds (default: %(default)s).",
    )
    parser.add_argument(
        "--poll-timeout-seconds",
        type=float,
        default=float(os.getenv("ROOKIEUI_LIVE_POLL_TIMEOUT_SECONDS", "180")),
        help="Per-profile queue poll timeout in seconds when --execute is enabled (default: %(default)s).",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=float(os.getenv("ROOKIEUI_LIVE_POLL_INTERVAL_SECONDS", "2")),
        help="Queue polling interval in seconds when --execute is enabled (default: %(default)s).",
    )
    return parser


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _request_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout_seconds: float,
) -> dict[str, Any]:
    request_data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        request_data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=request_data, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:  # pragma: no cover - runtime path depends on host state.
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover - runtime path depends on host reachability.
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc


def _request_json_with_status(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout_seconds: float,
) -> tuple[int, dict[str, Any]]:
    request_data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        request_data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=request_data, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
            return int(getattr(response, "status", 200) or 200), (json.loads(body) if body else {})
    except urllib.error.HTTPError as exc:  # pragma: no cover - runtime path depends on host state.
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            payload_data = json.loads(detail) if detail else {}
        except json.JSONDecodeError:
            payload_data = {"detail": detail}
        return exc.code, payload_data if isinstance(payload_data, dict) else {"detail": detail}
    except urllib.error.URLError as exc:  # pragma: no cover - runtime path depends on host reachability.
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc


def _load_server_payloads(base_url: str, timeout_seconds: float) -> tuple[dict[str, Any], dict[str, Any]]:
    models = _request_json(
        "GET",
        f"{base_url}/rookieui/models",
        timeout_seconds=timeout_seconds,
    )
    presets = _request_json(
        "GET",
        f"{base_url}/rookieui/presets",
        timeout_seconds=timeout_seconds,
    )
    return models, presets


def _load_bootstrap_payload(base_url: str, timeout_seconds: float) -> dict[str, Any]:
    return _request_json(
        "GET",
        f"{base_url}/rookieui/bootstrap",
        timeout_seconds=timeout_seconds,
    )


def _load_capabilities_payload(base_url: str, timeout_seconds: float) -> dict[str, Any]:
    return _request_json(
        "GET",
        f"{base_url}/rookieui/capabilities",
        timeout_seconds=timeout_seconds,
    )


def _load_controlnet_payloads(
    base_url: str,
    timeout_seconds: float,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        _request_json("GET", f"{base_url}/rookieui/controlnet/model_list", timeout_seconds=timeout_seconds),
        _request_json("GET", f"{base_url}/rookieui/controlnet/module_list", timeout_seconds=timeout_seconds),
        _request_json("GET", f"{base_url}/rookieui/controlnet/control_types", timeout_seconds=timeout_seconds),
    )


def _load_adetailer_catalog_payload(base_url: str, timeout_seconds: float) -> dict[str, Any]:
    return _request_json("GET", f"{base_url}/rookieui/adetailer/catalog", timeout_seconds=timeout_seconds)


def _load_xyz_plot_axes_payload(base_url: str, timeout_seconds: float) -> dict[str, Any]:
    return _request_json("GET", f"{base_url}/rookieui/xyz-plot/axes", timeout_seconds=timeout_seconds)


def _prompt_workbench_url(base_url: str, route_suffix: str, *, query: dict[str, str] | None = None) -> str:
    base = f"{base_url}/rookieui/prompt-tools/{route_suffix.lstrip('/')}"
    if not query:
        return base
    return f"{base}?{urllib.parse.urlencode(query)}"


def _request_prompt_workbench_json(
    base_url: str,
    route_suffix: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
    timeout_seconds: float,
) -> dict[str, Any]:
    return _request_json(
        method,
        _prompt_workbench_url(base_url, route_suffix, query=query),
        payload=payload,
        timeout_seconds=timeout_seconds,
    )


def _request_prompt_workbench_json_with_status(
    base_url: str,
    route_suffix: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
    timeout_seconds: float,
) -> tuple[int, dict[str, Any]]:
    return _request_json_with_status(
        method,
        _prompt_workbench_url(base_url, route_suffix, query=query),
        payload=payload,
        timeout_seconds=timeout_seconds,
    )


def _build_png_data_url(*, color: str = "white", metadata: dict[str, str] | None = None) -> str:
    try:
        # CRITICAL: keep the Pillow import lazy; catalog-only smoke and prompt-parity dry-run checks must remain import-safe even if a shell env is missing optional image helpers.
        from PIL import Image
        from PIL.PngImagePlugin import PngInfo
    except ImportError as exc:  # pragma: no cover - depends on local runtime packaging.
        raise RuntimeError("Pillow is required for auxiliary live-smoke PNG payload generation.") from exc

    image = Image.new("RGB", (32, 32), color=color)
    pnginfo = None
    if metadata:
        pnginfo = PngInfo()
        for key, value in metadata.items():
            pnginfo.add_text(key, value)

    buffer = io.BytesIO()
    save_kwargs: dict[str, Any] = {"format": "PNG"}
    if pnginfo is not None:
        save_kwargs["pnginfo"] = pnginfo
    image.save(buffer, **save_kwargs)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _parse_profiles(raw_profiles: str) -> list[str]:
    profiles = [segment.strip() for segment in raw_profiles.split(",") if segment.strip()]
    return list(dict.fromkeys(profiles))


def _get_fixture(case_id: str) -> PromptParityGoldenCase:
    for fixture in PROMPT_PARITY_GOLDEN_CASES:
        if fixture.case_id == case_id:
            return fixture
    raise KeyError(f"Unknown prompt parity fixture: {case_id}")


def _read_nested_text(payload: object, *path: str) -> str:
    current = payload
    for key in path:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    if current is None:
        return ""
    return str(current).strip()


def _build_live_host_freshness_context(
    bootstrap_payload: dict[str, Any],
) -> tuple[LiveHostFreshnessContext | None, list[str]]:
    runtime_payload = bootstrap_payload.get("runtime")
    if not isinstance(runtime_payload, dict):
        return None, ["live host /rookieui/bootstrap payload did not expose runtime metadata."]
    return (
        LiveHostFreshnessContext(
            host_build_fingerprint=_read_nested_text(runtime_payload, "build_fingerprint"),
            local_build_fingerprint=_LOCAL_RUNTIME_BUILD_FINGERPRINT,
        ),
        [],
    )


def _validate_live_host_freshness(context: LiveHostFreshnessContext) -> list[str]:
    errors: list[str] = []
    if not context.host_build_fingerprint:
        errors.append("live host /rookieui/bootstrap payload did not expose runtime.build_fingerprint.")
    elif context.host_build_fingerprint != context.local_build_fingerprint:
        errors.append(
            "live host runtime build fingerprint mismatch: "
            f"host='{context.host_build_fingerprint}' workspace='{context.local_build_fingerprint}'. "
            "Restart the ComfyUI host before accepting live-smoke evidence."
        )
    return errors


def _build_auxiliary_contract_probes() -> list[LiveRouteContractProbe]:
    pnginfo_infotext = (
        "masterpiece, harbor dusk\n"
        "Negative prompt: blurry\n"
        "Steps: 20, Sampler: Euler a, CFG scale: 7, Seed: 5, Size: 512x512"
    )
    return [
        LiveRouteContractProbe(
            surface="queue_snapshot_and_job_lookup",
            route_path="/rookieui/queue",
            local_contract_version=QUEUE_CONTRACT_VERSION,
        ),
        LiveRouteContractProbe(
            surface="pnginfo_parse_inspect",
            route_path="/rookieui/pnginfo/parse",
            local_contract_version=PNGINFO_CONTRACT_VERSION,
            method="POST",
            payload={"image_data": _build_png_data_url(metadata={"parameters": pnginfo_infotext})},
        ),
        LiveRouteContractProbe(
            surface="extras_run",
            route_path="/rookieui/extras/run",
            local_contract_version=EXTRAS_CONTRACT_VERSION,
            method="POST",
            payload={
                "mode": "single_image",
                "image_data": _build_png_data_url(color="lightblue"),
                "scale_by": 1.0,
            },
        ),
    ]


def _build_auxiliary_pipeline_context(models_payload: dict[str, Any]) -> AuxiliaryPipelineContext:
    checkpoints = _iter_string_list(models_payload, "checkpoints")
    checkpoint_name = (
        _select_checkpoint_by_keywords(checkpoints, prefix="SD15\\")
        or _select_checkpoint_by_keywords(checkpoints, prefix="SDXL\\", keywords=("pony", "illustrious", "noob"))
        or _select_checkpoint_by_keywords(checkpoints, prefix="SDXL\\")
        or _read_nested_text(models_payload, "default_checkpoint")
        or (checkpoints[0] if checkpoints else "__host_default__")
    )
    workflow_family = "sdxl" if checkpoint_name.lower().startswith("sdxl\\") else "sd15"
    return AuxiliaryPipelineContext(
        checkpoint_name=checkpoint_name,
        workflow_family=workflow_family,
    )


def _build_extras_smoke_payload() -> dict[str, Any]:
    return {
        "mode": "single_image",
        "image_data": _build_png_data_url(color="lightblue"),
        "upscale_enabled": True,
        "scale_mode": "scale_to",
        "scale_by": 1.0,
        "target_width": 128,
        "target_height": 160,
        "color_correction": True,
        "face_restoration": "codeformer",
        "codeformer_weight": 0.4,
    }


def _build_pnginfo_live_cases(context: AuxiliaryPipelineContext) -> list[LivePNGInfoCase]:
    size = "1024x1024" if context.workflow_family == "sdxl" else "512x512"
    txt2img_parameters = (
        "harbor dusk\n"
        "Negative prompt: blurry\n"
        f"Steps: 20, Sampler: Euler a, CFG scale: 7, Seed: 5, Size: {size}, Model: {context.checkpoint_name}"
    )
    inpaint_parameters = (
        "portrait cleanup\n"
        "Negative prompt: bad hands\n"
        "Steps: 24, Sampler: DPM++ 2M Karras, CFG scale: 7, Seed: 42, "
        f"Size: {size}, Denoising strength: 0.42, Mask mode: Inpaint masked, Masked content: original, "
        f"Inpaint area: Whole picture, Masked area padding: 16, Model: {context.checkpoint_name}"
    )
    return [
        LivePNGInfoCase(
            case_id="pnginfo_a1111_txt2img",
            image_data=_build_png_data_url(metadata={"parameters": txt2img_parameters}),
            expected_source_type="a1111",
            expected_target_form="txt2img",
            expected_apply_targets=("txt2img", "img2img"),
            expected_prompt="harbor dusk",
            expected_negative_prompt="blurry",
            expected_profile=context.workflow_family,
            expected_checkpoint_name=context.checkpoint_name,
            apply_back_route="/rookieui/generate/txt2img",
            expected_workflow_kind=f"txt2img-{context.workflow_family}",
        ),
        LivePNGInfoCase(
            case_id="pnginfo_comfy_inspect_only",
            image_data=_build_png_data_url(
                metadata={
                    "prompt": "{\"1\": {\"class_type\": \"KSampler\"}}",
                    "workflow": "{\"nodes\": []}",
                }
            ),
            expected_source_type="comfyui",
            expected_target_form="inspect_only",
            expected_apply_targets=(),
            expected_warning_fragment="inspection only",
        ),
        LivePNGInfoCase(
            case_id="pnginfo_a1111_inpaint",
            image_data=_build_png_data_url(metadata={"parameters": inpaint_parameters}),
            expected_source_type="a1111",
            expected_target_form="inpaint",
            expected_apply_targets=("txt2img", "img2img"),
            expected_prompt="portrait cleanup",
            expected_negative_prompt="bad hands",
            expected_profile=context.workflow_family,
            expected_checkpoint_name=context.checkpoint_name,
            expected_missing_inputs=("mask_asset",),
            expected_warning_fragment="Mask asset must be selected manually",
        ),
    ]


def _validate_route_contract_payload(probe: LiveRouteContractProbe, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if _read_nested_text(payload, "service") != "rookieui":
        errors.append(
            f"surface '{probe.surface}' expected top-level service='rookieui' but got "
            f"'{_read_nested_text(payload, 'service')}'."
        )
    if _read_nested_text(payload, "status") != "ok":
        errors.append(
            f"surface '{probe.surface}' expected top-level status='ok' but got "
            f"'{_read_nested_text(payload, 'status')}'."
        )

    host_surface = _read_nested_text(payload, "contract", "surface")
    if host_surface != probe.surface:
        errors.append(
            f"surface '{probe.surface}' expected contract.surface='{probe.surface}' but got '{host_surface}'."
        )

    host_contract_version = _read_nested_text(payload, "contract", "version")
    if not host_contract_version:
        errors.append(f"surface '{probe.surface}' did not expose contract.version.")
    elif host_contract_version != probe.local_contract_version:
        errors.append(
            f"surface '{probe.surface}' contract mismatch: "
            f"host='{host_contract_version}' workspace='{probe.local_contract_version}'."
        )
    return errors


def _run_auxiliary_contract_smoke(base_url: str, *, request_timeout_seconds: float) -> list[str]:
    errors: list[str] = []
    for probe in _build_auxiliary_contract_probes():
        try:
            response_payload = _request_json(
                probe.method,
                f"{base_url}{probe.route_path}",
                payload=probe.payload,
                timeout_seconds=request_timeout_seconds,
            )
        except Exception as exc:
            errors.append(f"surface '{probe.surface}' request failed: {exc}")
            continue
        errors.extend(_validate_route_contract_payload(probe, response_payload))
    return errors


def _build_prompt_workbench_host_context(
    config_payload: dict[str, Any],
    providers_payload: dict[str, Any],
) -> tuple[PromptWorkbenchHostContext | None, list[str]]:
    errors: list[str] = []
    config_probe = LiveRouteContractProbe(
        surface="prompt_tools_config",
        route_path="/rookieui/prompt-tools/config",
        local_contract_version=_LOCAL_PROMPT_WORKBENCH_CONTRACT_VERSION,
    )
    providers_probe = LiveRouteContractProbe(
        surface="prompt_tools_providers",
        route_path="/rookieui/prompt-tools/providers",
        local_contract_version=_LOCAL_PROMPT_WORKBENCH_CONTRACT_VERSION,
    )
    errors.extend(_validate_route_contract_payload(config_probe, config_payload))
    errors.extend(_validate_route_contract_payload(providers_probe, providers_payload))
    contract = config_payload.get("contract")
    if not isinstance(contract, dict):
        return None, errors + ["prompt-workbench config payload missing contract."]
    route_family = str(contract.get("route_family", "")).strip()
    if route_family != "/rookieui/prompt-tools":
        errors.append(f"prompt-workbench route_family drifted to '{route_family}'.")
    namespaces = contract.get("namespaces")
    if list(PROMPT_WORKBENCH_NAMESPACES) != (namespaces if isinstance(namespaces, list) else []):
        errors.append("prompt-workbench namespaces no longer match the shipped contract surface.")
    state_schema_version = contract.get("state_schema_version")
    if not isinstance(state_schema_version, int):
        errors.append("prompt-workbench config payload missing state_schema_version.")

    config = config_payload.get("config")
    if not isinstance(config, dict):
        return None, errors + ["prompt-workbench config payload missing config object."]
    if not str(config.get("language", "")).strip():
        errors.append("prompt-workbench config payload missing language.")
    if not str(config.get("theme_style", "")).strip():
        errors.append("prompt-workbench config payload missing theme_style.")
    ai_assist = config.get("ai_assist")
    if not isinstance(ai_assist, dict) or not str(ai_assist.get("instruction_preset", "")).strip():
        errors.append("prompt-workbench config payload missing ai_assist.instruction_preset.")

    language_options = config_payload.get("language_options")
    if not isinstance(language_options, list) or not any(
        isinstance(entry, dict) and str(entry.get("code", "")).strip() == "en" for entry in language_options
    ):
        errors.append("prompt-workbench config payload missing expected language option 'en'.")
    theme_style_options = config_payload.get("theme_style_options")
    if not isinstance(theme_style_options, list) or not any(
        isinstance(entry, dict) and str(entry.get("id", "")).strip() == "rookieui_classic"
        for entry in theme_style_options
    ):
        errors.append("prompt-workbench config payload missing expected theme style 'rookieui_classic'.")

    surfaces = providers_payload.get("surfaces")
    if not isinstance(surfaces, dict):
        return None, errors + ["prompt-workbench providers payload missing surfaces."]
    translation_surface = surfaces.get("translation")
    ai_surface = surfaces.get("ai_assist")
    if not isinstance(translation_surface, dict) or not isinstance(ai_surface, dict):
        return None, errors + ["prompt-workbench providers payload missing translation/ai_assist surfaces."]

    translation_shipped = tuple(translation_surface.get("shipped_provider_ids", ()))
    if translation_shipped != PROMPT_WORKBENCH_SHIPPED_TRANSLATION_PROVIDER_IDS:
        errors.append(
            "prompt-workbench translation shipped_provider_ids drifted from the workspace contract."
        )
    ai_shipped = tuple(ai_surface.get("shipped_provider_ids", ()))
    if ai_shipped != PROMPT_WORKBENCH_SHIPPED_AI_PROVIDER_IDS:
        errors.append("prompt-workbench AI assist shipped_provider_ids drifted from the workspace contract.")

    translation_default_provider = str(translation_surface.get("default_provider", "")).strip()
    ai_assist_default_provider = str(ai_surface.get("default_provider", "")).strip()

    def _provider_availability(surface_payload: dict[str, Any], provider_id: str) -> str:
        if not provider_id:
            return "unconfigured"
        providers = surface_payload.get("providers")
        if not isinstance(providers, list):
            return "unavailable"
        for entry in providers:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("provider_id", "")).strip() == provider_id:
                availability = entry.get("availability")
                if isinstance(availability, dict):
                    return str(availability.get("status", "")).strip() or "unavailable"
        return "unavailable"

    return (
        PromptWorkbenchHostContext(
            namespace=PROMPT_WORKBENCH_NAMESPACES[0],
            host_contract_version=str(contract.get("version", "")).strip(),
            local_contract_version=_LOCAL_PROMPT_WORKBENCH_CONTRACT_VERSION,
            translation_default_provider=translation_default_provider,
            translation_default_availability=_provider_availability(translation_surface, translation_default_provider),
            ai_assist_default_provider=ai_assist_default_provider,
            ai_assist_default_availability=_provider_availability(ai_surface, ai_assist_default_provider),
        ),
        errors,
    )


def _validate_prompt_workbench_host_sync(context: PromptWorkbenchHostContext) -> list[str]:
    errors: list[str] = []
    if not context.host_contract_version:
        errors.append("prompt-workbench config payload did not expose contract.version.")
    elif context.host_contract_version != context.local_contract_version:
        errors.append(
            "live host prompt-workbench contract mismatch: "
            f"host='{context.host_contract_version}' workspace='{context.local_contract_version}'."
        )
    return errors


def _validate_prompt_workbench_state_payload(
    namespace: str,
    payload: dict[str, Any],
) -> list[str]:
    probe = LiveRouteContractProbe(
        surface="prompt_tools_state",
        route_path="/rookieui/prompt-tools/state",
        local_contract_version=_LOCAL_PROMPT_WORKBENCH_CONTRACT_VERSION,
    )
    errors = _validate_route_contract_payload(probe, payload)
    if str(payload.get("namespace", "")).strip() != namespace:
        errors.append(f"prompt-workbench state namespace drifted from '{namespace}'.")
    state = payload.get("state")
    if not isinstance(state, dict):
        return errors + ["prompt-workbench state payload missing state object."]
    if str(state.get("namespace", "")).strip() != namespace:
        errors.append("prompt-workbench state.state.namespace drifted from the requested namespace.")
    return errors


def _validate_prompt_workbench_entry_list_payload(
    surface: str,
    namespace: str,
    payload: dict[str, Any],
) -> list[str]:
    probe = LiveRouteContractProbe(
        surface=surface,
        route_path=f"/rookieui/prompt-tools/{surface.split('_')[-1]}",
        local_contract_version=_LOCAL_PROMPT_WORKBENCH_CONTRACT_VERSION,
    )
    errors = _validate_route_contract_payload(probe, payload)
    if str(payload.get("namespace", "")).strip() != namespace:
        errors.append(f"{surface}: namespace drifted from '{namespace}'.")
    items = payload.get("items")
    if not isinstance(items, list):
        errors.append(f"{surface}: items list missing.")
    return errors


def _validate_prompt_workbench_blacklist_payload(payload: dict[str, Any]) -> list[str]:
    probe = LiveRouteContractProbe(
        surface="prompt_tools_blacklist",
        route_path="/rookieui/prompt-tools/blacklist",
        local_contract_version=_LOCAL_PROMPT_WORKBENCH_CONTRACT_VERSION,
    )
    errors = _validate_route_contract_payload(probe, payload)
    blacklist = payload.get("blacklist")
    if not isinstance(blacklist, dict):
        return errors + ["prompt-workbench blacklist payload missing blacklist object."]
    if not isinstance(blacklist.get("enabled"), bool):
        errors.append("prompt-workbench blacklist.enabled was not boolean.")
    if not isinstance(blacklist.get("entries"), list):
        errors.append("prompt-workbench blacklist.entries was not a list.")
    return errors


def _validate_prompt_workbench_catalog_payload(payload: dict[str, Any]) -> list[str]:
    probe = LiveRouteContractProbe(
        surface="prompt_tools_catalog",
        route_path="/rookieui/prompt-tools/catalog",
        local_contract_version=_LOCAL_PROMPT_WORKBENCH_CONTRACT_VERSION,
    )
    errors = _validate_route_contract_payload(probe, payload)
    group_tags = payload.get("group_tags")
    prompt_library = payload.get("prompt_library")
    extra_networks = payload.get("extra_networks")
    if not isinstance(group_tags, dict) or not isinstance(group_tags.get("groups"), list):
        errors.append("prompt-workbench catalog payload missing group_tags.groups.")
    if not isinstance(prompt_library, dict) or not isinstance(prompt_library.get("sections"), list):
        errors.append("prompt-workbench catalog payload missing prompt_library.sections.")
    if not isinstance(extra_networks, dict):
        errors.append("prompt-workbench catalog payload missing extra_networks.")
    else:
        if not isinstance(extra_networks.get("embeddings"), list):
            errors.append("prompt-workbench catalog payload missing extra_networks.embeddings.")
        if not isinstance(extra_networks.get("loras"), list):
            errors.append("prompt-workbench catalog payload missing extra_networks.loras.")
    return errors


def _validate_prompt_workbench_analyze_payload(payload: dict[str, Any]) -> list[str]:
    probe = LiveRouteContractProbe(
        surface="prompt_tools_analyze",
        route_path="/rookieui/prompt-tools/analyze",
        local_contract_version=_LOCAL_PROMPT_WORKBENCH_CONTRACT_VERSION,
    )
    errors = _validate_route_contract_payload(probe, payload)
    prompt_payload = payload.get("prompt")
    negative_payload = payload.get("negative_prompt")
    if not isinstance(prompt_payload, dict) or not isinstance(negative_payload, dict):
        return errors + ["prompt-workbench analyze payload missing prompt/negative_prompt objects."]
    for key in ("raw", "cleaned", "semantics", "metrics"):
        if key not in prompt_payload:
            errors.append(f"prompt-workbench analyze prompt payload missing '{key}'.")
        if key not in negative_payload:
            errors.append(f"prompt-workbench analyze negative payload missing '{key}'.")
    inventory_snapshot = payload.get("inventory_snapshot")
    if not isinstance(inventory_snapshot, dict):
        errors.append("prompt-workbench analyze payload missing inventory_snapshot.")
    return errors


def _validate_prompt_workbench_translate_payload(payload: dict[str, Any]) -> list[str]:
    probe = LiveRouteContractProbe(
        surface="prompt_tools_translate",
        route_path="/rookieui/prompt-tools/translate",
        local_contract_version=_LOCAL_PROMPT_WORKBENCH_CONTRACT_VERSION,
    )
    errors = _validate_route_contract_payload(probe, payload)
    if str(payload.get("provider_id", "")).strip() != "mymemory_free":
        errors.append("prompt-workbench translate did not execute through mymemory_free.")
    if not str(payload.get("translated_text", "")).strip():
        errors.append("prompt-workbench translate returned empty translated_text.")
    return errors


def _validate_prompt_workbench_assist_payload(payload: dict[str, Any]) -> list[str]:
    probe = LiveRouteContractProbe(
        surface="prompt_tools_assist",
        route_path="/rookieui/prompt-tools/assist",
        local_contract_version=_LOCAL_PROMPT_WORKBENCH_CONTRACT_VERSION,
    )
    errors = _validate_route_contract_payload(probe, payload)
    if str(payload.get("provider_id", "")).strip() != "openai":
        errors.append("prompt-workbench AI assist did not execute through openai.")
    if not str(payload.get("generated_prompt", "")).strip():
        errors.append("prompt-workbench AI assist returned empty generated_prompt.")
    return errors


def _validate_xyz_plot_axes_payload(payload: dict[str, Any]) -> list[str]:
    probe = LiveRouteContractProbe(
        surface="xyz_plot_axes",
        route_path="/rookieui/xyz-plot/axes",
        local_contract_version=_LOCAL_XYZ_PLOT_CONTRACT_VERSION,
    )
    errors = _validate_route_contract_payload(probe, payload)
    axes = payload.get("axes")
    if not isinstance(axes, dict):
        return errors + ["xyz-plot axes payload missing axes mapping."]
    for required_axis in ("steps", "cfg_scale", "seed", "checkpoint_name"):
        axis_payload = axes.get(required_axis)
        if not isinstance(axis_payload, dict):
            errors.append(f"xyz-plot axes payload missing '{required_axis}'.")
            continue
        if not axis_payload.get("session_runner_support", False):
            errors.append(f"xyz-plot axis '{required_axis}' was not session-runner ready.")
    denoise_axis = axes.get("denoising_strength")
    if not isinstance(denoise_axis, dict):
        errors.append("xyz-plot axes payload missing 'denoising_strength'.")
    else:
        scopes = denoise_axis.get("mode_scopes")
        if not isinstance(scopes, list) or "img2img" not in scopes:
            errors.append("xyz-plot denoising_strength axis lost img2img scope.")
    return errors


def _build_xyz_plot_host_context(
    models_payload: dict[str, Any],
    axes_payload: dict[str, Any],
) -> tuple[XYZPlotHostContext | None, list[str]]:
    errors = _validate_xyz_plot_axes_payload(axes_payload)
    auxiliary_context = _build_auxiliary_pipeline_context(models_payload)
    return (
        XYZPlotHostContext(
            checkpoint_name=auxiliary_context.checkpoint_name,
            workflow_family=auxiliary_context.workflow_family,
            host_contract_version=_read_nested_text(axes_payload, "contract", "version"),
            local_contract_version=_LOCAL_XYZ_PLOT_CONTRACT_VERSION,
        ),
        errors,
    )


def _validate_xyz_plot_host_sync(context: XYZPlotHostContext) -> list[str]:
    if context.host_contract_version == context.local_contract_version:
        return []
    return [
        "xyz-plot contract mismatch: "
        f"host='{context.host_contract_version or '<missing>'}' "
        f"workspace='{context.local_contract_version}'."
    ]


def _build_xyz_plot_txt2img_estimate_payload(context: XYZPlotHostContext) -> dict[str, Any]:
    return {
        "mode": "txt2img",
        "base_request": {
            "prompt": "rookieui xyz live smoke harbor dusk",
            "negative_prompt": "blurry",
            "checkpoint_name": context.checkpoint_name,
            "width": 512,
            "height": 512,
            "steps": 20,
        },
        "axes": [
            {"axis_id": "steps", "values": "12,20"},
            {"axis_id": "cfg_scale", "values": "5.5,7.0"},
        ],
    }


def _build_xyz_plot_img2img_estimate_payload(context: XYZPlotHostContext) -> dict[str, Any]:
    return {
        "mode": "img2img",
        "base_request": {
            "prompt": "rookieui xyz live smoke portrait cleanup",
            "negative_prompt": "artifact",
            "checkpoint_name": context.checkpoint_name,
            "width": 512,
            "height": 512,
            "steps": 20,
            "denoise_strength": 0.5,
        },
        "axes": [
            {"axis_id": "steps", "values": "10,18"},
            {"axis_id": "denoising_strength", "values": "0.35,0.55"},
        ],
    }


def _validate_xyz_plot_estimate_payload(
    payload: dict[str, Any],
    *,
    mode: str,
    expected_axis_ids: tuple[str, ...],
) -> list[str]:
    probe = LiveRouteContractProbe(
        surface="xyz_plot_estimate",
        route_path="/rookieui/xyz-plot/estimate",
        local_contract_version=_LOCAL_XYZ_PLOT_CONTRACT_VERSION,
        method="POST",
    )
    errors = _validate_route_contract_payload(probe, payload)
    if str(payload.get("mode", "")).strip() != mode:
        errors.append(f"xyz-plot estimate expected mode '{mode}' but got '{payload.get('mode')}'.")
    axes = payload.get("axes")
    if not isinstance(axes, list):
        return errors + ["xyz-plot estimate payload missing axes list."]
    axis_ids = tuple(
        str(entry.get("axis_id", "")).strip()
        for entry in axes
        if isinstance(entry, dict)
    )
    if axis_ids != expected_axis_ids:
        errors.append(f"xyz-plot estimate axis ids drifted from {expected_axis_ids} to {axis_ids}.")
    estimate = payload.get("estimate")
    if not isinstance(estimate, dict):
        return errors + ["xyz-plot estimate payload missing estimate object."]
    if int(estimate.get("cell_count", 0) or 0) != 4:
        errors.append("xyz-plot estimate expected cell_count=4.")
    if int(estimate.get("generated_image_count", 0) or 0) != 4:
        errors.append("xyz-plot estimate expected generated_image_count=4.")
    if not payload.get("can_run", False):
        errors.append("xyz-plot estimate unexpectedly reported can_run=false.")
    if not isinstance(payload.get("warnings"), list):
        errors.append("xyz-plot estimate warnings missing.")
    if not isinstance(payload.get("warning_codes"), list):
        errors.append("xyz-plot estimate warning_codes missing.")
    return errors


def _build_xyz_plot_execute_payload(context: XYZPlotHostContext, client_id: str) -> dict[str, Any]:
    return {
        "mode": "txt2img",
        "client_id": client_id,
        "max_parallel": 1,
        "base_request": {
            "prompt": "rookieui xyz live smoke harbor dusk",
            "negative_prompt": "blurry",
            "checkpoint_name": context.checkpoint_name,
            "width": 512,
            "height": 512,
            "steps": 16,
            "cfg_scale": 6.5,
            "sampler_name": "euler",
            "scheduler_name": "normal",
            "seed": -1,
        },
        "axes": [
            {"axis_id": "steps", "values": "12,16"},
            {"axis_id": "cfg_scale", "values": "5.5,7.0"},
        ],
        "draw_legend": True,
        "include_lone_images": True,
        "include_sub_grids": False,
        "keep_negative_one_seed": False,
        "vary_seeds_x": False,
        "vary_seeds_y": False,
        "vary_seeds_z": False,
        "margin_size": 0,
    }


def _validate_xyz_plot_session_payload(
    payload: dict[str, Any],
    *,
    surface: str,
    expect_session_id: str | None = None,
    expect_client_id: str | None = None,
    require_cells: bool,
) -> list[str]:
    probe = LiveRouteContractProbe(
        surface=surface,
        route_path=f"/rookieui/xyz-plot/{'run' if surface == 'xyz_plot_run' else 'sessions'}",
        local_contract_version=_LOCAL_XYZ_PLOT_CONTRACT_VERSION,
    )
    errors = _validate_route_contract_payload(probe, payload)
    session = payload.get("session")
    if not isinstance(session, dict):
        return errors + [f"{surface}: payload missing session object."]
    session_id = str(session.get("session_id", "")).strip()
    if not session_id:
        errors.append(f"{surface}: session_id missing.")
    if expect_session_id and session_id != expect_session_id:
        errors.append(f"{surface}: expected session_id '{expect_session_id}' but got '{session_id}'.")
    if expect_client_id is not None and str(session.get("client_id", "")).strip() != expect_client_id:
        errors.append(f"{surface}: client_id drifted from '{expect_client_id}'.")
    seed_policy = session.get("seed_policy")
    if not isinstance(seed_policy, dict):
        errors.append(f"{surface}: seed_policy missing.")
    else:
        for key in ("keep_negative_one_seed", "vary_seeds_x", "vary_seeds_y", "vary_seeds_z"):
            if not isinstance(seed_policy.get(key), bool):
                errors.append(f"{surface}: seed_policy.{key} missing or non-boolean.")
    summary = session.get("summary")
    if not isinstance(summary, dict):
        errors.append(f"{surface}: summary missing.")
    else:
        if int(summary.get("total_cells", 0) or 0) != 4:
            errors.append(f"{surface}: expected total_cells=4.")
    axes = session.get("axes")
    if not isinstance(axes, list) or len(axes) != 2:
        errors.append(f"{surface}: expected exactly two configured axes.")
    if require_cells:
        cells = session.get("cells")
        if not isinstance(cells, list) or len(cells) != 4:
            errors.append(f"{surface}: expected four session cells.")
    return errors


def _validate_xyz_plot_session_list_payload(
    payload: dict[str, Any],
    *,
    expect_session_id: str | None,
    expect_client_id: str | None,
) -> list[str]:
    probe = LiveRouteContractProbe(
        surface="xyz_plot_session_list",
        route_path="/rookieui/xyz-plot/sessions",
        local_contract_version=_LOCAL_XYZ_PLOT_CONTRACT_VERSION,
    )
    errors = _validate_route_contract_payload(probe, payload)
    sessions = payload.get("sessions")
    if not isinstance(sessions, list):
        return errors + ["xyz-plot session list missing sessions array."]
    if expect_session_id is None:
        return errors
    matched = next(
        (
            session
            for session in sessions
            if isinstance(session, dict) and str(session.get("session_id", "")).strip() == expect_session_id
        ),
        None,
    )
    if not isinstance(matched, dict):
        errors.append(f"xyz-plot session list did not include '{expect_session_id}'.")
        return errors
    if expect_client_id is not None and str(matched.get("client_id", "")).strip() != expect_client_id:
        errors.append("xyz-plot session list returned a mismatched client_id.")
    return errors


def _validate_xyz_plot_terminal_detail_payload(
    payload: dict[str, Any],
    *,
    session_id: str,
    client_id: str,
) -> list[str]:
    errors = _validate_xyz_plot_session_payload(
        payload,
        surface="xyz_plot_session_detail",
        expect_session_id=session_id,
        expect_client_id=client_id,
        require_cells=True,
    )
    session = payload.get("session")
    if not isinstance(session, dict):
        return errors
    status = str(session.get("status", "")).strip()
    if status != "completed":
        errors.append(f"xyz-plot session detail expected completed status but got '{status}'.")
    summary = session.get("summary")
    if isinstance(summary, dict) and int(summary.get("completed_cells", 0) or 0) != 4:
        errors.append("xyz-plot session detail expected completed_cells=4.")
    results = session.get("results")
    if not isinstance(results, dict):
        return errors + ["xyz-plot session detail missing results object."]
    if str(results.get("status", "")).strip() != "ready":
        errors.append("xyz-plot session detail expected ready results.")
    main_grid = results.get("main_grid")
    if not isinstance(main_grid, dict):
        errors.append("xyz-plot session detail missing main_grid payload.")
    else:
        if not str(main_grid.get("asset_handle", "")).strip():
            errors.append("xyz-plot session detail main_grid.asset_handle missing.")
        if not _read_nested_text(results, "main_grid", "preview_data_url").startswith("data:image/png;base64,"):
            errors.append("xyz-plot session detail main_grid.preview_data_url missing.")
    lone_images = results.get("lone_images")
    if not isinstance(lone_images, list) or len(lone_images) != 4:
        errors.append("xyz-plot session detail expected four lone_images entries.")
    if not isinstance(results.get("sub_grids"), list):
        errors.append("xyz-plot session detail missing sub_grids list.")
    if not isinstance(results.get("warnings"), list):
        errors.append("xyz-plot session detail missing warnings list.")
    seed_policy = session.get("seed_policy")
    if isinstance(seed_policy, dict):
        fixed_base_seed = seed_policy.get("fixed_base_seed")
        if not isinstance(fixed_base_seed, int) or fixed_base_seed < 0:
            errors.append("xyz-plot session detail expected a non-negative fixed_base_seed.")
        cells = session.get("cells")
        if isinstance(cells, list):
            resolved_seeds = [cell.get("resolved_seed") for cell in cells if isinstance(cell, dict)]
            if any(not isinstance(seed, int) for seed in resolved_seeds):
                errors.append("xyz-plot session detail expected integer resolved_seed values for every cell.")
            elif isinstance(fixed_base_seed, int) and any(seed != fixed_base_seed for seed in resolved_seeds):
                errors.append("xyz-plot session detail expected all resolved seeds to match the fixed base seed.")
    return errors


def _poll_xyz_plot_session_until_terminal(
    base_url: str,
    *,
    session_id: str,
    client_id: str,
    request_timeout_seconds: float,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> tuple[dict[str, Any], list[str]]:
    deadline = time.monotonic() + poll_timeout_seconds
    last_payload: dict[str, Any] = {}
    while time.monotonic() < deadline:
        payload = _request_json(
            "GET",
            f"{base_url}/rookieui/xyz-plot/sessions/{urllib.parse.quote(session_id)}?client_id={urllib.parse.quote(client_id)}",
            timeout_seconds=request_timeout_seconds,
        )
        last_payload = payload
        session = payload.get("session")
        if isinstance(session, dict):
            status = str(session.get("status", "")).strip()
            if status in {"completed", "failed", "cancelled"}:
                return payload, []
        time.sleep(poll_interval_seconds)
    return last_payload, [f"xyz-plot session '{session_id}' did not reach terminal state within {poll_timeout_seconds} seconds."]


def _run_prompt_workbench_validation_lane(
    base_url: str,
    *,
    execute: bool,
    request_timeout_seconds: float,
) -> tuple[list[str], list[str]]:
    bootstrap_payload = _load_bootstrap_payload(base_url, request_timeout_seconds)
    routes = bootstrap_payload.get("routes")
    if not isinstance(routes, list) or "/rookieui/prompt-tools/config" not in routes:
        return (
            [
                "prompt-workbench live-host bootstrap did not expose /rookieui/prompt-tools/config; "
                "restart or re-sync the ComfyUI host before closure acceptance."
            ],
            [],
        )
    config_payload = _request_prompt_workbench_json(
        base_url,
        "config",
        timeout_seconds=request_timeout_seconds,
    )
    providers_payload = _request_prompt_workbench_json(
        base_url,
        "providers",
        timeout_seconds=request_timeout_seconds,
    )
    context, context_errors = _build_prompt_workbench_host_context(config_payload, providers_payload)
    if context_errors:
        return context_errors, []
    assert context is not None

    combined_errors = _validate_prompt_workbench_host_sync(context)
    execution_errors: list[str] = []
    namespace = context.namespace

    original_state = _request_prompt_workbench_json(
        base_url,
        "state",
        query={"namespace": namespace},
        timeout_seconds=request_timeout_seconds,
    )
    original_history = _request_prompt_workbench_json(
        base_url,
        "history",
        query={"namespace": namespace},
        timeout_seconds=request_timeout_seconds,
    )
    original_favorites = _request_prompt_workbench_json(
        base_url,
        "favorites",
        query={"namespace": namespace},
        timeout_seconds=request_timeout_seconds,
    )
    original_blacklist = _request_prompt_workbench_json(
        base_url,
        "blacklist",
        timeout_seconds=request_timeout_seconds,
    )
    original_config = config_payload

    combined_errors.extend(_validate_prompt_workbench_state_payload(namespace, original_state))
    combined_errors.extend(_validate_prompt_workbench_entry_list_payload("prompt_tools_history", namespace, original_history))
    combined_errors.extend(
        _validate_prompt_workbench_entry_list_payload("prompt_tools_favorites", namespace, original_favorites)
    )
    combined_errors.extend(_validate_prompt_workbench_blacklist_payload(original_blacklist))

    stage_token = str(int(time.time() * 1000))
    history_item = {
        "label": f"Prompt Workbench Smoke {stage_token}",
        "prompt_text": "masterpiece, city skyline at dusk",
        "tag_tokens": ["masterpiece", "city skyline"],
    }
    favorite_item = {
        "label": f"Favorite Workbench Smoke {stage_token}",
        "prompt_text": "best quality, harbor lights",
        "tag_tokens": ["best quality", "harbor lights"],
    }
    target_state = {
        "workbench_open": True,
        "active_panel": "assist",
        "draft_prompt": f"masterpiece, stage token {stage_token}",
        "selected_entry_id": f"entry-{stage_token}",
    }
    target_blacklist = {
        "enabled": True,
        "entries": [f"bad-hands-{stage_token}", f"bad-feet-{stage_token}"],
    }
    target_config = {
        "language": "zh-TW",
        "theme_style": "rookieui_graphite",
        "translation": {
            "default_provider": "mymemory_free",
            "providers": {
                "mymemory_free": {
                    "base_url": "https://api.mymemory.translated.net/get",
                    "timeout_seconds": 15,
                }
            },
        },
    }

    try:
        updated_config = _request_prompt_workbench_json(
            base_url,
            "config",
            method="POST",
            payload={"config": target_config},
            timeout_seconds=request_timeout_seconds,
        )
        combined_errors.extend(_validate_route_contract_payload(
            LiveRouteContractProbe(
                surface="prompt_tools_config",
                route_path="/rookieui/prompt-tools/config",
                local_contract_version=_LOCAL_PROMPT_WORKBENCH_CONTRACT_VERSION,
            ),
            updated_config,
        ))
        updated_state = _request_prompt_workbench_json(
            base_url,
            "state",
            method="POST",
            payload={"namespace": namespace, "state": target_state},
            timeout_seconds=request_timeout_seconds,
        )
        combined_errors.extend(_validate_prompt_workbench_state_payload(namespace, updated_state))
        state_payload = updated_state.get("state")
        if isinstance(state_payload, dict):
            for key, value in target_state.items():
                if state_payload.get(key) != value:
                    combined_errors.append(f"prompt-workbench state update did not persist '{key}'.")

        updated_history = _request_prompt_workbench_json(
            base_url,
            "history",
            method="POST",
            payload={"namespace": namespace, "action": "push", "item": history_item},
            timeout_seconds=request_timeout_seconds,
        )
        combined_errors.extend(_validate_prompt_workbench_entry_list_payload("prompt_tools_history", namespace, updated_history))
        history_items = updated_history.get("items")
        if not isinstance(history_items, list) or not any(
            isinstance(item, dict) and item.get("prompt_text") == history_item["prompt_text"] for item in history_items
        ):
            combined_errors.append("prompt-workbench history update did not persist the injected prompt entry.")

        updated_favorites = _request_prompt_workbench_json(
            base_url,
            "favorites",
            method="POST",
            payload={"namespace": namespace, "action": "push", "item": favorite_item},
            timeout_seconds=request_timeout_seconds,
        )
        combined_errors.extend(
            _validate_prompt_workbench_entry_list_payload("prompt_tools_favorites", namespace, updated_favorites)
        )
        favorite_items = updated_favorites.get("items")
        if not isinstance(favorite_items, list) or not any(
            isinstance(item, dict) and item.get("prompt_text") == favorite_item["prompt_text"] for item in favorite_items
        ):
            combined_errors.append("prompt-workbench favorites update did not persist the injected prompt entry.")

        updated_blacklist = _request_prompt_workbench_json(
            base_url,
            "blacklist",
            method="POST",
            payload={"blacklist": target_blacklist},
            timeout_seconds=request_timeout_seconds,
        )
        combined_errors.extend(_validate_prompt_workbench_blacklist_payload(updated_blacklist))
        blacklist_payload = updated_blacklist.get("blacklist")
        if not isinstance(blacklist_payload, dict) or blacklist_payload.get("entries") != target_blacklist["entries"]:
            combined_errors.append("prompt-workbench blacklist update did not persist the injected entries.")

        catalog_payload = _request_prompt_workbench_json(
            base_url,
            "catalog",
            query={"language": "en"},
            timeout_seconds=request_timeout_seconds,
        )
        combined_errors.extend(_validate_prompt_workbench_catalog_payload(catalog_payload))

        analyze_payload = _request_prompt_workbench_json(
            base_url,
            "analyze",
            method="POST",
            payload={
                "prompt": "masterpiece, <lora:demo:0.8>, city skyline at dusk",
                "negative_prompt": "blurry, low quality",
                "steps": 28,
            },
            timeout_seconds=request_timeout_seconds,
        )
        combined_errors.extend(_validate_prompt_workbench_analyze_payload(analyze_payload))

        if execute and not combined_errors:
            translate_payload = _request_prompt_workbench_json(
                base_url,
                "translate",
                method="POST",
                payload={
                    "provider": "mymemory_free",
                    "from_lang": "auto",
                    "to_lang": "en",
                    "text": "city skyline at dusk",
                },
                timeout_seconds=request_timeout_seconds,
            )
            execution_errors.extend(_validate_prompt_workbench_translate_payload(translate_payload))

            if not context.ai_assist_default_provider:
                status_code, assist_payload = _request_prompt_workbench_json_with_status(
                    base_url,
                    "assist",
                    method="POST",
                    payload={"image_description": "city skyline at dusk"},
                    timeout_seconds=request_timeout_seconds,
                )
                if status_code != 400:
                    execution_errors.append(
                        f"prompt-workbench AI assist expected 400 for unconfigured provider but got {status_code}."
                    )
                if _read_nested_text(assist_payload, "status") != "invalid-request":
                    execution_errors.append("prompt-workbench AI assist unconfigured path lost invalid-request truthfulness.")
                if "No prompt-workbench AI assist provider is configured." not in _read_nested_text(
                    assist_payload, "detail"
                ):
                    execution_errors.append("prompt-workbench AI assist unconfigured detail drifted.")
            elif context.ai_assist_default_availability == "ready":
                assist_payload = _request_prompt_workbench_json(
                    base_url,
                    "assist",
                    method="POST",
                    payload={
                        "image_description": "city skyline at dusk",
                        "language": "en",
                        "theme_style": "rookieui_graphite",
                    },
                    timeout_seconds=request_timeout_seconds,
                )
                execution_errors.extend(_validate_prompt_workbench_assist_payload(assist_payload))
            elif context.ai_assist_default_availability == "configuration_required":
                status_code, assist_payload = _request_prompt_workbench_json_with_status(
                    base_url,
                    "assist",
                    method="POST",
                    payload={"image_description": "city skyline at dusk"},
                    timeout_seconds=request_timeout_seconds,
                )
                if status_code != 502:
                    execution_errors.append(
                        f"prompt-workbench AI assist expected 502 for configuration-required provider but got {status_code}."
                    )
                if _read_nested_text(assist_payload, "status") != "provider-error":
                    execution_errors.append("prompt-workbench AI assist configuration-required path lost provider-error truthfulness.")
                if "OpenAI-compatible execution requires api_key and model." not in _read_nested_text(
                    assist_payload, "detail"
                ):
                    execution_errors.append("prompt-workbench AI assist configuration-required detail drifted.")
            else:
                execution_errors.append(
                    f"prompt-workbench AI assist default provider availability '{context.ai_assist_default_availability}' is not covered by the live lane."
                )
    finally:
        _request_prompt_workbench_json(
            base_url,
            "config",
            method="POST",
            payload={"config": original_config.get("config", {})},
            timeout_seconds=request_timeout_seconds,
        )
        _request_prompt_workbench_json(
            base_url,
            "state",
            method="POST",
            payload={"namespace": namespace, "state": original_state.get("state", {})},
            timeout_seconds=request_timeout_seconds,
        )
        _request_prompt_workbench_json(
            base_url,
            "history",
            method="POST",
            payload={"namespace": namespace, "action": "replace", "items": original_history.get("items", [])},
            timeout_seconds=request_timeout_seconds,
        )
        _request_prompt_workbench_json(
            base_url,
            "favorites",
            method="POST",
            payload={"namespace": namespace, "action": "replace", "items": original_favorites.get("items", [])},
            timeout_seconds=request_timeout_seconds,
        )
        _request_prompt_workbench_json(
            base_url,
            "blacklist",
            method="POST",
            payload={"blacklist": original_blacklist.get("blacklist", {})},
            timeout_seconds=request_timeout_seconds,
        )

    return combined_errors, execution_errors


def _run_xyz_plot_validation_lane(
    base_url: str,
    models_payload: dict[str, Any],
    *,
    execute: bool,
    request_timeout_seconds: float,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> tuple[list[str], list[str]]:
    bootstrap_payload = _load_bootstrap_payload(base_url, request_timeout_seconds)
    routes = bootstrap_payload.get("routes")
    if not isinstance(routes, list) or "/rookieui/xyz-plot/axes" not in routes:
        return (
            [
                "xyz-plot live-host bootstrap did not expose /rookieui/xyz-plot/axes; "
                "restart or re-sync the ComfyUI host before closure acceptance."
            ],
            [],
        )

    axes_payload = _load_xyz_plot_axes_payload(base_url, request_timeout_seconds)
    context, context_errors = _build_xyz_plot_host_context(models_payload, axes_payload)
    if context_errors:
        return context_errors, []
    assert context is not None

    combined_errors = _validate_xyz_plot_host_sync(context)
    txt2img_estimate_payload = _request_json(
        "POST",
        f"{base_url}/rookieui/xyz-plot/estimate",
        payload=_build_xyz_plot_txt2img_estimate_payload(context),
        timeout_seconds=request_timeout_seconds,
    )
    combined_errors.extend(
        _validate_xyz_plot_estimate_payload(
            txt2img_estimate_payload,
            mode="txt2img",
            expected_axis_ids=("steps", "cfg_scale"),
        )
    )
    img2img_estimate_payload = _request_json(
        "POST",
        f"{base_url}/rookieui/xyz-plot/estimate",
        payload=_build_xyz_plot_img2img_estimate_payload(context),
        timeout_seconds=request_timeout_seconds,
    )
    combined_errors.extend(
        _validate_xyz_plot_estimate_payload(
            img2img_estimate_payload,
            mode="img2img",
            expected_axis_ids=("steps", "denoising_strength"),
        )
    )

    list_payload = _request_json(
        "GET",
        f"{base_url}/rookieui/xyz-plot/sessions?client_id=rookieui-live-xyz-list-probe",
        timeout_seconds=request_timeout_seconds,
    )
    combined_errors.extend(
        _validate_xyz_plot_session_list_payload(
            list_payload,
            expect_session_id=None,
            expect_client_id=None,
        )
    )

    execution_errors: list[str] = []
    if execute and not combined_errors:
        client_id = f"rookieui-live-xyz-{context.workflow_family}-{int(time.time() * 1000)}"
        run_payload = _request_json(
            "POST",
            f"{base_url}/rookieui/xyz-plot/run",
            payload=_build_xyz_plot_execute_payload(context, client_id),
            timeout_seconds=request_timeout_seconds,
        )
        execution_errors.extend(
            _validate_xyz_plot_session_payload(
                run_payload,
                surface="xyz_plot_run",
                expect_session_id=None,
                expect_client_id=client_id,
                require_cells=True,
            )
        )
        session_payload = run_payload.get("session")
        if not isinstance(session_payload, dict):
            execution_errors.append("xyz-plot run payload missing session object.")
            return combined_errors, execution_errors
        session_id = str(session_payload.get("session_id", "")).strip()
        cells = session_payload.get("cells")
        first_prompt_id = ""
        if isinstance(cells, list) and cells and isinstance(cells[0], dict):
            first_prompt_id = str(cells[0].get("prompt_id", "")).strip()
        if not first_prompt_id:
            execution_errors.append("xyz-plot run payload did not submit the first cell.")
            return combined_errors, execution_errors

        list_payload = _request_json(
            "GET",
            f"{base_url}/rookieui/xyz-plot/sessions?client_id={urllib.parse.quote(client_id)}",
            timeout_seconds=request_timeout_seconds,
        )
        execution_errors.extend(
            _validate_xyz_plot_session_list_payload(
                list_payload,
                expect_session_id=session_id,
                expect_client_id=client_id,
            )
        )
        if execution_errors:
            return combined_errors, execution_errors

        terminal_payload, poll_errors = _poll_xyz_plot_session_until_terminal(
            base_url,
            session_id=session_id,
            client_id=client_id,
            request_timeout_seconds=request_timeout_seconds,
            poll_timeout_seconds=poll_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        execution_errors.extend(poll_errors)
        if not poll_errors:
            execution_errors.extend(
                _validate_xyz_plot_terminal_detail_payload(
                    terminal_payload,
                    session_id=session_id,
                    client_id=client_id,
                )
            )

    return combined_errors, execution_errors


def _validate_extras_execution_response(response_payload: dict[str, Any]) -> list[str]:
    probe = LiveRouteContractProbe(
        surface="extras_run",
        route_path="/rookieui/extras/run",
        local_contract_version=EXTRAS_CONTRACT_VERSION,
    )
    errors = _validate_route_contract_payload(probe, response_payload)
    if response_payload.get("mode") != "single_image":
        errors.append(f"extras: expected mode 'single_image' but got '{response_payload.get('mode')}'.")

    normalized_request = response_payload.get("normalized_request")
    if not isinstance(normalized_request, dict):
        errors.append("extras: response missing normalized_request.")
        return errors
    if normalized_request.get("scale_mode") != "scale_to":
        errors.append("extras: normalized_request.scale_mode did not stay 'scale_to'.")
    if normalized_request.get("target_width") != 128 or normalized_request.get("target_height") != 160:
        errors.append("extras: normalized_request target dimensions did not match the live smoke payload.")
    if normalized_request.get("face_restoration") != "codeformer":
        errors.append("extras: normalized_request.face_restoration did not retain 'codeformer'.")
    if not bool(normalized_request.get("color_correction")):
        errors.append("extras: normalized_request.color_correction was not true.")

    warnings = response_payload.get("warnings")
    if not isinstance(warnings, list) or not any("without face restoration" in str(warning).lower() for warning in warnings):
        errors.append("extras: guarded face-restoration warning was missing.")

    output_assets = response_payload.get("output_assets")
    preview_asset = str(response_payload.get("preview_asset", "")).strip()
    preview_data_url = str(response_payload.get("preview_data_url", "")).strip()
    if not isinstance(output_assets, list) or not output_assets:
        errors.append("extras: expected at least one output asset.")
    if not preview_asset:
        errors.append("extras: preview_asset was empty.")
    elif isinstance(output_assets, list) and preview_asset not in output_assets:
        errors.append("extras: preview_asset was not included in output_assets.")
    if not preview_data_url.startswith("data:image/png;base64,"):
        errors.append("extras: preview_data_url was missing an inline PNG preview.")
    return errors


def _validate_pnginfo_parse_response(case: LivePNGInfoCase, response_payload: dict[str, Any]) -> list[str]:
    probe = LiveRouteContractProbe(
        surface="pnginfo_parse_inspect",
        route_path="/rookieui/pnginfo/parse",
        local_contract_version=PNGINFO_CONTRACT_VERSION,
    )
    errors = _validate_route_contract_payload(probe, response_payload)
    if response_payload.get("source_type") != case.expected_source_type:
        errors.append(
            f"{case.case_id}: expected source_type '{case.expected_source_type}' but got "
            f"'{response_payload.get('source_type')}'."
        )
    if response_payload.get("target_form") != case.expected_target_form:
        errors.append(
            f"{case.case_id}: expected target_form '{case.expected_target_form}' but got "
            f"'{response_payload.get('target_form')}'."
        )
    apply_targets = response_payload.get("apply_targets")
    if list(case.expected_apply_targets) != (apply_targets if isinstance(apply_targets, list) else []):
        errors.append(
            f"{case.case_id}: expected apply_targets {list(case.expected_apply_targets)} but got '{apply_targets}'."
        )
    if not str(response_payload.get("asset_handle", "")).strip():
        errors.append(f"{case.case_id}: asset_handle was empty.")

    warnings = response_payload.get("warnings")
    if case.expected_warning_fragment:
        if not isinstance(warnings, list) or not any(
            case.expected_warning_fragment.lower() in str(warning).lower() for warning in warnings
        ):
            errors.append(
                f"{case.case_id}: warning fragment '{case.expected_warning_fragment}' was missing."
            )

    payload = response_payload.get("payload")
    if case.expected_target_form == "inspect_only":
        if payload != {}:
            errors.append(f"{case.case_id}: inspect-only payload was expected to stay empty.")
        return errors

    if not isinstance(payload, dict):
        errors.append(f"{case.case_id}: parse response missing payload.")
        return errors
    if case.expected_prompt and payload.get("prompt") != case.expected_prompt:
        errors.append(
            f"{case.case_id}: expected payload.prompt '{case.expected_prompt}' but got '{payload.get('prompt')}'."
        )
    if case.expected_negative_prompt and payload.get("negative_prompt") != case.expected_negative_prompt:
        errors.append(
            f"{case.case_id}: expected payload.negative_prompt '{case.expected_negative_prompt}' but got '{payload.get('negative_prompt')}'."
        )
    if case.expected_profile and payload.get("profile") != case.expected_profile:
        errors.append(
            f"{case.case_id}: expected payload.profile '{case.expected_profile}' but got '{payload.get('profile')}'."
        )
    if case.expected_checkpoint_name and payload.get("checkpoint_name") != case.expected_checkpoint_name:
        errors.append(
            f"{case.case_id}: expected payload.checkpoint_name '{case.expected_checkpoint_name}' but got '{payload.get('checkpoint_name')}'."
        )

    missing_inputs = response_payload.get("missing_inputs")
    if not isinstance(missing_inputs, list):
        errors.append(f"{case.case_id}: response missing missing_inputs list.")
        missing_inputs = []
    for expected_field in case.expected_missing_inputs:
        if expected_field not in missing_inputs:
            errors.append(f"{case.case_id}: expected missing_inputs to include '{expected_field}'.")
    return errors


def _validate_pnginfo_apply_back_response(
    case: LivePNGInfoCase,
    response_payload: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    submission = response_payload.get("submission")
    if not isinstance(submission, dict) or submission.get("mode") != "dry-run":
        errors.append(f"{case.case_id}: apply-back expected dry-run submission payload.")
    if case.expected_workflow_kind and response_payload.get("workflow_kind") != case.expected_workflow_kind:
        errors.append(
            f"{case.case_id}: expected workflow_kind '{case.expected_workflow_kind}' but got "
            f"'{response_payload.get('workflow_kind')}'."
        )
    normalized_request = response_payload.get("normalized_request")
    if not isinstance(normalized_request, dict):
        errors.append(f"{case.case_id}: apply-back response missing normalized_request.")
        return errors
    if normalized_request.get("prompt") != case.expected_prompt:
        errors.append(f"{case.case_id}: apply-back prompt did not match parsed PNG Info payload.")
    if normalized_request.get("negative_prompt") != case.expected_negative_prompt:
        errors.append(f"{case.case_id}: apply-back negative prompt did not match parsed PNG Info payload.")
    if case.expected_checkpoint_name and normalized_request.get("checkpoint_name") != case.expected_checkpoint_name:
        errors.append(f"{case.case_id}: apply-back checkpoint_name drifted from the parsed PNG Info payload.")
    return errors


def _validate_queue_snapshot_response(
    response_payload: dict[str, Any],
    *,
    prompt_id: str,
    allowed_statuses: tuple[str, ...],
    require_visible_job: bool = True,
    expected_queue_remaining: int | None = None,
) -> list[str]:
    probe = LiveRouteContractProbe(
        surface="queue_snapshot_and_job_lookup",
        route_path="/rookieui/queue",
        local_contract_version=QUEUE_CONTRACT_VERSION,
    )
    errors = _validate_route_contract_payload(probe, response_payload)
    if response_payload.get("source") != "host":
        errors.append(f"queue snapshot: expected source 'host' but got '{response_payload.get('source')}'.")
    queue_remaining = response_payload.get("queue_remaining")
    if not isinstance(queue_remaining, int):
        errors.append("queue snapshot: queue_remaining was not an integer.")
    elif expected_queue_remaining is not None and queue_remaining != expected_queue_remaining:
        errors.append(
            f"queue snapshot: expected queue_remaining={expected_queue_remaining} but got {queue_remaining}."
        )
    jobs = response_payload.get("jobs")
    if not isinstance(jobs, list):
        errors.append("queue snapshot: jobs list missing.")
        return errors
    if not require_visible_job:
        return errors
    job = next((entry for entry in jobs if isinstance(entry, dict) and entry.get("id") == prompt_id), None)
    if not isinstance(job, dict):
        errors.append(f"queue snapshot: job '{prompt_id}' was not visible in the client-scoped snapshot.")
        return errors
    status = str(job.get("status", "")).strip().lower()
    if status not in allowed_statuses:
        errors.append(f"queue snapshot: job '{prompt_id}' had unexpected status '{status}'.")
    return errors


def _validate_queue_job_response(response_payload: dict[str, Any], *, prompt_id: str) -> list[str]:
    probe = LiveRouteContractProbe(
        surface="queue_snapshot_and_job_lookup",
        route_path=f"/rookieui/queue/{prompt_id}",
        local_contract_version=QUEUE_CONTRACT_VERSION,
    )
    errors = _validate_route_contract_payload(probe, response_payload)
    if response_payload.get("source") != "host":
        errors.append(f"queue job: expected source 'host' but got '{response_payload.get('source')}'.")
    job = response_payload.get("job")
    if not isinstance(job, dict):
        errors.append(f"queue job: expected job payload for '{prompt_id}'.")
        return errors
    if job.get("id") != prompt_id:
        errors.append(f"queue job: expected id '{prompt_id}' but got '{job.get('id')}'.")
    if str(job.get("status", "")).strip().lower() != "completed":
        errors.append(f"queue job: expected completed status but got '{job.get('status')}'.")
    reusable_outputs = job.get("reusable_outputs")
    if not isinstance(reusable_outputs, list) or not reusable_outputs:
        errors.append("queue job: completed job did not expose reusable_outputs.")
    queue_remaining = response_payload.get("queue_remaining")
    if not isinstance(queue_remaining, int):
        errors.append("queue job: queue_remaining was not an integer.")
    return errors


def _prefix_errors(prefix: str, errors: list[str]) -> list[str]:
    return [f"{prefix}: {error}" for error in errors]


def _run_shared_queue_post_state_smoke(
    base_url: str,
    *,
    lane_label: str,
    submit_result: dict[str, Any],
    client_id: str,
    request_timeout_seconds: float,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> list[str]:
    submission = submit_result.get("submission") if isinstance(submit_result, dict) else None
    if not isinstance(submission, dict) or not bool(submission.get("accepted")):
        return [f"{lane_label}: submit failed, expected accepted submission payload."]
    prompt_id = str(submission.get("prompt_id", "")).strip()
    if not prompt_id:
        return [f"{lane_label}: submit missing prompt_id."]

    errors: list[str] = []
    snapshot_payload = _poll_queue_snapshot_until_job_visible(
        base_url,
        prompt_id=prompt_id,
        client_id=client_id,
        request_timeout_seconds=request_timeout_seconds,
        poll_timeout_seconds=poll_timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )
    errors.extend(
        _prefix_errors(
            lane_label,
            _validate_queue_snapshot_response(
                snapshot_payload,
                prompt_id=prompt_id,
                allowed_statuses=("pending", "in_progress", "completed"),
            ),
        )
    )

    job = _poll_queue_job_until_terminal(
        base_url,
        prompt_id,
        client_id,
        request_timeout_seconds=request_timeout_seconds,
        poll_timeout_seconds=poll_timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )
    terminal_status = str(job.get("status", "")).strip().lower()
    if terminal_status != "completed":
        errors.append(f"{lane_label}: terminal status was '{terminal_status}'.")

    encoded_prompt_id = urllib.parse.quote(prompt_id, safe="")
    encoded_client_id = urllib.parse.quote(client_id, safe="")
    job_payload = _request_json(
        "GET",
        f"{base_url}/rookieui/queue/{encoded_prompt_id}?client_id={encoded_client_id}",
        timeout_seconds=request_timeout_seconds,
    )
    errors.extend(_prefix_errors(lane_label, _validate_queue_job_response(job_payload, prompt_id=prompt_id)))
    final_snapshot = _request_json(
        "GET",
        f"{base_url}/rookieui/queue?client_id={encoded_client_id}",
        timeout_seconds=request_timeout_seconds,
    )
    errors.extend(
        _prefix_errors(
            lane_label,
            _validate_queue_snapshot_response(
                final_snapshot,
                prompt_id=prompt_id,
                allowed_statuses=("completed",),
                require_visible_job=False,
                expected_queue_remaining=0,
            ),
        )
    )
    return errors


def _run_extras_execution_smoke(base_url: str, *, request_timeout_seconds: float) -> list[str]:
    response_payload = _request_json(
        "POST",
        f"{base_url}/rookieui/extras/run",
        payload=_build_extras_smoke_payload(),
        timeout_seconds=request_timeout_seconds,
    )
    return _validate_extras_execution_response(response_payload)


def _run_pnginfo_dry_run_smoke(
    base_url: str,
    context: AuxiliaryPipelineContext,
    *,
    request_timeout_seconds: float,
) -> tuple[list[str], LivePNGInfoCase | None, dict[str, Any] | None]:
    errors: list[str] = []
    execute_case: LivePNGInfoCase | None = None
    execute_payload: dict[str, Any] | None = None
    for case in _build_pnginfo_live_cases(context):
        response_payload = _request_json(
            "POST",
            f"{base_url}/rookieui/pnginfo/parse",
            payload={"image_data": case.image_data},
            timeout_seconds=request_timeout_seconds,
        )
        errors.extend(_validate_pnginfo_parse_response(case, response_payload))
        if not case.apply_back_route:
            continue
        parsed_payload = response_payload.get("payload")
        if not isinstance(parsed_payload, dict):
            errors.append(f"{case.case_id}: parse response did not expose payload for apply-back.")
            continue
        apply_response = _request_json(
            "POST",
            f"{base_url}{case.apply_back_route}",
            payload={**parsed_payload, "dry_run": True},
            timeout_seconds=request_timeout_seconds,
        )
        errors.extend(_validate_pnginfo_apply_back_response(case, apply_response))
        execute_case = case
        execute_payload = dict(parsed_payload)
    return errors, execute_case, execute_payload


def _poll_queue_snapshot_until_job_visible(
    base_url: str,
    *,
    prompt_id: str,
    client_id: str,
    request_timeout_seconds: float,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> dict[str, Any]:
    deadline = time.time() + poll_timeout_seconds
    encoded_client_id = urllib.parse.quote(client_id, safe="")
    queue_url = f"{base_url}/rookieui/queue?client_id={encoded_client_id}"
    last_payload: dict[str, Any] = {}
    while time.time() < deadline:
        payload = _request_json("GET", queue_url, timeout_seconds=request_timeout_seconds)
        last_payload = payload
        jobs = payload.get("jobs")
        if isinstance(jobs, list):
            matched = next((entry for entry in jobs if isinstance(entry, dict) and entry.get("id") == prompt_id), None)
            if isinstance(matched, dict):
                return payload
        time.sleep(max(poll_interval_seconds, 0.1))
    raise RuntimeError(
        f"Queue snapshot did not expose prompt '{prompt_id}' for client '{client_id}' within {poll_timeout_seconds:.1f}s."
    )


def _run_auxiliary_queue_execute_smoke(
    base_url: str,
    *,
    case: LivePNGInfoCase,
    parsed_payload: dict[str, Any],
    request_timeout_seconds: float,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> list[str]:
    if not case.apply_back_route:
        return [f"{case.case_id}: execute requested without an apply-back route."]
    client_id = f"rookieui-live-auxiliary-{int(time.time() * 1000)}"
    submit_result = _request_json(
        "POST",
        f"{base_url}{case.apply_back_route}",
        payload={**parsed_payload, "client_id": client_id},
        timeout_seconds=request_timeout_seconds,
    )
    return _run_shared_queue_post_state_smoke(
        base_url,
        lane_label=f"{case.case_id}: auxiliary execute",
        submit_result=submit_result,
        client_id=client_id,
        request_timeout_seconds=request_timeout_seconds,
        poll_timeout_seconds=poll_timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )


def _iter_string_list(payload: object, key: str) -> list[str]:
    if not isinstance(payload, dict):
        return []
    values = payload.get(key)
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if isinstance(value, str) and str(value).strip()]


def _select_checkpoint_by_keywords(
    checkpoints: list[str],
    *,
    prefix: str,
    keywords: tuple[str, ...] = (),
) -> str:
    normalized_prefix = prefix.lower()
    candidates = [selector for selector in checkpoints if selector.lower().startswith(normalized_prefix)]
    if not candidates:
        return ""
    if keywords:
        for keyword in keywords:
            lowered_keyword = keyword.lower()
            for selector in candidates:
                if lowered_keyword in selector.lower():
                    return selector
    return candidates[0]


def _first_non_empty_contract_version(*payloads: dict[str, Any]) -> str:
    for payload in payloads:
        version = _read_nested_text(payload, "contract", "version")
        if version:
            return version
    return ""


def _iter_controlnet_type_models(entry: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    raw_models = entry.get("model_list")
    if isinstance(raw_models, list):
        for candidate in raw_models:
            normalized = str(candidate).strip()
            if normalized and normalized not in candidates:
                candidates.append(normalized)
    default_model = str(entry.get("default_model", "")).strip()
    if default_model and default_model not in candidates:
        candidates.insert(0, default_model)
    return candidates


def _controlnet_asset_tokens(asset_name: str) -> set[str]:
    stem = Path(str(asset_name).strip()).stem.lower()
    for separator in ("\\", "/", "-", "_", ".", "(", ")", "[", "]"):
        stem = stem.replace(separator, " ")
    return {token for token in stem.split() if token}


def _is_sd15_control_model_name(model_name: str) -> bool:
    lowered = str(model_name).strip().lower()
    return any(marker in lowered for marker in _CONTROLNET_SD15_MODEL_MARKERS)


def _is_sdxl_control_model_name(model_name: str) -> bool:
    lowered = str(model_name).strip().lower()
    if any(marker in lowered for marker in _CONTROLNET_SDXL_MODEL_MARKERS):
        return True
    tokens = _controlnet_asset_tokens(lowered)
    return "sdxl" in tokens or "xl" in tokens


def _prefer_controlnet_model(candidates: list[str]) -> str:
    if not candidates:
        return ""
    return candidates[0]


def _select_controlnet_checkpoint(
    checkpoints: list[str],
    preferred_profiles: list[str],
) -> tuple[str, str, str] | None:
    profile_keywords = {
        "pony": ("pony",),
        "illustrious": ("illustrious", "illu"),
        "noob": ("noob",),
        "sdxl": (),
    }
    for profile_id in preferred_profiles:
        if profile_id == "sd15":
            checkpoint_name = _select_checkpoint_by_keywords(checkpoints, prefix="SD15\\")
            if checkpoint_name:
                return profile_id, checkpoint_name, "sd15"
            continue
        if profile_id in _SDXL_PROMPT_PARITY_PROFILES:
            checkpoint_name = _select_checkpoint_by_keywords(
                checkpoints,
                prefix="SDXL\\",
                keywords=profile_keywords.get(profile_id, ()),
            )
            if checkpoint_name:
                return profile_id, checkpoint_name, "sdxl"
    return None


def _select_controlnet_model(
    entry: dict[str, Any],
    global_model_list: list[str],
    *,
    base_family: str,
) -> str:
    candidates = _iter_controlnet_type_models(entry)
    if global_model_list:
        known_models = set(global_model_list)
        candidates = [candidate for candidate in candidates if candidate in known_models]
    if not candidates:
        return ""

    if base_family == "sd15":
        explicit_sd15_models = [candidate for candidate in candidates if _is_sd15_control_model_name(candidate)]
        if explicit_sd15_models:
            return _prefer_controlnet_model(explicit_sd15_models)
        return ""

    explicit_sdxl_models = [candidate for candidate in candidates if _is_sdxl_control_model_name(candidate)]
    if explicit_sdxl_models:
        return _prefer_controlnet_model(explicit_sdxl_models)

    non_sd15_models = [candidate for candidate in candidates if not _is_sd15_control_model_name(candidate)]
    if non_sd15_models:
        return _prefer_controlnet_model(non_sd15_models)
    return ""


def _build_controlnet_host_context(
    models_payload: dict[str, Any],
    model_list_payload: dict[str, Any],
    module_list_payload: dict[str, Any],
    control_types_payload: dict[str, Any],
    preferred_profiles: list[str],
) -> tuple[ControlNetHostContext | None, list[str]]:
    errors: list[str] = []
    checkpoints = _iter_string_list(models_payload, "checkpoints")

    model_list = _iter_string_list(model_list_payload, "model_list")
    module_list = _iter_string_list(module_list_payload, "module_list")
    control_types = control_types_payload.get("control_types")
    if not isinstance(control_types, dict):
        errors.append("live host /rookieui/controlnet/control_types payload did not expose a control_types mapping.")
        control_types = {}

    host_versions = {
        label: _read_nested_text(payload, "contract", "version")
        for label, payload in (
            ("model_list", model_list_payload),
            ("module_list", module_list_payload),
            ("control_types", control_types_payload),
        )
    }
    if not all(host_versions.values()):
        errors.append("live host ControlNet payloads did not expose integrated contract.version across model/module/type routes.")
    unique_versions = {version for version in host_versions.values() if version}
    if len(unique_versions) > 1:
        errors.append(
            "live host ControlNet routes reported drifted contract versions: "
            + ", ".join(f"{label}={version}" for label, version in host_versions.items())
            + "."
        )

    preferred_types = ("Canny", "Depth", "Lineart", "SoftEdge", "OpenPose", "Scribble", "Tile")
    candidate: tuple[str, str, str, str, str, str] | None = None
    ordered_types = list(preferred_types) + [
        key for key in control_types.keys() if isinstance(key, str) and key not in preferred_types
    ]
    resolved_profiles = [profile_id for profile_id in preferred_profiles if profile_id in _CONTROLNET_VALIDATION_PROFILES]
    checkpoint_missing = True
    for profile_id in resolved_profiles:
        checkpoint_selection = _select_controlnet_checkpoint(checkpoints, [profile_id])
        if checkpoint_selection is None:
            continue
        checkpoint_missing = False
        _, checkpoint_name, base_family = checkpoint_selection
        for control_type in ordered_types:
            entry = control_types.get(control_type)
            if not isinstance(entry, dict):
                continue
            default_module = str(entry.get("default_option", "")).strip()
            if not default_module or default_module == "none":
                continue
            if module_list and default_module not in module_list:
                continue
            selected_model = _select_controlnet_model(entry, model_list, base_family=base_family)
            if not selected_model:
                continue
            candidate = (profile_id, checkpoint_name, base_family, control_type, default_module, selected_model)
            break
        if candidate is not None:
            break

    if checkpoint_missing:
        errors.append(
            "live host did not expose any checkpoint selectors for the requested ControlNet validation profiles: "
            f"{', '.join(resolved_profiles)}."
        )

    if candidate is None:
        errors.append(
            "live host did not expose any usable non-'none' ControlNet control type with a profile-compatible model."
        )

    context = None
    if not errors and candidate is not None:
        profile_id, checkpoint_name, base_family, control_type, module_name, model_name = candidate
        context = ControlNetHostContext(
            profile_id=profile_id,
            checkpoint_name=checkpoint_name,
            base_family=base_family,
            control_type=control_type,
            module_name=module_name,
            model_name=model_name,
            host_contract_version=_first_non_empty_contract_version(
                model_list_payload,
                module_list_payload,
                control_types_payload,
            ),
            local_contract_version=_LOCAL_CONTROLNET_CONTRACT_VERSION,
        )
    return context, errors


def _build_controlnet_txt2img_defaults(profile_id: str, checkpoint_name: str) -> dict[str, Any]:
    profile = get_parity_profile(profile_id)
    return {
        "prompt": "city skyline",
        "negative_prompt": "",
        "profile": profile_id,
        "checkpoint_name": checkpoint_name,
        "vae_name": "Automatic",
        "text_encoder_name": "Automatic",
        "width": profile.default_width,
        "height": profile.default_height,
        "steps": max(8, profile.default_steps),
        "cfg_scale": profile.default_cfg_scale,
        "sampler_name": profile.default_sampler,
        "scheduler_name": profile.default_scheduler,
        "batch_count": 1,
        "seed": 1,
        "hires_enabled": False,
    }


def _build_controlnet_img2img_defaults(profile_id: str, checkpoint_name: str) -> dict[str, Any]:
    profile = get_parity_profile(profile_id)
    return {
        "prompt": "portrait cleanup",
        "negative_prompt": "",
        "profile": profile_id,
        "checkpoint_name": checkpoint_name,
        "vae_name": "Automatic",
        "text_encoder_name": "Automatic",
        "steps": max(8, profile.default_steps),
        "cfg_scale": profile.default_cfg_scale,
        "sampler_name": profile.default_sampler,
        "scheduler_name": profile.default_scheduler,
        "batch_size": 1,
        "seed": 1,
        "denoise_strength": 0.35,
    }


def _build_controlnet_dry_run_cases(context: ControlNetHostContext) -> list[LiveControlNetDryRunCase]:
    workflow_suffix = context.base_family
    advanced_txt2img_payload = _build_controlnet_txt2img_defaults(context.profile_id, context.checkpoint_name)
    advanced_txt2img_payload.update(
        {
            "dry_run": True,
            "controlnet_units": [
                {
                    "enabled": True,
                    "control_type": context.control_type,
                    "module": context.module_name,
                    "model": context.model_name,
                    "image_data": _build_png_data_url(),
                    "weight": 0.75,
                    "guidance_start": 0.1,
                    "guidance_end": 0.9,
                    "advanced": {
                        "enabled": True,
                        "weight_preset": "soft",
                        "layer_weights": [0.2, 0.4, 0.8],
                        "timestep_keyframes": [
                            {"start_percent": 0.0, "end_percent": 0.5, "strength_scale": 0.5},
                            {"start_percent": 0.5, "end_percent": 1.0, "strength_scale": 1.25},
                        ],
                    },
                }
            ],
        }
    )

    img2img_payload = _build_controlnet_img2img_defaults(context.profile_id, context.checkpoint_name)
    img2img_payload.update(
        {
            "dry_run": True,
            "image_data": _build_png_data_url(color="pink"),
            "controlnet_units": [
                {
                    "enabled": True,
                    "control_type": context.control_type,
                    "module": context.module_name,
                    "model": context.model_name,
                }
            ],
        }
    )

    return [
        LiveControlNetDryRunCase(
            case_id="txt2img_controlnet_advanced",
            route_path="/rookieui/generate/txt2img",
            request_payload=advanced_txt2img_payload,
            expected_workflow_kind=f"txt2img-{workflow_suffix}",
            expected_apply_nodes=2,
        ),
        LiveControlNetDryRunCase(
            case_id="img2img_controlnet_main_source_fallback",
            route_path="/rookieui/generate/img2img",
            request_payload=img2img_payload,
            expected_workflow_kind=f"img2img-{workflow_suffix}",
            expected_apply_nodes=1,
            expect_main_source_fallback=True,
        ),
    ]


def _select_adetailer_detector(catalog_payload: dict[str, Any]) -> tuple[str, str, str] | None:
    detectors = catalog_payload.get("detectors")
    availability = catalog_payload.get("availability")
    runtime_by_family = availability.get("detector_runtime") if isinstance(availability, dict) else {}
    if not isinstance(detectors, list) or not isinstance(runtime_by_family, dict):
        return None

    family_priority = {"mediapipe_face": 0, "ultralytics_bbox": 1, "ultralytics_segm": 2}
    detector_priority = {
        "mediapipe_face_full": 0,
        "mediapipe_face_short": 1,
        "mediapipe_face_mesh": 2,
        "mediapipe_face_mesh_eyes_only": 3,
    }
    candidates: list[tuple[tuple[int, int, int, int], tuple[str, str, str]]] = []
    for index, raw_entry in enumerate(detectors):
        if not isinstance(raw_entry, dict):
            continue
        detector_name = str(raw_entry.get("id", "")).strip()
        detector_family = str(raw_entry.get("provider_family") or raw_entry.get("family") or "").strip().lower()
        if not detector_name or detector_name == "None" or detector_family in {"", "none"}:
            continue
        runtime_state = str(runtime_by_family.get(detector_family, "")).strip()
        sort_key = (
            0 if runtime_state == ADETAILER_RUNTIME_READY else 1,
            family_priority.get(detector_family, 99),
            detector_priority.get(detector_name, 99),
            index,
        )
        candidates.append((sort_key, (detector_name, detector_family, runtime_state)))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _build_adetailer_host_context(
    catalog_payload: dict[str, Any],
    controlnet_context: ControlNetHostContext,
) -> tuple[ADetailerHostContext | None, list[str]]:
    errors: list[str] = []
    host_contract_version = _read_nested_text(catalog_payload, "contract", "version")
    if not host_contract_version:
        errors.append("live host /rookieui/adetailer/catalog payload did not expose contract.version.")

    controlnet_modes = _iter_string_list(catalog_payload, "controlnet_modes")
    for expected_mode in ("passthrough", "custom"):
        if controlnet_modes and expected_mode not in controlnet_modes:
            errors.append(
                f"live host /rookieui/adetailer/catalog payload did not expose controlnet mode '{expected_mode}'."
            )

    controlnet_models = _iter_string_list(catalog_payload, "controlnet_model_list")
    if controlnet_models and controlnet_context.model_name not in controlnet_models:
        errors.append(
            "live host /rookieui/adetailer/catalog controlnet_model_list did not include "
            f"'{controlnet_context.model_name}'."
        )
    controlnet_modules = _iter_string_list(catalog_payload, "controlnet_module_list")
    if controlnet_modules and controlnet_context.module_name not in controlnet_modules:
        errors.append(
            "live host /rookieui/adetailer/catalog controlnet_module_list did not include "
            f"'{controlnet_context.module_name}'."
        )

    selected_detector = _select_adetailer_detector(catalog_payload)
    if selected_detector is None:
        errors.append(
            "live host /rookieui/adetailer/catalog did not expose any usable non-'None' detector entries."
        )
        return None, errors

    detector_name, detector_family, detector_runtime_state = selected_detector
    if detector_runtime_state == "disabled":
        errors.append(
            f"selected ADetailer detector '{detector_name}' resolved to disabled runtime state."
        )

    context = None
    if not errors:
        context = ADetailerHostContext(
            profile_id=controlnet_context.profile_id,
            checkpoint_name=controlnet_context.checkpoint_name,
            base_family=controlnet_context.base_family,
            detector_name=detector_name,
            detector_family=detector_family,
            detector_runtime_state=detector_runtime_state,
            controlnet_control_type=controlnet_context.control_type,
            controlnet_module=controlnet_context.module_name,
            controlnet_model=controlnet_context.model_name,
            host_contract_version=host_contract_version,
            local_contract_version=_LOCAL_ADETAILER_CONTRACT_VERSION,
        )
    return context, errors


def _build_adetailer_dry_run_cases(context: ADetailerHostContext) -> list[LiveADetailerDryRunCase]:
    workflow_suffix = context.base_family

    passthrough_payload = _build_controlnet_txt2img_defaults(context.profile_id, context.checkpoint_name)
    passthrough_payload.update(
        {
            "dry_run": True,
            "controlnet_units": [
                {
                    "enabled": True,
                    "control_type": context.controlnet_control_type,
                    "module": context.controlnet_module,
                    "model": context.controlnet_model,
                    "image_data": _build_png_data_url(color="lightyellow"),
                }
            ],
            "adetailer": {
                "enabled": True,
                "units": [
                    {
                        "enabled": True,
                        "detector": context.detector_name,
                        "prompt": "detail [PROMPT]",
                        "controlnet": {"mode": "passthrough"},
                    }
                ],
            },
        }
    )

    custom_payload = _build_controlnet_txt2img_defaults(context.profile_id, context.checkpoint_name)
    custom_payload.update(
        {
            "dry_run": True,
            "adetailer": {
                "enabled": True,
                "units": [
                    {
                        "enabled": True,
                        "detector": context.detector_name,
                        "prompt": "detail [PROMPT]",
                        "controlnet": {
                            "mode": "custom",
                            "module": context.controlnet_module,
                            "model": context.controlnet_model,
                            "weight": 0.65,
                            "guidance_start": 0.1,
                            "guidance_end": 0.85,
                        },
                    }
                ],
            },
        }
    )

    img2img_refinement_payload = _build_controlnet_img2img_defaults(context.profile_id, context.checkpoint_name)
    img2img_refinement_payload.update(
        {
            "dry_run": True,
            "image_data": _build_png_data_url(color="pink"),
            "adetailer": {
                "enabled": True,
                "skip_img2img": False,
                "units": [
                    {
                        "enabled": True,
                        "detector": context.detector_name,
                        "prompt": "repair [PROMPT]",
                    }
                ],
            },
        }
    )

    img2img_skip_payload = _build_controlnet_img2img_defaults(context.profile_id, context.checkpoint_name)
    img2img_skip_payload.update(
        {
            "dry_run": True,
            "image_data": _build_png_data_url(color="lightgreen"),
            "adetailer": {
                "enabled": True,
                "skip_img2img": True,
                "units": [
                    {
                        "enabled": True,
                        "detector": context.detector_name,
                    }
                ],
            },
        }
    )

    return [
        LiveADetailerDryRunCase(
            case_id="txt2img_adetailer_passthrough_controlnet",
            route_path="/rookieui/generate/txt2img",
            request_payload=passthrough_payload,
            expected_workflow_kind=f"txt2img-{workflow_suffix}",
            expected_sampler_nodes=2,
            expected_apply_nodes=2,
            expect_refinement_nodes=True,
            expect_primary_controlnet_count=1,
        ),
        LiveADetailerDryRunCase(
            case_id="txt2img_adetailer_custom_controlnet",
            route_path="/rookieui/generate/txt2img",
            request_payload=custom_payload,
            expected_workflow_kind=f"txt2img-{workflow_suffix}",
            expected_sampler_nodes=2,
            expected_apply_nodes=1,
            expect_refinement_nodes=True,
            expect_primary_controlnet_count=0,
        ),
        LiveADetailerDryRunCase(
            case_id="img2img_adetailer_refinement",
            route_path="/rookieui/generate/img2img",
            request_payload=img2img_refinement_payload,
            expected_workflow_kind=f"img2img-{workflow_suffix}",
            expected_sampler_nodes=2,
            expected_apply_nodes=0,
            expect_refinement_nodes=True,
            expect_primary_controlnet_count=0,
        ),
        LiveADetailerDryRunCase(
            case_id="img2img_adetailer_skip",
            route_path="/rookieui/generate/img2img",
            request_payload=img2img_skip_payload,
            expected_workflow_kind=f"img2img-{workflow_suffix}",
            expected_sampler_nodes=1,
            expected_apply_nodes=0,
            expect_refinement_nodes=False,
            expect_primary_controlnet_count=0,
            expect_skip_img2img=True,
        ),
    ]


def _build_prompt_parity_host_context(
    models_payload: dict[str, Any],
    capabilities_payload: dict[str, Any],
    preferred_profiles: list[str],
) -> tuple[PromptParityHostContext | None, list[str]]:
    errors: list[str] = []
    checkpoints = _iter_string_list(models_payload, "checkpoints")
    embeddings = _iter_string_list(models_payload, "embeddings")
    host_prompt_semantics = capabilities_payload.get("prompt_semantics")
    host_contract_version = ""
    if isinstance(host_prompt_semantics, dict):
        host_contract_version = str(host_prompt_semantics.get("contract_version", "")).strip()

    sd15_checkpoint = _select_checkpoint_by_keywords(checkpoints, prefix="SD15\\")
    if not sd15_checkpoint:
        errors.append("live host did not expose any SD15 checkpoint selectors in /rookieui/models.checkpoints.")

    sdxl_profile = ""
    sdxl_checkpoint = ""
    preferred_sdxl_profiles = [
        profile_id
        for profile_id in preferred_profiles
        if profile_id in _SDXL_PROMPT_PARITY_PROFILES
    ] or list(_SDXL_PROMPT_PARITY_PROFILES)
    profile_keywords = {
        "pony": ("pony",),
        "illustrious": ("illustrious", "illu"),
        "noob": ("noob",),
        "sdxl": (),
    }
    for profile_id in preferred_sdxl_profiles:
        checkpoint_name = _select_checkpoint_by_keywords(
            checkpoints,
            prefix="SDXL\\",
            keywords=profile_keywords.get(profile_id, ()),
        )
        if checkpoint_name:
            sdxl_profile = profile_id
            sdxl_checkpoint = checkpoint_name
            break
    if not sdxl_profile or not sdxl_checkpoint:
        errors.append(
            "live host did not expose a healthy SDXL-family checkpoint selector for any of: "
            f"{', '.join(preferred_sdxl_profiles)}."
        )

    context = None
    if not errors:
        context = PromptParityHostContext(
            sd15_checkpoint=sd15_checkpoint,
            sdxl_profile=sdxl_profile,
            sdxl_checkpoint=sdxl_checkpoint,
            embedding_name=embeddings[0] if embeddings else None,
            host_contract_version=host_contract_version,
            local_contract_version=_LOCAL_PROMPT_CONTRACT_VERSION,
        )
    return context, errors


def _build_prompt_parity_cases(context: PromptParityHostContext) -> list[LivePromptParityCase]:
    sd15_attention = _get_fixture("sd15_attention_brackets")
    sd15_long_comma_chunk = _get_fixture("sd15_long_comma_chunk")
    sd15_break_schedule = _get_fixture("sd15_break_schedule")
    sd15_alternate_schedule = _get_fixture("sd15_alternate_schedule")
    sd15_and_multi_cond = _get_fixture("sd15_and_multi_cond")
    sd15_missing_explicit_embedding = _get_fixture("sd15_missing_explicit_embedding")

    cases = [
        LivePromptParityCase(sd15_attention, checkpoint_name=context.sd15_checkpoint, execute=True),
        LivePromptParityCase(sd15_long_comma_chunk, checkpoint_name=context.sd15_checkpoint, execute=True),
        LivePromptParityCase(sd15_break_schedule, checkpoint_name=context.sd15_checkpoint),
        LivePromptParityCase(sd15_alternate_schedule, checkpoint_name=context.sd15_checkpoint),
        LivePromptParityCase(sd15_and_multi_cond, checkpoint_name=context.sd15_checkpoint),
        LivePromptParityCase(sd15_missing_explicit_embedding, checkpoint_name=context.sd15_checkpoint),
    ]

    if context.embedding_name:
        embedding_fixture = replace(
            _get_fixture("sd15_embedding_bare"),
            prompt=f"portrait {context.embedding_name} dramatic light",
            inventory_embeddings=(context.embedding_name,),
            expected_cleaned_prompt=f"portrait embedding:{context.embedding_name} dramatic light",
            expected_prompt_embeddings=(
                ExpectedEmbeddingRef(
                    canonical_token=f"embedding:{context.embedding_name}",
                    exists=True,
                    syntax="bare",
                ),
            ),
            expected_prompt_workflow_fragments=(f"embedding:{context.embedding_name}",),
        )
        cases.append(
            LivePromptParityCase(
                embedding_fixture,
                checkpoint_name=context.sd15_checkpoint,
                execute=True,
            )
        )

        sdxl_fixture = replace(
            _get_fixture("pony_mixed_compound_with_negative_embedding"),
            profile=context.sdxl_profile,
            inventory_embeddings=(context.embedding_name,),
            prompt=f"((hero)) AND {context.embedding_name} BREAK [day:night:0.5]",
            negative_prompt=f"embedding:{context.embedding_name} [low quality]",
            expected_cleaned_prompt=f"((hero)) AND embedding:{context.embedding_name} BREAK [day:night:0.5]",
            expected_cleaned_negative_prompt=f"embedding:{context.embedding_name} [low quality]",
            expected_prompt_embeddings=(
                ExpectedEmbeddingRef(
                    canonical_token=f"embedding:{context.embedding_name}",
                    exists=True,
                    syntax="bare",
                ),
            ),
            expected_negative_embeddings=(
                ExpectedEmbeddingRef(
                    canonical_token=f"embedding:{context.embedding_name}",
                    exists=True,
                    syntax="explicit",
                ),
            ),
            expected_prompt_workflow_fragments=(f"embedding:{context.embedding_name}",),
            expected_negative_workflow_fragments=(f"embedding:{context.embedding_name}",),
        )
    else:
        sdxl_fixture = PromptParityGoldenCase(
            case_id=f"{context.sdxl_profile}_mixed_compound_without_embedding",
            profile=context.sdxl_profile,
            prompt="((hero)) BREAK [day:night:0.5]",
            negative_prompt="[low quality]",
            expected_cleaned_prompt="((hero)) BREAK [day:night:0.5]",
            expected_cleaned_negative_prompt="[low quality]",
            expected_warning_codes=(
                "PROMPT_BREAK_DETECTED",
                "PROMPT_SCHEDULE_DETECTED",
                "PROMPT_ATTENTION_DETECTED",
            ),
            expected_prompt_features=(
                "break_chunks",
                "prompt_scheduling",
                "attention_weighting",
            ),
            expected_negative_features=("attention_weighting",),
            expected_encoder_class="RookieUIA1111CLIPTextEncodeSDXL",
            expect_conditioning_combine=True,
            expect_timestep_range=True,
        )
    cases.append(
        LivePromptParityCase(
            sdxl_fixture,
            checkpoint_name=context.sdxl_checkpoint,
            execute=True,
        )
    )
    return cases


def _validate_catalog_contract(
    models_payload: dict[str, Any],
    presets_payload: dict[str, Any],
    target_profiles: list[str],
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    errors: list[str] = []
    presets = presets_payload.get("presets", [])
    presets_by_id = {
        str(preset.get("id", "")).strip(): preset
        for preset in presets
        if isinstance(preset, dict) and str(preset.get("id", "")).strip()
    }
    diffusion_models = [
        str(model).strip()
        for model in models_payload.get("diffusion_models", [])
        if isinstance(model, str) and str(model).strip()
    ]
    text_encoders = [
        str(model).strip()
        for model in models_payload.get("text_encoders", [])
        if isinstance(model, str) and str(model).strip()
    ]
    category_by_family = (
        ((models_payload.get("catalog") or {}).get("primary_model_category_by_family"))
        if isinstance(models_payload.get("catalog"), dict)
        else {}
    )
    if not isinstance(category_by_family, dict):
        category_by_family = {}

    for profile_id in target_profiles:
        preset = presets_by_id.get(profile_id)
        if preset is None:
            errors.append(f"profile '{profile_id}' missing in /rookieui/presets payload.")
            continue
        if category_by_family.get(profile_id) != "diffusion_models":
            errors.append(
                f"profile '{profile_id}' expected category 'diffusion_models' but got "
                f"'{category_by_family.get(profile_id)}'."
            )

        checkpoint_name = str(preset.get("checkpoint_name", "")).strip()
        if checkpoint_name not in diffusion_models:
            errors.append(
                f"profile '{profile_id}' checkpoint '{checkpoint_name}' not found in /rookieui/models.diffusion_models."
            )

        text_encoder_name = str(preset.get("text_encoder_name", "")).strip()
        if text_encoder_name and text_encoder_name not in text_encoders:
            errors.append(
                f"profile '{profile_id}' text encoder '{text_encoder_name}' not found in /rookieui/models.text_encoders."
            )

        lowered_text_encoder = text_encoder_name.lower()
        # CRITICAL: non-Qwen diffusion profiles must not inherit Qwen text encoders; this exact mismatch caused runtime crashes.
        if profile_id == "qwen_image":
            if "qwen" not in lowered_text_encoder:
                errors.append(
                    f"profile '{profile_id}' expected a Qwen text encoder but got '{text_encoder_name}'."
                )
        elif "qwen" in lowered_text_encoder:
            errors.append(
                f"profile '{profile_id}' must not default to a Qwen text encoder ('{text_encoder_name}')."
            )

    return errors, presets_by_id


def _build_txt2img_payload(profile_id: str, preset: dict[str, Any], client_id: str) -> dict[str, Any]:
    return {
        "prompt": f"[rookieui live smoke] {profile_id}",
        "negative_prompt": "",
        "profile": profile_id,
        "checkpoint_name": str(preset.get("checkpoint_name", "")).strip(),
        "vae_name": str(preset.get("vae_name", "Automatic")).strip() or "Automatic",
        "text_encoder_name": str(preset.get("text_encoder_name", "")).strip(),
        "width": int(preset.get("width", 1024)),
        "height": int(preset.get("height", 1024)),
        "steps": 1,
        "cfg_scale": float(preset.get("cfg_scale", 1.0)),
        "sampler_name": str(preset.get("sampler_name", "euler")).strip() or "euler",
        "scheduler_name": str(preset.get("scheduler_name", "normal")).strip() or "normal",
        "batch_count": 1,
        "seed": 1,
        "hires_enabled": False,
        "client_id": client_id,
    }


def _build_prompt_parity_request_payload(case: LivePromptParityCase) -> dict[str, Any]:
    profile = get_parity_profile(case.fixture.profile)
    requested_steps = (
        max(4, profile.default_steps)
        if case.fixture.expect_conditioning_combine or case.fixture.expect_timestep_range
        else 1
    )
    return {
        "prompt": case.fixture.prompt,
        "negative_prompt": case.fixture.negative_prompt,
        "profile": case.fixture.profile,
        "checkpoint_name": case.checkpoint_name,
        "vae_name": "Automatic",
        "text_encoder_name": "Automatic",
        "width": profile.default_width,
        "height": profile.default_height,
        "steps": requested_steps,
        "cfg_scale": profile.default_cfg_scale,
        "sampler_name": profile.default_sampler,
        "scheduler_name": profile.default_scheduler,
        "batch_count": 1,
        "seed": 1,
        "hires_enabled": False,
        "dry_run": True,
    }


def _collect_encoder_texts(workflow: dict[str, Any], encoder_class: str) -> list[str]:
    texts: list[str] = []
    for node in workflow.values():
        if not isinstance(node, dict) or node.get("class_type") != encoder_class:
            continue
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue
        if encoder_class == "RookieUIA1111CLIPTextEncodeSDXL":
            for key in ("text_g", "text_l"):
                value = inputs.get(key)
                if isinstance(value, str):
                    texts.append(value)
            continue
        value = inputs.get("text")
        if isinstance(value, str):
            texts.append(value)
    return texts


def _append_feature_mismatch_errors(
    errors: list[str],
    payload: dict[str, Any],
    expected_features: tuple[str, ...],
    *,
    case_id: str,
    lane: str,
) -> None:
    features = payload.get("features")
    if not isinstance(features, dict):
        errors.append(f"{case_id} {lane}: semantic payload missing features map.")
        return
    for feature_name in ALL_PROMPT_FEATURES:
        actual_value = bool(features.get(feature_name))
        expected_value = feature_name in expected_features
        if actual_value != expected_value:
            errors.append(
                f"{case_id} {lane}: feature '{feature_name}' expected {expected_value} but got {actual_value}."
            )


def _append_embedding_mismatch_errors(
    errors: list[str],
    payload: dict[str, Any],
    expected_embeddings: tuple[ExpectedEmbeddingRef, ...],
    *,
    case_id: str,
    lane: str,
) -> None:
    actual_embeddings = payload.get("embeddings")
    if not isinstance(actual_embeddings, list):
        if expected_embeddings:
            errors.append(f"{case_id} {lane}: semantic payload missing embeddings list.")
        return
    if len(actual_embeddings) != len(expected_embeddings):
        errors.append(
            f"{case_id} {lane}: expected {len(expected_embeddings)} embeddings but got {len(actual_embeddings)}."
        )
        return
    for actual, expected in zip(actual_embeddings, expected_embeddings):
        if not isinstance(actual, dict):
            errors.append(f"{case_id} {lane}: embedding entry was not an object.")
            continue
        for key, expected_value in (
            ("canonical_token", expected.canonical_token),
            ("exists", expected.exists),
            ("syntax", expected.syntax),
        ):
            actual_value = actual.get(key)
            if actual_value != expected_value:
                errors.append(
                    f"{case_id} {lane}: embedding field '{key}' expected '{expected_value}' but got '{actual_value}'."
                )


def _validate_controlnet_detect_response(
    context: ControlNetHostContext,
    response_payload: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if _read_nested_text(response_payload, "service") != "rookieui":
        errors.append("controlnet detect: expected top-level service='rookieui'.")
    if _read_nested_text(response_payload, "status") != "ok":
        errors.append("controlnet detect: expected top-level status='ok'.")
    host_contract_version = _read_nested_text(response_payload, "contract", "version")
    if host_contract_version != context.local_contract_version:
        errors.append(
            "controlnet detect: integrated contract mismatch: "
            f"host='{host_contract_version}' workspace='{context.local_contract_version}'."
        )
    if str(response_payload.get("module", "")).strip() != context.module_name:
        errors.append(
            f"controlnet detect: expected module '{context.module_name}' but got '{response_payload.get('module')}'."
        )
    if str(response_payload.get("requested_controlnet_model", "")).strip() != context.model_name:
        errors.append(
            "controlnet detect: expected requested_controlnet_model "
            f"'{context.model_name}' but got '{response_payload.get('requested_controlnet_model')}'."
        )
    images = response_payload.get("images")
    if not isinstance(images, list) or not images:
        errors.append("controlnet detect: expected at least one output image.")
    backend = str(response_payload.get("detect_backend", "")).strip()
    if backend not in _CONTROLNET_ALLOWED_DETECT_BACKENDS:
        errors.append(f"controlnet detect: unexpected detect_backend '{backend}'.")
    warning_codes = response_payload.get("warning_codes")
    if not isinstance(warning_codes, list):
        errors.append("controlnet detect: warning_codes missing.")
        warning_codes = []
    if backend == "rookieui_internal_disabled" and _CONTROLNET_WARNING_PREPROCESSOR_DISABLED not in warning_codes:
        errors.append("controlnet detect: disabled backend missing CONTROLNET_PREPROCESSOR_DISABLED warning.")
    if backend == "rookieui_internal_unavailable" and _CONTROLNET_WARNING_PREPROCESSOR_UNAVAILABLE not in warning_codes:
        errors.append("controlnet detect: unavailable backend missing CONTROLNET_PREPROCESSOR_UNAVAILABLE warning.")
    if backend == "rookieui_internal_fallback" and _CONTROLNET_WARNING_PREPROCESSOR_HOST_FALLBACK not in warning_codes:
        errors.append("controlnet detect: fallback backend missing CONTROLNET_PREPROCESSOR_HOST_FALLBACK warning.")
    return errors


def _validate_controlnet_dry_run_case_response(
    context: ControlNetHostContext,
    case: LiveControlNetDryRunCase,
    response_payload: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    submission = response_payload.get("submission")
    if not isinstance(submission, dict) or submission.get("mode") != "dry-run":
        errors.append(f"{case.case_id}: expected dry-run submission payload.")
    if response_payload.get("workflow_kind") != case.expected_workflow_kind:
        errors.append(
            f"{case.case_id}: expected workflow_kind '{case.expected_workflow_kind}' but got "
            f"'{response_payload.get('workflow_kind')}'."
        )

    normalized_request = response_payload.get("normalized_request")
    if not isinstance(normalized_request, dict):
        errors.append(f"{case.case_id}: response missing normalized_request.")
        return errors
    controlnet_units = normalized_request.get("controlnet_units")
    if not isinstance(controlnet_units, list) or len(controlnet_units) != 1 or not isinstance(controlnet_units[0], dict):
        errors.append(f"{case.case_id}: expected exactly one normalized ControlNet unit.")
        return errors

    unit = controlnet_units[0]
    if unit.get("module") != context.module_name:
        errors.append(
            f"{case.case_id}: expected normalized module '{context.module_name}' but got '{unit.get('module')}'."
        )
    if unit.get("model") != context.model_name:
        errors.append(
            f"{case.case_id}: expected normalized model '{context.model_name}' but got '{unit.get('model')}'."
        )
    if unit.get("control_type") != context.control_type:
        errors.append(
            f"{case.case_id}: expected normalized control_type '{context.control_type}' but got '{unit.get('control_type')}'."
        )
    if not str(unit.get("image_asset", "")).strip():
        errors.append(f"{case.case_id}: normalized ControlNet unit missing image_asset.")
    if case.expect_main_source_fallback and normalized_request.get("image_asset") != unit.get("image_asset"):
        errors.append(f"{case.case_id}: ControlNet unit did not inherit the main img2img image_asset.")

    workflow = response_payload.get("workflow")
    if not isinstance(workflow, dict):
        errors.append(f"{case.case_id}: response missing workflow payload.")
        return errors

    preprocess_nodes = [
        node for node in workflow.values() if isinstance(node, dict) and node.get("class_type") == "RookieUIControlNetPreprocess"
    ]
    if not preprocess_nodes:
        errors.append(f"{case.case_id}: workflow missing RookieUIControlNetPreprocess.")
    else:
        if preprocess_nodes[0].get("inputs", {}).get("module") != context.module_name:
            errors.append(f"{case.case_id}: preprocess node module did not match selected host context.")

    class_types = {node.get("class_type") for node in workflow.values() if isinstance(node, dict)}
    if "DiffControlNetLoader" not in class_types:
        errors.append(f"{case.case_id}: workflow missing DiffControlNetLoader.")
    apply_nodes = [
        node
        for node in workflow.values()
        if isinstance(node, dict) and node.get("class_type") == "RookieUIControlNetApplyNativeAdvanced"
    ]
    if len(apply_nodes) != case.expected_apply_nodes:
        errors.append(
            f"{case.case_id}: expected {case.expected_apply_nodes} RookieUIControlNetApplyNativeAdvanced nodes but got {len(apply_nodes)}."
        )
    if case.expected_apply_nodes > 1:
        for apply_node in apply_nodes:
            inputs = apply_node.get("inputs", {})
            if inputs.get("weight_preset") != "soft":
                errors.append(f"{case.case_id}: advanced apply node missing weight_preset='soft'.")
            if inputs.get("layer_weights_json") != "[0.2, 0.4, 0.8]":
                errors.append(f"{case.case_id}: advanced apply node missing expected layer_weights_json.")
    return errors


def _validate_adetailer_dry_run_case_response(
    context: ADetailerHostContext,
    case: LiveADetailerDryRunCase,
    response_payload: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    submission = response_payload.get("submission")
    if not isinstance(submission, dict) or submission.get("mode") != "dry-run":
        errors.append(f"{case.case_id}: expected dry-run submission payload.")
    if response_payload.get("workflow_kind") != case.expected_workflow_kind:
        errors.append(
            f"{case.case_id}: expected workflow_kind '{case.expected_workflow_kind}' but got "
            f"'{response_payload.get('workflow_kind')}'."
        )

    normalized_request = response_payload.get("normalized_request")
    if not isinstance(normalized_request, dict):
        errors.append(f"{case.case_id}: response missing normalized_request.")
        return errors

    controlnet_units = normalized_request.get("controlnet_units")
    if case.expect_primary_controlnet_count > 0:
        if (
            not isinstance(controlnet_units, list)
            or len(controlnet_units) != case.expect_primary_controlnet_count
            or not isinstance(controlnet_units[0], dict)
        ):
            errors.append(
                f"{case.case_id}: expected {case.expect_primary_controlnet_count} primary ControlNet unit(s)."
            )
        elif controlnet_units[0].get("model") != context.controlnet_model:
            errors.append(
                f"{case.case_id}: primary ControlNet unit did not retain model '{context.controlnet_model}'."
            )
    elif isinstance(controlnet_units, list) and controlnet_units:
        errors.append(f"{case.case_id}: expected no primary ControlNet units.")

    adetailer = normalized_request.get("adetailer")
    if not isinstance(adetailer, dict):
        errors.append(f"{case.case_id}: normalized_request missing adetailer block.")
        return errors

    if not bool(adetailer.get("enabled")):
        errors.append(f"{case.case_id}: normalized_request.adetailer.enabled was not true.")
    if bool(adetailer.get("skip_img2img")) != case.expect_skip_img2img:
        errors.append(
            f"{case.case_id}: expected skip_img2img={case.expect_skip_img2img} but got "
            f"{bool(adetailer.get('skip_img2img'))}."
        )

    units = adetailer.get("units")
    if not isinstance(units, list) or not units or not isinstance(units[0], dict):
        errors.append(f"{case.case_id}: normalized_request.adetailer.units missing first unit.")
        return errors
    unit = units[0]
    if unit.get("detector") != context.detector_name:
        errors.append(
            f"{case.case_id}: expected detector '{context.detector_name}' but got '{unit.get('detector')}'."
        )
    if unit.get("detector_family") != context.detector_family:
        errors.append(
            f"{case.case_id}: expected detector_family '{context.detector_family}' but got '{unit.get('detector_family')}'."
        )

    warning_codes = adetailer.get("warning_codes")
    if not isinstance(warning_codes, list):
        errors.append(f"{case.case_id}: normalized_request.adetailer.warning_codes missing.")
        warning_codes = []
    if context.detector_runtime_state != ADETAILER_RUNTIME_READY:
        if ADETAILER_WARNING_DETECTOR_RUNTIME_FALLBACK_MASK not in warning_codes:
            errors.append(f"{case.case_id}: expected fallback-mask warning for degraded detector runtime.")
    elif ADETAILER_WARNING_DETECTOR_RUNTIME_FALLBACK_MASK in warning_codes:
        errors.append(f"{case.case_id}: unexpected fallback-mask warning for ready detector runtime.")
    if (
        case.case_id == "txt2img_adetailer_passthrough_controlnet"
        and ADETAILER_WARNING_CONTROLNET_PASSTHROUGH_EMPTY in warning_codes
    ):
        errors.append(f"{case.case_id}: unexpected passthrough-empty warning.")
    if case.case_id == "txt2img_adetailer_custom_controlnet" and ADETAILER_WARNING_CONTROLNET_CUSTOM_MODEL_MISSING in warning_codes:
        errors.append(f"{case.case_id}: unexpected custom-model-missing warning.")

    diagnostics = adetailer.get("diagnostics")
    if not isinstance(diagnostics, dict):
        errors.append(f"{case.case_id}: normalized_request.adetailer.diagnostics missing.")
    elif diagnostics.get("primary_controlnet_unit_count") != case.expect_primary_controlnet_count:
        errors.append(
            f"{case.case_id}: expected primary_controlnet_unit_count={case.expect_primary_controlnet_count} but got "
            f"{diagnostics.get('primary_controlnet_unit_count')}."
        )

    workflow = response_payload.get("workflow")
    if not isinstance(workflow, dict):
        errors.append(f"{case.case_id}: response missing workflow payload.")
        return errors

    detect_nodes = [
        node for node in workflow.values() if isinstance(node, dict) and node.get("class_type") == "RookieUIADetailerDetectMask"
    ]
    inpaint_nodes = [
        node for node in workflow.values() if isinstance(node, dict) and node.get("class_type") == "RookieUIVAEEncodeForInpaint"
    ]
    sampler_nodes = [node for node in workflow.values() if isinstance(node, dict) and node.get("class_type") == "KSampler"]
    apply_nodes = [
        node
        for node in workflow.values()
        if isinstance(node, dict) and node.get("class_type") == "RookieUIControlNetApplyNativeAdvanced"
    ]
    decode_nodes = [(node_id, node) for node_id, node in workflow.items() if isinstance(node, dict) and node.get("class_type") == "VAEDecode"]
    save_nodes = [node for node in workflow.values() if isinstance(node, dict) and node.get("class_type") == "SaveImage"]

    if len(sampler_nodes) != case.expected_sampler_nodes:
        errors.append(
            f"{case.case_id}: expected {case.expected_sampler_nodes} KSampler nodes but got {len(sampler_nodes)}."
        )
    if len(apply_nodes) != case.expected_apply_nodes:
        errors.append(
            f"{case.case_id}: expected {case.expected_apply_nodes} RookieUIControlNetApplyNativeAdvanced nodes but got {len(apply_nodes)}."
        )

    if case.expect_refinement_nodes:
        if len(detect_nodes) != 1:
            errors.append(f"{case.case_id}: expected exactly one RookieUIADetailerDetectMask node.")
        else:
            inputs = detect_nodes[0].get("inputs", {})
            if inputs.get("detector") != context.detector_name:
                errors.append(f"{case.case_id}: detect-mask node detector did not match selected host detector.")
            if inputs.get("detector_family") != context.detector_family:
                errors.append(f"{case.case_id}: detect-mask node detector_family did not match selected host detector family.")
        if len(inpaint_nodes) != 1:
            errors.append(f"{case.case_id}: expected exactly one RookieUIVAEEncodeForInpaint node.")
        if not decode_nodes or not save_nodes:
            errors.append(f"{case.case_id}: workflow missing decode/save nodes for refinement chain.")
        elif save_nodes[0].get("inputs", {}).get("images") != [decode_nodes[-1][0], 0]:
            errors.append(f"{case.case_id}: SaveImage was not wired to the final decode node.")
    else:
        if detect_nodes:
            errors.append(f"{case.case_id}: workflow unexpectedly emitted RookieUIADetailerDetectMask.")
        if inpaint_nodes:
            errors.append(f"{case.case_id}: workflow unexpectedly emitted RookieUIVAEEncodeForInpaint.")

    return errors


def _validate_prompt_parity_case_response(case: LivePromptParityCase, response_payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    fixture = case.fixture
    submission = response_payload.get("submission")
    if not isinstance(submission, dict) or submission.get("mode") != "dry-run":
        errors.append(f"{fixture.case_id}: expected dry-run submission payload.")

    expected_workflow_kind = "txt2img-sdxl" if fixture.profile in _SDXL_PROMPT_PARITY_PROFILES else "txt2img-sd15"
    if response_payload.get("workflow_kind") != expected_workflow_kind:
        errors.append(
            f"{fixture.case_id}: expected workflow_kind '{expected_workflow_kind}' but got "
            f"'{response_payload.get('workflow_kind')}'."
        )

    normalized_request = response_payload.get("normalized_request")
    if not isinstance(normalized_request, dict):
        errors.append(f"{fixture.case_id}: response missing normalized_request.")
        return errors

    if normalized_request.get("prompt") != fixture.expected_cleaned_prompt:
        errors.append(
            f"{fixture.case_id}: expected cleaned prompt '{fixture.expected_cleaned_prompt}' but got "
            f"'{normalized_request.get('prompt')}'."
        )
    if normalized_request.get("negative_prompt") != fixture.expected_cleaned_negative_prompt:
        errors.append(
            f"{fixture.case_id}: expected cleaned negative prompt '{fixture.expected_cleaned_negative_prompt}' but got "
            f"'{normalized_request.get('negative_prompt')}'."
        )

    warning_codes = normalized_request.get("prompt_warning_codes")
    if not isinstance(warning_codes, list):
        errors.append(f"{fixture.case_id}: normalized_request.prompt_warning_codes missing.")
    else:
        for warning_code in fixture.expected_warning_codes:
            if warning_code not in warning_codes:
                errors.append(f"{fixture.case_id}: missing warning code '{warning_code}'.")

    prompt_semantics = normalized_request.get("prompt_semantics")
    negative_semantics = normalized_request.get("negative_prompt_semantics")
    if not isinstance(prompt_semantics, dict):
        errors.append(f"{fixture.case_id}: prompt_semantics missing.")
    else:
        _append_feature_mismatch_errors(
            errors,
            prompt_semantics,
            fixture.expected_prompt_features,
            case_id=fixture.case_id,
            lane="prompt",
        )
        if len(prompt_semantics.get("branches", [])) != fixture.expected_prompt_branch_count:
            errors.append(
                f"{fixture.case_id} prompt: expected {fixture.expected_prompt_branch_count} branches but got "
                f"{len(prompt_semantics.get('branches', []))}."
            )
        _append_embedding_mismatch_errors(
            errors,
            prompt_semantics,
            fixture.expected_prompt_embeddings,
            case_id=fixture.case_id,
            lane="prompt",
        )
    if not isinstance(negative_semantics, dict):
        errors.append(f"{fixture.case_id}: negative_prompt_semantics missing.")
    else:
        _append_feature_mismatch_errors(
            errors,
            negative_semantics,
            fixture.expected_negative_features,
            case_id=fixture.case_id,
            lane="negative",
        )
        if len(negative_semantics.get("branches", [])) != fixture.expected_negative_branch_count:
            errors.append(
                f"{fixture.case_id} negative: expected {fixture.expected_negative_branch_count} branches but got "
                f"{len(negative_semantics.get('branches', []))}."
            )
        _append_embedding_mismatch_errors(
            errors,
            negative_semantics,
            fixture.expected_negative_embeddings,
            case_id=fixture.case_id,
            lane="negative",
        )

    workflow = response_payload.get("workflow")
    if not isinstance(workflow, dict):
        errors.append(f"{fixture.case_id}: response missing workflow payload.")
        return errors

    class_types = {
        node.get("class_type")
        for node in workflow.values()
        if isinstance(node, dict)
    }
    if fixture.expected_encoder_class not in class_types:
        fallback_encoder = "CLIPTextEncodeSDXL" if fixture.expected_encoder_class.endswith("SDXL") else "CLIPTextEncode"
        if fallback_encoder in class_types:
            errors.append(
                f"{fixture.case_id}: expected '{fixture.expected_encoder_class}' but host emitted '{fallback_encoder}'. "
                "Live host appears to be running a pre-cutover RookieUI deployment."
            )
        else:
            errors.append(
                f"{fixture.case_id}: workflow missing expected encoder class '{fixture.expected_encoder_class}'."
            )
    if fixture.expect_conditioning_combine and "ConditioningCombine" not in class_types:
        errors.append(f"{fixture.case_id}: workflow missing ConditioningCombine.")
    if not fixture.expect_conditioning_combine and "ConditioningCombine" in class_types:
        errors.append(f"{fixture.case_id}: workflow unexpectedly emitted ConditioningCombine.")
    if fixture.expect_timestep_range and "ConditioningSetTimestepRange" not in class_types:
        errors.append(f"{fixture.case_id}: workflow missing ConditioningSetTimestepRange.")
    if not fixture.expect_timestep_range and "ConditioningSetTimestepRange" in class_types:
        errors.append(f"{fixture.case_id}: workflow unexpectedly emitted ConditioningSetTimestepRange.")

    encoder_texts = _collect_encoder_texts(workflow, fixture.expected_encoder_class)
    expected_fragments = fixture.expected_prompt_workflow_fragments + fixture.expected_negative_workflow_fragments
    for fragment in expected_fragments:
        if not any(fragment in text for text in encoder_texts):
            errors.append(f"{fixture.case_id}: workflow missing expected text fragment '{fragment}'.")
    return errors


def _run_prompt_parity_dry_run_smoke(
    base_url: str,
    cases: list[LivePromptParityCase],
    *,
    request_timeout_seconds: float,
) -> list[str]:
    errors: list[str] = []
    for case in cases:
        request_payload = _build_prompt_parity_request_payload(case)
        response_payload = _request_json(
            "POST",
            f"{base_url}/rookieui/generate/txt2img",
            payload=request_payload,
            timeout_seconds=request_timeout_seconds,
        )
        errors.extend(_validate_prompt_parity_case_response(case, response_payload))
    return errors


def _run_controlnet_detect_smoke(
    base_url: str,
    context: ControlNetHostContext,
    *,
    request_timeout_seconds: float,
) -> list[str]:
    response_payload = _request_json(
        "POST",
        f"{base_url}/rookieui/controlnet/detect",
        payload={
            "controlnet_module": context.module_name,
            "controlnet_model": context.model_name,
            "controlnet_input_images": [_build_png_data_url()],
        },
        timeout_seconds=request_timeout_seconds,
    )
    return _validate_controlnet_detect_response(context, response_payload)


def _run_controlnet_dry_run_smoke(
    base_url: str,
    context: ControlNetHostContext,
    cases: list[LiveControlNetDryRunCase],
    *,
    request_timeout_seconds: float,
) -> list[str]:
    errors: list[str] = []
    for case in cases:
        response_payload = _request_json(
            "POST",
            f"{base_url}{case.route_path}",
            payload=case.request_payload,
            timeout_seconds=request_timeout_seconds,
        )
        errors.extend(_validate_controlnet_dry_run_case_response(context, case, response_payload))
    return errors


def _run_adetailer_dry_run_smoke(
    base_url: str,
    context: ADetailerHostContext,
    cases: list[LiveADetailerDryRunCase],
    *,
    request_timeout_seconds: float,
) -> list[str]:
    errors: list[str] = []
    for case in cases:
        response_payload = _request_json(
            "POST",
            f"{base_url}{case.route_path}",
            payload=case.request_payload,
            timeout_seconds=request_timeout_seconds,
        )
        errors.extend(_validate_adetailer_dry_run_case_response(context, case, response_payload))
    return errors


def _build_prompt_parity_execute_payload(case: LivePromptParityCase, client_id: str) -> dict[str, Any]:
    payload = _build_prompt_parity_request_payload(case)
    payload.pop("dry_run", None)
    payload["client_id"] = client_id
    return payload


def _build_controlnet_execute_payload(context: ControlNetHostContext, client_id: str) -> dict[str, Any]:
    payload = _build_controlnet_txt2img_defaults(context.profile_id, context.checkpoint_name)
    payload["client_id"] = client_id
    payload["controlnet_units"] = [
        {
            "enabled": True,
            "control_type": context.control_type,
            "module": context.module_name,
            "model": context.model_name,
            "image_data": _build_png_data_url(color="lightgray"),
            "guidance_start": 0.0,
            "guidance_end": 1.0,
        }
    ]
    return payload


def _build_adetailer_execute_payload(context: ADetailerHostContext, client_id: str) -> dict[str, Any]:
    payload = _build_controlnet_txt2img_defaults(context.profile_id, context.checkpoint_name)
    payload["client_id"] = client_id
    payload["adetailer"] = {
        "enabled": True,
        "units": [
            {
                "enabled": True,
                "detector": context.detector_name,
                "prompt": "detail [PROMPT]",
            }
        ],
    }
    return payload


def _run_prompt_parity_execute_smoke(
    base_url: str,
    cases: list[LivePromptParityCase],
    *,
    request_timeout_seconds: float,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> list[str]:
    errors: list[str] = []
    for case in [candidate for candidate in cases if candidate.execute]:
        client_id = f"rookieui-prompt-parity-{case.fixture.profile}-{case.fixture.case_id}"
        submit_result = _request_json(
            "POST",
            f"{base_url}/rookieui/generate/txt2img",
            payload=_build_prompt_parity_execute_payload(case, client_id),
            timeout_seconds=request_timeout_seconds,
        )
        submission = submit_result.get("submission") if isinstance(submit_result, dict) else None
        if not isinstance(submission, dict) or not bool(submission.get("accepted")):
            errors.append(
                f"{case.fixture.case_id}: execute submit failed, expected accepted submission payload."
            )
            continue
        prompt_id = str(submission.get("prompt_id", "")).strip()
        if not prompt_id:
            errors.append(f"{case.fixture.case_id}: execute submit missing prompt_id.")
            continue
        job = _poll_queue_job_until_terminal(
            base_url,
            prompt_id,
            client_id,
            request_timeout_seconds=request_timeout_seconds,
            poll_timeout_seconds=poll_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        terminal_status = str(job.get("status", "")).strip().lower()
        if terminal_status != "completed":
            errors.append(
                f"{case.fixture.case_id}: execute lane ended in status '{terminal_status}'."
            )
    return errors


def _run_controlnet_execute_smoke(
    base_url: str,
    context: ControlNetHostContext,
    *,
    request_timeout_seconds: float,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> list[str]:
    client_id = f"rookieui-live-controlnet-{context.profile_id}-{int(time.time() * 1000)}"
    submit_result = _request_json(
        "POST",
        f"{base_url}/rookieui/generate/txt2img",
        payload=_build_controlnet_execute_payload(context, client_id),
        timeout_seconds=request_timeout_seconds,
    )
    return _run_shared_queue_post_state_smoke(
        base_url,
        lane_label="controlnet execute",
        submit_result=submit_result,
        client_id=client_id,
        request_timeout_seconds=request_timeout_seconds,
        poll_timeout_seconds=poll_timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )


def _run_adetailer_execute_smoke(
    base_url: str,
    context: ADetailerHostContext,
    *,
    request_timeout_seconds: float,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> list[str]:
    client_id = f"rookieui-live-adetailer-{context.profile_id}-{int(time.time() * 1000)}"
    submit_result = _request_json(
        "POST",
        f"{base_url}/rookieui/generate/txt2img",
        payload=_build_adetailer_execute_payload(context, client_id),
        timeout_seconds=request_timeout_seconds,
    )
    errors: list[str] = []
    normalized_request = submit_result.get("normalized_request")
    if not isinstance(normalized_request, dict):
        return ["adetailer execute: submit payload missing normalized_request."]
    adetailer = normalized_request.get("adetailer")
    if not isinstance(adetailer, dict):
        return ["adetailer execute: submit payload missing normalized_request.adetailer."]
    warning_codes = adetailer.get("warning_codes")
    if not isinstance(warning_codes, list):
        return ["adetailer execute: normalized_request.adetailer.warning_codes missing."]
    if context.detector_runtime_state != ADETAILER_RUNTIME_READY:
        if ADETAILER_WARNING_DETECTOR_RUNTIME_FALLBACK_MASK not in warning_codes:
            errors.append("adetailer execute: degraded detector runtime was missing fallback-mask warning.")
    elif ADETAILER_WARNING_DETECTOR_RUNTIME_FALLBACK_MASK in warning_codes:
        errors.append("adetailer execute: ready detector runtime unexpectedly emitted fallback-mask warning.")
    errors.extend(
        _run_shared_queue_post_state_smoke(
            base_url,
            lane_label="adetailer execute",
            submit_result=submit_result,
            client_id=client_id,
            request_timeout_seconds=request_timeout_seconds,
            poll_timeout_seconds=poll_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
    )
    return errors


def _validate_adetailer_host_sync(context: ADetailerHostContext) -> list[str]:
    errors: list[str] = []
    if context.host_contract_version != context.local_contract_version:
        errors.append(
            "adetailer contract mismatch: "
            f"host='{context.host_contract_version}' workspace='{context.local_contract_version}'."
        )
    return errors


def _poll_queue_job_until_terminal(
    base_url: str,
    prompt_id: str,
    client_id: str,
    *,
    request_timeout_seconds: float,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> dict[str, Any]:
    deadline = time.time() + poll_timeout_seconds
    encoded_prompt_id = urllib.parse.quote(prompt_id, safe="")
    encoded_client_id = urllib.parse.quote(client_id, safe="")
    queue_url = f"{base_url}/rookieui/queue/{encoded_prompt_id}?client_id={encoded_client_id}"
    while time.time() < deadline:
        payload = _request_json("GET", queue_url, timeout_seconds=request_timeout_seconds)
        job = payload.get("job")
        if isinstance(job, dict):
            status = str(job.get("status", "")).strip().lower()
            if status in {"completed", "failed", "cancelled"}:
                return job
        time.sleep(max(poll_interval_seconds, 0.1))
    raise RuntimeError(
        f"Queue polling timed out after {poll_timeout_seconds:.1f}s for prompt '{prompt_id}' and client '{client_id}'."
    )


def _run_execute_smoke(
    base_url: str,
    profiles: list[str],
    presets_by_id: dict[str, dict[str, Any]],
    *,
    request_timeout_seconds: float,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> list[str]:
    errors: list[str] = []
    for profile_id in profiles:
        preset = presets_by_id.get(profile_id)
        if preset is None:
            errors.append(f"profile '{profile_id}' missing preset; execute lane skipped.")
            continue
        client_id = f"rookieui-live-smoke-{profile_id}"
        request_payload = _build_txt2img_payload(profile_id, preset, client_id)
        submit_result = _request_json(
            "POST",
            f"{base_url}/rookieui/generate/txt2img",
            payload=request_payload,
            timeout_seconds=request_timeout_seconds,
        )
        submission = submit_result.get("submission") if isinstance(submit_result, dict) else None
        if not isinstance(submission, dict) or not bool(submission.get("accepted")):
            errors.append(
                f"profile '{profile_id}' submit failed: expected accepted submission payload, got '{submit_result}'."
            )
            continue
        prompt_id = str(submission.get("prompt_id", "")).strip()
        if not prompt_id:
            errors.append(f"profile '{profile_id}' submit missing prompt_id: '{submit_result}'.")
            continue
        job = _poll_queue_job_until_terminal(
            base_url,
            prompt_id,
            client_id,
            request_timeout_seconds=request_timeout_seconds,
            poll_timeout_seconds=poll_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        terminal_status = str(job.get("status", "")).strip().lower()
        if terminal_status != "completed":
            errors.append(
                f"profile '{profile_id}' execution ended in status '{terminal_status}': {json.dumps(job, ensure_ascii=True)}"
            )
    return errors


def _validate_prompt_parity_host_sync(context: PromptParityHostContext) -> list[str]:
    errors: list[str] = []
    if not context.host_contract_version:
        errors.append("live host /rookieui/capabilities payload did not expose prompt_semantics.contract_version.")
    elif context.host_contract_version != context.local_contract_version:
        errors.append(
            "live host prompt contract mismatch: "
            f"host='{context.host_contract_version}' workspace='{context.local_contract_version}'."
        )
    return errors


def _validate_controlnet_host_sync(context: ControlNetHostContext) -> list[str]:
    errors: list[str] = []
    if not context.host_contract_version:
        errors.append("live host ControlNet routes did not expose contract.version.")
    elif context.host_contract_version != context.local_contract_version:
        errors.append(
            "live host ControlNet contract mismatch: "
            f"host='{context.host_contract_version}' workspace='{context.local_contract_version}'."
        )
    return errors


def _run_auxiliary_pipeline_validation_lane(
    base_url: str,
    models_payload: dict[str, Any],
    *,
    execute: bool,
    request_timeout_seconds: float,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> tuple[list[str], list[str]]:
    context = _build_auxiliary_pipeline_context(models_payload)
    extras_errors = _run_extras_execution_smoke(
        base_url,
        request_timeout_seconds=request_timeout_seconds,
    )
    pnginfo_errors, execute_case, execute_payload = _run_pnginfo_dry_run_smoke(
        base_url,
        context,
        request_timeout_seconds=request_timeout_seconds,
    )
    combined_errors = extras_errors + pnginfo_errors
    execution_errors: list[str] = []
    if execute:
        if execute_case is None or not isinstance(execute_payload, dict):
            execution_errors.append("auxiliary execute lane had no parsed apply-back payload.")
        elif not combined_errors:
            execution_errors = _run_auxiliary_queue_execute_smoke(
                base_url,
                case=execute_case,
                parsed_payload=execute_payload,
                request_timeout_seconds=request_timeout_seconds,
                poll_timeout_seconds=poll_timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
            )
    return combined_errors, execution_errors


def _run_controlnet_validation_lane(
    base_url: str,
    models_payload: dict[str, Any],
    profiles: list[str],
    *,
    execute: bool,
    request_timeout_seconds: float,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> tuple[list[str], list[str]]:
    model_list_payload, module_list_payload, control_types_payload = _load_controlnet_payloads(
        base_url,
        request_timeout_seconds,
    )
    context, context_errors = _build_controlnet_host_context(
        models_payload,
        model_list_payload,
        module_list_payload,
        control_types_payload,
        profiles,
    )
    if context_errors:
        return context_errors, []
    assert context is not None

    sync_errors = _validate_controlnet_host_sync(context)
    dry_run_cases = _build_controlnet_dry_run_cases(context)
    detect_errors = _run_controlnet_detect_smoke(
        base_url,
        context,
        request_timeout_seconds=request_timeout_seconds,
    )
    dry_run_errors = _run_controlnet_dry_run_smoke(
        base_url,
        context,
        dry_run_cases,
        request_timeout_seconds=request_timeout_seconds,
    )
    combined_errors = sync_errors + detect_errors + dry_run_errors
    execution_errors: list[str] = []
    if execute and not combined_errors:
        execution_errors = _run_controlnet_execute_smoke(
            base_url,
            context,
            request_timeout_seconds=request_timeout_seconds,
            poll_timeout_seconds=poll_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
    return combined_errors, execution_errors


def _run_adetailer_validation_lane(
    base_url: str,
    models_payload: dict[str, Any],
    profiles: list[str],
    *,
    execute: bool,
    request_timeout_seconds: float,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> tuple[list[str], list[str]]:
    model_list_payload, module_list_payload, control_types_payload = _load_controlnet_payloads(
        base_url,
        request_timeout_seconds,
    )
    catalog_payload = _load_adetailer_catalog_payload(base_url, request_timeout_seconds)
    controlnet_context, controlnet_context_errors = _build_controlnet_host_context(
        models_payload,
        model_list_payload,
        module_list_payload,
        control_types_payload,
        profiles,
    )
    if controlnet_context_errors:
        return controlnet_context_errors, []
    assert controlnet_context is not None

    context, context_errors = _build_adetailer_host_context(catalog_payload, controlnet_context)
    if context_errors:
        return context_errors, []
    assert context is not None

    sync_errors = _validate_controlnet_host_sync(controlnet_context) + _validate_adetailer_host_sync(context)
    dry_run_cases = _build_adetailer_dry_run_cases(context)
    dry_run_errors = _run_adetailer_dry_run_smoke(
        base_url,
        context,
        dry_run_cases,
        request_timeout_seconds=request_timeout_seconds,
    )
    combined_errors = sync_errors + dry_run_errors
    execution_errors: list[str] = []
    if execute and not combined_errors:
        execution_errors = _run_adetailer_execute_smoke(
            base_url,
            context,
            request_timeout_seconds=request_timeout_seconds,
            poll_timeout_seconds=poll_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
    return combined_errors, execution_errors


def main() -> int:
    args = _build_parser().parse_args()
    base_url = _normalize_base_url(args.base_url)
    profiles = _parse_profiles(args.profiles or _default_profiles_for_mode(args.validation_mode))
    if args.validation_mode not in {"auxiliary-contracts", "auxiliary-pipelines", "prompt-workbench", "xyz-plot", "full-pipeline"} and not profiles:
        print("[live-smoke] ERROR: no profiles selected.", file=sys.stderr)
        return 1

    print(f"[live-smoke] base_url={base_url}")
    print(f"[live-smoke] profiles={','.join(profiles) if profiles else '<none>'}")
    print(f"[live-smoke] validation_mode={args.validation_mode}")
    print(f"[live-smoke] execute={'on' if args.execute else 'off'}")
    print(f"[live-smoke] report_only={'on' if args.report_only else 'off'}")

    try:
        bootstrap_payload = _load_bootstrap_payload(base_url, args.request_timeout_seconds)
    except Exception as exc:
        print(f"[live-smoke] ERROR: failed to load /bootstrap: {exc}", file=sys.stderr)
        return 0 if args.report_only else 1

    freshness_context, freshness_context_errors = _build_live_host_freshness_context(bootstrap_payload)
    if freshness_context_errors:
        print("[live-smoke] WARNING: live-host freshness validation reported issues:", file=sys.stderr)
        for error in freshness_context_errors:
            print(f"  - {error}", file=sys.stderr)
        return 0 if args.report_only else 1
    elif freshness_context is not None:
        freshness_errors = _validate_live_host_freshness(freshness_context)
        if freshness_errors:
            print("[live-smoke] WARNING: live-host freshness validation reported issues:", file=sys.stderr)
            for error in freshness_errors:
                print(f"  - {error}", file=sys.stderr)
            return 0 if args.report_only else 1

    if args.validation_mode == "auxiliary-contracts":
        try:
            auxiliary_errors = _run_auxiliary_contract_smoke(
                base_url,
                request_timeout_seconds=args.request_timeout_seconds,
            )
        except Exception as exc:
            print(f"[live-smoke] ERROR: auxiliary contract checks failed unexpectedly: {exc}", file=sys.stderr)
            return 0 if args.report_only else 1
        if auxiliary_errors:
            print("[live-smoke] ERROR: auxiliary contract validation failed:", file=sys.stderr)
            for error in auxiliary_errors:
                print(f"  - {error}", file=sys.stderr)
            return 0 if args.report_only else 1
        print("[live-smoke] auxiliary contract checks passed.")
        print("[live-smoke] PASS")
        return 0

    try:
        models_payload, presets_payload = _load_server_payloads(base_url, args.request_timeout_seconds)
    except Exception as exc:
        print(f"[live-smoke] ERROR: failed to load /models or /presets: {exc}", file=sys.stderr)
        return 1

    if args.validation_mode == "auxiliary-pipelines":
        try:
            combined_errors, execution_errors = _run_auxiliary_pipeline_validation_lane(
                base_url,
                models_payload,
                execute=args.execute,
                request_timeout_seconds=args.request_timeout_seconds,
                poll_timeout_seconds=args.poll_timeout_seconds,
                poll_interval_seconds=args.poll_interval_seconds,
            )
        except Exception as exc:
            print(f"[live-smoke] ERROR: auxiliary pipeline validation failed unexpectedly: {exc}", file=sys.stderr)
            return 0 if args.report_only else 1

        if combined_errors:
            print("[live-smoke] WARNING: auxiliary pipeline validation reported issues:", file=sys.stderr)
            for error in combined_errors:
                print(f"  - {error}", file=sys.stderr)
            if not args.report_only:
                return 1
        else:
            print("[live-smoke] auxiliary pipeline extras + pnginfo checks passed.")

        if args.execute:
            if combined_errors:
                print("[live-smoke] execute lane skipped because auxiliary dry-run checks were not green.")
            else:
                if execution_errors:
                    print("[live-smoke] ERROR: auxiliary execute lane failed:", file=sys.stderr)
                    for error in execution_errors:
                        print(f"  - {error}", file=sys.stderr)
                    return 0 if args.report_only else 1
                print("[live-smoke] auxiliary queue/apply-back execute checks passed.")

        if combined_errors:
            print("[live-smoke] REPORT-ONLY COMPLETE")
        else:
            print("[live-smoke] PASS")
        return 0

    if args.validation_mode == "prompt-workbench":
        try:
            combined_errors, execution_errors = _run_prompt_workbench_validation_lane(
                base_url,
                execute=args.execute,
                request_timeout_seconds=args.request_timeout_seconds,
            )
        except Exception as exc:
            print(f"[live-smoke] ERROR: prompt-workbench validation failed unexpectedly: {exc}", file=sys.stderr)
            return 0 if args.report_only else 1

        if combined_errors:
            print("[live-smoke] WARNING: prompt-workbench validation reported issues:", file=sys.stderr)
            for error in combined_errors:
                print(f"  - {error}", file=sys.stderr)
            if not args.report_only:
                return 1
        else:
            print("[live-smoke] prompt-workbench route/state checks passed.")

        if args.execute:
            if combined_errors:
                print("[live-smoke] execute lane skipped because prompt-workbench dry-run checks were not green.")
            elif execution_errors:
                print("[live-smoke] ERROR: prompt-workbench execute lane failed:", file=sys.stderr)
                for error in execution_errors:
                    print(f"  - {error}", file=sys.stderr)
                return 0 if args.report_only else 1
            else:
                print("[live-smoke] prompt-workbench execute checks passed.")

        if combined_errors:
            print("[live-smoke] REPORT-ONLY COMPLETE")
        else:
            print("[live-smoke] PASS")
        return 0

    if args.validation_mode == "xyz-plot":
        try:
            combined_errors, execution_errors = _run_xyz_plot_validation_lane(
                base_url,
                models_payload,
                execute=args.execute,
                request_timeout_seconds=args.request_timeout_seconds,
                poll_timeout_seconds=args.poll_timeout_seconds,
                poll_interval_seconds=args.poll_interval_seconds,
            )
        except Exception as exc:
            print(f"[live-smoke] ERROR: xyz-plot validation failed unexpectedly: {exc}", file=sys.stderr)
            return 0 if args.report_only else 1

        if combined_errors:
            print("[live-smoke] WARNING: xyz-plot validation reported issues:", file=sys.stderr)
            for error in combined_errors:
                print(f"  - {error}", file=sys.stderr)
            if not args.report_only:
                return 1
        else:
            print("[live-smoke] xyz-plot contract + estimate checks passed.")

        if args.execute:
            if combined_errors:
                print("[live-smoke] execute lane skipped because xyz-plot route checks were not green.")
            elif execution_errors:
                print("[live-smoke] ERROR: xyz-plot execute lane failed:", file=sys.stderr)
                for error in execution_errors:
                    print(f"  - {error}", file=sys.stderr)
                return 0 if args.report_only else 1
            else:
                print("[live-smoke] xyz-plot execute checks passed.")

        if combined_errors:
            print("[live-smoke] REPORT-ONLY COMPLETE")
        else:
            print("[live-smoke] PASS")
        return 0

    if args.validation_mode == "controlnet":
        try:
            combined_errors, execution_errors = _run_controlnet_validation_lane(
                base_url,
                models_payload,
                profiles,
                execute=args.execute,
                request_timeout_seconds=args.request_timeout_seconds,
                poll_timeout_seconds=args.poll_timeout_seconds,
                poll_interval_seconds=args.poll_interval_seconds,
            )
        except Exception as exc:
            print(f"[live-smoke] ERROR: controlnet validation failed unexpectedly: {exc}", file=sys.stderr)
            return 0 if args.report_only else 1
        if combined_errors:
            print("[live-smoke] WARNING: controlnet validation reported issues:", file=sys.stderr)
            for error in combined_errors:
                print(f"  - {error}", file=sys.stderr)
            if not args.report_only:
                return 1
        else:
            print("[live-smoke] controlnet detect + dry-run checks passed.")

        if args.execute:
            if combined_errors:
                print("[live-smoke] execute lane skipped because controlnet detect/dry-run was not green.")
            else:
                if execution_errors:
                    print("[live-smoke] ERROR: controlnet execute lane failed:", file=sys.stderr)
                    for error in execution_errors:
                        print(f"  - {error}", file=sys.stderr)
                    return 0 if args.report_only else 1
                print("[live-smoke] controlnet execute checks passed.")

        if combined_errors:
            print("[live-smoke] REPORT-ONLY COMPLETE")
        else:
            print("[live-smoke] PASS")
        return 0

    if args.validation_mode == "adetailer":
        try:
            combined_errors, execution_errors = _run_adetailer_validation_lane(
                base_url,
                models_payload,
                profiles,
                execute=args.execute,
                request_timeout_seconds=args.request_timeout_seconds,
                poll_timeout_seconds=args.poll_timeout_seconds,
                poll_interval_seconds=args.poll_interval_seconds,
            )
        except Exception as exc:
            print(f"[live-smoke] ERROR: adetailer validation failed unexpectedly: {exc}", file=sys.stderr)
            return 0 if args.report_only else 1
        if combined_errors:
            print("[live-smoke] WARNING: adetailer validation reported issues:", file=sys.stderr)
            for error in combined_errors:
                print(f"  - {error}", file=sys.stderr)
            if not args.report_only:
                return 1
        else:
            print("[live-smoke] adetailer dry-run checks passed.")

        if args.execute:
            if combined_errors:
                print("[live-smoke] execute lane skipped because adetailer dry-run was not green.")
            else:
                if execution_errors:
                    print("[live-smoke] ERROR: adetailer execute lane failed:", file=sys.stderr)
                    for error in execution_errors:
                        print(f"  - {error}", file=sys.stderr)
                    return 0 if args.report_only else 1
                print("[live-smoke] adetailer execute checks passed.")

        if combined_errors:
            print("[live-smoke] REPORT-ONLY COMPLETE")
        else:
            print("[live-smoke] PASS")
        return 0

    if args.validation_mode == "full-pipeline":
        controlnet_profiles = _parse_profiles(_default_profiles_for_mode("controlnet"))
        adetailer_profiles = _parse_profiles(_default_profiles_for_mode("adetailer"))
        pipeline_errors = False

        try:
            controlnet_errors, controlnet_execute_errors = _run_controlnet_validation_lane(
                base_url,
                models_payload,
                controlnet_profiles,
                execute=args.execute,
                request_timeout_seconds=args.request_timeout_seconds,
                poll_timeout_seconds=args.poll_timeout_seconds,
                poll_interval_seconds=args.poll_interval_seconds,
            )
        except Exception as exc:
            print(f"[live-smoke] ERROR: full-pipeline ControlNet lane failed unexpectedly: {exc}", file=sys.stderr)
            return 0 if args.report_only else 1
        if controlnet_errors:
            pipeline_errors = True
            print("[live-smoke] WARNING: full-pipeline controlnet lane reported issues:", file=sys.stderr)
            for error in controlnet_errors:
                print(f"  - {error}", file=sys.stderr)
            if not args.report_only:
                return 1
        else:
            print("[live-smoke] full-pipeline controlnet dry-run checks passed.")
        if args.execute:
            if controlnet_errors:
                print("[live-smoke] full-pipeline controlnet execute skipped because dry-run was not green.")
            elif controlnet_execute_errors:
                print("[live-smoke] ERROR: full-pipeline controlnet execute lane failed:", file=sys.stderr)
                for error in controlnet_execute_errors:
                    print(f"  - {error}", file=sys.stderr)
                return 0 if args.report_only else 1
            else:
                print("[live-smoke] full-pipeline controlnet execute checks passed.")

        try:
            adetailer_errors, adetailer_execute_errors = _run_adetailer_validation_lane(
                base_url,
                models_payload,
                adetailer_profiles,
                execute=args.execute,
                request_timeout_seconds=args.request_timeout_seconds,
                poll_timeout_seconds=args.poll_timeout_seconds,
                poll_interval_seconds=args.poll_interval_seconds,
            )
        except Exception as exc:
            print(f"[live-smoke] ERROR: full-pipeline ADetailer lane failed unexpectedly: {exc}", file=sys.stderr)
            return 0 if args.report_only else 1
        if adetailer_errors:
            pipeline_errors = True
            print("[live-smoke] WARNING: full-pipeline adetailer lane reported issues:", file=sys.stderr)
            for error in adetailer_errors:
                print(f"  - {error}", file=sys.stderr)
            if not args.report_only:
                return 1
        else:
            print("[live-smoke] full-pipeline adetailer dry-run checks passed.")
        if args.execute:
            if adetailer_errors:
                print("[live-smoke] full-pipeline adetailer execute skipped because dry-run was not green.")
            elif adetailer_execute_errors:
                print("[live-smoke] ERROR: full-pipeline adetailer execute lane failed:", file=sys.stderr)
                for error in adetailer_execute_errors:
                    print(f"  - {error}", file=sys.stderr)
                return 0 if args.report_only else 1
            else:
                print("[live-smoke] full-pipeline adetailer execute checks passed.")

        try:
            auxiliary_errors, auxiliary_execute_errors = _run_auxiliary_pipeline_validation_lane(
                base_url,
                models_payload,
                execute=args.execute,
                request_timeout_seconds=args.request_timeout_seconds,
                poll_timeout_seconds=args.poll_timeout_seconds,
                poll_interval_seconds=args.poll_interval_seconds,
            )
        except Exception as exc:
            print(f"[live-smoke] ERROR: full-pipeline auxiliary lane failed unexpectedly: {exc}", file=sys.stderr)
            return 0 if args.report_only else 1
        if auxiliary_errors:
            pipeline_errors = True
            print("[live-smoke] WARNING: full-pipeline auxiliary lane reported issues:", file=sys.stderr)
            for error in auxiliary_errors:
                print(f"  - {error}", file=sys.stderr)
            if not args.report_only:
                return 1
        else:
            print("[live-smoke] full-pipeline auxiliary dry-run checks passed.")
        if args.execute:
            if auxiliary_errors:
                print("[live-smoke] full-pipeline auxiliary execute skipped because dry-run was not green.")
            elif auxiliary_execute_errors:
                print("[live-smoke] ERROR: full-pipeline auxiliary execute lane failed:", file=sys.stderr)
                for error in auxiliary_execute_errors:
                    print(f"  - {error}", file=sys.stderr)
                return 0 if args.report_only else 1
            else:
                print("[live-smoke] full-pipeline auxiliary execute checks passed.")

        try:
            xyz_errors, xyz_execute_errors = _run_xyz_plot_validation_lane(
                base_url,
                models_payload,
                execute=args.execute,
                request_timeout_seconds=args.request_timeout_seconds,
                poll_timeout_seconds=args.poll_timeout_seconds,
                poll_interval_seconds=args.poll_interval_seconds,
            )
        except Exception as exc:
            print(f"[live-smoke] ERROR: full-pipeline XYZ lane failed unexpectedly: {exc}", file=sys.stderr)
            return 0 if args.report_only else 1
        if xyz_errors:
            pipeline_errors = True
            print("[live-smoke] WARNING: full-pipeline xyz lane reported issues:", file=sys.stderr)
            for error in xyz_errors:
                print(f"  - {error}", file=sys.stderr)
            if not args.report_only:
                return 1
        else:
            print("[live-smoke] full-pipeline xyz route checks passed.")
        if args.execute:
            if xyz_errors:
                print("[live-smoke] full-pipeline xyz execute skipped because route checks were not green.")
            elif xyz_execute_errors:
                print("[live-smoke] ERROR: full-pipeline xyz execute lane failed:", file=sys.stderr)
                for error in xyz_execute_errors:
                    print(f"  - {error}", file=sys.stderr)
                return 0 if args.report_only else 1
            else:
                print("[live-smoke] full-pipeline xyz execute checks passed.")

        if pipeline_errors:
            print("[live-smoke] REPORT-ONLY COMPLETE")
        else:
            print("[live-smoke] PASS")
        return 0

    if args.validation_mode == "prompt-parity":
        try:
            capabilities_payload = _load_capabilities_payload(base_url, args.request_timeout_seconds)
        except Exception as exc:
            print(f"[live-smoke] ERROR: failed to load /capabilities: {exc}", file=sys.stderr)
            return 1

        context, context_errors = _build_prompt_parity_host_context(models_payload, capabilities_payload, profiles)
        if context_errors:
            print("[live-smoke] ERROR: prompt-parity host context validation failed:", file=sys.stderr)
            for error in context_errors:
                print(f"  - {error}", file=sys.stderr)
            return 0 if args.report_only else 1
        assert context is not None

        sync_errors = _validate_prompt_parity_host_sync(context)
        if sync_errors:
            print("[live-smoke] WARNING: prompt-parity host/workspace sync mismatch detected:", file=sys.stderr)
            for error in sync_errors:
                print(f"  - {error}", file=sys.stderr)

        cases = _build_prompt_parity_cases(context)
        try:
            dry_run_errors = _run_prompt_parity_dry_run_smoke(
                base_url,
                cases,
                request_timeout_seconds=args.request_timeout_seconds,
            )
        except Exception as exc:
            print(f"[live-smoke] ERROR: prompt-parity dry-run failed unexpectedly: {exc}", file=sys.stderr)
            return 0 if args.report_only else 1

        combined_errors = sync_errors + dry_run_errors
        if combined_errors:
            print("[live-smoke] WARNING: prompt-parity validation reported issues:", file=sys.stderr)
            for error in combined_errors:
                print(f"  - {error}", file=sys.stderr)
            if not args.report_only:
                return 1
        else:
            print("[live-smoke] prompt-parity dry-run checks passed.")

        if args.execute:
            if combined_errors:
                print("[live-smoke] execute lane skipped because prompt-parity dry-run was not green.")
            else:
                try:
                    execution_errors = _run_prompt_parity_execute_smoke(
                        base_url,
                        cases,
                        request_timeout_seconds=args.request_timeout_seconds,
                        poll_timeout_seconds=args.poll_timeout_seconds,
                        poll_interval_seconds=args.poll_interval_seconds,
                    )
                except Exception as exc:
                    print(f"[live-smoke] ERROR: prompt-parity execute lane failed unexpectedly: {exc}", file=sys.stderr)
                    return 0 if args.report_only else 1
                if execution_errors:
                    print("[live-smoke] ERROR: prompt-parity execute lane failed:", file=sys.stderr)
                    for error in execution_errors:
                        print(f"  - {error}", file=sys.stderr)
                    return 0 if args.report_only else 1
                print("[live-smoke] prompt-parity execute checks passed.")

        if combined_errors:
            print("[live-smoke] REPORT-ONLY COMPLETE")
        else:
            print("[live-smoke] PASS")
        return 0

    contract_errors, presets_by_id = _validate_catalog_contract(models_payload, presets_payload, profiles)
    if contract_errors:
        print("[live-smoke] ERROR: catalog contract validation failed:", file=sys.stderr)
        for error in contract_errors:
            print(f"  - {error}", file=sys.stderr)
        return 0 if args.report_only else 1
    print("[live-smoke] catalog contract checks passed.")

    if args.execute:
        try:
            execution_errors = _run_execute_smoke(
                base_url,
                profiles,
                presets_by_id,
                request_timeout_seconds=args.request_timeout_seconds,
                poll_timeout_seconds=args.poll_timeout_seconds,
                poll_interval_seconds=args.poll_interval_seconds,
            )
        except Exception as exc:
            print(f"[live-smoke] ERROR: execute lane failed unexpectedly: {exc}", file=sys.stderr)
            return 1
        if execution_errors:
            print("[live-smoke] ERROR: execution smoke failed:", file=sys.stderr)
            for error in execution_errors:
                print(f"  - {error}", file=sys.stderr)
            return 0 if args.report_only else 1
        print("[live-smoke] execution checks passed.")

    print("[live-smoke] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
