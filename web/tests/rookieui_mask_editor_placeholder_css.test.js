import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

describe("Img2Img mask editor placeholder CSS contract", () => {
  test("keeps placeholder hidden when [hidden] attribute is present", () => {
    const cssPath = resolve(process.cwd(), "web", "rookieui_panes.css");
    const css = readFileSync(cssPath, "utf8");

    expect(css).toMatch(
      /\.rookieui-shell__mask-editor-placeholder\[hidden\]\s*\{[\s\S]*display:\s*none\s*!important;[\s\S]*\}/,
    );
  });
});
