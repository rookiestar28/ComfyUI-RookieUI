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

export function resolveActiveClientId(bootstrapState) {
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

export function createGenerationRuntimeState({ previewPlaceholder = "" } = {}) {
  return {
    runToken: 0,
    disposed: false,
    activeDisposers: new Set(),
    previewUrl: "",
    previewPlaceholder,
    lastPreviewRenderAt: 0,
    progressValue: null,
    progressMax: null,
    progressSeen: false,
    previewFrameSeen: false,
    finalImageDescriptor: null,
    finalOutputArtifact: null,
    finalImageUrl: "",
  };
}

export function destroyGenerationRuntimeState(runtimeState) {
  if (!runtimeState || runtimeState.disposed) {
    return;
  }
  runtimeState.disposed = true;
  runtimeState.runToken += 1;
  for (const dispose of runtimeState.activeDisposers ?? []) {
    dispose();
  }
  runtimeState.activeDisposers?.clear?.();
  if (String(runtimeState.previewUrl ?? "").startsWith("blob:")) {
    URL.revokeObjectURL(runtimeState.previewUrl);
  }
  runtimeState.previewUrl = "";
}

function setGenerationPreview(runtimeState, previewBox, setPreviewContent, imageUrl, fallbackText) {
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
    let frameHandle = null;
    const cancelRevoke = () => {
      if (frameHandle !== null && typeof cancelAnimationFrame === "function") {
        cancelAnimationFrame(frameHandle);
      }
      frameHandle = null;
      URL.revokeObjectURL(previousPreviewUrl);
    };
    frameHandle = requestAnimationFrame(() => {
      frameHandle = null;
      runtimeState.activeDisposers?.delete?.(cancelRevoke);
      URL.revokeObjectURL(previousPreviewUrl);
    });
    runtimeState.activeDisposers?.add?.(cancelRevoke);
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

function appendStatusSuffix(statusText, suffix) {
  const normalizedSuffix = typeof suffix === "string" ? suffix.trim() : "";
  return normalizedSuffix ? `${statusText} | ${normalizedSuffix}` : statusText;
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

function normalizeFinalImageDescriptor(imageDescriptor, { selectedIndex = 0, nodeId = "", nodeImageIndex = 0, promptId = "" } = {}) {
  if (!imageDescriptor?.filename) {
    return null;
  }
  const descriptorSelectedIndex = Number.isInteger(imageDescriptor.selectedIndex)
    ? imageDescriptor.selectedIndex
    : selectedIndex;
  const descriptorNodeImageIndex = Number.isInteger(imageDescriptor.nodeImageIndex)
    ? imageDescriptor.nodeImageIndex
    : nodeImageIndex;
  const normalizedSelectedIndex =
    Number.isInteger(descriptorSelectedIndex) && descriptorSelectedIndex >= 0 ? descriptorSelectedIndex : 0;
  const normalizedNodeImageIndex =
    Number.isInteger(descriptorNodeImageIndex) && descriptorNodeImageIndex >= 0
      ? descriptorNodeImageIndex
      : normalizedSelectedIndex;
  const metadata =
    imageDescriptor.metadata && typeof imageDescriptor.metadata === "object"
      ? { ...imageDescriptor.metadata }
      : null;
  const infotext =
    typeof imageDescriptor.infotext === "string"
      ? imageDescriptor.infotext
      : typeof imageDescriptor.parameters === "string"
        ? imageDescriptor.parameters
        : "";
  return {
    filename: imageDescriptor.filename,
    subfolder: typeof imageDescriptor.subfolder === "string" ? imageDescriptor.subfolder : "",
    type: typeof imageDescriptor.type === "string" ? imageDescriptor.type : "output",
    selectedIndex: normalizedSelectedIndex,
    nodeId: typeof imageDescriptor.nodeId === "string" ? imageDescriptor.nodeId : nodeId,
    nodeImageIndex: normalizedNodeImageIndex,
    promptId: typeof imageDescriptor.promptId === "string" ? imageDescriptor.promptId : promptId,
    metadata,
    infotext,
  };
}

function buildPreviewActionArtifact({
  previewUrl = "",
  finalImageDescriptor = null,
  selectedIndex = 0,
  source = "runtime-preview",
  sourceContext = {},
} = {}) {
  const normalizedSelectedIndex = Number.isInteger(selectedIndex) && selectedIndex >= 0 ? selectedIndex : 0;
  const descriptor = finalImageDescriptor ? normalizeFinalImageDescriptor(finalImageDescriptor) : null;
  return {
    previewUrl,
    imageDataUrl: "",
    fallbackAsset: previewUrl ? extractComfyViewFilename(previewUrl) : "",
    finalImageDescriptor: descriptor,
    selectedIndex: descriptor?.selectedIndex ?? normalizedSelectedIndex,
    source,
    sourceContext,
    metadata: descriptor?.metadata ?? null,
    infotext: descriptor?.infotext ?? "",
  };
}

const IMG2IMG_METADATA_PAYLOAD_KEYS = Object.freeze([
  "prompt",
  "negative_prompt",
  "profile",
  "checkpoint_name",
  "vae_name",
  "text_encoder_name",
  "dtype_profile",
  "width",
  "height",
  "resize_mode",
  "steps",
  "cfg_scale",
  "shift",
  "flux_guidance",
  "edit_megapixels",
  "sampler_name",
  "scheduler_name",
  "prompt_enhancement_enabled",
  "seed",
  "seed_extra",
  "batch_size",
  "clip_skip",
  "denoise_strength",
  "hires_enabled",
  "hires_scale",
  "hires_steps",
  "hires_denoise",
  "hires_upscale_method",
  "template_lora_name",
  "lora_name",
  "lora_strength_model",
  "lora_strength_clip",
]);

function sanitizeImg2ImgMetadataPayload(rawPayload) {
  if (!rawPayload || typeof rawPayload !== "object") {
    return {};
  }
  const payload = {};
  for (const key of IMG2IMG_METADATA_PAYLOAD_KEYS) {
    if (Object.prototype.hasOwnProperty.call(rawPayload, key)) {
      payload[key] = rawPayload[key];
    }
  }
  return payload;
}

async function inspectPreviewMetadataPayload(imageDataUrl, inspectPngInfoRequest) {
  if (!imageDataUrl || typeof inspectPngInfoRequest !== "function") {
    return { ok: false, payload: {}, sourceType: "", error: null };
  }
  try {
    const result = await inspectPngInfoRequest({ image_data: imageDataUrl });
    if (!result?.ok) {
      return { ok: false, payload: {}, sourceType: "", error: result?.data ?? null };
    }
    return {
      ok: true,
      payload: sanitizeImg2ImgMetadataPayload(result.data?.payload),
      sourceType: String(result.data?.source_type ?? ""),
      error: null,
    };
  } catch (error) {
    return { ok: false, payload: {}, sourceType: "", error };
  }
}

function buildImg2ImgPreviewActionPayload({
  imageDataUrl = "",
  fallbackAsset = "",
  metadataPayload = {},
  mode = "img2img",
} = {}) {
  return {
    ...metadataPayload,
    // IMPORTANT: preview send-to must always overwrite image/mask/batch handoff fields; metadata parsers may expose source fields from the inspected PNG that must not revive stale inpaint or batch state.
    mode,
    image_asset: imageDataUrl ? "" : fallbackAsset,
    image_data: imageDataUrl,
    mask_asset: "",
    mask_data: "",
    batch_images: [],
  };
}

function buildPreviewPaneActionPayload(payload, previewAction) {
  const sourceContext = payload?.sourceContext && typeof payload.sourceContext === "object" ? payload.sourceContext : {};
  // IMPORTANT: keep preview action provenance on PNG Info/Extras handoffs; image-only assertions missed A1111 send-to parity regressions.
  return {
    preview_action: previewAction,
    preview_source: String(payload?.source ?? ""),
    preview_selected_index: Number.isInteger(payload?.selectedIndex) ? payload.selectedIndex : 0,
    preview_prompt_id: String(sourceContext.promptId ?? payload?.finalImageDescriptor?.promptId ?? ""),
    preview_node_id: String(sourceContext.nodeId ?? payload?.finalImageDescriptor?.nodeId ?? ""),
    image_asset: payload?.imageDataUrl ? "" : payload?.fallbackAsset ?? "",
    image_data: payload?.imageDataUrl ?? "",
  };
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
  let selectedIndex = 0;
  for (const [nodeId, nodeOutput] of Object.entries(outputs)) {
    if (!nodeOutput || typeof nodeOutput !== "object") {
      continue;
    }
    const images = Array.isArray(nodeOutput.images) ? nodeOutput.images : [];
    for (let nodeImageIndex = 0; nodeImageIndex < images.length; nodeImageIndex += 1) {
      const image = images[nodeImageIndex];
      if (!image || typeof image !== "object") {
        selectedIndex += 1;
        continue;
      }
      const filename = typeof image.filename === "string" ? image.filename : "";
      if (!filename) {
        selectedIndex += 1;
        continue;
      }
      return normalizeFinalImageDescriptor(
        {
          ...image,
          filename,
        },
        {
          selectedIndex,
          nodeId,
          nodeImageIndex,
          promptId,
        },
      );
    }
  }
  return null;
}

function resolveHostApiUrl(bootstrapState, path) {
  const runtimeApi = resolveRuntimeApi(bootstrapState);
  if (typeof runtimeApi?.apiURL === "function") {
    return runtimeApi.apiURL(path);
  }
  return path;
}

function buildComfyViewUrl(imageDescriptor, bootstrapState = null) {
  if (!imageDescriptor?.filename) {
    return "";
  }
  const params = new URLSearchParams({
    filename: imageDescriptor.filename,
    subfolder: imageDescriptor.subfolder || "",
    type: imageDescriptor.type || "output",
  });
  return resolveHostApiUrl(bootstrapState, `/view?${params.toString()}`);
}

function setFinalGenerationPreview(runtimeState, previewBox, setPreviewContent, imageDescriptor, bootstrapState) {
  const normalizedDescriptor = normalizeFinalImageDescriptor(imageDescriptor);
  const finalImageUrl = buildComfyViewUrl(normalizedDescriptor, bootstrapState);
  if (!finalImageUrl) {
    return false;
  }
  runtimeState.finalImageDescriptor = normalizedDescriptor;
  runtimeState.finalImageUrl = finalImageUrl;
  runtimeState.finalOutputArtifact = buildPreviewActionArtifact({
    previewUrl: finalImageUrl,
    finalImageDescriptor: normalizedDescriptor,
    selectedIndex: normalizedDescriptor.selectedIndex,
    source: "final-output",
    sourceContext: {
      promptId: normalizedDescriptor.promptId,
      nodeId: normalizedDescriptor.nodeId,
      nodeImageIndex: normalizedDescriptor.nodeImageIndex,
    },
  });
  setGenerationPreview(runtimeState, previewBox, setPreviewContent, finalImageUrl, runtimeState.previewPlaceholder);
  return true;
}

async function resolveFinalHistoryImage(bootstrapState, promptId, { attempts = 4, delayMs = 300 } = {}) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const historyResult = await bootstrapState.fetchPromptHistoryRequest(promptId);
    if (historyResult.ok) {
      const outputImage = extractPrimaryHistoryImage(historyResult.data, promptId);
      if (outputImage) {
        return outputImage;
      }
    }
    if (attempt + 1 < attempts) {
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }
  return null;
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
    if (parsed.pathname !== "/view" && !parsed.pathname.endsWith("/view")) {
      return "";
    }
    return String(parsed.searchParams.get("filename") ?? "").trim();
  } catch (_error) {
    return "";
  }
}

export function resolvePreviewActionArtifact(runtimeState, previewBox = null, { preferFinalOutput = true } = {}) {
  if (preferFinalOutput && runtimeState?.finalImageUrl) {
    // CRITICAL: output action buttons must prefer the completed final artifact; falling back to a stale DOM/live-preview frame drops embedded metadata and breaks A1111 send-to parity.
    return buildPreviewActionArtifact({
      previewUrl: runtimeState.finalImageUrl,
      finalImageDescriptor: runtimeState.finalImageDescriptor,
      selectedIndex: runtimeState.finalImageDescriptor?.selectedIndex ?? 0,
      source: "final-output",
      sourceContext: runtimeState.finalOutputArtifact?.sourceContext ?? {},
    });
  }
  if (previewBox) {
    const previewImage = previewBox.querySelector?.("img");
    if (previewImage?.src) {
      return buildPreviewActionArtifact({
        previewUrl: previewImage.src,
        selectedIndex: 0,
        source: "preview-dom",
        sourceContext: {},
      });
    }
  }
  if (runtimeState?.finalImageUrl) {
    return buildPreviewActionArtifact({
      previewUrl: runtimeState.finalImageUrl,
      finalImageDescriptor: runtimeState.finalImageDescriptor,
      selectedIndex: runtimeState.finalImageDescriptor?.selectedIndex ?? 0,
      source: "final-output",
      sourceContext: runtimeState.finalOutputArtifact?.sourceContext ?? {},
    });
  }
  if (runtimeState?.previewUrl) {
    return buildPreviewActionArtifact({
      previewUrl: runtimeState.previewUrl,
      selectedIndex: 0,
      source: "runtime-preview",
      sourceContext: {},
    });
  }
  return buildPreviewActionArtifact();
}

function resolveCurrentPreviewUrl(runtimeState, previewBox = null, options = {}) {
  return resolvePreviewActionArtifact(runtimeState, previewBox, options).previewUrl;
}

async function resolvePreviewImagePayload(runtimeState, previewBox = null, options = {}) {
  const artifact = resolvePreviewActionArtifact(runtimeState, previewBox, options);
  const previewUrl = artifact.previewUrl;
  if (!previewUrl) {
    return artifact;
  }
  try {
    const imageDataUrl = await resolvePreviewUrlAsDataUrl(previewUrl);
    return { ...artifact, imageDataUrl };
  } catch (error) {
    if (artifact.fallbackAsset) {
      return { ...artifact, imageDataUrl: "", error };
    }
    throw error;
  }
}

export function createGenerationRuntimeHelpers({
  emitFrontendDebugWarning,
  setPreviewContent,
  applyCrossPanePayload,
  activateShellTab,
} = {}) {
  if (
    typeof emitFrontendDebugWarning !== "function" ||
    typeof setPreviewContent !== "function" ||
    typeof applyCrossPanePayload !== "function" ||
    typeof activateShellTab !== "function"
  ) {
    throw new Error("Generation runtime helpers require debug, preview, cross-pane apply, and tab-activation callbacks.");
  }

  const transferPreviewToImageMode = async (
    formRegistry,
    runtimeState,
    statusNode,
    previewBox = null,
    { inspectPngInfoRequest = null, mode = "img2img", label = "Img2Img" } = {},
  ) => {
    const { previewUrl, imageDataUrl, fallbackAsset } = await resolvePreviewImagePayload(runtimeState, previewBox);
    if (!previewUrl) {
      activateShellTab(formRegistry, "img2img", statusNode, `Opened ${label}`);
      return;
    }
    if (!formRegistry?.img2img?.applyPayload && !formRegistry?.__shellStateContract?.applyToForm) {
      emitFrontendDebugWarning("shell.preview_transfer", `${label} applyPayload is unavailable; falling back to tab switch.`);
      if (statusNode) {
        statusNode.textContent = `${label} form is unavailable.`;
      }
      return;
    }
    if (imageDataUrl) {
      const metadataResult = await inspectPreviewMetadataPayload(imageDataUrl, inspectPngInfoRequest);
      const applied = applyCrossPanePayload(
        formRegistry,
        "img2img",
        buildImg2ImgPreviewActionPayload({
          imageDataUrl,
          fallbackAsset: "",
          metadataPayload: metadataResult.payload,
          mode,
        }),
      );
      if (applied && statusNode) {
        statusNode.textContent =
          metadataResult.ok && Object.keys(metadataResult.payload).length
            ? `Sent preview image and metadata to ${label}`
            : `Sent preview image to ${label} (metadata unavailable)`;
      }
      return;
    }
    if (fallbackAsset) {
      const applied = applyCrossPanePayload(
        formRegistry,
        "img2img",
        buildImg2ImgPreviewActionPayload({
          imageDataUrl: "",
          fallbackAsset,
          mode,
        }),
      );
      if (applied && statusNode) {
        statusNode.textContent = `Sent preview image to ${label} (asset fallback)`;
      }
      return;
    }
    activateShellTab(formRegistry, "img2img", statusNode, `Opened ${label}`);
  };

  const transferPreviewToImg2Img = async (formRegistry, runtimeState, statusNode, previewBox = null, options = {}) => {
    return transferPreviewToImageMode(formRegistry, runtimeState, statusNode, previewBox, {
      ...options,
      mode: "img2img",
      label: "Img2Img",
    });
  };

  const transferPreviewToInpaint = async (formRegistry, runtimeState, statusNode, previewBox = null, options = {}) => {
    return transferPreviewToImageMode(formRegistry, runtimeState, statusNode, previewBox, {
      ...options,
      mode: "inpaint",
      label: "Inpaint",
    });
  };

  const transferPreviewImageToPane = async (
    formRegistry,
    targetKey,
    runtimeState,
    statusNode,
    previewBox = null,
    { appliedMessage = "Sent preview image", previewAction = "", requireDataUrl = false } = {},
  ) => {
    let payload;
    try {
      payload = await resolvePreviewImagePayload(runtimeState, previewBox);
    } catch (error) {
      emitFrontendDebugWarning("shell.preview_transfer", "Preview image handoff failed.", error);
      if (statusNode) {
        statusNode.textContent = "Preview image is unavailable.";
      }
      return false;
    }
    if (!payload.previewUrl) {
      activateShellTab(formRegistry, targetKey, statusNode, `Opened ${targetKey}`);
      return false;
    }
    if (requireDataUrl && !payload.imageDataUrl) {
      if (statusNode) {
        statusNode.textContent = "Preview image data is unavailable.";
      }
      activateShellTab(formRegistry, targetKey, statusNode, "Preview image data is unavailable.");
      return false;
    }
    let applied = applyCrossPanePayload(
      formRegistry,
      targetKey,
      buildPreviewPaneActionPayload(payload, previewAction),
      { activate: true },
    );
    if (!applied) {
      // IMPORTANT: PNG Info/Extras panes may be lazily registered; activate once so the pane can install applyPayload, then retry the handoff.
      activateShellTab(formRegistry, targetKey, statusNode, `Opened ${targetKey}`);
      for (let attempt = 0; attempt < 5; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 20));
        applied = applyCrossPanePayload(
          formRegistry,
          targetKey,
          buildPreviewPaneActionPayload(payload, previewAction),
          { activate: true },
        );
        if (applied) {
          break;
        }
      }
    }
    if (!applied && ["pnginfo", "extras"].includes(targetKey) && typeof globalThis.document?.dispatchEvent === "function") {
      const fallbackEvent = new CustomEvent(`rookieui:${targetKey}:preview-handoff`, {
        cancelable: true,
        detail: buildPreviewPaneActionPayload(payload, previewAction),
      });
      applied = globalThis.document.dispatchEvent(fallbackEvent) === false;
    }
    if (statusNode) {
      statusNode.textContent = applied ? appliedMessage : `${targetKey} form is unavailable.`;
    }
    return applied;
  };

  const transferPreviewToPngInfo = async (formRegistry, runtimeState, statusNode, previewBox = null) => {
    return transferPreviewImageToPane(formRegistry, "pnginfo", runtimeState, statusNode, previewBox, {
      appliedMessage: "Inspecting preview image in PNG Info",
      previewAction: "inspect-pnginfo",
      requireDataUrl: true,
    });
  };

  const transferPreviewToExtras = async (formRegistry, runtimeState, statusNode, previewBox = null) => {
    return transferPreviewImageToPane(formRegistry, "extras", runtimeState, statusNode, previewBox, {
      appliedMessage: "Sent selected preview image to Extras",
      previewAction: "send-to-extras",
      requireDataUrl: true,
    });
  };

  const trackGenerationRuntime = async (bootstrapState, promptId, statusNode, runtimeState, previewBox, statusSuffix = "") => {
    if (!runtimeState || !promptId || runtimeState.disposed) {
      return;
    }
    const runToken = runtimeState.runToken + 1;
    runtimeState.runToken = runToken;
    runtimeState.progressValue = null;
    runtimeState.progressMax = null;
    runtimeState.progressSeen = false;
    runtimeState.previewFrameSeen = false;
    runtimeState.finalImageDescriptor = null;
    runtimeState.finalOutputArtifact = null;
    runtimeState.finalImageUrl = "";
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
      listeners.length = 0;
    };
    runtimeState.activeDisposers?.add?.(unregisterRuntimeListeners);
    const waitForRuntimeDelay = (delayMs) =>
      new Promise((resolve) => {
        let settled = false;
        const finish = () => {
          if (settled) return;
          settled = true;
          clearTimeout(timeoutHandle);
          runtimeState.activeDisposers?.delete?.(finish);
          resolve();
        };
        const timeoutHandle = setTimeout(finish, delayMs);
        runtimeState.activeDisposers?.add?.(finish);
      });

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
      statusNode.textContent = appendStatusSuffix(
        formatGenerationProgress("in_progress", runtimeState.progressValue, runtimeState.progressMax),
        statusSuffix,
      );
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
      setGenerationPreview(runtimeState, previewBox, setPreviewContent, previewUrl, runtimeState.previewPlaceholder);
    };
    // IMPORTANT: host event names differ across Comfy surfaces; keep both listeners for stable in-sidebar preview updates.
    registerRuntimeListener("b_preview_with_metadata", applyPreviewEvent);
    registerRuntimeListener("b_preview", applyPreviewEvent);

    const startTime = Date.now();
    const maxDurationMs = 5 * 60 * 1000;
    let lastHistoryPollAt = 0;
    let finalStatus = "pending";
    try {
      while (!runtimeState.disposed && runtimeState.runToken === runToken && Date.now() - startTime < maxDurationMs) {
        const scopedClientId = resolveActiveClientId(bootstrapState);
        const jobResult = await bootstrapState.fetchQueueJobRequest(promptId, scopedClientId);
        if (runtimeState.disposed || runtimeState.runToken !== runToken) {
          return;
        }
        if (!jobResult.ok) {
          statusNode.textContent = appendStatusSuffix("Waiting for queue sync...", statusSuffix);
          await waitForRuntimeDelay(800);
          continue;
        }
        const queueJob = jobResult.data?.job ?? null;
        if (!queueJob) {
          statusNode.textContent = appendStatusSuffix("Waiting for queue registration...", statusSuffix);
          await waitForRuntimeDelay(800);
          continue;
        }

        finalStatus = String(queueJob.status ?? "pending");
        statusNode.textContent = appendStatusSuffix(
          formatGenerationProgress(finalStatus, runtimeState.progressValue, runtimeState.progressMax),
          statusSuffix,
        );
        if (runtimeState.progressSeen && !runtimeState.previewFrameSeen && Date.now() - startTime >= 4000) {
          // CRITICAL: when host runs with --preview-method none, progress updates still arrive but live preview frames never do; keep an explicit diagnostic instead of silent placeholder stalling.
          statusNode.textContent = appendStatusSuffix(
            `${formatGenerationProgress(finalStatus, runtimeState.progressValue, runtimeState.progressMax)} | ` +
              "Live preview frames unavailable (host preview may be disabled).",
            statusSuffix,
          );
        }
        if (["completed", "failed", "cancelled"].includes(finalStatus)) {
          break;
        }
        if (Date.now() - lastHistoryPollAt >= 1500) {
          const historyResult = await bootstrapState.fetchPromptHistoryRequest(promptId);
          const previewImage = extractPrimaryHistoryImage(historyResult.data, promptId);
          if (previewImage) {
            runtimeState.previewFrameSeen = true;
            setFinalGenerationPreview(runtimeState, previewBox, setPreviewContent, previewImage, bootstrapState);
          }
          lastHistoryPollAt = Date.now();
        }
        await waitForRuntimeDelay(800);
      }
    } finally {
      unregisterRuntimeListeners();
      runtimeState.activeDisposers?.delete?.(unregisterRuntimeListeners);
    }

    if (runtimeState.runToken !== runToken) {
      return;
    }

    if (finalStatus === "completed") {
      const outputImage = await resolveFinalHistoryImage(bootstrapState, promptId, {
        attempts: runtimeState.finalImageDescriptor ? 1 : 4,
        delayMs: 300,
      });
      if (outputImage && setFinalGenerationPreview(runtimeState, previewBox, setPreviewContent, outputImage, bootstrapState)) {
        statusNode.textContent = appendStatusSuffix(`Completed: ${promptId}`, statusSuffix);
        return;
      }
      if (runtimeState.finalImageUrl) {
        statusNode.textContent = appendStatusSuffix(`Completed: ${promptId}`, statusSuffix);
        return;
      }
      const fallbackDetail = runtimeState.previewUrl?.startsWith("blob:")
        ? "final image unavailable; showing live preview"
        : "no image output found";
      statusNode.textContent = appendStatusSuffix(`Completed: ${promptId} (${fallbackDetail})`, statusSuffix);
      return;
    }
    if (finalStatus === "failed") {
      statusNode.textContent = appendStatusSuffix(`Generation failed: ${promptId}`, statusSuffix);
      return;
    }
    if (finalStatus === "cancelled") {
      statusNode.textContent = appendStatusSuffix(`Generation cancelled: ${promptId}`, statusSuffix);
      return;
    }
    statusNode.textContent = appendStatusSuffix(`Runtime sync timed out: ${promptId}`, statusSuffix);
  };

  return {
    transferPreviewToImg2Img,
    transferPreviewToInpaint,
    transferPreviewToPngInfo,
    transferPreviewToExtras,
    trackGenerationRuntime,
  };
}
