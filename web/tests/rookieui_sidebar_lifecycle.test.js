import { afterEach, describe, expect, test, vi } from "vitest";

import { enforceSidebarMinWidth } from "../rookieui_extension.js";
import { installRookieUISidebarTab } from "../rookieui_sidebar_registration.js";

describe("RookieUI sidebar lifecycle ownership", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    document.body.replaceChildren();
  });

  test("ten mount/destroy cycles restore layout, resources, markers, and DOM to baseline", () => {
    document.body.innerHTML = `
      <div class="sidebar-content-container" style="min-width: 211px; width: 377px; flex-basis: 13px">
        <div class="side-bar-panel" style="min-width: 233px; width: 355px; flex-basis: 17px">
          <div id="mount" class="host-slot" data-theme="host" style="min-width: 19px; width: 29px; flex-basis: 31px"></div>
        </div>
      </div>
    `;
    const container = document.getElementById("mount");
    const panel = document.querySelector(".side-bar-panel");
    const content = document.querySelector(".sidebar-content-container");
    vi.spyOn(panel, "getBoundingClientRect").mockReturnValue({ width: 320 });
    vi.spyOn(content, "getBoundingClientRect").mockReturnValue({ width: 320 });

    let nextFrame = 1;
    const pendingFrames = new Map();
    vi.stubGlobal("requestAnimationFrame", vi.fn((callback) => {
      const id = nextFrame;
      nextFrame += 1;
      pendingFrames.set(id, callback);
      return id;
    }));
    vi.stubGlobal("cancelAnimationFrame", vi.fn((id) => pendingFrames.delete(id)));

    const runtimeApi = new EventTarget();
    const runtimeListeners = new Set();
    const addRuntimeListener = runtimeApi.addEventListener.bind(runtimeApi);
    const removeRuntimeListener = runtimeApi.removeEventListener.bind(runtimeApi);
    runtimeApi.addEventListener = vi.fn((name, handler) => {
      runtimeListeners.add(handler);
      addRuntimeListener(name, handler);
    });
    runtimeApi.removeEventListener = vi.fn((name, handler) => {
      runtimeListeners.delete(handler);
      removeRuntimeListener(name, handler);
    });

    const activeUrls = new Set();
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => {
        const url = `blob:lifecycle-${activeUrls.size + 1}`;
        activeUrls.add(url);
        return url;
      }),
      revokeObjectURL: vi.fn((url) => activeUrls.delete(url)),
    });

    let registeredTab = null;
    installRookieUISidebarTab({
      app: {
        extensionManager: {
          registerSidebarTab(tab) {
            registeredTab = tab;
          },
        },
      },
      documentRef: document,
      bootstrapState: {},
      enforceSidebarMinWidth,
      installLegacyLauncher: vi.fn(),
      renderRookieUISidebar(target) {
        const previousClassName = target.className;
        const previousTheme = target.dataset.theme;
        target.className = "rookieui-shell";
        target.dataset.theme = "normal";
        target.appendChild(document.createElement("section"));
        const documentHandler = () => {};
        const runtimeHandler = () => {};
        document.addEventListener("rookieui:lifecycle-test", documentHandler);
        runtimeApi.addEventListener("progress", runtimeHandler);
        const objectUrl = URL.createObjectURL(new Blob(["preview"]));
        let destroyed = false;
        return () => {
          if (destroyed) return;
          destroyed = true;
          document.removeEventListener("rookieui:lifecycle-test", documentHandler);
          runtimeApi.removeEventListener("progress", runtimeHandler);
          URL.revokeObjectURL(objectUrl);
          target.replaceChildren();
          target.className = previousClassName;
          target.dataset.theme = previousTheme;
        };
      },
    });

    for (let cycle = 0; cycle < 10; cycle += 1) {
      registeredTab.render(container);
      expect(container.style.minWidth).toBe("980px");
      registeredTab.destroy();
      registeredTab.destroy();
      expect(pendingFrames.size).toBe(0);
      expect(runtimeListeners.size).toBe(0);
      expect(activeUrls.size).toBe(0);
      expect(container.childElementCount).toBe(0);
      expect(container.className).toBe("host-slot");
      expect(container.dataset.theme).toBe("host");
      expect([container.style.minWidth, container.style.width, container.style.flexBasis]).toEqual([
        "19px",
        "29px",
        "31px",
      ]);
      expect([panel.style.minWidth, panel.style.width, panel.style.flexBasis]).toEqual([
        "233px",
        "355px",
        "17px",
      ]);
      expect([content.style.minWidth, content.style.width, content.style.flexBasis]).toEqual([
        "211px",
        "377px",
        "13px",
      ]);
    }
  });
});
