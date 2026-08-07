import { fetchRookieUIResource, postRookieUIJson } from "./rookieui_api_transport.js";

const PROMPT_WORKBENCH_CONTRACT_VERSION = "r145f141f142-20260418";

export async function fetchRookieUIPromptWorkbenchConfig(fetchImpl = globalThis.fetch) {
  return fetchRookieUIResource(
    "/rookieui/prompt-tools/config",
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_config",
        route_family: "/rookieui/prompt-tools",
        state_schema_version: 1,
        namespaces: ["txt2img_prompt", "txt2img_negative", "img2img_prompt", "img2img_negative"],
        provider_secret_field_keys: ["access_token", "api_key", "authorization", "password", "secret", "token"],
      },
      config: {
        language: "en",
        theme_style: "rookieui_classic",
        history_limit: 100,
        favorites_limit: 100,
        formatting_rules: {
          dedupe_commas: true,
          normalize_spacing: true,
          trim_outer_whitespace: true,
        },
        ui_preferences: {
          default_open: false,
          preferred_panel: "editor",
          show_history: true,
          show_favorites: true,
        },
        translation: { default_provider: "", providers: {} },
        ai_assist: {
          default_provider: "",
          providers: {},
          instruction_preset:
            "Write a concise Stable Diffusion prompt from the user's image description. Keep the result comma-separated and production-ready. Preserve any explicit prompt syntax the user already includes. Do not add explanation, markdown, numbering, or surrounding quotes. Return prompt text only.",
        },
      },
      blacklist: {
        enabled: false,
        entries: [],
        translation_entries: [],
      },
      host_actions: {
        danbooru_upsample: {
          action_id: "danbooru_upsample",
          title: "Upsample Tags",
          route_path: "/rookieui/prompt-tools/upsample",
          available: false,
          fixed_profile: "host_node_defaults",
          node_aliases: ["DanbooruTagsUpsampler", "DanbooruTagsUpsamplerNodeRay"],
          resolved_node_alias: "",
          availability: {
            status: "host_missing",
            detail: "Host-installed Danbooru upsampler node is not available in the active ComfyUI registry.",
          },
          input_fields: ["prompt", "negative_prompt_tags", "ban_tags"],
        },
      },
      language_options: [
        { code: "en", title: "English", native_title: "English", aliases: ["en_US", "en-US", "en_GB", "en-GB"], fallback_code: "en", source: "rookieui_host" },
        { code: "zh-TW", title: "Traditional Chinese", native_title: "繁體中文", aliases: ["zh_TW", "zh-Hant", "zh_Hant"], fallback_code: "en", source: "rookieui_host" },
        { code: "zh-CN", title: "Simplified Chinese", native_title: "简体中文", aliases: ["zh_CN", "zh", "zh-Hans", "zh_Hans"], fallback_code: "en", source: "rookieui_host" },
        { code: "zh-HK", title: "Traditional Chinese (Hong Kong)", native_title: "繁體中文 (香港)", aliases: ["zh_HK"], fallback_code: "zh-TW", source: "a1111_reference" },
        { code: "ja", title: "Japanese", native_title: "日本語", aliases: ["ja_JP", "ja-JP"], fallback_code: "en", source: "comfyui_frontend" },
        { code: "ko", title: "Korean", native_title: "한국어", aliases: ["ko_KR", "ko-KR"], fallback_code: "en", source: "comfyui_frontend" },
        { code: "ar", title: "Arabic", native_title: "العربية", aliases: ["ar_SA", "ar-SA"], fallback_code: "en", source: "comfyui_frontend" },
        { code: "es", title: "Spanish", native_title: "Español", aliases: ["es_ES", "es-ES"], fallback_code: "en", source: "comfyui_frontend" },
        { code: "fa", title: "Persian", native_title: "فارسی", aliases: ["fa_IR", "fa-IR"], fallback_code: "en", source: "comfyui_frontend" },
        { code: "fr", title: "French", native_title: "Français", aliases: ["fr_FR", "fr-FR"], fallback_code: "en", source: "comfyui_frontend" },
        { code: "ru", title: "Russian", native_title: "Русский", aliases: ["ru_RU", "ru-RU"], fallback_code: "en", source: "comfyui_frontend" },
        { code: "tr", title: "Turkish", native_title: "Türkçe", aliases: ["tr_TR", "tr-TR"], fallback_code: "en", source: "comfyui_frontend" },
        { code: "pt-BR", title: "Portuguese (Brazil)", native_title: "Português (Brasil)", aliases: ["pt_BR", "pt"], fallback_code: "en", source: "comfyui_frontend" },
      ],
      theme_style_options: [
        { id: "rookieui_classic", title: "RookieUI Classic", summary: "Default RookieUI framing with neutral panel contrast." },
        { id: "rookieui_graphite", title: "Graphite Studio", summary: "Higher-contrast shell chrome for denser prompt editing sessions." },
        { id: "rookieui_paper", title: "Paper Notes", summary: "Lighter note-card treatment for catalog and prompt drafting work." },
        { id: "rookieui_tagboard", title: "Tag Board", summary: "Color-forward catalog and tag-highlighting treatment for dense prompt authoring." },
      ],
    },
    fetchImpl,
  );
}

