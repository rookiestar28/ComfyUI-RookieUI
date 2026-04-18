const DESKTOP_USER_AGENT_RE = /\bElectron\b/i;

/**
 * @param {{ navigator?: { userAgent?: string }, document?: unknown, electronAPI?: unknown, __COMFYUI_DESKTOP__?: boolean } | undefined} [windowRef]
 * @returns {"desktop" | "standalone-web" | "unknown"}
 */
export function detectHostSurface(windowRef = globalThis.window ?? {}) {
  const navigatorRef = typeof windowRef === "object" && windowRef ? windowRef.navigator ?? {} : {};
  const userAgent = navigatorRef.userAgent ?? "";

  if (windowRef?.__COMFYUI_DESKTOP__ === true) {
    return "desktop";
  }

  if (windowRef?.electronAPI) {
    return "desktop";
  }

  if (DESKTOP_USER_AGENT_RE.test(userAgent)) {
    return "desktop";
  }

  if (windowRef?.document) {
    return "standalone-web";
  }

  return "unknown";
}

/**
 * @param {"desktop" | "standalone-web" | "unknown"} surface
 * @returns {string}
 */
export function describeHostSurface(surface) {
  if (surface === "desktop") {
    return "Desktop host surface";
  }
  if (surface === "standalone-web") {
    return "Standalone web host surface";
  }
  return "Unknown host surface";
}

/**
 * @param {"desktop" | "standalone-web" | "unknown"} surface
 * @param {{ host_surfaces?: string[] }} [capabilities]
 * @returns {boolean}
 */
export function isHostSurfaceSupported(surface, capabilities = {}) {
  const hostSurfaces = Array.isArray(capabilities?.host_surfaces)
    ? capabilities.host_surfaces
    : [];

  if (!surface || surface === "unknown") {
    return false;
  }

  return hostSurfaces.includes(surface);
}
