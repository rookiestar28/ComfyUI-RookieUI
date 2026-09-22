/**
 * Live RookieUI Qwen Image 2.1 sidebar qualification with private, content-free evidence.
 *
 * Usage: node scripts/run_qwen21_live_ui.mjs --config <host-config.json> --output <result.json>
 * The execute-phase result `<host>-execute.json` and its image directory must sit next to the output.
 * Edit-pane request checks are rewritten to dry-run in the browser route so they never enqueue.
 */

import { createHash } from "node:crypto";
import { closeSync, existsSync, mkdirSync, openSync, readFileSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

export const RESULT_SCHEMA = "Qwen21LiveUIV1";
const CONFIG_SCHEMA = "Qwen21HostConfigV1";
const EXECUTE_SCHEMA = "Qwen21HostQualificationV1";
const CASE_ID = "Q21-REMOVE-BG";
// Git object IDs are SHA-1 here (40 hex); file digests are SHA-256 (64 hex).
const GIT_OBJECT_ID = /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/;
const SHA256 = /^[0-9a-f]{64}$/;
const HANDLE = /^[A-Za-z0-9_-]{1,64}\.(?:png|jpg|webp)$/;
const BACKGROUND_INSTRUCTION = "Remove the background from <image1> and keep the subject with transparent alpha.";
const CONFIRM_MESSAGE = "Replace the current edit instruction?";
const UI_PROMPT = "A single flat red circle centered on a plain white background, simple vector illustration, no text.";
const EDIT_PROMPT = "Place a small copy of the red circle from <image2> at the center of the triangle in <image1>.";
const GENERATION_TIMEOUT_MS = 10 * 60 * 1000;

const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");

export function safeError(code) {
  const error = new Error(code);
  error.code = code;
  return error;
}

function readJson(path, code = "json_unreadable") {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    throw safeError(code);
  }
}

export function parseOptions(argv) {
  const values = {};
  if (argv.length !== 4) throw safeError("arguments_invalid");
  for (let index = 0; index < argv.length; index += 2) {
    if (!["--config", "--output"].includes(argv[index]) || !argv[index + 1] || values[argv[index].slice(2)]) {
      throw safeError("arguments_invalid");
    }
    values[argv[index].slice(2)] = argv[index + 1];
  }
  return values;
}

export function validateConfig(raw) {
  if (raw?.schema !== CONFIG_SCHEMA || !["H1", "H2"].includes(raw.host)) throw safeError("config_schema");
  let url;
  try {
    url = new URL(raw.base_url);
  } catch {
    throw safeError("config_url");
  }
  if (url.protocol !== "http:" || url.hostname !== "127.0.0.1" || url.port !== "8188" || url.username || url.password
      || url.search || url.hash || !["", "/"].includes(url.pathname)) {
    throw safeError("config_url");
  }
  if (!GIT_OBJECT_ID.test(raw.candidate_tree ?? "")) throw safeError("config_candidate");
  if (!SHA256.test(raw.frontend_index_sha256 ?? "")) throw safeError("config_frontend");
  for (const key of ["fixture_manifest", "rookieui_install_root"]) {
    if (typeof raw[key] !== "string" || !raw[key]) throw safeError("config_paths");
  }
  const selectors = {};
  for (const role of ["diffusion_bf16", "encoder_int8", "vae_bf16"]) {
    const selector = raw.models?.[role]?.selector;
    if (typeof selector !== "string" || !selector) throw safeError("config_models");
    selectors[role] = selector;
  }
  return {
    host: raw.host, base_url: url.origin, candidate_tree: raw.candidate_tree,
    frontend_index_sha256: raw.frontend_index_sha256, fixture_manifest: raw.fixture_manifest,
    rookieui_install_root: raw.rookieui_install_root, selectors,
  };
}

