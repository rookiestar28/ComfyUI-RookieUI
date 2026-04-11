export function createShellStateEventContract(formRegistry) {
  if (!formRegistry || typeof formRegistry !== "object") {
    throw new TypeError("Shell state contract requires a mutable form registry object.");
  }

  formRegistry.__paneStateLocks ??= {};

  let activeTopTabId = "";
  let topTabController = null;

  const setActiveTopTab = (tabId) => {
    const normalized = String(tabId ?? "").trim();
    if (!normalized) {
      return "";
    }
    activeTopTabId = normalized;
    return activeTopTabId;
  };

  const registerTopTabController = (controller) => {
    topTabController = controller && typeof controller === "object" ? controller : null;
    formRegistry.__shellTabs = topTabController ?? {};
    return formRegistry.__shellTabs;
  };

  const activateTopTab = (tabId) => {
    const normalized = setActiveTopTab(tabId);
    if (!normalized) {
      return false;
    }
    topTabController?.activateTabById?.(normalized);
    return true;
  };

  const registerPaneStateLock = (paneId, lock) => {
    const normalizedId = String(paneId ?? "").trim();
    if (!normalizedId) {
      throw new TypeError("Pane state lock registration requires a pane id.");
    }
    if (!lock || typeof lock.capture !== "function" || typeof lock.restore !== "function") {
      throw new TypeError(`Pane state lock '${normalizedId}' requires capture() and restore() methods.`);
    }
    const normalizedLock = Object.freeze({
      capture: lock.capture,
      restore: lock.restore,
    });
    formRegistry.__paneStateLocks[normalizedId] = normalizedLock;
    return normalizedLock;
  };

  const getPaneStateLock = (paneId) => {
    const normalizedId = String(paneId ?? "").trim();
    if (!normalizedId) {
      return null;
    }
    return formRegistry.__paneStateLocks?.[normalizedId] ?? null;
  };

  const applyToForm = (targetKey, payload = {}, options = {}) => {
    const normalizedTarget = String(targetKey ?? "").trim();
    if (!normalizedTarget) {
      return false;
    }
    const targetForm = formRegistry?.[normalizedTarget];
    if (!targetForm || typeof targetForm.applyPayload !== "function") {
      return false;
    }
    if (options.activate !== false) {
      activateTopTab(normalizedTarget);
    }
    targetForm.applyPayload(payload);
    return true;
  };

  return Object.freeze({
    registerTopTabController,
    activateTopTab,
    setActiveTopTab,
    getActiveTopTab: () => activeTopTabId,
    registerPaneStateLock,
    getPaneStateLock,
    applyToForm,
    getRegistry: () => formRegistry,
  });
}
