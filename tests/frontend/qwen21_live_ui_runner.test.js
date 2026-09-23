// @vitest-environment node
import { describe, expect, it } from "vitest";

import {
  dataUrlBytes,
  FRONTEND_INDEX_SHA256_BY_HOST,
  MINIMUM_FREE_VRAM_BYTES,
  parseOptions,
  selectedJob,
  validateConfig,
  validateFreeVram,
  validateGenerationCapacity,
} from "../../scripts/run_qwen21_live_ui.mjs";

const TREE = "e7b429d7f2e73bb5b97a0aa70336960489bbe6b9"; // pragma: allowlist secret - public Git tree id
const DIGEST = FRONTEND_INDEX_SHA256_BY_HOST.H1;

function config(overrides = {}) {
  return {
    schema: "Qwen21HostConfigV1",
    host: "H1",
    base_url: "http://127.0.0.1:8188/",
    candidate_tree: TREE,
    frontend_index_sha256: DIGEST,
    fixture_manifest: "fixtures/manifest.json",
    rookieui_install_root: "host/custom_nodes/comfyui-rookieui",
    models: {
      diffusion_bf16: { selector: "Qwen_Image\\qwen_image_2.1_bf16.safetensors" },
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
      ...rowOverrides,
    }],
    ...reportOverrides,
  };
}

describe("Qwen 2.1 live UI qualification runner", () => {
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