export function selectedJob(config, report) {
  if (report?.schema !== EXECUTE_SCHEMA || report.host !== config.host || report.phase !== "execute"
      || report.candidate_tree !== config.candidate_tree || report.served_frontend_digest !== config.frontend_index_sha256
      || report.status !== "PENDING_REVIEW") {
    throw safeError("execute_identity_mismatch");
  }
  const row = report.cases?.find((item) => item.case_id === CASE_ID);
  if (!row || row.selected !== true || row.child_exit !== 0 || row.status !== "PENDING_REVIEW" || row.original_decoded !== true
      || row.history_matched !== true || row.terminal_status !== "completed" || !SHA256.test(row.original_sha256 ?? "")
      || !/^[0-9a-fA-F-]{20,80}$/.test(row.prompt_id ?? "") || !/^rookieui-q21-[0-9a-f]{32}$/.test(row.client_id ?? "")
      || !HANDLE.test(row.output_handle ?? "")) {
    throw safeError("selected_job_unqualified");
  }
  return row;
}

export function dataUrlBytes(value) {
  const match = /^data:image\/[a-z0-9.+-]+;base64,(.+)$/i.exec(String(value ?? ""));
  if (!match) throw safeError("data_url_invalid");
  return Buffer.from(match[1], "base64");
}

function fixtureBytes(config, fixtureId) {
  const entries = readJson(config.fixture_manifest, "fixture_manifest_invalid");
  const entry = Array.isArray(entries) ? entries.find((item) => item?.id === fixtureId) : null;
  if (!entry || basename(entry.filename ?? "") !== entry.filename) throw safeError("fixture_entry_invalid");
  const bytes = readFileSync(join(dirname(config.fixture_manifest), entry.filename));
  if (sha256(bytes) !== entry.sha256) throw safeError("fixture_image_mismatch");
  return bytes;
}

function hostInputSha(config, handle) {
  if (!HANDLE.test(handle ?? "")) throw safeError("asset_handle_shape");
  const path = join(config.rookieui_install_root, ".rookieui_runtime", "input", handle);
  if (!existsSync(path)) throw safeError("asset_handle_missing");
  return sha256(readFileSync(path));
}

async function hostJson(config, path) {
  const response = await fetch(new URL(path, config.base_url));
  if (response.status !== 200) throw safeError("host_http_status");
  return response.json();
}

async function jobFor(config, promptId, clientId) {
  const url = new URL(`/rookieui/queue/${encodeURIComponent(promptId)}`, config.base_url);
  url.searchParams.set("client_id", clientId);
  return (await hostJson(config, url.pathname + url.search)).job ?? null;
}

async function openSidebar(page) {
  const shell = page.locator("#rookieui-shell-tabs");
  if (await shell.count() && await shell.first().isVisible()) return;
  await toggleSidebar(page);
  await shell.first().waitFor({ state: "visible", timeout: 30000 });
}

async function toggleSidebar(page) {
  const button = page.locator('[data-testid="rookieui-tab-button"], .rookieui-tab-button, #rookieui-legacy-launcher');
  if (await button.count() !== 1) throw safeError("sidebar_launcher_ambiguous");
  await button.click();
}

async function capture(page, dir, name, selector) {
  const target = page.locator(selector).first();
  await target.waitFor({ state: "visible", timeout: 15000 });
  const path = join(dir, `${name}.png`);
  await target.screenshot({ path, animations: "disabled" });
  return sha256(readFileSync(path));
}

async function selectIfPresent(page, selector, value) {
  const select = page.locator(selector);
  if (await select.locator(`option[value="${value.replaceAll("\\", "\\\\").replaceAll('"', '\\"')}"]`).count()) {
    await select.selectOption(value);
  }
  if (await select.inputValue() !== value) throw safeError(`model_selector_unavailable_${selector.slice(1).replaceAll("-", "_")}`);
}

async function inputBytes(page, selector) {
  return dataUrlBytes(await page.locator(selector).inputValue());
}

async function dryRunEditRequest(page, state) {
  const responsePromise = page.waitForResponse(
    (response) => /\/rookieui\/generate\/img2img$/.test(new URL(response.url()).pathname) && response.request().method() === "POST",
    { timeout: 60000 },
  );
  await page.locator("#rookieui-img2img-submit").click();
  const response = await responsePromise;
  if (response.status() !== 200) throw safeError("edit_dry_run_rejected");
  const body = await response.json();
  if (body?.submission?.mode !== "dry-run") throw safeError("edit_request_not_dry_run");
  return { request: state.lastEditRequest, response: body };
}

function encoderInputs(workflow) {
  const node = Object.values(workflow ?? {}).find((item) => item?.class_type === "TextEncodeQwenImage21");
  if (!node) throw safeError("encoder_missing");
  return node.inputs;
}

