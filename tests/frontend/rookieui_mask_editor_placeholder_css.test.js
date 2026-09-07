import { describe, expect, test } from "vitest";

import { readRookieUIShippedCss } from "./helpers/rookieui_css_assets.js";

describe("Img2Img mask editor placeholder CSS contract", () => {
  test("keeps placeholder hidden when [hidden] attribute is present", () => {
    const css = readRookieUIShippedCss();

    expect(css).toMatch(
      /\.rookieui-shell__mask-editor-placeholder\[hidden\]\s*\{[\s\S]*display:\s*none\s*!important;[\s\S]*\}/,
    );
  });
});
