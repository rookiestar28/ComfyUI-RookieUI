from __future__ import annotations

from dataclasses import dataclass

from rookieui.contracts.models import ModelInventorySnapshot

ALL_PROMPT_FEATURES = (
    "and_composition",
    "break_chunks",
    "prompt_scheduling",
    "alternate_prompt_scheduling",
    "attention_weighting",
    "embeddings_textual_inversion",
)
SDXL_PROMPT_PROFILES = {"sdxl", "pony", "illustrious", "noob"}
_LONG_COMMA_SD15_PROMPT = ", ".join(
    [
        "portrait",
        "alley",
        "lantern",
        "rain",
        "neon",
        "steam",
        "rooftop",
        "city",
        "midnight",
        "thunder",
    ]
    * 9
)


@dataclass(frozen=True)
class ExpectedEmbeddingRef:
    canonical_token: str
    exists: bool
    syntax: str


@dataclass(frozen=True)
class PromptParityGoldenCase:
    case_id: str
    profile: str
    prompt: str
    negative_prompt: str = ""
    inventory_embeddings: tuple[str, ...] = ()
    expected_cleaned_prompt: str = ""
    expected_cleaned_negative_prompt: str = ""
    expected_warning_codes: tuple[str, ...] = ()
    expected_prompt_features: tuple[str, ...] = ()
    expected_negative_features: tuple[str, ...] = ()
    expected_prompt_embeddings: tuple[ExpectedEmbeddingRef, ...] = ()
    expected_negative_embeddings: tuple[ExpectedEmbeddingRef, ...] = ()
    expected_prompt_branch_count: int = 1
    expected_negative_branch_count: int = 1
    expected_encoder_class: str = "RookieUIA1111CLIPTextEncode"
    expect_conditioning_combine: bool = False
    expect_timestep_range: bool = False
    expected_prompt_workflow_fragments: tuple[str, ...] = ()
    expected_negative_workflow_fragments: tuple[str, ...] = ()