async function runUiGeneration(page, config, checks, evidence) {
  await page.locator("#rookieui-tab-txt2img").click();
  await page.locator("#rookieui-preset").selectOption("qwen_image_21");
  if (await page.locator("#rookieui-preset").inputValue() !== "qwen_image_21") throw safeError("txt2img_profile_drift");
  await selectIfPresent(page, "#rookieui-checkpoint", config.selectors.diffusion_bf16);
  await selectIfPresent(page, "#rookieui-text-encoder", config.selectors.encoder_int8);
  await selectIfPresent(page, "#rookieui-vae", config.selectors.vae_bf16);
  await page.locator("#rookieui-prompt").fill(UI_PROMPT);
  await page.locator("#rookieui-width").fill("1024");
  await page.locator("#rookieui-height").fill("1024");
  const submitted = page.waitForResponse(
    (response) => /\/rookieui\/generate\/txt2img$/.test(new URL(response.url()).pathname) && response.request().method() === "POST",
    { timeout: 60000 },
  );
  await page.locator("#rookieui-txt2img-submit").click();
  const response = await submitted;
  const body = await response.json();
  const promptId = body?.submission?.prompt_id;
  if (response.status() !== 200 || body?.mode !== "queued" || !/^[0-9a-fA-F-]{20,80}$/.test(promptId ?? "")) {
    throw safeError("ui_generation_not_queued");
  }
  const status = page.locator("#rookieui-txt2img-status");
  let progressObserved = false;
  const deadline = Date.now() + GENERATION_TIMEOUT_MS;
  let text = "";
  while (Date.now() < deadline) {
    text = (await status.textContent()) ?? "";
    const progress = /in progress \((\d+)%\)/.exec(text);
    if (progress && Number(progress[1]) > 0 && Number(progress[1]) < 100) progressObserved = true;
    if (text.includes(promptId) && /^(Completed|Generation failed|Generation cancelled|Runtime sync timed out)/.test(text)) break;
    await page.waitForTimeout(250);
  }
  if (!text.startsWith(`Completed: ${promptId}`) || /final image unavailable|no image output found/.test(text)) {
    throw safeError("ui_generation_not_completed");
  }
  const job = await jobFor(config, promptId, evidence.clientId);
  const output = job?.reusable_outputs?.[0];
  if (job?.status !== "completed" || !HANDLE.test(output ?? "")) throw safeError("ui_generation_job_unbound");
  const src = await page.locator("#rookieui-txt2img-preview img").first().getAttribute("src");
  if (!src || new URL(src, config.base_url).searchParams.get("filename") !== output) throw safeError("ui_preview_not_job_output");
  if (!progressObserved) throw safeError("ui_progress_event_not_observed");
  checks.ui_generation = { prompt_id: promptId, progress_observed: true, preview_bound_to_output: true };
}

