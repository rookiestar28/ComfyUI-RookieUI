const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const ARTIFACT_ROOT = process.env.ROOKIEUI_VISUAL_ARTIFACT_DIR || "test-results/prompt-workbench-ui-parity";

function ensureArtifactDir() {
  const dir = path.resolve(process.cwd(), ARTIFACT_ROOT);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

test("captures Prompt Workbench prompt-all-in-one UI parity evidence", async ({ page }) => {
  const artifactDir = ensureArtifactDir();
  const referencePath = path.join(artifactDir, "reference-prompt-all-in-one-card.png");
  const currentCardPath = path.join(artifactDir, "current-rookieui-prompt-workbench-card.png");
  const currentPopoverPath = path.join(artifactDir, "current-rookieui-prompt-workbench-popover.png");

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.setContent(`<!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <style>
          body {
            margin: 0;
            padding: 28px;
            background: #eef1f5;
            font-family: ui-sans-serif, system-ui, sans-serif;
          }
          [data-reference="prompt-all-in-one-card"] {
            width: 760px;
            border: 1px solid #ccd3df;
            border-radius: 18px;
            background: #f9fbff;
            box-shadow: 0 16px 36px rgb(20 28 40 / 0.14);
            padding: 16px;
          }
          .reference-header,
          .reference-toolbar,
          .reference-chips,
          .reference-secondary,
          .reference-group-tags {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
          }
          .reference-header {
            justify-content: space-between;
            margin-bottom: 12px;
          }
          .reference-chip,
          .reference-button {
            border: 1px solid #b9c4d4;
            border-radius: 999px;
            background: #fff;
            padding: 8px 12px;
            color: #263241;
          }
          .reference-chips,
          .reference-group-tags {
            margin-top: 12px;
            padding: 12px;
            border: 1px dashed #c9d3e2;
            border-radius: 14px;
            background: #f1f5fb;
          }
        </style>
      </head>
      <body>
        <section data-reference="prompt-all-in-one-card">
          <div class="reference-header">
            <strong>Prompt Workbench</strong>
            <div class="reference-toolbar">
              <button class="reference-button">Fold</button>
              <button class="reference-button">History</button>
              <button class="reference-button">Favorites</button>
              <button class="reference-button">Prefs</button>
            </div>
          </div>
          <div class="reference-secondary">
            <button class="reference-button">Inline Add</button>
            <button class="reference-button">Tag Suggestions</button>
            <button class="reference-button">Group Tags</button>
          </div>
          <div class="reference-chips">
            <span class="reference-chip">masterpiece</span>
            <span class="reference-chip">city skyline</span>
            <span class="reference-chip">cinematic lighting</span>
            <button class="reference-button">Weight +</button>
            <button class="reference-button">Translate</button>
          </div>
          <div class="reference-group-tags">
            <span class="reference-chip">quality</span>
            <span class="reference-chip">composition</span>
            <span class="reference-chip">lighting</span>
          </div>
        </section>
      </body>
    </html>`);

  await page.locator("[data-reference='prompt-all-in-one-card']").screenshot({ path: referencePath });

  await page.goto("test-harness.html");
  await page.locator("#rookieui-prompt").fill("masterpiece, city skyline, cinematic lighting");
  await page.locator("#rookieui-txt2img-workbench-toggle").click();
  await expect(page.locator("#rookieui-txt2img-workbench-body")).toBeVisible();
  await page.locator("#rookieui-txt2img-workbench-capture").click();

  const workbench = page.locator("#rookieui-txt2img-workbench-section");
  await expect(workbench).toHaveAttribute("data-layout", "prompt_all_in_one_inline");
  await expect(workbench).toHaveAttribute("data-fixed-scope", "prompt");
  await expect(workbench.locator("[data-pw-ui='status-strip']")).toBeVisible();
  await expect(workbench.locator("[data-pw-ui='inline-add']")).toBeVisible();
  await expect(workbench.locator("[data-pw-ui='inline-suggestions']")).toBeVisible();
  await expect(workbench.locator("[data-pw-ui='token-chip-board']")).toBeVisible();
  await expect(workbench.locator("[data-pw-ui='token-chip']")).toHaveCount(3);
  await expect(workbench.locator("[data-pw-ui='secondary-entrypoints']")).toBeVisible();

  await workbench.screenshot({ path: currentCardPath });

  await page.locator("#rookieui-txt2img-workbench-quick-history").click();
  await expect(page.locator("#rookieui-txt2img-workbench-secondary-popover")).toHaveAttribute("data-active-surface", "history");
  await expect(page.locator("#rookieui-txt2img-workbench-panel-history")).toHaveAttribute("data-active", "true");
  await workbench.screenshot({ path: currentPopoverPath });

  [referencePath, currentCardPath, currentPopoverPath].forEach((artifactPath) => {
    expect(fs.statSync(artifactPath).size).toBeGreaterThan(1000);
  });
});
