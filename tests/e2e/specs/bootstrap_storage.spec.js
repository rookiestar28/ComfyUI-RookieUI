const { test, expect } = require("@playwright/test");
const path = require("node:path");

for (const placement of ["left", "right"]) {
  for (const activeHost of [false, true]) {
    test(`submits and remounts with denied storage in ${placement} placement (${activeHost ? "host" : "fallback"} identity)`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width: 1440, height: 1000 });
      const errors = [];
      page.on("pageerror", (error) => errors.push(error.message));
      await page.addInitScript(() => {
        Object.defineProperty(window, "sessionStorage", {
          configurable: true,
          get() { throw new DOMException("synthetic storage denial", "SecurityError"); },
        });
      });
      await page.goto(`test-harness.html?lifecycleSentinel=1${activeHost ? "&runtimeApiFetch=1" : ""}`);
      await expect(page.locator("#rookieui-shell-title")).toHaveText("RookieUI");
      const mount = page.locator("#mock-sidebar-tabs");
      // Model left/right host placement without importing a private host store.
      await page.locator(".sidebar-content-container").evaluate((node, side) => {
        node.style.marginLeft = side === "right" ? "auto" : "0px";
        node.style.marginRight = side === "left" ? "auto" : "0px";
      }, placement);
      const mountedBox = await mount.boundingBox();
      expect(mountedBox.width).toBe(980);
      if (placement === "right") expect(mountedBox.x).toBeGreaterThan(100);
      else expect(mountedBox.x).toBeLessThan(20);

      const prompt = page.locator("#rookieui-prompt");
      const idleListeners = await page.evaluate(() => window.__ROOKIEUI_E2E_RUNTIME__?.listenerCount());
      await prompt.fill("synthetic storage regression");
      await prompt.focus();
      await expect(prompt).toBeFocused();
      await page.locator("#rookieui-batch-count").fill("3");
      await expect(page.locator("#rookieui-batch-count-slider")).toHaveValue("3");
      await page.locator("#rookieui-batch-count").fill("1");
      await page.locator("#rookieui-txt2img-submit").click();
      await expect.poll(() => page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img.length)).toBe(1);
      const identity = await page.evaluate(() => ({
        selected: window.__ROOKIEUI_BOOTSTRAP__.clientId,
        submitted: window.__ROOKIEUI_E2E_REQUESTS__.txt2img[0].client_id,
      }));
      expect(identity.submitted).toBe(identity.selected);
      expect(identity.selected).toMatch(activeHost ? /^e2e-runtime-api-client$/ : /^rookieui-/);
      await page.locator(".rookieui-shell__content").evaluate((node) => {
        node.style.maxHeight = "400px";
        node.scrollTop = node.scrollHeight;
      });
      expect(await page.locator(".rookieui-shell__content").evaluate((node) => node.scrollTop)).toBeGreaterThan(0);
      await page.setViewportSize({ width: 1280, height: 720 });
      await expect(mount).toHaveCSS("min-width", "980px");
      await page.setViewportSize({ width: 1440, height: 1000 });
      const destroyed = await page.evaluate(() => {
        window.__ROOKIEUI_E2E_APP__.extensionManager.activeSidebarTab.destroy();
        return window.__ROOKIEUI_E2E_RUNTIME__?.listenerCount();
      });
      await expect(mount).toBeEmpty();
      await expect(mount).toHaveCSS("min-width", "19px");
      if (activeHost) expect(destroyed).toBe(0);
      await page.evaluate(() => window.__ROOKIEUI_E2E_APP__.extensionManager.activeSidebarTab.render(
        document.getElementById("mock-sidebar-tabs"),
      ));
      await expect(page.locator("#rookieui-shell-title")).toHaveText("RookieUI");
      if (activeHost) {
        expect(await page.evaluate(() => window.__ROOKIEUI_E2E_RUNTIME__.listenerCount())).toBe(idleListeners);
      }
      const visualDir = process.env.ROOKIEUI_VISUAL_EVIDENCE_DIR;
      const name = `storage-${placement}-${activeHost ? "host" : "fallback"}-1440x1000`;
      const visual = await mount.screenshot(visualDir ? { path: path.join(visualDir, `${name}.png`) } : {});
      await testInfo.attach(name, { body: visual, contentType: "image/png" });
      await page.locator("#rookieui-txt2img-submit").click();
      await expect.poll(() => page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img.length)).toBe(2);
      expect(await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img[1].client_id)).toBe(identity.selected);
      await page.evaluate(() => window.__ROOKIEUI_E2E_APP__.extensionManager.activeSidebarTab.destroy());
      if (activeHost) expect(await page.evaluate(() => window.__ROOKIEUI_E2E_RUNTIME__.listenerCount())).toBe(0);
      expect(errors).toEqual([]);
    });
  }
}
