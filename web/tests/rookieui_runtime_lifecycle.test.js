import { afterEach, describe, expect, test, vi } from "vitest";

import {
  createGenerationRuntimeHelpers,
  createGenerationRuntimeState,
  destroyGenerationRuntimeState,
} from "../rookieui_generation_runtime.js";
import { createPreviewFullscreenViewer } from "../rookieui_preview_fullscreen.js";

function createRuntimeEventTarget() {
  const listeners = new Map();
  return {
    addEventListener: vi.fn((eventName, handler) => {
      const handlers = listeners.get(eventName) ?? new Set();
      handlers.add(handler);
      listeners.set(eventName, handlers);
    }),
    removeEventListener: vi.fn((eventName, handler) => {
      listeners.get(eventName)?.delete(handler);
    }),
    dispatch(eventName, detail) {
      for (const handler of listeners.get(eventName) ?? []) {
        handler({ detail });
      }
    },
  };
}

function createFrameHarness() {
  let nextHandle = 1;
  const frames = new Map();
  const requestAnimationFrame = vi.fn((callback) => {
    const handle = nextHandle;
    nextHandle += 1;
    frames.set(handle, callback);
    return handle;
  });
  const cancelAnimationFrame = vi.fn((handle) => {
    frames.delete(handle);
  });
  vi.stubGlobal("requestAnimationFrame", requestAnimationFrame);
  vi.stubGlobal("cancelAnimationFrame", cancelAnimationFrame);
  return {
    cancelAnimationFrame,
    flushLatest() {
      const entry = Array.from(frames.entries()).at(-1);
      if (!entry) return;
      const [handle, callback] = entry;
      frames.delete(handle);
      callback(0);
    },
    requestAnimationFrame,
  };
}

function createTrackingSubject(
  runtimeApi,
  {
    runtimeState = createGenerationRuntimeState(),
    promptId = "job-current",
    fetchQueueJobRequest = vi.fn(async () => ({ ok: true, data: { job: null } })),
    fetchPromptHistoryRequest = vi.fn(async () => ({ ok: true, data: {} })),
    setPreviewContent = vi.fn(),
  } = {},
) {
  const statusNode = document.createElement("p");
  statusNode.textContent = "mounted";
  const previewBox = document.createElement("div");
  const helpers = createGenerationRuntimeHelpers({
    emitFrontendDebugWarning: vi.fn(),
    setPreviewContent,
    applyCrossPanePayload: vi.fn(),
    activateShellTab: vi.fn(),
  });
  const tracking = helpers.trackGenerationRuntime(
    {
      runtimeApi,
      fetchQueueJobRequest,
      fetchPromptHistoryRequest,
    },
    promptId,
    statusNode,
    runtimeState,
    previewBox,
  );
  return { runtimeState, setPreviewContent, statusNode, tracking };
}

