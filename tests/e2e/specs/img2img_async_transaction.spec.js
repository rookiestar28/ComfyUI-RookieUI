const { test, expect } = require("@playwright/test");

test.setTimeout(60000);

async function openImg2Img(page, query = "") {
  await page.goto(`test-harness.html${query}`);
  await expect(page.locator("#rookieui-root")).toContainText('"hostSurface":"standalone-web"', {
    timeout: 15000,
  });
  await page.locator("#rookieui-tab-img2img").click();
  await expect(page.locator("#rookieui-pane-img2img")).toBeVisible();
}

async function installControlledFileReader(page) {
  await page.addInitScript(() => {
    const BrowserFileReader = window.FileReader;
    window.FileReader = class ControlledFileReader extends BrowserFileReader {
      readAsDataURL(blob) {
        const name = String(blob?.name ?? "");
        if (name.startsWith("broken-")) {
          window.setTimeout(() => this.onerror?.(new ProgressEvent("error")), 10);
          return;
        }
        const delay = name.startsWith("slow-") ? 250 : 0;
        window.setTimeout(() => super.readAsDataURL(blob), delay);
      }
    };
  });
}

test("keeps every selected batch file in order through submission", async ({ page }) => {
  const expectedBatchImages = [
    "data:image/png;base64,YWxwaGE=",
    "data:image/png;base64,YnJhdm8=",
    "data:image/png;base64,Y2hhcmxpZQ==",
  ];
  await openImg2Img(page);
  await page.locator("#rookieui-img2img-generation-mode-batch").click();

  await page.locator("#rookieui-img2img-batch-file").setInputFiles([
    { name: "alpha.png", mimeType: "image/png", buffer: Buffer.from("alpha") },
    { name: "bravo.png", mimeType: "image/png", buffer: Buffer.from("bravo") },
    { name: "charlie.png", mimeType: "image/png", buffer: Buffer.from("charlie") },
  ]);

  await expect(page.locator("#rookieui-img2img-batch-status")).toHaveText("Loaded 3 batch image(s).");
  await expect(page.locator("#rookieui-img2img-batch-list li")).toHaveText([
    "alpha.png",
    "bravo.png",
    "charlie.png",
  ]);

  await page.locator("#rookieui-img2img-form").evaluate((form) => {
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });
  await expect.poll(async () => page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.img2img.length)).toBe(1);
  const request = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.img2img[0]);
  expect(request.batch_images).toEqual(expectedBatchImages);
  expect(request.image_data).toBe(expectedBatchImages[0]);
});

test("does not commit a delayed submit response after the pane is destroyed", async ({ page }) => {
  await openImg2Img(page, "?img2imgDelayMs=300");
  await page.locator("#rookieui-image-asset").fill("public-test-source.png");

  await page.locator("#rookieui-img2img-form").evaluate((form) => {
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });
  await expect(page.locator("#rookieui-img2img-status")).toHaveText("Submitting img2img request...");

  await page.evaluate(() => {
    window.__ROOKIEUI_DETACHED_STATUS_NODE__ = document.getElementById("rookieui-img2img-status");
    window.__ROOKIEUI_E2E_APP__.extensionManager.activeSidebarTab.destroy();
  });
  await page.waitForTimeout(600);

  const detachedStatus = await page.evaluate(() => window.__ROOKIEUI_DETACHED_STATUS_NODE__?.textContent ?? "");
  expect(detachedStatus).toBe("Submitting img2img request...");
});

test("keeps a newer batch selection when an older read completes late", async ({ page }) => {
  await installControlledFileReader(page);
  await openImg2Img(page);
  await page.locator("#rookieui-img2img-generation-mode-batch").click();
  const input = page.locator("#rookieui-img2img-batch-file");

  await input.setInputFiles([
    { name: "slow-old-a.png", mimeType: "image/png", buffer: Buffer.from("old-a") },
    { name: "slow-old-b.png", mimeType: "image/png", buffer: Buffer.from("old-b") },
  ]);
  await input.setInputFiles([
    { name: "fresh.png", mimeType: "image/png", buffer: Buffer.from("fresh") },
  ]);

  await expect(page.locator("#rookieui-img2img-batch-status")).toHaveText("Loaded 1 batch image(s).");
  await expect(page.locator("#rookieui-img2img-batch-list li")).toHaveText(["fresh.png"]);
  await page.waitForTimeout(400);
  await expect(page.locator("#rookieui-img2img-batch-list li")).toHaveText(["fresh.png"]);
});

test("clear and destroy invalidate pending batch reads atomically", async ({ page }) => {
  await installControlledFileReader(page);
  await openImg2Img(page);
  await page.locator("#rookieui-img2img-generation-mode-batch").click();
  const input = page.locator("#rookieui-img2img-batch-file");

  await input.setInputFiles([
    { name: "slow-clear.png", mimeType: "image/png", buffer: Buffer.from("clear") },
  ]);
  await input.setInputFiles([]);
  await expect(page.locator("#rookieui-img2img-batch-status")).toHaveText("No batch images selected.");
  await page.waitForTimeout(400);
  await expect(page.locator("#rookieui-img2img-batch-list li")).toHaveCount(0);

  await input.setInputFiles([
    { name: "slow-destroy.png", mimeType: "image/png", buffer: Buffer.from("destroy") },
  ]);
  await page.evaluate(() => {
    window.__ROOKIEUI_DETACHED_BATCH_STATUS__ = document.getElementById("rookieui-img2img-batch-status");
    window.__ROOKIEUI_DETACHED_BATCH_LIST__ = document.getElementById("rookieui-img2img-batch-list");
    window.__ROOKIEUI_E2E_APP__.extensionManager.activeSidebarTab.destroy();
    window.__ROOKIEUI_E2E_APP__.extensionManager.activeSidebarTab.destroy();
  });
  await page.waitForTimeout(400);
  const detachedState = await page.evaluate(() => ({
    status: window.__ROOKIEUI_DETACHED_BATCH_STATUS__?.textContent ?? "",
    items: window.__ROOKIEUI_DETACHED_BATCH_LIST__?.children.length ?? -1,
  }));
  expect(detachedState).toEqual({ status: "No batch images selected.", items: 0 });
});

test("rejects a partially unreadable batch without committing partial results", async ({ page }) => {
  await installControlledFileReader(page);
  await openImg2Img(page);
  await page.locator("#rookieui-img2img-generation-mode-batch").click();

  await page.locator("#rookieui-img2img-batch-file").setInputFiles([
    { name: "valid.png", mimeType: "image/png", buffer: Buffer.from("valid") },
    { name: "broken-image.png", mimeType: "image/png", buffer: Buffer.from("broken") },
  ]);

  await expect(page.locator("#rookieui-img2img-status")).toHaveText("Failed to load batch image upload.");
  await expect(page.locator("#rookieui-img2img-batch-status")).toHaveText("No batch images selected.");
  await expect(page.locator("#rookieui-img2img-batch-list li")).toHaveCount(0);
});
