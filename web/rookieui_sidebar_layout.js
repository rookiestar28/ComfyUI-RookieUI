const ROOKIEUI_SIDEBAR_MIN_WIDTH_PX = 980;
const LAYOUT_PROPERTIES = ["minWidth", "width", "flexBasis"];

export function enforceSidebarMinWidth(container) {
  if (!container?.style) return () => {};
  const styleSnapshots = new Map();
  let disposed = false;
  let scheduledKind = "";
  let scheduledHandle = null;
  const captureStyle = (element) => {
    if (!element?.style || styleSnapshots.has(element)) return;
    styleSnapshots.set(element, Object.fromEntries(LAYOUT_PROPERTIES.map((key) => [key, element.style[key]])));
  };
  const applyMinWidth = () => {
    scheduledHandle = null;
    scheduledKind = "";
    if (disposed) return;
    // CRITICAL: SplitterPanel controls the actual sidebar width; inner content min-width alone still clips.
    const sidePanel = container.closest(".side-bar-panel");
    const closestSplitterPanel = container.closest(".p-splitterpanel");
    const splitterPanel = sidePanel instanceof HTMLElement ? sidePanel : closestSplitterPanel;
    if (splitterPanel instanceof HTMLElement) {
      captureStyle(splitterPanel);
      splitterPanel.style.minWidth = `${ROOKIEUI_SIDEBAR_MIN_WIDTH_PX}px`;
      if (splitterPanel.getBoundingClientRect?.().width < ROOKIEUI_SIDEBAR_MIN_WIDTH_PX) {
        splitterPanel.style.width = `${ROOKIEUI_SIDEBAR_MIN_WIDTH_PX}px`;
        splitterPanel.style.flexBasis = `${ROOKIEUI_SIDEBAR_MIN_WIDTH_PX}px`;
      }
    }
    const sidebarContent = container.closest(".sidebar-content-container");
    if (sidebarContent instanceof HTMLElement) {
      captureStyle(sidebarContent);
      sidebarContent.style.minWidth = `${ROOKIEUI_SIDEBAR_MIN_WIDTH_PX}px`;
      if (sidebarContent.getBoundingClientRect?.().width < ROOKIEUI_SIDEBAR_MIN_WIDTH_PX) {
        sidebarContent.style.width = `${ROOKIEUI_SIDEBAR_MIN_WIDTH_PX}px`;
      }
    }
    captureStyle(container);
    container.style.minWidth = `${ROOKIEUI_SIDEBAR_MIN_WIDTH_PX}px`;
  };
  applyMinWidth();
  if (typeof requestAnimationFrame === "function") {
    scheduledKind = "animation-frame";
    scheduledHandle = requestAnimationFrame(applyMinWidth);
  } else {
    scheduledKind = "timeout";
    scheduledHandle = setTimeout(applyMinWidth, 0);
  }
  return () => {
    if (disposed) return;
    disposed = true;
    if (scheduledHandle !== null && scheduledKind === "animation-frame" && typeof cancelAnimationFrame === "function") {
      cancelAnimationFrame(scheduledHandle);
    } else if (scheduledHandle !== null && scheduledKind === "timeout") {
      clearTimeout(scheduledHandle);
    }
    for (const [element, snapshot] of styleSnapshots) {
      for (const [property, value] of Object.entries(snapshot)) element.style[property] = value;
    }
    styleSnapshots.clear();
  };
}
