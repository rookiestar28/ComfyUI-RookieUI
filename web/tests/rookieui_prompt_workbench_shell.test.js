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
        theme_style: "rookieui_classic",
        formatting_rules: {
          dedupe_commas: true,
          normalize_spacing: true,
          trim_outer_whitespace: true,
        },
        translation: {
          default_provider: "",
          providers: {},
        },
        ai_assist: {
          default_provider: "",
          providers: {},
          instruction_preset: "Write a concise Stable Diffusion prompt.",
        },
        ui_preferences: { default_open: false },
      },
      blacklist: { enabled: false, entries: [] },
      language_options: [
        { code: "en", title: "English" },
        { code: "zh-TW", title: "Traditional Chinese" },
      ],
      theme_style_options: [
        { id: "rookieui_classic", title: "RookieUI Classic" },
        { id: "rookieui_graphite", title: "Graphite Studio" },
      ],
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
            providers: [{ provider_id: "openai", title: "OpenAI-Compatible Chat Translation", execution_state: "shipped" }],
            shipped_provider_ids: ["openai"],
            deferred_provider_ids: [],
            reference_only_provider_ids: ["google_free"],
          },
          ai_assist: {
            providers: [
              {
                provider_id: "openai",
                title: "OpenAI-Compatible Chat Translation",
                execution_state: "shipped",
                config_fields: [
                  { key: "api_key", title: "API Key", secret: true, placeholder: "sk-..." },
                  { key: "model", title: "Model", placeholder: "gpt-4.1-mini" },
                ],
              },
            ],
            shipped_provider_ids: ["openai"],
            deferred_provider_ids: [],
            reference_only_provider_ids: [],
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
    translatePromptWorkbenchRequest: vi.fn(async (payload) => ({
      ok: true,
      data: {
        provider_id: payload?.provider ?? "mymemory_free",
        provider_title: "MyMemory Free Translation",
        mode: "single",
        from_lang: payload?.from_lang ?? "auto",
        to_lang: payload?.to_lang ?? "en",
        translated_text: payload?.to_lang === "en" ? "city skyline at dusk" : "城市天際線黃昏",
      },
    })),
    assistPromptWorkbenchRequest: vi.fn(async (payload) => ({
      ok: true,
      data: {
        provider_id: payload?.provider ?? "openai",
        provider_title: "OpenAI-Compatible Chat Translation",
        language: payload?.language ?? "en",
        theme_style: payload?.theme_style ?? "rookieui_classic",
        instruction_preset: payload?.instruction_preset ?? "",
        image_description: payload?.image_description ?? "",
        generated_prompt: "masterpiece, city skyline, dusk lighting",
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
    expect(document.getElementById("test-workbench-providers")?.textContent).toContain("1 translate / 1 assist / en");
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

  test("supports translation actions and catalog quick insert flows", async () => {
    const { prompt, negative, parent } = createBaseDom();
    prompt.value = "傍晚城市天際線";
    const bootstrapState = createBootstrapState({
      promptWorkbench: {
        config: {
          language: "zh-TW",
          theme_style: "rookieui_classic",
          formatting_rules: {
            dedupe_commas: true,
            normalize_spacing: true,
            trim_outer_whitespace: true,
          },
          translation: {
            default_provider: "mymemory_free",
            providers: {},
          },
          ai_assist: {
            default_provider: "",
            providers: {},
            instruction_preset: "Write a concise Stable Diffusion prompt.",
          },
          ui_preferences: { default_open: false },
        },
        blacklist: { enabled: false, entries: [] },
        language_options: [
          { code: "en", title: "English" },
          { code: "zh-TW", title: "Traditional Chinese" },
        ],
        theme_style_options: [
          { id: "rookieui_classic", title: "RookieUI Classic" },
          { id: "rookieui_graphite", title: "Graphite Studio" },
        ],
      },
      fetchPromptWorkbenchStateRequest: vi.fn(async (namespace) => ({
        ok: true,
        data: {
          state: {
            namespace,
            workbench_open: false,
            active_panel: "editor",
            draft_prompt: namespace.includes("negative") ? "" : "傍晚城市天際線",
            selected_entry_id: "",
          },
        },
      })),
      fetchPromptWorkbenchCatalogRequest: vi.fn(async () => ({
        ok: true,
        data: {
          group_tags: { groups: [{ id: "quality", title: "Quality", tags: ["masterpiece"] }] },
          prompt_library: {
            sections: [
              {
                id: "positive_base",
                title: "Positive Base",
                entries: [{ id: "masterpiece_core", label: "Masterpiece Core", prompt_text: "masterpiece, best quality, high detail" }],
              },
            ],
          },
          extra_networks: {
            embeddings: [{ id: "badhandv4.pt", insert_token: "embedding:badhandv4.pt" }],
            loras: [{ id: "detail_tweaker.safetensors", insert_token: "<lora:detail_tweaker.safetensors:0.8>" }],
          },
        },
      })),
    });

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "catalog-workbench",
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

    document.getElementById("catalog-workbench-translate-en").click();
    await flushPromises();
    expect(bootstrapState.translatePromptWorkbenchRequest).toHaveBeenCalledWith({
      provider: "mymemory_free",
      from_lang: "auto",
      to_lang: "en",
      text: "傍晚城市天際線",
    });
    expect(prompt.value).toBe("city skyline at dusk");

    document.getElementById("catalog-workbench-panel-catalog").click();
    await flushPromises();
    document.getElementById("catalog-workbench-quality-0").click();
    expect(prompt.value).toBe("city skyline at dusk, masterpiece");

    document.getElementById("catalog-workbench-library-append-0-0").click();
    expect(prompt.value).toContain("masterpiece, best quality, high detail");

    document.getElementById("catalog-workbench-embeddings-0").click();
    expect(prompt.value).toContain("embedding:badhandv4.pt");

    document.getElementById("catalog-workbench-loras-0").click();
    expect(prompt.value).toContain("<lora:detail_tweaker.safetensors:0.8>");
  });

  test("supports ai assist generation plus language and theme persistence", async () => {
    const { prompt, negative, parent } = createBaseDom();
    const bootstrapState = createBootstrapState({
      promptWorkbench: {
        config: {
          language: "en",
          theme_style: "rookieui_classic",
          formatting_rules: {
            dedupe_commas: true,
            normalize_spacing: true,
            trim_outer_whitespace: true,
          },
          translation: {
            default_provider: "",
            providers: {},
          },
          ai_assist: {
            default_provider: "openai",
            providers: { openai: { api_key: "sk-test", model: "gpt-4.1-mini" } }, // pragma: allowlist secret
            instruction_preset: "Write a concise Stable Diffusion prompt.",
          },
          ui_preferences: { default_open: false },
        },
        blacklist: { enabled: false, entries: [] },
        language_options: [
          { code: "en", title: "English" },
          { code: "zh-TW", title: "Traditional Chinese" },
        ],
        theme_style_options: [
          { id: "rookieui_classic", title: "RookieUI Classic" },
          { id: "rookieui_graphite", title: "Graphite Studio" },
        ],
      },
    });

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "assist-workbench",
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

    document.getElementById("assist-workbench-panel-assist").click();
    await flushPromises();

    const languageSelect = document.getElementById("assist-workbench-assist-language");
    languageSelect.value = "zh-TW";
    languageSelect.dispatchEvent(new Event("change", { bubbles: true }));
    await flushPromises();

    const themeSelect = document.getElementById("assist-workbench-assist-theme");
    themeSelect.value = "rookieui_graphite";
    themeSelect.dispatchEvent(new Event("change", { bubbles: true }));
    await flushPromises();

    const description = document.getElementById("assist-workbench-assist-description");
    description.value = "city skyline at dusk";
    description.dispatchEvent(new Event("input", { bubbles: true }));

    document.getElementById("assist-workbench-assist-generate").click();
    await flushPromises();

    expect(bootstrapState.assistPromptWorkbenchRequest).toHaveBeenCalledWith({
      provider: "openai",
      instruction_preset: "Write a concise Stable Diffusion prompt.",
      image_description: "city skyline at dusk",
      language: "zh-TW",
      theme_style: "rookieui_graphite",
    });
    expect(document.getElementById("assist-workbench-assist-result").value).toBe(
      "masterpiece, city skyline, dusk lighting",
    );

    document.getElementById("assist-workbench-assist-apply").click();
    expect(prompt.value).toBe("masterpiece, city skyline, dusk lighting");
    expect(bootstrapState.updatePromptWorkbenchConfigRequest).toHaveBeenCalled();
  });
});
