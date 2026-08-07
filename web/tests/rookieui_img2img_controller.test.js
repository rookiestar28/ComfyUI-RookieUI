import { describe, expect, test } from "vitest";

import {
  IMG2IMG_GENERATION_MODES,
  createImg2ImgController,
} from "../sidebar_tabs/img2img/rookieui_img2img_controller.js";
import { buildImageEditReferencePayloadFromElements } from "../sidebar_tabs/img2img/rookieui_img2img_reference_state.js";

describe("createImg2ImgController", () => {
  test("normalizes canonical modes and image-edit availability", () => {
    const controller = createImg2ImgController({ initialMode: "unknown" });

    expect(controller.getSnapshot().mode).toBe("img2img");
    expect(controller.getSupportedModes()).toEqual(IMG2IMG_GENERATION_MODES);
    expect(controller.setMode("inpaint")).toBe("inpaint");
    controller.setProfileState({ profileId: "qwen_image_edit_2511", imageEditProfile: true, maxDirectReferences: 2 });
    expect(controller.getSnapshot()).toMatchObject({
      profileId: "qwen_image_edit_2511",
      imageEditProfile: true,
      referenceLimit: 2,
      mode: "img2img",
    });
    expect(controller.setMode("batch")).toBe("img2img");
  });

  test("preserves ordered reference slots and maps the selected main slot", () => {
    const controller = createImg2ImgController({ referenceLimit: 3 });
    controller.setReferenceSlots([
      { image_asset: "source.png", image_data: "" },
      { image_asset: "", image_data: "" },
      { image_asset: "third.png", image_data: "" },
    ]);
    controller.setMainReferenceSlot(2);

    expect(controller.getReferencePayload()).toEqual({
      referenceImages: [
        { image_asset: "source.png", image_data: "" },
        { image_asset: "third.png", image_data: "" },
      ],
      mainReferenceIndex: 1,
      selectedMainSlot: 2,
    });
  });

  test("imports payload state and returns immutable mask, batch, and reference snapshots", () => {
    const controller = createImg2ImgController();
    controller.applyPayload({
      mode: "inpaint",
      profile: "sd15",
      image_asset: "source.png",
      mask_asset: "mask.png",
      mask_data: "data:image/png;base64,mask",
      batch_images: ["a.png", "", "b.png"],
      reference_images: [{ image_asset: "source.png" }, { image_asset: "ref.png" }],
      main_reference_index: 1,
    });

    const snapshot = controller.getSnapshot();
    snapshot.referenceSlots[0].image_asset = "mutated";
    snapshot.mask.data = "mutated";
    expect(controller.getSnapshot()).toMatchObject({
      mode: "inpaint",
      profileId: "sd15",
      batchImages: ["a.png", "b.png"],
      mask: { asset: "mask.png", data: "data:image/png;base64,mask" },
    });
    expect(controller.getReferencePayload().mainReferenceIndex).toBe(1);
  });

  test("keeps reference payload structure equivalent to the existing element helper", () => {
    const elements = {
      maxDirectReferences: { value: "3" },
      imageAsset: { value: "source.png" },
      imageData: { value: "" },
      referenceAsset2: { value: "" },
      referenceData2: { value: "" },
      referenceAsset3: { value: "third.png" },
      referenceData3: { value: "" },
      mainReferenceIndex: { value: "2" },
    };
    const expected = buildImageEditReferencePayloadFromElements(elements, 3);
    const controller = createImg2ImgController({ referenceLimit: 3 });
    controller.setReferenceSlots([
      { image_asset: elements.imageAsset.value, image_data: elements.imageData.value },
      { image_asset: elements.referenceAsset2.value, image_data: elements.referenceData2.value },
      { image_asset: elements.referenceAsset3.value, image_data: elements.referenceData3.value },
    ]);
    controller.setMainReferenceSlot(elements.mainReferenceIndex.value);
    expect(controller.getReferencePayload()).toEqual(expected);
  });

  test("rejects stale epochs and becomes inert after idempotent destroy", () => {
    const controller = createImg2ImgController();
    const epoch = controller.beginAsyncEpoch();
    expect(controller.isAsyncEpochCurrent(epoch)).toBe(true);
    controller.invalidateAsyncEpoch();
    expect(controller.isAsyncEpochCurrent(epoch)).toBe(false);
    controller.destroy();
    controller.destroy();
    expect(controller.isDestroyed()).toBe(true);
    expect(controller.isAsyncEpochCurrent(controller.beginAsyncEpoch())).toBe(false);
    expect(controller.setMode("batch")).toBe("img2img");
  });
});
