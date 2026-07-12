export function createMockComfyUIApp({ sidebar = true, api = null } = {}) {
  const app = {
    registerExtension({ setup }) {
      return Promise.resolve(setup());
    },
  };

  if (api) {
    app.api = api;
  }

  if (sidebar) {
    app.extensionManager = {
      activeSidebarTab: null,
      registerSidebarTab(tab) {
        this.activeSidebarTab = tab;
        const host = document.getElementById("mock-sidebar-tabs");
        host.dataset.sidebarId = tab.id;
        tab.render(host);
      },
      unregisterSidebarTab(id) {
        if (this.activeSidebarTab?.id !== id) return;
        this.activeSidebarTab.destroy?.();
        this.activeSidebarTab = null;
      },
    };
  }

  return app;
}
