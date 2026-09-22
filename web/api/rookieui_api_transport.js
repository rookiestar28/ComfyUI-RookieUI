import { rookieUIDebugWarn } from "../rookieui_debug_deps.js";
import { DEFAULT_MODEL_FAMILY_FALLBACK_PROVENANCE } from "../rookieui_family_profile_projection.js";
import { classifyPostFailure, createPostDeadline, resolvePostPolicy } from "../rookieui_post_deadline.js";

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
  const policy = resolvePostPolicy(options, payload, fallbackData);
  const timeoutMs = options.timeoutMs ?? 60_000;
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) {
    throw new RangeError("POST timeoutMs must be a finite positive number.");
  }

  if (typeof fetchImpl !== "function") {
    rookieUIDebugWarn(policy.unavailableDebugScope, policy.unavailableMessage, { path });
    return { ok: false, status: 0, data: policy.unavailableFallbackData, failure_kind: "unavailable", request_outcome: "not-sent" };
  }

  const callerSignal = options.signal;
  if (callerSignal?.aborted) {
    return { ok: false, status: 0, data: fallbackData, failure_kind: "cancelled", request_outcome: "not-sent" };
  }
  const deadline = createPostDeadline(callerSignal, timeoutMs);
  let response;
  try {
    const requestOptions = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(policy.bodyPayload),
      signal: deadline.signal,
      timeoutMs,
    };
    response = await fetchImpl(path, requestOptions);
    deadline.clearHeaderTimeout();
    const data = await response.json();
    return response.ok
      ? { ok: true, status: response.status, data }
      : { ok: false, status: response.status, data, failure_kind: "http", request_outcome: "rejected" };
  } catch (_error) {
    const failureKind = classifyPostFailure(_error, response, deadline.abortKind);
    const requestOutcome = failureKind === "http" ? "rejected" : "unknown";
    rookieUIDebugWarn(policy.failureDebugScope, policy.failureMessage, {
      path,
      failure_kind: failureKind,
    });
    return { ok: false, status: response?.status ?? 0, data: fallbackData, failure_kind: failureKind, request_outcome: requestOutcome };
  } finally {
    deadline.dispose();
  }
}
