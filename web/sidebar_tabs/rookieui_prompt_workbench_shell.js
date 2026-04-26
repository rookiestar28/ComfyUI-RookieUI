let tokenSequence = 0;

const WORKBENCH_I18N = Object.freeze({
  en: {
    title: "Prompt Workbench",
    subtitle: "Structured prompt editor with persisted history, favorites, formatting rules, and blacklist-aware cleanup.",
    openWorkbench: "Open Workbench",
    hideWorkbench: "Hide Workbench",
    promptTab: "Prompt",
    negativeTab: "Negative",
    summaryState: "State",
    summaryProviders: "Providers",
    summaryCatalogs: "Catalogs",
    summaryHistory: "History",
    summaryFavorites: "Favorites",
    summaryBlacklist: "Blacklist",
    panelEditor: "Editor",
    panelHistory: "History",
    panelFavorites: "Favorites",
    panelCatalog: "Catalog",
    panelAssist: "Assist",
    panelFormat: "Format",
    captureCurrentText: "Capture Current Text",
    restoreDraft: "Restore Draft",
    ready: "Prompt Workbench ready",
    formattingAndBlacklist: "Formatting and Blacklist",
    importExport: "Import / Export",
    exportJson: "Export JSON",
    importJson: "Import JSON",
    exportReady: "Prompt Workbench export JSON generated",
    importReady: "Prompt Workbench import synchronized",
    importInvalidJson: "Import JSON must be a valid object",
  },
  "zh-TW": {
    title: "提示詞工作台",
    subtitle: "結構化提示詞編輯器，支援歷史、收藏、格式化規則與黑名單清理。",
    openWorkbench: "開啟工作台",
    hideWorkbench: "收合工作台",
    promptTab: "正向提示詞",
    negativeTab: "反向提示詞",
    summaryState: "狀態",
    summaryProviders: "供應器",
    summaryCatalogs: "目錄",
    summaryHistory: "歷史",
    summaryFavorites: "收藏",
    summaryBlacklist: "黑名單",
    panelEditor: "編輯",
    panelHistory: "歷史",
    panelFavorites: "收藏",
    panelCatalog: "目錄",
    panelAssist: "助理",
    panelFormat: "格式",
    captureCurrentText: "擷取目前文字",
    restoreDraft: "還原草稿",
    ready: "提示詞工作台已就緒",
    formattingAndBlacklist: "格式化與黑名單",
    importExport: "匯入 / 匯出",
    exportJson: "匯出 JSON",
    importJson: "匯入 JSON",
    exportReady: "提示詞工作台匯出 JSON 已產生",
    importReady: "提示詞工作台匯入已同步",
    importInvalidJson: "匯入 JSON 必須是有效物件",
  },
});

function normalizeTokenText(text) {
  return String(text ?? "").trim();
}

function classifyPromptToken(text) {
  const normalized = normalizeTokenText(text);
  const lower = normalized.toLowerCase();
  if (lower === "break") {
    return "break";
  }
  if (lower === "and" || lower.startsWith("and ")) {
    return "and";
  }
  if (lower.startsWith("<lora:")) {
    return "lora";
  }
  if (lower.startsWith("<lyco:") || lower.startsWith("<lycoris:")) {
    return "lycoris";
  }
  if (lower.startsWith("embedding:")) {
    return "embedding";
  }
  if (lower.startsWith("[") && lower.endsWith("]") && lower.includes(":")) {
    return "schedule";
  }
  if (extractTokenWeight(normalized) !== null || (normalized.startsWith("(") && normalized.endsWith(")"))) {
    return "weighted";
  }
  return "plain";
}

function extractTokenWeight(text) {
  const match = normalizeTokenText(text).match(/^\((.+):([+-]?(?:\d+(?:\.\d+)?|\.\d+))\)$/);
  if (!match) {
    return null;
  }
  const value = Number.parseFloat(match[2]);
  return Number.isFinite(value) ? value : null;
}

function createToken(
  text,
  {
    disabled = false,
    selected = false,
    translatedText = "",
    scope = "prompt",
    orderIndex = 0,
  } = {},
) {
  tokenSequence += 1;
  const rawText = normalizeTokenText(text);
  return {
    id: `pw-token-${tokenSequence}`,
    text: rawText,
    raw_text: rawText,
    normalized_text: rawText.toLowerCase(),
    scope: String(scope ?? "prompt").trim() || "prompt",
    order_index: Number.isInteger(orderIndex) ? orderIndex : 0,
    disabled: Boolean(disabled),
    selected: Boolean(selected),
    translated_text: String(translatedText ?? ""),
    keyword_family: classifyPromptToken(rawText),
    weight: extractTokenWeight(rawText),
  };
}

function normalizeStatePayload(namespace, payload) {
  return {
    namespace,
    workbench_open: Boolean(payload?.workbench_open),
    active_panel: String(payload?.active_panel ?? "editor").trim() || "editor",
    draft_prompt: String(payload?.draft_prompt ?? ""),
    selected_entry_id: String(payload?.selected_entry_id ?? ""),
  };
}

function normalizePromptEntry(entry) {
  return {
    id: String(entry?.id ?? "").trim() || `pw-entry-${Date.now()}`,
    label: String(entry?.label ?? "").trim(),
    prompt_text: String(entry?.prompt_text ?? "").trim(),
    tag_tokens: Array.isArray(entry?.tag_tokens) ? entry.tag_tokens.map((token) => normalizeTokenText(token)).filter(Boolean) : [],
    token_payloads: Array.isArray(entry?.token_payloads) ? entry.token_payloads.map(normalizePersistedTokenPayload).filter(Boolean) : [],
    created_at: Number(entry?.created_at ?? 0) || 0,
  };
}

function normalizePersistedTokenPayload(token) {
  if (!token || typeof token !== "object") {
    return null;
  }
  const rawText = normalizeTokenText(token.raw_text ?? token.text);
  if (!rawText) {
    return null;
  }
  return {
    raw_text: rawText,
    normalized_text: normalizeTokenText(token.normalized_text) || rawText.toLowerCase(),
    scope: normalizeTokenText(token.scope),
    order_index: Number.isInteger(token.order_index) ? token.order_index : 0,
    disabled: Boolean(token.disabled),
    selected: Boolean(token.selected),
    translated_text: String(token.translated_text ?? ""),
    keyword_family: normalizeTokenText(token.keyword_family) || classifyPromptToken(rawText),
    weight: Number.isFinite(Number(token.weight)) ? Number(token.weight) : null,
  };
}

function setText(node, value) {
  if (node) {
    node.textContent = String(value ?? "");
  }
}

function countPromptUnits(value) {
  const trimmed = String(value ?? "").trim();
  if (!trimmed) {
    return 0;
  }
  return trimmed.split(/[\s,]+/).filter(Boolean).length;
}

function splitPromptTokenText(text) {
  const source = String(text ?? "");
  const tokens = [];
  let current = "";
  let escaped = false;
  let parenDepth = 0;
  let bracketDepth = 0;
  let angleDepth = 0;

  for (const char of source) {
    if (escaped) {
      current += char;
      escaped = false;
      continue;
    }
    if (char === "\\") {
      current += char;
      escaped = true;
      continue;
    }
    if (char === "<") {
      angleDepth += 1;
      current += char;
      continue;
    }
    if (char === ">" && angleDepth > 0) {
      angleDepth -= 1;
      current += char;
      continue;
    }
    if (char === "(" && angleDepth === 0) {
      parenDepth += 1;
      current += char;
      continue;
    }
    if (char === ")" && parenDepth > 0 && angleDepth === 0) {
      parenDepth -= 1;
      current += char;
      continue;
    }
    if (char === "[" && angleDepth === 0) {
      bracketDepth += 1;
      current += char;
      continue;
    }
    if (char === "]" && bracketDepth > 0 && angleDepth === 0) {
      bracketDepth -= 1;
      current += char;
      continue;
    }
    if ((char === "," || char === "\n") && parenDepth === 0 && bracketDepth === 0 && angleDepth === 0) {
      const normalized = normalizeTokenText(current);
      if (normalized) {
        tokens.push(normalized);
      }
      current = "";
      continue;
    }
    current += char;
  }

  const normalized = normalizeTokenText(current);
  if (normalized) {
    tokens.push(normalized);
  }
  return tokens;
}

function parsePromptTokens(text, { scope = "prompt" } = {}) {
  return splitPromptTokenText(text).map((entry, index) => createToken(entry, { scope, orderIndex: index }));
}

function buildPromptTextFromTokens(tokens) {
  return (Array.isArray(tokens) ? tokens : [])
    .filter((token) => token && !token.disabled && normalizeTokenText(token.raw_text ?? token.text))
    .map((token) => normalizeTokenText(token.raw_text ?? token.text))
    .join(", ");
}

function formatTokenWeight(value) {
  const rounded = Math.max(0, Math.round(Number(value) * 100) / 100);
  return String(rounded).replace(/\.0+$/, "").replace(/(\.\d*[1-9])0+$/, "$1");
}

function adjustPromptTokenWeight(text, delta) {
  const normalized = normalizeTokenText(text);
  if (!normalized) {
    return "";
  }
  const match = normalized.match(/^\((.+):([+-]?(?:\d+(?:\.\d+)?|\.\d+))\)$/);
  if (match) {
    return `(${match[1]}:${formatTokenWeight(Number.parseFloat(match[2]) + delta)})`;
  }
  return `(${normalized}:${delta >= 0 ? "1.1" : "0.9"})`;
}

function updateTokenText(token, nextText) {
  const rawText = normalizeTokenText(nextText);
  token.text = rawText;
  token.raw_text = rawText;
  token.normalized_text = rawText.toLowerCase();
  token.keyword_family = classifyPromptToken(rawText);
  token.weight = extractTokenWeight(rawText);
}

function formatPromptText(text, formattingRules) {
  let nextText = String(text ?? "");
  if (formattingRules?.normalize_spacing) {
    nextText = nextText
      .split(/[\n,]+/)
      .map((entry) => entry.trim())
      .filter(Boolean)
      .join(", ");
  }
  if (formattingRules?.dedupe_commas) {
    const seen = new Set();
    nextText = nextText
      .split(/[\n,]+/)
      .map((entry) => entry.trim())
      .filter(Boolean)
      .filter((entry) => {
        const key = entry.toLowerCase();
        if (seen.has(key)) {
          return false;
        }
        seen.add(key);
        return true;
      })
      .join(", ");
  }
  if (formattingRules?.trim_outer_whitespace) {
    nextText = nextText.trim();
  }
  return nextText;
}

function buildEntryLabel(scope, promptText) {
  const preview = String(promptText ?? "").trim();
  if (!preview) {
    return scope === "negative" ? "Negative Prompt" : "Prompt";
  }
  const prefix = scope === "negative" ? "Negative" : "Prompt";
  return `${prefix}: ${preview.slice(0, 48)}`;
}

function clearChildren(node) {
  if (node) {
    node.replaceChildren();
  }
}

