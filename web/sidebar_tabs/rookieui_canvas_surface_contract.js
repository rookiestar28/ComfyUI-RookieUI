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

export async function requestCanvasFullscreen(element) {
  const candidate = element && typeof element === "object" ? element : null;
  const request = candidate?.requestFullscreen;
  if (typeof request !== "function") {
    return false;
  }
  try {
    await request.call(candidate);
    return true;
  } catch (_error) {
    return false;
  }
}
