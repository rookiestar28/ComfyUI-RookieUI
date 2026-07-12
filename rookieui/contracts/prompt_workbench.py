from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PROMPT_WORKBENCH_CONTRACT_VERSION = "r145f141f142-20260418"
PROMPT_WORKBENCH_STATE_SCHEMA_VERSION = 1
PROMPT_WORKBENCH_ROUTE_FAMILY = "/rookieui/prompt-tools"
PROMPT_WORKBENCH_DANBOORU_ACTION_ID = "danbooru_upsample"
PROMPT_WORKBENCH_DANBOORU_ROUTE_PATH = f"{PROMPT_WORKBENCH_ROUTE_FAMILY}/upsample"
PROMPT_WORKBENCH_DANBOORU_NODE_ALIASES = (
    "DanbooruTagsUpsampler",
    "DanbooruTagsUpsamplerNodeRay",
)
PROMPT_WORKBENCH_NAMESPACES = (
    "txt2img_prompt",
    "txt2img_negative",
    "img2img_prompt",
    "img2img_negative",
)
PROMPT_WORKBENCH_PANELS = ("editor", "history", "favorites", "catalog", "assist", "format")
PROMPT_WORKBENCH_PROVIDER_SECRET_FIELD_KEYS = (
    "access_token",
    "api_key",
    "authorization",
    "password",
    "secret",
    "token",
)
PROMPT_WORKBENCH_PROVIDER_SURFACES = ("translation", "ai_assist")
PROMPT_WORKBENCH_SHIPPED_TRANSLATION_PROVIDER_IDS = ("csv_tag_dictionary", "mymemory_free", "openai")
PROMPT_WORKBENCH_SHIPPED_AI_PROVIDER_IDS = ("openai",)
PROMPT_WORKBENCH_DEFERRED_TRANSLATION_PROVIDER_IDS = ("local_host_model",)
PROMPT_WORKBENCH_DEFERRED_AI_PROVIDER_IDS = ()
DEFAULT_PROMPT_WORKBENCH_AI_ASSIST_PRESET = (
    "Write a concise Stable Diffusion prompt from the user's image description. "
    "Keep the result comma-separated and production-ready. Preserve any explicit prompt syntax the user already includes. "
    "Do not add explanation, markdown, numbering, or surrounding quotes. Return prompt text only."
)
PROMPT_WORKBENCH_LANGUAGE_OPTIONS = (
    {"code": "en", "title": "English", "native_title": "English", "aliases": ("en_US", "en-US", "en_GB", "en-GB"), "fallback_code": "en", "source": "rookieui_host"},
    {"code": "zh-TW", "title": "Traditional Chinese", "native_title": "繁體中文", "aliases": ("zh_TW", "zh-Hant", "zh_Hant"), "fallback_code": "en", "source": "rookieui_host"},
    {"code": "zh-CN", "title": "Simplified Chinese", "native_title": "简体中文", "aliases": ("zh_CN", "zh", "zh-Hans", "zh_Hans"), "fallback_code": "en", "source": "rookieui_host"},
    {"code": "zh-HK", "title": "Traditional Chinese (Hong Kong)", "native_title": "繁體中文 (香港)", "aliases": ("zh_HK",), "fallback_code": "zh-TW", "source": "a1111_reference"},
    {"code": "ja", "title": "Japanese", "native_title": "日本語", "aliases": ("ja_JP", "ja-JP"), "fallback_code": "en", "source": "comfyui_frontend"},
    {"code": "ko", "title": "Korean", "native_title": "한국어", "aliases": ("ko_KR", "ko-KR"), "fallback_code": "en", "source": "comfyui_frontend"},
    {"code": "ar", "title": "Arabic", "native_title": "العربية", "aliases": ("ar_SA", "ar-SA"), "fallback_code": "en", "source": "comfyui_frontend"},
    {"code": "es", "title": "Spanish", "native_title": "Español", "aliases": ("es_ES", "es-ES"), "fallback_code": "en", "source": "comfyui_frontend"},
    {"code": "fa", "title": "Persian", "native_title": "فارسی", "aliases": ("fa_IR", "fa-IR"), "fallback_code": "en", "source": "comfyui_frontend"},
    {"code": "fr", "title": "French", "native_title": "Français", "aliases": ("fr_FR", "fr-FR"), "fallback_code": "en", "source": "comfyui_frontend"},
    {"code": "ru", "title": "Russian", "native_title": "Русский", "aliases": ("ru_RU", "ru-RU"), "fallback_code": "en", "source": "comfyui_frontend"},
    {"code": "tr", "title": "Turkish", "native_title": "Türkçe", "aliases": ("tr_TR", "tr-TR"), "fallback_code": "en", "source": "comfyui_frontend"},
    {"code": "pt-BR", "title": "Portuguese (Brazil)", "native_title": "Português (Brasil)", "aliases": ("pt_BR", "pt"), "fallback_code": "en", "source": "comfyui_frontend"},
    {"code": "de", "title": "German", "native_title": "Deutsch", "aliases": ("de_DE", "de-DE"), "fallback_code": "en", "source": "a1111_reference"},
    {"code": "it", "title": "Italian", "native_title": "Italiano", "aliases": ("it_IT", "it-IT"), "fallback_code": "en", "source": "a1111_reference"},
    {"code": "nl", "title": "Dutch", "native_title": "Nederlands", "aliases": ("nl_NL", "nl-NL"), "fallback_code": "en", "source": "a1111_reference"},
    {"code": "pl", "title": "Polish", "native_title": "Polski", "aliases": ("pl_PL", "pl-PL"), "fallback_code": "en", "source": "a1111_reference"},
    {"code": "uk", "title": "Ukrainian", "native_title": "Українська", "aliases": ("uk_UA", "uk-UA"), "fallback_code": "en", "source": "a1111_reference"},
    {"code": "vi", "title": "Vietnamese", "native_title": "Tiếng Việt", "aliases": ("vi_VN", "vi-VN"), "fallback_code": "en", "source": "a1111_reference"},
    {"code": "th", "title": "Thai", "native_title": "ไทย", "aliases": ("th_TH", "th-TH"), "fallback_code": "en", "source": "a1111_reference"},
    {"code": "id", "title": "Indonesian", "native_title": "Bahasa Indonesia", "aliases": ("id_ID", "id-ID"), "fallback_code": "en", "source": "a1111_reference"},
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
    {
        "id": "rookieui_tagboard",
        "title": "Tag Board",
        "summary": "Color-forward catalog and tag-highlighting treatment for dense prompt authoring.",
    },
)
PROMPT_WORKBENCH_REFERENCE_ONLY_PROVIDER_IDS = (
    "alibaba",
    "alibaba_free",
    "amazon",
    "argos_free",
    "baidu",
    "baidu_free",
    "bing_free",
    "caiyun",
    "caiyun_free",
    "cloudyi_free",
    "deepl",
    "elia_free",
    "google",
    "google_free",
    "iciba_free",
    "iflytekV1",
    "iflytekV2",
    "itranslate_free",
    "judic_free",
    "lingvanex_free",
    "microsoft",
    "modernmt_free",
    "mymemory",
    "niutrans",
    "papago_free",
    "qqtransmart_free",
    "reverso_free",
    "sogou_free",
    "systran_free",
    "tencent",
    "translatecom_free",
    "translateme_free",
    "volcengine",
    "yandex",
    "youdao",
    "youdao_free",
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
            key="allow_custom_endpoint",
            title="Allow Custom Endpoint",
            value_type="boolean",
            default=False,
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
            max_value=60,
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
            key="allow_custom_endpoint",
            title="Allow Custom Endpoint",
            value_type="boolean",
            default=False,
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
            provider_id="csv_tag_dictionary",
            title="CSV / Tag Dictionary Translation",
            surface_scopes=("translation",),
            execution_state="shipped",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: group_tags / keyword dictionary enhancement",
            summary="Local exact-match tag dictionary lookup used before network-backed providers.",
            notes=(
                "Runtime dictionaries are loaded from Prompt Workbench catalog storage.",
                "No network or model dependency is required.",
            ),
        ),
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
            provider_id="itranslate_free",
            title="iTranslate Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: itranslate_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="lingvanex_free",
            title="Lingvanex Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: lingvanex_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="modernmt_free",
            title="ModernMT Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: modernMt_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="systran_free",
            title="SYSTRAN Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: sysTran_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="translatecom_free",
            title="Translate.com Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: translateCom_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="argos_free",
            title="Argos / Libre Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: argos_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="papago_free",
            title="Papago Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: papago_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="reverso_free",
            title="Reverso Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: reverso_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="translateme_free",
            title="TranslateMe Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: translateMe_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="elia_free",
            title="Elia Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: elia_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="judic_free",
            title="Judic Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: judic_free",
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
            provider_id="baidu_free",
            title="Baidu Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: baidu_free",
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
            provider_id="sogou_free",
            title="Sogou Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: sogou_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="qqtransmart_free",
            title="QQ TranSmart Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: qqTranSmart_free",
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
            provider_id="youdao_free",
            title="Youdao Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: youdao_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="iciba_free",
            title="iCIBA Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: iciba_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="cloudyi_free",
            title="Cloud Yi Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: cloudYi_free",
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
            provider_id="caiyun_free",
            title="Caiyun Free (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: caiyun_free",
            summary="Reference-provider entry preserved for migration truthfulness only.",
        ),
        PromptWorkbenchProviderCatalogEntry(
            provider_id="mymemory",
            title="MyMemory API-key (Reference Only)",
            surface_scopes=("translation",),
            execution_state="reference_only",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: myMemory",
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
        PromptWorkbenchProviderCatalogEntry(
            provider_id="local_host_model",
            title="Local / Host Model Provider (Optional)",
            surface_scopes=("translation",),
            execution_state="deferred",
            supports_batch=True,
            reference_origin="sd-webui-prompt-all-in-one: offline/local model provider class",
            summary="Optional local or host-installed model integration point; no baseline dependency is required.",
            notes=(
                "Classification-only entry for truthful provider planning.",
                "No local model runtime is executed by baseline RookieUI.",
            ),
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
    if surface == "translation" and normalized_provider_id in PROMPT_WORKBENCH_DEFERRED_TRANSLATION_PROVIDER_IDS:
        return "deferred"
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
            "shipped_provider_ids": list(
                PROMPT_WORKBENCH_SHIPPED_TRANSLATION_PROVIDER_IDS
                if surface == "translation"
                else PROMPT_WORKBENCH_SHIPPED_AI_PROVIDER_IDS
            ),
            "deferred_provider_ids": list(
                PROMPT_WORKBENCH_DEFERRED_TRANSLATION_PROVIDER_IDS
                if surface == "translation"
                else PROMPT_WORKBENCH_DEFERRED_AI_PROVIDER_IDS
            ),
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
        "translation_entries": [],
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


def _language_alias_key(value: object) -> str:
    return str(value or "").strip().replace("_", "-").lower()


def build_prompt_workbench_language_options() -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "code": str(entry["code"]),
            "title": str(entry["title"]),
            "native_title": str(entry.get("native_title", entry["title"])),
            "aliases": [str(alias) for alias in entry.get("aliases", ())],
            "fallback_code": str(entry.get("fallback_code", "en")),
            "source": str(entry.get("source", "rookieui_host")),
        }
        for entry in PROMPT_WORKBENCH_LANGUAGE_OPTIONS
    )