function buildPromptWorkbenchNamespacePath(basePath, namespace) {
  const normalizedNamespace = String(namespace ?? "").trim();
  if (!normalizedNamespace) {
    return basePath;
  }
  const params = new URLSearchParams({ namespace: normalizedNamespace });
  return `${basePath}?${params.toString()}`;
}

export async function fetchRookieUIPromptWorkbenchState(namespace, fetchImpl = globalThis.fetch) {
  const normalizedNamespace = String(namespace ?? "").trim();
  return fetchRookieUIResource(
    buildPromptWorkbenchNamespacePath("/rookieui/prompt-tools/state", normalizedNamespace),
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_state",
      },
      namespace: normalizedNamespace,
      state: {
        namespace: normalizedNamespace,
        workbench_open: false,
        active_panel: "editor",
        draft_prompt: "",
        selected_entry_id: "",
      },
    },
    fetchImpl,
  );
}

export async function updateRookieUIPromptWorkbenchState(namespace, state, fetchImpl = globalThis.fetch) {
  const normalizedNamespace = String(namespace ?? "").trim();
  return postRookieUIJson(
    "/rookieui/prompt-tools/state",
    {
      namespace: normalizedNamespace,
      state: state ?? {},
    },
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_state",
      },
      namespace: normalizedNamespace,
      state: {
        namespace: normalizedNamespace,
        workbench_open: Boolean(state?.workbench_open),
        active_panel: String(state?.active_panel ?? "editor"),
        draft_prompt: String(state?.draft_prompt ?? ""),
        selected_entry_id: String(state?.selected_entry_id ?? ""),
      },
      saved: false,
    },
    fetchImpl,
  );
}

export async function fetchRookieUIPromptWorkbenchHistory(namespace, fetchImpl = globalThis.fetch) {
  const normalizedNamespace = String(namespace ?? "").trim();
  return fetchRookieUIResource(
    buildPromptWorkbenchNamespacePath("/rookieui/prompt-tools/history", normalizedNamespace),
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_history",
      },
      namespace: normalizedNamespace,
      items: [],
    },
    fetchImpl,
  );
}

export async function fetchRookieUIPromptWorkbenchFavorites(namespace, fetchImpl = globalThis.fetch) {
  const normalizedNamespace = String(namespace ?? "").trim();
  return fetchRookieUIResource(
    buildPromptWorkbenchNamespacePath("/rookieui/prompt-tools/favorites", normalizedNamespace),
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_favorites",
      },
      namespace: normalizedNamespace,
      items: [],
    },
    fetchImpl,
  );
}

export async function fetchRookieUIPromptWorkbenchProviders(fetchImpl = globalThis.fetch) {
  return fetchRookieUIResource(
    "/rookieui/prompt-tools/providers",
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_providers",
      },
      surfaces: {
        translation: { providers: [], shipped_provider_ids: [], deferred_provider_ids: [], reference_only_provider_ids: [] },
        ai_assist: { providers: [], shipped_provider_ids: [], deferred_provider_ids: [], reference_only_provider_ids: [] },
      },
    },
    fetchImpl,
  );
}

export async function exportRookieUIPromptWorkbench(fetchImpl = globalThis.fetch) {
  return fetchRookieUIResource(
    "/rookieui/prompt-tools/export",
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_export",
      },
      export: {
        schema_version: 1,
        exported_at: 0,
        includes: ["config", "blacklist", "surfaces"],
        secret_policy: "masked_provider_fields", // pragma: allowlist secret
        data: {
          schema_version: 1,
          config: {},
          blacklist: { enabled: false, entries: [], translation_entries: [] },
          surfaces: {},
        },
      },
    },
    fetchImpl,
  );
}

export async function importRookieUIPromptWorkbench(payload, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/prompt-tools/import",
    payload ?? {},
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_import",
      },
      import_result: {
        imported: false,
        schema_version: 1,
        surface_count: 0,
      },
    },
    fetchImpl,
  );
}