PROMPT_PARITY_GOLDEN_CASES = (
    PromptParityGoldenCase(
        case_id="sd15_attention_brackets",
        profile="sd15",
        prompt="portrait [soft light]",
        expected_cleaned_prompt="portrait [soft light]",
        expected_warning_codes=("PROMPT_ATTENTION_DETECTED",),
        expected_prompt_features=("attention_weighting",),
        expected_encoder_class="RookieUIA1111CLIPTextEncode",
    ),
    PromptParityGoldenCase(
        case_id="sd15_long_comma_chunk",
        profile="sd15",
        prompt=_LONG_COMMA_SD15_PROMPT,
        expected_cleaned_prompt=_LONG_COMMA_SD15_PROMPT,
        expected_encoder_class="RookieUIA1111CLIPTextEncode",
    ),
    PromptParityGoldenCase(
        case_id="sd15_break_schedule",
        profile="sd15",
        prompt="hero BREAK [calm:chaos:0.4]",
        expected_cleaned_prompt="hero BREAK [calm:chaos:0.4]",
        expected_warning_codes=("PROMPT_BREAK_DETECTED", "PROMPT_SCHEDULE_DETECTED"),
        expected_prompt_features=("break_chunks", "prompt_scheduling"),
        expected_encoder_class="RookieUIA1111CLIPTextEncode",
        expect_conditioning_combine=True,
        expect_timestep_range=True,
    ),
    PromptParityGoldenCase(
        case_id="sd15_alternate_schedule",
        profile="sd15",
        prompt="portrait [warm|cool] light",
        expected_cleaned_prompt="portrait [warm|cool] light",
        expected_warning_codes=("PROMPT_ALTERNATE_DETECTED",),
        expected_prompt_features=("alternate_prompt_scheduling",),
        expected_encoder_class="RookieUIA1111CLIPTextEncode",
        expect_conditioning_combine=True,
        expect_timestep_range=True,
    ),
    PromptParityGoldenCase(
        case_id="sd15_and_multi_cond",
        profile="sd15",
        prompt="hero AND villain:0.7",
        expected_cleaned_prompt="hero AND villain:0.7",
        expected_warning_codes=("PROMPT_AND_DETECTED",),
        expected_prompt_features=("and_composition",),
        expected_prompt_branch_count=2,
        expected_encoder_class="RookieUIA1111CLIPTextEncode",
        expect_conditioning_combine=True,
        expect_timestep_range=True,
    ),
    PromptParityGoldenCase(
        case_id="sd15_embedding_bare",
        profile="sd15",
        prompt="portrait badhandv4 dramatic light",
        inventory_embeddings=("badhandv4.pt",),
        expected_cleaned_prompt="portrait embedding:badhandv4.pt dramatic light",
        expected_warning_codes=("PROMPT_EMBEDDING_DETECTED",),
        expected_prompt_features=("embeddings_textual_inversion",),
        expected_prompt_embeddings=(
            ExpectedEmbeddingRef(
                canonical_token="embedding:badhandv4.pt",
                exists=True,
                syntax="bare",
            ),
        ),
        expected_encoder_class="RookieUIA1111CLIPTextEncode",
        expected_prompt_workflow_fragments=("embedding:badhandv4.pt",),
    ),
    PromptParityGoldenCase(
        case_id="sd15_missing_explicit_embedding",
        profile="sd15",
        prompt="portrait embedding:missing_style dramatic light",
        inventory_embeddings=("badhandv4.pt",),
        expected_cleaned_prompt="portrait missing_style dramatic light",
        expected_warning_codes=("PROMPT_EMBEDDING_DETECTED", "PROMPT_EMBEDDING_MISSING"),
        expected_prompt_features=("embeddings_textual_inversion",),
        expected_prompt_embeddings=(
            ExpectedEmbeddingRef(
                canonical_token="missing_style",
                exists=False,
                syntax="explicit",
            ),
        ),
        expected_encoder_class="RookieUIA1111CLIPTextEncode",
        expected_prompt_workflow_fragments=("missing_style",),
    ),
    PromptParityGoldenCase(
        case_id="pony_mixed_compound_with_negative_embedding",
        profile="pony",
        prompt="((hero)) AND badhandv4 BREAK [day:night:0.5]",
        negative_prompt="embedding:badhandv4.pt [low quality]",
        inventory_embeddings=("badhandv4.pt",),
        expected_cleaned_prompt="((hero)) AND embedding:badhandv4.pt BREAK [day:night:0.5]",
        expected_cleaned_negative_prompt="embedding:badhandv4.pt [low quality]",
        expected_warning_codes=(
            "PROMPT_AND_DETECTED",
            "PROMPT_BREAK_DETECTED",
            "PROMPT_SCHEDULE_DETECTED",
            "PROMPT_ATTENTION_DETECTED",
            "PROMPT_EMBEDDING_DETECTED",
        ),
        expected_prompt_features=(
            "and_composition",
            "break_chunks",
            "prompt_scheduling",
            "attention_weighting",
            "embeddings_textual_inversion",
        ),
        expected_negative_features=("attention_weighting", "embeddings_textual_inversion"),
        expected_prompt_embeddings=(
            ExpectedEmbeddingRef(
                canonical_token="embedding:badhandv4.pt",
                exists=True,
                syntax="bare",
            ),
        ),
        expected_negative_embeddings=(
            ExpectedEmbeddingRef(
                canonical_token="embedding:badhandv4.pt",
                exists=True,
                syntax="explicit",
            ),
        ),
        expected_prompt_branch_count=2,
        expected_encoder_class="RookieUIA1111CLIPTextEncodeSDXL",
        expect_conditioning_combine=True,
        expect_timestep_range=True,
        expected_prompt_workflow_fragments=("embedding:badhandv4.pt",),
        expected_negative_workflow_fragments=("embedding:badhandv4.pt",),
    ),
)


def build_fixture_inventory(case: PromptParityGoldenCase) -> ModelInventorySnapshot:
    checkpoint_name = (
        "SDXL\\pony.safetensors"
        if case.profile in SDXL_PROMPT_PROFILES
        else "SD15\\dreamshaper.safetensors"
    )
    return ModelInventorySnapshot(
        source="host",
        checkpoints=[checkpoint_name],
        vae=["Automatic"],
        text_encoders=["Automatic"],
        embeddings=list(case.inventory_embeddings),
        loras=[],
        default_checkpoint=checkpoint_name,
        default_vae="Automatic",
        default_text_encoder="Automatic",
    )
