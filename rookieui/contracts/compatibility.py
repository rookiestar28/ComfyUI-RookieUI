from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CompatibilityOption:
    id: str
    title: str
    summary: str
    default: bool = False
    experimental: bool = False
    aliases: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SchedulerCatalogEntry:
    id: str
    title: str
    tier: str
    default: bool = False
    aliases: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SamplerCatalogEntry:
    id: str
    title: str
    tier: str
    default: bool = False
    aliases: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompatibilityCatalogSnapshot:
    source: str = "internal"
    samplers: list[SamplerCatalogEntry] = field(default_factory=list)
    schedulers: list[SchedulerCatalogEntry] = field(default_factory=list)
    runtime_profiles: list[CompatibilityOption] = field(default_factory=list)
    dtype_profiles: list[CompatibilityOption] = field(default_factory=list)
    newer_family_profiles: list[CompatibilityOption] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)
