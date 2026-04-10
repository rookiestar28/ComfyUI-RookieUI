from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from rookieui.services.parity_matrix import build_parity_payload


@dataclass(frozen=True)
class RookieUITabSnapshot:
    id: str
    title: str
    state: str
    enabled: bool


@dataclass(frozen=True)
class RookieUICapabilitiesSnapshot:
    service: str = "rookieui"
    visibility: str = "internal"
    shell_version: str = "0.1.0"
    host_surfaces: list[str] = field(
        default_factory=lambda: ["standalone-web", "desktop"]
    )
    features: dict[str, bool] = field(
        default_factory=lambda: {
            "sidebarShell": True,
            "capabilityBootstrap": True,
            "parityMatrix": True,
            "workflowTranslation": True,
            "modelInventory": True,
            "presets": True,
            "compatibilityLayer": True,
            "txt2img": True,
            "img2img": True,
            "extras": True,
            "pngInfo": True,
            "queue": True,
        }
    )
    tabs: list[RookieUITabSnapshot] = field(
        default_factory=lambda: [
            RookieUITabSnapshot(
                id="txt2img",
                title="Txt2Img",
                state="active",
                enabled=True,
            ),
            RookieUITabSnapshot(
                id="img2img",
                title="Img2Img",
                state="active",
                enabled=True,
            ),
            RookieUITabSnapshot(
                id="extras",
                title="Extras",
                state="active",
                enabled=True,
            ),
            RookieUITabSnapshot(
                id="pnginfo",
                title="PNG Info",
                state="active",
                enabled=True,
            ),
            RookieUITabSnapshot(
                id="queue",
                title="Queue",
                state="active",
                enabled=True,
            ),
        ]
    )
    parity: dict[str, object] = field(default_factory=build_parity_payload)
    routes: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)
