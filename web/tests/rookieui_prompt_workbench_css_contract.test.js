import { describe, expect, test } from "vitest";

import { readRookieUIShippedCss } from "./helpers/rookieui_css_assets.js";

describe("Prompt Workbench CSS contract", () => {
  test("keeps inline settings native select menus readable in dark hosts", () => {
    const css = readRookieUIShippedCss();

    expect(css).toMatch(
      /\.rookieui-shell__prompt-workbench-inline-setting-select\s+select\s*\{[\s\S]*background:\s*color-mix\(in srgb,\s*var\(--rookieui-bg-panel\)\s*88%,\s*black\s*12%\);[\s\S]*color:\s*var\(--rookieui-text-strong\);[\s\S]*\}/,
    );
    expect(css).toMatch(
      /\.rookieui-shell__prompt-workbench-inline-setting-select\s+select\s+option\s*\{[\s\S]*background:\s*var\(--rookieui-bg-panel\);[\s\S]*color:\s*var\(--rookieui-text-strong\);[\s\S]*\}/,
    );
  });
});
