// @vitest-environment node
import { createHash } from "node:crypto";
import { chromium } from "@playwright/test";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import * as liveUiRunner from "../../scripts/run_qwen21_live_ui.mjs";
import {
  dataUrlBytes,
  FRONTEND_INDEX_SHA256_BY_HOST,
  MINIMUM_FREE_VRAM_BYTES,
  parseOptions,
  pinBrowserClientIdentity,
  selectedJob,
  selectIfPresent,
  toggleSidebar,
  validateConfig,
  validateCandidateIdentity,
  validateFreeVram,
  validateGenerationCapacity,
  validateHostRuntimeIdentity,
  validateLiveProcessIdentity,
} from "../../scripts/run_qwen21_live_ui.mjs";

describe("live Qwen 2.1 UI runner browser contracts", () => {
  let browser;
  let page;

  beforeAll(async () => {
    browser = await chromium.launch({ headless: true });
    page = await browser.newPage();
    page.setDefaultTimeout(1200);
  });

  afterAll(async () => {
    await browser?.close();
  });

  it("sets a visible enabled selector to the requested model", async () => {
    await page.setContent('<select id="rookieui-text-encoder"><option value="other">Other</option><option value="qwen3vl-int8">Qwen 3 VL</option></select>');
    await selectIfPresent(page, "#rookieui-text-encoder", "qwen3vl-int8");
    expect(await page.locator("#rookieui-text-encoder").inputValue()).toBe("qwen3vl-int8");
  });

  it("accepts a hidden disabled profile-owned selector only when its selected value already matches", async () => {
    await page.setContent('<select id="rookieui-text-encoder" hidden disabled><option value="qwen3vl-int8" selected>Qwen 3 VL</option></select>');
    await expect(selectIfPresent(page, "#rookieui-text-encoder", "qwen3vl-int8")).resolves.toBeUndefined();
    expect(await page.locator("#rookieui-text-encoder").inputValue()).toBe("qwen3vl-int8");
  });

  it("fails closed when a hidden disabled selector does not hold the requested model", async () => {
    await page.setContent('<select id="rookieui-text-encoder" hidden disabled><option value="other" selected>Other</option><option value="qwen3vl-int8">Qwen 3 VL</option></select>');
    await expect(selectIfPresent(page, "#rookieui-text-encoder", "qwen3vl-int8"))
      .rejects.toThrow("model_selector_unavailable_rookieui_text_encoder");
    expect(await page.locator("#rookieui-text-encoder").inputValue()).toBe("other");
  });

  it("reads exact bytes from one visible image preview", async () => {
    const previewImageBytes = liveUiRunner.previewImageBytes;
    expect(typeof previewImageBytes).toBe("function");
    await page.setContent('<img class="preview" width="1" height="1" src="data:image/png;base64,AQID">');
    await expect(previewImageBytes(page, ".preview")).resolves.toEqual(Buffer.from([1, 2, 3]));
  });

  it("rejects missing, duplicate, non-image, and hidden preview targets", async () => {
    const previewImageBytes = liveUiRunner.previewImageBytes;
    expect(typeof previewImageBytes).toBe("function");
    await page.setContent('<img class="preview" width="1" height="1" src="data:image/png;base64,AQID"><img class="preview" width="1" height="1" src="data:image/png;base64,AQID">');
    await expect(previewImageBytes(page, "#missing")).rejects.toThrow("preview_image_count");
    await expect(previewImageBytes(page, ".preview")).rejects.toThrow("preview_image_count");

    await page.setContent('<div id="preview"></div>');
    await expect(previewImageBytes(page, "#preview")).rejects.toThrow("preview_image_not_img");

    await page.setContent('<img id="preview" hidden width="1" height="1" src="data:image/png;base64,AQID">');
    await expect(previewImageBytes(page, "#preview")).rejects.toThrow("preview_image_hidden");

    await page.setContent('<img id="preview" width="1" height="1" src="data:text/plain;base64,AQID">');
    await expect(previewImageBytes(page, "#preview")).rejects.toThrow("data_url_invalid");
  });
});

const TREE = "e7b429d7f2e73bb5b97a0aa70336960489bbe6b9"; // pragma: allowlist secret - public Git tree id
const CORE = "e638023d54497dbe0579565e5de4bb7076899592"; // pragma: allowlist secret - public Git commit id
const DIGEST = FRONTEND_INDEX_SHA256_BY_HOST.H1;
const HOST_IDENTITY = "d".repeat(64);

