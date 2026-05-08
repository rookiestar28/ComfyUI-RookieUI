import { rookieUIDebugWarn } from "./rookieui_debug_deps.js";

export const ROOKIEUI_SIDEBAR_TAB_ID = "comfyui-rookieui";

export function installRookieUISidebarTab({
  app,
  documentRef,
  bootstrapState,
  enforceSidebarMinWidth,
  renderRookieUISidebar,
  installLegacyLauncher,
}) {
  const extensionManager = app?.extensionManager ?? null;
  if (typeof extensionManager?.registerSidebarTab !== "function") {
    installLegacyLauncher(documentRef, bootstrapState);
    return;
  }

  let mountedSidebarContainer = null;
  const sidebarTab = {
    id: ROOKIEUI_SIDEBAR_TAB_ID,
    icon: "pi pi-compass",
    title: "RookieUI",
    tooltip: "Rookie-friendly generation shell",
    type: "custom",
    render: (container) => {
      mountedSidebarContainer = container;
      enforceSidebarMinWidth(container);
      renderRookieUISidebar(container, bootstrapState);
    },
    destroy: () => {
      if (mountedSidebarContainer?.replaceChildren) {
        mountedSidebarContainer.replaceChildren();
      }
      mountedSidebarContainer = null;
    },
  };

  if (typeof extensionManager.unregisterSidebarTab === "function") {
    try {
      // IMPORTANT: current ComfyUI calls custom tab destroy() during unregister; clear stale RookieUI mounts before re-registering.
      extensionManager.unregisterSidebarTab(ROOKIEUI_SIDEBAR_TAB_ID);
    } catch (error) {
      rookieUIDebugWarn("sidebar", "Failed to unregister stale RookieUI sidebar tab.", {
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  extensionManager.registerSidebarTab(sidebarTab);
}
