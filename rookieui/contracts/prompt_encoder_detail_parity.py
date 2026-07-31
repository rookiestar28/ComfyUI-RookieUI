from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

PROMPT_ENCODER_DETAIL_PARITY_CONTRACT_VERSION = "prompt-encoder-smznodes-detail-parity-20260801"

PROMPT_ENCODER_DETAIL_PARITY_STATUSES = (
    "completed",
    "implemented",
    "in_progress",
    "planned",
    "planned_optional_live",
    "adapted_comfyui_native",
    "gated",
)


@dataclass(frozen=True)
class PromptEncoderDetailDimension:
    dimension_id: str
    title: str
    reference_surface: str
    rookieui_target: str
    status: str
    delivery_group: str
    acceptance_signal: str

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromptEncoderDetailFeature:
    feature_id: str
    title: str
    status: str
    covers: tuple[str, ...]
    acceptance_signal: str

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["covers"] = list(self.covers)
        return payload


def _dimension_entries() -> tuple[PromptEncoderDetailDimension, ...]:
    return (
        PromptEncoderDetailDimension(
            dimension_id="parser_mode_matrix",
            title="Parser Mode Matrix",
            reference_surface="smZNodes CLIP Text Encode++ parser selector",
            rookieui_target="Expose or explicitly gate supported parser modes without changing default A1111 parity.",
            status="completed",
            delivery_group="parser_modes",
            acceptance_signal="unit tests prove parser mode selection and unsupported-mode diagnostics.",
        ),
        PromptEncoderDetailDimension(
            dimension_id="a1111_default_parser",
            title="A1111 Default Parser",
            reference_surface="stable-diffusion-webui default prompt parser",
            rookieui_target="Keep Phase 100 default parser behavior stable.",
            status="implemented",
            delivery_group="parser_modes",
            acceptance_signal="existing node-level prompt encoding tests cover A1111 schedules, AND, BREAK, and attention.",
        ),
        PromptEncoderDetailDimension(
            dimension_id="full_parser",
            title="Full Parser",
            reference_surface="smZNodes full parser",
            rookieui_target="Pin whitespace/newline/special-character normalization when this mode is selected.",
            status="implemented",
            delivery_group="parser_modes",
            acceptance_signal="targeted tests prove full-parser text normalization before encoding.",
        ),
        PromptEncoderDetailDimension(
            dimension_id="comfy_plus_parser",
            title="Comfy++ Parser",
            reference_surface="smZNodes comfy++ parser",
            rookieui_target="Use Comfy-style parsing with A1111-style encoding/mean handling or gate it truthfully.",
            status="implemented",
            delivery_group="parser_modes",
            acceptance_signal="targeted tests prove either implemented behavior or explicit gated diagnostics.",
        ),
        PromptEncoderDetailDimension(
            dimension_id="fixed_attention_parser",
            title="Fixed Attention Parser",
            reference_surface="smZNodes fixed attention parser",
            rookieui_target="Support an attention-disabled encode mode without disrupting A1111 default parsing.",
            status="implemented",
            delivery_group="parser_modes",
            acceptance_signal="targeted tests prove weighted syntax is encoded literally in fixed-attention mode.",
        ),
        PromptEncoderDetailDimension(
            dimension_id="old_emphasis",
            title="Old Emphasis",
            reference_surface="smZNodes old emphasis implementation flag",
            rookieui_target="Make old-emphasis selection observable and regression-tested.",
            status="implemented",
            delivery_group="conditioning_weights",
            acceptance_signal="deterministic fake conditioning tests prove old and current emphasis modes differ where expected.",
        ),
        PromptEncoderDetailDimension(
            dimension_id="mean_normalization_exactness",
            title="Mean-Normalization Exactness",
            reference_surface="stable-diffusion-webui prompt mean normalization",
            rookieui_target="Keep mean normalization selectable and numerically pinned.",
            status="implemented",
            delivery_group="conditioning_weights",
            acceptance_signal="unit tests cover enabled and disabled normalization behavior.",
        ),
        PromptEncoderDetailDimension(
            dimension_id="textual_inversion_scan",
            title="Textual Inversion Scan",
            reference_surface="smZNodes textual inversion embedding database",
            rookieui_target="Resolve explicit safe embedding roots without executing reference code.",
            status="implemented",
            delivery_group="textual_inversion",
            acceptance_signal="unit tests cover scanning and alias lookup using synthetic embedding fixtures.",
        ),
        PromptEncoderDetailDimension(
            dimension_id="embedding_prefix_alias",
            title="Embedding Prefix and Alias",
            reference_surface="A1111 optional embedding: prefix and bare embedding aliases",
            rookieui_target="Resolve prefixed and bare aliases consistently against the host-safe resolver.",
            status="implemented",
            delivery_group="textual_inversion",
            acceptance_signal="unit tests cover prefixed, bare, extensionless, and extension-bearing aliases.",
        ),
        PromptEncoderDetailDimension(
            dimension_id="missing_embedding_behavior",
            title="Missing Embedding Behavior",
            reference_surface="smZNodes/A1111 missing embedding handling",
            rookieui_target="Report missing embeddings truthfully without corrupting prompt text.",
            status="implemented",
            delivery_group="textual_inversion",
            acceptance_signal="unit tests cover missing embedding diagnostics and fallback text behavior.",
        ),
        PromptEncoderDetailDimension(
            dimension_id="multi_vector_embedding_injection",
            title="Multi-Vector Embedding Injection",
            reference_surface="smZNodes textual inversion token fix injection",
            rookieui_target="Inject multi-vector embeddings at stable token offsets in the RookieUI encode path.",
            status="implemented",
            delivery_group="textual_inversion",
            acceptance_signal="unit tests cover multi-vector fix offsets and chunk-boundary behavior.",
        ),
        PromptEncoderDetailDimension(
            dimension_id="sdxl_dual_channel_embedding",
            title="SDXL Dual-Channel Embedding",
            reference_surface="smZNodes SDXL clip_g/clip_l textual inversion vectors",
            rookieui_target="Validate and apply SDXL global/local vectors per channel.",
            status="implemented",
            delivery_group="sdxl_textual_inversion",
            acceptance_signal="unit tests cover g/l vector selection, mismatches, and fallback behavior.",
        ),
        PromptEncoderDetailDimension(
            dimension_id="live_tensor_differential",
            title="Live Tensor Differential",
            reference_surface="same-model smZNodes/A1111 tensor comparison",
            rookieui_target="Provide optional local report-only tensor comparison tooling.",
            status="implemented",
            delivery_group="tensor_differential",
            acceptance_signal="CLI tests prove prerequisite detection and skipped-report behavior without private assets.",
        ),
    )


