import { describe, expect, test } from "vitest";

import {
  CANVAS_FULLSCREEN_ACTIONS,
  CANVAS_ACTIONS,
  CANVAS_INTERACTION_MODES,
  canCanvasStageOpenUpload,
  hasCanvasSourceImage,
  isCanvasElementFullscreen,
  normalizeCanvasSourceValue,
  resolveCanvasInteractionMode,
  requestCanvasFullscreen,
  toggleCanvasFullscreen,
} from "../sidebar_tabs/rookieui_canvas_surface_contract.js";

describe("canvas surface contract helpers", () => {
  test("normalizes source values and detects source presence", () => {
    expect(normalizeCanvasSourceValue(null)).toBe("");
    expect(normalizeCanvasSourceValue("  data:image/png;base64,abc  ")).toBe("data:image/png;base64,abc");
    expect(hasCanvasSourceImage("", "")).toBe(false);
    expect(hasCanvasSourceImage("data:image/png;base64,abc", "")).toBe(true);
    expect(hasCanvasSourceImage("", "control-image-asset")).toBe(true);
    expect(resolveCanvasInteractionMode("", "")).toBe(CANVAS_INTERACTION_MODES.upload);
    expect(resolveCanvasInteractionMode("data:image/png;base64,abc", "")).toBe(CANVAS_INTERACTION_MODES.edit);
    expect(canCanvasStageOpenUpload("", "")).toBe(true);
    expect(canCanvasStageOpenUpload("data:image/png;base64,abc", "")).toBe(false);
  });

  test("requests fullscreen only when supported", async () => {
    expect(CANVAS_ACTIONS.fullscreen).toBe("fullscreen");
    expect(await requestCanvasFullscreen(null)).toBe(false);

    let requested = false;
    const element = {
      async requestFullscreen() {
        requested = true;
      },
    };

    await expect(requestCanvasFullscreen(element)).resolves.toBe(true);
    expect(requested).toBe(true);

    const failingElement = {
      async requestFullscreen() {
        throw new Error("denied");
      },
    };
    await expect(requestCanvasFullscreen(failingElement)).resolves.toBe(false);
  });

  test("toggles fullscreen state between enter and exit actions", async () => {
    let fullscreenElement = null;
    const originalDescriptor = Object.getOwnPropertyDescriptor(document, "fullscreenElement");
    const originalExitDescriptor = Object.getOwnPropertyDescriptor(document, "exitFullscreen");
    Object.defineProperty(document, "fullscreenElement", {
      configurable: true,
      get() {
        return fullscreenElement;
      },
    });

    const element = {
      async requestFullscreen() {
        fullscreenElement = element;
      },
      contains(target) {
        return target === element;
      },
    };

    Object.defineProperty(document, "exitFullscreen", {
      configurable: true,
      value: async () => {
        fullscreenElement = null;
      },
    });

    try {
      expect(isCanvasElementFullscreen(element)).toBe(false);
      await expect(toggleCanvasFullscreen(element)).resolves.toBe(CANVAS_FULLSCREEN_ACTIONS.entered);
      expect(isCanvasElementFullscreen(element)).toBe(true);
      await expect(toggleCanvasFullscreen(element)).resolves.toBe(CANVAS_FULLSCREEN_ACTIONS.exited);
      expect(isCanvasElementFullscreen(element)).toBe(false);
    } finally {
      if (originalDescriptor) {
        Object.defineProperty(document, "fullscreenElement", originalDescriptor);
      } else {
        Reflect.deleteProperty(document, "fullscreenElement");
      }
      if (originalExitDescriptor) {
        Object.defineProperty(document, "exitFullscreen", originalExitDescriptor);
      } else {
        Reflect.deleteProperty(document, "exitFullscreen");
      }
    }
  });
});