export function createPromptWorkbenchShell({
  idPrefix,
  parent,
  bootstrapState,
  promptInput,
  negativePromptInput,
  namespaces,
  appendTextElement,
  createActionButton,
  onStatusMessage,
} = {}) {
  const shell = document.createElement("section");
  shell.id = `${idPrefix}-section`;
  shell.className = "rookieui-shell__prompt-workbench rookieui-shell__prompt-workbench-card-root";
  shell.dataset.layout = "prompt_all_in_one";
  shell.tabIndex = -1;
  parent.appendChild(shell);

  const configState = structuredClone(bootstrapState?.promptWorkbench?.config ?? {});
  configState.translation = configState.translation ?? { default_provider: "", providers: {} };
  configState.ai_assist = configState.ai_assist ?? {
    default_provider: "",
    providers: {},
    instruction_preset: "",
  };
  const blacklistState = structuredClone(bootstrapState?.promptWorkbench?.blacklist ?? { enabled: false, entries: [], translation_entries: [] });
  blacklistState.translation_entries = Array.isArray(blacklistState.translation_entries) ? blacklistState.translation_entries : [];
  const hostActions = structuredClone(bootstrapState?.promptWorkbench?.host_actions ?? {});
  const languageOptions = Array.isArray(bootstrapState?.promptWorkbench?.language_options)
    ? bootstrapState.promptWorkbench.language_options
    : [];
  const themeStyleOptions = Array.isArray(bootstrapState?.promptWorkbench?.theme_style_options)
    ? bootstrapState.promptWorkbench.theme_style_options
    : [];
  const namespaceMap = {
    prompt: String(namespaces?.prompt ?? "").trim(),
    negative: String(namespaces?.negative ?? "").trim(),
  };
  const inputMap = {
    prompt: promptInput,
    negative: negativePromptInput,
  };
  const stateCache = new Map();
  const editorCache = new Map();
  const historyCache = new Map();
  const favoritesCache = new Map();
  const dirtyTimers = new Map();
  const autoHistoryTimers = new Map();
  const lastAutoHistoryText = new Map();
  const catalogSearchState = { query: "" };
  let providersPayload = null;
  let catalogPayload = null;
  let stateReadyPromise = null;
  let resourcesReadyPromise = null;
  let activeScope = "prompt";
  let resourcesLoaded = false;
  let dragTokenId = "";
  const assistState = {
    imageDescription: "",
    generatedPrompt: "",
    generating: false,
  };
  const upsampleState = {
    running: false,
  };
  const importExportState = {
    jsonText: "",
    busy: false,
  };
  const t = (key) => {
    const language = String(configState?.language ?? "en").trim();
    return WORKBENCH_I18N[language]?.[key] ?? WORKBENCH_I18N.en[key] ?? key;
  };

  const header = document.createElement("div");
  header.className = "rookieui-shell__prompt-workbench-header";
  header.dataset.pwUi = "prompt-card-header";
  shell.appendChild(header);

  const headerCopy = document.createElement("div");
  headerCopy.className = "rookieui-shell__prompt-workbench-copy";
  header.appendChild(headerCopy);
  appendTextElement(headerCopy, "h5", "rookieui-shell__prompt-workbench-title", t("title"));
  appendTextElement(
    headerCopy,
    "p",
    "rookieui-shell__prompt-workbench-subtitle",
    t("subtitle"),
  );

  const headerActions = document.createElement("div");
  headerActions.className = "rookieui-shell__prompt-workbench-header-actions rookieui-shell__prompt-workbench-toolbar";
  headerActions.dataset.pwUi = "header-toolbar";
  header.appendChild(headerActions);

  const toggleButton = createActionButton(`${idPrefix}-toggle`, t("openWorkbench"));
  toggleButton.classList.add("rookieui-shell__prompt-workbench-toggle");
  toggleButton.dataset.pwUi = "fold-toggle";
  headerActions.appendChild(toggleButton);

  const body = document.createElement("div");
  body.id = `${idPrefix}-body`;
  body.className = "rookieui-shell__prompt-workbench-body rookieui-shell__prompt-workbench-card-body";
  body.dataset.pwUi = "prompt-card-body";
  shell.appendChild(body);

  const namespaceTabs = document.createElement("div");
  namespaceTabs.className = "rookieui-shell__prompt-workbench-tabs";
  namespaceTabs.dataset.pwUi = "scope-tabs";
  body.appendChild(namespaceTabs);

  const tabButtons = new Map();
  const createScopeButton = (scope, label) => {
    const button = document.createElement("button");
    button.type = "button";
    button.id = `${idPrefix}-tab-${scope}`;
    button.className = "rookieui-shell__prompt-workbench-tab";
    button.textContent = label;
    button.addEventListener("click", () => {
      activeScope = scope;
      syncUi();
    });
    namespaceTabs.appendChild(button);
    tabButtons.set(scope, button);
  };
  createScopeButton("prompt", t("promptTab"));
  createScopeButton("negative", t("negativeTab"));

  const summaryGrid = document.createElement("div");
  summaryGrid.className = "rookieui-shell__prompt-workbench-summary-grid rookieui-shell__prompt-workbench-status-strip";
  summaryGrid.dataset.pwUi = "status-strip";
  body.appendChild(summaryGrid);

  const createSummaryCard = (key, label) => {
    const card = document.createElement("article");
    card.className = "rookieui-shell__prompt-workbench-card";
    appendTextElement(card, "span", "rookieui-shell__prompt-workbench-card-label", label);
    const value = document.createElement("strong");
    value.id = `${idPrefix}-${key}`;
    value.className = "rookieui-shell__prompt-workbench-card-value";
    card.appendChild(value);
    summaryGrid.appendChild(card);
    return value;
  };

  const summaryNodes = {
    state: createSummaryCard("state", t("summaryState")),
    providers: createSummaryCard("providers", t("summaryProviders")),
    catalogs: createSummaryCard("catalogs", t("summaryCatalogs")),
    history: createSummaryCard("history", t("summaryHistory")),
    favorites: createSummaryCard("favorites", t("summaryFavorites")),
    blacklist: createSummaryCard("blacklist", t("summaryBlacklist")),
  };

  const panelRail = document.createElement("div");
  panelRail.className = "rookieui-shell__prompt-workbench-panel-rail";
  body.appendChild(panelRail);

  const panelButtons = new Map();
  ["editor", "history", "favorites", "catalog", "assist", "format"].forEach((panelId) => {
    const button = document.createElement("button");
    button.type = "button";
    button.id = `${idPrefix}-panel-${panelId}`;
    button.className = "rookieui-shell__prompt-workbench-panel-button";
    button.textContent = t(`panel${panelId.charAt(0).toUpperCase()}${panelId.slice(1)}`);
    button.addEventListener("click", () => {
      const currentState = getActiveState();
      currentState.active_panel = panelId;
      queueStatePersist();
      syncUi();
    });
    panelRail.appendChild(button);
    panelButtons.set(panelId, button);
  });

  const actionsRow = document.createElement("div");
  actionsRow.className = "rookieui-shell__prompt-workbench-actions";
  body.appendChild(actionsRow);

  const captureButton = createActionButton(`${idPrefix}-capture`, t("captureCurrentText"));
  captureButton.addEventListener("click", () => {
    const input = getActiveInput();
    const nextText = String(input?.value ?? "");
    const state = getActiveState();
    state.draft_prompt = nextText;
    editorCache.set(getActiveNamespace(), parsePromptTokens(nextText, { scope: activeScope }));
    queueStatePersist();
    syncUi();
    onStatusMessage?.("Captured current prompt text into Prompt Workbench state");
  });
  actionsRow.appendChild(captureButton);

  const restoreButton = createActionButton(`${idPrefix}-restore`, t("restoreDraft"));
  restoreButton.addEventListener("click", () => {
    applyPromptTextToInput(getActiveState().draft_prompt, {
      updateEditor: true,
      statusMessage: "Restored saved Prompt Workbench draft into the active prompt field",
    });
  });
  actionsRow.appendChild(restoreButton);

  const panelContent = document.createElement("div");
  panelContent.className = "rookieui-shell__prompt-workbench-panel-content";
  body.appendChild(panelContent);

  const editorPane = document.createElement("section");
  editorPane.id = `${idPrefix}-editor-pane`;
  editorPane.className = "rookieui-shell__prompt-workbench-pane";
  panelContent.appendChild(editorPane);

  const historyPane = document.createElement("section");
  historyPane.id = `${idPrefix}-history-pane`;
  historyPane.className = "rookieui-shell__prompt-workbench-pane";
  panelContent.appendChild(historyPane);

  const favoritesPane = document.createElement("section");
  favoritesPane.id = `${idPrefix}-favorites-pane`;
  favoritesPane.className = "rookieui-shell__prompt-workbench-pane";
  panelContent.appendChild(favoritesPane);

  const catalogPane = document.createElement("section");
  catalogPane.id = `${idPrefix}-catalog-pane`;
  catalogPane.className = "rookieui-shell__prompt-workbench-pane";
  panelContent.appendChild(catalogPane);

  const formatPane = document.createElement("section");
  formatPane.id = `${idPrefix}-format-pane`;
  formatPane.className = "rookieui-shell__prompt-workbench-pane";
  panelContent.appendChild(formatPane);

  const assistPane = document.createElement("section");
  assistPane.id = `${idPrefix}-assist-pane`;
  assistPane.className = "rookieui-shell__prompt-workbench-pane";
  panelContent.appendChild(assistPane);

  const details = document.createElement("div");
  details.className = "rookieui-shell__prompt-workbench-details";
  body.appendChild(details);

  const detailNodes = {
    scope: appendTextElement(details, "p", "rookieui-shell__prompt-workbench-detail", ""),
    draft: appendTextElement(details, "p", "rookieui-shell__prompt-workbench-detail", ""),
    panel: appendTextElement(details, "p", "rookieui-shell__prompt-workbench-detail", ""),
    status: appendTextElement(details, "p", "rookieui-shell__prompt-workbench-status", t("ready")),
  };

  function getActiveNamespace() {
    return namespaceMap[activeScope];
  }

  function getActiveInput() {
    return inputMap[activeScope] ?? null;
  }

  function getNamespaceInput(namespace) {
    if (namespace === namespaceMap.prompt) {
      return inputMap.prompt;
    }
    if (namespace === namespaceMap.negative) {
      return inputMap.negative;
    }
    return null;
  }

  function getActiveState() {
    const namespace = getActiveNamespace();
    if (!stateCache.has(namespace)) {
      stateCache.set(namespace, normalizeStatePayload(namespace, { draft_prompt: getActiveInput()?.value ?? "" }));
    }
    return stateCache.get(namespace);
  }

  function ensureEditorTokens(namespace) {
    if (!editorCache.has(namespace)) {
      const state = stateCache.get(namespace) ?? normalizeStatePayload(namespace, { draft_prompt: getNamespaceInput(namespace)?.value ?? "" });
      editorCache.set(namespace, parsePromptTokens(state.draft_prompt || getNamespaceInput(namespace)?.value, { scope: activeScope }));
    }
    return editorCache.get(namespace);
  }

  function setBodyOpen(isOpen) {
    shell.dataset.open = String(isOpen);
    body.hidden = !isOpen;
    toggleButton.textContent = isOpen ? t("hideWorkbench") : t("openWorkbench");
  }

  function readPreferredOpenState() {
    const state = getActiveState();
    if (state.workbench_open) {
      return true;
    }
    return Boolean(configState?.ui_preferences?.default_open);
  }

  function isPanelVisible(panelId) {
    if (panelId === "history") {
      return configState?.ui_preferences?.show_history !== false;
    }
    if (panelId === "favorites") {
      return configState?.ui_preferences?.show_favorites !== false;
    }
    return true;
  }

  function resolveVisiblePanel(panelId) {
    if (panelId && isPanelVisible(panelId)) {
      return panelId;
    }
    const preferredPanel = normalizeTokenText(configState?.ui_preferences?.preferred_panel) || "editor";
    if (isPanelVisible(preferredPanel)) {
      return preferredPanel;
    }
    return "editor";
  }

  function updateStatus(message) {
    setText(detailNodes.status, message);
  }

  function queueStatePersist(namespaceOverride = "") {
    const namespace = normalizeTokenText(namespaceOverride) || getActiveNamespace();
    const state =
      stateCache.get(namespace) ??
      normalizeStatePayload(namespace, { draft_prompt: getNamespaceInput(namespace)?.value ?? "" });
    stateCache.set(namespace, state);
    const existingTimer = dirtyTimers.get(namespace);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }
    const nextTimer = setTimeout(async () => {
      dirtyTimers.delete(namespace);
      const result = await bootstrapState?.updatePromptWorkbenchStateRequest?.(namespace, {
        workbench_open: state.workbench_open,
        active_panel: state.active_panel,
        draft_prompt: state.draft_prompt,
        selected_entry_id: state.selected_entry_id,
      });
      updateStatus(result?.ok === false ? "Prompt Workbench state saved with fallback semantics" : "Prompt Workbench state synchronized");
      syncUi();
    }, 180);
    dirtyTimers.set(namespace, nextTimer);
  }

  function serializeTokenPayload(token, index) {
    const rawText = normalizeTokenText(token?.raw_text ?? token?.text);
    if (!rawText) {
      return null;
    }
    return {
      raw_text: rawText,
      normalized_text: normalizeTokenText(token.normalized_text) || rawText.toLowerCase(),
      scope: normalizeTokenText(token.scope) || activeScope,
      order_index: Number.isInteger(token.order_index) ? token.order_index : index,
      disabled: Boolean(token.disabled),
      selected: Boolean(token.selected),
      translated_text: String(token.translated_text ?? ""),
      keyword_family: normalizeTokenText(token.keyword_family) || classifyPromptToken(rawText),
      weight: Number.isFinite(Number(token.weight)) ? Number(token.weight) : null,
    };
  }

  function serializeTokenPayloads(tokens) {
    return (Array.isArray(tokens) ? tokens : []).map(serializeTokenPayload).filter(Boolean);
  }

  function buildCollectionItem(scope, promptText, tokens) {
    const tokenPayloads = serializeTokenPayloads(tokens);
    return {
      label: buildEntryLabel(scope, promptText),
      prompt_text: String(promptText ?? "").trim(),
      tag_tokens: tokenPayloads.filter((token) => !token.disabled).map((token) => token.raw_text),
      token_payloads: tokenPayloads,
    };
  }

  function queueAutoHistoryCapture(namespace, scope, promptText, tokens) {
    const normalizedText = String(promptText ?? "").trim();
    if (!namespace || !normalizedText || normalizedText === lastAutoHistoryText.get(namespace)) {
      return;
    }
    const existingTimer = autoHistoryTimers.get(namespace);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }
    const tokenSnapshot = serializeTokenPayloads(tokens);
    const nextTimer = setTimeout(() => {
      autoHistoryTimers.delete(namespace);
      if (normalizedText === lastAutoHistoryText.get(namespace)) {
        return;
      }
      lastAutoHistoryText.set(namespace, normalizedText);
      void bootstrapState?.updatePromptWorkbenchHistoryRequest?.(namespace, "auto_capture", {
        item: buildCollectionItem(scope, normalizedText, tokenSnapshot),
      }).then((result) => {
        const normalizedItems = Array.isArray(result?.data?.items) ? result.data.items.map(normalizePromptEntry) : [];
        historyCache.set(namespace, normalizedItems);
        updateStatus("Auto-saved prompt history");
        syncUi();
      });
    }, 600);
    autoHistoryTimers.set(namespace, nextTimer);
  }

  function queueConfigPersist() {
    void bootstrapState?.updatePromptWorkbenchConfigRequest?.(configState).then((result) => {
      if (result?.data?.config) {
        Object.assign(configState, result.data.config);
      }
      updateStatus(result?.ok === false ? "Formatting preferences saved with fallback semantics" : "Formatting preferences synchronized");
      syncUi();
    });
  }

  function getTranslationProviders() {
    return Array.isArray(providersPayload?.surfaces?.translation?.providers)
      ? providersPayload.surfaces.translation.providers.filter((entry) => entry?.execution_state === "shipped")
      : [];
  }

  function getAiAssistProviders() {
    return Array.isArray(providersPayload?.surfaces?.ai_assist?.providers)
      ? providersPayload.surfaces.ai_assist.providers.filter((entry) => entry?.execution_state === "shipped")
      : [];
  }

  function getDanbooruUpsampleAction() {
    const action = hostActions?.danbooru_upsample;
    if (action && typeof action === "object") {
      return action;
    }
    return {
      action_id: "danbooru_upsample",
      title: "Upsample Tags",
      route_path: "/rookieui/prompt-tools/upsample",
      available: false,
      resolved_node_alias: "",
      availability: {
        status: "host_missing",
        detail: "Host-installed Danbooru upsampler node is not available in the active ComfyUI registry.",
      },
    };
  }

  function getCatalogHighlight(entry, fallback = "plain") {
    return normalizeTokenText(entry?.highlight ?? entry?.category) || fallback;
  }

  function getTokenHighlight(token) {
    const tokenFamily = normalizeTokenText(token?.keyword_family) || "plain";
    const tokenFamilyHighlights = catalogPayload?.catalog_highlights?.token_families ?? {};
    return normalizeTokenText(tokenFamilyHighlights[tokenFamily]?.highlight) || tokenFamily;
  }

  function appendPromptFragment(fragment, { replace = false, statusMessage = "" } = {}) {
    const normalizedFragment = String(fragment ?? "").trim();
    if (!normalizedFragment) {
      return;
    }
    const currentText = String(getActiveState().draft_prompt || getActiveInput()?.value || "").trim();
    const nextText = replace || !currentText ? normalizedFragment : `${currentText}, ${normalizedFragment}`;
    applyPromptTextToInput(nextText, {
      updateEditor: true,
      statusMessage: statusMessage || "Updated prompt from Prompt Workbench catalog action",
    });
  }

  function persistTranslationProviderSelection(providerId) {
    configState.translation = {
      ...(configState.translation ?? {}),
      default_provider: String(providerId ?? "").trim(),
      providers: configState.translation?.providers ?? {},
    };
    queueConfigPersist();
  }

  function persistAiAssistProviderSelection(providerId) {
    configState.ai_assist = {
      ...(configState.ai_assist ?? {}),
      default_provider: String(providerId ?? "").trim(),
      providers: configState.ai_assist?.providers ?? {},
      instruction_preset: String(configState.ai_assist?.instruction_preset ?? ""),
    };
    queueConfigPersist();
  }

  function updateShellThemeStyle() {
    shell.dataset.themeStyle = String(configState?.theme_style ?? "rookieui_classic").trim() || "rookieui_classic";
  }

  function translateActivePrompt(targetLanguage) {
    const providerId = String(configState.translation?.default_provider ?? "").trim();
    const promptText = String(getActiveState().draft_prompt || getActiveInput()?.value || "").trim();
    if (!providerId) {
      updateStatus("Select a shipped translation provider before translating");
      return;
    }
    if (!promptText) {
      updateStatus("No prompt text is available for translation");
      return;
    }
    updateStatus("Translating prompt text...");
    void bootstrapState
      ?.translatePromptWorkbenchRequest?.({
        provider: providerId,
        from_lang: "auto",
        to_lang: targetLanguage,
        text: promptText,
      })
      .then((result) => {
        const translatedText = String(result?.data?.translated_text ?? "").trim();
        if (!translatedText) {
          updateStatus("Translation response did not include translated text");
          return;
        }
        applyPromptTextToInput(translatedText, {
          updateEditor: true,
          statusMessage: `Translated prompt text to ${targetLanguage}`,
        });
      })
      .catch(() => {
        updateStatus("Prompt translation failed");
      });
  }

  function translateTokenBatch(tokens, targetLanguage) {
    const providerId = String(configState.translation?.default_provider ?? "").trim();
    const selectedTokens = (Array.isArray(tokens) ? tokens : []).filter(Boolean);
    if (!selectedTokens.length) {
      updateStatus("Select one or more prompt tokens before translating");
      return;
    }
    if (!providerId) {
      updateStatus("Select a shipped translation provider before translating");
      return;
    }
    const texts = selectedTokens.map((token) => normalizeTokenText(token.raw_text ?? token.text)).filter(Boolean);
    if (!texts.length) {
      updateStatus("No prompt tokens are available for translation");
      return;
    }
    updateStatus("Translating selected prompt tokens...");
    void bootstrapState
      ?.translatePromptWorkbenchRequest?.({
        provider: providerId,
        from_lang: "auto",
        to_lang: targetLanguage,
        texts,
        dictionary_first: true,
      })
      .then((result) => {
        const translatedTexts = Array.isArray(result?.data?.translated_texts) ? result.data.translated_texts : [];
        selectedTokens.forEach((token, index) => {
          const translatedText = String(translatedTexts[index] ?? "").trim();
          if (translatedText) {
            token.translated_text = translatedText;
          }
        });
        updateStatus("Translated selected prompt tokens");
        syncUi();
      })
      .catch(() => {
        updateStatus("Prompt token translation failed");
      });
  }

  function requestDanbooruUpsample() {
    const action = getDanbooruUpsampleAction();
    const availability = action?.availability ?? {};
    const availabilityStatus = String(availability?.status ?? "").trim() || "host_missing";
    const promptText = String(getActiveState().draft_prompt || getActiveInput()?.value || "").trim();
    const negativePromptText = String(inputMap.negative?.value ?? stateCache.get(namespaceMap.negative)?.draft_prompt ?? "").trim();
    if (activeScope !== "prompt") {
      updateStatus("Upsample Tags is only available for the primary prompt scope");
      return;
    }
    if (!promptText) {
      updateStatus("No prompt text is available for tag upsampling");
      return;
    }
    if (!Boolean(action?.available) || availabilityStatus !== "ready") {
      updateStatus(String(availability?.detail ?? "Danbooru upsampler host action is unavailable."));
      return;
    }
    upsampleState.running = true;
    updateStatus("Upsampling prompt tags through the host Danbooru node...");
    syncUi();
    const requestPromise = bootstrapState?.upsamplePromptWorkbenchRequest?.({
        prompt: promptText,
        negative_prompt_tags: negativePromptText,
        ban_tags: "",
      });
    if (!requestPromise || typeof requestPromise.then !== "function") {
      upsampleState.running = false;
      updateStatus("Danbooru upsampler request binding is unavailable");
      syncUi();
      return;
    }
    void requestPromise
      .then((result) => {
        if (result?.ok === false) {
          const errorDetail =
            String(result?.data?.detail ?? "").trim() ||
            String(result?.data?.availability?.detail ?? "").trim() ||
            "Danbooru upsampler request did not complete successfully";
          updateStatus(errorDetail);
          return;
        }
        const finalPrompt = String(result?.data?.final_prompt ?? "").trim();
        if (!finalPrompt) {
          updateStatus("Danbooru upsampler returned empty prompt text");
          return;
        }
        applyPromptTextToInput(finalPrompt, {
          updateEditor: true,
          statusMessage: "Applied Danbooru upsampled tags",
        });
      })
      .catch(() => {
        updateStatus("Danbooru upsampler request failed");
      })
      .finally(() => {
        upsampleState.running = false;
        syncUi();
      });
  }

  function applyPromptTextToInput(nextText, { updateEditor = true, statusMessage = "" } = {}) {
    const namespace = getActiveNamespace();
    const input = getActiveInput();
    const state = getActiveState();
    const normalizedText = String(nextText ?? "");
    state.draft_prompt = normalizedText;
    if (updateEditor) {
      editorCache.set(namespace, parsePromptTokens(normalizedText, { scope: activeScope }));
    }
    if (input) {
      input.value = normalizedText;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    } else {
      queueStatePersist();
      syncUi();
    }
    if (statusMessage) {
      onStatusMessage?.(statusMessage);
      updateStatus(statusMessage);
    }
  }

  function requestAiAssistGeneration() {
    const providerId = String(configState?.ai_assist?.default_provider ?? "").trim();
    const instructionPreset = String(configState?.ai_assist?.instruction_preset ?? "").trim();
    const imageDescription = String(assistState.imageDescription ?? "").trim();
    if (!providerId) {
      updateStatus("Select a shipped AI assist provider before generating");
      return;
    }
    if (!imageDescription) {
      updateStatus("AI Assist requires an image description");
      return;
    }
    assistState.generating = true;
    updateStatus("Generating prompt with AI Assist...");
    syncUi();
    void bootstrapState
      ?.assistPromptWorkbenchRequest?.({
        provider: providerId,
        instruction_preset: instructionPreset,
        image_description: imageDescription,
        language: configState?.language ?? "en",
        theme_style: configState?.theme_style ?? "rookieui_classic",
      })
      .then((result) => {
        assistState.generatedPrompt = String(result?.data?.generated_prompt ?? "").trim();
        updateStatus(assistState.generatedPrompt ? "AI Assist generated a prompt draft" : "AI Assist returned empty prompt text");
      })
      .catch(() => {
        updateStatus("AI Assist request failed");
      })
      .finally(() => {
        assistState.generating = false;
        syncUi();
      });
  }

  function rebuildPromptFromEditor(statusMessage) {
    const namespace = getActiveNamespace();
    const tokens = ensureEditorTokens(namespace);
    const nextText = buildPromptTextFromTokens(tokens);
    const state = getActiveState();
    state.draft_prompt = nextText;
    const input = getActiveInput();
    if (input) {
      input.value = nextText;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    } else {
      queueStatePersist();
      syncUi();
    }
    if (statusMessage) {
      onStatusMessage?.(statusMessage);
      updateStatus(statusMessage);
    }
  }

  function addCurrentPromptToCollection(collectionName) {
    const actionMethod =
      collectionName === "favorites"
        ? bootstrapState?.updatePromptWorkbenchFavoritesRequest
        : bootstrapState?.updatePromptWorkbenchHistoryRequest;
    const namespace = getActiveNamespace();
    const state = getActiveState();
    const promptText = state.draft_prompt || String(getActiveInput()?.value ?? "").trim();
    if (!promptText) {
      updateStatus(`No ${activeScope === "negative" ? "negative prompt" : "prompt"} text to save`);
      return;
    }
    const item = buildCollectionItem(activeScope, promptText, ensureEditorTokens(namespace));
    void actionMethod?.(namespace, "push", { item }).then((result) => {
      const normalizedItems = Array.isArray(result?.data?.items) ? result.data.items.map(normalizePromptEntry) : [];
      if (collectionName === "favorites") {
        favoritesCache.set(namespace, normalizedItems);
      } else {
        historyCache.set(namespace, normalizedItems);
      }
      updateStatus(`Saved current ${activeScope === "negative" ? "negative prompt" : "prompt"} to ${collectionName}`);
      syncUi();
    });
  }

  function applyCollectionEntry(entry) {
    applyPromptTextToInput(entry.prompt_text, {
      updateEditor: true,
      statusMessage: `Applied ${activeScope === "negative" ? "negative prompt" : "prompt"} entry`,
    });
  }

  function mutateCollection(collectionName, action, payload) {
    const namespace = getActiveNamespace();
    const actionMethod =
      collectionName === "favorites"
        ? bootstrapState?.updatePromptWorkbenchFavoritesRequest
        : bootstrapState?.updatePromptWorkbenchHistoryRequest;
    void actionMethod?.(namespace, action, payload).then((result) => {
      const normalizedItems = Array.isArray(result?.data?.items) ? result.data.items.map(normalizePromptEntry) : [];
      if (collectionName === "favorites") {
        favoritesCache.set(namespace, normalizedItems);
      } else {
        historyCache.set(namespace, normalizedItems);
      }
      updateStatus(`${collectionName === "favorites" ? "Favorites" : "History"} updated`);
      syncUi();
    });
  }

  function addTokenToBlacklist(tokenText) {
    const normalized = String(tokenText ?? "").trim();
    if (!normalized) {
      return;
    }
    addTokensToBlacklist([normalized]);
  }

  function addTokensToBlacklist(tokenTexts) {
    const normalizedTokens = (Array.isArray(tokenTexts) ? tokenTexts : [])
      .map((tokenText) => String(tokenText ?? "").trim())
      .filter(Boolean);
    if (!normalizedTokens.length) {
      return;
    }
    const nextEntries = Array.from(new Set([...(blacklistState.entries ?? []), ...normalizedTokens]));
    blacklistState.enabled = true;
    blacklistState.entries = nextEntries;
    void bootstrapState?.updatePromptWorkbenchBlacklistRequest?.(blacklistState).then((result) => {
      if (result?.data?.blacklist) {
        Object.assign(blacklistState, result.data.blacklist);
      }
      updateStatus("Prompt Workbench blacklist updated");
      syncUi();
    });
  }

  function addTokensToTranslationBlacklist(tokenTexts) {
    const normalizedTokens = (Array.isArray(tokenTexts) ? tokenTexts : [])
      .map((tokenText) => String(tokenText ?? "").trim())
      .filter(Boolean);
    if (!normalizedTokens.length) {
      return;
    }
    const nextEntries = Array.from(new Set([...(blacklistState.translation_entries ?? []), ...normalizedTokens]));
    blacklistState.translation_entries = nextEntries;
    void bootstrapState?.updatePromptWorkbenchBlacklistRequest?.(blacklistState).then((result) => {
      if (result?.data?.blacklist) {
        Object.assign(blacklistState, result.data.blacklist);
      }
      blacklistState.translation_entries = Array.isArray(blacklistState.translation_entries) ? blacklistState.translation_entries : [];
      updateStatus("Prompt Workbench translation blacklist updated");
      syncUi();
    });
  }

  function removeBlacklistEntry(entryText) {
    blacklistState.entries = (blacklistState.entries ?? []).filter((entry) => entry !== entryText);
    void bootstrapState?.updatePromptWorkbenchBlacklistRequest?.(blacklistState).then((result) => {
      if (result?.data?.blacklist) {
        Object.assign(blacklistState, result.data.blacklist);
      }
      blacklistState.translation_entries = Array.isArray(blacklistState.translation_entries) ? blacklistState.translation_entries : [];
      updateStatus("Removed blacklist entry");
      syncUi();
    });
  }

  function removeTranslationBlacklistEntry(entryText) {
    blacklistState.translation_entries = (blacklistState.translation_entries ?? []).filter((entry) => entry !== entryText);
    void bootstrapState?.updatePromptWorkbenchBlacklistRequest?.(blacklistState).then((result) => {
      if (result?.data?.blacklist) {
        Object.assign(blacklistState, result.data.blacklist);
      }
      blacklistState.translation_entries = Array.isArray(blacklistState.translation_entries) ? blacklistState.translation_entries : [];
      updateStatus("Removed translation blacklist entry");
      syncUi();
    });
  }

  function applyBlacklistFilter() {
    const tokens = ensureEditorTokens(getActiveNamespace());
    const blacklistSet = new Set((blacklistState.entries ?? []).map((entry) => String(entry).trim().toLowerCase()));
    tokens.forEach((token) => {
      token.disabled = blacklistSet.has(normalizeTokenText(token.raw_text ?? token.text).toLowerCase());
    });
    rebuildPromptFromEditor("Applied Prompt Workbench blacklist filter");
  }

  function getSelectedTokens() {
    return ensureEditorTokens(getActiveNamespace()).filter((token) => token.selected);
  }

  function mutateSelectedTokens(action) {
    const namespace = getActiveNamespace();
    const tokens = ensureEditorTokens(namespace);
    const selectedTokens = tokens.filter((token) => token.selected);
    if (!selectedTokens.length) {
      updateStatus("Select one or more prompt tokens before running a batch action");
      return;
    }
    if (action === "enable" || action === "disable") {
      selectedTokens.forEach((token) => {
        token.disabled = action === "disable";
      });
      rebuildPromptFromEditor(action === "disable" ? "Disabled selected prompt tokens" : "Enabled selected prompt tokens");
      return;
    }
    if (action === "delete") {
      editorCache.set(
        namespace,
        tokens.filter((token) => !token.selected),
      );
      rebuildPromptFromEditor("Deleted selected prompt tokens");
      return;
    }
    if (action === "copy") {
      const selectedText = selectedTokens.map((token) => normalizeTokenText(token.raw_text ?? token.text)).filter(Boolean).join(", ");
      if (navigator?.clipboard?.writeText) {
        void navigator.clipboard.writeText(selectedText);
      }
      updateStatus("Copied selected prompt tokens");
      return;
    }
    if (action === "favorite") {
      const selectedText = selectedTokens.map((token) => normalizeTokenText(token.raw_text ?? token.text)).filter(Boolean).join(", ");
      const item = buildCollectionItem(activeScope, selectedText, selectedTokens);
      void bootstrapState?.updatePromptWorkbenchFavoritesRequest?.(namespace, "push", { item }).then((result) => {
        favoritesCache.set(
          namespace,
          Array.isArray(result?.data?.items) ? result.data.items.map(normalizePromptEntry) : [],
        );
        updateStatus("Saved selected prompt tokens to favorites");
        syncUi();
      });
      return;
    }
    if (action === "translate") {
      translateTokenBatch(selectedTokens, String(configState.language ?? "en").trim() || "en");
      return;
    }
    if (action === "blacklist") {
      addTokensToBlacklist(selectedTokens.map((token) => token.raw_text ?? token.text));
    }
    if (action === "translation-blacklist") {
      addTokensToTranslationBlacklist(selectedTokens.map((token) => token.raw_text ?? token.text));
    }
  }

  function renderEditorPane() {
    clearChildren(editorPane);
    const heading = document.createElement("div");
    heading.className = "rookieui-shell__prompt-workbench-pane-header";
    editorPane.appendChild(heading);
    appendTextElement(
      heading,
      "h6",
      "rookieui-shell__prompt-workbench-pane-title",
      activeScope === "negative" ? "Negative Prompt Editor" : "Prompt Editor",
    );

    const addRow = document.createElement("div");
    addRow.className = "rookieui-shell__prompt-workbench-editor-toolbar";
    editorPane.appendChild(addRow);

    const addInput = document.createElement("input");
    addInput.type = "text";
    addInput.id = `${idPrefix}-token-add`;
    addInput.className = "rookieui-shell__input";
    addInput.placeholder = "Add keyword or token";
    addRow.appendChild(addInput);

    const addButton = createActionButton(`${idPrefix}-token-add-button`, "Add Token");
    addButton.addEventListener("click", () => {
      const normalizedText = String(addInput.value ?? "").trim();
      if (!normalizedText) {
        return;
      }
      const tokens = ensureEditorTokens(getActiveNamespace());
      tokens.push(createToken(normalizedText, { scope: activeScope, orderIndex: tokens.length }));
      addInput.value = "";
      rebuildPromptFromEditor("Added prompt token");
    });
    addRow.appendChild(addButton);

    const translateRow = document.createElement("div");
    translateRow.className = "rookieui-shell__prompt-workbench-editor-toolbar";
    editorPane.appendChild(translateRow);

    const providerSelect = document.createElement("select");
    providerSelect.id = `${idPrefix}-translation-provider`;
    providerSelect.className = "rookieui-shell__input rookieui-shell__prompt-workbench-provider-select";
    providerSelect.setAttribute("aria-label", "Prompt Workbench translation provider");
    const providerPlaceholder = document.createElement("option");
    providerPlaceholder.value = "";
    providerPlaceholder.textContent = "Translation provider";
    providerSelect.appendChild(providerPlaceholder);
    getTranslationProviders().forEach((provider) => {
      const option = document.createElement("option");
      option.value = String(provider.provider_id ?? "");
      option.textContent = String(provider.title ?? provider.provider_id ?? "");
      providerSelect.appendChild(option);
    });
    providerSelect.value = String(configState.translation?.default_provider ?? "").trim();
    providerSelect.addEventListener("change", () => {
      persistTranslationProviderSelection(providerSelect.value);
    });
    translateRow.appendChild(providerSelect);

    const translateEnglishButton = createActionButton(`${idPrefix}-translate-en`, "Translate to English");
    translateEnglishButton.addEventListener("click", () => {
      translateActivePrompt("en");
    });
    translateRow.appendChild(translateEnglishButton);

    if (String(configState.language ?? "en").trim().toLowerCase() !== "en") {
      const localLanguage = String(configState.language ?? "en").trim() || "en";
      const translateLocalButton = createActionButton(`${idPrefix}-translate-local`, `Translate to ${localLanguage}`);
      translateLocalButton.addEventListener("click", () => {
        translateActivePrompt(localLanguage);
      });
      translateRow.appendChild(translateLocalButton);
    }

    const danbooruAction = getDanbooruUpsampleAction();
    const upsampleAvailability = danbooruAction?.availability ?? {};
    const upsampleStatus = String(upsampleAvailability?.status ?? "").trim() || "host_missing";
    const upsampleRow = document.createElement("div");
    upsampleRow.className = "rookieui-shell__prompt-workbench-editor-toolbar";
    editorPane.appendChild(upsampleRow);

    const upsampleButton = createActionButton(
      `${idPrefix}-upsample-tags`,
      upsampleState.running ? "Upsampling..." : String(danbooruAction?.title ?? "Upsample Tags"),
    );
    upsampleButton.disabled = upsampleState.running || activeScope !== "prompt" || !Boolean(danbooruAction?.available) || upsampleStatus !== "ready";
    upsampleButton.addEventListener("click", () => {
      requestDanbooruUpsample();
    });
    upsampleRow.appendChild(upsampleButton);

    const upsampleDetail = document.createElement("span");
    upsampleDetail.id = `${idPrefix}-upsample-detail`;
    upsampleDetail.className = "rookieui-shell__prompt-workbench-detail";
    upsampleDetail.textContent =
      activeScope !== "prompt"
        ? "Upsample Tags is limited to the primary prompt editor."
        : String(upsampleAvailability?.detail ?? "Danbooru upsampler host action is unavailable.");
    upsampleRow.appendChild(upsampleDetail);

    const tokens = ensureEditorTokens(getActiveNamespace());
    const selectedCount = getSelectedTokens().length;
    const batchRow = document.createElement("div");
    batchRow.className = "rookieui-shell__prompt-workbench-editor-toolbar rookieui-shell__prompt-workbench-selection-toolbar";
    batchRow.dataset.pwUi = "selection-batch-toolbar";
    editorPane.appendChild(batchRow);

    const selectedLabel = document.createElement("span");
    selectedLabel.id = `${idPrefix}-token-selected-count`;
    selectedLabel.className = "rookieui-shell__prompt-workbench-detail";
    selectedLabel.textContent = `${selectedCount} selected`;
    batchRow.appendChild(selectedLabel);

    const batchActions = [
      ["enable", "Enable Selected"],
      ["disable", "Disable Selected"],
      ["delete", "Delete Selected"],
      ["copy", "Copy Selected"],
      ["favorite", "Favorite Selected"],
      ["translate", "Translate Selected"],
      ["blacklist", "Blacklist Selected"],
      ["translation-blacklist", "Skip Translation"],
    ];
    batchActions.forEach(([action, label]) => {
      const button = createActionButton(`${idPrefix}-token-batch-${action}`, label);
      button.disabled = selectedCount === 0;
      button.setAttribute("aria-label", `${label} prompt tokens`);
      button.addEventListener("click", () => {
        mutateSelectedTokens(action);
      });
      batchRow.appendChild(button);
    });

    const list = document.createElement("div");
    list.id = `${idPrefix}-token-list`;
    list.className = "rookieui-shell__prompt-workbench-token-list rookieui-shell__prompt-workbench-token-board";
    list.dataset.pwUi = "token-chip-board";
    editorPane.appendChild(list);

    if (!tokens.length) {
      appendTextElement(
        list,
        "p",
        "rookieui-shell__prompt-workbench-empty",
        "No tokens yet. Capture or add prompt text to begin editing.",
      );
      return;
    }

    tokens.forEach((token, index) => {
      const row = document.createElement("div");
      row.className = "rookieui-shell__prompt-workbench-token rookieui-shell__prompt-workbench-token-chip";
      row.dataset.pwUi = "token-chip";
      row.dataset.disabled = String(token.disabled);
      row.dataset.keywordFamily = String(token.keyword_family ?? "plain");
      row.dataset.highlight = getTokenHighlight(token);
      row.draggable = true;
      row.tabIndex = 0;
      row.id = `${idPrefix}-token-${token.id}`;
      row.addEventListener("dragstart", () => {
        dragTokenId = token.id;
      });
      row.addEventListener("dragover", (event) => {
        event.preventDefault();
      });
      row.addEventListener("drop", (event) => {
        event.preventDefault();
        const draggedIndex = tokens.findIndex((entry) => entry.id === dragTokenId);
        const dropIndex = tokens.findIndex((entry) => entry.id === token.id);
        if (draggedIndex < 0 || dropIndex < 0 || draggedIndex === dropIndex) {
          return;
        }
        const [draggedToken] = tokens.splice(draggedIndex, 1);
        tokens.splice(dropIndex, 0, draggedToken);
        rebuildPromptFromEditor("Reordered prompt tokens");
      });

      const dragHandle = document.createElement("span");
      dragHandle.className = "rookieui-shell__prompt-workbench-token-handle";
      dragHandle.textContent = "::";
      row.appendChild(dragHandle);

      const selectedCheckbox = document.createElement("input");
      selectedCheckbox.type = "checkbox";
      selectedCheckbox.id = `${idPrefix}-token-select-${index}`;
      selectedCheckbox.className = "rookieui-shell__prompt-workbench-token-select";
      selectedCheckbox.setAttribute("aria-label", `Select prompt token ${index + 1}`);
      selectedCheckbox.checked = Boolean(token.selected);
      selectedCheckbox.addEventListener("change", () => {
        token.selected = selectedCheckbox.checked;
        updateStatus(token.selected ? "Selected prompt token" : "Deselected prompt token");
        syncUi();
      });
      row.appendChild(selectedCheckbox);

      const valueInput = document.createElement("input");
      valueInput.type = "text";
      valueInput.className = "rookieui-shell__input rookieui-shell__prompt-workbench-token-input";
      valueInput.value = token.raw_text ?? token.text;
      valueInput.addEventListener("change", () => {
        updateTokenText(token, valueInput.value);
        rebuildPromptFromEditor("Edited prompt token");
      });
      row.appendChild(valueInput);

      const translatedText = String(token.translated_text ?? "").trim();
      const translationDetail = document.createElement("span");
      translationDetail.id = `${idPrefix}-token-translation-${index}`;
      translationDetail.className =
        "rookieui-shell__prompt-workbench-token-translation rookieui-shell__prompt-workbench-token-local-language";
      translationDetail.dataset.pwUi = "token-local-language";
      translationDetail.dataset.hasTranslation = String(Boolean(translatedText));
      translationDetail.textContent = translatedText ? `Translation: ${translatedText}` : "Translation: not available";
      row.appendChild(translationDetail);

      const controls = document.createElement("div");
      controls.className = "rookieui-shell__prompt-workbench-token-actions rookieui-shell__prompt-workbench-token-quick-actions";
      controls.dataset.pwUi = "token-quick-actions";
      row.appendChild(controls);

      const toggleButton = createActionButton(`${idPrefix}-token-toggle-${index}`, token.disabled ? "Enable" : "Disable");
      toggleButton.addEventListener("click", () => {
        token.disabled = !token.disabled;
        rebuildPromptFromEditor(token.disabled ? "Disabled prompt token" : "Enabled prompt token");
      });
      controls.appendChild(toggleButton);

      const upButton = createActionButton(`${idPrefix}-token-up-${index}`, "Up");
      upButton.addEventListener("click", () => {
        if (index <= 0) {
          return;
        }
        [tokens[index - 1], tokens[index]] = [tokens[index], tokens[index - 1]];
        rebuildPromptFromEditor("Moved prompt token up");
      });
      controls.appendChild(upButton);

      const downButton = createActionButton(`${idPrefix}-token-down-${index}`, "Down");
      downButton.addEventListener("click", () => {
        if (index >= tokens.length - 1) {
          return;
        }
        [tokens[index], tokens[index + 1]] = [tokens[index + 1], tokens[index]];
        rebuildPromptFromEditor("Moved prompt token down");
      });
      controls.appendChild(downButton);

      const weightUpButton = createActionButton(`${idPrefix}-token-weight-up-${index}`, "Weight +");
      weightUpButton.addEventListener("click", () => {
        updateTokenText(token, adjustPromptTokenWeight(token.raw_text ?? token.text, 0.1));
        rebuildPromptFromEditor("Increased prompt token weight");
      });
      controls.appendChild(weightUpButton);

      const weightDownButton = createActionButton(`${idPrefix}-token-weight-down-${index}`, "Weight -");
      weightDownButton.addEventListener("click", () => {
        updateTokenText(token, adjustPromptTokenWeight(token.raw_text ?? token.text, -0.1));
        rebuildPromptFromEditor("Decreased prompt token weight");
      });
      controls.appendChild(weightDownButton);

      const copyButton = createActionButton(`${idPrefix}-token-copy-${index}`, "Copy");
      copyButton.addEventListener("click", () => {
        const tokenText = normalizeTokenText(token.raw_text ?? token.text);
        if (navigator?.clipboard?.writeText) {
          void navigator.clipboard.writeText(tokenText);
        }
        updateStatus("Copied prompt token");
      });
      controls.appendChild(copyButton);

      const deleteButton = createActionButton(`${idPrefix}-token-delete-${index}`, "Delete");
      deleteButton.addEventListener("click", () => {
        tokens.splice(index, 1);
        rebuildPromptFromEditor("Deleted prompt token");
      });
      controls.appendChild(deleteButton);

      const favoriteButton = createActionButton(`${idPrefix}-token-favorite-${index}`, "Favorite");
      favoriteButton.addEventListener("click", () => {
        const item = {
          label: token.raw_text ?? token.text,
          prompt_text: token.raw_text ?? token.text,
          tag_tokens: [token.raw_text ?? token.text],
          token_payloads: [serializeTokenPayload(token, index)],
        };
        void bootstrapState?.updatePromptWorkbenchFavoritesRequest?.(getActiveNamespace(), "push", { item }).then((result) => {
          favoritesCache.set(
            getActiveNamespace(),
            Array.isArray(result?.data?.items) ? result.data.items.map(normalizePromptEntry) : [],
          );
          updateStatus("Saved token to favorites");
          syncUi();
        });
      });
      controls.appendChild(favoriteButton);

      const translateButton = createActionButton(`${idPrefix}-token-translate-${index}`, "Translate");
      translateButton.addEventListener("click", () => {
        translateTokenBatch([token], String(configState.language ?? "en").trim() || "en");
      });
      controls.appendChild(translateButton);

      const blacklistButton = createActionButton(`${idPrefix}-token-blacklist-${index}`, "Blacklist");
      blacklistButton.addEventListener("click", () => {
        addTokenToBlacklist(token.raw_text ?? token.text);
      });
      controls.appendChild(blacklistButton);

      const translationBlacklistButton = createActionButton(`${idPrefix}-token-translation-blacklist-${index}`, "Skip Translate");
      translationBlacklistButton.addEventListener("click", () => {
        addTokensToTranslationBlacklist([token.raw_text ?? token.text]);
      });
      controls.appendChild(translationBlacklistButton);

      list.appendChild(row);
    });
  }

  function renderCollectionPane(targetPane, collectionName) {
    clearChildren(targetPane);
    const heading = document.createElement("div");
    heading.className = "rookieui-shell__prompt-workbench-pane-header";
    targetPane.appendChild(heading);
    appendTextElement(
      heading,
      "h6",
      "rookieui-shell__prompt-workbench-pane-title",
      collectionName === "favorites" ? "Favorites" : "History",
    );

    const toolbar = document.createElement("div");
    toolbar.className = "rookieui-shell__prompt-workbench-editor-toolbar";
    targetPane.appendChild(toolbar);

    const saveButton = createActionButton(
      `${idPrefix}-${collectionName}-save-current`,
      collectionName === "favorites" ? "Save Current Favorite" : "Save Current Prompt",
    );
    saveButton.addEventListener("click", () => {
      addCurrentPromptToCollection(collectionName);
    });
    toolbar.appendChild(saveButton);

    const clearButton = createActionButton(`${idPrefix}-${collectionName}-clear`, "Clear");
    clearButton.addEventListener("click", () => {
      mutateCollection(collectionName, "clear", {});
    });
    toolbar.appendChild(clearButton);

    const entries = collectionName === "favorites"
      ? favoritesCache.get(getActiveNamespace()) ?? []
      : historyCache.get(getActiveNamespace()) ?? [];
    const list = document.createElement("div");
    list.className = "rookieui-shell__prompt-workbench-entry-list";
    targetPane.appendChild(list);

    if (!entries.length) {
      appendTextElement(
        list,
        "p",
        "rookieui-shell__prompt-workbench-empty",
        `No ${collectionName} saved for this namespace yet.`,
      );
      return;
    }

    entries.forEach((entry, index) => {
      const row = document.createElement("div");
      row.className = "rookieui-shell__prompt-workbench-entry";
      list.appendChild(row);

      const copy = document.createElement("div");
      copy.className = "rookieui-shell__prompt-workbench-entry-copy";
      row.appendChild(copy);
      appendTextElement(copy, "strong", "rookieui-shell__prompt-workbench-entry-label", entry.label || "Saved Prompt");
      appendTextElement(copy, "p", "rookieui-shell__prompt-workbench-entry-text", entry.prompt_text);

      const controls = document.createElement("div");
      controls.className = "rookieui-shell__prompt-workbench-entry-actions";
      row.appendChild(controls);

      const applyButton = createActionButton(`${idPrefix}-${collectionName}-apply-${index}`, "Apply");
      applyButton.addEventListener("click", () => {
        applyCollectionEntry(entry);
      });
      controls.appendChild(applyButton);

      const removeButton = createActionButton(`${idPrefix}-${collectionName}-remove-${index}`, "Remove");
      removeButton.addEventListener("click", () => {
        mutateCollection(collectionName, "remove", { item_id: entry.id });
      });
      controls.appendChild(removeButton);

      if (collectionName === "favorites") {
        const upButton = createActionButton(`${idPrefix}-${collectionName}-up-${index}`, "Up");
        upButton.addEventListener("click", () => {
          mutateCollection(collectionName, "move_up", { item_id: entry.id });
        });
        controls.appendChild(upButton);
      }
    });
  }

  function renderCatalogPane() {
    clearChildren(catalogPane);
    const heading = document.createElement("div");
    heading.className = "rookieui-shell__prompt-workbench-pane-header";
    catalogPane.appendChild(heading);
    appendTextElement(heading, "h6", "rookieui-shell__prompt-workbench-pane-title", "Catalog and Quick Insert");

    const groups = Array.isArray(catalogPayload?.group_tags?.groups) ? catalogPayload.group_tags.groups : [];
    const sections = Array.isArray(catalogPayload?.prompt_library?.sections) ? catalogPayload.prompt_library.sections : [];
    const tagcompleteEntries = Array.isArray(catalogPayload?.tagcomplete?.entries) ? catalogPayload.tagcomplete.entries : [];
    const embeddings = Array.isArray(catalogPayload?.extra_networks?.embeddings) ? catalogPayload.extra_networks.embeddings : [];
    const loras = Array.isArray(catalogPayload?.extra_networks?.loras) ? catalogPayload.extra_networks.loras : [];

    const renderChipRow = (title, entries, fragmentBuilder, actionLabel = "Add") => {
      const block = document.createElement("section");
      block.className = "rookieui-shell__prompt-workbench-catalog-block";
      catalogPane.appendChild(block);
      appendTextElement(block, "h6", "rookieui-shell__prompt-workbench-pane-title", title);
      const chipGrid = document.createElement("div");
      chipGrid.className = "rookieui-shell__prompt-workbench-chip-grid";
      block.appendChild(chipGrid);
      if (!entries.length) {
        appendTextElement(
          chipGrid,
          "p",
          "rookieui-shell__prompt-workbench-empty",
          `No ${title.toLowerCase()} entries are available for this workbench profile.`,
        );
        return;
      }
      entries.forEach((entry, index) => {
        const button = createActionButton(`${idPrefix}-${title.toLowerCase().replace(/\s+/g, "-")}-${index}`, actionLabel);
        button.classList.add("rookieui-shell__prompt-workbench-chip");
        if (entry?.highlight_class) {
          button.classList.add(String(entry.highlight_class));
        }
        button.dataset.highlight = getCatalogHighlight(entry);
        if (Array.isArray(entry?.aliases) && entry.aliases.length) {
          button.title = `Aliases: ${entry.aliases.join(", ")}`;
        }
        button.textContent = String(entry?.label ?? entry?.title ?? entry?.id ?? fragmentBuilder(entry));
        button.addEventListener("click", () => {
          appendPromptFragment(fragmentBuilder(entry), {
            statusMessage: `Inserted ${String(entry?.label ?? entry?.title ?? entry?.id ?? "catalog entry")}`,
          });
        });
        chipGrid.appendChild(button);
      });
    };

    const tagcompleteBlock = document.createElement("section");
    tagcompleteBlock.className = "rookieui-shell__prompt-workbench-catalog-block";
    catalogPane.appendChild(tagcompleteBlock);
    appendTextElement(tagcompleteBlock, "h6", "rookieui-shell__prompt-workbench-pane-title", "Tagcomplete Lookup");
    const searchInput = document.createElement("input");
    searchInput.id = `${idPrefix}-tagcomplete-search`;
    searchInput.type = "search";
    searchInput.className = "rookieui-shell__input";
    searchInput.placeholder = "Search tags, aliases, or categories";
    searchInput.setAttribute("aria-label", "Search Prompt Workbench tagcomplete catalog");
    searchInput.value = catalogSearchState.query;
    searchInput.addEventListener("input", () => {
      catalogSearchState.query = String(searchInput.value ?? "");
      syncUi();
    });
    tagcompleteBlock.appendChild(searchInput);
    const query = normalizeTokenText(catalogSearchState.query).toLowerCase();
    const filteredTagcomplete = tagcompleteEntries
      .filter((entry) => {
        if (!query) {
          return true;
        }
        const haystack = [
          entry?.tag,
          entry?.label,
          entry?.category,
          ...(Array.isArray(entry?.aliases) ? entry.aliases : []),
        ]
          .map((value) => String(value ?? "").toLowerCase())
          .join(" ");
        return haystack.includes(query);
      })
      .slice(0, 24);
    renderChipRow("Tagcomplete Matches", filteredTagcomplete, (entry) => String(entry?.insert_token ?? entry?.tag ?? entry?.label ?? ""));

    groups.forEach((group, groupIndex) => {
      renderChipRow(
        String(group?.title ?? `Group ${groupIndex + 1}`),
        Array.isArray(group?.tag_entries)
          ? group.tag_entries
          : Array.isArray(group?.tags)
            ? group.tags.map((tag) => ({ id: tag, label: tag }))
            : [],
        (entry) => String(entry?.insert_token ?? entry?.tag ?? entry?.label ?? ""),
      );
    });

    sections.forEach((section, sectionIndex) => {
      const block = document.createElement("section");
      block.className = "rookieui-shell__prompt-workbench-catalog-block";
      catalogPane.appendChild(block);
      appendTextElement(
        block,
        "h6",
        "rookieui-shell__prompt-workbench-pane-title",
        String(section?.title ?? `Section ${sectionIndex + 1}`),
      );
      const list = document.createElement("div");
      list.className = "rookieui-shell__prompt-workbench-entry-list";
      block.appendChild(list);
      const entries = Array.isArray(section?.entries) ? section.entries : [];
      if (!entries.length) {
        appendTextElement(list, "p", "rookieui-shell__prompt-workbench-empty", "No prompt-library entries available.");
        return;
      }
      entries.forEach((entry, entryIndex) => {
        const row = document.createElement("div");
        row.className = "rookieui-shell__prompt-workbench-entry";
        list.appendChild(row);
        const copy = document.createElement("div");
        copy.className = "rookieui-shell__prompt-workbench-entry-copy";
        row.appendChild(copy);
        appendTextElement(copy, "strong", "rookieui-shell__prompt-workbench-entry-label", String(entry?.label ?? "Library Entry"));
        appendTextElement(copy, "p", "rookieui-shell__prompt-workbench-entry-text", String(entry?.prompt_text ?? ""));
        const controls = document.createElement("div");
        controls.className = "rookieui-shell__prompt-workbench-entry-actions";
        row.appendChild(controls);
        const appendButton = createActionButton(`${idPrefix}-library-append-${sectionIndex}-${entryIndex}`, "Append");
        appendButton.addEventListener("click", () => {
          appendPromptFragment(String(entry?.prompt_text ?? ""), {
            statusMessage: `Appended ${String(entry?.label ?? "library entry")}`,
          });
        });
        controls.appendChild(appendButton);
        const replaceButton = createActionButton(`${idPrefix}-library-replace-${sectionIndex}-${entryIndex}`, "Replace");
        replaceButton.addEventListener("click", () => {
          appendPromptFragment(String(entry?.prompt_text ?? ""), {
            replace: true,
            statusMessage: `Replaced prompt with ${String(entry?.label ?? "library entry")}`,
          });
        });
        controls.appendChild(replaceButton);
      });
    });

    renderChipRow("Embeddings", embeddings, (entry) => String(entry?.insert_token ?? entry?.id ?? ""), "Insert");
    renderChipRow("LoRAs", loras, (entry) => String(entry?.insert_token ?? entry?.id ?? ""), "Insert");
  }

  function renderAssistPane() {
    clearChildren(assistPane);
    const heading = document.createElement("div");
    heading.className = "rookieui-shell__prompt-workbench-pane-header";
    assistPane.appendChild(heading);
    appendTextElement(heading, "h6", "rookieui-shell__prompt-workbench-pane-title", "AI Assist and Delivery");

    const settingsGrid = document.createElement("div");
    settingsGrid.className = "rookieui-shell__prompt-workbench-format-grid";
    assistPane.appendChild(settingsGrid);

    const renderField = (label, fieldNode) => {
      const row = document.createElement("label");
      row.className = "rookieui-shell__prompt-workbench-rule rookieui-shell__prompt-workbench-rule--stacked";
      appendTextElement(row, "span", "rookieui-shell__prompt-workbench-rule-label", label);
      row.appendChild(fieldNode);
      settingsGrid.appendChild(row);
      return fieldNode;
    };

    const languageSelect = document.createElement("select");
    languageSelect.id = `${idPrefix}-assist-language`;
    languageSelect.className = "rookieui-shell__input";
    (languageOptions.length ? languageOptions : [{ code: "en", title: "English" }]).forEach((entry) => {
      const option = document.createElement("option");
      option.value = String(entry?.code ?? "en");
      option.textContent = `${String(entry?.code ?? "en")} - ${String(entry?.title ?? "English")}`;
      languageSelect.appendChild(option);
    });
    languageSelect.value = String(configState?.language ?? "en");
    languageSelect.addEventListener("change", () => {
      configState.language = String(languageSelect.value ?? "en").trim() || "en";
      queueConfigPersist();
    });
    renderField("Language", languageSelect);

    const themeSelect = document.createElement("select");
    themeSelect.id = `${idPrefix}-assist-theme`;
    themeSelect.className = "rookieui-shell__input";
    themeSelect.setAttribute("aria-label", "Prompt Workbench theme style");
    (themeStyleOptions.length
      ? themeStyleOptions
      : [{ id: "rookieui_classic", title: "RookieUI Classic", summary: "" }]).forEach((entry) => {
      const option = document.createElement("option");
      option.value = String(entry?.id ?? "rookieui_classic");
      option.textContent = String(entry?.title ?? entry?.id ?? "RookieUI Classic");
      themeSelect.appendChild(option);
    });
    themeSelect.value = String(configState?.theme_style ?? "rookieui_classic");
    themeSelect.addEventListener("change", () => {
      configState.theme_style = String(themeSelect.value ?? "rookieui_classic").trim() || "rookieui_classic";
      queueConfigPersist();
    });
    renderField("Theme Style", themeSelect);

    const providerSelect = document.createElement("select");
    providerSelect.id = `${idPrefix}-assist-provider`;
    providerSelect.className = "rookieui-shell__input rookieui-shell__prompt-workbench-provider-select";
    providerSelect.setAttribute("aria-label", "Prompt Workbench AI assist provider");
    const providerPlaceholder = document.createElement("option");
    providerPlaceholder.value = "";
    providerPlaceholder.textContent = "Select AI assist provider";
    providerSelect.appendChild(providerPlaceholder);
    getAiAssistProviders().forEach((entry) => {
      const option = document.createElement("option");
      option.value = String(entry?.provider_id ?? "");
      option.textContent = String(entry?.title ?? entry?.provider_id ?? "");
      providerSelect.appendChild(option);
    });
    providerSelect.value = String(configState?.ai_assist?.default_provider ?? "");
    providerSelect.addEventListener("change", () => {
      persistAiAssistProviderSelection(providerSelect.value);
    });
    renderField("Provider", providerSelect);

    const providerDetails = getAiAssistProviders().find(
      (entry) => String(entry?.provider_id ?? "") === String(configState?.ai_assist?.default_provider ?? ""),
    );
    const providerFields = Array.isArray(providerDetails?.config_fields) ? providerDetails.config_fields : [];
    providerFields.forEach((fieldSpec) => {
      const fieldKey = String(fieldSpec?.key ?? "").trim();
      if (!fieldKey) {
        return;
      }
      const providerStore = {
        ...(configState.ai_assist?.providers ?? {}),
      };
      const providerConfig = {
        ...(providerStore[providerSelect.value] ?? {}),
      };
      const input = document.createElement("input");
      input.type = fieldSpec?.secret ? "password" : "text";
      input.id = `${idPrefix}-assist-config-${fieldKey}`;
      input.className = "rookieui-shell__input";
      input.placeholder = String(fieldSpec?.placeholder ?? "");
      input.value = String(providerConfig[fieldKey] ?? fieldSpec?.default ?? "");
      input.addEventListener("change", () => {
        const selectedProviderId = String(configState?.ai_assist?.default_provider ?? "").trim();
        if (!selectedProviderId) {
          return;
        }
        const nextProviders = {
          ...(configState.ai_assist?.providers ?? {}),
          [selectedProviderId]: {
            ...(configState.ai_assist?.providers?.[selectedProviderId] ?? {}),
            [fieldKey]: input.value,
          },
        };
        configState.ai_assist = {
          ...(configState.ai_assist ?? {}),
          providers: nextProviders,
          instruction_preset: String(configState.ai_assist?.instruction_preset ?? ""),
        };
        queueConfigPersist();
      });
      renderField(String(fieldSpec?.title ?? fieldKey), input);
    });

    const presetBlock = document.createElement("section");
    presetBlock.className = "rookieui-shell__prompt-workbench-catalog-block";
    assistPane.appendChild(presetBlock);
    appendTextElement(presetBlock, "h6", "rookieui-shell__prompt-workbench-pane-title", "Instruction Preset");

    const presetInput = document.createElement("textarea");
    presetInput.id = `${idPrefix}-assist-preset`;
    presetInput.className = "rookieui-shell__textarea";
    presetInput.rows = 4;
    presetInput.value = String(configState?.ai_assist?.instruction_preset ?? "");
    presetInput.addEventListener("change", () => {
      configState.ai_assist = {
        ...(configState.ai_assist ?? {}),
        instruction_preset: presetInput.value,
        providers: configState.ai_assist?.providers ?? {},
      };
      queueConfigPersist();
    });
    presetBlock.appendChild(presetInput);

    const promptBlock = document.createElement("section");
    promptBlock.className = "rookieui-shell__prompt-workbench-catalog-block";
    assistPane.appendChild(promptBlock);
    appendTextElement(promptBlock, "h6", "rookieui-shell__prompt-workbench-pane-title", "Image Description");

    const descriptionInput = document.createElement("textarea");
    descriptionInput.id = `${idPrefix}-assist-description`;
    descriptionInput.className = "rookieui-shell__textarea";
    descriptionInput.rows = 4;
    descriptionInput.placeholder = "Describe the image you want as prompt input";
    descriptionInput.value = String(assistState.imageDescription ?? "");
    descriptionInput.addEventListener("input", () => {
      assistState.imageDescription = descriptionInput.value;
    });
    promptBlock.appendChild(descriptionInput);

    const toolbar = document.createElement("div");
    toolbar.className = "rookieui-shell__prompt-workbench-editor-toolbar";
    assistPane.appendChild(toolbar);

    const generateButton = createActionButton(
      `${idPrefix}-assist-generate`,
      assistState.generating ? "Generating..." : "Generate Prompt",
    );
    generateButton.disabled = assistState.generating;
    generateButton.addEventListener("click", () => {
      requestAiAssistGeneration();
    });
    toolbar.appendChild(generateButton);

    const applyButton = createActionButton(`${idPrefix}-assist-apply`, "Apply Result");
    applyButton.disabled = !String(assistState.generatedPrompt ?? "").trim();
    applyButton.addEventListener("click", () => {
      applyPromptTextToInput(assistState.generatedPrompt, {
        updateEditor: true,
        statusMessage: "Applied AI Assist prompt result",
      });
    });
    toolbar.appendChild(applyButton);

    const resultBlock = document.createElement("section");
    resultBlock.className = "rookieui-shell__prompt-workbench-catalog-block";
    assistPane.appendChild(resultBlock);
    appendTextElement(resultBlock, "h6", "rookieui-shell__prompt-workbench-pane-title", "Generated Prompt");
    const resultInput = document.createElement("textarea");
    resultInput.id = `${idPrefix}-assist-result`;
    resultInput.className = "rookieui-shell__textarea";
    resultInput.rows = 4;
    resultInput.value = String(assistState.generatedPrompt ?? "");
    resultInput.addEventListener("input", () => {
      assistState.generatedPrompt = resultInput.value;
    });
    resultBlock.appendChild(resultInput);
  }

  async function exportWorkbenchJson(outputNode) {
    importExportState.busy = true;
    syncUi();
    const result = await bootstrapState?.exportPromptWorkbenchRequest?.();
    const payload = result?.data?.export ?? result?.data ?? {};
    importExportState.jsonText = JSON.stringify(payload, null, 2);
    if (outputNode) {
      outputNode.value = importExportState.jsonText;
    }
    importExportState.busy = false;
    updateStatus(result?.ok === false ? "Prompt Workbench export used fallback data" : t("exportReady"));
    syncUi();
  }

  async function importWorkbenchJson(inputNode) {
    const rawText = String(inputNode?.value ?? importExportState.jsonText ?? "").trim();
    let payload = null;
    try {
      payload = JSON.parse(rawText);
    } catch (_error) {
      updateStatus(t("importInvalidJson"));
      return;
    }
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      updateStatus(t("importInvalidJson"));
      return;
    }
    importExportState.busy = true;
    syncUi();
    const result = await bootstrapState?.importPromptWorkbenchRequest?.(payload);
    importExportState.busy = false;
    updateStatus(result?.ok === false ? "Prompt Workbench import saved with fallback semantics" : t("importReady"));
    resourcesReadyPromise = null;
    resourcesLoaded = false;
    await ensureResourcesLoaded({
      statusMessage: result?.ok === false ? "Prompt Workbench import saved with fallback semantics" : t("importReady"),
    });
    syncUi();
  }

  function renderFormatPane() {
    clearChildren(formatPane);
    const heading = document.createElement("div");
    heading.className = "rookieui-shell__prompt-workbench-pane-header";
    formatPane.appendChild(heading);
    appendTextElement(heading, "h6", "rookieui-shell__prompt-workbench-pane-title", t("formattingAndBlacklist"));

    const ruleGrid = document.createElement("div");
    ruleGrid.className = "rookieui-shell__prompt-workbench-format-grid";
    formatPane.appendChild(ruleGrid);

    const createRuleToggle = (key, label) => {
      const row = document.createElement("label");
      row.className = "rookieui-shell__prompt-workbench-rule";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = Boolean(configState?.formatting_rules?.[key]);
      input.addEventListener("change", () => {
        configState.formatting_rules = {
          ...configState.formatting_rules,
          [key]: input.checked,
        };
        queueConfigPersist();
      });
      row.appendChild(input);
      appendTextElement(row, "span", "rookieui-shell__prompt-workbench-rule-label", label);
      ruleGrid.appendChild(row);
    };

    createRuleToggle("dedupe_commas", "Remove duplicate prompt entries");
    createRuleToggle("normalize_spacing", "Normalize spacing and comma separators");
    createRuleToggle("trim_outer_whitespace", "Trim outer whitespace");

    appendTextElement(formatPane, "h6", "rookieui-shell__prompt-workbench-pane-title", "Workbench Preferences");

    const settingsGrid = document.createElement("div");
    settingsGrid.className = "rookieui-shell__prompt-workbench-format-grid";
    formatPane.appendChild(settingsGrid);

    const createPreferenceToggle = (key, label) => {
      const row = document.createElement("label");
      row.className = "rookieui-shell__prompt-workbench-rule";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.id = `${idPrefix}-pref-${key.replace(/_/g, "-")}`;
      input.checked = configState?.ui_preferences?.[key] !== false;
      if (key === "default_open") {
        input.checked = Boolean(configState?.ui_preferences?.default_open);
      }
      input.addEventListener("change", () => {
        configState.ui_preferences = {
          ...(configState.ui_preferences ?? {}),
          [key]: input.checked,
        };
        const state = getActiveState();
        state.active_panel = resolveVisiblePanel(state.active_panel);
        queueConfigPersist();
        syncUi();
      });
      row.appendChild(input);
      appendTextElement(row, "span", "rookieui-shell__prompt-workbench-rule-label", label);
      settingsGrid.appendChild(row);
    };

    createPreferenceToggle("default_open", "Open Prompt Workbench by default");
    createPreferenceToggle("show_history", "Show history panel");
    createPreferenceToggle("show_favorites", "Show favorites panel");

    const preferredPanelRow = document.createElement("label");
    preferredPanelRow.className = "rookieui-shell__prompt-workbench-rule rookieui-shell__prompt-workbench-rule--stacked";
    appendTextElement(preferredPanelRow, "span", "rookieui-shell__prompt-workbench-rule-label", "Preferred panel when opening");
    const preferredPanelSelect = document.createElement("select");
    preferredPanelSelect.id = `${idPrefix}-pref-preferred-panel`;
    preferredPanelSelect.className = "rookieui-shell__input";
    preferredPanelSelect.setAttribute("aria-label", "Prompt Workbench preferred panel");
    ["editor", "history", "favorites", "catalog", "assist", "format"].forEach((panelId) => {
      const option = document.createElement("option");
      option.value = panelId;
      option.textContent = panelId.charAt(0).toUpperCase() + panelId.slice(1);
      option.disabled = !isPanelVisible(panelId);
      preferredPanelSelect.appendChild(option);
    });
    preferredPanelSelect.value = resolveVisiblePanel(configState?.ui_preferences?.preferred_panel ?? "editor");
    preferredPanelSelect.addEventListener("change", () => {
      configState.ui_preferences = {
        ...(configState.ui_preferences ?? {}),
        preferred_panel: preferredPanelSelect.value,
      };
      queueConfigPersist();
      syncUi();
    });
    preferredPanelRow.appendChild(preferredPanelSelect);
    settingsGrid.appendChild(preferredPanelRow);

    const toolbar = document.createElement("div");
    toolbar.className = "rookieui-shell__prompt-workbench-editor-toolbar";
    formatPane.appendChild(toolbar);

    const applyFormattingButton = createActionButton(`${idPrefix}-apply-formatting`, "Apply Formatting");
    applyFormattingButton.addEventListener("click", () => {
      const formatted = formatPromptText(getActiveState().draft_prompt || getActiveInput()?.value, configState.formatting_rules);
      applyPromptTextToInput(formatted, {
        updateEditor: true,
        statusMessage: "Applied Prompt Workbench formatting rules",
      });
    });
    toolbar.appendChild(applyFormattingButton);

    const applyBlacklistButton = createActionButton(`${idPrefix}-apply-blacklist`, "Apply Blacklist");
    applyBlacklistButton.addEventListener("click", () => {
      applyBlacklistFilter();
    });
    toolbar.appendChild(applyBlacklistButton);

    const importExportBlock = document.createElement("section");
    importExportBlock.className = "rookieui-shell__prompt-workbench-catalog-block";
    formatPane.appendChild(importExportBlock);
    appendTextElement(importExportBlock, "h6", "rookieui-shell__prompt-workbench-pane-title", t("importExport"));
    const importExportInput = document.createElement("textarea");
    importExportInput.id = `${idPrefix}-import-export-json`;
    importExportInput.className = "rookieui-shell__textarea";
    importExportInput.rows = 6;
    importExportInput.value = importExportState.jsonText;
    importExportInput.addEventListener("input", () => {
      importExportState.jsonText = importExportInput.value;
    });
    importExportBlock.appendChild(importExportInput);

    const importExportToolbar = document.createElement("div");
    importExportToolbar.className = "rookieui-shell__prompt-workbench-editor-toolbar";
    importExportBlock.appendChild(importExportToolbar);
    const exportButton = createActionButton(`${idPrefix}-export-json`, t("exportJson"));
    exportButton.disabled = importExportState.busy;
    exportButton.addEventListener("click", () => {
      void exportWorkbenchJson(importExportInput);
    });
    importExportToolbar.appendChild(exportButton);

    const importButton = createActionButton(`${idPrefix}-import-json`, t("importJson"));
    importButton.disabled = importExportState.busy;
    importButton.addEventListener("click", () => {
      void importWorkbenchJson(importExportInput);
    });
    importExportToolbar.appendChild(importButton);

    const blacklistHeading = appendTextElement(
      formatPane,
      "p",
      "rookieui-shell__prompt-workbench-detail",
      blacklistState.enabled ? "Blacklist entries" : "Blacklist disabled",
    );
    blacklistHeading.id = `${idPrefix}-blacklist-heading`;

    const list = document.createElement("div");
    list.className = "rookieui-shell__prompt-workbench-entry-list";
    formatPane.appendChild(list);

    if (!(blacklistState.entries ?? []).length) {
      appendTextElement(list, "p", "rookieui-shell__prompt-workbench-empty", "No blacklist entries configured.");
    } else {
      (blacklistState.entries ?? []).forEach((entry, index) => {
        const row = document.createElement("div");
        row.className = "rookieui-shell__prompt-workbench-entry";
        list.appendChild(row);
        appendTextElement(row, "strong", "rookieui-shell__prompt-workbench-entry-label", entry);
        const controls = document.createElement("div");
        controls.className = "rookieui-shell__prompt-workbench-entry-actions";
        row.appendChild(controls);
        const removeButton = createActionButton(`${idPrefix}-blacklist-remove-${index}`, "Remove");
        removeButton.addEventListener("click", () => {
          removeBlacklistEntry(entry);
        });
        controls.appendChild(removeButton);
      });
    }

    const translationBlacklistHeading = appendTextElement(
      formatPane,
      "p",
      "rookieui-shell__prompt-workbench-detail",
      "Translation blacklist entries",
    );
    translationBlacklistHeading.id = `${idPrefix}-translation-blacklist-heading`;

    const translationList = document.createElement("div");
    translationList.className = "rookieui-shell__prompt-workbench-entry-list";
    formatPane.appendChild(translationList);

    if (!(blacklistState.translation_entries ?? []).length) {
      appendTextElement(translationList, "p", "rookieui-shell__prompt-workbench-empty", "No translation blacklist entries configured.");
      return;
    }

    (blacklistState.translation_entries ?? []).forEach((entry, index) => {
      const row = document.createElement("div");
      row.className = "rookieui-shell__prompt-workbench-entry";
      translationList.appendChild(row);
      appendTextElement(row, "strong", "rookieui-shell__prompt-workbench-entry-label", entry);
      const controls = document.createElement("div");
      controls.className = "rookieui-shell__prompt-workbench-entry-actions";
      row.appendChild(controls);
      const removeButton = createActionButton(`${idPrefix}-translation-blacklist-remove-${index}`, "Remove");
      removeButton.addEventListener("click", () => {
        removeTranslationBlacklistEntry(entry);
      });
      controls.appendChild(removeButton);
    });
  }

  function syncUi() {
    const state = getActiveState();
    state.active_panel = resolveVisiblePanel(state.active_panel);
    const historyItems = historyCache.get(getActiveNamespace()) ?? [];
    const favoriteItems = favoritesCache.get(getActiveNamespace()) ?? [];
    const language = String(configState?.language ?? "en").trim() || "en";
    const translationSurface = providersPayload?.surfaces?.translation ?? null;
    const shippedProviders = Array.isArray(translationSurface?.shipped_provider_ids)
      ? translationSurface.shipped_provider_ids.length
      : 0;
    const groupCount = Array.isArray(catalogPayload?.group_tags?.groups) ? catalogPayload.group_tags.groups.length : 0;
    const libraryCount = Array.isArray(catalogPayload?.prompt_library?.sections)
      ? catalogPayload.prompt_library.sections.length
      : 0;
    const extraNetworkCount =
      (Array.isArray(catalogPayload?.extra_networks?.embeddings) ? catalogPayload.extra_networks.embeddings.length : 0) +
      (Array.isArray(catalogPayload?.extra_networks?.loras) ? catalogPayload.extra_networks.loras.length : 0);

    setBodyOpen(readPreferredOpenState());
    tabButtons.forEach((button, scope) => {
      button.dataset.active = String(scope === activeScope);
      button.setAttribute("aria-pressed", String(scope === activeScope));
    });
    panelButtons.forEach((button, panelId) => {
      button.hidden = !isPanelVisible(panelId);
      button.dataset.active = String(panelId === state.active_panel);
      button.setAttribute("aria-pressed", String(panelId === state.active_panel));
    });

    editorPane.hidden = state.active_panel !== "editor";
    historyPane.hidden = state.active_panel !== "history";
    favoritesPane.hidden = state.active_panel !== "favorites";
    catalogPane.hidden = state.active_panel !== "catalog";
    assistPane.hidden = state.active_panel !== "assist";
    formatPane.hidden = state.active_panel !== "format";

    updateShellThemeStyle();
    setText(summaryNodes.state, state.workbench_open ? "Persisted open" : "Collapsed");
    const assistShippedProviders = Array.isArray(providersPayload?.surfaces?.ai_assist?.shipped_provider_ids)
      ? providersPayload.surfaces.ai_assist.shipped_provider_ids.length
      : 0;
    setText(summaryNodes.providers, resourcesLoaded ? `${shippedProviders} translate / ${assistShippedProviders} assist / ${language}` : "Lazy");
    setText(
      summaryNodes.catalogs,
      resourcesLoaded ? `${groupCount} groups / ${libraryCount} sections / ${extraNetworkCount} networks` : "Lazy",
    );
    setText(summaryNodes.history, `${historyItems.length} entries`);
    setText(summaryNodes.favorites, `${favoriteItems.length} entries`);
    setText(summaryNodes.blacklist, blacklistState.enabled ? `${(blacklistState.entries ?? []).length} blocked` : "Disabled");

    setText(detailNodes.scope, `${activeScope === "prompt" ? "Prompt" : "Negative Prompt"} namespace: ${getActiveNamespace()}`);
    setText(detailNodes.draft, `Saved draft: ${countPromptUnits(state.draft_prompt)} prompt units`);
    setText(detailNodes.panel, `Active panel: ${state.active_panel}`);

    renderEditorPane();
    renderCollectionPane(historyPane, "history");
    renderCollectionPane(favoritesPane, "favorites");
    renderCatalogPane();
    renderAssistPane();
    renderFormatPane();
  }

  async function ensureStateLoaded() {
    if (stateReadyPromise) {
      return stateReadyPromise;
    }
    const namespacesToLoad = Object.values(namespaceMap).filter(Boolean);
    stateReadyPromise = Promise.all(
      namespacesToLoad.map(async (namespace) => {
        const result = await bootstrapState?.fetchPromptWorkbenchStateRequest?.(namespace);
        const nextState = normalizeStatePayload(
          namespace,
          result?.data?.state ?? { draft_prompt: getNamespaceInput(namespace)?.value ?? "" },
        );
        if (!nextState.draft_prompt) {
          nextState.draft_prompt = String(getNamespaceInput(namespace)?.value ?? "");
        }
        stateCache.set(namespace, nextState);
        editorCache.set(namespace, parsePromptTokens(nextState.draft_prompt, { scope: activeScope }));
      }),
    )
      .then(() => {
        const promptState = stateCache.get(namespaceMap.prompt);
        const negativeState = stateCache.get(namespaceMap.negative);
        if (!promptState?.workbench_open && negativeState?.workbench_open) {
          activeScope = "negative";
        }
      })
      .finally(() => {
        syncUi();
      });
    return stateReadyPromise;
  }

  async function ensureResourcesLoaded({ statusMessage = "Prompt Workbench resources loaded" } = {}) {
    if (resourcesReadyPromise) {
      return resourcesReadyPromise;
    }
    resourcesReadyPromise = Promise.all([
      bootstrapState?.fetchPromptWorkbenchProvidersRequest?.(),
      bootstrapState?.fetchPromptWorkbenchCatalogRequest?.(configState?.language ?? "en"),
      bootstrapState?.fetchPromptWorkbenchHistoryRequest?.(namespaceMap.prompt),
      bootstrapState?.fetchPromptWorkbenchHistoryRequest?.(namespaceMap.negative),
      bootstrapState?.fetchPromptWorkbenchFavoritesRequest?.(namespaceMap.prompt),
      bootstrapState?.fetchPromptWorkbenchFavoritesRequest?.(namespaceMap.negative),
      bootstrapState?.fetchPromptWorkbenchBlacklistRequest?.(),
    ])
      .then(
        ([
          providersResult,
          catalogResult,
          promptHistory,
          negativeHistory,
          promptFavorites,
          negativeFavorites,
          blacklistResult,
        ]) => {
          providersPayload = providersResult?.data ?? null;
          catalogPayload = catalogResult?.data ?? null;
          historyCache.set(
            namespaceMap.prompt,
            Array.isArray(promptHistory?.data?.items) ? promptHistory.data.items.map(normalizePromptEntry) : [],
          );
          historyCache.set(
            namespaceMap.negative,
            Array.isArray(negativeHistory?.data?.items) ? negativeHistory.data.items.map(normalizePromptEntry) : [],
          );
          favoritesCache.set(
            namespaceMap.prompt,
            Array.isArray(promptFavorites?.data?.items) ? promptFavorites.data.items.map(normalizePromptEntry) : [],
          );
          favoritesCache.set(
            namespaceMap.negative,
            Array.isArray(negativeFavorites?.data?.items) ? negativeFavorites.data.items.map(normalizePromptEntry) : [],
          );
          if (blacklistResult?.data?.blacklist) {
            Object.assign(blacklistState, blacklistResult.data.blacklist);
          }
          resourcesLoaded = true;
          updateStatus(statusMessage);
        },
      )
      .catch(() => {
        updateStatus("Prompt Workbench resources are using fallback data");
      })
      .finally(() => {
        syncUi();
      });
    return resourcesReadyPromise;
  }

  toggleButton.addEventListener("click", () => {
    void ensureStateLoaded().then(async () => {
      const state = getActiveState();
      state.workbench_open = !state.workbench_open;
      queueStatePersist();
      syncUi();
      if (state.workbench_open) {
        await ensureResourcesLoaded();
        const preferredPanel = resolveVisiblePanel(configState?.ui_preferences?.preferred_panel ?? state.active_panel);
        if (preferredPanel !== state.active_panel) {
          state.active_panel = preferredPanel;
          queueStatePersist();
          syncUi();
        }
        onStatusMessage?.("Opened Prompt Workbench");
      } else {
        onStatusMessage?.("Collapsed Prompt Workbench");
      }
    });
  });

  function shouldIgnoreWorkbenchHotkey(event) {
    const target = event?.target;
    if (!target || !shell.contains(target)) {
      return true;
    }
    const tagName = String(target.tagName ?? "").toLowerCase();
    if (["input", "select", "textarea"].includes(tagName)) {
      return true;
    }
    return Boolean(target.isContentEditable);
  }

  shell.addEventListener("keydown", (event) => {
    if (shouldIgnoreWorkbenchHotkey(event)) {
      return;
    }
    const isModifier = Boolean(event.ctrlKey || event.metaKey);
    if (event.key === "Delete") {
      event.preventDefault();
      mutateSelectedTokens("delete");
      return;
    }
    if (isModifier && String(event.key).toLowerCase() === "c") {
      event.preventDefault();
      mutateSelectedTokens("copy");
      return;
    }
    if (isModifier && String(event.key).toLowerCase() === "t") {
      event.preventDefault();
      mutateSelectedTokens("translate");
    }
  });

  Object.entries(namespaceMap).forEach(([scope, namespace]) => {
    const input = inputMap[scope];
    if (!input || !namespace) {
      return;
    }
    input.addEventListener("input", () => {
      const cachedState =
        stateCache.get(namespace) ?? normalizeStatePayload(namespace, { draft_prompt: String(input.value ?? "") });
      cachedState.draft_prompt = String(input.value ?? "");
      stateCache.set(namespace, cachedState);
      const nextTokens = parsePromptTokens(cachedState.draft_prompt, { scope });
      editorCache.set(namespace, nextTokens);
      queueAutoHistoryCapture(namespace, scope, cachedState.draft_prompt, nextTokens);
      queueStatePersist(namespace);
      if (scope === activeScope) {
        syncUi();
      }
    });
  });

  void ensureStateLoaded();
  syncUi();
  return {
    element: shell,
    async openWorkbench() {
      await ensureStateLoaded();
      const state = getActiveState();
      if (!state.workbench_open) {
        state.workbench_open = true;
        queueStatePersist();
      }
      await ensureResourcesLoaded();
      syncUi();
    },
  };
}
