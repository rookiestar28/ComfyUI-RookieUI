import { registerRookieUIBootstrapExtension } from "../../web/rookieui_extension.js";
import { createMockComfyUIApp } from "./mocks/comfyui-app.js";

const params = new URLSearchParams(window.location.search);
const surface = params.get("surface") === "desktop" ? "desktop" : "standalone-web";
const sidebar = params.get("sidebar") !== "0";

const E2E_PARITY_PROFILES = [
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
    default_cfg_scale: 6,
    default_sampler: "euler_ancestral",
    default_scheduler: "normal",
    default_clip_skip: 1,
    supports_clip_skip: false,
    notes: [],
  },
  {
    id: "flux",
    title: "Flux",
    base_family: "sdxl",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 24,
    default_cfg_scale: 4,
    default_sampler: "euler_ancestral",
    default_scheduler: "normal",
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
    default_steps: 24,
    default_cfg_scale: 4,
    default_sampler: "euler_ancestral",
    default_scheduler: "normal",
    default_clip_skip: 1,
    supports_clip_skip: false,
    notes: [],
  },
];

const E2E_PRESETS = [
  {
    id: "sd15",
    title: "Stable Diffusion 1.5",
    profile: "sd15",
    base_family: "sd15",
    checkpoint_name: "realvisxl.safetensors",
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
    checkpoint_name: "realvisxl.safetensors",
    vae_name: "Automatic",
    text_encoder_name: "Automatic",
    width: 1024,
    height: 1024,
    steps: 28,
    cfg_scale: 6,
    sampler_name: "euler_ancestral",
    scheduler_name: "normal",
    clip_skip: 1,
  },
  {
    id: "flux",
    title: "Flux",
    profile: "flux",
    base_family: "flux",
    checkpoint_name: "flux1-dev.safetensors",
    vae_name: "Automatic",
    text_encoder_name: "Automatic",
    width: 1024,
    height: 1024,
    steps: 24,
    cfg_scale: 4,
    sampler_name: "euler_ancestral",
    scheduler_name: "normal",
    clip_skip: 1,
  },
  {
    id: "qwen_image",
    title: "Qwen-Image",
    profile: "qwen_image",
    base_family: "qwen_image",
    checkpoint_name: "flux1-dev.safetensors",
    vae_name: "Automatic",
    text_encoder_name: "Automatic",
    width: 1024,
    height: 1024,
    steps: 24,
    cfg_scale: 4,
    sampler_name: "euler_ancestral",
    scheduler_name: "normal",
    clip_skip: 1,
  },
];

if (surface === "desktop") {
  window.__COMFYUI_DESKTOP__ = true;
  window.electronAPI = {};
}

window.__ROOKIEUI_E2E_REQUESTS__ = {
  txt2img: [],
  img2img: [],
  extras: [],
};