function expectedHostIdentity(configured, fingerprint) {
  const identity = {
    command_sha256: configured.process_command_sha256,
    core: configured.core_head,
    created: configured.process_created_utc,
    frontend: configured.frontend_index_sha256,
    pid: configured.process_pid,
    rookieui: fingerprint,
  };
  return createHash("sha256").update(JSON.stringify(identity)).digest("hex");
}

function config(overrides = {}) {
  return {
    schema: "Qwen21HostConfigV1",
    host: "H1",
    base_url: "http://127.0.0.1:8188/",
    candidate_tree: TREE,
    core_root: "C:\\host\\ComfyUI",
    core_head: CORE,
    process_pid: 12345,
    process_created_utc: "2026-09-22T11:00:00.0000000Z",
    process_command_sha256: "e".repeat(64),
    frontend_index_sha256: DIGEST,
    fixture_manifest: "fixtures/manifest.json",
    rookieui_install_root: "host/custom_nodes/comfyui-rookieui",
    models: {
      diffusion_primary: {
        selector: "Qwen_Image\\qwen_image_2.1_int8_convrot.safetensors",
        sha256: "cb74113cb03faecd79611b01fd7fd642f0aa60d6f0b95086abee214d75eaa57d", // pragma: allowlist secret - public artifact digest
        size: 7256783064,
      },
      encoder_int8: { selector: "qwen3vl_8b_int8_convrot.safetensors" },
      vae_bf16: { selector: "qwen_image_2.1_vae_bf16.safetensors" },
    },
    ...overrides,
  };
}

function report(rowOverrides = {}, reportOverrides = {}) {
  return {
    schema: "Qwen21HostQualificationV1",
    phase: "execute",
    host: "H1",
    status: "PENDING_REVIEW",
    candidate_tree: TREE,
    host_identity_digest: HOST_IDENTITY,
    served_frontend_digest: DIGEST,
    cases: [{
      case_id: "Q21-REMOVE-BG",
      selected: true,
      child_exit: 0,
      status: "PENDING_REVIEW",
      original_decoded: true,
      history_matched: true,
      terminal_status: "completed",
      original_sha256: "b".repeat(64),
      prompt_id: "0f7c0c9e-6f71-4c5a-9d1e-2b0f3c8a9e11",
      client_id: `rookieui-q21-${"c".repeat(32)}`,
      output_handle: "RookieUI_00007_.png",
      host_identity_digest: HOST_IDENTITY,
      ...rowOverrides,
    }],
    ...reportOverrides,
  };
}

