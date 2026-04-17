const { test, expect } = require("@playwright/test");

test("loads the RookieUI bootstrap harness", async ({ page }) => {
  await page.goto("test-harness.html");
  await page.evaluate(() => {
    let fullscreenElement = null;
    Object.defineProperty(document, "fullscreenElement", {
      configurable: true,
      get() {
        return fullscreenElement;
      },
    });
    HTMLElement.prototype.requestFullscreen = async function requestFullscreenShim() {
      fullscreenElement = this;
      document.dispatchEvent(new Event("fullscreenchange"));
    };
    document.exitFullscreen = async function exitFullscreenShim() {
      fullscreenElement = null;
      document.dispatchEvent(new Event("fullscreenchange"));
    };
  });
  await expect(page.locator("#rookieui-title")).toHaveText("RookieUI Bootstrap Harness");
  await expect(page.locator("#rookieui-root")).toContainText('"hostSurface":"standalone-web"');
  await expect(page.locator("#rookieui-root")).toContainText('"hostSurfaceSupported":true');
  await expect(page.locator("#rookieui-shell-title")).toHaveText("RookieUI");
  await expect(page.locator("#rookieui-header-version")).toHaveText("v0.1.0");
  await expect(page.locator("#rookieui-view-github")).toHaveText("View on GitHub");
  await expect(page.locator("#mock-sidebar-tabs")).toHaveCSS("min-width", "980px");
  await expect(page.locator(".side-bar-panel")).toHaveCSS("min-width", "980px");
  await expect(page.locator(".sidebar-content-container")).toHaveCSS("min-width", "980px");
  await expect(page.locator("#mock-sidebar-tabs")).toHaveAttribute("data-theme", "normal");
  await expect(page.locator("#mock-sidebar-tabs")).not.toContainText("Rookie Mode");
  await expect(page.locator("#mock-sidebar-tabs")).not.toContainText("Server capabilities");
  await expect(page.locator("#rookieui-txt2img-quicksettings")).toBeVisible();
  await expect(page.locator("#rookieui-low-bits-quicksetting")).toBeVisible();
  await expect(page.locator("#rookieui-preset")).toHaveCSS("min-height", "28px");
  await expect(page.locator("#rookieui-checkpoint")).toHaveCSS("min-height", "28px");
  await expect(page.locator("#rookieui-preset-quicksetting .rookieui-shell__quicksetting-label")).toHaveCSS(
    "font-size",
    "12px",
  );
  await expect(page.locator("#rookieui-preset-quicksetting .rookieui-shell__quicksetting-label")).toHaveCSS(
    "font-weight",
    "500",
  );
  await expect(page.locator("#rookieui-prompt")).toHaveCSS("min-height", "108px");
  await expect(page.locator("#rookieui-pane-txt2img .rookieui-shell__prompt-field .rookieui-shell__field-label")).toHaveCount(0);
  await expect(page.locator("#rookieui-txt2img-submit")).toHaveCSS("font-size", "14px");
  await expect(page.locator("#rookieui-txt2img-submit")).toHaveCSS("font-weight", "400");
  const promptPlaceholderStyles = await page.locator("#rookieui-prompt").evaluate((node) => {
    const styles = getComputedStyle(node, "::placeholder");
    return {
      fontSize: styles.fontSize,
      fontWeight: styles.fontWeight,
    };
  });
  expect(promptPlaceholderStyles).toEqual({ fontSize: "12px", fontWeight: "400" });
  const sizeFieldLabel = page.locator("#rookieui-steps-field .rookieui-shell__field-label");
  await expect(sizeFieldLabel).toHaveCSS("font-size", "12px");
  await expect(sizeFieldLabel).toHaveCSS("font-weight", "500");
  const alignment = await page.evaluate(() => {
    const prompt = document.querySelector("#rookieui-prompt");
    const hero = document.querySelector("#rookieui-txt2img-submit");
    const promptRect = prompt?.getBoundingClientRect();
    const heroRect = hero?.getBoundingClientRect();
    return {
      topDelta: Math.abs((promptRect?.top ?? 0) - (heroRect?.top ?? 0)),
      heightDelta: Math.abs((promptRect?.height ?? 0) - (heroRect?.height ?? 0)),
    };
  });
  expect(alignment.topDelta).toBeLessThanOrEqual(2);
  expect(alignment.heightDelta).toBeGreaterThanOrEqual(26);
  expect(alignment.heightDelta).toBeLessThanOrEqual(34);
  const txt2imgHeroHeight = await page.locator("#rookieui-txt2img-submit").evaluate((node) => {
    return Math.round(node.getBoundingClientRect().height);
  });
  expect(txt2imgHeroHeight).toBeGreaterThanOrEqual(76);
  expect(txt2imgHeroHeight).toBeLessThanOrEqual(82);
  await expect(page.locator("#rookieui-txt2img-action-target")).toBeVisible();
  await expect(page.locator("#rookieui-txt2img-apply-action-target")).toBeVisible();
  await expect(page.locator("#rookieui-txt2img-open-queue-icon .rookieui-shell__mini-action-icon")).toHaveText("📂");
  await expect(page.locator("#rookieui-txt2img-open-pnginfo .rookieui-shell__mini-action-icon")).toHaveText("📋");
  await expect(page.locator("#rookieui-txt2img-apply-action-target .rookieui-shell__mini-action-icon")).toHaveText("🖌️");
  await expect(page.locator("#rookieui-txt2img-preview-extras .rookieui-shell__mini-action-icon")).toHaveText("📐");
  await expect(
    page.locator("#rookieui-pane-txt2img .rookieui-shell__preview-toolbar .rookieui-shell__mini-action--icon"),
  ).toHaveCount(6);
  await expect(
    page.locator("#rookieui-pane-txt2img .rookieui-shell__preview-overlay-toolbar #rookieui-txt2img-preview-fullscreen"),
  ).toBeVisible();
  await page.evaluate(() => {
    const previewBox = document.getElementById("rookieui-txt2img-preview");
    previewBox.innerHTML = "";
    const image = document.createElement("img");
    image.className = "rookieui-shell__preview-image";
    image.src =
      "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7ZrY4AAAAASUVORK5CYII=";
    previewBox.appendChild(image);
    previewBox.__previewFullscreenController?.syncImage?.();
  });
  await page.locator("#rookieui-txt2img-preview").click();
  await expect
    .poll(async () =>
      page.evaluate(() =>
        document.fullscreenElement?.classList?.contains("rookieui-shell__preview-surface") ?? false,
      ),
    )
    .toBe(true);
  await expect(page.locator("#rookieui-txt2img-status")).toContainText("entered fullscreen mode");
  await page.locator("#rookieui-txt2img-preview").click();
  await expect
    .poll(async () => page.evaluate(() => document.fullscreenElement === null))
    .toBe(true);
  await expect(page.locator("#rookieui-txt2img-status")).toContainText("exited fullscreen mode");
  await page.evaluate(() => {
    const previewBox = document.getElementById("rookieui-txt2img-preview");
    previewBox.innerHTML = "";
    const placeholder = document.createElement("span");
    placeholder.className = "rookieui-shell__preview-placeholder";
    placeholder.textContent = "Generation preview will update while the job is running.";
    previewBox.appendChild(placeholder);
    previewBox.__previewFullscreenController?.syncImage?.();
  });
  await expect(page.locator("#rookieui-steps-slider")).toHaveCSS("accent-color", "rgb(78, 134, 235)");
  const sliderBackground = await page.locator("#rookieui-steps-slider").evaluate((node) => {
    return getComputedStyle(node).backgroundImage;
  });
  expect(sliderBackground).toContain("rgb(78, 134, 235)");
  expect(sliderBackground).toContain("rgb(255, 255, 255)");
  await expect(page.locator("#rookieui-tab-txt2img")).toHaveClass(/is-active/);
  await expect(page.locator("#rookieui-tab-txt2img")).toHaveCSS("font-size", "14px");
  await expect(page.locator("#rookieui-tab-txt2img")).toHaveCSS("font-weight", "400");
  await expect(page.locator("#rookieui-shell-tabs")).toHaveCSS("border-bottom-width", "1px");
  await expect(page.locator("#rookieui-txt2img-workspace-tab-generation")).toHaveCSS("font-size", "14px");
  await expect(page.locator("#rookieui-txt2img-workspace-tab-generation")).toHaveCSS("font-weight", "400");
  await expect(page.locator("#rookieui-txt2img-workspace-tabs")).toHaveCSS("border-bottom-width", "1px");
  await expect(page.locator("#rookieui-profile")).toHaveCount(0);
  await expect(page.locator("#rookieui-img2img-profile")).toHaveCount(0);
  await expect(page.locator("#mock-sidebar-tabs")).not.toContainText("Shared Model Inventory");
  await expect(page.locator("#rookieui-checkpoint-list")).toHaveCount(0);
  await expect(page.locator("#rookieui-vae-list")).toHaveCount(0);
  await expect(page.locator("#rookieui-text-encoder-list")).toHaveCount(0);
  await expect(page.locator("#rookieui-prompt")).toHaveValue("");
  await expect(page.locator("#rookieui-prompt")).toHaveAttribute("placeholder", /Ctrl\+Enter to Generate/);
  await expect(page.locator("#rookieui-negative-prompt")).toHaveAttribute("placeholder", /Ctrl\+Enter to Generate/);
  await page.locator("#rookieui-prompt").fill("   ");
  await expect(page.locator("#rookieui-prompt")).toHaveValue("");
  await expect(page.locator("#rookieui-prompt-counter")).toHaveText("0/75");
  await expect(page.locator("#rookieui-cfg-scale")).toHaveAttribute("step", "0.01");
  await expect(page.locator("#rookieui-hires-scale")).toHaveAttribute("step", "0.01");
  await expect(page.locator("#rookieui-hires-denoise")).toHaveAttribute("step", "0.01");
  await expect(page.locator("#rookieui-hires-denoise")).toHaveAttribute("max", "1");
  await expect(page.locator("#rookieui-img2img-cfg-scale")).toHaveAttribute("step", "0.01");
  await expect(page.locator("#rookieui-denoise-strength")).toHaveAttribute("step", "0.01");
  await expect(page.locator("#rookieui-img2img-hires-denoise")).toHaveAttribute("max", "1");
  await expect(page.locator("#rookieui-sampler")).toHaveJSProperty("tagName", "SELECT");
  await expect(page.locator("#rookieui-scheduler")).toHaveJSProperty("tagName", "SELECT");
  await expect(page.locator("#rookieui-steps-slider")).toBeVisible();
  await expect(page.locator("#rookieui-width-slider")).toBeVisible();
  await expect(page.locator("#rookieui-batch-count")).toHaveValue("1");
  await expect(page.locator("#rookieui-hires-enabled")).toHaveClass(/rookieui-shell__checkbox/);
  await expect(page.locator("#rookieui-pane-txt2img")).toBeVisible();
  await expect(page.locator("#rookieui-pane-img2img")).toBeHidden();
  await expect(page.locator("#rookieui-pane-img2img")).toHaveAttribute("hidden", "");
  await page.locator("#rookieui-txt2img-open-queue-icon").click();
  await expect(page.locator("#rookieui-pane-queue")).toBeVisible();
  await page.locator("#rookieui-tab-txt2img").click();
  const txt2imgHeroWidth = await page.locator("#rookieui-txt2img-submit").evaluate((node) => {
    return Math.round(node.getBoundingClientRect().width);
  });
  const txt2imgActionRailLayout = await page.evaluate(() => {
    const heroRect = document.querySelector("#rookieui-txt2img-submit")?.getBoundingClientRect();
    const miniActionsRect = document.querySelector("#rookieui-pane-txt2img .rookieui-shell__mini-actions")?.getBoundingClientRect();
    const actionTargetRowRect = document.querySelector("#rookieui-txt2img-action-target")?.closest(".rookieui-shell__action-target-row")?.getBoundingClientRect();
    return {
      miniLeftDelta: Math.abs((miniActionsRect?.left ?? 0) - (heroRect?.left ?? 0)),
      targetLeftDelta: Math.abs((actionTargetRowRect?.left ?? 0) - (heroRect?.left ?? 0)),
      targetWidth: Math.round(actionTargetRowRect?.width ?? 0),
    };
  });
  expect(txt2imgActionRailLayout.miniLeftDelta).toBeLessThanOrEqual(2);
  expect(txt2imgActionRailLayout.targetLeftDelta).toBeLessThanOrEqual(2);
  expect(Math.abs(txt2imgActionRailLayout.targetWidth - txt2imgHeroWidth)).toBeLessThanOrEqual(2);
  await page.locator("#rookieui-txt2img-action-target").selectOption("extras");
  await page.locator("#rookieui-txt2img-apply-action-target").click();
  await expect(page.locator("#rookieui-pane-extras")).toBeVisible();
  await expect(page.locator("#rookieui-extras-generate-open-queue .rookieui-shell__mini-action-icon")).toHaveText("📂");
  await expect(page.locator("#rookieui-extras-generate-open-pnginfo .rookieui-shell__mini-action-icon")).toHaveText("📋");
  const extrasHeroWidth = await page.locator("#rookieui-extras-submit").evaluate((node) => {
    return Math.round(node.getBoundingClientRect().width);
  });
  expect(Math.abs(txt2imgHeroWidth - extrasHeroWidth)).toBeLessThanOrEqual(2);
  const extrasAlignment = await page.evaluate(() => {
    const singlePane = document.querySelector("#rookieui-extras-single-pane");
    const hero = document.querySelector("#rookieui-extras-submit");
    const singleRect = singlePane?.getBoundingClientRect();
    const heroRect = hero?.getBoundingClientRect();
    return {
      topDelta: Math.abs((singleRect?.top ?? 0) - (heroRect?.top ?? 0)),
    };
  });
  expect(extrasAlignment.topDelta).toBeLessThanOrEqual(2);
  await page.locator("#rookieui-tab-txt2img").click();

  // CRITICAL: this preset matrix pins the clip-skip regression seam; profile switches must never hard-disable input/slider.
  const diffusionModelOptions = [
    "flux1-dev.safetensors",
    "qwen-image.safetensors",
    "klein-flux2.safetensors",
    "lumina2.safetensors",
    "zImageTurboNSFW_21BF16AIO.safetensors",
    "wan2_2b.safetensors",
    "animaPencilXL_v500.safetensors",
  ];
  const diffusionProfileDefaults = {
    flux: "flux1-dev.safetensors",
    qwen_image: "qwen-image.safetensors",
    klein: "klein-flux2.safetensors",
    lumina: "lumina2.safetensors",
    zit: "zImageTurboNSFW_21BF16AIO.safetensors",
    wan: "wan2_2b.safetensors",
    anima: "animaPencilXL_v500.safetensors",
  };
  const clipSkipPresetMatrix = [
    { id: "sd15", textEncoderVisible: false, ignoredHint: false },
    { id: "sdxl", textEncoderVisible: false, ignoredHint: true },
    { id: "flux", textEncoderVisible: true, ignoredHint: true },
    { id: "qwen_image", textEncoderVisible: true, ignoredHint: true },
    { id: "klein", textEncoderVisible: true, ignoredHint: true },
    { id: "lumina", textEncoderVisible: true, ignoredHint: true },
    { id: "zit", textEncoderVisible: true, ignoredHint: true },
    { id: "wan", textEncoderVisible: true, ignoredHint: true },
    { id: "anima", textEncoderVisible: true, ignoredHint: true },
  ];

  for (const row of clipSkipPresetMatrix) {
    await page.locator("#rookieui-preset").selectOption(row.id);
    await expect(page.locator("#rookieui-clip-skip")).toBeEnabled();
    await expect(page.locator("#rookieui-clip-skip-slider")).toBeEnabled();
    if (row.textEncoderVisible) {
      await expect(page.locator("#rookieui-text-encoder")).toBeVisible();
    } else {
      await expect(page.locator("#rookieui-text-encoder")).toBeHidden();
    }
    if (row.ignoredHint) {
      await expect(page.locator("#rookieui-clip-skip")).toHaveAttribute("data-execution-hint", "ignored");
    } else {
      await expect(page.locator("#rookieui-clip-skip")).not.toHaveAttribute("data-execution-hint", "ignored");
    }
    if (row.id in diffusionProfileDefaults) {
      await expect(page.locator("#rookieui-checkpoint")).toHaveAttribute("data-model-category", "diffusion_models");
      const checkpointOptions = await page.locator("#rookieui-checkpoint option").evaluateAll((options) =>
        options.map((option) => option.value),
      );
      expect(checkpointOptions).toEqual(diffusionModelOptions);
      await expect(page.locator("#rookieui-checkpoint")).toHaveValue(diffusionProfileDefaults[row.id]);
    } else {
      await expect(page.locator("#rookieui-checkpoint")).toHaveAttribute("data-model-category", "checkpoints");
    }
  }
  await page.locator("#rookieui-tab-queue").click();
  await page.locator("#rookieui-tab-txt2img").click();
  await expect(page.locator("#rookieui-clip-skip")).toBeEnabled();
  await expect(page.locator("#rookieui-clip-skip-slider")).toBeEnabled();

  await page.locator("#rookieui-txt2img-preview-img2img").click();
  await expect(page.locator("#rookieui-pane-img2img")).toBeVisible();
  for (const row of clipSkipPresetMatrix) {
    await page.locator("#rookieui-img2img-preset").selectOption(row.id);
    await expect(page.locator("#rookieui-img2img-clip-skip")).toBeEnabled();
    await expect(page.locator("#rookieui-img2img-clip-skip-slider")).toBeEnabled();
    if (row.textEncoderVisible) {
      await expect(page.locator("#rookieui-img2img-text-encoder")).toBeVisible();
    } else {
      await expect(page.locator("#rookieui-img2img-text-encoder")).toBeHidden();
    }
    if (row.ignoredHint) {
      await expect(page.locator("#rookieui-img2img-clip-skip")).toHaveAttribute("data-execution-hint", "ignored");
    } else {
      await expect(page.locator("#rookieui-img2img-clip-skip")).not.toHaveAttribute("data-execution-hint", "ignored");
    }
    if (row.id in diffusionProfileDefaults) {
      await expect(page.locator("#rookieui-img2img-checkpoint")).toHaveAttribute(
        "data-model-category",
        "diffusion_models",
      );
      const checkpointOptions = await page.locator("#rookieui-img2img-checkpoint option").evaluateAll((options) =>
        options.map((option) => option.value),
      );
      expect(checkpointOptions).toEqual(diffusionModelOptions);
      await expect(page.locator("#rookieui-img2img-checkpoint")).toHaveValue(diffusionProfileDefaults[row.id]);
    } else {
      await expect(page.locator("#rookieui-img2img-checkpoint")).toHaveAttribute("data-model-category", "checkpoints");
    }
  }
  await page.locator("#rookieui-tab-queue").click();
  await page.locator("#rookieui-tab-img2img").click();
  await expect(page.locator("#rookieui-img2img-clip-skip")).toBeEnabled();
  await expect(page.locator("#rookieui-img2img-clip-skip-slider")).toBeEnabled();

  await page.locator("#rookieui-tab-txt2img").click();
  await page.locator("#rookieui-preset").selectOption("sd15");
  await expect(page.locator("#rookieui-txt2img-generation-section #rookieui-advanced-controls")).toHaveCount(1);
  await expect(page.locator("#rookieui-advanced-controls")).toHaveClass(/rookieui-shell__section/);
  await expect(page.locator("#rookieui-advanced-controls")).toHaveClass(/rookieui-shell__hires--integrated/);
  await expect(page.locator("#rookieui-advanced-controls .rookieui-shell__hires-toggle")).toBeVisible();
  await expect(page.locator("#rookieui-advanced-controls .rookieui-shell__hires-toggle")).toHaveText("");
  await expect(page.locator("#rookieui-advanced-controls .rookieui-shell__hires-caret")).toHaveCSS("font-size", "30px");
  await expect(page.locator("#rookieui-advanced-controls")).not.toContainText(
    "Second latent pass with bounded rookie-safe defaults.",
  );
  await page.locator("#rookieui-advanced-controls").evaluate((details) => {
    details.open = true;
  });
  await page.locator("#rookieui-prompt").fill("e2e sunset skyline");
  await page.locator("#rookieui-batch-count").fill("2");
  await expect(page.locator("#rookieui-batch-count-slider")).toHaveValue("2");
  await page.locator("#rookieui-txt2img-workspace-tab-textual-inversion").click();
  await page.locator("#rookieui-txt2img-embedding-item-0").click();
  await expect(page.locator("#rookieui-prompt")).toHaveValue(/embedding:badhandv4\.pt/);
  await expect(page.locator("#rookieui-prompt-counter")).not.toHaveText("0/75");
  await page.locator("#rookieui-txt2img-workspace-tab-lora").click();
  await page.locator("#rookieui-txt2img-lora-item-0").click();
  await page.locator("#rookieui-lora-strength-model").fill("0.9");
  await page.locator("#rookieui-lora-strength-clip").fill("0.7");
  await page.locator("#rookieui-txt2img-workspace-tab-generation").click();
  await page.locator("#rookieui-txt2img-controlnet-section").evaluate((details) => {
    details.open = true;
  });
  await expect(page.locator("#rookieui-txt2img-controlnet-run-preprocessor-0")).toBeVisible();
  await expect(page.locator("#rookieui-txt2img-controlnet-run-preprocessor-0")).toHaveAttribute(
    "title",
    "Run Preprocessor",
  );
  await expect(
    page.locator("#rookieui-txt2img-controlnet-run-preprocessor-0 .rookieui-shell__mini-action-icon"),
  ).toHaveText("💥");
  await expect(
    page.locator("#rookieui-txt2img-controlnet-preview-stage-0 .rookieui-shell__controlnet-preview-placeholder-icon"),
  ).toHaveText("⤴");
  await expect(
    page.locator("#rookieui-txt2img-controlnet-preview-upload-action-0 .rookieui-shell__mini-action-icon"),
  ).toHaveText("📁");
  await expect(
    page.locator("#rookieui-txt2img-controlnet-preview-remove-action-0 .rookieui-shell__mini-action-icon"),
  ).toHaveText("🗑");
  await expect(page.locator("#rookieui-txt2img-controlnet-image-upload-button-0")).toBeHidden();
  const txt2imgControlNetRowLayout = await page.evaluate(() => {
    const moduleSelect = document.querySelector("#rookieui-txt2img-controlnet-module-0");
    const runButton = document.querySelector("#rookieui-txt2img-controlnet-run-preprocessor-0");
    const modelSelect = document.querySelector("#rookieui-txt2img-controlnet-model-0");
    const weightField = document.querySelector("#rookieui-txt2img-controlnet-weight-field-0");
    const timestepField = document.querySelector("#rookieui-txt2img-controlnet-timestep-range-field-0");
    const moduleRect = moduleSelect?.getBoundingClientRect();
    const runRect = runButton?.getBoundingClientRect();
    const modelRect = modelSelect?.getBoundingClientRect();
    const weightRect = weightField?.getBoundingClientRect();
    const timestepRect = timestepField?.getBoundingClientRect();
    return {
      moduleLeft: moduleRect?.left ?? 0,
      runLeft: runRect?.left ?? 0,
      modelLeft: modelRect?.left ?? 0,
      moduleHeight: moduleRect?.height ?? 0,
      modelHeight: modelRect?.height ?? 0,
      weightWidth: weightRect?.width ?? 0,
      timestepWidth: timestepRect?.width ?? 0,
    };
  });
  expect(txt2imgControlNetRowLayout.moduleLeft).toBeLessThan(txt2imgControlNetRowLayout.runLeft);
  expect(txt2imgControlNetRowLayout.runLeft).toBeLessThan(txt2imgControlNetRowLayout.modelLeft);
  expect(Math.abs(txt2imgControlNetRowLayout.moduleHeight - txt2imgControlNetRowLayout.modelHeight)).toBeLessThanOrEqual(
    2,
  );
  expect(Math.abs(txt2imgControlNetRowLayout.weightWidth - txt2imgControlNetRowLayout.timestepWidth)).toBeLessThanOrEqual(
    2,
  );
  await page.locator("#rookieui-cfg-scale").fill("7.25");
  await page.locator("#rookieui-hires-enabled").check();
  await page.locator("#rookieui-hires-scale").fill("1.8");
  await page.locator("#rookieui-hires-denoise").fill("0.45");
  await page.locator("#rookieui-hires-steps").fill("12");
  await page.locator("#rookieui-txt2img-form").evaluate((form) => {
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });
  await expect(page.locator("#rookieui-txt2img-status")).toContainText("e2e-prompt-123");
  const txt2imgRequests = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img);
  expect(txt2imgRequests).toHaveLength(1);
  expect(txt2imgRequests[0]).toMatchObject({
    prompt: "e2e sunset skyline, embedding:badhandv4.pt",
    cfg_scale: 7.25,
    dtype_profile: "automatic",
    batch_count: 2,
    hires_enabled: true,
    hires_scale: 1.8,
    hires_denoise: 0.45,
    hires_steps: 12,
    lora_name: "detail_tweaker.safetensors",
    lora_strength_model: 0.9,
    lora_strength_clip: 0.7,
  });
  await page.locator("#rookieui-tab-img2img").click();
  await expect(page.locator("#rookieui-pane-txt2img")).toBeHidden();
  await expect(page.locator("#rookieui-pane-img2img")).toBeVisible();
  await expect(page.locator("#rookieui-pane-txt2img")).toHaveAttribute("hidden", "");
  await expect(page.locator("#rookieui-img2img-source-canvas-stage")).toBeVisible();
  await expect(page.locator("#rookieui-img2img-source-canvas-stage")).toHaveAttribute("data-interaction-mode", "upload");
  await expect(page.locator("#rookieui-img2img-source-canvas-stage")).toHaveAttribute("aria-label", "Upload source image");
  await expect(
    page.locator("#rookieui-img2img-image-dropzone .rookieui-shell__canvas-upload-placeholder-text"),
  ).toHaveText("Upload Img2Img source image");
  const sourceStageRouting = await page.evaluate(() => {
    const stage = document.getElementById("rookieui-img2img-source-canvas-stage");
    const input = document.getElementById("rookieui-img2img-image-file");
    const sourceValueInput =
      document.getElementById("rookieui-image-data") ?? document.getElementById("rookieui-image-asset");
    let clickCount = 0;
    const originalClick = input.click.bind(input);
    input.click = () => {
      clickCount += 1;
    };
    stage.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    if (sourceValueInput) {
      sourceValueInput.value =
        sourceValueInput.id === "rookieui-image-data" ? "data:image/png;base64,c291cmNl" : "img2img-stage-source";
      sourceValueInput.dispatchEvent(new Event("input", { bubbles: true }));
    }
    const interactionModeAfterBind = stage.dataset.interactionMode;
    const ariaLabelAfterBind = stage.getAttribute("aria-label");
    stage.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    stage.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    input.click = originalClick;
    return {
      clickCount,
      interactionModeAfterBind,
      ariaLabelAfterBind,
    };
  });
  expect(sourceStageRouting.clickCount).toBe(1);
  expect(sourceStageRouting.interactionModeAfterBind).toBe("edit");
  expect(sourceStageRouting.ariaLabelAfterBind).toBe("Img2Img source canvas editing surface");
  await page.locator("#rookieui-img2img-image-dropzone").hover();
  await expect(page.locator("#rookieui-img2img-source-upload .rookieui-shell__mini-action-icon")).toHaveText("📁");
  await expect(page.locator("#rookieui-img2img-source-remove .rookieui-shell__mini-action-icon")).toHaveText("🗑");
  await expect(page.locator("#rookieui-img2img-source-reset .rookieui-shell__mini-action-icon")).toHaveText("↺");
  await expect(page.locator("#rookieui-img2img-source-brush-toggle")).toBeVisible();
  await expect(page.locator("#rookieui-img2img-source-brush-width")).toHaveValue("25");
  await expect(page.locator("#rookieui-img2img-source-brush-opacity")).toHaveValue("100");
  await expect(page.locator("#rookieui-img2img-source-brush-softness")).toHaveValue("0");
  await expect(page.locator("#rookieui-img2img-source-undo")).toBeDisabled();
  await expect(page.locator("#rookieui-img2img-source-redo")).toBeDisabled();
  await page.locator("#rookieui-img2img-image-dropzone").hover();
  await page.locator("#rookieui-img2img-source-fullscreen").click();
  await expect
    .poll(async () =>
      page.evaluate(() =>
        document.fullscreenElement?.classList?.contains("rookieui-shell__canvas-upload-surface") ?? false,
      ),
    )
    .toBe(true);
  await expect(page.locator("#rookieui-img2img-status")).toContainText("entered fullscreen mode");
  await page.locator("#rookieui-img2img-image-dropzone").hover();
  await page.locator("#rookieui-img2img-source-fullscreen").click();
  await expect
    .poll(async () => page.evaluate(() => document.fullscreenElement === null))
    .toBe(true);
  await expect(page.locator("#rookieui-img2img-status")).toContainText("exited fullscreen mode");
  await page.locator("#rookieui-img2img-image-dropzone").hover();
  await page.locator("#rookieui-img2img-source-remove").click();
  await expect(page.locator("#rookieui-img2img-source-canvas-stage")).toHaveAttribute("data-interaction-mode", "upload");
  await expect(page.locator("#rookieui-img2img-source-undo")).toBeEnabled();
  await page.locator("#rookieui-img2img-image-dropzone").hover();
  await page.locator("#rookieui-img2img-source-undo").click();
  await expect(page.locator("#rookieui-img2img-source-canvas-stage")).toHaveAttribute("data-interaction-mode", "edit");
  await expect(page.locator("#rookieui-img2img-source-redo")).toBeEnabled();
  await page.locator("#rookieui-img2img-image-dropzone").hover();
  await page.locator("#rookieui-img2img-source-redo").click();
  await expect(page.locator("#rookieui-img2img-source-canvas-stage")).toHaveAttribute("data-interaction-mode", "upload");
  await page.locator("#rookieui-img2img-preset").selectOption("sd15");
  await page.locator("#rookieui-img2img-workspace-tab-lora").click();
  await page.locator("#rookieui-img2img-lora-item-0").click();
  await page.locator("#rookieui-img2img-workspace-tab-generation").click();
  await page.locator("#rookieui-img2img-controlnet-section").evaluate((details) => {
    details.open = true;
  });
  const img2imgRunPreprocessorButton = page.locator("#rookieui-img2img-controlnet-run-preprocessor-0");
  await expect(img2imgRunPreprocessorButton).toBeHidden();
  await expect(page.locator("#rookieui-img2img-controlnet-preview-upload-action-0")).toBeHidden();
  await page.locator("#rookieui-img2img-controlnet-preview-stage-0").hover();
  await expect(page.locator("#rookieui-img2img-controlnet-preview-upload-action-0")).toBeVisible();
  await expect(page.locator("#rookieui-img2img-controlnet-source-0-brush-toggle")).toBeVisible();
  await expect(page.locator("#rookieui-img2img-controlnet-source-0-brush-width")).toHaveValue("25");
  await expect(page.locator("#rookieui-img2img-controlnet-source-0-brush-opacity")).toHaveValue("100");
  await expect(page.locator("#rookieui-img2img-controlnet-source-0-brush-softness")).toHaveValue("0");
  await expect(
    page.locator("#rookieui-img2img-controlnet-run-preprocessor-0 .rookieui-shell__mini-action-icon"),
  ).toHaveText("💥");
  await expect(page.locator("#rookieui-img2img-controlnet-preview-stage-0")).toHaveAttribute(
    "data-interaction-mode",
    "upload",
  );
  const controlNetStageRouting = await page.evaluate(() => {
    const stage = document.getElementById("rookieui-img2img-controlnet-preview-stage-0");
    const input = document.getElementById("rookieui-img2img-controlnet-preview-image-upload-0");
    const imageData =
      document.getElementById("rookieui-img2img-controlnet-image-data-0") ??
      document.getElementById("rookieui-img2img-controlnet-image-asset-0");
    let clickCount = 0;
    const originalClick = input.click.bind(input);
    input.click = () => {
      clickCount += 1;
    };
    stage.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    if (imageData) {
      imageData.value =
        imageData.id === "rookieui-img2img-controlnet-image-data-0"
          ? "data:image/png;base64,Y250cmwtc291cmNl"
          : "controlnet-stage-source";
      imageData.dispatchEvent(new Event("input", { bubbles: true }));
    }
    const interactionModeAfterBind = stage.dataset.interactionMode;
    stage.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    stage.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    input.click = originalClick;
    return {
      clickCount,
      interactionModeAfterBind,
    };
  });
  expect(controlNetStageRouting.clickCount).toBe(1);
  expect(controlNetStageRouting.interactionModeAfterBind).toBe("edit");
  await page.locator("#rookieui-img2img-controlnet-image-data-0").evaluate((input) => {
    input.value = "data:image/png;base64,aW1hZ2UtY29udHJvbA==";
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await expect(img2imgRunPreprocessorButton).toBeVisible();
  await expect(img2imgRunPreprocessorButton).toHaveAttribute("title", "Run Preprocessor");
  // CRITICAL: this mock pins preprocessor output routing to generated-preview lane; source field must remain immutable.
  await page.evaluate(() => {
    if (window.__ROOKIEUI_ORIGINAL_FETCH__) {
      return;
    }
    window.__ROOKIEUI_ORIGINAL_FETCH__ = window.fetch.bind(window);
    window.fetch = async (input, init) => {
      const url = typeof input === "string" ? input : input?.url ?? "";
      if (url.includes("/rookieui/controlnet/detect")) {
        return new Response(JSON.stringify({ images: ["data:image/png;base64,cHJldmlldy1pbWFnZQ=="] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return window.__ROOKIEUI_ORIGINAL_FETCH__(input, init);
    };
  });
  await page.locator("#rookieui-img2img-controlnet-module-0").selectOption("depth");
  await page.locator("#rookieui-img2img-controlnet-allow-preview-0").check();
  const sourceBeforeRun = await page.locator("#rookieui-img2img-controlnet-image-data-0").inputValue();
  await img2imgRunPreprocessorButton.click();
  await expect(page.locator("#rookieui-img2img-controlnet-preview-generated-lane-0")).toBeVisible();
  await expect(page.locator("#rookieui-img2img-controlnet-preview-dual-pane-0")).toHaveAttribute(
    "data-generated-visible",
    "true",
  );
  await expect(page.locator("#rookieui-img2img-controlnet-image-data-0")).toHaveValue(sourceBeforeRun);
  await page.locator("#rookieui-img2img-controlnet-allow-preview-0").uncheck();
  await expect(page.locator("#rookieui-img2img-controlnet-preview-generated-lane-0")).toBeHidden();
  await expect(page.locator("#rookieui-img2img-controlnet-preview-dual-pane-0")).toHaveAttribute(
    "data-generated-visible",
    "false",
  );
  await page.evaluate(() => {
    if (!window.__ROOKIEUI_ORIGINAL_FETCH__) {
      return;
    }
    window.fetch = window.__ROOKIEUI_ORIGINAL_FETCH__;
    delete window.__ROOKIEUI_ORIGINAL_FETCH__;
  });
  await page.locator("#rookieui-img2img-controlnet-preview-stage-0").hover();
  await page.locator("#rookieui-img2img-controlnet-preview-remove-action-0").click();
  await expect(img2imgRunPreprocessorButton).toBeHidden();
  await page.locator("#rookieui-img2img-controlnet-preview-stage-0").hover();
  await page.locator("#rookieui-img2img-controlnet-preview-undo-action-0").click();
  await expect(img2imgRunPreprocessorButton).toBeVisible();
  await page.locator("#rookieui-img2img-controlnet-preview-stage-0").hover();
  await page.locator("#rookieui-img2img-controlnet-preview-redo-action-0").click();
  await expect(img2imgRunPreprocessorButton).toBeHidden();
  await page.locator("#rookieui-tab-txt2img").click();
  await page.locator("#rookieui-txt2img-controlnet-section").evaluate((details) => {
    details.open = true;
  });
  await expect(page.locator("#rookieui-txt2img-controlnet-run-preprocessor-0")).toBeVisible();
  await page.locator("#rookieui-tab-img2img").click();
  const img2imgModes = await page.locator("#rookieui-img2img-mode option").evaluateAll((options) =>
    options.map((option) => option.value),
  );
  expect(img2imgModes).toEqual(["img2img", "sketch", "inpaint", "inpaint_sketch", "inpaint_upload", "batch"]);
  await page.locator("#rookieui-img2img-mode").selectOption("batch");
  await expect(page.locator("#rookieui-img2img-batch-pane")).toBeVisible();
  await page.locator("#rookieui-img2img-mode").selectOption("img2img");
  await page.locator("#rookieui-img2img-mode").selectOption("inpaint");
  await page.locator("#rookieui-image-asset").fill("e2e-source-image");
  await page.locator("#rookieui-mask-asset").fill("e2e-mask-image");
  await expect(page.locator("#rookieui-img2img-generation-section #rookieui-img2img-hires-controls")).toHaveCount(1);
  await expect(page.locator("#rookieui-img2img-hires-controls")).toHaveClass(/rookieui-shell__section/);
  await expect(page.locator("#rookieui-img2img-hires-controls")).toHaveClass(/rookieui-shell__hires--integrated/);
  await expect(page.locator("#rookieui-img2img-hires-controls .rookieui-shell__hires-toggle")).toBeVisible();
  await page.locator("#rookieui-img2img-cfg-scale").fill("6.5");
  await page.locator("#rookieui-denoise-strength").fill("0.65");
  await page.locator("#rookieui-img2img-hires-enabled").check();
  await page.locator("#rookieui-img2img-hires-controls").evaluate((details) => {
    details.open = true;
  });
  await page.locator("#rookieui-img2img-hires-scale").fill("1.7");
  await page.locator("#rookieui-img2img-hires-steps").fill("10");
  await page.locator("#rookieui-img2img-hires-denoise").fill("0.4");
  await page.locator("#rookieui-img2img-form").evaluate((form) => {
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });
  await expect(page.locator("#rookieui-img2img-status")).toContainText("e2e-img2img-456");
  const img2imgRequests = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.img2img);
  expect(img2imgRequests).toHaveLength(1);
  expect(img2imgRequests[0]).toMatchObject({
    mode: "inpaint",
    image_asset: "e2e-source-image",
    mask_asset: "e2e-mask-image",
    dtype_profile: "automatic",
    cfg_scale: 6.5,
    denoise_strength: 0.65,
    hires_enabled: true,
    hires_scale: 1.7,
    hires_steps: 10,
    hires_denoise: 0.4,
    lora_name: "detail_tweaker.safetensors",
  });
  await page.locator("#rookieui-tab-txt2img").click();
  await expect(page.locator("#rookieui-cfg-scale")).toHaveValue("7.25");
  await page.locator("#rookieui-tab-img2img").click();
  await expect(page.locator("#rookieui-img2img-mode")).toHaveValue("inpaint");
  await page.locator("#rookieui-tab-pnginfo").click();
  await expect(page.locator("#rookieui-pane-pnginfo")).toBeVisible();
  const pngInfoPreviewIsFirstLeftSection = await page.evaluate(() => {
    const leftColumn = document.querySelector(
      "#rookieui-pane-pnginfo .rookieui-shell__workspace-grid--pnginfo .rookieui-shell__workspace-column",
    );
    const firstSection = leftColumn?.firstElementChild;
    return Boolean(firstSection?.querySelector("#rookieui-pnginfo-preview"));
  });
  expect(pngInfoPreviewIsFirstLeftSection).toBe(true);
  const pngInfoLayout = await page.evaluate(() => {
    const previewSection = document.querySelector("#rookieui-pnginfo-preview")?.closest("section");
    const metadataSection = document.querySelector("#rookieui-pnginfo-metadata")?.closest("section");
    const previewRect = previewSection?.getBoundingClientRect();
    const metadataRect = metadataSection?.getBoundingClientRect();
    const topDelta = Math.abs((previewRect?.top ?? 0) - (metadataRect?.top ?? 0));
    return {
      previewWidth: Math.round(previewRect?.width ?? 0),
      metadataWidth: Math.round(metadataRect?.width ?? 0),
      previewLeft: Math.round(previewRect?.left ?? 0),
      metadataLeft: Math.round(metadataRect?.left ?? 0),
      topDelta,
    };
  });
  expect(pngInfoLayout.previewWidth).toBeGreaterThanOrEqual(280);
  expect(pngInfoLayout.metadataWidth).toBeGreaterThanOrEqual(280);
  if (pngInfoLayout.topDelta <= 20) {
    expect(pngInfoLayout.previewLeft).toBeLessThan(pngInfoLayout.metadataLeft);
  }
  await expect(page.locator("#rookieui-pnginfo-input")).toHaveCount(0);
  await expect(page.locator("#rookieui-pnginfo-submit")).toHaveCount(0);
  const pngApplyHeights = await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll("#rookieui-pnginfo-apply-rail .rookieui-shell__button--apply"));
    return buttons.map((button) => Math.round(button.getBoundingClientRect().height));
  });
  expect(pngApplyHeights).toHaveLength(2);
  expect(Math.max(...pngApplyHeights)).toBeLessThanOrEqual(42);
  expect(Math.min(...pngApplyHeights)).toBeGreaterThanOrEqual(38);
  await page.setInputFiles("#rookieui-pnginfo-image-file", {
    name: "pnginfo.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7ZrY4AAAAASUVORK5CYII=",
      "base64",
    ),
  });
  await expect(page.locator("#rookieui-pnginfo-status")).toContainText("Ready to apply txt2img fields");
  await page.locator("#rookieui-pnginfo-apply-txt2img").click();
  await expect(page.locator("#rookieui-pnginfo-status")).toContainText("Applied txt2img fields");
  await page.locator("#rookieui-tab-txt2img").click();
  await expect(page.locator("#rookieui-prompt")).toHaveValue("e2e imported prompt");
  await expect(page.locator("#rookieui-width")).toHaveValue("768");
  await page.locator("#rookieui-tab-pnginfo").click();
  await expect(page.locator("#rookieui-pnginfo-unsupported")).toContainText("ENSD");
  await expect(page.locator("#rookieui-pnginfo-metadata")).toContainText("e2e imported prompt");
  await expect(page.locator("#rookieui-pnginfo-metadata")).toContainText("e2e imported negative");
  await page.locator("#rookieui-tab-queue").click();
  await expect(page.locator("#rookieui-queue-remaining")).toContainText("1");
  await page.locator("#rookieui-reuse-img2img-0").click();
  await expect(page.locator("#rookieui-queue-status")).toContainText("Applied history-image.png to img2img");
  await page.locator("#rookieui-tab-img2img").click();
  await expect(page.locator("#rookieui-image-asset")).toHaveValue("history-image.png");
  await page.locator("#rookieui-tab-extras").click();
  await expect(page.locator("#rookieui-pane-extras")).toBeVisible();
  await page.locator("#rookieui-extras-mode-single").click();
  await expect(page.locator("#rookieui-extras-single-pane")).toBeVisible();
  await page.setInputFiles("#rookieui-extras-single-file", {
    name: "extras.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7ZrY4AAAAASUVORK5CYII=",
      "base64",
    ),
  });
  await page.locator("#rookieui-extras-submit").click();
  await expect(page.locator("#rookieui-extras-status")).toContainText("Generated 1 extras output");
  const extrasRequests = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.extras);
  expect(extrasRequests).toHaveLength(1);
  expect(extrasRequests[0].mode).toBe("single_image");
  await expect(page.locator(".rookieui-shell__footer")).toContainText("host: standalone-web");
});
