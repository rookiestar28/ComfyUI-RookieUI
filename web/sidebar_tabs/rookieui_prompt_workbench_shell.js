import {
  INLINE_TOOLBAR_ICONS,
  PROMPT_WORKBENCH_LANGUAGE_SYNC_EVENT,
  clampOverlayValue,
  computeLanguageSelectorPlacement,
  createWorkbenchLanguageSupport,
  formatLanguageOptionLabel,
  getViewportSize,
} from "./prompt_workbench/rookieui_prompt_workbench_i18n.js";
import {
  adjustPromptTokenWeight,
  buildCollectionItem,
  buildPromptTextFromTokens,
  clearChildren,
  countPromptUnits,
  createToken,
  formatPromptText,
  normalizeDomIdPart,
  normalizePromptEntry,
  normalizeStatePayload,
  normalizeTokenText,
  parsePromptTokens,
  serializeTokenPayload,
  serializeTokenPayloads,
  setText,
  updateTokenText,
} from "./prompt_workbench/rookieui_prompt_workbench_tokens.js";
import {
  normalizeGroupTagGroups,
  renderPromptWorkbenchCatalogPane,
} from "./prompt_workbench/rookieui_prompt_workbench_catalog.js";
import { createProviderConfigInput } from "./prompt_workbench/rookieui_prompt_workbench_provider_fields.js";
import { createPromptWorkbenchLifecycle } from "./prompt_workbench/rookieui_prompt_workbench_lifecycle.js";
let promptWorkbenchInstanceSequence = 0;

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
  fixedScope = "",
} = {}) {
  const normalizedFixedScope = fixedScope === "prompt" || fixedScope === "negative" ? fixedScope : "";
  const shell = document.createElement("section");
  shell.id = `${idPrefix}-section`;
  shell.className = "rookieui-shell__prompt-workbench rookieui-shell__prompt-workbench-card-root";
  if (normalizedFixedScope) {
    shell.classList.add("rookieui-shell__prompt-workbench--inline");
  }
  shell.dataset.layout = normalizedFixedScope ? "prompt_all_in_one_inline" : "prompt_all_in_one";
  shell.dataset.scopeMode = normalizedFixedScope ? "fixed" : "paired";
  if (normalizedFixedScope) {
    shell.dataset.fixedScope = normalizedFixedScope;
  }
  shell.tabIndex = -1;
  parent.appendChild(shell);

  const configState = structuredClone(bootstrapState?.promptWorkbench?.config ?? {});
  configState.ui_preferences = configState.ui_preferences ?? {};
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
  const languageSyncSourceId = `${idPrefix}-${++promptWorkbenchInstanceSequence}`;
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
  let activeScope = normalizedFixedScope || "prompt";
  let activeSecondaryPopover = "";
  let languageSelectorOpen = false;
  let resourcesLoaded = false;
  const lifecycle = createPromptWorkbenchLifecycle();
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
  const languageSupport = createWorkbenchLanguageSupport(languageOptions);
  const getLanguageOptions = languageSupport.getLanguageOptions;
  const normalizeLanguageCode = languageSupport.normalizeLanguageCode;
  const t = (key) => languageSupport.translate(configState?.language ?? "en", key);
  const text = (key, replacements = {}) => languageSupport.format(configState?.language ?? "en", key, replacements);

  const header = document.createElement("div");
  header.className = "rookieui-shell__prompt-workbench-header";
  header.dataset.pwUi = "prompt-card-header";
  shell.appendChild(header);

  const headerCopy = document.createElement("div");
  headerCopy.className = "rookieui-shell__prompt-workbench-copy";
  header.appendChild(headerCopy);
  const titleNode = appendTextElement(headerCopy, "h5", "rookieui-shell__prompt-workbench-title", t("title"));
  const subtitleNode = appendTextElement(
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
  toggleButton.setAttribute("aria-controls", `${idPrefix}-body`);
  headerActions.appendChild(toggleButton);

  const inlineToolbarNodes = {
    counter: null,
    language: null,
    historyButton: null,
    favoritesButton: null,
    settingsButton: null,
    settingsHoverBox: null,
    appendButton: null,
    keywordInput: null,
    languageSelector: null,
  };

  const applyIconButtonLabel = (button, icon, label) => {
    button.textContent = icon;
    button.setAttribute("aria-label", label);
    button.setAttribute("title", label);
  };

  const createInlineToolbarButton = (buttonId, icon, label, uiName, handler) => {
    const button = createActionButton(`${idPrefix}-${buttonId}`, icon);
    button.classList.add("rookieui-shell__prompt-workbench-inline-tool");
    button.dataset.pwUi = uiName;
    applyIconButtonLabel(button, icon, label);
    button.addEventListener("click", handler);
    headerActions.appendChild(button);
    return button;
  };

  const openInlinePanel = (panelId, surface = "") => {
    activeSecondaryPopover = surface;
    const state = getActiveState();
    state.workbench_open = true;
    state.active_panel = panelId;
    queueStatePersist();
    syncUi();
  };

  const createInlineSettingsHoverBox = () => {
    const box = document.createElement("div");
    box.id = `${idPrefix}-inline-settings-hoverbox`;
    box.className = "rookieui-shell__prompt-workbench-inline-settings-box";
    box.dataset.pwUi = "inline-settings-hoverbox";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-label", t("preferences"));

    const actionRow = document.createElement("div");
    actionRow.className = "rookieui-shell__prompt-workbench-inline-settings-row";
    box.appendChild(actionRow);

    const addDetailButton = (buttonId, icon, label, panelId, statusMessage = "") => {
      const button = createActionButton(`${idPrefix}-inline-settings-${buttonId}`, icon);
      button.classList.add("rookieui-shell__prompt-workbench-inline-setting-detail");
      button.dataset.pwUi = `inline-settings-${buttonId}`;
      button.setAttribute("aria-label", label);
      button.setAttribute("title", label);
      button.addEventListener("click", () => {
        openInlinePanel(panelId, panelId === "format" ? "settings" : "");
        if (statusMessage) {
          updateStatus(statusMessage);
        }
      });
      actionRow.appendChild(button);
      return button;
    };

    addDetailButton("api", INLINE_TOOLBAR_ICONS.api, "Translation API settings", "assist");
    addDetailButton("format", INLINE_TOOLBAR_ICONS.format, "Prompt format settings", "format");
    addDetailButton("blacklist", INLINE_TOOLBAR_ICONS.blacklist, "Keywords blacklist", "format");
    addDetailButton("hotkey", INLINE_TOOLBAR_ICONS.hotkey, "Hotkey settings", "format", "Prompt Workbench hotkeys are scoped to the active editor");
    addDetailButton("theme", INLINE_TOOLBAR_ICONS.theme, "Theme settings", "assist");
    addDetailButton("about", INLINE_TOOLBAR_ICONS.info, "Prompt Workbench details", "assist", "Prompt Workbench inline prompt-all-in-one parity controls");

    const optionRow = document.createElement("div");
    optionRow.className = "rookieui-shell__prompt-workbench-inline-settings-row";
    box.appendChild(optionRow);

    const addOptionToggle = (key, icon, label, defaultChecked = false) => {
      const labelNode = document.createElement("label");
      labelNode.className = "rookieui-shell__prompt-workbench-inline-setting-toggle";
      labelNode.setAttribute("title", label);
      labelNode.setAttribute("aria-label", label);
      const input = document.createElement("input");
      input.type = "checkbox";
      input.id = `${idPrefix}-inline-settings-${key.replace(/_/g, "-")}`;
      input.checked = Boolean(configState?.ui_preferences?.[key] ?? defaultChecked);
      input.addEventListener("change", () => {
        configState.ui_preferences = {
          ...(configState.ui_preferences ?? {}),
          [key]: input.checked,
        };
        queueConfigPersist();
      });
      labelNode.appendChild(input);
      appendTextElement(labelNode, "span", "rookieui-shell__prompt-workbench-inline-setting-icon", icon);
      optionRow.appendChild(labelNode);
      return input;
    };

    addOptionToggle("auto_translate", INLINE_TOOLBAR_ICONS.autoTranslate, "Auto translate new keywords");
    addOptionToggle("enable_tooltip", INLINE_TOOLBAR_ICONS.tooltip, "Enable keyword tooltips", true);

    const autoInputLabel = document.createElement("label");
    autoInputLabel.className = "rookieui-shell__prompt-workbench-inline-setting-select";
    autoInputLabel.setAttribute("title", "Auto input prompt after page load");
    appendTextElement(autoInputLabel, "span", "rookieui-shell__prompt-workbench-inline-setting-icon", INLINE_TOOLBAR_ICONS.autoInput);
    const autoInputSelect = document.createElement("select");
    autoInputSelect.id = `${idPrefix}-inline-settings-auto-input`;
    autoInputSelect.setAttribute("aria-label", "Auto input prompt after page load");
    [
      ["disabled", "Auto input: disabled"],
      ["last", "Last input prompt"],
    ].forEach(([value, label]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      autoInputSelect.appendChild(option);
    });
    autoInputSelect.value = String(configState?.ui_preferences?.auto_input_prompt ?? "disabled");
    autoInputSelect.addEventListener("change", () => {
      configState.ui_preferences = {
        ...(configState.ui_preferences ?? {}),
        auto_input_prompt: autoInputSelect.value,
      };
      queueConfigPersist();
    });
    autoInputLabel.appendChild(autoInputSelect);
    box.appendChild(autoInputLabel);

    return box;
  };

  const createInlineKeywordInput = () => {
    const input = document.createElement("textarea");
    input.id = `${idPrefix}-inline-keyword-input`;
    input.className = "rookieui-shell__prompt-workbench-inline-keyword-input";
    input.dataset.pwUi = "inline-keyword-input";
    input.rows = 1;
    input.placeholder = t("enterNewKeyword");
    input.setAttribute("aria-label", t("keywordInput"));
    input.setAttribute("title", t("enterToAddKeyword"));
    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" || event.shiftKey) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      const value = normalizeTokenText(input.value);
      if (!value) {
        return;
      }
      appendPromptFragment(value, {
        statusMessage: text("groupTagInserted", { label: value }),
      });
      input.value = "";
    });
    return input;
  };

  if (normalizedFixedScope) {
    const counterChip = document.createElement("span");
    counterChip.id = `${idPrefix}-inline-counter`;
    counterChip.className = "rookieui-shell__prompt-workbench-inline-chip";
    counterChip.dataset.pwUi = "inline-counter";
    counterChip.setAttribute("role", "status");
    counterChip.setAttribute("aria-live", "polite");
    counterChip.setAttribute("aria-label", t("promptTokenCount"));
    counterChip.textContent = `0 ${t("tagPlural")}`;
    headerActions.appendChild(counterChip);
    inlineToolbarNodes.counter = counterChip;

    const languageButton = createActionButton(`${idPrefix}-inline-language`, "en");
    languageButton.classList.add("rookieui-shell__prompt-workbench-inline-chip", "rookieui-shell__prompt-workbench-language-button");
    languageButton.dataset.pwUi = "inline-language";
    languageButton.setAttribute("aria-label", t("languageAndScope"));
    languageButton.setAttribute("aria-haspopup", "listbox");
    languageButton.setAttribute("aria-controls", `${idPrefix}-language-selector`);
    languageButton.setAttribute("aria-expanded", "false");
    languageButton.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      languageSelectorOpen = !languageSelectorOpen;
      activeSecondaryPopover = "";
      syncUi();
      if (languageSelectorOpen) {
        focusSelectedLanguageOption();
      }
    });
    headerActions.appendChild(languageButton);
    inlineToolbarNodes.language = languageButton;

    const languageSelector = document.createElement("div");
    languageSelector.id = `${idPrefix}-language-selector`;
    languageSelector.className = "rookieui-shell__prompt-workbench-language-selector";
    languageSelector.dataset.pwUi = "language-selector-popover";
    languageSelector.setAttribute("role", "listbox");
    languageSelector.setAttribute("aria-label", t("languageSelector"));
    languageSelector.hidden = true;
    languageSelector.addEventListener("keydown", handleLanguageSelectorKeydown);
    headerActions.appendChild(languageSelector);
    inlineToolbarNodes.languageSelector = languageSelector;

    inlineToolbarNodes.historyButton = createInlineToolbarButton("inline-history", INLINE_TOOLBAR_ICONS.history, t("panelHistory"), "inline-history-anchor", () => {
      activeSecondaryPopover = activeSecondaryPopover === "history" ? "" : "history";
      const state = getActiveState();
      state.workbench_open = true;
      state.active_panel = "history";
      queueStatePersist();
      void ensureResourcesLoaded({ statusMessage: t("historyLoaded") });
      syncUi();
    });
    inlineToolbarNodes.favoritesButton = createInlineToolbarButton("inline-favorites", INLINE_TOOLBAR_ICONS.favorites, t("panelFavorites"), "inline-favorites-anchor", () => {
      activeSecondaryPopover = activeSecondaryPopover === "favorites" ? "" : "favorites";
      const state = getActiveState();
      state.workbench_open = true;
      state.active_panel = "favorites";
      queueStatePersist();
      void ensureResourcesLoaded({ statusMessage: t("favoritesLoaded") });
      syncUi();
    });
    const settingsCluster = document.createElement("span");
    settingsCluster.className = "rookieui-shell__prompt-workbench-inline-settings-cluster";
    settingsCluster.dataset.pwUi = "inline-settings-cluster";
    headerActions.appendChild(settingsCluster);
    inlineToolbarNodes.settingsButton = createActionButton(`${idPrefix}-inline-settings`, INLINE_TOOLBAR_ICONS.settings);
    inlineToolbarNodes.settingsButton.classList.add("rookieui-shell__prompt-workbench-inline-tool");
    inlineToolbarNodes.settingsButton.dataset.pwUi = "inline-settings-anchor";
    applyIconButtonLabel(inlineToolbarNodes.settingsButton, INLINE_TOOLBAR_ICONS.settings, t("preferencesShort"));
    inlineToolbarNodes.settingsButton.removeAttribute("title");
    inlineToolbarNodes.settingsButton.addEventListener("click", () => {
      activeSecondaryPopover = activeSecondaryPopover === "settings" ? "" : "settings";
      const state = getActiveState();
      state.workbench_open = true;
      state.active_panel = "format";
      queueStatePersist();
      syncUi();
    });
    settingsCluster.appendChild(inlineToolbarNodes.settingsButton);
    inlineToolbarNodes.settingsHoverBox = createInlineSettingsHoverBox();
    settingsCluster.appendChild(inlineToolbarNodes.settingsHoverBox);
    [inlineToolbarNodes.historyButton, inlineToolbarNodes.favoritesButton, inlineToolbarNodes.settingsButton].forEach((button) => {
      button?.setAttribute("aria-haspopup", "dialog");
      button?.setAttribute("aria-controls", `${idPrefix}-secondary-popover`);
    });
    createInlineToolbarButton("inline-translate", INLINE_TOOLBAR_ICONS.translate, "Translate", "inline-translate-action", () => {
      translateActivePrompt(String(configState.language ?? "en").trim() || "en");
    });
    createInlineToolbarButton("inline-copy", INLINE_TOOLBAR_ICONS.copy, "Copy", "inline-copy-action", () => {
      const promptText = String(getActiveState().draft_prompt || getActiveInput()?.value || "");
      if (navigator?.clipboard?.writeText) {
        void navigator.clipboard.writeText(promptText);
      }
      updateStatus(t("copiedActivePrompt"));
    });
    createInlineToolbarButton("inline-delete", INLINE_TOOLBAR_ICONS.delete, "Delete", "inline-delete-action", () => {
      applyPromptTextToInput("", {
        updateEditor: true,
        statusMessage: t("clearedActivePrompt"),
      });
    });
    inlineToolbarNodes.appendButton = createInlineToolbarButton("inline-append", INLINE_TOOLBAR_ICONS.append, t("append"), "inline-append-anchor", () => {
      activeSecondaryPopover = activeSecondaryPopover === "append" ? "" : "append";
      const state = getActiveState();
      state.workbench_open = true;
      state.active_panel = "editor";
      queueStatePersist();
      void ensureResourcesLoaded({ statusMessage: t("appendLoaded") });
      syncUi();
    });
    inlineToolbarNodes.appendButton.setAttribute("aria-haspopup", "dialog");
    inlineToolbarNodes.appendButton.setAttribute("aria-controls", `${idPrefix}-secondary-popover`);
    inlineToolbarNodes.keywordInput = createInlineKeywordInput();
    headerActions.appendChild(inlineToolbarNodes.keywordInput);
  }

  const body = document.createElement("div");
  body.id = `${idPrefix}-body`;
  body.className = "rookieui-shell__prompt-workbench-body rookieui-shell__prompt-workbench-card-body";
  body.dataset.pwUi = "prompt-card-body";
  shell.appendChild(body);

  const namespaceTabs = document.createElement("div");
  namespaceTabs.className = "rookieui-shell__prompt-workbench-tabs";
  namespaceTabs.dataset.pwUi = "scope-tabs";
  namespaceTabs.hidden = Boolean(normalizedFixedScope);
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

  const summaryLabels = new Map();
  const createSummaryCard = (key, label) => {
    const card = document.createElement("article");
    card.className = "rookieui-shell__prompt-workbench-card";
    const labelNode = appendTextElement(card, "span", "rookieui-shell__prompt-workbench-card-label", label);
    summaryLabels.set(key, labelNode);
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

  const secondaryRow = document.createElement("div");
  secondaryRow.className = "rookieui-shell__prompt-workbench-secondary-entrypoints";
  secondaryRow.dataset.pwUi = "secondary-entrypoints";
  body.appendChild(secondaryRow);

  const secondaryButtons = new Map();
  const createSecondaryButton = (surface, label, panelId = surface) => {
    const button = createActionButton(`${idPrefix}-quick-${surface}`, label);
    button.classList.add("rookieui-shell__prompt-workbench-secondary-button");
    button.dataset.pwUi = surface === "settings" ? "settings-menu-entrypoint" : `${surface}-popover-entrypoint`;
    button.addEventListener("click", () => {
      activeSecondaryPopover = activeSecondaryPopover === surface ? "" : surface;
      const currentState = getActiveState();
      currentState.active_panel = panelId;
      queueStatePersist();
      syncUi();
    });
    secondaryRow.appendChild(button);
    secondaryButtons.set(surface, button);
    return button;
  };

  createSecondaryButton("history", t("panelHistory"));
  createSecondaryButton("favorites", t("panelFavorites"));
  createSecondaryButton("settings", t("preferencesShort"), "format");

  const secondaryPopover = document.createElement("div");
  secondaryPopover.id = `${idPrefix}-secondary-popover`;
  secondaryPopover.className = "rookieui-shell__prompt-workbench-secondary-popover";
  secondaryPopover.dataset.pwUi = "history-favorites-popovers";
  secondaryPopover.hidden = true;
  body.appendChild(secondaryPopover);

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

  function closeLanguageSelector({ focusTrigger = false } = {}) {
    if (!languageSelectorOpen) {
      return;
    }
    languageSelectorOpen = false;
    syncUi();
    if (focusTrigger) {
      inlineToolbarNodes.language?.focus();
    }
  }

  function placeLanguageSelector() {
    const selector = inlineToolbarNodes.languageSelector;
    const trigger = inlineToolbarNodes.language;
    if (!selector || !trigger || selector.hidden) {
      return;
    }
    const placement = computeLanguageSelectorPlacement(
      trigger.getBoundingClientRect?.(),
      getViewportSize(),
    );

    selector.dataset.placement = "fixed";
    selector.style.position = "fixed";
    selector.style.left = `${placement.left}px`;
    selector.style.top = `${placement.top}px`;
    selector.style.width = `${placement.width}px`;
    selector.style.maxHeight = `${placement.maxHeight}px`;
  }

  function getLanguageOptionButtons() {
    return Array.from(inlineToolbarNodes.languageSelector?.querySelectorAll("[data-pw-ui='language-option']") ?? []);
  }

  function focusLanguageOptionByIndex(index) {
    const options = getLanguageOptionButtons();
    if (!options.length) {
      return;
    }
    const nextIndex = clampOverlayValue(index, 0, options.length - 1);
    const nextOption = options[nextIndex];
    inlineToolbarNodes.languageSelector?.setAttribute("aria-activedescendant", nextOption.id);
    nextOption.focus();
  }

  function focusSelectedLanguageOption() {
    const options = getLanguageOptionButtons();
    const selectedIndex = options.findIndex((option) => option.dataset.selected === "true");
    focusLanguageOptionByIndex(selectedIndex >= 0 ? selectedIndex : 0);
  }

  function focusRelativeLanguageOption(offset) {
    const options = getLanguageOptionButtons();
    if (!options.length) {
      return;
    }
    const activeIndex = options.findIndex((option) => option === document.activeElement);
    const selectedIndex = options.findIndex((option) => option.dataset.selected === "true");
    const currentIndex = activeIndex >= 0 ? activeIndex : selectedIndex >= 0 ? selectedIndex : 0;
    focusLanguageOptionByIndex(currentIndex + offset);
  }

  function handleLanguageSelectorKeydown(event) {
    if (!languageSelectorOpen) {
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      closeLanguageSelector({ focusTrigger: true });
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      focusRelativeLanguageOption(1);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      focusRelativeLanguageOption(-1);
      return;
    }
    if (event.key === "Home") {
      event.preventDefault();
      focusLanguageOptionByIndex(0);
      return;
    }
    if (event.key === "End") {
      event.preventDefault();
      focusLanguageOptionByIndex(getLanguageOptionButtons().length - 1);
      return;
    }
    if (event.key === "Enter" || event.key === " ") {
      const eventOption = event.target?.dataset?.pwUi === "language-option" ? event.target : null;
      const activeOption = eventOption ?? (document.activeElement?.dataset?.pwUi === "language-option"
        ? document.activeElement
        : inlineToolbarNodes.languageSelector?.querySelector("[data-selected='true']"));
      const languageCode = activeOption?.dataset?.languageCode;
      if (languageCode) {
        event.preventDefault();
        setPromptWorkbenchLanguage(languageCode, { focusTrigger: true });
      }
    }
  }

  function setPromptWorkbenchLanguage(nextLanguage, { focusTrigger = false, broadcast = true } = {}) {
    const normalizedLanguage = normalizeLanguageCode(nextLanguage);
    const didChange = String(configState.language ?? "en").trim() !== normalizedLanguage;
    if (String(configState.language ?? "en").trim() !== normalizedLanguage) {
      configState.language = normalizedLanguage;
      queueConfigPersist();
    }
    languageSelectorOpen = false;
    syncUi();
    if (didChange && resourcesLoaded) {
      void refreshCatalogForLanguage(normalizedLanguage);
    }
    if (broadcast) {
      // IMPORTANT: keep paired inline shells synchronized.
      document.dispatchEvent(
        new CustomEvent(PROMPT_WORKBENCH_LANGUAGE_SYNC_EVENT, {
          detail: {
            language: normalizedLanguage,
            sourceId: languageSyncSourceId,
          },
        }),
      );
    }
    if (focusTrigger) {
      inlineToolbarNodes.language?.focus();
    }
  }

  function handlePromptWorkbenchLanguageSync(event) {
    const detail = event?.detail ?? {};
    if (detail.sourceId === languageSyncSourceId) {
      return;
    }
    if (!shell.isConnected) {
      return;
    }
    const normalizedLanguage = normalizeLanguageCode(detail.language);
    const didChange = String(configState.language ?? "en").trim() !== normalizedLanguage;
    configState.language = normalizedLanguage;
    languageSelectorOpen = false;
    syncUi();
    if (didChange && resourcesLoaded) {
      void refreshCatalogForLanguage(normalizedLanguage);
    }
  }

  lifecycle.listen(document, PROMPT_WORKBENCH_LANGUAGE_SYNC_EVENT, handlePromptWorkbenchLanguageSync);

  async function refreshCatalogForLanguage(language) {
    const normalizedLanguage = normalizeLanguageCode(language);
    try {
      const result = await bootstrapState?.fetchPromptWorkbenchCatalogRequest?.(normalizedLanguage);
      if (result?.data) {
        catalogPayload = result.data;
      }
      updateStatus(`Prompt Workbench catalog refreshed for ${normalizedLanguage}`);
    } catch {
      updateStatus(`Prompt Workbench catalog refresh failed for ${normalizedLanguage}`);
    } finally {
      syncUi();
    }
  }

  function renderLanguageSelector() {
    const selector = inlineToolbarNodes.languageSelector;
    if (!selector) {
      return;
    }
    clearChildren(selector);
    selector.hidden = !languageSelectorOpen;
    const currentLanguage = normalizeLanguageCode(configState?.language ?? "en");
    if (configState.language !== currentLanguage) {
      configState.language = currentLanguage;
    }
    selector.setAttribute("aria-activedescendant", `${idPrefix}-language-option-${normalizeDomIdPart(currentLanguage)}`);
    getLanguageOptions().forEach((entry) => {
      const displayTitle = formatLanguageOptionLabel(entry);
      const optionButton = createActionButton(`${idPrefix}-language-option-${normalizeDomIdPart(entry.code)}`, displayTitle);
      optionButton.classList.add("rookieui-shell__prompt-workbench-language-option");
      optionButton.dataset.pwUi = "language-option";
      optionButton.dataset.languageCode = entry.code;
      optionButton.dataset.selected = String(entry.code === currentLanguage);
      optionButton.setAttribute("role", "option");
      optionButton.setAttribute("aria-selected", String(entry.code === currentLanguage));
      optionButton.addEventListener("focus", () => {
        selector.setAttribute("aria-activedescendant", optionButton.id);
      });
      optionButton.addEventListener("click", () => {
        setPromptWorkbenchLanguage(entry.code, { focusTrigger: true });
      });
      selector.appendChild(optionButton);
    });
    placeLanguageSelector();
  }

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
    shell.dataset.folded = String(!isOpen);
    body.hidden = !isOpen;
    if (normalizedFixedScope) {
      applyIconButtonLabel(toggleButton, isOpen ? INLINE_TOOLBAR_ICONS.fold : INLINE_TOOLBAR_ICONS.open, isOpen ? t("foldTools") : t("openTools"));
    } else {
      toggleButton.textContent = isOpen ? t("hideWorkbench") : t("openWorkbench");
    }
    toggleButton.setAttribute("aria-expanded", String(isOpen));
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
    if (lifecycle.destroyed) return;
    setText(detailNodes.status, message);
  }

  function syncLocalizedUiLabels() {
    setText(titleNode, t("title"));
    setText(subtitleNode, t("subtitle"));
    tabButtons.get("prompt").textContent = t("promptTab");
    tabButtons.get("negative").textContent = t("negativeTab");
    summaryLabels.get("state").textContent = t("summaryState");
    summaryLabels.get("providers").textContent = t("summaryProviders");
    summaryLabels.get("catalogs").textContent = t("summaryCatalogs");
    summaryLabels.get("history").textContent = t("summaryHistory");
    summaryLabels.get("favorites").textContent = t("summaryFavorites");
    summaryLabels.get("blacklist").textContent = t("summaryBlacklist");
    panelButtons.forEach((button, panelId) => {
      button.textContent = t(`panel${panelId.charAt(0).toUpperCase()}${panelId.slice(1)}`);
    });
    secondaryButtons.get("history").textContent = t("panelHistory");
    secondaryButtons.get("favorites").textContent = t("panelFavorites");
    secondaryButtons.get("settings").textContent = t("preferencesShort");
    captureButton.textContent = t("captureCurrentText");
    restoreButton.textContent = t("restoreDraft");
    if (inlineToolbarNodes.counter) {
      inlineToolbarNodes.counter.setAttribute("aria-label", t("promptTokenCount"));
    }
    if (inlineToolbarNodes.language) {
      inlineToolbarNodes.language.setAttribute("aria-label", t("languageAndScope"));
    }
    if (inlineToolbarNodes.languageSelector) {
      inlineToolbarNodes.languageSelector.setAttribute("aria-label", t("languageSelector"));
    }
    if (inlineToolbarNodes.keywordInput) {
      inlineToolbarNodes.keywordInput.placeholder = t("enterNewKeyword");
      inlineToolbarNodes.keywordInput.setAttribute("aria-label", t("keywordInput"));
      inlineToolbarNodes.keywordInput.setAttribute("title", t("enterToAddKeyword"));
    }
    if (inlineToolbarNodes.historyButton) {
      applyIconButtonLabel(inlineToolbarNodes.historyButton, INLINE_TOOLBAR_ICONS.history, t("panelHistory"));
    }
    if (inlineToolbarNodes.favoritesButton) {
      applyIconButtonLabel(inlineToolbarNodes.favoritesButton, INLINE_TOOLBAR_ICONS.favorites, t("panelFavorites"));
    }
    if (inlineToolbarNodes.settingsButton) {
      applyIconButtonLabel(inlineToolbarNodes.settingsButton, INLINE_TOOLBAR_ICONS.settings, t("preferencesShort"));
      inlineToolbarNodes.settingsButton.removeAttribute("title");
    }
    if (inlineToolbarNodes.appendButton) {
      applyIconButtonLabel(inlineToolbarNodes.appendButton, INLINE_TOOLBAR_ICONS.append, t("append"));
    }
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

  function queueAutoHistoryCapture(namespace, scope, promptText, tokens) {
    const normalizedText = String(promptText ?? "").trim();
    if (!namespace || !normalizedText || normalizedText === lastAutoHistoryText.get(namespace)) {
      return;
    }
    const existingTimer = autoHistoryTimers.get(namespace);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }
    const tokenSnapshot = serializeTokenPayloads(tokens, activeScope);
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

  function getInlineSuggestions() {
    const seen = new Set();
    const suggestions = [];
    const pushSuggestion = (source, label, fragment) => {
      const normalizedFragment = normalizeTokenText(fragment);
      if (!normalizedFragment || seen.has(normalizedFragment)) {
        return;
      }
      seen.add(normalizedFragment);
      suggestions.push({
        source,
        label: String(label ?? normalizedFragment),
        fragment: normalizedFragment,
      });
    };

    (favoritesCache.get(getActiveNamespace()) ?? []).slice(0, 3).forEach((entry) => {
      pushSuggestion("favorites", entry.label || "Favorite", entry.prompt_text);
    });
    (historyCache.get(getActiveNamespace()) ?? []).slice(0, 3).forEach((entry) => {
      pushSuggestion("history", entry.label || "History", entry.prompt_text);
    });
    (Array.isArray(catalogPayload?.tagcomplete?.entries) ? catalogPayload.tagcomplete.entries : []).slice(0, 6).forEach((entry) => {
      pushSuggestion("tagcomplete", entry?.label ?? entry?.tag, entry?.insert_token ?? entry?.tag ?? entry?.label);
    });

    return suggestions.slice(0, 8);
  }

  function renderInlineSuggestions(parent, surfaceId = "inline") {
    const suggestions = getInlineSuggestions();
    const suggestionRow = document.createElement("div");
    suggestionRow.className = "rookieui-shell__prompt-workbench-inline-suggestions";
    suggestionRow.dataset.pwUi = "inline-suggestions";
    parent.appendChild(suggestionRow);

    if (!suggestions.length) {
      appendTextElement(suggestionRow, "span", "rookieui-shell__prompt-workbench-detail", t("noInlineSuggestions"));
      return;
    }

    suggestions.forEach((suggestion, index) => {
      const button = createActionButton(`${idPrefix}-${surfaceId}-suggestion-${index}`, suggestion.label);
      button.classList.add("rookieui-shell__prompt-workbench-chip");
      button.dataset.source = suggestion.source;
      button.addEventListener("click", () => {
        appendPromptFragment(suggestion.fragment, {
          statusMessage: `Inserted ${suggestion.label}`,
        });
      });
      suggestionRow.appendChild(button);
    });
  }

  function getNormalizedGroupTagGroups() {
    return normalizeGroupTagGroups(catalogPayload);
  }

  function isGroupTagsVisible() {
    return configState?.ui_preferences?.show_group_tags !== false;
  }

  function persistGroupTagPreference(patch) {
    configState.ui_preferences = {
      ...(configState.ui_preferences ?? {}),
      ...patch,
    };
    queueConfigPersist();
  }

  function selectActiveGroupTagState(groups) {
    const preferredGroupId = normalizeTokenText(configState?.ui_preferences?.active_group_tag_group);
    const activeGroup = groups.find((group) => group.id === preferredGroupId) ?? groups[0] ?? null;
    const preferredSubgroupId = normalizeTokenText(configState?.ui_preferences?.active_group_tag_subgroup);
    const activeSubgroup = activeGroup?.subgroups.find((subgroup) => subgroup.id === preferredSubgroupId) ?? activeGroup?.subgroups[0] ?? null;
    return { activeGroup, activeSubgroup };
  }

  function hasActivePromptToken(insertToken) {
    const normalizedInsertToken = normalizeTokenText(insertToken).toLowerCase();
    return ensureEditorTokens(getActiveNamespace()).some((token) => normalizeTokenText(token.raw_text ?? token.text).toLowerCase() === normalizedInsertToken);
  }

  function toggleGroupTagEntry(entry) {
    const insertToken = normalizeTokenText(entry?.insert_token ?? entry?.tag ?? entry?.label);
    if (!insertToken) {
      return;
    }
    const normalizedInsertToken = insertToken.toLowerCase();
    const tokens = ensureEditorTokens(getActiveNamespace());
    const existingIndex = tokens.findIndex((token) => normalizeTokenText(token.raw_text ?? token.text).toLowerCase() === normalizedInsertToken);
    const label = normalizeTokenText(entry?.label) || insertToken;
    if (existingIndex >= 0) {
      tokens.splice(existingIndex, 1);
      rebuildPromptFromEditor(text("groupTagRemoved", { label }));
      syncUi();
      return;
    }
    appendPromptFragment(insertToken, {
      statusMessage: text("groupTagInserted", { label }),
    });
  }

  function renderGroupTagsBoard(parent, surfaceId = "editor") {
    const groups = getNormalizedGroupTagGroups();
    const board = document.createElement("section");
    board.className = "rookieui-shell__prompt-workbench-group-tags-board";
    board.dataset.pwUi = "group-tags-tab-board";
    parent.appendChild(board);
    const header = document.createElement("div");
    header.className = "rookieui-shell__prompt-workbench-group-tags-header";
    board.appendChild(header);
    appendTextElement(header, "h6", "rookieui-shell__prompt-workbench-pane-title", t("groupTags"));
    const toggleButton = createActionButton(
      `${idPrefix}-${surfaceId}-group-tags-visibility`,
      isGroupTagsVisible() ? t("hideGroupTags") : t("showGroupTags"),
    );
    toggleButton.classList.add("rookieui-shell__prompt-workbench-group-tags-toggle");
    toggleButton.dataset.pwUi = "group-tags-visibility-toggle";
    toggleButton.setAttribute("aria-pressed", String(isGroupTagsVisible()));
    toggleButton.addEventListener("click", () => {
      persistGroupTagPreference({ show_group_tags: !isGroupTagsVisible() });
      syncUi();
    });
    header.appendChild(toggleButton);

    if (!isGroupTagsVisible()) {
      appendTextElement(board, "p", "rookieui-shell__prompt-workbench-empty", t("groupTagsHidden"));
      return;
    }

    if (!groups.length) {
      appendTextElement(board, "p", "rookieui-shell__prompt-workbench-empty", t("noGroupTags"));
      return;
    }

    const { activeGroup, activeSubgroup } = selectActiveGroupTagState(groups);
    const activeGroupIndex = Math.max(0, groups.findIndex((group) => group.id === activeGroup?.id));
    const groupTabs = document.createElement("div");
    groupTabs.className = "rookieui-shell__prompt-workbench-group-tags-tabs";
    groupTabs.dataset.pwUi = "group-tags-group-tabs";
    board.appendChild(groupTabs);
    groups.forEach((group, groupIndex) => {
      const button = createActionButton(`${idPrefix}-${surfaceId}-group-tags-group-${normalizeDomIdPart(group.id)}`, group.title);
      button.classList.add("rookieui-shell__prompt-workbench-group-tags-tab");
      button.dataset.pwUi = "group-tags-group-tab";
      button.dataset.active = String(group.id === activeGroup?.id);
      button.setAttribute("aria-pressed", String(group.id === activeGroup?.id));
      button.addEventListener("click", () => {
        persistGroupTagPreference({
          active_group_tag_group: group.id,
          active_group_tag_subgroup: group.subgroups[0]?.id ?? "",
        });
        syncUi();
      });
      groupTabs.appendChild(button);
    });

    const subgroupTabs = document.createElement("div");
    subgroupTabs.className = "rookieui-shell__prompt-workbench-group-tags-tabs rookieui-shell__prompt-workbench-group-tags-tabs--sub";
    subgroupTabs.dataset.pwUi = "group-tags-subgroup-tabs";
    board.appendChild(subgroupTabs);
    (activeGroup?.subgroups ?? []).forEach((subgroup) => {
      const button = createActionButton(`${idPrefix}-${surfaceId}-group-tags-subgroup-${normalizeDomIdPart(subgroup.id)}`, subgroup.title);
      button.classList.add("rookieui-shell__prompt-workbench-group-tags-tab");
      button.dataset.pwUi = "group-tags-subgroup-tab";
      button.dataset.active = String(subgroup.id === activeSubgroup?.id);
      button.setAttribute("aria-pressed", String(subgroup.id === activeSubgroup?.id));
      button.addEventListener("click", () => {
        persistGroupTagPreference({
          active_group_tag_group: activeGroup?.id ?? "",
          active_group_tag_subgroup: subgroup.id,
        });
        syncUi();
      });
      subgroupTabs.appendChild(button);
    });

    const entryGrid = document.createElement("div");
    entryGrid.className = "rookieui-shell__prompt-workbench-chip-grid rookieui-shell__prompt-workbench-group-tags-entry-grid";
    entryGrid.dataset.pwUi = "group-tags-entry-grid";
    board.appendChild(entryGrid);
    (activeSubgroup?.tag_entries ?? []).forEach((entry, entryIndex) => {
      const insertToken = normalizeTokenText(entry?.insert_token ?? entry?.tag ?? entry?.label);
      if (!insertToken) {
        return;
      }
      const label = normalizeTokenText(entry?.label) || insertToken;
      const button = createActionButton(`${idPrefix}-${surfaceId}-group-tag-${activeGroupIndex}-${entryIndex}`, "");
      button.classList.add("rookieui-shell__prompt-workbench-chip", "rookieui-shell__prompt-workbench-group-tags-entry");
      button.dataset.pwUi = "group-tags-entry";
      button.dataset.highlight = getCatalogHighlight(entry);
      button.dataset.selected = String(hasActivePromptToken(insertToken));
      button.setAttribute("aria-pressed", button.dataset.selected);
      button.title = `${activeGroup?.title ?? t("groupTags")} / ${activeSubgroup?.title ?? ""}`.trim();
      const labelStack = document.createElement("span");
      labelStack.className = "rookieui-shell__prompt-workbench-group-tags-entry-labels";
      const localLabel = normalizeTokenText(entry?.local_label);
      const englishLabel = normalizeTokenText(entry?.english_label) || insertToken;
      if (localLabel && localLabel !== englishLabel) {
        appendTextElement(labelStack, "span", "rookieui-shell__prompt-workbench-group-tags-entry-local", localLabel);
        appendTextElement(labelStack, "span", "rookieui-shell__prompt-workbench-group-tags-entry-en", englishLabel);
      } else {
        appendTextElement(labelStack, "span", "rookieui-shell__prompt-workbench-group-tags-entry-local", label);
      }
      button.appendChild(labelStack);
      button.addEventListener("click", () => {
        toggleGroupTagEntry(entry);
      });
      entryGrid.appendChild(button);
    });
  }

  function renderSecondaryPopover() {
    clearChildren(secondaryPopover);
    const surface = activeSecondaryPopover;
    secondaryPopover.hidden = !surface;
    secondaryPopover.dataset.activeSurface = surface;
    if (!surface) {
      return;
    }

    const title =
      surface === "settings"
        ? t("preferences")
        : surface === "favorites"
          ? t("panelFavorites")
          : surface === "append"
            ? t("append")
            : t("panelHistory");
    appendTextElement(secondaryPopover, "h6", "rookieui-shell__prompt-workbench-pane-title", title);

    if (surface === "settings") {
      [
        ["format", t("formattingAndBlacklist")],
        ["assist", t("panelAssist")],
      ].forEach(([panelId, label], index) => {
        const button = createActionButton(`${idPrefix}-settings-popover-${index}`, label);
        button.addEventListener("click", () => {
          activeSecondaryPopover = "";
          const currentState = getActiveState();
          currentState.active_panel = panelId;
          queueStatePersist();
          syncUi();
        });
        secondaryPopover.appendChild(button);
      });
      return;
    }

    if (surface === "append") {
      secondaryPopover.dataset.pwUi = "append-dropdown-popover";
      renderInlineSuggestions(secondaryPopover, "append-popover");
      renderGroupTagsBoard(secondaryPopover, "append-popover");
      return;
    }

    secondaryPopover.dataset.pwUi = "history-favorites-popovers";

    const entries = surface === "favorites"
      ? favoritesCache.get(getActiveNamespace()) ?? []
      : historyCache.get(getActiveNamespace()) ?? [];
    if (!entries.length) {
      appendTextElement(secondaryPopover, "p", "rookieui-shell__prompt-workbench-empty", `No ${surface} entries available.`);
      return;
    }

    entries.slice(0, 4).forEach((entry, index) => {
      const button = createActionButton(`${idPrefix}-${surface}-popover-${index}`, String(entry.label || entry.prompt_text || title));
      button.classList.add("rookieui-shell__prompt-workbench-popover-entry");
      button.addEventListener("click", () => {
        activeSecondaryPopover = "";
        applyCollectionEntry(entry);
      });
      secondaryPopover.appendChild(button);
    });
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
      activeScope === "negative" ? t("editorNegative") : t("editorPrompt"),
    );

    const addRow = document.createElement("div");
    addRow.className = "rookieui-shell__prompt-workbench-editor-toolbar";
    addRow.dataset.pwUi = "inline-add";
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

    renderInlineSuggestions(editorPane);

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

    if (normalizeLanguageCode(configState.language ?? "en").toLowerCase() !== "en") {
      const localLanguage = normalizeLanguageCode(configState.language ?? "en");
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
    batchRow.dataset.batchLayout = normalizedFixedScope ? "inline-overlay" : "panel";
    if (normalizedFixedScope && selectedCount === 0) {
      batchRow.hidden = true;
    }
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
    list.dataset.tokenLayout = normalizedFixedScope ? "inline-tags" : "board";
    editorPane.appendChild(list);

    if (!tokens.length) {
      appendTextElement(
        list,
        "p",
        "rookieui-shell__prompt-workbench-empty",
        "No tokens yet. Capture or add prompt text to begin editing.",
      );
      renderGroupTagsBoard(editorPane, "editor");
      return;
    }

    tokens.forEach((token, index) => {
      const row = document.createElement("div");
      row.className = "rookieui-shell__prompt-workbench-token rookieui-shell__prompt-workbench-token-chip";
      if (normalizedFixedScope) {
        row.classList.add("rookieui-shell__prompt-workbench-token--inline-tag");
      }
      row.dataset.pwUi = "token-chip";
      row.dataset.pwTokenUi = normalizedFixedScope ? "inline-token-tag" : "token-chip";
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
      const localLanguage = normalizeLanguageCode(configState.language ?? "en");
      const translationDetail = document.createElement("span");
      translationDetail.id = `${idPrefix}-token-translation-${index}`;
      translationDetail.className =
        "rookieui-shell__prompt-workbench-token-translation rookieui-shell__prompt-workbench-token-local-language";
      translationDetail.dataset.pwUi = "token-local-language";
      translationDetail.dataset.hasTranslation = String(Boolean(translatedText));
      translationDetail.textContent = translatedText ? `${localLanguage}: ${translatedText}` : `${localLanguage}: not translated`;
      row.appendChild(translationDetail);

      const controls = document.createElement("div");
      controls.className = "rookieui-shell__prompt-workbench-token-actions rookieui-shell__prompt-workbench-token-quick-actions";
      controls.dataset.pwUi = "token-quick-actions";
      controls.setAttribute("aria-label", "Prompt token quick actions");
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
          token_payloads: [serializeTokenPayload(token, index, activeScope)],
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

    renderGroupTagsBoard(editorPane, "editor");
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
    renderPromptWorkbenchCatalogPane({
      catalogPane,
      catalogPayload,
      catalogSearchState,
      clearChildren,
      appendTextElement,
      createActionButton,
      idPrefix,
      getCatalogHighlight,
      appendPromptFragment,
      syncUi,
    });
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
    getLanguageOptions().forEach((entry) => {
      const option = document.createElement("option");
      option.value = String(entry?.code ?? "en");
      option.textContent = `${String(entry?.code ?? "en")} - ${String(entry?.title ?? "English")}`;
      languageSelect.appendChild(option);
    });
    languageSelect.value = normalizeLanguageCode(configState?.language ?? "en");
    languageSelect.addEventListener("change", () => {
      setPromptWorkbenchLanguage(languageSelect.value);
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
      const input = createProviderConfigInput({ fieldSpec, fieldKey, providerConfig, idPrefix, onChange: (value) => {
        const selectedProviderId = String(configState?.ai_assist?.default_provider ?? "").trim();
        if (!selectedProviderId) {
          return;
        }
        const nextProviders = {
          ...(configState.ai_assist?.providers ?? {}),
          [selectedProviderId]: {
            ...(configState.ai_assist?.providers?.[selectedProviderId] ?? {}),
            [fieldKey]: value,
          },
        };
        configState.ai_assist = {
          ...(configState.ai_assist ?? {}),
          providers: nextProviders,
          instruction_preset: String(configState.ai_assist?.instruction_preset ?? ""),
        };
        queueConfigPersist();
      } });
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
    if (lifecycle.destroyed) return;
    const state = getActiveState();
    state.active_panel = resolveVisiblePanel(state.active_panel);
    if ((activeSecondaryPopover === "history" && !isPanelVisible("history")) || (activeSecondaryPopover === "favorites" && !isPanelVisible("favorites"))) {
      activeSecondaryPopover = "";
    }
    const historyItems = historyCache.get(getActiveNamespace()) ?? [];
    const favoriteItems = favoritesCache.get(getActiveNamespace()) ?? [];
    const language = normalizeLanguageCode(configState?.language ?? "en");
    if (configState.language !== language) {
      configState.language = language;
    }
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
    const activeText = String(state.draft_prompt || getActiveInput()?.value || "");
    const activeUnitCount = countPromptUnits(activeText);

    syncLocalizedUiLabels();
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
    const quickHistoryButton = document.getElementById(`${idPrefix}-quick-history`);
    if (quickHistoryButton) {
      quickHistoryButton.hidden = !isPanelVisible("history");
      quickHistoryButton.dataset.active = String(activeSecondaryPopover === "history");
    }
    const quickFavoritesButton = document.getElementById(`${idPrefix}-quick-favorites`);
    if (quickFavoritesButton) {
      quickFavoritesButton.hidden = !isPanelVisible("favorites");
      quickFavoritesButton.dataset.active = String(activeSecondaryPopover === "favorites");
    }
    const quickSettingsButton = document.getElementById(`${idPrefix}-quick-settings`);
    if (quickSettingsButton) {
      quickSettingsButton.dataset.active = String(activeSecondaryPopover === "settings");
    }
    if (inlineToolbarNodes.counter) {
      inlineToolbarNodes.counter.textContent = `${activeUnitCount} ${activeUnitCount === 1 ? t("tagSingular") : t("tagPlural")}`;
    }
    if (inlineToolbarNodes.language) {
      inlineToolbarNodes.language.textContent = `${language} / ${activeScope === "negative" ? t("negativeScope") : t("promptScope")}`;
      inlineToolbarNodes.language.setAttribute("aria-expanded", String(languageSelectorOpen));
    }
    if (inlineToolbarNodes.historyButton) {
      inlineToolbarNodes.historyButton.hidden = !isPanelVisible("history");
      inlineToolbarNodes.historyButton.dataset.active = String(activeSecondaryPopover === "history");
      inlineToolbarNodes.historyButton.setAttribute("aria-expanded", String(activeSecondaryPopover === "history"));
    }
    if (inlineToolbarNodes.favoritesButton) {
      inlineToolbarNodes.favoritesButton.hidden = !isPanelVisible("favorites");
      inlineToolbarNodes.favoritesButton.dataset.active = String(activeSecondaryPopover === "favorites");
      inlineToolbarNodes.favoritesButton.setAttribute("aria-expanded", String(activeSecondaryPopover === "favorites"));
    }
    if (inlineToolbarNodes.settingsButton) {
      inlineToolbarNodes.settingsButton.dataset.active = String(activeSecondaryPopover === "settings");
      inlineToolbarNodes.settingsButton.setAttribute("aria-expanded", String(activeSecondaryPopover === "settings"));
    }
    if (inlineToolbarNodes.appendButton) {
      inlineToolbarNodes.appendButton.dataset.active = String(activeSecondaryPopover === "append");
      inlineToolbarNodes.appendButton.setAttribute("aria-expanded", String(activeSecondaryPopover === "append"));
    }

    editorPane.hidden = state.active_panel !== "editor";
    historyPane.hidden = state.active_panel !== "history";
    favoritesPane.hidden = state.active_panel !== "favorites";
    catalogPane.hidden = state.active_panel !== "catalog";
    assistPane.hidden = state.active_panel !== "assist";
    formatPane.hidden = state.active_panel !== "format";

    updateShellThemeStyle();
    setText(summaryNodes.state, state.workbench_open ? t("persistedOpen") : t("collapsed"));
    const assistShippedProviders = Array.isArray(providersPayload?.surfaces?.ai_assist?.shipped_provider_ids)
      ? providersPayload.surfaces.ai_assist.shipped_provider_ids.length
      : 0;
    setText(
      summaryNodes.providers,
      resourcesLoaded
        ? `${shippedProviders} ${t("translateProviders")} / ${assistShippedProviders} ${t("assistProviders")} / ${language}`
        : t("lazy"),
    );
    setText(
      summaryNodes.catalogs,
      resourcesLoaded
        ? `${groupCount} ${t("groupsCount")} / ${libraryCount} ${t("sectionsCount")} / ${extraNetworkCount} ${t("networksCount")}`
        : t("lazy"),
    );
    setText(summaryNodes.history, `${historyItems.length} ${t("entries")}`);
    setText(summaryNodes.favorites, `${favoriteItems.length} ${t("entries")}`);
    setText(summaryNodes.blacklist, blacklistState.enabled ? `${(blacklistState.entries ?? []).length} ${t("blocked")}` : t("disabled"));

    setText(
      detailNodes.scope,
      text("scopeDetail", {
        scope: activeScope === "prompt" ? t("promptNamespace") : t("negativeNamespace"),
        namespace: getActiveNamespace(),
      }),
    );
    setText(detailNodes.draft, text("savedDraft", { count: countPromptUnits(state.draft_prompt) }));
    setText(detailNodes.panel, text("activePanel", { panel: state.active_panel }));

    renderEditorPane();
    renderCollectionPane(historyPane, "history");
    renderCollectionPane(favoritesPane, "favorites");
    renderCatalogPane();
    renderAssistPane();
    renderFormatPane();
    renderSecondaryPopover();
    renderLanguageSelector();
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
        if (normalizedFixedScope) {
          activeScope = normalizedFixedScope;
          return;
        }
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
      bootstrapState?.fetchPromptWorkbenchCatalogRequest?.(normalizeLanguageCode(configState?.language ?? "en")),
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
    if (event.key === "Escape" && activeSecondaryPopover && shell.contains(event.target)) {
      event.preventDefault();
      activeSecondaryPopover = "";
      syncUi();
      updateStatus("Closed Prompt Workbench popover");
      return;
    }
    if (event.key === "Escape" && languageSelectorOpen && shell.contains(event.target)) {
      event.preventDefault();
      closeLanguageSelector({ focusTrigger: true });
      updateStatus("Closed Prompt Workbench language selector");
      return;
    }
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

  const handleDocumentPointerDown = (event) => {
    if (!languageSelectorOpen) {
      return;
    }
    const target = event.target;
    if (inlineToolbarNodes.language?.contains(target) || inlineToolbarNodes.languageSelector?.contains(target)) {
      return;
    }
    closeLanguageSelector({ focusTrigger: true });
  };
  lifecycle.listen(document, "pointerdown", handleDocumentPointerDown);

  const repositionLanguageSelector = () => {
    if (languageSelectorOpen) {
      placeLanguageSelector();
    }
  };
  lifecycle.listen(globalThis, "resize", repositionLanguageSelector, { passive: true });
  lifecycle.listen(globalThis, "scroll", repositionLanguageSelector, { passive: true, capture: true });

  Object.entries(namespaceMap).forEach(([scope, namespace]) => {
    if (normalizedFixedScope && scope !== normalizedFixedScope) {
      return;
    }
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
    destroy: () => lifecycle.destroy(dirtyTimers, autoHistoryTimers),
  };
}
