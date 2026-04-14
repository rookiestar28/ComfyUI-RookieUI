import { createTopLevelTabDefinition } from "./rookieui_tab_deps.js";

export function createTxt2ImgTabDefinition(buildSection, bootstrapState, formRegistry) {
  return createTopLevelTabDefinition("txt2img", buildSection, bootstrapState, formRegistry);
}