export async function fetchRookieUIPromptWorkbenchCatalog(language = "en", fetchImpl = globalThis.fetch) {
  const params = new URLSearchParams();
  const normalizedLanguage = String(language ?? "").trim();
  if (normalizedLanguage) {
    params.set("language", normalizedLanguage);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return fetchRookieUIResource(
    `/rookieui/prompt-tools/catalog${suffix}`,
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_catalog",
      },
      group_tags: { language: normalizedLanguage || "en", source: "fallback", groups: [] },
      prompt_library: { source: "fallback", sections: [] },
      tagcomplete: { language: normalizedLanguage || "en", source: "fallback", entries: [] },
      extra_networks: { embeddings: [], loras: [] },
      catalog_highlights: { token_families: {}, catalog_categories: {} },
    },
    fetchImpl,
  );
}

export async function translateRookieUIPromptWorkbench(payload, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/prompt-tools/translate",
    payload ?? {},
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_translate",
      },
      provider_id: String(payload?.provider ?? ""),
      provider_title: "",
      mode: Array.isArray(payload?.texts) ? "batch" : "single",
      from_lang: String(payload?.from_lang ?? "auto"),
      to_lang: String(payload?.to_lang ?? "en"),
      translated_text: String(payload?.text ?? ""),
      translated_texts: Array.isArray(payload?.texts) ? payload.texts.map((value) => String(value ?? "")) : [],
    },
    fetchImpl,
  );
}

export async function assistRookieUIPromptWorkbench(payload, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/prompt-tools/assist",
    payload ?? {},
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_assist",
      },
      provider_id: String(payload?.provider ?? ""),
      provider_title: "",
      language: String(payload?.language ?? "en"),
      theme_style: String(payload?.theme_style ?? "rookieui_classic"),
      instruction_preset: String(payload?.instruction_preset ?? ""),
      image_description: String(payload?.image_description ?? ""),
      generated_prompt: "",
    },
    fetchImpl,
  );
}

export async function upsampleRookieUIPromptWorkbench(payload, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/prompt-tools/upsample",
    payload ?? {},
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_upsample",
      },
      action_id: "danbooru_upsample",
      final_prompt: String(payload?.prompt ?? ""),
      generated_suffix: "",
      host_node_alias: "",
      availability: {
        status: "host_missing",
        detail: "Host-installed Danbooru upsampler node is not available in the active ComfyUI registry.",
      },
      warnings: [],
      warning_codes: [],
    },
    fetchImpl,
  );
}

export async function updateRookieUIPromptWorkbenchConfig(config, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/prompt-tools/config",
    { config: config ?? {} },
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_config",
      },
      config: config ?? {},
      saved: false,
    },
    fetchImpl,
  );
}

export async function fetchRookieUIPromptWorkbenchBlacklist(fetchImpl = globalThis.fetch) {
  return fetchRookieUIResource(
    "/rookieui/prompt-tools/blacklist",
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_blacklist",
      },
      blacklist: {
        enabled: false,
        entries: [],
        translation_entries: [],
      },
    },
    fetchImpl,
  );
}

export async function updateRookieUIPromptWorkbenchBlacklist(blacklist, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/prompt-tools/blacklist",
    { blacklist: blacklist ?? {} },
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_blacklist",
      },
      blacklist: blacklist ?? { enabled: false, entries: [], translation_entries: [] },
    },
    fetchImpl,
  );
}

export async function updateRookieUIPromptWorkbenchHistory(namespace, action, payload, fetchImpl = globalThis.fetch) {
  const normalizedNamespace = String(namespace ?? "").trim();
  const normalizedAction = String(action ?? "").trim() || "push";
  return postRookieUIJson(
    "/rookieui/prompt-tools/history",
    {
      namespace: normalizedNamespace,
      action: normalizedAction,
      ...(payload && typeof payload === "object" ? payload : {}),
    },
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_history",
      },
      namespace: normalizedNamespace,
      items: [],
    },
    fetchImpl,
  );
}

export async function updateRookieUIPromptWorkbenchFavorites(namespace, action, payload, fetchImpl = globalThis.fetch) {
  const normalizedNamespace = String(namespace ?? "").trim();
  const normalizedAction = String(action ?? "").trim() || "push";
  return postRookieUIJson(
    "/rookieui/prompt-tools/favorites",
    {
      namespace: normalizedNamespace,
      action: normalizedAction,
      ...(payload && typeof payload === "object" ? payload : {}),
    },
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_favorites",
      },
      namespace: normalizedNamespace,
      items: [],
    },
    fetchImpl,
  );
}
