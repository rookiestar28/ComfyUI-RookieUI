from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class PromptLoraActivation:
    name: str
    strength_model: float
    strength_clip: float
    source: str = "inline"
    dyn_dim: int | None = None

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromptAttentionMarker:
    token: str
    weight: float
    syntax: str

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromptEmbeddingReference:
    token: str
    canonical_token: str
    name: str
    exists: bool
    syntax: str

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromptScheduleSlice:
    text: str
    start: float = 0.0
    end: float = 1.0

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromptChunkSemantic:
    text: str
    slices: list[PromptScheduleSlice] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["slices"] = [slice_item.to_payload() for slice_item in self.slices]
        return payload


@dataclass(frozen=True)
class PromptBranchSemantic:
    text: str
    weight: float = 1.0
    chunks: list[PromptChunkSemantic] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["chunks"] = [chunk.to_payload() for chunk in self.chunks]
        return payload


@dataclass(frozen=True)
class PromptSemanticPlan:
    normalized_text: str
    features: dict[str, bool] = field(default_factory=dict)
    branches: list[PromptBranchSemantic] = field(default_factory=list)
    attention: list[PromptAttentionMarker] = field(default_factory=list)
    embeddings: list[PromptEmbeddingReference] = field(default_factory=list)
    guardrail_hits: list[str] = field(default_factory=list)

    @staticmethod
    def empty(text: str) -> "PromptSemanticPlan":
        return PromptSemanticPlan(
            normalized_text=text,
            features={
                "and_composition": False,
                "break_chunks": False,
                "prompt_scheduling": False,
                "alternate_prompt_scheduling": False,
                "attention_weighting": False,
                "embeddings_textual_inversion": False,
            },
            branches=[],
            attention=[],
            embeddings=[],
            guardrail_hits=[],
        )

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["branches"] = [branch.to_payload() for branch in self.branches]
        payload["attention"] = [marker.to_payload() for marker in self.attention]
        payload["embeddings"] = [reference.to_payload() for reference in self.embeddings]
        return payload


@dataclass(frozen=True)
class PromptPreprocessResult:
    cleaned_prompt: str
    cleaned_negative_prompt: str
    lora_activations: list[PromptLoraActivation] = field(default_factory=list)
    prompt_warnings: list[str] = field(default_factory=list)
    warning_codes: list[str] = field(default_factory=list)
    prompt_semantics: PromptSemanticPlan = field(default_factory=lambda: PromptSemanticPlan.empty(""))
    negative_prompt_semantics: PromptSemanticPlan = field(default_factory=lambda: PromptSemanticPlan.empty(""))

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["lora_activations"] = [activation.to_payload() for activation in self.lora_activations]
        payload["prompt_semantics"] = self.prompt_semantics.to_payload()
        payload["negative_prompt_semantics"] = self.negative_prompt_semantics.to_payload()
        return payload
