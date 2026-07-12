export function captureContainerMarkers(container) {
  const className = container.className;
  const hadTheme = Object.prototype.hasOwnProperty.call(container.dataset, "theme");
  const theme = container.dataset.theme;
  return () => {
    container.className = className;
    if (hadTheme) container.dataset.theme = theme;
    else delete container.dataset.theme;
  };
}

export function destroyTabLifecycles(lifecycles, activeIndex) {
  if (activeIndex >= 0) lifecycles[activeIndex]?.onDeactivate?.();
  lifecycles.forEach((lifecycle) => lifecycle?.destroy?.());
  return -1;
}

export function createShellDisposer(container, shellTabs, restoreMarkers) {
  let destroyed = false;
  return () => {
    if (destroyed) return;
    destroyed = true;
    shellTabs.destroy?.();
    container.replaceChildren();
    restoreMarkers();
  };
}

export function buildShellFooter(container, bootstrapState) {
  const footer = document.createElement("footer");
  footer.className = "rookieui-shell__footer";
  const theme = container.dataset.theme ?? "normal";
  footer.textContent = `host: ${bootstrapState.hostSurface ?? "unknown"} • models: ${bootstrapState.models?.source ?? "fallback"} • theme: ${theme}`;
  container.appendChild(footer);
}
