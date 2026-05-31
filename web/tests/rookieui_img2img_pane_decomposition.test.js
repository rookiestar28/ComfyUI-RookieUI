import { describe, expect, test, vi } from "vitest";

import {
  buildImageEditReferencePayloadFromElements,
  resolveActiveImg2ImgProfile,
  syncImageEditProfileStateFromElements,
} from "../sidebar_tabs/img2img/rookieui_img2img_reference_state.js";
import {
  setImg2ImgFieldVisibility,
  syncImageEditReferenceUi,
  syncImg2ImgModeAvailability,
  syncImg2ImgModeParameterFields,
} from "../sidebar_tabs/img2img/rookieui_img2img_mode_surface.js";

const input = (value) => ({ value });

function createReferenceElements() {
  return {
    imageAsset: input("source.png"),
    imageData: input(""),
    referenceAsset2: input("ref-2.png"),
    referenceData2: input(""),
    referenceAsset3: input(""),
    referenceData3: input("data:image/png;base64,REF3"),
    mainReferenceIndex: input("2"),
    imageEditProfile: input("false"),
    maxDirectReferences: input("3"),
  };
}

function createFieldWithControls() {
  const field = document.createElement("div");
  field.appendChild(document.createElement("input"));
  field.appendChild(document.createElement("button"));
  return field;
}

describe("Img2Img pane decomposition helpers", () => {
  test("resolves active profiles with normalized ids", () => {
    const profile = { id: "qwen_image_edit_2511", image_edit_profile: true };
    const lookup = new Map([["qwen_image_edit_2511", profile]]);
    expect(resolveActiveImg2ImgProfile(lookup, " QWEN_IMAGE_EDIT_2511 ")).toBe(profile);
    expect(resolveActiveImg2ImgProfile(lookup, "missing")).toBeNull();
  });

  test("builds ordered image-edit reference payloads from element snapshots", () => {
    const payload = buildImageEditReferencePayloadFromElements(createReferenceElements());
    expect(payload).toEqual({
      referenceImages: [
        { image_asset: "source.png", image_data: "" },
        { image_asset: "ref-2.png", image_data: "" },
        { image_asset: "", image_data: "data:image/png;base64,REF3" },
      ],
      mainReferenceIndex: 2,
      selectedMainSlot: 2,
    });

    expect(buildImageEditReferencePayloadFromElements(createReferenceElements(), 0)).toEqual({
      referenceImages: [],
      mainReferenceIndex: 0,
      selectedMainSlot: 0,
    });
  });

  test("syncs image-edit profile hidden state and clamps main reference slot", () => {
    const elements = createReferenceElements();
    elements.mainReferenceIndex.value = "99";
    const state = syncImageEditProfileStateFromElements(elements, {
      image_edit_profile: true,
      max_direct_references: 2,
    });

    expect(state).toMatchObject({ imageEditProfile: true, referenceLimit: 2, normalizedMainSlot: 1 });
    expect(elements.imageEditProfile.value).toBe("true");
    expect(elements.maxDirectReferences.value).toBe("2");
    expect(elements.mainReferenceIndex.value).toBe("1");
  });

  test("toggles field trees and mode availability for image-edit profiles", () => {
    const modeInput = input("inpaint");
    const img2imgButton = document.createElement("button");
    const inpaintButton = document.createElement("button");
    const modeRouter = { activateSubtab: vi.fn() };
    const setElementValue = vi.fn((element, value) => {
      element.value = value;
    });

    syncImg2ImgModeAvailability({
      profileState: { imageEditProfile: true },
      elements: { mode: modeInput },
      modeRouter,
      modeUi: {
        modeButtons: new Map([
          ["img2img", img2imgButton],
          ["inpaint", inpaintButton],
        ]),
      },
      setElementValue,
    });

    expect(modeInput.value).toBe("img2img");
    expect(modeRouter.activateSubtab).toHaveBeenCalledWith("img2img", { dispatchChange: false });
    expect(img2imgButton.disabled).toBe(false);
    expect(inpaintButton.disabled).toBe(true);
    expect(inpaintButton.getAttribute("aria-disabled")).toBe("true");
  });

  test("syncs reference slot visibility and parameter fields", () => {
    const referenceSection = document.createElement("section");
    const referenceHintNode = document.createElement("p");
    const visibleSlot = {
      slotIndex: 0,
      card: document.createElement("div"),
      mainRadio: document.createElement("input"),
      assetInput: document.createElement("input"),
      fileInput: document.createElement("input"),
      updateStatus: vi.fn(),
    };
    const hiddenSlot = {
      slotIndex: 1,
      card: document.createElement("div"),
      mainRadio: document.createElement("input"),
      assetInput: document.createElement("input"),
      fileInput: document.createElement("input"),
      updateStatus: vi.fn(),
    };

    syncImageEditReferenceUi(
      { imageEditProfile: true, referenceLimit: 1, normalizedMainSlot: 0 },
      { referenceSection, referenceHintNode, referenceSlots: [visibleSlot, hiddenSlot] },
    );

    expect(referenceSection.hidden).toBe(false);
    expect(referenceHintNode.textContent).toContain("only one direct reference");
    expect(visibleSlot.card.hidden).toBe(false);
    expect(visibleSlot.mainRadio.checked).toBe(true);
    expect(hiddenSlot.card.hidden).toBe(true);
    expect(hiddenSlot.assetInput.disabled).toBe(true);

    const widthField = createFieldWithControls();
    const hiresSection = createFieldWithControls();
    syncImg2ImgModeParameterFields(
      { imageEditProfile: true },
      {
        widthField,
        heightField: null,
        resizeModeField: null,
        denoiseField: null,
        growMaskField: null,
        batchSizeField: null,
        clipSkipField: null,
        hiresSection,
      },
    );
    expect(widthField.hidden).toBe(true);
    expect(widthField.querySelector("input").disabled).toBe(true);
    expect(hiresSection.hidden).toBe(true);
    expect(hiresSection.querySelector("button").disabled).toBe(true);

    setImg2ImgFieldVisibility(widthField, true);
    expect(widthField.hidden).toBe(false);
    expect(widthField.querySelector("input").disabled).toBe(false);
  });
});
