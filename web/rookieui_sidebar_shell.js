import {
  appendTextElement,
  bindSliderPair,
  buildCompatibilityList,
  buildFeatureList,
  buildParityList,
  buildTabList,
  createCheckbox,
  createField,
  createHiresFixSection,
  createInlineCheckboxField,
  createInput,
  createRangeInput,
  createSelect,
  createSliderField,
  createTextarea,
  generateDeterministicSeed,
  preventSummaryToggleOnCheckbox,
  syncBoundControls,
} from "./rookieui_sidebar_shell_utils.js?v=20260411-r46-utils";
import { rookieUIDebugWarn } from "./rookieui_debug.js?v=20260411-r48-debug";
import { createTxt2ImgTabDefinition } from "./sidebar_tabs/rookieui_txt2img_tab.js?v=20260411-r47-tabs";
import { createImg2ImgTabDefinition } from "./sidebar_tabs/rookieui_img2img_tab.js?v=20260411-r47-tabs";
import { createExtrasTabDefinition } from "./sidebar_tabs/rookieui_extras_tab.js?v=20260411-r47-tabs";
import { createPngInfoTabDefinition } from "./sidebar_tabs/rookieui_pnginfo_tab.js?v=20260411-r47-tabs";
import { createQueueTabDefinition } from "./sidebar_tabs/rookieui_queue_tab.js?v=20260411-r47-tabs";
import { createImg2ImgMaskCanvasContract } from "./sidebar_tabs/rookieui_img2img_mask_canvas.js?v=20260411-r49-mask-contract";
import { createImg2ImgMaskCanvasEditor } from "./sidebar_tabs/rookieui_img2img_mask_editor.js?v=20260411-f58-mask-editor";

const ROOKIEUI_GITHUB_URL = "https://github.com/rookiestar28/ComfyUI-RookieUI";

function emitFrontendDebugWarning(scope, message, error = null, metadata = null) {
  const detail = {};
  if (metadata && typeof metadata === "object") {
    Object.assign(detail, metadata);
  }
  if (error) {
    detail.error = error instanceof Error ? error.message : String(error);
  }
  rookieUIDebugWarn(scope, message, Object.keys(detail).length ? detail : null);
}

function createSeedControlField(parent, labelText, seedInput, seedExtraInput, id = "") {
  const field = document.createElement("div");
  field.className = "rookieui-shell__field rookieui-shell__seed-field";
  if (id) {
    field.id = id;
  }

  const label = document.createElement("span");
  label.className = "rookieui-shell__field-label";
  label.textContent = labelText;
  field.appendChild(label);

  const row = document.createElement("div");
  row.className = "rookieui-shell__seed-row";
  field.appendChild(row);
  row.appendChild(seedInput);

  const randomButton = createMiniActionButton(`${seedInput.id}-random`, "🎲");
  randomButton.classList.add("rookieui-shell__seed-action");
  randomButton.title = "Use random seed (-1)";
  randomButton.setAttribute("aria-label", "Use random seed");
  randomButton.addEventListener("click", () => {
    seedInput.value = "-1";
    seedInput.dispatchEvent(new Event("input", { bubbles: true }));
    seedInput.dispatchEvent(new Event("change", { bubbles: true }));
  });
  row.appendChild(randomButton);

  const fixedButton = createMiniActionButton(`${seedInput.id}-fixed`, "♻️");
  fixedButton.classList.add("rookieui-shell__seed-action");
  fixedButton.title = "Fix current seed";
  fixedButton.setAttribute("aria-label", "Fix current seed");
  fixedButton.addEventListener("click", () => {
    const current = Number(seedInput.value);
    if (Number.isInteger(current) && current >= 0) {
      return;
    }
    seedInput.value = String(generateDeterministicSeed());
    seedInput.dispatchEvent(new Event("input", { bubbles: true }));
    seedInput.dispatchEvent(new Event("change", { bubbles: true }));
  });
  row.appendChild(fixedButton);

  const extraToggle = document.createElement("label");
  extraToggle.className = "rookieui-shell__seed-extra";
  extraToggle.appendChild(seedExtraInput);
  appendTextElement(extraToggle, "span", "rookieui-shell__field-label", "Extra");
  row.appendChild(extraToggle);

  parent.appendChild(field);
}

function countPromptUnits(value) {
  const trimmed = String(value ?? "").trim();
  if (!trimmed) {
    return 0;
  }
  const grouped = trimmed.split(/[\n,]+/).map((entry) => entry.trim()).filter(Boolean);
  if (grouped.length > 1) {
    return grouped.length;
  }
  return trimmed.split(/\s+/).filter(Boolean).length;
}

function createPromptField(parent, labelText, textarea, counterId) {
  const field = document.createElement("label");
  field.className = "rookieui-shell__prompt-field";
  textarea.setAttribute("aria-label", labelText);
  field.appendChild(textarea);

  const counter = document.createElement("span");
  counter.className = "rookieui-shell__counter-badge rookieui-shell__counter-badge--overlay";
  counter.id = counterId;
  field.appendChild(counter);

  const syncCounter = () => {
    // IMPORTANT: normalize whitespace-only prompt edits to empty string so placeholder guidance does not disappear while counter still shows 0/75.
    if (typeof textarea.value === "string" && textarea.value.length > 0 && textarea.value.trim().length === 0) {
      textarea.value = "";
    }
    counter.textContent = `${countPromptUnits(textarea.value)}/75`;
  };
  textarea.addEventListener("input", syncCounter);
  textarea.__syncBinding = syncCounter;
  syncCounter();

  parent.appendChild(field);
}

function createList(id) {
  const list = document.createElement("ul");
  list.className = "rookieui-shell__list";
  list.id = id;
  return list;
}

function setListVisibility(headingNode, listNode, values) {
  if (!headingNode || !listNode) {
    return;
  }
  const normalizedValues = Array.isArray(values) ? values : [];
  populateList(listNode, normalizedValues);
  const hasItems = normalizedValues.length > 0;
  headingNode.hidden = !hasItems;
  listNode.hidden = !hasItems;
}

function setMetadataVisibility(sectionNode, metadataItems) {
  if (!sectionNode) {
    return;
  }
  const entries = Object.entries(metadataItems ?? {});
  sectionNode.replaceChildren();
  sectionNode.hidden = entries.length === 0;
  entries.forEach(([key, value]) => {
    const row = document.createElement("div");
    row.className = "rookieui-shell__metadata-row";
    appendTextElement(row, "span", "rookieui-shell__metadata-key", key);
    appendTextElement(row, "span", "rookieui-shell__metadata-value", value);
    sectionNode.appendChild(row);
  });
}

function formatPngInfoSourceLabel(sourceType) {
  const normalized = String(sourceType ?? "").trim().toLowerCase();
  if (!normalized) {
    return "";
  }
  if (normalized === "a1111") {
    return "A1111";
  }
  if (normalized === "comfyui") {
    return "ComfyUI";
  }
  return normalized.toUpperCase();
}

function readPngInfoSummaryText(inspectionResult) {
  const metadataItems = inspectionResult?.metadata_items ?? {};
  const candidates = [metadataItems.parameters, metadataItems.Comment, metadataItems.info];
  for (const entry of candidates) {
    if (typeof entry === "string" && entry.trim()) {
      return entry.trim();
    }
  }
  return "";
}

function normalizePngInfoCardValue(value) {
  if (value === null || value === undefined) {
    return "";
  }
  const normalized = String(value).trim();
  return normalized;
}

function setPngInfoDetailCards(gridNode, cards) {
  if (!gridNode) {
    return;
  }
  gridNode.replaceChildren();
  const visibleCards = Array.isArray(cards)
    ? cards.filter((card) => card && normalizePngInfoCardValue(card.value))
    : [];
  if (!visibleCards.length) {
    appendTextElement(
      gridNode,
      "p",
      "rookieui-shell__status",
      "No structured A1111 parameter cards were found in this metadata payload.",
    );
    return;
  }

  visibleCards.forEach((card) => {
    const cardNode = document.createElement("article");
    cardNode.className = "rookieui-shell__pnginfo-card";
    appendTextElement(cardNode, "span", "rookieui-shell__pnginfo-card-label", card.label);
    appendTextElement(cardNode, "span", "rookieui-shell__pnginfo-card-value", normalizePngInfoCardValue(card.value));
    gridNode.appendChild(cardNode);
  });
}

function setPngInfoSummaryVisibility(summaryNodes, inspectionResult) {
  if (!summaryNodes) {
    return;
  }
  const sourceLabel = formatPngInfoSourceLabel(inspectionResult?.source_type);
  summaryNodes.sourceBadge.hidden = !sourceLabel;
  if (sourceLabel) {
    summaryNodes.sourceBadge.textContent = sourceLabel;
  }

  const summaryText = readPngInfoSummaryText(inspectionResult);
  if (summaryText) {
    summaryNodes.summaryText.hidden = false;
    summaryNodes.summaryText.textContent = summaryText;
  } else {
    summaryNodes.summaryText.hidden = false;
    summaryNodes.summaryText.textContent = "Generation summary will appear after metadata is loaded.";
  }

  const payload = inspectionResult?.payload ?? {};
  const raw = inspectionResult?.raw_parameters ?? {};
  const sizeValue = normalizePngInfoCardValue(raw["Size-1"]) && normalizePngInfoCardValue(raw["Size-2"])
    ? `${normalizePngInfoCardValue(raw["Size-1"])}x${normalizePngInfoCardValue(raw["Size-2"])}`
    : "";
  setPngInfoDetailCards(summaryNodes.cards, [
    { label: "Source", value: sourceLabel },
    { label: "Steps", value: raw["Steps"] ?? payload.steps },
    { label: "Sampler", value: raw.Sampler ?? payload.sampler_name },
    { label: "CFG Scale", value: raw["CFG scale"] ?? payload.cfg_scale },
    { label: "Seed", value: raw.Seed ?? payload.seed },
    { label: "Size", value: sizeValue },
    { label: "Model", value: raw.Model ?? raw["Model name"] ?? payload.checkpoint_name },
    { label: "Model Hash", value: raw["Model hash"] },
    { label: "Schedule Type", value: raw["Schedule type"] ?? payload.scheduler_name },
    { label: "VAE Hash", value: raw["VAE hash"] },
    { label: "VAE", value: raw.VAE ?? payload.vae_name },
    { label: "Denoising Strength", value: raw["Denoising strength"] ?? payload.denoise_strength },
    { label: "Hires Upscale", value: raw["Hires upscale"] ?? payload.hires_scale },
    { label: "Hires Upscaler", value: raw["Hires upscaler"] ?? payload.hires_upscale_method },
    { label: "Version", value: raw.Version },
  ]);

  const promptText = normalizePngInfoCardValue(payload.prompt ?? raw.Prompt ?? inspectionResult?.metadata_items?.Prompt);
  const negativePromptText = normalizePngInfoCardValue(
    payload.negative_prompt ?? raw["Negative prompt"] ?? inspectionResult?.metadata_items?.["Negative prompt"],
  );
  summaryNodes.promptText.textContent = promptText || "Prompt is unavailable in this metadata payload.";
  summaryNodes.negativePromptText.textContent =
    negativePromptText || "Negative prompt is unavailable in this metadata payload.";
  summaryNodes.copyPrompt.disabled = !promptText;
  summaryNodes.copyNegativePrompt.disabled = !negativePromptText;
}

async function writeTextToClipboard(text) {
  const normalized = String(text ?? "").trim();
  if (!normalized) {
    return false;
  }
  if (globalThis?.navigator?.clipboard?.writeText) {
    await globalThis.navigator.clipboard.writeText(normalized);
    return true;
  }
  return false;
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Failed to read image file."));
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.readAsDataURL(file);
  });
}

function buildProfileLookup(capabilities) {
  const profiles = capabilities.parity?.profiles ?? [];
  const lookup = new Map();
  profiles.forEach((profile) => {
    lookup.set(profile.id, profile);
  });
  return lookup;
}

function buildPresetLookup(presets) {
  const lookup = new Map();
  presets.forEach((preset) => {
    lookup.set(preset.id, preset);
  });
  return lookup;
}

function findPresetIdForProfile(presets, profileId) {
  const matchedPreset = presets.find((preset) => preset.profile === profileId);
  return matchedPreset?.id ?? "";
}

function setElementValue(element, value) {
  if (!element || value === undefined || value === null) {
    return;
  }
  if (element.type === "checkbox") {
    element.checked = Boolean(value);
    return;
  }
  element.value = String(value);
}

function snapshotElementState(elements) {
  const snapshot = {};
  Object.entries(elements).forEach(([key, element]) => {
    if (!element || !element.id || element.type === "file") {
      return;
    }
    snapshot[key] = element.type === "checkbox" ? Boolean(element.checked) : String(element.value ?? "");
  });
  return snapshot;
}

function restoreElementState(elements, snapshot) {
  if (!snapshot || typeof snapshot !== "object") {
    return;
  }
  Object.entries(snapshot).forEach(([key, value]) => {
    if (!(key in elements)) {
      return;
    }
    const element = elements[key];
    if (!element || element.type === "file") {
      return;
    }
    setElementValue(element, value);
    if (element.type === "range") {
      element.__syncSliderVisual?.();
    }
  });
  syncBoundControls(Object.values(elements));
}

function installPaneStateLock(formRegistry, paneId, elements, afterRestore = null) {
  let snapshot = snapshotElementState(elements);
  const capture = () => {
    snapshot = snapshotElementState(elements);
  };
  // CRITICAL: keep per-pane state lock here; top-tab switches must not silently reset user-selected models/parameters.
  const restore = () => {
    restoreElementState(elements, snapshot);
    if (typeof afterRestore === "function") {
      afterRestore();
    }
  };

  Object.values(elements).forEach((element) => {
    if (!element || typeof element.addEventListener !== "function" || element.type === "file") {
      return;
    }
    element.addEventListener("input", capture);
    element.addEventListener("change", capture);
  });

  if (formRegistry && paneId) {
    formRegistry.__paneStateLocks ??= {};
    formRegistry.__paneStateLocks[paneId] = { capture, restore };
  }
  return { capture, restore };
}

function populateList(listNode, values) {
  if (!listNode) {
    return;
  }

  listNode.replaceChildren();
  values.forEach((value) => {
    const item = document.createElement("li");
    item.className = "rookieui-shell__list-item";
    item.textContent = value;
    listNode.appendChild(item);
  });
}

function applyPayloadToElements(elements, payload, fieldMap) {
  Object.entries(fieldMap).forEach(([payloadKey, elementKey]) => {
    if (!(payloadKey in payload)) {
      return;
    }
    setElementValue(elements[elementKey], payload[payloadKey]);
  });
}

