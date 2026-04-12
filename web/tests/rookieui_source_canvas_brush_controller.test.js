import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { createSourceCanvasBrushController } from "../sidebar_tabs/rookieui_source_canvas_brush.js";

function createMock2dContext() {
  return {
    clearRect: vi.fn(),
    drawImage: vi.fn(),
    save: vi.fn(),
    restore: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
  };
}

describe("createSourceCanvasBrushController fullscreen zoom behavior", () => {
  let originalGetContext;
  let originalImage;
  let originalFullscreenDescriptor;
  let originalUserAgentDescriptor;
  let fullscreenElementRef;

  beforeEach(() => {
    originalGetContext = HTMLCanvasElement.prototype.getContext;
    originalImage = globalThis.Image;
    originalFullscreenDescriptor = Object.getOwnPropertyDescriptor(document, "fullscreenElement");
    originalUserAgentDescriptor = Object.getOwnPropertyDescriptor(globalThis.navigator, "userAgent");

    const context = createMock2dContext();
    HTMLCanvasElement.prototype.getContext = vi.fn(() => context);

    class MockImage {
      constructor() {
        this.onload = null;
        this.onerror = null;
        this.naturalWidth = 200;
        this.naturalHeight = 100;
        this.width = 200;
        this.height = 100;
      }

      set src(value) {
        this._src = value;
        queueMicrotask(() => {
          if (typeof this.onload === "function") {
            this.onload();
          }
        });
      }

      get src() {
        return this._src;
      }
    }

    globalThis.Image = MockImage;
    Object.defineProperty(globalThis.navigator, "userAgent", {
      configurable: true,
      value: "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    });
    fullscreenElementRef = null;
    Object.defineProperty(document, "fullscreenElement", {
      configurable: true,
      get() {
        return fullscreenElementRef;
      },
    });
  });

  afterEach(() => {
    HTMLCanvasElement.prototype.getContext = originalGetContext;
    globalThis.Image = originalImage;
    if (originalFullscreenDescriptor) {
      Object.defineProperty(document, "fullscreenElement", originalFullscreenDescriptor);
    } else {
      Reflect.deleteProperty(document, "fullscreenElement");
    }
    if (originalUserAgentDescriptor) {
      Object.defineProperty(globalThis.navigator, "userAgent", originalUserAgentDescriptor);
    }
    document.body.innerHTML = "";
  });

  test("fits source by default, expands with fullscreen zoom slider, and resets on fullscreen exit", async () => {
    const stage = document.createElement("div");
    stage.id = "test-source-stage";
    stage.getBoundingClientRect = () => ({
      width: 400,
      height: 300,
      left: 0,
      top: 0,
      right: 400,
      bottom: 300,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    });

    const previewImage = document.createElement("img");
    stage.appendChild(previewImage);

    const toolbar = document.createElement("div");
    document.body.appendChild(stage);
    document.body.appendChild(toolbar);

    const controller = createSourceCanvasBrushController({
      idPrefix: "test-source",
      stage,
      toolbar,
      previewImage,
      onCommitSource: vi.fn(async () => {}),
    });

    await controller.syncSourceData("data:image/png;base64,c291cmNl");

    const fullscreenZoom = document.getElementById("test-source-fullscreen-zoom");
    const fullscreenSlider = document.getElementById("test-source-fullscreen-zoom-slider");
    expect(fullscreenZoom).not.toBeNull();
    expect(fullscreenSlider).not.toBeNull();
    expect(fullscreenZoom.hidden).toBe(true);
    expect(previewImage.style.width).toBe("400px");
    expect(previewImage.style.height).toBe("200px");

    fullscreenElementRef = stage;
    document.dispatchEvent(new Event("fullscreenchange"));
    expect(fullscreenZoom.hidden).toBe(false);

    fullscreenSlider.value = "200";
    fullscreenSlider.dispatchEvent(new Event("input", { bubbles: true }));
    expect(previewImage.style.width).toBe("800px");
    expect(previewImage.style.height).toBe("400px");

    fullscreenElementRef = null;
    document.dispatchEvent(new Event("fullscreenchange"));
    expect(fullscreenZoom.hidden).toBe(true);
    expect(fullscreenSlider.value).toBe("100");
    expect(previewImage.style.width).toBe("400px");
    expect(previewImage.style.height).toBe("200px");
  });
});
