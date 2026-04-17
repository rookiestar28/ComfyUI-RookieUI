from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

XYZ_PLOT_CONTRACT_VERSION = "r139-20260418"
XYZ_PLOT_ROUTE_FAMILY = "/rookieui/xyz-plot"
XYZ_PLOT_SESSION_EXECUTION_MODEL = "queue_backed_rookieui_session_runner"
XYZ_PLOT_GRID_DELIVERY_MODEL = "rookieui_asset_store_grid_outputs"
XYZ_PLOT_SUPPORTED_MODES = ("txt2img", "img2img")
XYZ_PLOT_SUPPORT_TIERS = ("direct", "adapted", "not_supported_yet")
XYZ_PLOT_ROUTE_SURFACES = (
    "xyz_plot_axes",
    "xyz_plot_estimate",
    "xyz_plot_run",
    "xyz_plot_session_list",
    "xyz_plot_session_detail",
    "xyz_plot_session_cancel",
)
XYZ_PLOT_ROUTE_PATHS = (
    f"{XYZ_PLOT_ROUTE_FAMILY}/axes",
    f"{XYZ_PLOT_ROUTE_FAMILY}/estimate",
    f"{XYZ_PLOT_ROUTE_FAMILY}/run",
    f"{XYZ_PLOT_ROUTE_FAMILY}/sessions",
    f"{XYZ_PLOT_ROUTE_FAMILY}/sessions/{{session_id}}",
    f"{XYZ_PLOT_ROUTE_FAMILY}/sessions/{{session_id}}/cancel",
)
XYZ_PLOT_ADAPTATION_RULES = (
    "Do not port the A1111 Gradio script-slot mechanism into RookieUI.",
    "Do not mutate a shared processing object directly; every XYZ cell must flow through RookieUI normalization, translation, and prompt submission seams.",
    "Keep execution queue-backed and session-owned instead of inventing a parallel runtime.",
    "Expose only axes that RookieUI can support truthfully at the current phase boundary.",
    "Keep grid assembly and asset delivery RookieUI-owned rather than reusing A1111 save/grid assumptions directly.",
)


@dataclass(frozen=True)
class XYZPlotAxisContract:
    axis_id: str
    title: str
    support_tier: str
    mode_scopes: tuple[str, ...]
    value_input_mode: str
    a1111_reference_label: str
    notes: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["mode_scopes"] = list(self.mode_scopes)
        payload["notes"] = list(self.notes)
        return payload


@dataclass(frozen=True)
class XYZPlotRouteContract:
    version: str = XYZ_PLOT_CONTRACT_VERSION
    route_family: str = XYZ_PLOT_ROUTE_FAMILY
    supported_modes: tuple[str, ...] = XYZ_PLOT_SUPPORTED_MODES
    route_surfaces: tuple[str, ...] = XYZ_PLOT_ROUTE_SURFACES
    route_paths: tuple[str, ...] = XYZ_PLOT_ROUTE_PATHS
    session_execution_model: str = XYZ_PLOT_SESSION_EXECUTION_MODEL
    grid_delivery_model: str = XYZ_PLOT_GRID_DELIVERY_MODEL
    support_tiers: tuple[str, ...] = XYZ_PLOT_SUPPORT_TIERS
    adaptation_rules: tuple[str, ...] = XYZ_PLOT_ADAPTATION_RULES

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["supported_modes"] = list(self.supported_modes)
        payload["route_surfaces"] = list(self.route_surfaces)
        payload["route_paths"] = list(self.route_paths)
        payload["support_tiers"] = list(self.support_tiers)
        payload["adaptation_rules"] = list(self.adaptation_rules)
        return payload


