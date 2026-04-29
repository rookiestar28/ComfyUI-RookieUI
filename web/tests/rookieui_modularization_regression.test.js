import { beforeEach, describe, expect, test } from "vitest";

import { renderRookieUISidebar } from "../rookieui_sidebar_shell.js";

function createBootstrapState() {
  const basePreset = {
    id: "sd15",
    title: "SD 1.5",
    profile: "sd15",
    checkpoint_name: "model.safetensors",
    vae_name: "Automatic",
    text_encoder_name: "Automatic",
    width: 512,
    height: 512,
    steps: 28,
    cfg_scale: 7,
    sampler_name: "euler_ancestral",
    scheduler_name: "normal",
    seed: -1,
    seed_extra: false,
    batch_count: 1,
    batch_size: 1,
    clip_skip: 1,
    hires_enabled: false,
    hires_scale: 1.5,
    hires_steps: 14,
    hires_denoise: 0.35,
    hires_upscale_method: "bislerp",
    dtype_profile: "automatic",
    lora_name: "",
    lora_strength_model: 1,
    lora_strength_clip: 1,
  };

  return {
    hostSurface: "desktop",
    clientId: "test-client",
    runtimeApi: {
      addEventListener() {},
      removeEventListener() {},
      clientId: "test-client",
    },
    capabilities: {
      shell_version: "0.1.0",
      parity: {
        profiles: [
          {
            id: "sd15",
            title: "SD 1.5",
            base_family: "sd15",
            supports_clip_skip: true,
            default_width: 512,
            default_height: 512,
            default_steps: 28,
            default_cfg_scale: 7,
            default_sampler: "euler_ancestral",
            default_scheduler: "normal",
            default_clip_skip: 1,
          },
        ],
      },
    },
    compatibility: {
      source: "test",
      samplers: [{ id: "euler_ancestral", title: "Euler a", default: true, tier: "core" }],
      schedulers: [{ id: "normal", title: "Normal", default: true, tier: "core" }],
      dtype_profiles: [{ id: "automatic", title: "Automatic", default: true, tier: "core" }],
      runtime_profiles: [{ id: "balanced", title: "Balanced", default: true, tier: "core" }],
      newer_family_profiles: [],
    },
    models: {
      source: "test",
      checkpoints: ["model.safetensors", "alternate-model.safetensors"],
      vae: ["Automatic"],
      text_encoders: ["Automatic"],
      embeddings: [],
      loras: ["detail_lora.safetensors"],
      upscale_models: ["4x-ultrasharp.pth"],
      default_checkpoint: "model.safetensors",
      default_vae: "Automatic",
      default_text_encoder: "Automatic",
    },
    presets: { presets: [basePreset] },
    queue: {
      queue_remaining: 0,
      jobs: [
        {
          id: "job-1",
          status: "completed",
          reusable_outputs: ["history-image.png"],
          output_filenames: ["history-image.png"],
        },
      ],
    },
    fetchQueueRequest: async () => ({ ok: true, data: { queue_remaining: 0, jobs: [] } }),
    fetchQueueJobRequest: async () => ({
      ok: true,
      data: {
        source: "host",
        queue_remaining: 0,
        job: {
          id: "job-1",
          status: "completed",
          reusable_outputs: ["history-image.png"],
          output_filenames: ["history-image.png"],
        },
      },
    }),
    fetchPromptHistoryRequest: async () => ({
      ok: true,
      data: {
        "job-1": {
          outputs: {
            "7": {
              images: [{ filename: "history-image.png", subfolder: "", type: "output" }],
            },
          },
        },
      },
    }),
    submitTxt2ImgRequest: async () => ({ ok: true, data: { mode: "translated", workflow_kind: "txt2img-sd15" } }),
    submitImg2ImgRequest: async () => ({ ok: true, data: { mode: "translated", workflow_kind: "img2img-sd15" } }),
    inspectPngInfoRequest: async () => ({
      ok: true,
      data: {
        status: "ok",
        source_type: "a1111",
        payload: {},
        metadata_items: {},
        apply_targets: ["txt2img", "img2img"],
      },
    }),
    submitExtrasRequest: async () => ({ ok: true, data: { output_assets: [], preview_data_url: "" } }),
  };
}

