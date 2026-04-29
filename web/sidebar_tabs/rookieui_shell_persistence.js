const ROOKIEUI_SHELL_STATE_VERSION = 1;
const memoryStateByKey = new Map();

function clonePlainObject(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }
  return JSON.parse(JSON.stringify(value));
}

function normalizeStoredState(candidate) {
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) {
    return { version: ROOKIEUI_SHELL_STATE_VERSION, activeTopTabId: "", panes: {} };
  }
  const panes = candidate.panes && typeof candidate.panes === "object" && !Array.isArray(candidate.panes)
    ? clonePlainObject(candidate.panes)
    : {};
  return {
    version: ROOKIEUI_SHELL_STATE_VERSION,
    activeTopTabId: typeof candidate.activeTopTabId === "string" ? candidate.activeTopTabId : "",
    panes,
  };
}

function readStorageState(storage, key) {
  if (!storage?.getItem) {
    return null;
  }
  try {
    const raw = storage.getItem(key);
    if (!raw) {
      return null;
    }
    return normalizeStoredState(JSON.parse(raw));
  } catch (_error) {
    return null;
  }
}

function writeStorageState(storage, key, state) {
  if (!storage?.setItem) {
    return;
  }
  try {
    storage.setItem(key, JSON.stringify(state));
  } catch (_error) {
    // Storage can be unavailable in private or embedded host contexts.
  }
}

function resolveStorage(container) {
  try {
    return container?.ownerDocument?.defaultView?.sessionStorage ?? globalThis.sessionStorage ?? null;
  } catch (_error) {
    return null;
  }
}

function canUseStorage(storage) {
  if (!storage?.setItem || !storage?.removeItem) {
    return false;
  }
  try {
    const probeKey = "rookieui:shell-state:probe";
    storage.setItem(probeKey, "1");
    storage.removeItem(probeKey);
    return true;
  } catch (_error) {
    return false;
  }
}

function resolveStateKey(bootstrapState) {
  const clientId = String(bootstrapState?.clientId ?? "anonymous").trim() || "anonymous";
  return `rookieui:shell-state:v${ROOKIEUI_SHELL_STATE_VERSION}:${clientId}`;
}

function setElementValue(element, value) {
  if (!element || value === undefined || value === null) {
    return;
  }
  if (element.type === "checkbox") {
    element.checked = Boolean(value);
    return;
  }
  if (element.tagName === "SELECT") {
    const nextValue = String(value);
    const hasOption = Array.from(element.options ?? []).some((option) => option.value === nextValue);
    if (!hasOption) {
      return;
    }
  }
  element.value = String(value);
}

export function snapshotElementState(elements) {
  const snapshot = {};
  Object.entries(elements).forEach(([key, element]) => {
    if (!element || !element.id || element.type === "file") {
      return;
    }
    snapshot[key] = element.type === "checkbox" ? Boolean(element.checked) : String(element.value ?? "");
  });
  return snapshot;
}

export function restoreElementState(elements, snapshot, syncBoundControls = null) {
  if (!snapshot || typeof snapshot !== "object") {
    return;
  }
  Object.entries(snapshot).forEach(([key, value]) => {
    if (!(key in elements)) {
      return;
    }
    const element = elements[key];
    if (!element || element.type === "file") {
      return;
    }
    setElementValue(element, value);
    if (element.type === "range") {
      element.__syncSliderVisual?.();
    }
  });
  syncBoundControls?.(Object.values(elements));
}

export function createShellPersistenceController(container, bootstrapState) {
  const storage = resolveStorage(container);
  const storageUsable = canUseStorage(storage);
  const key = resolveStateKey(bootstrapState);
  let state = normalizeStoredState(
    storageUsable ? readStorageState(storage, key) : memoryStateByKey.get(key),
  );

  const commit = () => {
    const stored = normalizeStoredState(state);
    memoryStateByKey.set(key, clonePlainObject(stored));
    if (storageUsable) {
      writeStorageState(storage, key, stored);
    }
  };

  return Object.freeze({
    readActiveTopTab() {
      return state.activeTopTabId;
    },
    writeActiveTopTab(tabId) {
      state.activeTopTabId = String(tabId ?? "").trim();
      commit();
    },
    readPaneSnapshot(paneId) {
      const normalizedId = String(paneId ?? "").trim();
      return clonePlainObject(state.panes?.[normalizedId]);
    },
    writePaneSnapshot(paneId, snapshot) {
      const normalizedId = String(paneId ?? "").trim();
      if (!normalizedId) {
        return;
      }
      state = normalizeStoredState({
        ...state,
        panes: {
          ...state.panes,
          [normalizedId]: clonePlainObject(snapshot),
        },
      });
      commit();
    },
  });
}

export function installPaneStateLock(formRegistry, paneId, elements, afterRestore = null) {
  const shellPersistence = formRegistry?.__shellPersistence ?? null;
  const syncBoundControls = formRegistry?.__syncBoundControls ?? null;
  const storedSnapshot = shellPersistence?.readPaneSnapshot?.(paneId);
  let snapshot = Object.keys(storedSnapshot ?? {}).length ? storedSnapshot : snapshotElementState(elements);
  const capture = () => {
    snapshot = snapshotElementState(elements);
    shellPersistence?.writePaneSnapshot?.(paneId, snapshot);
  };
  const restore = () => {
    restoreElementState(elements, snapshot, syncBoundControls);
    if (typeof afterRestore === "function") {
      afterRestore();
    }
  };

  Object.values(elements).forEach((element) => {
    if (!element || typeof element.addEventListener !== "function" || element.type === "file") {
      return;
    }
    element.addEventListener("input", capture);
    element.addEventListener("change", capture);
  });

  if (formRegistry && paneId) {
    const shellStateContract = formRegistry.__shellStateContract;
    if (shellStateContract?.registerPaneStateLock) {
      shellStateContract.registerPaneStateLock(paneId, { capture, restore });
    } else {
      formRegistry.__paneStateLocks ??= {};
      formRegistry.__paneStateLocks[paneId] = { capture, restore };
    }
  }
  if (storedSnapshot && Object.keys(storedSnapshot).length) {
    restore();
  } else {
    capture();
  }
  return { capture, restore };
}
