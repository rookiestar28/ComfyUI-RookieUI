import { createTopLevelTabDefinition } from "./rookieui_tab_contract.js?v=20260411-r51-tab-contract";

export function createTxt2ImgTabDefinition(buildSection, bootstrapState, formRegistry) {
  return createTopLevelTabDefinition("txt2img", buildSection, bootstrapState, formRegistry);
}
