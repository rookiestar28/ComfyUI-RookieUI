export function createPostDeadline(callerSignal, timeoutMs) {
  const controller = new AbortController();
  let abortKind = "";
  const cancelFromCaller = () => {
    abortKind = "cancelled";
    controller.abort(callerSignal.reason);
  };
  callerSignal?.addEventListener?.("abort", cancelFromCaller, { once: true });
  // CRITICAL: this deadline ends at response headers; a timed-out POST may already be queued.
  const timeoutId = setTimeout(() => {
    abortKind = "timeout";
    controller.abort(new DOMException("Response header deadline exceeded", "TimeoutError"));
  }, timeoutMs);
  return {
    signal: controller.signal,
    get abortKind() { return abortKind; },
    clearHeaderTimeout() { clearTimeout(timeoutId); },
    dispose() {
      clearTimeout(timeoutId);
      callerSignal?.removeEventListener?.("abort", cancelFromCaller);
    },
  };
}

export function resolvePostPolicy(options, payload, fallbackData) {
  return {
    unavailableDebugScope: options.unavailableDebugScope ?? "api.resource_post",
    unavailableMessage: options.unavailableMessage ?? "Using fallback payload because fetch() is unavailable.",
    failureDebugScope: options.failureDebugScope ?? "api.resource_post",
    failureMessage: options.failureMessage ?? "POST request failed; returning fallback payload.",
    unavailableFallbackData: options.unavailableFallbackData ?? fallbackData,
    bodyPayload: options.preserveUndefinedPayload ? payload : (payload ?? {}),
  };
}

export function classifyPostFailure(error, response, abortKind) {
  if (response && !response.ok) return "http";
  if (abortKind) return abortKind;
  if (error?.name === "TimeoutError") return "timeout";
  if (error?.name === "AbortError") return "cancelled";
  if (response) return "invalid-response";
  return "network-unknown";
}
