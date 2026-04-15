import { importRevisionedModule } from "../rookieui_asset_revision.js";

const [controlNetModule, adetailerModule] = await Promise.all([
  importRevisionedModule("./rookieui_controlnet_units.js", import.meta.url),
  importRevisionedModule("./rookieui_adetailer_units.js", import.meta.url),
]);

export const { createControlNetUnitEditor } = controlNetModule;
export const { createADetailerEditor } = adetailerModule;
