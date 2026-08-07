import { describe, expect, test, vi } from "vitest";

import { createPromptWorkbenchController } from "../sidebar_tabs/prompt_workbench/rookieui_prompt_workbench_controller.js";

const normalizeStatePayload = (namespace, payload = {}) => ({
  namespace,
  workbench_open: Boolean(payload.workbench_open),
  active_panel: ["editor", "history", "favorites", "catalog", "assist", "format"].includes(payload.active_panel)
    ? payload.active_panel
    : "editor",
  draft_prompt: String(payload.draft_prompt ?? ""),
  selected_entry_id: String(payload.selected_entry_id ?? ""),
});

describe("Prompt Workbench DOM-free controller", () => {
  test("keeps prompt and negative namespaces isolated and exposes cloned snapshots", () => {
    const controller = createPromptWorkbenchController({
      namespaces: { prompt: "txt2img_prompt", negative: "txt2img_negative" },
      initialConfig: { language: "en", ui_preferences: { preferred_panel: "editor" } },
      normalizeStatePayload,
    });

    controller.setSurfaceState("txt2img_prompt", { draft_prompt: "masterpiece", active_panel: "history" });
    controller.setSurfaceState("txt2img_negative", { draft_prompt: "bad anatomy", active_panel: "favorites" });

    expect(controller.getSurfaceState("txt2img_prompt")).toMatchObject({
      namespace: "txt2img_prompt",
      draft_prompt: "masterpiece",
      active_panel: "history",
    });
    expect(controller.getSurfaceState("txt2img_negative")).toMatchObject({
      namespace: "txt2img_negative",
      draft_prompt: "bad anatomy",
      active_panel: "favorites",
    });

    const snapshot = controller.getSurfaceState("txt2img_prompt");
    snapshot.draft_prompt = "mutated outside controller";
    expect(controller.getSurfaceState("txt2img_prompt").draft_prompt).toBe("masterpiece");
  });

  test("normalizes fixed scope and supported panels without DOM construction", () => {
    const controller = createPromptWorkbenchController({
      namespaces: { prompt: "prompt", negative: "negative" },
      fixedScope: "negative",
      normalizeStatePayload,
    });

    expect(controller.getActiveScope()).toBe("negative");
    expect(controller.setActiveScope("prompt")).toBe("negative");
    expect(controller.setActivePanel("not-a-panel")).toBe("editor");
    expect(controller.setActivePanel("history")).toBe("history");
  });

  test("provides collection snapshots and rejects stale async epochs after destroy", () => {
    const controller = createPromptWorkbenchController({
      namespaces: { prompt: "prompt", negative: "negative" },
      normalizeStatePayload,
    });
    const epoch = controller.beginAsyncEpoch();
    controller.replaceCollection("history", "prompt", [{ id: "h1", prompt_text: "safe" }]);
    expect(controller.getCollection("history", "prompt")).toEqual([{ id: "h1", prompt_text: "safe" }]);
    expect(controller.isAsyncEpochCurrent(epoch)).toBe(true);

    controller.destroy();

    expect(controller.isDestroyed()).toBe(true);
    expect(controller.isAsyncEpochCurrent(epoch)).toBe(false);
    expect(controller.getCollection("history", "prompt")).toEqual([]);
    expect(controller.replaceCollection("history", "prompt", [{ id: "late" }])).toEqual([]);
  });

  test("advances the epoch for each new asynchronous operation", () => {
    const controller = createPromptWorkbenchController({
      namespaces: { prompt: "prompt", negative: "negative" },
      normalizeStatePayload,
    });
    const firstEpoch = controller.beginAsyncEpoch();
    const secondEpoch = controller.beginAsyncEpoch();

    expect(secondEpoch).toBeGreaterThan(firstEpoch);
    expect(controller.isAsyncEpochCurrent(firstEpoch)).toBe(false);
    expect(controller.isAsyncEpochCurrent(secondEpoch)).toBe(true);
  });

  test("config and blacklist updates return clones and do not expose caller mutation", () => {
    const controller = createPromptWorkbenchController({
      namespaces: { prompt: "prompt", negative: "negative" },
      initialConfig: { language: "en", translation: { providers: {} } },
      initialBlacklist: { enabled: false, entries: [] },
      normalizeStatePayload,
    });
    const onChange = vi.fn();
    const config = controller.updateConfig({ language: "zh-TW", translation: { providers: {} } });
    const blacklist = controller.updateBlacklist({ enabled: true, entries: ["blurry"] });
    config.translation.providers.extra = "outside";
    blacklist.entries.push("outside");
    onChange(controller.getConfigSnapshot(), controller.getBlacklistSnapshot());

    expect(controller.getConfigSnapshot().language).toBe("zh-TW");
    expect(controller.getConfigSnapshot().translation.providers.extra).toBeUndefined();
    expect(controller.getBlacklistSnapshot().entries).toEqual(["blurry"]);
    expect(onChange).toHaveBeenCalledTimes(1);
  });
});