describe("Qwen 2.1 live UI qualification runner", () => {
  it("opens the current registered sidebar tab and rejects ambiguous controls", async () => {
    const makePage = (matchCount) => {
      const state = { selector: "", clicks: 0 };
      const page = {
        locator(selector) {
          state.selector = selector;
          return {
            count: async () => matchCount,
            click: async () => { state.clicks += 1; },
          };
        },
      };
      return { page, state };
    };

    const single = makePage(1);
    await toggleSidebar(single.page);
    expect(single.state.selector).toContain('[data-testid="comfyui-rookieui-tab-button"]');
    expect(single.state.clicks).toBe(1);

    const ambiguous = makePage(2);
    await expect(toggleSidebar(ambiguous.page)).rejects.toThrow("sidebar_launcher_ambiguous");
    expect(ambiguous.state.clicks).toBe(0);
  });

  it("pins both UI flows to the exact convrot primary model role", () => {
    const valid = validateConfig(config());
    expect(valid.selectors.diffusion_primary).toBe("Qwen_Image\\qwen_image_2.1_int8_convrot.safetensors");
    for (const field of ["selector", "sha256", "size"]) {
      const wrong = config();
      wrong.models.diffusion_primary[field] = field === "selector"
        ? "Qwen_Image\\qwen_image_2.1_bf16.safetensors"
        : field === "sha256" ? "b".repeat(64) : 1;
      expect(() => validateConfig(wrong)).toThrow("config_primary_diffusion_identity");
    }
  });

  it("accepts the repository's real SHA-1 git tree identity", () => {
    expect(validateConfig(config()).candidate_tree).toBe(TREE);
  });

  it("rejects malformed tree ids, remote hosts and credentials", () => {
    for (const candidate_tree of [TREE.slice(1), TREE.toUpperCase(), `${TREE}0`]) {
      expect(() => validateConfig(config({ candidate_tree }))).toThrow("config_candidate");
    }
    for (const base_url of ["https://127.0.0.1:8188", "http://example.com:8188", "http://u:p@127.0.0.1:8188", "http://127.0.0.1:8189"]) { // pragma: allowlist secret
      expect(() => validateConfig(config({ base_url }))).toThrow("config_url");
    }
  });

  it("pins each host label to its own served frontend artifact", () => {
    expect(validateConfig(config()).frontend_index_sha256).toBe(FRONTEND_INDEX_SHA256_BY_HOST.H1);
    expect(validateConfig(config({ host: "H2", frontend_index_sha256: FRONTEND_INDEX_SHA256_BY_HOST.H2 })).host).toBe("H2");
    expect(() => validateConfig(config({ frontend_index_sha256: FRONTEND_INDEX_SHA256_BY_HOST.H2 })))
      .toThrow("config_frontend_identity");
    expect(() => validateConfig(config({ host: "H2", frontend_index_sha256: FRONTEND_INDEX_SHA256_BY_HOST.H1 })))
      .toThrow("config_frontend_identity");
  });

  it("requires the frozen local Core process identity", () => {
    expect(() => validateConfig(config({ process_pid: 0 }))).toThrow("config_process");
    expect(() => validateConfig(config({ process_command_sha256: "invalid" }))).toThrow("config_process");
    expect(() => validateConfig(config({ core_head: "bad" }))).toThrow("config_process");
  });

  it("requires the UI runner's clean local candidate tree to remain frozen", () => {
    const valid = validateConfig(config());
    expect(validateCandidateIdentity(valid, { tree: TREE, dirty: false })).toBe(true);
    expect(() => validateCandidateIdentity(valid, { tree: "f".repeat(40), dirty: false }))
      .toThrow("candidate_tree_mismatch");
    expect(() => validateCandidateIdentity(valid, { tree: TREE, dirty: true }))
      .toThrow("candidate_worktree_dirty");
  });

  it("binds current Core, bundled frontend and runtime fingerprint to the execute identity", () => {
    const valid = validateConfig(config());
    const fingerprint = `sha256:${"a".repeat(64)}`;
    const stats = { system: { comfyui_version: "0.37.0", comfy_package_versions: [
      { name: "comfyui-frontend-package", installed: "1.53.6" },
    ] } };
    const bootstrap = { runtime: { build_fingerprint: fingerprint } };
    const digest = expectedHostIdentity(valid, fingerprint);
    expect(validateHostRuntimeIdentity(stats, bootstrap, valid, digest)).toBe(fingerprint);
    expect(() => validateHostRuntimeIdentity({ system: { ...stats.system, comfyui_version: "0.38.0" } }, bootstrap, valid, digest))
      .toThrow("host_core_runtime_mismatch");
    expect(() => validateHostRuntimeIdentity({ system: { ...stats.system, comfy_package_versions: [] } }, bootstrap, valid, digest))
      .toThrow("host_bundled_frontend_mismatch");
    expect(() => validateHostRuntimeIdentity(stats, { runtime: { build_fingerprint: "stale" } }, valid, digest))
      .toThrow("host_rookieui_fingerprint_mismatch");
    expect(() => validateHostRuntimeIdentity(stats, bootstrap, valid, "f".repeat(64)))
      .toThrow("host_identity_digest_mismatch");
  });

  it("requires the running listener PID, creation time and command digest to match", () => {
    const valid = validateConfig(config());
    const identity = {
      listener_pid: valid.process_pid,
      pid: valid.process_pid,
      created_utc: valid.process_created_utc,
      command_sha256: valid.process_command_sha256,
    };
    expect(validateLiveProcessIdentity(valid, identity)).toBe(true);
    expect(() => validateLiveProcessIdentity(valid, { ...identity, listener_pid: valid.process_pid + 1 }))
      .toThrow("host_process_identity_mismatch");
    expect(() => validateLiveProcessIdentity(valid, { ...identity, command_sha256: "f".repeat(64) }))
      .toThrow("host_process_identity_mismatch");
  });

  it("requires an idle global queue and at least 48 GiB free before generation", () => {
    const enough = { devices: [{ vram_free: MINIMUM_FREE_VRAM_BYTES }] };
    expect(validateGenerationCapacity({ queue_running: [], queue_pending: [] }, enough)).toBe(MINIMUM_FREE_VRAM_BYTES);
    expect(() => validateGenerationCapacity({ queue_running: [{}], queue_pending: [] }, enough)).toThrow("host_queue_busy");
    expect(() => validateGenerationCapacity({ queue_running: [], queue_pending: [] },
      { devices: [{ vram_free: MINIMUM_FREE_VRAM_BYTES - 1 }] })).toThrow("host_vram_low");
    expect(() => validateGenerationCapacity({ queue_running: [], queue_pending: [] }, {})).toThrow("host_vram_unavailable");
    expect(() => validateGenerationCapacity({}, enough)).toThrow("host_queue_shape");
    expect(() => validateFreeVram({ devices: [{ vram_free: -1 }] })).toThrow("host_vram_unavailable");
  });

  it("binds only a completed, reviewable execute row of the same host and candidate", () => {
    const valid = validateConfig(config());
    expect(selectedJob(valid, report()).output_handle).toBe("RookieUI_00007_.png");
    expect(() => selectedJob(valid, report({}, { host: "H2" }))).toThrow("execute_identity_mismatch");
    expect(() => selectedJob(valid, report({}, { candidate_tree: "d".repeat(40) }))).toThrow("execute_identity_mismatch");
    expect(() => selectedJob(valid, report({}, { status: "FAIL" }))).toThrow("execute_identity_mismatch");
    expect(() => selectedJob(valid, report({ child_exit: 1 }))).toThrow("selected_job_unqualified");
    expect(() => selectedJob(valid, report({ terminal_status: "failed" }))).toThrow("selected_job_unqualified");
    expect(() => selectedJob(valid, report({ client_id: "shared-client" }))).toThrow("selected_job_unqualified");
    expect(() => selectedJob(valid, report({ output_handle: "../escape.png" }))).toThrow("selected_job_unqualified");
    expect(() => selectedJob(valid, report({ host_identity_digest: "f".repeat(64) })))
      .toThrow("execute_identity_mismatch");
    expect(() => selectedJob(valid, report({}, { host_identity_digest: "f".repeat(64) })))
      .toThrow("execute_identity_mismatch");
  });

  it("rejects a reused background-removal row from the source process after resume", () => {
    const valid = validateConfig(config());
    const staleSourceRow = report(
      { host_identity_digest: HOST_IDENTITY },
      { host_identity_digest: "f".repeat(64) },
    );
    expect(() => selectedJob(valid, staleSourceRow)).toThrow("execute_identity_mismatch");
  });

  it("pins the validated case client id to Core's pre-navigation WebSocket identity", () => {
    const values = new Map();
    const windowRef = {
      name: "",
      sessionStorage: {
        setItem: (key, value) => values.set(key, value),
        getItem: (key) => values.get(key) ?? null,
      },
    };
    const clientId = `rookieui-q21-${"a".repeat(32)}`;

    expect(pinBrowserClientIdentity(clientId, windowRef)).toBe(true);
    expect(windowRef.name).toBe(clientId);
    expect(windowRef.sessionStorage.getItem("clientId")).toBe(clientId);
  });

  it("fails closed for invalid client ids and unavailable browser storage", () => {
    const windowRef = { name: "untouched", sessionStorage: { setItem() {}, getItem: () => null } };
    expect(() => pinBrowserClientIdentity("shared-client", windowRef)).toThrow("browser_client_invalid");
    expect(windowRef.name).toBe("untouched");

    const unavailable = { name: "", sessionStorage: { setItem() { throw new Error("private-detail"); } } };
    expect(() => pinBrowserClientIdentity(`rookieui-q21-${"a".repeat(32)}`, unavailable))
      .toThrow("browser_client_binding_failed");
  });

  it("requires exactly one config and one output argument", () => {
    expect(parseOptions(["--config", "c.json", "--output", "o.json"])).toEqual({ config: "c.json", output: "o.json" });
    expect(() => parseOptions(["--config", "c.json"])).toThrow("arguments_invalid");
    expect(() => parseOptions(["--config", "a", "--config", "b"])).toThrow("arguments_invalid");
    expect(() => parseOptions(["--output", "o.json", "--extra", "x"])).toThrow("arguments_invalid");
  });

  it("decodes only image data URLs", () => {
    expect([...dataUrlBytes("data:image/png;base64,AQID")]).toEqual([1, 2, 3]);
    expect(() => dataUrlBytes("https://example.com/a.png")).toThrow("data_url_invalid");
  });
});
