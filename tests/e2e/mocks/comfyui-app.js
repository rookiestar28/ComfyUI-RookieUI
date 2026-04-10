export function createMockComfyUIApp({ sidebar = true } = {}) {
  const app = {
    registerExtension({ setup }) {
      return Promise.resolve(setup());
    },
  };

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
