const DEBUG_STORAGE_KEY = "ROOKIEUI_DEBUG";

function coerceDebugFlag(rawValue) {
  if (typeof rawValue === "boolean") {
    return rawValue;
  }
  if (typeof rawValue === "number") {
    return rawValue !== 0;
  }
  if (typeof rawValue !== "string") {
    return false;
  }
  const normalized = rawValue.trim().toLowerCase();
  if (!normalized) {
    return false;
  }
  return ["1", "true", "yes", "on", "debug"].includes(normalized);
}

export function isRookieUIDebugEnabled() {
  const directFlag = globalThis?.__ROOKIEUI_DEBUG__;
  if (typeof directFlag !== "undefined") {
    return coerceDebugFlag(directFlag);
  }

  const runtimeFlag = globalThis?.ROOKIEUI_DEBUG;
  if (typeof runtimeFlag !== "undefined") {
    return coerceDebugFlag(runtimeFlag);
  }

  try {
    const queryValue = globalThis?.window?.location?.search
      ? new URLSearchParams(globalThis.window.location.search).get("rookieui_debug")
      : "";
    if (queryValue) {
      return coerceDebugFlag(queryValue);
    }
  } catch (_error) {
    // Ignore URL parsing failures.
  }

  try {
    const stored = globalThis?.window?.localStorage?.getItem?.(DEBUG_STORAGE_KEY);
    if (stored !== null && stored !== undefined) {
      return coerceDebugFlag(stored);
    }
  } catch (_error) {
    // Ignore storage access failures (private mode / blocked storage).
  }

  return false;
}

export function rookieUIDebugWarn(scope, message, details = null) {
  if (!isRookieUIDebugEnabled()) {
    return;
  }
  if (typeof globalThis?.console?.warn !== "function") {
    return;
  }
  const tag = `[RookieUI:${scope}]`;
  if (details && typeof details === "object") {
    globalThis.console.warn(`${tag} ${message}`, details);
    return;
  }
  globalThis.console.warn(`${tag} ${message}`);
}
