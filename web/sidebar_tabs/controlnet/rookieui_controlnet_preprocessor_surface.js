import { hasCanvasSourceImage } from "../rookieui_canvas_surface_contract.js";

export const RUN_PREPROCESSOR_ICON = "💥";
export const RUN_PREPROCESSOR_BUSY_ICON = "⏳";

export function hasIndependentControlImageData(row) {
  return hasCanvasSourceImage(row?.imageData?.value ?? "", "");
}

export function syncRunPreprocessorVisibility(row, isImg2ImgEditor) {
  if (!row?.runPreprocessorButton) {
    return;
  }
  const shouldShow = !isImg2ImgEditor || hasIndependentControlImageData(row);
  const isBusy = Boolean(row.preprocessorBusy);
  row.runPreprocessorButton.hidden = !shouldShow;
  row.runPreprocessorButton.style.display = shouldShow ? "" : "none";
  row.runPreprocessorButton.dataset.running = isBusy ? "true" : "false";
  row.runPreprocessorButton.setAttribute("aria-busy", isBusy ? "true" : "false");
  row.runPreprocessorButton.title = isBusy ? "Running Preprocessor..." : "Run Preprocessor";
  row.runPreprocessorButton.setAttribute("aria-label", row.runPreprocessorButton.title);
  const runIcon = row.runPreprocessorButton.querySelector(".rookieui-shell__mini-action-icon");
  if (runIcon) {
    runIcon.textContent = isBusy ? RUN_PREPROCESSOR_BUSY_ICON : RUN_PREPROCESSOR_ICON;
  }
  // CRITICAL: img2img must hide Run Preprocessor until an independent control image is present.
  row.runPreprocessorButton.disabled = !shouldShow || isBusy;
}
