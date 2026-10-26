import { afterEach, describe, expect, test, vi } from "vitest";

import { createDefaultCapabilities } from "../../web/rookieui_api.js";
import { registerRookieUIBootstrapExtension } from "../../web/rookieui_extension.js";
import { resolveActiveClientId } from "../../web/rookieui_generation_runtime.js";
import { createShellPersistenceController } from "../../web/sidebar_tabs/rookieui_shell_persistence.js";

async function bootstrap({ storage, storageGetter, activeId = "" } = {}) {
  const calls = [];
  const windowRef = {};
  if (storageGetter) {
    Object.defineProperty(windowRef, "sessionStorage", { get: storageGetter });
  } else {
    windowRef.sessionStorage = storage;
  }
  const app = {
    registerExtension: (definition) => definition.setup(),
    api: { clientId: activeId },
    extensionManager: { registerSidebarTab() {} },
  };
  await registerRookieUIBootstrapExtension({
    app, windowRef, documentRef: document,
    fetchImpl: async (path, options = {}) => {
      calls.push({ path, options });
      return new Response(JSON.stringify(path === "/rookieui/capabilities" ? createDefaultCapabilities() : {}),
        { status: 200, headers: { "Content-Type": "application/json" } });
    },
  });
  return { state: windowRef.__ROOKIEUI_BOOTSTRAP__, app, calls };
}

function denied() {
  throw new DOMException("synthetic storage denial", "SecurityError");
}

