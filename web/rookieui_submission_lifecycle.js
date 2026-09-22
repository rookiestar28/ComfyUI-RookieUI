import { captureSubmissionTerminalEvents, resolveActiveClientId } from "./rookieui_generation_runtime.js";

export function formatSubmissionFailure(result) {
  if (result?.request_outcome === "unknown") {
    // CRITICAL: a lost POST response may follow queue acceptance; do not invite a duplicate submission.
    return "Request outcome unknown; check queue and history before submitting again.";
  }
  if (result?.failure_kind === "cancelled") return "Request cancelled before submission.";
  const detail = String(result?.data?.detail ?? "").trim();
  const status = String(result?.data?.status ?? "unavailable");
  return detail ? `Request failed: ${status} (${detail})` : `Request failed: ${status}`;
}

export async function submitWithLifecycle(bootstrapState, submitRequest, payload, runtimeState, clientId) {
  const earlyEvents = captureSubmissionTerminalEvents(bootstrapState, runtimeState, clientId);
  const controller = new AbortController();
  const abortOnDispose = () => controller.abort();
  runtimeState.activeDisposers.add(abortOnDispose);
  try {
    const result = await submitRequest(payload, { signal: controller.signal });
    const promptId = String(result?.data?.submission?.prompt_id ?? "");
    const earlyStatus = earlyEvents.take(promptId, resolveActiveClientId(bootstrapState));
    return { result, earlyStatus };
  } finally {
    earlyEvents.dispose();
    runtimeState.activeDisposers.delete(abortOnDispose);
  }
}
