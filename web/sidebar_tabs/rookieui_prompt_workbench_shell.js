function normalizeStatePayload(namespace, payload) {
  return {
    namespace,
    workbench_open: Boolean(payload?.workbench_open),
    active_panel: String(payload?.active_panel ?? "editor").trim() || "editor",
    draft_prompt: String(payload?.draft_prompt ?? ""),
    selected_entry_id: String(payload?.selected_entry_id ?? ""),
  };
}

function countPromptTokens(value) {
  const trimmed = String(value ?? "").trim();
  if (!trimmed) {
    return 0;
  }
  return trimmed.split(/[\s,]+/).filter(Boolean).length;
}

function setText(node, value) {
  if (node) {
    node.textContent = String(value ?? "");
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

  const config = bootstrapState?.promptWorkbench?.config ?? {};
  const namespaceMap = {
    prompt: String(namespaces?.prompt ?? "").trim(),
    negative: String(namespaces?.negative ?? "").trim(),
  };
  const inputMap = {
    prompt: promptInput,
    negative: negativePromptInput,
  };
  const stateCache = new Map();
  const historyCache = new Map();
  const favoritesCache = new Map();
  const dirtyTimers = new Map();
  let providersPayload = null;
  let catalogPayload = null;
  let stateReadyPromise = null;
  let resourcesReadyPromise = null;
  let activeScope = "prompt";
  let resourcesLoaded = false;

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
    "Foundation shell for prompt state, providers, catalogs, and later editor actions.",
  );

  const headerActions = document.createElement("div");
  headerActions.className = "rookieui-shell__prompt-workbench-header-actions";
  header.appendChild(headerActions);

  const toggleButton = createActionButton(`${idPrefix}-toggle`, "Open Workbench", "secondary");
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
      void ensureStateLoaded().then(() => {
        syncUi();
      });
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
  ["editor", "history", "favorites", "library"].forEach((panelId) => {
    const button = document.createElement("button");
    button.type = "button";
    button.id = `${idPrefix}-panel-${panelId}`;
    button.className = "rookieui-shell__prompt-workbench-panel-button";
    button.textContent = panelId === "library" ? "Library" : panelId.charAt(0).toUpperCase() + panelId.slice(1);
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

  const captureButton = createActionButton(`${idPrefix}-capture`, "Capture Current Text", "ghost");
  captureButton.addEventListener("click", () => {
    const state = getActiveState();
    const input = getActiveInput();
    state.draft_prompt = String(input?.value ?? "");
    queueStatePersist();
    syncUi();
    onStatusMessage?.("Captured current prompt text into Prompt Workbench state");
  });
  actionsRow.appendChild(captureButton);

  const restoreButton = createActionButton(`${idPrefix}-restore`, "Restore Draft", "ghost");
  restoreButton.addEventListener("click", () => {
    const state = getActiveState();
    const input = getActiveInput();
    if (input) {
      input.value = state.draft_prompt;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }
    onStatusMessage?.("Restored saved Prompt Workbench draft into the active prompt field");
  });
  actionsRow.appendChild(restoreButton);

  const details = document.createElement("div");
  details.className = "rookieui-shell__prompt-workbench-details";
  body.appendChild(details);

  const detailNodes = {
    scope: appendTextElement(details, "p", "rookieui-shell__prompt-workbench-detail", ""),
    draft: appendTextElement(details, "p", "rookieui-shell__prompt-workbench-detail", ""),
    panel: appendTextElement(details, "p", "rookieui-shell__prompt-workbench-detail", ""),
    status: appendTextElement(details, "p", "rookieui-shell__prompt-workbench-status", "Workbench shell ready"),
  };

  function getActiveNamespace() {
    return namespaceMap[activeScope];
  }

  function getActiveState() {
    const namespace = getActiveNamespace();
    if (!stateCache.has(namespace)) {
      stateCache.set(namespace, normalizeStatePayload(namespace, { draft_prompt: getActiveInput()?.value ?? "" }));
    }
    return stateCache.get(namespace);
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
    return Boolean(config?.ui_preferences?.default_open);
  }

  function syncUi() {
    const state = getActiveState();
    const language = String(config?.language ?? "en").trim() || "en";
    const historyItems = historyCache.get(getActiveNamespace()) ?? [];
    const favoriteItems = favoritesCache.get(getActiveNamespace()) ?? [];
    const blacklistEntries = Array.isArray(bootstrapState?.promptWorkbench?.blacklist?.entries)
      ? bootstrapState.promptWorkbench.blacklist.entries
      : [];
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

    setText(summaryNodes.state, state.workbench_open ? "Persisted open" : "Collapsed");
    setText(summaryNodes.providers, resourcesLoaded ? `${shippedProviders} shipped / ${language}` : "Lazy");
    setText(
      summaryNodes.catalogs,
      resourcesLoaded ? `${groupCount} groups / ${libraryCount} sections / ${extraNetworkCount} networks` : "Lazy",
    );
    setText(summaryNodes.history, `${historyItems.length} entries`);
    setText(summaryNodes.favorites, `${favoriteItems.length} entries`);
    setText(
      summaryNodes.blacklist,
      bootstrapState?.promptWorkbench?.blacklist?.enabled ? `${blacklistEntries.length} blocked` : "Disabled",
    );

    const promptUnits = countPromptTokens(state.draft_prompt);
    setText(detailNodes.scope, `${activeScope === "prompt" ? "Prompt" : "Negative Prompt"} namespace: ${getActiveNamespace()}`);
    setText(detailNodes.draft, `Saved draft: ${promptUnits} prompt units`);
    setText(detailNodes.panel, `Active panel: ${state.active_panel}`);
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
      bootstrapState?.fetchPromptWorkbenchCatalogRequest?.(config?.language ?? "en"),
      bootstrapState?.fetchPromptWorkbenchHistoryRequest?.(namespaceMap.prompt),
      bootstrapState?.fetchPromptWorkbenchHistoryRequest?.(namespaceMap.negative),
      bootstrapState?.fetchPromptWorkbenchFavoritesRequest?.(namespaceMap.prompt),
      bootstrapState?.fetchPromptWorkbenchFavoritesRequest?.(namespaceMap.negative),
    ])
      .then(([providersResult, catalogResult, promptHistory, negativeHistory, promptFavorites, negativeFavorites]) => {
        providersPayload = providersResult?.data ?? null;
        catalogPayload = catalogResult?.data ?? null;
        historyCache.set(namespaceMap.prompt, promptHistory?.data?.items ?? []);
        historyCache.set(namespaceMap.negative, negativeHistory?.data?.items ?? []);
        favoritesCache.set(namespaceMap.prompt, promptFavorites?.data?.items ?? []);
        favoritesCache.set(namespaceMap.negative, negativeFavorites?.data?.items ?? []);
        resourcesLoaded = true;
        setText(detailNodes.status, "Prompt Workbench resources loaded");
      })
      .catch(() => {
        setText(detailNodes.status, "Prompt Workbench resources are using fallback data");
      })
      .finally(() => {
        syncUi();
      });
    return resourcesReadyPromise;
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
      if (result?.ok === false) {
        setText(detailNodes.status, "Prompt Workbench state saved locally with fallback semantics");
      } else {
        setText(detailNodes.status, "Prompt Workbench state synchronized");
      }
      syncUi();
    }, 180);
    dirtyTimers.set(namespace, nextTimer);
  }

  toggleButton.addEventListener("click", () => {
    void ensureStateLoaded().then(async () => {
      const state = getActiveState();
      state.workbench_open = !state.workbench_open;
      queueStatePersist();
      syncUi();
      if (state.workbench_open) {
        await ensureResourcesLoaded();
        onStatusMessage?.("Opened Prompt Workbench shell");
      } else {
        onStatusMessage?.("Collapsed Prompt Workbench shell");
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
