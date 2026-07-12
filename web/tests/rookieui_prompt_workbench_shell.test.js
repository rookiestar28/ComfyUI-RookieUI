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
      blacklist: { enabled: false, entries: [], translation_entries: [] },
      host_actions: {
        danbooru_upsample: {
          action_id: "danbooru_upsample",
          title: "Upsample Tags",
          route_path: "/rookieui/prompt-tools/upsample",
          available: true,
          resolved_node_alias: "DanbooruTagsUpsampler",
          availability: {
            status: "ready",
            detail: "Host-installed Danbooru upsampler node 'DanbooruTagsUpsampler' is ready.",
          },
        },
      },
      language_options: [
        { code: "en", title: "English" },
        { code: "zh-TW", title: "Traditional Chinese" },
      ],
      theme_style_options: [
        { id: "rookieui_classic", title: "RookieUI Classic" },
        { id: "rookieui_graphite", title: "Graphite Studio" },
        { id: "rookieui_tagboard", title: "Tag Board" },
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
                  { key: "allow_custom_endpoint", title: "Allow Custom Endpoint", value_type: "boolean", default: false },
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
        group_tags: {
          groups: [
            {
              id: "quality",
              title: "Quality",
              tags: ["masterpiece"],
              tag_entries: [{ tag: "masterpiece", label: "masterpiece", insert_token: "masterpiece", highlight: "quality" }],
            },
          ],
        },
        tagcomplete: {
          entries: [
            {
              tag: "city skyline",
              label: "city skyline",
              insert_token: "city skyline",
              category: "composition",
              aliases: ["skyline city"],
              highlight: "composition",
            },
          ],
        },
        prompt_library: { sections: [{ id: "portrait", title: "Portrait", entries: [] }] },
        extra_networks: {
          embeddings: [{ id: "badhandv4", highlight: "embedding" }],
          loras: [{ id: "detail_tweaker", highlight: "lora" }],
        },
        catalog_highlights: {
          token_families: {
            plain: { highlight: "plain" },
            lora: { highlight: "lora" },
            weighted: { highlight: "quality" },
          },
          catalog_categories: {},
        },
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
        blacklist: { enabled: false, entries: [], translation_entries: [] },
      },
    })),
    translatePromptWorkbenchRequest: vi.fn(async (payload) => ({
      ok: true,
      data: {
        provider_id: payload?.provider ?? "mymemory_free",
        provider_title: "MyMemory Free Translation",
        mode: Array.isArray(payload?.texts) ? "batch" : "single",
        from_lang: payload?.from_lang ?? "auto",
        to_lang: payload?.to_lang ?? "en",
        translated_texts: Array.isArray(payload?.texts)
          ? payload.texts.map((text) => `translated ${text}`)
          : undefined,
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
    upsamplePromptWorkbenchRequest: vi.fn(async (payload) => ({
      ok: true,
      data: {
        action_id: "danbooru_upsample",
        final_prompt: `${String(payload?.prompt ?? "")}, enhanced tags`,
        generated_suffix: "enhanced tags",
        host_node_alias: "DanbooruTagsUpsampler",
        availability: { status: "ready" },
        warnings: [],
        warning_codes: [],
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
            : [
                {
                  id: "history-2",
                  label: payload?.item?.label ?? "Prompt",
                  prompt_text: payload?.item?.prompt_text ?? "",
                  tag_tokens: payload?.item?.tag_tokens ?? [],
                  token_payloads: payload?.item?.token_payloads ?? [],
                },
              ],
      },
    })),
    updatePromptWorkbenchFavoritesRequest: vi.fn(async (_namespace, action, payload) => ({
      ok: true,
      data: {
        items:
          action === "move_up"
            ? [{ id: payload?.item_id ?? "favorite-1", label: "Moved", prompt_text: "masterpiece" }]
            : [
                {
                  id: "favorite-2",
                  label: payload?.item?.label ?? "Favorite",
                  prompt_text: payload?.item?.prompt_text ?? "",
                  tag_tokens: payload?.item?.tag_tokens ?? [],
                  token_payloads: payload?.item?.token_payloads ?? [],
                },
              ],
      },
    })),
    updatePromptWorkbenchBlacklistRequest: vi.fn(async (blacklist) => ({
      ok: true,
      data: { blacklist },
    })),
    exportPromptWorkbenchRequest: vi.fn(async () => ({
      ok: true,
      data: {
        export: {
          schema_version: 1,
          secret_policy: "masked_provider_fields", // pragma: allowlist secret
          data: {
            config: { language: "en" },
            blacklist: { enabled: false, entries: [], translation_entries: [] },
            surfaces: {},
          },
        },
      },
    })),
    importPromptWorkbenchRequest: vi.fn(async () => ({
      ok: true,
      data: {
        import_result: {
          imported: true,
          surface_count: 4,
        },
      },
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

    const promptCard = document.getElementById("test-workbench-section");
    expect(promptCard.classList.contains("rookieui-shell__prompt-workbench-card-root")).toBe(true);
    expect(promptCard.dataset.layout).toBe("prompt_all_in_one");
    expect(document.getElementById("test-workbench-toggle")?.dataset.pwUi).toBe("fold-toggle");
    expect(document.querySelector("#test-workbench-section .rookieui-shell__prompt-workbench-toolbar")?.dataset.pwUi).toBe(
      "header-toolbar",
    );
    expect(document.getElementById("test-workbench-body")?.dataset.pwUi).toBe("prompt-card-body");
    expect(document.querySelector("#test-workbench-section .rookieui-shell__prompt-workbench-status-strip")?.dataset.pwUi).toBe(
      "status-strip",
    );
    expect(document.querySelector("#test-workbench-section [data-pw-ui='inline-add']")).toBeTruthy();
    expect(document.querySelector("#test-workbench-section [data-pw-ui='inline-suggestions']")).toBeTruthy();
    expect(document.querySelector("#test-workbench-section [data-pw-ui='history-popover-entrypoint']")).toBeTruthy();
    expect(document.querySelector("#test-workbench-section [data-pw-ui='favorites-popover-entrypoint']")).toBeTruthy();
    expect(document.querySelector("#test-workbench-section [data-pw-ui='settings-menu-entrypoint']")).toBeTruthy();
    expect(document.getElementById("test-workbench-secondary-popover")?.dataset.pwUi).toBe("history-favorites-popovers");
    expect(document.getElementById("test-workbench-token-list")?.dataset.pwUi).toBe("token-chip-board");
    expect(
      document.getElementById("test-workbench-token-list")?.classList.contains("rookieui-shell__prompt-workbench-token-board"),
    ).toBe(true);

    const tokenInputs = Array.from(
      document.querySelectorAll("#test-workbench-token-list .rookieui-shell__prompt-workbench-token-input"),
    );
    expect(tokenInputs.map((node) => node.value)).toEqual(["masterpiece", "city skyline"]);
    const tokenChips = Array.from(document.querySelectorAll("#test-workbench-token-list .rookieui-shell__prompt-workbench-token-chip"));
    expect(tokenChips).toHaveLength(2);
    expect(tokenChips.map((node) => node.dataset.pwUi)).toEqual(["token-chip", "token-chip"]);
    expect(tokenChips.map((node) => node.tabIndex)).toEqual([0, 0]);
    expect(
      Array.from(document.querySelectorAll("#test-workbench-token-list .rookieui-shell__prompt-workbench-token-quick-actions")).map(
        (node) => node.dataset.pwUi,
      ),
    ).toEqual(["token-quick-actions", "token-quick-actions"]);
    expect(
      Array.from(document.querySelectorAll("#test-workbench-token-list .rookieui-shell__prompt-workbench-token-local-language")).map(
        (node) => node.dataset.pwUi,
      ),
    ).toEqual(["token-local-language", "token-local-language"]);
    expect(bootstrapState.fetchPromptWorkbenchProvidersRequest).toHaveBeenCalledTimes(1);
    expect(bootstrapState.fetchPromptWorkbenchBlacklistRequest).toHaveBeenCalledTimes(1);
    expect(document.getElementById("test-workbench-providers")?.textContent).toContain("1 translate / 1 assist / en");
    expect(document.getElementById("test-workbench-catalogs")?.textContent).toContain("1 groups");

    document.getElementById("test-workbench-inline-suggestion-0").click();
    await flushPromises();
    expect(prompt.value).toContain("masterpiece, city skyline, masterpiece");

    expect(document.querySelector("#test-workbench-section [data-pw-ui='group-tags-tab-board']")).toBeTruthy();
    document.getElementById("test-workbench-editor-group-tag-0-0").click();
    await flushPromises();
    expect(prompt.value).toBe("city skyline, masterpiece");

    document.getElementById("test-workbench-quick-history").click();
    await flushPromises();
    expect(document.getElementById("test-workbench-secondary-popover")?.dataset.activeSurface).toBe("history");
    expect(document.getElementById("test-workbench-secondary-popover")?.textContent).toContain("Prompt: masterpiece");

    document.getElementById("test-workbench-quick-settings").click();
    await flushPromises();
    expect(document.getElementById("test-workbench-secondary-popover")?.dataset.activeSurface).toBe("settings");
    expect(document.getElementById("test-workbench-panel-format")?.dataset.active).toBe("true");
  });

  test("supports fixed-scope inline prompt and negative workbench surfaces", async () => {
    const { prompt, negative, parent } = createBaseDom();
    const promptField = document.createElement("label");
    promptField.className = "rookieui-shell__prompt-field";
    promptField.appendChild(prompt);
    const negativeField = document.createElement("label");
    negativeField.className = "rookieui-shell__prompt-field";
    negativeField.appendChild(negative);
    parent.replaceChildren(promptField);
    const bootstrapState = createBootstrapState();

    const promptShell = createPromptWorkbenchShell({
      idPrefix: "inline-prompt-workbench",
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
      fixedScope: "prompt",
    });
    parent.appendChild(negativeField);
    const negativeShell = createPromptWorkbenchShell({
      idPrefix: "inline-negative-workbench",
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
      fixedScope: "negative",
    });

    expect(promptField.nextElementSibling).toBe(promptShell.element);
    expect(negativeField.nextElementSibling).toBe(negativeShell.element);
    expect(promptShell.element.dataset.layout).toBe("prompt_all_in_one_inline");
    expect(promptShell.element.dataset.fixedScope).toBe("prompt");
    expect(negativeShell.element.dataset.fixedScope).toBe("negative");
    expect(document.getElementById("inline-prompt-workbench-body")?.querySelector("[data-pw-ui='scope-tabs']")?.hidden).toBe(true);
    expect(document.getElementById("inline-negative-workbench-body")?.querySelector("[data-pw-ui='scope-tabs']")?.hidden).toBe(true);
    expect(document.getElementById("inline-prompt-workbench-inline-counter")?.textContent).toBe("0 tags");
    expect(document.getElementById("inline-negative-workbench-inline-language")?.textContent).toBe("en / negative");
    expect(document.getElementById("inline-negative-workbench-inline-counter")?.getAttribute("role")).toBe("status");
    expect(document.getElementById("inline-negative-workbench-inline-language")?.getAttribute("aria-label")).toBe(
      "Prompt workbench language and scope",
    );
    expect(document.getElementById("inline-negative-workbench-inline-history")?.getAttribute("aria-haspopup")).toBe("dialog");
    expect(document.getElementById("inline-negative-workbench-inline-append")?.getAttribute("aria-controls")).toBe(
      "inline-negative-workbench-secondary-popover",
    );

    await promptShell.openWorkbench();
    await negativeShell.openWorkbench();
    await flushPromises();

    expect(document.getElementById("inline-negative-workbench-toggle")?.textContent).toBe("🔼");
    expect(document.getElementById("inline-negative-workbench-toggle")?.getAttribute("title")).toBe("Fold tools");
    expect(document.getElementById("inline-negative-workbench-inline-history")?.textContent).toBe("🕘");
    expect(document.getElementById("inline-negative-workbench-inline-history")?.getAttribute("title")).toBe("History");
    expect(document.getElementById("inline-negative-workbench-inline-translate")?.textContent).toBe("🌐");
    expect(document.getElementById("inline-negative-workbench-inline-translate")?.getAttribute("aria-label")).toBe("Translate");
    expect(document.getElementById("inline-negative-workbench-inline-settings")?.getAttribute("aria-label")).toBe("Prefs");
    expect(document.getElementById("inline-negative-workbench-inline-settings")?.hasAttribute("title")).toBe(false);
    expect(document.getElementById("inline-negative-workbench-inline-settings-hoverbox")?.dataset.pwUi).toBe(
      "inline-settings-hoverbox",
    );
    expect(document.getElementById("inline-negative-workbench-inline-settings-format")?.getAttribute("title")).toBe(
      "Prompt format settings",
    );
    expect(document.getElementById("inline-negative-workbench-inline-settings-auto-input")?.value).toBe("disabled");
    const inlineKeywordInput = document.getElementById("inline-negative-workbench-inline-keyword-input");
    expect(inlineKeywordInput?.getAttribute("placeholder")).toBe("Enter new keyword");
    expect(document.getElementById("inline-prompt-workbench-section")?.textContent).toContain("Prompt namespace: txt2img_prompt");
    expect(document.getElementById("inline-negative-workbench-section")?.textContent).toContain(
      "Negative Prompt namespace: txt2img_negative",
    );
    expect(document.getElementById("inline-negative-workbench-inline-counter")?.textContent).toBe("2 tags");
    expect(document.getElementById("inline-negative-workbench-token-list")?.dataset.tokenLayout).toBe("inline-tags");
    expect(
      document.querySelector("#inline-negative-workbench-token-list [data-pw-token-ui='inline-token-tag']"),
    ).toBeTruthy();
    expect(
      document
        .querySelector("#inline-negative-workbench-token-list [data-pw-ui='token-quick-actions']")
        ?.getAttribute("aria-label"),
    ).toBe("Prompt token quick actions");
    expect(
      Array.from(
        document.querySelectorAll("#inline-negative-workbench-token-list [data-pw-ui='token-local-language']"),
      ).length,
    ).toBeGreaterThan(0);
    expect(document.querySelector("#inline-negative-workbench-section [data-pw-ui='selection-batch-toolbar']")?.hidden).toBe(
      true,
    );

    document.getElementById("inline-negative-workbench-token-select-0").click();
    await flushPromises();
    expect(document.querySelector("#inline-negative-workbench-section [data-pw-ui='selection-batch-toolbar']")?.hidden).toBe(
      false,
    );
    expect(
      document.querySelector("#inline-negative-workbench-section [data-pw-ui='selection-batch-toolbar']")?.dataset.batchLayout,
    ).toBe("inline-overlay");
    const tokenCountBeforeInputDelete = document.querySelectorAll(
      "#inline-negative-workbench-token-list [data-pw-token-ui='inline-token-tag']",
    ).length;
    document
      .querySelector("#inline-negative-workbench-token-list .rookieui-shell__prompt-workbench-token-input")
      .dispatchEvent(new KeyboardEvent("keydown", { key: "Delete", bubbles: true }));
    expect(
      document.querySelectorAll("#inline-negative-workbench-token-list [data-pw-token-ui='inline-token-tag']").length,
    ).toBe(tokenCountBeforeInputDelete);

    document.getElementById("inline-negative-workbench-inline-history").click();
    await flushPromises();
    expect(document.getElementById("inline-negative-workbench-secondary-popover")?.dataset.activeSurface).toBe("history");
    expect(document.getElementById("inline-negative-workbench-panel-history")?.dataset.active).toBe("true");

    document.getElementById("inline-negative-workbench-inline-settings").click();
    await flushPromises();
    expect(document.getElementById("inline-negative-workbench-secondary-popover")?.dataset.activeSurface).toBe("settings");
    expect(document.getElementById("inline-negative-workbench-panel-format")?.dataset.active).toBe("true");

    document.getElementById("inline-negative-workbench-inline-append").click();
    await flushPromises();
    expect(document.getElementById("inline-negative-workbench-secondary-popover")?.dataset.activeSurface).toBe("append");
    expect(document.getElementById("inline-negative-workbench-secondary-popover")?.dataset.pwUi).toBe(
      "append-dropdown-popover",
    );
    expect(document.getElementById("inline-negative-workbench-secondary-popover")?.textContent).toContain("Group Tags");
    negativeShell.element.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await flushPromises();
    expect(document.getElementById("inline-negative-workbench-secondary-popover")?.hidden).toBe(true);
    document.getElementById("inline-negative-workbench-inline-append").click();
    await flushPromises();
    document.getElementById("inline-negative-workbench-append-popover-group-tag-0-0").click();
    await flushPromises();
    expect(negative.value).toContain("bad anatomy, masterpiece");

    document.getElementById("inline-negative-workbench-token-add").value = "low quality";
    document.getElementById("inline-negative-workbench-token-add-button").click();
    await flushPromises();

    expect(negative.value).toContain("bad anatomy, masterpiece, low quality");
    inlineKeywordInput.value = "film grain";
    inlineKeywordInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }));
    await flushPromises();
    expect(negative.value).toContain("film grain");
    expect(inlineKeywordInput.value).toBe("");
    expect(prompt.value).toBe("");

    document.getElementById("inline-negative-workbench-toggle").click();
    await flushPromises();
    expect(negativeShell.element.dataset.folded).toBe("true");
    expect(document.getElementById("inline-negative-workbench-toggle")?.getAttribute("aria-expanded")).toBe("false");

    document.getElementById("inline-negative-workbench-inline-delete").click();
    await flushPromises();
    expect(negative.value).toBe("");
    expect(prompt.value).toBe("");
  });

  test("opens inline language selector and synchronizes selected language", async () => {
    const { prompt, negative, parent } = createBaseDom();
    const bootstrapState = createBootstrapState({
      promptWorkbench: {
        ...createBootstrapState().promptWorkbench,
        config: {
          ...createBootstrapState().promptWorkbench.config,
          language: "en",
        },
        language_options: [
          { code: "en", title: "English" },
          { code: "zh-TW", title: "Traditional Chinese" },
          { code: "ja", title: "Japanese" },
        ],
      },
    });

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "inline-language-workbench",
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
      fixedScope: "prompt",
    });

    await shellApi.openWorkbench();
    await flushPromises();

    const languageButton = document.getElementById("inline-language-workbench-inline-language");
    expect(languageButton?.tagName).toBe("BUTTON");
    expect(languageButton?.getAttribute("aria-haspopup")).toBe("listbox");
    expect(languageButton?.getAttribute("aria-expanded")).toBe("false");

    languageButton.click();
    await flushPromises();

    const selector = document.getElementById("inline-language-workbench-language-selector");
    expect(selector?.dataset.pwUi).toBe("language-selector-popover");
    expect(selector?.hidden).toBe(false);
    expect(languageButton?.getAttribute("aria-expanded")).toBe("true");
    expect(selector?.querySelector("[data-pw-ui='language-option'][data-selected='true']")?.textContent).toContain("en - English");

    document.getElementById("inline-language-workbench-language-option-zh-TW").click();
    await flushPromises();

    expect(document.getElementById("inline-language-workbench-inline-language")?.textContent).toBe("zh-TW / 正向");
    expect(document.getElementById("inline-language-workbench-assist-language")?.value).toBe("zh-TW");
    expect(bootstrapState.updatePromptWorkbenchConfigRequest).toHaveBeenCalledWith(
      expect.objectContaining({ language: "zh-TW" }),
    );
    expect(document.getElementById("inline-language-workbench-language-selector")?.hidden).toBe(true);
    expect(document.activeElement).toBe(document.getElementById("inline-language-workbench-inline-language"));
  });

  test("synchronizes language across prompt and negative inline workbenches", async () => {
    const { prompt, negative, parent } = createBaseDom();
    const bootstrapState = createBootstrapState({
      promptWorkbench: {
        ...createBootstrapState().promptWorkbench,
        config: {
          ...createBootstrapState().promptWorkbench.config,
          language: "en",
        },
        language_options: [
          { code: "en", title: "English" },
          { code: "zh-TW", title: "Traditional Chinese", native_title: "繁體中文" },
        ],
      },
    });

    const promptShell = createPromptWorkbenchShell({
      idPrefix: "global-language-prompt-workbench",
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
      fixedScope: "prompt",
    });
    const negativeShell = createPromptWorkbenchShell({
      idPrefix: "global-language-negative-workbench",
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
      fixedScope: "negative",
    });

    await promptShell.openWorkbench();
    await negativeShell.openWorkbench();
    await flushPromises();

    document.getElementById("global-language-prompt-workbench-inline-language").click();
    await flushPromises();
    document.getElementById("global-language-prompt-workbench-language-option-zh-TW").click();
    await flushPromises();

    expect(document.getElementById("global-language-prompt-workbench-inline-language")?.textContent).toBe("zh-TW / 正向");
    expect(document.getElementById("global-language-negative-workbench-inline-language")?.textContent).toBe("zh-TW / 反向");
    expect(document.getElementById("global-language-prompt-workbench-inline-keyword-input")?.getAttribute("placeholder")).toBe(
      "請輸入新關鍵詞",
    );
    expect(document.getElementById("global-language-negative-workbench-inline-keyword-input")?.getAttribute("placeholder")).toBe(
      "請輸入新關鍵詞",
    );

    document.getElementById("global-language-negative-workbench-inline-language").click();
    await flushPromises();
    document.getElementById("global-language-negative-workbench-language-option-en").click();
    await flushPromises();

    expect(document.getElementById("global-language-prompt-workbench-inline-language")?.textContent).toBe("en / prompt");
    expect(document.getElementById("global-language-negative-workbench-inline-language")?.textContent).toBe("en / negative");
    expect(document.getElementById("global-language-prompt-workbench-inline-keyword-input")?.getAttribute("placeholder")).toBe(
      "Enter new keyword",
    );
    expect(document.getElementById("global-language-negative-workbench-inline-keyword-input")?.getAttribute("placeholder")).toBe(
      "Enter new keyword",
    );
  });

  test("localizes non-English prompt workbench languages and honors fallback codes", async () => {
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
          translation: { default_provider: "", providers: {} },
          ai_assist: {
            default_provider: "",
            providers: {},
            instruction_preset: "Write a concise Stable Diffusion prompt.",
          },
          ui_preferences: { default_open: false },
        },
        blacklist: { enabled: false, entries: [], translation_entries: [] },
        language_options: [
          { code: "en", title: "English", native_title: "English", fallback_code: "en" },
          { code: "zh-TW", title: "Traditional Chinese", native_title: "繁體中文", fallback_code: "en" },
          { code: "zh-CN", title: "Simplified Chinese", native_title: "简体中文", fallback_code: "en" },
          { code: "zh-HK", title: "Traditional Chinese (Hong Kong)", native_title: "繁體中文 (香港)", fallback_code: "zh-TW" },
          { code: "ja", title: "Japanese", native_title: "日本語", fallback_code: "en" },
        ],
        theme_style_options: [
          { id: "rookieui_classic", title: "RookieUI Classic" },
          { id: "rookieui_graphite", title: "Graphite Studio" },
        ],
      },
    });

    createPromptWorkbenchShell({
      idPrefix: "language-pack-workbench",
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
      fixedScope: "prompt",
    });

    await flushPromises();

    document.getElementById("language-pack-workbench-inline-language").click();
    document.getElementById("language-pack-workbench-language-option-ja").click();
    await flushPromises();
    expect(document.getElementById("language-pack-workbench-inline-language")?.textContent).toBe("ja / プロンプト");
    expect(parent.querySelector(".rookieui-shell__prompt-workbench-title")?.textContent).toBe("プロンプトワークベンチ");
    expect(document.getElementById("language-pack-workbench-inline-keyword-input")?.getAttribute("placeholder")).toBe(
      "新しいキーワードを入力",
    );

    document.getElementById("language-pack-workbench-inline-language").click();
    document.getElementById("language-pack-workbench-language-option-zh-CN").click();
    await flushPromises();
    expect(document.getElementById("language-pack-workbench-inline-language")?.textContent).toBe("zh-CN / 正向");
    expect(parent.querySelector(".rookieui-shell__prompt-workbench-title")?.textContent).toBe("提示词工作台");
    expect(document.getElementById("language-pack-workbench-inline-keyword-input")?.getAttribute("placeholder")).toBe(
      "请输入新关键词",
    );

    document.getElementById("language-pack-workbench-inline-language").click();
    document.getElementById("language-pack-workbench-language-option-zh-HK").click();
    await flushPromises();
    expect(document.getElementById("language-pack-workbench-inline-language")?.textContent).toBe("zh-HK / 正向");
    expect(parent.querySelector(".rookieui-shell__prompt-workbench-title")?.textContent).toBe("提示詞工作台");
    expect(document.getElementById("language-pack-workbench-inline-keyword-input")?.getAttribute("placeholder")).toBe(
      "請輸入新關鍵詞",
    );
  });

  test("localizes inline workbench controls and toggles grouped tags by active language", async () => {
    const { prompt, negative, parent } = createBaseDom();
    const fetchCatalog = vi.fn(async (language = "en") => ({
      ok: true,
      data: {
        group_tags: {
          language,
          source: "test",
          groups: [
            {
              id: "facial_expression",
              title: language === "zh-TW" ? "表情動作" : "Facial expression",
              tags: ["looking at viewer"],
              tag_entries: [
                {
                  tag: "looking at viewer",
                  label: language === "zh-TW" ? "看向鏡頭" : "looking at viewer",
                  local_label: language === "zh-TW" ? "看向鏡頭" : "",
                  english_label: "looking at viewer",
                  insert_token: "looking at viewer",
                  highlight: "composition",
                },
              ],
              subgroups: [
                {
                  id: "eyes",
                  title: language === "zh-TW" ? "眼睛" : "Eyes",
                  tag_entries: [
                    {
                      tag: "looking at viewer",
                      label: language === "zh-TW" ? "看向鏡頭" : "looking at viewer",
                      local_label: language === "zh-TW" ? "看向鏡頭" : "",
                      english_label: "looking at viewer",
                      insert_token: "looking at viewer",
                      highlight: "composition",
                    },
                  ],
                },
              ],
            },
          ],
        },
        tagcomplete: { language, source: "test", entries: [] },
        prompt_library: { sections: [] },
        extra_networks: { embeddings: [], loras: [] },
        catalog_highlights: { token_families: { plain: { highlight: "plain" } }, catalog_categories: {} },
      },
    }));
    const bootstrapState = createBootstrapState({
      fetchPromptWorkbenchCatalogRequest: fetchCatalog,
      promptWorkbench: {
        ...createBootstrapState().promptWorkbench,
        config: {
          ...createBootstrapState().promptWorkbench.config,
          language: "en",
        },
        language_options: [
          { code: "en", title: "English" },
          { code: "zh-TW", title: "Traditional Chinese", native_title: "繁體中文" },
        ],
      },
    });

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "localized-group-workbench",
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
      fixedScope: "prompt",
    });

    await shellApi.openWorkbench();
    await flushPromises();

    document.getElementById("localized-group-workbench-inline-language").click();
    await flushPromises();
    document.getElementById("localized-group-workbench-language-option-zh-TW").click();
    await flushPromises();
    await flushPromises();

    expect(document.querySelector("#localized-group-workbench-section .rookieui-shell__prompt-workbench-title")?.textContent).toBe(
      "提示詞工作台",
    );
    expect(document.getElementById("localized-group-workbench-inline-keyword-input")?.getAttribute("placeholder")).toBe(
      "請輸入新關鍵詞",
    );

    document.getElementById("localized-group-workbench-inline-append").click();
    await flushPromises();

    const groupBoard = document.querySelector(
      "#localized-group-workbench-secondary-popover [data-pw-ui='group-tags-tab-board']",
    );
    expect(groupBoard?.textContent).toContain("分組標籤");
    expect(groupBoard?.querySelector("[data-pw-ui='group-tags-group-tab']")?.textContent).toContain("表情動作");
    expect(groupBoard?.querySelector("[data-pw-ui='group-tags-subgroup-tab']")?.textContent).toContain("眼睛");
    const tagButton = groupBoard?.querySelector("[data-pw-ui='group-tags-entry']");
    expect(tagButton?.textContent).toContain("看向鏡頭");
    expect(tagButton?.textContent).toContain("looking at viewer");

    tagButton.click();
    await flushPromises();
    expect(prompt.value).toContain("looking at viewer");
    expect(
      document.querySelector(
        "#localized-group-workbench-secondary-popover [data-pw-ui='group-tags-entry']",
      )?.dataset.selected,
    ).toBe("true");

    document
      .querySelector("#localized-group-workbench-secondary-popover [data-pw-ui='group-tags-entry']")
      .click();
    await flushPromises();
    expect(prompt.value).not.toContain("looking at viewer");
  });

  test("normalizes alias language codes before rendering and persistence", async () => {
    const { prompt, negative, parent } = createBaseDom();
    const bootstrapState = createBootstrapState({
      promptWorkbench: {
        ...createBootstrapState().promptWorkbench,
        config: {
          ...createBootstrapState().promptWorkbench.config,
          language: "zh_TW",
        },
        language_options: [
          { code: "en", title: "English", aliases: ["en_US", "en-US"] },
          { code: "zh-TW", title: "Traditional Chinese", native_title: "繁體中文", aliases: ["zh_TW"] },
          { code: "pt-BR", title: "Portuguese (Brazil)", aliases: ["pt_BR"] },
        ],
      },
    });

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "inline-language-alias-workbench",
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
      fixedScope: "prompt",
    });

    await shellApi.openWorkbench();
    await flushPromises();

    expect(document.getElementById("inline-language-alias-workbench-inline-language")?.textContent).toBe("zh-TW / 正向");
    document.getElementById("inline-language-alias-workbench-inline-language").click();
    await flushPromises();
    expect(
      document
        .getElementById("inline-language-alias-workbench-language-option-zh-TW")
        ?.getAttribute("aria-selected"),
    ).toBe("true");

    document.getElementById("inline-language-alias-workbench-language-option-pt-BR").click();
    await flushPromises();

    expect(bootstrapState.updatePromptWorkbenchConfigRequest).toHaveBeenCalledWith(
      expect.objectContaining({ language: "pt-BR" }),
    );
  });

  test("refreshes language-sensitive catalog resources and translation targets after language selection", async () => {
    const { prompt, negative, parent } = createBaseDom();
    const fetchCatalog = vi.fn(async (language = "en") => ({
      ok: true,
      data: {
        group_tags: {
          language,
          source: "test",
          groups: [
            {
              id: "quality",
              title: language === "zh-TW" ? "Local Quality" : "Quality",
              tags: ["masterpiece"],
              tag_entries: [
                {
                  tag: "masterpiece",
                  label: language === "zh-TW" ? "local masterpiece" : "masterpiece",
                  insert_token: "masterpiece",
                  highlight: "quality",
                },
              ],
            },
          ],
        },
        tagcomplete: { language, source: "test", entries: [] },
        prompt_library: { sections: [] },
        extra_networks: { embeddings: [], loras: [] },
        catalog_highlights: { token_families: { plain: { highlight: "plain" } }, catalog_categories: {} },
      },
    }));
    const bootstrapState = createBootstrapState({
      fetchPromptWorkbenchCatalogRequest: fetchCatalog,
      promptWorkbench: {
        ...createBootstrapState().promptWorkbench,
        config: {
          ...createBootstrapState().promptWorkbench.config,
          language: "en",
          translation: {
            default_provider: "openai",
            providers: {},
          },
        },
        language_options: [
          { code: "en", title: "English", aliases: ["en_US"] },
          { code: "zh-TW", title: "Traditional Chinese", aliases: ["zh_TW"] },
        ],
      },
    });

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "inline-language-sync-workbench",
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
      fixedScope: "prompt",
    });

    await shellApi.openWorkbench();
    await flushPromises();

    expect(fetchCatalog).toHaveBeenCalledWith("en");
    expect(document.getElementById("inline-language-sync-workbench-translate-local")).toBeNull();
    expect(document.getElementById("inline-language-sync-workbench-token-translation-0")?.textContent).toContain("en");

    document.getElementById("inline-language-sync-workbench-inline-language").click();
    await flushPromises();
    document.getElementById("inline-language-sync-workbench-language-option-zh-TW").click();
    await flushPromises();
    await flushPromises();

    expect(fetchCatalog).toHaveBeenLastCalledWith("zh-TW");
    expect(document.getElementById("inline-language-sync-workbench-translate-local")?.textContent).toBe("Translate to zh-TW");
    expect(document.getElementById("inline-language-sync-workbench-token-translation-0")?.textContent).toContain("zh-TW");

    document.getElementById("inline-language-sync-workbench-inline-append").click();
    await flushPromises();
    expect(document.getElementById("inline-language-sync-workbench-secondary-popover")?.textContent).toContain("local masterpiece");

    document.getElementById("inline-language-sync-workbench-translate-local").click();
    await flushPromises();
    expect(bootstrapState.translatePromptWorkbenchRequest).toHaveBeenCalledWith(
      expect.objectContaining({ to_lang: "zh-TW" }),
    );
  });

  test("dismisses inline language selector with escape and outside click", async () => {
    const { prompt, negative, parent } = createBaseDom();
    const bootstrapState = createBootstrapState();

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "inline-language-dismiss-workbench",
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
      fixedScope: "prompt",
    });

    await shellApi.openWorkbench();
    await flushPromises();

    const languageButton = document.getElementById("inline-language-dismiss-workbench-inline-language");
    languageButton.click();
    await flushPromises();
    expect(document.getElementById("inline-language-dismiss-workbench-language-selector")?.hidden).toBe(false);

    shellApi.element.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await flushPromises();
    expect(document.getElementById("inline-language-dismiss-workbench-language-selector")?.hidden).toBe(true);
    expect(document.activeElement).toBe(languageButton);

    languageButton.click();
    await flushPromises();
    expect(document.getElementById("inline-language-dismiss-workbench-language-selector")?.hidden).toBe(false);
    document.body.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true }));
    await flushPromises();
    expect(document.getElementById("inline-language-dismiss-workbench-language-selector")?.hidden).toBe(true);
    expect(document.activeElement).toBe(languageButton);
  });

  test("places inline language selector with viewport-safe fixed geometry", async () => {
    const { prompt, negative, parent } = createBaseDom();
    const bootstrapState = createBootstrapState();

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "inline-language-placement-workbench",
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
      fixedScope: "prompt",
    });

    await shellApi.openWorkbench();
    await flushPromises();

    const languageButton = document.getElementById("inline-language-placement-workbench-inline-language");
    languageButton.getBoundingClientRect = () => ({
      left: 1220,
      right: 1270,
      top: 42,
      bottom: 72,
      width: 50,
      height: 30,
      x: 1220,
      y: 42,
      toJSON: () => ({}),
    });

    languageButton.click();
    await flushPromises();

    const selector = document.getElementById("inline-language-placement-workbench-language-selector");
    expect(selector?.dataset.placement).toBe("fixed");
    expect(selector?.style.position).toBe("fixed");
    expect(selector?.style.left).toMatch(/px$/);
    expect(selector?.style.top).toMatch(/px$/);
    expect(selector?.style.maxHeight).toMatch(/px$/);
  });

  test("supports keyboard navigation and selection in inline language selector", async () => {
    const { prompt, negative, parent } = createBaseDom();
    const bootstrapState = createBootstrapState({
      promptWorkbench: {
        ...createBootstrapState().promptWorkbench,
        language_options: [
          { code: "en", title: "English" },
          { code: "zh-TW", title: "Traditional Chinese" },
          { code: "ja", title: "Japanese" },
        ],
      },
    });

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "inline-language-keyboard-workbench",
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
      fixedScope: "prompt",
    });

    await shellApi.openWorkbench();
    await flushPromises();

    const languageButton = document.getElementById("inline-language-keyboard-workbench-inline-language");
    const selector = document.getElementById("inline-language-keyboard-workbench-language-selector");
    languageButton.click();
    await flushPromises();

    expect(document.activeElement).toBe(document.getElementById("inline-language-keyboard-workbench-language-option-en"));

    selector.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
    await flushPromises();
    expect(document.activeElement).toBe(document.getElementById("inline-language-keyboard-workbench-language-option-zh-TW"));

    selector.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await flushPromises();
    expect(document.getElementById("inline-language-keyboard-workbench-inline-language")?.textContent).toBe("zh-TW / 正向");
    expect(selector?.hidden).toBe(true);
    expect(document.activeElement).toBe(languageButton);
  });

  test("localizes core labels and supports import export actions", async () => {
    const { prompt, negative, parent } = createBaseDom();
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
          translation: { default_provider: "", providers: {} },
          ai_assist: {
            default_provider: "",
            providers: {},
            instruction_preset: "Write a concise Stable Diffusion prompt.",
          },
          ui_preferences: { default_open: false },
        },
        blacklist: { enabled: false, entries: [], translation_entries: [] },
        language_options: [
          { code: "en", title: "English" },
          { code: "zh-TW", title: "Traditional Chinese" },
        ],
        theme_style_options: [{ id: "rookieui_classic", title: "RookieUI Classic" }],
      },
    });

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "i18n-workbench",
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

    expect(document.querySelector(".rookieui-shell__prompt-workbench-title")?.textContent).toBe("提示詞工作台");

    await flushPromises();
    await shellApi.openWorkbench();
    await flushPromises();
    document.getElementById("i18n-workbench-panel-format").click();
    await flushPromises();

    document.getElementById("i18n-workbench-export-json").click();
    await flushPromises();
    expect(bootstrapState.exportPromptWorkbenchRequest).toHaveBeenCalledTimes(1);
    expect(document.getElementById("i18n-workbench-import-export-json").value).toContain("masked_provider_fields");

    const importInput = document.getElementById("i18n-workbench-import-export-json");
    importInput.value = JSON.stringify({ schema_version: 1, data: { blacklist: { enabled: true, entries: ["bad hands"] } } });
    importInput.dispatchEvent(new Event("input", { bubbles: true }));
    document.getElementById("i18n-workbench-import-json").click();
    await flushPromises();
    expect(bootstrapState.importPromptWorkbenchRequest).toHaveBeenCalledWith({
      schema_version: 1,
      data: { blacklist: { enabled: true, entries: ["bad hands"] } },
    });
    expect(document.querySelector(".rookieui-shell__prompt-workbench-status")?.textContent).toBe("提示詞工作台匯入已同步");
  });

  test("preserves special token syntax and supports copy plus weight controls", async () => {
    const { prompt, negative, parent } = createBaseDom();
    const clipboard = { writeText: vi.fn(async () => undefined) };
    Object.defineProperty(globalThis.navigator, "clipboard", {
      value: clipboard,
      configurable: true,
    });
    const bootstrapState = createBootstrapState({
      fetchPromptWorkbenchStateRequest: vi.fn(async (namespace) => ({
        ok: true,
        data: {
          state: {
            namespace,
            workbench_open: false,
            active_panel: "editor",
            draft_prompt: namespace.includes("negative")
              ? ""
              : String.raw`city\, skyline, <lora:detail_tweaker:0.8>, (soft light:1.2)`,
            selected_entry_id: "",
          },
        },
      })),
    });

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "syntax-workbench",
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
      document.querySelectorAll("#syntax-workbench-token-list .rookieui-shell__prompt-workbench-token-input"),
    );
    expect(tokenInputs.map((node) => node.value)).toEqual([
      String.raw`city\, skyline`,
      "<lora:detail_tweaker:0.8>",
      "(soft light:1.2)",
    ]);
    const tokenRows = Array.from(document.querySelectorAll("#syntax-workbench-token-list .rookieui-shell__prompt-workbench-token"));
    expect(tokenRows[1]?.dataset.keywordFamily).toBe("lora");
    expect(tokenRows[1]?.dataset.highlight).toBe("lora");

    document.getElementById("syntax-workbench-token-copy-1").click();
    expect(clipboard.writeText).toHaveBeenCalledWith("<lora:detail_tweaker:0.8>");

    document.getElementById("syntax-workbench-token-weight-up-2").click();
    expect(prompt.value).toBe(String.raw`city\, skyline, <lora:detail_tweaker:0.8>, (soft light:1.3)`);

    document.getElementById("syntax-workbench-token-weight-down-0").click();
    expect(prompt.value).toBe(String.raw`(city\, skyline:0.9), <lora:detail_tweaker:0.8>, (soft light:1.3)`);
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

  test("supports selected token batch copy, favorites, blacklist, and delete", async () => {
    const { prompt, negative, parent } = createBaseDom();
    prompt.value = "masterpiece, city skyline";
    const clipboard = { writeText: vi.fn(async () => undefined) };
    Object.defineProperty(globalThis.navigator, "clipboard", {
      value: clipboard,
      configurable: true,
    });
    const bootstrapState = createBootstrapState();

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "batch-workbench",
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

    expect(document.querySelector("#batch-workbench-section .rookieui-shell__prompt-workbench-selection-toolbar")?.dataset.pwUi).toBe(
      "selection-batch-toolbar",
    );
    const providerSelect = document.getElementById("batch-workbench-translation-provider");
    providerSelect.value = "openai";
    providerSelect.dispatchEvent(new Event("change", { bubbles: true }));
    await flushPromises();

    document.getElementById("batch-workbench-token-select-0").click();
    document.getElementById("batch-workbench-token-select-1").click();
    expect(document.getElementById("batch-workbench-token-selected-count").textContent).toBe("2 selected");

    document.getElementById("batch-workbench-token-batch-copy").click();
    expect(clipboard.writeText).toHaveBeenCalledWith("masterpiece, city skyline");

    document.getElementById("batch-workbench-token-batch-favorite").click();
    await flushPromises();
    expect(bootstrapState.updatePromptWorkbenchFavoritesRequest).toHaveBeenCalledWith(
      "txt2img_prompt",
      "push",
      expect.objectContaining({
        item: expect.objectContaining({
          prompt_text: "masterpiece, city skyline",
          tag_tokens: ["masterpiece", "city skyline"],
          token_payloads: [
            expect.objectContaining({ raw_text: "masterpiece", selected: true }),
            expect.objectContaining({ raw_text: "city skyline", selected: true }),
          ],
        }),
      }),
    );

    document.getElementById("batch-workbench-token-batch-translate").click();
    await flushPromises();
    expect(bootstrapState.translatePromptWorkbenchRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        provider: "openai",
        texts: ["masterpiece", "city skyline"],
        dictionary_first: true,
      }),
    );
    expect(document.getElementById("batch-workbench-token-translation-0").textContent).toContain("translated masterpiece");
    expect(prompt.value).toBe("masterpiece, city skyline");

    document.getElementById("batch-workbench-token-batch-blacklist").click();
    await flushPromises();
    expect(bootstrapState.updatePromptWorkbenchBlacklistRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        enabled: true,
        entries: ["masterpiece", "city skyline"],
      }),
    );

    document.getElementById("batch-workbench-token-batch-translation-blacklist").click();
    await flushPromises();
    expect(bootstrapState.updatePromptWorkbenchBlacklistRequest).toHaveBeenLastCalledWith(
      expect.objectContaining({
        entries: ["masterpiece", "city skyline"],
        translation_entries: ["masterpiece", "city skyline"],
      }),
    );

    const tokenInput = document.querySelector("#batch-workbench-token-list input[type='text']");
    tokenInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Delete", bubbles: true }));
    expect(prompt.value).toBe("masterpiece, city skyline");

    document.getElementById("batch-workbench-section").dispatchEvent(
      new KeyboardEvent("keydown", { key: "t", ctrlKey: true, bubbles: true }),
    );
    await flushPromises();
    expect(bootstrapState.translatePromptWorkbenchRequest).toHaveBeenCalledTimes(2);

    document.getElementById("batch-workbench-section").dispatchEvent(
      new KeyboardEvent("keydown", { key: "Delete", bubbles: true }),
    );
    expect(prompt.value).toBe("");
  });

  test("auto-captures prompt history from input edits with token payloads", async () => {
    const { prompt, negative, parent } = createBaseDom();
    const bootstrapState = createBootstrapState();

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "history-auto-workbench",
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

    prompt.value = "masterpiece, night skyline";
    prompt.dispatchEvent(new Event("input", { bubbles: true }));
    vi.advanceTimersByTime(600);
    await flushPromises();

    expect(bootstrapState.updatePromptWorkbenchHistoryRequest).toHaveBeenCalledWith(
      "txt2img_prompt",
      "auto_capture",
      expect.objectContaining({
        item: expect.objectContaining({
          prompt_text: "masterpiece, night skyline",
          tag_tokens: ["masterpiece", "night skyline"],
          token_payloads: [
            expect.objectContaining({ raw_text: "masterpiece", scope: "prompt" }),
            expect.objectContaining({ raw_text: "night skyline", scope: "prompt" }),
          ],
        }),
      }),
    );
  });

  test("persists inactive namespace edits and labels workbench controls", async () => {
    const { prompt, negative, parent } = createBaseDom();
    const bootstrapState = createBootstrapState();

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "host-sync-workbench",
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

    expect(document.getElementById("host-sync-workbench-translation-provider").getAttribute("aria-label")).toBe(
      "Prompt Workbench translation provider",
    );
    expect(document.getElementById("host-sync-workbench-token-select-0").getAttribute("aria-label")).toBe(
      "Select prompt token 1",
    );
    expect(document.getElementById("host-sync-workbench-token-batch-copy").getAttribute("aria-label")).toBe(
      "Copy Selected prompt tokens",
    );
    expect(document.getElementById("host-sync-workbench-tagcomplete-search").getAttribute("aria-label")).toBe(
      "Search Prompt Workbench tagcomplete catalog",
    );

    negative.value = "low quality, blurry";
    negative.dispatchEvent(new Event("input", { bubbles: true }));
    vi.advanceTimersByTime(180);
    await flushPromises();

    expect(bootstrapState.updatePromptWorkbenchStateRequest).toHaveBeenCalledWith(
      "txt2img_negative",
      expect.objectContaining({
        draft_prompt: "low quality, blurry",
      }),
    );
  });

  test("persists UI preferences and hides disabled collection panels", async () => {
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
          translation: { default_provider: "", providers: {} },
          ai_assist: {
            default_provider: "",
            providers: {},
            instruction_preset: "Write a concise Stable Diffusion prompt.",
          },
          ui_preferences: {
            default_open: false,
            preferred_panel: "history",
            show_history: false,
            show_favorites: true,
          },
        },
        blacklist: { enabled: false, entries: [], translation_entries: [] },
        host_actions: {},
        language_options: [{ code: "en", title: "English" }],
        theme_style_options: [{ id: "rookieui_classic", title: "RookieUI Classic" }],
      },
    });

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "settings-workbench",
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

    expect(document.getElementById("settings-workbench-panel-history").hidden).toBe(true);
    expect(document.getElementById("settings-workbench-panel-favorites").hidden).toBe(false);
    expect(document.getElementById("settings-workbench-panel-editor").dataset.active).toBe("true");

    document.getElementById("settings-workbench-panel-format").click();
    await flushPromises();

    const showHistoryToggle = document.getElementById("settings-workbench-pref-show-history");
    showHistoryToggle.click();
    await flushPromises();
    expect(bootstrapState.updatePromptWorkbenchConfigRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        ui_preferences: expect.objectContaining({
          show_history: true,
        }),
      }),
    );
    expect(document.getElementById("settings-workbench-panel-history").hidden).toBe(false);

    const preferredPanelSelect = document.getElementById("settings-workbench-pref-preferred-panel");
    preferredPanelSelect.value = "catalog";
    preferredPanelSelect.dispatchEvent(new Event("change", { bubbles: true }));
    await flushPromises();
    expect(bootstrapState.updatePromptWorkbenchConfigRequest).toHaveBeenLastCalledWith(
      expect.objectContaining({
        ui_preferences: expect.objectContaining({
          preferred_panel: "catalog",
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
    expect(bootstrapState.updatePromptWorkbenchBlacklistRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        enabled: true,
        entries: ["bad hands"],
      }),
    );

    document.getElementById("format-workbench-token-translation-blacklist-0").click();
    await flushPromises();
    expect(bootstrapState.updatePromptWorkbenchBlacklistRequest).toHaveBeenLastCalledWith(
      expect.objectContaining({
        entries: ["bad hands"],
        translation_entries: ["masterpiece"],
      }),
    );

    document.getElementById("format-workbench-panel-format").click();
    await flushPromises();
    document.getElementById("format-workbench-apply-blacklist").click();
    expect(prompt.value).toBe("masterpiece");

    document.getElementById("format-workbench-translation-blacklist-remove-0").click();
    await flushPromises();
    expect(bootstrapState.updatePromptWorkbenchBlacklistRequest).toHaveBeenLastCalledWith(
      expect.objectContaining({
        entries: ["bad hands"],
        translation_entries: [],
      }),
    );

    document.getElementById("format-workbench-blacklist-remove-0").click();
    await flushPromises();
    expect(bootstrapState.updatePromptWorkbenchBlacklistRequest).toHaveBeenLastCalledWith(
      expect.objectContaining({
        enabled: true,
        entries: [],
        translation_entries: [],
      }),
    );
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
        blacklist: { enabled: false, entries: [], translation_entries: [] },
        language_options: [
          { code: "en", title: "English" },
          { code: "zh-TW", title: "Traditional Chinese" },
        ],
          theme_style_options: [
            { id: "rookieui_classic", title: "RookieUI Classic" },
            { id: "rookieui_graphite", title: "Graphite Studio" },
            { id: "rookieui_tagboard", title: "Tag Board" },
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
          group_tags: {
            groups: [
              {
                id: "quality",
                title: "Quality",
                tags: ["masterpiece"],
                tag_entries: [{ tag: "masterpiece", label: "masterpiece", insert_token: "masterpiece", highlight: "quality" }],
              },
            ],
          },
          tagcomplete: {
            entries: [
              {
                tag: "city skyline",
                label: "city skyline",
                insert_token: "city skyline",
                category: "composition",
                aliases: ["skyline city"],
                highlight: "composition",
              },
              {
                tag: "soft light",
                label: "soft light",
                insert_token: "soft light",
                category: "lighting",
                aliases: ["gentle lighting"],
                highlight: "lighting",
              },
            ],
          },
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
            embeddings: [{ id: "badhandv4.pt", insert_token: "embedding:badhandv4.pt", highlight: "embedding" }],
            loras: [{ id: "detail_tweaker.safetensors", insert_token: "<lora:detail_tweaker.safetensors:0.8>", highlight: "lora" }],
          },
          catalog_highlights: {
            token_families: { plain: { highlight: "plain" }, lora: { highlight: "lora" } },
            catalog_categories: {},
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
    const tagcompleteSearch = document.getElementById("catalog-workbench-tagcomplete-search");
    tagcompleteSearch.value = "skyline";
    tagcompleteSearch.dispatchEvent(new Event("input", { bubbles: true }));
    expect(document.getElementById("catalog-workbench-tagcomplete-matches-0")?.dataset.highlight).toBe("composition");
    document.getElementById("catalog-workbench-tagcomplete-matches-0").click();
    expect(prompt.value).toContain("city skyline");

    expect(document.getElementById("catalog-workbench-quality-0")?.dataset.highlight).toBe("quality");
    document.getElementById("catalog-workbench-quality-0").click();
    expect(prompt.value).toBe("city skyline at dusk, city skyline, masterpiece");

    document.getElementById("catalog-workbench-library-append-0-0").click();
    expect(prompt.value).toContain("masterpiece, best quality, high detail");

    expect(document.getElementById("catalog-workbench-embeddings-0")).toBeNull();
    expect(document.getElementById("catalog-workbench-embeddings-select")?.dataset.pwUi).toBe("catalog-network-select");
    document.getElementById("catalog-workbench-embeddings-select").value = "embedding:badhandv4.pt";
    document.getElementById("catalog-workbench-embeddings-select").dispatchEvent(new Event("change", { bubbles: true }));
    document.getElementById("catalog-workbench-embeddings-insert").click();
    expect(prompt.value).toContain("embedding:badhandv4.pt");

    expect(document.getElementById("catalog-workbench-loras-0")).toBeNull();
    expect(document.getElementById("catalog-workbench-loras-select")?.dataset.pwUi).toBe("catalog-network-select");
    document.getElementById("catalog-workbench-loras-select").value = "<lora:detail_tweaker.safetensors:0.8>";
    document.getElementById("catalog-workbench-loras-select").dispatchEvent(new Event("change", { bubbles: true }));
    document.getElementById("catalog-workbench-loras-insert").click();
    expect(prompt.value).toContain("<lora:detail_tweaker.safetensors:0.8>");
  });

  test("applies Danbooru upsampled tags back into the active prompt", async () => {
    const { prompt, negative, parent } = createBaseDom();
    prompt.value = "masterpiece, city skyline";
    negative.value = "blurry";
    const bootstrapState = createBootstrapState();

    const shellApi = createPromptWorkbenchShell({
      idPrefix: "upsample-workbench",
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

    document.getElementById("upsample-workbench-upsample-tags").click();
    await flushPromises();

    expect(bootstrapState.upsamplePromptWorkbenchRequest).toHaveBeenCalledWith({
      prompt: "masterpiece, city skyline",
      negative_prompt_tags: "blurry",
      ban_tags: "",
    });
    expect(prompt.value).toBe("masterpiece, city skyline, enhanced tags");
  });

  test("shows truthful disabled detail when Danbooru host action is unavailable", async () => {
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
          translation: { default_provider: "", providers: {} },
          ai_assist: {
            default_provider: "",
            providers: {},
            instruction_preset: "Write a concise Stable Diffusion prompt.",
          },
          ui_preferences: { default_open: false },
        },
        blacklist: { enabled: false, entries: [], translation_entries: [] },
        host_actions: {
          danbooru_upsample: {
            action_id: "danbooru_upsample",
            title: "Upsample Tags",
            route_path: "/rookieui/prompt-tools/upsample",
            available: false,
            resolved_node_alias: "",
            availability: {
              status: "host_missing",
              detail: "Host-installed Danbooru upsampler node is not available in the active ComfyUI registry.",
            },
          },
        },
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
      idPrefix: "upsample-disabled",
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

    const button = document.getElementById("upsample-disabled-upsample-tags");
    const detail = document.getElementById("upsample-disabled-upsample-detail");
    expect(button.disabled).toBe(true);
    expect(detail.textContent).toContain("Host-installed Danbooru upsampler node");
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
        blacklist: { enabled: false, entries: [], translation_entries: [] },
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

    const customEndpointOptIn = document.getElementById("assist-workbench-assist-config-allow_custom_endpoint");
    expect(customEndpointOptIn.type).toBe("checkbox");
    expect(customEndpointOptIn.checked).toBe(false);
    customEndpointOptIn.checked = true;
    customEndpointOptIn.dispatchEvent(new Event("change", { bubbles: true }));
    await flushPromises();
    expect(bootstrapState.updatePromptWorkbenchConfigRequest.mock.calls.some(
      ([config]) => config?.ai_assist?.providers?.openai?.allow_custom_endpoint === true,
    )).toBe(true);

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
