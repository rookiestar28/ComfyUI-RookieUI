export const IMG2IMG_GENERATION_MODE_DEFINITIONS = Object.freeze([
  Object.freeze({ id: "img2img", label: "img2img" }),
  Object.freeze({ id: "sketch", label: "Sketch" }),
  Object.freeze({ id: "inpaint", label: "Inpaint" }),
  Object.freeze({ id: "inpaint_sketch", label: "Inpaint sketch" }),
  Object.freeze({ id: "inpaint_upload", label: "Inpaint upload" }),
  Object.freeze({ id: "batch", label: "Batch" }),
]);

function normalizeMode(value) {
  return String(value ?? "").trim().toLowerCase();
}

export function createImg2ImgModeRouter({
  modeInput,
  definitions = IMG2IMG_GENERATION_MODE_DEFINITIONS,
  defaultTabId = "img2img",
  resolveExecutionMode = null,
  onTabChange = null,
} = {}) {
  const normalizedDefinitions = Array.isArray(definitions)
    ? definitions.filter((entry) => entry && typeof entry.id === "string")
    : IMG2IMG_GENERATION_MODE_DEFINITIONS;
  const knownTabIds = new Set(normalizedDefinitions.map((entry) => normalizeMode(entry.id)));
  const normalizedDefault = knownTabIds.has(normalizeMode(defaultTabId)) ? normalizeMode(defaultTabId) : "img2img";
  const state = {
    activeTabId: normalizedDefault,
  };

  const notifyTabChange = (tabId) => {
    const executionMode =
      typeof resolveExecutionMode === "function" ? String(resolveExecutionMode(tabId) ?? tabId).trim().toLowerCase() : tabId;
    if (typeof onTabChange === "function") {
      onTabChange({
        tabId,
        modeValue: tabId,
        executionMode,
      });
    }
  };

  const syncFromModeValue = () => {
    const currentValue = normalizeMode(modeInput?.value);
    const resolvedTabId = knownTabIds.has(currentValue) ? currentValue : normalizedDefault;
    state.activeTabId = resolvedTabId;
    if (modeInput && modeInput.value !== resolvedTabId) {
      modeInput.value = resolvedTabId;
    }
    notifyTabChange(resolvedTabId);
    return resolvedTabId;
  };

  const activateSubtab = (tabId, options = {}) => {
    const candidate = normalizeMode(tabId);
    const resolvedTabId = knownTabIds.has(candidate) ? candidate : normalizedDefault;
    state.activeTabId = resolvedTabId;
    if (modeInput && modeInput.value !== resolvedTabId) {
      modeInput.value = resolvedTabId;
    }
    notifyTabChange(resolvedTabId);
    if (modeInput && options.dispatchChange !== false) {
      // IMPORTANT: mode input remains backend source-of-truth; subtab activation must emit the same change path as legacy select UX.
      modeInput.dispatchEvent(new Event("change", { bubbles: true }));
    }
    return resolvedTabId;
  };

  if (modeInput) {
    syncFromModeValue();
  }

  return {
    definitions: normalizedDefinitions.map((entry) => ({ ...entry })),
    activateSubtab,
    getActiveTabId() {
      return state.activeTabId;
    },
    syncFromModeValue,
  };
}
