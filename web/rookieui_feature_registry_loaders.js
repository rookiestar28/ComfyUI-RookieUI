/** @typedef {import("./types/rookieui_frontend").RookieUIBootstrapLoaders} RookieUIBootstrapLoaders */

export async function buildDefaultBootstrapLoaders() {
  // IMPORTANT: keep the host-specific revisioned loader import lazy so injected-loader consumers
  // can reuse the bootstrap contract without pulling ComfyUI runtime asset wiring into spikes/tests.
  const {
    fetchRookieUIADetailerCatalog,
    fetchRookieUICapabilities,
    fetchRookieUICompatibility,
    fetchRookieUIControlNetModels,
    fetchRookieUIControlNetModules,
    fetchRookieUIControlNetTypes,
    fetchRookieUIModels,
    fetchRookieUIPromptWorkbenchConfig,
    fetchRookieUIPresets,
    fetchRookieUIQueue,
    fetchRookieUIXYZPlotAxes,
  } = await import("./rookieui_extension_deps.js");
  /** @type {RookieUIBootstrapLoaders} */
  return {
    capabilities: (fetchImpl) => fetchRookieUICapabilities(fetchImpl),
    compatibility: (fetchImpl) => fetchRookieUICompatibility(fetchImpl),
    models: (fetchImpl) => fetchRookieUIModels(fetchImpl),
    presets: (fetchImpl) => fetchRookieUIPresets(fetchImpl),
    controlnetModels: (fetchImpl) => fetchRookieUIControlNetModels(fetchImpl),
    controlnetModules: (fetchImpl) => fetchRookieUIControlNetModules(fetchImpl),
    controlnetTypes: (fetchImpl) => fetchRookieUIControlNetTypes(fetchImpl),
    adetailerCatalog: (fetchImpl) => fetchRookieUIADetailerCatalog(fetchImpl),
    promptWorkbench: (fetchImpl) => fetchRookieUIPromptWorkbenchConfig(fetchImpl),
    xyzPlot: (fetchImpl) => fetchRookieUIXYZPlotAxes(fetchImpl),
    queue: (fetchImpl, { clientId }) => fetchRookieUIQueue(fetchImpl, { clientId }),
  };
}
