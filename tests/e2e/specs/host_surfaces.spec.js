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
  const requestCapture = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__ ?? {});
  expect(submittedPrompts).toContain("proxy-safe cat");
  expect(requestCapture.fetchApiRoutes).toContain("/rookieui/generate/txt2img");
  expect(requestCapture.fetchApiNetworkPaths).toContain("/api/rookieui/generate/txt2img");
  expect(requestCapture.rootFetchPaths).toEqual([]);
});

test("recovers model selectors from ComfyUI object_info when RookieUI models route is unavailable", async ({ page }) => {
  await page.goto("test-harness.html?rejectRookieModels=1");
  await expect(page.locator("#rookieui-shell-title")).toHaveText("RookieUI");
  await expect(page.locator("#rookieui-checkpoint option")).toHaveCount(1);
  const checkpointOptions = await page.locator("#rookieui-checkpoint option").evaluateAll((options) =>
    options.map((option) => option.value),
  );
  expect(checkpointOptions).toEqual(["realvisxl.safetensors"]);
  expect(checkpointOptions).not.toContain("__host_default__");
  const vaeOptions = await page.locator("#rookieui-vae option").evaluateAll((options) =>
    options.map((option) => option.value),
  );
  expect(vaeOptions).toContain("ae.safetensors");
  expect(vaeOptions).toContain("qwen_image_vae.safetensors");
  await page.locator("#rookieui-preset").selectOption("flux");
  await expect(page.locator("#rookieui-checkpoint")).toHaveAttribute("data-model-category", "diffusion_models");
  const diffusionOptions = await page.locator("#rookieui-checkpoint option").evaluateAll((options) =>
    options.map((option) => option.value),
  );
  expect(diffusionOptions).toContain("flux1-dev.safetensors");
});
