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
