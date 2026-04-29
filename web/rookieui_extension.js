import {
  createPromptWorkbenchRequestBindings,
  createXYZPlotRequestBindings,
  fetchRookieUIADetailerCatalog,
  fetchRookieUIControlNetModels,
  fetchRookieUIControlNetModules,
  fetchRookieUIControlNetTypes,
  fetchRookieUIHistoryPrompt,
  fetchRookieUIQueue,
  fetchRookieUIQueueJob,
  detectRookieUIControlNet,
  inspectRookieUIPngInfo,
  submitRookieUIExtras,
  submitRookieUIImg2Img,
  submitRookieUITxt2Img,
  describeHostSurface,
  detectHostSurface,
  installA1111CanvasImportParityPatch,
  isHostSurfaceSupported,
  renderRookieUISidebar,
} from "./rookieui_extension_deps.js";
import { applyRevisionToUrl } from "./rookieui_asset_revision.js";
import { loadRookieUIBootstrapData } from "./rookieui_feature_registry.js";
/** @typedef {import("./types/rookieui_frontend").RookieUIRegisterExtensionOptions} RookieUIRegisterExtensionOptions */

const ROOKIEUI_SIDEBAR_MIN_WIDTH_PX = 980;

function normalizeClientId(rawClientId) {
  if (typeof rawClientId !== "string") {
    return "";
  }
  const normalized = rawClientId.trim();
  if (!normalized || /\s/.test(normalized)) {
    return "";
  }
  return normalized;
}

function createRookieUIClientId(windowRef, runtimeApi = null) {
  const apiClientId = normalizeClientId(runtimeApi?.clientId ?? windowRef?.app?.api?.clientId);
  if (apiClientId) {
    return apiClientId;
  }

  const sessionClientId = normalizeClientId(windowRef?.sessionStorage?.getItem?.("clientId"));
  if (sessionClientId) {
    return sessionClientId;
  }
  if (typeof globalThis?.crypto?.randomUUID === "function") {
    return `rookieui-${globalThis.crypto.randomUUID()}`;
  }
  const suffix = Math.random().toString(36).slice(2, 12);
  return `rookieui-${Date.now().toString(36)}-${suffix}`;
}

export function createRookieUIHostFetch(fetchImpl = globalThis.fetch, runtimeApi = null) {
  if (typeof runtimeApi?.fetchApi === "function") {
    // CRITICAL: use ComfyUI's API resolver when available; root-relative fetch breaks under proxied or subpath-mounted hosts.
    return (path, options = {}) => runtimeApi.fetchApi(path, options);
  }
  return fetchImpl;
}

function enforceSidebarMinWidth(container) {
  if (!container?.style) {
    return;
  }

  const applyMinWidth = () => {
    // CRITICAL: SplitterPanel controls the actual sidebar width; inner content min-width alone still clips.
    const sidePanel = container.closest(".side-bar-panel");
    const closestSplitterPanel = container.closest(".p-splitterpanel");
    const splitterPanel = sidePanel instanceof HTMLElement ? sidePanel : closestSplitterPanel;
    if (splitterPanel instanceof HTMLElement) {
      splitterPanel.style.minWidth = `${ROOKIEUI_SIDEBAR_MIN_WIDTH_PX}px`;
      if (splitterPanel.getBoundingClientRect?.().width < ROOKIEUI_SIDEBAR_MIN_WIDTH_PX) {
        // IMPORTANT: Min-width alone does not reliably expand an already-mounted ComfyUI Splitter panel.
        splitterPanel.style.width = `${ROOKIEUI_SIDEBAR_MIN_WIDTH_PX}px`;
        splitterPanel.style.flexBasis = `${ROOKIEUI_SIDEBAR_MIN_WIDTH_PX}px`;
      }
    }

    const sidebarContent = container.closest(".sidebar-content-container");
    if (sidebarContent instanceof HTMLElement) {
      sidebarContent.style.minWidth = `${ROOKIEUI_SIDEBAR_MIN_WIDTH_PX}px`;
      if (sidebarContent.getBoundingClientRect?.().width < ROOKIEUI_SIDEBAR_MIN_WIDTH_PX) {
        sidebarContent.style.width = `${ROOKIEUI_SIDEBAR_MIN_WIDTH_PX}px`;
      }
    }

    container.style.minWidth = `${ROOKIEUI_SIDEBAR_MIN_WIDTH_PX}px`;
  };

  applyMinWidth();
  if (typeof requestAnimationFrame === "function") {
    requestAnimationFrame(applyMinWidth);
  } else {
    setTimeout(applyMinWidth, 0);
  }
}

const ROOKIEUI_STYLESHEETS = [["rookieui-styles", "./rookieui.css"], ["rookieui-styles-foundation", "./rookieui_shell_foundation.css"], ["rookieui-styles-panes", "./rookieui_panes.css"]];
function ensureCssInjected(documentRef) {
  if (!documentRef?.head) return;
  for (const [id, specifier] of ROOKIEUI_STYLESHEETS) {
    if (documentRef.getElementById(id)) continue;
    const link = Object.assign(documentRef.createElement("link"), {
      id,
      rel: "stylesheet",
      href: applyRevisionToUrl(specifier, import.meta.url).href,
    });
    documentRef.head.appendChild(link);
  }
}

