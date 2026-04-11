const { test, expect } = require("@playwright/test");

test("preserves modular pane state and cross-pane routing seams", async ({ page }) => {
  await page.goto("test-harness.html");

  await page.locator("#rookieui-prompt").fill("modularization-persisted-prompt");

  await page.locator("#rookieui-tab-img2img").click();
  await page.locator("#rookieui-img2img-generation-mode-inpaint").click();
  await expect(page.locator("#rookieui-img2img-mode")).toHaveValue("inpaint");

  await page.locator("#rookieui-tab-extras").click();
  await page.locator("#rookieui-tab-img2img").click();
  await expect(page.locator("#rookieui-img2img-mode")).toHaveValue("inpaint");

  await page.locator("#rookieui-tab-txt2img").click();
  await expect(page.locator("#rookieui-prompt")).toHaveValue("modularization-persisted-prompt");

  await page.locator("#rookieui-tab-queue").click();
  await page.locator("#rookieui-reuse-img2img-0").click();
  await page.locator("#rookieui-tab-img2img").click();
  await expect(page.locator("#rookieui-image-asset")).toHaveValue("history-image.png");
});
