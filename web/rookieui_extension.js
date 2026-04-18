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
  inspectRookieUIPngInfo,
  submitRookieUIExtras,
  submitRookieUIImg2Img,
  submitRookieUITxt2Img,
  describeHostSurface,
  detectHostSurface,
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

function ensureCssInjected(documentRef) {
  if (!documentRef?.head || documentRef.getElementById("rookieui-styles")) {
    return;
  }

  const link = documentRef.createElement("link");
  link.id = "rookieui-styles";
  link.rel = "stylesheet";
  const stylesheetUrl = applyRevisionToUrl("./rookieui.css", import.meta.url);
  // IMPORTANT: build the cache-busting query via URL APIs; inline template strings are treated as static literals by some test/tooling paths.
  link.href = stylesheetUrl.href;
  documentRef.head.appendChild(link);
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
      const hostSurface = detectHostSurface(windowRef);
      const clientId = createRookieUIClientId(windowRef, runtimeApi);
      const bootstrapData = await loadRookieUIBootstrapData(fetchImpl, { clientId });
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
        fetchQueueRequest: (scopeClientId = clientId) => fetchRookieUIQueue(fetchImpl, { clientId: scopeClientId }),
        fetchQueueJobRequest: (promptId, scopeClientId = clientId) =>
          fetchRookieUIQueueJob(promptId, { clientId: scopeClientId }, fetchImpl),
        fetchPromptHistoryRequest: (promptId) => fetchRookieUIHistoryPrompt(promptId, fetchImpl),
        submitTxt2ImgRequest: (payload) => submitRookieUITxt2Img(payload, fetchImpl),
        submitImg2ImgRequest: (payload) => submitRookieUIImg2Img(payload, fetchImpl),
        inspectPngInfoRequest: (payload) => inspectRookieUIPngInfo(payload, fetchImpl),
        parsePngInfoRequest: (payload) => inspectRookieUIPngInfo(payload, fetchImpl),
        submitExtrasRequest: (payload) => submitRookieUIExtras(payload, fetchImpl),
        fetchControlNetModelListRequest: () => fetchRookieUIControlNetModels(fetchImpl),
        fetchControlNetModuleListRequest: () => fetchRookieUIControlNetModules(fetchImpl),
        fetchControlNetTypeListRequest: () => fetchRookieUIControlNetTypes(fetchImpl),
        fetchADetailerCatalogRequest: () => fetchRookieUIADetailerCatalog(fetchImpl),
        ...createPromptWorkbenchRequestBindings(fetchImpl),
        ...createXYZPlotRequestBindings(fetchImpl),
      };

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

      windowRef.__ROOKIEUI_BOOTSTRAP__ = {
        ...bootstrapState,
      };
    },
  });
}
