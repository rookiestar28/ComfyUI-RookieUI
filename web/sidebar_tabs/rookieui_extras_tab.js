import { createTopLevelTabDefinition } from "./rookieui_tab_contract.js?v=20260411-r51-tab-contract";

export function createExtrasTabDefinition(buildSection, bootstrapState, formRegistry) {
  return createTopLevelTabDefinition("extras", buildSection, bootstrapState, formRegistry);
}
