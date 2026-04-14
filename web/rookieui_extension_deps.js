import { importRevisionedModule } from "./rookieui_asset_revision.js";

const [apiModule, hostSurfaceModule, sidebarShellModule] = await Promise.all([
  importRevisionedModule("./rookieui_api.js", import.meta.url),
  importRevisionedModule("./rookieui_host_surface.js", import.meta.url),
  importRevisionedModule("./rookieui_sidebar_shell.js", import.meta.url),
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
  fetchRookieUIPresets,
  fetchRookieUIQueue,
  fetchRookieUIQueueJob,
  inspectRookieUIPngInfo,
  submitRookieUIExtras,
  submitRookieUIImg2Img,
  submitRookieUITxt2Img,
} = apiModule;

export const {
  describeHostSurface,
  detectHostSurface,
  isHostSurfaceSupported,
} = hostSurfaceModule;

export const { renderRookieUISidebar } = sidebarShellModule;
