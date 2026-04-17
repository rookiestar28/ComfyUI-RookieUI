from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PROMPT_WORKBENCH_CONTRACT_VERSION = "r123f114f115f116f120-20260417"
PROMPT_WORKBENCH_STATE_SCHEMA_VERSION = 1
PROMPT_WORKBENCH_ROUTE_FAMILY = "/rookieui/prompt-tools"
PROMPT_WORKBENCH_NAMESPACES = (
    "txt2img_prompt",
    "txt2img_negative",
    "img2img_prompt",
    "img2img_negative",
)
PROMPT_WORKBENCH_PROVIDER_SECRET_FIELD_KEYS = (
    "access_token",
    "api_key",
    "authorization",
    "password",
    "secret",
    "token",
)
PROMPT_WORKBENCH_PROVIDER_SURFACES = ("translation", "ai_assist")
PROMPT_WORKBENCH_SHIPPED_TRANSLATION_PROVIDER_IDS = ("openai", "mymemory_free")
PROMPT_WORKBENCH_SHIPPED_AI_PROVIDER_IDS = ("openai",)
PROMPT_WORKBENCH_DEFERRED_AI_PROVIDER_IDS = ()
DEFAULT_PROMPT_WORKBENCH_AI_ASSIST_PRESET = (
    "Write a concise Stable Diffusion prompt from the user's image description. "
    "Keep the result comma-separated and production-ready. Preserve any explicit prompt syntax the user already includes. "
    "Do not add explanation, markdown, numbering, or surrounding quotes. Return prompt text only."
)
PROMPT_WORKBENCH_LANGUAGE_OPTIONS = (
    {"code": "en", "title": "English"},
    {"code": "zh-TW", "title": "Traditional Chinese"},
    {"code": "zh-CN", "title": "Simplified Chinese"},
    {"code": "ja", "title": "Japanese"},
    {"code": "ko", "title": "Korean"},
)
PROMPT_WORKBENCH_THEME_STYLE_OPTIONS = (
    {
        "id": "rookieui_classic",
        "title": "RookieUI Classic",
        "summary": "Default RookieUI framing with neutral panel contrast.",
    },
    {
        "id": "rookieui_graphite",
        "title": "Graphite Studio",
        "summary": "Higher-contrast shell chrome for denser prompt editing sessions.",
    },
    {
        "id": "rookieui_paper",
        "title": "Paper Notes",
        "summary": "Lighter note-card treatment for catalog and prompt drafting work.",
    },
)
PROMPT_WORKBENCH_REFERENCE_ONLY_PROVIDER_IDS = (
    "alibaba",
    "alibaba_free",
    "amazon",
    "baidu",
    "bing_free",
    "caiyun",
    "deepl",
    "google",
    "google_free",
    "iflytekV1",
    "iflytekV2",
    "microsoft",
    "niutrans",
    "tencent",
    "volcengine",
    "yandex",
    "youdao",
)


@dataclass(frozen=True)
class PromptWorkbenchProviderField:
    key: str
    title: str
    value_type: str = "string"
    default: Any = ""
    required: bool = False
    secret: bool = False
    max_length: int = 512
    min_value: float | None = None
    max_value: float | None = None
    placeholder: str = ""

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromptWorkbenchProviderCatalogEntry:
    provider_id: str
    title: str
    surface_scopes: tuple[str, ...]
    execution_state: str
    supports_batch: bool
    reference_origin: str
    summary: str
    config_fields: tuple[PromptWorkbenchProviderField, ...] = ()
    notes: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["config_fields"] = [field.to_payload() for field in self.config_fields]
        return payload


def _openai_provider_fields() -> tuple[PromptWorkbenchProviderField, ...]:
    return (
        PromptWorkbenchProviderField(
            key="api_key",
            title="API Key",
            required=True,
            secret=True,
            placeholder="sk-...",
        ),
        PromptWorkbenchProviderField(
            key="base_url",
            title="Base URL",
            default="https://api.openai.com/v1",
            placeholder="https://api.openai.com/v1",
        ),
        PromptWorkbenchProviderField(
            key="model",
            title="Model",
            required=True,
            placeholder="gpt-4.1-mini",
        ),
        PromptWorkbenchProviderField(
            key="timeout_seconds",
            title="Timeout Seconds",
            value_type="integer",
            default=20,
            min_value=5,
            max_value=120,
        ),
    )


