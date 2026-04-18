from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from rookieui.contracts.model_family_registry import build_model_family_registry_payload
from rookieui.services.adetailer import build_adetailer_capability_payload
from rookieui.services.parity_matrix import build_parity_payload
from rookieui.services.prompt_capability_matrix import build_prompt_capability_matrix_payload
from rookieui.services.version import resolve_shell_version


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
    shell_version: str = field(default_factory=resolve_shell_version)
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
            "adetailer": True,
            "controlnet": True,
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
    model_families: dict[str, object] = field(default_factory=build_model_family_registry_payload)
    prompt_semantics: dict[str, object] = field(default_factory=build_prompt_capability_matrix_payload)
    adetailer: dict[str, object] = field(default_factory=build_adetailer_capability_payload)
    routes: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)
