export const ROOKIEUI_TOP_LEVEL_TAB_SPECS = Object.freeze({
  txt2img: Object.freeze({ id: "txt2img", label: "Txt2Img" }),
  img2img: Object.freeze({ id: "img2img", label: "Img2Img" }),
  extras: Object.freeze({ id: "extras", label: "Extras" }),
  pnginfo: Object.freeze({ id: "pnginfo", label: "PNG Info" }),
  queue: Object.freeze({ id: "queue", label: "Queue" }),
});

const REQUIRED_TAB_IDS = Object.freeze(Object.keys(ROOKIEUI_TOP_LEVEL_TAB_SPECS));
const REQUIRED_TAB_ID_SET = new Set(REQUIRED_TAB_IDS);

export function createTopLevelTabDefinition(tabId, buildSection, bootstrapState, formRegistry) {
  const spec = ROOKIEUI_TOP_LEVEL_TAB_SPECS[tabId];
  if (!spec) {
    throw new Error(`Unknown RookieUI top-level tab id: ${String(tabId)}`);
  }
  if (typeof buildSection !== "function") {
    throw new TypeError(`Top-level tab '${tabId}' requires a section builder function.`);
  }

  return {
    id: spec.id,
    label: spec.label,
    render: (pane) => buildSection(pane, bootstrapState, formRegistry),
  };
}

export function assertTopLevelTabDefinitions(definitions) {
  if (!Array.isArray(definitions) || definitions.length === 0) {
    throw new TypeError("Top-level tab definitions must be a non-empty array.");
  }

  const seen = new Set();
  definitions.forEach((definition, index) => {
    const id = definition?.id;
    if (!REQUIRED_TAB_ID_SET.has(id)) {
      throw new Error(`Invalid top-level tab id at index ${index}: ${String(id)}`);
    }
    if (seen.has(id)) {
      throw new Error(`Duplicate top-level tab id: ${id}`);
    }
    seen.add(id);
    if (typeof definition?.label !== "string" || !definition.label.trim()) {
      throw new Error(`Top-level tab '${id}' requires a non-empty label.`);
    }
    if (typeof definition?.render !== "function") {
      throw new Error(`Top-level tab '${id}' requires a render(pane) function.`);
    }
  });

  const missing = REQUIRED_TAB_IDS.filter((id) => !seen.has(id));
  if (missing.length) {
    throw new Error(`Missing top-level tab definitions: ${missing.join(", ")}`);
  }
}
