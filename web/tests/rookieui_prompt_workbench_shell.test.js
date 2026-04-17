import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

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

function createBaseDom() {
  const prompt = document.createElement("textarea");
  const negative = document.createElement("textarea");
  const parent = document.createElement("div");
  parent.append(prompt, negative);
  document.body.appendChild(parent);
  return { prompt, negative, parent };
}

function createBootstrapState(overrides = {}) {
  return {
    promptWorkbench: {
      config: {
        language: "en",
        formatting_rules: {
          dedupe_commas: true,
          normalize_spacing: true,
          trim_outer_whitespace: true,
        },
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
          draft_prompt: namespace.includes("negative") ? "bad anatomy" : "masterpiece, city skyline",
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
    fetchPromptWorkbenchHistoryRequest: vi.fn(async () => ({
      ok: true,
      data: {
        items: [{ id: "history-1", label: "Prompt: masterpiece", prompt_text: "masterpiece, city skyline" }],
      },
    })),
    fetchPromptWorkbenchFavoritesRequest: vi.fn(async () => ({
      ok: true,
      data: {
        items: [{ id: "favorite-1", label: "Prompt: masterpiece", prompt_text: "masterpiece" }],
      },
    })),
    fetchPromptWorkbenchBlacklistRequest: vi.fn(async () => ({
      ok: true,
      data: {
        blacklist: { enabled: false, entries: [] },
      },
    })),
    updatePromptWorkbenchStateRequest: vi.fn(async (_namespace, state) => ({
      ok: true,
      data: { saved: true, state },
    })),
    updatePromptWorkbenchConfigRequest: vi.fn(async (config) => ({
      ok: true,
      data: { saved: true, config },
    })),
    updatePromptWorkbenchHistoryRequest: vi.fn(async (_namespace, action, payload) => ({
      ok: true,
      data: {
        items:
          action === "clear"
            ? []
            : [{ id: "history-2", label: payload?.item?.label ?? "Prompt", prompt_text: payload?.item?.prompt_text ?? "" }],
      },
    })),
    updatePromptWorkbenchFavoritesRequest: vi.fn(async (_namespace, action, payload) => ({
      ok: true,
      data: {
        items:
          action === "move_up"
            ? [{ id: payload?.item_id ?? "favorite-1", label: "Moved", prompt_text: "masterpiece" }]
            : [{ id: "favorite-2", label: payload?.item?.label ?? "Favorite", prompt_text: payload?.item?.prompt_text ?? "" }],
      },
    })),
    updatePromptWorkbenchBlacklistRequest: vi.fn(async (blacklist) => ({
      ok: true,
      data: { blacklist },
    })),
    ...overrides,
  };
}

describe("prompt workbench shell", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    document.body.innerHTML = "";
  });

  afterEach(async () => {
    vi.runOnlyPendingTimers();
    await flushPromises();
    vi.useRealTimers();
  });

  test("loads editor resources on demand and renders tokenized prompt rows", async () => {
    const { prompt, negative, parent } = createBaseDom();
    const bootstrapState = createBootstrapState();

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
    await shellApi.openWorkbench();
    await flushPromises();

    const tokenInputs = Array.from(
      document.querySelectorAll("#test-workbench-token-list .rookieui-shell__prompt-workbench-token-input"),
    );
    expect(tokenInputs.map((node) => node.value)).toEqual(["masterpiece", "city skyline"]);
    expect(bootstrapState.fetchPromptWorkbenchProvidersRequest).toHaveBeenCalledTimes(1);
    expect(bootstrapState.fetchPromptWorkbenchBlacklistRequest).toHaveBeenCalledTimes(1);
    expect(document.getElementById("test-workbench-providers")?.textContent).toContain("1 shipped");
    expect(document.getElementById("test-workbench-catalogs")?.textContent).toContain("1 groups");
  });

  test("supports editor token actions and collection saves", async () => {
    const { prompt, negative, parent } = createBaseDom();
    prompt.value = "masterpiece, city skyline";
    const bootstrapState = createBootstrapState();

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "editor-workbench",
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
    await shellApi.openWorkbench();
    await flushPromises();

    document.getElementById("editor-workbench-token-add").value = "cinematic lighting";
    document.getElementById("editor-workbench-token-add-button").click();
    expect(prompt.value).toBe("masterpiece, city skyline, cinematic lighting");

    document.getElementById("editor-workbench-token-toggle-1").click();
    expect(prompt.value).toBe("masterpiece, cinematic lighting");

    document.getElementById("editor-workbench-token-up-1").click();
    expect(prompt.value).toBe("cinematic lighting, masterpiece");

    document.getElementById("editor-workbench-panel-favorites").click();
    await flushPromises();
    document.getElementById("editor-workbench-favorites-save-current").click();
    await flushPromises();
    expect(bootstrapState.updatePromptWorkbenchFavoritesRequest).toHaveBeenCalledWith(
      "txt2img_prompt",
      "push",
      expect.objectContaining({
        item: expect.objectContaining({
          prompt_text: "cinematic lighting, masterpiece",
        }),
      }),
    );

    document.getElementById("editor-workbench-panel-history").click();
    await flushPromises();
    document.getElementById("editor-workbench-history-save-current").click();
    await flushPromises();
    expect(bootstrapState.updatePromptWorkbenchHistoryRequest).toHaveBeenCalledWith(
      "txt2img_prompt",
      "push",
      expect.objectContaining({
        item: expect.objectContaining({
          prompt_text: "cinematic lighting, masterpiece",
        }),
      }),
    );
  });

  test("applies formatting and blacklist actions through the active editor", async () => {
    const { prompt, negative, parent } = createBaseDom();
    prompt.value = " masterpiece , masterpiece , bad hands ";
    const bootstrapState = createBootstrapState({
      fetchPromptWorkbenchStateRequest: vi.fn(async (namespace) => ({
        ok: true,
        data: {
          state: {
            namespace,
            workbench_open: false,
            active_panel: "editor",
            draft_prompt: namespace.includes("negative") ? "" : " masterpiece , masterpiece , bad hands ",
            selected_entry_id: "",
          },
        },
      })),
    });

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "format-workbench",
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
    await shellApi.openWorkbench();
    await flushPromises();

    document.getElementById("format-workbench-panel-format").click();
    await flushPromises();

    document.getElementById("format-workbench-apply-formatting").click();
    expect(prompt.value).toBe("masterpiece, bad hands");

    const dedupeRule = document.querySelector(".rookieui-shell__prompt-workbench-rule input");
    dedupeRule.click();
    await flushPromises();
    expect(bootstrapState.updatePromptWorkbenchConfigRequest).toHaveBeenCalled();

    document.getElementById("format-workbench-panel-editor").click();
    await flushPromises();
    document.getElementById("format-workbench-token-blacklist-1").click();
    await flushPromises();
    expect(bootstrapState.updatePromptWorkbenchBlacklistRequest).toHaveBeenCalledWith({
      enabled: true,
      entries: ["bad hands"],
    });

    document.getElementById("format-workbench-panel-format").click();
    await flushPromises();
    document.getElementById("format-workbench-apply-blacklist").click();
    expect(prompt.value).toBe("masterpiece");

    document.getElementById("format-workbench-blacklist-remove-0").click();
    await flushPromises();
    expect(bootstrapState.updatePromptWorkbenchBlacklistRequest).toHaveBeenLastCalledWith({
      enabled: true,
      entries: [],
    });
  });
});
