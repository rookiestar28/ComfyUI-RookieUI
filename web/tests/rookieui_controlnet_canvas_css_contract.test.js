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
    expect(css).toMatch(
      /\.rookieui-shell__controlnet-preview-stage::before,\s*\.rookieui-shell__canvas-upload-surface::before\s*\{[\s\S]*opacity:\s*0;[\s\S]*transition:\s*opacity\s*120ms\s*ease;[\s\S]*\}/,
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

  test("defines fullscreen auto-fit stage rules and fullscreen zoom slider chrome", () => {
    const cssPath = resolve(process.cwd(), "web", "rookieui_panes.css");
    const css = readFileSync(cssPath, "utf8");

    expect(css).toMatch(
      /\.rookieui-shell__controlnet-preview-stage:fullscreen[\s\S]*width:\s*100vw;[\s\S]*height:\s*100vh;[\s\S]*min-height:\s*100vh;[\s\S]*\}/,
    );
    expect(css).toMatch(
      /\.rookieui-shell__canvas-upload-surface:fullscreen[\s\S]*width:\s*100vw;[\s\S]*height:\s*100vh;[\s\S]*\}/,
    );
    expect(css).toMatch(
      /\.rookieui-shell__controlnet-preview-image\s*\{[\s\S]*left:\s*0;[\s\S]*top:\s*0;[\s\S]*max-width:\s*none;[\s\S]*max-height:\s*none;[\s\S]*\}/,
    );
    expect(css).toMatch(
      /\.rookieui-shell__canvas-upload-preview\s*\{[\s\S]*left:\s*0;[\s\S]*top:\s*0;[\s\S]*max-width:\s*none;[\s\S]*max-height:\s*none;[\s\S]*\}/,
    );
    expect(css).toMatch(
      /\.rookieui-shell__canvas-fullscreen-zoom\s*\{[\s\S]*position:\s*absolute;[\s\S]*bottom:\s*14px;[\s\S]*min-width:\s*232px;[\s\S]*\}/,
    );
    expect(css).toMatch(
      /\.rookieui-shell__canvas-fullscreen-zoom\[hidden\]\s*\{[\s\S]*display:\s*none\s*!important;[\s\S]*\}/,
    );
    expect(css).toMatch(
      /\.rookieui-shell__hires-caret\s*\{[\s\S]*transform:\s*scaleX\(-1\);[\s\S]*\}/,
    );
    expect(css).toMatch(
      /\.rookieui-shell__controlnet-summary\s+\.rookieui-shell__hires-header\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)\s*auto;[\s\S]*\}/,
    );
    expect(css).toMatch(
      /\.rookieui-shell__controlnet-summary\s+\.rookieui-shell__hires-caret\s*\{[\s\S]*transform:\s*scaleX\(-1\);[\s\S]*\}/,
    );
  });
});
