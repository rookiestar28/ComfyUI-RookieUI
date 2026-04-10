from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RookieUIQueueJob:
    id: str
    status: str
    priority: int | None = None
    create_time: int | None = None
    outputs_count: int = 0
    output_filenames: list[str] = field(default_factory=list)
    reusable_outputs: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RookieUIQueueSnapshot:
    source: str
    queue_remaining: int
    jobs: list[RookieUIQueueJob] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["jobs"] = [job.to_payload() for job in self.jobs]
        return payload
