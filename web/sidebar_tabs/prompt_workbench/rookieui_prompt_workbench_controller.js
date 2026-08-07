const SUPPORTED_SCOPES = Object.freeze(["prompt", "negative"]);
const SUPPORTED_PANELS = Object.freeze(["editor", "history", "favorites", "catalog", "assist", "format"]);
const SUPPORTED_COLLECTIONS = Object.freeze(["history", "favorites"]);

function cloneValue(value) {
  if (typeof structuredClone === "function") {
    return structuredClone(value);
  }
  if (value === undefined) {
    return undefined;
  }
  return JSON.parse(JSON.stringify(value));
}

function normalizeText(value) {
  return String(value ?? "").trim();
}

function normalizeScope(value, fallback = "prompt") {
  const normalized = normalizeText(value).toLowerCase();
  return SUPPORTED_SCOPES.includes(normalized) ? normalized : fallback;
}

function normalizePanel(value, fallback = "editor") {
  const normalized = normalizeText(value).toLowerCase();
  return SUPPORTED_PANELS.includes(normalized) ? normalized : fallback;
}

function normalizeNamespaceMap(namespaces = {}) {
  return Object.freeze({
    prompt: normalizeText(namespaces.prompt),
    negative: normalizeText(namespaces.negative),
  });
}

/**
 * @param {unknown} namespace
 * @param {{workbench_open?: unknown, active_panel?: unknown, draft_prompt?: unknown, selected_entry_id?: unknown}} payload
 */
function defaultNormalizeStatePayload(namespace, payload = {}) {
  const source = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
  return {
    namespace,
    workbench_open: Boolean(source.workbench_open),
    active_panel: normalizePanel(source.active_panel),
    draft_prompt: String(source.draft_prompt ?? ""),
    selected_entry_id: String(source.selected_entry_id ?? ""),
  };
}

/**
 * Own Prompt Workbench state and payload transitions without importing DOM or
 * host APIs. The shell is a renderer/compatibility facade over this boundary.
 */
export function createPromptWorkbenchController({
  namespaces = {},
  fixedScope = "",
  initialConfig = {},
  initialBlacklist = {},
  normalizeStatePayload = defaultNormalizeStatePayload,
} = {}) {
  const namespaceMap = normalizeNamespaceMap(namespaces);
  const normalizedFixedScope = SUPPORTED_SCOPES.includes(normalizeText(fixedScope).toLowerCase())
    ? normalizeScope(fixedScope)
    : "";
  const data = {
    config: cloneValue(initialConfig && typeof initialConfig === "object" ? initialConfig : {}),
    blacklist: cloneValue(initialBlacklist && typeof initialBlacklist === "object" ? initialBlacklist : {}),
    state: new Map(),
    editor: new Map(),
    history: new Map(),
    favorites: new Map(),
  };
  let activeScope = normalizedFixedScope || "prompt";
  let activePanel = "editor";
  let destroyed = false;
  let asyncEpoch = 0;

  const namespaceForScope = (scope) => namespaceMap[normalizeScope(scope)] || "";
  const assertLive = () => !destroyed;
  const normalizeState = (namespace, payload) => {
    const normalized = normalizeStatePayload(namespace, payload);
    return normalized && typeof normalized === "object" && !Array.isArray(normalized)
      ? cloneValue(normalized)
      : defaultNormalizeStatePayload(namespace, payload);
  };

  function ensureSurfaceState(namespace, fallback = {}) {
    const normalizedNamespace = normalizeText(namespace);
    if (!normalizedNamespace || !assertLive()) {
      return defaultNormalizeStatePayload(normalizedNamespace, fallback);
    }
    if (!data.state.has(normalizedNamespace)) {
      data.state.set(normalizedNamespace, normalizeState(normalizedNamespace, fallback));
    }
    return cloneValue(data.state.get(normalizedNamespace));
  }

  return {
    get namespaceMap() {
      return namespaceMap;
    },
    get configState() {
      return data.config;
    },
    get blacklistState() {
      return data.blacklist;
    },
    get stateCache() {
      return data.state;
    },
    get editorCache() {
      return data.editor;
    },
    get historyCache() {
      return data.history;
    },
    get favoritesCache() {
      return data.favorites;
    },
    get fixedScope() {
      return normalizedFixedScope;
    },
    isDestroyed() {
      return destroyed;
    },
    getActiveScope() {
      return activeScope;
    },
    setActiveScope(scope) {
      if (normalizedFixedScope) {
        activeScope = normalizedFixedScope;
      } else {
        activeScope = normalizeScope(scope, activeScope);
      }
      return activeScope;
    },
    getActiveNamespace() {
      return namespaceForScope(activeScope);
    },
    getNamespaceForScope(scope) {
      return namespaceForScope(scope);
    },
    getActivePanel() {
      return activePanel;
    },
    setActivePanel(panel) {
      activePanel = normalizePanel(panel, activePanel);
      return activePanel;
    },
    getSurfaceState(namespace, fallback = {}) {
      return ensureSurfaceState(namespace, fallback);
    },
    setSurfaceState(namespace, payload = {}) {
      const normalizedNamespace = normalizeText(namespace);
      if (!normalizedNamespace || !assertLive()) {
        return defaultNormalizeStatePayload(normalizedNamespace, payload);
      }
      const nextState = normalizeState(normalizedNamespace, payload);
      data.state.set(normalizedNamespace, nextState);
      return cloneValue(nextState);
    },
    getConfigSnapshot() {
      return cloneValue(data.config);
    },
    updateConfig(patch = {}) {
      if (assertLive() && patch && typeof patch === "object" && !Array.isArray(patch)) {
        Object.assign(data.config, cloneValue(patch));
      }
      return cloneValue(data.config);
    },
    getBlacklistSnapshot() {
      return cloneValue(data.blacklist);
    },
    updateBlacklist(patch = {}) {
      if (assertLive() && patch && typeof patch === "object" && !Array.isArray(patch)) {
        Object.assign(data.blacklist, cloneValue(patch));
      }
      return cloneValue(data.blacklist);
    },
    getCollection(collectionName, namespace) {
      if (!SUPPORTED_COLLECTIONS.includes(collectionName) || !assertLive()) {
        return [];
      }
      return cloneValue(data[collectionName].get(normalizeText(namespace)) ?? []);
    },
    replaceCollection(collectionName, namespace, entries) {
      if (!SUPPORTED_COLLECTIONS.includes(collectionName) || !assertLive()) {
        return [];
      }
      const normalizedNamespace = normalizeText(namespace);
      const nextEntries = Array.isArray(entries) ? cloneValue(entries) : [];
      data[collectionName].set(normalizedNamespace, nextEntries);
      return cloneValue(nextEntries);
    },
    beginAsyncEpoch() {
      if (!assertLive()) {
        return asyncEpoch;
      }
      asyncEpoch += 1;
      return asyncEpoch;
    },
    isAsyncEpochCurrent(epoch) {
      return !destroyed && epoch === asyncEpoch;
    },
    invalidateAsyncEpoch() {
      asyncEpoch += 1;
      return asyncEpoch;
    },
    destroy() {
      if (destroyed) {
        return;
      }
      destroyed = true;
      asyncEpoch += 1;
      data.state.clear();
      data.editor.clear();
      data.history.clear();
      data.favorites.clear();
      Object.keys(data.config).forEach((key) => delete data.config[key]);
      Object.keys(data.blacklist).forEach((key) => delete data.blacklist[key]);
    },
  };
}

export { SUPPORTED_PANELS, SUPPORTED_SCOPES };
