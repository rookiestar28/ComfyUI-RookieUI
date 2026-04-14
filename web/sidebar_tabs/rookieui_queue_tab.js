import { createTopLevelTabDefinition } from "./rookieui_tab_deps.js";

export function createQueueTabDefinition(buildSection, bootstrapState, formRegistry) {
  return createTopLevelTabDefinition("queue", buildSection, bootstrapState, formRegistry);
}