async function runEditPane(page, config, checks, state) {
  await page.locator("#rookieui-tab-img2img").click();
  await page.locator("#rookieui-img2img-preset").selectOption("qwen_image_21_edit");
  await page.locator("#rookieui-img2img-qwen21-controls").waitFor({ state: "visible" });
  for (let slot = 1; slot <= 10; slot += 1) {
    await page.locator(`#rookieui-img2img-reference-card-${slot}`).waitFor({ state: "visible" });
  }
  await selectIfPresent(page, "#rookieui-img2img-checkpoint", config.selectors.diffusion_bf16);
  await selectIfPresent(page, "#rookieui-img2img-text-encoder", config.selectors.encoder_int8);
  await selectIfPresent(page, "#rookieui-img2img-vae", config.selectors.vae_bf16);
  const ref1 = fixtureBytes(config, "ref_01");
  const ref2 = fixtureBytes(config, "ref_02");
  await page.locator("#rookieui-img2img-image-file").setInputFiles({ name: "reference-1.png", mimeType: "image/png", buffer: ref1 });
  await page.locator("#rookieui-img2img-reference-file-2").setInputFiles({ name: "reference-2.png", mimeType: "image/png", buffer: ref2 });
  await page.waitForFunction(() => document.querySelector("#rookieui-image-data")?.value
    && document.querySelector("#rookieui-img2img-reference-data-2")?.value, null, { timeout: 15000 });
  if (sha256(await inputBytes(page, "#rookieui-image-data")) !== sha256(ref1)
      || sha256(await inputBytes(page, "#rookieui-img2img-reference-data-2")) !== sha256(ref2)) {
    throw safeError("reference_upload_bytes_changed");
  }
  await page.locator("#rookieui-img2img-reference-main-1").check();
  if (sha256(await inputBytes(page, "#rookieui-image-data")) !== sha256(ref2)
      || sha256(await inputBytes(page, "#rookieui-img2img-reference-data-2")) !== sha256(ref1)
      || !(await page.locator("#rookieui-img2img-reference-main-0").isChecked())
      || await page.locator("#rookieui-img2img-main-reference-index").inputValue() !== "0") {
    throw safeError("primary_promotion_not_visible");
  }
  await page.locator("#rookieui-img2img-prompt").fill(EDIT_PROMPT);
  let dry = await dryRunEditRequest(page, state);
  const sent = dry.request?.reference_images ?? [];
  const handles = dry.response?.normalized_request?.reference_image_assets ?? [];
  if (dry.request?.profile !== "qwen_image_21_edit" || dry.request?.main_reference_index !== 0 || sent.length !== 2
      || sha256(dataUrlBytes(sent[0].image_data)) !== sha256(ref2) || sha256(dataUrlBytes(sent[1].image_data)) !== sha256(ref1)
      || handles.length !== 2 || hostInputSha(config, handles[0]) !== sha256(ref2) || hostInputSha(config, handles[1]) !== sha256(ref1)) {
    throw safeError("promoted_request_order_mismatch");
  }
  const encoder = encoderInputs(dry.response.workflow);
  if (dry.response.workflow[encoder["images.image_1"][0]]?.inputs?.asset_handle !== handles[0]) {
    throw safeError("promoted_graph_order_mismatch");
  }
  checks.reference_promotion = { visible_slot_order: "reference_2_first", serialized_order: "reference_2_first", graph_image_1: "reference_2" };
  await page.locator("#rookieui-img2img-reference-clear-2").click();
  dry = await dryRunEditRequest(page, state);
  if ((dry.request?.reference_images ?? []).length !== 1
      || (dry.response?.normalized_request?.reference_image_assets ?? []).length !== 1) {
    throw safeError("reference_clear_not_serialized");
  }
  checks.reference_clear = { serialized_references: 1 };
  await page.locator("#rookieui-img2img-reference-resolution").fill("1024");
  await page.locator("#rookieui-img2img-output-size-mode").selectOption("custom");
  await page.locator("#rookieui-img2img-width").fill("768");
  await page.locator("#rookieui-img2img-height").fill("1024");
  dry = await dryRunEditRequest(page, state);
  const latent = Object.values(dry.response.workflow).find((item) => item?.class_type === "EmptyLatentImage");
  if (dry.request?.reference_resolution !== 1024 || dry.request?.output_size_mode !== "custom"
      || encoderInputs(dry.response.workflow).resolution !== 1024 || latent?.inputs?.width !== 768 || latent?.inputs?.height !== 1024) {
    throw safeError("custom_size_controls_ineffective");
  }
  checks.custom_size_controls = { reference_resolution: 1024, width: 768, height: 1024 };
  await page.locator("#rookieui-img2img-prompt").fill("draft instruction");
  const taskBefore = await page.locator("#rookieui-img2img-edit-task").inputValue();
  state.dialogMode = "dismiss";
  await page.locator("#rookieui-img2img-qwen21-background-instruction").click();
  await page.waitForTimeout(250);
  if (state.confirmDialogs !== 1 || await page.locator("#rookieui-img2img-prompt").inputValue() !== "draft instruction"
      || await page.locator("#rookieui-img2img-edit-task").inputValue() !== taskBefore) {
    throw safeError("background_preset_overwrote_without_consent");
  }
  state.dialogMode = "accept";
  await page.locator("#rookieui-img2img-qwen21-background-instruction").click();
  await page.waitForTimeout(250);
  if (state.confirmDialogs !== 2 || await page.locator("#rookieui-img2img-prompt").inputValue() !== BACKGROUND_INSTRUCTION
      || await page.locator("#rookieui-img2img-edit-task").inputValue() !== "background_removal") {
    throw safeError("background_preset_not_applied");
  }
  state.dialogMode = "unexpected";
  checks.background_preset = { dismiss_preserved_text: true, accept_applied_visible_instruction: true };
}

