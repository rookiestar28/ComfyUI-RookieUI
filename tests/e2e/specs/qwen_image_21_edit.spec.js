const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");
const TINY_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7ZrY4AAAAASUVORK5CYII=",
  "base64",
);

test("source-canvas fit keeps the Qwen 2.1 edit form natively valid", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("test-harness.html");
  await expect(page.locator("#rookieui-root")).toContainText('"hostSurface":"standalone-web"');
  await page.locator("#rookieui-tab-img2img").click();
  await page.locator("#rookieui-img2img-preset").selectOption("qwen_image_21_edit");
  await page.locator("#rookieui-img2img-mask-editor .rookieui-shell__mask-editor-viewport").evaluate((viewport) => {
    viewport.style.width = "400px";
    viewport.style.height = "320px";
    viewport.style.minHeight = "320px";
  });
  const sourceDataUrl = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 512;
    const context = canvas.getContext("2d");
    context.fillStyle = "#456789";
    context.fillRect(0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/png");
  });
  const syntheticPng = Buffer.from(sourceDataUrl.slice(sourceDataUrl.indexOf(",") + 1), "base64");
  await page.locator("#rookieui-img2img-image-file").setInputFiles({
    name: "synthetic-fit-source.png",
    mimeType: "image/png",
    buffer: syntheticPng,
  });
  await page.locator("#rookieui-img2img-reference-file-2").setInputFiles({
    name: "synthetic-fit-reference.png",
    mimeType: "image/png",
    buffer: syntheticPng,
  });
  await expect(page.locator("#rookieui-img2img-reference-status-2")).toContainText("Uploaded reference image ready");
  await page.locator("#rookieui-img2img-reference-main-1").click();
  await expect(page.locator("#rookieui-img2img-reference-main-0")).toBeChecked();
  await page.waitForFunction(() => {
    const preview = document.querySelector("#rookieui-img2img-mask-editor .rookieui-shell__mask-editor-source");
    return preview instanceof HTMLImageElement && preview.complete && preview.naturalWidth === 512;
  });
  const zoomRow = page.locator("#rookieui-img2img-mask-editor .rookieui-shell__mask-editor-control").nth(2);
  const zoomNumber = zoomRow.locator('input[type="number"]');
  const zoomSlider = zoomRow.locator('input[type="range"]');
  const zoom = await zoomNumber.evaluate((input) => ({
    value: input.value,
    stepMismatch: input.validity.stepMismatch,
    valid: input.checkValidity(),
  }));
  expect(zoom.value).toBe("0.63");
  expect(zoom.stepMismatch).toBe(false);
  expect(zoom.valid).toBe(true);
  await expect(zoomSlider).toHaveValue(zoom.value);
  await expect.poll(() => page.locator("#rookieui-img2img-form").evaluate((form) => form.checkValidity())).toBe(true);
});

