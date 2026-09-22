export function applyQwen21EditSubmitControls(payload, elements) {
  if (payload.profile !== "qwen_image_21_edit") return payload;
  return {
    ...payload,
    dtype_profile: "automatic",
    template_lora_name: "",
    mask_asset: "",
    mask_data: "",
    reference_resolution: Number(elements.referenceResolution.value),
    output_size_mode: elements.outputSizeMode.value,
    edit_task: elements.editTask.value,
    batch_images: [],
    shift: null,
    flux_guidance: null,
    prompt_enhancement_enabled: false,
    batch_size: 1,
    denoise_strength: 1,
    hires_enabled: false,
    lora_name: "",
    adetailer: {},
    controlnet_units: [],
  };
}

export function parseImg2ImgBatchImages(rawValue, emitDebugWarning) {
  if (typeof rawValue !== "string" || !rawValue.trim()) return [];
  try {
    const parsed = JSON.parse(rawValue);
    return Array.isArray(parsed)
      ? parsed.filter((entry) => typeof entry === "string" && entry.trim()) : [];
  } catch (error) {
    emitDebugWarning("shell.img2img_batch_parse", "Failed to parse batch image JSON field; returning empty list.", error);
    return [];
  }
}
