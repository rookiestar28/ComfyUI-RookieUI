import { describe, expect, test } from "vitest";

import {
  createControlNetPreviewStage,
  setControlNetGeneratedPreview,
  setControlNetPreview,
} from "../sidebar_tabs/controlnet/rookieui_controlnet_preview_surface.js";
import {
  RUN_PREPROCESSOR_BUSY_ICON,
  RUN_PREPROCESSOR_ICON,
  syncRunPreprocessorVisibility,
} from "../sidebar_tabs/controlnet/rookieui_controlnet_preprocessor_surface.js";

function createInput(type, id, value = "", options = {}) {
  const input = document.createElement("input");
  input.type = type;
  input.id = id;
  input.value = String(value ?? "");
  if (options.className) {
    input.className = options.className;
  }
  return input;
}

function appendTextElement(parent, tagName, className, textContent) {
  const node = document.createElement(tagName);
  node.className = className;
  node.textContent = textContent;
  parent.appendChild(node);
  return node;
}

function buildPreviewState() {
  return createControlNetPreviewStage({
    idPrefix: "rookieui-test-controlnet",
    index: 0,
    appendTextElement,
    createInput,
  });
}

describe("ControlNet preview surface helpers", () => {
  test("builds the preview stage with source and generated lanes", () => {
    const preview = buildPreviewState();

    expect(preview.stage.id).toBe("rookieui-test-controlnet-preview-stage-0");
    expect(preview.uploadButton.dataset.canvasAction).toBe("upload");
    expect(preview.removeButton.dataset.canvasAction).toBe("remove");
    expect(preview.undoButton.disabled).toBe(false);
    expect(preview.dualPane.dataset.generatedVisible).toBe("false");
    expect(preview.generatedLane.hidden).toBe(true);
    expect(preview.placeholderText.textContent).toBe("Upload control image");
  });

  test("syncs source preview state from image data and asset handles", () => {
    const preview = buildPreviewState();

    setControlNetPreview(preview, { imageAsset: "control-source.png" });
    expect(preview.stage.dataset.hasSource).toBe("true");
    expect(preview.stage.dataset.interactionMode).toBe("edit");
    expect(preview.previewImage.hidden).toBe(true);
    expect(preview.placeholder.hidden).toBe(false);
    expect(preview.placeholderText.textContent).toBe("Asset: control-source.png");
    expect(preview.removeButton.disabled).toBe(false);

    setControlNetPreview(preview, { imageData: "data:image/png;base64,aW1hZ2U=" });
    expect(preview.previewImage.hidden).toBe(false);
    expect(preview.previewImage.src).toContain("data:image/png;base64,aW1hZ2U=");
    expect(preview.placeholder.hidden).toBe(true);
  });

  test("keeps generated preview hidden until visibility and image data are both present", () => {
    const preview = buildPreviewState();

    setControlNetGeneratedPreview(preview, { imageData: "data:image/png;base64,cHJldmlldw==", visible: false });
    expect(preview.dualPane.dataset.generatedVisible).toBe("false");
    expect(preview.generatedLane.hidden).toBe(true);

    setControlNetGeneratedPreview(preview, { imageData: "data:image/png;base64,cHJldmlldw==", visible: true });
    expect(preview.dualPane.dataset.generatedVisible).toBe("true");
    expect(preview.generatedLane.hidden).toBe(false);
    expect(preview.generatedImage.hidden).toBe(false);
  });
});

describe("ControlNet preprocessor surface helpers", () => {
  test("syncs run-preprocessor visibility and busy state", () => {
    const button = document.createElement("button");
    const icon = document.createElement("span");
    icon.className = "rookieui-shell__mini-action-icon";
    button.appendChild(icon);
    const row = {
      imageData: createInput("hidden", "image-data", ""),
      runPreprocessorButton: button,
      preprocessorBusy: false,
    };

    syncRunPreprocessorVisibility(row, true);
    expect(button.hidden).toBe(true);
    expect(button.disabled).toBe(true);
    expect(button.dataset.running).toBe("false");
    expect(icon.textContent).toBe(RUN_PREPROCESSOR_ICON);

    row.imageData.value = "data:image/png;base64,aW1hZ2U=";
    syncRunPreprocessorVisibility(row, true);
    expect(button.hidden).toBe(false);
    expect(button.disabled).toBe(false);
    expect(button.title).toBe("Run Preprocessor");

    row.preprocessorBusy = true;
    syncRunPreprocessorVisibility(row, true);
    expect(button.hidden).toBe(false);
    expect(button.disabled).toBe(true);
    expect(button.dataset.running).toBe("true");
    expect(button.getAttribute("aria-busy")).toBe("true");
    expect(icon.textContent).toBe(RUN_PREPROCESSOR_BUSY_ICON);
  });
});
