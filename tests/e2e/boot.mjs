import { registerRookieUIBootstrapExtension } from "../../web/rookieui_extension.js";
import { createMockComfyUIApp } from "./mocks/comfyui-app.js";

const params = new URLSearchParams(window.location.search);
const surface = params.get("surface") === "desktop" ? "desktop" : "standalone-web";
const sidebar = params.get("sidebar") !== "0";

const E2E_MODEL_FAMILY_ENTRIES = [
  {
    id: "sd15",
    title: "Stable Diffusion 1.5",
    translation_base_family: "sd15",
    public_base_family: "sd15",
    prompt_encoder: "clip_text_encode",
    default_width: 512,
    default_height: 512,
    default_steps: 28,
    default_cfg_scale: 7,
    default_sampler: "euler_ancestral",
    default_scheduler: "normal",
    default_clip_skip: 1,
    supports_clip_skip: true,
    primary_model_category: "checkpoints",
    text_encoder_visible: false,
    support_tier: "parity",
    compatibility_summary: "Primary A1111 parity baseline for classic Stable Diffusion checkpoints.",
    experimental: false,
    aliases: [],
    notes: [],
    checkpoint_name: "realvisxl.safetensors",
    vae_name: "Automatic",
    text_encoder_name: "Automatic",
  },
  {
    id: "sdxl",
    title: "Stable Diffusion XL",
    translation_base_family: "sdxl",
    public_base_family: "sdxl",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 28,
    default_cfg_scale: 7,
    default_sampler: "dpmpp_2m",
    default_scheduler: "karras",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "checkpoints",
    text_encoder_visible: false,
    support_tier: "parity",
    compatibility_summary: "Primary SDXL parity baseline with dual-text-encoder semantics.",
    experimental: false,
    aliases: [],
    notes: [],
    checkpoint_name: "realvisxl.safetensors",
    vae_name: "Automatic",
    text_encoder_name: "Automatic",
  },
  {
    id: "pony",
    title: "Pony",
    translation_base_family: "sdxl",
    public_base_family: "sdxl",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 28,
    default_cfg_scale: 7,
    default_sampler: "dpmpp_2m",
    default_scheduler: "karras",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "checkpoints",
    text_encoder_visible: false,
    support_tier: "parity",
    compatibility_summary: "SDXL-derived parity lane with preserved Pony-facing defaults.",
    experimental: false,
    aliases: [],
    notes: [],
    checkpoint_name: "realvisxl.safetensors",
    vae_name: "Automatic",
    text_encoder_name: "Automatic",
  },
  {
    id: "illustrious",
    title: "Illustrious",
    translation_base_family: "sdxl",
    public_base_family: "sdxl",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 28,
    default_cfg_scale: 7,
    default_sampler: "dpmpp_2m",
    default_scheduler: "karras",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "checkpoints",
    text_encoder_visible: false,
    support_tier: "parity",
    compatibility_summary: "SDXL-derived parity lane retained as an explicit profile.",
    experimental: false,
    aliases: [],
    notes: [],
    checkpoint_name: "realvisxl.safetensors",
    vae_name: "Automatic",
    text_encoder_name: "Automatic",
  },
  {
    id: "noob",
    title: "Noob",
    translation_base_family: "sdxl",
    public_base_family: "sdxl",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 28,
    default_cfg_scale: 7,
    default_sampler: "dpmpp_2m",
    default_scheduler: "karras",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "checkpoints",
    text_encoder_visible: false,
    support_tier: "parity",
    compatibility_summary: "SDXL-derived parity lane retained for rookie-safe defaults.",
    experimental: false,
    aliases: [],
    notes: [],
    checkpoint_name: "realvisxl.safetensors",
    vae_name: "Automatic",
    text_encoder_name: "Automatic",
  },
  {
    id: "flux",
    title: "Flux.1 Dev FP8",
    translation_base_family: "sdxl",
    public_base_family: "flux",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 20,
    default_cfg_scale: 1,
    default_sampler: "euler",
    default_scheduler: "simple",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary: "Official ComfyUI Flux.1 Dev FP8 template preset on the current non-SD translation seam.",
    experimental: true,
    aliases: ["flux.1 dev fp8", "flux-1 dev fp8", "flux1 dev fp8"],
    notes: [],
    checkpoint_name: "flux1-dev.safetensors",
    vae_name: "ae.safetensors",
    text_encoder_name: "Automatic",
  },
  {
    id: "qwen_image",
    title: "Qwen-Image 2512",
    translation_base_family: "sdxl",
    public_base_family: "qwen_image",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1328,
    default_height: 1328,
    default_steps: 2,
    default_cfg_scale: 1,
    default_sampler: "euler",
    default_scheduler: "simple",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary: "Official ComfyUI Qwen-Image 2512 template preset on the current non-SD translation seam.",
    experimental: true,
    aliases: ["qwen image", "qwen-image 2512", "qwen image 2512"],
    notes: [],
    checkpoint_name: "qwen_image_2512_fp8_e4m3fn.safetensors",
    vae_name: "qwen_image_vae.safetensors",
    text_encoder_name: "Automatic",
  },
  {
    id: "klein_4b_distilled",
    title: "Flux.2 4B Distilled Klein",
    translation_base_family: "sdxl",
    public_base_family: "klein",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 4,
    default_cfg_scale: 1,
    default_sampler: "euler",
    default_scheduler: "beta",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary:
      "Official ComfyUI Flux.2 4B Distilled Klein template preset on the current non-SD translation seam.",
    experimental: true,
    aliases: ["flux.2 4b distilled klein", "klein 4b distilled"],
    notes: [],
    checkpoint_name: "flux-2-klein-4b.safetensors",
    vae_name: "flux2-vae.safetensors",
    text_encoder_name: "Automatic",
  },
  {
    id: "klein_4b",
    title: "Flux.2 4B Klein",
    translation_base_family: "sdxl",
    public_base_family: "klein",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 20,
    default_cfg_scale: 5,
    default_sampler: "euler",
    default_scheduler: "beta",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary: "Official ComfyUI Flux.2 4B Klein template preset on the current non-SD translation seam.",
    experimental: true,
    aliases: ["klein", "flux.2", "flux2", "flux.2 4b klein", "klein 4b"],
    notes: [],
    checkpoint_name: "flux-2-klein-base-4b.safetensors",
    vae_name: "flux2-vae.safetensors",
    text_encoder_name: "Automatic",
  },
  {
    id: "klein_9b_distilled",
    title: "Flux.2 9B Distilled Klein",
    translation_base_family: "sdxl",
    public_base_family: "klein",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 4,
    default_cfg_scale: 1,
    default_sampler: "euler",
    default_scheduler: "beta",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary:
      "Official ComfyUI Flux.2 9B Distilled Klein template preset on the current non-SD translation seam.",
    experimental: true,
    aliases: ["flux.2 9b distilled klein", "klein 9b distilled"],
    notes: [],
    checkpoint_name: "flux-2-klein-9b-fp8.safetensors",
    vae_name: "full_encoder_small_decoder.safetensors",
    text_encoder_name: "Automatic",
  },
  {
    id: "klein_9b",
    title: "Flux.2 9B Klein",
    translation_base_family: "sdxl",
    public_base_family: "klein",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 20,
    default_cfg_scale: 5,
    default_sampler: "euler",
    default_scheduler: "beta",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary: "Official ComfyUI Flux.2 9B Klein template preset on the current non-SD translation seam.",
    experimental: true,
    aliases: ["flux.2 9b klein", "klein 9b"],
    notes: [],
    checkpoint_name: "flux-2-klein-base-9b-fp8.safetensors",
    vae_name: "full_encoder_small_decoder.safetensors",
    text_encoder_name: "Automatic",
  },
  {
    id: "anima",
    title: "Anima",
    translation_base_family: "sdxl",
    public_base_family: "anima",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 30,
    default_cfg_scale: 4,
    default_sampler: "er_sde",
    default_scheduler: "simple",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary: "Official ComfyUI Anima template preset routed through the non-SD template seam.",
    experimental: true,
    aliases: ["anima preview3"],
    notes: [],
    checkpoint_name: "anima-preview3-base.safetensors",
    vae_name: "qwen_image_vae.safetensors",
    text_encoder_name: "Automatic",
  },
  {
    id: "chroma",
    title: "Chroma",
    translation_base_family: "sdxl",
    public_base_family: "chroma",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 26,
    default_cfg_scale: 3.5,
    default_sampler: "euler",
    default_scheduler: "beta",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary: "Official ComfyUI Chroma template preset routed through the non-SD template seam.",
    experimental: true,
    aliases: ["chroma1"],
    notes: [],
    checkpoint_name: "Chroma1-HD-fp8mixed.safetensors",
    vae_name: "ae.safetensors",
    text_encoder_name: "Automatic",
  },
  {
    id: "ernie_image",
    title: "ERNIE-Image",
    translation_base_family: "sdxl",
    public_base_family: "ernie_image",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 40,
    default_cfg_scale: 4,
    default_sampler: "euler",
    default_scheduler: "simple",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary: "Official ComfyUI ERNIE-Image template preset on the current non-SD translation seam.",
    experimental: true,
    aliases: ["ernie-image", "ernie image"],
    notes: [],
    checkpoint_name: "ernie-image.safetensors",
    vae_name: "flux2-vae.safetensors",
    text_encoder_name: "Automatic",
  },
  {
    id: "ernie_image_turbo",
    title: "ERNIE-Image Turbo",
    translation_base_family: "sdxl",
    public_base_family: "ernie_image",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 8,
    default_cfg_scale: 1,
    default_sampler: "euler",
    default_scheduler: "simple",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary:
      "Official ComfyUI ERNIE-Image Turbo template preset on the current non-SD translation seam.",
    experimental: true,
    aliases: ["ernie-image-turbo", "ernie image turbo"],
    notes: [],
    checkpoint_name: "ernie-image-turbo.safetensors",
    vae_name: "flux2-vae.safetensors",
    text_encoder_name: "Automatic",
  },
  {
    id: "hidream_i1_dev_fp8",
    title: "HiDream i1 Dev FP8",
    translation_base_family: "sdxl",
    public_base_family: "hidream",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 28,
    default_cfg_scale: 1,
    default_sampler: "lcm",
    default_scheduler: "normal",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary:
      "Official ComfyUI HiDream i1 Dev FP8 template preset on the current non-SD translation seam.",
    experimental: true,
    aliases: ["hidream i1 dev fp8"],
    notes: [],
    checkpoint_name: "hidream_i1_dev_fp8.safetensors",
    vae_name: "ae.safetensors",
    text_encoder_name: "Automatic",
  },
  {
    id: "hidream_i1_fast",
    title: "HiDream i1 fast",
    translation_base_family: "sdxl",
    public_base_family: "hidream",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 16,
    default_cfg_scale: 1,
    default_sampler: "lcm",
    default_scheduler: "normal",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary:
      "Official ComfyUI HiDream i1 fast template preset on the current non-SD translation seam.",
    experimental: true,
    aliases: ["hidream i1 fast"],
    notes: [],
    checkpoint_name: "hidream_i1_fast_fp8.safetensors",
    vae_name: "ae.safetensors",
    text_encoder_name: "Automatic",
  },
  {
    id: "hidream_i1_full",
    title: "HiDream i1 full",
    translation_base_family: "sdxl",
    public_base_family: "hidream",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 50,
    default_cfg_scale: 5,
    default_sampler: "uni_pc",
    default_scheduler: "simple",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary:
      "Official ComfyUI HiDream i1 full template preset on the current non-SD translation seam.",
    experimental: true,
    aliases: ["hidream", "hidream i1", "hidream i1 full"],
    notes: [],
    checkpoint_name: "hidream_i1_full_fp8.safetensors",
    vae_name: "ae.safetensors",
    text_encoder_name: "Automatic",
  },
  {
    id: "longcat_image",
    title: "Longcat BF16",
    translation_base_family: "sdxl",
    public_base_family: "longcat_image",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 20,
    default_cfg_scale: 4,
    default_sampler: "euler",
    default_scheduler: "simple",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary: "Official ComfyUI Longcat BF16 template preset on the current non-SD translation seam.",
    experimental: true,
    aliases: ["longcat", "longcat image"],
    notes: [],
    checkpoint_name: "longcat_image_bf16.safetensors",
    vae_name: "ae.safetensors",
    text_encoder_name: "Automatic",
  },
  {
    id: "z_image",
    title: "Z-Image",
    translation_base_family: "sdxl",
    public_base_family: "z_image",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 25,
    default_cfg_scale: 4,
    default_sampler: "res_multistep",
    default_scheduler: "simple",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary: "Official ComfyUI Z-Image template preset on the current non-SD translation seam.",
    experimental: true,
    aliases: ["lumina", "z-image", "z image", "lumina2"],
    notes: [],
    checkpoint_name: "z_image_bf16.safetensors",
    vae_name: "ae.safetensors",
    text_encoder_name: "Automatic",
  },
  {
    id: "z_image_turbo",
    title: "Z-Image Turbo",
    translation_base_family: "sdxl",
    public_base_family: "z_image",
    prompt_encoder: "clip_text_encode_sdxl",
    default_width: 1024,
    default_height: 1024,
    default_steps: 8,
    default_cfg_scale: 1,
    default_sampler: "res_multistep",
    default_scheduler: "simple",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary: "Official ComfyUI Z-Image Turbo template preset on the current non-SD translation seam.",
    experimental: true,
    aliases: ["zit", "z-image-turbo", "z image turbo"],
    notes: [],
    checkpoint_name: "z_image_turbo_bf16.safetensors",
    vae_name: "ae.safetensors",
    text_encoder_name: "Automatic",
  },
];