function createActionButton(id, text) {
  const button = document.createElement("button");
  button.id = id;
  button.className = "rookieui-shell__button rookieui-shell__button--secondary";
  button.type = "button";
  button.textContent = text;
  return button;
}

function updateFormFromPreset(presetLookup, presetId, elements, profileLookup) {
  const preset = presetLookup.get(presetId);
  if (!preset) {
    return;
  }

  setElementValue(elements.profileState, preset.profile);
  setElementValue(elements.checkpoint, preset.checkpoint_name);
  setElementValue(elements.vae, preset.vae_name);
  setElementValue(elements.textEncoder, preset.text_encoder_name);
  setElementValue(elements.width, preset.width);
  setElementValue(elements.height, preset.height);
  setElementValue(elements.steps, preset.steps);
  setElementValue(elements.cfgScale, preset.cfg_scale);
  setElementValue(elements.sampler, preset.sampler_name);
  setElementValue(elements.scheduler, preset.scheduler_name);
  setElementValue(elements.clipSkip, preset.clip_skip);

  // CRITICAL: never hard-disable Clip Skip on preset switch; users must be able to adjust values even when the profile may ignore them at execution.
  syncClipSkipAvailability(profileLookup, preset.profile, elements.clipSkip, elements.clipSkipSlider);
  syncBoundControls(Object.values(elements));
}

function updateFormFromProfile(profileLookup, profileId, elements) {
  const profile = profileLookup.get(profileId);
  if (!profile) {
    return;
  }

  setElementValue(elements.width, profile.default_width);
  setElementValue(elements.height, profile.default_height);
  setElementValue(elements.steps, profile.default_steps);
  setElementValue(elements.cfgScale, profile.default_cfg_scale);
  setElementValue(elements.sampler, profile.default_sampler);
  setElementValue(elements.scheduler, profile.default_scheduler);
  setElementValue(elements.clipSkip, profile.default_clip_skip);
  // IMPORTANT: keep profile default sync and editability sync together to avoid stale disabled state after profile transitions.
  syncClipSkipAvailability(profileLookup, profile.id, elements.clipSkip, elements.clipSkipSlider);
  syncBoundControls(Object.values(elements));
}

function syncClipSkipAvailability(profileLookup, profileId, clipSkipInput, clipSkipSlider = null) {
  if (!clipSkipInput) {
    return;
  }
  const profile = profileLookup?.get?.(profileId);
  const supportsClipSkip = Boolean(profile?.supports_clip_skip);
  const ignoredHint = "This profile may ignore Clip Skip during execution.";

  // IMPORTANT: keep Clip Skip editable in UI across all presets (including SD1.5/SDXL/Flux/Qwen); execution-level support is enforced in backend normalization.
  clipSkipInput.disabled = false;
  if (clipSkipSlider) {
    clipSkipSlider.disabled = false;
  }

  if (!supportsClipSkip) {
    clipSkipInput.title = ignoredHint;
    clipSkipInput.dataset.executionHint = "ignored";
    if (clipSkipSlider) {
      clipSkipSlider.title = ignoredHint;
      clipSkipSlider.dataset.executionHint = "ignored";
    }
    return;
  }
  clipSkipInput.title = "";
  delete clipSkipInput.dataset.executionHint;
  if (clipSkipSlider) {
    clipSkipSlider.title = "";
    delete clipSkipSlider.dataset.executionHint;
  }
}

function syncFamilyAwareModuleQuicksetting(profileLookup, profileId, quicksettingCard, labelNode, textEncoderControl) {
  const profile = profileLookup.get(profileId);
  const baseFamily = profile?.base_family ?? "";
  // CRITICAL: profile id drives Text Encoder visibility; Flux/Qwen route through SDXL graphs but must keep selector visible.
  const profileKey = String(profile?.id ?? profileId ?? "").trim().toLowerCase();
  const showTextEncoder = !["sd15", "sdxl", "pony", "illustrious", "noob"].includes(profileKey);
  if (labelNode) {
    labelNode.textContent = showTextEncoder ? "VAE / Text Encoder" : "VAE";
  }
  if (quicksettingCard) {
    quicksettingCard.dataset.baseFamily = baseFamily;
  }
  if (textEncoderControl) {
    textEncoderControl.hidden = !showTextEncoder;
    textEncoderControl.disabled = !showTextEncoder;
  }
}

function readTxt2ImgPayload(elements) {
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
    sampler_name: elements.sampler.value,
    scheduler_name: elements.scheduler.value,
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
    lora_name: elements.loraName.value,
    lora_strength_model: Number(elements.loraStrengthModel.value),
    lora_strength_clip: Number(elements.loraStrengthClip.value),
  };
}

function normalizeRuntimeClientId(rawClientId) {
  if (typeof rawClientId !== "string") {
    return "";
  }
  const normalized = rawClientId.trim();
  if (!normalized || /\s/.test(normalized)) {
    return "";
  }
  return normalized;
}

function resolveRuntimeApi(bootstrapState) {
  const runtimeApi = bootstrapState?.runtimeApi ?? globalThis?.window?.app?.api ?? null;
  if (bootstrapState && runtimeApi && bootstrapState.runtimeApi !== runtimeApi) {
    bootstrapState.runtimeApi = runtimeApi;
  }
  return runtimeApi;
}

function resolveActiveClientId(bootstrapState) {
  const runtimeApi = resolveRuntimeApi(bootstrapState);
  const runtimeClientId = normalizeRuntimeClientId(runtimeApi?.clientId);
  if (runtimeClientId) {
    if (bootstrapState) {
      bootstrapState.clientId = runtimeClientId;
    }
    return runtimeClientId;
  }
  const sessionClientId = normalizeRuntimeClientId(globalThis?.window?.sessionStorage?.getItem?.("clientId"));
  if (sessionClientId) {
    if (bootstrapState) {
      bootstrapState.clientId = sessionClientId;
    }
    return sessionClientId;
  }
  return normalizeRuntimeClientId(bootstrapState?.clientId);
}

function createGenerationRuntimeState({ previewPlaceholder = "" } = {}) {
  return {
    runToken: 0,
    previewUrl: "",
    previewPlaceholder,
    lastPreviewRenderAt: 0,
    progressValue: null,
    progressMax: null,
    progressSeen: false,
    previewFrameSeen: false,
  };
}

function setGenerationPreview(runtimeState, previewBox, imageUrl, fallbackText) {
  if (!runtimeState || !previewBox) {
    return;
  }
  const previousPreviewUrl = runtimeState.previewUrl;
  runtimeState.previewUrl = imageUrl || "";
  setPreviewContent(previewBox, runtimeState.previewUrl, fallbackText || runtimeState.previewPlaceholder);
  if (
    previousPreviewUrl &&
    previousPreviewUrl !== runtimeState.previewUrl &&
    previousPreviewUrl.startsWith("blob:")
  ) {
    // CRITICAL: delay blob URL revoke until after DOM source swap; immediate revoke can trigger visible sidebar-wide flicker on rapid preview frames.
    requestAnimationFrame(() => URL.revokeObjectURL(previousPreviewUrl));
  }
}

function formatGenerationProgress(status, progressValue, progressMax) {
  const safeStatus = status || "pending";
  if (
    typeof progressValue === "number" &&
    Number.isFinite(progressValue) &&
    typeof progressMax === "number" &&
    Number.isFinite(progressMax) &&
    progressMax > 0
  ) {
    const percent = Math.max(0, Math.min(100, Math.round((progressValue / progressMax) * 100)));
    return `${safeStatus.replace("_", " ")} (${percent}%)`;
  }
  return safeStatus.replace("_", " ");
}

function extractRuntimePromptId(detail) {
  if (!detail || typeof detail !== "object") {
    return "";
  }
  const keys = ["prompt_id", "promptId", "jobId", "id"];
  for (const key of keys) {
    const value = detail[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return "";
}

function extractPreviewBlob(payload) {
  if (payload instanceof Blob) {
    return payload;
  }
  if (!payload || typeof payload !== "object") {
    return null;
  }
  if (payload.blob instanceof Blob) {
    return payload.blob;
  }
  if (payload.buffer instanceof ArrayBuffer) {
    return new Blob([payload.buffer], { type: payload.mime || "image/png" });
  }
  if (payload.data instanceof Uint8Array) {
    return new Blob([payload.data], { type: payload.mime || "image/png" });
  }
  return null;
}

function extractPrimaryHistoryImage(historyPayload, promptId) {
  const promptHistory = historyPayload?.[promptId];
  if (!promptHistory || typeof promptHistory !== "object") {
    return null;
  }
  const outputs = promptHistory.outputs;
  if (!outputs || typeof outputs !== "object") {
    return null;
  }
  for (const nodeOutput of Object.values(outputs)) {
    if (!nodeOutput || typeof nodeOutput !== "object") {
      continue;
    }
    const images = Array.isArray(nodeOutput.images) ? nodeOutput.images : [];
    for (const image of images) {
      if (!image || typeof image !== "object") {
        continue;
      }
      const filename = typeof image.filename === "string" ? image.filename : "";
      if (!filename) {
        continue;
      }
      return {
        filename,
        subfolder: typeof image.subfolder === "string" ? image.subfolder : "",
        type: typeof image.type === "string" ? image.type : "output",
      };
    }
  }
  return null;
}

function buildComfyViewUrl(imageDescriptor) {
  if (!imageDescriptor?.filename) {
    return "";
  }
  const params = new URLSearchParams({
    filename: imageDescriptor.filename,
    subfolder: imageDescriptor.subfolder || "",
    type: imageDescriptor.type || "output",
  });
  return `/view?${params.toString()}`;
}

function readBlobAsDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Failed to decode image blob."));
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.readAsDataURL(blob);
  });
}

async function resolvePreviewUrlAsDataUrl(previewUrl) {
  if (!previewUrl) {
    return "";
  }
  if (previewUrl.startsWith("data:image/")) {
    return previewUrl;
  }
  const response = await fetch(previewUrl);
  if (!response.ok) {
    throw new Error(`Failed to fetch preview image: ${response.status}`);
  }
  const blob = await response.blob();
  return readBlobAsDataUrl(blob);
}

async function transferPreviewToImg2Img(formRegistry, runtimeState, statusNode, previewBox = null) {
  let previewUrl = runtimeState?.previewUrl ?? "";
  if (!previewUrl && previewBox) {
    const previewImage = previewBox.querySelector?.("img");
    if (previewImage?.src) {
      previewUrl = previewImage.src;
    }
  }
  if (previewBox) {
    const previewImage = previewBox.querySelector?.("img");
    if (previewImage?.src?.startsWith("data:image/")) {
      previewUrl = previewImage.src;
    }
  }
  if (!previewUrl) {
    activateShellTab(formRegistry, "img2img", statusNode, "Opened Img2Img");
    return;
  }
  if (!formRegistry?.img2img?.applyPayload) {
    emitFrontendDebugWarning("shell.preview_transfer", "Img2Img applyPayload is unavailable; falling back to tab switch.");
    if (statusNode) {
      statusNode.textContent = "Img2Img form is unavailable.";
    }
    return;
  }
  try {
    const imageDataUrl = await resolvePreviewUrlAsDataUrl(previewUrl);
    if (!imageDataUrl) {
      throw new Error("Preview image is empty.");
    }
    activateShellTab(formRegistry, "img2img", statusNode, "Opened Img2Img");
    formRegistry.img2img.applyPayload({
      mode: "img2img",
      image_asset: "",
      image_data: imageDataUrl,
    });
    if (statusNode) {
      statusNode.textContent = "Sent preview image to Img2Img";
    }
  } catch (_error) {
    emitFrontendDebugWarning("shell.preview_transfer", "Preview transfer failed; falling back to tab switch only.", _error);
    activateShellTab(formRegistry, "img2img", statusNode, "Opened Img2Img");
  }
}

async function trackGenerationRuntime(bootstrapState, promptId, statusNode, runtimeState, previewBox) {
  if (!runtimeState || !promptId) {
    return;
  }
  const runToken = runtimeState.runToken + 1;
  runtimeState.runToken = runToken;
  runtimeState.progressValue = null;
  runtimeState.progressMax = null;
  runtimeState.progressSeen = false;
  runtimeState.previewFrameSeen = false;
  runtimeState.lastPreviewRenderAt = 0;

  const runtimeApi = resolveRuntimeApi(bootstrapState);
  const listeners = [];
  const registerRuntimeListener = (eventName, handler) => {
    if (!runtimeApi?.addEventListener) {
      return;
    }
    runtimeApi.addEventListener(eventName, handler);
    listeners.push([eventName, handler]);
  };
  const unregisterRuntimeListeners = () => {
    if (!runtimeApi?.removeEventListener) {
      return;
    }
    listeners.forEach(([eventName, handler]) => runtimeApi.removeEventListener(eventName, handler));
  };

  registerRuntimeListener("progress", (event) => {
    if (runtimeState.runToken !== runToken) {
      return;
    }
    const detail = event?.detail ?? {};
    if (detail.prompt_id && detail.prompt_id !== promptId) {
      return;
    }
    runtimeState.progressValue = typeof detail.value === "number" ? detail.value : runtimeState.progressValue;
    runtimeState.progressMax = typeof detail.max === "number" ? detail.max : runtimeState.progressMax;
    runtimeState.progressSeen = true;
    statusNode.textContent = formatGenerationProgress("in_progress", runtimeState.progressValue, runtimeState.progressMax);
  });
  const applyPreviewEvent = (event) => {
    if (runtimeState.runToken !== runToken) {
      return;
    }
    const detail = event?.detail ?? {};
    const eventPromptId = extractRuntimePromptId(detail);
    if (eventPromptId && eventPromptId !== promptId) {
      return;
    }
    const blob = extractPreviewBlob(detail);
    if (!blob) {
      return;
    }
    const now = Date.now();
    if (now - (runtimeState.lastPreviewRenderAt || 0) < 120) {
      return;
    }
    runtimeState.lastPreviewRenderAt = now;
    runtimeState.previewFrameSeen = true;
    const previewUrl = URL.createObjectURL(blob);
    setGenerationPreview(runtimeState, previewBox, previewUrl, runtimeState.previewPlaceholder);
  };
  // IMPORTANT: host event names differ across Comfy surfaces; keep both listeners for stable in-sidebar preview updates.
  registerRuntimeListener("b_preview_with_metadata", applyPreviewEvent);
  registerRuntimeListener("b_preview", applyPreviewEvent);

  const startTime = Date.now();
  const maxDurationMs = 5 * 60 * 1000;
  let lastHistoryPollAt = 0;
  let finalStatus = "pending";
  try {
    while (runtimeState.runToken === runToken && Date.now() - startTime < maxDurationMs) {
      const scopedClientId = resolveActiveClientId(bootstrapState);
      const jobResult = await bootstrapState.fetchQueueJobRequest(promptId, scopedClientId);
      if (!jobResult.ok) {
        statusNode.textContent = "Waiting for queue sync...";
        await new Promise((resolve) => setTimeout(resolve, 800));
        continue;
      }
      const queueJob = jobResult.data?.job ?? null;
      if (!queueJob) {
        statusNode.textContent = "Waiting for queue registration...";
        await new Promise((resolve) => setTimeout(resolve, 800));
        continue;
      }

      finalStatus = String(queueJob.status ?? "pending");
      statusNode.textContent = formatGenerationProgress(finalStatus, runtimeState.progressValue, runtimeState.progressMax);
      if (runtimeState.progressSeen && !runtimeState.previewFrameSeen && Date.now() - startTime >= 4000) {
        // CRITICAL: when host runs with --preview-method none, progress updates still arrive but live preview frames never do; keep an explicit diagnostic instead of silent placeholder stalling.
        statusNode.textContent =
          `${formatGenerationProgress(finalStatus, runtimeState.progressValue, runtimeState.progressMax)} | ` +
          "Live preview frames unavailable (host preview may be disabled).";
      }
      if (["completed", "failed", "cancelled"].includes(finalStatus)) {
        break;
      }
      if (Date.now() - lastHistoryPollAt >= 1500) {
        const historyResult = await bootstrapState.fetchPromptHistoryRequest(promptId);
        const previewImage = historyResult.ok ? extractPrimaryHistoryImage(historyResult.data, promptId) : null;
        const previewUrl = buildComfyViewUrl(previewImage);
        if (previewUrl) {
          runtimeState.previewFrameSeen = true;
          setGenerationPreview(runtimeState, previewBox, previewUrl, runtimeState.previewPlaceholder);
        }
        lastHistoryPollAt = Date.now();
      }
      await new Promise((resolve) => setTimeout(resolve, 800));
    }
  } finally {
    unregisterRuntimeListeners();
  }

  if (runtimeState.runToken !== runToken) {
    return;
  }

  if (finalStatus === "completed") {
    const historyResult = await bootstrapState.fetchPromptHistoryRequest(promptId);
    const outputImage = historyResult.ok ? extractPrimaryHistoryImage(historyResult.data, promptId) : null;
    const finalImageUrl = buildComfyViewUrl(outputImage);
    if (finalImageUrl) {
      setGenerationPreview(runtimeState, previewBox, finalImageUrl, runtimeState.previewPlaceholder);
      statusNode.textContent = `Completed: ${promptId}`;
      return;
    }
    statusNode.textContent = `Completed: ${promptId} (no image output found)`;
    return;
  }
  if (finalStatus === "failed") {
    statusNode.textContent = `Generation failed: ${promptId}`;
    return;
  }
  if (finalStatus === "cancelled") {
    statusNode.textContent = `Generation cancelled: ${promptId}`;
    return;
  }
  statusNode.textContent = `Runtime sync timed out: ${promptId}`;
}

