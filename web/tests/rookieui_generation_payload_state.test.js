import { describe, expect, test } from "vitest";

import {
  buildImg2ImgPayloadFromElements,
  buildTxt2ImgPayloadFromElements,
  parseJsonObjectArrayField,
  parseJsonObjectField,
  parseStringArrayField,
  readOptionalNumericValue,
} from "../sidebar_tabs/rookieui_generation_payload_state.js";

const input = (value) => ({ value });
const checkbox = (checked) => ({ checked });

function createTxt2ImgElements(overrides = {}) {
  return {
    prompt: input("a cinematic mountain"),
    negativePrompt: input("low quality"),
    profileState: input("flux2_dev"),
    lowBits: input("fp8"),
    checkpoint: input("model.safetensors"),
    vae: input("Automatic"),
    textEncoder: input("t5xxl_fp16.safetensors"),
    width: input("832"),
    height: input("1216"),
    steps: input("28"),
    cfgScale: input("3.5"),
    shift: input("3.1"),
    fluxGuidance: input(""),
    sampler: input("euler"),
    scheduler: input("normal"),
    promptEnhancementEnabled: checkbox(true),
    seed: input("-1"),
    seedExtra: checkbox(false),
    batchSize: input("2"),
    batchCount: input("3"),
    clipSkip: input("1"),
    hiresEnabled: checkbox(true),
    hiresScale: input("1.5"),
    hiresSteps: input("12"),
    hiresDenoise: input("0.35"),
    hiresUpscaleMethod: input("bislerp"),
    templateLoraName: input("official-lora.safetensors"),
    loraName: input("detail.safetensors"),
    loraStrengthModel: input("0.85"),
    loraStrengthClip: input("0.7"),
    adetailer: input('{"enabled":true}'),
    controlnetUnits: input('[{"enabled":true,"module":"canny"}]'),
    ...overrides,
  };
}

function createImg2ImgElements(overrides = {}) {
  return {
    ...createTxt2ImgElements({
      profileState: input("qwen_image_edit_2511"),
      lowBits: input("automatic"),
      checkpoint: input("qwen-image-edit.safetensors"),
      promptEnhancementEnabled: checkbox(false),
      hiresEnabled: checkbox(false),
    }),
    imageAsset: input("source.png"),
    imageData: input("data:image/png;base64,AAAA"),
    maskAsset: input("mask.png"),
    maskData: input("data:image/png;base64,BBBB"),
    mode: input("inpaint"),
    batchImagesData: input('["a.png","",17,"b.png"]'),
    resizeMode: input("crop_and_resize"),
    editMegapixels: input("1.5"),
    denoiseStrength: input("0.62"),
    growMaskBy: input("8"),
    maskBlur: input("4"),
    inpaintMaskMode: input("invert"),
    inpaintMaskedContent: input("latent_noise"),
    inpaintArea: input("only_masked"),
    inpaintPadding: input("32"),
    softInpaintingEnabled: checkbox(true),
    softInpaintingScheduleBias: input("0.1"),
    softInpaintingPreservationStrength: input("0.2"),
    softInpaintingTransitionContrastBoost: input("0.3"),
    softInpaintingMaskInfluence: input("0.4"),
    softInpaintingDifferenceThreshold: input("0.5"),
    softInpaintingDifferenceContrast: input("0.6"),
    ...overrides,
  };
}

describe("generation payload state helpers", () => {
  test("parses hidden JSON fields defensively", () => {
    expect(parseJsonObjectField('{"enabled":true}')).toEqual({ enabled: true });
    expect(parseJsonObjectField("[]", { fallback: true })).toEqual({ fallback: true });
    expect(parseJsonObjectField("{bad", { fallback: true })).toEqual({ fallback: true });
    expect(parseJsonObjectArrayField('[{"a":1}, null, "x", {"b":2}]')).toEqual([{ a: 1 }, { b: 2 }]);
    expect(parseJsonObjectArrayField("{}")).toEqual([]);
    expect(parseStringArrayField('["one", "", 2, "two"]')).toEqual(["one", "two"]);
  });

  test("keeps optional numeric fields nullable when blank", () => {
    expect(readOptionalNumericValue(input(""))).toBeNull();
    expect(readOptionalNumericValue(input("  "))).toBeNull();
    expect(readOptionalNumericValue(input("3.25"))).toBe(3.25);
  });

  test("builds txt2img payloads from DOM-like element snapshots", () => {
    const payload = buildTxt2ImgPayloadFromElements(createTxt2ImgElements());

    expect(payload).toMatchObject({
      prompt: "a cinematic mountain",
      negative_prompt: "low quality",
      profile: "flux2_dev",
      dtype_profile: "fp8",
      width: 832,
      height: 1216,
      steps: 28,
      cfg_scale: 3.5,
      shift: 3.1,
      flux_guidance: null,
      prompt_enhancement_enabled: true,
      batch_size: 2,
      batch_count: 3,
      hires_enabled: true,
      template_lora_name: "official-lora.safetensors",
      adetailer: { enabled: true },
      controlnet_units: [{ enabled: true, module: "canny" }],
    });
  });

  test("builds img2img payloads with reference and mode-specific fields", () => {
    const payload = buildImg2ImgPayloadFromElements(createImg2ImgElements(), {
      referenceImages: [{ image_asset: "ref.png" }],
      mainReferenceIndex: 1,
    });

    expect(payload).toMatchObject({
      prompt: "a cinematic mountain",
      profile: "qwen_image_edit_2511",
      image_asset: "source.png",
      image_data: "data:image/png;base64,AAAA",
      mask_asset: "mask.png",
      mask_data: "data:image/png;base64,BBBB",
      reference_images: [{ image_asset: "ref.png" }],
      main_reference_index: 1,
      mode: "inpaint",
      batch_images: ["a.png", "b.png"],
      resize_mode: "crop_and_resize",
      edit_megapixels: 1.5,
      denoise_strength: 0.62,
      grow_mask_by: 8,
      mask_blur: 4,
      inpaint_mask_mode: "invert",
      inpaint_masked_content: "latent_noise",
      inpaint_area: "only_masked",
      inpaint_padding: 32,
      soft_inpainting_enabled: true,
      soft_inpainting_schedule_bias: 0.1,
      soft_inpainting_preservation_strength: 0.2,
      soft_inpainting_transition_contrast_boost: 0.3,
      soft_inpainting_mask_influence: 0.4,
      soft_inpainting_difference_threshold: 0.5,
      soft_inpainting_difference_contrast: 0.6,
    });
  });
});