const E2E_PARITY_PROFILES = E2E_MODEL_FAMILY_ENTRIES.map((entry) => ({
  id: entry.id,
  title: entry.title,
  base_family: entry.translation_base_family,
  prompt_encoder: entry.prompt_encoder,
  default_width: entry.default_width,
  default_height: entry.default_height,
  default_steps: entry.default_steps,
  default_cfg_scale: entry.default_cfg_scale,
  default_sampler: entry.default_sampler,
  default_scheduler: entry.default_scheduler,
  default_clip_skip: entry.default_clip_skip,
  supports_clip_skip: entry.supports_clip_skip,
  notes: [...entry.notes],
}));

const E2E_PRESETS = E2E_MODEL_FAMILY_ENTRIES.map((entry) => ({
  id: entry.id,
  title: entry.id === "sd15" ? "SD1.5" : entry.id === "sdxl" ? "SDXL" : entry.title,
  profile: entry.id,
  base_family: entry.public_base_family,
  checkpoint_name: entry.checkpoint_name,
  vae_name: entry.vae_name,
  text_encoder_name: entry.text_encoder_name,
  width: entry.default_width,
  height: entry.default_height,
  steps: entry.default_steps,
  cfg_scale: entry.default_cfg_scale,
  sampler_name: entry.default_sampler,
  scheduler_name: entry.default_scheduler,
  clip_skip: entry.default_clip_skip,
}));

