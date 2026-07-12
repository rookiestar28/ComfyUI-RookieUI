const DEFAULT_BRUSH_WIDTH = 25;
const DEFAULT_BRUSH_OPACITY = 100;
const DEFAULT_BRUSH_SOFTNESS = 0;
const MIN_INDICATOR_PIXELS = 8;

function clamp(value, min, max) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return min;
  }
  return Math.min(max, Math.max(min, numeric));
}

function createBrushControl({ host, id, labelText, min, max, step, defaultValue }) {
  const control = document.createElement("label");
  control.className = "rookieui-shell__canvas-brush-control";
  control.id = `${id}-field`;

  const label = document.createElement("span");
  label.className = "rookieui-shell__canvas-brush-control-label";
  control.appendChild(label);

  const slider = document.createElement("input");
  slider.type = "range";
  slider.className = "rookieui-shell__slider";
  slider.id = id;
  slider.min = String(min);
  slider.max = String(max);
  slider.step = String(step);
  slider.value = String(defaultValue);
  control.appendChild(slider);

  const updateLabel = () => {
    label.textContent = `${labelText} (${slider.value})`;
  };
  slider.addEventListener("input", updateLabel);
  updateLabel();

  host.appendChild(control);
  return {
    control,
    slider,
    setDisabled(disabled) {
      slider.disabled = disabled;
    },
  };
}

function resolveCanvasRenderBox(stage, canvas, zoomScale = 1) {
  const stageRect = stage.getBoundingClientRect();
  const canvasWidth = Number(canvas.width || 0);
  const canvasHeight = Number(canvas.height || 0);
  if (!stageRect.width || !stageRect.height || !canvasWidth || !canvasHeight) {
    return null;
  }
  const normalizedZoom = clamp(zoomScale, 0.1, 4);
  const renderScale = Math.min(stageRect.width / canvasWidth, stageRect.height / canvasHeight) * normalizedZoom;
  const renderWidth = canvasWidth * renderScale;
  const renderHeight = canvasHeight * renderScale;
  const offsetX = (stageRect.width - renderWidth) / 2;
  const offsetY = (stageRect.height - renderHeight) / 2;
  return {
    stageRect,
    renderScale,
    renderWidth,
    renderHeight,
    offsetX,
    offsetY,
  };
}

function mapPointerToCanvas(event, stage, canvas, zoomScale = 1) {
  const renderBox = resolveCanvasRenderBox(stage, canvas, zoomScale);
  if (!renderBox) {
    return null;
  }
  const localX = event.clientX - renderBox.stageRect.left;
  const localY = event.clientY - renderBox.stageRect.top;
  if (
    localX < renderBox.offsetX ||
    localX > renderBox.offsetX + renderBox.renderWidth ||
    localY < renderBox.offsetY ||
    localY > renderBox.offsetY + renderBox.renderHeight
  ) {
    return null;
  }
  return {
    x: (localX - renderBox.offsetX) / renderBox.renderScale,
    y: (localY - renderBox.offsetY) / renderBox.renderScale,
  };
}

function readCanvasImage(dataUrl) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("failed to decode source image"));
    image.src = dataUrl;
  });
}

function isJSDOMEnvironment() {
  const userAgent = String(globalThis?.navigator?.userAgent ?? "");
  return /jsdom/i.test(userAgent);
}

function resolveDocumentFullscreenElement() {
  const doc = globalThis.document;
  if (!doc || typeof doc !== "object") {
    return null;
  }
  return doc.fullscreenElement ?? doc.webkitFullscreenElement ?? null;
}

function getCanvas2dContext(canvas) {
  if (!canvas || typeof canvas.getContext !== "function") {
    return null;
  }
  if (isJSDOMEnvironment()) {
    // CRITICAL: jsdom's canvas backend is intentionally unimplemented and emits noisy not-implemented errors; short-circuit to keep CI signal clean.
    return null;
  }
  try {
    // CRITICAL: some runtime environments expose <canvas> without a 2D backend; guard to keep editor boot resilient instead of throwing during module init.
    return canvas.getContext("2d");
  } catch (_error) {
    return null;
  }
}

