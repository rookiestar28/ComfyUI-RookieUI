import { createTopLevelTabDefinition } from "./rookieui_tab_deps.js";

export function createImg2ImgTabDefinition(buildSection, bootstrapState, formRegistry) {
  return createTopLevelTabDefinition("img2img", buildSection, bootstrapState, formRegistry);
}
