import { describe, expect, test, vi } from "vitest";

import {
  fetchRookieUICapabilities,
  fetchRookieUICompatibility,
  fetchRookieUIHistoryPrompt,
  fetchRookieUIModels,
  fetchRookieUIPresets,
  fetchRookieUIQueue,
  fetchRookieUIQueueJob,
  inspectRookieUIPngInfo,
  submitRookieUIExtras,
  submitRookieUIImg2Img,
  submitRookieUITxt2Img,
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
    expect(models.data.catalog.primary_model_category_by_family.flux).toBe("diffusion_models");
    expect(models.data.catalog.categories.checkpoints.sidebar_visible).toBe(true);
    expect(compatibility.data.samplers[0].id).toBe("euler_ancestral");
    expect(compatibility.data.schedulers[0].id).toBe("normal");
    expect(presets.data.presets[0].id).toBe("sd15");
    expect(queue.data.queue_remaining).toBe(0);
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