export function createSourceCanvasBrushController({
  idPrefix,
  stage,
  toolbar,
  previewImage = null,
  onCommitSource,
  onStatusMessage = null,
}) {
  if (!stage || !toolbar || typeof onCommitSource !== "function") {
    return {
      syncSourceData: () => {},
      setEnabled: () => {},
      isEnabled: () => false,
    };
  }

  const canvas = document.createElement("canvas");
  canvas.className = "rookieui-shell__canvas-brush-layer";
  canvas.id = `${idPrefix}-brush-canvas`;
  canvas.hidden = true;
  stage.appendChild(canvas);
  const context = getCanvas2dContext(canvas);

  const brushIndicator = document.createElement("div");
  brushIndicator.className = "rookieui-shell__canvas-brush-indicator";
  brushIndicator.id = `${idPrefix}-brush-indicator`;
  brushIndicator.hidden = true;
  const indicatorCrossHorizontal = document.createElement("span");
  indicatorCrossHorizontal.className = "rookieui-shell__canvas-brush-indicator-cross rookieui-shell__canvas-brush-indicator-cross--horizontal";
  brushIndicator.appendChild(indicatorCrossHorizontal);
  const indicatorCrossVertical = document.createElement("span");
  indicatorCrossVertical.className = "rookieui-shell__canvas-brush-indicator-cross rookieui-shell__canvas-brush-indicator-cross--vertical";
  brushIndicator.appendChild(indicatorCrossVertical);
  stage.appendChild(brushIndicator);

  const brushToggleButton = document.createElement("button");
  brushToggleButton.type = "button";
  brushToggleButton.id = `${idPrefix}-brush-toggle`;
  brushToggleButton.className =
    "rookieui-shell__mini-action rookieui-shell__mini-action--icon rookieui-shell__mini-action--tone-neutral";
  brushToggleButton.dataset.canvasAction = "brush";
  brushToggleButton.title = "Toggle brush drawing";
  brushToggleButton.setAttribute("aria-label", "Toggle brush drawing");
  const brushIcon = document.createElement("span");
  brushIcon.className = "rookieui-shell__mini-action-icon";
  brushIcon.textContent = "🖌";
  brushToggleButton.appendChild(brushIcon);
  toolbar.appendChild(brushToggleButton);

  const controlsHost = document.createElement("div");
  controlsHost.className = "rookieui-shell__canvas-brush-controls";
  controlsHost.id = `${idPrefix}-brush-controls`;
  toolbar.appendChild(controlsHost);

  const widthControl = createBrushControl({
    host: controlsHost,
    id: `${idPrefix}-brush-width`,
    labelText: "Brush Width",
    min: 1,
    max: 128,
    step: 1,
    defaultValue: DEFAULT_BRUSH_WIDTH,
  });
  const opacityControl = createBrushControl({
    host: controlsHost,
    id: `${idPrefix}-brush-opacity`,
    labelText: "Brush Opacity",
    min: 1,
    max: 100,
    step: 1,
    defaultValue: DEFAULT_BRUSH_OPACITY,
  });
  const softnessControl = createBrushControl({
    host: controlsHost,
    id: `${idPrefix}-brush-softness`,
    labelText: "Brush Softness",
    min: 0,
    max: 100,
    step: 1,
    defaultValue: DEFAULT_BRUSH_SOFTNESS,
  });

  const state = {
    enabled: false,
    hasSource: false,
    drawing: false,
    lastPoint: null,
    dirty: false,
    sourceToken: 0,
    lastPointerClientX: null,
    lastPointerClientY: null,
    zoomPercent: 100,
    fullscreenActive: false,
  };

  const fullscreenZoom = document.createElement("div");
  fullscreenZoom.className = "rookieui-shell__canvas-fullscreen-zoom";
  fullscreenZoom.id = `${idPrefix}-fullscreen-zoom`;
  fullscreenZoom.hidden = true;
  const fullscreenZoomLabel = document.createElement("span");
  fullscreenZoomLabel.className = "rookieui-shell__canvas-fullscreen-zoom-label";
  fullscreenZoom.appendChild(fullscreenZoomLabel);
  const fullscreenZoomSlider = document.createElement("input");
  fullscreenZoomSlider.type = "range";
  fullscreenZoomSlider.className = "rookieui-shell__slider";
  fullscreenZoomSlider.id = `${idPrefix}-fullscreen-zoom-slider`;
  fullscreenZoomSlider.min = "50";
  fullscreenZoomSlider.max = "300";
  fullscreenZoomSlider.step = "5";
  fullscreenZoomSlider.value = "100";
  fullscreenZoom.appendChild(fullscreenZoomSlider);
  stage.appendChild(fullscreenZoom);

  const updateFullscreenZoomLabel = () => {
    fullscreenZoomLabel.textContent = `Zoom (${state.zoomPercent}%)`;
  };
  updateFullscreenZoomLabel();

  const resolveZoomScale = () => {
    if (!state.fullscreenActive) {
      return 1;
    }
    return clamp(state.zoomPercent, 50, 300) / 100;
  };

  const isStageWithinFullscreenElement = () => {
    const fullscreenElement = resolveDocumentFullscreenElement();
    if (!fullscreenElement || !stage) {
      return false;
    }
    if (fullscreenElement === stage) {
      return true;
    }
    return typeof fullscreenElement.contains === "function" && fullscreenElement.contains(stage);
  };

  const hideBrushIndicator = () => {
    brushIndicator.hidden = true;
  };

  const syncCanvasViewport = () => {
    const renderBox = resolveCanvasRenderBox(stage, canvas, resolveZoomScale());
    if (!renderBox) {
      canvas.style.left = "0px";
      canvas.style.top = "0px";
      canvas.style.width = "0px";
      canvas.style.height = "0px";
      if (previewImage) {
        previewImage.style.left = "0px";
        previewImage.style.top = "0px";
        previewImage.style.width = "100%";
        previewImage.style.height = "100%";
      }
      hideBrushIndicator();
      return null;
    }
    // IMPORTANT: keep brush-layer viewport anchored to the same contain-fitted geometry as the preview image to avoid aspect-ratio stretching and pointer drift.
    canvas.style.left = `${renderBox.offsetX}px`;
    canvas.style.top = `${renderBox.offsetY}px`;
    canvas.style.width = `${renderBox.renderWidth}px`;
    canvas.style.height = `${renderBox.renderHeight}px`;
    if (previewImage) {
      previewImage.style.left = `${renderBox.offsetX}px`;
      previewImage.style.top = `${renderBox.offsetY}px`;
      previewImage.style.width = `${renderBox.renderWidth}px`;
      previewImage.style.height = `${renderBox.renderHeight}px`;
    }
    return renderBox;
  };

  const syncBrushIndicatorAtClientPoint = (clientX, clientY) => {
    if (!state.enabled || !state.hasSource) {
      hideBrushIndicator();
      return;
    }
    const renderBox = resolveCanvasRenderBox(stage, canvas, resolveZoomScale());
    if (!renderBox) {
      hideBrushIndicator();
      return;
    }
    const localX = clientX - renderBox.stageRect.left;
    const localY = clientY - renderBox.stageRect.top;
    const withinBounds =
      localX >= renderBox.offsetX &&
      localX <= renderBox.offsetX + renderBox.renderWidth &&
      localY >= renderBox.offsetY &&
      localY <= renderBox.offsetY + renderBox.renderHeight;
    if (!withinBounds) {
      hideBrushIndicator();
      return;
    }

    const brushDiameter = Math.max(MIN_INDICATOR_PIXELS, clamp(widthControl.slider.value, 1, 128) * renderBox.renderScale);
    brushIndicator.style.left = `${localX}px`;
    brushIndicator.style.top = `${localY}px`;
    brushIndicator.style.width = `${brushDiameter}px`;
    brushIndicator.style.height = `${brushDiameter}px`;
    brushIndicator.hidden = false;
  };

  const syncBrushIndicatorFromStoredPointer = () => {
    if (!Number.isFinite(state.lastPointerClientX) || !Number.isFinite(state.lastPointerClientY)) {
      return;
    }
    syncBrushIndicatorAtClientPoint(state.lastPointerClientX, state.lastPointerClientY);
  };

  const syncEnabledVisual = () => {
    brushToggleButton.dataset.active = state.enabled ? "true" : "false";
    brushToggleButton.classList.toggle("is-active", state.enabled);
    canvas.style.pointerEvents = state.enabled ? "auto" : "none";
    canvas.style.cursor = state.enabled ? "none" : "default";
    widthControl.setDisabled(!state.hasSource);
    opacityControl.setDisabled(!state.hasSource);
    softnessControl.setDisabled(!state.hasSource);
    if (!state.enabled || !state.hasSource) {
      hideBrushIndicator();
      return;
    }
    syncBrushIndicatorFromStoredPointer();
  };

  const setEnabled = (nextEnabled) => {
    state.enabled = Boolean(nextEnabled) && state.hasSource;
    syncEnabledVisual();
  };

  const drawSegment = (from, to) => {
    if (!context) {
      return;
    }
    const width = clamp(widthControl.slider.value, 1, 128);
    const opacity = clamp(opacityControl.slider.value, 1, 100) / 100;
    const softness = clamp(softnessControl.slider.value, 0, 100) / 100;

    context.save();
    context.globalAlpha = opacity;
    context.strokeStyle = "rgba(255, 255, 255, 1)";
    context.lineCap = "round";
    context.lineJoin = "round";
    context.lineWidth = width;
    context.shadowColor = "rgba(255, 255, 255, 0.9)";
    context.shadowBlur = width * softness;
    context.beginPath();
    context.moveTo(from.x, from.y);
    context.lineTo(to.x, to.y);
    context.stroke();
    context.restore();
  };

  const commitBrushStroke = async () => {
    if (!state.dirty || !state.hasSource) {
      return;
    }
    state.dirty = false;
    try {
      await onCommitSource(canvas.toDataURL("image/png"));
      if (typeof onStatusMessage === "function") {
        onStatusMessage("Applied source brush edits.");
      }
    } catch (_error) {
      if (typeof onStatusMessage === "function") {
        onStatusMessage("Failed to commit source brush edits.");
      }
    }
  };

  const stopDrawing = async (event) => {
    if (!state.drawing) {
      return;
    }
    state.drawing = false;
    state.lastPoint = null;
    if (typeof event?.pointerId === "number" && canvas.hasPointerCapture(event.pointerId)) {
      canvas.releasePointerCapture(event.pointerId);
    }
    await commitBrushStroke();
  };

  canvas.addEventListener("pointerdown", (event) => {
    if (!state.enabled || !state.hasSource || event.button !== 0) {
      return;
    }
    const point = mapPointerToCanvas(event, stage, canvas, resolveZoomScale());
    if (!point) {
      return;
    }
    state.lastPointerClientX = event.clientX;
    state.lastPointerClientY = event.clientY;
    syncBrushIndicatorAtClientPoint(event.clientX, event.clientY);
    state.drawing = true;
    state.dirty = false;
    state.lastPoint = point;
    canvas.setPointerCapture(event.pointerId);
    event.preventDefault();
  });

  canvas.addEventListener("pointermove", (event) => {
    state.lastPointerClientX = event.clientX;
    state.lastPointerClientY = event.clientY;
    syncBrushIndicatorAtClientPoint(event.clientX, event.clientY);
    if (!state.drawing || !state.enabled || !state.lastPoint) {
      return;
    }
    const point = mapPointerToCanvas(event, stage, canvas, resolveZoomScale());
    if (!point) {
      return;
    }
    drawSegment(state.lastPoint, point);
    state.lastPoint = point;
    state.dirty = true;
    event.preventDefault();
  });

  canvas.addEventListener("pointerenter", (event) => {
    state.lastPointerClientX = event.clientX;
    state.lastPointerClientY = event.clientY;
    syncBrushIndicatorAtClientPoint(event.clientX, event.clientY);
  });

  canvas.addEventListener("pointerleave", async (event) => {
    hideBrushIndicator();
    await stopDrawing(event);
  });
  canvas.addEventListener("pointerup", stopDrawing);
  canvas.addEventListener("pointercancel", stopDrawing);

  brushToggleButton.addEventListener("click", () => {
    setEnabled(!state.enabled);
  });
  widthControl.slider.addEventListener("input", syncBrushIndicatorFromStoredPointer);

  const syncFullscreenZoomVisibility = () => {
    state.fullscreenActive = isStageWithinFullscreenElement();
    if (!state.fullscreenActive) {
      state.zoomPercent = 100;
      fullscreenZoomSlider.value = "100";
      updateFullscreenZoomLabel();
    }
    fullscreenZoom.hidden = !(state.fullscreenActive && state.hasSource);
    syncCanvasViewport();
    syncBrushIndicatorFromStoredPointer();
  };

  fullscreenZoomSlider.addEventListener("input", () => {
    state.zoomPercent = Math.round(clamp(fullscreenZoomSlider.value, 50, 300));
    fullscreenZoomSlider.value = String(state.zoomPercent);
    updateFullscreenZoomLabel();
    syncCanvasViewport();
    syncBrushIndicatorFromStoredPointer();
  });

  if (globalThis.document && typeof globalThis.document.addEventListener === "function") {
    globalThis.document.addEventListener("fullscreenchange", syncFullscreenZoomVisibility);
    globalThis.document.addEventListener("webkitfullscreenchange", syncFullscreenZoomVisibility);
  }

  if (typeof globalThis.ResizeObserver === "function") {
    const resizeObserver = new globalThis.ResizeObserver(() => {
      syncCanvasViewport();
      syncBrushIndicatorFromStoredPointer();
    });
    resizeObserver.observe(stage);
  }

  syncEnabledVisual();

  const syncSourceData = async (dataUrl) => {
    const normalized = String(dataUrl ?? "").trim();
    const token = state.sourceToken + 1;
    state.sourceToken = token;

    if (!normalized.startsWith("data:image/")) {
      state.hasSource = false;
      state.drawing = false;
      state.lastPoint = null;
      state.lastPointerClientX = null;
      state.lastPointerClientY = null;
      canvas.hidden = true;
      hideBrushIndicator();
      if (context) {
        context.clearRect(0, 0, canvas.width, canvas.height);
      }
      setEnabled(false);
      syncFullscreenZoomVisibility();
      return;
    }

    try {
      const image = await readCanvasImage(normalized);
      if (token !== state.sourceToken || !context) {
        return;
      }
      canvas.width = Math.max(1, image.naturalWidth || image.width || 1);
      canvas.height = Math.max(1, image.naturalHeight || image.height || 1);
      context.clearRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      canvas.hidden = false;
      state.hasSource = true;
      syncCanvasViewport();
      // IMPORTANT: source-present surfaces must default to brush-ready interaction mode instead of upload-click mode.
      setEnabled(true);
      syncBrushIndicatorFromStoredPointer();
      syncFullscreenZoomVisibility();
    } catch (_error) {
      state.hasSource = false;
      canvas.hidden = true;
      hideBrushIndicator();
      setEnabled(false);
      syncFullscreenZoomVisibility();
      if (typeof onStatusMessage === "function") {
        onStatusMessage("Unable to initialize source brush canvas.");
      }
    }
  };

  return {
    syncSourceData,
    setEnabled,
    syncFullscreenState: syncFullscreenZoomVisibility,
    isEnabled() {
      return state.enabled;
    },
    destroy() {
      state.sourceToken += 1;
      globalThis.document?.removeEventListener?.("fullscreenchange", syncFullscreenZoomVisibility);
      globalThis.document?.removeEventListener?.("webkitfullscreenchange", syncFullscreenZoomVisibility);
    },
  };
}
