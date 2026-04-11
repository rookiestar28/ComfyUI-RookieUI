import { describe, expect, test } from "vitest";

import { createImg2ImgMaskCanvasContract } from "../sidebar_tabs/rookieui_img2img_mask_canvas.js";

function createInput(value = "") {
  const input = document.createElement("input");
  input.value = value;
  return input;
}

describe("createImg2ImgMaskCanvasContract", () => {
  test("stages and applies mask data into existing img2img payload fields", () => {
    const modeInput = createInput("inpaint");
    const imageDataInput = createInput("data:image/png;base64,source");
    const imageAssetInput = createInput("");
    const maskDataInput = createInput("");
    const maskAssetInput = createInput("existing-mask-asset");

    const contract = createImg2ImgMaskCanvasContract({
      modeInput,
      imageDataInput,
      imageAssetInput,
      maskDataInput,
      maskAssetInput,
      resolveExecutionMode: (mode) => mode,
    });

    expect(contract.stageMaskData("data:image/png;base64,mask")).toBe(true);
    expect(contract.getSubmissionReadiness()).toEqual({
      ok: false,
      message: "Mask canvas has unapplied changes. Click Apply Mask before submitting.",
    });

    const applyResult = contract.applyStagedMask();
    expect(applyResult.ok).toBe(true);
    expect(maskDataInput.value).toBe("data:image/png;base64,mask");
    expect(maskAssetInput.value).toBe("");
    expect(contract.getSubmissionReadiness()).toEqual({ ok: true });
  });

  test("reports mode guard when inpaint execution has staged mask but no payload mask", () => {
    const modeInput = createInput("inpaint_upload");
    const imageDataInput = createInput("");
    const imageAssetInput = createInput("img-asset");
    const maskDataInput = createInput("");
    const maskAssetInput = createInput("");

    const contract = createImg2ImgMaskCanvasContract({
      modeInput,
      imageDataInput,
      imageAssetInput,
      maskDataInput,
      maskAssetInput,
      resolveExecutionMode: () => "inpaint",
    });
    contract.stageMaskData("data:image/png;base64,mask");
    const guard = contract.onModeChange();
    expect(guard.ok).toBe(false);
    expect(guard.message).toContain("Apply Mask");
  });

  test("resets dirty staged state when external payload mutates mask_data", () => {
    const modeInput = createInput("inpaint");
    const imageDataInput = createInput("data:image/png;base64,source");
    const imageAssetInput = createInput("");
    const maskDataInput = createInput("");
    const maskAssetInput = createInput("");

    const contract = createImg2ImgMaskCanvasContract({
      modeInput,
      imageDataInput,
      imageAssetInput,
      maskDataInput,
      maskAssetInput,
      resolveExecutionMode: (mode) => mode,
    });
    contract.stageMaskData("data:image/png;base64,staged-mask");
    maskDataInput.value = "data:image/png;base64,external-mask";
    contract.handleExternalMaskMutation();

    const snapshot = contract.getStateSnapshot();
    expect(snapshot.stagedMaskData).toBe("data:image/png;base64,external-mask");
    expect(snapshot.stagedMaskDirty).toBe(false);
  });

  test("clears staged mask state when external payload clears mask_data", () => {
    const modeInput = createInput("inpaint");
    const imageDataInput = createInput("data:image/png;base64,source");
    const imageAssetInput = createInput("");
    const maskDataInput = createInput("");
    const maskAssetInput = createInput("");

    const contract = createImg2ImgMaskCanvasContract({
      modeInput,
      imageDataInput,
      imageAssetInput,
      maskDataInput,
      maskAssetInput,
      resolveExecutionMode: (mode) => mode,
    });
    contract.stageMaskData("data:image/png;base64,staged-mask");
    maskDataInput.value = "";
    contract.handleExternalMaskMutation();

    const snapshot = contract.getStateSnapshot();
    expect(snapshot.stagedMaskData).toBe("");
    expect(snapshot.stagedMaskDirty).toBe(false);
  });

  test("resets staged dirty state when source signature changes without committed mask payload", () => {
    const modeInput = createInput("img2img");
    const imageDataInput = createInput("data:image/png;base64,source-a");
    const imageAssetInput = createInput("");
    const maskDataInput = createInput("");
    const maskAssetInput = createInput("");

    const contract = createImg2ImgMaskCanvasContract({
      modeInput,
      imageDataInput,
      imageAssetInput,
      maskDataInput,
      maskAssetInput,
      resolveExecutionMode: (mode) => mode,
    });
    contract.stageMaskData("data:image/png;base64,staged-mask");
    imageDataInput.value = "data:image/png;base64,source-b";
    contract.refreshSourceBinding();

    const snapshot = contract.getStateSnapshot();
    expect(snapshot.sourceSignature).toContain("source-b");
    expect(snapshot.stagedMaskData).toBe("");
    expect(snapshot.stagedMaskDirty).toBe(false);
  });
});
