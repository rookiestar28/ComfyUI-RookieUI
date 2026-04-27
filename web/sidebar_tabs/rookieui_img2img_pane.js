import {
  createControlNetUnitEditor,
  createADetailerEditor,
  createPromptWorkbenchShell,
  createXYZPlotShell,
} from "./rookieui_pane_deps.js";
import {
  CANVAS_FULLSCREEN_ACTIONS,
  CANVAS_ACTIONS,
  canCanvasStageOpenUpload,
  hasCanvasSourceImage,
  isCanvasElementFullscreen,
  resolveCanvasInteractionMode,
  toggleCanvasFullscreen,
} from "./rookieui_canvas_surface_contract.js";
import { createSourceCanvasBrushController } from "./rookieui_canvas_brush_deps.js";

function parseJsonObjectField(rawValue, fallback = {}) {
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

function parseStringArrayField(rawValue) {
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

function parseJsonObjectArrayField(rawValue) {
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

export function buildImg2ImgPane(parent, bootstrapState, formRegistry, context) {
  const {
    buildProfileLookup,
    buildPresetLookup,
    createGenerationRuntimeState,
    createSelect,
    createInput,
    createRangeInput,
    createTextarea,
    createCheckbox,
    createInlineCheckboxField,
    createField,
    createSliderField,
    createHiresFixSection,
    createSeedControlField,
    createPromptField,
    installExplicitFormSubmitShortcuts,
    createActionButton,
    createIconActionButton,
    createPreviewFullscreenViewer,
    buildQuicksettingCard,
    buildSelectionLibrary,
    buildSubtabShell,
    buildEmbeddingLibrary,
    buildLoraLibrary,
    bindSliderPair,
    appendTextElement,
    populateList,
    applyPayloadToElements,
    createList,
    appendPromptToken,
    transferPreviewToImg2Img,
    activateShellTab,
    updateFormFromPreset,
    syncFamilyAwareModuleQuicksetting,
    syncFamilyAwareAdvancedParameterFields,
    syncClipSkipAvailability,
    syncMaskField,
    resolveImg2ImgExecutionMode,
    isImg2ImgBatchMode,
    parseJsonArrayField,
    createImg2ImgMaskCanvasContract,
    createImg2ImgMaskEditor,
    createImg2ImgModeRouter,
    emitFrontendDebugWarning,
    submitImg2Img,
    readFileAsDataUrl,
    setPreviewContent,
    installPaneStateLock,
    findPresetIdForProfile,
    setElementValue,
    syncBoundControls,
  } = context;
  const section = document.createElement("section");
  section.className = "rookieui-shell__integrated-pane";
  parent.appendChild(section);

  const form = document.createElement("form");
  form.className = "rookieui-shell__form rookieui-shell__integrated-form";
  form.id = "rookieui-img2img-form";
  section.appendChild(form);
  installExplicitFormSubmitShortcuts(form);

  const profileLookup = buildProfileLookup(bootstrapState.capabilities);
  const rawPresets = bootstrapState.presets?.presets ?? [];
  const presetLookup = buildPresetLookup(rawPresets);
  const retiredVisibleImg2ImgPresetIds = new Set(["qwen_image_edit_multi_lora"]);
  const filterPresetsForSurfaceFlow = (surfaceFlow) =>
    rawPresets.filter((preset) => {
      const profile = profileLookup.get(String(preset?.profile ?? "").trim().toLowerCase()) ?? profileLookup.get(preset?.profile);
      if (!profile) {
        return false;
      }
      const availableSurfaceFlows = Array.isArray(profile?.available_surface_flows)
        ? profile.available_surface_flows
        : [];
      if (!availableSurfaceFlows.includes(surfaceFlow)) {
        return false;
      }
      // CRITICAL: keep retired image-edit presets backend-compatible while removing them from the visible img2img dropdown.
      return surfaceFlow !== "img2img" || !retiredVisibleImg2ImgPresetIds.has(String(preset?.id ?? "").trim());
    });
  const img2imgVisiblePresets = filterPresetsForSurfaceFlow("img2img");
  const resolveVisiblePresetsForMode = () => (img2imgVisiblePresets.length > 0 ? img2imgVisiblePresets : rawPresets);
  const profiles = bootstrapState.capabilities.parity?.profiles ?? [];
  const inventory = bootstrapState.models ?? {
    checkpoints: ["__host_default__"],
    vae: ["Automatic"],
    text_encoders: ["Automatic"],
    embeddings: [],
    loras: [],
    default_checkpoint: "__host_default__",
    default_vae: "Automatic",
    default_text_encoder: "Automatic",
  };
  const controlnetCatalog = bootstrapState.controlnetCatalog ?? {};
  const adetailerCatalog = bootstrapState.adetailerCatalog ?? {};
  const controlnetModelValues =
    Array.isArray(controlnetCatalog.model_list) && controlnetCatalog.model_list.length > 0
      ? controlnetCatalog.model_list
      : inventory.controlnet ?? [];
  const adetailerCheckpointChoices = Array.from(
    new Set(
      [
        ...(Array.isArray(adetailerCatalog.checkpoint_choices) ? adetailerCatalog.checkpoint_choices : []),
        ...(Array.isArray(inventory.checkpoints) ? inventory.checkpoints : []),
        ...(Array.isArray(inventory.diffusion_models) ? inventory.diffusion_models : []),
      ]
        .map((value) => String(value ?? "").trim())
        .filter(Boolean),
    ),
  );
  const mergedADetailerCatalog = {
    ...adetailerCatalog,
    // IMPORTANT: ADetailer-local ControlNet must fall back to the primary ControlNet catalog when the dedicated payload is stale or partial.
    controlnet_model_list:
      Array.isArray(adetailerCatalog.controlnet_model_list) && adetailerCatalog.controlnet_model_list.length > 0
        ? adetailerCatalog.controlnet_model_list
        : controlnetModelValues,
    controlnet_module_list:
      Array.isArray(adetailerCatalog.controlnet_module_list) && adetailerCatalog.controlnet_module_list.length > 0
        ? adetailerCatalog.controlnet_module_list
        : Array.isArray(controlnetCatalog.module_list) && controlnetCatalog.module_list.length > 0
          ? controlnetCatalog.module_list
          : ["none"],
    checkpoint_choices: adetailerCheckpointChoices,
  };
  const controlnetTypeCatalog =
    controlnetCatalog.control_types && typeof controlnetCatalog.control_types === "object"
      ? controlnetCatalog.control_types
      : {};
  const controlnetTypeOrder = Array.isArray(controlnetCatalog.control_type_order)
    ? controlnetCatalog.control_type_order
    : undefined;
  const presetOptions = resolveVisiblePresetsForMode("img2img").map((preset) => ({
    value: preset.id,
    label: preset.title,
  }));
  const allPresets = rawPresets;
  const initialPreset = presetOptions[0]?.value ?? "sd15";
  const initialProfile = profiles[0]?.id ?? "sd15";
  const dtypeProfiles = bootstrapState.compatibility?.dtype_profiles ?? [
    { id: "automatic", title: "Automatic", default: true },
  ];
  const samplerCatalog = bootstrapState.compatibility?.samplers ?? [
    { id: "euler_ancestral", title: "Euler a", default: true },
  ];
  const schedulerCatalog = bootstrapState.compatibility?.schedulers ?? [
    { id: "normal", title: "Normal", default: true },
  ];
  const initialLowBits = dtypeProfiles.find((entry) => entry.default)?.id ?? dtypeProfiles[0]?.id ?? "automatic";
  const initialSampler = samplerCatalog.find((entry) => entry.default)?.id ?? samplerCatalog[0]?.id ?? "euler_ancestral";
  const initialScheduler =
    schedulerCatalog.find((entry) => entry.default)?.id ?? schedulerCatalog[0]?.id ?? "normal";
  const runtimeState = createGenerationRuntimeState({
    previewPlaceholder: "Generation preview will update while the job is running.",
  });
  let img2imgPreviewBox = null;
  const img2imgModeUi = {
    modeHintNode: null,
    referenceSection: null,
    referenceHintNode: null,
    referenceSlots: [],
    maskDropzone: null,
    maskFileInput: null,
    batchPane: null,
    batchFileInput: null,
    batchStatusNode: null,
    maskEditor: null,
    modeButtons: new Map(),
  };
  let refreshSourceCanvasSurface = null;
  let img2imgControlNetEditor = null;
  let img2imgADetailerEditor = null;

  const elements = {
    prompt: createTextarea("rookieui-img2img-prompt", "", 4, {
      className: "rookieui-shell__textarea rookieui-shell__textarea--prompt",
    }),
    negativePrompt: createTextarea("rookieui-img2img-negative-prompt", "", 3, {
      className: "rookieui-shell__textarea rookieui-shell__textarea--negative",
    }),
    preset: createSelect("rookieui-img2img-preset", presetOptions, initialPreset),
    profileState: createSelect(
      "rookieui-img2img-profile",
      profiles.map((profile) => ({ value: profile.id, label: profile.title })),
      initialProfile,
    ),
    mode: createSelect(
      "rookieui-img2img-mode",
      [
        { value: "img2img", label: "Img2Img" },
        { value: "sketch", label: "Sketch" },
        { value: "inpaint", label: "Inpaint" },
        { value: "inpaint_sketch", label: "Inpaint Sketch" },
        { value: "inpaint_upload", label: "Inpaint Upload" },
        { value: "batch", label: "Batch" },
      ],
      "img2img",
    ),
    width: createInput("number", "rookieui-img2img-width", "512", { step: 8, min: 64, max: 2048 }),
    widthSlider: createRangeInput("rookieui-img2img-width-slider", "512", { step: 8, min: 64, max: 2048 }),
    height: createInput("number", "rookieui-img2img-height", "512", { step: 8, min: 64, max: 2048 }),
    heightSlider: createRangeInput("rookieui-img2img-height-slider", "512", { step: 8, min: 64, max: 2048 }),
    resizeMode: createSelect(
      "rookieui-img2img-resize-mode",
      [
        { value: "just_resize", label: "Just resize" },
        { value: "crop_and_resize", label: "Crop and resize" },
        { value: "resize_and_fill", label: "Resize and fill" },
        { value: "latent_upscale", label: "Just resize (latent upscale)" },
      ],
      "crop_and_resize",
    ),
    checkpoint: createSelect(
      "rookieui-img2img-checkpoint",
      inventory.checkpoints.map((value) => ({ value, label: value })),
      inventory.default_checkpoint,
    ),
    vae: createSelect(
      "rookieui-img2img-vae",
      inventory.vae.map((value) => ({ value, label: value })),
      inventory.default_vae,
    ),
    textEncoder: createSelect(
      "rookieui-img2img-text-encoder",
      inventory.text_encoders.map((value) => ({ value, label: value })),
      inventory.default_text_encoder,
    ),
    lowBits: createSelect(
      "rookieui-img2img-low-bits",
      dtypeProfiles.map((profile) => ({ value: profile.id, label: profile.title })),
      initialLowBits,
    ),
    templateLoraName: createInput("text", "rookieui-img2img-template-lora-name", ""),
    loraName: createInput("text", "rookieui-img2img-lora-name", ""),
    loraStrengthModel: createInput("number", "rookieui-img2img-lora-strength-model", "1", {
      step: 0.05,
      min: -4,
      max: 4,
      inputMode: "decimal",
    }),
    loraStrengthClip: createInput("number", "rookieui-img2img-lora-strength-clip", "1", {
      step: 0.05,
      min: -4,
      max: 4,
      inputMode: "decimal",
    }),
    imageAsset: createInput("text", "rookieui-image-asset", ""),
    imageData: createInput("hidden", "rookieui-image-data", ""),
    maskAsset: createInput("text", "rookieui-mask-asset", ""),
    maskData: createInput("hidden", "rookieui-mask-data", ""),
    imageEditProfile: createInput("hidden", "rookieui-img2img-image-edit-profile", "false"),
    maxDirectReferences: createInput("hidden", "rookieui-img2img-max-direct-references", "0"),
    mainReferenceIndex: createInput("hidden", "rookieui-img2img-main-reference-index", "0"),
    referenceAsset2: createInput("text", "rookieui-img2img-reference-asset-2", ""),
    referenceData2: createInput("hidden", "rookieui-img2img-reference-data-2", ""),
    referenceAsset3: createInput("text", "rookieui-img2img-reference-asset-3", ""),
    referenceData3: createInput("hidden", "rookieui-img2img-reference-data-3", ""),
    batchImagesData: createInput("hidden", "rookieui-img2img-batch-images-data", "[]"),
    steps: createInput("number", "rookieui-img2img-steps", "28", { step: 1, min: 1, max: 150 }),
    stepsSlider: createRangeInput("rookieui-img2img-steps-slider", "28", { step: 1, min: 1, max: 150 }),
    cfgScale: createInput("number", "rookieui-img2img-cfg-scale", "7", {
      step: 0.01,
      min: 1,
      max: 30,
      inputMode: "decimal",
    }),
    cfgScaleSlider: createRangeInput("rookieui-img2img-cfg-scale-slider", "7", { step: 0.1, min: 1, max: 30 }),
    shift: createInput("number", "rookieui-img2img-shift", "", {
      step: 0.1,
      min: 0,
      max: 20,
      inputMode: "decimal",
    }),
    fluxGuidance: createInput("number", "rookieui-img2img-flux-guidance", "", {
      step: 0.1,
      min: 0,
      max: 20,
      inputMode: "decimal",
    }),
    editMegapixels: createInput("number", "rookieui-img2img-edit-megapixels", "", {
      step: 0.05,
      min: 0.25,
      max: 8,
      inputMode: "decimal",
    }),
    sampler: createSelect(
      "rookieui-img2img-sampler",
      samplerCatalog.map((entry) => ({ value: entry.id, label: entry.title })),
      initialSampler,
    ),
    scheduler: createSelect(
      "rookieui-img2img-scheduler",
      schedulerCatalog.map((entry) => ({ value: entry.id, label: entry.title })),
      initialScheduler,
    ),
    promptEnhancementEnabled: createCheckbox("rookieui-img2img-prompt-enhancement-enabled", false),
    seed: createInput("number", "rookieui-img2img-seed", "-1", { step: 1 }),
    seedExtra: createCheckbox("rookieui-img2img-seed-extra", false),
    batchSize: createInput("number", "rookieui-img2img-batch-size", "1", { step: 1, min: 1, max: 8 }),
    batchSizeSlider: createRangeInput("rookieui-img2img-batch-size-slider", "1", { step: 1, min: 1, max: 8 }),
    clipSkip: createInput("number", "rookieui-img2img-clip-skip", "1", { step: 1, min: 1, max: 12 }),
    clipSkipSlider: createRangeInput("rookieui-img2img-clip-skip-slider", "1", { step: 1, min: 1, max: 12 }),
    denoiseStrength: createInput("number", "rookieui-denoise-strength", "0.75", {
      step: 0.01,
      min: 0,
      max: 1,
      inputMode: "decimal",
    }),
    denoiseStrengthSlider: createRangeInput("rookieui-denoise-strength-slider", "0.75", {
      step: 0.05,
      min: 0,
      max: 1,
    }),
    growMaskBy: createInput("number", "rookieui-grow-mask-by", "6", { step: 1, min: 0, max: 64 }),
    growMaskBySlider: createRangeInput("rookieui-grow-mask-by-slider", "6", { step: 1, min: 0, max: 64 }),
    maskBlur: createInput("number", "rookieui-mask-blur", "4", { step: 1, min: 0, max: 64 }),
    maskBlurSlider: createRangeInput("rookieui-mask-blur-slider", "4", { step: 1, min: 0, max: 64 }),
    inpaintMaskMode: createSelect(
      "rookieui-img2img-mask-mode",
      [
        { value: "inpaint_masked", label: "Inpaint masked" },
        { value: "inpaint_not_masked", label: "Inpaint not masked" },
      ],
      "inpaint_masked",
    ),
    inpaintMaskedContent: createSelect(
      "rookieui-img2img-masked-content",
      [
        { value: "fill", label: "Fill" },
        { value: "original", label: "Original" },
        { value: "latent_noise", label: "Latent noise" },
        { value: "latent_nothing", label: "Latent nothing" },
      ],
      "original",
    ),
    inpaintArea: createSelect(
      "rookieui-img2img-inpaint-area",
      [
        { value: "whole_picture", label: "Whole picture" },
        { value: "only_masked", label: "Only masked" },
      ],
      "only_masked",
    ),
    inpaintPadding: createInput("number", "rookieui-img2img-inpaint-padding", "32", { step: 1, min: 0, max: 256 }),
    inpaintPaddingSlider: createRangeInput("rookieui-img2img-inpaint-padding-slider", "32", { step: 1, min: 0, max: 256 }),
    softInpaintingEnabled: createCheckbox("rookieui-img2img-soft-inpainting-enabled", false),
    softInpaintingScheduleBias: createInput("number", "rookieui-img2img-soft-schedule-bias", "1", {
      step: 0.01,
      min: 0,
      max: 8,
      inputMode: "decimal",
    }),
    softInpaintingScheduleBiasSlider: createRangeInput("rookieui-img2img-soft-schedule-bias-slider", "1", { step: 0.1, min: 0, max: 8 }),
    softInpaintingPreservationStrength: createInput("number", "rookieui-img2img-soft-preservation-strength", "0.5", {
      step: 0.01,
      min: 0,
      max: 8,
      inputMode: "decimal",
    }),
    softInpaintingPreservationStrengthSlider: createRangeInput("rookieui-img2img-soft-preservation-strength-slider", "0.5", {
      step: 0.1,
      min: 0,
      max: 8,
    }),
    softInpaintingTransitionContrastBoost: createInput("number", "rookieui-img2img-soft-transition-contrast-boost", "4", {
      step: 0.01,
      min: 1,
      max: 32,
      inputMode: "decimal",
    }),
    softInpaintingTransitionContrastBoostSlider: createRangeInput("rookieui-img2img-soft-transition-contrast-boost-slider", "4", {
      step: 0.1,
      min: 1,
      max: 32,
    }),
    softInpaintingMaskInfluence: createInput("number", "rookieui-img2img-soft-mask-influence", "0", {
      step: 0.01,
      min: 0,
      max: 1,
      inputMode: "decimal",
    }),
    softInpaintingMaskInfluenceSlider: createRangeInput("rookieui-img2img-soft-mask-influence-slider", "0", { step: 0.01, min: 0, max: 1 }),
    softInpaintingDifferenceThreshold: createInput("number", "rookieui-img2img-soft-difference-threshold", "0.5", {
      step: 0.01,
      min: 0,
      max: 8,
      inputMode: "decimal",
    }),
    softInpaintingDifferenceThresholdSlider: createRangeInput("rookieui-img2img-soft-difference-threshold-slider", "0.5", {
      step: 0.1,
      min: 0,
      max: 8,
    }),
    softInpaintingDifferenceContrast: createInput("number", "rookieui-img2img-soft-difference-contrast", "2", {
      step: 0.01,
      min: 0,
      max: 8,
      inputMode: "decimal",
    }),
    softInpaintingDifferenceContrastSlider: createRangeInput("rookieui-img2img-soft-difference-contrast-slider", "2", {
      step: 0.1,
      min: 0,
      max: 8,
    }),
    hiresEnabled: createCheckbox("rookieui-img2img-hires-enabled", false),
    hiresScale: createInput("number", "rookieui-img2img-hires-scale", "1.5", {
      step: 0.01,
      min: 1,
      max: 2.5,
      inputMode: "decimal",
    }),
    hiresSteps: createInput("number", "rookieui-img2img-hires-steps", "14", { step: 1, min: 1, max: 150 }),
    hiresDenoise: createInput("number", "rookieui-img2img-hires-denoise", "0.35", {
      step: 0.01,
      min: 0.1,
      max: 1,
      inputMode: "decimal",
    }),
    hiresScaleSlider: createRangeInput("rookieui-img2img-hires-scale-slider", "1.5", { step: 0.1, min: 1, max: 2.5 }),
    hiresStepsSlider: createRangeInput("rookieui-img2img-hires-steps-slider", "14", { step: 1, min: 1, max: 150 }),
    hiresDenoiseSlider: createRangeInput("rookieui-img2img-hires-denoise-slider", "0.35", {
      step: 0.05,
      min: 0.1,
      max: 1,
    }),
    hiresUpscaleMethod: createSelect(
      "rookieui-img2img-hires-upscale-method",
      [
        { value: "bislerp", label: "Bislerp" },
        { value: "bicubic", label: "Bicubic" },
        { value: "bilinear", label: "Bilinear" },
        { value: "nearest-exact", label: "Nearest Exact" },
        { value: "area", label: "Area" },
      ],
      "bislerp",
    ),
    adetailer: createInput("hidden", "rookieui-img2img-adetailer", "{}"),
    controlnetUnits: createInput("hidden", "rookieui-img2img-controlnet-units", "[]"),
  };
  form.appendChild(elements.adetailer);
  form.appendChild(elements.controlnetUnits);
  bindSliderPair(elements.width, elements.widthSlider);
  bindSliderPair(elements.height, elements.heightSlider);
  bindSliderPair(elements.steps, elements.stepsSlider);
  bindSliderPair(elements.cfgScale, elements.cfgScaleSlider);
  bindSliderPair(elements.batchSize, elements.batchSizeSlider);
  bindSliderPair(elements.clipSkip, elements.clipSkipSlider);
  bindSliderPair(elements.denoiseStrength, elements.denoiseStrengthSlider);
  bindSliderPair(elements.growMaskBy, elements.growMaskBySlider);
  bindSliderPair(elements.maskBlur, elements.maskBlurSlider);
  bindSliderPair(elements.inpaintPadding, elements.inpaintPaddingSlider);
  bindSliderPair(elements.softInpaintingScheduleBias, elements.softInpaintingScheduleBiasSlider);
  bindSliderPair(elements.softInpaintingPreservationStrength, elements.softInpaintingPreservationStrengthSlider);
  bindSliderPair(elements.softInpaintingTransitionContrastBoost, elements.softInpaintingTransitionContrastBoostSlider);
  bindSliderPair(elements.softInpaintingMaskInfluence, elements.softInpaintingMaskInfluenceSlider);
  bindSliderPair(elements.softInpaintingDifferenceThreshold, elements.softInpaintingDifferenceThresholdSlider);
  bindSliderPair(elements.softInpaintingDifferenceContrast, elements.softInpaintingDifferenceContrastSlider);
  bindSliderPair(elements.hiresScale, elements.hiresScaleSlider);
  bindSliderPair(elements.hiresSteps, elements.hiresStepsSlider);
  bindSliderPair(elements.hiresDenoise, elements.hiresDenoiseSlider);
  elements.prompt.placeholder = "Prompt\n(Ctrl+Enter to Generate ; Alt+Enter to Skip ; Esc to Interrupt)";
  elements.negativePrompt.placeholder =
    "Negative Prompt\n(Ctrl+Enter to Generate ; Alt+Enter to Skip ; Esc to Interrupt)";
  elements.imageAsset.placeholder = "required";
  elements.maskAsset.placeholder = "optional";
  const readOptionalNumeric = (input) => {
    const rawValue = String(input?.value ?? "").trim();
    return rawValue ? Number(rawValue) : null;
  };
  const advancedParameterControls = {
    shiftField: null,
    shiftInput: elements.shift,
    fluxGuidanceField: null,
    fluxGuidanceInput: elements.fluxGuidance,
    promptEnhancementField: null,
    promptEnhancementInput: elements.promptEnhancementEnabled,
    editMegapixelsField: null,
    editMegapixelsInput: elements.editMegapixels,
  };
  const modeAwareFieldControls = {
    widthField: null,
    heightField: null,
    resizeModeField: null,
    denoiseField: null,
    growMaskField: null,
    batchSizeField: null,
    clipSkipField: null,
    hiresSection: null,
  };
  const templateLoraControls = {
    field: null,
    statusNode: null,
    resetButton: null,
    libraryHeading: null,
    libraryHost: null,
  };
  const getActiveProfile = () =>
    profileLookup.get(String(elements.profileState.value ?? "").trim().toLowerCase()) ??
    profileLookup.get(elements.profileState.value) ??
    null;
  const buildImageEditReferencePayload = (referenceLimit = null) => {
    const resolvedLimit = Math.max(0, Number(referenceLimit ?? elements.maxDirectReferences?.value ?? 0) || 0);
    if (resolvedLimit <= 0) {
      return {
        referenceImages: [],
        mainReferenceIndex: 0,
        selectedMainSlot: 0,
      };
    }
    const normalizedLimit = Math.max(1, resolvedLimit);
    const orderedSlots = [
      {
        image_asset: String(elements.imageAsset?.value ?? "").trim(),
        image_data: String(elements.imageData?.value ?? "").trim(),
      },
      {
        image_asset: String(elements.referenceAsset2?.value ?? "").trim(),
        image_data: String(elements.referenceData2?.value ?? "").trim(),
      },
      {
        image_asset: String(elements.referenceAsset3?.value ?? "").trim(),
        image_data: String(elements.referenceData3?.value ?? "").trim(),
      },
    ].slice(0, normalizedLimit);
    const selectedMainSlot = Math.min(
      Math.max(0, Number(elements.mainReferenceIndex?.value ?? 0) || 0),
      Math.max(0, normalizedLimit - 1),
    );
    const referenceImages = [];
    let mainReferenceIndex = -1;
    orderedSlots.forEach((entry, slotIndex) => {
      if (!entry.image_asset && !entry.image_data) {
        return;
      }
      if (slotIndex === selectedMainSlot) {
        mainReferenceIndex = referenceImages.length;
      }
      referenceImages.push(entry);
    });
    return {
      referenceImages,
      mainReferenceIndex,
      selectedMainSlot,
    };
  };
  const syncImageEditProfileState = () => {
    const activeProfile = getActiveProfile();
    const imageEditProfile = Boolean(activeProfile?.image_edit_profile);
    const referenceLimit = imageEditProfile ? Math.max(1, Number(activeProfile?.max_direct_references ?? 0) || 0) : 0;
    elements.imageEditProfile.value = imageEditProfile ? "true" : "false";
    elements.maxDirectReferences.value = String(referenceLimit);
    const normalizedMainSlot = Math.min(
      Math.max(0, Number(elements.mainReferenceIndex.value ?? 0) || 0),
      Math.max(0, referenceLimit - 1),
    );
    elements.mainReferenceIndex.value = String(normalizedMainSlot);
    return {
      activeProfile,
      imageEditProfile,
      referenceLimit,
      normalizedMainSlot,
    };
  };

  const buildXYZBaseRequest = () => {
    const imageEditReferencePayload = buildImageEditReferencePayload();
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
    reference_images: imageEditReferencePayload.referenceImages,
    main_reference_index: imageEditReferencePayload.mainReferenceIndex,
    mode: elements.mode.value,
    batch_images: parseStringArrayField(elements.batchImagesData?.value ?? "[]"),
    width: Number(elements.width.value),
    height: Number(elements.height.value),
    resize_mode: elements.resizeMode.value,
    steps: Number(elements.steps.value),
    cfg_scale: Number(elements.cfgScale.value),
    shift: readOptionalNumeric(elements.shift),
    flux_guidance: readOptionalNumeric(elements.fluxGuidance),
    edit_megapixels: readOptionalNumeric(elements.editMegapixels),
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
  };

  const quicksettings = document.createElement("div");
  quicksettings.className = "rookieui-shell__quicksettings";
  quicksettings.id = "rookieui-img2img-quicksettings";
  form.appendChild(quicksettings);
  buildQuicksettingCard(quicksettings, "UI Preset", elements.preset, "rookieui-img2img-preset-quicksetting");
  buildQuicksettingCard(
    quicksettings,
    "Checkpoint",
    elements.checkpoint,
    "rookieui-img2img-checkpoint-quicksetting",
  );
  const modulesQuicksetting = buildQuicksettingCard(
    quicksettings,
    "VAE / Text Encoder",
    [elements.vae, elements.textEncoder],
    "rookieui-img2img-modules-quicksetting",
  );
  const modulesQuicksettingLabel = modulesQuicksetting.querySelector(".rookieui-shell__quicksetting-label");
  buildQuicksettingCard(
    quicksettings,
    "Diffusion in Low Bits",
    elements.lowBits,
    "rookieui-img2img-low-bits-quicksetting",
  );

  const promptBand = document.createElement("div");
  promptBand.className = "rookieui-shell__prompt-band";
  form.appendChild(promptBand);

  const promptStack = document.createElement("div");
  promptStack.className = "rookieui-shell__prompt-stack";
  promptBand.appendChild(promptStack);
  createPromptField(promptStack, "Prompt", elements.prompt, "rookieui-img2img-prompt-counter");
  createPromptWorkbenchShell({
    idPrefix: "rookieui-img2img-workbench",
    parent: promptStack,
    bootstrapState,
    promptInput: elements.prompt,
    negativePromptInput: elements.negativePrompt,
    namespaces: {
      prompt: "img2img_prompt",
      negative: "img2img_negative",
    },
    appendTextElement,
    createActionButton,
    fixedScope: "prompt",
    onStatusMessage: (message) => {
      statusNode.textContent = message;
    },
  });
  createPromptField(
    promptStack,
    "Negative Prompt",
    elements.negativePrompt,
    "rookieui-img2img-negative-prompt-counter",
  );
  createPromptWorkbenchShell({
    idPrefix: "rookieui-img2img-negative-workbench",
    parent: promptStack,
    bootstrapState,
    promptInput: elements.prompt,
    negativePromptInput: elements.negativePrompt,
    namespaces: {
      prompt: "img2img_prompt",
      negative: "img2img_negative",
    },
    appendTextElement,
    createActionButton,
    fixedScope: "negative",
    onStatusMessage: (message) => {
      statusNode.textContent = message;
    },
  });

  const actionRail = document.createElement("div");
  actionRail.className = "rookieui-shell__action-rail";
  promptBand.appendChild(actionRail);

  const submitButton = document.createElement("button");
  submitButton.id = "rookieui-img2img-submit";
  submitButton.className = "rookieui-shell__button rookieui-shell__button--hero";
  submitButton.type = "submit";
  submitButton.textContent = "Generate";
  actionRail.appendChild(submitButton);

  const actionRow = document.createElement("div");
  actionRow.className = "rookieui-shell__mini-actions";
  actionRail.appendChild(actionRow);

  const queueIconButton = createIconActionButton(
    "rookieui-img2img-open-queue-icon",
    "pi-check-square",
    "Open Queue",
    "queue",
  );
  queueIconButton.addEventListener("click", () => {
    activateShellTab(formRegistry, "queue", statusNode, "Opened queue view");
  });
  actionRow.appendChild(queueIconButton);

  const clearButton = createIconActionButton("rookieui-img2img-clear", "pi-trash", "Clear Prompt Fields", "danger");
  clearButton.addEventListener("click", () => {
    elements.prompt.value = "";
    elements.negativePrompt.value = "";
    syncBoundControls([elements.prompt, elements.negativePrompt]);
    statusNode.textContent = "Cleared prompt fields";
  });
  actionRow.appendChild(clearButton);

  const pngInfoButton = createIconActionButton("rookieui-img2img-open-pnginfo", "pi-file", "Open PNG Info", "metadata");
  pngInfoButton.addEventListener("click", () => {
    activateShellTab(formRegistry, "pnginfo", statusNode, "Opened PNG Info");
  });
  actionRow.appendChild(pngInfoButton);

  const actionTargetRow = document.createElement("div");
  actionTargetRow.className = "rookieui-shell__action-target-row";
  actionRail.appendChild(actionTargetRow);

  const actionTarget = createSelect(
    "rookieui-img2img-action-target",
    [
      { value: "queue", label: "Queue / History" },
      { value: "pnginfo", label: "PNG Info" },
      { value: "txt2img", label: "Send to Txt2Img" },
      { value: "extras", label: "Extras" },
    ],
    "queue",
  );
  actionTarget.classList.add("rookieui-shell__action-target");
  actionTargetRow.appendChild(actionTarget);

  const actionApplyButton = createIconActionButton(
    "rookieui-img2img-apply-action-target",
    "pi-pencil",
    "Apply Action",
    "transfer",
  );
  actionApplyButton.addEventListener("click", () => {
    const actionLabels = {
      queue: "Opened queue view",
      pnginfo: "Opened PNG Info",
      txt2img: "Opened Txt2Img",
      extras: "Opened Extras",
    };
    activateShellTab(formRegistry, actionTarget.value, statusNode, actionLabels[actionTarget.value] ?? "Action applied");
  });
  actionTargetRow.appendChild(actionApplyButton);

  const statusNode = document.createElement("p");
  statusNode.id = "rookieui-img2img-status";
  statusNode.className = "rookieui-shell__status rookieui-shell__status--inline";
  statusNode.textContent = "Idle";
  actionRail.appendChild(statusNode);

  const img2imgMaskCanvasContract = createImg2ImgMaskCanvasContract({
    modeInput: elements.mode,
    imageDataInput: elements.imageData,
    imageAssetInput: elements.imageAsset,
    maskDataInput: elements.maskData,
    maskAssetInput: elements.maskAsset,
    resolveExecutionMode: resolveImg2ImgExecutionMode,
    syncBoundControls,
  });

  updateFormFromPreset(presetLookup, initialPreset, elements, profileLookup, bootstrapState.models);
  syncFamilyAwareModuleQuicksetting(
    profileLookup,
    elements.profileState.value,
    modulesQuicksetting,
    modulesQuicksettingLabel,
    elements.textEncoder,
  );
  syncFamilyAwareAdvancedParameterFields(profileLookup, elements.profileState.value, advancedParameterControls);
  const inpaintModeControls = [
    elements.maskBlur,
    elements.maskBlurSlider,
    elements.inpaintMaskMode,
    elements.inpaintMaskedContent,
    elements.inpaintArea,
    elements.inpaintPadding,
    elements.inpaintPaddingSlider,
    elements.softInpaintingEnabled,
    elements.softInpaintingScheduleBias,
    elements.softInpaintingScheduleBiasSlider,
    elements.softInpaintingPreservationStrength,
    elements.softInpaintingPreservationStrengthSlider,
    elements.softInpaintingTransitionContrastBoost,
    elements.softInpaintingTransitionContrastBoostSlider,
    elements.softInpaintingMaskInfluence,
    elements.softInpaintingMaskInfluenceSlider,
    elements.softInpaintingDifferenceThreshold,
    elements.softInpaintingDifferenceThresholdSlider,
    elements.softInpaintingDifferenceContrast,
    elements.softInpaintingDifferenceContrastSlider,
  ];
  let img2imgModeRouter = null;
  const setFieldVisibility = (fieldNode, visible) => {
    if (!fieldNode) {
      return;
    }
    fieldNode.hidden = !visible;
    fieldNode.querySelectorAll("input, select, textarea, button").forEach((control) => {
      control.disabled = !visible;
    });
  };
  const resolvePresetTemplateLoraDefault = () =>
    String(presetLookup.get(elements.preset.value)?.template_lora_name ?? "").trim();
  const resolveTemplateLoraOfficialLabel = () =>
    String(profileLookup.get(elements.profileState.value)?.official_template_lora_label ?? "").trim();
  const syncTemplateLoraControls = () => {
    const profile = profileLookup.get(String(elements.profileState.value ?? "").trim().toLowerCase()) ?? null;
    const visible = Boolean(profile?.template_lora_visible);
    const overrideAllowed = Boolean(profile?.template_lora_override_allowed);
    const currentValue = String(elements.templateLoraName.value ?? "").trim();
    const presetDefault = resolvePresetTemplateLoraDefault();
    const officialLabel = resolveTemplateLoraOfficialLabel();
    const officialResolved = presetDefault || officialLabel;
    setFieldVisibility(templateLoraControls.field, visible);
    if (templateLoraControls.libraryHeading) {
      templateLoraControls.libraryHeading.hidden = !visible;
    }
    if (templateLoraControls.libraryHost) {
      templateLoraControls.libraryHost.hidden = !visible;
      templateLoraControls.libraryHost.querySelectorAll("button").forEach((button) => {
        button.disabled = !visible || !overrideAllowed;
      });
    }
    if (templateLoraControls.statusNode) {
      templateLoraControls.statusNode.hidden = !visible;
    }
    if (templateLoraControls.resetButton) {
      templateLoraControls.resetButton.hidden = !visible;
      templateLoraControls.resetButton.disabled = !visible || !overrideAllowed;
    }
    elements.templateLoraName.disabled = !visible || !overrideAllowed;
    if (!visible || !templateLoraControls.statusNode) {
      return;
    }
    if (!currentValue && !officialResolved) {
      templateLoraControls.statusNode.textContent = "No template-owned LoRA is required for this preset.";
      return;
    }
    if (!officialResolved) {
      templateLoraControls.statusNode.textContent = `Official template LoRA '${officialLabel || "template-owned LoRA"}' is not available on the current host. Generation can continue; to add a LoRA manually, use <lora:model_name:1> in the prompt.`;
      return;
    }
    if (!currentValue || currentValue === presetDefault) {
      templateLoraControls.statusNode.textContent = `Official default active: ${officialResolved}`;
      return;
    }
    templateLoraControls.statusNode.textContent = `Custom override active: ${currentValue}. Official default is ${officialResolved}; exact official template parity no longer applies.`;
  };
  const syncVisiblePresetOptions = (modeValue) => {
    const visiblePresets = resolveVisiblePresetsForMode(modeValue);
    const currentPresetId = String(elements.preset.value ?? "").trim();
    const currentProfileId = String(elements.profileState.value ?? "").trim().toLowerCase();
    const hiddenCompatiblePresetId =
      retiredVisibleImg2ImgPresetIds.has(currentPresetId) && presetLookup.has(currentPresetId)
        ? currentPresetId
        : retiredVisibleImg2ImgPresetIds.has(currentProfileId) && presetLookup.has(currentProfileId)
          ? currentProfileId
          : "";
    const nextPresetId =
      visiblePresets.some((preset) => preset.id === currentPresetId)
        ? currentPresetId
        : hiddenCompatiblePresetId || findPresetIdForProfile(visiblePresets, currentProfileId) || visiblePresets[0]?.id || "";

    elements.preset.replaceChildren();
    visiblePresets.forEach((preset) => {
      const option = document.createElement("option");
      option.value = preset.id;
      option.textContent = preset.title;
      elements.preset.appendChild(option);
    });
    if (hiddenCompatiblePresetId && nextPresetId === hiddenCompatiblePresetId) {
      const hiddenPreset = presetLookup.get(hiddenCompatiblePresetId);
      if (hiddenPreset) {
        const option = document.createElement("option");
        option.value = hiddenPreset.id;
        option.textContent = hiddenPreset.title;
        option.hidden = true;
        elements.preset.appendChild(option);
      }
    }
    if (nextPresetId) {
      setElementValue(elements.preset, nextPresetId);
    }
    return nextPresetId;
  };
  const syncImageEditReferenceUi = (profileState = syncImageEditProfileState()) => {
    const { imageEditProfile, referenceLimit, normalizedMainSlot } = profileState;
    if (img2imgModeUi.referenceSection) {
      img2imgModeUi.referenceSection.hidden = !imageEditProfile;
    }
    if (img2imgModeUi.referenceHintNode) {
      img2imgModeUi.referenceHintNode.textContent =
        referenceLimit > 1
          ? `Reference 1 uses the source image canvas above. Add up to ${referenceLimit - 1} more ordered references here and choose the main reference.`
          : "Reference 1 uses the source image canvas above. This profile accepts only one direct reference image.";
    }
    img2imgModeUi.referenceSlots.forEach((slot) => {
      const visible = imageEditProfile && slot.slotIndex < referenceLimit;
      if (slot.card) {
        slot.card.hidden = !visible;
      }
      if (slot.mainRadio) {
        slot.mainRadio.disabled = !visible;
        slot.mainRadio.checked = visible && slot.slotIndex === normalizedMainSlot;
      }
      if (slot.assetInput) {
        slot.assetInput.disabled = !visible;
      }
      if (slot.fileInput) {
        slot.fileInput.disabled = !visible;
      }
      slot.updateStatus?.();
    });
  };
  const syncImg2ImgModeAvailability = (profileState = syncImageEditProfileState()) => {
    if (profileState.imageEditProfile && elements.mode.value !== "img2img") {
      setElementValue(elements.mode, "img2img");
      img2imgModeRouter?.activateSubtab?.("img2img", { dispatchChange: false });
    }
    img2imgModeUi.modeButtons.forEach((button, tabId) => {
      const allowed = !profileState.imageEditProfile || tabId === "img2img";
      button.disabled = !allowed;
      button.setAttribute("aria-disabled", String(!allowed));
    });
  };
  const syncImg2ImgModeParameterFields = (profileState = syncImageEditProfileState()) => {
    const editEnabled = profileState.imageEditProfile;
    setFieldVisibility(modeAwareFieldControls.widthField, !editEnabled);
    setFieldVisibility(modeAwareFieldControls.heightField, !editEnabled);
    setFieldVisibility(modeAwareFieldControls.resizeModeField, !editEnabled);
    setFieldVisibility(modeAwareFieldControls.denoiseField, !editEnabled);
    setFieldVisibility(modeAwareFieldControls.growMaskField, !editEnabled);
    setFieldVisibility(modeAwareFieldControls.batchSizeField, !editEnabled);
    setFieldVisibility(modeAwareFieldControls.clipSkipField, !editEnabled);
    if (modeAwareFieldControls.hiresSection) {
      modeAwareFieldControls.hiresSection.hidden = editEnabled;
      modeAwareFieldControls.hiresSection.querySelectorAll("input, select, textarea, button").forEach((control) => {
        control.disabled = editEnabled;
      });
    }
  };
  const syncImg2ImgModeSurface = () => {
    const resolvedPresetId = syncVisiblePresetOptions(elements.mode.value);
    if (resolvedPresetId) {
      updateFormFromPreset(presetLookup, resolvedPresetId, elements, profileLookup, bootstrapState.models);
      syncFamilyAwareModuleQuicksetting(
        profileLookup,
        elements.profileState.value,
        modulesQuicksetting,
        modulesQuicksettingLabel,
        elements.textEncoder,
      );
      syncFamilyAwareAdvancedParameterFields(profileLookup, elements.profileState.value, advancedParameterControls);
    }
    const profileState = syncImageEditProfileState();
    syncImg2ImgModeAvailability(profileState);
    syncImageEditReferenceUi(profileState);
    syncTemplateLoraControls();
    syncImg2ImgModeParameterFields(profileState);
    syncMaskField(elements.mode, elements.maskAsset, inpaintModeControls, {
      imageEditProfile: profileState.imageEditProfile,
      referenceLimit: profileState.referenceLimit,
      modeHintNode: img2imgModeUi.modeHintNode,
      imageAssetField: elements.imageAsset,
      maskDropzone: img2imgModeUi.maskDropzone,
      maskFileInput: img2imgModeUi.maskFileInput,
      batchPane: img2imgModeUi.batchPane,
      batchFileInput: img2imgModeUi.batchFileInput,
      batchStatusNode: img2imgModeUi.batchStatusNode,
    });
    const modeGuard = img2imgMaskCanvasContract.onModeChange();
    if (!modeGuard.ok && modeGuard.message) {
      statusNode.textContent = modeGuard.message;
    }
    img2imgModeUi.maskEditor?.setMode(elements.mode.value);
    const activeModeTabId =
      img2imgModeRouter?.getActiveTabId?.() ?? String(elements.mode.value ?? "img2img").trim().toLowerCase();
    img2imgModeUi.modeButtons.forEach((button, tabId) => {
      const active = tabId === activeModeTabId;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
    });
  };
  img2imgModeRouter = createImg2ImgModeRouter({
    modeInput: elements.mode,
    resolveExecutionMode: resolveImg2ImgExecutionMode,
    onTabChange: () => {
      syncImg2ImgModeSurface();
    },
  });
  img2imgModeRouter.syncFromModeValue();
  elements.preset.addEventListener("change", () => {
    syncImg2ImgModeSurface();
  });
  elements.profileState.addEventListener("change", () => {
    syncImg2ImgModeSurface();
  });
  elements.mode.addEventListener("change", () => {
    img2imgModeRouter.syncFromModeValue();
  });

  const subtabHost = document.createElement("div");
  subtabHost.className = "rookieui-shell__workspace-frame";
  form.appendChild(subtabHost);

  buildSubtabShell(subtabHost, "rookieui-img2img-workspace", [
    {
      id: "generation",
      label: "Generation",
      render: (pane) => {
        const generationModeRailSection = document.createElement("section");
        generationModeRailSection.className = "rookieui-shell__section rookieui-shell__section--soft";
        generationModeRailSection.id = "rookieui-img2img-generation-mode-rail";
        pane.appendChild(generationModeRailSection);
        appendTextElement(generationModeRailSection, "h4", "rookieui-shell__section-title", "Generation Modes");
        const generationModeTabs = document.createElement("div");
        generationModeTabs.className = "rookieui-shell__subtabs rookieui-shell__subtabs--mode";
        generationModeTabs.id = "rookieui-img2img-generation-mode-tabs";
        generationModeTabs.setAttribute("role", "tablist");
        generationModeRailSection.appendChild(generationModeTabs);
        img2imgModeRouter.definitions.forEach((definition) => {
          const button = document.createElement("button");
          button.type = "button";
          button.id = `rookieui-img2img-generation-mode-${definition.id}`;
          button.className = "rookieui-shell__subtab";
          button.textContent = definition.label;
          button.setAttribute("role", "tab");
          button.setAttribute("aria-selected", "false");
          button.tabIndex = -1;
          button.addEventListener("click", () => {
            img2imgModeRouter.activateSubtab(definition.id);
          });
          generationModeTabs.appendChild(button);
          img2imgModeUi.modeButtons.set(String(definition.id).toLowerCase(), button);
        });

        const workspace = document.createElement("div");
        workspace.className = "rookieui-shell__workspace-grid";
        pane.appendChild(workspace);

        const leftColumn = document.createElement("div");
        leftColumn.className = "rookieui-shell__workspace-column";
        workspace.appendChild(leftColumn);

        const generationSection = document.createElement("section");
        generationSection.className = "rookieui-shell__section rookieui-shell__section--soft";
        generationSection.id = "rookieui-img2img-generation-section";
        leftColumn.appendChild(generationSection);
        appendTextElement(generationSection, "h4", "rookieui-shell__section-title", "Generation");

        const generationGrid = document.createElement("div");
        generationGrid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
        generationSection.appendChild(generationGrid);
        createField(generationGrid, "Sampling Method", elements.sampler);
        createField(generationGrid, "Schedule Type", elements.scheduler);
        modeAwareFieldControls.widthField = createSliderField(
          generationGrid,
          "Width",
          elements.width,
          elements.widthSlider,
          "rookieui-img2img-width-field",
        );
        modeAwareFieldControls.heightField = createSliderField(
          generationGrid,
          "Height",
          elements.height,
          elements.heightSlider,
          "rookieui-img2img-height-field",
        );
        modeAwareFieldControls.resizeModeField = createField(generationGrid, "Resize Mode", elements.resizeMode);
        createSliderField(
          generationGrid,
          "Sampling Steps",
          elements.steps,
          elements.stepsSlider,
          "rookieui-img2img-steps-field",
        );
        createSliderField(
          generationGrid,
          "CFG Scale",
          elements.cfgScale,
          elements.cfgScaleSlider,
          "rookieui-img2img-cfg-scale-field",
        );
        advancedParameterControls.shiftField = createField(generationGrid, "Shift", elements.shift);
        advancedParameterControls.fluxGuidanceField = createField(
          generationGrid,
          "Flux Guidance",
          elements.fluxGuidance,
        );
        advancedParameterControls.editMegapixelsField = createField(
          generationGrid,
          "Edit Megapixels",
          elements.editMegapixels,
        );
        modeAwareFieldControls.denoiseField = createSliderField(
          generationGrid,
          "Denoise",
          elements.denoiseStrength,
          elements.denoiseStrengthSlider,
          "rookieui-img2img-denoise-field",
        );
        modeAwareFieldControls.growMaskField = createSliderField(
          generationGrid,
          "Grow Mask",
          elements.growMaskBy,
          elements.growMaskBySlider,
          "rookieui-img2img-grow-mask-field",
        );
        modeAwareFieldControls.batchSizeField = createSliderField(
          generationGrid,
          "Batch Size",
          elements.batchSize,
          elements.batchSizeSlider,
          "rookieui-img2img-batch-size-field",
        );
        modeAwareFieldControls.clipSkipField = createSliderField(
          generationGrid,
          "Clip Skip",
          elements.clipSkip,
          elements.clipSkipSlider,
          "rookieui-img2img-clip-skip-field",
        );
        advancedParameterControls.promptEnhancementField = createInlineCheckboxField(
          generationGrid,
          "Prompt Enhancement",
          elements.promptEnhancementEnabled,
        );
        createSeedControlField(
          generationGrid,
          "Seed",
          elements.seed,
          elements.seedExtra,
          "rookieui-img2img-seed-field",
        );
        syncFamilyAwareAdvancedParameterFields(profileLookup, elements.profileState.value, advancedParameterControls);

        const hiresGrid = createHiresFixSection(
          generationSection,
          "rookieui-img2img-hires-controls",
          elements.hiresEnabled,
        );
        modeAwareFieldControls.hiresSection = hiresGrid.parentElement;
        // IMPORTANT: keep Hires.fix border/checkbox chrome while integrating into Generation section.
        hiresGrid.parentElement?.classList.add("rookieui-shell__hires--integrated");
        createSliderField(
          hiresGrid,
          "Hires Scale",
          elements.hiresScale,
          elements.hiresScaleSlider,
          "rookieui-img2img-hires-scale-field",
        );
        createSliderField(
          hiresGrid,
          "Hires Steps",
          elements.hiresSteps,
          elements.hiresStepsSlider,
          "rookieui-img2img-hires-steps-field",
        );
        createSliderField(
          hiresGrid,
          "Hires Denoise",
          elements.hiresDenoise,
          elements.hiresDenoiseSlider,
          "rookieui-img2img-hires-denoise-field",
        );
        createField(hiresGrid, "Upscale Method", elements.hiresUpscaleMethod);

        img2imgADetailerEditor = createADetailerEditor({
          idPrefix: "rookieui-img2img-adetailer",
          parent: generationSection,
          hiddenInput: elements.adetailer,
          catalog: mergedADetailerCatalog,
          surface: "img2img",
          createInput,
          createRangeInput,
          createSelect,
          createTextarea,
          createCheckbox,
          createField,
          createSliderField,
          createInlineCheckboxField,
          appendTextElement,
          bindSliderPair,
          syncBoundControls,
        });

        img2imgControlNetEditor = createControlNetUnitEditor({
          idPrefix: "rookieui-img2img-controlnet",
          parent: generationSection,
          hiddenInput: elements.controlnetUnits,
          modelOptions: controlnetModelValues.map((value) => ({ value, label: value })),
          controlTypeOrder: controlnetTypeOrder,
          createInput,
          createRangeInput,
          createSelect,
          createCheckbox,
          createField,
          createSliderField,
          appendTextElement,
          readFileAsDataUrl,
          syncBoundControls,
          detectControlNetRequest: bootstrapState.detectControlNetRequest,
          onStatusMessage: (message) => {
            statusNode.textContent = message;
          },
        });
        img2imgControlNetEditor.setControlTypeCatalog(controlnetTypeCatalog, controlnetCatalog.preprocessor_profiles);

        createSliderField(
          generationGrid,
          "Mask Blur",
          elements.maskBlur,
          elements.maskBlurSlider,
          "rookieui-img2img-mask-blur-field",
        );
        createField(generationGrid, "Mask Mode", elements.inpaintMaskMode);
        createField(generationGrid, "Masked Content", elements.inpaintMaskedContent);
        createField(generationGrid, "Inpaint Area", elements.inpaintArea);
        createSliderField(
          generationGrid,
          "Inpaint Padding",
          elements.inpaintPadding,
          elements.inpaintPaddingSlider,
          "rookieui-img2img-inpaint-padding-field",
        );
        createInlineCheckboxField(generationGrid, "Soft Inpainting", elements.softInpaintingEnabled);
        createSliderField(
          generationGrid,
          "Soft: Schedule Bias",
          elements.softInpaintingScheduleBias,
          elements.softInpaintingScheduleBiasSlider,
          "rookieui-img2img-soft-schedule-bias-field",
        );
        createSliderField(
          generationGrid,
          "Soft: Preservation",
          elements.softInpaintingPreservationStrength,
          elements.softInpaintingPreservationStrengthSlider,
          "rookieui-img2img-soft-preservation-field",
        );
        createSliderField(
          generationGrid,
          "Soft: Transition Contrast",
          elements.softInpaintingTransitionContrastBoost,
          elements.softInpaintingTransitionContrastBoostSlider,
          "rookieui-img2img-soft-transition-field",
        );
        createSliderField(
          generationGrid,
          "Soft: Mask Influence",
          elements.softInpaintingMaskInfluence,
          elements.softInpaintingMaskInfluenceSlider,
          "rookieui-img2img-soft-mask-influence-field",
        );
        createSliderField(
          generationGrid,
          "Soft: Diff Threshold",
          elements.softInpaintingDifferenceThreshold,
          elements.softInpaintingDifferenceThresholdSlider,
          "rookieui-img2img-soft-diff-threshold-field",
        );
        createSliderField(
          generationGrid,
          "Soft: Diff Contrast",
          elements.softInpaintingDifferenceContrast,
          elements.softInpaintingDifferenceContrastSlider,
          "rookieui-img2img-soft-diff-contrast-field",
        );

        const rightColumn = document.createElement("div");
        rightColumn.className = "rookieui-shell__workspace-column";
        workspace.appendChild(rightColumn);

        const assetSection = document.createElement("section");
        assetSection.className = "rookieui-shell__section rookieui-shell__section--soft";
        rightColumn.appendChild(assetSection);
        appendTextElement(assetSection, "h4", "rookieui-shell__section-title", "Input Assets");

        const assetGrid = document.createElement("div");
        assetGrid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
        assetSection.appendChild(assetGrid);
        createField(assetGrid, "Mode", elements.mode);
        const hiddenModeField = elements.mode.closest(".rookieui-shell__field");
        // IMPORTANT: keep legacy mode input in DOM as hidden source-of-truth while user-facing switching is routed through generation subtabs.
        if (hiddenModeField) {
          hiddenModeField.hidden = true;
          hiddenModeField.dataset.modeSource = "subtab-router";
        }
        createField(assetGrid, "Resize Mode", elements.resizeMode);
        createField(assetGrid, "Image Asset", elements.imageAsset);
        createField(assetGrid, "Mask Asset", elements.maskAsset);
        const modeHintNode = appendTextElement(
          assetSection,
          "p",
          "rookieui-shell__status",
          "Img2Img/Sketch mode: source image required; mask optional.",
          "rookieui-img2img-mode-note",
        );

        const uploadGrid = document.createElement("div");
        uploadGrid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
        assetSection.appendChild(uploadGrid);

        const imageCanvasSurface = document.createElement("section");
        imageCanvasSurface.className = "rookieui-shell__canvas-upload-surface";
        imageCanvasSurface.id = "rookieui-img2img-image-dropzone";
        uploadGrid.appendChild(imageCanvasSurface);

        const imageCanvasToolbar = document.createElement("div");
        imageCanvasToolbar.className = "rookieui-shell__canvas-upload-toolbar";
        imageCanvasSurface.appendChild(imageCanvasToolbar);

        const createCanvasActionButton = (id, action, icon, label) => {
          const button = document.createElement("button");
          button.type = "button";
          button.id = id;
          button.className =
            "rookieui-shell__mini-action rookieui-shell__mini-action--icon rookieui-shell__mini-action--tone-neutral";
          button.dataset.canvasAction = action;
          button.title = label;
          button.setAttribute("aria-label", label);
          const iconNode = document.createElement("span");
          iconNode.className = "rookieui-shell__mini-action-icon";
          iconNode.textContent = icon;
          button.appendChild(iconNode);
          imageCanvasToolbar.appendChild(button);
          return button;
        };

        const sourceFullscreenButton = createCanvasActionButton(
          "rookieui-img2img-source-fullscreen",
          CANVAS_ACTIONS.fullscreen,
          "⛶",
          "Fullscreen source canvas",
        );
        const sourceUploadButton = createCanvasActionButton(
          "rookieui-img2img-source-upload",
          CANVAS_ACTIONS.upload,
          "📁",
          "Upload source image",
        );
        const sourceRemoveButton = createCanvasActionButton(
          "rookieui-img2img-source-remove",
          CANVAS_ACTIONS.remove,
          "🗑",
          "Remove source image",
        );
        const sourceResetButton = createCanvasActionButton(
          "rookieui-img2img-source-reset",
          CANVAS_ACTIONS.reset,
          "↺",
          "Reset source canvas",
        );
        const sourceUndoButton = createCanvasActionButton(
          "rookieui-img2img-source-undo",
          CANVAS_ACTIONS.undo,
          "↶",
          "Undo source change",
        );
        const sourceRedoButton = createCanvasActionButton(
          "rookieui-img2img-source-redo",
          CANVAS_ACTIONS.redo,
          "↷",
          "Redo source change",
        );

        const imageCanvasStage = document.createElement("div");
        imageCanvasStage.className = "rookieui-shell__canvas-upload-stage";
        imageCanvasStage.id = "rookieui-img2img-source-canvas-stage";
        imageCanvasStage.setAttribute("role", "button");
        imageCanvasStage.setAttribute("tabindex", "0");
        imageCanvasStage.setAttribute("aria-label", "Upload source image");
        imageCanvasSurface.appendChild(imageCanvasStage);

        const imageCanvasPreview = document.createElement("img");
        imageCanvasPreview.className = "rookieui-shell__canvas-upload-preview";
        imageCanvasPreview.id = "rookieui-img2img-source-canvas-preview";
        imageCanvasPreview.alt = "Img2Img source canvas preview";
        imageCanvasPreview.hidden = true;
        imageCanvasStage.appendChild(imageCanvasPreview);

        const imageCanvasPlaceholder = document.createElement("div");
        imageCanvasPlaceholder.className = "rookieui-shell__canvas-upload-placeholder";
        appendTextElement(imageCanvasPlaceholder, "span", "rookieui-shell__canvas-upload-placeholder-icon", "⇪");
        const imageCanvasPlaceholderText = appendTextElement(
          imageCanvasPlaceholder,
          "span",
          "rookieui-shell__canvas-upload-placeholder-text",
          "Upload Img2Img source image",
        );
        imageCanvasStage.appendChild(imageCanvasPlaceholder);

        const imageFileInput = createInput("file", "rookieui-img2img-image-file", "", {
          className: "rookieui-shell__file-input",
        });
        imageFileInput.accept = "image/png,image/webp,image/jpeg";
        imageCanvasSurface.appendChild(imageFileInput);

        const maskDropzone = document.createElement("label");
        maskDropzone.className = "rookieui-shell__dropzone";
        maskDropzone.id = "rookieui-img2img-mask-dropzone";
        uploadGrid.appendChild(maskDropzone);
        appendTextElement(maskDropzone, "span", "rookieui-shell__dropzone-icon", "⇪");
        appendTextElement(maskDropzone, "span", "rookieui-shell__dropzone-text", "Upload inpaint mask");
        const maskFileInput = createInput("file", "rookieui-img2img-mask-file", "", {
          className: "rookieui-shell__file-input",
        });
        maskFileInput.accept = "image/png,image/webp,image/jpeg";
        maskDropzone.appendChild(maskFileInput);

        const referenceSection = document.createElement("section");
        referenceSection.className = "rookieui-shell__section rookieui-shell__section--soft";
        referenceSection.id = "rookieui-img2img-reference-section";
        assetSection.appendChild(referenceSection);
        appendTextElement(referenceSection, "h4", "rookieui-shell__section-title", "Image Edit References");
        const referenceHintNode = appendTextElement(
          referenceSection,
          "p",
          "rookieui-shell__status",
          "Reference 1 uses the source image canvas above.",
          "rookieui-img2img-reference-note",
        );
        const referenceGrid = document.createElement("div");
        referenceGrid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
        referenceSection.appendChild(referenceGrid);
        const primaryReferenceCard = document.createElement("div");
        primaryReferenceCard.className = "rookieui-shell__section rookieui-shell__section--soft";
        primaryReferenceCard.id = "rookieui-img2img-reference-card-1";
        referenceGrid.appendChild(primaryReferenceCard);
        appendTextElement(primaryReferenceCard, "h5", "rookieui-shell__section-title", "Reference 1");
        const primaryReferenceMainLabel = document.createElement("label");
        primaryReferenceMainLabel.className = "rookieui-shell__status";
        primaryReferenceMainLabel.htmlFor = "rookieui-img2img-reference-main-0";
        const primaryReferenceMainRadio = document.createElement("input");
        primaryReferenceMainRadio.type = "radio";
        primaryReferenceMainRadio.name = "rookieui-img2img-main-reference";
        primaryReferenceMainRadio.id = "rookieui-img2img-reference-main-0";
        primaryReferenceMainRadio.value = "0";
        primaryReferenceMainRadio.checked = true;
        primaryReferenceMainLabel.appendChild(primaryReferenceMainRadio);
        primaryReferenceMainLabel.append(" Main reference");
        primaryReferenceCard.appendChild(primaryReferenceMainLabel);
        const primaryReferenceStatus = appendTextElement(
          primaryReferenceCard,
          "p",
          "rookieui-shell__status",
          "Uses the source image canvas and Image Asset field above.",
          "rookieui-img2img-reference-status-1",
        );
        const createAdditionalReferenceSlot = (slotNumber, assetInput, dataInput) => {
          const card = document.createElement("div");
          card.className = "rookieui-shell__section rookieui-shell__section--soft";
          card.id = `rookieui-img2img-reference-card-${slotNumber}`;
          referenceGrid.appendChild(card);
          appendTextElement(card, "h5", "rookieui-shell__section-title", `Reference ${slotNumber}`);
          const mainLabel = document.createElement("label");
          mainLabel.className = "rookieui-shell__status";
          mainLabel.htmlFor = `rookieui-img2img-reference-main-${slotNumber - 1}`;
          const mainRadio = document.createElement("input");
          mainRadio.type = "radio";
          mainRadio.name = "rookieui-img2img-main-reference";
          mainRadio.id = `rookieui-img2img-reference-main-${slotNumber - 1}`;
          mainRadio.value = String(slotNumber - 1);
          mainLabel.appendChild(mainRadio);
          mainLabel.append(" Main reference");
          card.appendChild(mainLabel);
          createField(card, `Reference ${slotNumber} Asset`, assetInput);
          const actionRow = document.createElement("div");
          card.appendChild(actionRow);
          const uploadButton = createActionButton(
            `rookieui-img2img-reference-upload-${slotNumber}`,
            `Upload Reference ${slotNumber}`,
          );
          actionRow.appendChild(uploadButton);
          const clearButton = createActionButton(
            `rookieui-img2img-reference-clear-${slotNumber}`,
            `Clear Reference ${slotNumber}`,
          );
          actionRow.appendChild(clearButton);
          const fileInput = createInput("file", `rookieui-img2img-reference-file-${slotNumber}`, "", {
            className: "rookieui-shell__file-input",
          });
          fileInput.accept = "image/png,image/webp,image/jpeg";
          fileInput.hidden = true;
          fileInput.tabIndex = -1;
          card.appendChild(fileInput);
          const status = appendTextElement(
            card,
            "p",
            "rookieui-shell__status",
            "No additional reference selected.",
            `rookieui-img2img-reference-status-${slotNumber}`,
          );
          const updateStatus = () => {
            const assetValue = String(assetInput.value ?? "").trim();
            const dataValue = String(dataInput.value ?? "").trim();
            status.textContent = assetValue
              ? `Asset: ${assetValue}`
              : dataValue
                ? "Uploaded reference image ready."
                : "No additional reference selected.";
          };
          uploadButton.addEventListener("click", () => {
            fileInput.click();
          });
          clearButton.addEventListener("click", () => {
            assetInput.value = "";
            dataInput.value = "";
            syncBoundControls([assetInput, dataInput]);
            updateStatus();
            statusNode.textContent = `Cleared Reference ${slotNumber}.`;
          });
          assetInput.addEventListener("input", () => {
            if (String(assetInput.value ?? "").trim()) {
              dataInput.value = "";
            }
            syncBoundControls([assetInput, dataInput]);
            updateStatus();
          });
          fileInput.addEventListener("change", async () => {
            const [file] = Array.from(fileInput.files ?? []);
            if (!file) {
              return;
            }
            try {
              dataInput.value = await readFileAsDataUrl(file);
              assetInput.value = "";
              syncBoundControls([assetInput, dataInput]);
              updateStatus();
              statusNode.textContent = `Loaded Reference ${slotNumber}: ${file.name}`;
            } catch (_error) {
              emitFrontendDebugWarning("shell.img2img_reference_upload", "Reference image upload failed.", _error);
              statusNode.textContent = `Failed to load Reference ${slotNumber}.`;
            }
          });
          mainRadio.addEventListener("change", () => {
            if (!mainRadio.checked) {
              return;
            }
            elements.mainReferenceIndex.value = String(slotNumber - 1);
            syncBoundControls([elements.mainReferenceIndex]);
          });
          updateStatus();
          return {
            slotIndex: slotNumber - 1,
            card,
            mainRadio,
            assetInput,
            dataInput,
            fileInput,
            statusNode: status,
            updateStatus,
          };
        };
        primaryReferenceMainRadio.addEventListener("change", () => {
          if (!primaryReferenceMainRadio.checked) {
            return;
          }
          elements.mainReferenceIndex.value = "0";
          syncBoundControls([elements.mainReferenceIndex]);
        });
        const referenceSlotTwo = createAdditionalReferenceSlot(2, elements.referenceAsset2, elements.referenceData2);
        const referenceSlotThree = createAdditionalReferenceSlot(3, elements.referenceAsset3, elements.referenceData3);
        img2imgModeUi.referenceSection = referenceSection;
        img2imgModeUi.referenceHintNode = referenceHintNode;
        img2imgModeUi.referenceSlots = [
          {
            slotIndex: 0,
            card: primaryReferenceCard,
            mainRadio: primaryReferenceMainRadio,
            statusNode: primaryReferenceStatus,
            updateStatus: () => {
              const sourceAsset = String(elements.imageAsset.value ?? "").trim();
              const sourceData = String(elements.imageData.value ?? "").trim();
              primaryReferenceStatus.textContent = sourceAsset
                ? `Uses source asset: ${sourceAsset}`
                : sourceData
                  ? "Uploaded source image is ready as Reference 1."
                  : "Reference 1 uses the source image canvas and Image Asset field above.";
            },
          },
          referenceSlotTwo,
          referenceSlotThree,
        ];

        const batchPane = document.createElement("section");
        batchPane.className = "rookieui-shell__section rookieui-shell__section--soft";
        batchPane.id = "rookieui-img2img-batch-pane";
        assetSection.appendChild(batchPane);
        appendTextElement(batchPane, "h4", "rookieui-shell__section-title", "Batch Upload");

        const batchDropzone = document.createElement("label");
        batchDropzone.className = "rookieui-shell__dropzone";
        batchDropzone.id = "rookieui-img2img-batch-dropzone";
        batchPane.appendChild(batchDropzone);
        appendTextElement(batchDropzone, "span", "rookieui-shell__dropzone-icon", "⇪");
        appendTextElement(batchDropzone, "span", "rookieui-shell__dropzone-text", "Upload multiple source images for batch mode");
        const batchFileInput = createInput("file", "rookieui-img2img-batch-file", "", {
          className: "rookieui-shell__file-input",
        });
        batchFileInput.accept = "image/png,image/webp,image/jpeg";
        batchFileInput.multiple = true;
        batchDropzone.appendChild(batchFileInput);

        const batchList = createList("rookieui-img2img-batch-list");
        batchPane.appendChild(batchList);
        const batchStatusNode = appendTextElement(
          batchPane,
          "p",
          "rookieui-shell__status",
          "No batch images selected.",
          "rookieui-img2img-batch-status",
        );
        img2imgModeUi.modeHintNode = modeHintNode;
        img2imgModeUi.maskDropzone = maskDropzone;
        img2imgModeUi.maskFileInput = maskFileInput;
        img2imgModeUi.batchPane = batchPane;
        img2imgModeUi.batchFileInput = batchFileInput;
        img2imgModeUi.batchStatusNode = batchStatusNode;

        const sourceHistoryState = {
          undo: [],
          redo: [],
          limit: 24,
        };
        let sourceBrushController = null;

        const readSourceSnapshot = () => ({
          imageData: String(elements.imageData.value ?? "").trim(),
          imageAsset: String(elements.imageAsset.value ?? "").trim(),
        });

        const areSourceSnapshotsEqual = (left, right) =>
          String(left?.imageData ?? "") === String(right?.imageData ?? "") &&
          String(left?.imageAsset ?? "") === String(right?.imageAsset ?? "");

        const syncSourceHistoryButtons = () => {
          sourceUndoButton.disabled = sourceHistoryState.undo.length === 0;
          sourceRedoButton.disabled = sourceHistoryState.redo.length === 0;
        };

        const renderSourceCanvasSurface = () => {
          const sourceData = String(elements.imageData.value ?? "").trim();
          const sourceAsset = String(elements.imageAsset.value ?? "").trim();
          const interactionMode = resolveCanvasInteractionMode(sourceData, sourceAsset);
          if (sourceData.startsWith("data:image/")) {
            imageCanvasPreview.src = sourceData;
            imageCanvasPreview.hidden = false;
            imageCanvasPlaceholder.hidden = true;
          } else {
            imageCanvasPreview.hidden = true;
            imageCanvasPreview.removeAttribute("src");
            imageCanvasPlaceholder.hidden = false;
            imageCanvasPlaceholderText.textContent = sourceAsset ? `Asset: ${sourceAsset}` : "Upload Img2Img source image";
          }
          const hasSource = hasCanvasSourceImage(sourceData, sourceAsset);
          sourceRemoveButton.disabled = !hasSource;
          sourceResetButton.disabled = !hasSource;
          imageCanvasStage.dataset.interactionMode = interactionMode;
          imageCanvasStage.setAttribute(
            "aria-label",
            interactionMode === "upload" ? "Upload source image" : "Img2Img source canvas editing surface",
          );
          const brushSyncPromise = sourceBrushController?.syncSourceData(sourceData);
          if (brushSyncPromise && typeof brushSyncPromise.catch === "function") {
            // CRITICAL: brush sync runs async image decode; swallow local decode errors so stage-mode rendering never regresses into a dead UI state.
            brushSyncPromise.catch(() => {});
          }
          img2imgModeUi.referenceSlots[0]?.updateStatus?.();
        };
        refreshSourceCanvasSurface = renderSourceCanvasSurface;

        const pushSourceUndoSnapshot = () => {
          const snapshot = readSourceSnapshot();
          const previous = sourceHistoryState.undo[sourceHistoryState.undo.length - 1];
          if (areSourceSnapshotsEqual(snapshot, previous)) {
            return;
          }
          sourceHistoryState.undo.push(snapshot);
          if (sourceHistoryState.undo.length > sourceHistoryState.limit) {
            sourceHistoryState.undo.shift();
          }
        };

        const applySourceSnapshot = async (snapshot, options = {}) => {
          const nextSnapshot = {
            imageData: String(snapshot?.imageData ?? "").trim(),
            imageAsset: String(snapshot?.imageAsset ?? "").trim(),
          };
          if (options.recordHistory) {
            pushSourceUndoSnapshot();
            sourceHistoryState.redo = [];
          }
          elements.imageData.value = nextSnapshot.imageData;
          elements.imageAsset.value = nextSnapshot.imageAsset;
          img2imgMaskCanvasContract.refreshSourceBinding();
          renderSourceCanvasSurface();
          syncSourceHistoryButtons();
          const previewValue = nextSnapshot.imageData;
          if (img2imgPreviewBox) {
            setPreviewContent(img2imgPreviewBox, previewValue, runtimeState.previewPlaceholder);
          }
          syncBoundControls([elements.imageData, elements.imageAsset]);
          await img2imgModeUi.maskEditor?.refreshFromInputs();
          if (options.statusMessage) {
            statusNode.textContent = options.statusMessage;
          }
        };

        sourceBrushController = createSourceCanvasBrushController({
          idPrefix: "rookieui-img2img-source",
          stage: imageCanvasStage,
          toolbar: imageCanvasToolbar,
          previewImage: imageCanvasPreview,
          onCommitSource: async (editedImageData) => {
            await applySourceSnapshot(
              {
                imageData: editedImageData,
                imageAsset: "",
              },
              {
                recordHistory: true,
                statusMessage: "Applied source brush edits.",
              },
            );
          },
          onStatusMessage: (message) => {
            statusNode.textContent = message;
          },
        });

        const openSourceFilePicker = () => {
          imageFileInput.click();
        };

        const syncSourceFullscreenButton = () => {
          const fullscreenActive = isCanvasElementFullscreen(imageCanvasSurface);
          // CRITICAL: fullscreen can be exited via Esc; always re-read document fullscreen state instead of relying on click toggles.
          const iconNode = sourceFullscreenButton.querySelector(".rookieui-shell__mini-action-icon");
          if (iconNode) {
            iconNode.textContent = fullscreenActive ? "🗗" : "⛶";
          }
          sourceFullscreenButton.title = fullscreenActive ? "Exit fullscreen source canvas" : "Fullscreen source canvas";
          sourceFullscreenButton.setAttribute(
            "aria-label",
            fullscreenActive ? "Exit fullscreen source canvas" : "Fullscreen source canvas",
          );
        };
        syncSourceFullscreenButton();
        if (globalThis.document && typeof globalThis.document.addEventListener === "function") {
          globalThis.document.addEventListener("fullscreenchange", syncSourceFullscreenButton);
          globalThis.document.addEventListener("webkitfullscreenchange", syncSourceFullscreenButton);
        }

        const loadSourceFile = async (file, options = {}) => {
          const sourceImageData = await readFileAsDataUrl(file);
          await applySourceSnapshot(
            {
              imageData: sourceImageData,
              imageAsset: "",
            },
            {
              recordHistory: options.recordHistory !== false,
              statusMessage: `Loaded source image: ${file.name}`,
            },
          );
        };

        sourceUploadButton.addEventListener("click", () => {
          openSourceFilePicker();
        });
        imageCanvasStage.addEventListener("click", () => {
          if (!canCanvasStageOpenUpload(elements.imageData.value, elements.imageAsset.value)) {
            // CRITICAL: once source image exists, stage click must stop forcing file-picker opens; the integrated A1111-like flow switches the stage to edit-first behavior.
            return;
          }
          openSourceFilePicker();
        });
        imageCanvasStage.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            if (!canCanvasStageOpenUpload(elements.imageData.value, elements.imageAsset.value)) {
              return;
            }
            openSourceFilePicker();
          }
        });

        sourceRemoveButton.addEventListener("click", async () => {
          // IMPORTANT: removing source image must clear both source fields together so mode guards do not observe split state.
          await applySourceSnapshot(
            {
              imageData: "",
              imageAsset: "",
            },
            {
              recordHistory: true,
              statusMessage: "Cleared source image.",
            },
          );
        });

        sourceResetButton.addEventListener("click", async () => {
          const sourceSnapshot = readSourceSnapshot();
          if (!hasCanvasSourceImage(sourceSnapshot.imageData, sourceSnapshot.imageAsset)) {
            statusNode.textContent = "No source image to reset.";
            return;
          }
          await img2imgModeUi.maskEditor?.refreshFromInputs();
          statusNode.textContent = "Reset source canvas view.";
        });

        sourceFullscreenButton.addEventListener("click", async () => {
          const fullscreenAction = await toggleCanvasFullscreen(imageCanvasSurface);
          syncSourceFullscreenButton();
          statusNode.textContent =
            fullscreenAction === CANVAS_FULLSCREEN_ACTIONS.entered
              ? "Source canvas entered fullscreen mode."
              : fullscreenAction === CANVAS_FULLSCREEN_ACTIONS.exited
                ? "Source canvas exited fullscreen mode."
                : "Fullscreen is unavailable.";
        });

        sourceUndoButton.addEventListener("click", async () => {
          if (!sourceHistoryState.undo.length) {
            return;
          }
          const currentSnapshot = readSourceSnapshot();
          const previousSnapshot = sourceHistoryState.undo.pop();
          sourceHistoryState.redo.push(currentSnapshot);
          await applySourceSnapshot(previousSnapshot, {
            recordHistory: false,
            statusMessage: "Restored previous source image.",
          });
        });

        sourceRedoButton.addEventListener("click", async () => {
          if (!sourceHistoryState.redo.length) {
            return;
          }
          const currentSnapshot = readSourceSnapshot();
          const nextSnapshot = sourceHistoryState.redo.pop();
          sourceHistoryState.undo.push(currentSnapshot);
          await applySourceSnapshot(nextSnapshot, {
            recordHistory: false,
            statusMessage: "Reapplied source image.",
          });
        });

        const maskEditor = createImg2ImgMaskEditor({
          idPrefix: "rookieui-img2img-mask-editor",
          parent: assetSection,
          modeInput: elements.mode,
          imageEditProfileInput: elements.imageEditProfile,
          imageDataInput: elements.imageData,
          imageAssetInput: elements.imageAsset,
          maskDataInput: elements.maskData,
          maskAssetInput: elements.maskAsset,
          maskCanvasContract: img2imgMaskCanvasContract,
          resolveExecutionMode: resolveImg2ImgExecutionMode,
          onStatusMessage: (message) => {
            statusNode.textContent = message;
          },
          syncBoundControls,
        });
        img2imgModeUi.maskEditor = maskEditor;
        maskEditor.setMode(elements.mode.value);
        maskEditor.refreshFromInputs();
        renderSourceCanvasSurface();
        syncSourceHistoryButtons();

        const assetPreview = document.createElement("div");
        assetPreview.className = "rookieui-shell__preview-box rookieui-shell__preview-box--compact";
        assetPreview.id = "rookieui-img2img-preview";
        assetSection.appendChild(assetPreview);
        img2imgPreviewBox = assetPreview;
        appendTextElement(
          assetPreview,
          "span",
          "rookieui-shell__preview-placeholder",
          runtimeState.previewPlaceholder,
        );

        const attachDropzoneHandlers = (dropzone, fileInput, onFile) => {
          fileInput.addEventListener("change", async () => {
            const [file] = Array.from(fileInput.files ?? []);
            if (!file) {
              return;
            }
            try {
              await onFile(file);
            } catch (_error) {
              emitFrontendDebugWarning("shell.img2img_upload", "Image upload handler failed on file input.", _error);
              statusNode.textContent = "Failed to load image upload.";
            }
          });
          dropzone.addEventListener("dragover", (event) => {
            event.preventDefault();
            dropzone.dataset.dragging = "true";
          });
          dropzone.addEventListener("dragleave", () => {
            dropzone.dataset.dragging = "false";
          });
          dropzone.addEventListener("drop", async (event) => {
            event.preventDefault();
            dropzone.dataset.dragging = "false";
            const [file] = Array.from(event.dataTransfer?.files ?? []);
            if (!file) {
              return;
            }
            try {
              await onFile(file);
            } catch (_error) {
              emitFrontendDebugWarning("shell.img2img_upload", "Image upload handler failed on drop event.", _error);
              statusNode.textContent = "Failed to load dropped image.";
            }
          });
        };

        imageFileInput.addEventListener("change", async () => {
          const [file] = Array.from(imageFileInput.files ?? []);
          if (!file) {
            return;
          }
          try {
            await loadSourceFile(file, { recordHistory: true });
          } catch (_error) {
            emitFrontendDebugWarning("shell.img2img_canvas_source", "Source canvas upload failed on file input.", _error);
            statusNode.textContent = "Failed to load source image.";
          }
        });

        imageCanvasSurface.addEventListener("dragover", (event) => {
          event.preventDefault();
          imageCanvasSurface.dataset.dragging = "true";
        });
        imageCanvasSurface.addEventListener("dragleave", () => {
          imageCanvasSurface.dataset.dragging = "false";
        });
        imageCanvasSurface.addEventListener("drop", async (event) => {
          event.preventDefault();
          imageCanvasSurface.dataset.dragging = "false";
          const [file] = Array.from(event.dataTransfer?.files ?? []);
          if (!file) {
            return;
          }
          try {
            await loadSourceFile(file, { recordHistory: true });
          } catch (_error) {
            emitFrontendDebugWarning("shell.img2img_canvas_source", "Source canvas upload failed on drop event.", _error);
            statusNode.textContent = "Failed to load dropped source image.";
          }
        });

        attachDropzoneHandlers(maskDropzone, maskFileInput, async (file) => {
          const maskData = await readFileAsDataUrl(file);
          elements.maskData.value = maskData;
          elements.maskAsset.value = "";
          img2imgMaskCanvasContract.handleExternalMaskMutation();
          statusNode.textContent = `Loaded inpaint mask: ${file.name}`;
          syncBoundControls([elements.maskData, elements.maskAsset]);
          await img2imgModeUi.maskEditor?.handleExternalMaskMutation();
        });

        elements.imageData.addEventListener("input", () => {
          renderSourceCanvasSurface();
          syncSourceHistoryButtons();
        });
        elements.imageAsset.addEventListener("input", () => {
          renderSourceCanvasSurface();
          syncSourceHistoryButtons();
        });

        const setBatchFiles = async (files) => {
          const fileList = Array.from(files ?? []);
          if (!fileList.length) {
            elements.batchImagesData.value = "[]";
            populateList(batchList, []);
            batchStatusNode.textContent = "No batch images selected.";
            syncBoundControls([elements.batchImagesData]);
            return;
          }
          const entries = await Promise.all(
            fileList.map(async (file) => ({
              name: file.name,
              dataUrl: await readFileAsDataUrl(file),
            })),
          );
          elements.batchImagesData.value = JSON.stringify(entries.map((entry) => entry.dataUrl));
          populateList(batchList, entries.map((entry) => entry.name));
          batchStatusNode.textContent = `Loaded ${entries.length} batch image(s).`;
          if (entries[0]?.dataUrl) {
            setPreviewContent(assetPreview, entries[0].dataUrl, runtimeState.previewPlaceholder);
          }
          syncBoundControls([elements.batchImagesData]);
        };

        batchFileInput.addEventListener("change", async () => {
          try {
            await setBatchFiles(batchFileInput.files);
          } catch (_error) {
            emitFrontendDebugWarning("shell.img2img_batch_upload", "Batch image input handling failed.", _error);
            statusNode.textContent = "Failed to load batch image upload.";
          }
        });
        batchDropzone.addEventListener("dragover", (event) => {
          event.preventDefault();
          batchDropzone.dataset.dragging = "true";
        });
        batchDropzone.addEventListener("dragleave", () => {
          batchDropzone.dataset.dragging = "false";
        });
        batchDropzone.addEventListener("drop", async (event) => {
          event.preventDefault();
          batchDropzone.dataset.dragging = "false";
          try {
            await setBatchFiles(event.dataTransfer?.files);
          } catch (_error) {
            emitFrontendDebugWarning("shell.img2img_batch_upload", "Batch image drop handling failed.", _error);
            statusNode.textContent = "Failed to load dropped batch images.";
          }
        });

        const assetPreviewToolbar = document.createElement("div");
        assetPreviewToolbar.className = "rookieui-shell__preview-toolbar";
        assetSection.appendChild(assetPreviewToolbar);

        createPreviewFullscreenViewer({
          idPrefix: "rookieui-img2img",
          previewBox: assetPreview,
          previewToolbar: assetPreviewToolbar,
          createIconActionButton,
          statusNode,
          labelText: "Preview",
        });

        const previewActions = [
          {
            id: "rookieui-img2img-preview-queue",
            iconClass: "pi-folder-open",
            label: "Queue History",
            tabId: "queue",
            message: "Opened queue history",
            tone: "queue",
          },
          {
            id: "rookieui-img2img-preview-pnginfo",
            iconClass: "pi-file",
            label: "PNG Info",
            tabId: "pnginfo",
            message: "Opened PNG Info",
            tone: "metadata",
          },
          {
            id: "rookieui-img2img-preview-txt2img",
            iconClass: "pi-image",
            label: "Send to Txt2Img",
            tabId: "txt2img",
            message: "Opened Txt2Img",
            tone: "transfer",
          },
          {
            id: "rookieui-img2img-preview-extras",
            iconClass: "pi-star",
            label: "Extras",
            tabId: "extras",
            message: "Opened Extras",
            tone: "extras",
          },
        ];

        previewActions.forEach((action) => {
          const button = createIconActionButton(action.id, action.iconClass, action.label, action.tone);
          button.addEventListener("click", () => {
            activateShellTab(formRegistry, action.tabId, statusNode, action.message);
          });
          assetPreviewToolbar.appendChild(button);
        });
        syncImg2ImgModeSurface();
      },
    },
    {
      id: "textual-inversion",
      label: "Textual Inversion",
      render: (pane) => {
        const infoSection = document.createElement("section");
        infoSection.className = "rookieui-shell__section rookieui-shell__section--soft";
        infoSection.id = "rookieui-img2img-textual-inversion-pane";
        pane.appendChild(infoSection);
        appendTextElement(infoSection, "h4", "rookieui-shell__section-title", "Textual Inversion");
        appendTextElement(
          infoSection,
          "p",
          "rookieui-shell__status",
          "Click an embedding to inject a Comfy-compatible embedding token into the img2img prompt.",
        );
        buildEmbeddingLibrary(
          pane,
          "Available Embeddings",
          inventory.embeddings ?? [],
          elements.prompt,
          "rookieui-img2img-embedding-item",
        );
      },
    },
    {
      id: "checkpoints",
      label: "Checkpoints",
      render: (pane) =>
        buildSelectionLibrary(
          pane,
          "Available Checkpoints",
          inventory.checkpoints ?? [],
          () => elements.checkpoint.value,
          (value) => {
            elements.checkpoint.value = value;
          },
          "rookieui-img2img-checkpoint-item",
        ),
    },
    {
      id: "lora",
      label: "Lora",
      render: (pane) => {
        const loraSection = document.createElement("section");
        loraSection.className = "rookieui-shell__section rookieui-shell__section--soft";
        loraSection.id = "rookieui-img2img-lora-pane";
        pane.appendChild(loraSection);
        appendTextElement(loraSection, "h4", "rookieui-shell__section-title", "LoRA");
        appendTextElement(
          loraSection,
          "p",
          "rookieui-shell__status",
          "Select one host LoRA to inject through a workflow LoraLoader seam during img2img or inpaint execution.",
        );

        const loraGrid = document.createElement("div");
        loraGrid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
        loraSection.appendChild(loraGrid);
        templateLoraControls.field = createField(loraGrid, "Template LoRA", elements.templateLoraName);
        createField(loraGrid, "Model Strength", elements.loraStrengthModel);
        createField(loraGrid, "CLIP Strength", elements.loraStrengthClip);

        templateLoraControls.statusNode = document.createElement("p");
        templateLoraControls.statusNode.className = "rookieui-shell__status";
        templateLoraControls.statusNode.id = "rookieui-img2img-template-lora-status";
        loraSection.appendChild(templateLoraControls.statusNode);

        templateLoraControls.resetButton = createActionButton(
          "rookieui-img2img-reset-template-lora",
          "Reset Template LoRA",
        );
        templateLoraControls.resetButton.addEventListener("click", () => {
          elements.templateLoraName.value = resolvePresetTemplateLoraDefault();
          syncTemplateLoraControls();
        });
        loraSection.appendChild(templateLoraControls.resetButton);

        templateLoraControls.libraryHeading = appendTextElement(
          loraSection,
          "h5",
          "rookieui-shell__section-title",
          "Template LoRA Overrides",
        );
        templateLoraControls.libraryHost = document.createElement("div");
        loraSection.appendChild(templateLoraControls.libraryHost);
        buildSelectionLibrary(
          templateLoraControls.libraryHost,
          "Available Template LoRA Overrides",
          inventory.loras ?? [],
          () => elements.templateLoraName.value,
          (value) => {
            elements.templateLoraName.value = value;
            syncTemplateLoraControls();
          },
          "rookieui-img2img-template-lora-item",
        );

        const loraStatus = document.createElement("p");
        loraStatus.className = "rookieui-shell__status";
        loraStatus.id = "rookieui-img2img-lora-status";
        loraSection.appendChild(loraStatus);

        const clearButton = createActionButton("rookieui-img2img-clear-lora", "Clear LoRA");
        clearButton.addEventListener("click", () => {
          elements.loraName.value = "";
          loraStatus.textContent = "No LoRA selected. Generation will use the base checkpoint only.";
          pane.querySelectorAll(".rookieui-shell__library-item").forEach((node) => {
            node.dataset.active = "false";
          });
        });
        loraSection.appendChild(clearButton);

        const loraLibraryControls = buildLoraLibrary(
          pane,
          "Available LoRAs",
          inventory.loras ?? [],
          elements,
          "rookieui-img2img-lora-item",
          loraStatus,
        );
        clearButton.addEventListener("click", () => {
          if (loraLibraryControls?.select) {
            loraLibraryControls.select.value = "";
            if (loraLibraryControls.actionButton) {
              loraLibraryControls.actionButton.disabled = true;
            }
          }
        });
        elements.templateLoraName.addEventListener("input", syncTemplateLoraControls);
        elements.templateLoraName.addEventListener("change", syncTemplateLoraControls);
        syncTemplateLoraControls();
      },
    },
  ]);

  createXYZPlotShell({
    idPrefix: "rookieui-img2img-xyz-plot",
    parent: form,
    mode: "img2img",
    bootstrapState,
    buildBaseRequest: buildXYZBaseRequest,
    appendTextElement,
    createActionButton,
    createIconActionButton,
    createPreviewFullscreenViewer,
    syncPrimaryPreview: (imageDataUrl) => {
      // IMPORTANT: keep XYZ session previews flowing into the shared top preview box; otherwise only the local Results card updates and the main img2img preview looks stalled.
      runtimeState.previewUrl = imageDataUrl || "";
      setPreviewContent(img2imgPreviewBox, runtimeState.previewUrl, runtimeState.previewPlaceholder);
    },
    onStatusMessage: (message) => {
      statusNode.textContent = message;
    },
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitImg2Img(
      bootstrapState,
      elements,
      statusNode,
      runtimeState,
      img2imgPreviewBox,
      img2imgMaskCanvasContract,
    );
  });

  const img2imgStateLock = installPaneStateLock(formRegistry, "img2img", elements, () => {
    // IMPORTANT: img2img pane restore follows the same Clip Skip editability contract as txt2img.
    syncClipSkipAvailability(profileLookup, elements.profileState.value, elements.clipSkip, elements.clipSkipSlider);
    syncFamilyAwareModuleQuicksetting(
      profileLookup,
      elements.profileState.value,
      modulesQuicksetting,
      modulesQuicksettingLabel,
      elements.textEncoder,
    );
    syncFamilyAwareAdvancedParameterFields(profileLookup, elements.profileState.value, advancedParameterControls);
    syncTemplateLoraControls();
    syncImg2ImgModeSurface();
  });

  formRegistry.img2img = {
    applyPayload(payload) {
      applyPayloadToElements(elements, payload, {
        prompt: "prompt",
        negative_prompt: "negativePrompt",
        profile: "profileState",
        checkpoint_name: "checkpoint",
        vae_name: "vae",
        text_encoder_name: "textEncoder",
        dtype_profile: "lowBits",
        mode: "mode",
        width: "width",
        height: "height",
        resize_mode: "resizeMode",
        image_asset: "imageAsset",
        image_data: "imageData",
        mask_asset: "maskAsset",
        mask_data: "maskData",
        steps: "steps",
        cfg_scale: "cfgScale",
        shift: "shift",
        flux_guidance: "fluxGuidance",
        edit_megapixels: "editMegapixels",
        sampler_name: "sampler",
        scheduler_name: "scheduler",
        prompt_enhancement_enabled: "promptEnhancementEnabled",
        seed: "seed",
        seed_extra: "seedExtra",
        batch_size: "batchSize",
        clip_skip: "clipSkip",
        denoise_strength: "denoiseStrength",
        grow_mask_by: "growMaskBy",
        mask_blur: "maskBlur",
        inpaint_mask_mode: "inpaintMaskMode",
        inpaint_masked_content: "inpaintMaskedContent",
        inpaint_area: "inpaintArea",
        inpaint_padding: "inpaintPadding",
        soft_inpainting_enabled: "softInpaintingEnabled",
        soft_inpainting_schedule_bias: "softInpaintingScheduleBias",
        soft_inpainting_preservation_strength: "softInpaintingPreservationStrength",
        soft_inpainting_transition_contrast_boost: "softInpaintingTransitionContrastBoost",
        soft_inpainting_mask_influence: "softInpaintingMaskInfluence",
        soft_inpainting_difference_threshold: "softInpaintingDifferenceThreshold",
        soft_inpainting_difference_contrast: "softInpaintingDifferenceContrast",
        hires_enabled: "hiresEnabled",
        hires_scale: "hiresScale",
        hires_steps: "hiresSteps",
        hires_denoise: "hiresDenoise",
        hires_upscale_method: "hiresUpscaleMethod",
        template_lora_name: "templateLoraName",
        lora_name: "loraName",
        lora_strength_model: "loraStrengthModel",
        lora_strength_clip: "loraStrengthClip",
      });
      if (Array.isArray(payload.batch_images)) {
        elements.batchImagesData.value = JSON.stringify(payload.batch_images);
      } else if (String(payload.mode ?? "").trim().toLowerCase() !== "batch") {
        elements.batchImagesData.value = "[]";
      }
      const referenceImages = Array.isArray(payload.reference_images)
        ? payload.reference_images.filter((entry) => entry && typeof entry === "object")
        : [];
      const additionalReferenceSlots = [
        { assetInput: elements.referenceAsset2, dataInput: elements.referenceData2 },
        { assetInput: elements.referenceAsset3, dataInput: elements.referenceData3 },
      ];
      if (referenceImages.length) {
        const [primaryReference, ...additionalReferences] = referenceImages;
        elements.imageAsset.value = String(primaryReference?.image_asset ?? "").trim();
        elements.imageData.value = String(primaryReference?.image_data ?? "").trim();
        additionalReferenceSlots.forEach((slot, index) => {
          const entry = additionalReferences[index] ?? {};
          slot.assetInput.value = String(entry.image_asset ?? "").trim();
          slot.dataInput.value = String(entry.image_data ?? "").trim();
        });
        elements.mainReferenceIndex.value = String(Math.min(Math.max(0, Number(payload.main_reference_index ?? 0) || 0), 2));
      } else {
        additionalReferenceSlots.forEach((slot) => {
          slot.assetInput.value = "";
          slot.dataInput.value = "";
        });
        elements.mainReferenceIndex.value = "0";
      }
      if (Array.isArray(payload.controlnet_units)) {
        elements.controlnetUnits.value = JSON.stringify(payload.controlnet_units);
        img2imgControlNetEditor?.setUnits(payload.controlnet_units);
      }
      if (payload.adetailer && typeof payload.adetailer === "object") {
        elements.adetailer.value = JSON.stringify(payload.adetailer);
        img2imgADetailerEditor?.setValue(payload.adetailer);
      }
      const resolvedPresetId = findPresetIdForProfile(allPresets, elements.profileState.value);
      if (resolvedPresetId) {
        setElementValue(elements.preset, resolvedPresetId);
      }
      // IMPORTANT: re-apply editability after payload import so clip-skip never remains frozen from previous profile state.
      syncClipSkipAvailability(profileLookup, elements.profileState.value, elements.clipSkip, elements.clipSkipSlider);
      syncFamilyAwareModuleQuicksetting(
        profileLookup,
        elements.profileState.value,
        modulesQuicksetting,
        modulesQuicksettingLabel,
        elements.textEncoder,
      );
      syncFamilyAwareAdvancedParameterFields(profileLookup, elements.profileState.value, advancedParameterControls);
      syncTemplateLoraControls();
      img2imgModeRouter.syncFromModeValue();
      img2imgMaskCanvasContract.refreshSourceBinding();
      img2imgMaskCanvasContract.handleExternalMaskMutation();
      img2imgModeUi.maskEditor?.refreshFromInputs();
      refreshSourceCanvasSurface?.();
      const appliedImageData = String(elements.imageData.value ?? "").trim();
      const hasAppliedSourceImage = hasCanvasSourceImage(appliedImageData, elements.imageAsset.value);
      const appliedBatchImages = parseJsonArrayField(elements.batchImagesData.value);
      const previewImageData =
        (hasAppliedSourceImage ? appliedImageData : "") ||
        (isImg2ImgBatchMode(elements.mode.value) ? String(appliedBatchImages[0] ?? "") : "");
      if (img2imgPreviewBox) {
        if (previewImageData) {
          setPreviewContent(img2imgPreviewBox, previewImageData, runtimeState.previewPlaceholder);
        } else {
          setPreviewContent(img2imgPreviewBox, "", runtimeState.previewPlaceholder);
        }
      }
      syncBoundControls(Object.values(elements));
      img2imgStateLock.capture();
    },
    maskCanvas: {
      stageMaskData: (maskDataUrl, metadata = {}) =>
        img2imgMaskCanvasContract.stageMaskData(maskDataUrl, metadata),
      applyStagedMask: () => img2imgMaskCanvasContract.applyStagedMask(),
      clearStagedMask: () => img2imgMaskCanvasContract.clearStagedMask(),
      refreshSourceBinding: () => img2imgMaskCanvasContract.refreshSourceBinding(),
      getStateSnapshot: () => img2imgMaskCanvasContract.getStateSnapshot(),
    },
    modeRouter: {
      activateSubtab: (subtabId, options = {}) => img2imgModeRouter.activateSubtab(subtabId, options),
      getActiveTabId: () => img2imgModeRouter.getActiveTabId(),
      syncFromModeValue: () => img2imgModeRouter.syncFromModeValue(),
    },
  };

  return {
    onActivate: img2imgStateLock.restore,
    onDeactivate: img2imgStateLock.capture,
  };
}
