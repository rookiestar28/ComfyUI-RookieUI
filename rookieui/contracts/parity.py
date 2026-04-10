from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class A1111ParityProfile:
    id: str
    title: str
    base_family: str
    prompt_encoder: str
    default_width: int
    default_height: int
    default_steps: int
    default_cfg_scale: float
    default_sampler: str
    default_scheduler: str
    default_clip_skip: int = 1
    supports_clip_skip: bool = True
    notes: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SamplerAliasMap:
    samplers: dict[str, str]
    scheduler_aliases: dict[str, str]
    scheduler_overrides: dict[str, str]
    supported_schedulers: list[str]

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)
