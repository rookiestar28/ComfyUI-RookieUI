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
class PromptPreprocessResult:
    cleaned_prompt: str
    cleaned_negative_prompt: str
    lora_activations: list[PromptLoraActivation] = field(default_factory=list)
    prompt_warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["lora_activations"] = [activation.to_payload() for activation in self.lora_activations]
        return payload
