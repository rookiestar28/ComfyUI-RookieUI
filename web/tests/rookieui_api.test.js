import { describe, expect, test, vi } from "vitest";

import {
  fetchRookieUICapabilities,
  fetchRookieUIADetailerCatalog,
  fetchRookieUICompatibility,
  fetchRookieUIControlNetModels,
  fetchRookieUIControlNetModules,
  fetchRookieUIControlNetTypes,
  fetchRookieUIHistoryPrompt,
  fetchRookieUIModels,
  fetchRookieUIPromptWorkbenchBlacklist,
  fetchRookieUIPromptWorkbenchCatalog,
  fetchRookieUIPromptWorkbenchConfig,
  fetchRookieUIPromptWorkbenchState,
  fetchRookieUIPresets,
  fetchRookieUIQueue,
  fetchRookieUIQueueJob,
  fetchRookieUIXYZPlotAxes,
  fetchRookieUIXYZPlotSessions,
  fetchRookieUIXYZPlotSessionDetail,
  inspectRookieUIPngInfo,
  submitRookieUIExtras,
  submitRookieUIImg2Img,
  submitRookieUITxt2Img,
  submitRookieUIXYZPlotEstimate,
  submitRookieUIXYZPlotRun,
  assistRookieUIPromptWorkbench,
  cancelRookieUIXYZPlotSession,
  translateRookieUIPromptWorkbench,
  upsampleRookieUIPromptWorkbench,
  updateRookieUIPromptWorkbenchBlacklist,
  updateRookieUIPromptWorkbenchConfig,
  updateRookieUIPromptWorkbenchFavorites,
  updateRookieUIPromptWorkbenchHistory,
  updateRookieUIPromptWorkbenchState,
} from "../rookieui_api.js";