function installLegacyLauncher(documentRef, bootstrapState) {
  if (!documentRef || documentRef.getElementById("rookieui-legacy-launcher")) {
    return;
  }

  const button = documentRef.createElement("button");
  button.id = "rookieui-legacy-launcher";
  button.textContent = "RookieUI";

  const panel = documentRef.createElement("div");
  panel.id = "rookieui-legacy-panel";
  panel.hidden = true;

  button.addEventListener("click", () => {
    panel.hidden = !panel.hidden;
    if (!panel.hidden) {
      renderRookieUISidebar(panel, bootstrapState);
    }
  });

  documentRef.body.appendChild(button);
  documentRef.body.appendChild(panel);
}

/**
 * @param {RookieUIRegisterExtensionOptions} options
 * @returns {unknown}
 */
export function registerRookieUIBootstrapExtension({
  app,
  windowRef = globalThis.window,
  documentRef = globalThis.document,
  fetchImpl = globalThis.fetch,
} = {}) {
  if (!app?.registerExtension) {
    throw new Error("ComfyUI app.registerExtension is required.");
  }

  return app.registerExtension({
    name: "ComfyUI-RookieUI",
    async setup() {
      const runtimeApi = app?.api ?? windowRef?.app?.api ?? null;
      const apiFetch = createRookieUIHostFetch(fetchImpl, runtimeApi);
      const hostSurface = detectHostSurface(windowRef);
      const clientId = createRookieUIClientId(windowRef, runtimeApi);
      const bootstrapData = await loadRookieUIBootstrapData(apiFetch, { clientId });
      if (clientId && windowRef?.sessionStorage?.setItem) {
        try {
          // IMPORTANT: persist the active host client id so queue polling and runtime events stay on the same session boundary after host reconnects.
          windowRef.sessionStorage.setItem("clientId", clientId);
        } catch (_error) {
          // Ignore storage failures (e.g., private mode restrictions).
        }
      }
      ensureCssInjected(documentRef);
      const hostSurfaceSupported = isHostSurfaceSupported(hostSurface, bootstrapData.capabilities);

      const bootstrapState = {
        hostSurface,
        hostDescription: describeHostSurface(hostSurface),
        hostSurfaceSupported,
        extensionName: "ComfyUI-RookieUI",
        ...bootstrapData,
        clientId,
        runtimeApi,
        fetchQueueRequest: (scopeClientId = clientId) => fetchRookieUIQueue(apiFetch, { clientId: scopeClientId }),
        fetchQueueJobRequest: (promptId, scopeClientId = clientId) => fetchRookieUIQueueJob(promptId, { clientId: scopeClientId }, apiFetch),
        fetchPromptHistoryRequest: (promptId) => fetchRookieUIHistoryPrompt(promptId, apiFetch),
        submitTxt2ImgRequest: (payload) => submitRookieUITxt2Img(payload, apiFetch),
        submitImg2ImgRequest: (payload) => submitRookieUIImg2Img(payload, apiFetch),
        inspectPngInfoRequest: (payload) => inspectRookieUIPngInfo(payload, apiFetch),
        parsePngInfoRequest: (payload) => inspectRookieUIPngInfo(payload, apiFetch),
        submitExtrasRequest: (payload) => submitRookieUIExtras(payload, apiFetch),
        detectControlNetRequest: (payload) => detectRookieUIControlNet(payload, apiFetch),
        fetchControlNetModelListRequest: () => fetchRookieUIControlNetModels(apiFetch),
        fetchControlNetModuleListRequest: () => fetchRookieUIControlNetModules(apiFetch),
        fetchControlNetTypeListRequest: () => fetchRookieUIControlNetTypes(apiFetch),
        fetchADetailerCatalogRequest: () => fetchRookieUIADetailerCatalog(apiFetch),
        ...createPromptWorkbenchRequestBindings(apiFetch),
        ...createXYZPlotRequestBindings(apiFetch),
      };

      installA1111CanvasImportParityPatch({ app, windowRef, inspectPngInfoRequest: bootstrapState.inspectPngInfoRequest });

      if (app?.extensionManager?.registerSidebarTab) {
        app.extensionManager.registerSidebarTab({
          id: "comfyui-rookieui",
          icon: "pi pi-compass",
          title: "RookieUI",
          tooltip: "Rookie-friendly generation shell",
          type: "custom",
          render: (container) => {
            enforceSidebarMinWidth(container);
            renderRookieUISidebar(container, bootstrapState);
          },
        });
      } else {
        installLegacyLauncher(documentRef, bootstrapState);
      }

      windowRef.__ROOKIEUI_BOOTSTRAP__ = { ...bootstrapState };
    },
  });
}
