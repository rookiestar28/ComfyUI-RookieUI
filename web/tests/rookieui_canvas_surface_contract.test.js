import { describe, expect, test } from "vitest";

import {
  CANVAS_ACTIONS,
  hasCanvasSourceImage,
  normalizeCanvasSourceValue,
  requestCanvasFullscreen,
} from "../sidebar_tabs/rookieui_canvas_surface_contract.js";

describe("canvas surface contract helpers", () => {
  test("normalizes source values and detects source presence", () => {
    expect(normalizeCanvasSourceValue(null)).toBe("");
    expect(normalizeCanvasSourceValue("  data:image/png;base64,abc  ")).toBe("data:image/png;base64,abc");
    expect(hasCanvasSourceImage("", "")).toBe(false);
    expect(hasCanvasSourceImage("data:image/png;base64,abc", "")).toBe(true);
    expect(hasCanvasSourceImage("", "control-image-asset")).toBe(true);
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
});