describe("rookieui modularization regression seams", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    document.head.innerHTML = "";
    window.sessionStorage.clear();
  });

  test("preserves visibility contract while switching top-level tabs", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    renderRookieUISidebar(container, createBootstrapState());

    const txt2imgPane = document.getElementById("rookieui-pane-txt2img");
    const img2imgPane = document.getElementById("rookieui-pane-img2img");
    expect(txt2imgPane?.classList.contains("is-active")).toBe(true);
    expect(txt2imgPane?.hidden).toBe(false);
    expect(img2imgPane?.classList.contains("is-active")).toBe(false);
    expect(img2imgPane?.hidden).toBe(true);

    document.getElementById("rookieui-tab-img2img")?.click();
    expect(txt2imgPane?.classList.contains("is-active")).toBe(false);
    expect(txt2imgPane?.hidden).toBe(true);
    expect(img2imgPane?.classList.contains("is-active")).toBe(true);
    expect(img2imgPane?.hidden).toBe(false);
  });

  test("keeps pane-local state across activation lifecycle after module extraction", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    renderRookieUISidebar(container, createBootstrapState());

    const promptInput = document.getElementById("rookieui-prompt");
    promptInput.value = "persisted modular prompt";
    promptInput.dispatchEvent(new Event("input", { bubbles: true }));

    document.getElementById("rookieui-tab-img2img")?.click();
    document.getElementById("rookieui-img2img-generation-mode-inpaint")?.click();
    expect(document.getElementById("rookieui-img2img-mode")?.value).toBe("inpaint");

    document.getElementById("rookieui-tab-extras")?.click();
    document.getElementById("rookieui-tab-img2img")?.click();
    expect(document.getElementById("rookieui-img2img-mode")?.value).toBe("inpaint");

    document.getElementById("rookieui-tab-txt2img")?.click();
    expect(document.getElementById("rookieui-prompt")?.value).toBe("persisted modular prompt");
  });

  test("keeps user form state when the host re-renders the sidebar panel", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    renderRookieUISidebar(container, createBootstrapState());

    const promptInput = document.getElementById("rookieui-prompt");
    promptInput.value = "persist across host panel reopen";
    promptInput.dispatchEvent(new Event("input", { bubbles: true }));

    const checkpointSelect = document.getElementById("rookieui-checkpoint");
    checkpointSelect.value = "alternate-model.safetensors";
    checkpointSelect.dispatchEvent(new Event("change", { bubbles: true }));

    document.getElementById("rookieui-tab-img2img")?.click();
    renderRookieUISidebar(container, createBootstrapState());

    expect(document.getElementById("rookieui-tab-img2img")?.classList.contains("is-active")).toBe(true);
    expect(document.getElementById("rookieui-prompt")?.value).toBe("persist across host panel reopen");
    expect(document.getElementById("rookieui-checkpoint")?.value).toBe("alternate-model.safetensors");
  });

  test("routes cross-pane apply payloads into extracted img2img pane via queue actions", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    renderRookieUISidebar(container, createBootstrapState());

    document.getElementById("rookieui-tab-queue")?.click();
    document.getElementById("rookieui-reuse-img2img-0")?.click();

    document.getElementById("rookieui-tab-img2img")?.click();
    expect(document.getElementById("rookieui-image-asset")?.value).toBe("history-image.png");
    expect(document.getElementById("rookieui-img2img-mode")?.value).toBe("img2img");
    expect(document.getElementById("rookieui-queue-status")?.textContent).toContain("Applied history-image.png");
  });

  test("keeps extras hires controls available and stateful after pane extraction", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    renderRookieUISidebar(container, createBootstrapState());

    document.getElementById("rookieui-tab-extras")?.click();
    const extrasHires = document.getElementById("rookieui-extras-hires-controls");
    expect(extrasHires).not.toBeNull();
    expect(extrasHires?.classList.contains("rookieui-shell__hires--integrated")).toBe(true);
    expect(document.querySelector("#rookieui-extras-hires-controls .rookieui-shell__hires-toggle")).not.toBeNull();

    const hiresToggle = document.getElementById("rookieui-extras-hires-enabled");
    hiresToggle.checked = false;
    hiresToggle.dispatchEvent(new Event("change", { bubbles: true }));

    document.getElementById("rookieui-tab-img2img")?.click();
    document.getElementById("rookieui-tab-extras")?.click();
    expect(document.getElementById("rookieui-extras-hires-enabled")?.checked).toBe(false);
  });
});
