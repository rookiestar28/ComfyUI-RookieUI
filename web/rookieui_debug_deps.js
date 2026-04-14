import { importRevisionedModule } from "./rookieui_asset_revision.js";

const debugModule = await importRevisionedModule("./rookieui_debug.js", import.meta.url);

export const { rookieUIDebugWarn } = debugModule;
