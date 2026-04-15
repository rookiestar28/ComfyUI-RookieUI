import { importRevisionedModule } from "../rookieui_asset_revision.js";

const brushModule = await importRevisionedModule("./rookieui_source_canvas_brush.js", import.meta.url);

export const { createSourceCanvasBrushController } = brushModule;