async function runSidebarLifecycle(page, checks) {
  if (await page.locator("#rookieui-tab-img2img").getAttribute("aria-selected") !== "true") throw safeError("active_tab_precondition");
  await toggleSidebar(page);
  await page.waitForFunction(() => {
    const shell = document.querySelector("#rookieui-shell-tabs");
    return !shell || !shell.checkVisibility?.();
  }, null, { timeout: 15000 });
  await toggleSidebar(page);
  await page.locator("#rookieui-shell-tabs").first().waitFor({ state: "visible", timeout: 15000 });
  if (await page.locator("#rookieui-shell-tabs").count() !== 1
      || await page.locator("#rookieui-tab-img2img").getAttribute("aria-selected") !== "true") {
    throw safeError("sidebar_remount_state_lost");
  }
  checks.sidebar_lifecycle = { closed_and_reopened: true, single_shell: true, active_tab_restored: true };
}

async function runTransfer(page, config, row, output, checks) {
  await page.locator("#rookieui-tab-queue").click();
  const item = page.locator("#rookieui-queue-list li").filter({ hasText: row.prompt_id });
  await item.waitFor({ state: "visible", timeout: 20000 });
  await item.getByRole("button", { name: "Use as Img2Img" }).click();
  await page.locator("#rookieui-tab-img2img").click();
  if (await page.locator("#rookieui-image-asset").inputValue() !== row.output_handle) throw safeError("queue_send_to_edit_mismatch");
  checks.queue_send_to_edit = { image_asset_is_job_output: true };
  const imageBytes = readFileSync(resolve(dirname(output), `${config.host}-execute-images`, `${CASE_ID}.png`));
  if (sha256(imageBytes) !== row.original_sha256) throw safeError("output_image_mismatch");
  await page.locator("#rookieui-tab-pnginfo").click();
  const inspected = page.waitForResponse(
    (response) => /\/rookieui\/pnginfo\/inspect$/.test(new URL(response.url()).pathname) && response.request().method() === "POST",
    { timeout: 30000 },
  );
  await page.locator("#rookieui-pnginfo-image-file").setInputFiles({ name: "synthetic-output.png", mimeType: "image/png", buffer: imageBytes });
  const response = await inspected;
  const body = await response.json();
  if (response.status() !== 200 || body?.status !== "ok" || body?.source_type !== "a1111"
      || hostInputSha(config, body?.asset_handle) !== row.original_sha256) {
    throw safeError("pnginfo_transfer_mismatch");
  }
  await page.waitForFunction(() => document.querySelector("#rookieui-pnginfo-status")?.textContent === "Ready to apply img2img fields",
    null, { timeout: 20000 });
  checks.pnginfo = { interpreted: "a1111_infotext", stored_bytes_equal_original: true };
}

