from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeRouter:
    routes: list[tuple[str, str, Any]] = field(default_factory=list)

    def add_get(self, path: str, handler: Any) -> None:
        self.routes.append(("GET", path, handler))

    def add_post(self, path: str, handler: Any) -> None:
        self.routes.append(("POST", path, handler))


@dataclass
class FakeApp:
    router: FakeRouter = field(default_factory=FakeRouter)


@dataclass
class FakePromptServerInstance:
    app: FakeApp = field(default_factory=FakeApp)