window.fetch = async (url, options = {}) => {
  if (url === "/rookieui/generate/txt2img") {
    const payload = JSON.parse(options.body ?? "{}");
    window.__ROOKIEUI_E2E_REQUESTS__.txt2img.push(payload);
    return new Response(
      JSON.stringify({
        mode: "queued",
        workflow_kind: payload.hires_enabled ? "txt2img-sd15-hires" : "txt2img-sd15",
        submission: {
          accepted: true,
          prompt_id: "e2e-prompt-123",
        },
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  if (url === "/rookieui/generate/img2img") {
    const payload = JSON.parse(options.body ?? "{}");
    window.__ROOKIEUI_E2E_REQUESTS__.img2img.push(payload);
    return new Response(
      JSON.stringify({
        mode: "queued",
        workflow_kind: payload.hires_enabled ? "inpaint-sd15-hires" : "inpaint-sd15",
        submission: {
          accepted: true,
          prompt_id: "e2e-img2img-456",
        },
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  if (url === "/rookieui/pnginfo/inspect") {
    return new Response(
      JSON.stringify({
        service: "rookieui",
        status: "ok",
        source_type: "a1111",
        target_form: "txt2img",
        payload: {
          prompt: "e2e imported prompt",
          negative_prompt: "e2e imported negative",
          width: 768,
          height: 768,
          sampler_name: "euler_ancestral",
          image_asset: "pnginfo_asset.png",
        },
        metadata_items: {
          parameters: "e2e imported prompt",
          Prompt: "e2e imported prompt",
          "Negative prompt": "e2e imported negative",
        },
        apply_targets: ["txt2img", "img2img"],
        asset_handle: "pnginfo_asset.png",
        unsupported_fields: ["ENSD"],
        warnings: [],
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  if (url === "/rookieui/extras/run") {
    const payload = JSON.parse(options.body ?? "{}");
    window.__ROOKIEUI_E2E_REQUESTS__.extras.push(payload);
    return new Response(
      JSON.stringify({
        status: "ok",
        mode: payload.mode ?? "single_image",
        output_assets: ["rookieui_extras_output.png"],
        preview_asset: "rookieui_extras_output.png",
        preview_data_url: "data:image/png;base64,ZmFrZQ==",
        warnings: [],
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  if (url === "/rookieui/models") {
    return new Response(
      JSON.stringify({
        source: "host",
        checkpoints: ["realvisxl.safetensors"],
        clip: [],
        clip_vision: [],
        controlnet: [],
        diffusion_models: ["flux1-dev.safetensors"],
        vae: ["Automatic"],
        text_encoders: ["Automatic"],
        embeddings: ["badhandv4.pt"],
        loras: ["detail_tweaker.safetensors"],
        ultralytics: ["sam2_b.pt"],
        unet: [],
        upscale_models: ["4x-UltraSharp.pth"],
        default_checkpoint: "realvisxl.safetensors",
        default_vae: "Automatic",
        default_text_encoder: "Automatic",
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  if (url === "/rookieui/compatibility") {
    return new Response(
      JSON.stringify({
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
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  if (url.startsWith("/rookieui/queue/")) {
    const promptId = url.split("?")[0].split("/").pop();
    return new Response(
      JSON.stringify({
        source: "host",
        queue_remaining: 0,
        job: {
          id: promptId,
          status: "completed",
          output_filenames: ["history-image.png"],
          reusable_outputs: ["history-image.png"],
        },
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  if (url.startsWith("/history/")) {
    const promptId = url.split("/").pop();
    return new Response(
      JSON.stringify({
        [promptId]: {
          outputs: {
            "7": {
              images: [{ filename: "history-image.png", subfolder: "", type: "output" }],
            },
          },
        },
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  if (url.startsWith("/rookieui/queue")) {
    return new Response(
      JSON.stringify({
        source: "host",
        queue_remaining: 1,
        jobs: [
          {
            id: "prompt-history",
            status: "completed",
            output_filenames: ["history-image.png"],
            reusable_outputs: ["history-image.png"],
          },
        ],
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  if (url === "/rookieui/presets") {
    return new Response(
      JSON.stringify({
        source: "host",
        presets: E2E_PRESETS,
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  return new Response(
    JSON.stringify({
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
        { id: "queue", title: "Queue", state: "active", enabled: true },
      ],
      parity: {
        profiles: E2E_PARITY_PROFILES,
      },
      routes: [
        "/rookieui/health",
        "/rookieui/bootstrap",
        "/rookieui/capabilities",
        "/rookieui/parity",
        "/rookieui/compatibility",
        "/rookieui/models",
        "/rookieui/presets",
        "/rookieui/queue",
        "/rookieui/pnginfo/inspect",
        "/rookieui/generate/txt2img",
        "/rookieui/generate/img2img",
        "/rookieui/extras/run",
      ],
    }),
    {
      status: 200,
      headers: { "Content-Type": "application/json" },
    },
  );
};

const app = createMockComfyUIApp({ sidebar });
await registerRookieUIBootstrapExtension({
  app,
  windowRef: window,
  documentRef: document,
  fetchImpl: window.fetch,
});

const root = document.getElementById("rookieui-root");
root.textContent = JSON.stringify(window.__ROOKIEUI_BOOTSTRAP__);