def _mymemory_provider_fields() -> tuple[PromptWorkbenchProviderField, ...]:
    return (
        PromptWorkbenchProviderField(
            key="email",
            title="Contact Email",
            placeholder="optional@example.com",
        ),
        PromptWorkbenchProviderField(
            key="base_url",
            title="Base URL",
            default="https://api.mymemory.translated.net/get",
            placeholder="https://api.mymemory.translated.net/get",
        ),
        PromptWorkbenchProviderField(
            key="timeout_seconds",
            title="Timeout Seconds",
            value_type="integer",
            default=15,
            min_value=5,
            max_value=60,
        ),
    )


def _provider_catalog_entries() -> tuple[PromptWorkbenchProviderCatalogEntry, ...]:
    return (
        PromptWorkbenchProviderCatalogEntry(
            provider_id="openai",
            title="OpenAI-Compatible Chat Translation",
            surface_scopes=("translation", "ai_assist"),
            execution_state="shipped",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: openai",
            summary="Network-backed translation path using an OpenAI-compatible chat-completions endpoint.",
            config_fields=_openai_provider_fields(),
            notes=(
                "Translation execution ships in F115.",
                "AI-assist execution ships in F120 through the same OpenAI-compatible provider contract.",
            ),
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="mymemory_free",
            title="MyMemory Free Translation",
            surface_scopes=("translation",),
            execution_state="shipped",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: myMemory_free / myMemory",
            summary="No-key translation path backed by the MyMemory public API.",
            config_fields=_mymemory_provider_fields(),
            notes=(
                "Best-effort public provider with lower reliability than dedicated API-key providers.",
            ),
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="bing_free",
            title="Microsoft Bing (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: bing_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="google_free",
            title="Google Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: google_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="google",
            title="Google (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: google",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="microsoft",
            title="Microsoft (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: microsoft",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="deepl",
            title="DeepL (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: deepl",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="amazon",
            title="Amazon (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: amazon",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="baidu",
            title="Baidu (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: baidu",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="alibaba",
            title="Alibaba (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: alibaba",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="alibaba_free",
            title="Alibaba Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: alibaba_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="yandex",
            title="Yandex (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: yandex",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="youdao",
            title="Youdao (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: youdao",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="tencent",
            title="Tencent (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: tencent",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="niutrans",
            title="Niutrans (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: niutrans",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="caiyun",
            title="Caiyun (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: caiyun",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="volcengine",
            title="Volcengine (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: volcengine",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="iflytekV1",
            title="iFlytek V1 (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: iflytekV1",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="iflytekV2",
            title="iFlytek V2 (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: iflytekV2",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
    )


def get_prompt_workbench_provider_catalog_entries(
    *, surface: str | None = None
) -> tuple[PromptWorkbenchProviderCatalogEntry, ...]:
    entries = _provider_catalog_entries()
    if surface is None:
        return entries
    return tuple(entry for entry in entries if surface in entry.surface_scopes)


def get_prompt_workbench_provider_catalog_entry(provider_id: object) -> PromptWorkbenchProviderCatalogEntry | None:
    normalized_provider_id = str(provider_id or "").strip()
    if not normalized_provider_id:
        return None
    for entry in _provider_catalog_entries():
        if entry.provider_id == normalized_provider_id:
            return entry
    return None


def get_prompt_workbench_provider_execution_state(provider_id: object, *, surface: str) -> str:
    normalized_provider_id = str(provider_id or "").strip()
    if not normalized_provider_id or surface not in PROMPT_WORKBENCH_PROVIDER_SURFACES:
        return "reference_only"
    if surface == "translation" and normalized_provider_id in PROMPT_WORKBENCH_SHIPPED_TRANSLATION_PROVIDER_IDS:
        return "shipped"
    if surface == "ai_assist" and normalized_provider_id in PROMPT_WORKBENCH_SHIPPED_AI_PROVIDER_IDS:
        return "shipped"
    if surface == "ai_assist" and normalized_provider_id in PROMPT_WORKBENCH_DEFERRED_AI_PROVIDER_IDS:
        return "deferred"
    if normalized_provider_id in PROMPT_WORKBENCH_REFERENCE_ONLY_PROVIDER_IDS:
        return "reference_only"
    return "reference_only"


def build_prompt_workbench_provider_catalog_payload() -> dict[str, Any]:
    surfaces: dict[str, Any] = {}
    for surface in PROMPT_WORKBENCH_PROVIDER_SURFACES:
        entries = [entry.to_payload() for entry in get_prompt_workbench_provider_catalog_entries(surface=surface)]
        for entry in entries:
            entry["execution_state"] = get_prompt_workbench_provider_execution_state(
                entry["provider_id"],
                surface=surface,
            )
        surfaces[surface] = {
            "providers": entries,
            "shipped_provider_ids": [
                entry["provider_id"]
                for entry in entries
                if entry["execution_state"] == "shipped"
            ],
            "deferred_provider_ids": [
                entry["provider_id"]
                for entry in entries
                if entry["execution_state"] == "deferred"
            ],
            "reference_only_provider_ids": [
                entry["provider_id"]
                for entry in entries
                if entry["execution_state"] == "reference_only"
            ],
        }
    return {
        "contract": build_prompt_workbench_contract_meta(surface="prompt_tools_providers"),
        "surfaces": surfaces,
    }


def _default_formatting_rules() -> dict[str, Any]:
    return {
        "dedupe_commas": True,
        "normalize_spacing": True,
        "trim_outer_whitespace": True,
    }


def _default_ui_preferences() -> dict[str, Any]:
    return {
        "default_open": False,
        "preferred_panel": "editor",
        "show_history": True,
        "show_favorites": True,
    }


def _default_blacklist_state() -> dict[str, Any]:
    return {
        "enabled": False,
        "entries": [],
    }


def _default_provider_settings() -> dict[str, Any]:
    return {
        "default_provider": "",
        "providers": {},
    }


def build_default_prompt_workbench_config() -> dict[str, Any]:
    return {
        "language": "en",
        "theme_style": "rookieui_classic",
        "history_limit": 100,
        "favorites_limit": 100,
        "formatting_rules": _default_formatting_rules(),
        "ui_preferences": _default_ui_preferences(),
        "translation": _default_provider_settings(),
        "ai_assist": {
            **_default_provider_settings(),
            "instruction_preset": DEFAULT_PROMPT_WORKBENCH_AI_ASSIST_PRESET,
        },
    }


def build_default_prompt_workbench_surface_state(namespace: str) -> dict[str, Any]:
    return {
        "namespace": namespace,
        "workbench_open": False,
        "active_panel": "editor",
        "draft_prompt": "",
        "selected_entry_id": "",
    }


@dataclass(frozen=True)
class PromptWorkbenchRouteContract:
    version: str = PROMPT_WORKBENCH_CONTRACT_VERSION
    surface: str = "prompt_tools"
    route_family: str = PROMPT_WORKBENCH_ROUTE_FAMILY
    state_schema_version: int = PROMPT_WORKBENCH_STATE_SCHEMA_VERSION
    namespaces: tuple[str, ...] = PROMPT_WORKBENCH_NAMESPACES
    provider_secret_field_keys: tuple[str, ...] = PROMPT_WORKBENCH_PROVIDER_SECRET_FIELD_KEYS
    notes: tuple[str, ...] = (
        "Prompt-workbench state is RookieUI-owned and versioned.",
        "Provider secret fields must remain masked in readback payloads.",
        "Heavy history/favorite data should stay lazy-loaded outside bootstrap.",
    )

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromptWorkbenchBootstrapSnapshot:
    contract: PromptWorkbenchRouteContract = field(default_factory=PromptWorkbenchRouteContract)
    config: dict[str, Any] = field(default_factory=build_default_prompt_workbench_config)
    blacklist: dict[str, Any] = field(default_factory=_default_blacklist_state)
    language_options: tuple[dict[str, str], ...] = PROMPT_WORKBENCH_LANGUAGE_OPTIONS
    theme_style_options: tuple[dict[str, str], ...] = PROMPT_WORKBENCH_THEME_STYLE_OPTIONS

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


def build_prompt_workbench_contract_meta(*, surface: str = "prompt_tools") -> dict[str, Any]:
    contract = PromptWorkbenchRouteContract(surface=surface)
    return contract.to_payload()
