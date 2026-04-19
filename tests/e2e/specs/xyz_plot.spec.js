const { test, expect } = require("@playwright/test");

test("renders XYZ Plot at the bottom of txt2img and img2img and runs a sweep", async ({ page }) => {
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

  await expect(page.locator("#rookieui-txt2img-xyz-plot-section")).toBeVisible();
  await expect(page.locator("#rookieui-txt2img-xyz-plot-section")).not.toHaveAttribute("open", "");
  const txt2imgLayout = await page.evaluate(() => {
    const generationSection = document.getElementById("rookieui-txt2img-generation-section");
    const xyzSection = document.getElementById("rookieui-txt2img-xyz-plot-section");
    const form = document.getElementById("rookieui-txt2img-form");
    return {
      generationBottom: generationSection?.getBoundingClientRect().bottom ?? 0,
      xyzTop: xyzSection?.getBoundingClientRect().top ?? 0,
      xyzIndex: Array.from(form?.children ?? []).indexOf(xyzSection),
      subtabIndex: Array.from(form?.children ?? []).indexOf(document.querySelector("#rookieui-txt2img-form .rookieui-shell__workspace-frame")),
    };
  });
  expect(txt2imgLayout.xyzTop).toBeGreaterThanOrEqual(txt2imgLayout.generationBottom);
  expect(txt2imgLayout.xyzIndex).toBeGreaterThan(txt2imgLayout.subtabIndex);

  await page.locator("#rookieui-txt2img-xyz-plot-section > summary").click();
  await expect(page.locator("#rookieui-txt2img-xyz-plot-section")).toHaveAttribute("open", "");
  const controlSurfaceMetrics = await page.evaluate(() => {
    const optionLabel = document.querySelector("#rookieui-txt2img-xyz-plot-draw-legend + span");
    const marginLabel = document.querySelector("#rookieui-txt2img-xyz-plot-margin-size")?.closest("label")?.querySelector(".rookieui-shell__field-label");
    const actionRow = document.querySelector("#rookieui-txt2img-xyz-plot-section .rookieui-shell__xyz-plot-actions");
    const xyzSection = document.getElementById("rookieui-txt2img-xyz-plot-section");
    const estimateButton = document.getElementById("rookieui-txt2img-xyz-plot-estimate");
    const runButton = document.getElementById("rookieui-txt2img-xyz-plot-run");
    const refreshButton = document.getElementById("rookieui-txt2img-xyz-plot-refresh");
    const cancelButton = document.getElementById("rookieui-txt2img-xyz-plot-cancel");
    const generateButton = document.getElementById("rookieui-txt2img-submit");
    const actionButtons = [estimateButton, refreshButton, runButton, cancelButton];
    const actionRects = actionButtons.map((button) => button?.getBoundingClientRect() ?? null);
    const rowRect = actionRow?.getBoundingClientRect() ?? null;
    return {
      optionFont: optionLabel ? getComputedStyle(optionLabel).fontSize : "",
      marginFont: marginLabel ? getComputedStyle(marginLabel).fontSize : "",
      notePresent: Boolean(
        Array.from(xyzSection?.querySelectorAll(".rookieui-shell__xyz-plot-note") ?? []).some(
          (node) => node.textContent?.includes("Bottom-mounted sweep surface"),
        ),
      ),
      borderStyle: xyzSection ? getComputedStyle(xyzSection).borderStyle : "",
      generateBackgroundImage: generateButton ? getComputedStyle(generateButton).backgroundImage : "",
      generateColor: generateButton ? getComputedStyle(generateButton).color : "",
      estimateBackgroundImage: estimateButton ? getComputedStyle(estimateButton).backgroundImage : "",
      estimateClassName: estimateButton?.className ?? "",
      refreshBackgroundImage: refreshButton ? getComputedStyle(refreshButton).backgroundImage : "",
      refreshClassName: refreshButton?.className ?? "",
      cancelBackgroundImage: cancelButton ? getComputedStyle(cancelButton).backgroundImage : "",
      cancelBorderColor: cancelButton ? getComputedStyle(cancelButton).borderColor : "",
      cancelColor: cancelButton ? getComputedStyle(cancelButton).color : "",
      actionLabels: Array.from(actionRow?.querySelectorAll("button") ?? []).map((button) => button.textContent?.trim() ?? ""),
      actionWidths: actionRects.map((rect) => rect?.width ?? 0),
      rowLeftDelta: rowRect && actionRects[0] ? Math.abs(actionRects[0].left - rowRect.left) : 999,
      rowRightDelta: rowRect && actionRects[3] ? Math.abs(rowRect.right - actionRects[3].right) : 999,
    };
  });
  expect(controlSurfaceMetrics.optionFont).toBe(controlSurfaceMetrics.marginFont);
  expect(controlSurfaceMetrics.notePresent).toBe(false);
  expect(controlSurfaceMetrics.borderStyle).toBe("solid");
  expect(controlSurfaceMetrics.actionLabels).toEqual(["Estimate", "Refresh", "Run XYZ Plot", "Cancel Session"]);
  expect(controlSurfaceMetrics.estimateClassName).toContain("rookieui-shell__xyz-plot-action--estimate");
  expect(controlSurfaceMetrics.refreshClassName).toContain("rookieui-shell__xyz-plot-action--refresh");
  expect(controlSurfaceMetrics.estimateBackgroundImage).toContain("25, 135, 84");
  expect(controlSurfaceMetrics.refreshBackgroundImage).toContain("43, 124, 220");
  expect(controlSurfaceMetrics.cancelBackgroundImage).not.toBe(controlSurfaceMetrics.generateBackgroundImage);
  expect(controlSurfaceMetrics.cancelBackgroundImage).toContain("219, 0, 0");
  expect(controlSurfaceMetrics.cancelBorderColor).toBe("rgb(255, 18, 0)");
  expect(controlSurfaceMetrics.cancelColor).toBe(controlSurfaceMetrics.generateColor);
  expect(Math.max(...controlSurfaceMetrics.actionWidths) - Math.min(...controlSurfaceMetrics.actionWidths)).toBeLessThanOrEqual(1);
  expect(controlSurfaceMetrics.rowLeftDelta).toBeLessThanOrEqual(1);
  expect(controlSurfaceMetrics.rowRightDelta).toBeLessThanOrEqual(1);
  await page.locator("#rookieui-txt2img-xyz-plot-axis-z-select").selectOption("checkpoint_name");
  await expect(page.locator("#rookieui-txt2img-xyz-plot-axis-z-values-multiselect")).toBeVisible();
  await expect(page.locator("#rookieui-txt2img-xyz-plot-axis-z-values")).toBeHidden();
  const txt2imgCheckpointChoices = await page
    .locator("#rookieui-txt2img-xyz-plot-axis-z-values-options input")
    .evaluateAll((nodes) => nodes.map((node) => node.value).slice(0, 2));
  await page.locator("#rookieui-txt2img-xyz-plot-axis-z-values-summary").click();
  const choicePanelLayout = await page.evaluate(() => {
    const summary = document.getElementById("rookieui-txt2img-xyz-plot-axis-z-values-summary");
    const panel = document.querySelector("#rookieui-txt2img-xyz-plot-axis-z-values-multiselect .rookieui-shell__xyz-plot-choice-panel");
    const optionText = document.querySelector("#rookieui-txt2img-xyz-plot-axis-z-values-options .rookieui-shell__xyz-plot-choice-option-text");
    const select = document.getElementById("rookieui-txt2img-xyz-plot-axis-z-select");
    const summaryRect = summary?.getBoundingClientRect();
    const panelRect = panel?.getBoundingClientRect();
    return {
      summaryWidth: summaryRect?.width ?? 0,
      panelWidth: panelRect?.width ?? 0,
      summaryFont: summary ? getComputedStyle(summary).fontSize : "",
      panelFont: panel ? getComputedStyle(panel).fontSize : "",
      selectFont: select ? getComputedStyle(select).fontSize : "",
      optionWrap: optionText ? getComputedStyle(optionText).overflowWrap : "",
    };
  });
  expect(choicePanelLayout.panelWidth).toBeGreaterThanOrEqual(choicePanelLayout.summaryWidth);
  expect(choicePanelLayout.summaryFont).toBe(choicePanelLayout.selectFont);
  expect(choicePanelLayout.panelFont).toBe(choicePanelLayout.selectFont);
  expect(choicePanelLayout.optionWrap).toBe("anywhere");
  await expect(page.locator("#rookieui-txt2img-xyz-plot-axis-z-values-multiselect")).toHaveAttribute("open", "");
  await page.locator("#rookieui-title").click();
  await expect(page.locator("#rookieui-txt2img-xyz-plot-axis-z-values-multiselect")).not.toHaveAttribute("open", "");
  await page.locator("#rookieui-txt2img-xyz-plot-axis-z-values-summary").click();
  await expect(page.locator("#rookieui-txt2img-xyz-plot-axis-z-values-multiselect")).toHaveAttribute("open", "");
  await page.keyboard.press("Escape");
  await expect(page.locator("#rookieui-txt2img-xyz-plot-axis-z-values-multiselect")).not.toHaveAttribute("open", "");
  await page.locator("#rookieui-txt2img-xyz-plot-axis-z-fill").click();
  await expect(page.locator("#rookieui-txt2img-xyz-plot-axis-z-values-options input:checked")).toHaveCount(txt2imgCheckpointChoices.length);
  await page.locator("#rookieui-txt2img-xyz-plot-axis-z-fill").click();
  await expect(page.locator("#rookieui-txt2img-xyz-plot-axis-z-values-options input:checked")).toHaveCount(0);
  await page.locator("#rookieui-txt2img-xyz-plot-axis-z-values-summary").click();
  await page.locator(`#rookieui-txt2img-xyz-plot-axis-z-values-options input[value="${txt2imgCheckpointChoices[0]}"]`).check();
  await page.locator(`#rookieui-txt2img-xyz-plot-axis-z-values-options input[value="${txt2imgCheckpointChoices[1]}"]`).check();
  await page.locator("#rookieui-txt2img-xyz-plot-axis-x-values").fill("20, 28, 36");
  await page.locator("#rookieui-txt2img-xyz-plot-axis-y-values").fill("5.5, 7, 8.5");
  await page.locator("#rookieui-txt2img-xyz-plot-keep-negative-one-seed").check();
  await page.locator("#rookieui-txt2img-xyz-plot-vary-seeds-y").check();
  await page.locator("#rookieui-txt2img-xyz-plot-estimate").click();
  await expect(page.locator("#rookieui-txt2img-xyz-plot-section")).toContainText("9");

  await page.locator("#rookieui-txt2img-xyz-plot-run").click();
  await expect(page.locator("#rookieui-txt2img-xyz-plot-session-status")).toContainText("in_progress");
  await page.locator("#rookieui-txt2img-xyz-plot-refresh").click();
  await expect(page.locator("#rookieui-txt2img-xyz-plot-main-grid-preview img")).toBeVisible();
  await expect(page.locator("#rookieui-txt2img-preview img")).toBeVisible();
  await expect(page.locator("#rookieui-txt2img-xyz-plot-preview-fullscreen")).toBeVisible();
  await page.locator("#rookieui-txt2img-xyz-plot-preview-fullscreen").click();
  await expect
    .poll(async () =>
      page.evaluate(() =>
        document.fullscreenElement?.classList?.contains("rookieui-shell__preview-surface") ?? false,
      ),
    )
    .toBe(true);
  await expect(page.locator("#rookieui-txt2img-xyz-plot-fullscreen-zoom")).toBeVisible();
  await page.locator("#rookieui-txt2img-xyz-plot-preview-fullscreen").click();
  await expect
    .poll(async () => page.evaluate(() => document.fullscreenElement === null))
    .toBe(true);

  const txt2imgRunRequests = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.xyzPlot.run);
  expect(txt2imgRunRequests).toHaveLength(1);
  expect(txt2imgRunRequests[0].mode).toBe("txt2img");
  expect(typeof txt2imgRunRequests[0].client_id).toBe("string");
  expect(txt2imgRunRequests[0].axes).toEqual([
    { axis_id: "steps", values: "20, 28, 36" },
    { axis_id: "cfg_scale", values: "5.5, 7, 8.5" },
    { axis_id: "checkpoint_name", values: txt2imgCheckpointChoices.join(", ") },
  ]);
  expect(txt2imgRunRequests[0].keep_negative_one_seed).toBe(true);
  expect(txt2imgRunRequests[0].vary_seeds_x).toBe(false);
  expect(txt2imgRunRequests[0].vary_seeds_y).toBe(true);
  expect(txt2imgRunRequests[0].vary_seeds_z).toBe(false);

  await page.locator("#rookieui-tab-img2img").click();
  await expect(page.locator("#rookieui-img2img-xyz-plot-section")).toBeVisible();
  await expect(page.locator("#rookieui-img2img-xyz-plot-section")).not.toHaveAttribute("open", "");
  const img2imgLayout = await page.evaluate(() => {
    const generationSection = document.getElementById("rookieui-img2img-generation-section");
    const xyzSection = document.getElementById("rookieui-img2img-xyz-plot-section");
    const form = document.getElementById("rookieui-img2img-form");
    return {
      generationBottom: generationSection?.getBoundingClientRect().bottom ?? 0,
      xyzTop: xyzSection?.getBoundingClientRect().top ?? 0,
      xyzIndex: Array.from(form?.children ?? []).indexOf(xyzSection),
      subtabIndex: Array.from(form?.children ?? []).indexOf(document.querySelector("#rookieui-img2img-form .rookieui-shell__workspace-frame")),
    };
  });
  expect(img2imgLayout.xyzTop).toBeGreaterThanOrEqual(img2imgLayout.generationBottom);
  expect(img2imgLayout.xyzIndex).toBeGreaterThan(img2imgLayout.subtabIndex);

  await page.locator("#rookieui-img2img-xyz-plot-section > summary").click();
  await expect(page.locator("#rookieui-img2img-xyz-plot-section")).toHaveAttribute("open", "");
  await page.locator("#rookieui-img2img-xyz-plot-axis-y-select").selectOption("denoising_strength");
  await page.locator("#rookieui-img2img-xyz-plot-axis-x-values").fill("1, 2, 3");
  await page.locator("#rookieui-img2img-xyz-plot-axis-y-values").fill("0.35, 0.55, 0.75");
  await page.locator("#rookieui-img2img-xyz-plot-axis-z-select").selectOption("");
  await page.locator("#rookieui-img2img-xyz-plot-run").click();
  await page.locator("#rookieui-img2img-xyz-plot-refresh").click();
  await expect(page.locator("#rookieui-img2img-xyz-plot-main-grid-preview img")).toBeVisible();
  await expect(page.locator("#rookieui-img2img-preview img")).toBeVisible();

  const allRunRequests = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.xyzPlot.run);
  expect(allRunRequests).toHaveLength(2);
  expect(allRunRequests[1].mode).toBe("img2img");
  expect(allRunRequests[1].axes).toEqual([
    { axis_id: "steps", values: "1, 2, 3" },
    { axis_id: "denoising_strength", values: "0.35, 0.55, 0.75" },
  ]);
  expect(allRunRequests[1].keep_negative_one_seed).toBe(false);
  expect(allRunRequests[1].vary_seeds_x).toBe(false);
  expect(allRunRequests[1].vary_seeds_y).toBe(false);
  expect(allRunRequests[1].vary_seeds_z).toBe(false);
});