const E2E_NEWER_FAMILY_PROFILES = E2E_MODEL_FAMILY_ENTRIES.filter((entry) => entry.support_tier !== "parity").map(
  (entry) => ({
    id: entry.id,
    title: entry.title,
    summary: entry.compatibility_summary,
    default: false,
    experimental: entry.experimental,
    aliases: [...entry.aliases],
  }),
);

const E2E_PRIMARY_MODEL_CATEGORY_BY_FAMILY = E2E_MODEL_FAMILY_ENTRIES.reduce((categoryMap, entry) => {
  for (const key of new Set([entry.id, entry.public_base_family, ...entry.aliases])) {
    if (typeof key === "string" && key.trim()) {
      categoryMap[key] = entry.primary_model_category;
    }
  }
  return categoryMap;
}, {});

const E2E_DIFFUSION_MODELS = E2E_MODEL_FAMILY_ENTRIES.filter(
  (entry) => entry.primary_model_category === "diffusion_models",
).map((entry) => entry.checkpoint_name);

const E2E_VAE_OPTIONS = [
  "Automatic",
  "ae.safetensors",
  "flux2-vae.safetensors",
  "full_encoder_small_decoder.safetensors",
  "qwen_image_vae.safetensors",
];

const E2E_TEXT_ENCODER_OPTIONS = [
  "Automatic",
  "clip_l.safetensors",
  "clip_l_hidream.safetensors",
  "clip_g_hidream.safetensors",
  "ernie-image-prompt-enhancer.safetensors",
  "llama_3.1_8b_instruct_fp8_scaled.safetensors",
  "ministral-3-3b.safetensors",
  "qwen_2.5_vl_7b_fp8_scaled.safetensors",
  "qwen_3_06b_base.safetensors",
  "qwen_3_4b.safetensors",
  "qwen_3_8b_fp8mixed.safetensors",
  "t5xxl_fp16.safetensors",
  "t5xxl_fp8_e4m3fn_scaled.safetensors",
];

