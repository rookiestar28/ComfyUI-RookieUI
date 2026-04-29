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

test("keeps txt2img Generate clickable when host submit listeners intercept the form event", async ({ page }) => {
  await page.goto("test-harness.html?runtimeApiFetch=1&rejectRootApiFetch=1");
  await expect(page.locator("#rookieui-root")).toContainText('"clientId":"e2e-runtime-api-client"');
  await page.locator("#rookieui-prompt").fill("click-only cat");
  await page.evaluate(() => {
    document.getElementById("rookieui-txt2img-form")?.addEventListener(
      "submit",
      (event) => {
        event.preventDefault();
        event.stopImmediatePropagation();
      },
      true,
    );
  });

  await page.locator("#rookieui-txt2img-submit").click();

  await expect(page.locator("#rookieui-txt2img-status")).toContainText(/(Queued prompt|Completed:) e2e-prompt-123/);
  const submittedPrompts = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__?.txt2img?.map((entry) => entry.prompt));
  expect(submittedPrompts).toContain("click-only cat");
  expect(submittedPrompts.filter((prompt) => prompt === "click-only cat")).toHaveLength(1);
});

test("routes bootstrap request bindings through the ComfyUI runtime API resolver", async ({ page }) => {
  await page.goto("test-harness.html?runtimeApiFetch=1&rejectRootApiFetch=1");
  await expect(page.locator("#rookieui-root")).toContainText('"clientId":"e2e-runtime-api-client"');
  await page.evaluate(async () => {
    await window.__ROOKIEUI_BOOTSTRAP__.submitImg2ImgRequest({
      prompt: "runtime-bound variation",
      image_asset: "input.png",
      profile: "sd15",
    });
    await window.__ROOKIEUI_BOOTSTRAP__.inspectPngInfoRequest({ image_data: "data:image/png;base64,ZmFrZQ==" });
    await window.__ROOKIEUI_BOOTSTRAP__.submitExtrasRequest({
      mode: "single_image",
      image_data: "data:image/png;base64,ZmFrZQ==",
    });
    await window.__ROOKIEUI_BOOTSTRAP__.fetchQueueRequest("e2e-runtime-api-client");
    await window.__ROOKIEUI_BOOTSTRAP__.fetchControlNetModelListRequest();
    await window.__ROOKIEUI_BOOTSTRAP__.estimateXYZPlotRequest({ mode: "txt2img", axes: [] });
  });

  const requestCapture = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__ ?? {});
  expect(requestCapture.fetchApiRoutes).toEqual(
    expect.arrayContaining([
      "/rookieui/generate/img2img",
      "/rookieui/pnginfo/inspect",
      "/rookieui/extras/run",
      "/rookieui/controlnet/model_list",
      "/rookieui/xyz-plot/estimate",
    ]),
  );
  expect(requestCapture.fetchApiNetworkPaths).toEqual(
    expect.arrayContaining([
      "/api/rookieui/generate/img2img",
      "/api/rookieui/pnginfo/inspect",
      "/api/rookieui/extras/run",
      "/api/rookieui/controlnet/model_list",
      "/api/rookieui/xyz-plot/estimate",
    ]),
  );
  expect(requestCapture.fetchApiNetworkPaths.some((path) => path.startsWith("/api/rookieui/queue"))).toBe(true);
  expect(requestCapture.rootFetchPaths).toEqual([]);
});

test("runs ControlNet preprocessor through the ComfyUI runtime API resolver", async ({ page }) => {
  await page.goto("test-harness.html?runtimeApiFetch=1&rejectRootApiFetch=1");
  await expect(page.locator("#rookieui-root")).toContainText('"clientId":"e2e-runtime-api-client"');
  await page.locator("#rookieui-txt2img-controlnet-section").evaluate((details) => {
    details.open = true;
  });
  await page.locator("#rookieui-txt2img-controlnet-image-data-0").evaluate((input) => {
    input.value = "data:image/png;base64,aW1hZ2UtY29udHJvbA==";
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await page.locator("#rookieui-txt2img-controlnet-module-0").selectOption("depth");
  await page.locator("#rookieui-txt2img-controlnet-run-preprocessor-0").click();

  await expect(page.locator("#rookieui-txt2img-status")).toContainText("preprocessor completed");
  const requestCapture = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__ ?? {});
  expect(requestCapture.fetchApiRoutes).toContain("/rookieui/controlnet/detect");
  expect(requestCapture.fetchApiNetworkPaths).toContain("/api/rookieui/controlnet/detect");
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
