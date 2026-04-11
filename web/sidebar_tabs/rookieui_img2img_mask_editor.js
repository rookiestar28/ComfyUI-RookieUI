function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function normalizeSelectionRect(startX, startY, endX, endY, canvasWidth, canvasHeight) {
  const left = clamp(Math.min(startX, endX), 0, canvasWidth);
  const top = clamp(Math.min(startY, endY), 0, canvasHeight);
  const right = clamp(Math.max(startX, endX), 0, canvasWidth);
  const bottom = clamp(Math.max(startY, endY), 0, canvasHeight);
  return {
    x: Math.floor(left),
    y: Math.floor(top),
    width: Math.max(0, Math.floor(right - left)),
    height: Math.max(0, Math.floor(bottom - top)),
  };
}

function createEditorButton(id, text, title, options = {}) {
  const button = document.createElement("button");
  button.type = "button";
  button.id = id;
  button.className = "rookieui-shell__mini-action rookieui-shell__mini-action--tone-neutral";
  if (options.compact) {
    button.classList.add("rookieui-shell__mini-action--compact");
  }
  button.textContent = text;
  button.title = title;
  button.setAttribute("aria-label", title);
  return button;
}

function readTrimmedValue(input) {
  return String(input?.value ?? "").trim();
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = src;
  });
}

function resolveAssetPreviewUrl(assetValue) {
  const raw = String(assetValue ?? "").trim();
  if (!raw) {
    return "";
  }
  if (/^(data:|blob:|https?:|\/)/i.test(raw)) {
    return raw;
  }
  return `/view?filename=${encodeURIComponent(raw)}&subfolder=&type=output`;
}

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

