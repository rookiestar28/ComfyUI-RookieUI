import { importRevisionedModule } from "../rookieui_asset_revision.js";

const [controlNetModule, adetailerModule, promptWorkbenchModule, xyzPlotModule] = await Promise.all([
  importRevisionedModule("./rookieui_controlnet_units.js", import.meta.url),
  importRevisionedModule("./rookieui_adetailer_units.js", import.meta.url),
  importRevisionedModule("./rookieui_prompt_workbench_shell.js", import.meta.url),
  importRevisionedModule("./rookieui_xyz_plot_shell.js", import.meta.url),
]);

export const { createControlNetUnitEditor } = controlNetModule;
export const { createADetailerEditor } = adetailerModule;
export const { createPromptWorkbenchShell } = promptWorkbenchModule;
export const { createXYZPlotShell } = xyzPlotModule;
