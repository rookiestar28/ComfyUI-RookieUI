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
import { buildTxt2ImgPane } from "./sidebar_tabs/rookieui_txt2img_pane.js?v=20260411-f62-pane-split";
import { buildImg2ImgPane } from "./sidebar_tabs/rookieui_img2img_pane.js?v=20260411-f61-img2img-pane";
import { buildPngInfoPane } from "./sidebar_tabs/rookieui_pnginfo_pane.js?v=20260411-f62-pane-split";
import { buildExtrasPane } from "./sidebar_tabs/rookieui_extras_pane.js?v=20260411-f42-extras-hires";
import { buildQueuePane } from "./sidebar_tabs/rookieui_queue_pane.js?v=20260411-f62-pane-split";
import {
  assertTopLevelTabDefinitions,
} from "./sidebar_tabs/rookieui_tab_contract.js?v=20260411-r51-tab-contract";
import { createShellStateEventContract } from "./sidebar_tabs/rookieui_shell_state_contract.js?v=20260411-r52-shell-state";
import { createImg2ImgMaskCanvasContract } from "./sidebar_tabs/rookieui_img2img_mask_canvas.js?v=20260411-r49-mask-contract";
import { createImg2ImgMaskCanvasEditor } from "./sidebar_tabs/rookieui_img2img_mask_editor.js?v=20260411-f58-mask-editor";
import { createImg2ImgModeRouter } from "./sidebar_tabs/rookieui_img2img_mode_router.js?v=20260411-r50-mode-router";

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
    const shellStateContract = formRegistry.__shellStateContract;
    if (shellStateContract?.registerPaneStateLock) {
      shellStateContract.registerPaneStateLock(paneId, { capture, restore });
    } else {
      formRegistry.__paneStateLocks ??= {};
      formRegistry.__paneStateLocks[paneId] = { capture, restore };
    }
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
  // CRITICAL: host preview/progress events can nest identifiers under metadata/payload wrappers; keep recursive prompt-id extraction to prevent cross-job frame leakage.
  const queue = [detail];
  const visited = new Set();
  const idKeys = ["prompt_id", "promptId", "jobId", "id"];
  const nestedKeys = ["metadata", "meta", "payload", "data", "event", "job"];
  while (queue.length) {
    const candidate = queue.shift();
    if (!candidate || typeof candidate !== "object") {
      continue;
    }
    if (visited.has(candidate)) {
      continue;
    }
    visited.add(candidate);
    for (const key of idKeys) {
      const value = candidate[key];
      if (typeof value === "string" && value.trim()) {
        return value.trim();
      }
    }
    for (const key of nestedKeys) {
      const nested = candidate[key];
      if (nested && typeof nested === "object") {
        queue.push(nested);
      }
    }
  }
  return "";
}

function decodeDataUrlToBlob(dataUrl) {
  if (typeof dataUrl !== "string") {
    return null;
  }
  const trimmed = dataUrl.trim();
  const match = /^data:(image\/[a-zA-Z0-9.+-]+)?;base64,(.+)$/i.exec(trimmed);
  if (!match) {
    return null;
  }
  try {
    const mimeType = match[1] || "image/png";
    const binary = atob(match[2]);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return new Blob([bytes], { type: mimeType });
  } catch (_error) {
    return null;
  }
}

function normalizeBinaryCandidate(candidate, fallbackMime = "image/png") {
  if (candidate instanceof Blob) {
    return candidate;
  }
  if (candidate instanceof ArrayBuffer) {
    return new Blob([candidate], { type: fallbackMime });
  }
  if (ArrayBuffer.isView(candidate)) {
    return new Blob([candidate], { type: fallbackMime });
  }
  if (Array.isArray(candidate) && candidate.length) {
    const bytes = candidate.filter((value) => Number.isFinite(value)).map((value) => Number(value));
    if (bytes.length) {
      return new Blob([Uint8Array.from(bytes)], { type: fallbackMime });
    }
  }
  if (typeof candidate === "string" && candidate.startsWith("data:image/")) {
    return decodeDataUrlToBlob(candidate);
  }
  return null;
}

