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
  let destroyMountedSidebar = null;
  const destroyCurrentMount = () => {
    if (!destroyMountedSidebar) {
      return;
    }
    const destroy = destroyMountedSidebar;
    destroyMountedSidebar = null;
    destroy();
  };
  const sidebarTab = {
    id: ROOKIEUI_SIDEBAR_TAB_ID,
    icon: "pi pi-compass",
    title: "RookieUI",
    tooltip: "Rookie-friendly generation shell",
    type: "custom",
    render: (container) => {
      destroyCurrentMount();
      mountedSidebarContainer = container;
      const restoreLayout = enforceSidebarMinWidth(container);
      let destroyShell = null;
      try {
        destroyShell = renderRookieUISidebar(container, bootstrapState);
      } catch (error) {
        restoreLayout?.();
        mountedSidebarContainer = null;
        throw error;
      }
      let destroyed = false;
      destroyMountedSidebar = () => {
        if (destroyed) {
          return;
        }
        destroyed = true;
        destroyShell?.();
        if (mountedSidebarContainer === container && container?.replaceChildren) {
          container.replaceChildren();
          mountedSidebarContainer = null;
        }
        restoreLayout?.();
      };
    },
    destroy: () => {
      destroyCurrentMount();
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