export async function run(config, output, row) {
  const index = await fetch(`${config.base_url}/`);
  if (index.status !== 200 || sha256(Buffer.from(await index.arrayBuffer())) !== config.frontend_index_sha256) {
    throw safeError("frontend_digest_mismatch");
  }
  const job = await jobFor(config, row.prompt_id, row.client_id);
  if (job?.id !== row.prompt_id || job.status !== "completed" || job.reusable_outputs?.[0] !== row.output_handle) {
    throw safeError("selected_job_changed");
  }
  const screenshots = resolve(dirname(output), `${config.host}-ui-screenshots`);
  mkdirSync(screenshots, { recursive: true });
  const { chromium } = await import("@playwright/test");
  const browser = await chromium.launch({ headless: true });
  const checks = {};
  const shots = {};
  const state = { dialogMode: "unexpected", confirmDialogs: 0, unexpectedDialogs: 0, rookieuiPageErrors: 0, lastEditRequest: null };
  try {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
    const page = await context.newPage();
    page.on("dialog", async (dialog) => {
      if (dialog.type() === "confirm" && dialog.message() === CONFIRM_MESSAGE && state.dialogMode !== "unexpected") {
        state.confirmDialogs += 1;
        await (state.dialogMode === "accept" ? dialog.accept() : dialog.dismiss());
        return;
      }
      state.unexpectedDialogs += 1;
      await dialog.dismiss();
    });
    page.on("pageerror", (error) => {
      if (/rookieui/i.test(`${error?.stack ?? ""}`)) state.rookieuiPageErrors += 1;
    });
    await page.route(/\/rookieui\/generate\/img2img$/, async (route) => {
      // Edit-pane checks inspect the real host translation without queueing a GPU job.
      const body = JSON.parse(route.request().postData() ?? "{}");
      state.lastEditRequest = body;
      await route.continue({ postData: JSON.stringify({ ...body, dry_run: true }) });
    });
    await page.addInitScript((clientId) => sessionStorage.setItem("clientId", clientId), row.client_id);
    await page.goto(`${config.base_url}/`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForFunction(() => window.__ROOKIEUI_BOOTSTRAP__?.clientId, null, { timeout: 60000 });
    if (await page.evaluate(() => window.__ROOKIEUI_BOOTSTRAP__?.clientId) !== row.client_id) throw safeError("browser_client_mismatch");
    await openSidebar(page);
    if (await page.locator("#rookieui-shell-tabs").count() !== 1) throw safeError("sidebar_shell_duplicated");
    shots.baseline = await capture(page, screenshots, "baseline", "#rookieui-shell-tabs");
    await runUiGeneration(page, config, checks, { clientId: row.client_id });
    shots.txt2img = await capture(page, screenshots, "txt2img", "#rookieui-pane-txt2img");
    await runEditPane(page, config, checks, state);
    shots.edit = await capture(page, screenshots, "edit", "#rookieui-pane-img2img");
    await runSidebarLifecycle(page, checks);
    shots.remount = await capture(page, screenshots, "remount", "#rookieui-shell-tabs");
    await runTransfer(page, config, row, output, checks);
    shots.pnginfo = await capture(page, screenshots, "pnginfo", "#rookieui-pane-pnginfo");
    if (state.unexpectedDialogs || state.rookieuiPageErrors) throw safeError("unexpected_browser_errors");
    return { checks, screenshots: shots, dialogs: { confirm: state.confirmDialogs, unexpected: state.unexpectedDialogs },
      rookieui_page_errors: state.rookieuiPageErrors, ui_generation_prompt_id: checks.ui_generation.prompt_id };
  } finally {
    await browser.close();
  }
}

export async function main(argv = process.argv.slice(2)) {
  let args;
  try {
    args = parseOptions(argv);
  } catch (error) {
    process.stderr.write(`qualification FAIL: ${error.code ?? "arguments_invalid"}\n`);
    return 1;
  }
  if (existsSync(args.output)) {
    process.stderr.write("qualification FAIL: result_exists\n");
    return 1;
  }
  const result = { schema: RESULT_SCHEMA, status: "FAIL", timestamp_utc: new Date().toISOString(), screenshots: {}, checks: {} };
  let exitCode = 1;
  try {
    const config = validateConfig(readJson(args.config, "config_unreadable"));
    const execute = readJson(resolve(dirname(args.output), `${config.host}-execute.json`), "execute_result_unreadable");
    const row = selectedJob(config, execute);
    Object.assign(result, { host: config.host, candidate_tree: config.candidate_tree,
      served_frontend_digest: config.frontend_index_sha256, selected_case_id: CASE_ID, selected_prompt_id: row.prompt_id });
    Object.assign(result, await run(config, args.output, row));
    result.status = "PASS";
    exitCode = 0;
  } catch (error) {
    result.error_code = /^[a-z][a-z0-9_]{2,63}$/.test(error?.code ?? "") ? error.code : `unexpected_${String(error?.name ?? "error").toLowerCase()}`;
  }
  mkdirSync(dirname(args.output), { recursive: true });
  const descriptor = openSync(args.output, "wx");
  try {
    writeFileSync(descriptor, `${JSON.stringify(result, null, 2)}\n`);
  } finally {
    closeSync(descriptor);
  }
  process.stdout.write(`qualification ${result.status}: ${result.error_code ?? "ok"}\n`);
  return exitCode;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
