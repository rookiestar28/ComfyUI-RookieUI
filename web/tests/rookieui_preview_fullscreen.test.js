import { beforeEach, describe, expect, test } from "vitest";

import { createIconActionButton } from "../rookieui_action_buttons.js";
import { createPreviewFullscreenViewer } from "../rookieui_preview_fullscreen.js";

describe("preview fullscreen viewer", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

test("toggles fullscreen zoom controls and applies zoom to the preview image", async () => {
    const section = document.createElement("section");
    const previewBox = document.createElement("div");
    previewBox.className = "rookieui-shell__preview-box";
    section.appendChild(previewBox);
    const toolbar = document.createElement("div");
    section.appendChild(toolbar);
    const statusNode = document.createElement("p");
    section.appendChild(statusNode);
    document.body.appendChild(section);

    let fullscreenActive = false;
    const viewer = createPreviewFullscreenViewer(
      {
        idPrefix: "test-preview",
        previewBox,
        previewToolbar: toolbar,
        createIconActionButton,
        statusNode,
        labelText: "Preview",
      },
      {
        isCanvasElementFullscreen: () => fullscreenActive,
        toggleCanvasFullscreen: async () => {
          fullscreenActive = !fullscreenActive;
          return fullscreenActive ? "entered" : "exited";
        },
      },
    );

    const image = document.createElement("img");
    image.className = "rookieui-shell__preview-image";
    Object.defineProperty(image, "naturalWidth", { configurable: true, value: 800 });
    previewBox.appendChild(image);
    viewer.syncImage();

    expect(viewer.fullscreenButton.disabled).toBe(false);
    expect(viewer.zoomSlider.parentElement.hidden).toBe(true);

    viewer.fullscreenButton.click();
    await Promise.resolve();

    expect(viewer.zoomSlider.parentElement.hidden).toBe(false);
    expect(statusNode.textContent).toContain("entered fullscreen mode");
    expect(image.style.width).toBe("800px");

    viewer.zoomSlider.value = "2";
    viewer.zoomSlider.dispatchEvent(new Event("input", { bubbles: true }));
    expect(image.style.width).toBe("1600px");

    viewer.fullscreenButton.click();
    await Promise.resolve();

    expect(viewer.zoomSlider.parentElement.hidden).toBe(true);
    expect(statusNode.textContent).toContain("exited fullscreen mode");
  });

  test("lets the preview surface itself toggle fullscreen when an image is present", async () => {
    const section = document.createElement("section");
    const previewBox = document.createElement("div");
    previewBox.className = "rookieui-shell__preview-box";
    section.appendChild(previewBox);
    const toolbar = document.createElement("div");
    section.appendChild(toolbar);
    const statusNode = document.createElement("p");
    section.appendChild(statusNode);
    document.body.appendChild(section);

    let fullscreenActive = false;
    let toggleCount = 0;
    const viewer = createPreviewFullscreenViewer(
      {
        idPrefix: "test-preview-surface-click",
        previewBox,
        previewToolbar: toolbar,
        createIconActionButton,
        statusNode,
        labelText: "Preview",
      },
      {
        isCanvasElementFullscreen: () => fullscreenActive,
        toggleCanvasFullscreen: async () => {
          toggleCount += 1;
          fullscreenActive = !fullscreenActive;
          return fullscreenActive ? "entered" : "exited";
        },
      },
    );

    const image = document.createElement("img");
    image.className = "rookieui-shell__preview-image";
    previewBox.appendChild(image);
    viewer.syncImage();

    viewer.surface.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await Promise.resolve();

    expect(toggleCount).toBe(1);
    expect(statusNode.textContent).toContain("entered fullscreen mode");
  });
});
