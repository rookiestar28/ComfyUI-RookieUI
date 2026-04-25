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
    previewUrl: "",
    previewPlaceholder,
    lastPreviewRenderAt: 0,
    progressValue: null,
    progressMax: null,
    progressSeen: false,
    previewFrameSeen: false,
  };
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

  const transferPreviewToImg2Img = async (formRegistry, runtimeState, statusNode, previewBox = null) => {
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
        mask_data: "",
        batch_images: [],
      });
      if (applied && statusNode) {
        statusNode.textContent = "Sent preview image to Img2Img";
      }
    } catch (error) {
      emitFrontendDebugWarning(
        "shell.preview_transfer",
        "Preview transfer image decode failed; attempting asset-based fallback.",
        error,
      );
      if (fallbackAsset) {
        const applied = applyCrossPanePayload(formRegistry, "img2img", {
          mode: "img2img",
          image_asset: fallbackAsset,
          image_data: "",
          mask_asset: "",
          mask_data: "",
          batch_images: [],
        });
        if (applied && statusNode) {
          statusNode.textContent = "Sent preview image to Img2Img (asset fallback)";
        }
        return;
      }
      activateShellTab(formRegistry, "img2img", statusNode, "Opened Img2Img");
    }
  };

  const trackGenerationRuntime = async (bootstrapState, promptId, statusNode, runtimeState, previewBox, statusSuffix = "") => {
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
      while (runtimeState.runToken === runToken && Date.now() - startTime < maxDurationMs) {
        const scopedClientId = resolveActiveClientId(bootstrapState);
        const jobResult = await bootstrapState.fetchQueueJobRequest(promptId, scopedClientId);
        if (!jobResult.ok) {
          statusNode.textContent = appendStatusSuffix("Waiting for queue sync...", statusSuffix);
          await new Promise((resolve) => setTimeout(resolve, 800));
          continue;
        }
        const queueJob = jobResult.data?.job ?? null;
        if (!queueJob) {
          statusNode.textContent = appendStatusSuffix("Waiting for queue registration...", statusSuffix);
          await new Promise((resolve) => setTimeout(resolve, 800));
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
          const previewUrl = buildComfyViewUrl(previewImage);
          if (previewUrl) {
            runtimeState.previewFrameSeen = true;
            setGenerationPreview(runtimeState, previewBox, setPreviewContent, previewUrl, runtimeState.previewPlaceholder);
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
        setGenerationPreview(runtimeState, previewBox, setPreviewContent, finalImageUrl, runtimeState.previewPlaceholder);
        statusNode.textContent = appendStatusSuffix(`Completed: ${promptId}`, statusSuffix);
        return;
      }
      statusNode.textContent = appendStatusSuffix(`Completed: ${promptId} (no image output found)`, statusSuffix);
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
    trackGenerationRuntime,
  };
}
