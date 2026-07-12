const { test, expect } = require("@playwright/test");

test("restores host layout and durable pane state across sidebar destroy/remount", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("test-harness.html?lifecycleSentinel=1");
  const mount = page.locator("#mock-sidebar-tabs");
  const panel = page.locator(".side-bar-panel");
  const content = page.locator(".sidebar-content-container");
  await expect(page.locator("#rookieui-shell-title")).toHaveText("RookieUI");
  await page.locator("#rookieui-tab-img2img").click();
  await expect(page.locator("#rookieui-pane-img2img")).toBeVisible();
  const mountedVisual = await mount.screenshot();
  const mountedBox = await mount.boundingBox();
  await testInfo.attach("sidebar-before-remount", { body: mountedVisual, contentType: "image/png" });

  await page.evaluate(() => window.__ROOKIEUI_E2E_APP__.extensionManager.activeSidebarTab.destroy());
  await expect(mount).toBeEmpty();
  await expect(mount).toHaveCSS("min-width", "19px");
  await expect(mount).toHaveCSS("width", "29px");
  await expect(mount).toHaveCSS("flex-basis", "31px");
  await expect(panel).toHaveCSS("min-width", "233px");
  await expect(panel).toHaveCSS("width", "355px");
  await expect(panel).toHaveCSS("flex-basis", "17px");
  await expect(content).toHaveCSS("min-width", "211px");
  await expect(content).toHaveCSS("width", "377px");
  await expect(content).toHaveCSS("flex-basis", "13px");

  await page.evaluate(() => {
    const app = window.__ROOKIEUI_E2E_APP__;
    app.extensionManager.activeSidebarTab.render(document.getElementById("mock-sidebar-tabs"));
  });
  await expect(page.locator("#rookieui-pane-img2img")).toBeVisible();
  await expect(mount).toHaveCSS("min-width", "980px");
  const remountedVisual = await mount.screenshot();
  const remountedBox = await mount.boundingBox();
  await testInfo.attach("sidebar-after-remount", { body: remountedVisual, contentType: "image/png" });
  expect(remountedBox?.width).toBeCloseTo(mountedBox?.width ?? 0, 0);
  expect(remountedBox?.height).toBeCloseTo(mountedBox?.height ?? 0, 0);
});
