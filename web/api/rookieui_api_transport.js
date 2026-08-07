import { rookieUIDebugWarn } from "../rookieui_debug_deps.js";
import { DEFAULT_MODEL_FAMILY_FALLBACK_PROVENANCE } from "../rookieui_family_profile_projection.js";

export function toErrorDetail(error) {
  if (!error) {
    return "";
  }
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

/**
 * Fetch a RookieUI JSON resource while preserving the compatibility fallback envelope.
 * @param {string} path
 * @param {unknown} fallbackData
 * @param {typeof globalThis.fetch} fetchImpl
 */
export async function fetchRookieUIResource(path, fallbackData, fetchImpl = globalThis.fetch) {
  if (typeof fetchImpl !== "function") {
    rookieUIDebugWarn("api.resource", "Using fallback resource because fetch() is unavailable.", { path });
    return { ok: false, source: DEFAULT_MODEL_FAMILY_FALLBACK_PROVENANCE.source, data: fallbackData };
  }

  try {
    const response = await fetchImpl(path, { headers: { Accept: "application/json" } });
    if (!response?.ok) {
      throw new Error(`Request failed with status ${response?.status ?? "unknown"}`);
    }
    return { ok: true, source: "server", data: await response.json() };
  } catch (_error) {
    rookieUIDebugWarn("api.resource", "Resource request failed; returning fallback payload.", {
      path,
      error: toErrorDetail(_error),
    });
    return { ok: false, source: DEFAULT_MODEL_FAMILY_FALLBACK_PROVENANCE.source, data: fallbackData };
  }
}

export async function postRookieUIJson(path, payload, fallbackData, fetchImpl = globalThis.fetch, options = {}) {
  const unavailableDebugScope = options.unavailableDebugScope ?? "api.resource_post";
  const unavailableMessage = options.unavailableMessage ?? "Using fallback payload because fetch() is unavailable.";
  const failureDebugScope = options.failureDebugScope ?? "api.resource_post";
  const failureMessage = options.failureMessage ?? "POST request failed; returning fallback payload.";
  const unavailableFallbackData = options.unavailableFallbackData ?? fallbackData;
  const bodyPayload = options.preserveUndefinedPayload ? payload : (payload ?? {});

  if (typeof fetchImpl !== "function") {
    rookieUIDebugWarn(unavailableDebugScope, unavailableMessage, { path });
    return { ok: false, status: 0, data: unavailableFallbackData };
  }

  try {
    const response = await fetchImpl(path, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(bodyPayload),
    });
    const data = await response.json();
    return {
      ok: response.ok,
      status: response.status,
      data,
    };
  } catch (_error) {
    rookieUIDebugWarn(failureDebugScope, failureMessage, {
      path,
      error: toErrorDetail(_error),
    });
    return { ok: false, status: 0, data: fallbackData };
  }
}
