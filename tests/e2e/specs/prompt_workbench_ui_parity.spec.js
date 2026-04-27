const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const ARTIFACT_ROOT = process.env.ROOKIEUI_VISUAL_ARTIFACT_DIR || "test-results/prompt-workbench-ui-parity";

test.setTimeout(60000);

function ensureArtifactDir() {
  const dir = path.resolve(process.cwd(), ARTIFACT_ROOT);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

test("captures Prompt Workbench prompt-all-in-one UI parity evidence", async ({ page }) => {
  const artifactDir = ensureArtifactDir();
  const referencePath = path.join(artifactDir, "reference-prompt-all-in-one-card.png");
  const referenceLanguageSelectorPath = path.join(artifactDir, "reference-prompt-all-in-one-language-selector.png");
  const currentCardPath = path.join(artifactDir, "current-rookieui-prompt-workbench-card.png");
  const currentPopoverPath = path.join(artifactDir, "current-rookieui-prompt-workbench-popover.png");
  const currentLanguageSelectorPath = path.join(artifactDir, "current-rookieui-prompt-workbench-language-selector.png");

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
          .reference-settings-cluster {
            position: relative;
            display: inline-flex;
          }
          .reference-settings-box {
            position: absolute;
            top: 26px;
            left: 0;
            display: inline-flex;
            min-width: 260px;
            gap: 6px;
            padding: 6px;
            border-radius: 8px;
            background: #e6f4ff;
            box-shadow: 0 8px 22px rgb(20 32 46 / 0.22);
          }
          .reference-keyword-input {
            min-width: 220px;
            min-height: 24px;
            border-radius: 5px;
            background: #fff;
          }
          .reference-language-selector {
            width: 360px;
            max-height: 360px;
            margin-top: 24px;
            overflow: hidden;
            border: 1px solid #7c8fad;
            border-radius: 8px;
            background: #1b1d21;
            box-shadow: 0 18px 42px rgb(14 20 30 / 0.38);
            color: #f5f7fb;
            padding: 6px;
          }
          .reference-language-option {
            display: flex;
            min-height: 34px;
            align-items: center;
            padding: 0 10px;
            border-radius: 5px;
            font-size: 13px;
            font-weight: 700;
          }
          .reference-language-option[data-selected="true"] {
            background: linear-gradient(90deg, #26c6da, #5965ff);
          }
        </style>
      </head>
      <body>
        <section data-reference="prompt-all-in-one-card">
          <div class="reference-header">
            <strong>Prompt Workbench</strong>
          <div class="reference-toolbar">
              <button class="reference-button" title="Fold tools">🔼</button>
              <span class="reference-chip">5 tags</span>
              <span class="reference-chip">en / prompt</span>
              <button class="reference-button" title="History">🕘</button>
              <button class="reference-button" title="Favorites">🔖</button>
              <span class="reference-settings-cluster">
                <button class="reference-button" aria-label="Prefs">⚙️</button>
                <span class="reference-settings-box">API A↔B ▦ ⌘ 🎨 ⓘ ✅ Ⓣ ⌨️</span>
              </span>
              <button class="reference-button" title="Translate">🌐</button>
              <button class="reference-button" title="Append">➕</button>
              <textarea class="reference-keyword-input" placeholder="Enter new keyword"></textarea>
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
        <section class="reference-language-selector" data-reference="prompt-all-in-one-language-selector">
          <div class="reference-language-option">zh_CN - 简体中文 (中国)</div>
          <div class="reference-language-option">zh_HK - 繁體中文 (中國香港)</div>
          <div class="reference-language-option">zh_TW - 繁體中文 (中國台灣)</div>
          <div class="reference-language-option" data-selected="true">en_US - English (US)</div>
          <div class="reference-language-option">af_ZA - Afrikaans (South Africa)</div>
          <div class="reference-language-option">sq_AL - Shqip (Shqipëria)</div>
          <div class="reference-language-option">ja_JP - Japanese (Japan)</div>
          <div class="reference-language-option">ko_KR - Korean (Korea)</div>
        </section>
      </body>
    </html>`);

  await page.locator("[data-reference='prompt-all-in-one-card']").screenshot({ path: referencePath });
  await page.locator("[data-reference='prompt-all-in-one-language-selector']").screenshot({ path: referenceLanguageSelectorPath });

  await page.goto("test-harness.html");
  await page.locator("#rookieui-prompt").fill("masterpiece, city skyline, cinematic lighting");
  await page.locator("#rookieui-txt2img-workbench-toggle").click();
  await expect(page.locator("#rookieui-txt2img-workbench-body")).toBeVisible();
  await page.locator("#rookieui-txt2img-workbench-capture").click();

  const workbench = page.locator("#rookieui-txt2img-workbench-section");
  await expect(workbench).toHaveAttribute("data-layout", "prompt_all_in_one_inline");
  await expect(workbench).toHaveAttribute("data-fixed-scope", "prompt");
  await expect(workbench.locator("[data-pw-ui='fold-toggle']")).toHaveAttribute("aria-expanded", "true");
  await expect(workbench.locator("[data-pw-ui='inline-counter']")).toHaveText("5 tags");
  await expect(workbench.locator("[data-pw-ui='inline-counter']")).toHaveAttribute("role", "status");
  await expect(workbench.locator("[data-pw-ui='inline-language']")).toContainText("prompt");
  const counterFontSize = await workbench.locator("[data-pw-ui='inline-counter']").evaluate((node) => getComputedStyle(node).fontSize);
  await expect(workbench.locator("[data-pw-ui='inline-language']")).toHaveCSS("font-size", counterFontSize);
  await expect(workbench.locator("[data-pw-ui='inline-language']")).toHaveAttribute(
    "aria-label",
    "Prompt workbench language and scope",
  );
  await expect(workbench.locator("[data-pw-ui='inline-history-anchor']")).toBeVisible();
  await expect(workbench.locator("[data-pw-ui='inline-history-anchor']")).toHaveAttribute("aria-haspopup", "dialog");
  await expect(workbench.locator("[data-pw-ui='inline-history-anchor']")).toHaveText("🕘");
  await expect(workbench.locator("[data-pw-ui='inline-history-anchor']")).toHaveAttribute("title", "History");
  await expect(workbench.locator("[data-pw-ui='inline-favorites-anchor']")).toBeVisible();
  await expect(workbench.locator("[data-pw-ui='inline-settings-anchor']")).toBeVisible();
  await expect(workbench.locator("[data-pw-ui='inline-settings-anchor']")).toHaveAttribute("aria-label", "Prefs");
  await expect(workbench.locator("[data-pw-ui='inline-settings-anchor']")).not.toHaveAttribute("title", /.+/);
  await expect(workbench.locator("[data-pw-ui='inline-settings-hoverbox']")).toBeHidden();
  await expect(workbench.locator("[data-pw-ui='inline-translate-action']")).toBeVisible();
  await expect(workbench.locator("[data-pw-ui='inline-translate-action']")).toHaveText("🌐");
  await expect(workbench.locator("[data-pw-ui='inline-translate-action']")).toHaveAttribute("title", "Translate");
  await expect(workbench.locator("[data-pw-ui='inline-copy-action']")).toBeVisible();
  await expect(workbench.locator("[data-pw-ui='inline-delete-action']")).toBeVisible();
  await expect(workbench.locator("[data-pw-ui='inline-append-anchor']")).toBeVisible();
  await expect(workbench.locator("[data-pw-ui='inline-keyword-input']")).toBeVisible();
  await expect(workbench.locator("[data-pw-ui='inline-keyword-input']")).toHaveAttribute("placeholder", "Enter new keyword");
  await expect(workbench.locator("[data-pw-ui='status-strip']")).toBeVisible();
  await expect(workbench.locator("[data-pw-ui='inline-add']")).toBeVisible();
  await expect(workbench.locator("[data-pw-ui='inline-suggestions']")).toBeVisible();
  await expect(workbench.locator("[data-pw-ui='token-chip-board']")).toBeVisible();
  await expect(workbench.locator("[data-pw-ui='token-chip']")).toHaveCount(3);
  await expect(workbench.locator("[data-pw-ui='token-chip-board']")).toHaveAttribute("data-token-layout", "inline-tags");
  await expect(workbench.locator("[data-pw-token-ui='inline-token-tag']")).toHaveCount(3);
  await expect(workbench.locator("[data-pw-ui='secondary-entrypoints']")).toBeVisible();
  const selectionToolbar = workbench.locator("[data-pw-ui='selection-batch-toolbar']");
  await expect(selectionToolbar).toBeHidden();

  const inlineToolbarShell = workbench.locator("[data-pw-ui='header-toolbar']");
  await expect(inlineToolbarShell).toHaveCSS("border-top-style", "none");
  await expect(inlineToolbarShell).toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
  await expect(workbench).toHaveCSS("overflow", "visible");

  const historyHoverTool = workbench.locator("[data-pw-ui='inline-history-anchor']");
  const toolbarStyleBeforeHover = await historyHoverTool.evaluate((node) => {
    const style = getComputedStyle(node);
    return {
      backgroundColor: style.backgroundColor,
      borderColor: style.borderColor,
      boxShadow: style.boxShadow,
      transform: style.transform,
    };
  });
  await historyHoverTool.hover();
  const toolbarStyleAfterHover = await historyHoverTool.evaluate((node) => {
    const style = getComputedStyle(node);
    return {
      backgroundColor: style.backgroundColor,
      borderColor: style.borderColor,
      boxShadow: style.boxShadow,
      transform: style.transform,
    };
  });
  expect(toolbarStyleAfterHover).not.toEqual(toolbarStyleBeforeHover);
  await page.mouse.move(0, 0);

  await workbench.locator("[data-pw-ui='inline-settings-anchor']").hover();
  const settingsHoverBox = workbench.locator("[data-pw-ui='inline-settings-hoverbox']");
  await expect(settingsHoverBox).toBeVisible();
  await expect(settingsHoverBox).toBeInViewport();
  await expect(settingsHoverBox.locator("[data-pw-ui='inline-settings-api']")).toBeVisible();
  await expect(settingsHoverBox.locator("[data-pw-ui='inline-settings-format']")).toHaveAttribute("title", "Prompt format settings");
  await expect(settingsHoverBox.locator("#rookieui-txt2img-workbench-inline-settings-auto-translate")).toBeVisible();
  await expect(settingsHoverBox.locator("#rookieui-txt2img-workbench-inline-settings-auto-input")).toBeVisible();
  await page.mouse.move(0, 0);

  const firstToken = workbench.locator("[data-pw-token-ui='inline-token-tag']").first();
  const firstTokenActions = firstToken.locator("[data-pw-ui='token-quick-actions']");
  await expect(firstToken.locator("[data-pw-ui='token-local-language']")).toBeVisible();
  await expect(firstTokenActions).toBeHidden();
  await firstToken.hover();
  await expect(firstTokenActions).toBeVisible();
  await expect(firstTokenActions.getByRole("button", { name: "Disable" })).toBeVisible();
  await expect(firstTokenActions.getByRole("button", { name: "Weight +" })).toBeVisible();
  await expect(firstTokenActions.getByRole("button", { name: "Copy" })).toBeVisible();
  await expect(firstTokenActions.getByRole("button", { name: "Favorite" })).toBeVisible();
  await expect(firstTokenActions.getByRole("button", { name: "Blacklist" })).toBeVisible();
  await page.mouse.move(0, 0);
  await expect(firstTokenActions).toBeHidden();
  await firstToken.locator(".rookieui-shell__prompt-workbench-token-input").focus();
  await expect(firstTokenActions).toBeVisible();
  await firstToken.locator(".rookieui-shell__prompt-workbench-token-select").check();
  await expect(selectionToolbar).toBeVisible();
  await expect(selectionToolbar).toHaveAttribute("data-batch-layout", "inline-overlay");
  await expect(selectionToolbar.locator("#rookieui-txt2img-workbench-token-selected-count")).toHaveText("1 selected");

  await workbench.screenshot({ path: currentCardPath });

  const languageButton = workbench.locator("[data-pw-ui='inline-language']");
  await languageButton.click();
  const languageSelector = page.locator("#rookieui-txt2img-workbench-language-selector");
  await expect(languageSelector).toBeVisible();
  await expect(languageSelector).toHaveAttribute("data-placement", "fixed");
  await expect(languageSelector).toBeInViewport();
  await expect(languageSelector.locator("[data-language-code='zh-TW']")).toBeVisible();
  await languageSelector.screenshot({ path: currentLanguageSelectorPath });
  await languageSelector.locator("[data-language-code='zh-TW']").click();
  await expect(languageButton).toHaveText("zh-TW / 正向");
  await expect(page.locator("#rookieui-txt2img-workbench-assist-language")).toHaveValue("zh-TW");
  await expect(workbench.locator(".rookieui-shell__prompt-workbench-title")).toHaveText("提示詞工作台");
  await expect(workbench.locator("[data-pw-ui='inline-keyword-input']")).toHaveAttribute("placeholder", "請輸入新關鍵詞");
  await expect(languageSelector).toBeHidden();
  await languageButton.click();
  await expect(languageSelector).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(languageSelector).toBeHidden();
  await expect(languageButton).toBeFocused();

  await workbench.locator("[data-pw-ui='inline-keyword-input']").fill("soft rim light");
  await workbench.locator("[data-pw-ui='inline-keyword-input']").press("Enter");
  await expect(page.locator("#rookieui-prompt")).toHaveValue(/soft rim light/);

  await page.locator("#rookieui-txt2img-workbench-toggle").click();
  await expect(workbench).toHaveAttribute("data-folded", "true");
  await expect(workbench.locator("[data-pw-ui='fold-toggle']")).toHaveAttribute("aria-expanded", "false");
  await page.locator("#rookieui-txt2img-workbench-toggle").click();
  await expect(workbench).toHaveAttribute("data-folded", "false");

  await page.locator("#rookieui-txt2img-workbench-inline-history").click();
  await expect(page.locator("#rookieui-txt2img-workbench-secondary-popover")).toHaveAttribute("data-active-surface", "history");
  await expect(page.locator("#rookieui-txt2img-workbench-panel-history")).toHaveAttribute("data-active", "true");
  await workbench.screenshot({ path: currentPopoverPath });

  await page.locator("#rookieui-txt2img-workbench-panel-editor").click();
  await page.locator("[data-pw-token-ui='inline-token-tag']").first().hover();
  await page.locator("#rookieui-txt2img-workbench-token-delete-0").click();
  await expect(page.locator("#rookieui-prompt")).not.toHaveValue(/masterpiece/);

  await page.locator("#rookieui-txt2img-workbench-inline-append").click();
  await expect(page.locator("#rookieui-txt2img-workbench-secondary-popover")).toHaveAttribute("data-active-surface", "append");
  await expect(page.locator("#rookieui-txt2img-workbench-secondary-popover")).toHaveAttribute(
    "data-pw-ui",
    "append-dropdown-popover",
  );
  await expect(page.locator("#rookieui-txt2img-workbench-secondary-popover [data-pw-ui='inline-suggestions']")).toBeVisible();
  const groupTagsBoard = page.locator("#rookieui-txt2img-workbench-secondary-popover [data-pw-ui='group-tags-tab-board']");
  await expect(groupTagsBoard).toBeVisible();
  await expect(groupTagsBoard.locator("[data-pw-ui='group-tags-group-tab']").first()).toBeVisible();
  await expect(groupTagsBoard.locator("[data-pw-ui='group-tags-subgroup-tab']").first()).toBeVisible();
  const firstGroupTag = groupTagsBoard.locator("[data-pw-ui='group-tags-entry']").first();
  await expect(firstGroupTag).toBeVisible();
  const promptBeforeGroupTag = await page.locator("#rookieui-prompt").inputValue();
  await firstGroupTag.click();
  await expect(page.locator("#rookieui-prompt")).not.toHaveValue(promptBeforeGroupTag);
  await expect(groupTagsBoard.locator("[data-pw-ui='group-tags-entry'][data-selected='true']").first()).toBeVisible();
  await workbench.locator("[data-pw-ui='inline-append-anchor']").focus();
  await page.keyboard.press("Escape");
  await expect(page.locator("#rookieui-txt2img-workbench-secondary-popover")).toBeHidden();

  await page.locator("#rookieui-txt2img-workbench-inline-delete").click();
  await expect(page.locator("#rookieui-prompt")).toHaveValue("");
  await expect(workbench.locator("[data-pw-ui='inline-counter']")).toHaveText("0 標籤");

  [referencePath, referenceLanguageSelectorPath, currentCardPath, currentPopoverPath, currentLanguageSelectorPath].forEach((artifactPath) => {
    expect(fs.statSync(artifactPath).size).toBeGreaterThan(1000);
  });
});
