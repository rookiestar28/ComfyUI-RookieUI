from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class PNGInfoParseResult:
    source: str
    source_type: str
    target_form: str
    payload: dict[str, Any]
    raw_parameters: dict[str, Any]
    metadata_items: dict[str, str] = field(default_factory=dict)
    apply_targets: list[str] = field(default_factory=list)
    asset_handle: str = ""
    unsupported_fields: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)
