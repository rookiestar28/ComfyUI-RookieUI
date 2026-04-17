import { beforeEach, describe, expect, test, vi } from "vitest";

import { createPromptWorkbenchShell } from "../sidebar_tabs/rookieui_prompt_workbench_shell.js";

function flushPromises() {
  return Promise.resolve().then(() => Promise.resolve());
}

function createActionButton(id, label) {
  const button = document.createElement("button");
  button.type = "button";
  button.id = id;
  button.textContent = label;
  return button;
}

function appendTextElement(parent, tagName, className, textContent) {
  const node = document.createElement(tagName);
  node.className = className;
  node.textContent = textContent;
  parent.appendChild(node);
  return node;
}

describe("prompt workbench shell", () => {
  beforeEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = "";
  });

  test("loads namespace state on mount and lazy resources on first open", async () => {
    const prompt = document.createElement("textarea");
    const negative = document.createElement("textarea");
    const parent = document.createElement("div");
    parent.append(prompt, negative);
    document.body.appendChild(parent);

    const bootstrapState = {
      promptWorkbench: {
        config: {
          language: "en",
          ui_preferences: { default_open: false },
        },
        blacklist: { enabled: true, entries: ["bad-hands"] },
      },
      fetchPromptWorkbenchStateRequest: vi.fn(async (namespace) => ({
        ok: true,
        data: {
          state: {
            namespace,
            workbench_open: namespace === "txt2img_negative",
            active_panel: namespace === "txt2img_negative" ? "history" : "editor",
            draft_prompt: namespace === "txt2img_negative" ? "bad anatomy" : "masterpiece",
            selected_entry_id: "",
          },
        },
      })),
      fetchPromptWorkbenchProvidersRequest: vi.fn(async () => ({
        ok: true,
        data: {
          surfaces: {
            translation: {
              shipped_provider_ids: ["openai"],
              deferred_provider_ids: [],
              reference_only_provider_ids: ["google_free"],
            },
          },
        },
      })),
      fetchPromptWorkbenchCatalogRequest: vi.fn(async () => ({
        ok: true,
        data: {
          group_tags: { groups: [{ id: "quality", title: "Quality", tags: ["masterpiece"] }] },
          prompt_library: { sections: [{ id: "portrait", title: "Portrait", entries: [] }] },
          extra_networks: { embeddings: [{ id: "badhandv4" }], loras: [{ id: "detail_tweaker" }] },
        },
      })),
      fetchPromptWorkbenchHistoryRequest: vi.fn(async () => ({ ok: true, data: { items: [{ id: "h1" }] } })),
      fetchPromptWorkbenchFavoritesRequest: vi.fn(async () => ({ ok: true, data: { items: [{ id: "f1" }, { id: "f2" }] } })),
      updatePromptWorkbenchStateRequest: vi.fn(async () => ({ ok: true, data: { saved: true } })),
    };

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "test-workbench",
      parent,
      bootstrapState,
      promptInput: prompt,
      negativePromptInput: negative,
      namespaces: {
        prompt: "txt2img_prompt",
        negative: "txt2img_negative",
      },
      appendTextElement,
      createActionButton,
    });

    await flushPromises();

    expect(bootstrapState.fetchPromptWorkbenchStateRequest).toHaveBeenCalledTimes(2);
    expect(document.getElementById("test-workbench-section")?.dataset.open).toBe("true");
    expect(document.getElementById("test-workbench-tab-negative")?.dataset.active).toBe("true");

    await shellApi.openWorkbench();
    await flushPromises();

    expect(bootstrapState.fetchPromptWorkbenchProvidersRequest).toHaveBeenCalledTimes(1);
    expect(bootstrapState.fetchPromptWorkbenchCatalogRequest).toHaveBeenCalledTimes(1);
    expect(bootstrapState.fetchPromptWorkbenchHistoryRequest).toHaveBeenCalledTimes(2);
    expect(bootstrapState.fetchPromptWorkbenchFavoritesRequest).toHaveBeenCalledTimes(2);
    expect(document.getElementById("test-workbench-providers")?.textContent).toContain("1 shipped");
    expect(document.getElementById("test-workbench-catalogs")?.textContent).toContain("1 groups");
    expect(document.getElementById("test-workbench-blacklist")?.textContent).toContain("1 blocked");
  });

  test("persists draft updates with debounce on the active namespace", async () => {
    vi.useFakeTimers();
    const prompt = document.createElement("textarea");
    const negative = document.createElement("textarea");
    const parent = document.createElement("div");
    parent.append(prompt, negative);
    document.body.appendChild(parent);

    const bootstrapState = {
      promptWorkbench: {
        config: {
          language: "en",
          ui_preferences: { default_open: false },
        },
        blacklist: { enabled: false, entries: [] },
      },
      fetchPromptWorkbenchStateRequest: vi.fn(async (namespace) => ({
        ok: true,
        data: {
          state: {
            namespace,
            workbench_open: false,
            active_panel: "editor",
            draft_prompt: "",
            selected_entry_id: "",
          },
        },
      })),
      fetchPromptWorkbenchProvidersRequest: vi.fn(async () => ({ ok: true, data: { surfaces: { translation: { shipped_provider_ids: [] } } } })),
      fetchPromptWorkbenchCatalogRequest: vi.fn(async () => ({ ok: true, data: { group_tags: { groups: [] }, prompt_library: { sections: [] }, extra_networks: { embeddings: [], loras: [] } } })),
      fetchPromptWorkbenchHistoryRequest: vi.fn(async () => ({ ok: true, data: { items: [] } })),
      fetchPromptWorkbenchFavoritesRequest: vi.fn(async () => ({ ok: true, data: { items: [] } })),
      updatePromptWorkbenchStateRequest: vi.fn(async () => ({ ok: true, data: { saved: true } })),
    };

    createPromptWorkbenchShell({
      idPrefix: "debounce-workbench",
      parent,
      bootstrapState,
      promptInput: prompt,
      negativePromptInput: negative,
      namespaces: {
        prompt: "txt2img_prompt",
        negative: "txt2img_negative",
      },
      appendTextElement,
      createActionButton,
    });

    await flushPromises();

    prompt.value = "masterpiece, city skyline";
    prompt.dispatchEvent(new Event("input", { bubbles: true }));
    vi.advanceTimersByTime(200);
    await flushPromises();

    expect(bootstrapState.updatePromptWorkbenchStateRequest).toHaveBeenCalledTimes(1);
    expect(bootstrapState.updatePromptWorkbenchStateRequest).toHaveBeenCalledWith("txt2img_prompt", {
      workbench_open: false,
      active_panel: "editor",
      draft_prompt: "masterpiece, city skyline",
      selected_entry_id: "",
    });
  });
});
