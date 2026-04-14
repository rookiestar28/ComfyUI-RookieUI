import { importRevisionedModule } from "../rookieui_asset_revision.js";

const tabContractModule = await importRevisionedModule("./rookieui_tab_contract.js", import.meta.url);

export const { createTopLevelTabDefinition } = tabContractModule;