if (surface === "desktop") {
  window.__COMFYUI_DESKTOP__ = true;
  window.electronAPI = {};
}

window.__ROOKIEUI_E2E_REQUESTS__ = {
  txt2img: [],
  img2img: [],
  extras: [],
  xyzPlot: {
    estimate: [],
    run: [],
    cancel: [],
  },
};

window.__ROOKIEUI_E2E_XYZ__ = {
  sessions: {},
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

  if (url === "/rookieui/xyz-plot/axes") {
    return new Response(
      JSON.stringify({
        contract: {
          version: "r125-20260417",
          surface: "xyz_plot_axes",
          route_family: "/rookieui/xyz-plot",
        },
        axes: {
          steps: {
            axis_id: "steps",
            title: "Steps",
            support_tier: "direct",
            mode_scopes: ["txt2img", "img2img"],
            value_input_mode: "int_csv_or_range",
            choices: [],
            session_runner_support: true,
            a1111_reference_label: "Steps",
            notes: [],
          },
          cfg_scale: {
            axis_id: "cfg_scale",
            title: "CFG Scale",
            support_tier: "direct",
            mode_scopes: ["txt2img", "img2img"],
            value_input_mode: "float_csv_or_range",
            choices: [],
            session_runner_support: true,
            a1111_reference_label: "CFG Scale",
            notes: [],
          },
          seed: {
            axis_id: "seed",
            title: "Seed",
            support_tier: "direct",
            mode_scopes: ["txt2img", "img2img"],
            value_input_mode: "int_csv_or_range",
            choices: [],
            session_runner_support: true,
            a1111_reference_label: "Seed",
            notes: [],
          },
          checkpoint_name: {
            axis_id: "checkpoint_name",
            title: "Checkpoint Name",
            support_tier: "direct",
            mode_scopes: ["txt2img", "img2img"],
            value_input_mode: "choices_or_csv",
            choices: ["realvisxl.safetensors", "flux1-dev.safetensors"],
            session_runner_support: true,
            a1111_reference_label: "Checkpoint name",
            notes: [],
          },
          denoising_strength: {
            axis_id: "denoising_strength",
            title: "Denoising",
            support_tier: "direct",
            mode_scopes: ["img2img"],
            value_input_mode: "float_csv_or_range",
            choices: [],
            session_runner_support: true,
            a1111_reference_label: "Denoising",
            notes: [],
          },
        },
        axis_order: ["steps", "cfg_scale", "seed", "checkpoint_name", "denoising_strength"],
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  if (url === "/rookieui/xyz-plot/estimate") {
    const payload = JSON.parse(options.body ?? "{}");
    window.__ROOKIEUI_E2E_REQUESTS__.xyzPlot.estimate.push(payload);
    const axisCount = Array.isArray(payload.axes) ? payload.axes.length : 0;
    return new Response(
      JSON.stringify({
        estimate: {
          cell_count: axisCount * 3,
          generated_image_count: axisCount * 3,
          total_step_estimate: 96,
          projected_grid_megapixels: 2.4,
        },
        can_run: axisCount > 0,
        warnings: [],
        warning_codes: [],
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  if (url === "/rookieui/xyz-plot/run") {
    const payload = JSON.parse(options.body ?? "{}");
    window.__ROOKIEUI_E2E_REQUESTS__.xyzPlot.run.push(payload);
    const sessionId = `xyz-e2e-${window.__ROOKIEUI_E2E_REQUESTS__.xyzPlot.run.length}`;
    window.__ROOKIEUI_E2E_XYZ__.sessions[sessionId] = {
      session_id: sessionId,
      status: "in_progress",
      seed_policy: {
        keep_negative_one_seed: Boolean(payload.keep_negative_one_seed),
        vary_seeds_x: Boolean(payload.vary_seeds_x),
        vary_seeds_y: Boolean(payload.vary_seeds_y),
        vary_seeds_z: Boolean(payload.vary_seeds_z),
        fixed_base_seed: payload.keep_negative_one_seed ? null : 101,
        fixed_axis_values: {},
      },
      summary: {
        total_cells: 9,
        completed_cells: 3,
        queued_cells: 2,
        failed_cells: 0,
      },
      axes: payload.axes ?? [],
      cells: [{ resolved_seed: 101 }, {}, {}, {}],
      results: {
        status: "running",
        main_grid: {},
        sub_grids: [],
        lone_images: [],
        warnings: [],
      },
    };
    return new Response(
      JSON.stringify({
        session: window.__ROOKIEUI_E2E_XYZ__.sessions[sessionId],
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  if (url.startsWith("/rookieui/xyz-plot/sessions/") && url.endsWith("/cancel")) {
    const sessionId = url.split("/").at(-2);
    const payload = JSON.parse(options.body ?? "{}");
    window.__ROOKIEUI_E2E_REQUESTS__.xyzPlot.cancel.push({ sessionId, payload });
    const session = window.__ROOKIEUI_E2E_XYZ__.sessions[sessionId] ?? {
      session_id: sessionId,
      seed_policy: {
        keep_negative_one_seed: false,
        vary_seeds_x: false,
        vary_seeds_y: false,
        vary_seeds_z: false,
        fixed_base_seed: 101,
        fixed_axis_values: {},
      },
      summary: { total_cells: 0, completed_cells: 0, queued_cells: 0, failed_cells: 0 },
      axes: [],
      cells: [],
      results: { status: "pending", main_grid: {}, sub_grids: [], lone_images: [], warnings: [] },
    };
    session.status = "cancelled";
    session.cancel_requested = true;
    window.__ROOKIEUI_E2E_XYZ__.sessions[sessionId] = session;
    return new Response(
      JSON.stringify({ session }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  if (url.startsWith("/rookieui/xyz-plot/sessions/")) {
    const sessionId = url.split("?")[0].split("/").pop();
    const session = window.__ROOKIEUI_E2E_XYZ__.sessions[sessionId] ?? {
      session_id: sessionId,
      status: "completed",
      seed_policy: {
        keep_negative_one_seed: false,
        vary_seeds_x: false,
        vary_seeds_y: false,
        vary_seeds_z: false,
        fixed_base_seed: 101,
        fixed_axis_values: {},
      },
      summary: {
        total_cells: 9,
        completed_cells: 9,
        queued_cells: 0,
        failed_cells: 0,
      },
      axes: [],
      cells: [{ resolved_seed: 101 }, { resolved_seed: 101 }],
      results: {
        status: "ready",
        main_grid: { preview_data_url: "data:image/png;base64,ZmFrZQ==" },
        sub_grids: [{ z_index: 0 }],
        lone_images: [{ cell_id: "cell-1" }],
        warnings: [],
      },
    };
    if (session.status === "in_progress") {
      session.status = "completed";
      session.summary = {
        total_cells: 9,
        completed_cells: 9,
        queued_cells: 0,
        failed_cells: 0,
      };
      session.cells = [{ resolved_seed: 101 }, { resolved_seed: 101 }];
      session.results = {
        status: "ready",
        main_grid: { preview_data_url: "data:image/png;base64,ZmFrZQ==" },
        sub_grids: [{ z_index: 0 }],
        lone_images: [{ cell_id: "cell-1" }, { cell_id: "cell-2" }],
        warnings: [],
      };
      window.__ROOKIEUI_E2E_XYZ__.sessions[sessionId] = session;
    }
    return new Response(
      JSON.stringify({ session }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  if (url.startsWith("/rookieui/xyz-plot/sessions")) {
    return new Response(
      JSON.stringify({
        sessions: Object.values(window.__ROOKIEUI_E2E_XYZ__.sessions),
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
        diffusion_models: E2E_DIFFUSION_MODELS,
        vae: E2E_VAE_OPTIONS,
        text_encoders: E2E_TEXT_ENCODER_OPTIONS,
        embeddings: ["badhandv4.pt"],
        loras: ["detail_tweaker.safetensors"],
        ultralytics: ["sam2_b.pt"],
        unet: [],
        upscale_models: ["4x-UltraSharp.pth"],
        default_checkpoint: "realvisxl.safetensors",
        default_vae: "Automatic",
        default_text_encoder: "Automatic",
        catalog: {
          surface_groups: [
            {
              id: "sd_generation",
              title: "SD Generation",
              categories: ["checkpoints", "diffusion_models", "vae", "text_encoders", "embeddings", "loras"],
            },
          ],
          primary_model_category_by_family: E2E_PRIMARY_MODEL_CATEGORY_BY_FAMILY,
          categories: {
            checkpoints: {
              title: "Checkpoints",
              items: ["realvisxl.safetensors"],
              default_value: "realvisxl.safetensors",
              sidebar_visible: true,
            },
            diffusion_models: {
              title: "Diffusion Models",
              items: E2E_DIFFUSION_MODELS,
              default_value: E2E_DIFFUSION_MODELS[0],
              sidebar_visible: false,
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
        newer_family_profiles: E2E_NEWER_FAMILY_PROFILES,
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
        xyzPlot: true,
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
      model_families: {
        contract_version: "f150-20260418",
        entries: E2E_MODEL_FAMILY_ENTRIES.map(
          ({ checkpoint_name: _checkpointName, vae_name: _vaeName, text_encoder_name: _textEncoderName, ...entry }) => entry,
        ),
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
        "/rookieui/xyz-plot/axes",
        "/rookieui/xyz-plot/estimate",
        "/rookieui/xyz-plot/run",
        "/rookieui/xyz-plot/sessions",
        "/rookieui/xyz-plot/sessions/{session_id}",
        "/rookieui/xyz-plot/sessions/{session_id}/cancel",
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