def _feature_entries() -> tuple[PromptEncoderDetailFeature, ...]:
    return (
        PromptEncoderDetailFeature(
            feature_id="reference_baseline",
            title="smZNodes Detail Parity Reference Freeze",
            status="completed",
            covers=tuple(entry.dimension_id for entry in _dimension_entries()),
            acceptance_signal="this executable matrix and tests freeze the public reference scope.",
        ),
        PromptEncoderDetailFeature(
            feature_id="parser_modes",
            title="Prompt Parser Mode Matrix Parity",
            status="completed",
            covers=("parser_mode_matrix",),
            acceptance_signal="parser mode tests cover implemented and gated modes.",
        ),
        PromptEncoderDetailFeature(
            feature_id="conditioning_weights",
            title="Old Emphasis and Mean-Normalization Exactness",
            status="completed",
            covers=("old_emphasis", "mean_normalization_exactness"),
            acceptance_signal="emphasis/normalization tests prove observable behavior.",
        ),
        PromptEncoderDetailFeature(
            feature_id="textual_inversion",
            title="Textual Inversion Resolver Parity",
            status="completed",
            covers=(
                "textual_inversion_scan",
                "embedding_prefix_alias",
                "missing_embedding_behavior",
                "multi_vector_embedding_injection",
            ),
            acceptance_signal="resolver tests cover SD15 textual inversion behavior.",
        ),
        PromptEncoderDetailFeature(
            feature_id="sdxl_textual_inversion",
            title="SDXL Embedding and Dual-Channel Resolver Parity",
            status="completed",
            covers=("sdxl_dual_channel_embedding",),
            acceptance_signal="SDXL resolver tests cover dual-channel behavior.",
        ),
        PromptEncoderDetailFeature(
            feature_id="tensor_differential",
            title="Live Tensor Differential Harness",
            status="completed",
            covers=("live_tensor_differential",),
            acceptance_signal="harness tests cover safe skip/report behavior.",
        ),
        PromptEncoderDetailFeature(
            feature_id="acceptance_closure",
            title="smZNodes Detail Parity Acceptance Closure",
            status="completed",
            covers=tuple(entry.dimension_id for entry in _dimension_entries()),
            acceptance_signal="closure records and full gate completed after all Phase 101 items passed.",
        ),
    )


def build_prompt_encoder_detail_parity_payload() -> dict[str, Any]:
    return {
        "contract_version": PROMPT_ENCODER_DETAIL_PARITY_CONTRACT_VERSION,
        "reference": "smZNodes CLIP Text Encode++ / stable-diffusion-webui prompt encoding",
        "dimensions": [entry.to_payload() for entry in _dimension_entries()],
        "features": [entry.to_payload() for entry in _feature_entries()],
    }
