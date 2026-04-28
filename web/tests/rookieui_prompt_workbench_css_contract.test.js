import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

describe("Prompt Workbench CSS contract", () => {
  test("keeps inline settings native select menus readable in dark hosts", () => {
    const cssPath = resolve(process.cwd(), "web", "rookieui_panes.css");
    const css = readFileSync(cssPath, "utf8");

    expect(css).toMatch(
      /\.rookieui-shell__prompt-workbench-inline-setting-select\s+select\s*\{[\s\S]*background:\s*color-mix\(in srgb,\s*var\(--rookieui-bg-panel\)\s*88%,\s*black\s*12%\);[\s\S]*color:\s*var\(--rookieui-text-strong\);[\s\S]*\}/,
    );
    expect(css).toMatch(
      /\.rookieui-shell__prompt-workbench-inline-setting-select\s+select\s+option\s*\{[\s\S]*background:\s*var\(--rookieui-bg-panel\);[\s\S]*color:\s*var\(--rookieui-text-strong\);[\s\S]*\}/,
    );
  });
});
