import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

describe("ControlNet source canvas CSS contract", () => {
  test("keeps brush toolbar and controls bounded inside preview stages", () => {
    const cssPath = resolve(process.cwd(), "web", "rookieui_panes.css");
    const css = readFileSync(cssPath, "utf8");

    expect(css).toMatch(
      /\.rookieui-shell__controlnet-preview-toolbar\s*\{[\s\S]*max-width:\s*calc\(100%\s*-\s*16px\);[\s\S]*\}/,
    );
    expect(css).toMatch(
      /\.rookieui-shell__canvas-upload-toolbar\s*\{[\s\S]*max-width:\s*calc\(100%\s*-\s*16px\);[\s\S]*\}/,
    );
    expect(css).toMatch(
      /\.rookieui-shell__canvas-brush-controls\s*\{[\s\S]*grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\);[\s\S]*width:\s*min\(100%,\s*560px\);[\s\S]*max-width:\s*100%;[\s\S]*\}/,
    );
  });

  test("hides overlay toolbars by default on pointer-hover surfaces and reveals them on hover/focus", () => {
    const cssPath = resolve(process.cwd(), "web", "rookieui_panes.css");
    const css = readFileSync(cssPath, "utf8");

    expect(css).toMatch(/@media\s*\(hover:\s*hover\)\s*and\s*\(pointer:\s*fine\)\s*\{[\s\S]*\}/);
    expect(css).toMatch(
      /\.rookieui-shell__controlnet-preview-toolbar,\s*\.rookieui-shell__canvas-upload-toolbar\s*\{[\s\S]*opacity:\s*0;[\s\S]*visibility:\s*hidden;[\s\S]*pointer-events:\s*none;[\s\S]*\}/,
    );
    expect(css).toMatch(
      /\.rookieui-shell__controlnet-preview-stage:hover\s+\.rookieui-shell__controlnet-preview-toolbar[\s\S]*\.rookieui-shell__canvas-upload-surface:focus-within\s+\.rookieui-shell__canvas-upload-toolbar[\s\S]*\{[\s\S]*opacity:\s*1;[\s\S]*visibility:\s*visible;[\s\S]*pointer-events:\s*auto;[\s\S]*\}/,
    );
  });

  test("defines explicit circular brush indicator layer for edit-mode cursor parity", () => {
    const cssPath = resolve(process.cwd(), "web", "rookieui_panes.css");
    const css = readFileSync(cssPath, "utf8");

    expect(css).toMatch(
      /\.rookieui-shell__canvas-brush-indicator\s*\{[\s\S]*position:\s*absolute;[\s\S]*border-radius:\s*999px;[\s\S]*pointer-events:\s*none;[\s\S]*\}/,
    );
    expect(css).toMatch(
      /\.rookieui-shell__canvas-brush-indicator-cross--horizontal\s*\{[\s\S]*width:\s*10px;[\s\S]*height:\s*1px;[\s\S]*\}/,
    );
    expect(css).toMatch(
      /\.rookieui-shell__canvas-brush-indicator-cross--vertical\s*\{[\s\S]*width:\s*1px;[\s\S]*height:\s*10px;[\s\S]*\}/,
    );
  });
});
