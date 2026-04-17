let tokenSequence = 0;

function createToken(text, { disabled = false } = {}) {
  tokenSequence += 1;
  return {
    id: `pw-token-${tokenSequence}`,
    text: String(text ?? "").trim(),
    disabled: Boolean(disabled),
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
    created_at: Number(entry?.created_at ?? 0) || 0,
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

function parsePromptTokens(text) {
  return String(text ?? "")
    .split(/[\n,]+/)
    .map((entry) => entry.trim())
    .filter(Boolean)
    .map((entry) => createToken(entry));
}

function buildPromptTextFromTokens(tokens) {
  return (Array.isArray(tokens) ? tokens : [])
    .filter((token) => token && !token.disabled && String(token.text ?? "").trim())
    .map((token) => String(token.text).trim())
    .join(", ");
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
  shell.className = "rookieui-shell__prompt-workbench";
  parent.appendChild(shell);

  const configState = structuredClone(bootstrapState?.promptWorkbench?.config ?? {});
  configState.translation = configState.translation ?? { default_provider: "", providers: {} };
  configState.ai_assist = configState.ai_assist ?? {
    default_provider: "",
    providers: {},
    instruction_preset: "",
  };
  const blacklistState = structuredClone(bootstrapState?.promptWorkbench?.blacklist ?? { enabled: false, entries: [] });
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

  const header = document.createElement("div");
  header.className = "rookieui-shell__prompt-workbench-header";
  shell.appendChild(header);

  const headerCopy = document.createElement("div");
  headerCopy.className = "rookieui-shell__prompt-workbench-copy";
  header.appendChild(headerCopy);
  appendTextElement(headerCopy, "h5", "rookieui-shell__prompt-workbench-title", "Prompt Workbench");
  appendTextElement(
    headerCopy,
    "p",
    "rookieui-shell__prompt-workbench-subtitle",
    "Structured prompt editor with persisted history, favorites, formatting rules, and blacklist-aware cleanup.",
  );

  const headerActions = document.createElement("div");
  headerActions.className = "rookieui-shell__prompt-workbench-header-actions";
  header.appendChild(headerActions);

  const toggleButton = createActionButton(`${idPrefix}-toggle`, "Open Workbench");
  toggleButton.classList.add("rookieui-shell__prompt-workbench-toggle");
  headerActions.appendChild(toggleButton);

  const body = document.createElement("div");
  body.id = `${idPrefix}-body`;
  body.className = "rookieui-shell__prompt-workbench-body";
  shell.appendChild(body);

  const namespaceTabs = document.createElement("div");
  namespaceTabs.className = "rookieui-shell__prompt-workbench-tabs";
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
  createScopeButton("prompt", "Prompt");
  createScopeButton("negative", "Negative");

  const summaryGrid = document.createElement("div");
  summaryGrid.className = "rookieui-shell__prompt-workbench-summary-grid";
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
    state: createSummaryCard("state", "State"),
    providers: createSummaryCard("providers", "Providers"),
    catalogs: createSummaryCard("catalogs", "Catalogs"),
    history: createSummaryCard("history", "History"),
    favorites: createSummaryCard("favorites", "Favorites"),
    blacklist: createSummaryCard("blacklist", "Blacklist"),
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
    button.textContent = panelId === "format" ? "Format" : panelId.charAt(0).toUpperCase() + panelId.slice(1);
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

  const captureButton = createActionButton(`${idPrefix}-capture`, "Capture Current Text");
  captureButton.addEventListener("click", () => {
    const input = getActiveInput();
    const nextText = String(input?.value ?? "");
    const state = getActiveState();
    state.draft_prompt = nextText;
    editorCache.set(getActiveNamespace(), parsePromptTokens(nextText));
    queueStatePersist();
    syncUi();
    onStatusMessage?.("Captured current prompt text into Prompt Workbench state");
  });
  actionsRow.appendChild(captureButton);

  const restoreButton = createActionButton(`${idPrefix}-restore`, "Restore Draft");
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
    status: appendTextElement(details, "p", "rookieui-shell__prompt-workbench-status", "Prompt Workbench ready"),
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
      editorCache.set(namespace, parsePromptTokens(state.draft_prompt || getNamespaceInput(namespace)?.value));
    }
    return editorCache.get(namespace);
  }

  function setBodyOpen(isOpen) {
    shell.dataset.open = String(isOpen);
    body.hidden = !isOpen;
    toggleButton.textContent = isOpen ? "Hide Workbench" : "Open Workbench";
  }

  function readPreferredOpenState() {
    const state = getActiveState();
    if (state.workbench_open) {
      return true;
    }
    return Boolean(configState?.ui_preferences?.default_open);
  }

  function updateStatus(message) {
    setText(detailNodes.status, message);
  }

  function queueStatePersist() {
    const namespace = getActiveNamespace();
    const state = getActiveState();
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

  function applyPromptTextToInput(nextText, { updateEditor = true, statusMessage = "" } = {}) {
    const namespace = getActiveNamespace();
    const input = getActiveInput();
    const state = getActiveState();
    const normalizedText = String(nextText ?? "");
    state.draft_prompt = normalizedText;
    if (updateEditor) {
      editorCache.set(namespace, parsePromptTokens(normalizedText));
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
    const item = {
      label: buildEntryLabel(activeScope, promptText),
      prompt_text: promptText,
      tag_tokens: ensureEditorTokens(namespace).filter((token) => !token.disabled).map((token) => token.text),
    };
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
    const nextEntries = Array.from(new Set([...(blacklistState.entries ?? []), normalized]));
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

  function removeBlacklistEntry(entryText) {
    blacklistState.entries = (blacklistState.entries ?? []).filter((entry) => entry !== entryText);
    void bootstrapState?.updatePromptWorkbenchBlacklistRequest?.(blacklistState).then((result) => {
      if (result?.data?.blacklist) {
        Object.assign(blacklistState, result.data.blacklist);
      }
      updateStatus("Removed blacklist entry");
      syncUi();
    });
  }

  function applyBlacklistFilter() {
    const tokens = ensureEditorTokens(getActiveNamespace());
    const blacklistSet = new Set((blacklistState.entries ?? []).map((entry) => String(entry).trim().toLowerCase()));
    tokens.forEach((token) => {
      token.disabled = blacklistSet.has(String(token.text ?? "").trim().toLowerCase());
    });
    rebuildPromptFromEditor("Applied Prompt Workbench blacklist filter");
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
      ensureEditorTokens(getActiveNamespace()).push(createToken(normalizedText));
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

    const tokens = ensureEditorTokens(getActiveNamespace());
    const list = document.createElement("div");
    list.id = `${idPrefix}-token-list`;
    list.className = "rookieui-shell__prompt-workbench-token-list";
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
      row.className = "rookieui-shell__prompt-workbench-token";
      row.dataset.disabled = String(token.disabled);
      row.draggable = true;
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
      dragHandle.textContent = "⋮⋮";
      row.appendChild(dragHandle);

      const valueInput = document.createElement("input");
      valueInput.type = "text";
      valueInput.className = "rookieui-shell__input rookieui-shell__prompt-workbench-token-input";
      valueInput.value = token.text;
      valueInput.addEventListener("change", () => {
        token.text = String(valueInput.value ?? "").trim();
        rebuildPromptFromEditor("Edited prompt token");
      });
      row.appendChild(valueInput);

      const controls = document.createElement("div");
      controls.className = "rookieui-shell__prompt-workbench-token-actions";
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

      const deleteButton = createActionButton(`${idPrefix}-token-delete-${index}`, "Delete");
      deleteButton.addEventListener("click", () => {
        tokens.splice(index, 1);
        rebuildPromptFromEditor("Deleted prompt token");
      });
      controls.appendChild(deleteButton);

      const favoriteButton = createActionButton(`${idPrefix}-token-favorite-${index}`, "Favorite");
      favoriteButton.addEventListener("click", () => {
        const item = {
          label: token.text,
          prompt_text: token.text,
          tag_tokens: [token.text],
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

      const blacklistButton = createActionButton(`${idPrefix}-token-blacklist-${index}`, "Blacklist");
      blacklistButton.addEventListener("click", () => {
        addTokenToBlacklist(token.text);
      });
      controls.appendChild(blacklistButton);

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
        button.textContent = String(entry?.label ?? entry?.title ?? entry?.id ?? fragmentBuilder(entry));
        button.addEventListener("click", () => {
          appendPromptFragment(fragmentBuilder(entry), {
            statusMessage: `Inserted ${String(entry?.label ?? entry?.title ?? entry?.id ?? "catalog entry")}`,
          });
        });
        chipGrid.appendChild(button);
      });
    };

    groups.forEach((group, groupIndex) => {
      renderChipRow(
        String(group?.title ?? `Group ${groupIndex + 1}`),
        Array.isArray(group?.tags) ? group.tags.map((tag) => ({ id: tag, label: tag })) : [],
        (entry) => String(entry?.label ?? ""),
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

  function renderFormatPane() {
    clearChildren(formatPane);
    const heading = document.createElement("div");
    heading.className = "rookieui-shell__prompt-workbench-pane-header";
    formatPane.appendChild(heading);
    appendTextElement(heading, "h6", "rookieui-shell__prompt-workbench-pane-title", "Formatting and Blacklist");

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
      return;
    }

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

  function syncUi() {
    const state = getActiveState();
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
        editorCache.set(namespace, parsePromptTokens(nextState.draft_prompt));
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

  async function ensureResourcesLoaded() {
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
          updateStatus("Prompt Workbench resources loaded");
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
        onStatusMessage?.("Opened Prompt Workbench");
      } else {
        onStatusMessage?.("Collapsed Prompt Workbench");
      }
    });
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
      editorCache.set(namespace, parsePromptTokens(cachedState.draft_prompt));
      if (scope === activeScope) {
        queueStatePersist();
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
