import { beforeEach, describe, expect, test } from "vitest";

import { registerRookieUIBootstrapExtension } from "../rookieui_extension.js";

describe("registerRookieUIBootstrapExtension", () => {
  beforeEach(() => {
    delete window.__ROOKIEUI_BOOTSTRAP__;
    document.head.innerHTML = "";
    document.body.innerHTML = "";
  });

  test("registers a sidebar tab and renders the rookie shell", async () => {
    document.body.innerHTML = `
      <div class="sidebar-content-container">
        <div class="side-bar-panel">
          <div id="mock-sidebar-tabs"></div>
        </div>
      </div>
    `;
    let extensionDefinition;
    const fetchCalls = [];
    const app = {
      registerExtension(definition) {
        extensionDefinition = definition;
        return Promise.resolve(definition.setup());
      },
      api: {
        clientId: "socket-client-1",
        addEventListener() {},
        removeEventListener() {},
      },
      extensionManager: {
        registerSidebarTab(tab) {
          const host = document.getElementById("mock-sidebar-tabs");
          tab.render(host);
        },
      },
    };
    const fetchImpl = async (url, options = {}) => {
      fetchCalls.push([url, options]);
      if (url === "/rookieui/generate/txt2img") {
        const requestPayload = JSON.parse(options.body);
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              mode: "queued",
              workflow_kind: requestPayload.hires_enabled ? "txt2img-sd15-hires" : "txt2img-sd15",
              submission: { accepted: true, prompt_id: "prompt-123" },
            };
          },
        };
      }

      if (url === "/rookieui/generate/img2img") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              mode: "queued",
              workflow_kind: "inpaint-sd15",
              submission: { accepted: true, prompt_id: "prompt-456" },
            };
          },
        };
      }

      if (url === "/rookieui/pnginfo/inspect") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              status: "ok",
              source_type: "a1111",
              target_form: "txt2img",
              payload: {
                prompt: "parsed prompt",
                negative_prompt: "parsed negative",
                width: 768,
                height: 768,
                sampler_name: "euler_ancestral",
                image_asset: "pnginfo_asset.png",
              },
              metadata_items: {
                parameters: "parsed prompt",
                Prompt: "parsed prompt",
                "Negative prompt": "parsed negative",
              },
              apply_targets: ["txt2img", "img2img"],
              asset_handle: "pnginfo_asset.png",
              unsupported_fields: ["ENSD"],
              warnings: [],
            };
          },
        };
      }

      if (url === "/rookieui/extras/run") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              status: "ok",
              mode: "single_image",
              output_assets: ["rookieui_extras_output.png"],
              preview_asset: "rookieui_extras_output.png",
              preview_data_url: "data:image/png;base64,ZmFrZQ==",
              warnings: [],
            };
          },
        };
      }

      if (typeof url === "string" && url.startsWith("/view?")) {
        return {
          ok: true,
          status: 200,
          async blob() {
            return new Blob([Uint8Array.from([137, 80, 78, 71])], { type: "image/png" });
          },
        };
      }

      if (url.startsWith("/rookieui/queue/")) {
        const promptId = url.split("?")[0].split("/").pop();
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              source: "host",
              queue_remaining: 0,
              job: {
                id: promptId,
                status: "completed",
                output_filenames: ["history-image.png"],
                reusable_outputs: ["history-image.png"],
              },
            };
          },
        };
      }

      if (url.startsWith("/history/")) {
        const promptId = url.split("/").pop();
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              [promptId]: {
                outputs: {
                  "7": {
                    images: [
                      { filename: "history-image.png", subfolder: "", type: "output" },
                    ],
                  },
                },
              },
            };
          },
        };
      }

      if (url === "/rookieui/models") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              source: "host",
              checkpoints: ["dreamshaper.safetensors"],
              clip: ["clip-vit-l.safetensors"],
              clip_vision: ["clip-vision.safetensors"],
              controlnet: ["control_v11p_sd15_canny.safetensors"],
              diffusion_models: ["flux1-dev.safetensors"],
              vae: ["Automatic"],
              text_encoders: ["Automatic", "clip_g.safetensors"],
              embeddings: ["badhandv4.pt"],
              loras: ["detail_tweaker.safetensors"],
              ultralytics: ["sam2_b.pt"],
              unet: ["sdxl_base_unet.safetensors"],
              upscale_models: ["4x-ultrasharp.pth"],
              default_checkpoint: "dreamshaper.safetensors",
              default_vae: "Automatic",
              default_text_encoder: "Automatic",
              catalog: {
                surface_groups: [
                  {
                    id: "sd_generation",
                    title: "SD Generation",
                    categories: ["checkpoints", "vae", "text_encoders", "embeddings", "loras"],
                  },
                ],
                primary_model_category_by_family: {
                  sd15: "checkpoints",
                  sdxl: "checkpoints",
                  flux: "diffusion_models",
                  qwen_image: "diffusion_models",
                },
                categories: {
                  checkpoints: {
                    title: "Checkpoints",
                    items: ["dreamshaper.safetensors"],
                    default_value: "dreamshaper.safetensors",
                    sidebar_visible: true,
                  },
                },
              },
            };
          },
        };
      }

      if (url === "/rookieui/compatibility") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              source: "internal",
              samplers: [
                { id: "euler_ancestral", title: "Euler a", tier: "core", default: true, aliases: ["euler a"] },
                { id: "dpmpp_2m", title: "DPM++ 2M", tier: "core", default: false, aliases: ["dpm++ 2m"] },
              ],
              schedulers: [
                { id: "normal", title: "Normal", tier: "core", default: true, aliases: ["automatic"] },
                { id: "ddim_uniform", title: "DDIM Uniform", tier: "extended", default: false, aliases: ["ddim"] },
              ],
              runtime_profiles: [
                {
                  id: "balanced",
                  title: "Balanced",
                  summary: "Default RookieUI runtime policy with no extra host-memory hints.",
                  default: true,
                  experimental: false,
                  aliases: [],
                },
              ],
              dtype_profiles: [
                {
                  id: "automatic",
                  title: "Automatic",
                  summary: "Use the host default diffusion weight dtype policy.",
                  default: true,
                  experimental: false,
                  aliases: [],
                },
              ],
              newer_family_profiles: [
                {
                  id: "flux",
                  title: "Flux",
                  summary: "Experimental catalog entry for later complexity-gated newer-family support.",
                  default: false,
                  experimental: true,
                  aliases: [],
                },
              ],
            };
          },
        };
      }

      if (url.startsWith("/rookieui/queue")) {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              source: "host",
              queue_remaining: 2,
              jobs: [
                {
                  id: "prompt-history",
                  status: "completed",
                  output_filenames: ["history-image.png"],
                  reusable_outputs: ["history-image.png"],
                },
              ],
            };
          },
        };
      }

      if (url === "/rookieui/presets") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              source: "host",
              presets: [
                {
                  id: "sd15",
                  title: "Stable Diffusion 1.5",
                  profile: "sd15",
                  base_family: "sd15",
                  checkpoint_name: "dreamshaper.safetensors",
                  vae_name: "Automatic",
                  text_encoder_name: "Automatic",
                  width: 512,
                  height: 512,
                  steps: 28,
                  cfg_scale: 7,
                  sampler_name: "euler_ancestral",
                  scheduler_name: "normal",
                  clip_skip: 1,
                },
                {
                  id: "sdxl",
                  title: "Stable Diffusion XL",
                  profile: "sdxl",
                  base_family: "sdxl",
                  checkpoint_name: "dreamshaper.safetensors",
                  vae_name: "Automatic",
                  text_encoder_name: "clip_g.safetensors",
                  width: 1024,
                  height: 1024,
                  steps: 28,
                  cfg_scale: 7,
                  sampler_name: "dpmpp_2m",
                  scheduler_name: "karras",
                  clip_skip: 1,
                },
                {
                  id: "flux",
                  title: "Flux",
                  profile: "flux",
                  base_family: "flux",
                  checkpoint_name: "dreamshaper.safetensors",
                  vae_name: "Automatic",
                  text_encoder_name: "Automatic",
                  width: 896,
                  height: 1152,
                  steps: 20,
                  cfg_scale: 1,
                  sampler_name: "euler",
                  scheduler_name: "beta",
                  clip_skip: 1,
                },
                {
                  id: "qwen_image",
                  title: "Qwen-Image",
                  profile: "qwen_image",
                  base_family: "qwen_image",
                  checkpoint_name: "dreamshaper.safetensors",
                  vae_name: "Automatic",
                  text_encoder_name: "Automatic",
                  width: 1024,
                  height: 1024,
                  steps: 8,
                  cfg_scale: 1,
                  sampler_name: "dpmpp_2m",
                  scheduler_name: "normal",
                  clip_skip: 1,
                },
              ],
            };
          },
        };
      }

      return {
        ok: true,
        async json() {
          return {
            service: "rookieui",
            visibility: "internal",
            shell_version: "0.1.0",
            host_surfaces: ["standalone-web", "desktop"],
            features: {
              sidebarShell: true,
              capabilityBootstrap: true,
              parityMatrix: true,
              workflowTranslation: true,
              compatibilityLayer: true,
              txt2img: true,
              img2img: true,
              pngInfo: true,
              queue: false,
            },
            tabs: [
              { id: "txt2img", title: "Txt2Img", state: "active", enabled: true },
              { id: "img2img", title: "Img2Img", state: "active", enabled: true },
              { id: "extras", title: "Extras", state: "active", enabled: true },
              { id: "pnginfo", title: "PNG Info", state: "active", enabled: true },
            ],
            parity: {
              profiles: [
                {
                  id: "sd15",
                  title: "Stable Diffusion 1.5",
                  base_family: "sd15",
                  prompt_encoder: "clip_text_encode",
                  default_width: 512,
                  default_height: 512,
                  default_steps: 28,
                  default_cfg_scale: 7,
                  default_sampler: "euler_ancestral",
                  default_scheduler: "normal",
                  default_clip_skip: 1,
                  supports_clip_skip: true,
                  notes: [],
                },
                {
                  id: "sdxl",
                  title: "Stable Diffusion XL",
                  base_family: "sdxl",
                  prompt_encoder: "clip_text_encode_sdxl",
                  default_width: 1024,
                  default_height: 1024,
                  default_steps: 28,
                  default_cfg_scale: 7,
                  default_sampler: "dpmpp_2m",
                  default_scheduler: "karras",
                  default_clip_skip: 1,
                  supports_clip_skip: false,
                  notes: [],
                },
                {
                  id: "flux",
                  title: "Flux",
                  base_family: "sdxl",
                  prompt_encoder: "clip_text_encode_sdxl",
                  default_width: 896,
                  default_height: 1152,
                  default_steps: 20,
                  default_cfg_scale: 1,
                  default_sampler: "euler",
                  default_scheduler: "beta",
                  default_clip_skip: 1,
                  supports_clip_skip: false,
                  notes: [],
                },
                {
                  id: "qwen_image",
                  title: "Qwen-Image",
                  base_family: "sdxl",
                  prompt_encoder: "clip_text_encode_sdxl",
                  default_width: 1024,
                  default_height: 1024,
                  default_steps: 8,
                  default_cfg_scale: 1,
                  default_sampler: "dpmpp_2m",
                  default_scheduler: "normal",
                  default_clip_skip: 1,
                  supports_clip_skip: false,
                  notes: [],
                },
              ],
            },
            routes: [
              "/rookieui/capabilities",
              "/rookieui/pnginfo/inspect",
              "/rookieui/generate/txt2img",
              "/rookieui/generate/img2img",
              "/rookieui/extras/run",
            ],
          };
        },
      };
    };

    await registerRookieUIBootstrapExtension({
      app,
      windowRef: window,
      documentRef: document,
      fetchImpl,
    });

    expect(extensionDefinition.name).toBe("ComfyUI-RookieUI");
    expect(window.__ROOKIEUI_BOOTSTRAP__).toMatchObject({
      extensionName: "ComfyUI-RookieUI",
      hostSurface: "standalone-web",
      hostSurfaceSupported: true,
      capabilitySource: "server",
    });
    expect(document.getElementById("mock-sidebar-tabs").style.minWidth).toBe("980px");
    expect(document.querySelector(".side-bar-panel").style.minWidth).toBe("980px");
    expect(document.querySelector(".sidebar-content-container").style.minWidth).toBe("980px");
    expect(document.getElementById("mock-sidebar-tabs").dataset.theme).toBe("normal");
    expect(document.getElementById("rookieui-styles").href).toContain("20260410-r30-live-preview-runtime");
    expect(window.__ROOKIEUI_BOOTSTRAP__.models.catalog.primary_model_category_by_family.flux).toBe(
      "diffusion_models",
    );
    expect(document.getElementById("mock-sidebar-tabs").textContent).toContain("RookieUI");
    expect(document.getElementById("rookieui-header-version").textContent).toBe("v0.1.0");
    expect(document.getElementById("rookieui-view-github").textContent).toBe("View on GitHub");
    expect(document.getElementById("rookieui-txt2img-quicksettings")).not.toBeNull();
    expect(document.getElementById("rookieui-low-bits-quicksetting")).not.toBeNull();
    expect(document.getElementById("rookieui-modules-quicksetting").textContent).toContain("VAE");
    expect(document.getElementById("rookieui-modules-quicksetting").textContent).not.toContain(
      "VAE / Text Encoder",
    );
    expect(document.getElementById("rookieui-text-encoder").hidden).toBe(true);
    expect(document.getElementById("rookieui-txt2img-open-queue-icon")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-open-queue-icon").textContent).toContain("📂");
    expect(document.getElementById("rookieui-txt2img-open-pnginfo").textContent).toContain("📋");
    expect(document.getElementById("rookieui-txt2img-action-target")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-apply-action-target")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-apply-action-target").textContent).toContain("🖌️");
    expect(document.getElementById("rookieui-txt2img-preview-extras").textContent).toContain("📐");
    expect(
      document.querySelectorAll(
        "#rookieui-pane-txt2img .rookieui-shell__preview-toolbar .rookieui-shell__mini-action--icon",
      ).length,
    ).toBe(6);
    expect(document.getElementById("mock-sidebar-tabs").textContent).not.toContain("Rookie Mode");
    expect(document.getElementById("mock-sidebar-tabs").textContent).not.toContain("Server capabilities");
    expect(document.getElementById("mock-sidebar-tabs").textContent).toContain("Txt2Img");
    expect(document.getElementById("mock-sidebar-tabs").textContent).toContain("Img2Img");
    expect(document.getElementById("mock-sidebar-tabs").textContent).toContain("Extras");
    expect(document.getElementById("mock-sidebar-tabs").textContent).toContain("PNG Info");
    expect(document.getElementById("mock-sidebar-tabs").textContent).toContain("Queue");
    expect(document.getElementById("mock-sidebar-tabs").textContent).not.toContain("Settings");
    expect(document.getElementById("rookieui-profile")).toBeNull();
    expect(document.getElementById("rookieui-img2img-profile")).toBeNull();
    expect(document.getElementById("mock-sidebar-tabs").textContent).not.toContain("Shared Model Inventory");
    expect(document.getElementById("rookieui-checkpoint-list")).toBeNull();
    expect(document.getElementById("rookieui-vae-list")).toBeNull();
    expect(document.getElementById("rookieui-text-encoder-list")).toBeNull();
    expect(document.getElementById("rookieui-prompt").value).toBe("");
    expect(document.getElementById("rookieui-prompt-counter").textContent).toBe("0/75");
    expect(document.getElementById("rookieui-prompt").placeholder).toContain("Ctrl+Enter to Generate");
    expect(document.getElementById("rookieui-negative-prompt").placeholder).toContain("Ctrl+Enter to Generate");
    document.getElementById("rookieui-prompt").value = "  \n  ";
    document.getElementById("rookieui-prompt").dispatchEvent(new Event("input", { bubbles: true }));
    expect(document.getElementById("rookieui-prompt").value).toBe("");
    expect(document.getElementById("rookieui-prompt-counter").textContent).toBe("0/75");
    expect(document.querySelector("#rookieui-pane-txt2img .rookieui-shell__prompt-field .rookieui-shell__field-label")).toBeNull();
    expect(document.getElementById("rookieui-cfg-scale").step).toBe("0.01");
    expect(document.getElementById("rookieui-hires-scale").step).toBe("0.01");
    expect(document.getElementById("rookieui-hires-denoise").step).toBe("0.01");
    expect(document.getElementById("rookieui-img2img-cfg-scale").step).toBe("0.01");
    expect(document.getElementById("rookieui-denoise-strength").step).toBe("0.01");
    expect(document.getElementById("rookieui-steps").step).toBe("1");
    expect(document.getElementById("rookieui-sampler").tagName).toBe("SELECT");
    expect(document.getElementById("rookieui-scheduler").tagName).toBe("SELECT");
    expect(document.getElementById("rookieui-steps-slider")).not.toBeNull();
    expect(document.getElementById("rookieui-width-slider")).not.toBeNull();
    expect(document.getElementById("rookieui-batch-count")).not.toBeNull();
    const hiresToggle = document.getElementById("rookieui-hires-enabled");
    expect(hiresToggle.classList.contains("rookieui-shell__checkbox")).toBe(true);
    expect(hiresToggle.classList.contains("rookieui-shell__input")).toBe(false);
    expect(hiresToggle.closest(".rookieui-shell__hires-toggle")).not.toBeNull();
    expect(document.getElementById("rookieui-pane-txt2img").classList.contains("is-active")).toBe(true);
    expect(document.getElementById("rookieui-pane-img2img").classList.contains("is-active")).toBe(false);
    expect(document.getElementById("rookieui-pane-txt2img").hidden).toBe(false);
    expect(document.getElementById("rookieui-pane-img2img").hidden).toBe(true);
    document.getElementById("rookieui-txt2img-open-queue-icon").click();
    expect(document.getElementById("rookieui-pane-queue").classList.contains("is-active")).toBe(true);
    document.getElementById("rookieui-tab-txt2img").click();
    document.getElementById("rookieui-txt2img-action-target").value = "extras";
    document.getElementById("rookieui-txt2img-apply-action-target").click();
    expect(document.getElementById("rookieui-pane-extras").classList.contains("is-active")).toBe(true);
    document.getElementById("rookieui-tab-txt2img").click();
    document.getElementById("rookieui-txt2img-preview-img2img").click();
    expect(document.getElementById("rookieui-pane-img2img").classList.contains("is-active")).toBe(true);
    document.getElementById("rookieui-tab-txt2img").click();
    expect(document.getElementById("rookieui-advanced-controls").textContent).toContain("Hires. fix");
    expect(document.querySelector("#rookieui-advanced-controls .rookieui-shell__hires-toggle")).not.toBeNull();
    expect(document.getElementById("rookieui-advanced-controls").textContent).not.toContain(
      "Second latent pass with bounded rookie-safe defaults.",
    );
    expect(document.getElementById("rookieui-txt2img-workspace-tab-textual-inversion")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-workspace-tab-lora")).not.toBeNull();

    document.getElementById("rookieui-prompt").value = "sunset harbor";
    document.getElementById("rookieui-prompt").dispatchEvent(new Event("input", { bubbles: true }));
    app.api.clientId = "socket-client-2";
    // CRITICAL: regression matrix must keep Clip Skip editable across all preset profiles.
    const presetClipSkipMatrix = [
      { id: "sd15", textEncoderHidden: true, ignoredHint: false },
      { id: "sdxl", textEncoderHidden: true, ignoredHint: true },
      { id: "flux", textEncoderHidden: false, ignoredHint: true },
      { id: "qwen_image", textEncoderHidden: false, ignoredHint: true },
    ];
    for (const matrixRow of presetClipSkipMatrix) {
      document.getElementById("rookieui-preset").value = matrixRow.id;
      document.getElementById("rookieui-preset").dispatchEvent(new Event("change", { bubbles: true }));
      expect(document.getElementById("rookieui-text-encoder").hidden).toBe(matrixRow.textEncoderHidden);
      expect(document.getElementById("rookieui-clip-skip").disabled).toBe(false);
      expect(document.getElementById("rookieui-clip-skip-slider").disabled).toBe(false);
      expect(document.getElementById("rookieui-clip-skip").dataset.executionHint).toBe(
        matrixRow.ignoredHint ? "ignored" : undefined,
      );
    }
    document.getElementById("rookieui-preset").value = "sd15";
    document.getElementById("rookieui-preset").dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("rookieui-modules-quicksetting").textContent).not.toContain("VAE / Text Encoder");
    expect(document.getElementById("rookieui-text-encoder").hidden).toBe(true);
    document.getElementById("rookieui-low-bits").value = "automatic";
    document.getElementById("rookieui-hires-enabled").checked = true;
    document.getElementById("rookieui-hires-scale").value = "1.8";
    document.getElementById("rookieui-batch-count").value = "2";
    document.getElementById("rookieui-batch-count").dispatchEvent(new Event("input", { bubbles: true }));
    expect(document.getElementById("rookieui-batch-count-slider").value).toBe("2");
    document.getElementById("rookieui-txt2img-workspace-tab-textual-inversion").click();
    document.getElementById("rookieui-txt2img-embedding-item-0").click();
    expect(document.getElementById("rookieui-prompt").value).toContain("embedding:badhandv4.pt");
    expect(document.getElementById("rookieui-prompt-counter").textContent).not.toBe("0/75");
    document.getElementById("rookieui-txt2img-workspace-tab-lora").click();
    document.getElementById("rookieui-txt2img-lora-item-0").click();
    document.getElementById("rookieui-lora-strength-model").value = "0.9";
    document.getElementById("rookieui-lora-strength-clip").value = "0.7";
    document.getElementById("rookieui-txt2img-workspace-tab-generation").click();
    document.getElementById("rookieui-cfg-scale").value = "7.25";
    document.getElementById("rookieui-cfg-scale").dispatchEvent(new Event("input", { bubbles: true }));
    document.getElementById("rookieui-txt2img-form").dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(document.getElementById("rookieui-txt2img-status").textContent).toMatch(/(Queued prompt|Completed:) prompt-123/);
    document.getElementById("rookieui-tab-img2img").click();
    expect(document.getElementById("rookieui-pane-txt2img").classList.contains("is-active")).toBe(false);
    expect(document.getElementById("rookieui-pane-img2img").classList.contains("is-active")).toBe(true);
    expect(document.getElementById("rookieui-pane-txt2img").hidden).toBe(true);
    expect(document.getElementById("rookieui-pane-img2img").hidden).toBe(false);
    // IMPORTANT: regression guard — mask upload must remain clickable in Img2Img mode so users can preload masks before switching to inpaint.
    expect(document.getElementById("rookieui-img2img-mask-file").disabled).toBe(false);
    expect(document.getElementById("rookieui-img2img-mask-dropzone").hidden).toBe(false);
    expect(document.getElementById("rookieui-img2img-hires-controls")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-mask-editor")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-text-encoder").hidden).toBe(true);
    for (const matrixRow of presetClipSkipMatrix) {
      document.getElementById("rookieui-img2img-preset").value = matrixRow.id;
      document.getElementById("rookieui-img2img-preset").dispatchEvent(new Event("change", { bubbles: true }));
      expect(document.getElementById("rookieui-img2img-text-encoder").hidden).toBe(matrixRow.textEncoderHidden);
      expect(document.getElementById("rookieui-img2img-clip-skip").disabled).toBe(false);
      expect(document.getElementById("rookieui-img2img-clip-skip-slider").disabled).toBe(false);
      expect(document.getElementById("rookieui-img2img-clip-skip").dataset.executionHint).toBe(
        matrixRow.ignoredHint ? "ignored" : undefined,
      );
    }
    document.getElementById("rookieui-img2img-preset").value = "sd15";
    document.getElementById("rookieui-img2img-preset").dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("rookieui-img2img-modules-quicksetting").textContent).not.toContain("VAE / Text Encoder");
    expect(document.getElementById("rookieui-img2img-text-encoder").hidden).toBe(true);
    expect(document.getElementById("rookieui-img2img-clip-skip").disabled).toBe(false);
    document.getElementById("rookieui-img2img-mode").value = "batch";
    document.getElementById("rookieui-img2img-mode").dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("rookieui-img2img-mask-editor").hidden).toBe(true);
    document.getElementById("rookieui-img2img-mode").value = "img2img";
    document.getElementById("rookieui-img2img-mode").dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("rookieui-img2img-mask-editor").hidden).toBe(false);
    expect(document.getElementById("rookieui-image-asset").value).toBe("");
    document.getElementById("rookieui-img2img-form").dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.getElementById("rookieui-img2img-status").textContent).toContain(
      "Image asset or uploaded image is required",
    );
    expect(fetchCalls.filter(([url]) => url === "/rookieui/generate/img2img")).toHaveLength(0);
    document.getElementById("rookieui-img2img-mode").value = "inpaint";
    document.getElementById("rookieui-img2img-mode").dispatchEvent(new Event("change", { bubbles: true }));
    document.getElementById("rookieui-image-asset").value = "source-asset";
    document.getElementById("rookieui-mask-asset").value = "mask-asset";
    document.getElementById("rookieui-img2img-form").dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(document.getElementById("rookieui-img2img-status").textContent).toMatch(/(Queued prompt|Completed:) prompt-456/);
    document.getElementById("rookieui-tab-txt2img").click();
    expect(document.getElementById("rookieui-cfg-scale").value).toBe("7.25");
    document.getElementById("rookieui-tab-img2img").click();
    expect(document.getElementById("rookieui-img2img-mode").value).toBe("inpaint");
    document.getElementById("rookieui-tab-txt2img").click();
    document.getElementById("rookieui-txt2img-preview").innerHTML =
      '<img class="rookieui-shell__preview-image" src="data:image/png;base64,ZmFrZQ==" alt="preview">';
    document.getElementById("rookieui-txt2img-preview-img2img").click();
    for (let attempt = 0; attempt < 20; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 10));
      if (document.getElementById("rookieui-img2img-mode").value === "img2img") {
        break;
      }
    }
    expect(document.getElementById("rookieui-pane-img2img").classList.contains("is-active")).toBe(true);
    const transferredPreviewImage = document.querySelector("#rookieui-img2img-preview img");
    expect(transferredPreviewImage).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-mode").value).toBe("img2img");
    document.getElementById("rookieui-tab-pnginfo").click();
    expect(document.getElementById("rookieui-pane-pnginfo").classList.contains("is-active")).toBe(true);
    expect(document.getElementById("rookieui-pane-pnginfo").hidden).toBe(false);
    const pngInfoLeftColumn = document.querySelector(
      "#rookieui-pane-pnginfo .rookieui-shell__workspace-grid--pnginfo .rookieui-shell__workspace-column",
    );
    expect(pngInfoLeftColumn?.firstElementChild?.querySelector("#rookieui-pnginfo-preview")).not.toBeNull();
    expect(document.getElementById("rookieui-pnginfo-input")).toBeNull();
    expect(document.getElementById("rookieui-pnginfo-submit")).toBeNull();
    const OriginalFileReader = global.FileReader;
    global.FileReader = class MockFileReader {
      readAsDataURL() {
        this.result = "data:image/png;base64,ZmFrZQ==";
        this.onload?.();
      }
    };
    const pngFileInput = document.getElementById("rookieui-pnginfo-image-file");
    const pngBytes = Uint8Array.from([
      137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82, 0, 0, 0, 1, 0, 0, 0, 1,
      8, 6, 0, 0, 0, 31, 21, 196, 137, 0, 0, 0, 12, 73, 68, 65, 84, 120, 156, 99, 248, 255, 31,
      0, 3, 3, 2, 0, 238, 217, 173, 142, 0, 0, 0, 0, 73, 69, 78, 68, 174, 66, 96, 130,
    ]);
    const pngFile = new File([pngBytes], "parsed.png", { type: "image/png" });
    Object.defineProperty(pngFileInput, "files", { configurable: true, value: [pngFile] });
    pngFileInput.dispatchEvent(new Event("change", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    global.FileReader = OriginalFileReader;
    expect(document.getElementById("rookieui-pnginfo-status").textContent).toContain("Ready to apply txt2img fields");
    expect(document.getElementById("rookieui-pnginfo-apply-txt2img").disabled).toBe(false);
    document.getElementById("rookieui-pnginfo-apply-txt2img").click();
    expect(document.getElementById("rookieui-pnginfo-status").textContent).toContain("Applied txt2img fields");
    document.getElementById("rookieui-tab-txt2img").click();
    expect(document.getElementById("rookieui-prompt").value).toBe("parsed prompt");
    expect(document.getElementById("rookieui-width").value).toBe("768");
    expect(document.getElementById("rookieui-pnginfo-unsupported").textContent).toContain("ENSD");
    expect(document.getElementById("rookieui-pnginfo-metadata").textContent).toContain("parsed prompt");
    expect(document.getElementById("rookieui-pnginfo-metadata").textContent).toContain("parsed negative");
    document.getElementById("rookieui-tab-queue").click();
    document.getElementById("rookieui-reuse-img2img-0").click();

    expect(document.getElementById("rookieui-queue-status").textContent).toContain("Applied history-image.png to img2img");
    document.getElementById("rookieui-tab-img2img").click();
    expect(document.getElementById("rookieui-image-asset").value).toBe("history-image.png");
    document.getElementById("rookieui-tab-extras").click();
    expect(document.getElementById("rookieui-pane-extras").classList.contains("is-active")).toBe(true);
    expect(document.querySelector(".rookieui-shell__footer").textContent).toContain("host: standalone-web");
    expect(fetchCalls.some(([url]) => url === "/rookieui/generate/txt2img")).toBe(true);
    expect(fetchCalls.some(([url]) => url === "/rookieui/generate/img2img")).toBe(true);
    expect(fetchCalls.some(([url]) => String(url).startsWith("/rookieui/queue"))).toBe(true);
    expect(fetchCalls.some(([url]) => url === "/rookieui/pnginfo/inspect")).toBe(true);
    expect(fetchCalls.some(([url]) => url === "/rookieui/models")).toBe(true);
    expect(fetchCalls.some(([url]) => url === "/rookieui/presets")).toBe(true);
    expect(fetchCalls.some(([url]) => url === "/rookieui/compatibility")).toBe(true);
    const txt2imgCall = fetchCalls.find(([url]) => url === "/rookieui/generate/txt2img");
    expect(JSON.parse(txt2imgCall[1].body).hires_enabled).toBe(true);
    expect(JSON.parse(txt2imgCall[1].body).hires_scale).toBe(1.8);
    expect(JSON.parse(txt2imgCall[1].body).batch_count).toBe(2);
    expect(JSON.parse(txt2imgCall[1].body).dtype_profile).toBe("automatic");
    expect(JSON.parse(txt2imgCall[1].body).lora_name).toBe("detail_tweaker.safetensors");
    expect(JSON.parse(txt2imgCall[1].body).lora_strength_model).toBe(0.9);
    expect(JSON.parse(txt2imgCall[1].body).lora_strength_clip).toBe(0.7);
    expect(JSON.parse(txt2imgCall[1].body).client_id).toBe("socket-client-2");
    const img2imgCall = fetchCalls.find(([url]) => url === "/rookieui/generate/img2img");
    expect(JSON.parse(img2imgCall[1].body).hires_enabled).toBe(false);
    expect(JSON.parse(img2imgCall[1].body).client_id).toBe("socket-client-2");
    expect(
      fetchCalls.some(
        ([url]) =>
          String(url).startsWith("/rookieui/queue/prompt-123") && String(url).includes("client_id=socket-client-2"),
      ),
    ).toBe(true);
  });

  test("installs a legacy launcher when sidebar tabs are unavailable", async () => {
    const app = {
      registerExtension(definition) {
        return Promise.resolve(definition.setup());
      },
    };

    await registerRookieUIBootstrapExtension({
      app,
      windowRef: window,
      documentRef: document,
      fetchImpl: async () => ({ ok: false, status: 404 }),
    });

    expect(document.getElementById("rookieui-legacy-launcher")).not.toBeNull();
    document.getElementById("rookieui-legacy-launcher").click();
    expect(document.getElementById("rookieui-legacy-panel").hidden).toBe(false);
    expect(document.getElementById("rookieui-legacy-panel").textContent).toContain("RookieUI");
  });

  test("records desktop host surface support in bootstrap state", async () => {
    const windowRef = {
      __COMFYUI_DESKTOP__: true,
      fetch: async () => ({ ok: false, status: 404 }),
    };
    const app = {
      registerExtension(definition) {
        return Promise.resolve(definition.setup());
      },
      extensionManager: {
        registerSidebarTab() {},
      },
    };

    await registerRookieUIBootstrapExtension({
      app,
      windowRef,
      documentRef: document,
      fetchImpl: async () => ({
        ok: true,
        status: 200,
        async json() {
          return {
            service: "rookieui",
            visibility: "internal",
            shell_version: "0.1.0",
            host_surfaces: ["standalone-web", "desktop"],
            features: {
              sidebarShell: true,
              capabilityBootstrap: true,
              parityMatrix: true,
              workflowTranslation: true,
              compatibilityLayer: true,
              txt2img: true,
              img2img: true,
              pngInfo: true,
              queue: true,
            },
            tabs: [{ id: "overview", title: "Overview", state: "active", enabled: true }],
            parity: { profiles: [], sampler_aliases: { samplers: {}, scheduler_overrides: {}, supported_schedulers: [] } },
            routes: ["/rookieui/capabilities"],
          };
        },
      }),
    });

    expect(windowRef.__ROOKIEUI_BOOTSTRAP__).toMatchObject({
      hostSurface: "desktop",
      hostSurfaceSupported: true,
    });
  });
});
