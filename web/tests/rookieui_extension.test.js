import { beforeEach, describe, expect, test, vi } from "vitest";

import { ROOKIEUI_ASSET_REVISION } from "../rookieui_asset_revision.js";
import { createDefaultCapabilities } from "../rookieui_api.js";
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
      if (url === "/rookieui/capabilities") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              ...createDefaultCapabilities(),
              shell_version: "0.1.0",
            };
          },
        };
      }

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
        const requestPayload = JSON.parse(options.body);
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              mode: "queued",
              workflow_kind: requestPayload.hires_enabled ? "inpaint-sd15-hires" : "inpaint-sd15",
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

      if (typeof url === "string" && url.startsWith("/rookieui/prompt-tools/state")) {
        const namespace = url.includes("namespace=img2img_negative")
          ? "img2img_negative"
          : url.includes("namespace=img2img_prompt")
            ? "img2img_prompt"
            : url.includes("namespace=txt2img_negative")
              ? "txt2img_negative"
              : "txt2img_prompt";
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              contract: { version: "r145f141f142-20260418", surface: "prompt_tools_state" },
              namespace,
              state: {
                namespace,
                workbench_open: false,
                active_panel: "editor",
                draft_prompt: "",
                selected_entry_id: "",
              },
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
              diffusion_models: [
                "flux1-dev.safetensors",
                "qwen-image.safetensors",
                "qwen_image_edit_fp8_e4m3fn.safetensors",
                "klein-flux2.safetensors",
                "lumina2.safetensors",
                "zImageTurboNSFW_21BF16AIO.safetensors",
                "wan2_2b.safetensors",
                "animaPencilXL_v500.safetensors",
              ],
              vae: ["Automatic", "qwen_image_vae.safetensors"],
              text_encoders: [
                "QwenImageTEModel_.safetensors",
                "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                "FluxT5XXL.safetensors",
                "KleinT5XXL.safetensors",
                "LuminaTEModel.safetensors",
                "WanTextEncoder.safetensors",
                "AnimaTextEncoder.safetensors",
                "clip_g.safetensors",
              ],
              embeddings: ["badhandv4.pt"],
              loras: [
                "detail_tweaker.safetensors",
                "Flux_2-Turbo-LoRA_comfyui.safetensors",
                "Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors",
              ],
              ultralytics: ["sam2_b.pt"],
              unet: ["sdxl_base_unet.safetensors"],
              upscale_models: ["4x-ultrasharp.pth"],
              default_checkpoint: "dreamshaper.safetensors",
              default_vae: "Automatic",
              default_text_encoder: "QwenImageTEModel_.safetensors",
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
                  qwen_image_edit: "diffusion_models",
                  klein: "diffusion_models",
                  lumina: "diffusion_models",
                  zit: "diffusion_models",
                  wan: "diffusion_models",
                  anima: "diffusion_models",
                },
                categories: {
                  checkpoints: {
                    title: "Checkpoints",
                    items: ["dreamshaper.safetensors"],
                    default_value: "dreamshaper.safetensors",
                    sidebar_visible: true,
                  },
                  diffusion_models: {
                    title: "Diffusion Models",
                    items: [
                      "flux1-dev.safetensors",
                      "qwen-image.safetensors",
                      "qwen_image_edit_fp8_e4m3fn.safetensors",
                      "klein-flux2.safetensors",
                      "lumina2.safetensors",
                      "zImageTurboNSFW_21BF16AIO.safetensors",
                      "wan2_2b.safetensors",
                      "animaPencilXL_v500.safetensors",
                    ],
                    default_value: "flux1-dev.safetensors",
                    sidebar_visible: false,
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
                {
                  id: "qwen_image",
                  title: "Qwen-Image",
                  summary: "Experimental catalog entry for later complexity-gated newer-family support.",
                  default: false,
                  experimental: true,
                  aliases: [],
                },
                {
                  id: "klein",
                  title: "Klein (Flux.2)",
                  summary: "Experimental catalog entry for later complexity-gated newer-family support.",
                  default: false,
                  experimental: true,
                  aliases: [],
                },
                {
                  id: "lumina",
                  title: "Lumina",
                  summary: "Experimental catalog entry for later complexity-gated newer-family support.",
                  default: false,
                  experimental: true,
                  aliases: [],
                },
                {
                  id: "zit",
                  title: "ZiT (Z-Image-Turbo)",
                  summary: "Experimental catalog entry for later complexity-gated newer-family support.",
                  default: false,
                  experimental: true,
                  aliases: [],
                },
                {
                  id: "wan",
                  title: "Wan",
                  summary: "Experimental catalog entry for later complexity-gated newer-family support.",
                  default: false,
                  experimental: true,
                  aliases: [],
                },
                {
                  id: "anima",
                  title: "Anima",
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

      if (url === "/rookieui/controlnet/model_list") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              source: "host",
              contract: {
                version: "r72-20260412",
                ui_variant: "integrated_sidebar_controlnet",
                unit_count: 3,
                advanced_contract: { version: "r111-20260415", runtime_state: "rookieui_native_advanced_runtime" },
              },
              model_list: ["control_v11p_sd15_canny.safetensors", "control_v11f1p_sd15_depth.safetensors"],
              default_model: "control_v11p_sd15_canny.safetensors",
            };
          },
        };
      }

      if (url === "/rookieui/controlnet/module_list") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              source: "internal",
              contract: {
                version: "r72-20260412",
                ui_variant: "integrated_sidebar_controlnet",
                unit_count: 3,
                advanced_contract: { version: "r111-20260415", runtime_state: "rookieui_native_advanced_runtime" },
              },
              module_list: ["none", "canny", "depth", "openpose"],
              default_module: "none",
            };
          },
        };
      }

      if (url === "/rookieui/controlnet/control_types") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              source: "internal",
              contract: {
                version: "r72-20260412",
                ui_variant: "integrated_sidebar_controlnet",
                unit_count: 3,
                advanced_contract: { version: "r111-20260415", runtime_state: "rookieui_native_advanced_runtime" },
              },
              control_type_order: ["All", "Canny", "Depth", "OpenPose", "SoftEdge", "Tile"],
              default_type: "All",
              control_types: {
                All: {
                  module_list: ["none", "canny", "depth", "openpose"],
                  model_list: ["control_v11p_sd15_canny.safetensors", "control_v11f1p_sd15_depth.safetensors"],
                  default_option: "none",
                },
                Canny: {
                  module_list: ["none", "canny"],
                  model_list: ["control_v11p_sd15_canny.safetensors"],
                  default_option: "canny",
                },
              },
            };
          },
        };
      }

      if (url === "/rookieui/adetailer/catalog") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              source: "host",
              contract: {
                version: "r74f77-20260414",
                ui_variant: "a1111_integrated_detailer",
                unit_count: 4,
                prompt_tokens: ["[PROMPT]", "[SEP]", "[SKIP]"],
                controlnet_modes: ["none", "passthrough", "custom"],
                detector_provider_families: ["none", "ultralytics_bbox", "ultralytics_segm", "mediapipe_face"],
                detector_result_contract: "rookieui_detection_regions_v1",
                mask_filter_methods: ["Area", "Confidence"],
                mask_merge_modes: ["None", "Merge", "Merge and Invert"],
                defaults: {
                  detector: "None",
                  detector_classes: "",
                  confidence: 0.3,
                  mask_filter_method: "Area",
                  mask_k: 0,
                  mask_min_ratio: 0.0,
                  mask_max_ratio: 1.0,
                  x_offset: 0,
                  y_offset: 0,
                  dilate_erode: 4,
                  mask_merge_mode: "None",
                  mask_blur: 4,
                  denoising_strength: 0.4,
                  inpaint_only_masked: true,
                  inpaint_padding: 32,
                  use_inpaint_size: false,
                  inpaint_width: 512,
                  inpaint_height: 512,
                  use_steps: false,
                  steps: 28,
                  use_cfg_scale: false,
                  cfg_scale: 7.0,
                  use_checkpoint: false,
                  checkpoint_name: "Use same checkpoint",
                  use_vae: false,
                  vae_name: "Use same VAE",
                  use_sampler: false,
                  sampler_name: "DPM++ 2M Karras",
                  scheduler_name: "Use same scheduler",
                  use_noise_multiplier: false,
                  noise_multiplier: 1.0,
                  use_clip_skip: false,
                  clip_skip: 1,
                  restore_face: false,
                },
              },
              detector_list: ["None", "face_yolov8n.pt", "yolov8x-worldv2.pt", "mediapipe_face_full"],
              detectors: [
                { id: "None", label: "None", family: "none", source: "builtin", supports_class_filter: false },
                {
                  id: "face_yolov8n.pt",
                  label: "face_yolov8n.pt",
                  family: "ultralytics_bbox",
                  source: "host",
                  supports_class_filter: false,
                },
                {
                  id: "yolov8x-worldv2.pt",
                  label: "yolov8x-worldv2.pt",
                  family: "ultralytics_bbox",
                  source: "host",
                  supports_class_filter: true,
                },
                {
                  id: "mediapipe_face_full",
                  label: "mediapipe_face_full",
                  family: "mediapipe_face",
                  source: "builtin",
                  supports_class_filter: false,
                },
              ],
              default_detector: "None",
              prompt_tokens: ["[PROMPT]", "[SEP]", "[SKIP]"],
              skip_img2img_surfaces: ["img2img"],
              controlnet_modes: ["none", "passthrough", "custom"],
              controlnet_model_list: ["control_v11p_sd15_canny.safetensors"],
              controlnet_default_model: "",
              controlnet_module_list: ["none", "openpose"],
              controlnet_default_module: "none",
              checkpoint_choices: ["dreamshaper.safetensors"],
              vae_choices: ["Automatic"],
              sampler_choices: ["Euler a", "DPM++ 2M Karras"],
              scheduler_choices: ["Normal", "Karras"],
              mask_filter_methods: ["Area", "Confidence"],
              mask_merge_modes: ["None", "Merge", "Merge and Invert"],
            };
          },
        };
      }

      if (url === "/rookieui/prompt-tools/config") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              contract: {
                version: "r145f141f142-20260418",
                surface: "prompt_tools_config",
                route_family: "/rookieui/prompt-tools",
              },
              config: {
                language: "en",
                theme_style: "rookieui_classic",
                history_limit: 100,
                favorites_limit: 100,
                formatting_rules: {
                  dedupe_commas: true,
                  normalize_spacing: true,
                  trim_outer_whitespace: true,
                },
                ui_preferences: {
                  default_open: false,
                  preferred_panel: "editor",
                  show_history: true,
                  show_favorites: true,
                },
                translation: { default_provider: "", providers: {} },
                ai_assist: {
                  default_provider: "",
                  providers: {},
                  instruction_preset: "Write a concise Stable Diffusion prompt.",
                },
              },
              blacklist: {
                enabled: false,
                entries: [],
              },
              host_actions: {
                danbooru_upsample: {
                  action_id: "danbooru_upsample",
                  route_path: "/rookieui/prompt-tools/upsample",
                  available: false,
                  resolved_node_alias: "",
                  availability: {
                    status: "host_missing",
                    detail: "Host-installed Danbooru upsampler node is not available in the active ComfyUI registry.",
                  },
                },
              },
              language_options: [{ code: "en", title: "English" }],
              theme_style_options: [{ id: "rookieui_classic", title: "RookieUI Classic" }],
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
                  checkpoint_name: "flux1-dev.safetensors",
                  vae_name: "Automatic",
                  text_encoder_name: "FluxT5XXL.safetensors",
                  template_lora_name: "Flux_2-Turbo-LoRA_comfyui.safetensors",
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
                  checkpoint_name: "qwen-image.safetensors",
                  vae_name: "Automatic",
                  text_encoder_name: "QwenImageTEModel_.safetensors",
                  template_lora_name: "Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors",
                  width: 1328,
                  height: 1328,
                  steps: 50,
                  cfg_scale: 4,
                  sampler_name: "euler",
                  scheduler_name: "simple",
                  clip_skip: 1,
                },
                {
                  id: "qwen_image_edit",
                  title: "Qwen-Image Edit",
                  profile: "qwen_image_edit",
                  base_family: "qwen_image_edit",
                  checkpoint_name: "qwen_image_edit_fp8_e4m3fn.safetensors",
                  vae_name: "qwen_image_vae.safetensors",
                  text_encoder_name: "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                  template_lora_name: "Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors",
                  width: 1328,
                  height: 1328,
                  steps: 4,
                  cfg_scale: 1,
                  shift: 3,
                  edit_megapixels: 1.5,
                  sampler_name: "euler",
                  scheduler_name: "simple",
                  clip_skip: 1,
                },
                {
                  id: "klein",
                  title: "Klein",
                  profile: "klein",
                  base_family: "klein",
                  checkpoint_name: "klein-flux2.safetensors",
                  vae_name: "Automatic",
                  text_encoder_name: "KleinT5XXL.safetensors",
                  width: 896,
                  height: 1152,
                  steps: 20,
                  cfg_scale: 1,
                  sampler_name: "euler",
                  scheduler_name: "beta",
                  clip_skip: 1,
                },
                {
                  id: "lumina",
                  title: "Lumina",
                  profile: "lumina",
                  base_family: "lumina",
                  checkpoint_name: "lumina2.safetensors",
                  vae_name: "Automatic",
                  text_encoder_name: "LuminaTEModel.safetensors",
                  width: 1024,
                  height: 1024,
                  steps: 16,
                  cfg_scale: 2,
                  sampler_name: "dpmpp_2m",
                  scheduler_name: "normal",
                  clip_skip: 1,
                },
                {
                  id: "zit",
                  title: "ZiT",
                  profile: "zit",
                  base_family: "zit",
                  checkpoint_name: "zImageTurboNSFW_21BF16AIO.safetensors",
                  vae_name: "Automatic",
                  text_encoder_name: "LuminaTEModel.safetensors",
                  width: 1024,
                  height: 1024,
                  steps: 8,
                  cfg_scale: 1,
                  sampler_name: "res_multistep",
                  scheduler_name: "simple",
                  clip_skip: 1,
                },
                {
                  id: "wan",
                  title: "Wan",
                  profile: "wan",
                  base_family: "wan",
                  checkpoint_name: "wan2_2b.safetensors",
                  vae_name: "Automatic",
                  text_encoder_name: "WanTextEncoder.safetensors",
                  width: 832,
                  height: 1216,
                  steps: 20,
                  cfg_scale: 6,
                  sampler_name: "euler",
                  scheduler_name: "simple",
                  clip_skip: 1,
                },
                {
                  id: "anima",
                  title: "Anima",
                  profile: "anima",
                  base_family: "anima",
                  checkpoint_name: "animaPencilXL_v500.safetensors",
                  vae_name: "Automatic",
                  text_encoder_name: "AnimaTextEncoder.safetensors",
                  width: 1024,
                  height: 1024,
                  steps: 20,
                  cfg_scale: 2,
                  sampler_name: "dpmpp_2m",
                  scheduler_name: "karras",
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
                  template_lora_visible: true,
                  template_lora_override_allowed: true,
                  official_template_lora_label: "Flux_2-Turbo-LoRA_comfyui.safetensors",
                  notes: [],
                },
                {
                  id: "qwen_image",
                  title: "Qwen-Image",
                  base_family: "sdxl",
                  prompt_encoder: "clip_text_encode_sdxl",
                  default_width: 1328,
                  default_height: 1328,
                  default_steps: 50,
                  default_cfg_scale: 4,
                  default_sampler: "euler",
                  default_scheduler: "simple",
                  default_clip_skip: 1,
                  supports_clip_skip: false,
                  notes: [],
                },
                {
                  id: "klein",
                  title: "Klein (Flux.2)",
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
                  id: "lumina",
                  title: "Lumina",
                  base_family: "sdxl",
                  prompt_encoder: "clip_text_encode_sdxl",
                  default_width: 1024,
                  default_height: 1024,
                  default_steps: 16,
                  default_cfg_scale: 2,
                  default_sampler: "dpmpp_2m",
                  default_scheduler: "normal",
                  default_clip_skip: 1,
                  supports_clip_skip: false,
                  notes: [],
                },
                {
                  id: "zit",
                  title: "ZiT (Z-Image-Turbo)",
                  base_family: "sdxl",
                  prompt_encoder: "clip_text_encode_sdxl",
                  default_width: 1024,
                  default_height: 1024,
                  default_steps: 8,
                  default_cfg_scale: 1,
                  default_sampler: "res_multistep",
                  default_scheduler: "simple",
                  default_clip_skip: 1,
                  supports_clip_skip: false,
                  notes: [],
                },
                {
                  id: "wan",
                  title: "Wan",
                  base_family: "sdxl",
                  prompt_encoder: "clip_text_encode_sdxl",
                  default_width: 832,
                  default_height: 1216,
                  default_steps: 20,
                  default_cfg_scale: 6,
                  default_sampler: "euler",
                  default_scheduler: "simple",
                  default_clip_skip: 1,
                  supports_clip_skip: false,
                  notes: [],
                },
                {
                  id: "anima",
                  title: "Anima",
                  base_family: "sdxl",
                  prompt_encoder: "clip_text_encode_sdxl",
                  default_width: 1024,
                  default_height: 1024,
                  default_steps: 20,
                  default_cfg_scale: 2,
                  default_sampler: "dpmpp_2m",
                  default_scheduler: "karras",
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
    expect(document.getElementById("rookieui-styles").href).toContain(ROOKIEUI_ASSET_REVISION);
    expect(document.getElementById("rookieui-txt2img-preview-fullscreen")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-preview-fullscreen")).not.toBeNull();
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
    expect(
      document.querySelector(
        "#rookieui-pane-txt2img .rookieui-shell__preview-overlay-toolbar #rookieui-txt2img-preview-fullscreen",
      ),
    ).not.toBeNull();
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
    expect(document.getElementById("rookieui-txt2img-workbench-section")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-workbench-section")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-workbench-state")?.textContent).toContain("Collapsed");
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
    const txt2imgGenerationSection = document.getElementById("rookieui-txt2img-generation-section");
    const txt2imgHiresControls = document.getElementById("rookieui-advanced-controls");
    const txt2imgControlNetSection = document.getElementById("rookieui-txt2img-controlnet-section");
    expect(txt2imgGenerationSection).not.toBeNull();
    expect(txt2imgGenerationSection?.contains(txt2imgHiresControls)).toBe(true);
    expect(txt2imgGenerationSection?.contains(txt2imgControlNetSection)).toBe(true);
    expect(txt2imgHiresControls).not.toBeNull();
    expect(txt2imgControlNetSection).not.toBeNull();
    expect(txt2imgControlNetSection?.open).toBe(false);
    expect(txt2imgControlNetSection?.classList.contains("rookieui-shell__controlnet-integrated")).toBe(true);
    expect(txt2imgControlNetSection?.textContent).toContain("Controlnet");
    expect(
      Array.from(txt2imgGenerationSection?.children ?? []).indexOf(document.getElementById("rookieui-txt2img-adetailer-section")),
    ).toBeLessThan(Array.from(txt2imgGenerationSection?.children ?? []).indexOf(txt2imgControlNetSection));
    expect(document.getElementById("rookieui-txt2img-controlnet-tab-0")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-controlnet-tab-0")?.textContent).toContain("ControlNet Unit 1");
    expect(document.getElementById("rookieui-txt2img-adetailer-section")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-adetailer-section")?.open).toBe(false);
    expect(document.getElementById("rookieui-txt2img-adetailer-tab-0")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-adetailer-tab-3")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-adetailer-section")?.textContent).not.toContain("r74f77-20260414");
    expect(document.getElementById("rookieui-txt2img-adetailer-enabled")?.checked).toBe(false);
    expect(document.getElementById("rookieui-txt2img-adetailer-unit-enabled-0")?.checked).toBe(false);
    expect(document.getElementById("rookieui-txt2img-adetailer-unit-enabled-1")?.checked).toBe(false);
    expect(document.getElementById("rookieui-txt2img-adetailer-unit-enabled-2")?.checked).toBe(false);
    expect(document.getElementById("rookieui-txt2img-adetailer-unit-enabled-3")?.checked).toBe(false);
    expect(document.getElementById("rookieui-txt2img-adetailer-detector-classes-field-0")?.hidden).toBe(true);
    expect(document.getElementById("rookieui-txt2img-adetailer-detector-classes-0")?.disabled).toBe(true);
    expect(JSON.parse(document.getElementById("rookieui-adetailer").value)).toMatchObject({
      enabled: false,
      units: [
        { enabled: false },
        { enabled: false },
        { enabled: false },
        { enabled: false },
      ],
    });
    document.getElementById("rookieui-txt2img-adetailer-enabled").checked = true;
    document
      .getElementById("rookieui-txt2img-adetailer-enabled")
      .dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("rookieui-txt2img-adetailer-unit-enabled-0")?.checked).toBe(true);
    expect(document.getElementById("rookieui-txt2img-adetailer-unit-enabled-1")?.checked).toBe(false);
    expect(document.getElementById("rookieui-txt2img-adetailer-unit-enabled-2")?.checked).toBe(false);
    expect(document.getElementById("rookieui-txt2img-adetailer-unit-enabled-3")?.checked).toBe(false);
    expect(JSON.parse(document.getElementById("rookieui-adetailer").value)).toMatchObject({
      enabled: true,
      units: [
        { enabled: true },
        { enabled: false },
        { enabled: false },
        { enabled: false },
      ],
    });
    document.getElementById("rookieui-txt2img-adetailer-controlnet-mode-0").value = "custom";
    document
      .getElementById("rookieui-txt2img-adetailer-controlnet-mode-0")
      .dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("rookieui-txt2img-adetailer-controlnet-model-0")?.disabled).toBe(false);
    expect(document.getElementById("rookieui-txt2img-adetailer-controlnet-module-0")?.disabled).toBe(false);
    expect(
      Array.from(document.getElementById("rookieui-txt2img-adetailer-controlnet-model-0")?.options ?? []).map(
        (option) => option.value,
      ),
    ).toContain("control_v11p_sd15_canny.safetensors");
    expect(
      Array.from(document.getElementById("rookieui-txt2img-adetailer-controlnet-module-0")?.options ?? []).map(
        (option) => option.value,
      ),
    ).toContain("openpose");
    document.getElementById("rookieui-txt2img-adetailer-detector-0").value = "yolov8x-worldv2.pt";
    document
      .getElementById("rookieui-txt2img-adetailer-detector-0")
      .dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("rookieui-txt2img-adetailer-detector-classes-field-0")?.hidden).toBe(false);
    expect(document.getElementById("rookieui-txt2img-adetailer-detector-classes-0")?.disabled).toBe(false);
    expect(document.getElementById("rookieui-txt2img-adetailer-detector-classes-0")?.placeholder).toContain(
      "YOLO-World classes",
    );
    expect(document.getElementById("rookieui-txt2img-controlnet-allow-preview-0")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-controlnet-use-mask-0")).not.toBeNull();
    expect(txt2imgControlNetSection?.textContent).toContain("Instant-ID");
    expect(document.getElementById("rookieui-txt2img-controlnet-image-upload-button-0")?.textContent).toBe(
      "Choose Image File",
    );
    expect(document.getElementById("rookieui-txt2img-controlnet-mask-upload-button-0")?.textContent).toBe(
      "Choose Mask File",
    );
    expect(document.getElementById("rookieui-txt2img-controlnet-image-upload-name-0")?.value).toBe("No file selected");
    expect(document.getElementById("rookieui-txt2img-controlnet-mask-upload-name-0")?.value).toBe("No file selected");
    expect(document.getElementById("rookieui-txt2img-controlnet-image-upload-0")?.hidden).toBe(true);
    expect(document.getElementById("rookieui-txt2img-controlnet-mask-upload-0")?.hidden).toBe(true);
    expect(document.getElementById("rookieui-txt2img-controlnet-preview-stage-0")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-controlnet-preview-image-0")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-controlnet-source-0-fullscreen-zoom")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-controlnet-weight-slider-0")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-controlnet-guidance-start-slider-0")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-controlnet-guidance-end-slider-0")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-controlnet-timestep-range-field-0")).not.toBeNull();
    const txt2imgSelectorRow = document.getElementById("rookieui-txt2img-controlnet-selector-row-0");
    expect(txt2imgSelectorRow).not.toBeNull();
    expect(
      txt2imgSelectorRow?.children[0]?.querySelector(".rookieui-shell__field-label")?.textContent?.trim(),
    ).toBe("Preprocessor");
    expect(txt2imgSelectorRow?.children[1]?.classList.contains("rookieui-shell__controlnet-run-preprocessor-slot")).toBe(
      true,
    );
    expect(
      txt2imgSelectorRow?.children[2]?.querySelector(".rookieui-shell__field-label")?.textContent?.trim(),
    ).toBe("Model");
    expect(
      document.getElementById("rookieui-txt2img-controlnet-module-0")?.closest(".rookieui-shell__controlnet-selector-field"),
    ).not.toBeNull();
    expect(
      document.getElementById("rookieui-txt2img-controlnet-model-0")?.closest(".rookieui-shell__controlnet-selector-field"),
    ).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-controlnet-weight-field-0")?.classList.contains("rookieui-shell__field--full")).toBe(
      true,
    );
    expect(
      document
        .getElementById("rookieui-txt2img-controlnet-weight-field-0")
        ?.classList.contains("rookieui-shell__controlnet-weight-field"),
    ).toBe(true);
    const txt2imgRunPreprocessorButton = document.getElementById("rookieui-txt2img-controlnet-run-preprocessor-0");
    expect(txt2imgRunPreprocessorButton).not.toBeNull();
    expect(txt2imgRunPreprocessorButton?.hidden).toBe(false);
    expect(txt2imgRunPreprocessorButton?.querySelector(".rookieui-shell__mini-action-icon")?.textContent).toBe("💥");
    expect(
      document
        .querySelector("#rookieui-txt2img-controlnet-preview-stage-0 .rookieui-shell__controlnet-preview-placeholder-icon")
        ?.textContent,
    ).toBe("⤴");
    expect(document.getElementById("rookieui-txt2img-controlnet-control-mode-segmented-0")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-controlnet-resize-mode-segmented-0")).not.toBeNull();
    expect(
      document.getElementById("rookieui-txt2img-controlnet-allow-preview-field-0")?.classList.contains(
        "rookieui-shell__controlnet-toggle-field",
      ),
    ).toBe(true);
    expect(txt2imgHiresControls?.classList.contains("rookieui-shell__section")).toBe(true);
    expect(txt2imgHiresControls?.classList.contains("rookieui-shell__hires--integrated")).toBe(true);
    expect(document.querySelector("#rookieui-advanced-controls .rookieui-shell__hires-toggle")).not.toBeNull();
    expect(document.querySelector("#rookieui-advanced-controls .rookieui-shell__hires-summary")?.textContent).toContain(
      "Hires. fix",
    );
    expect(document.querySelector("#rookieui-advanced-controls .rookieui-shell__hires-summary")?.textContent).not.toContain(
      "Enable Hires",
    );
    expect(document.getElementById("rookieui-txt2img-adetailer-section")?.textContent).toContain("ADetailer");
    expect(document.getElementById("rookieui-txt2img-adetailer-section")?.textContent).not.toContain("Enable ADetailer");
    expect(txt2imgHiresControls?.textContent).not.toContain(
      "Second latent pass with bounded rookie-safe defaults.",
    );
    expect(document.getElementById("rookieui-txt2img-workspace-tab-textual-inversion")).not.toBeNull();
    expect(document.getElementById("rookieui-txt2img-workspace-tab-lora")).not.toBeNull();

    document.getElementById("rookieui-prompt").value = "sunset harbor";
    document.getElementById("rookieui-prompt").dispatchEvent(new Event("input", { bubbles: true }));
    const bootstrapFetchCalls = [...fetchCalls];
    fetchCalls.length = 0;
    document.getElementById("rookieui-width").dispatchEvent(
      new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }),
    );
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(fetchCalls.filter(([url]) => url === "/rookieui/generate/txt2img")).toHaveLength(0);
    document.getElementById("rookieui-prompt").dispatchEvent(
      new KeyboardEvent("keydown", { key: "Enter", ctrlKey: true, bubbles: true, cancelable: true }),
    );
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(fetchCalls.filter(([url]) => url === "/rookieui/generate/txt2img")).toHaveLength(1);
    fetchCalls.length = 0;
    app.api.clientId = "socket-client-2";
    // CRITICAL: regression matrix must keep Clip Skip editable across all preset profiles.
    const diffusionModelOptions = [
      "flux1-dev.safetensors",
      "qwen-image.safetensors",
      "qwen_image_edit_fp8_e4m3fn.safetensors",
      "klein-flux2.safetensors",
      "lumina2.safetensors",
      "zImageTurboNSFW_21BF16AIO.safetensors",
      "wan2_2b.safetensors",
      "animaPencilXL_v500.safetensors",
    ];
    const diffusionProfileDefaults = {
      flux: "flux1-dev.safetensors",
      qwen_image: "qwen-image.safetensors",
      anima: "animaPencilXL_v500.safetensors",
    };
    const presetClipSkipMatrix = [
      { id: "sd15", textEncoderHidden: true, ignoredHint: false },
      { id: "sdxl", textEncoderHidden: true, ignoredHint: true },
      { id: "flux", textEncoderHidden: true, ignoredHint: true },
      { id: "qwen_image", textEncoderHidden: true, ignoredHint: true },
      { id: "anima", textEncoderHidden: true, ignoredHint: true },
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
      if (matrixRow.id in diffusionProfileDefaults) {
        expect(document.getElementById("rookieui-checkpoint").dataset.modelCategory).toBe("diffusion_models");
        expect(
          Array.from(document.getElementById("rookieui-checkpoint").options).map((option) => option.value),
        ).toEqual(diffusionModelOptions);
        expect(document.getElementById("rookieui-checkpoint").value).toBe(diffusionProfileDefaults[matrixRow.id]);
      } else {
        expect(document.getElementById("rookieui-checkpoint").dataset.modelCategory).toBe("checkpoints");
      }
    }
    document.getElementById("rookieui-preset").value = "sd15";
    document.getElementById("rookieui-preset").dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("rookieui-modules-quicksetting").textContent).not.toContain("VAE / Text Encoder");
    expect(document.getElementById("rookieui-text-encoder").hidden).toBe(true);
    expect(document.getElementById("rookieui-seed-random").textContent).toContain("🎲");
    expect(document.getElementById("rookieui-seed-fixed").textContent).toContain("♻️");
    document.getElementById("rookieui-seed").value = "-1";
    document.getElementById("rookieui-seed-fixed").click();
    expect(Number(document.getElementById("rookieui-seed").value)).toBeGreaterThanOrEqual(0);
    document.getElementById("rookieui-seed-random").click();
    expect(document.getElementById("rookieui-seed").value).toBe("-1");
    document.getElementById("rookieui-seed-extra").checked = true;
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
    document.getElementById("rookieui-preset").value = "flux";
    document.getElementById("rookieui-preset").dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("rookieui-template-lora-name").disabled).toBe(false);
    expect(document.getElementById("rookieui-template-lora-name").value).toBe("Flux_2-Turbo-LoRA_comfyui.safetensors");
    expect(document.getElementById("rookieui-txt2img-template-lora-status").textContent).toContain(
      "Official default active",
    );
    document.getElementById("rookieui-preset").value = "qwen_image";
    document.getElementById("rookieui-preset").dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("rookieui-template-lora-name").disabled).toBe(false);
    expect(document.getElementById("rookieui-txt2img-template-lora-status").textContent).toContain(
      "Official default active",
    );
    document.getElementById("rookieui-template-lora-name").value = "detail_tweaker.safetensors";
    document.getElementById("rookieui-template-lora-name").dispatchEvent(new Event("input", { bubbles: true }));
    expect(document.getElementById("rookieui-txt2img-template-lora-status").textContent).toContain(
      "exact official template parity no longer applies",
    );
    document.getElementById("rookieui-txt2img-lora-item-0").click();
    document.getElementById("rookieui-lora-strength-model").value = "0.9";
    document.getElementById("rookieui-lora-strength-clip").value = "0.7";
    document.getElementById("rookieui-txt2img-workspace-tab-generation").click();
    document.getElementById("rookieui-cfg-scale").value = "7.25";
    document.getElementById("rookieui-cfg-scale").dispatchEvent(new Event("input", { bubbles: true }));
    document.getElementById("rookieui-adetailer").value = JSON.stringify({
      enabled: true,
      units: [
        {
          enabled: true,
          detector: "face_yolov8n.pt",
          prompt: "repair eyes",
          controlnet: { mode: "passthrough" },
        },
      ],
    });
    document.getElementById("rookieui-controlnet-units").value = JSON.stringify([
      {
        enabled: true,
        module: "canny",
        model: "control_v11p_sd15_canny.safetensors",
        image_asset: "txt2img-control-asset",
      },
    ]);
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
    const img2imgSourceStage = document.getElementById("rookieui-img2img-source-canvas-stage");
    expect(img2imgSourceStage).not.toBeNull();
    expect(img2imgSourceStage?.dataset.interactionMode).toBe("upload");
    expect(document.getElementById("rookieui-img2img-source-brush-width")?.value).toBe("25");
    expect(document.getElementById("rookieui-img2img-source-brush-opacity")?.value).toBe("100");
    expect(document.getElementById("rookieui-img2img-source-brush-softness")?.value).toBe("0");
    expect(document.getElementById("rookieui-img2img-source-brush-indicator")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-source-fullscreen-zoom")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-source-remove")?.querySelector(".rookieui-shell__mini-action-icon")?.textContent).toBe("🗑");
    expect(document.getElementById("rookieui-img2img-source-undo")?.disabled).toBe(true);
    expect(document.getElementById("rookieui-img2img-source-redo")?.disabled).toBe(true);
    const img2imgSourceValueInput =
      document.getElementById("rookieui-image-data") ?? document.getElementById("rookieui-image-asset");
    expect(img2imgSourceValueInput).not.toBeNull();
    img2imgSourceValueInput.value =
      img2imgSourceValueInput?.id === "rookieui-image-data" ? "data:image/png;base64,c291cmNl" : "img2img-stage-source";
    img2imgSourceValueInput.dispatchEvent(new Event("input", { bubbles: true }));
    expect(img2imgSourceStage?.dataset.interactionMode).toBe("edit");
    document.getElementById("rookieui-img2img-source-remove").click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(img2imgSourceValueInput.value).toBe("");
    expect(img2imgSourceStage?.dataset.interactionMode).toBe("upload");
    expect(document.getElementById("rookieui-img2img-source-undo")?.disabled).toBe(false);
    document.getElementById("rookieui-img2img-source-undo").click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(img2imgSourceValueInput.value).not.toBe("");
    expect(img2imgSourceStage?.dataset.interactionMode).toBe("edit");
    expect(document.getElementById("rookieui-img2img-source-redo")?.disabled).toBe(false);
    document.getElementById("rookieui-img2img-source-redo").click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(img2imgSourceValueInput.value).toBe("");
    expect(img2imgSourceStage?.dataset.interactionMode).toBe("upload");
    // IMPORTANT: regression guard — mask upload must remain clickable in Img2Img mode so users can preload masks before switching to inpaint.
    expect(document.getElementById("rookieui-img2img-mask-file").disabled).toBe(false);
    expect(document.getElementById("rookieui-img2img-mask-dropzone").hidden).toBe(false);
    const img2imgGenerationSection = document.getElementById("rookieui-img2img-generation-section");
    const img2imgHiresControls = document.getElementById("rookieui-img2img-hires-controls");
    const img2imgControlNetSection = document.getElementById("rookieui-img2img-controlnet-section");
    expect(img2imgGenerationSection).not.toBeNull();
    expect(img2imgGenerationSection?.contains(img2imgHiresControls)).toBe(true);
    expect(img2imgGenerationSection?.contains(img2imgControlNetSection)).toBe(true);
    expect(img2imgHiresControls).not.toBeNull();
    expect(img2imgControlNetSection).not.toBeNull();
    expect(img2imgControlNetSection?.open).toBe(false);
    expect(img2imgControlNetSection?.classList.contains("rookieui-shell__controlnet-integrated")).toBe(true);
    expect(img2imgControlNetSection?.textContent).toContain("Controlnet");
    expect(
      Array.from(img2imgGenerationSection?.children ?? []).indexOf(document.getElementById("rookieui-img2img-adetailer-section")),
    ).toBeLessThan(Array.from(img2imgGenerationSection?.children ?? []).indexOf(img2imgControlNetSection));
    expect(document.getElementById("rookieui-img2img-controlnet-tab-0")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-adetailer-section")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-adetailer-section")?.open).toBe(false);
    expect(document.getElementById("rookieui-img2img-adetailer-tab-0")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-controlnet-allow-preview-0")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-controlnet-use-mask-0")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-controlnet-image-upload-button-0")?.textContent).toBe(
      "Choose Image File",
    );
    expect(document.getElementById("rookieui-img2img-controlnet-mask-upload-button-0")?.textContent).toBe(
      "Choose Mask File",
    );
    expect(document.getElementById("rookieui-img2img-controlnet-image-upload-name-0")?.value).toBe("No file selected");
    expect(document.getElementById("rookieui-img2img-controlnet-mask-upload-name-0")?.value).toBe("No file selected");
    expect(document.getElementById("rookieui-img2img-controlnet-image-upload-0")?.hidden).toBe(true);
    expect(document.getElementById("rookieui-img2img-controlnet-mask-upload-0")?.hidden).toBe(true);
    expect(document.getElementById("rookieui-img2img-controlnet-preview-stage-0")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-controlnet-preview-image-0")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-controlnet-source-0-brush-indicator")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-controlnet-source-0-fullscreen-zoom")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-controlnet-weight-slider-0")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-controlnet-guidance-start-slider-0")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-controlnet-guidance-end-slider-0")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-controlnet-timestep-range-field-0")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-controlnet-weight-field-0")?.classList.contains("rookieui-shell__field--full")).toBe(
      true,
    );
    const img2imgRunPreprocessorButton = document.getElementById("rookieui-img2img-controlnet-run-preprocessor-0");
    expect(img2imgRunPreprocessorButton).not.toBeNull();
    expect(img2imgRunPreprocessorButton?.hidden).toBe(true);
    expect(img2imgRunPreprocessorButton?.querySelector(".rookieui-shell__mini-action-icon")?.textContent).toBe("💥");
    expect(document.getElementById("rookieui-img2img-controlnet-control-mode-segmented-0")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-controlnet-resize-mode-segmented-0")).not.toBeNull();
    expect(
      document.getElementById("rookieui-img2img-controlnet-use-mask-field-0")?.classList.contains(
        "rookieui-shell__controlnet-toggle-field",
      ),
    ).toBe(true);
    expect(img2imgHiresControls?.classList.contains("rookieui-shell__section")).toBe(true);
    expect(img2imgHiresControls?.classList.contains("rookieui-shell__hires--integrated")).toBe(true);
    expect(document.querySelector("#rookieui-img2img-hires-controls .rookieui-shell__hires-toggle")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-mask-editor")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-mask-editor-tool-select")).not.toBeNull();
    expect(document.getElementById("rookieui-img2img-generation-mode-tabs")).not.toBeNull();
    const img2imgControlImageData = document.getElementById("rookieui-img2img-controlnet-image-data-0");
    img2imgControlImageData.value = "data:image/png;base64,aW1hZ2UtbWF0cml4";
    img2imgControlImageData.dispatchEvent(new Event("input", { bubbles: true }));
    expect(img2imgRunPreprocessorButton?.hidden).toBe(false);
    img2imgControlImageData.value = "";
    img2imgControlImageData.dispatchEvent(new Event("input", { bubbles: true }));
    expect(img2imgRunPreprocessorButton?.hidden).toBe(true);
    expect(document.getElementById("rookieui-img2img-text-encoder").hidden).toBe(true);
    const img2imgPresetValues = Array.from(document.getElementById("rookieui-img2img-preset").options).map(
      (option) => option.value,
    );
    expect(img2imgPresetValues).toContain("sd15");
    expect(img2imgPresetValues).toContain("sdxl");
    expect(img2imgPresetValues).not.toContain("flux");
    expect(img2imgPresetValues).not.toContain("qwen_image");
    expect(img2imgPresetValues).not.toContain("qwen_image_edit");
    expect(img2imgPresetValues).not.toContain("ernie_image");
    for (const matrixRow of presetClipSkipMatrix.filter((row) => ["sd15", "sdxl"].includes(row.id))) {
      document.getElementById("rookieui-img2img-preset").value = matrixRow.id;
      document.getElementById("rookieui-img2img-preset").dispatchEvent(new Event("change", { bubbles: true }));
      expect(document.getElementById("rookieui-img2img-text-encoder").hidden).toBe(matrixRow.textEncoderHidden);
      expect(document.getElementById("rookieui-img2img-clip-skip").disabled).toBe(false);
      expect(document.getElementById("rookieui-img2img-clip-skip-slider").disabled).toBe(false);
      expect(document.getElementById("rookieui-img2img-clip-skip").dataset.executionHint).toBe(
        matrixRow.ignoredHint ? "ignored" : undefined,
      );
      if (matrixRow.id in diffusionProfileDefaults) {
        expect(document.getElementById("rookieui-img2img-checkpoint").dataset.modelCategory).toBe("diffusion_models");
        expect(
          Array.from(document.getElementById("rookieui-img2img-checkpoint").options).map((option) => option.value),
        ).toEqual(diffusionModelOptions);
        expect(document.getElementById("rookieui-img2img-checkpoint").value).toBe(diffusionProfileDefaults[matrixRow.id]);
      } else {
        expect(document.getElementById("rookieui-img2img-checkpoint").dataset.modelCategory).toBe("checkpoints");
      }
    }
    document.getElementById("rookieui-img2img-preset").value = "sd15";
    document.getElementById("rookieui-img2img-preset").dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("rookieui-img2img-modules-quicksetting").textContent).not.toContain("VAE / Text Encoder");
    expect(document.getElementById("rookieui-img2img-text-encoder").hidden).toBe(true);
    expect(document.getElementById("rookieui-img2img-clip-skip").disabled).toBe(false);
    expect(document.getElementById("rookieui-img2img-seed-random").textContent).toContain("🎲");
    expect(document.getElementById("rookieui-img2img-seed-fixed").textContent).toContain("♻️");
    document.getElementById("rookieui-img2img-seed").value = "-1";
    document.getElementById("rookieui-img2img-seed-fixed").click();
    expect(Number(document.getElementById("rookieui-img2img-seed").value)).toBeGreaterThanOrEqual(0);
    document.getElementById("rookieui-img2img-seed-random").click();
    expect(document.getElementById("rookieui-img2img-seed").value).toBe("-1");
    document.getElementById("rookieui-img2img-seed-extra").checked = true;
    document.getElementById("rookieui-img2img-generation-mode-batch").click();
    expect(document.getElementById("rookieui-img2img-mode").value).toBe("batch");
    expect(document.getElementById("rookieui-img2img-mask-editor").hidden).toBe(true);
    document.getElementById("rookieui-img2img-generation-mode-edit").click();
    expect(document.getElementById("rookieui-img2img-mode").value).toBe("edit");
    expect(document.getElementById("rookieui-img2img-mask-editor").hidden).toBe(true);
    expect(document.getElementById("rookieui-mask-asset").disabled).toBe(true);
    expect(document.getElementById("rookieui-img2img-mask-file").disabled).toBe(true);
    expect(document.getElementById("rookieui-img2img-mask-dropzone").hidden).toBe(true);
    expect(document.getElementById("rookieui-mask-asset").placeholder).toBe("not used by edit models");
    expect(document.getElementById("rookieui-img2img-mode-note").textContent).toContain(
      "official edit models do not use mask input",
    );
    const editPresetValues = Array.from(document.getElementById("rookieui-img2img-preset").options).map(
      (option) => option.value,
    );
    expect(editPresetValues).toEqual(["qwen_image_edit"]);
    expect(document.getElementById("rookieui-img2img-edit-megapixels").disabled).toBe(false);
    expect(document.getElementById("rookieui-img2img-template-lora-name").disabled).toBe(false);
    expect(document.getElementById("rookieui-img2img-template-lora-status").textContent).toContain(
      "Official default active",
    );
    document.getElementById("rookieui-img2img-template-lora-name").value = "detail_tweaker.safetensors";
    document.getElementById("rookieui-img2img-template-lora-name").dispatchEvent(new Event("input", { bubbles: true }));
    expect(document.getElementById("rookieui-img2img-template-lora-status").textContent).toContain(
      "exact official template parity no longer applies",
    );
    expect(document.getElementById("rookieui-img2img-width").disabled).toBe(true);
    expect(document.getElementById("rookieui-denoise-strength").disabled).toBe(true);
    document.getElementById("rookieui-img2img-generation-mode-img2img").click();
    expect(document.getElementById("rookieui-img2img-mode").value).toBe("img2img");
    expect(document.getElementById("rookieui-img2img-mask-editor").hidden).toBe(false);
    expect(document.getElementById("rookieui-mask-asset").disabled).toBe(false);
    expect(document.getElementById("rookieui-img2img-mask-file").disabled).toBe(false);
    expect(document.getElementById("rookieui-img2img-mask-dropzone").hidden).toBe(false);
    expect(document.getElementById("rookieui-img2img-width").disabled).toBe(false);
    expect(document.getElementById("rookieui-denoise-strength").disabled).toBe(false);
    expect(document.getElementById("rookieui-image-asset").value).toBe("");
    const restoredPresetValues = Array.from(document.getElementById("rookieui-img2img-preset").options).map(
      (option) => option.value,
    );
    expect(restoredPresetValues).toContain("sd15");
    expect(restoredPresetValues).not.toContain("qwen_image_edit");
    document.getElementById("rookieui-img2img-form").dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.getElementById("rookieui-img2img-status").textContent).toContain(
      "Image asset or uploaded image is required",
    );
    expect(fetchCalls.filter(([url]) => url === "/rookieui/generate/img2img")).toHaveLength(0);
    document.getElementById("rookieui-img2img-generation-mode-inpaint").click();
    expect(document.getElementById("rookieui-img2img-mode").value).toBe("inpaint");
    document.getElementById("rookieui-img2img-hires-enabled").checked = true;
    document.getElementById("rookieui-img2img-hires-scale").value = "1.7";
    document.getElementById("rookieui-img2img-hires-steps").value = "10";
    document.getElementById("rookieui-img2img-hires-denoise").value = "0.4";
    document.getElementById("rookieui-image-asset").value = "source-asset";
    document.getElementById("rookieui-mask-asset").value = "mask-asset";
    document.getElementById("rookieui-img2img-adetailer").value = JSON.stringify({
      enabled: true,
      skip_img2img: true,
      units: [
        {
          enabled: true,
          detector: "mediapipe_face_full",
          controlnet: { mode: "custom", module: "openpose", model: "control_v11p_sd15_canny.safetensors" },
        },
      ],
    });
    document.getElementById("rookieui-img2img-controlnet-units").value = JSON.stringify([
      {
        enabled: true,
        module: "depth",
        model: "control_v11p_sd15_canny.safetensors",
        image_asset: "img2img-control-asset",
      },
    ]);
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
    document.getElementById("rookieui-tab-img2img").click();
    document.getElementById("rookieui-mask-asset").value = "stale-mask-before-transfer";
    const staleMaskDataField = document.getElementById("rookieui-mask-data");
    if (staleMaskDataField) {
      staleMaskDataField.value = "data:image/png;base64,c3RhbGUtbWFzaw==";
    }
    const staleBatchImagesField = document.getElementById("rookieui-img2img-batch-images-data");
    if (staleBatchImagesField) {
      staleBatchImagesField.value = '["data:image/png;base64,c3RhbGUtYmF0Y2g="]';
    }
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
    expect(document.getElementById("rookieui-mask-asset").value).toBe("");
    if (staleMaskDataField) {
      expect(staleMaskDataField.value).toBe("");
    }
    if (staleBatchImagesField) {
      expect(staleBatchImagesField.value).toBe("[]");
    }
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
    const extrasHiresControls = document.getElementById("rookieui-extras-hires-controls");
    expect(extrasHiresControls).not.toBeNull();
    expect(extrasHiresControls?.classList.contains("rookieui-shell__section")).toBe(true);
    expect(extrasHiresControls?.classList.contains("rookieui-shell__hires--integrated")).toBe(true);
    expect(document.querySelector("#rookieui-extras-hires-controls .rookieui-shell__hires-toggle")).not.toBeNull();
    document.getElementById("rookieui-extras-hires-enabled").checked = false;
    document.getElementById("rookieui-extras-submit").click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.querySelector(".rookieui-shell__footer").textContent).toContain("host: standalone-web");
    expect(fetchCalls.some(([url]) => url === "/rookieui/generate/txt2img")).toBe(true);
    expect(fetchCalls.some(([url]) => url === "/rookieui/generate/img2img")).toBe(true);
    expect(fetchCalls.some(([url]) => String(url).startsWith("/rookieui/queue"))).toBe(true);
    expect(fetchCalls.some(([url]) => url === "/rookieui/pnginfo/inspect")).toBe(true);
    expect(bootstrapFetchCalls.some(([url]) => url === "/rookieui/models")).toBe(true);
    expect(bootstrapFetchCalls.some(([url]) => url === "/rookieui/presets")).toBe(true);
    expect(bootstrapFetchCalls.some(([url]) => url === "/rookieui/compatibility")).toBe(true);
    expect(bootstrapFetchCalls.some(([url]) => url === "/rookieui/controlnet/model_list")).toBe(true);
    expect(bootstrapFetchCalls.some(([url]) => url === "/rookieui/controlnet/module_list")).toBe(true);
    expect(bootstrapFetchCalls.some(([url]) => url === "/rookieui/controlnet/control_types")).toBe(true);
    expect(bootstrapFetchCalls.some(([url]) => url === "/rookieui/adetailer/catalog")).toBe(true);
    const txt2imgCall = fetchCalls.find(([url]) => url === "/rookieui/generate/txt2img");
    expect(JSON.parse(txt2imgCall[1].body).hires_enabled).toBe(true);
    expect(JSON.parse(txt2imgCall[1].body).hires_scale).toBe(1.8);
    expect(JSON.parse(txt2imgCall[1].body).batch_count).toBe(2);
    expect(JSON.parse(txt2imgCall[1].body).seed_extra).toBe(true);
    expect(JSON.parse(txt2imgCall[1].body).dtype_profile).toBe("automatic");
    expect(JSON.parse(txt2imgCall[1].body).lora_name).toBe("detail_tweaker.safetensors");
    expect(JSON.parse(txt2imgCall[1].body).lora_strength_model).toBe(0.9);
    expect(JSON.parse(txt2imgCall[1].body).lora_strength_clip).toBe(0.7);
    expect(JSON.parse(txt2imgCall[1].body).client_id).toBe("socket-client-2");
    expect(JSON.parse(txt2imgCall[1].body).adetailer.enabled).toBe(true);
    expect(JSON.parse(txt2imgCall[1].body).adetailer.units[0].detector).toBe("face_yolov8n.pt");
    expect(JSON.parse(txt2imgCall[1].body).controlnet_units[0].image_asset).toBe("txt2img-control-asset");
    const img2imgCall = fetchCalls.find(([url]) => url === "/rookieui/generate/img2img");
    expect(JSON.parse(img2imgCall[1].body).hires_enabled).toBe(true);
    expect(JSON.parse(img2imgCall[1].body).hires_scale).toBe(1.7);
    expect(JSON.parse(img2imgCall[1].body).hires_steps).toBe(10);
    expect(JSON.parse(img2imgCall[1].body).hires_denoise).toBe(0.4);
    expect(JSON.parse(img2imgCall[1].body).seed_extra).toBe(true);
    expect(JSON.parse(img2imgCall[1].body).client_id).toBe("socket-client-2");
    expect(JSON.parse(img2imgCall[1].body).adetailer.skip_img2img).toBe(true);
    expect(JSON.parse(img2imgCall[1].body).adetailer.units[0].controlnet.mode).toBe("custom");
    expect(JSON.parse(img2imgCall[1].body).controlnet_units[0].image_asset).toBe("img2img-control-asset");
    const extrasCall = fetchCalls.find(([url]) => url === "/rookieui/extras/run");
    expect(extrasCall).toBeDefined();
    expect(JSON.parse(extrasCall[1].body).upscale_enabled).toBe(false);
    expect(JSON.parse(extrasCall[1].body).scale_mode).toBe("scale_by");
    expect(
      fetchCalls.some(
        ([url]) =>
          String(url).startsWith("/rookieui/queue/prompt-123") && String(url).includes("client_id=socket-client-2"),
      ),
    ).toBe(true);
  });

  test("surfaces backend invalid-request detail in txt2img status feedback", async () => {
    document.body.innerHTML = `
      <div class="sidebar-content-container">
        <div class="side-bar-panel">
          <div id="mock-sidebar-tabs"></div>
        </div>
      </div>
    `;

    const app = {
      registerExtension(definition) {
        return Promise.resolve(definition.setup());
      },
      api: {
        clientId: "socket-client-invalid-request",
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
    const fetchImpl = async (url) => {
      if (url === "/rookieui/generate/txt2img") {
        return {
          ok: false,
          status: 400,
          async json() {
            return {
              status: "invalid-request",
              detail: "checkpoint_name must match a host inventory entry.",
            };
          },
        };
      }
      if (url === "/rookieui/bootstrap") {
        return {
          ok: true,
          status: 200,
          async json() {
            return { service: "rookieui", status: "bootstrap-ready", routes: [] };
          },
        };
      }
      if (url === "/rookieui/capabilities") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              features: { controlnet: true, adetailer: true, extras: true, pnginfo: true, queue: true },
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
                ],
              },
              routes: [],
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
              clip: [],
              clip_vision: [],
              controlnet: [],
              diffusion_models: [],
              vae: ["Automatic"],
              text_encoders: ["clip_l.safetensors"],
              embeddings: [],
              loras: [],
              ultralytics: [],
              unet: [],
              upscale_models: [],
              default_checkpoint: "dreamshaper.safetensors",
              default_vae: "Automatic",
              default_text_encoder: "clip_l.safetensors",
              catalog: {
                surface_groups: [],
                primary_model_category_by_family: { sd15: "checkpoints", sdxl: "checkpoints" },
                categories: {
                  checkpoints: {
                    title: "Checkpoints",
                    items: ["dreamshaper.safetensors"],
                    default_value: "dreamshaper.safetensors",
                    sidebar_visible: true,
                  },
                  vae: {
                    title: "VAE",
                    items: ["Automatic"],
                    default_value: "Automatic",
                    sidebar_visible: true,
                  },
                  text_encoders: {
                    title: "Text Encoders",
                    items: ["clip_l.safetensors"],
                    default_value: "clip_l.safetensors",
                    sidebar_visible: true,
                  },
                },
              },
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
                  title: "SD1.5",
                  profile: "sd15",
                  base_family: "sd15",
                  checkpoint_name: "dreamshaper.safetensors",
                  vae_name: "Automatic",
                  text_encoder_name: "clip_l.safetensors",
                  width: 512,
                  height: 512,
                  steps: 28,
                  cfg_scale: 7,
                  sampler_name: "euler_ancestral",
                  scheduler_name: "normal",
                  clip_skip: 1,
                },
              ],
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
              samplers: [{ id: "euler_ancestral", title: "Euler a", default: true }],
              schedulers: [{ id: "normal", title: "Normal", default: true }],
              dtype_profiles: [{ id: "automatic", title: "Automatic", default: true }],
              runtime_profiles: [],
            };
          },
        };
      }
      if (url === "/rookieui/controlnet/model_list") {
        return { ok: true, status: 200, async json() { return { model_list: [], default_model: "" }; } };
      }
      if (url === "/rookieui/controlnet/module_list") {
        return { ok: true, status: 200, async json() { return { module_list: [], default_module: "none" }; } };
      }
      if (url === "/rookieui/controlnet/control_types") {
        return { ok: true, status: 200, async json() { return { control_types: {}, control_type_order: [] }; } };
      }
      if (url === "/rookieui/adetailer/catalog") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              detectors: [{ id: "None", label: "None", family: "none", supports_class_filter: false }],
              detector_list: ["None"],
              default_detector: "None",
              controlnet_modes: ["none", "passthrough", "custom"],
              controlnet_model_list: [],
              controlnet_module_list: ["none"],
              controlnet_default_module: "none",
              checkpoint_choices: ["Use same checkpoint"],
              vae_choices: ["Use same VAE"],
              sampler_choices: ["DPM++ 2M Karras"],
              scheduler_choices: ["Use same scheduler"],
              mask_filter_methods: ["Area", "Confidence"],
              mask_merge_modes: ["None", "Merge", "Merge and Invert"],
              contract: { defaults: {} },
            };
          },
        };
      }
      return { ok: true, status: 200, async json() { return {}; } };
    };

    await registerRookieUIBootstrapExtension({ app, fetchImpl });
    await Promise.resolve();
    await Promise.resolve();

    document.getElementById("rookieui-prompt").value = "test prompt";
    document.getElementById("rookieui-txt2img-form").dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(document.getElementById("rookieui-txt2img-status").textContent).toContain(
      "Request failed: invalid-request (checkpoint_name must match a host inventory entry.)",
    );
  });

  test("falls back to primary controlnet catalog for adetailer custom controlnet selectors", async () => {
    document.body.innerHTML = `
      <div class="sidebar-content-container">
        <div class="side-bar-panel">
          <div id="mock-sidebar-tabs"></div>
        </div>
      </div>
    `;

    const app = {
      registerExtension(definition) {
        return Promise.resolve(definition.setup());
      },
      api: {
        clientId: "socket-client-adetailer-controlnet-fallback",
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

    const fetchImpl = async (url) => {
      if (url === "/rookieui/bootstrap") {
        return {
          ok: true,
          status: 200,
          async json() {
            return { service: "rookieui", status: "bootstrap-ready", routes: [] };
          },
        };
      }
      if (url === "/rookieui/capabilities") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              features: { controlnet: true, adetailer: true, extras: true, pnginfo: true, queue: true },
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
                ],
              },
              routes: [],
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
              clip: [],
              clip_vision: [],
              controlnet: ["control_v11p_sd15_canny.safetensors", "control_v11f1p_sd15_depth.safetensors"],
              diffusion_models: ["flux1-dev.safetensors"],
              vae: ["Automatic"],
              text_encoders: ["clip_l.safetensors"],
              embeddings: [],
              loras: [],
              ultralytics: [],
              unet: [],
              upscale_models: [],
              default_checkpoint: "dreamshaper.safetensors",
              default_vae: "Automatic",
              default_text_encoder: "clip_l.safetensors",
              catalog: {
                surface_groups: [],
                primary_model_category_by_family: { sd15: "checkpoints", flux: "diffusion_models" },
                categories: {
                  checkpoints: {
                    title: "Checkpoints",
                    items: ["dreamshaper.safetensors"],
                    default_value: "dreamshaper.safetensors",
                    sidebar_visible: true,
                  },
                  diffusion_models: {
                    title: "Diffusion Models",
                    items: ["flux1-dev.safetensors"],
                    default_value: "flux1-dev.safetensors",
                    sidebar_visible: false,
                  },
                },
              },
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
                  title: "SD1.5",
                  profile: "sd15",
                  base_family: "sd15",
                  checkpoint_name: "dreamshaper.safetensors",
                  vae_name: "Automatic",
                  text_encoder_name: "clip_l.safetensors",
                  width: 512,
                  height: 512,
                  steps: 28,
                  cfg_scale: 7,
                  sampler_name: "euler_ancestral",
                  scheduler_name: "normal",
                  clip_skip: 1,
                },
              ],
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
              samplers: [{ id: "euler_ancestral", title: "Euler a", default: true }],
              schedulers: [{ id: "normal", title: "Normal", default: true }],
              dtype_profiles: [{ id: "automatic", title: "Automatic", default: true }],
              runtime_profiles: [],
            };
          },
        };
      }
      if (url === "/rookieui/controlnet/model_list") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              model_list: ["control_v11p_sd15_canny.safetensors", "control_v11f1p_sd15_depth.safetensors"],
              default_model: "control_v11p_sd15_canny.safetensors",
            };
          },
        };
      }
      if (url === "/rookieui/controlnet/module_list") {
        return {
          ok: true,
          status: 200,
          async json() {
            return { module_list: ["none", "openpose", "depth"], default_module: "none" };
          },
        };
      }
      if (url === "/rookieui/controlnet/control_types") {
        return { ok: true, status: 200, async json() { return { control_types: {}, control_type_order: [] }; } };
      }
      if (url === "/rookieui/adetailer/catalog") {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              detectors: [{ id: "None", label: "None", family: "none", supports_class_filter: false }],
              detector_list: ["None"],
              default_detector: "None",
              controlnet_modes: ["none", "passthrough", "custom"],
              controlnet_model_list: [],
              controlnet_module_list: [],
              controlnet_default_module: "none",
              checkpoint_choices: ["Use same checkpoint"],
              vae_choices: ["Use same VAE"],
              sampler_choices: ["DPM++ 2M Karras"],
              scheduler_choices: ["Use same scheduler"],
              mask_filter_methods: ["Area", "Confidence"],
              mask_merge_modes: ["None", "Merge", "Merge and Invert"],
              contract: { defaults: {} },
            };
          },
        };
      }
      return { ok: true, status: 200, async json() { return {}; } };
    };

    await registerRookieUIBootstrapExtension({ app, fetchImpl });
    await Promise.resolve();
    await Promise.resolve();

    document.getElementById("rookieui-txt2img-adetailer-enabled").checked = true;
    document
      .getElementById("rookieui-txt2img-adetailer-enabled")
      .dispatchEvent(new Event("change", { bubbles: true }));
    document.getElementById("rookieui-txt2img-adetailer-controlnet-mode-0").value = "custom";
    document
      .getElementById("rookieui-txt2img-adetailer-controlnet-mode-0")
      .dispatchEvent(new Event("change", { bubbles: true }));

    const adetailerControlnetModels = Array.from(
      document.getElementById("rookieui-txt2img-adetailer-controlnet-model-0")?.options ?? [],
    ).map((option) => option.value);
    const adetailerControlnetModules = Array.from(
      document.getElementById("rookieui-txt2img-adetailer-controlnet-module-0")?.options ?? [],
    ).map((option) => option.value);
    const adetailerCheckpointChoices = Array.from(
      document.getElementById("rookieui-txt2img-adetailer-checkpoint-name-0")?.options ?? [],
    ).map((option) => option.value);

    expect(document.getElementById("rookieui-txt2img-adetailer-controlnet-model-0")?.disabled).toBe(false);
    expect(document.getElementById("rookieui-txt2img-adetailer-controlnet-module-0")?.disabled).toBe(false);
    expect(adetailerControlnetModels).toContain("control_v11p_sd15_canny.safetensors");
    expect(adetailerControlnetModels).toContain("control_v11f1p_sd15_depth.safetensors");
    expect(adetailerControlnetModules).toContain("openpose");
    expect(adetailerControlnetModules).toContain("depth");
    expect(adetailerCheckpointChoices).toContain("dreamshaper.safetensors");
    expect(adetailerCheckpointChoices).toContain("flux1-dev.safetensors");
  });

  test("falls back to image_asset transfer when preview decode fails", async () => {
    document.body.innerHTML = `
      <div class="sidebar-content-container">
        <div class="side-bar-panel">
          <div id="mock-sidebar-tabs"></div>
        </div>
      </div>
    `;

    let extensionDefinition;
    const app = {
      registerExtension(definition) {
        extensionDefinition = definition;
        return Promise.resolve(definition.setup());
      },
      api: {
        clientId: "socket-client-transfer-fallback",
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

    const fetchImpl = async (url) => {
      if (typeof url === "string" && url.includes("/view?")) {
        return {
          ok: false,
          status: 404,
          async blob() {
            return new Blob();
          },
        };
      }
      return {
        ok: false,
        status: 404,
        async json() {
          return {};
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
    const txt2imgPreview = document.getElementById("rookieui-txt2img-preview");
    txt2imgPreview.innerHTML =
      '<img class="rookieui-shell__preview-image" src="/view?filename=fallback-image.png&subfolder=&type=output" alt="preview">';

    document.getElementById("rookieui-txt2img-preview-img2img").click();
    for (let attempt = 0; attempt < 20; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 10));
      if (document.getElementById("rookieui-pane-img2img").classList.contains("is-active")) {
        break;
      }
    }

    expect(document.getElementById("rookieui-pane-img2img").classList.contains("is-active")).toBe(true);
    expect(document.getElementById("rookieui-image-asset").value).toBe("fallback-image.png");
    expect(document.getElementById("rookieui-txt2img-status").textContent).toContain("asset fallback");
  });

  test("adapts nested host preview payload variants and filters foreign prompt frames", async () => {
    document.body.innerHTML = `
      <div class="sidebar-content-container">
        <div class="side-bar-panel">
          <div id="mock-sidebar-tabs"></div>
        </div>
      </div>
    `;

    let extensionDefinition;
    const runtimeListeners = new Map();
    const app = {
      registerExtension(definition) {
        extensionDefinition = definition;
        return Promise.resolve(definition.setup());
      },
      api: {
        clientId: "socket-client-preview-variants",
        addEventListener(eventName, handler) {
          const handlers = runtimeListeners.get(eventName) || [];
          handlers.push(handler);
          runtimeListeners.set(eventName, handlers);
        },
        removeEventListener(eventName, handler) {
          const handlers = runtimeListeners.get(eventName) || [];
          runtimeListeners.set(
            eventName,
            handlers.filter((entry) => entry !== handler),
          );
        },
      },
      extensionManager: {
        registerSidebarTab(tab) {
          const host = document.getElementById("mock-sidebar-tabs");
          tab.render(host);
        },
      },
    };

    const emitRuntimeEvent = (eventName, detail) => {
      const handlers = runtimeListeners.get(eventName) || [];
      handlers.forEach((handler) => handler({ detail }));
    };

    let resolveFirstQueuePoll;
    const firstQueuePoll = new Promise((resolve) => {
      resolveFirstQueuePoll = resolve;
    });
    let queueJobCallCount = 0;
    const fetchImpl = async (url, options = {}) => {
      if (url === "/rookieui/generate/txt2img") {
        const requestPayload = JSON.parse(options.body);
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              mode: "queued",
              workflow_kind: requestPayload.hires_enabled ? "txt2img-sd15-hires" : "txt2img-sd15",
              submission: { accepted: true, prompt_id: "prompt-preview-1" },
            };
          },
        };
      }

      if (typeof url === "string" && url.startsWith("/rookieui/queue/prompt-preview-1")) {
        queueJobCallCount += 1;
        if (queueJobCallCount === 1) {
          await firstQueuePoll;
        }
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              source: "host",
              queue_remaining: 0,
              job: {
                id: "prompt-preview-1",
                status: "completed",
                output_filenames: [],
                reusable_outputs: [],
              },
            };
          },
        };
      }

      if (typeof url === "string" && url.startsWith("/history/prompt-preview-1")) {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              "prompt-preview-1": {
                outputs: {},
              },
            };
          },
        };
      }

      if (typeof url === "string" && url.startsWith("/rookieui/queue")) {
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              source: "host",
              queue_remaining: 0,
              jobs: [],
            };
          },
        };
      }

      return {
        ok: false,
        status: 404,
        async json() {
          return {};
        },
      };
    };

    const originalCreateObjectURL = URL.createObjectURL;
    const originalRevokeObjectURL = URL.revokeObjectURL;
    URL.createObjectURL = vi.fn(() => "blob:preview-variant-1");
    URL.revokeObjectURL = vi.fn();

    try {
      await registerRookieUIBootstrapExtension({
        app,
        windowRef: window,
        documentRef: document,
        fetchImpl,
      });

      expect(extensionDefinition.name).toBe("ComfyUI-RookieUI");
      const txt2imgForm = document.getElementById("rookieui-txt2img-form");
      txt2imgForm.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      await new Promise((resolve) => setTimeout(resolve, 0));

      emitRuntimeEvent("b_preview_with_metadata", {
        metadata: { prompt_id: "foreign-prompt-id" },
        data: {
          buffer: Uint8Array.from([137, 80, 78, 71]).buffer,
          mime: "image/png",
        },
      });

      emitRuntimeEvent("b_preview_with_metadata", {
        metadata: { prompt_id: "prompt-preview-1" },
        data: {
          buffer: Uint8Array.from([137, 80, 78, 71]).buffer,
          mime: "image/png",
        },
      });

      resolveFirstQueuePoll();
      await new Promise((resolve) => setTimeout(resolve, 0));
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
      const previewImage = document.querySelector("#rookieui-txt2img-preview img");
      expect(previewImage).not.toBeNull();
      expect(previewImage?.getAttribute("src")).toBe("blob:preview-variant-1");
      expect(document.getElementById("rookieui-txt2img-status").textContent).toContain("Completed: prompt-preview-1");
    } finally {
      URL.createObjectURL = originalCreateObjectURL;
      URL.revokeObjectURL = originalRevokeObjectURL;
    }
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