async function submitTxt2Img(bootstrapState, elements, statusNode, runtimeState, previewBox) {
  statusNode.textContent = "Submitting txt2img request...";

  const payload = readTxt2ImgPayload(elements);
  const activeClientId = resolveActiveClientId(bootstrapState);
  if (activeClientId) {
    payload.client_id = activeClientId;
  }
  const result = await bootstrapState.submitTxt2ImgRequest(payload);
  if (!result.ok) {
    statusNode.textContent = `Request failed: ${result.data.status}`;
    return;
  }

  const submission = result.data.submission ?? {};
  if (submission.accepted) {
    statusNode.textContent = `Queued prompt ${submission.prompt_id}`;
    void trackGenerationRuntime(
      bootstrapState,
      String(submission.prompt_id ?? ""),
      statusNode,
      runtimeState,
      previewBox,
    );
    return;
  }

  statusNode.textContent = `Preview ready: ${result.data.workflow_kind}`;
}

function readImg2ImgPayload(elements) {
  const batchImages = parseJsonArrayField(elements.batchImagesData?.value ?? "[]");
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
    mode: elements.mode.value,
    batch_images: batchImages,
    width: Number(elements.width.value),
    height: Number(elements.height.value),
    resize_mode: elements.resizeMode.value,
    steps: Number(elements.steps.value),
    cfg_scale: Number(elements.cfgScale.value),
    sampler_name: elements.sampler.value,
    scheduler_name: elements.scheduler.value,
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
    lora_name: elements.loraName.value,
    lora_strength_model: Number(elements.loraStrengthModel.value),
    lora_strength_clip: Number(elements.loraStrengthClip.value),
  };
}

// IMPORTANT: keep A1111-facing mode labels separate from execution mode; sketch/inpaint-upload/batch still route through normalized backend graph lanes.
const IMG2IMG_EXECUTION_MODE_MAP = Object.freeze({
  img2img: "img2img",
  sketch: "img2img",
  inpaint: "inpaint",
  inpaint_sketch: "inpaint",
  inpaint_upload: "inpaint",
  batch: "img2img",
});

function parseJsonArrayField(rawValue) {
  if (typeof rawValue !== "string" || !rawValue.trim()) {
    return [];
  }
  try {
    const parsed = JSON.parse(rawValue);
    return Array.isArray(parsed) ? parsed.filter((entry) => typeof entry === "string" && entry.trim()) : [];
  } catch (_error) {
    emitFrontendDebugWarning("shell.img2img_batch_parse", "Failed to parse batch image JSON field; returning empty list.", _error);
    return [];
  }
}

function resolveImg2ImgExecutionMode(modeValue) {
  const normalized = String(modeValue ?? "").trim().toLowerCase();
  return IMG2IMG_EXECUTION_MODE_MAP[normalized] ?? "img2img";
}

function isImg2ImgBatchMode(modeValue) {
  return String(modeValue ?? "").trim().toLowerCase() === "batch";
}

function syncMaskField(modeInput, maskField, inpaintControls = [], options = {}) {
  const inpaintEnabled = resolveImg2ImgExecutionMode(modeInput.value) === "inpaint";
  const batchMode = isImg2ImgBatchMode(modeInput.value);
  // IMPORTANT: keep mask asset input/upload interactive in every Img2Img mode; users often preload masks before switching to an inpaint execution mode.
  maskField.disabled = false;
  maskField.placeholder = inpaintEnabled ? "required for inpaint" : "optional";
  inpaintControls.forEach((control) => {
    if (!control) {
      return;
    }
    control.disabled = !inpaintEnabled;
  });
  if (options.maskDropzone) {
    options.maskDropzone.hidden = false;
  }
  if (options.maskFileInput) {
    options.maskFileInput.disabled = false;
  }
  if (options.batchPane) {
    options.batchPane.hidden = !batchMode;
  }
  if (options.batchFileInput) {
    options.batchFileInput.disabled = !batchMode;
  }
  if (options.imageAssetField) {
    options.imageAssetField.placeholder = batchMode ? "optional when batch files are loaded" : "required";
  }
  if (options.modeHintNode) {
    if (batchMode) {
      options.modeHintNode.textContent = "Batch mode: upload multiple source files below (first file drives current workflow preview).";
      return;
    }
    if (inpaintEnabled) {
      options.modeHintNode.textContent = "Inpaint family mode: source image plus mask are required.";
      return;
    }
    options.modeHintNode.textContent = "Img2Img/Sketch mode: source image required; mask optional (used when switching to inpaint).";
  }
}

async function submitImg2Img(
  bootstrapState,
  elements,
  statusNode,
  runtimeState,
  previewBox,
  maskCanvasContract = null,
) {
  statusNode.textContent = "Submitting img2img request...";

  const payload = readImg2ImgPayload(elements);
  const maskCanvasReadiness = maskCanvasContract?.getSubmissionReadiness?.() ?? { ok: true };
  if (!maskCanvasReadiness.ok) {
    statusNode.textContent = maskCanvasReadiness.message ?? "Mask canvas is not ready.";
    return;
  }
  const executionMode = resolveImg2ImgExecutionMode(payload.mode);
  const batchImages = Array.isArray(payload.batch_images) ? payload.batch_images : [];
  payload.image_asset = String(payload.image_asset ?? "").trim();
  payload.image_data = String(payload.image_data ?? "").trim();
  payload.mask_asset = String(payload.mask_asset ?? "").trim();
  payload.mask_data = String(payload.mask_data ?? "").trim();
  if (isImg2ImgBatchMode(payload.mode) && !payload.image_asset && !payload.image_data && batchImages.length) {
    // CRITICAL: batch lane still executes through single-workflow translation today; keep deterministic first-image fallback so submission never loses source input.
    payload.image_data = String(batchImages[0] ?? "").trim();
  }
  if (isImg2ImgBatchMode(payload.mode) && !payload.image_asset && !payload.image_data) {
    statusNode.textContent = "Batch mode requires at least one uploaded batch image.";
    return;
  }
  // CRITICAL: keep img2img asset validation on the RookieUI side so missing handles are rejected before entering the host queue.
  if (!payload.image_asset && !payload.image_data) {
    statusNode.textContent = "Image asset or uploaded image is required for img2img.";
    return;
  }
  if (executionMode === "inpaint" && !payload.mask_asset && !payload.mask_data) {
    statusNode.textContent = "Mask asset or uploaded mask is required for inpaint mode.";
    return;
  }
  const activeClientId = resolveActiveClientId(bootstrapState);
  if (activeClientId) {
    payload.client_id = activeClientId;
  }
  const result = await bootstrapState.submitImg2ImgRequest(payload);
  if (!result.ok) {
    statusNode.textContent = `Request failed: ${result.data.status}`;
    return;
  }

  const submission = result.data.submission ?? {};
  if (submission.accepted) {
    statusNode.textContent = `Queued prompt ${submission.prompt_id}`;
    void trackGenerationRuntime(
      bootstrapState,
      String(submission.prompt_id ?? ""),
      statusNode,
      runtimeState,
      previewBox,
    );
    return;
  }

  statusNode.textContent = `Preview ready: ${result.data.workflow_kind}`;
}

function createMiniActionButton(id, text) {
  const button = document.createElement("button");
  button.id = id;
  button.className = "rookieui-shell__mini-action";
  button.type = "button";
  button.textContent = text;
  return button;
}

const A1111_TOOL_EMOJI_MAP = Object.freeze({
  "pi-check-square": "📂",
  "pi-trash": "🗑️",
  "pi-file": "📋",
  "pi-pencil": "🖌️",
  "pi-folder-open": "📂",
  "pi-image": "🖼️",
  "pi-star": "📐",
  "pi-sliders-h": "♻️",
  "pi-images": "🗃️",
});

function resolveToolEmoji(iconToken) {
  if (typeof iconToken !== "string") {
    return "🔹";
  }
  const normalized = iconToken.trim();
  if (!normalized) {
    return "🔹";
  }
  // IMPORTANT: keep A1111/Forge emoji semantics here; replacing this with icon-font classes breaks the target ToolButton parity.
  return A1111_TOOL_EMOJI_MAP[normalized] ?? normalized;
}

function createIconActionButton(id, iconToken, labelText, tone = "neutral") {
  const button = document.createElement("button");
  const safeTone = typeof tone === "string" && tone.trim() ? tone.trim() : "neutral";
  button.id = id;
  button.className = `rookieui-shell__mini-action rookieui-shell__mini-action--icon rookieui-shell__mini-action--tone-${safeTone}`;
  button.type = "button";
  button.title = labelText;
  button.setAttribute("aria-label", labelText);

  const icon = document.createElement("span");
  icon.className = "rookieui-shell__mini-action-icon";
  icon.textContent = resolveToolEmoji(iconToken);
  icon.setAttribute("aria-hidden", "true");
  button.appendChild(icon);
  return button;
}

function activateShellTab(formRegistry, tabId, statusNode, message = "") {
  formRegistry.__shellTabs?.activateTabById?.(tabId);
  if (statusNode && message) {
    statusNode.textContent = message;
  }
}

function buildQuicksettingCard(parent, labelText, controls, id = "") {
  const card = document.createElement("div");
  card.className = "rookieui-shell__quicksetting";
  if (id) {
    card.id = id;
  }
  appendTextElement(card, "span", "rookieui-shell__quicksetting-label", labelText);
  const body = document.createElement("div");
  body.className = "rookieui-shell__quicksetting-body";
  card.appendChild(body);
  const controlList = Array.isArray(controls) ? controls : [controls];
  controlList.forEach((control) => {
    if (control) {
      body.appendChild(control);
    }
  });
  parent.appendChild(card);
  return card;
}

function buildSubtabShell(parent, prefix, definitions) {
  const tabs = document.createElement("div");
  tabs.className = "rookieui-shell__subtabs";
  tabs.id = `${prefix}-tabs`;
  tabs.setAttribute("role", "tablist");
  parent.appendChild(tabs);

  const content = document.createElement("div");
  content.className = "rookieui-shell__subcontent";
  parent.appendChild(content);

  const buttons = [];
  const panes = [];

  const activateTab = (activeIndex) => {
    buttons.forEach((button, index) => {
      const active = index === activeIndex;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
      panes[index].classList.toggle("is-active", active);
      panes[index].hidden = !active;
    });
  };

  definitions.forEach((definition, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.id = `${prefix}-tab-${definition.id}`;
    button.className = "rookieui-shell__subtab";
    button.textContent = definition.label;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", `${prefix}-pane-${definition.id}`);
    tabs.appendChild(button);
    buttons.push(button);

    const pane = document.createElement("div");
    pane.id = `${prefix}-pane-${definition.id}`;
    pane.className = "rookieui-shell__subpane";
    pane.setAttribute("role", "tabpanel");
    pane.setAttribute("aria-labelledby", button.id);
    pane.hidden = true;
    content.appendChild(pane);
    panes.push(pane);
    definition.render(pane);

    button.addEventListener("click", () => {
      activateTab(index);
    });

    button.setAttribute("aria-selected", "false");
    button.tabIndex = -1;
  });

  activateTab(0);
}

function buildPlaceholderSection(parent, title, message, id = "") {
  const section = document.createElement("section");
  section.className = "rookieui-shell__section rookieui-shell__section--soft";
  if (id) {
    section.id = id;
  }
  parent.appendChild(section);
  appendTextElement(section, "h4", "rookieui-shell__section-title", title);
  appendTextElement(section, "p", "rookieui-shell__status", message);
  return section;
}