test("Qwen Image 2.1 edit keeps ten ordered references and scoped controls", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("test-harness.html");
  await expect(page.locator("#rookieui-root")).toContainText('"hostSurface":"standalone-web"');
  await page.locator("#rookieui-tab-img2img").click();
  const pane = page.locator("#rookieui-pane-img2img");
  const artifactRoot = path.resolve(process.cwd(),
    process.env.ROOKIEUI_QWEN21_EDIT_VISUAL_ARTIFACT_DIR || "test-results/qwen21-edit");
  fs.mkdirSync(artifactRoot, { recursive: true });
  await pane.screenshot({ path: path.join(artifactRoot, "before-profile.png") });

  await page.locator("#rookieui-img2img-preset").selectOption("qwen_image_21_edit");
  await expect(page.locator("#rookieui-img2img-qwen21-controls")).toBeVisible();
  await expect(page.locator("#rookieui-img2img-reference-card-10")).toBeVisible();
  await expect(page.locator("#rookieui-img2img-denoise-field")).toBeHidden();
  await expect(page.locator("#rookieui-img2img-mask-editor")).toBeHidden();
  await expect(page.locator("#rookieui-img2img-adetailer-section")).toBeHidden();
  for (let index = 1; index <= 10; index += 1) {
    const selector = index === 1 ? "#rookieui-image-asset" : `#rookieui-img2img-reference-asset-${index}`;
    await page.locator(selector).fill(`synthetic-ref-${index}`);
  }
  await page.locator("#rookieui-img2img-reference-clear-7").click();
  await expect(page.locator("#rookieui-img2img-reference-asset-7")).toBeEmpty();
  await expect(page.locator("#rookieui-img2img-reference-status-7")).toContainText("No additional reference");
  await page.locator("#rookieui-img2img-reference-asset-7").fill("synthetic-ref-7");
  await page.locator("#rookieui-img2img-reference-main-9").click();
  await expect(page.locator("#rookieui-image-asset")).toHaveValue("synthetic-ref-10");
  await expect(page.locator("#rookieui-img2img-reference-main-0")).toBeChecked();

  await page.locator("#rookieui-img2img-reference-resolution").fill("1024");
  await page.locator("#rookieui-img2img-output-size-mode").selectOption("custom");
  await expect(page.locator("#rookieui-img2img-width")).toBeVisible();
  await page.locator("#rookieui-img2img-width").fill("768");
  await page.locator("#rookieui-img2img-height").fill("1024");
  await page.locator("#rookieui-img2img-qwen21-background-instruction").click();
  await expect(page.locator("#rookieui-img2img-edit-task")).toHaveValue("background_removal");
  await expect(page.locator("#rookieui-img2img-prompt")).toHaveValue(/<image1>/);
  await pane.screenshot({ path: path.join(artifactRoot, "qwen-edit-ten-references.png") });

  await page.locator("#rookieui-img2img-form").evaluate((form) =>
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
  await expect.poll(async () => page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.img2img.length)).toBe(1);
  const request = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.img2img[0]);
  expect(request).toMatchObject({
    profile: "qwen_image_21_edit",
    image_asset: "synthetic-ref-10",
    main_reference_index: 0,
    reference_resolution: 1024,
    output_size_mode: "custom",
    edit_task: "background_removal",
    width: 768,
    height: 1024,
    batch_size: 1,
    denoise_strength: 1,
  });
  expect(request.reference_images).toHaveLength(10);
  expect(request.reference_images.map((entry) => entry.image_asset)).toEqual([
    "synthetic-ref-10", ...Array.from({ length: 9 }, (_, index) => `synthetic-ref-${index + 1}`),
  ]);

  await page.locator("#rookieui-img2img-preset").selectOption("qwen_image_edit");
  await expect(page.locator("#rookieui-img2img-qwen21-controls")).toBeHidden();
  await expect(page.locator("#rookieui-img2img-reference-card-4")).toBeHidden();
  await expect(page.locator("#rookieui-img2img-adetailer-section")).toBeVisible();
});

test("Qwen edit PNG Info restore keeps canonical order and rejects a stale primary", async ({ page }) => {
  for (const [scenario, valid] of [["valid", true], ["nonzero", false]]) {
    await page.goto(`test-harness.html?qwen21EditImport=${scenario}`);
    await expect(page.locator("#rookieui-root")).toContainText('"hostSurface":"standalone-web"', { timeout: 15000 });
    await page.locator("#rookieui-tab-pnginfo").click();
    await page.setInputFiles("#rookieui-pnginfo-image-file", {
      name: "synthetic.png", mimeType: "image/png", buffer: TINY_PNG,
    });
    await expect(page.locator("#rookieui-pnginfo-status")).toContainText("Ready to apply img2img fields");
    const presetBefore = await page.locator("#rookieui-img2img-preset").inputValue();
    const sourceBefore = await page.locator("#rookieui-image-asset").inputValue();
    await page.locator("#rookieui-pnginfo-apply-img2img").click();
    if (valid) {
      await expect(page.locator("#rookieui-pnginfo-status")).toContainText("Applied img2img fields");
      await expect(page.locator("#rookieui-img2img-preset")).toHaveValue("qwen_image_21_edit");
      await expect(page.locator("#rookieui-image-asset")).toHaveValue("synthetic-restore-1");
      await expect(page.locator("#rookieui-img2img-reference-asset-2")).toHaveValue("synthetic-restore-2");
      await expect(page.locator("#rookieui-img2img-reference-main-0")).toBeChecked();
      await expect(page.locator("#rookieui-img2img-reference-resolution")).toHaveValue("1024");
      await expect(page.locator("#rookieui-img2img-output-size-mode")).toHaveValue("custom");
      await expect(page.locator("#rookieui-img2img-edit-task")).toHaveValue("background_removal");
    } else {
      await expect(page.locator("#rookieui-pnginfo-status")).toContainText("rejected or unavailable");
      await expect(page.locator("#rookieui-img2img-status")).toContainText("reference 1 must be primary");
      await expect(page.locator("#rookieui-img2img-preset")).toHaveValue(presetBefore);
      await expect(page.locator("#rookieui-image-asset")).toHaveValue(sourceBefore);
    }
  }
});
