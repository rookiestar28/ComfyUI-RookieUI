import { describe, expect, test, vi } from "vitest";

import {
  ROOKIEUI_TOP_LEVEL_TAB_SPECS,
  assertTopLevelTabDefinitions,
  createTopLevelTabDefinition,
} from "../sidebar_tabs/rookieui_tab_contract.js";
import { createTxt2ImgTabDefinition } from "../sidebar_tabs/rookieui_txt2img_tab.js";

describe("rookieui top-level tab contract", () => {
  test("creates definition with canonical metadata and delegated render", () => {
    const buildSection = vi.fn();
    const bootstrapState = { source: "unit-test" };
    const formRegistry = { test: true };
    const definition = createTopLevelTabDefinition("txt2img", buildSection, bootstrapState, formRegistry);
    const pane = document.createElement("section");

    expect(definition.id).toBe("txt2img");
    expect(definition.label).toBe(ROOKIEUI_TOP_LEVEL_TAB_SPECS.txt2img.label);
    definition.render(pane);
    expect(buildSection).toHaveBeenCalledWith(pane, bootstrapState, formRegistry);
  });

  test("adapter module reuses shared contract helper", () => {
    const buildSection = vi.fn();
    const bootstrapState = { source: "adapter-test" };
    const formRegistry = { adapter: true };
    const definition = createTxt2ImgTabDefinition(buildSection, bootstrapState, formRegistry);

    expect(definition.id).toBe("txt2img");
    expect(definition.label).toBe("Txt2Img");
    definition.render(document.createElement("div"));
    expect(buildSection).toHaveBeenCalledTimes(1);
  });

  test("rejects duplicate and missing top-level tab definitions", () => {
    const makeDefinition = (id) => ({
      id,
      label: ROOKIEUI_TOP_LEVEL_TAB_SPECS[id].label,
      render: () => {},
    });

    expect(() =>
      assertTopLevelTabDefinitions([
        makeDefinition("txt2img"),
        makeDefinition("img2img"),
        makeDefinition("extras"),
        makeDefinition("pnginfo"),
        makeDefinition("txt2img"),
      ]),
    ).toThrow(/Duplicate top-level tab id/);

    expect(() =>
      assertTopLevelTabDefinitions([
        makeDefinition("txt2img"),
        makeDefinition("img2img"),
        makeDefinition("extras"),
        makeDefinition("pnginfo"),
      ]),
    ).toThrow(/Missing top-level tab definitions/);
  });
});
