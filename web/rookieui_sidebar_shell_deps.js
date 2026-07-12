import { importRevisionedModule } from "./rookieui_asset_revision.js";

const [
  utilsModule,
  debugModule,
  txt2imgTabModule,
  img2imgTabModule,
  extrasTabModule,
  pnginfoTabModule,
  queueTabModule,
  txt2imgPaneModule,
  img2imgPaneModule,
  pnginfoPaneModule,
  extrasPaneModule,
  queuePaneModule,
  tabContractModule,
  shellStateModule,
  shellPersistenceModule,
  maskCanvasModule,
  maskEditorModule,
  img2imgModeRouterModule,
  actionButtonsModule,
  generationRuntimeModule,
  previewFullscreenModule,
] = await Promise.all([
  importRevisionedModule("./rookieui_sidebar_shell_utils.js", import.meta.url),
  importRevisionedModule("./rookieui_debug.js", import.meta.url),
  importRevisionedModule("./sidebar_tabs/rookieui_txt2img_tab.js", import.meta.url),
  importRevisionedModule("./sidebar_tabs/rookieui_img2img_tab.js", import.meta.url),
  importRevisionedModule("./sidebar_tabs/rookieui_extras_tab.js", import.meta.url),
  importRevisionedModule("./sidebar_tabs/rookieui_pnginfo_tab.js", import.meta.url),
  importRevisionedModule("./sidebar_tabs/rookieui_queue_tab.js", import.meta.url),
  importRevisionedModule("./sidebar_tabs/rookieui_txt2img_pane.js", import.meta.url),
  importRevisionedModule("./sidebar_tabs/rookieui_img2img_pane.js", import.meta.url),
  importRevisionedModule("./sidebar_tabs/rookieui_pnginfo_pane.js", import.meta.url),
  importRevisionedModule("./sidebar_tabs/rookieui_extras_pane.js", import.meta.url),
  importRevisionedModule("./sidebar_tabs/rookieui_queue_pane.js", import.meta.url),
  importRevisionedModule("./sidebar_tabs/rookieui_tab_contract.js", import.meta.url),
  importRevisionedModule("./sidebar_tabs/rookieui_shell_state_contract.js", import.meta.url),
  importRevisionedModule("./sidebar_tabs/rookieui_shell_persistence.js", import.meta.url),
  importRevisionedModule("./sidebar_tabs/rookieui_img2img_mask_canvas.js", import.meta.url),
  importRevisionedModule("./sidebar_tabs/rookieui_img2img_mask_editor.js", import.meta.url),
  importRevisionedModule("./sidebar_tabs/rookieui_img2img_mode_router.js", import.meta.url),
  importRevisionedModule("./rookieui_action_buttons.js", import.meta.url),
  importRevisionedModule("./rookieui_generation_runtime.js", import.meta.url),
  importRevisionedModule("./rookieui_preview_fullscreen.js", import.meta.url),
]);

export const {
  appendTextElement,
  bindSliderPair,
  buildProfileLookup,
  buildCompatibilityList,
  buildFeatureList,
  buildParityList,
  buildTabList,
  createCheckbox,
  createField,
  createHiresFixSection,
  createInlineCheckboxField,
  createInput,
  createRangeInput,
  createSelect,
  createSliderField,
  createTextarea,
  generateDeterministicSeed,
  installExplicitFormSubmitShortcuts,
  preventSummaryToggleOnCheckbox,
  readImg2ImgReferencePayload,
  syncBoundControls,
  syncEffectiveControls,
} = utilsModule;

export const { rookieUIDebugWarn } = debugModule;
export const { createTxt2ImgTabDefinition } = txt2imgTabModule;
export const { createImg2ImgTabDefinition } = img2imgTabModule;
export const { createExtrasTabDefinition } = extrasTabModule;
export const { createPngInfoTabDefinition } = pnginfoTabModule;
export const { createQueueTabDefinition } = queueTabModule;
export const { buildTxt2ImgPane } = txt2imgPaneModule;
export const { buildImg2ImgPane } = img2imgPaneModule;
export const { buildPngInfoPane } = pnginfoPaneModule;
export const { buildExtrasPane } = extrasPaneModule;
export const { buildQueuePane } = queuePaneModule;
export const { assertTopLevelTabDefinitions } = tabContractModule;
export const { createShellStateEventContract } = shellStateModule;
export const { createShellPersistenceController, installPaneStateLock } = shellPersistenceModule;
export const { createImg2ImgMaskCanvasContract } = maskCanvasModule;
export const { createImg2ImgMaskCanvasEditor } = maskEditorModule;
export const { createImg2ImgModeRouter } = img2imgModeRouterModule;
export const { createActionButton, createMiniActionButton, createIconActionButton } = actionButtonsModule;
export const {
  resolveActiveClientId,
  createGenerationRuntimeState,
  createGenerationRuntimeHelpers,
  destroyGenerationRuntimeState,
} = generationRuntimeModule;
export const { createPreviewFullscreenViewer } = previewFullscreenModule;
