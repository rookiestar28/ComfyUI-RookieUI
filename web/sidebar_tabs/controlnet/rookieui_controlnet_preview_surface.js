import {
  CANVAS_ACTIONS,
  hasCanvasSourceImage,
  resolveCanvasInteractionMode,
} from "../rookieui_canvas_surface_contract.js";

export const PREVIEW_UPLOAD_ICON = "⤴";
export const FULLSCREEN_ENTER_ICON = "⛶";
export const FULLSCREEN_EXIT_ICON = "🗗";

function createControlNetPreviewActionButton({ toolbar, idPrefix, index, action, icon, label }) {
  const button = document.createElement("button");
  button.type = "button";
  button.id = `${idPrefix}-preview-${action}-action-${index}`;
  button.className = "rookieui-shell__mini-action rookieui-shell__mini-action--icon rookieui-shell__mini-action--tone-neutral";
  button.dataset.canvasAction = action;
  button.title = label;
  button.setAttribute("aria-label", label);
  const iconNode = document.createElement("span");
  iconNode.className = "rookieui-shell__mini-action-icon";
  iconNode.textContent = icon;
  button.appendChild(iconNode);
  toolbar.appendChild(button);
  return button;
}

export function createControlNetPreviewStage({ idPrefix, index, appendTextElement, createInput }) {
  const stage = document.createElement("div");
  stage.className = "rookieui-shell__controlnet-preview-stage";
  stage.id = `${idPrefix}-preview-stage-${index}`;

  const toolbar = document.createElement("div");
  toolbar.className = "rookieui-shell__controlnet-preview-toolbar";
  stage.appendChild(toolbar);

  const fullscreenButton = createControlNetPreviewActionButton({
    toolbar,
    idPrefix,
    index,
    action: CANVAS_ACTIONS.fullscreen,
    icon: FULLSCREEN_ENTER_ICON,
    label: "Fullscreen preview",
  });
  const uploadButton = createControlNetPreviewActionButton({
    toolbar,
    idPrefix,
    index,
    action: CANVAS_ACTIONS.upload,
    icon: "📁",
    label: "Upload control image",
  });
  const removeButton = createControlNetPreviewActionButton({
    toolbar,
    idPrefix,
    index,
    action: CANVAS_ACTIONS.remove,
    icon: "🗑",
    label: "Remove control image",
  });
  const resetButton = createControlNetPreviewActionButton({
    toolbar,
    idPrefix,
    index,
    action: CANVAS_ACTIONS.reset,
    icon: "↺",
    label: "Reset control image view",
  });
  const undoButton = createControlNetPreviewActionButton({
    toolbar,
    idPrefix,
    index,
    action: CANVAS_ACTIONS.undo,
    icon: "↶",
    label: "Undo control image change",
  });
  const redoButton = createControlNetPreviewActionButton({
    toolbar,
    idPrefix,
    index,
    action: CANVAS_ACTIONS.redo,
    icon: "↷",
    label: "Redo control image change",
  });

  const previewImage = document.createElement("img");
  previewImage.className = "rookieui-shell__controlnet-preview-image";
  previewImage.id = `${idPrefix}-preview-image-${index}`;
  previewImage.alt = `ControlNet source preview ${index + 1}`;
  previewImage.hidden = true;
  stage.appendChild(previewImage);

  const placeholder = document.createElement("div");
  placeholder.className = "rookieui-shell__controlnet-preview-placeholder";
  const icon = document.createElement("span");
  icon.className = "rookieui-shell__controlnet-preview-placeholder-icon";
  icon.textContent = PREVIEW_UPLOAD_ICON;
  placeholder.appendChild(icon);
  const text = appendTextElement(
    placeholder,
    "span",
    "rookieui-shell__controlnet-preview-placeholder-text",
    "Upload control image",
  );
  stage.appendChild(placeholder);

  const sourceUploadInput = createInput("file", `${idPrefix}-preview-image-upload-${index}`, "", {
    className: "rookieui-shell__input",
  });
  sourceUploadInput.accept = "image/png,image/webp,image/jpeg";
  sourceUploadInput.hidden = true;
  sourceUploadInput.setAttribute("tabindex", "-1");
  sourceUploadInput.setAttribute("aria-hidden", "true");
  stage.appendChild(sourceUploadInput);

  const generatedLane = document.createElement("div");
  generatedLane.className = "rookieui-shell__controlnet-generated-preview";
  generatedLane.id = `${idPrefix}-preview-generated-lane-${index}`;
  generatedLane.hidden = true;

  const generatedImage = document.createElement("img");
  generatedImage.className = "rookieui-shell__controlnet-generated-preview-image";
  generatedImage.id = `${idPrefix}-preview-generated-image-${index}`;
  generatedImage.alt = `ControlNet generated preview ${index + 1}`;
  generatedImage.hidden = true;
  generatedLane.appendChild(generatedImage);

  const generatedPlaceholder = document.createElement("div");
  generatedPlaceholder.className = "rookieui-shell__controlnet-generated-preview-placeholder";
  appendTextElement(
    generatedPlaceholder,
    "span",
    "rookieui-shell__controlnet-generated-preview-placeholder-text",
    "Run Preprocessor output preview",
  );
  generatedLane.appendChild(generatedPlaceholder);

  const dualPane = document.createElement("div");
  dualPane.className = "rookieui-shell__controlnet-preview-dual-pane";
  dualPane.id = `${idPrefix}-preview-dual-pane-${index}`;
  dualPane.dataset.generatedVisible = "false";
  dualPane.appendChild(stage);
  dualPane.appendChild(generatedLane);

  return {
    unitIndex: index,
    dualPane,
    stage,
    generatedLane,
    generatedImage,
    generatedPlaceholder,
    toolbar,
    previewImage,
    placeholder,
    placeholderText: text,
    sourceUploadInput,
    fullscreenButton,
    uploadButton,
    removeButton,
    resetButton,
    undoButton,
    redoButton,
    history: {
      undo: [],
      redo: [],
      limit: 24,
    },
  };
}

