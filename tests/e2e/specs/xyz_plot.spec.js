const { test, expect } = require("@playwright/test");

test("renders XYZ Plot at the bottom of txt2img and img2img and runs a sweep", async ({ page }) => {
  await page.goto("test-harness.html");

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
  await page.locator("#rookieui-txt2img-xyz-plot-axis-z-select").selectOption("checkpoint_name");
  await expect(page.locator("#rookieui-txt2img-xyz-plot-axis-z-values-multiselect")).toBeVisible();
  await expect(page.locator("#rookieui-txt2img-xyz-plot-axis-z-values")).toBeHidden();
  const txt2imgCheckpointChoices = await page
    .locator("#rookieui-txt2img-xyz-plot-axis-z-values-options input")
    .evaluateAll((nodes) => nodes.map((node) => node.value).slice(0, 2));
  await page.locator("#rookieui-txt2img-xyz-plot-axis-z-values-summary").click();
  await page.locator(`#rookieui-txt2img-xyz-plot-axis-z-values-options input[value="${txt2imgCheckpointChoices[0]}"]`).check();
  await page.locator(`#rookieui-txt2img-xyz-plot-axis-z-values-options input[value="${txt2imgCheckpointChoices[1]}"]`).check();
  await page.locator("#rookieui-txt2img-xyz-plot-axis-x-values").fill("20, 28, 36");
  await page.locator("#rookieui-txt2img-xyz-plot-axis-y-values").fill("5.5, 7, 8.5");
  await page.locator("#rookieui-txt2img-xyz-plot-estimate").click();
  await expect(page.locator("#rookieui-txt2img-xyz-plot-section")).toContainText("9");

  await page.locator("#rookieui-txt2img-xyz-plot-run").click();
  await expect(page.locator("#rookieui-txt2img-xyz-plot-session-status")).toContainText("in_progress");
  await page.locator("#rookieui-txt2img-xyz-plot-refresh").click();
  await expect(page.locator("#rookieui-txt2img-xyz-plot-main-grid-preview img")).toBeVisible();

  const txt2imgRunRequests = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.xyzPlot.run);
  expect(txt2imgRunRequests).toHaveLength(1);
  expect(txt2imgRunRequests[0].mode).toBe("txt2img");
  expect(typeof txt2imgRunRequests[0].client_id).toBe("string");
  expect(txt2imgRunRequests[0].axes).toEqual([
    { axis_id: "steps", values: "20, 28, 36" },
    { axis_id: "cfg_scale", values: "5.5, 7, 8.5" },
    { axis_id: "checkpoint_name", values: txt2imgCheckpointChoices.join(", ") },
  ]);

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

  const allRunRequests = await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.xyzPlot.run);
  expect(allRunRequests).toHaveLength(2);
  expect(allRunRequests[1].mode).toBe("img2img");
  expect(allRunRequests[1].axes).toEqual([
    { axis_id: "steps", values: "1, 2, 3" },
    { axis_id: "denoising_strength", values: "0.35, 0.55, 0.75" },
  ]);
});
