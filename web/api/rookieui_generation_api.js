import { postRookieUIJson } from "./rookieui_api_transport.js";

export async function submitRookieUITxt2Img(payload, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/generate/txt2img",
    payload,
    {
      status: "network-unavailable",
      detail: "RookieUI txt2img submission failed before reaching the backend.",
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
      failureMessage: "Submission failed before reaching backend.",
      preserveUndefinedPayload: true,
    },
  );
}

export async function submitRookieUIImg2Img(payload, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/generate/img2img",
    payload,
    {
      status: "network-unavailable",
      detail: "RookieUI img2img submission failed before reaching the backend.",
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
      failureMessage: "Submission failed before reaching backend.",
      preserveUndefinedPayload: true,
    },
  );
}

export async function inspectRookieUIPngInfo(payload, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/pnginfo/inspect",
    payload,
    {
      status: "network-unavailable",
      detail: "RookieUI pnginfo inspection failed before reaching the backend.",
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
      failureMessage: "Inspection request failed before reaching backend.",
      preserveUndefinedPayload: true,
    },
  );
}

export async function submitRookieUIExtras(payload, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/extras/run",
    payload,
    {
      status: "network-unavailable",
      detail: "RookieUI extras submission failed before reaching the backend.",
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
      failureMessage: "Submission failed before reaching backend.",
      preserveUndefinedPayload: true,
    },
  );
}
