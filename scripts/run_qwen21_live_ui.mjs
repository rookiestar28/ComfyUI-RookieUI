/**
 * Live RookieUI Qwen Image 2.1 sidebar qualification with private, content-free evidence.
 *
 * Usage: node scripts/run_qwen21_live_ui.mjs --config <host-config.json> --output <result.json>
 * The execute-phase result `<host>-execute.json` and its image directory must sit next to the output.
 * Edit-pane request checks are rewritten to dry-run in the browser route so they never enqueue.
 */

import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { closeSync, existsSync, mkdirSync, openSync, readFileSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const RESULT_SCHEMA = "Qwen21LiveUIV1";
export const FRONTEND_INDEX_SHA256_BY_HOST = Object.freeze({
  H1: "38f822ff4d165ccc57e39587761928f95ab63e96c9cbff53041e91bf68f395cc", // pragma: allowlist secret - public artifact digest
  H2: "646c7d93ee00987398471b5abd58a17a238017a5385917a2394a2d05635b8302", // pragma: allowlist secret - public artifact digest
});
export const MINIMUM_FREE_VRAM_BYTES = 48 * 1024 ** 3;
const CONFIG_SCHEMA = "Qwen21HostConfigV1";
const EXECUTE_SCHEMA = "Qwen21HostQualificationV1";
const CASE_ID = "Q21-REMOVE-BG";
const EXPECTED_CORE_VERSION = "0.37.0";
const EXPECTED_BUNDLED_FRONTEND_VERSION = "1.53.6";
const PRIMARY_DIFFUSION_SELECTOR = "Qwen_Image\\qwen_image_2.1_int8_convrot.safetensors";
const PRIMARY_DIFFUSION_SHA256 = "cb74113cb03faecd79611b01fd7fd642f0aa60d6f0b95086abee214d75eaa57d"; // pragma: allowlist secret - public artifact digest
const PRIMARY_DIFFUSION_SIZE = 7256783064;
// Git object IDs are SHA-1 here (40 hex); file digests are SHA-256 (64 hex).
const GIT_OBJECT_ID = /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/;
const SHA256 = /^[0-9a-f]{64}$/;
const CLIENT_ID = /^rookieui-q21-[0-9a-f]{32}$/;
const HANDLE = /^[A-Za-z0-9_-]{1,64}\.(?:png|jpg|webp)$/;
const BACKGROUND_INSTRUCTION = "Remove the background from <image1> and keep the subject with transparent alpha.";
const CONFIRM_MESSAGE = "Replace the current edit instruction?";
const UI_PROMPT = "A single flat red circle centered on a plain white background, simple vector illustration, no text.";
const EDIT_PROMPT = "Place a small copy of the red circle from <image2> at the center of the triangle in <image1>.";
const GENERATION_TIMEOUT_MS = 10 * 60 * 1000;
// IMPORTANT: ComfyUI derives custom sidebar test IDs from the registered tab ID; the bare RookieUI prefix misses that button.
export const SIDEBAR_LAUNCHER_SELECTOR = '[data-testid="comfyui-rookieui-tab-button"], [data-testid="rookieui-tab-button"], .rookieui-tab-button, #rookieui-legacy-launcher';

const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");
const PROJECT_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

export function safeError(code) {
  const error = new Error(code);
  error.code = code;
  return error;
}

export function pinBrowserClientIdentity(clientId, windowRef = globalThis.window) {
  const codedError = (code) => {
    const error = new Error(code);
    error.code = code;
    return error;
  };
  if (!/^rookieui-q21-[0-9a-f]{32}$/.test(clientId ?? "")) {
    throw codedError("browser_client_invalid");
  }
  try {
    if (!windowRef?.sessionStorage?.setItem || !windowRef.sessionStorage.getItem) {
      throw codedError("browser_client_binding_failed");
    }
    windowRef.sessionStorage.setItem("clientId", clientId);
    windowRef.name = clientId;
    if (windowRef.name !== clientId || windowRef.sessionStorage.getItem("clientId") !== clientId) {
      throw codedError("browser_client_binding_failed");
    }
  } catch {
    throw codedError("browser_client_binding_failed");
  }
  return true;
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
  if (!GIT_OBJECT_ID.test(raw.core_head ?? "") || typeof raw.core_root !== "string" || !raw.core_root
      || !Number.isSafeInteger(raw.process_pid) || raw.process_pid <= 0
      || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z$/.test(raw.process_created_utc ?? "")
      || !SHA256.test(raw.process_command_sha256 ?? "")) {
    throw safeError("config_process");
  }
  if (!SHA256.test(raw.frontend_index_sha256 ?? "")) throw safeError("config_frontend");
  if (raw.frontend_index_sha256 !== FRONTEND_INDEX_SHA256_BY_HOST[raw.host]) {
    throw safeError("config_frontend_identity");
  }
  for (const key of ["fixture_manifest", "rookieui_install_root"]) {
    if (typeof raw[key] !== "string" || !raw[key]) throw safeError("config_paths");
  }
  const selectors = {};
  for (const role of ["diffusion_primary", "encoder_int8", "vae_bf16"]) {
    const model = raw.models?.[role];
    const selector = model?.selector;
    if (typeof selector !== "string" || !selector) throw safeError("config_models");
    if (role === "diffusion_primary" && (selector !== PRIMARY_DIFFUSION_SELECTOR
        || model.sha256 !== PRIMARY_DIFFUSION_SHA256 || model.size !== PRIMARY_DIFFUSION_SIZE)) {
      throw safeError("config_primary_diffusion_identity");
    }
    selectors[role] = selector;
  }
  return {
    host: raw.host, base_url: url.origin, candidate_tree: raw.candidate_tree,
    core_root: raw.core_root, core_head: raw.core_head, process_pid: raw.process_pid,
    process_created_utc: raw.process_created_utc, process_command_sha256: raw.process_command_sha256,
    frontend_index_sha256: raw.frontend_index_sha256, fixture_manifest: raw.fixture_manifest,
    rookieui_install_root: raw.rookieui_install_root, selectors,
  };
}

export function selectedJob(config, report) {
  if (report?.schema !== EXECUTE_SCHEMA || report.host !== config.host || report.phase !== "execute"
      || report.candidate_tree !== config.candidate_tree || report.served_frontend_digest !== config.frontend_index_sha256
      || !SHA256.test(report.host_identity_digest ?? "") || report.status !== "PENDING_REVIEW") {
    throw safeError("execute_identity_mismatch");
  }
  const row = report.cases?.find((item) => item.case_id === CASE_ID);
  if (row && row.host_identity_digest !== report.host_identity_digest) throw safeError("execute_identity_mismatch");
  if (!row || row.selected !== true || row.child_exit !== 0 || row.status !== "PENDING_REVIEW" || row.original_decoded !== true
      || row.history_matched !== true || row.terminal_status !== "completed" || !SHA256.test(row.original_sha256 ?? "")
      || !/^[0-9a-fA-F-]{20,80}$/.test(row.prompt_id ?? "") || !CLIENT_ID.test(row.client_id ?? "")
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

export async function previewImageBytes(page, selector) {
  const preview = page.locator(selector);
  if (await preview.count() !== 1) throw safeError("preview_image_count");
  if (!(await preview.evaluate((element) => element instanceof HTMLImageElement))) {
    throw safeError("preview_image_not_img");
  }
  if (!(await preview.isVisible())) throw safeError("preview_image_hidden");
  return dataUrlBytes(await preview.getAttribute("src"));
}

export function validateGenerationCapacity(queue, stats) {
  if (!Array.isArray(queue?.queue_running) || !Array.isArray(queue?.queue_pending)) {
    throw safeError("host_queue_shape");
  }
  if (queue.queue_running.length || queue.queue_pending.length) throw safeError("host_queue_busy");
  const free = validateFreeVram(stats);
  if (free < MINIMUM_FREE_VRAM_BYTES) throw safeError("host_vram_low");
  return free;
}

export function validateFreeVram(stats) {
  const free = stats?.devices?.[0]?.vram_free;
  if (!Number.isSafeInteger(free) || free < 0) {
    throw safeError("host_vram_unavailable");
  }
  return free;
}

export function validateLiveProcessIdentity(config, identity) {
  if (identity?.listener_pid !== config.process_pid || identity?.pid !== config.process_pid
      || identity?.created_utc !== config.process_created_utc
      || identity?.command_sha256 !== config.process_command_sha256) {
    throw safeError("host_process_identity_mismatch");
  }
  return true;
}

export function validateCandidateIdentity(config, observation) {
  if (observation?.tree !== config.candidate_tree) throw safeError("candidate_tree_mismatch");
  if (observation?.dirty !== false) throw safeError("candidate_worktree_dirty");
  return true;
}

export function validateHostRuntimeIdentity(stats, bootstrap, config, expectedDigest) {
  const system = stats?.system;
  if (system?.comfyui_version !== EXPECTED_CORE_VERSION) throw safeError("host_core_runtime_mismatch");
  const packages = system?.comfy_package_versions;
  const frontend = Array.isArray(packages)
    ? packages.find((item) => item?.name === "comfyui-frontend-package")
    : undefined;
  if (frontend?.installed !== EXPECTED_BUNDLED_FRONTEND_VERSION) throw safeError("host_bundled_frontend_mismatch");
  const fingerprint = bootstrap?.runtime?.build_fingerprint;
  if (typeof fingerprint !== "string" || !/^sha256:[0-9a-f]{64}$/.test(fingerprint)) {
    throw safeError("host_rookieui_fingerprint_mismatch");
  }
  const identity = {
    command_sha256: config.process_command_sha256,
    core: config.core_head,
    created: config.process_created_utc,
    frontend: config.frontend_index_sha256,
    pid: config.process_pid,
    rookieui: fingerprint,
  };
  if (!SHA256.test(expectedDigest ?? "") || sha256(Buffer.from(JSON.stringify(identity))) !== expectedDigest) {
    throw safeError("host_identity_digest_mismatch");
  }
  return fingerprint;
}

function verifyLocalProcess(config) {
  if (process.platform !== "win32") throw safeError("host_process_identity_unavailable");
  const command = `$listener = Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; `
    + `$proc = Get-CimInstance Win32_Process -Filter 'ProcessId=${config.process_pid}'; `
    + "if ($null -eq $listener -or $null -eq $proc) { exit 2 }; "
    + "$bytes=[System.Text.Encoding]::UTF8.GetBytes([string]$proc.CommandLine); "
    + "$sha=[System.Security.Cryptography.SHA256]::Create(); "
    + "$commandHash=[BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').ToLowerInvariant(); "
    + "[pscustomobject]@{listener_pid=[int]$listener.OwningProcess; pid=[int]$proc.ProcessId; "
    + "created_utc=$proc.CreationDate.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffffffZ'); "
    + "command_sha256=$commandHash} | ConvertTo-Json -Compress";
  let observation;
  try {
    observation = JSON.parse(execFileSync("powershell", ["-NoProfile", "-NonInteractive", "-Command", command], {
      encoding: "utf8", timeout: 25000, windowsHide: true,
    }));
  } catch {
    throw safeError("host_process_identity_unavailable");
  }
  const identity = {
    listener_pid: observation.listener_pid,
    pid: observation.pid,
    created_utc: observation.created_utc,
    command_sha256: observation.command_sha256,
  };
  validateLiveProcessIdentity(config, identity);
}

function verifyLocalCandidate(config) {
  let tree;
  let dirty;
  try {
    tree = execFileSync("git", ["-C", PROJECT_ROOT, "rev-parse", "HEAD^{tree}"], {
      encoding: "utf8", timeout: 30000, windowsHide: true,
    }).trim();
    dirty = execFileSync("git", ["-C", PROJECT_ROOT, "status", "--porcelain", "--untracked-files=no"], {
      encoding: "utf8", timeout: 30000, windowsHide: true,
    }).trim().length > 0;
  } catch {
    throw safeError("candidate_identity_unavailable");
  }
  validateCandidateIdentity(config, { tree, dirty });
}

function verifyLocalCore(config) {
  let head;
  try {
    head = execFileSync("git", ["-C", config.core_root, "rev-parse", "HEAD"], {
      encoding: "utf8", timeout: 30000, windowsHide: true,
    }).trim();
  } catch {
    throw safeError("core_head_unavailable");
  }
  if (head !== config.core_head) throw safeError("core_head_mismatch");
}

async function verifyCurrentHost(config, row) {
  verifyLocalCandidate(config);
  verifyLocalProcess(config);
  verifyLocalCore(config);
  const [stats, bootstrap] = await Promise.all([
    hostJson(config, "/system_stats"),
    hostJson(config, "/rookieui/bootstrap"),
  ]);
  validateHostRuntimeIdentity(stats, bootstrap, config, row.host_identity_digest);
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
  const response = await fetch(new URL(path, config.base_url), { signal: AbortSignal.timeout(10000) });
  if (response.status !== 200) throw safeError("host_http_status");
  return response.json();
}

async function assertGenerationCapacity(config) {
  const [queue, stats] = await Promise.all([
    hostJson(config, "/queue"),
    hostJson(config, "/system_stats"),
  ]);
  return validateGenerationCapacity(queue, stats);
}

async function readFreeVram(config) {
  return validateFreeVram(await hostJson(config, "/system_stats"));
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

export async function toggleSidebar(page) {
  const button = page.locator(SIDEBAR_LAUNCHER_SELECTOR);
  if (await button.count() !== 1) throw safeError("sidebar_launcher_ambiguous");
  await button.click();
}

async function capture(page, dir, name, selector) {
  const target = page.locator(selector).first();
  await target.waitFor({ state: "visible", timeout: 15000 });
  const path = join(dir, `${name}.png`);
  const mask = await page.addStyleTag({ content: `
    input, select, textarea, [contenteditable], [contenteditable] * {
      color: transparent !important;
      -webkit-text-fill-color: transparent !important;
      text-shadow: 0 0 8px rgba(0, 0, 0, 1) !important;
      caret-color: transparent !important;
    }
    input::placeholder, textarea::placeholder { color: transparent !important; text-shadow: none !important; }
    #rookieui-pnginfo-metadata, #rookieui-pnginfo-metadata * { visibility: hidden !important; }
  ` });
  try {
    await target.screenshot({ path, animations: "disabled" });
  } finally {
    await mask.evaluate((style) => style.remove());
  }
  return sha256(readFileSync(path));
}

export async function selectIfPresent(page, selector, value) {
  const select = page.locator(selector);
  const optionCount = await select.locator(`option[value="${value.replaceAll("\\", "\\\\").replaceAll('"', '\\"')}"]`).count();
  if (optionCount > 0 && await select.isVisible() && await select.isEnabled()) {
    await select.selectOption(value);
  }
  // CRITICAL: template-owned selectors can be hidden/disabled; only accept their exact preset value, never force a hidden interaction.
  if (await select.inputValue() !== value) throw safeError(`model_selector_unavailable_${selector.slice(1).replaceAll("-", "_")}`);
}

async function dryRunEditRequest(page, state) {
  const form = page.locator("#rookieui-img2img-form");
  if (!(await form.evaluate((element) => element.checkValidity()))) throw safeError("edit_form_invalid");
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
  await selectIfPresent(page, "#rookieui-checkpoint", config.selectors.diffusion_primary);
  await selectIfPresent(page, "#rookieui-text-encoder", config.selectors.encoder_int8);
  await selectIfPresent(page, "#rookieui-vae", config.selectors.vae_bf16);
  await page.locator("#rookieui-prompt").fill(UI_PROMPT);
  await page.locator("#rookieui-width").fill("1024");
  await page.locator("#rookieui-height").fill("1024");
  const vramFreeBefore = await assertGenerationCapacity(config);
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
  const vramFreeAfter = await readFreeVram(config);
  const src = await page.locator("#rookieui-txt2img-preview img").first().getAttribute("src");
  if (!src || new URL(src, config.base_url).searchParams.get("filename") !== output) throw safeError("ui_preview_not_job_output");
  if (!progressObserved) throw safeError("ui_progress_event_not_observed");
  checks.ui_generation = { prompt_id: promptId, progress_observed: true, preview_bound_to_output: true,
    vram_free_before: vramFreeBefore, vram_free_after: vramFreeAfter };
}

async function runEditPane(page, config, checks, state) {
  await page.locator("#rookieui-tab-img2img").click();
  await page.locator("#rookieui-img2img-preset").selectOption("qwen_image_21_edit");
  await page.locator("#rookieui-img2img-qwen21-controls").waitFor({ state: "visible" });
  for (let slot = 1; slot <= 10; slot += 1) {
    await page.locator(`#rookieui-img2img-reference-card-${slot}`).waitFor({ state: "visible" });
  }
  await selectIfPresent(page, "#rookieui-img2img-checkpoint", config.selectors.diffusion_primary);
  await selectIfPresent(page, "#rookieui-img2img-text-encoder", config.selectors.encoder_int8);
  await selectIfPresent(page, "#rookieui-img2img-vae", config.selectors.vae_bf16);
  const ref1 = fixtureBytes(config, "ref_01");
  const ref2 = fixtureBytes(config, "ref_02");
  const sourcePreviewSelector = "#rookieui-img2img-source-canvas-preview";
  await page.locator("#rookieui-img2img-image-file").setInputFiles({ name: "reference-1.png", mimeType: "image/png", buffer: ref1 });
  await page.waitForFunction(() => {
    const preview = document.querySelector("#rookieui-img2img-source-canvas-preview");
    return preview instanceof HTMLImageElement && !preview.hidden && preview.getAttribute("src")?.startsWith("data:image/");
  }, null, { timeout: 15000 });
  if (sha256(await previewImageBytes(page, sourcePreviewSelector)) !== sha256(ref1)) {
    throw safeError("reference_one_preview_mismatch");
  }
  await page.locator("#rookieui-img2img-reference-file-2").setInputFiles({ name: "reference-2.png", mimeType: "image/png", buffer: ref2 });
  await page.waitForFunction(() => /uploaded reference image ready/i.test(
    document.querySelector("#rookieui-img2img-reference-status-2")?.textContent ?? "",
  ), null, { timeout: 15000 });
  await page.locator("#rookieui-img2img-reference-main-1").click();
  if (!(await page.locator("#rookieui-img2img-reference-main-0").isChecked())
      || sha256(await previewImageBytes(page, sourcePreviewSelector)) !== sha256(ref2)) {
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
  await verifyCurrentHost(config, row);
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
    // CRITICAL: Core 0.37 reads window.name for its WebSocket clientId.
    // Session storage alone is overwritten by Core's returned sid.
    await page.addInitScript(pinBrowserClientIdentity, row.client_id);
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
      served_frontend_digest: config.frontend_index_sha256, host_identity_digest: row.host_identity_digest,
      selected_case_id: CASE_ID, selected_prompt_id: row.prompt_id });
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
