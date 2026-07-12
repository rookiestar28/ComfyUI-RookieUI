import {
  isCanvasElementFullscreen,
  toggleCanvasFullscreen,
} from "./sidebar_tabs/rookieui_canvas_surface_contract.js";

const ENTER_FULLSCREEN_ICON = "⛶";
const EXIT_FULLSCREEN_ICON = "🗗";

function syncSliderProgressVisual(slider) {
  if (!slider) {
    return;
  }
  const min = Number(slider.min || 0);
  const max = Number(slider.max || 100);
  const value = Number(slider.value || min);
  const ratio = max > min ? ((value - min) / (max - min)) * 100 : 0;
  slider.style.setProperty("--rookieui-slider-progress", `${Math.min(100, Math.max(0, ratio))}%`);
}

function clearFullscreenImageSizing(image) {
  if (!image) {
    return;
  }
  image.style.removeProperty("width");
  image.style.removeProperty("max-width");
  image.style.removeProperty("max-height");
}

function buildFullscreenZoomControls(surface, idPrefix) {
  const zoomPanel = document.createElement("div");
  zoomPanel.className = "rookieui-shell__canvas-fullscreen-zoom rookieui-shell__preview-fullscreen-zoom";
  zoomPanel.hidden = true;
  surface.appendChild(zoomPanel);

  const zoomLabel = document.createElement("span");
  zoomLabel.className = "rookieui-shell__canvas-fullscreen-zoom-label";
  zoomPanel.appendChild(zoomLabel);

  const zoomSlider = document.createElement("input");
  zoomSlider.type = "range";
  zoomSlider.className = "rookieui-shell__slider";
  zoomSlider.id = `${idPrefix}-fullscreen-zoom`;
  zoomSlider.min = "0.25";
  zoomSlider.max = "4";
  zoomSlider.step = "0.05";
  zoomSlider.value = "1";
  syncSliderProgressVisual(zoomSlider);
  zoomPanel.appendChild(zoomSlider);

  return { zoomPanel, zoomLabel, zoomSlider };
}