export function createImg2ImgMaskCanvasEditor({
  idPrefix = "rookieui-img2img-mask-editor",
  parent,
  modeInput,
  imageDataInput,
  imageAssetInput,
  maskDataInput,
  maskAssetInput,
  maskCanvasContract,
  resolveExecutionMode,
  onStatusMessage,
  syncBoundControls,
  allowJsdomCanvas = false,
} = {}) {
  if (!parent) {
    throw new Error("Img2Img mask canvas editor requires a parent node.");
  }

  const root = document.createElement("section");
  root.className = "rookieui-shell__section rookieui-shell__section--soft rookieui-shell__mask-editor";
  root.id = idPrefix;
  parent.appendChild(root);
  const titleNode = document.createElement("h4");
  titleNode.className = "rookieui-shell__section-title";
  titleNode.textContent = "Mask Canvas";
  root.appendChild(titleNode);

  const statusNode = document.createElement("p");
  statusNode.className = "rookieui-shell__status";
  statusNode.id = `${idPrefix}-status`;
  statusNode.textContent = "Load a source image to start drawing mask.";
  root.appendChild(statusNode);

  const toolbar = document.createElement("div");
  toolbar.className = "rookieui-shell__mask-editor-toolbar";
  root.appendChild(toolbar);

  const brushButton = createEditorButton(`${idPrefix}-tool-brush`, "🖌️", "Brush tool");
  const eraserButton = createEditorButton(`${idPrefix}-tool-eraser`, "🧽", "Eraser tool");
  const selectButton = createEditorButton(`${idPrefix}-tool-select`, "⬚", "Rectangle selection tool");
  const panButton = createEditorButton(`${idPrefix}-tool-pan`, "✋", "Pan tool");
  toolbar.appendChild(brushButton);
  toolbar.appendChild(eraserButton);
  toolbar.appendChild(selectButton);
  toolbar.appendChild(panButton);

  const controls = document.createElement("div");
  controls.className = "rookieui-shell__mask-editor-controls";
  root.appendChild(controls);

  const createSliderControl = (name, value, min, max, step) => {
    const row = document.createElement("label");
    row.className = "rookieui-shell__mask-editor-control";
    const label = document.createElement("span");
    label.className = "rookieui-shell__field-label";
    label.textContent = name;
    row.appendChild(label);
    const valueInput = document.createElement("input");
    valueInput.type = "number";
    valueInput.className = "rookieui-shell__input";
    valueInput.value = String(value);
    valueInput.min = String(min);
    valueInput.max = String(max);
    valueInput.step = String(step);
    row.appendChild(valueInput);
    const slider = document.createElement("input");
    slider.type = "range";
    slider.className = "rookieui-shell__slider";
    slider.min = String(min);
    slider.max = String(max);
    slider.step = String(step);
    slider.value = String(value);
    syncSliderProgressVisual(slider);
    row.appendChild(slider);
    controls.appendChild(row);
    return { valueInput, slider };
  };

  const brushSizeControl = createSliderControl("Size", 36, 1, 256, 1);
  const brushOpacityControl = createSliderControl("Opacity", 1, 0.05, 1, 0.01);
  const zoomControl = createSliderControl("Zoom", 1, 0.25, 4, 0.05);

  const actionRow = document.createElement("div");
  actionRow.className = "rookieui-shell__mask-editor-actions";
  root.appendChild(actionRow);
  const undoButton = createEditorButton(`${idPrefix}-undo`, "↶", "Undo", { compact: true });
  const redoButton = createEditorButton(`${idPrefix}-redo`, "↷", "Redo", { compact: true });
  const clearButton = createEditorButton(`${idPrefix}-clear`, "Clear", "Clear mask", { compact: true });
  const invertButton = createEditorButton(`${idPrefix}-invert`, "Invert", "Invert mask", { compact: true });
  const fitButton = createEditorButton(`${idPrefix}-fit`, "Fit", "Fit canvas to viewport", { compact: true });
  const applyButton = createEditorButton(`${idPrefix}-apply`, "Apply Mask", "Apply mask to request payload");
  applyButton.classList.add("rookieui-shell__mini-action--tone-transfer");
  actionRow.appendChild(undoButton);
  actionRow.appendChild(redoButton);
  actionRow.appendChild(clearButton);
  actionRow.appendChild(invertButton);
  actionRow.appendChild(fitButton);
  actionRow.appendChild(applyButton);

  const advancedActionRow = document.createElement("div");
  advancedActionRow.className = "rookieui-shell__mask-editor-actions rookieui-shell__mask-editor-actions--advanced";
  root.appendChild(advancedActionRow);
  const fillSelectionButton = createEditorButton(`${idPrefix}-fill-selection`, "Fill Sel", "Fill selected area", {
    compact: true,
  });
  const eraseSelectionButton = createEditorButton(
    `${idPrefix}-erase-selection`,
    "Erase Sel",
    "Erase selected area",
    { compact: true },
  );
  const invertSelectionButton = createEditorButton(
    `${idPrefix}-invert-selection`,
    "Invert Sel",
    "Invert selected area",
    { compact: true },
  );
  const nudgeLeftButton = createEditorButton(`${idPrefix}-nudge-left`, "←", "Move selected area left", { compact: true });
  const nudgeRightButton = createEditorButton(`${idPrefix}-nudge-right`, "→", "Move selected area right", {
    compact: true,
  });
  const nudgeUpButton = createEditorButton(`${idPrefix}-nudge-up`, "↑", "Move selected area up", { compact: true });
  const nudgeDownButton = createEditorButton(`${idPrefix}-nudge-down`, "↓", "Move selected area down", { compact: true });
  const clearSelectionButton = createEditorButton(
    `${idPrefix}-clear-selection`,
    "Clear Sel",
    "Clear selection box",
    { compact: true },
  );
  advancedActionRow.appendChild(fillSelectionButton);
  advancedActionRow.appendChild(eraseSelectionButton);
  advancedActionRow.appendChild(invertSelectionButton);
  advancedActionRow.appendChild(nudgeLeftButton);
  advancedActionRow.appendChild(nudgeRightButton);
  advancedActionRow.appendChild(nudgeUpButton);
  advancedActionRow.appendChild(nudgeDownButton);
  advancedActionRow.appendChild(clearSelectionButton);

  const viewport = document.createElement("div");
  viewport.className = "rookieui-shell__mask-editor-viewport";
  root.appendChild(viewport);

  const stage = document.createElement("div");
  stage.className = "rookieui-shell__mask-editor-stage";
  viewport.appendChild(stage);

  const sourceImage = document.createElement("img");
  sourceImage.className = "rookieui-shell__mask-editor-source";
  sourceImage.alt = "Img2Img source preview for mask drawing";
  stage.appendChild(sourceImage);

  const canvas = document.createElement("canvas");
  canvas.className = "rookieui-shell__mask-editor-canvas";
  stage.appendChild(canvas);

  const selectionBox = document.createElement("div");
  selectionBox.className = "rookieui-shell__mask-editor-selection";
  selectionBox.hidden = true;
  stage.appendChild(selectionBox);

  const placeholder = document.createElement("span");
  placeholder.className = "rookieui-shell__mask-editor-placeholder";
  placeholder.textContent = "No source image";
  stage.appendChild(placeholder);

  let context = null;
  const isJsdomRuntime = typeof navigator !== "undefined" && /jsdom/i.test(String(navigator.userAgent ?? ""));
  if (!isJsdomRuntime || allowJsdomCanvas) {
    try {
      context = canvas.getContext("2d", { willReadFrequently: true });
    } catch (_error) {
      // IMPORTANT: keep non-fatal fallback when 2D canvas is unavailable (for example jsdom test runtime).
      context = null;
    }
  }
  if (!context) {
    statusNode.textContent = "Mask editor is unavailable in this browser runtime.";
  }

  const state = {
    tool: "brush",
    pointerDown: false,
    panning: false,
    panPointerX: 0,
    panPointerY: 0,
    lastDrawX: 0,
    lastDrawY: 0,
    zoom: 1,
    panX: 0,
    panY: 0,
    sourceWidth: 512,
    sourceHeight: 512,
    sourceSignature: "",
    undoStack: [],
    redoStack: [],
    historyLimit: 24,
    pendingApply: false,
    loadingToken: 0,
    selection: null,
    selectionAnchor: null,
  };

  const updateToolButtons = () => {
    [brushButton, eraserButton, selectButton, panButton].forEach((button) => {
      button.classList.remove("is-active");
    });
    if (state.tool === "brush") {
      brushButton.classList.add("is-active");
    } else if (state.tool === "eraser") {
      eraserButton.classList.add("is-active");
    } else if (state.tool === "select") {
      selectButton.classList.add("is-active");
    } else {
      panButton.classList.add("is-active");
    }
  };

  const updateUndoRedoState = () => {
    undoButton.disabled = state.undoStack.length === 0;
    redoButton.disabled = state.redoStack.length === 0;
  };

  const updateSelectionBox = () => {
    const selection = state.selection;
    if (!selection || selection.width <= 0 || selection.height <= 0) {
      selectionBox.hidden = true;
      return;
    }
    selectionBox.hidden = false;
    selectionBox.style.left = `${selection.x}px`;
    selectionBox.style.top = `${selection.y}px`;
    selectionBox.style.width = `${selection.width}px`;
    selectionBox.style.height = `${selection.height}px`;
  };

  const clearSelection = () => {
    state.selection = null;
    state.selectionAnchor = null;
    updateSelectionBox();
  };

  const setSelection = (rect) => {
    if (!rect || rect.width <= 0 || rect.height <= 0) {
      clearSelection();
      return;
    }
    const x = clamp(Math.floor(rect.x), 0, canvas.width);
    const y = clamp(Math.floor(rect.y), 0, canvas.height);
    const width = clamp(Math.floor(rect.width), 0, Math.max(canvas.width - x, 0));
    const height = clamp(Math.floor(rect.height), 0, Math.max(canvas.height - y, 0));
    if (width <= 0 || height <= 0) {
      clearSelection();
      return;
    }
    state.selection = {
      x,
      y,
      width,
      height,
    };
    updateSelectionBox();
  };

  const updateStatus = (message) => {
    if (message) {
      statusNode.textContent = message;
    } else if (state.pendingApply) {
      statusNode.textContent = "Mask changed. Click Apply Mask to commit to payload.";
    } else {
      statusNode.textContent = "Mask payload is synced.";
    }
    if (typeof onStatusMessage === "function") {
      onStatusMessage(statusNode.textContent);
    }
  };

  const fillMaskWithBlack = () => {
    if (!context) {
      return;
    }
    context.save();
    context.globalCompositeOperation = "source-over";
    context.fillStyle = "rgba(0, 0, 0, 1)";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.restore();
  };

  const resetMaskCanvas = (width, height) => {
    const normalizedWidth = Math.max(64, Math.round(width || 512));
    const normalizedHeight = Math.max(64, Math.round(height || 512));
    state.sourceWidth = normalizedWidth;
    state.sourceHeight = normalizedHeight;
    canvas.width = normalizedWidth;
    canvas.height = normalizedHeight;
    sourceImage.width = normalizedWidth;
    sourceImage.height = normalizedHeight;
    stage.style.width = `${normalizedWidth}px`;
    stage.style.height = `${normalizedHeight}px`;
    fillMaskWithBlack();
    state.undoStack = [];
    state.redoStack = [];
    clearSelection();
    updateUndoRedoState();
  };

  const updateTransform = () => {
    stage.style.transformOrigin = "top left";
    stage.style.transform = `translate(${state.panX}px, ${state.panY}px) scale(${state.zoom})`;
  };

  const fitToViewport = () => {
    const viewportWidth = viewport.clientWidth || 420;
    const viewportHeight = viewport.clientHeight || 320;
    const fitZoom = clamp(
      Math.min(viewportWidth / Math.max(state.sourceWidth, 1), viewportHeight / Math.max(state.sourceHeight, 1)),
      0.25,
      4,
    );
    state.zoom = fitZoom;
    state.panX = (viewportWidth - state.sourceWidth * fitZoom) / 2;
    state.panY = (viewportHeight - state.sourceHeight * fitZoom) / 2;
    zoomControl.valueInput.value = String(Number(fitZoom.toFixed(2)));
    zoomControl.slider.value = String(Number(fitZoom.toFixed(2)));
    syncSliderProgressVisual(zoomControl.slider);
    updateTransform();
  };

  const snapshotMask = () => {
    if (!context) {
      return null;
    }
    return context.getImageData(0, 0, canvas.width, canvas.height);
  };

  const pushUndoSnapshot = () => {
    const snapshot = snapshotMask();
    if (!snapshot) {
      return;
    }
    state.undoStack.push(snapshot);
    if (state.undoStack.length > state.historyLimit) {
      state.undoStack.shift();
    }
    state.redoStack = [];
    updateUndoRedoState();
  };

  const stageMask = () => {
    if (!canvas.width || !canvas.height || !maskCanvasContract?.stageMaskData) {
      return;
    }
    const maskDataUrl = canvas.toDataURL("image/png");
    const staged = maskCanvasContract.stageMaskData(maskDataUrl, {
      sourceImageData: readTrimmedValue(imageDataInput),
      sourceImageAsset: readTrimmedValue(imageAssetInput),
    });
    if (staged) {
      state.pendingApply = true;
      updateStatus();
    }
  };

  const applyStagedMask = () => {
    if (!maskCanvasContract?.applyStagedMask) {
      updateStatus("Mask contract is unavailable.");
      return;
    }
    if (!state.pendingApply) {
      updateStatus("No pending mask changes.");
      return;
    }
    const result = maskCanvasContract.applyStagedMask();
    if (result?.ok) {
      state.pendingApply = false;
      if (typeof syncBoundControls === "function") {
        syncBoundControls([maskDataInput, maskAssetInput]);
      }
      updateStatus(result.message || "Applied mask.");
      return;
    }
    updateStatus(result?.message || "Failed to apply mask.");
  };

  const loadMaskFromDataUrl = async (maskDataUrl, options = {}) => {
    const normalized = String(maskDataUrl ?? "").trim();
    if (!normalized || !context || !canvas.width || !canvas.height) {
      return;
    }
    try {
      const image = await loadImage(normalized);
      context.save();
      context.globalCompositeOperation = "source-over";
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      context.restore();
      if (options.stageAfterLoad) {
        stageMask();
      } else {
        state.pendingApply = false;
        updateStatus("Loaded mask payload into editor.");
      }
    } catch (_error) {
      updateStatus("Unable to preview the current mask payload.");
    }
  };

  const loadSource = async (sourceUrl, options = {}) => {
    const signature = String(sourceUrl ?? "").trim();
    if (!signature) {
      sourceImage.removeAttribute("src");
      placeholder.hidden = false;
      stage.hidden = false;
      resetMaskCanvas(512, 512);
      state.sourceSignature = "";
      state.pendingApply = false;
      updateStatus("Load a source image to start drawing mask.");
      return;
    }
    const token = state.loadingToken + 1;
    state.loadingToken = token;
    try {
      const loadedImage = await loadImage(signature);
      if (token !== state.loadingToken) {
        return;
      }
      const longEdge = Math.max(loadedImage.naturalWidth, loadedImage.naturalHeight, 1);
      const downscale = longEdge > 1536 ? 1536 / longEdge : 1;
      const width = Math.max(64, Math.round(loadedImage.naturalWidth * downscale));
      const height = Math.max(64, Math.round(loadedImage.naturalHeight * downscale));
      sourceImage.src = signature;
      sourceImage.hidden = false;
      placeholder.hidden = true;
      resetMaskCanvas(width, height);
      state.sourceSignature = signature;
      if (options.fit !== false) {
        fitToViewport();
      } else {
        updateTransform();
      }
      if (options.maskDataUrl) {
        await loadMaskFromDataUrl(options.maskDataUrl, { stageAfterLoad: false });
      } else {
        updateStatus("Source image ready for mask drawing.");
      }
    } catch (_error) {
      sourceImage.removeAttribute("src");
      placeholder.hidden = false;
      resetMaskCanvas(512, 512);
      state.sourceSignature = "";
      updateStatus("Unable to load source image into mask editor.");
    }
  };

  const getCanvasPointer = (event) => {
    const rect = canvas.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / Math.max(rect.width, 1)) * canvas.width;
    const y = ((event.clientY - rect.top) / Math.max(rect.height, 1)) * canvas.height;
    return {
      x: clamp(x, 0, canvas.width),
      y: clamp(y, 0, canvas.height),
    };
  };

  const drawLine = (fromX, fromY, toX, toY) => {
    if (!context) {
      return;
    }
    const brushSize = clamp(Number(brushSizeControl.valueInput.value) || 36, 1, 256);
    const opacity = clamp(Number(brushOpacityControl.valueInput.value) || 1, 0.05, 1);
    const brushTone = state.tool === "eraser" ? 0 : 255;
    context.save();
    context.globalCompositeOperation = "source-over";
    context.lineCap = "round";
    context.lineJoin = "round";
    context.strokeStyle = `rgba(${brushTone}, ${brushTone}, ${brushTone}, ${opacity})`;
    context.lineWidth = brushSize;
    context.beginPath();
    context.moveTo(fromX, fromY);
    context.lineTo(toX, toY);
    context.stroke();
    context.restore();
  };

  const beginDrawing = (event) => {
    if (!context || !state.sourceSignature) {
      return;
    }
    if (state.tool === "pan") {
      state.panning = true;
      state.panPointerX = event.clientX;
      state.panPointerY = event.clientY;
      return;
    }
    if (state.tool === "select") {
      const point = getCanvasPointer(event);
      state.selectionAnchor = point;
      setSelection({ x: point.x, y: point.y, width: 1, height: 1 });
      return;
    }
    event.preventDefault();
    pushUndoSnapshot();
    state.pointerDown = true;
    const point = getCanvasPointer(event);
    state.lastDrawX = point.x;
    state.lastDrawY = point.y;
    drawLine(point.x, point.y, point.x, point.y);
  };

  const moveDrawing = (event) => {
    if (state.panning) {
      const deltaX = event.clientX - state.panPointerX;
      const deltaY = event.clientY - state.panPointerY;
      state.panPointerX = event.clientX;
      state.panPointerY = event.clientY;
      state.panX += deltaX;
      state.panY += deltaY;
      updateTransform();
      return;
    }
    if (!state.pointerDown || state.tool === "pan") {
      if (state.tool === "select" && state.selectionAnchor) {
        const point = getCanvasPointer(event);
        setSelection(
          normalizeSelectionRect(
            state.selectionAnchor.x,
            state.selectionAnchor.y,
            point.x,
            point.y,
            canvas.width,
            canvas.height,
          ),
        );
      }
      return;
    }
    event.preventDefault();
    const point = getCanvasPointer(event);
    drawLine(state.lastDrawX, state.lastDrawY, point.x, point.y);
    state.lastDrawX = point.x;
    state.lastDrawY = point.y;
  };

  const stopDrawing = () => {
    if (state.pointerDown) {
      state.pointerDown = false;
      stageMask();
    }
    if (state.tool === "select" && state.selectionAnchor) {
      state.selectionAnchor = null;
      if (!state.selection || state.selection.width < 2 || state.selection.height < 2) {
        clearSelection();
        updateStatus("Selection cleared.");
      } else {
        updateStatus("Selection ready.");
      }
    }
    if (state.panning) {
      state.panning = false;
    }
  };

  brushButton.addEventListener("click", () => {
    state.tool = "brush";
    updateToolButtons();
  });
  eraserButton.addEventListener("click", () => {
    state.tool = "eraser";
    updateToolButtons();
  });
  selectButton.addEventListener("click", () => {
    state.tool = "select";
    updateToolButtons();
  });
  panButton.addEventListener("click", () => {
    state.tool = "pan";
    updateToolButtons();
  });

  const bindNumberWithSlider = (control, min, max, fractionDigits = 2, onChange = null) => {
    const syncFromInput = () => {
      const normalized = clamp(Number(control.valueInput.value) || min, min, max);
      const rounded = Number(normalized.toFixed(fractionDigits));
      control.valueInput.value = String(rounded);
      control.slider.value = String(rounded);
      syncSliderProgressVisual(control.slider);
      if (typeof onChange === "function") {
        onChange(rounded);
      }
    };
    const syncFromSlider = () => {
      const normalized = clamp(Number(control.slider.value) || min, min, max);
      const rounded = Number(normalized.toFixed(fractionDigits));
      control.valueInput.value = String(rounded);
      control.slider.value = String(rounded);
      syncSliderProgressVisual(control.slider);
      if (typeof onChange === "function") {
        onChange(rounded);
      }
    };
    control.valueInput.addEventListener("input", syncFromInput);
    control.slider.addEventListener("input", syncFromSlider);
    // CRITICAL: force a first-pass slider sync at mount; otherwise Opacity/Zoom can render stale position/progress despite valid default numeric values.
    syncFromInput();
  };

  bindNumberWithSlider(brushSizeControl, 1, 256, 0);
  bindNumberWithSlider(brushOpacityControl, 0.05, 1, 2);
  bindNumberWithSlider(zoomControl, 0.25, 4, 2, (zoomValue) => {
    state.zoom = zoomValue;
    updateTransform();
  });

  viewport.addEventListener("wheel", (event) => {
    if (!event.ctrlKey) {
      return;
    }
    event.preventDefault();
    const direction = event.deltaY > 0 ? -0.1 : 0.1;
    const nextZoom = clamp(state.zoom + direction, 0.25, 4);
    state.zoom = Number(nextZoom.toFixed(2));
    zoomControl.valueInput.value = String(state.zoom);
    zoomControl.slider.value = String(state.zoom);
    syncSliderProgressVisual(zoomControl.slider);
    updateTransform();
  });

  canvas.addEventListener("pointerdown", beginDrawing);
  canvas.addEventListener("pointermove", moveDrawing);
  canvas.addEventListener("pointerup", stopDrawing);
  canvas.addEventListener("pointerleave", stopDrawing);
  canvas.addEventListener("pointercancel", stopDrawing);
  window.addEventListener("pointerup", stopDrawing);

  undoButton.addEventListener("click", () => {
    if (!context || !state.undoStack.length) {
      return;
    }
    const snapshot = snapshotMask();
    if (snapshot) {
      state.redoStack.push(snapshot);
    }
    const previous = state.undoStack.pop();
    if (previous) {
      context.putImageData(previous, 0, 0);
      stageMask();
    }
    updateUndoRedoState();
  });

  redoButton.addEventListener("click", () => {
    if (!context || !state.redoStack.length) {
      return;
    }
    const snapshot = snapshotMask();
    if (snapshot) {
      state.undoStack.push(snapshot);
    }
    const next = state.redoStack.pop();
    if (next) {
      context.putImageData(next, 0, 0);
      stageMask();
    }
    updateUndoRedoState();
  });

  const getActiveSelection = () => {
    const selection = state.selection;
    if (!selection || selection.width <= 0 || selection.height <= 0) {
      return null;
    }
    return selection;
  };

  const requireSelection = () => {
    const selection = getActiveSelection();
    if (!selection) {
      updateStatus("Create a selection first.");
      return null;
    }
    return selection;
  };

  const runSelectionMutation = (mutator, successMessage) => {
    const selection = requireSelection();
    if (!context || !selection) {
      return;
    }
    pushUndoSnapshot();
    mutator(selection);
    stageMask();
    updateStatus(successMessage);
  };

  clearButton.addEventListener("click", () => {
    if (!context || !state.sourceSignature) {
      return;
    }
    pushUndoSnapshot();
    fillMaskWithBlack();
    stageMask();
  });

  invertButton.addEventListener("click", () => {
    if (!context || !state.sourceSignature) {
      return;
    }
    pushUndoSnapshot();
    const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
    const pixels = imageData.data;
    for (let index = 0; index < pixels.length; index += 4) {
      pixels[index] = 255 - pixels[index];
      pixels[index + 1] = 255 - pixels[index + 1];
      pixels[index + 2] = 255 - pixels[index + 2];
      pixels[index + 3] = 255;
    }
    context.putImageData(imageData, 0, 0);
    stageMask();
  });

  fillSelectionButton.addEventListener("click", () => {
    runSelectionMutation((selection) => {
      context.save();
      context.fillStyle = "rgba(255, 255, 255, 1)";
      context.fillRect(selection.x, selection.y, selection.width, selection.height);
      context.restore();
    }, "Filled selected area.");
  });

  eraseSelectionButton.addEventListener("click", () => {
    runSelectionMutation((selection) => {
      context.save();
      context.fillStyle = "rgba(0, 0, 0, 1)";
      context.fillRect(selection.x, selection.y, selection.width, selection.height);
      context.restore();
    }, "Erased selected area.");
  });

  invertSelectionButton.addEventListener("click", () => {
    runSelectionMutation((selection) => {
      const selected = context.getImageData(selection.x, selection.y, selection.width, selection.height);
      const pixels = selected.data;
      for (let index = 0; index < pixels.length; index += 4) {
        pixels[index] = 255 - pixels[index];
        pixels[index + 1] = 255 - pixels[index + 1];
        pixels[index + 2] = 255 - pixels[index + 2];
        pixels[index + 3] = 255;
      }
      context.putImageData(selected, selection.x, selection.y);
    }, "Inverted selected area.");
  });

  const nudgeSelection = (deltaX, deltaY) => {
    const selection = requireSelection();
    if (!context || !selection) {
      return;
    }
    const nextX = clamp(selection.x + deltaX, 0, Math.max(canvas.width - selection.width, 0));
    const nextY = clamp(selection.y + deltaY, 0, Math.max(canvas.height - selection.height, 0));
    if (nextX === selection.x && nextY === selection.y) {
      return;
    }
    // IMPORTANT: move selected mask region as pixel data, then clamp new selection bounds to avoid off-canvas writes.
    pushUndoSnapshot();
    const selectedRegion = context.getImageData(selection.x, selection.y, selection.width, selection.height);
    context.save();
    context.fillStyle = "rgba(0, 0, 0, 1)";
    context.fillRect(selection.x, selection.y, selection.width, selection.height);
    context.restore();
    context.putImageData(selectedRegion, nextX, nextY);
    setSelection({
      x: nextX,
      y: nextY,
      width: selection.width,
      height: selection.height,
    });
    stageMask();
    updateStatus("Moved selected area.");
  };

  nudgeLeftButton.addEventListener("click", () => nudgeSelection(-8, 0));
  nudgeRightButton.addEventListener("click", () => nudgeSelection(8, 0));
  nudgeUpButton.addEventListener("click", () => nudgeSelection(0, -8));
  nudgeDownButton.addEventListener("click", () => nudgeSelection(0, 8));
  clearSelectionButton.addEventListener("click", () => {
    clearSelection();
    updateStatus("Selection cleared.");
  });

  fitButton.addEventListener("click", () => {
    fitToViewport();
    updateStatus("Mask viewport fitted.");
  });

  applyButton.addEventListener("click", () => {
    applyStagedMask();
  });

  const setMode = (modeValue) => {
    const rawMode = String(modeValue ?? "").trim().toLowerCase();
    const executionMode =
      typeof resolveExecutionMode === "function" ? String(resolveExecutionMode(rawMode) ?? rawMode) : rawMode;
    root.hidden = executionMode === "batch" || rawMode === "batch";
  };

  const refreshFromInputs = async () => {
    const sourceFromData = readTrimmedValue(imageDataInput);
    const sourceFromAsset = resolveAssetPreviewUrl(readTrimmedValue(imageAssetInput));
    const sourceSignature = sourceFromData || sourceFromAsset;
    const maskFromPayload = readTrimmedValue(maskDataInput);
    if (!sourceSignature) {
      await loadSource("");
      return;
    }
    if (sourceSignature !== state.sourceSignature) {
      await loadSource(sourceSignature, { maskDataUrl: maskFromPayload });
      return;
    }
    if (maskFromPayload && !state.pendingApply) {
      fillMaskWithBlack();
      await loadMaskFromDataUrl(maskFromPayload, { stageAfterLoad: false });
    }
  };

  const handleExternalMaskMutation = async () => {
    const payloadMask = readTrimmedValue(maskDataInput);
    if (!payloadMask) {
      return;
    }
    state.pendingApply = false;
    fillMaskWithBlack();
    await loadMaskFromDataUrl(payloadMask, { stageAfterLoad: false });
  };

  const forceStageCurrentMask = () => {
    if (!context || !state.sourceSignature) {
      return;
    }
    stageMask();
  };

  updateToolButtons();
  updateUndoRedoState();
  resetMaskCanvas(512, 512);
  updateTransform();
  setMode(modeInput?.value);

  return {
    applyStagedMask,
    forceStageCurrentMask,
    handleExternalMaskMutation,
    refreshFromInputs,
    setSelectionRect(rect) {
      setSelection(rect);
    },
    setMode,
    unmount() {
      window.removeEventListener("pointerup", stopDrawing);
    },
  };
}
