import { createTopLevelTabDefinition } from "./rookieui_tab_contract.js?v=20260411-r51-tab-contract";

export function createQueueTabDefinition(buildSection, bootstrapState, formRegistry) {
  return createTopLevelTabDefinition("queue", buildSection, bootstrapState, formRegistry);
}
