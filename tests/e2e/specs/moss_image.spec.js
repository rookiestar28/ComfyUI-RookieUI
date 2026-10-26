const { test, expect } = require("@playwright/test");
const path = require("node:path");

test("MOSS profile switch, SLG, submit and restore preserve effective parameters", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("test-harness.html");
  await expect(page.locator("#rookieui-shell-title")).toHaveText("RookieUI");
  await page.locator("#rookieui-prompt").fill("synthetic native 中文 (literal:1.2)");
  await page.locator("#rookieui-negative-prompt").fill("synthetic unwanted");
  await page.locator("#rookieui-preset").selectOption("moss_image_base");
  await expect(page.locator("#rookieui-prompt")).toHaveValue("synthetic native 中文 (literal:1.2)");
  await expect(page.locator("#rookieui-moss-slg-enabled")).toBeChecked();
  await expect(page.locator("#rookieui-sampler")).toHaveValue("er_sde");
  await expect(page.locator("#rookieui-scheduler")).toHaveValue("simple");
  await expect(page.locator("#rookieui-txt2img-submit")).toBeEnabled();
  await expect(page.locator("#rookieui-clip-skip")).toBeDisabled();
  await expect(page.locator("#rookieui-checkpoint option")).toHaveCount(1);
  await page.locator("#rookieui-moss-slg-enabled").uncheck();
  await page.locator("#rookieui-width").fill("768");
  await expect(page.locator("#rookieui-width-slider")).toHaveValue("768");
  await page.locator("#rookieui-steps").fill("27");
  await page.locator("#rookieui-cfg-scale").fill("3");
  await page.locator("#rookieui-seed").fill("123");
  await page.locator("#rookieui-txt2img-submit").click();
  await expect.poll(() => page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img.length)).toBe(1);
  expect(await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img[0])).toMatchObject({
    profile: "moss_image_base", checkpoint_name: "moss_image_base_int8_convrot.safetensors",
    text_encoder_name: "qwen3.5_9b_int8_convrot.safetensors", vae_name: "flux2-vae.safetensors",
    moss_options: { slg_enabled: false }, width: 768, steps: 27, cfg_scale: 3, seed: 123,
    sampler_name: "er_sde", scheduler_name: "simple",
    prompt: "synthetic native 中文 (literal:1.2)", negative_prompt: "synthetic unwanted",
    prompt_enhancement_enabled: false, hires_enabled: false, clip_skip: 1,
  });
  await page.locator("#rookieui-preset").selectOption("moss_image_sft");
  await expect(page.locator("#rookieui-moss-slg-enabled")).not.toBeChecked();
  await expect(page.locator("#rookieui-checkpoint")).toHaveValue("moss_image_sft_int8_convrot.safetensors");
  await expect(page.locator("#rookieui-sampler")).toHaveValue("er_sde");
  await expect(page.locator("#rookieui-scheduler")).toHaveValue("simple");
  await page.locator("#rookieui-moss-slg-enabled").check();
  await page.evaluate(() => window.__ROOKIEUI_E2E_APP__.extensionManager.activeSidebarTab.destroy());
  await page.evaluate(() => window.__ROOKIEUI_E2E_APP__.extensionManager.activeSidebarTab.render(document.getElementById("mock-sidebar-tabs")));
  await expect(page.locator("#rookieui-preset")).toHaveValue("moss_image_sft");
  await expect(page.locator("#rookieui-moss-slg-enabled")).toBeChecked();
  await expect(page.locator("#rookieui-txt2img-submit")).toBeEnabled();
  const visualDir = process.env.ROOKIEUI_VISUAL_EVIDENCE_DIR;
  const shot = await page.locator("#mock-sidebar-tabs").screenshot(visualDir ? { path: path.join(visualDir, "moss-sft-restored-1440x1000.png") } : {});
  await testInfo.attach("moss-sft-restored", { body: shot, contentType: "image/png" });
  await page.locator("#rookieui-preset").selectOption("sd15");
  await expect(page.locator("#rookieui-moss-controls")).toBeHidden();
  await expect(page.locator("#rookieui-clip-skip")).toBeEnabled();
  expect(errors).toEqual([]);
});

test("missing MOSS host reports a reason and prevents Generate and keyboard enqueue", async ({ page }) => {
  await page.goto("test-harness.html?mossHost=missing");
  await page.locator("#rookieui-preset").selectOption("moss_image_base");
  await expect(page.locator("#rookieui-moss-status")).toContainText("MOSS");
  await expect(page.locator("#rookieui-txt2img-submit")).toBeDisabled();
  await page.locator("#rookieui-prompt").fill("synthetic unavailable");
  await page.locator("#rookieui-prompt").press("Control+Enter");
  expect(await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img.length)).toBe(0);
  await page.locator("#rookieui-preset").selectOption("sd15");
  await expect(page.locator("#rookieui-txt2img-submit")).toBeEnabled();
});

test("PNG Info restores MOSS to txt2img with explicit SLG and no img2img fallback", async ({ page }) => {
  await page.goto("test-harness.html?mossPng=1");
  await page.locator("#rookieui-tab-pnginfo").click();
  await page.locator("#rookieui-pnginfo-image-file").setInputFiles({
    name: "synthetic.png", mimeType: "image/png",
    buffer: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lxkAAAAASUVORK5CYII=", "base64"),
  });
  await expect(page.locator("#rookieui-pnginfo-status")).toContainText("Ready to apply");
  await expect(page.locator("#rookieui-pnginfo-apply-img2img")).toBeDisabled();
  await expect(page.locator("#rookieui-pnginfo-apply-txt2img")).toBeEnabled();
  await page.locator("#rookieui-pnginfo-apply-txt2img").click();
  await expect(page.locator("#rookieui-preset")).toHaveValue("moss_image_sft");
  await expect(page.locator("#rookieui-moss-slg-enabled")).toBeChecked();
  await expect(page.locator("#rookieui-width")).toHaveValue("768");
  await expect(page.locator("#rookieui-steps")).toHaveValue("27");
  await expect(page.locator("#rookieui-seed")).toHaveValue("321");
  await page.locator("#rookieui-txt2img-submit").click();
  await expect.poll(() => page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img.length)).toBe(1);
  expect(await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img[0])).toMatchObject({
    profile: "moss_image_sft", moss_options: { slg_enabled: true }, seed: 321, width: 768,
    prompt: "synthetic PNG restored 中文", checkpoint_name: "moss_image_sft_int8_convrot.safetensors",
  });
});