describe("bootstrap storage failures and queue identity", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.head.replaceChildren();
    document.body.replaceChildren();
  });

  test.each(["", "active-host-client"])("survives a throwing sessionStorage getter with active id %s", async (activeId) => {
    const { state, app, calls } = await bootstrap({ storageGetter: denied, activeId });
    expect(state.clientId).toMatch(activeId ? /^active-host-client$/ : /^rookieui-/);
    expect(app.api.clientId).toBe(activeId);
    await state.fetchQueueRequest();
    await state.fetchQueueJobRequest("synthetic-job");
    const queues = calls.filter(({ path }) => path.startsWith("/rookieui/queue"));
    expect(queues.length).toBeGreaterThanOrEqual(3);
    for (const { path } of queues) {
      expect(new URL(path, "https://example.test").searchParams.get("client_id")).toBe(state.clientId);
    }
  });

  test.each(["read-method", "read-getter", "write-getter", "write-method", "getter-after-read"])(
    "keeps setup usable when storage fails at %s", async (failure) => {
      let reads = 0;
      const storage = { getItem: () => "stored-client", setItem() {} };
      if (failure === "read-method") storage.getItem = denied;
      if (failure === "read-getter") Object.defineProperty(storage, "getItem", { get: denied });
      if (failure === "write-getter") Object.defineProperty(storage, "setItem", { get: denied });
      if (failure === "write-method") storage.setItem = denied;
      const storageGetter = failure === "getter-after-read" ? () => (++reads === 1 ? storage : denied()) : undefined;
      const { state } = await bootstrap({ storage, storageGetter });
      expect(state.clientId).toMatch(failure.startsWith("read-") ? /^rookieui-/ : /^stored-client$/);
      await expect(state.fetchQueueRequest()).resolves.toBeDefined();
    },
  );

  test("prefers the active host id without reading or changing it", async () => {
    const writes = [];
    const { state, app } = await bootstrap({
      activeId: "  active-host-client  ",
      storage: { getItem: denied, setItem: (key, value) => writes.push([key, value]) },
    });
    expect(state.clientId).toBe("active-host-client");
    expect(app.api.clientId).toBe("  active-host-client  ");
    expect(writes).toEqual([["clientId", "active-host-client"]]);
  });

  test.each([undefined, "", "invalid id", 42, {}, null])("generates one in-memory fallback for invalid stored value %j", async (stored) => {
    const { state, calls } = await bootstrap({ storage: { getItem: () => stored, setItem() {} } });
    expect(state.clientId).toMatch(/^rookieui-/);
    await state.fetchQueueRequest();
    const clients = calls.filter(({ path }) => path.startsWith("/rookieui/queue"))
      .map(({ path }) => new URL(path, "https://example.test").searchParams.get("client_id"));
    expect(clients.length).toBeGreaterThan(1);
    expect(new Set(clients)).toEqual(new Set([state.clientId]));
  });

  test("uses a normalized stored id after an invalid active id and tolerates missing storage", async () => {
    const stored = await bootstrap({ activeId: "invalid active id", storage: { getItem: () => "  stored-client  " } });
    expect(stored.state.clientId).toBe("stored-client");
    const absent = await bootstrap();
    expect(absent.state.clientId).toMatch(/^rookieui-/);
  });

  test("preserves the selected runtime fallback instead of adopting stale storage", () => {
    vi.spyOn(window, "sessionStorage", "get").mockReturnValue({ getItem: () => "stale-client" });
    const state = { clientId: "selected-client" };
    expect(resolveActiveClientId(state)).toBe("selected-client");
    expect(state.clientId).toBe("selected-client");
  });

  test("runtime identity tolerates denied storage and still follows active host reconnects", () => {
    vi.spyOn(window, "sessionStorage", "get").mockImplementation(denied);
    expect(resolveActiveClientId({})).toBe("");
    const state = { clientId: "selected-client", runtimeApi: { clientId: "" } };
    expect(resolveActiveClientId(state)).toBe("selected-client");
    state.runtimeApi.clientId = "reconnected-host";
    expect(resolveActiveClientId(state)).toBe("reconnected-host");
    expect(state.clientId).toBe("reconnected-host");
  });

  test.each(["getItem", "setItem", "removeItem"])("shell persistence survives a denied %s method getter", (method) => {
    const storage = { getItem: () => null, setItem() {}, removeItem() {} };
    Object.defineProperty(storage, method, { get: denied });
    vi.spyOn(window, "sessionStorage", "get").mockReturnValue(storage);
    const controller = createShellPersistenceController(document.createElement("div"), { clientId: `synthetic-${method}` });
    controller.writePaneSnapshot("txt2img", { prompt: "synthetic" });
    expect(controller.readPaneSnapshot("txt2img")).toEqual({ prompt: "synthetic" });
  });

  test.each(["read-method", "read-getter"])("restores tab and pane state across remount after %s denial", (failure) => {
    const storage = { getItem: denied, setItem() {}, removeItem() {} };
    if (failure === "read-getter") Object.defineProperty(storage, "getItem", { get: denied });
    vi.spyOn(window, "sessionStorage", "get").mockReturnValue(storage);
    const bootstrapState = { clientId: `synthetic-remount-${failure}` };
    const first = createShellPersistenceController(document.createElement("div"), bootstrapState);
    first.writeActiveTopTab("img2img");
    first.writePaneSnapshot("img2img", { strength: "0.7", prompt: "synthetic" });
    const remounted = createShellPersistenceController(document.createElement("div"), bootstrapState);
    expect(remounted.readActiveTopTab()).toBe("img2img");
    expect(remounted.readPaneSnapshot("img2img")).toEqual({ strength: "0.7", prompt: "synthetic" });
  });

  test("prefers readable persisted state over an older in-memory snapshot", () => {
    let persisted = null;
    const storage = {
      getItem: () => persisted,
      setItem(key, value) { if (key !== "rookieui:shell-state:probe") persisted = value; },
      removeItem() {},
    };
    vi.spyOn(window, "sessionStorage", "get").mockReturnValue(storage);
    const bootstrapState = { clientId: "synthetic-persisted-precedence" };
    createShellPersistenceController(document.createElement("div"), bootstrapState).writeActiveTopTab("txt2img");
    persisted = JSON.stringify({ activeTopTabId: "img2img", panes: { img2img: { strength: "0.5" } } });
    const remounted = createShellPersistenceController(document.createElement("div"), bootstrapState);
    expect(remounted.readActiveTopTab()).toBe("img2img");
    expect(remounted.readPaneSnapshot("img2img")).toEqual({ strength: "0.5" });
  });
});
