const { test, expect } = require("@playwright/test");


test("shows an uncertain submission outcome without a duplicate POST", async ({ page }) => {
  await page.goto("test-harness.html?runtimeApiFetch=1&txt2imgLostResponse=1");
  await page.locator("#rookieui-prompt").fill("synthetic test prompt");
  await page.locator("#rookieui-txt2img-submit").click();

  const status = page.locator("#rookieui-txt2img-status");
  await expect(status).toContainText("outcome unknown");
  await expect(status).toContainText("check queue");
  const submissions = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img.length);
  expect(submissions).toBe(1);
});

test("recovers an exact early terminal event when the scoped queue entry has expired", async ({ page }) => {
  await page.goto("test-harness.html?runtimeApiFetch=1&earlyTerminalScenario=1");
  await page.locator("#rookieui-prompt").fill("synthetic event ordering");
  await page.locator("#rookieui-txt2img-submit").click();

  await expect(page.locator("#rookieui-txt2img-status")).toContainText("Completed: e2e-prompt-123");
  const submissions = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img.length);
  expect(submissions).toBe(1);
});