export function setControlNetPreview(
  previewState,
  { imageData = "", imageAsset = "", fallbackText = "Upload control image" } = {},
) {
  const normalizedImage = String(imageData ?? "").trim();
  const normalizedAsset = String(imageAsset ?? "").trim();
  const hasSource = hasCanvasSourceImage(normalizedImage, normalizedAsset);
  const interactionMode = resolveCanvasInteractionMode(normalizedImage, normalizedAsset);
  const unitLabel = `ControlNet Unit ${(previewState.unitIndex ?? 0) + 1}`;
  previewState.stage.dataset.hasSource = hasSource ? "true" : "false";
  previewState.stage.dataset.interactionMode = interactionMode;
  previewState.stage.setAttribute(
    "aria-label",
    interactionMode === "upload" ? `${unitLabel} upload source image` : `${unitLabel} source image editing surface`,
  );
  if (normalizedImage.startsWith("data:image/")) {
    previewState.previewImage.src = normalizedImage;
    previewState.previewImage.hidden = false;
    previewState.placeholder.hidden = true;
  } else {
    previewState.previewImage.hidden = true;
    previewState.previewImage.removeAttribute("src");
    previewState.placeholder.hidden = false;
    if (normalizedAsset) {
      // IMPORTANT: asset handles are server-side identifiers; keep text fallback instead of forcing /view fetches that may fail on non-image handles.
      previewState.placeholderText.textContent = `Asset: ${normalizedAsset}`;
    } else {
      previewState.placeholderText.textContent = fallbackText;
    }
  }

  previewState.removeButton.disabled = !hasSource;
  previewState.resetButton.disabled = !hasSource;
  previewState.undoButton.disabled = previewState.history.undo.length === 0;
  previewState.redoButton.disabled = previewState.history.redo.length === 0;
}

export function setControlNetGeneratedPreview(previewState, { imageData = "", visible = false } = {}) {
  const normalizedImage = String(imageData ?? "").trim();
  const hasGeneratedImage = normalizedImage.startsWith("data:image/");
  const shouldShow = Boolean(visible) && hasGeneratedImage;
  if (previewState.dualPane) {
    previewState.dualPane.dataset.generatedVisible = shouldShow ? "true" : "false";
  }
  previewState.generatedLane.hidden = !shouldShow;
  if (shouldShow) {
    previewState.generatedImage.src = normalizedImage;
    previewState.generatedImage.hidden = false;
    previewState.generatedPlaceholder.hidden = true;
    return;
  }
  previewState.generatedImage.hidden = true;
  previewState.generatedImage.removeAttribute("src");
  previewState.generatedPlaceholder.hidden = false;
}