function buildSelectionLibrary(parent, title, values, activeValue, onSelect, idPrefix, options = {}) {
  const section = document.createElement("section");
  section.className = "rookieui-shell__section rookieui-shell__section--soft";
  parent.appendChild(section);
  appendTextElement(section, "h4", "rookieui-shell__section-title", title);
  const list = document.createElement("div");
  list.className = "rookieui-shell__library";
  section.appendChild(list);
  const getLabel = options.getLabel ?? ((value) => value);
  const emptyMessage = options.emptyMessage ?? "No host items available yet.";

  if (!values.length) {
    appendTextElement(section, "p", "rookieui-shell__status", emptyMessage);
    return;
  }

  values.forEach((value, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.id = `${idPrefix}-${index}`;
    button.className = "rookieui-shell__library-item";
    button.textContent = getLabel(value);
    button.dataset.value = value;
    button.dataset.active = String(value === activeValue());
    button.addEventListener("click", () => {
      onSelect(value);
      Array.from(list.children).forEach((node) => {
        node.dataset.active = String(node.dataset.value === value);
      });
    });
    list.appendChild(button);
  });
}

function formatModelAssetLabel(value) {
  return String(value).replace(/\.(safetensors|pt|bin)$/i, "");
}

function appendPromptToken(textarea, token) {
  // IMPORTANT: keep token injection centralized; prompt libraries must update the real submit path, not decorative mirrors.
  const trimmedToken = String(token ?? "").trim();
  if (!textarea || !trimmedToken) {
    return;
  }

  const currentValue = textarea.value.trim();
  if (!currentValue) {
    textarea.value = trimmedToken;
    syncBoundControls([textarea]);
    return;
  }

  const separator = currentValue.endsWith(",") ? " " : ", ";
  textarea.value = `${currentValue}${separator}${trimmedToken}`;
  syncBoundControls([textarea]);
}

function buildEmbeddingLibrary(parent, title, values, promptInput, idPrefix) {
  buildSelectionLibrary(
    parent,
    title,
    values,
    () => "",
    (value) => {
      appendPromptToken(promptInput, `embedding:${value}`);
    },
    idPrefix,
    {
      getLabel: formatModelAssetLabel,
      emptyMessage: "No host textual inversion embeddings available yet.",
    },
  );
}

function buildLoraLibrary(parent, title, values, elements, idPrefix, statusNode) {
  const updateStatus = () => {
    const activeLora = elements.loraName.value;
    statusNode.textContent = activeLora
      ? `Selected LoRA: ${formatModelAssetLabel(activeLora)} (${elements.loraStrengthModel.value}/${elements.loraStrengthClip.value})`
      : "No LoRA selected. Generation will use the base checkpoint only.";
  };

  buildSelectionLibrary(
    parent,
    title,
    values,
    () => elements.loraName.value,
    (value) => {
      elements.loraName.value = value;
      updateStatus();
    },
    idPrefix,
    {
      getLabel: formatModelAssetLabel,
      emptyMessage: "No host LoRA files available yet.",
    },
  );

  elements.loraStrengthModel.addEventListener("change", updateStatus);
  elements.loraStrengthClip.addEventListener("change", updateStatus);
  updateStatus();
}

function buildTxt2ImgSection(parent, bootstrapState, formRegistry) {
  const section = document.createElement("section");
  section.className = "rookieui-shell__forge-pane";
  parent.appendChild(section);

  const form = document.createElement("form");
  form.className = "rookieui-shell__form rookieui-shell__forge-form";
  form.id = "rookieui-txt2img-form";
  section.appendChild(form);

  const profileLookup = buildProfileLookup(bootstrapState.capabilities);
  const presetLookup = buildPresetLookup(bootstrapState.presets?.presets ?? []);
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
  const presetOptions = (bootstrapState.presets?.presets ?? []).map((preset) => ({
    value: preset.id,
    label: preset.title,
  }));
  const allPresets = bootstrapState.presets?.presets ?? [];
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
  let txt2imgPreviewBox = null;

  const elements = {
    prompt: createTextarea("rookieui-prompt", "", 4, {
      className: "rookieui-shell__textarea rookieui-shell__textarea--prompt",
    }),
    negativePrompt: createTextarea("rookieui-negative-prompt", "", 3, {
      className: "rookieui-shell__textarea rookieui-shell__textarea--negative",
    }),
    preset: createSelect("rookieui-preset", presetOptions, initialPreset),
    profileState: createSelect(
      "rookieui-profile",
      profiles.map((profile) => ({ value: profile.id, label: profile.title })),
      initialProfile,
    ),
    checkpoint: createSelect(
      "rookieui-checkpoint",
      inventory.checkpoints.map((value) => ({ value, label: value })),
      inventory.default_checkpoint,
    ),
    vae: createSelect(
      "rookieui-vae",
      inventory.vae.map((value) => ({ value, label: value })),
      inventory.default_vae,
    ),
    textEncoder: createSelect(
      "rookieui-text-encoder",
      inventory.text_encoders.map((value) => ({ value, label: value })),
      inventory.default_text_encoder,
    ),
    lowBits: createSelect(
      "rookieui-low-bits",
      dtypeProfiles.map((profile) => ({ value: profile.id, label: profile.title })),
      initialLowBits,
    ),
    loraName: createInput("text", "rookieui-lora-name", ""),
    loraStrengthModel: createInput("number", "rookieui-lora-strength-model", "1", {
      step: 0.05,
      min: -4,
      max: 4,
      inputMode: "decimal",
    }),
    loraStrengthClip: createInput("number", "rookieui-lora-strength-clip", "1", {
      step: 0.05,
      min: -4,
      max: 4,
      inputMode: "decimal",
    }),
    width: createInput("number", "rookieui-width", "512", { step: 8, min: 64, max: 2048 }),
    widthSlider: createRangeInput("rookieui-width-slider", "512", { step: 8, min: 64, max: 2048 }),
    height: createInput("number", "rookieui-height", "512", { step: 8, min: 64, max: 2048 }),
    heightSlider: createRangeInput("rookieui-height-slider", "512", { step: 8, min: 64, max: 2048 }),
    steps: createInput("number", "rookieui-steps", "28", { step: 1, min: 1, max: 150 }),
    stepsSlider: createRangeInput("rookieui-steps-slider", "28", { step: 1, min: 1, max: 150 }),
    cfgScale: createInput("number", "rookieui-cfg-scale", "7", {
      step: 0.01,
      min: 1,
      max: 30,
      inputMode: "decimal",
    }),
    cfgScaleSlider: createRangeInput("rookieui-cfg-scale-slider", "7", { step: 0.1, min: 1, max: 30 }),
    sampler: createSelect(
      "rookieui-sampler",
      samplerCatalog.map((entry) => ({ value: entry.id, label: entry.title })),
      initialSampler,
    ),
    scheduler: createSelect(
      "rookieui-scheduler",
      schedulerCatalog.map((entry) => ({ value: entry.id, label: entry.title })),
      initialScheduler,
    ),
    seed: createInput("number", "rookieui-seed", "-1", { step: 1 }),
    seedExtra: createCheckbox("rookieui-seed-extra", false),
    batchSize: createInput("number", "rookieui-batch-size", "1", { step: 1, min: 1, max: 8 }),
    batchSizeSlider: createRangeInput("rookieui-batch-size-slider", "1", { step: 1, min: 1, max: 8 }),
    batchCount: createInput("number", "rookieui-batch-count", "1", { step: 1, min: 1, max: 32 }),
    batchCountSlider: createRangeInput("rookieui-batch-count-slider", "1", { step: 1, min: 1, max: 32 }),
    clipSkip: createInput("number", "rookieui-clip-skip", "1", { step: 1, min: 1, max: 12 }),
    clipSkipSlider: createRangeInput("rookieui-clip-skip-slider", "1", { step: 1, min: 1, max: 12 }),
    hiresEnabled: createCheckbox("rookieui-hires-enabled", false),
    hiresScale: createInput("number", "rookieui-hires-scale", "1.5", {
      step: 0.01,
      min: 1,
      max: 2.5,
      inputMode: "decimal",
    }),
    hiresSteps: createInput("number", "rookieui-hires-steps", "14", { step: 1, min: 1, max: 150 }),
    hiresDenoise: createInput("number", "rookieui-hires-denoise", "0.35", {
      step: 0.01,
      min: 0.1,
      max: 1,
      inputMode: "decimal",
    }),
    hiresScaleSlider: createRangeInput("rookieui-hires-scale-slider", "1.5", { step: 0.1, min: 1, max: 2.5 }),
    hiresStepsSlider: createRangeInput("rookieui-hires-steps-slider", "14", { step: 1, min: 1, max: 150 }),
    hiresDenoiseSlider: createRangeInput("rookieui-hires-denoise-slider", "0.35", {
      step: 0.05,
      min: 0.1,
      max: 1,
    }),
    hiresUpscaleMethod: createSelect(
      "rookieui-hires-upscale-method",
      [
        { value: "bislerp", label: "Bislerp" },
        { value: "bicubic", label: "Bicubic" },
        { value: "bilinear", label: "Bilinear" },
        { value: "nearest-exact", label: "Nearest Exact" },
        { value: "area", label: "Area" },
      ],
      "bislerp",
    ),
  };
  bindSliderPair(elements.width, elements.widthSlider);
  bindSliderPair(elements.height, elements.heightSlider);
  bindSliderPair(elements.steps, elements.stepsSlider);
  bindSliderPair(elements.cfgScale, elements.cfgScaleSlider);
  bindSliderPair(elements.batchSize, elements.batchSizeSlider);
  bindSliderPair(elements.batchCount, elements.batchCountSlider);
  bindSliderPair(elements.clipSkip, elements.clipSkipSlider);
  bindSliderPair(elements.hiresScale, elements.hiresScaleSlider);
  bindSliderPair(elements.hiresSteps, elements.hiresStepsSlider);
  bindSliderPair(elements.hiresDenoise, elements.hiresDenoiseSlider);
  elements.prompt.placeholder = "Prompt\n(Ctrl+Enter to Generate ; Alt+Enter to Skip ; Esc to Interrupt)";
  elements.negativePrompt.placeholder =
    "Negative Prompt\n(Ctrl+Enter to Generate ; Alt+Enter to Skip ; Esc to Interrupt)";

  const quicksettings = document.createElement("div");
  quicksettings.className = "rookieui-shell__quicksettings";
  quicksettings.id = "rookieui-txt2img-quicksettings";
  form.appendChild(quicksettings);
  buildQuicksettingCard(quicksettings, "UI Preset", elements.preset, "rookieui-preset-quicksetting");
  buildQuicksettingCard(quicksettings, "Checkpoint", elements.checkpoint, "rookieui-checkpoint-quicksetting");
  const modulesQuicksetting = buildQuicksettingCard(
    quicksettings,
    "VAE / Text Encoder",
    [elements.vae, elements.textEncoder],
    "rookieui-modules-quicksetting",
  );
  const modulesQuicksettingLabel = modulesQuicksetting.querySelector(".rookieui-shell__quicksetting-label");
  buildQuicksettingCard(
    quicksettings,
    "Diffusion in Low Bits",
    elements.lowBits,
    "rookieui-low-bits-quicksetting",
  );

  const promptBand = document.createElement("div");
  promptBand.className = "rookieui-shell__prompt-band";
  form.appendChild(promptBand);

  const promptStack = document.createElement("div");
  promptStack.className = "rookieui-shell__prompt-stack";
  promptBand.appendChild(promptStack);
  createPromptField(promptStack, "Prompt", elements.prompt, "rookieui-prompt-counter");
  createPromptField(promptStack, "Negative Prompt", elements.negativePrompt, "rookieui-negative-prompt-counter");

  const actionRail = document.createElement("div");
  actionRail.className = "rookieui-shell__action-rail";
  promptBand.appendChild(actionRail);

  const submitButton = document.createElement("button");
  submitButton.id = "rookieui-txt2img-submit";
  submitButton.className = "rookieui-shell__button rookieui-shell__button--hero";
  submitButton.type = "submit";
  submitButton.textContent = "Generate";
  actionRail.appendChild(submitButton);

  const actionRow = document.createElement("div");
  actionRow.className = "rookieui-shell__mini-actions";
  actionRail.appendChild(actionRow);

  const queueIconButton = createIconActionButton(
    "rookieui-txt2img-open-queue-icon",
    "pi-check-square",
    "Open Queue",
    "queue",
  );
  queueIconButton.addEventListener("click", () => {
    activateShellTab(formRegistry, "queue", statusNode, "Opened queue view");
  });
  actionRow.appendChild(queueIconButton);

  const clearButton = createIconActionButton("rookieui-txt2img-clear", "pi-trash", "Clear Prompt Fields", "danger");
  clearButton.addEventListener("click", () => {
    elements.prompt.value = "";
    elements.negativePrompt.value = "";
    syncBoundControls([elements.prompt, elements.negativePrompt]);
    statusNode.textContent = "Cleared prompt fields";
  });
  actionRow.appendChild(clearButton);

  const pngInfoButton = createIconActionButton("rookieui-txt2img-open-pnginfo", "pi-file", "Open PNG Info", "metadata");
  pngInfoButton.addEventListener("click", () => {
    activateShellTab(formRegistry, "pnginfo", statusNode, "Opened PNG Info");
  });
  actionRow.appendChild(pngInfoButton);

  const actionTargetRow = document.createElement("div");
  actionTargetRow.className = "rookieui-shell__action-target-row";
  actionRail.appendChild(actionTargetRow);

  const actionTarget = createSelect(
    "rookieui-txt2img-action-target",
    [
      { value: "queue", label: "Queue / History" },
      { value: "pnginfo", label: "PNG Info" },
      { value: "img2img", label: "Send to Img2Img" },
      { value: "extras", label: "Extras" },
    ],
    "queue",
  );
  actionTarget.classList.add("rookieui-shell__action-target");
  actionTargetRow.appendChild(actionTarget);

  const actionApplyButton = createIconActionButton(
    "rookieui-txt2img-apply-action-target",
    "pi-pencil",
    "Apply Action",
    "transfer",
  );
  actionApplyButton.addEventListener("click", () => {
    const actionLabels = {
      queue: "Opened queue view",
      pnginfo: "Opened PNG Info",
      img2img: "Sent preview image to Img2Img",
      extras: "Opened Extras",
    };
    if (actionTarget.value === "img2img") {
      void transferPreviewToImg2Img(formRegistry, runtimeState, statusNode, txt2imgPreviewBox);
      return;
    }
    activateShellTab(formRegistry, actionTarget.value, statusNode, actionLabels[actionTarget.value] ?? "Action applied");
  });
  actionTargetRow.appendChild(actionApplyButton);

  const statusNode = document.createElement("p");
  statusNode.id = "rookieui-txt2img-status";
  statusNode.className = "rookieui-shell__status rookieui-shell__status--inline";
  statusNode.textContent = "Idle";
  actionRail.appendChild(statusNode);

  updateFormFromPreset(presetLookup, initialPreset, elements, profileLookup);
  syncFamilyAwareModuleQuicksetting(
    profileLookup,
    elements.profileState.value,
    modulesQuicksetting,
    modulesQuicksettingLabel,
    elements.textEncoder,
  );
  elements.preset.addEventListener("change", () => {
    updateFormFromPreset(presetLookup, elements.preset.value, elements, profileLookup);
    syncFamilyAwareModuleQuicksetting(
      profileLookup,
      elements.profileState.value,
      modulesQuicksetting,
      modulesQuicksettingLabel,
      elements.textEncoder,
    );
  });

  const subtabHost = document.createElement("div");
  subtabHost.className = "rookieui-shell__workspace-frame";
  form.appendChild(subtabHost);

  buildSubtabShell(subtabHost, "rookieui-txt2img-workspace", [
    {
      id: "generation",
      label: "Generation",
      render: (pane) => {
        const workspace = document.createElement("div");
        workspace.className = "rookieui-shell__workspace-grid";
        pane.appendChild(workspace);

        const leftColumn = document.createElement("div");
        leftColumn.className = "rookieui-shell__workspace-column";
        workspace.appendChild(leftColumn);

        const samplingSection = document.createElement("section");
        samplingSection.className = "rookieui-shell__section rookieui-shell__section--soft";
        leftColumn.appendChild(samplingSection);
        appendTextElement(samplingSection, "h4", "rookieui-shell__section-title", "Generation");

        const samplingGrid = document.createElement("div");
        samplingGrid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
        samplingSection.appendChild(samplingGrid);
        createField(samplingGrid, "Sampling Method", elements.sampler);
        createField(samplingGrid, "Schedule Type", elements.scheduler);
        createSliderField(samplingGrid, "Sampling Steps", elements.steps, elements.stepsSlider, "rookieui-steps-field");
        createSliderField(samplingGrid, "CFG Scale", elements.cfgScale, elements.cfgScaleSlider, "rookieui-cfg-scale-field");
        createSliderField(samplingGrid, "Width", elements.width, elements.widthSlider, "rookieui-width-field");
        createSliderField(samplingGrid, "Height", elements.height, elements.heightSlider, "rookieui-height-field");
        createSliderField(samplingGrid, "Batch Count", elements.batchCount, elements.batchCountSlider, "rookieui-batch-count-field");
        createSliderField(samplingGrid, "Batch Size", elements.batchSize, elements.batchSizeSlider, "rookieui-batch-size-field");
        createSliderField(samplingGrid, "Clip Skip", elements.clipSkip, elements.clipSkipSlider, "rookieui-clip-skip-field");
        createSeedControlField(samplingGrid, "Seed", elements.seed, elements.seedExtra, "rookieui-seed-field");

        const advancedGrid = createHiresFixSection(
          leftColumn,
          "rookieui-advanced-controls",
          elements.hiresEnabled,
        );
        createSliderField(advancedGrid, "Hires Scale", elements.hiresScale, elements.hiresScaleSlider, "rookieui-hires-scale-field");
        createSliderField(advancedGrid, "Hires Steps", elements.hiresSteps, elements.hiresStepsSlider, "rookieui-hires-steps-field");
        createSliderField(advancedGrid, "Hires Denoise", elements.hiresDenoise, elements.hiresDenoiseSlider, "rookieui-hires-denoise-field");
        createField(advancedGrid, "Upscale Method", elements.hiresUpscaleMethod);

        const rightColumn = document.createElement("div");
        rightColumn.className = "rookieui-shell__workspace-column";
        workspace.appendChild(rightColumn);

        const previewSection = document.createElement("section");
        previewSection.className = "rookieui-shell__section rookieui-shell__section--soft";
        rightColumn.appendChild(previewSection);
        appendTextElement(previewSection, "h4", "rookieui-shell__section-title", "Preview");

        const previewBox = document.createElement("div");
        previewBox.className = "rookieui-shell__preview-box";
        previewBox.id = "rookieui-txt2img-preview";
        previewSection.appendChild(previewBox);
        txt2imgPreviewBox = previewBox;
        appendTextElement(
          previewBox,
          "span",
          "rookieui-shell__preview-placeholder",
          runtimeState.previewPlaceholder,
        );

        const previewToolbar = document.createElement("div");
        previewToolbar.className = "rookieui-shell__preview-toolbar";
        previewSection.appendChild(previewToolbar);

        const previewActions = [
          {
            id: "rookieui-txt2img-preview-queue",
            iconClass: "pi-folder-open",
            label: "Queue History",
            tabId: "queue",
            message: "Opened queue history",
            tone: "queue",
          },
          {
            id: "rookieui-txt2img-preview-pnginfo",
            iconClass: "pi-file",
            label: "PNG Info",
            tabId: "pnginfo",
            message: "Opened PNG Info",
            tone: "metadata",
          },
          {
            id: "rookieui-txt2img-preview-img2img",
            iconClass: "pi-image",
            label: "Send to Img2Img",
            tabId: "img2img",
            message: "Opened Img2Img",
            tone: "transfer",
          },
          {
            id: "rookieui-txt2img-preview-extras",
            iconClass: "pi-star",
            label: "Extras",
            tabId: "extras",
            message: "Opened Extras",
            tone: "extras",
          },
          {
            id: "rookieui-txt2img-preview-return",
            iconClass: "pi-sliders-h",
            label: "Generation Controls",
            tabId: "txt2img",
            message: "Returned to txt2img controls",
            tone: "neutral",
          },
          {
            id: "rookieui-txt2img-preview-history",
            iconClass: "pi-images",
            label: "History",
            tabId: "queue",
            message: "Opened queue history",
            tone: "queue",
          },
        ];

        previewActions.forEach((action) => {
          const button = createIconActionButton(action.id, action.iconClass, action.label, action.tone);
          button.addEventListener("click", async () => {
            if (action.id === "rookieui-txt2img-preview-img2img") {
              await transferPreviewToImg2Img(formRegistry, runtimeState, statusNode, previewBox);
              return;
            }
            activateShellTab(formRegistry, action.tabId, statusNode, action.message);
          });
          previewToolbar.appendChild(button);
        });
      },
    },
    {
      id: "textual-inversion",
      label: "Textual Inversion",
      render: (pane) => {
        const infoSection = document.createElement("section");
        infoSection.className = "rookieui-shell__section rookieui-shell__section--soft";
        infoSection.id = "rookieui-txt2img-textual-inversion-pane";
        pane.appendChild(infoSection);
        appendTextElement(infoSection, "h4", "rookieui-shell__section-title", "Textual Inversion");
        appendTextElement(
          infoSection,
          "p",
          "rookieui-shell__status",
          "Click an embedding to inject a Comfy-compatible embedding token into the prompt.",
        );
        buildEmbeddingLibrary(
          pane,
          "Available Embeddings",
          inventory.embeddings ?? [],
          elements.prompt,
          "rookieui-txt2img-embedding-item",
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
          "rookieui-txt2img-checkpoint-item",
        ),
    },
    {
      id: "lora",
      label: "Lora",
      render: (pane) => {
        const loraSection = document.createElement("section");
        loraSection.className = "rookieui-shell__section rookieui-shell__section--soft";
        loraSection.id = "rookieui-txt2img-lora-pane";
        pane.appendChild(loraSection);
        appendTextElement(loraSection, "h4", "rookieui-shell__section-title", "LoRA");
        appendTextElement(
          loraSection,
          "p",
          "rookieui-shell__status",
          "Select one host LoRA to inject through a workflow LoraLoader seam during generation.",
        );

        const loraGrid = document.createElement("div");
        loraGrid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
        loraSection.appendChild(loraGrid);
        createField(loraGrid, "Model Strength", elements.loraStrengthModel);
        createField(loraGrid, "CLIP Strength", elements.loraStrengthClip);

        const loraStatus = document.createElement("p");
        loraStatus.className = "rookieui-shell__status";
        loraStatus.id = "rookieui-txt2img-lora-status";
        loraSection.appendChild(loraStatus);

        const clearButton = createActionButton("rookieui-txt2img-clear-lora", "Clear LoRA");
        clearButton.addEventListener("click", () => {
          elements.loraName.value = "";
          loraStatus.textContent = "No LoRA selected. Generation will use the base checkpoint only.";
          pane.querySelectorAll(".rookieui-shell__library-item").forEach((node) => {
            node.dataset.active = "false";
          });
        });
        loraSection.appendChild(clearButton);

        buildLoraLibrary(
          pane,
          "Available LoRAs",
          inventory.loras ?? [],
          elements,
          "rookieui-txt2img-lora-item",
          loraStatus,
        );
      },
    },
  ]);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitTxt2Img(bootstrapState, elements, statusNode, runtimeState, txt2imgPreviewBox);
  });

  const txt2imgStateLock = installPaneStateLock(formRegistry, "txt2img", elements, () => {
    // IMPORTANT: tab restore must re-apply Clip Skip editability; otherwise old profile lock state can persist and look frozen.
    syncClipSkipAvailability(profileLookup, elements.profileState.value, elements.clipSkip, elements.clipSkipSlider);
    syncFamilyAwareModuleQuicksetting(
      profileLookup,
      elements.profileState.value,
      modulesQuicksetting,
      modulesQuicksettingLabel,
      elements.textEncoder,
    );
  });

  formRegistry.txt2img = {
    applyPayload(payload) {
      applyPayloadToElements(elements, payload, {
        prompt: "prompt",
        negative_prompt: "negativePrompt",
        profile: "profileState",
        checkpoint_name: "checkpoint",
        vae_name: "vae",
        text_encoder_name: "textEncoder",
        dtype_profile: "lowBits",
        width: "width",
        height: "height",
        steps: "steps",
        cfg_scale: "cfgScale",
        sampler_name: "sampler",
        scheduler_name: "scheduler",
        seed: "seed",
        seed_extra: "seedExtra",
        batch_count: "batchCount",
        batch_size: "batchSize",
        clip_skip: "clipSkip",
        hires_enabled: "hiresEnabled",
        hires_scale: "hiresScale",
        hires_steps: "hiresSteps",
        hires_denoise: "hiresDenoise",
        hires_upscale_method: "hiresUpscaleMethod",
        lora_name: "loraName",
        lora_strength_model: "loraStrengthModel",
        lora_strength_clip: "loraStrengthClip",
      });
      const resolvedPresetId = findPresetIdForProfile(allPresets, elements.profileState.value);
      if (resolvedPresetId) {
        setElementValue(elements.preset, resolvedPresetId);
      }
      // IMPORTANT: PNG Info / history apply may change profile; always re-sync Clip Skip editability after payload apply.
      syncClipSkipAvailability(profileLookup, elements.profileState.value, elements.clipSkip, elements.clipSkipSlider);
      syncFamilyAwareModuleQuicksetting(
        profileLookup,
        elements.profileState.value,
        modulesQuicksetting,
        modulesQuicksettingLabel,
        elements.textEncoder,
      );
      syncBoundControls(Object.values(elements));
      txt2imgStateLock.capture();
    },
  };

  return {
    onActivate: txt2imgStateLock.restore,
    onDeactivate: txt2imgStateLock.capture,
  };
}