describe("fetchRookieUICapabilities", () => {
  test("returns server capabilities when the backend responds", async () => {
    const fetchImpl = async () => ({
      ok: true,
      async json() {
        return {
          service: "rookieui",
          visibility: "internal",
          shell_version: "0.1.0",
          host_surfaces: ["standalone-web", "desktop"],
          features: { sidebarShell: true },
          tabs: [{ id: "txt2img", title: "Txt2Img", state: "active", enabled: true }],
          routes: ["/rookieui/capabilities"],
        };
      },
    });

    const result = await fetchRookieUICapabilities(fetchImpl);
    expect(result.ok).toBe(true);
    expect(result.source).toBe("server");
    expect(result.data.features.sidebarShell).toBe(true);
  });

  test("falls back when the backend is unavailable", async () => {
    const result = await fetchRookieUICapabilities(async () => {
      throw new Error("network unavailable");
    });

    expect(result.ok).toBe(false);
    expect(result.source).toBe("fallback");
    expect(result.data.tabs[0].title).toBe("Txt2Img");
    expect(result.data.parity.profiles[0].id).toBe("sd15");
    expect(result.data.model_families.contract_version).toBe("f151-20260418");
    expect(result.data.model_families.entries[0].id).toBe("sd15");
    const chromaEntry = result.data.model_families.entries.find((entry) => entry.id === "chroma");
    const ernieEntry = result.data.model_families.entries.find((entry) => entry.id === "ernie_image");
    const longcatEntry = result.data.model_families.entries.find((entry) => entry.id === "longcat_image");
    expect(chromaEntry.shift_visible).toBe(true);
    expect(chromaEntry.default_shift).toBe(1);
    expect(ernieEntry.prompt_enhancement_visible).toBe(true);
    expect(ernieEntry.default_prompt_enhancement_enabled).toBe(true);
    expect(longcatEntry.flux_guidance_visible).toBe(true);
    expect(longcatEntry.default_flux_guidance).toBe(4);
    expect(result.data.prompt_semantics.contract_version).toBe("r55-20260411");
    expect(result.data.features.adetailer).toBe(true);
    expect(result.data.adetailer.contract.version).toBe("r74f77-20260414");
    expect(result.data.adetailer.execution_backend).toBe("rookieui_comfy_native_refinement_pipeline");
    expect(result.data.adetailer.warning_code_contract).toBe("stable_f81");
    expect(result.data.adetailer.warning_codes.ADETAILER_DETECTOR_RUNTIME_FALLBACK_MASK).toContain("fallback");
    expect(result.data.adetailer.routes).toContain("/rookieui/adetailer/catalog");
  });

  test("submits txt2img payloads to the backend", async () => {
    const calls = [];
    const result = await submitRookieUITxt2Img(
      { prompt: "test prompt", profile: "sd15" },
      async (url, options) => {
        calls.push([url, options]);
        return {
          ok: true,
          status: 200,
          async json() {
            return { mode: "queued", submission: { accepted: true, prompt_id: "abc123" } };
          },
        };
      },
    );

    expect(result.ok).toBe(true);
    expect(result.data.submission.prompt_id).toBe("abc123");
    expect(calls[0][0]).toBe("/rookieui/generate/txt2img");
    expect(JSON.parse(calls[0][1].body).prompt).toBe("test prompt");
  });

  test("submits img2img payloads to the backend", async () => {
    const calls = [];
    const result = await submitRookieUIImg2Img(
      { prompt: "variation", image_asset: "input-image", profile: "sd15" },
      async (url, options) => {
        calls.push([url, options]);
        return {
          ok: true,
          status: 200,
          async json() {
            return { mode: "queued", submission: { accepted: true, prompt_id: "img-123" } };
          },
        };
      },
    );

    expect(result.ok).toBe(true);
    expect(result.data.submission.prompt_id).toBe("img-123");
    expect(calls[0][0]).toBe("/rookieui/generate/img2img");
    expect(JSON.parse(calls[0][1].body).image_asset).toBe("input-image");
  });

  test("inspects pnginfo payloads through the backend", async () => {
    const calls = [];
    const result = await inspectRookieUIPngInfo(
      { image_data: "data:image/png;base64,ZmFrZQ==" },
      async (url, options) => {
        calls.push([url, options]);
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              status: "ok",
              target_form: "txt2img",
              payload: { prompt: "masterpiece", width: 512, height: 512 },
              unsupported_fields: [],
            };
          },
        };
      },
    );

    expect(result.ok).toBe(true);
    expect(result.data.target_form).toBe("txt2img");
    expect(calls[0][0]).toBe("/rookieui/pnginfo/inspect");
    expect(JSON.parse(calls[0][1].body).image_data).toContain("data:image/png;base64,");
  });

  test("submits extras payloads to the backend", async () => {
    const calls = [];
    const result = await submitRookieUIExtras(
      { mode: "single_image", image_data: "data:image/png;base64,abc=" },
      async (url, options) => {
        calls.push([url, options]);
        return {
          ok: true,
          status: 200,
          async json() {
            return { status: "ok", output_assets: ["rookieui_extras_a.png"], preview_asset: "rookieui_extras_a.png" };
          },
        };
      },
    );

    expect(result.ok).toBe(true);
    expect(calls[0][0]).toBe("/rookieui/extras/run");
    expect(JSON.parse(calls[0][1].body).mode).toBe("single_image");
  });

  test("loads fallback model inventory, compatibility catalog, and presets", async () => {
    const models = await fetchRookieUIModels(async () => {
      throw new Error("offline");
    });
    const compatibility = await fetchRookieUICompatibility(async () => {
      throw new Error("offline");
    });
    const presets = await fetchRookieUIPresets(async () => {
      throw new Error("offline");
    });
    const queue = await fetchRookieUIQueue(async () => {
      throw new Error("offline");
    });

    expect(models.data.default_checkpoint).toBe("__host_default__");
    expect(models.data.catalog.primary_model_category_by_family.pony).toBe("checkpoints");
    expect(models.data.catalog.primary_model_category_by_family.flux).toBe("diffusion_models");
    expect(models.data.catalog.primary_model_category_by_family.anima).toBe("diffusion_models");
    expect(models.data.catalog.primary_model_category_by_family.ernie_image).toBe("diffusion_models");
    expect(models.data.catalog.primary_model_category_by_family.zit).toBe("diffusion_models");
    expect(models.data.catalog.categories.checkpoints.sidebar_visible).toBe(true);
    expect(compatibility.data.samplers[0].id).toBe("euler_ancestral");
    expect(compatibility.data.schedulers[0].id).toBe("normal");
    expect(compatibility.data.newer_family_profiles.map((profile) => profile.id)).toEqual([
      "anima",
      "chroma",
      "ernie_image",
      "ernie_image_turbo",
      "flux",
      "klein_4b_distilled",
      "klein_4b",
      "klein_9b_distilled",
      "klein_9b",
      "hidream_i1_dev_fp8",
      "hidream_i1_fast",
      "hidream_i1_full",
      "longcat_image",
      "qwen_image",
      "z_image",
      "z_image_turbo",
    ]);
    expect(presets.data.presets[0].id).toBe("sd15");
    expect(presets.data.presets.map((preset) => preset.id)).toEqual([
      "sd15",
      "sdxl",
      "pony",
      "illustrious",
      "noob",
      "anima",
      "chroma",
      "ernie_image",
      "ernie_image_turbo",
      "flux",
      "klein_4b_distilled",
      "klein_4b",
      "klein_9b_distilled",
      "klein_9b",
      "hidream_i1_dev_fp8",
      "hidream_i1_fast",
      "hidream_i1_full",
      "longcat_image",
      "qwen_image",
      "z_image",
      "z_image_turbo",
    ]);
    expect(presets.data.presets.find((preset) => preset.id === "flux")?.profile).toBe("flux");
    expect(presets.data.presets.find((preset) => preset.id === "chroma")?.shift).toBe(1);
    expect(presets.data.presets.find((preset) => preset.id === "qwen_image")?.profile).toBe("qwen_image");
    expect(presets.data.presets.find((preset) => preset.id === "ernie_image")?.profile).toBe("ernie_image");
    expect(presets.data.presets.find((preset) => preset.id === "ernie_image")?.prompt_enhancement_enabled).toBe(true);
    expect(presets.data.presets.find((preset) => preset.id === "longcat_image")?.flux_guidance).toBe(4);
    expect(presets.data.presets.find((preset) => preset.id === "z_image_turbo")?.base_family).toBe("z_image");
    expect(queue.data.queue_remaining).toBe(0);
  });

  test("loads prompt-workbench bootstrap config with fallback masking contract", async () => {
    const result = await fetchRookieUIPromptWorkbenchConfig(async () => {
      throw new Error("offline");
    });

    expect(result.ok).toBe(false);
    expect(result.data.contract.version).toBe("r145f141f142-20260418");
    expect(result.data.contract.surface).toBe("prompt_tools_config");
    expect(result.data.config.translation.providers).toEqual({});
    expect(result.data.config.ai_assist.instruction_preset).toContain("Stable Diffusion prompt");
    expect(result.data.language_options[0].code).toBe("en");
    expect(result.data.theme_style_options[0].id).toBe("rookieui_classic");
    expect(result.data.blacklist).toEqual({ enabled: false, entries: [] });
    expect(result.data.host_actions.danbooru_upsample.route_path).toBe("/rookieui/prompt-tools/upsample");
  });

  test("loads prompt-workbench namespace state with a fallback payload", async () => {
    const result = await fetchRookieUIPromptWorkbenchState("txt2img_prompt", async () => {
      throw new Error("offline");
    });

    expect(result.ok).toBe(false);
    expect(result.data.namespace).toBe("txt2img_prompt");
    expect(result.data.state.active_panel).toBe("editor");
  });

  test("loads prompt-workbench blacklist with a fallback payload", async () => {
    const result = await fetchRookieUIPromptWorkbenchBlacklist(async () => {
      throw new Error("offline");
    });

    expect(result.ok).toBe(false);
    expect(result.data.contract.surface).toBe("prompt_tools_blacklist");
    expect(result.data.blacklist).toEqual({ enabled: false, entries: [] });
  });

  test("loads xyz-plot axes fallback contract", async () => {
    const result = await fetchRookieUIXYZPlotAxes(async () => {
      throw new Error("offline");
    });

    expect(result.ok).toBe(false);
    expect(result.data.contract.surface).toBe("xyz_plot_axes");
    expect(result.data.axis_order).toEqual(["steps", "cfg_scale", "sampler"]);
    expect(result.data.axes.steps.session_runner_support).toBe(true);
  });

  test("updates prompt-workbench namespace state through the backend", async () => {
    const calls = [];
    const result = await updateRookieUIPromptWorkbenchState(
      "txt2img_prompt",
      { workbench_open: true, active_panel: "history", draft_prompt: "masterpiece, skyline" },
      async (url, options) => {
        calls.push([url, options]);
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              contract: { surface: "prompt_tools_state" },
              namespace: "txt2img_prompt",
              state: {
                namespace: "txt2img_prompt",
                workbench_open: true,
                active_panel: "history",
                draft_prompt: "masterpiece, skyline",
                selected_entry_id: "",
              },
              saved: true,
            };
          },
        };
      },
    );

    expect(result.ok).toBe(true);
    expect(calls[0][0]).toBe("/rookieui/prompt-tools/state");
    expect(JSON.parse(calls[0][1].body)).toEqual({
      namespace: "txt2img_prompt",
      state: {
        workbench_open: true,
        active_panel: "history",
        draft_prompt: "masterpiece, skyline",
      },
    });
  });

  test("updates prompt-workbench config through the backend", async () => {
    const calls = [];
    const result = await updateRookieUIPromptWorkbenchConfig(
      {
        formatting_rules: {
          dedupe_commas: false,
          normalize_spacing: true,
          trim_outer_whitespace: true,
        },
      },
      async (url, options) => {
        calls.push([url, options]);
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              config: {
                formatting_rules: {
                  dedupe_commas: false,
                  normalize_spacing: true,
                  trim_outer_whitespace: true,
                },
              },
              saved: true,
            };
          },
        };
      },
    );

    expect(result.ok).toBe(true);
    expect(calls[0][0]).toBe("/rookieui/prompt-tools/config");
    expect(JSON.parse(calls[0][1].body)).toEqual({
      config: {
        formatting_rules: {
          dedupe_commas: false,
          normalize_spacing: true,
          trim_outer_whitespace: true,
        },
      },
    });
  });

  test("submits Danbooru prompt-workbench upsample payloads to the backend", async () => {
    const calls = [];
    const result = await upsampleRookieUIPromptWorkbench(
      { prompt: "masterpiece, city skyline", negative_prompt_tags: "blurry", ban_tags: "lowres" },
      async (url, options) => {
        calls.push([url, options]);
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              contract: { surface: "prompt_tools_upsample" },
              action_id: "danbooru_upsample",
              final_prompt: "masterpiece, city skyline, enhanced tags",
              generated_suffix: "enhanced tags",
              host_node_alias: "DanbooruTagsUpsampler",
              availability: { status: "ready" },
              warnings: [],
              warning_codes: [],
            };
          },
        };
      },
    );

    expect(result.ok).toBe(true);
    expect(calls[0][0]).toBe("/rookieui/prompt-tools/upsample");
    expect(JSON.parse(calls[0][1].body)).toEqual({
      prompt: "masterpiece, city skyline",
      negative_prompt_tags: "blurry",
      ban_tags: "lowres",
    });
    expect(result.data.final_prompt).toContain("enhanced tags");
  });

  test("updates prompt-workbench blacklist through the backend", async () => {
    const calls = [];
    const result = await updateRookieUIPromptWorkbenchBlacklist(
      { enabled: true, entries: ["bad-hands"] },
      async (url, options) => {
        calls.push([url, options]);
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              blacklist: { enabled: true, entries: ["bad-hands"] },
            };
          },
        };
      },
    );

    expect(result.ok).toBe(true);
    expect(calls[0][0]).toBe("/rookieui/prompt-tools/blacklist");
    expect(JSON.parse(calls[0][1].body)).toEqual({
      blacklist: { enabled: true, entries: ["bad-hands"] },
    });
  });

  test("updates prompt-workbench history through the backend", async () => {
    const calls = [];
    const result = await updateRookieUIPromptWorkbenchHistory(
      "txt2img_prompt",
      "push",
      {
        item: {
          label: "Prompt: masterpiece",
          prompt_text: "masterpiece",
          tag_tokens: ["masterpiece"],
        },
      },
      async (url, options) => {
        calls.push([url, options]);
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              namespace: "txt2img_prompt",
              items: [{ id: "history-1", label: "Prompt: masterpiece", prompt_text: "masterpiece" }],
            };
          },
        };
      },
    );

    expect(result.ok).toBe(true);
    expect(calls[0][0]).toBe("/rookieui/prompt-tools/history");
    expect(JSON.parse(calls[0][1].body)).toEqual({
      namespace: "txt2img_prompt",
      action: "push",
      item: {
        label: "Prompt: masterpiece",
        prompt_text: "masterpiece",
        tag_tokens: ["masterpiece"],
      },
    });
  });

  test("updates prompt-workbench favorites through the backend", async () => {
    const calls = [];
    const result = await updateRookieUIPromptWorkbenchFavorites(
      "txt2img_negative",
      "move_up",
      { item_id: "favorite-1" },
      async (url, options) => {
        calls.push([url, options]);
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              namespace: "txt2img_negative",
              items: [{ id: "favorite-1", label: "Negative: bad anatomy", prompt_text: "bad anatomy" }],
            };
          },
        };
      },
    );

    expect(result.ok).toBe(true);
    expect(calls[0][0]).toBe("/rookieui/prompt-tools/favorites");
    expect(JSON.parse(calls[0][1].body)).toEqual({
      namespace: "txt2img_negative",
      action: "move_up",
      item_id: "favorite-1",
    });
  });

  test("loads prompt-workbench catalog fallback summary", async () => {
    const result = await fetchRookieUIPromptWorkbenchCatalog("en", async () => {
      throw new Error("offline");
    });

    expect(result.ok).toBe(false);
    expect(result.data.group_tags.language).toBe("en");
    expect(result.data.prompt_library.sections).toEqual([]);
  });

  test("submits prompt-workbench translation requests through the backend", async () => {
    const calls = [];
    const result = await translateRookieUIPromptWorkbench(
      {
        provider: "mymemory_free",
        from_lang: "auto",
        to_lang: "en",
        text: "傍晚城市天際線",
      },
      async (url, options) => {
        calls.push([url, options]);
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              provider_id: "mymemory_free",
              provider_title: "MyMemory Free Translation",
              mode: "single",
              from_lang: "auto",
              to_lang: "en",
              translated_text: "city skyline at dusk",
            };
          },
        };
      },
    );

    expect(result.ok).toBe(true);
    expect(calls[0][0]).toBe("/rookieui/prompt-tools/translate");
    expect(JSON.parse(calls[0][1].body)).toEqual({
      provider: "mymemory_free",
      from_lang: "auto",
      to_lang: "en",
      text: "傍晚城市天際線",
    });
  });

  test("submits prompt-workbench ai assist requests through the backend", async () => {
    const calls = [];
    const result = await assistRookieUIPromptWorkbench(
      {
        provider: "openai",
        instruction_preset: "Write a concise Stable Diffusion prompt.",
        image_description: "city skyline at dusk",
        language: "zh-TW",
        theme_style: "rookieui_graphite",
      },
      async (url, options) => {
        calls.push([url, options]);
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              provider_id: "openai",
              provider_title: "OpenAI-Compatible Chat Translation",
              language: "zh-TW",
              theme_style: "rookieui_graphite",
              instruction_preset: "Write a concise Stable Diffusion prompt.",
              image_description: "city skyline at dusk",
              generated_prompt: "masterpiece, city skyline, dusk lighting",
            };
          },
        };
      },
    );

    expect(result.ok).toBe(true);
    expect(calls[0][0]).toBe("/rookieui/prompt-tools/assist");
    expect(JSON.parse(calls[0][1].body)).toEqual({
      provider: "openai",
      instruction_preset: "Write a concise Stable Diffusion prompt.",
      image_description: "city skyline at dusk",
      language: "zh-TW",
      theme_style: "rookieui_graphite",
    });
  });

  test("submits xyz-plot estimate and run payloads through the backend", async () => {
    const calls = [];
    const estimateResult = await submitRookieUIXYZPlotEstimate(
      {
        mode: "txt2img",
        base_request: { prompt: "skyline" },
        axes: [{ axis_id: "steps", values: "20,28,36" }],
      },
      async (url, options) => {
        calls.push([url, options]);
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              estimate: {
                cell_count: 3,
                generated_image_count: 3,
                total_step_estimate: 84,
                projected_grid_megapixels: 1.5,
              },
              can_run: true,
              warnings: [],
              warning_codes: [],
            };
          },
        };
      },
    );
    const runResult = await submitRookieUIXYZPlotRun(
      {
        mode: "txt2img",
        base_request: { prompt: "skyline" },
        axes: [{ axis_id: "steps", values: "20,28,36" }],
      },
      async (url, options) => {
        calls.push([url, options]);
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              session: {
                session_id: "xyz-1",
                status: "in_progress",
                summary: { total_cells: 3, pending_cells: 0 },
                axes: [],
                results: { status: "pending", main_grid: {}, sub_grids: [], lone_images: [], warnings: [] },
              },
            };
          },
        };
      },
    );

    expect(estimateResult.ok).toBe(true);
    expect(runResult.ok).toBe(true);
    expect(calls[0][0]).toBe("/rookieui/xyz-plot/estimate");
    expect(calls[1][0]).toBe("/rookieui/xyz-plot/run");
    expect(JSON.parse(calls[0][1].body).axes[0].axis_id).toBe("steps");
    expect(JSON.parse(calls[1][1].body).base_request.prompt).toBe("skyline");
  });

  test("loads xyz-plot sessions, detail, and cancel routes with client-scoped paths", async () => {
    const listCalls = [];
    const listResult = await fetchRookieUIXYZPlotSessions(
      async (url) => {
        listCalls.push(url);
        return {
          ok: true,
          async json() {
            return { sessions: [{ session_id: "xyz-1" }] };
          },
        };
      },
      { clientId: "browser-1" },
    );
    const detailCalls = [];
    const detailResult = await fetchRookieUIXYZPlotSessionDetail(
      "xyz-1",
      { clientId: "browser-1" },
      async (url) => {
        detailCalls.push(url);
        return {
          ok: true,
          async json() {
            return {
              session: {
                session_id: "xyz-1",
                status: "completed",
                summary: { total_cells: 3, pending_cells: 0 },
                axes: [],
                cells: [],
                results: { status: "ready", main_grid: {}, sub_grids: [], lone_images: [], warnings: [] },
              },
            };
          },
        };
      },
    );
    const cancelCalls = [];
    const cancelResult = await cancelRookieUIXYZPlotSession(
      "xyz-1",
      { clientId: "browser-1" },
      async (url, options) => {
        cancelCalls.push([url, options]);
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              session: {
                session_id: "xyz-1",
                status: "cancelled",
                cancel_requested: true,
                summary: { total_cells: 3, cancelled_cells: 3 },
                axes: [],
                cells: [],
                results: { status: "pending", main_grid: {}, sub_grids: [], lone_images: [], warnings: [] },
              },
            };
          },
        };
      },
    );

    expect(listResult.ok).toBe(true);
    expect(detailResult.ok).toBe(true);
    expect(cancelResult.ok).toBe(true);
    expect(listCalls[0]).toBe("/rookieui/xyz-plot/sessions?client_id=browser-1");
    expect(detailCalls[0]).toBe("/rookieui/xyz-plot/sessions/xyz-1?client_id=browser-1");
    expect(cancelCalls[0][0]).toBe("/rookieui/xyz-plot/sessions/xyz-1/cancel");
    expect(JSON.parse(cancelCalls[0][1].body)).toEqual({ client_id: "browser-1" });
  });

  test("builds client-scoped queue paths and prompt-history helpers", async () => {
    const queueCalls = [];
    const queueResult = await fetchRookieUIQueue(
      async (url) => {
        queueCalls.push(url);
        return {
          ok: true,
          async json() {
            return { source: "host", queue_remaining: 0, jobs: [] };
          },
        };
      },
      { clientId: "browser-1" },
    );
    expect(queueResult.ok).toBe(true);
    expect(queueCalls[0]).toContain("/rookieui/queue?client_id=browser-1");

    const queueJobCalls = [];
    const queueJob = await fetchRookieUIQueueJob(
      "prompt-123",
      { clientId: "browser-1" },
      async (url) => {
        queueJobCalls.push(url);
        return {
          ok: true,
          async json() {
            return { source: "host", queue_remaining: 0, job: { id: "prompt-123", status: "completed" } };
          },
        };
      },
    );
    expect(queueJob.ok).toBe(true);
    expect(queueJobCalls[0]).toContain("/rookieui/queue/prompt-123?client_id=browser-1");

    const historyCalls = [];
    const history = await fetchRookieUIHistoryPrompt("prompt-123", async (url) => {
      historyCalls.push(url);
      return {
        ok: true,
        async json() {
          return { "prompt-123": { outputs: {} } };
        },
      };
    });
    expect(history.ok).toBe(true);
    expect(historyCalls[0]).toBe("/history/prompt-123");
  });

  test("loads dynamic controlnet resources and keeps fallback contracts", async () => {
    const calls = [];
    const fetchImpl = async (url) => {
      calls.push(url);
      if (url === "/rookieui/controlnet/model_list") {
        return {
          ok: true,
          async json() {
            return {
              source: "host",
              contract: {
                version: "r72-20260412",
                ui_variant: "integrated_sidebar_controlnet",
                unit_count: 3,
                advanced_contract: { version: "r111-20260415", runtime_state: "rookieui_native_advanced_runtime" },
              },
              model_list: ["control_v11p_sd15_canny.safetensors"],
              default_model: "control_v11p_sd15_canny.safetensors",
            };
          },
        };
      }
      if (url === "/rookieui/controlnet/module_list") {
        return {
          ok: true,
          async json() {
            return {
              source: "internal",
              contract: {
                version: "r72-20260412",
                ui_variant: "integrated_sidebar_controlnet",
                unit_count: 3,
                advanced_contract: { version: "r111-20260415", runtime_state: "rookieui_native_advanced_runtime" },
              },
              module_list: ["none", "canny", "depth"],
              default_module: "none",
            };
          },
        };
      }
      if (url === "/rookieui/controlnet/control_types") {
        return {
          ok: true,
          async json() {
            return {
              source: "internal",
              contract: {
                version: "r72-20260412",
                ui_variant: "integrated_sidebar_controlnet",
                unit_count: 3,
                advanced_contract: { version: "r111-20260415", runtime_state: "rookieui_native_advanced_runtime" },
              },
              control_type_order: ["All", "Canny", "Depth"],
              default_type: "All",
              control_types: {
                All: {
                  module_list: ["none", "canny", "depth"],
                  model_list: ["control_v11p_sd15_canny.safetensors"],
                  default_option: "none",
                },
              },
            };
          },
        };
      }
      throw new Error(`unexpected url: ${url}`);
    };

    const models = await fetchRookieUIControlNetModels(fetchImpl);
    const modules = await fetchRookieUIControlNetModules(fetchImpl);
    const types = await fetchRookieUIControlNetTypes(fetchImpl);

    expect(models.ok).toBe(true);
    expect(modules.ok).toBe(true);
    expect(types.ok).toBe(true);
    expect(models.data.model_list[0]).toContain("canny");
    expect(modules.data.module_list).toContain("depth");
    expect(types.data.control_type_order).toContain("Canny");
    expect(calls).toEqual([
      "/rookieui/controlnet/model_list",
      "/rookieui/controlnet/module_list",
      "/rookieui/controlnet/control_types",
    ]);

    const fallbackTypes = await fetchRookieUIControlNetTypes(async () => {
      throw new Error("offline");
    });
    expect(fallbackTypes.ok).toBe(false);
    expect(fallbackTypes.data.contract.version).toBe("r72-20260412");
    expect(fallbackTypes.data.contract.advanced_contract.runtime_state).toBe("rookieui_native_advanced_runtime");
    expect(fallbackTypes.data.default_type).toBe("All");
  });

  test("loads adetailer catalog fallback contract", async () => {
    const fallbackCatalog = await fetchRookieUIADetailerCatalog(async () => {
      throw new Error("offline");
    });

    expect(fallbackCatalog.ok).toBe(false);
    expect(fallbackCatalog.data.contract.version).toBe("r74f77-20260414");
    expect(fallbackCatalog.data.contract.unit_count).toBe(4);
    expect(fallbackCatalog.data.contract.detector_provider_families).toEqual([
      "none",
      "ultralytics_bbox",
      "ultralytics_segm",
      "mediapipe_face",
    ]);
    expect(fallbackCatalog.data.prompt_tokens).toEqual(["[PROMPT]", "[SEP]", "[SKIP]"]);
    expect(fallbackCatalog.data.controlnet_modes).toEqual(["none", "passthrough", "custom"]);
    expect(fallbackCatalog.data.availability.runtime_stages).toContain("detect_mask");
    expect(fallbackCatalog.data.warning_codes.ADETAILER_CONTROLNET_PASSTHROUGH_EMPTY).toContain("passthrough");
  });

  test("emits guarded debug warnings only when ROOKIEUI_DEBUG is enabled", async () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const originalFlag = globalThis.__ROOKIEUI_DEBUG__;

    globalThis.__ROOKIEUI_DEBUG__ = false;
    await fetchRookieUICapabilities(async () => {
      throw new Error("offline");
    });
    expect(warnSpy).not.toHaveBeenCalled();

    globalThis.__ROOKIEUI_DEBUG__ = true;
    await fetchRookieUICapabilities(async () => {
      throw new Error("offline");
    });
    expect(warnSpy).toHaveBeenCalled();
    expect(String(warnSpy.mock.calls[0][0])).toContain("[RookieUI:api.capabilities]");

    warnSpy.mockRestore();
    globalThis.__ROOKIEUI_DEBUG__ = originalFlag;
  });
});
