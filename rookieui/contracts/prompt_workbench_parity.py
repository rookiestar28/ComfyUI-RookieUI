from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

PROMPT_WORKBENCH_PARITY_CONTRACT_VERSION = "prompt-all-in-one-parity-20260426"

PROMPT_WORKBENCH_PARITY_CLASSES = (
    "implemented",
    "adapted_comfyui_native",
    "optional_provider",
    "reference_only",
    "out_of_scope",
)

PROMPT_WORKBENCH_TRANSLATION_PROVIDER_LAYER_ORDER = (
    "csv_tag_dictionary",
    "shipped_lightweight",
    "optional_openai_compatible",
    "optional_local_host_model",
)


@dataclass(frozen=True)
class PromptWorkbenchFeatureParityEntry:
    feature_id: str
    title: str
    reference_surface: str
    reference_concept: str
    rookieui_target: str
    parity_class: str
    delivery_stage: str
    acceptance_signal: str

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromptWorkbenchProviderParityEntry:
    provider_id: str
    title: str
    provider_layer: str
    reference_keys: tuple[str, ...]
    parity_class: str
    baseline_dependency: str
    acceptance_signal: str

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


def _feature_entries() -> tuple[PromptWorkbenchFeatureParityEntry, ...]:
    return (
        PromptWorkbenchFeatureParityEntry(
            feature_id="prompt_field_binding",
            title="Prompt Field Binding",
            reference_surface="A1111 prompt / negative prompt textareas",
            reference_concept="Attach richer controls to the host prompt fields while keeping host prompt values authoritative.",
            rookieui_target="Bind Prompt Workbench to ComfyUI txt2img/img2img prompt and negative prompt inputs.",
            parity_class="implemented",
            delivery_stage="host_integration",
            acceptance_signal="route and E2E tests prove prompt-field synchronization through the ComfyUI harness.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="token_tag_model",
            title="Token / Tag Model",
            reference_surface="tag list editor",
            reference_concept="Represent prompt text as editable tag items rather than one opaque textarea string.",
            rookieui_target="Use stable token ids across prompt and negative scopes while preserving raw prompt syntax.",
            parity_class="adapted_comfyui_native",
            delivery_stage="token_editor",
            acceptance_signal="unit tests cover parser preservation for tags, LoRA, embeddings, BREAK, AND, schedules, and escapes.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="token_quick_actions",
            title="Per-token Quick Actions",
            reference_surface="tag action buttons",
            reference_concept="Delete, copy, translate, favorite, blacklist, enable/disable, and reorder individual tags.",
            rookieui_target="Expose equivalent actions in the ComfyUI-native workbench token list.",
            parity_class="adapted_comfyui_native",
            delivery_stage="token_editor",
            acceptance_signal="frontend tests pin each token action and resulting prompt synchronization.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="quick_weight_adjustment",
            title="Quick Weight Adjustment",
            reference_surface="tag weight controls",
            reference_concept="Adjust tag emphasis without hand-editing all prompt syntax.",
            rookieui_target="Offer safe weight up/down actions for parenthesis/bracket and explicit-weight forms.",
            parity_class="adapted_comfyui_native",
            delivery_stage="token_editor",
            acceptance_signal="parser and shell tests prove valid weighted syntax is preserved.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="automatic_translation",
            title="Automatic Translation",
            reference_surface="auto translate settings",
            reference_concept="Translate prompt and negative prompt tags automatically, with dictionary enhancement first.",
            rookieui_target="Support CSV/tag dictionary auto-translate, with provider fallback only for manual flows.",
            parity_class="adapted_comfyui_native",
            delivery_stage="translation_providers",
            acceptance_signal="tests prove dictionary-only auto mode and manual dictionary-plus-provider fallback.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="manual_batch_translation",
            title="Manual and Batch Translation",
            reference_surface="one-click / batch translation",
            reference_concept="Translate selected tags or full prompt text on demand.",
            rookieui_target="Translate token selections, full prompts, and negative prompt scopes with per-token status.",
            parity_class="adapted_comfyui_native",
            delivery_stage="translation_providers",
            acceptance_signal="backend and frontend tests cover token, batch, and full-prompt translation paths.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="translation_provider_matrix",
            title="Translation Provider Matrix",
            reference_surface="translation API configuration",
            reference_concept="Expose many online, API-key, and local/offline translation backends.",
            rookieui_target="Classify providers as dictionary, shipped lightweight, optional OpenAI-compatible, optional local/host, or reference-only.",
            parity_class="optional_provider",
            delivery_stage="translation_providers",
            acceptance_signal="provider parity tests prove truthful classification and no heavy baseline dependency.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="history",
            title="Prompt History",
            reference_surface="history popup",
            reference_concept="Persist prompt edits and allow reusing previous prompt/tag states.",
            rookieui_target="Capture namespace-scoped prompt and negative history with dedupe and limit rules.",
            parity_class="adapted_comfyui_native",
            delivery_stage="collections",
            acceptance_signal="state tests prove automatic capture, dedupe, apply, remove, and limits.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="favorites",
            title="Favorites",
            reference_surface="favorite popup and tag action",
            reference_concept="Save prompts or tags for reuse from the editor and catalog surfaces.",
            rookieui_target="Support prompt-level and token-level favorites with namespace-aware apply behavior.",
            parity_class="adapted_comfyui_native",
            delivery_stage="collections",
            acceptance_signal="state and shell tests prove save, apply, remove, reorder, and batch favorite actions.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="prompt_blacklist",
            title="Prompt Blacklist",
            reference_surface="blacklist dialog",
            reference_concept="Filter prompt, negative prompt, LoRA, LyCORIS, and embedding terms.",
            rookieui_target="Apply prompt blacklist classes without hiding translation-blacklist semantics.",
            parity_class="adapted_comfyui_native",
            delivery_stage="collections",
            acceptance_signal="tests prove prompt blacklist and translation blacklist are independent.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="translation_blacklist",
            title="Translation Blacklist",
            reference_surface="disable translation list",
            reference_concept="Keep selected terms visible but prevent them from being translated.",
            rookieui_target="Skip dictionary/provider translation for blacklisted tokens while preserving token state.",
            parity_class="adapted_comfyui_native",
            delivery_stage="translation_blacklist",
            acceptance_signal="translation tests prove blacklist hits bypass provider calls and remain visible.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="batch_operations",
            title="Batch Operations",
            reference_surface="multi-tag workflows",
            reference_concept="Operate on multiple selected tags for editing, translation, and collection actions.",
            rookieui_target="Batch delete, disable, enable, translate, favorite, copy, blacklist, move, and cleanup.",
            parity_class="adapted_comfyui_native",
            delivery_stage="collections",
            acceptance_signal="frontend tests pin multi-select state transitions for every batch action.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="group_tags_catalog",
            title="Group Tags Catalog",
            reference_surface="group_tags YAML catalog",
            reference_concept="Show localized tag groups and use them to improve translation lookup.",
            rookieui_target="Support built-in and runtime catalogs with strict schema validation and dictionary lookup.",
            parity_class="adapted_comfyui_native",
            delivery_stage="catalog_highlighting",
            acceptance_signal="catalog tests cover localized group tags, user CSV ingestion, and fallback lookup.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="tagcomplete_lookup",
            title="Tagcomplete-style Lookup",
            reference_surface="keyword search and group tags",
            reference_concept="Find and insert prompt tags from searchable keyword sources.",
            rookieui_target="Expose searchable catalog entries without depending on A1111 tagcomplete internals.",
            parity_class="adapted_comfyui_native",
            delivery_stage="catalog_highlighting",
            acceptance_signal="catalog and shell tests prove lookup, insert, and prompt synchronization.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="extra_network_highlighting",
            title="Extra-network Highlighting",
            reference_surface="LoRA/LyCORIS/embedding tag metadata",
            reference_concept="Identify special prompt tokens and color them distinctly.",
            rookieui_target="Highlight LoRA, LyCORIS-like syntax, embeddings, disabled tags, and blacklist states.",
            parity_class="adapted_comfyui_native",
            delivery_stage="catalog_highlighting",
            acceptance_signal="frontend tests assert keyword-family classes and token status styling.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="themes",
            title="Theme Variants",
            reference_surface="prompt-all-in-one style/theme extensions",
            reference_concept="Allow changing visual density and style for the prompt editor.",
            rookieui_target="Expose ComfyUI-native workbench themes through settings without importing reference CSS.",
            parity_class="adapted_comfyui_native",
            delivery_stage="catalog_highlighting",
            acceptance_signal="contract and shell tests prove theme selection survives bootstrap and state updates.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="settings",
            title="Settings Parity",
            reference_surface="extension settings panel",
            reference_concept="Configure formatting, visibility, translation, history, favorites, tooltips, and themes.",
            rookieui_target="Persist equivalent settings under RookieUI-owned schema with masked provider secrets.",
            parity_class="adapted_comfyui_native",
            delivery_stage="settings",
            acceptance_signal="state tests prove schema defaults, updates, migration, and secret masking.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="prompt_field_visibility",
            title="Prompt Field Visibility",
            reference_surface="hide default input / hide panel settings",
            reference_concept="Collapse or hide the original host prompt fields while using the enhanced editor.",
            rookieui_target="Offer safe ComfyUI-native show/collapse modes while keeping source fields synchronized.",
            parity_class="adapted_comfyui_native",
            delivery_stage="settings",
            acceptance_signal="E2E tests prove source-field synchronization in visible and collapsed modes.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="bilingual_token_display",
            title="Bilingual Token Display",
            reference_surface="translated tag display",
            reference_concept="Show original and localized/translated tag text in the editing surface.",
            rookieui_target="Show raw text, translated text, provider/source, cache hit, and per-token error status.",
            parity_class="adapted_comfyui_native",
            delivery_stage="bilingual_hotkeys",
            acceptance_signal="frontend tests prove per-token translation status and fallback display.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="hotkeys",
            title="Scoped Hotkeys",
            reference_surface="hotkey settings",
            reference_concept="Use keyboard shortcuts for tag editing workflows.",
            rookieui_target="Scope hotkeys to Prompt Workbench focus and avoid ComfyUI global shortcut conflicts.",
            parity_class="adapted_comfyui_native",
            delivery_stage="bilingual_hotkeys",
            acceptance_signal="frontend tests prove focus-scoped selection, delete, copy, weight, and translate shortcuts.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="workbench_i18n",
            title="Workbench i18n",
            reference_surface="i18n resources",
            reference_concept="Localize prompt editor labels, statuses, and configuration text.",
            rookieui_target="Provide Prompt Workbench control/status localization with English fallback.",
            parity_class="adapted_comfyui_native",
            delivery_stage="i18n_import_export",
            acceptance_signal="unit and shell tests prove label fallback and language switching.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="import_export",
            title="Import / Export",
            reference_surface="settings and data files",
            reference_concept="Move settings, histories, favorites, blacklists, and catalogs between installs.",
            rookieui_target="Import/export settings, history, favorites, prompt library, dictionaries, and blacklists without secrets.",
            parity_class="adapted_comfyui_native",
            delivery_stage="i18n_import_export",
            acceptance_signal="backend tests prove schema validation, migration, round trip, and secret stripping.",
        ),
        PromptWorkbenchFeatureParityEntry(
            feature_id="a1111_gradio_textarea_hijack",
            title="A1111 Gradio Textarea Hijack",
            reference_surface="stable-diffusion-webui Gradio DOM",
            reference_concept="Patch A1111 textarea DOM and Gradio APIs directly.",
            rookieui_target="Do not reproduce. RookieUI must stay ComfyUI-native.",
            parity_class="out_of_scope",
            delivery_stage="host_boundary",
            acceptance_signal="matrix tests keep this boundary explicit.",
        ),
    )


