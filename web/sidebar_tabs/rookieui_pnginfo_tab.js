import { createTopLevelTabDefinition } from "./rookieui_tab_deps.js";

export function createPngInfoTabDefinition(buildSection, bootstrapState, formRegistry) {
  return createTopLevelTabDefinition("pnginfo", buildSection, bootstrapState, formRegistry);
}
