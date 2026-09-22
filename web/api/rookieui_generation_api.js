import { postRookieUIJson } from "./rookieui_api_transport.js";

export async function submitRookieUITxt2Img(payload, fetchImpl = globalThis.fetch, requestOptions = {}) {
  return postRookieUIJson(
    "/rookieui/generate/txt2img",
    payload,
    {
      status: "network-unavailable",
      detail: "RookieUI txt2img submission outcome is unknown; check queue and history.",
    },
    fetchImpl,
    {
      unavailableFallbackData: {
        status: "network-unavailable",
        detail: "RookieUI txt2img submission is unavailable without fetch().",
      },
      unavailableDebugScope: "api.submit_txt2img",
      unavailableMessage: "Submission skipped because fetch() is unavailable.",
      failureDebugScope: "api.submit_txt2img",
      failureMessage: "Submission transport did not return a usable response.",
      preserveUndefinedPayload: true,
      signal: requestOptions.signal,
      timeoutMs: requestOptions.timeoutMs,
    },
  );
}

export async function submitRookieUIImg2Img(payload, fetchImpl = globalThis.fetch, requestOptions = {}) {
  return postRookieUIJson(
    "/rookieui/generate/img2img",
    payload,
    {
      status: "network-unavailable",
      detail: "RookieUI img2img submission outcome is unknown; check queue and history.",
    },
    fetchImpl,
    {
      unavailableFallbackData: {
        status: "network-unavailable",
        detail: "RookieUI img2img submission is unavailable without fetch().",
      },
      unavailableDebugScope: "api.submit_img2img",
      unavailableMessage: "Submission skipped because fetch() is unavailable.",
      failureDebugScope: "api.submit_img2img",
      failureMessage: "Submission transport did not return a usable response.",
      preserveUndefinedPayload: true,
      signal: requestOptions.signal,
      timeoutMs: requestOptions.timeoutMs,
    },
  );
}

export async function inspectRookieUIPngInfo(payload, fetchImpl = globalThis.fetch, requestOptions = {}) {
  return postRookieUIJson(
    "/rookieui/pnginfo/inspect",
    payload,
    {
      status: "network-unavailable",
      detail: "RookieUI pnginfo inspection did not return a usable response.",
    },
    fetchImpl,
    {
      unavailableFallbackData: {
        status: "network-unavailable",
        detail: "RookieUI pnginfo inspection is unavailable without fetch().",
      },
      unavailableDebugScope: "api.inspect_pnginfo",
      unavailableMessage: "Inspection skipped because fetch() is unavailable.",
      failureDebugScope: "api.inspect_pnginfo",
      failureMessage: "Inspection transport did not return a usable response.",
      preserveUndefinedPayload: true,
      signal: requestOptions.signal,
      timeoutMs: requestOptions.timeoutMs,
    },
  );
}

export async function submitRookieUIExtras(payload, fetchImpl = globalThis.fetch, requestOptions = {}) {
  return postRookieUIJson(
    "/rookieui/extras/run",
    payload,
    {
      status: "network-unavailable",
      detail: "RookieUI extras submission outcome is unknown; check queue and history.",
    },
    fetchImpl,
    {
      unavailableFallbackData: {
        status: "network-unavailable",
        detail: "RookieUI extras submission is unavailable without fetch().",
      },
      unavailableDebugScope: "api.submit_extras",
      unavailableMessage: "Submission skipped because fetch() is unavailable.",
      failureDebugScope: "api.submit_extras",
      failureMessage: "Submission transport did not return a usable response.",
      preserveUndefinedPayload: true,
      signal: requestOptions.signal,
      timeoutMs: requestOptions.timeoutMs,
    },
  );
}