function buildImg2ImgSection(parent, bootstrapState, formRegistry) {
  const section = document.createElement("section");
  section.className = "rookieui-shell__forge-pane";
  parent.appendChild(section);

  const form = document.createElement("form");
  form.className = "rookieui-shell__form rookieui-shell__forge-form";
  form.id = "rookieui-img2img-form";
  section.appendChild(form);

  const profileLookup = buildProfileLookup(bootstrapState.capabilities);
  const presetLookup = buildPresetLookup(bootstrapState.presets?.presets ?? []);
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
  const presetOptions = (bootstrapState.presets?.presets ?? []).map((preset) => ({
    value: preset.id,
    label: preset.title,
  }));
  const allPresets = bootstrapState.presets?.presets ?? [];
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
    maskDropzone: null,
    maskFileInput: null,
    batchPane: null,
    batchFileInput: null,
    batchStatusNode: null,
    maskEditor: null,
  };

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
  };
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
  createPromptField(
    promptStack,
    "Negative Prompt",
    elements.negativePrompt,
    "rookieui-img2img-negative-prompt-counter",
  );

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

  updateFormFromPreset(presetLookup, initialPreset, elements, profileLookup);
  syncFamilyAwareModuleQuicksetting(
    profileLookup,
    elements.profileState.value,
    modulesQuicksetting,
    modulesQuicksettingLabel,
    elements.textEncoder,
  );
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
  const syncImg2ImgModeSurface = () => {
    syncMaskField(elements.mode, elements.maskAsset, inpaintModeControls, {
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
  };
  syncImg2ImgModeSurface();
  elements.preset.addEventListener("change", () => {
    updateFormFromPreset(presetLookup, elements.preset.value, elements, profileLookup);
    syncFamilyAwareModuleQuicksetting(
      profileLookup,
      elements.profileState.value,
      modulesQuicksetting,
      modulesQuicksettingLabel,
      elements.textEncoder,
    );
  });
  elements.mode.addEventListener("change", () => {
    syncImg2ImgModeSurface();
  });

  const subtabHost = document.createElement("div");
  subtabHost.className = "rookieui-shell__workspace-frame";
  form.appendChild(subtabHost);

  buildSubtabShell(subtabHost, "rookieui-img2img-workspace", [
    {
      id: "generation",
      label: "Generation",
      render: (pane) => {
        const workspace = document.createElement("div");
        workspace.className = "rookieui-shell__workspace-grid";
        pane.appendChild(workspace);

        const leftColumn = document.createElement("div");
        leftColumn.className = "rookieui-shell__workspace-column";
        workspace.appendChild(leftColumn);

        const generationSection = document.createElement("section");
        generationSection.className = "rookieui-shell__section rookieui-shell__section--soft";
        leftColumn.appendChild(generationSection);
        appendTextElement(generationSection, "h4", "rookieui-shell__section-title", "Generation");

        const generationGrid = document.createElement("div");
        generationGrid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
        generationSection.appendChild(generationGrid);
        createField(generationGrid, "Sampling Method", elements.sampler);
        createField(generationGrid, "Schedule Type", elements.scheduler);
        createSliderField(
          generationGrid,
          "Width",
          elements.width,
          elements.widthSlider,
          "rookieui-img2img-width-field",
        );
        createSliderField(
          generationGrid,
          "Height",
          elements.height,
          elements.heightSlider,
          "rookieui-img2img-height-field",
        );
        createField(generationGrid, "Resize Mode", elements.resizeMode);
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
        createSliderField(
          generationGrid,
          "Denoise",
          elements.denoiseStrength,
          elements.denoiseStrengthSlider,
          "rookieui-img2img-denoise-field",
        );
        createSliderField(
          generationGrid,
          "Grow Mask",
          elements.growMaskBy,
          elements.growMaskBySlider,
          "rookieui-img2img-grow-mask-field",
        );
        createSliderField(
          generationGrid,
          "Batch Size",
          elements.batchSize,
          elements.batchSizeSlider,
          "rookieui-img2img-batch-size-field",
        );
        createSliderField(
          generationGrid,
          "Clip Skip",
          elements.clipSkip,
          elements.clipSkipSlider,
          "rookieui-img2img-clip-skip-field",
        );
        createSeedControlField(
          generationGrid,
          "Seed",
          elements.seed,
          elements.seedExtra,
          "rookieui-img2img-seed-field",
        );
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

        const hiresGrid = createHiresFixSection(
          leftColumn,
          "rookieui-img2img-hires-controls",
          elements.hiresEnabled,
        );
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

        const imageDropzone = document.createElement("label");
        imageDropzone.className = "rookieui-shell__dropzone";
        imageDropzone.id = "rookieui-img2img-image-dropzone";
        uploadGrid.appendChild(imageDropzone);
        appendTextElement(imageDropzone, "span", "rookieui-shell__dropzone-icon", "⇪");
        appendTextElement(imageDropzone, "span", "rookieui-shell__dropzone-text", "Upload Img2Img source image");
        const imageFileInput = createInput("file", "rookieui-img2img-image-file", "", {
          className: "rookieui-shell__file-input",
        });
        imageFileInput.accept = "image/png,image/webp,image/jpeg";
        imageDropzone.appendChild(imageFileInput);

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
        const maskEditor = createImg2ImgMaskCanvasEditor({
          idPrefix: "rookieui-img2img-mask-editor",
          parent: assetSection,
          modeInput: elements.mode,
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

        attachDropzoneHandlers(imageDropzone, imageFileInput, async (file) => {
          const imageData = await readFileAsDataUrl(file);
          elements.imageData.value = imageData;
          elements.imageAsset.value = "";
          img2imgMaskCanvasContract.refreshSourceBinding();
          setPreviewContent(assetPreview, imageData, runtimeState.previewPlaceholder);
          statusNode.textContent = `Loaded source image: ${file.name}`;
          syncBoundControls([elements.imageData, elements.imageAsset]);
          await img2imgModeUi.maskEditor?.refreshFromInputs();
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
        createField(loraGrid, "Model Strength", elements.loraStrengthModel);
        createField(loraGrid, "CLIP Strength", elements.loraStrengthClip);

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

        buildLoraLibrary(
          pane,
          "Available LoRAs",
          inventory.loras ?? [],
          elements,
          "rookieui-img2img-lora-item",
          loraStatus,
        );
      },
    },
  ]);

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
        sampler_name: "sampler",
        scheduler_name: "scheduler",
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
        lora_name: "loraName",
        lora_strength_model: "loraStrengthModel",
        lora_strength_clip: "loraStrengthClip",
      });
      if (Array.isArray(payload.batch_images)) {
        elements.batchImagesData.value = JSON.stringify(payload.batch_images);
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
      syncImg2ImgModeSurface();
      img2imgMaskCanvasContract.refreshSourceBinding();
      img2imgMaskCanvasContract.handleExternalMaskMutation();
      img2imgModeUi.maskEditor?.refreshFromInputs();
      const appliedImageData = String(elements.imageData.value ?? "").trim();
      const appliedBatchImages = parseJsonArrayField(elements.batchImagesData.value);
      const previewImageData =
        appliedImageData || (isImg2ImgBatchMode(elements.mode.value) ? String(appliedBatchImages[0] ?? "") : "");
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
  };

  return {
    onActivate: img2imgStateLock.restore,
    onDeactivate: img2imgStateLock.capture,
  };
}

function setPreviewContent(previewBox, imageDataUrl, placeholderText) {
  if (!previewBox) {
    return;
  }
  const currentImage = previewBox.querySelector(".rookieui-shell__preview-image");
  const currentPlaceholder = previewBox.querySelector(".rookieui-shell__preview-placeholder");
  if (imageDataUrl) {
    let image = currentImage;
    if (!image) {
      image = document.createElement("img");
      image.className = "rookieui-shell__preview-image";
      image.alt = "RookieUI preview image";
      previewBox.appendChild(image);
    }
    if (currentPlaceholder) {
      currentPlaceholder.remove();
    }
    if (image.src !== imageDataUrl) {
      image.src = imageDataUrl;
    }
    return;
  }
  if (currentImage) {
    currentImage.remove();
  }
  if (currentPlaceholder) {
    currentPlaceholder.textContent = placeholderText;
    return;
  }
  appendTextElement(previewBox, "span", "rookieui-shell__preview-placeholder", placeholderText);
}

function updatePngInfoApplyButtons(state, buttons) {
  const applyTargets = state.inspectionResult?.apply_targets ?? [];
  const isA1111 = state.inspectionResult?.source_type === "a1111";
  buttons.txt2img.disabled = !(isA1111 && applyTargets.includes("txt2img"));
  buttons.img2img.disabled = !(isA1111 && applyTargets.includes("img2img"));
}

async function inspectPngInfo(bootstrapState, state, statusNode, detailNodes, buttons) {
  statusNode.textContent = "Inspecting PNG metadata...";
  setListVisibility(detailNodes.unsupportedHeading, detailNodes.unsupported, []);
  setListVisibility(detailNodes.warningsHeading, detailNodes.warnings, []);
  setPngInfoSummaryVisibility(detailNodes.summary, null);

  const requestPayload = {};
  if (state.imageData) {
    requestPayload.image_data = state.imageData;
  }

  const result = await bootstrapState.inspectPngInfoRequest(requestPayload);
  if (!result.ok) {
    state.inspectionResult = null;
    updatePngInfoApplyButtons(state, buttons);
    statusNode.textContent = `Request failed: ${result.data.status}`;
    return;
  }

  state.inspectionResult = result.data;
  setListVisibility(detailNodes.unsupportedHeading, detailNodes.unsupported, result.data.unsupported_fields ?? []);
  setListVisibility(detailNodes.warningsHeading, detailNodes.warnings, result.data.warnings ?? []);
  setPngInfoSummaryVisibility(detailNodes.summary, result.data);
  updatePngInfoApplyButtons(state, buttons);
  if (result.data.source_type === "comfyui") {
    statusNode.textContent = "ComfyUI metadata loaded for inspection only.";
    return;
  }
  statusNode.textContent = `Ready to apply ${result.data.target_form} fields`;
}

function applyPngInfoResult(formRegistry, targetKey, state, statusNode) {
  const inspectionResult = state.inspectionResult;
  if (!inspectionResult) {
    statusNode.textContent = "Load PNG metadata first before applying it.";
    return;
  }

  const targetForm = formRegistry[targetKey];
  if (!targetForm?.applyPayload) {
    statusNode.textContent = `Target form unavailable: ${targetKey}`;
    return;
  }

  formRegistry.__shellTabs?.activateTabById?.(targetKey);
  targetForm.applyPayload(inspectionResult.payload ?? {});
  statusNode.textContent = `Applied ${targetKey} fields`;
}

function buildPngInfoSection(parent, bootstrapState, formRegistry) {
  const section = document.createElement("section");
  section.className = "rookieui-shell__section";
  parent.appendChild(section);

  appendTextElement(section, "h3", "rookieui-shell__section-title", "PNG Info");

  const workspace = document.createElement("div");
  workspace.className = "rookieui-shell__workspace-grid rookieui-shell__workspace-grid--pnginfo";
  section.appendChild(workspace);

  const leftColumn = document.createElement("div");
  leftColumn.className = "rookieui-shell__workspace-column";
  workspace.appendChild(leftColumn);

  const rightColumn = document.createElement("div");
  rightColumn.className = "rookieui-shell__workspace-column";
  workspace.appendChild(rightColumn);

  const form = document.createElement("form");
  form.className = "rookieui-shell__form";
  form.id = "rookieui-pnginfo-form";
  leftColumn.appendChild(form);

  const uploadSection = document.createElement("section");
  uploadSection.className = "rookieui-shell__section rookieui-shell__section--soft";
  form.appendChild(uploadSection);
  appendTextElement(uploadSection, "h4", "rookieui-shell__section-title", "Image Inspector");

  const dropzone = document.createElement("label");
  dropzone.className = "rookieui-shell__dropzone";
  dropzone.id = "rookieui-pnginfo-dropzone";
  uploadSection.appendChild(dropzone);
  appendTextElement(dropzone, "span", "rookieui-shell__dropzone-icon", "⇪");
  appendTextElement(
    dropzone,
    "span",
    "rookieui-shell__dropzone-text",
    "Drop a PNG here or browse for an image to auto-read metadata.",
  );

  const fileInput = createInput("file", "rookieui-pnginfo-image-file", "", {
    className: "rookieui-shell__file-input",
  });
  fileInput.accept = "image/png,image/webp,image/jpeg";
  dropzone.appendChild(fileInput);

  const actions = document.createElement("div");
  actions.className = "rookieui-shell__pnginfo-apply-rail";
  actions.id = "rookieui-pnginfo-apply-rail";
  form.appendChild(actions);

  const applyTxt2ImgButton = createActionButton("rookieui-pnginfo-apply-txt2img", "Apply to Txt2Img");
  const applyImg2ImgButton = createActionButton("rookieui-pnginfo-apply-img2img", "Apply to Img2Img");
  applyTxt2ImgButton.classList.add("rookieui-shell__button--apply");
  applyImg2ImgButton.classList.add("rookieui-shell__button--apply");
  applyTxt2ImgButton.disabled = true;
  applyImg2ImgButton.disabled = true;
  actions.appendChild(applyTxt2ImgButton);
  actions.appendChild(applyImg2ImgButton);

  const statusNode = document.createElement("p");
  statusNode.id = "rookieui-pnginfo-status";
  statusNode.className = "rookieui-shell__status";
  statusNode.textContent = "Idle";
  form.appendChild(statusNode);

  const previewSection = document.createElement("section");
  previewSection.className = "rookieui-shell__section rookieui-shell__section--soft";
  // IMPORTANT: keep PNG Info preview section anchored above the upload/action form; users expect the image preview at the top of the input block.
  leftColumn.insertBefore(previewSection, form);
  appendTextElement(previewSection, "h4", "rookieui-shell__section-title", "Preview");

  const previewBox = document.createElement("div");
  previewBox.className = "rookieui-shell__preview-box rookieui-shell__preview-box--compact";
  previewBox.id = "rookieui-pnginfo-preview";
  previewSection.appendChild(previewBox);
  setPreviewContent(
    previewBox,
    "",
    "Imported PNG preview will appear here after selecting an image.",
  );

  const metadataSection = document.createElement("section");
  metadataSection.className = "rookieui-shell__section rookieui-shell__section--soft";
  metadataSection.id = "rookieui-pnginfo-metadata";
  rightColumn.appendChild(metadataSection);
  const summaryHeader = document.createElement("div");
  summaryHeader.className = "rookieui-shell__pnginfo-header";
  metadataSection.appendChild(summaryHeader);
  appendTextElement(summaryHeader, "h4", "rookieui-shell__section-title", "Generation Summary");
  const sourceBadge = appendTextElement(summaryHeader, "span", "rookieui-shell__pnginfo-source", "");
  sourceBadge.hidden = true;

  const summaryText = appendTextElement(
    metadataSection,
    "p",
    "rookieui-shell__pnginfo-summary-text",
    "Generation summary will appear after metadata is loaded.",
  );

  const metadataCards = document.createElement("div");
  metadataCards.className = "rookieui-shell__pnginfo-cards";
  metadataCards.id = "rookieui-pnginfo-cards";
  metadataSection.appendChild(metadataCards);

  const promptsGrid = document.createElement("div");
  promptsGrid.className = "rookieui-shell__pnginfo-prompts";
  metadataSection.appendChild(promptsGrid);

  const promptCard = document.createElement("article");
  promptCard.className = "rookieui-shell__pnginfo-prompt-card";
  promptsGrid.appendChild(promptCard);
  const promptHeader = document.createElement("div");
  promptHeader.className = "rookieui-shell__pnginfo-prompt-header";
  promptCard.appendChild(promptHeader);
  appendTextElement(promptHeader, "span", "rookieui-shell__pnginfo-prompt-label", "Prompt");
  const copyPromptButton = createMiniActionButton("rookieui-pnginfo-copy-prompt", "Copy");
  copyPromptButton.classList.add("rookieui-shell__pnginfo-copy");
  copyPromptButton.disabled = true;
  promptHeader.appendChild(copyPromptButton);
  const promptTextNode = appendTextElement(
    promptCard,
    "pre",
    "rookieui-shell__pnginfo-prompt-text",
    "Prompt is unavailable in this metadata payload.",
  );

  const negativePromptCard = document.createElement("article");
  negativePromptCard.className = "rookieui-shell__pnginfo-prompt-card";
  promptsGrid.appendChild(negativePromptCard);
  const negativePromptHeader = document.createElement("div");
  negativePromptHeader.className = "rookieui-shell__pnginfo-prompt-header";
  negativePromptCard.appendChild(negativePromptHeader);
  appendTextElement(negativePromptHeader, "span", "rookieui-shell__pnginfo-prompt-label", "Negative Prompt");
  const copyNegativePromptButton = createMiniActionButton("rookieui-pnginfo-copy-negative-prompt", "Copy");
  copyNegativePromptButton.classList.add("rookieui-shell__pnginfo-copy");
  copyNegativePromptButton.disabled = true;
  negativePromptHeader.appendChild(copyNegativePromptButton);
  const negativePromptTextNode = appendTextElement(
    negativePromptCard,
    "pre",
    "rookieui-shell__pnginfo-prompt-text",
    "Negative prompt is unavailable in this metadata payload.",
  );

  const unsupportedHeading = appendTextElement(
    metadataSection,
    "h4",
    "rookieui-shell__subsection-title",
    "Unsupported Fields",
  );
  const unsupportedList = createList("rookieui-pnginfo-unsupported");
  unsupportedList.hidden = true;
  unsupportedHeading.hidden = true;
  metadataSection.appendChild(unsupportedList);

  const warningsHeading = appendTextElement(
    metadataSection,
    "h4",
    "rookieui-shell__subsection-title",
    "Warnings",
  );
  const warningList = createList("rookieui-pnginfo-warnings");
  warningList.hidden = true;
  warningsHeading.hidden = true;
  metadataSection.appendChild(warningList);

  const state = {
    imageData: "",
    inspectionResult: null,
  };

  const runAutoInspection = async () => {
    if (!state.imageData) {
      state.inspectionResult = null;
      setListVisibility(unsupportedHeading, unsupportedList, []);
      setListVisibility(warningsHeading, warningList, []);
      setPngInfoSummaryVisibility(
        {
          sourceBadge,
          summaryText,
          cards: metadataCards,
          promptText: promptTextNode,
          negativePromptText: negativePromptTextNode,
          copyPrompt: copyPromptButton,
          copyNegativePrompt: copyNegativePromptButton,
        },
        null,
      );
      updatePngInfoApplyButtons(state, {
        txt2img: applyTxt2ImgButton,
        img2img: applyImg2ImgButton,
      });
      statusNode.textContent = "Idle";
      return;
    }
    await inspectPngInfo(
      bootstrapState,
      state,
      statusNode,
      {
        summary: {
          sourceBadge,
          summaryText,
          cards: metadataCards,
          promptText: promptTextNode,
          negativePromptText: negativePromptTextNode,
          copyPrompt: copyPromptButton,
          copyNegativePrompt: copyNegativePromptButton,
        },
        unsupportedHeading,
        unsupported: unsupportedList,
        warningsHeading,
        warnings: warningList,
      },
      {
        txt2img: applyTxt2ImgButton,
        img2img: applyImg2ImgButton,
      },
    );
  };

  const syncFileSelection = async (file) => {
    if (!file) {
      return;
    }
    state.imageData = await readFileAsDataUrl(file);
    setPreviewContent(previewBox, state.imageData, "");
    statusNode.textContent = `Loaded ${file.name}; reading metadata...`;
  };

  fileInput.addEventListener("change", async () => {
    const [file] = Array.from(fileInput.files ?? []);
    if (!file) {
      return;
    }
    try {
      await syncFileSelection(file);
      await runAutoInspection();
    } catch (_error) {
      emitFrontendDebugWarning("shell.pnginfo_upload", "PNG Info file input handling failed.", _error);
      statusNode.textContent = "Failed to read the selected image.";
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
      await syncFileSelection(file);
      await runAutoInspection();
    } catch (_error) {
      emitFrontendDebugWarning("shell.pnginfo_upload", "PNG Info file drop handling failed.", _error);
      statusNode.textContent = "Failed to read the dropped image.";
    }
  });
  copyPromptButton.addEventListener("click", async () => {
    const copied = await writeTextToClipboard(promptTextNode.textContent);
    statusNode.textContent = copied ? "Copied prompt text." : "Prompt text is unavailable to copy.";
  });
  copyNegativePromptButton.addEventListener("click", async () => {
    const copied = await writeTextToClipboard(negativePromptTextNode.textContent);
    statusNode.textContent = copied ? "Copied negative prompt text." : "Negative prompt text is unavailable to copy.";
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void runAutoInspection();
  });

  applyTxt2ImgButton.addEventListener("click", () => {
    applyPngInfoResult(formRegistry, "txt2img", state, statusNode);
  });
  applyImg2ImgButton.addEventListener("click", () => {
    applyPngInfoResult(formRegistry, "img2img", state, statusNode);
  });
}

function syncExtrasMode(modeButtons, panes, mode) {
  const activeIndex = mode === "batch_process" ? 1 : 0;
  modeButtons.forEach((button, index) => {
    const active = index === activeIndex;
    button.classList.toggle("is-active", active);
    panes[index].hidden = !active;
    panes[index].classList.toggle("is-active", active);
  });
}

async function loadExtrasFiles(fileList) {
  const files = Array.from(fileList ?? []);
  return Promise.all(
    files.map(async (file) => ({
      name: file.name,
      dataUrl: await readFileAsDataUrl(file),
    })),
  );
}

function updateExtrasPreview(previewBox, dataUrl, fallbackText) {
  setPreviewContent(previewBox, dataUrl, fallbackText);
}

async function submitExtras(bootstrapState, state, elements, statusNode, previewBox) {
  statusNode.textContent = "Running Extras...";
  const payload = {
    mode: state.mode,
    upscale_enabled: elements.upscaleEnabled.checked,
    scale_mode: elements.scaleMode.value,
    scale_by: Number(elements.scaleBy.value),
    target_width: Number(elements.targetWidth.value),
    target_height: Number(elements.targetHeight.value),
    upscaler_1: elements.upscaler1.value,
    upscaler_2: elements.upscaler2.value,
    upscaler_2_visibility: Number(elements.upscaler2Visibility.value),
    color_correction: elements.colorCorrection.checked,
    face_restoration: elements.faceRestoration.value,
    codeformer_weight: Number(elements.codeformerWeight.value),
  };

  if (state.mode === "batch_process") {
    // CRITICAL: Extras uploads must stay inside the RookieUI workspace asset bridge; do not pass host filesystem paths from browser state.
    payload.batch_images = state.batchImages.map((entry) => entry.dataUrl);
  } else if (state.singleImage?.dataUrl) {
    payload.image_data = state.singleImage.dataUrl;
  }

  const result = await bootstrapState.submitExtrasRequest(payload);
  if (!result.ok) {
    statusNode.textContent = `Request failed: ${result.data.status}`;
    return;
  }

  state.lastResult = result.data;
  updateExtrasPreview(
    previewBox,
    result.data.preview_data_url ?? "",
    "Extras preview will appear here after processing.",
  );
  statusNode.textContent = `Generated ${result.data.output_assets?.length ?? 0} extras output(s)`;
}

function buildExtrasSection(parent, bootstrapState, formRegistry) {
  const inventory = bootstrapState.models ?? {};
  const section = document.createElement("section");
  section.className = "rookieui-shell__section";
  parent.appendChild(section);

  const workspace = document.createElement("div");
  workspace.className = "rookieui-shell__workspace-grid";
  section.appendChild(workspace);

  const leftColumn = document.createElement("div");
  leftColumn.className = "rookieui-shell__workspace-column";
  workspace.appendChild(leftColumn);

  const rightColumn = document.createElement("div");
  rightColumn.className = "rookieui-shell__workspace-column";
  workspace.appendChild(rightColumn);

  const state = {
    mode: "single_image",
    singleImage: null,
    batchImages: [],
    lastResult: null,
  };

  const modeTabs = document.createElement("div");
  modeTabs.className = "rookieui-shell__subtabs";
  leftColumn.appendChild(modeTabs);

  const singleButton = document.createElement("button");
  singleButton.type = "button";
  singleButton.id = "rookieui-extras-mode-single";
  singleButton.className = "rookieui-shell__subtab";
  singleButton.textContent = "Single Image";
  modeTabs.appendChild(singleButton);

  const batchButton = document.createElement("button");
  batchButton.type = "button";
  batchButton.id = "rookieui-extras-mode-batch";
  batchButton.className = "rookieui-shell__subtab";
  batchButton.textContent = "Batch Process";
  modeTabs.appendChild(batchButton);

  const singlePane = document.createElement("section");
  singlePane.className = "rookieui-shell__section rookieui-shell__section--soft rookieui-shell__subpane";
  singlePane.id = "rookieui-extras-single-pane";
  leftColumn.appendChild(singlePane);
  appendTextElement(singlePane, "h4", "rookieui-shell__section-title", "Single Image");

  const singleDropzone = document.createElement("label");
  singleDropzone.className = "rookieui-shell__dropzone";
  singleDropzone.id = "rookieui-extras-single-dropzone";
  singlePane.appendChild(singleDropzone);
  appendTextElement(singleDropzone, "span", "rookieui-shell__dropzone-icon", "⇪");
  appendTextElement(singleDropzone, "span", "rookieui-shell__dropzone-text", "Drop a single image here or browse.");

  const singleFileInput = createInput("file", "rookieui-extras-single-file", "", {
    className: "rookieui-shell__file-input",
  });
  singleFileInput.accept = "image/png,image/webp,image/jpeg";
  singleDropzone.appendChild(singleFileInput);

  const singleStatus = appendTextElement(
    singlePane,
    "p",
    "rookieui-shell__status",
    "No image selected.",
    "rookieui-extras-single-status",
  );

  const batchPane = document.createElement("section");
  batchPane.className = "rookieui-shell__section rookieui-shell__section--soft rookieui-shell__subpane";
  batchPane.id = "rookieui-extras-batch-pane";
  leftColumn.appendChild(batchPane);
  appendTextElement(batchPane, "h4", "rookieui-shell__section-title", "Batch Process");

  const batchDropzone = document.createElement("label");
  batchDropzone.className = "rookieui-shell__dropzone";
  batchDropzone.id = "rookieui-extras-batch-dropzone";
  batchPane.appendChild(batchDropzone);
  appendTextElement(batchDropzone, "span", "rookieui-shell__dropzone-icon", "⇪");
  appendTextElement(batchDropzone, "span", "rookieui-shell__dropzone-text", "Drop multiple images here or browse.");

  const batchFileInput = createInput("file", "rookieui-extras-batch-file", "", {
    className: "rookieui-shell__file-input",
  });
  batchFileInput.accept = "image/png,image/webp,image/jpeg";
  batchFileInput.multiple = true;
  batchDropzone.appendChild(batchFileInput);

  const batchList = createList("rookieui-extras-batch-list");
  batchPane.appendChild(batchList);
  const batchStatus = appendTextElement(
    batchPane,
    "p",
    "rookieui-shell__status",
    "No batch images selected.",
    "rookieui-extras-batch-status",
  );

  const optionsSection = document.createElement("section");
  optionsSection.className = "rookieui-shell__section rookieui-shell__section--soft";
  leftColumn.appendChild(optionsSection);
  appendTextElement(optionsSection, "h4", "rookieui-shell__section-title", "Postprocessing");

  const optionsGrid = document.createElement("div");
  optionsGrid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
  optionsSection.appendChild(optionsGrid);

  const elements = {
    upscaleEnabled: createCheckbox("rookieui-extras-upscale-enabled", true),
    scaleMode: createSelect(
      "rookieui-extras-scale-mode",
      [
        { value: "scale_by", label: "Scale by" },
        { value: "scale_to", label: "Scale to" },
      ],
      "scale_by",
    ),
    scaleBy: createInput("number", "rookieui-extras-scale-by", "2", { step: 0.1, min: 1, max: 8 }),
    targetWidth: createInput("number", "rookieui-extras-target-width", "1024", { step: 8, min: 64, max: 4096 }),
    targetHeight: createInput("number", "rookieui-extras-target-height", "1024", { step: 8, min: 64, max: 4096 }),
    upscaler1: createSelect(
      "rookieui-extras-upscaler-1",
      [{ value: "None", label: "None" }, ...(inventory.upscale_models ?? []).map((value) => ({ value, label: value }))],
      "None",
    ),
    upscaler2: createSelect(
      "rookieui-extras-upscaler-2",
      [{ value: "None", label: "None" }, ...(inventory.upscale_models ?? []).map((value) => ({ value, label: value }))],
      "None",
    ),
    upscaler2Visibility: createInput("number", "rookieui-extras-upscaler-2-visibility", "0", {
      step: 0.05,
      min: 0,
      max: 1,
    }),
    colorCorrection: createCheckbox("rookieui-extras-color-correction", false),
    faceRestoration: createSelect(
      "rookieui-extras-face-restoration",
      [
        { value: "none", label: "None" },
        { value: "codeformer", label: "CodeFormer" },
        { value: "gfpgan", label: "GFPGAN" },
      ],
      "none",
    ),
    codeformerWeight: createInput("number", "rookieui-extras-codeformer-weight", "0.5", {
      step: 0.05,
      min: 0,
      max: 1,
    }),
  };

  createInlineCheckboxField(optionsGrid, "Upscale", elements.upscaleEnabled);
  createField(optionsGrid, "Scale Mode", elements.scaleMode);
  createField(optionsGrid, "Scale By", elements.scaleBy);
  createField(optionsGrid, "Target Width", elements.targetWidth);
  createField(optionsGrid, "Target Height", elements.targetHeight);
  createField(optionsGrid, "Upscaler 1", elements.upscaler1);
  createField(optionsGrid, "Upscaler 2", elements.upscaler2);
  createField(optionsGrid, "Upscaler 2 visibility", elements.upscaler2Visibility);
  createInlineCheckboxField(optionsGrid, "Color Correction", elements.colorCorrection);
  createField(optionsGrid, "Face Restoration", elements.faceRestoration);
  createField(optionsGrid, "CodeFormer Weight", elements.codeformerWeight);

  const actionRail = document.createElement("div");
  actionRail.className = "rookieui-shell__action-rail rookieui-shell__action-rail--extras";
  rightColumn.appendChild(actionRail);

  const submitButton = document.createElement("button");
  submitButton.id = "rookieui-extras-submit";
  submitButton.className = "rookieui-shell__button rookieui-shell__button--hero";
  submitButton.type = "button";
  submitButton.textContent = "Generate";
  actionRail.appendChild(submitButton);

  const generateActionRow = document.createElement("div");
  generateActionRow.className = "rookieui-shell__mini-actions";
  actionRail.appendChild(generateActionRow);
  // IMPORTANT: keep quick actions directly below Extras Generate; removing this row hides expected A1111-style emoji tools.
  const generateOpenQueue = createIconActionButton(
    "rookieui-extras-generate-open-queue",
    "pi-folder-open",
    "Queue History",
    "queue",
  );
  generateOpenQueue.addEventListener("click", () => {
    activateShellTab(formRegistry, "queue", statusNode, "Opened queue history");
  });
  generateActionRow.appendChild(generateOpenQueue);
  const generateOpenPngInfo = createIconActionButton(
    "rookieui-extras-generate-open-pnginfo",
    "pi-file",
    "PNG Info",
    "metadata",
  );
  generateOpenPngInfo.addEventListener("click", () => {
    activateShellTab(formRegistry, "pnginfo", statusNode, "Opened PNG Info");
  });
  generateActionRow.appendChild(generateOpenPngInfo);

  const statusNode = appendTextElement(
    actionRail,
    "p",
    "rookieui-shell__status rookieui-shell__status--inline",
    "Idle",
    "rookieui-extras-status",
  );

  const previewSection = document.createElement("section");
  previewSection.className = "rookieui-shell__section rookieui-shell__section--soft";
  rightColumn.appendChild(previewSection);
  appendTextElement(previewSection, "h4", "rookieui-shell__section-title", "Preview");

  const previewBox = document.createElement("div");
  previewBox.className = "rookieui-shell__preview-box rookieui-shell__preview-box--compact";
  previewBox.id = "rookieui-extras-preview";
  previewSection.appendChild(previewBox);
  updateExtrasPreview(previewBox, "", "Extras preview will appear here after processing.");

  const previewToolbar = document.createElement("div");
  previewToolbar.className = "rookieui-shell__preview-toolbar";
  previewSection.appendChild(previewToolbar);

  const sendToImg2Img = createIconActionButton(
    "rookieui-extras-preview-img2img",
    "pi-image",
    "Send to Img2Img",
    "transfer",
  );
  sendToImg2Img.addEventListener("click", () => {
    const asset = state.lastResult?.preview_asset;
    if (!asset) {
      statusNode.textContent = "Run Extras before sending an output to img2img.";
      return;
    }
    activateShellTab(formRegistry, "img2img", statusNode, "Opened Img2Img");
    formRegistry.img2img?.applyPayload({
      image_asset: asset,
      mode: "img2img",
      mask_asset: "",
    });
    statusNode.textContent = `Applied ${asset} to img2img`;
  });
  previewToolbar.appendChild(sendToImg2Img);

  const openQueue = createIconActionButton(
    "rookieui-extras-open-queue",
    "pi-folder-open",
    "Queue History",
    "queue",
  );
  openQueue.addEventListener("click", () => {
    activateShellTab(formRegistry, "queue", statusNode, "Opened queue history");
  });
  previewToolbar.appendChild(openQueue);

  const openPngInfo = createIconActionButton("rookieui-extras-open-pnginfo", "pi-file", "PNG Info", "metadata");
  openPngInfo.addEventListener("click", () => {
    activateShellTab(formRegistry, "pnginfo", statusNode, "Opened PNG Info");
  });
  previewToolbar.appendChild(openPngInfo);

  const setSingleFiles = async (files) => {
    const [entry] = await loadExtrasFiles(files);
    state.singleImage = entry ?? null;
    singleStatus.textContent = entry ? `Loaded ${entry.name}` : "No image selected.";
    updateExtrasPreview(
      previewBox,
      entry?.dataUrl ?? state.lastResult?.preview_data_url ?? "",
      "Extras preview will appear here after processing.",
    );
  };

  const setBatchFiles = async (files) => {
    state.batchImages = await loadExtrasFiles(files);
    populateList(batchList, state.batchImages.map((entry) => entry.name));
    batchStatus.textContent = state.batchImages.length
      ? `Loaded ${state.batchImages.length} image(s)`
      : "No batch images selected.";
  };

  singleFileInput.addEventListener("change", async () => {
    try {
      await setSingleFiles(singleFileInput.files);
    } catch (_error) {
      emitFrontendDebugWarning("shell.extras_upload", "Extras single-image input handling failed.", _error);
      statusNode.textContent = "Failed to load the selected Extras image.";
    }
  });
  batchFileInput.addEventListener("change", async () => {
    try {
      await setBatchFiles(batchFileInput.files);
    } catch (_error) {
      emitFrontendDebugWarning("shell.extras_upload", "Extras batch-image input handling failed.", _error);
      statusNode.textContent = "Failed to load the selected batch images.";
    }
  });

  [singleDropzone, batchDropzone].forEach((dropzone) => {
    dropzone.addEventListener("dragover", (event) => {
      event.preventDefault();
      dropzone.dataset.dragging = "true";
    });
    dropzone.addEventListener("dragleave", () => {
      dropzone.dataset.dragging = "false";
    });
  });
  singleDropzone.addEventListener("drop", async (event) => {
    event.preventDefault();
    singleDropzone.dataset.dragging = "false";
    try {
      await setSingleFiles(event.dataTransfer?.files);
    } catch (_error) {
      emitFrontendDebugWarning("shell.extras_upload", "Extras single-image drop handling failed.", _error);
      statusNode.textContent = "Failed to load the dropped Extras image.";
    }
  });
  batchDropzone.addEventListener("drop", async (event) => {
    event.preventDefault();
    batchDropzone.dataset.dragging = "false";
    try {
      await setBatchFiles(event.dataTransfer?.files);
    } catch (_error) {
      emitFrontendDebugWarning("shell.extras_upload", "Extras batch-image drop handling failed.", _error);
      statusNode.textContent = "Failed to load the dropped batch images.";
    }
  });

  singleButton.addEventListener("click", () => {
    state.mode = "single_image";
    syncExtrasMode([singleButton, batchButton], [singlePane, batchPane], state.mode);
  });
  batchButton.addEventListener("click", () => {
    state.mode = "batch_process";
    syncExtrasMode([singleButton, batchButton], [singlePane, batchPane], state.mode);
  });
  syncExtrasMode([singleButton, batchButton], [singlePane, batchPane], state.mode);

  let extrasModeSnapshot = state.mode;
  const extrasStateLock = installPaneStateLock(formRegistry, "extras", elements, () => {
    state.mode = extrasModeSnapshot;
    syncExtrasMode([singleButton, batchButton], [singlePane, batchPane], state.mode);
  });
  const captureExtrasState = () => {
    extrasModeSnapshot = state.mode;
    extrasStateLock.capture();
  };
  const restoreExtrasState = () => {
    extrasStateLock.restore();
    state.mode = extrasModeSnapshot;
    syncExtrasMode([singleButton, batchButton], [singlePane, batchPane], state.mode);
  };

  submitButton.addEventListener("click", async () => {
    await submitExtras(bootstrapState, state, elements, statusNode, previewBox);
    captureExtrasState();
  });

  return {
    onActivate: restoreExtrasState,
    onDeactivate: captureExtrasState,
  };
}

function buildQueueSection(parent, bootstrapState, formRegistry) {
  const section = document.createElement("section");
  section.className = "rookieui-shell__section";
  parent.appendChild(section);

  appendTextElement(section, "h3", "rookieui-shell__section-title", "Queue and History");
  appendTextElement(
    section,
    "p",
    "rookieui-shell__status",
    `Queue remaining: ${bootstrapState.queue?.queue_remaining ?? 0}`,
    "rookieui-queue-remaining",
  );

  const statusNode = appendTextElement(
    section,
    "p",
    "rookieui-shell__status",
    "Idle",
    "rookieui-queue-status",
  );

  const list = createList("rookieui-queue-list");
  section.appendChild(list);

  const jobs = bootstrapState.queue?.jobs ?? [];
  if (!jobs.length) {
    const item = document.createElement("li");
    item.className = "rookieui-shell__list-item";
    item.textContent = "No queue or history items available.";
    list.appendChild(item);
    return;
  }

  jobs.forEach((job, index) => {
    const item = document.createElement("li");
    item.className = "rookieui-shell__list-item";
    item.textContent = `${job.id} (${job.status})`;
    list.appendChild(item);

    if (!job.reusable_outputs?.length) {
      return;
    }

    const actions = document.createElement("div");
    actions.className = "rookieui-shell__actions";
    item.appendChild(actions);

    const img2imgButton = createActionButton(`rookieui-reuse-img2img-${index}`, "Use as Img2Img");
    img2imgButton.addEventListener("click", () => {
      formRegistry.img2img?.applyPayload({
        image_asset: job.reusable_outputs[0],
        mode: "img2img",
        mask_asset: "",
      });
      statusNode.textContent = `Applied ${job.reusable_outputs[0]} to img2img`;
    });
    actions.appendChild(img2imgButton);

    const inpaintButton = createActionButton(`rookieui-reuse-inpaint-${index}`, "Use as Inpaint");
    inpaintButton.addEventListener("click", () => {
      formRegistry.img2img?.applyPayload({
        image_asset: job.reusable_outputs[0],
        mode: "inpaint",
      });
      statusNode.textContent = `Applied ${job.reusable_outputs[0]} to inpaint`;
    });
    actions.appendChild(inpaintButton);
  });
}

function buildCompatibilitySection(parent, compatibility) {
  if (!compatibility) {
    return;
  }

  const section = document.createElement("section");
  section.className = "rookieui-shell__section";
  parent.appendChild(section);

  appendTextElement(section, "h3", "rookieui-shell__section-title", "Compatibility Layer");
  appendTextElement(
    section,
    "p",
    "rookieui-shell__status",
    `Catalog source: ${compatibility.source ?? "fallback"}`,
    "rookieui-compatibility-source",
  );

  appendTextElement(section, "h4", "rookieui-shell__subsection-title", "Samplers");
  buildCompatibilityList(
    section,
    compatibility.samplers ?? [],
    "rookieui-compatibility-samplers",
    (entry) => `${entry.title} (${entry.tier})`,
  );

  appendTextElement(section, "h4", "rookieui-shell__subsection-title", "Schedulers");
  buildCompatibilityList(
    section,
    compatibility.schedulers ?? [],
    "rookieui-compatibility-schedulers",
    (entry) => `${entry.title} (${entry.tier})`,
  );

  appendTextElement(section, "h4", "rookieui-shell__subsection-title", "Runtime Profiles");
  buildCompatibilityList(
    section,
    compatibility.runtime_profiles ?? [],
    "rookieui-compatibility-runtime",
    (entry) => `${entry.title}${entry.experimental ? " (experimental)" : ""}`,
  );

  appendTextElement(section, "h4", "rookieui-shell__subsection-title", "DType Profiles");
  buildCompatibilityList(
    section,
    compatibility.dtype_profiles ?? [],
    "rookieui-compatibility-dtype",
    (entry) => `${entry.title}${entry.experimental ? " (experimental)" : ""}`,
  );

  appendTextElement(section, "h4", "rookieui-shell__subsection-title", "Newer Families");
  buildCompatibilityList(
    section,
    compatibility.newer_family_profiles ?? [],
    "rookieui-compatibility-families",
    (entry) => `${entry.title}${entry.experimental ? " (experimental)" : ""}`,
  );
}

function buildShellHeader(container, bootstrapState) {
  const header = document.createElement("header");
  header.className = "rookieui-shell__header";
  container.appendChild(header);

  const identity = document.createElement("div");
  identity.className = "rookieui-shell__identity";
  header.appendChild(identity);

  appendTextElement(identity, "span", "rookieui-shell__status-dot", "", "rookieui-header-status-dot");
  appendTextElement(identity, "h2", "rookieui-shell__title", "RookieUI", "rookieui-shell-title");

  const actions = document.createElement("div");
  actions.className = "rookieui-shell__header-actions";
  header.appendChild(actions);

  appendTextElement(
    actions,
    "span",
    "rookieui-shell__version",
    `v${bootstrapState.capabilities.shell_version ?? "0.1.0"}`,
    "rookieui-header-version",
  );

  const githubLink = document.createElement("a");
  githubLink.id = "rookieui-view-github";
  githubLink.className = "rookieui-shell__button rookieui-shell__button--secondary rookieui-shell__repo-link";
  githubLink.href = ROOKIEUI_GITHUB_URL;
  githubLink.target = "_blank";
  githubLink.rel = "noreferrer";
  githubLink.textContent = "View on GitHub";
  actions.appendChild(githubLink);
}

function resolveForgeNeoTheme(documentRef, windowRef = documentRef?.defaultView) {
  const classHints = [
    documentRef?.body?.className ?? "",
    documentRef?.documentElement?.className ?? "",
    documentRef?.documentElement?.dataset?.theme ?? "",
  ]
    .join(" ")
    .toLowerCase();
  if (/(dark|night)/.test(classHints)) {
    return "dark";
  }
  if (/(light|normal)/.test(classHints)) {
    return "normal";
  }
  if (typeof windowRef?.matchMedia === "function" && windowRef.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }
  return "normal";
}

function buildTabbedShell(container, definitions, controller = {}) {
  const tabs = document.createElement("div");
  tabs.className = "rookieui-shell__tabs";
  tabs.id = "rookieui-shell-tabs";
  tabs.setAttribute("role", "tablist");
  container.appendChild(tabs);

  const content = document.createElement("div");
  content.className = "rookieui-shell__content";
  container.appendChild(content);

  const buttons = [];
  const panes = [];
  const lifecycles = [];
  let activeIndex = -1;

  const activateTab = (nextIndex) => {
    if (activeIndex === nextIndex) {
      return;
    }
    if (activeIndex >= 0) {
      lifecycles[activeIndex]?.onDeactivate?.();
    }
    buttons.forEach((button, index) => {
      const active = index === nextIndex;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
      panes[index].classList.toggle("is-active", active);
      panes[index].hidden = !active;
    });
    lifecycles[nextIndex]?.onActivate?.();
    activeIndex = nextIndex;
  };

  // CRITICAL: shell tab switching must stay callable from internal action buttons; otherwise queue/pnginfo shortcuts become decorative only.
  controller.activateTabById = (tabId) => {
    const activeIndex = definitions.findIndex((definition) => definition.id === tabId);
    if (activeIndex >= 0) {
      activateTab(activeIndex);
    }
  };

  definitions.forEach((definition, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.id = `rookieui-tab-${definition.id}`;
    button.className = "rookieui-shell__tab";
    button.textContent = definition.label;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", `rookieui-pane-${definition.id}`);
    tabs.appendChild(button);
    buttons.push(button);

    const pane = document.createElement("div");
    pane.id = `rookieui-pane-${definition.id}`;
    pane.className = "rookieui-shell__pane";
    pane.setAttribute("role", "tabpanel");
    pane.setAttribute("aria-labelledby", button.id);
    pane.hidden = true;
    content.appendChild(pane);
    panes.push(pane);
    const lifecycle = definition.render(pane);
    lifecycles.push(lifecycle && typeof lifecycle === "object" ? lifecycle : {});

    button.addEventListener("click", () => {
      activateTab(index);
    });

    button.setAttribute("aria-selected", "false");
    button.tabIndex = -1;
  });

  activateTab(0);
  return controller;
}

function buildShellFooter(container, bootstrapState) {
  const footer = document.createElement("footer");
  footer.className = "rookieui-shell__footer";
  container.appendChild(footer);
  const theme = container.dataset.theme ?? "normal";
  footer.textContent = `host: ${bootstrapState.hostSurface ?? "unknown"} • models: ${bootstrapState.models?.source ?? "fallback"} • theme: ${theme}`;
}

export function renderRookieUISidebar(container, bootstrapState) {
  container.replaceChildren();
  container.className = "rookieui-shell";
  container.dataset.theme = resolveForgeNeoTheme(container.ownerDocument);
  const formRegistry = {};
  const shellTabs = {};
  formRegistry.__shellTabs = shellTabs;
  const tabDefinitions = [
    createTxt2ImgTabDefinition(buildTxt2ImgSection, bootstrapState, formRegistry),
    createImg2ImgTabDefinition(buildImg2ImgSection, bootstrapState, formRegistry),
    createExtrasTabDefinition(buildExtrasSection, bootstrapState, formRegistry),
    createPngInfoTabDefinition(buildPngInfoSection, bootstrapState, formRegistry),
    createQueueTabDefinition(buildQueueSection, bootstrapState, formRegistry),
  ];

  buildShellHeader(container, bootstrapState);
  // IMPORTANT: keep tab wiring in per-tab modules so pane ownership is explicit and future tab-level refactors do not reopen a single giant definition block.
  buildTabbedShell(container, tabDefinitions, shellTabs);
  buildShellFooter(container, bootstrapState);
}