export function createPreviewFullscreenViewer(
  {
    idPrefix,
    previewBox,
    previewToolbar,
    createIconActionButton,
    statusNode = null,
    labelText = "Preview",
  } = {},
  deps = {
    isCanvasElementFullscreen,
    toggleCanvasFullscreen,
  },
) {
  if (!previewBox || !previewToolbar || typeof createIconActionButton !== "function") {
    throw new Error("Preview fullscreen viewer requires a preview box, toolbar, and icon button factory.");
  }

  const surface = document.createElement("div");
  surface.className = "rookieui-shell__preview-surface";
  previewBox.parentNode?.insertBefore(surface, previewBox);
  surface.appendChild(previewBox);

  const overlayToolbar = document.createElement("div");
  overlayToolbar.className = "rookieui-shell__preview-overlay-toolbar";
  surface.appendChild(overlayToolbar);

  const { zoomPanel, zoomLabel, zoomSlider } = buildFullscreenZoomControls(surface, idPrefix);
  let zoomValue = 1;
  let boundImage = null;

  const fullscreenButton = createIconActionButton(
    `${idPrefix}-preview-fullscreen`,
    ENTER_FULLSCREEN_ICON,
    `Fullscreen ${labelText.toLowerCase()}`,
    "neutral",
  );
  // IMPORTANT: keep the fullscreen affordance inside the preview surface; a toolbar-only button is too easy to miss and does not match the inpaint/source canvas interaction model.
  overlayToolbar.appendChild(fullscreenButton);

  const syncZoomLabel = () => {
    zoomLabel.textContent = `Zoom ${Math.round(zoomValue * 100)}%`;
  };

  const applyZoom = () => {
    const image = previewBox.querySelector(".rookieui-shell__preview-image");
    const fullscreenActive = deps.isCanvasElementFullscreen(surface);
    if (!image || !fullscreenActive) {
      clearFullscreenImageSizing(image);
      return;
    }
    const naturalWidth = Number(image.naturalWidth || 0);
    if (!naturalWidth) {
      return;
    }
    image.style.maxWidth = "none";
    image.style.maxHeight = "none";
    image.style.width = `${Math.max(1, naturalWidth * zoomValue)}px`;
  };

  const syncFullscreenUi = () => {
    const image = previewBox.querySelector(".rookieui-shell__preview-image");
    const hasImage = Boolean(image);
    const fullscreenActive = deps.isCanvasElementFullscreen(surface);
    surface.dataset.fullscreen = fullscreenActive ? "true" : "false";
    surface.dataset.hasImage = hasImage ? "true" : "false";
    fullscreenButton.disabled = !hasImage;
    zoomPanel.hidden = !fullscreenActive || !hasImage;
    const iconNode = fullscreenButton.querySelector(".rookieui-shell__mini-action-icon");
    if (iconNode) {
      iconNode.textContent = fullscreenActive ? EXIT_FULLSCREEN_ICON : ENTER_FULLSCREEN_ICON;
    }
    const buttonLabel = fullscreenActive ? `Exit fullscreen ${labelText.toLowerCase()}` : `Fullscreen ${labelText.toLowerCase()}`;
    fullscreenButton.title = buttonLabel;
    fullscreenButton.setAttribute("aria-label", buttonLabel);
    applyZoom();
  };

  const syncImage = () => {
    const image = previewBox.querySelector(".rookieui-shell__preview-image");
    if (boundImage && boundImage !== image) {
      boundImage.removeEventListener("load", applyZoom);
      boundImage = null;
    }
    if (image && boundImage !== image) {
      image.addEventListener("load", applyZoom);
      boundImage = image;
    }
    syncFullscreenUi();
  };

  zoomSlider.addEventListener("input", () => {
    zoomValue = Number(zoomSlider.value || "1");
    syncSliderProgressVisual(zoomSlider);
    syncZoomLabel();
    applyZoom();
  });

  fullscreenButton.addEventListener("click", async () => {
    const fullscreenAction = await deps.toggleCanvasFullscreen(surface);
    syncFullscreenUi();
    if (!statusNode) {
      return;
    }
    statusNode.textContent =
      fullscreenAction === "entered"
        ? `${labelText} entered fullscreen mode.`
        : fullscreenAction === "exited"
          ? `${labelText} exited fullscreen mode.`
          : fullscreenAction === "unavailable"
            ? "Fullscreen preview is unavailable in this browser."
            : statusNode.textContent;
  });

  surface.addEventListener("click", async (event) => {
    if (!previewBox.querySelector(".rookieui-shell__preview-image")) {
      return;
    }
    const target = event.target;
    if (target instanceof Element && target.closest("button, input, select, textarea, a")) {
      return;
    }
    // IMPORTANT: generated preview itself must be clickable for fullscreen; users should not have to hunt for a secondary toolbar button.
    const fullscreenAction = await deps.toggleCanvasFullscreen(surface);
    syncFullscreenUi();
    if (!statusNode) {
      return;
    }
    statusNode.textContent =
      fullscreenAction === "entered"
        ? `${labelText} entered fullscreen mode.`
        : fullscreenAction === "exited"
          ? `${labelText} exited fullscreen mode.`
          : fullscreenAction === "unavailable"
            ? "Fullscreen preview is unavailable in this browser."
            : statusNode.textContent;
  });

  if (globalThis.document?.addEventListener) {
    globalThis.document.addEventListener("fullscreenchange", syncFullscreenUi);
    globalThis.document.addEventListener("webkitfullscreenchange", syncFullscreenUi);
  }

  previewBox.__previewFullscreenController = { syncImage };
  syncZoomLabel();
  syncImage();

  return {
    surface,
    fullscreenButton,
    zoomSlider,
    syncImage,
    destroy() {
      if (boundImage) {
        boundImage.removeEventListener("load", applyZoom);
        boundImage = null;
      }
      globalThis.document?.removeEventListener?.("fullscreenchange", syncFullscreenUi);
      globalThis.document?.removeEventListener?.("webkitfullscreenchange", syncFullscreenUi);
      if (previewBox.__previewFullscreenController?.syncImage === syncImage) {
        delete previewBox.__previewFullscreenController;
      }
    },
  };
}
