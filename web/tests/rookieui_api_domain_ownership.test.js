import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

import * as facade from "../rookieui_api.js";
import * as controlnet from "../api/rookieui_controlnet_api.js";
import * as inventory from "../api/rookieui_inventory_api.js";
import * as promptWorkbench from "../api/rookieui_prompt_workbench_api.js";
import * as queue from "../api/rookieui_queue_api.js";
import * as xyzPlot from "../api/rookieui_xyz_plot_api.js";

const FROZEN_FACADE_EXPORTS = Object.freeze([
  "DEFAULT_MODEL_FAMILY_ENTRIES",
  "DEFAULT_MODEL_FAMILY_FALLBACK_PROVENANCE",
  "DEFAULT_MODEL_FAMILY_REGISTRY_ENTRIES",
  "DEFAULT_NEWER_FAMILY_PROFILES",
  "DEFAULT_PRIMARY_MODEL_CATEGORY_BY_FAMILY",
  "assistRookieUIPromptWorkbench",
  "buildModelFamilyStableProjection",
  "cancelRookieUIXYZPlotSession",
  "createDefaultCapabilities",
  "detectRookieUIControlNet",
  "exportRookieUIPromptWorkbench",
  "fetchRookieUIADetailerCatalog",
  "fetchRookieUICapabilities",
  "fetchRookieUICompatibility",
  "fetchRookieUIControlNetModels",
  "fetchRookieUIControlNetModules",
  "fetchRookieUIControlNetTypes",
  "fetchRookieUIHistoryPrompt",
  "fetchRookieUIModels",
  "fetchRookieUIPresets",
  "fetchRookieUIPromptWorkbenchBlacklist",
  "fetchRookieUIPromptWorkbenchCatalog",
  "fetchRookieUIPromptWorkbenchConfig",
  "fetchRookieUIPromptWorkbenchFavorites",
  "fetchRookieUIPromptWorkbenchHistory",
  "fetchRookieUIPromptWorkbenchProviders",
  "fetchRookieUIPromptWorkbenchState",
  "fetchRookieUIQueue",
  "fetchRookieUIQueueJob",
  "fetchRookieUIXYZPlotAxes",
  "fetchRookieUIXYZPlotSessionDetail",
  "fetchRookieUIXYZPlotSessions",
  "importRookieUIPromptWorkbench",
  "inspectRookieUIPngInfo",
  "parseRookieUIPngInfo",
  "submitRookieUIExtras",
  "submitRookieUIImg2Img",
  "submitRookieUITxt2Img",
  "submitRookieUIXYZPlotEstimate",
  "submitRookieUIXYZPlotRun",
  "translateRookieUIPromptWorkbench",
  "updateRookieUIPromptWorkbenchBlacklist",
  "updateRookieUIPromptWorkbenchConfig",
  "updateRookieUIPromptWorkbenchFavorites",
  "updateRookieUIPromptWorkbenchHistory",
  "updateRookieUIPromptWorkbenchState",
  "upsampleRookieUIPromptWorkbench",
]);

const DOMAIN_EXPORTS = Object.freeze({
  inventory: [
    "DEFAULT_MODEL_FAMILY_ENTRIES",
    "DEFAULT_MODEL_FAMILY_REGISTRY_ENTRIES",
    "DEFAULT_NEWER_FAMILY_PROFILES",
    "DEFAULT_PRIMARY_MODEL_CATEGORY_BY_FAMILY",
    "createDefaultCapabilities",
    "fetchRookieUICapabilities",
    "fetchRookieUICompatibility",
    "fetchRookieUIModels",
    "fetchRookieUIPresets",
  ],
  controlnet: [
    "detectRookieUIControlNet",
    "fetchRookieUIADetailerCatalog",
    "fetchRookieUIControlNetModels",
    "fetchRookieUIControlNetModules",
    "fetchRookieUIControlNetTypes",
  ],
  promptWorkbench: [
    "assistRookieUIPromptWorkbench",
    "exportRookieUIPromptWorkbench",
    "fetchRookieUIPromptWorkbenchBlacklist",
    "fetchRookieUIPromptWorkbenchCatalog",
    "fetchRookieUIPromptWorkbenchConfig",
    "fetchRookieUIPromptWorkbenchFavorites",
    "fetchRookieUIPromptWorkbenchHistory",
    "fetchRookieUIPromptWorkbenchProviders",
    "fetchRookieUIPromptWorkbenchState",
    "importRookieUIPromptWorkbench",
    "translateRookieUIPromptWorkbench",
    "updateRookieUIPromptWorkbenchBlacklist",
    "updateRookieUIPromptWorkbenchConfig",
    "updateRookieUIPromptWorkbenchFavorites",
    "updateRookieUIPromptWorkbenchHistory",
    "updateRookieUIPromptWorkbenchState",
    "upsampleRookieUIPromptWorkbench",
  ],
  xyzPlot: [
    "cancelRookieUIXYZPlotSession",
    "fetchRookieUIXYZPlotAxes",
    "fetchRookieUIXYZPlotSessionDetail",
    "fetchRookieUIXYZPlotSessions",
    "submitRookieUIXYZPlotEstimate",
    "submitRookieUIXYZPlotRun",
  ],
  queue: ["fetchRookieUIHistoryPrompt", "fetchRookieUIQueue", "fetchRookieUIQueueJob"],
});

describe("frontend API domain ownership", () => {
  test("preserves the exact compatibility facade export surface", () => {
    expect(Object.keys(facade).sort()).toEqual([...FROZEN_FACADE_EXPORTS].sort());
  });

  test("re-exports every moved operation by identity from its domain owner", () => {
    const modules = { inventory, controlnet, promptWorkbench, queue, xyzPlot };
    Object.entries(DOMAIN_EXPORTS).forEach(([domain, exportNames]) => {
      exportNames.forEach((exportName) => {
        expect(facade[exportName], `${domain}.${exportName}`).toBe(modules[domain][exportName]);
      });
    });
  });

  test("raises the checked-file floor and covers all changed API/controller/lifecycle seams", () => {
    const tsconfigPath = resolve(process.cwd(), "tsconfig.json");
    const config = JSON.parse(readFileSync(tsconfigPath, "utf8"));
    const includes = new Set(config.include ?? []);
    const required = [
      "web/api/rookieui_controlnet_api.js",
      "web/api/rookieui_inventory_api.js",
      "web/api/rookieui_prompt_workbench_api.js",
      "web/api/rookieui_queue_api.js",
      "web/api/rookieui_xyz_plot_api.js",
      "web/sidebar_tabs/img2img/rookieui_img2img_controller.js",
      "web/sidebar_tabs/img2img/rookieui_img2img_lifecycle.js",
      "web/sidebar_tabs/prompt_workbench/rookieui_prompt_workbench_controller.js",
      "web/sidebar_tabs/prompt_workbench/rookieui_prompt_workbench_lifecycle.js",
    ];

    expect(config.compilerOptions.checkJs).toBe(true);
    expect(config.compilerOptions.noEmit).toBe(true);
    expect((config.include ?? []).filter((entry) => entry.endsWith(".js")).length).toBeGreaterThan(20);
    required.forEach((entry) => expect(includes.has(entry), entry).toBe(true));
  });
});