def _provider_entries() -> tuple[PromptWorkbenchProviderParityEntry, ...]:
    reference_only = (
        ("bing_free", "Microsoft Bing Free", ("bing_free",)),
        ("google_free", "Google Free", ("google_free",)),
        ("itranslate_free", "iTranslate Free", ("itranslate_free",)),
        ("lingvanex_free", "Lingvanex Free", ("lingvanex_free",)),
        ("modernmt_free", "ModernMT Free", ("modernMt_free",)),
        ("systran_free", "SYSTRAN Free", ("sysTran_free",)),
        ("translatecom_free", "Translate.com Free", ("translateCom_free",)),
        ("argos_free", "Argos Free", ("argos_free",)),
        ("papago_free", "Papago Free", ("papago_free",)),
        ("reverso_free", "Reverso Free", ("reverso_free",)),
        ("translateme_free", "TranslateMe Free", ("translateMe_free",)),
        ("elia_free", "Elia Free", ("elia_free",)),
        ("judic_free", "Judic Free", ("judic_free",)),
        ("alibaba_free", "Alibaba Free", ("alibaba_free",)),
        ("baidu_free", "Baidu Free", ("baidu_free",)),
        ("sogou_free", "Sogou Free", ("sogou_free",)),
        ("qqtransmart_free", "QQ TranSmart Free", ("qqTranSmart_free",)),
        ("youdao_free", "Youdao Free", ("youdao_free",)),
        ("iciba_free", "iCIBA Free", ("iciba_free",)),
        ("cloudyi_free", "Cloud Yi Free", ("cloudYi_free",)),
        ("caiyun_free", "Caiyun Free", ("caiyun_free",)),
        ("google", "Google API", ("google",)),
        ("microsoft", "Microsoft Translator API", ("microsoft",)),
        ("amazon", "Amazon Translate API", ("amazon",)),
        ("deepl", "DeepL API", ("deepl",)),
        ("yandex", "Yandex API", ("yandex",)),
        ("mymemory", "MyMemory API-key", ("myMemory",)),
        ("baidu", "Baidu API", ("baidu",)),
        ("alibaba", "Alibaba API", ("alibaba",)),
        ("youdao", "Youdao API", ("youdao",)),
        ("tencent", "Tencent API", ("tencent",)),
        ("niutrans", "Niutrans API", ("niutrans",)),
        ("caiyun", "Caiyun API", ("caiyun",)),
        ("volcengine", "Volcengine API", ("volcengine",)),
        ("iflytekv1", "iFlytek V1 API", ("iflytekV1",)),
        ("iflytekv2", "iFlytek V2 API", ("iflytekV2",)),
    )
    entries = [
        PromptWorkbenchProviderParityEntry(
            provider_id="csv_tag_dictionary",
            title="CSV / Tag Dictionary",
            provider_layer="csv_tag_dictionary",
            reference_keys=("group_tags", "keyword_group", "tag_csv"),
            parity_class="adapted_comfyui_native",
            baseline_dependency="none",
            acceptance_signal="dictionary lookup tests prove exact tag hits and auto-translate dictionary-only mode.",
        ),
        PromptWorkbenchProviderParityEntry(
            provider_id="mymemory_free",
            title="MyMemory Free Translation",
            provider_layer="shipped_lightweight",
            reference_keys=("myMemory_free",),
            parity_class="implemented",
            baseline_dependency="network_optional",
            acceptance_signal="provider tests prove no-key translation path and timeout/error handling.",
        ),
        PromptWorkbenchProviderParityEntry(
            provider_id="openai_compatible",
            title="OpenAI-compatible Chat Translation",
            provider_layer="optional_openai_compatible",
            reference_keys=("openai",),
            parity_class="optional_provider",
            baseline_dependency="configured_api_key",
            acceptance_signal="provider tests prove masked config and no execution without explicit configuration.",
        ),
        PromptWorkbenchProviderParityEntry(
            provider_id="local_host_model",
            title="Optional Local / Host Model Provider",
            provider_layer="optional_local_host_model",
            reference_keys=("mbart50", "host_model"),
            parity_class="optional_provider",
            baseline_dependency="user_installed_runtime",
            acceptance_signal="availability tests prove missing host/runtime is non-fatal and truthfully reported.",
        ),
    ]
    entries.extend(
        PromptWorkbenchProviderParityEntry(
            provider_id=provider_id,
            title=title,
            provider_layer="reference_only",
            reference_keys=reference_keys,
            parity_class="reference_only",
            baseline_dependency="not_shipped",
            acceptance_signal="provider matrix preserves the reference name without claiming RookieUI execution support.",
        )
        for provider_id, title, reference_keys in reference_only
    )
    return tuple(entries)