function extractPreviewBlob(payload) {
  const directBlob = normalizeBinaryCandidate(payload, "image/png");
  if (directBlob) {
    return directBlob;
  }
  if (!payload || typeof payload !== "object") {
    return null;
  }
  // IMPORTANT: preview payloads differ by host/frontend bridge; probe nested wrappers before giving up so live preview remains stable across Comfy variants.
  const queue = [payload];
  const visited = new Set();
  const nestedKeys = ["blob", "buffer", "data", "preview", "image", "frame", "payload", "detail", "bytes"];
  while (queue.length) {
    const candidate = queue.shift();
    if (!candidate || typeof candidate !== "object") {
      continue;
    }
    if (visited.has(candidate)) {
      continue;
    }
    visited.add(candidate);
    const mimeType =
      (typeof candidate.mime === "string" && candidate.mime) ||
      (typeof candidate.mimetype === "string" && candidate.mimetype) ||
      (typeof candidate.content_type === "string" && candidate.content_type) ||
      "image/png";
    for (const key of nestedKeys) {
      const value = candidate[key];
      const normalized = normalizeBinaryCandidate(value, mimeType);
      if (normalized) {
        return normalized;
      }
      if (value && typeof value === "object") {
        queue.push(value);
      }
    }
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

function extractComfyViewFilename(previewUrl) {
  const raw = String(previewUrl ?? "").trim();
  if (!raw) {
    return "";
  }
  try {
    const parsed = new URL(raw, globalThis?.window?.location?.origin ?? "http://127.0.0.1");
    if (parsed.pathname !== "/view") {
      return "";
    }
    return String(parsed.searchParams.get("filename") ?? "").trim();
  } catch (_error) {
    return "";
  }
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
  if (!formRegistry?.img2img?.applyPayload && !formRegistry?.__shellStateContract?.applyToForm) {
    emitFrontendDebugWarning("shell.preview_transfer", "Img2Img applyPayload is unavailable; falling back to tab switch.");
    if (statusNode) {
      statusNode.textContent = "Img2Img form is unavailable.";
    }
    return;
  }
  const fallbackAsset = extractComfyViewFilename(previewUrl);
  try {
    const imageDataUrl = await resolvePreviewUrlAsDataUrl(previewUrl);
    if (!imageDataUrl) {
      throw new Error("Preview image is empty.");
    }
    const applied = applyCrossPanePayload(formRegistry, "img2img", {
      mode: "img2img",
      image_asset: "",
      image_data: imageDataUrl,
      mask_asset: "",
    });
    if (applied && statusNode) {
      statusNode.textContent = "Sent preview image to Img2Img";
    }
  } catch (_error) {
    emitFrontendDebugWarning(
      "shell.preview_transfer",
      "Preview transfer image decode failed; attempting asset-based fallback.",
      _error,
    );
    if (fallbackAsset) {
      // IMPORTANT: keep asset fallback for transfer flow so Send-to-Img2Img still works when preview blobs/data-url decoding fails.
      const applied = applyCrossPanePayload(formRegistry, "img2img", {
        mode: "img2img",
        image_asset: fallbackAsset,
        image_data: "",
        mask_asset: "",
      });
      if (applied && statusNode) {
        statusNode.textContent = "Sent preview image to Img2Img (asset fallback)";
      }
      return;
    }
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
  const shellStateContract = formRegistry?.__shellStateContract;
  if (shellStateContract?.activateTopTab) {
    shellStateContract.activateTopTab(tabId);
  } else {
    formRegistry.__shellTabs?.activateTabById?.(tabId);
  }
  if (statusNode && message) {
    statusNode.textContent = message;
  }
}

function applyCrossPanePayload(formRegistry, targetKey, payload, options = {}) {
  const normalizedTarget = String(targetKey ?? "").trim();
  if (!normalizedTarget) {
    return false;
  }
  const shellStateContract = formRegistry?.__shellStateContract;
  if (shellStateContract?.applyToForm) {
    return shellStateContract.applyToForm(normalizedTarget, payload, { activate: options.activate !== false });
  }
  const targetForm = formRegistry?.[normalizedTarget];
  if (!targetForm?.applyPayload) {
    return false;
  }
  if (options.activate !== false) {
    formRegistry.__shellTabs?.activateTabById?.(normalizedTarget);
  }
  targetForm.applyPayload(payload);
  return true;
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

function buildPaneModuleContext() {
  // CRITICAL: extracted pane modules depend on this explicit injection map; removing keys here can trigger runtime ReferenceError regressions across tab render paths.
  return {
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
    createActionButton,
    createIconActionButton,
    createMiniActionButton,
    buildQuicksettingCard,
    buildSelectionLibrary,
    buildSubtabShell,
    buildEmbeddingLibrary,
    buildLoraLibrary,
    appendTextElement,
    populateList,
    createList,
    bindSliderPair,
    appendPromptToken,
    transferPreviewToImg2Img,
    activateShellTab,
    updateFormFromPreset,
    syncFamilyAwareModuleQuicksetting,
    syncClipSkipAvailability,
    syncMaskField,
    resolveImg2ImgExecutionMode,
    isImg2ImgBatchMode,
    parseJsonArrayField,
    createImg2ImgMaskCanvasContract,
    createImg2ImgMaskEditor: createImg2ImgMaskCanvasEditor,
    createImg2ImgModeRouter,
    emitFrontendDebugWarning,
    submitImg2Img,
    submitTxt2Img,
    readFileAsDataUrl,
    setPreviewContent,
    installPaneStateLock,
    findPresetIdForProfile,
    setElementValue,
    syncBoundControls,
    applyPayloadToElements,
    applyCrossPanePayload,
    inspectPngInfo,
    setPngInfoSummaryVisibility,
    setListVisibility,
    updatePngInfoApplyButtons,
    writeTextToClipboard,
    applyPngInfoResult,
    syncExtrasMode,
    loadExtrasFiles,
    updateExtrasPreview,
    submitExtras,
    buildShellHeader,
    buildCompatibilitySection,
    buildCompatibilityList,
    resolveForgeNeoTheme,
  };
}

function buildTxt2ImgSection(parent, bootstrapState, formRegistry) {
  return buildTxt2ImgPane(parent, bootstrapState, formRegistry, buildPaneModuleContext());
}


function buildImg2ImgSection(parent, bootstrapState, formRegistry) {
  // CRITICAL: keep this helper/context bridge explicit; missing injections silently break pane extraction at runtime (ReferenceError in tests/live host).
  return buildImg2ImgPane(parent, bootstrapState, formRegistry, buildPaneModuleContext());
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

  const applied = applyCrossPanePayload(formRegistry, targetKey, inspectionResult.payload ?? {});
  if (!applied) {
    statusNode.textContent = `Target form unavailable: ${targetKey}`;
    return;
  }
  statusNode.textContent = `Applied ${targetKey} fields`;
}

function buildPngInfoSection(parent, bootstrapState, formRegistry) {
  return buildPngInfoPane(parent, bootstrapState, formRegistry, buildPaneModuleContext());
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
    // IMPORTANT: Extras Hires.fix toggle intentionally reuses upscale_enabled backend contract; avoid introducing a decorative frontend-only flag.
    upscale_enabled: elements.hiresEnabled.checked,
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
  return buildExtrasPane(parent, bootstrapState, formRegistry, buildPaneModuleContext());
}

function buildQueueSection(parent, bootstrapState, formRegistry) {
  return buildQueuePane(parent, bootstrapState, formRegistry, buildPaneModuleContext());
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

function buildTabbedShell(container, definitions, controller = {}, options = {}) {
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
    options.onActiveTabIdChange?.(definitions[nextIndex]?.id ?? "");
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
  const shellStateContract = createShellStateEventContract(formRegistry);
  formRegistry.__shellStateContract = shellStateContract;
  const shellTabs = {};
  shellStateContract.registerTopTabController(shellTabs);
  const tabDefinitions = [
    createTxt2ImgTabDefinition(buildTxt2ImgSection, bootstrapState, formRegistry),
    createImg2ImgTabDefinition(buildImg2ImgSection, bootstrapState, formRegistry),
    createExtrasTabDefinition(buildExtrasSection, bootstrapState, formRegistry),
    createPngInfoTabDefinition(buildPngInfoSection, bootstrapState, formRegistry),
    createQueueTabDefinition(buildQueueSection, bootstrapState, formRegistry),
  ];
  // CRITICAL: top-level tab contract validation must run before render to catch missing/duplicate pane ownership during modularization stages.
  assertTopLevelTabDefinitions(tabDefinitions);

  buildShellHeader(container, bootstrapState);
  // IMPORTANT: keep tab wiring in per-tab modules so pane ownership is explicit and future tab-level refactors do not reopen a single giant definition block.
  buildTabbedShell(container, tabDefinitions, shellTabs, {
    onActiveTabIdChange: (tabId) => shellStateContract.setActiveTopTab(tabId),
  });
  buildShellFooter(container, bootstrapState);
}