def normalize_prompt_workbench_language_code(value: object, *, default: str = "en") -> str:
    alias_map: dict[str, str] = {}
    for entry in PROMPT_WORKBENCH_LANGUAGE_OPTIONS:
        code = str(entry["code"])
        alias_map[_language_alias_key(code)] = code
        for alias in entry.get("aliases", ()):
            alias_map[_language_alias_key(alias)] = code
    normalized_default = alias_map.get(_language_alias_key(default), "en")
    return alias_map.get(_language_alias_key(value), normalized_default)


def build_default_prompt_workbench_host_actions() -> dict[str, Any]:
    return {
        PROMPT_WORKBENCH_DANBOORU_ACTION_ID: {
            "action_id": PROMPT_WORKBENCH_DANBOORU_ACTION_ID,
            "title": "Upsample Tags",
            "route_path": PROMPT_WORKBENCH_DANBOORU_ROUTE_PATH,
            "available": False,
            "fixed_profile": "host_node_defaults",
            "node_aliases": list(PROMPT_WORKBENCH_DANBOORU_NODE_ALIASES),
            "availability": {
                "status": "host_missing",
                "detail": "Host-installed Danbooru upsampler node is not available in the active ComfyUI registry.",
            },
            "input_fields": ["prompt", "negative_prompt_tags", "ban_tags"],
        }
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
    host_actions: dict[str, Any] = field(default_factory=build_default_prompt_workbench_host_actions)
    language_options: tuple[dict[str, Any], ...] = field(default_factory=build_prompt_workbench_language_options)
    theme_style_options: tuple[dict[str, str], ...] = PROMPT_WORKBENCH_THEME_STYLE_OPTIONS

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


def build_prompt_workbench_contract_meta(*, surface: str = "prompt_tools") -> dict[str, Any]:
    contract = PromptWorkbenchRouteContract(surface=surface)
    return contract.to_payload()
