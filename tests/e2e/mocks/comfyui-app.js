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
      registerSidebarTab({ id, render }) {
        const host = document.getElementById("mock-sidebar-tabs");
        host.dataset.sidebarId = id;
        render(host);
      },
    };
  }

  return app;
}
