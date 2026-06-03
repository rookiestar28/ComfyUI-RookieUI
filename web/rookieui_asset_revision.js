// IMPORTANT: bump this token whenever shipped frontend module wiring changes; otherwise Comfy-host browser caches can mask live UI fixes.
export const ROOKIEUI_ASSET_REVISION = "20260603-preview-actions-hfe966230f3"; // pragma: allowlist secret

export function buildRevisionedModuleUrl(specifier, metaUrl = import.meta.url) {
  const moduleUrl = new URL(specifier, metaUrl);
  moduleUrl.searchParams.set("v", ROOKIEUI_ASSET_REVISION);
  return moduleUrl.href;
}

export function applyRevisionToUrl(url, metaUrl = import.meta.url) {
  const resolvedUrl = new URL(url, metaUrl);
  resolvedUrl.searchParams.set("v", ROOKIEUI_ASSET_REVISION);
  return resolvedUrl;
}

export async function importRevisionedModule(specifier, metaUrl = import.meta.url) {
  // IMPORTANT: keep revision ownership centralized here; scattered hard-coded ?v= imports reintroduce cache-drift regressions across sidebar modules.
  return import(buildRevisionedModuleUrl(specifier, metaUrl));
}
