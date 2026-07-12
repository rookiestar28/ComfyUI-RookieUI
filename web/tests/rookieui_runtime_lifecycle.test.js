import { afterEach, describe, expect, test, vi } from "vitest";

import {
  createGenerationRuntimeHelpers,
  createGenerationRuntimeState,
  destroyGenerationRuntimeState,
} from "../rookieui_generation_runtime.js";
import { createPreviewFullscreenViewer } from "../rookieui_preview_fullscreen.js";

describe("RookieUI owned runtime lifecycle", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
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
    expect(runtimeApi.addEventListener).toHaveBeenCalledTimes(3);
    expect(vi.getTimerCount()).toBe(1);

    destroyGenerationRuntimeState(runtimeState);
    await tracking;

    expect(runtimeApi.removeEventListener).toHaveBeenCalledTimes(3);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:active-preview");
    expect(vi.getTimerCount()).toBe(0);
    expect(runtimeState.disposed).toBe(true);
    expect(statusNode.textContent).toBe("Waiting for queue registration...");
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
