import {
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
  describeHostSurface,
  detectHostSurface,
  isHostSurfaceSupported,
  renderRookieUISidebar,
} from "./rookieui_extension_deps.js";
import { applyRevisionToUrl } from "./rookieui_asset_revision.js";

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

function toStringArray(rawValue) {
  return Array.isArray(rawValue)
    ? rawValue.map((value) => String(value ?? "").trim()).filter(Boolean)
    : [];
}

function buildControlNetCatalog(modelResult, moduleResult, typeResult) {
  const modelList = toStringArray(modelResult?.data?.model_list);
  const moduleList = toStringArray(moduleResult?.data?.module_list);
  const controlTypeOrder = toStringArray(typeResult?.data?.control_type_order);
  const controlTypes =
    typeResult?.data?.control_types && typeof typeResult.data.control_types === "object"
      ? typeResult.data.control_types
      : {};

  return {
    source: String(typeResult?.data?.source ?? modelResult?.data?.source ?? moduleResult?.data?.source ?? "fallback"),
    contract:
      typeResult?.data?.contract ??
      modelResult?.data?.contract ??
      moduleResult?.data?.contract ?? {
        version: "r72-20260412",
        ui_variant: "integrated_sidebar_controlnet",
        unit_count: 3,
      },
    model_list: modelList,
    module_list: moduleList,
    control_type_order: controlTypeOrder,
    default_type: String(typeResult?.data?.default_type ?? "All"),
    default_module: String(moduleResult?.data?.default_module ?? "none"),
    default_model: String(modelResult?.data?.default_model ?? ""),
    control_types: controlTypes,
  };
}

function enforceSidebarMinWidth(container) {
  if (!container?.style) {
    return;
  }

  const applyMinWidth = () => {
    // CRITICAL: SplitterPanel controls the actual sidebar width; inner content min-width alone still clips.
    const sidePanel = container.closest(".side-bar-panel");
    const splitterPanel = sidePanel || container.closest(".p-splitterpanel");
    if (splitterPanel?.style) {
      splitterPanel.style.minWidth = `${ROOKIEUI_SIDEBAR_MIN_WIDTH_PX}px`;
      if (splitterPanel.getBoundingClientRect?.().width < ROOKIEUI_SIDEBAR_MIN_WIDTH_PX) {
        // IMPORTANT: Min-width alone does not reliably expand an already-mounted ComfyUI Splitter panel.
        splitterPanel.style.width = `${ROOKIEUI_SIDEBAR_MIN_WIDTH_PX}px`;
        splitterPanel.style.flexBasis = `${ROOKIEUI_SIDEBAR_MIN_WIDTH_PX}px`;
      }
    }

    const sidebarContent = container.closest(".sidebar-content-container");
    if (sidebarContent?.style) {
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
      const [
        capabilityResult,
        compatibilityResult,
        modelResult,
        presetResult,
        controlNetModelResult,
        controlNetModuleResult,
        controlNetTypeResult,
        adetailerCatalogResult,
      ] = await Promise.all([
        fetchRookieUICapabilities(fetchImpl),
        fetchRookieUICompatibility(fetchImpl),
        fetchRookieUIModels(fetchImpl),
        fetchRookieUIPresets(fetchImpl),
        fetchRookieUIControlNetModels(fetchImpl),
        fetchRookieUIControlNetModules(fetchImpl),
        fetchRookieUIControlNetTypes(fetchImpl),
        fetchRookieUIADetailerCatalog(fetchImpl),
      ]);
      const clientId = createRookieUIClientId(windowRef, runtimeApi);
      if (clientId && windowRef?.sessionStorage?.setItem) {
        try {
          // IMPORTANT: persist the active host client id so queue polling and runtime events stay on the same session boundary after host reconnects.
          windowRef.sessionStorage.setItem("clientId", clientId);
        } catch (_error) {
          // Ignore storage failures (e.g., private mode restrictions).
        }
      }
      const queueResult = await fetchRookieUIQueue(fetchImpl, { clientId });
      ensureCssInjected(documentRef);
      const hostSurfaceSupported = isHostSurfaceSupported(hostSurface, capabilityResult.data);
      const controlnetCatalog = buildControlNetCatalog(
        controlNetModelResult,
        controlNetModuleResult,
        controlNetTypeResult,
      );

      const bootstrapState = {
        hostSurface,
        hostDescription: describeHostSurface(hostSurface),
        hostSurfaceSupported,
        extensionName: "ComfyUI-RookieUI",
        capabilitySource: capabilityResult.source,
        capabilities: capabilityResult.data,
        compatibility: compatibilityResult.data,
        models: modelResult.data,
        presets: presetResult.data,
        controlnetCatalog,
        adetailerCatalog: adetailerCatalogResult.data,
        queue: queueResult.data,
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
