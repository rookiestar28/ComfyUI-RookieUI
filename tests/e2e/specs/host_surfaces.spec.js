const { test, expect } = require("@playwright/test");

test("loads the desktop host surface harness", async ({ page }) => {
  await page.goto("test-harness.html?surface=desktop");
  await expect(page.locator("#rookieui-root")).toContainText('"hostSurface":"desktop"');
  await expect(page.locator("#rookieui-root")).toContainText('"hostSurfaceSupported":true');
  await expect(page.locator("#rookieui-shell-title")).toHaveText("RookieUI");
  await expect(page.locator("#rookieui-header-version")).toHaveText("v0.1.0");
  await expect(page.locator("#rookieui-view-github")).toHaveText("View on GitHub");
});

test("falls back to the legacy launcher when sidebar tabs are unavailable", async ({ page }) => {
  await page.goto("test-harness.html?sidebar=0");
  await expect(page.locator("#rookieui-legacy-launcher")).toHaveText("RookieUI");
  await page.locator("#rookieui-legacy-launcher").click();
  await expect(page.locator("#rookieui-legacy-panel")).not.toBeHidden();
  await expect(page.locator("#rookieui-legacy-panel")).toContainText("RookieUI");
  await expect(page.locator("#rookieui-legacy-panel")).toContainText("View on GitHub");
  await expect(page.locator("#rookieui-legacy-panel")).not.toContainText("Standalone web");
});

test("submits txt2img through the ComfyUI runtime API resolver when root API paths are unavailable", async ({ page }) => {
  await page.goto("test-harness.html?runtimeApiFetch=1&rejectRootApiFetch=1");
  await expect(page.locator("#rookieui-root")).toContainText('"clientId":"e2e-runtime-api-client"');
  await page.locator("#rookieui-prompt").fill("proxy-safe cat");
  await page.locator("#rookieui-txt2img-submit").click();
  await expect(page.locator("#rookieui-txt2img-status")).toContainText(/(Queued prompt|Completed:) e2e-prompt-123/);
  const submittedPrompts = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__?.txt2img?.map((entry) => entry.prompt));
  expect(submittedPrompts).toContain("proxy-safe cat");
});
