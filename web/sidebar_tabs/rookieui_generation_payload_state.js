export function parseJsonObjectField(rawValue, fallback = {}) {
  if (typeof rawValue !== "string" || !rawValue.trim()) {
    return { ...fallback };
  }
  try {
    const parsed = JSON.parse(rawValue);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : { ...fallback };
  } catch (_error) {
    return { ...fallback };
  }
}

export function parseStringArrayField(rawValue) {
  if (typeof rawValue !== "string" || !rawValue.trim()) {
    return [];
  }
  try {
    const parsed = JSON.parse(rawValue);
    return Array.isArray(parsed) ? parsed.filter((entry) => typeof entry === "string" && entry.trim()) : [];
  } catch (_error) {
    return [];
  }
}

export function parseJsonObjectArrayField(rawValue) {
  if (typeof rawValue !== "string" || !rawValue.trim()) {
    return [];
  }
  try {
    const parsed = JSON.parse(rawValue);
    return Array.isArray(parsed) ? parsed.filter((entry) => entry && typeof entry === "object") : [];
  } catch (_error) {
    return [];
  }
}

export function readOptionalNumericValue(input) {
  const rawValue = String(input?.value ?? "").trim();
  return rawValue ? Number(rawValue) : null;
}

export function buildTxt2ImgPayloadFromElements(elements) {
  return {
    prompt: elements.prompt.value,
    negative_prompt: elements.negativePrompt.value,
    profile: elements.profileState.value,
    dtype_profile: elements.lowBits.value,
    checkpoint_name: elements.checkpoint.value,
    vae_name: elements.vae.value,
    text_encoder_name: elements.textEncoder.value,
    width: Number(elements.width.value),
    height: Number(elements.height.value),
    steps: Number(elements.steps.value),
    cfg_scale: Number(elements.cfgScale.value),
    shift: readOptionalNumericValue(elements.shift),
    flux_guidance: readOptionalNumericValue(elements.fluxGuidance),
    sampler_name: elements.sampler.value,
    scheduler_name: elements.scheduler.value,
    prompt_enhancement_enabled: elements.promptEnhancementEnabled.checked,
    seed: Number(elements.seed.value),
    seed_extra: elements.seedExtra.checked,
    batch_size: Number(elements.batchSize.value),
    batch_count: Number(elements.batchCount.value),
    clip_skip: Number(elements.clipSkip.value),
    hires_enabled: elements.hiresEnabled.checked,
    hires_scale: Number(elements.hiresScale.value),
    hires_steps: Number(elements.hiresSteps.value),
    hires_denoise: Number(elements.hiresDenoise.value),
    hires_upscale_method: elements.hiresUpscaleMethod.value,
    template_lora_name: elements.templateLoraName.value,
    lora_name: elements.loraName.value,
    lora_strength_model: Number(elements.loraStrengthModel.value),
    lora_strength_clip: Number(elements.loraStrengthClip.value),
    adetailer: parseJsonObjectField(elements.adetailer?.value ?? "{}", {}),
    controlnet_units: parseJsonObjectArrayField(elements.controlnetUnits?.value ?? "[]"),
  };
}

export function buildImg2ImgPayloadFromElements(elements, imageEditReferencePayload = {}) {
  return {
    prompt: elements.prompt.value,
    negative_prompt: elements.negativePrompt.value,
    profile: elements.profileState.value,
    dtype_profile: elements.lowBits.value,
    checkpoint_name: elements.checkpoint.value,
    vae_name: elements.vae.value,
    text_encoder_name: elements.textEncoder.value,
    image_asset: elements.imageAsset.value,
    image_data: elements.imageData.value,
    mask_asset: elements.maskAsset.value,
    mask_data: elements.maskData.value,
    reference_images: imageEditReferencePayload.referenceImages ?? [],
    main_reference_index: imageEditReferencePayload.mainReferenceIndex ?? 0,
    mode: elements.mode.value,
    batch_images: parseStringArrayField(elements.batchImagesData?.value ?? "[]"),
    width: Number(elements.width.value),
    height: Number(elements.height.value),
    resize_mode: elements.resizeMode.value,
    steps: Number(elements.steps.value),
    cfg_scale: Number(elements.cfgScale.value),
    shift: readOptionalNumericValue(elements.shift),
    flux_guidance: readOptionalNumericValue(elements.fluxGuidance),
    edit_megapixels: readOptionalNumericValue(elements.editMegapixels),
    sampler_name: elements.sampler.value,
    scheduler_name: elements.scheduler.value,
    prompt_enhancement_enabled: elements.promptEnhancementEnabled.checked,
    seed: Number(elements.seed.value),
    seed_extra: elements.seedExtra.checked,
    batch_size: Number(elements.batchSize.value),
    clip_skip: Number(elements.clipSkip.value),
    denoise_strength: Number(elements.denoiseStrength.value),
    grow_mask_by: Number(elements.growMaskBy.value),
    mask_blur: Number(elements.maskBlur.value),
    inpaint_mask_mode: elements.inpaintMaskMode.value,
    inpaint_masked_content: elements.inpaintMaskedContent.value,
    inpaint_area: elements.inpaintArea.value,
    inpaint_padding: Number(elements.inpaintPadding.value),
    soft_inpainting_enabled: elements.softInpaintingEnabled.checked,
    soft_inpainting_schedule_bias: Number(elements.softInpaintingScheduleBias.value),
    soft_inpainting_preservation_strength: Number(elements.softInpaintingPreservationStrength.value),
    soft_inpainting_transition_contrast_boost: Number(elements.softInpaintingTransitionContrastBoost.value),
    soft_inpainting_mask_influence: Number(elements.softInpaintingMaskInfluence.value),
    soft_inpainting_difference_threshold: Number(elements.softInpaintingDifferenceThreshold.value),
    soft_inpainting_difference_contrast: Number(elements.softInpaintingDifferenceContrast.value),
    hires_enabled: elements.hiresEnabled.checked,
    hires_scale: Number(elements.hiresScale.value),
    hires_steps: Number(elements.hiresSteps.value),
    hires_denoise: Number(elements.hiresDenoise.value),
    hires_upscale_method: elements.hiresUpscaleMethod.value,
    template_lora_name: elements.templateLoraName.value,
    lora_name: elements.loraName.value,
    lora_strength_model: Number(elements.loraStrengthModel.value),
    lora_strength_clip: Number(elements.loraStrengthClip.value),
    adetailer: parseJsonObjectField(elements.adetailer?.value ?? "{}", {}),
    controlnet_units: parseJsonObjectArrayField(elements.controlnetUnits?.value ?? "[]"),
  };
}
