export const CANVAS_ACTIONS = Object.freeze({
  upload: "upload",
  remove: "remove",
  reset: "reset",
  undo: "undo",
  redo: "redo",
  fullscreen: "fullscreen",
});

export function normalizeCanvasSourceValue(value) {
  return String(value ?? "").trim();
}

export function hasCanvasSourceImage(imageData = "", imageAsset = "") {
  return Boolean(normalizeCanvasSourceValue(imageData) || normalizeCanvasSourceValue(imageAsset));
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
