import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { createImg2ImgMaskCanvasEditor } from "../sidebar_tabs/rookieui_img2img_mask_editor.js";

function createInput(value = "") {
  const input = document.createElement("input");
  input.value = value;
  return input;
}

function getSliderControl(rootId, labelText) {
  const controls = Array.from(document.querySelectorAll(`#${rootId} .rookieui-shell__mask-editor-control`));
  const row = controls.find((entry) => {
    const label = entry.querySelector(".rookieui-shell__field-label");
    return label?.textContent === labelText;
  });
  if (!row) {
    throw new Error(`Unable to find slider control row for label: ${labelText}`);
  }
  return {
    valueInput: row.querySelector('input[type="number"]'),
    slider: row.querySelector('input[type="range"]'),
  };
}

function computeSliderProgressPercent(slider) {
  const min = Number(slider.min || 0);
  const max = Number(slider.max || 100);
  const value = Number(slider.value || min);
  const ratio = max > min ? ((value - min) / (max - min)) * 100 : 0;
  return `${Math.min(100, Math.max(0, ratio))}%`;
}

describe("createImg2ImgMaskCanvasEditor", () => {
  let originalImage;
  let originalGetContext;
  let originalToDataUrl;

  beforeEach(() => {
    document.body.innerHTML = "";
    originalImage = global.Image;
    originalGetContext = HTMLCanvasElement.prototype.getContext;
    originalToDataUrl = HTMLCanvasElement.prototype.toDataURL;

    global.Image = class MockImage {
      constructor() {
        this.naturalWidth = 256;
        this.naturalHeight = 256;
      }

      set src(value) {
        this._src = value;
        queueMicrotask(() => {
          this.onload?.();
        });
      }

      get src() {
        return this._src;
      }
    };

    HTMLCanvasElement.prototype.getContext = function mockGetContext() {
      const width = this.width || 1;
      const height = this.height || 1;
      const data = new Uint8ClampedArray(width * height * 4);
      return {
        save: vi.fn(),
        restore: vi.fn(),
        fillRect: vi.fn(),
        beginPath: vi.fn(),
        moveTo: vi.fn(),
        lineTo: vi.fn(),
        stroke: vi.fn(),
        drawImage: vi.fn(),
        getImageData: vi.fn(() => ({ data: new Uint8ClampedArray(data), width, height })),
        putImageData: vi.fn(),
      };
    };

    HTMLCanvasElement.prototype.toDataURL = vi.fn(() => "data:image/png;base64,mask");
  });

  test("stages and applies mask payload through the R49 contract bridge", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);
    const modeInput = createInput("inpaint");
    const imageDataInput = createInput("data:image/png;base64,source");
    const imageAssetInput = createInput("");
    const maskDataInput = createInput("");
    const maskAssetInput = createInput("");
    const stageMaskData = vi.fn(() => true);
    const applyStagedMask = vi.fn(() => ({ ok: true, message: "Applied staged mask to Img2Img request payload." }));

    const editor = createImg2ImgMaskCanvasEditor({
      idPrefix: "mask-editor-test",
      parent,
      modeInput,
      imageDataInput,
      imageAssetInput,
      maskDataInput,
      maskAssetInput,
      resolveExecutionMode: () => "inpaint",
      maskCanvasContract: {
        stageMaskData,
        applyStagedMask,
      },
      syncBoundControls: vi.fn(),
      allowJsdomCanvas: true,
    });

    await editor.refreshFromInputs();
    editor.forceStageCurrentMask();
    document.getElementById("mask-editor-test-apply").click();

    expect(stageMaskData).toHaveBeenCalled();
    expect(applyStagedMask).toHaveBeenCalledTimes(1);
  });

  test("hides editor in batch execution mode", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);
    const editor = createImg2ImgMaskCanvasEditor({
      idPrefix: "mask-editor-batch",
      parent,
      modeInput: createInput("img2img"),
      imageDataInput: createInput("data:image/png;base64,source"),
      imageAssetInput: createInput(""),
      maskDataInput: createInput(""),
      maskAssetInput: createInput(""),
      resolveExecutionMode: (mode) => mode,
      maskCanvasContract: {
        stageMaskData: vi.fn(() => true),
        applyStagedMask: vi.fn(() => ({ ok: true })),
      },
      allowJsdomCanvas: true,
    });

    editor.setMode("batch");
    expect(document.getElementById("mask-editor-batch").hidden).toBe(true);
  });

  test("toggles source placeholder visibility with source binding state", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);
    const imageDataInput = createInput("data:image/png;base64,source");
    const imageAssetInput = createInput("");
    const editor = createImg2ImgMaskCanvasEditor({
      idPrefix: "mask-editor-source-placeholder",
      parent,
      modeInput: createInput("img2img"),
      imageDataInput,
      imageAssetInput,
      maskDataInput: createInput(""),
      maskAssetInput: createInput(""),
      resolveExecutionMode: (mode) => mode,
      maskCanvasContract: {
        stageMaskData: vi.fn(() => true),
        applyStagedMask: vi.fn(() => ({ ok: true })),
      },
      allowJsdomCanvas: true,
    });

    await editor.refreshFromInputs();
    const placeholder = document.querySelector(
      "#mask-editor-source-placeholder .rookieui-shell__mask-editor-placeholder",
    );
    expect(placeholder).not.toBeNull();
    expect(placeholder.hidden).toBe(true);

    imageDataInput.value = "";
    imageAssetInput.value = "";
    await editor.refreshFromInputs();
    expect(placeholder.hidden).toBe(false);
  });

  test("clear and invert buttons stage mask updates", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);
    const stageMaskData = vi.fn(() => true);
    const editor = createImg2ImgMaskCanvasEditor({
      idPrefix: "mask-editor-actions",
      parent,
      modeInput: createInput("inpaint"),
      imageDataInput: createInput("data:image/png;base64,source"),
      imageAssetInput: createInput(""),
      maskDataInput: createInput(""),
      maskAssetInput: createInput(""),
      resolveExecutionMode: () => "inpaint",
      maskCanvasContract: {
        stageMaskData,
        applyStagedMask: vi.fn(() => ({ ok: true })),
      },
      allowJsdomCanvas: true,
    });

    await editor.refreshFromInputs();
    document.getElementById("mask-editor-actions-clear").click();
    document.getElementById("mask-editor-actions-invert").click();

    expect(stageMaskData).toHaveBeenCalledTimes(2);
    expect(document.getElementById("mask-editor-actions-undo").disabled).toBe(false);
  });

  test("advanced selection actions stage updates and support transform nudge", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);
    const stageMaskData = vi.fn(() => true);
    const editor = createImg2ImgMaskCanvasEditor({
      idPrefix: "mask-editor-advanced",
      parent,
      modeInput: createInput("inpaint"),
      imageDataInput: createInput("data:image/png;base64,source"),
      imageAssetInput: createInput(""),
      maskDataInput: createInput(""),
      maskAssetInput: createInput(""),
      resolveExecutionMode: () => "inpaint",
      maskCanvasContract: {
        stageMaskData,
        applyStagedMask: vi.fn(() => ({ ok: true })),
      },
      allowJsdomCanvas: true,
    });

    await editor.refreshFromInputs();
    editor.setSelectionRect({ x: 12, y: 10, width: 48, height: 36 });
    document.getElementById("mask-editor-advanced-fill-selection").click();
    document.getElementById("mask-editor-advanced-nudge-right").click();
    expect(stageMaskData).toHaveBeenCalledTimes(2);
    document.getElementById("mask-editor-advanced-clear-selection").click();
    const selectionOverlay = document.querySelector("#mask-editor-advanced .rookieui-shell__mask-editor-selection");
    expect(selectionOverlay.hidden).toBe(true);
  });

  test("keeps Opacity and Zoom slider position synchronized with numeric defaults at mount", () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);
    createImg2ImgMaskCanvasEditor({
      idPrefix: "mask-editor-slider-defaults",
      parent,
      modeInput: createInput("img2img"),
      imageDataInput: createInput(""),
      imageAssetInput: createInput(""),
      maskDataInput: createInput(""),
      maskAssetInput: createInput(""),
      resolveExecutionMode: (mode) => mode,
      maskCanvasContract: {
        stageMaskData: vi.fn(() => true),
        applyStagedMask: vi.fn(() => ({ ok: true })),
      },
      allowJsdomCanvas: true,
    });

    const opacity = getSliderControl("mask-editor-slider-defaults", "Opacity");
    const zoom = getSliderControl("mask-editor-slider-defaults", "Zoom");

    expect(opacity.valueInput.value).toBe("1");
    expect(opacity.slider.value).toBe("1");
    expect(opacity.slider.style.getPropertyValue("--rookieui-slider-progress")).toBe("100%");

    expect(zoom.valueInput.value).toBe("1");
    expect(zoom.slider.value).toBe("1");
    expect(zoom.slider.style.getPropertyValue("--rookieui-slider-progress")).toBe(computeSliderProgressPercent(zoom.slider));
  });

  test("updates Zoom slider progress after fit-to-viewport recalculation", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);
    const editor = createImg2ImgMaskCanvasEditor({
      idPrefix: "mask-editor-slider-fit",
      parent,
      modeInput: createInput("img2img"),
      imageDataInput: createInput("data:image/png;base64,source"),
      imageAssetInput: createInput(""),
      maskDataInput: createInput(""),
      maskAssetInput: createInput(""),
      resolveExecutionMode: (mode) => mode,
      maskCanvasContract: {
        stageMaskData: vi.fn(() => true),
        applyStagedMask: vi.fn(() => ({ ok: true })),
      },
      allowJsdomCanvas: true,
    });

    await editor.refreshFromInputs();
    const zoom = getSliderControl("mask-editor-slider-fit", "Zoom");
    expect(zoom.slider.style.getPropertyValue("--rookieui-slider-progress")).toBe(computeSliderProgressPercent(zoom.slider));
  });

  afterEach(() => {
    global.Image = originalImage;
    HTMLCanvasElement.prototype.getContext = originalGetContext;
    HTMLCanvasElement.prototype.toDataURL = originalToDataUrl;
  });
});