def get_prompt_workbench_feature_parity_entries() -> tuple[PromptWorkbenchFeatureParityEntry, ...]:
    return _feature_entries()


def get_prompt_workbench_provider_parity_entries() -> tuple[PromptWorkbenchProviderParityEntry, ...]:
    return _provider_entries()


def build_prompt_workbench_parity_matrix_payload() -> dict[str, Any]:
    features = [entry.to_payload() for entry in get_prompt_workbench_feature_parity_entries()]
    providers = [entry.to_payload() for entry in get_prompt_workbench_provider_parity_entries()]
    return {
        "contract_version": PROMPT_WORKBENCH_PARITY_CONTRACT_VERSION,
        "source_reference": "sd-webui-prompt-all-in-one",
        "parity_classes": list(PROMPT_WORKBENCH_PARITY_CLASSES),
        "translation_provider_layer_order": list(PROMPT_WORKBENCH_TRANSLATION_PROVIDER_LAYER_ORDER),
        "features": features,
        "providers": providers,
    }


__all__ = [
    "PROMPT_WORKBENCH_PARITY_CLASSES",
    "PROMPT_WORKBENCH_PARITY_CONTRACT_VERSION",
    "PROMPT_WORKBENCH_TRANSLATION_PROVIDER_LAYER_ORDER",
    "PromptWorkbenchFeatureParityEntry",
    "PromptWorkbenchProviderParityEntry",
    "build_prompt_workbench_parity_matrix_payload",
    "get_prompt_workbench_feature_parity_entries",
    "get_prompt_workbench_provider_parity_entries",
]