describe("RookieUI owned runtime lifecycle", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    document.body.replaceChildren();
  });

  test("destroy cancels polling, unregisters host events, revokes blob preview, and blocks late writes", async () => {
    vi.useFakeTimers();
    const runtimeApi = {
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    const revokeObjectURL = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    const runtimeState = createGenerationRuntimeState();
    runtimeState.previewUrl = "blob:active-preview";
    const statusNode = document.createElement("p");
    statusNode.textContent = "mounted";
    const previewBox = document.createElement("div");
    const helpers = createGenerationRuntimeHelpers({
      emitFrontendDebugWarning: vi.fn(),
      setPreviewContent: vi.fn(),
      applyCrossPanePayload: vi.fn(),
      activateShellTab: vi.fn(),
    });
    const tracking = helpers.trackGenerationRuntime(
      {
        runtimeApi,
        fetchQueueJobRequest: vi.fn(async () => ({ ok: true, data: { job: null } })),
        fetchPromptHistoryRequest: vi.fn(),
      },
      "prompt-lifecycle",
      statusNode,
      runtimeState,
      previewBox,
    );

    await Promise.resolve();
    await Promise.resolve();
    expect(runtimeApi.addEventListener.mock.calls.map(([eventName]) => eventName)).toEqual([
      "progress",
      "progress_state",
      "b_preview_with_metadata",
      "b_preview",
      "execution_success",
      "execution_error",
      "execution_interrupted",
    ]);
    expect(vi.getTimerCount()).toBe(1);

    destroyGenerationRuntimeState(runtimeState);
    await tracking;

    expect(runtimeApi.removeEventListener.mock.calls.map(([eventName]) => eventName)).toEqual([
      "progress",
      "progress_state",
      "b_preview_with_metadata",
      "b_preview",
      "execution_success",
      "execution_error",
      "execution_interrupted",
    ]);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:active-preview");
    expect(vi.getTimerCount()).toBe(0);
    expect(runtimeState.disposed).toBe(true);
    expect(statusNode.textContent).toBe("Waiting for queue registration...");
  });

  test("coalesces matching progress and progress_state bursts to the latest animation-frame update", async () => {
    vi.useFakeTimers();
    const runtimeApi = createRuntimeEventTarget();
    const frameHarness = createFrameHarness();
    const { runtimeState, statusNode, tracking } = createTrackingSubject(runtimeApi);

    await Promise.resolve();
    await Promise.resolve();
    expect(statusNode.textContent).toBe("Waiting for queue registration...");

    runtimeApi.dispatch("progress", { prompt_id: "job-other", value: 9, max: 10, node: "1" });
    expect(frameHarness.requestAnimationFrame).not.toHaveBeenCalled();

    runtimeApi.dispatch("progress", { prompt_id: "job-current", value: 1, max: 10, node: "1" });
    runtimeApi.dispatch("progress", { prompt_id: "job-current", value: 6, max: 10, node: "1" });
    expect(frameHarness.requestAnimationFrame).toHaveBeenCalledTimes(1);
    expect(statusNode.textContent).toBe("Waiting for queue registration...");
    frameHarness.flushLatest();
    expect(statusNode.textContent).toBe("in progress (60%)");

    runtimeApi.dispatch("progress_state", {
      prompt_id: "job-other",
      nodes: {
        "2": { prompt_id: "job-other", node_id: "2", state: "running", value: 4, max: 5 },
      },
    });
    expect(frameHarness.requestAnimationFrame).toHaveBeenCalledTimes(1);
    runtimeApi.dispatch("progress_state", {
      prompt_id: "job-current",
      nodes: {
        "1": { prompt_id: "job-current", node_id: "1", state: "finished", value: 10, max: 10 },
        "2": { prompt_id: "job-current", node_id: "2", state: "running", value: 3, max: 4 },
      },
    });
    expect(frameHarness.requestAnimationFrame).toHaveBeenCalledTimes(2);
    frameHarness.flushLatest();
    expect(statusNode.textContent).toBe("in progress (75%)");

    destroyGenerationRuntimeState(runtimeState);
    await tracking;
    expect(frameHarness.cancelAnimationFrame).not.toHaveBeenCalled();
  });

  test.each([
    ["execution_success", "Generation finished; syncing output: job-current"],
    ["execution_error", "Generation failed: job-current"],
    ["execution_interrupted", "Generation cancelled: job-current"],
  ])("handles matching %s and cancels pending progress without cross-job mutation", async (eventName, expected) => {
    vi.useFakeTimers();
    const runtimeApi = createRuntimeEventTarget();
    const frameHarness = createFrameHarness();
    const { runtimeState, statusNode, tracking } = createTrackingSubject(runtimeApi);

    await Promise.resolve();
    await Promise.resolve();
    expect(vi.getTimerCount()).toBe(1);
    runtimeApi.dispatch("progress", { prompt_id: "job-current", value: 2, max: 10, node: "1" });
    expect(frameHarness.requestAnimationFrame).toHaveBeenCalledTimes(1);

    runtimeApi.dispatch(eventName, { prompt_id: "job-other" });
    expect(statusNode.textContent).toBe("Waiting for queue registration...");
    expect(frameHarness.cancelAnimationFrame).not.toHaveBeenCalled();
    expect(runtimeApi.removeEventListener).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(1);

    runtimeApi.dispatch(eventName, { prompt_id: "job-current" });
    expect(statusNode.textContent).toBe(expected);
    expect(frameHarness.cancelAnimationFrame).toHaveBeenCalledTimes(1);
    expect(runtimeApi.removeEventListener).toHaveBeenCalledTimes(7);
    expect(vi.getTimerCount()).toBe(0);

    destroyGenerationRuntimeState(runtimeState);
    await tracking;
  });

  test("terminal during history resolution prevents late preview and status mutation", async () => {
    vi.useFakeTimers();
    const runtimeApi = createRuntimeEventTarget();
    let resolveHistory;
    const fetchPromptHistoryRequest = vi.fn(
      () =>
        new Promise((resolve) => {
          resolveHistory = resolve;
        }),
    );
    const fetchQueueJobRequest = vi.fn(async () => ({
      ok: true,
      data: { job: { id: "job-current", status: "in_progress" } },
    }));
    const subject = createTrackingSubject(runtimeApi, {
      fetchPromptHistoryRequest,
      fetchQueueJobRequest,
    });

    for (let attempt = 0; attempt < 8 && fetchPromptHistoryRequest.mock.calls.length === 0; attempt += 1) {
      await Promise.resolve();
    }
    expect(fetchPromptHistoryRequest).toHaveBeenCalledTimes(1);
    const previewWritesBeforeTerminal = subject.setPreviewContent.mock.calls.length;

    runtimeApi.dispatch("execution_interrupted", { prompt_id: "job-other" });
    expect(runtimeApi.removeEventListener).not.toHaveBeenCalled();
    runtimeApi.dispatch("execution_interrupted", { prompt_id: "job-current" });
    expect(subject.statusNode.textContent).toBe("Generation cancelled: job-current");
    expect(runtimeApi.removeEventListener).toHaveBeenCalledTimes(7);
    expect(vi.getTimerCount()).toBe(0);

    resolveHistory({
      ok: true,
      data: {
        "job-current": {
          outputs: {
            "7": { images: [{ filename: "late-history.png", subfolder: "", type: "output" }] },
          },
        },
      },
    });
    await subject.tracking;

    expect(subject.setPreviewContent).toHaveBeenCalledTimes(previewWritesBeforeTerminal);
    expect(subject.runtimeState.finalImageDescriptor).toBeNull();
    expect(subject.statusNode.textContent).toBe("Generation cancelled: job-current");
    expect(vi.getTimerCount()).toBe(0);
  });

  test("run replacement rejects a late final-history result without disposing successor listeners", async () => {
    vi.useFakeTimers();
    const runtimeApi = createRuntimeEventTarget();
    const frameHarness = createFrameHarness();
    const runtimeState = createGenerationRuntimeState();
    let resolveFinalHistory;
    const fetchPromptHistoryRequest = vi.fn(
      () =>
        new Promise((resolve) => {
          resolveFinalHistory = resolve;
        }),
    );
    const first = createTrackingSubject(runtimeApi, {
      runtimeState,
      fetchPromptHistoryRequest,
    });

    await Promise.resolve();
    await Promise.resolve();
    runtimeApi.dispatch("execution_success", { prompt_id: "job-current" });
    for (let attempt = 0; attempt < 8 && fetchPromptHistoryRequest.mock.calls.length === 0; attempt += 1) {
      await Promise.resolve();
    }
    expect(fetchPromptHistoryRequest).toHaveBeenCalledTimes(1);
    expect(runtimeApi.removeEventListener).toHaveBeenCalledTimes(7);
    const firstPreviewWritesBeforeReplacement = first.setPreviewContent.mock.calls.length;

    const replacement = createTrackingSubject(runtimeApi, { runtimeState, promptId: "job-next" });
    await Promise.resolve();
    await Promise.resolve();
    expect(runtimeApi.addEventListener).toHaveBeenCalledTimes(14);

    resolveFinalHistory({
      ok: true,
      data: {
        "job-current": {
          outputs: {
            "7": { images: [{ filename: "stale-final.png", subfolder: "", type: "output" }] },
          },
        },
      },
    });
    await first.tracking;

    expect(first.setPreviewContent).toHaveBeenCalledTimes(firstPreviewWritesBeforeReplacement);
    expect(first.statusNode.textContent).toBe("Generation finished; syncing output: job-current");
    expect(runtimeState.finalImageDescriptor).toBeNull();
    expect(runtimeApi.removeEventListener).toHaveBeenCalledTimes(7);

    runtimeApi.dispatch("progress", { prompt_id: "job-next", value: 1, max: 2, node: "2" });
    expect(frameHarness.requestAnimationFrame).toHaveBeenCalledTimes(1);
    frameHarness.flushLatest();
    expect(replacement.statusNode.textContent).toBe("in progress (50%)");

    destroyGenerationRuntimeState(runtimeState);
    await replacement.tracking;
    expect(runtimeApi.removeEventListener).toHaveBeenCalledTimes(14);
    expect(vi.getTimerCount()).toBe(0);
  });

  test("run replacement cancels the prior frame, wait, and seven listeners before rebinding", async () => {
    vi.useFakeTimers();
    const runtimeApi = createRuntimeEventTarget();
    const frameHarness = createFrameHarness();
    const revokeObjectURL = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    const runtimeState = createGenerationRuntimeState();
    const first = createTrackingSubject(runtimeApi, { runtimeState, promptId: "job-current" });

    await Promise.resolve();
    await Promise.resolve();
    runtimeApi.dispatch("progress", { prompt_id: "job-current", value: 2, max: 10, node: "1" });
    expect(frameHarness.requestAnimationFrame).toHaveBeenCalledTimes(1);
    runtimeState.previewUrl = "blob:first-run-preview";

    const replacement = createTrackingSubject(runtimeApi, { runtimeState, promptId: "job-next" });
    await Promise.resolve();
    await Promise.resolve();
    await first.tracking;
    expect(frameHarness.cancelAnimationFrame).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:first-run-preview");
    expect(runtimeState.previewUrl).toBe("");
    expect(runtimeApi.removeEventListener).toHaveBeenCalledTimes(7);
    expect(runtimeApi.addEventListener).toHaveBeenCalledTimes(14);

    runtimeApi.dispatch("progress", { prompt_id: "job-current", value: 9, max: 10, node: "1" });
    expect(frameHarness.requestAnimationFrame).toHaveBeenCalledTimes(1);
    runtimeApi.dispatch("progress", { prompt_id: "job-next", value: 1, max: 2, node: "2" });
    expect(frameHarness.requestAnimationFrame).toHaveBeenCalledTimes(2);
    frameHarness.flushLatest();
    expect(replacement.statusNode.textContent).toBe("in progress (50%)");

    destroyGenerationRuntimeState(runtimeState);
    await replacement.tracking;
    expect(runtimeApi.removeEventListener).toHaveBeenCalledTimes(14);
  });

  test("preview fullscreen destroy removes document listeners and image binding idempotently", () => {
    const addEventListener = vi.spyOn(document, "addEventListener");
    const removeEventListener = vi.spyOn(document, "removeEventListener");
    const host = document.createElement("div");
    const previewBox = document.createElement("div");
    const image = document.createElement("img");
    image.className = "rookieui-shell__preview-image";
    previewBox.appendChild(image);
    const toolbar = document.createElement("div");
    host.append(previewBox, toolbar);
    document.body.appendChild(host);
    const viewer = createPreviewFullscreenViewer(
      {
        idPrefix: "lifecycle",
        previewBox,
        previewToolbar: toolbar,
        createIconActionButton: () => {
          const button = document.createElement("button");
          button.appendChild(document.createElement("span"));
          return button;
        },
      },
      {
        isCanvasElementFullscreen: () => false,
        toggleCanvasFullscreen: async () => "unavailable",
      },
    );

    viewer.destroy();
    viewer.destroy();

    expect(addEventListener).toHaveBeenCalledWith("fullscreenchange", expect.any(Function));
    expect(removeEventListener).toHaveBeenCalledWith("fullscreenchange", expect.any(Function));
    expect(removeEventListener).toHaveBeenCalledWith("webkitfullscreenchange", expect.any(Function));
    expect(previewBox.__previewFullscreenController).toBeUndefined();
  });
});
