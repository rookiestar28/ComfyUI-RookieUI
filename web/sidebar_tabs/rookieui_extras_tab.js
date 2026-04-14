import { createTopLevelTabDefinition } from "./rookieui_tab_deps.js";

export function createExtrasTabDefinition(buildSection, bootstrapState, formRegistry) {
  return createTopLevelTabDefinition("extras", buildSection, bootstrapState, formRegistry);
}
