export function createMockComfyUIRuntimeApi({ clientId = "", fetchApi = null } = {}) {
  const listeners = new Map();
  return {
    clientId,
    fetchApi,
    addEventListener(eventName, listener) {
      const eventListeners = listeners.get(eventName) ?? new Set();
      eventListeners.add(listener);
      listeners.set(eventName, eventListeners);
    },
    removeEventListener(eventName, listener) {
      const eventListeners = listeners.get(eventName);
      eventListeners?.delete(listener);
      if (eventListeners?.size === 0) {
        listeners.delete(eventName);
      }
    },
    dispatch(eventName, detail) {
      for (const listener of Array.from(listeners.get(eventName) ?? [])) {
        listener(new CustomEvent(eventName, { detail }));
      }
    },
    listenerCount() {
      return Array.from(listeners.values()).reduce((count, eventListeners) => count + eventListeners.size, 0);
    },
  };
}

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
