export function createPromptWorkbenchDataLoader({
  bootstrapState,
  controller,
  namespaceMap,
  fixedScope,
  configState,
  blacklistState,
  stateCache,
  editorCache,
  historyCache,
  favoritesCache,
  normalizeStatePayload,
  normalizePromptEntry,
  parsePromptTokens,
  normalizeLanguageCode,
  getNamespaceInput,
  getActiveScope,
  setActiveScope,
  isLive,
  isAsyncEpochLive,
  updateStatus,
  syncUi,
} = {}) {
  let stateReadyPromise = null;
  let resourcesReadyPromise = null;
  let resourcesLoaded = false;
  let providersPayload = null;
  let catalogPayload = null;

  async function ensureStateLoaded() {
    if (stateReadyPromise) return stateReadyPromise;
    const requestEpoch = controller.beginAsyncEpoch();
    const namespacesToLoad = Object.values(namespaceMap).filter(Boolean);
    stateReadyPromise = Promise.all(
      namespacesToLoad.map(async (namespace) => {
        const result = await bootstrapState?.fetchPromptWorkbenchStateRequest?.(namespace);
        if (!isAsyncEpochLive(requestEpoch)) return;
        const nextState = normalizeStatePayload(
          namespace,
          result?.data?.state ?? { draft_prompt: getNamespaceInput(namespace)?.value ?? "" },
        );
        if (!nextState.draft_prompt) nextState.draft_prompt = String(getNamespaceInput(namespace)?.value ?? "");
        stateCache.set(namespace, nextState);
        editorCache.set(namespace, parsePromptTokens(nextState.draft_prompt, { scope: getActiveScope() }));
      }),
    )
      .then(() => {
        if (!isAsyncEpochLive(requestEpoch)) return;
        if (fixedScope) {
          setActiveScope(fixedScope);
          return;
        }
        const promptState = stateCache.get(namespaceMap.prompt);
        const negativeState = stateCache.get(namespaceMap.negative);
        if (!promptState?.workbench_open && negativeState?.workbench_open) setActiveScope("negative");
      })
      .finally(() => {
        if (isLive()) syncUi();
      });
    return stateReadyPromise;
  }

  async function ensureResourcesLoaded({ statusMessage = "Prompt Workbench resources loaded" } = {}) {
    if (resourcesReadyPromise) return resourcesReadyPromise;
    const requestEpoch = controller.beginAsyncEpoch();
    resourcesReadyPromise = Promise.all([
      bootstrapState?.fetchPromptWorkbenchProvidersRequest?.(),
      bootstrapState?.fetchPromptWorkbenchCatalogRequest?.(normalizeLanguageCode(configState?.language ?? "en")),
      bootstrapState?.fetchPromptWorkbenchHistoryRequest?.(namespaceMap.prompt),
      bootstrapState?.fetchPromptWorkbenchHistoryRequest?.(namespaceMap.negative),
      bootstrapState?.fetchPromptWorkbenchFavoritesRequest?.(namespaceMap.prompt),
      bootstrapState?.fetchPromptWorkbenchFavoritesRequest?.(namespaceMap.negative),
      bootstrapState?.fetchPromptWorkbenchBlacklistRequest?.(),
    ])
      .then(([providersResult, catalogResult, promptHistory, negativeHistory, promptFavorites, negativeFavorites, blacklistResult]) => {
        if (!isAsyncEpochLive(requestEpoch)) return;
        providersPayload = providersResult?.data ?? null;
        catalogPayload = catalogResult?.data ?? null;
        historyCache.set(namespaceMap.prompt, Array.isArray(promptHistory?.data?.items) ? promptHistory.data.items.map(normalizePromptEntry) : []);
        historyCache.set(namespaceMap.negative, Array.isArray(negativeHistory?.data?.items) ? negativeHistory.data.items.map(normalizePromptEntry) : []);
        favoritesCache.set(namespaceMap.prompt, Array.isArray(promptFavorites?.data?.items) ? promptFavorites.data.items.map(normalizePromptEntry) : []);
        favoritesCache.set(namespaceMap.negative, Array.isArray(negativeFavorites?.data?.items) ? negativeFavorites.data.items.map(normalizePromptEntry) : []);
        if (blacklistResult?.data?.blacklist) Object.assign(blacklistState, blacklistResult.data.blacklist);
        resourcesLoaded = true;
        updateStatus(statusMessage);
      })
      .catch(() => {
        if (isLive()) updateStatus("Prompt Workbench resources are using fallback data");
      })
      .finally(() => {
        if (isLive()) syncUi();
      });
    return resourcesReadyPromise;
  }

  return {
    ensureStateLoaded,
    ensureResourcesLoaded,
    resetResources() {
      resourcesReadyPromise = null;
      resourcesLoaded = false;
      providersPayload = null;
      catalogPayload = null;
    },
    get resourcesLoaded() {
      return resourcesLoaded;
    },
    get providersPayload() {
      return providersPayload;
    },
    get catalogPayload() {
      return catalogPayload;
    },
    getTranslationProviders() {
      const providers = providersPayload?.surfaces?.translation?.providers;
      return Array.isArray(providers) ? providers.filter((entry) => entry?.execution_state === "shipped") : [];
    },
    getAiAssistProviders() {
      const providers = providersPayload?.surfaces?.ai_assist?.providers;
      return Array.isArray(providers) ? providers.filter((entry) => entry?.execution_state === "shipped") : [];
    },
    setCatalogPayload(payload) {
      catalogPayload = payload ?? null;
    },
  };
}
