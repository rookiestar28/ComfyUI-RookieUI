import { importRevisionedModule } from "./rookieui_asset_revision.js";

const [apiModule, hostSurfaceModule, sidebarShellModule, canvasImportModule] = await Promise.all([
  importRevisionedModule("./rookieui_api.js", import.meta.url),
  importRevisionedModule("./rookieui_host_surface.js", import.meta.url),
  importRevisionedModule("./rookieui_sidebar_shell.js", import.meta.url),
  importRevisionedModule("./rookieui_a1111_canvas_import.js", import.meta.url),
]);

export const {
  fetchRookieUICapabilities,
  fetchRookieUIADetailerCatalog,
  fetchRookieUICompatibility,
  fetchRookieUIControlNetModels,
  fetchRookieUIControlNetModules,
  fetchRookieUIControlNetTypes,
  fetchRookieUIHistoryPrompt,
  fetchRookieUIModels,
  fetchRookieUIPromptWorkbenchBlacklist,
  fetchRookieUIPromptWorkbenchCatalog,
  fetchRookieUIPromptWorkbenchConfig,
  fetchRookieUIPromptWorkbenchFavorites,
  fetchRookieUIPromptWorkbenchHistory,
  fetchRookieUIPromptWorkbenchProviders,
  fetchRookieUIPromptWorkbenchState,
  exportRookieUIPromptWorkbench,
  importRookieUIPromptWorkbench,
  fetchRookieUIPresets,
  fetchRookieUIQueue,
  fetchRookieUIQueueJob,
  fetchRookieUIXYZPlotAxes,
  fetchRookieUIXYZPlotSessions,
  fetchRookieUIXYZPlotSessionDetail,
  inspectRookieUIPngInfo,
  submitRookieUIExtras,
  submitRookieUIImg2Img,
  submitRookieUITxt2Img,
  submitRookieUIXYZPlotEstimate,
  submitRookieUIXYZPlotRun,
  assistRookieUIPromptWorkbench,
  cancelRookieUIXYZPlotSession,
  detectRookieUIControlNet,
  translateRookieUIPromptWorkbench,
  upsampleRookieUIPromptWorkbench,
  updateRookieUIPromptWorkbenchBlacklist,
  updateRookieUIPromptWorkbenchConfig,
  updateRookieUIPromptWorkbenchFavorites,
  updateRookieUIPromptWorkbenchHistory,
  updateRookieUIPromptWorkbenchState,
} = apiModule;

export function createPromptWorkbenchRequestBindings(fetchImpl) {
  return {
    fetchPromptWorkbenchStateRequest: (namespace) => fetchRookieUIPromptWorkbenchState(namespace, fetchImpl),
    updatePromptWorkbenchStateRequest: (namespace, state) =>
      updateRookieUIPromptWorkbenchState(namespace, state, fetchImpl),
    fetchPromptWorkbenchHistoryRequest: (namespace) => fetchRookieUIPromptWorkbenchHistory(namespace, fetchImpl),
    fetchPromptWorkbenchFavoritesRequest: (namespace) => fetchRookieUIPromptWorkbenchFavorites(namespace, fetchImpl),
    fetchPromptWorkbenchProvidersRequest: () => fetchRookieUIPromptWorkbenchProviders(fetchImpl),
    fetchPromptWorkbenchCatalogRequest: (language) => fetchRookieUIPromptWorkbenchCatalog(language, fetchImpl),
    exportPromptWorkbenchRequest: () => exportRookieUIPromptWorkbench(fetchImpl),
    importPromptWorkbenchRequest: (payload) => importRookieUIPromptWorkbench(payload, fetchImpl),
    translatePromptWorkbenchRequest: (payload) => translateRookieUIPromptWorkbench(payload, fetchImpl),
    assistPromptWorkbenchRequest: (payload) => assistRookieUIPromptWorkbench(payload, fetchImpl),
    upsamplePromptWorkbenchRequest: (payload) => upsampleRookieUIPromptWorkbench(payload, fetchImpl),
    fetchPromptWorkbenchBlacklistRequest: () => fetchRookieUIPromptWorkbenchBlacklist(fetchImpl),
    updatePromptWorkbenchBlacklistRequest: (blacklist) =>
      updateRookieUIPromptWorkbenchBlacklist(blacklist, fetchImpl),
    updatePromptWorkbenchConfigRequest: (config) => updateRookieUIPromptWorkbenchConfig(config, fetchImpl),
    updatePromptWorkbenchHistoryRequest: (namespace, action, payload) =>
      updateRookieUIPromptWorkbenchHistory(namespace, action, payload, fetchImpl),
    updatePromptWorkbenchFavoritesRequest: (namespace, action, payload) =>
      updateRookieUIPromptWorkbenchFavorites(namespace, action, payload, fetchImpl),
  };
}

export function createXYZPlotRequestBindings(fetchImpl) {
  return {
    fetchXYZPlotAxesRequest: () => fetchRookieUIXYZPlotAxes(fetchImpl),
    estimateXYZPlotRequest: (payload) => submitRookieUIXYZPlotEstimate(payload, fetchImpl),
    runXYZPlotRequest: (payload) => submitRookieUIXYZPlotRun(payload, fetchImpl),
    fetchXYZPlotSessionsRequest: (clientId) => fetchRookieUIXYZPlotSessions(fetchImpl, { clientId }),
    fetchXYZPlotSessionDetailRequest: (sessionId, clientId) =>
      fetchRookieUIXYZPlotSessionDetail(sessionId, { clientId }, fetchImpl),
    cancelXYZPlotSessionRequest: (sessionId, clientId) =>
      cancelRookieUIXYZPlotSession(sessionId, { clientId }, fetchImpl),
  };
}

export const {
  describeHostSurface,
  detectHostSurface,
  isHostSurfaceSupported,
} = hostSurfaceModule;

export const { renderRookieUISidebar } = sidebarShellModule;
export const { installA1111CanvasImportParityPatch } = canvasImportModule;
