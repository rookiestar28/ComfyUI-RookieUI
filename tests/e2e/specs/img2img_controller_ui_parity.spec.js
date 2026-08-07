const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const ARTIFACT_ROOT = process.env.ROOKIEUI_IMG2IMG_VISUAL_ARTIFACT_DIR || "test-results/f310-img2img-ui-parity";

test.setTimeout(60000);

function artifactPath(fileName) {
  const directory = path.resolve(process.cwd(), ARTIFACT_ROOT);
  fs.mkdirSync(directory, { recursive: true });
  return path.join(directory, fileName);
}

test("preserves Img2Img mode/reference/mask/action parity and captures comparable evidence", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("test-harness.html");
  await expect(page.locator("#rookieui-root")).toContainText('"hostSurface":"standalone-web"', { timeout: 15000 });
  await page.locator("#rookieui-tab-img2img").click();

  const pane = page.locator("#rookieui-pane-img2img");
  await expect(pane).toBeVisible();
  const referencePath = artifactPath("reference-img2img-pane.png");
  if (!fs.existsSync(referencePath)) {
    await pane.screenshot({ path: referencePath });
  }
  await pane.screenshot({ path: artifactPath("current-img2img-pane.png") });

  const modeValues = await page.locator("#rookieui-img2img-mode option").evaluateAll((options) =>
    options.map((option) => option.value),
  );
  expect(modeValues).toEqual(["img2img", "sketch", "inpaint", "inpaint_sketch", "inpaint_upload", "batch"]);

  await page.locator("#rookieui-img2img-generation-mode-batch").click();
  await expect(page.locator("#rookieui-img2img-mode")).toHaveValue("batch");
  await expect(page.locator("#rookieui-img2img-batch-pane")).toBeVisible();

  await page.locator("#rookieui-img2img-preset").selectOption("flux_kontext_dev_edit");
  await expect(page.locator("#rookieui-img2img-mode")).toHaveValue("img2img");
  await expect(page.locator("#rookieui-img2img-reference-section")).toBeVisible();
  await expect(page.locator("#rookieui-img2img-reference-card-2")).toBeVisible();
  await expect(page.locator("#rookieui-img2img-reference-card-3")).toBeVisible();

  await page.locator("#rookieui-image-asset").fill("f310-source-1");
  await page.locator("#rookieui-img2img-reference-asset-2").fill("f310-source-2");
  await page.locator("#rookieui-img2img-reference-asset-3").fill("f310-source-3");
  await page.locator("#rookieui-img2img-reference-main-2").check();
  await page.evaluate(() => {
    document.getElementById("rookieui-img2img-form").dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
  });
  await expect.poll(async () => page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.img2img.length)).toBe(1);
  const referenceRequest = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.img2img[0]);
  expect(referenceRequest).toMatchObject({
    mode: "img2img",
    profile: "flux_kontext_dev_edit",
    reference_images: [
      { image_asset: "f310-source-1" },
      { image_asset: "f310-source-2" },
      { image_asset: "f310-source-3" },
    ],
    main_reference_index: 2,
  });

  await page.evaluate(() => {
    window.__ROOKIEUI_E2E_REQUESTS__.img2img.length = 0;
  });
  await page.locator("#rookieui-img2img-generation-mode-img2img").click();
  await page.locator("#rookieui-img2img-preset").selectOption("sd15");
  await page.locator("#rookieui-img2img-generation-mode-inpaint").click();
  await page.locator("#rookieui-image-asset").fill("f310-inpaint-source");
  await page.locator("#rookieui-mask-asset").fill("f310-inpaint-mask");
  await page.locator("#rookieui-denoise-strength").fill("0.65");
  await expect(page.locator("#rookieui-img2img-mask-editor")).toBeVisible();
  await page.locator("#rookieui-img2img-form").evaluate((form) => {
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });
  await expect(page.locator("#rookieui-img2img-status")).toContainText("e2e-img2img-456");
  const inpaintRequest = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.img2img[0]);
  expect(inpaintRequest).toMatchObject({
    mode: "inpaint",
    image_asset: "f310-inpaint-source",
    mask_asset: "f310-inpaint-mask",
    denoise_strength: 0.65,
  });
  await pane.screenshot({ path: artifactPath("current-img2img-inpaint-pane.png") });

  await page.locator("#rookieui-img2img-prompt").fill("f310 transfer prompt");
  await page.locator("#rookieui-img2img-action-target").selectOption("txt2img");
  await page.locator("#rookieui-img2img-apply-action-target").click();
  await expect(page.locator("#rookieui-prompt")).toHaveValue("f310 transfer prompt");
});
