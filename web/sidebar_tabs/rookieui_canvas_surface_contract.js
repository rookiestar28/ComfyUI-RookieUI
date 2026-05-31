export const CANVAS_ACTIONS = Object.freeze({
  upload: "upload",
  remove: "remove",
  reset: "reset",
  undo: "undo",
  redo: "redo",
  fullscreen: "fullscreen",
});

export const CANVAS_INTERACTION_MODES = Object.freeze({
  upload: "upload",
  edit: "edit",
});

export const CANVAS_FULLSCREEN_ACTIONS = Object.freeze({
  entered: "entered",
  exited: "exited",
  unavailable: "unavailable",
  failed: "failed",
});

export function normalizeCanvasSourceValue(value) {
  return String(value ?? "").trim();
}

export function hasCanvasSourceImage(imageData = "", imageAsset = "") {
  return Boolean(normalizeCanvasSourceValue(imageData) || normalizeCanvasSourceValue(imageAsset));
}

export function resolveCanvasInteractionMode(imageData = "", imageAsset = "") {
  return hasCanvasSourceImage(imageData, imageAsset) ? CANVAS_INTERACTION_MODES.edit : CANVAS_INTERACTION_MODES.upload;
}

export function canCanvasStageOpenUpload(imageData = "", imageAsset = "") {
  return resolveCanvasInteractionMode(imageData, imageAsset) === CANVAS_INTERACTION_MODES.upload;
}

function resolveFullscreenElement() {
  const doc = globalThis.document;
  if (!doc || typeof doc !== "object") {
    return null;
  }
  // IMPORTANT: Safari/WebKit fullscreen properties are intentionally typed locally; widening global DOM types would hide host-browser drift.
  const fullscreenDocument = /** @type {Document & { webkitFullscreenElement?: Element | null }} */ (doc);
  return fullscreenDocument.fullscreenElement ?? fullscreenDocument.webkitFullscreenElement ?? null;
}

export function isCanvasElementFullscreen(element) {
  const candidate = element && typeof element === "object" ? element : null;
  const fullscreenElement = resolveFullscreenElement();
  if (!candidate || !fullscreenElement) {
    return false;
  }
  if (candidate === fullscreenElement) {
    return true;
  }
  if (typeof fullscreenElement.contains === "function" && fullscreenElement.contains(candidate)) {
    return true;
  }
  // IMPORTANT: fullscreen roots can be either the stage itself or an enclosing surface; check both containment directions.
  return typeof candidate.contains === "function" && candidate.contains(fullscreenElement);
}

async function exitCanvasFullscreen() {
  const doc = globalThis.document;
  if (!doc || typeof doc !== "object") {
    return false;
  }
  // IMPORTANT: keep the prefixed branch for embedded WebKit shells that do not expose the standard method.
  const fullscreenDocument = /** @type {Document & { webkitExitFullscreen?: () => Promise<void> | void }} */ (doc);
  const exit = fullscreenDocument.exitFullscreen ?? fullscreenDocument.webkitExitFullscreen;
  if (typeof exit !== "function") {
    return false;
  }
  try {
    await exit.call(doc);
    return true;
  } catch (_error) {
    return false;
  }
}

export async function toggleCanvasFullscreen(element) {
  const candidate = element && typeof element === "object" ? element : null;
  if (!candidate) {
    return CANVAS_FULLSCREEN_ACTIONS.unavailable;
  }

  if (isCanvasElementFullscreen(candidate)) {
    const exited = await exitCanvasFullscreen();
    return exited ? CANVAS_FULLSCREEN_ACTIONS.exited : CANVAS_FULLSCREEN_ACTIONS.failed;
  }

  const request = candidate.requestFullscreen ?? candidate.webkitRequestFullscreen;
  if (typeof request !== "function") {
    return CANVAS_FULLSCREEN_ACTIONS.unavailable;
  }
  try {
    await request.call(candidate);
    return CANVAS_FULLSCREEN_ACTIONS.entered;
  } catch (_error) {
    return CANVAS_FULLSCREEN_ACTIONS.failed;
  }
}

export async function requestCanvasFullscreen(element) {
  const result = await toggleCanvasFullscreen(element);
  return result === CANVAS_FULLSCREEN_ACTIONS.entered;
}
