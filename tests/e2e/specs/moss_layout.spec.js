const { test, expect } = require("@playwright/test");
const path = require("node:path");

async function capture(page, testInfo, name) {
  const folder = process.env.ROOKIEUI_VISUAL_EVIDENCE_DIR;
  const image = await page.locator("#rookieui-moss-controls").screenshot(folder ? { path: path.join(folder, `${name}-1440x1000.png`) } : {});
  await testInfo.attach(name, { body: image, contentType: "image/png" });
}
const rows = page => page.locator("[data-layout-row]");
const field = (row, name) => row.locator(`[data-layout-field="${name}"]`);

test("Layout CRUD, sizing, invalid draft remount, explicit SLG and actual submissions stay aligned", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("test-harness.html");
  await page.locator("#rookieui-preset").selectOption("moss_image_sft");
  await page.locator("#rookieui-prompt").fill("synthetic ordered layout 中文");
  await expect(page.locator("#rookieui-moss-slg-enabled")).not.toBeChecked();
  await capture(page, testInfo, "layout-baseline");
  await page.locator("#rookieui-moss-layout-enabled").check();
  await expect(page.locator("#rookieui-moss-slg-enabled")).toBeChecked();
  await page.locator("#rookieui-moss-layout-enabled").uncheck();
  await expect(page.locator("#rookieui-moss-slg-enabled")).not.toBeChecked();
  await page.locator("#rookieui-moss-layout-enabled").check();
  await page.locator("#rookieui-moss-layout-add").click();
  await field(rows(page).nth(0), "kind").selectOption("text");
  await field(rows(page).nth(0), "caption").fill("synthetic text caption");
  await field(rows(page).nth(0), "text").fill("<script>literal</script>\n字");
  for (const [key, value] of Object.entries({ y0: "0", x0: "0", y1: "500", x1: "1000", palette: "#abcdef, #123456" })) {
    await field(rows(page).nth(0), key).fill(value);
  }
  await page.locator("#rookieui-moss-layout-add").click();
  await field(rows(page).nth(1), "kind").selectOption("character");
  await field(rows(page).nth(1), "caption").fill("synthetic character");
  await rows(page).nth(1).locator('[data-layout-action="up"]').click();
  await expect(field(rows(page).nth(0), "caption")).toHaveValue("synthetic character");
  await page.locator("#rookieui-width").fill("768");
  await page.locator("#rookieui-height").fill("512");
  await expect(page.locator("#rookieui-moss-layout-preview")).toHaveAttribute("viewBox", "0 0 768 512");
  await expect(page.locator("[data-layout-preview-box]")).toHaveCount(2);
  await expect(page.locator("#rookieui-moss-layout script")).toHaveCount(0);
  await page.locator("#rookieui-txt2img-submit").click();
  await expect.poll(() => page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img.length)).toBe(1);
  expect(await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img[0])).toMatchObject({ width: 768, height: 512,
    moss_options: { slg_enabled: true, layout: { enabled: true, elements: [
      { kind: "character", caption: "synthetic character" },
      { kind: "text", text: "<script>literal</script>\n字", bbox: [0, 0, 500, 1000], palette: ["#abcdef", "#123456"] },
    ] } } });
  await field(rows(page).nth(1), "y0").fill("1000");
  await expect(page.locator("#rookieui-txt2img-submit")).toBeDisabled();
  await expect(page.locator("#rookieui-moss-layout-error")).toContainText("bbox");
  await capture(page, testInfo, "layout-invalid");
  await page.locator("#rookieui-prompt").press("Control+Enter");
  expect(await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img.length)).toBe(1);
  await page.evaluate(() => window.__ROOKIEUI_E2E_APP__.extensionManager.activeSidebarTab.destroy());
  await page.evaluate(() => window.__ROOKIEUI_E2E_APP__.extensionManager.activeSidebarTab.render(document.getElementById("mock-sidebar-tabs")));
  await expect(field(rows(page).nth(1), "y0")).toHaveValue("1000");
  await expect(field(rows(page).nth(1), "text")).toHaveValue("<script>literal</script>\n字");
  await expect(page.locator("#rookieui-txt2img-submit")).toBeDisabled();
  await field(rows(page).nth(1), "y0").fill("0");
  await page.locator("#rookieui-moss-slg-enabled").uncheck();
  await page.locator("#rookieui-moss-layout-enabled").uncheck();
  await page.locator("#rookieui-moss-layout-enabled").check();
  await expect(page.locator("#rookieui-moss-slg-enabled")).not.toBeChecked();
  await rows(page).nth(0).locator('[data-layout-action="delete"]').click();
  await expect(rows(page)).toHaveCount(1);
  await expect(page.locator("[data-layout-preview-box]")).toHaveCount(1);
  await expect(page.locator("#rookieui-txt2img-submit")).toBeEnabled();
  await page.evaluate(() => window.__ROOKIEUI_E2E_APP__.extensionManager.activeSidebarTab.destroy());
  await page.evaluate(() => window.__ROOKIEUI_E2E_APP__.extensionManager.activeSidebarTab.render(document.getElementById("mock-sidebar-tabs")));
  await expect(page.locator("#rookieui-moss-layout-enabled")).toBeChecked();
  await expect(page.locator("#rookieui-moss-slg-enabled")).not.toBeChecked();
  await expect(field(rows(page).nth(0), "text")).toHaveValue("<script>literal</script>\n字");
  await capture(page, testInfo, "layout-current");
  await page.locator("#rookieui-txt2img-submit").click();
  await expect.poll(() => page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img.length)).toBe(2);
  expect(await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img[1].moss_options)).toMatchObject({ slg_enabled: false,
    layout: { elements: [{ kind: "text", bbox: [0, 0, 500, 1000] }] } });
  await page.locator("#rookieui-preset").selectOption("sd15");
  await expect(page.locator("#rookieui-moss-controls")).toBeHidden();
  await expect(page.locator("#rookieui-txt2img-submit")).toBeEnabled();
  expect(errors).toEqual([]);
});

test("PNG Info restores original Layout text, palette and explicit SLG with txt2img-only transfer", async ({ page }) => {
  await page.goto("test-harness.html?mossPng=1&mossLayout=1");
  await page.locator("#rookieui-tab-pnginfo").click();
  await page.locator("#rookieui-pnginfo-image-file").setInputFiles({ name: "synthetic.png", mimeType: "image/png",
    buffer: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lxkAAAAASUVORK5CYII=", "base64") });
  await expect(page.locator("#rookieui-pnginfo-apply-img2img")).toBeDisabled();
  await page.locator("#rookieui-pnginfo-apply-txt2img").click();
  await expect(page.locator("#rookieui-moss-layout-enabled")).toBeChecked();
  await expect(field(rows(page).nth(0), "text")).toHaveValue("還原\ntext");
  await expect(field(rows(page).nth(0), "palette")).toHaveValue("#abcdef");
  await expect(page.locator("#rookieui-moss-slg-enabled")).toBeChecked();
  await page.locator("#rookieui-txt2img-submit").click();
  await expect.poll(() => page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img.length)).toBe(1);
  expect(await page.evaluate(() => window.__ROOKIEUI_E2E_REQUESTS__.txt2img[0])).toMatchObject({ profile: "moss_image_sft", seed: 321,
    moss_options: { slg_enabled: true, layout: { enabled: true, elements: [{ text: "還原\ntext", bbox: [100, 200, 800, 900] }] } } });
});