def _axis_contracts() -> tuple[XYZPlotAxisContract, ...]:
    return (
        XYZPlotAxisContract(
            axis_id="seed",
            title="Seed",
            support_tier="direct",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="int_csv_or_range",
            a1111_reference_label="Seed",
            notes=("Maps directly to RookieUI generation seed fields, including session-level fixed-seed and vary-seed policy follow-ups.",),
        ),
        XYZPlotAxisContract(
            axis_id="steps",
            title="Steps",
            support_tier="direct",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="int_csv_or_range",
            a1111_reference_label="Steps",
        ),
        XYZPlotAxisContract(
            axis_id="cfg_scale",
            title="CFG Scale",
            support_tier="direct",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="float_csv_or_range",
            a1111_reference_label="CFG Scale",
        ),
        XYZPlotAxisContract(
            axis_id="sampler",
            title="Sampler",
            support_tier="direct",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="choices_or_csv",
            a1111_reference_label="Sampler",
        ),
        XYZPlotAxisContract(
            axis_id="scheduler",
            title="Schedule Type",
            support_tier="direct",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="choices_or_csv",
            a1111_reference_label="Schedule type",
        ),
        XYZPlotAxisContract(
            axis_id="checkpoint_name",
            title="Checkpoint Name",
            support_tier="direct",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="choices_or_csv",
            a1111_reference_label="Checkpoint name",
        ),
        XYZPlotAxisContract(
            axis_id="vae",
            title="VAE",
            support_tier="direct",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="choices_or_csv",
            a1111_reference_label="VAE",
        ),
        XYZPlotAxisContract(
            axis_id="clip_skip",
            title="Clip Skip",
            support_tier="adapted",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="int_csv_or_range",
            a1111_reference_label="Clip skip",
            notes=("Profile-aware because non-SD-family profiles may coerce clip skip to the host-safe default.",),
        ),
        XYZPlotAxisContract(
            axis_id="size",
            title="Size",
            support_tier="direct",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="size_csv",
            a1111_reference_label="Size",
        ),
        XYZPlotAxisContract(
            axis_id="denoising_strength",
            title="Denoising",
            support_tier="direct",
            mode_scopes=("img2img",),
            value_input_mode="float_csv_or_range",
            a1111_reference_label="Denoising",
        ),
        XYZPlotAxisContract(
            axis_id="hires_steps",
            title="Hires Steps",
            support_tier="adapted",
            mode_scopes=("txt2img",),
            value_input_mode="int_csv_or_range",
            a1111_reference_label="Hires steps",
            notes=("Backed by RookieUI's integrated hires path instead of A1111's mutable processing object fields.",),
        ),
        XYZPlotAxisContract(
            axis_id="hires_upscaler",
            title="Hires Upscaler",
            support_tier="adapted",
            mode_scopes=("txt2img",),
            value_input_mode="choices_or_csv",
            a1111_reference_label="Hires upscaler",
        ),
        XYZPlotAxisContract(
            axis_id="var_seed",
            title="Var. seed",
            support_tier="adapted",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="int_csv_or_range",
            a1111_reference_label="Var. seed",
            notes=("Requires RookieUI-owned seed-variation expansion rather than direct A1111 subseed mutation.",),
        ),
        XYZPlotAxisContract(
            axis_id="var_strength",
            title="Var. strength",
            support_tier="adapted",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="float_csv_or_range",
            a1111_reference_label="Var. strength",
        ),
        XYZPlotAxisContract(
            axis_id="prompt_sr",
            title="Prompt S/R",
            support_tier="adapted",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="csv_pairs",
            a1111_reference_label="Prompt S/R",
            notes=("Must reuse RookieUI prompt normalization rather than raw prompt string mutation only.",),
        ),
        XYZPlotAxisContract(
            axis_id="prompt_order",
            title="Prompt Order",
            support_tier="adapted",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="permutation_csv",
            a1111_reference_label="Prompt order",
        ),
        XYZPlotAxisContract(
            axis_id="styles",
            title="Styles",
            support_tier="not_supported_yet",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="choices_or_csv",
            a1111_reference_label="Styles",
            notes=("RookieUI does not currently ship a truthful A1111 style-library surface.",),
        ),
        XYZPlotAxisContract(
            axis_id="face_restore",
            title="Face Restore",
            support_tier="not_supported_yet",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="choices_or_csv",
            a1111_reference_label="Face restore",
            notes=("Current Extras face-restoration behavior is guarded warning/skip, not execution parity.",),
        ),
        XYZPlotAxisContract(
            axis_id="refiner_checkpoint",
            title="Refiner Checkpoint",
            support_tier="not_supported_yet",
            mode_scopes=("txt2img",),
            value_input_mode="choices_or_csv",
            a1111_reference_label="Refiner checkpoint",
        ),
        XYZPlotAxisContract(
            axis_id="refiner_switch_at",
            title="Refiner Switch At",
            support_tier="not_supported_yet",
            mode_scopes=("txt2img",),
            value_input_mode="float_csv_or_range",
            a1111_reference_label="Refiner switch at",
        ),
        XYZPlotAxisContract(
            axis_id="token_merging_ratio",
            title="Token Merging Ratio",
            support_tier="not_supported_yet",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="float_csv_or_range",
            a1111_reference_label="Token merging ratio",
        ),
        XYZPlotAxisContract(
            axis_id="rng_source",
            title="RNG Source",
            support_tier="not_supported_yet",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="choices_or_csv",
            a1111_reference_label="RNG source",
        ),
        XYZPlotAxisContract(
            axis_id="fp8_mode",
            title="FP8 Mode",
            support_tier="not_supported_yet",
            mode_scopes=("txt2img", "img2img"),
            value_input_mode="choices_or_csv",
            a1111_reference_label="FP8 mode",
        ),
    )


def build_xyz_plot_contract_meta(*, surface: str = "xyz_plot") -> dict[str, Any]:
    payload = XYZPlotRouteContract().to_payload()
    payload["surface"] = surface
    return payload


def build_xyz_plot_axis_support_payload() -> dict[str, Any]:
    axes = [axis.to_payload() for axis in _axis_contracts()]
    return {
        "contract": build_xyz_plot_contract_meta(surface="xyz_plot_axes_contract"),
        "axes": axes,
        "support_summary": {
            "direct": [axis["axis_id"] for axis in axes if axis["support_tier"] == "direct"],
            "adapted": [axis["axis_id"] for axis in axes if axis["support_tier"] == "adapted"],
            "not_supported_yet": [axis["axis_id"] for axis in axes if axis["support_tier"] == "not_supported_yet"],
        },
    }


def build_xyz_plot_contract_payload() -> dict[str, Any]:
    return {
        "contract": build_xyz_plot_contract_meta(surface="xyz_plot_contract"),
        "session_model": {
            "execution_model": XYZ_PLOT_SESSION_EXECUTION_MODEL,
            "submission_path": "reuse_existing_rookieui_generate_routes",
            "queue_ownership": "session_owned_prompt_metadata",
        },
        "grid_delivery": {
            "delivery_model": XYZ_PLOT_GRID_DELIVERY_MODEL,
            "subgrid_policy": "explicit_runtime_option",
            "metadata_embedding": "xyz_plot_axis_labels_and_values",
        },
        "axis_support": build_xyz_plot_axis_support_payload()["axes"],
    }
