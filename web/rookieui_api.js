import { rookieUIDebugWarn } from "./rookieui_debug_deps.js";

const PROMPT_WORKBENCH_CONTRACT_VERSION = "r145f141f142-20260418";
const DEFAULT_MODEL_FAMILY_ENTRIES = Object.freeze([
  {
    id: "sd15",
    title: "Stable Diffusion 1.5",
    translation_base_family: "sd15",
    public_base_family: "sd15",
    prompt_encoder: "clip_text_encode",
    default_width: 512,
    default_height: 512,
    default_steps: 28,
    default_cfg_scale: 7.0,
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
    notes: [
      "Primary A1111 baseline for classic Stable Diffusion checkpoints.",
      "Uses standard CLIP text encoding and optional clip-skip projection.",
    ],
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
    default_cfg_scale: 7.0,
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
    notes: [
      "Uses SDXL dual-text-encoder semantics through CLIPTextEncodeSDXL.",
      "Acts as the baseline for SDXL-derived families in RookieUI parity lanes.",
    ],
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
    default_cfg_scale: 7.0,
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
    notes: ["SDXL-derived parity lane with community-oriented defaults preserved as SDXL translation."],
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
    default_cfg_scale: 7.0,
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
    notes: ["SDXL-derived parity lane retained as an explicit profile for A1111-style UX."],
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
    default_cfg_scale: 7.0,
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
    notes: ["SDXL-derived parity lane retained as an explicit profile for rookie-safe defaults."],
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
    default_cfg_scale: 4.0,
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
    notes: [
      "Matches the official Anima text-to-image template defaults.",
      "Text Encoder selector stays hidden because the official template owns the fixed qwen_3_06b pairing.",
    ],
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
    notes: [
      "Matches the official Chroma text-to-image template defaults.",
      "Text Encoder selector stays hidden because the official template owns the fixed T5 encoder pairing.",
    ],
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
    default_cfg_scale: 4.0,
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
    notes: [
      "Matches the official ERNIE-Image template defaults.",
      "Text Encoder selector stays hidden because the official template owns both the Ministral and prompt-enhancer pairing.",
    ],
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
    default_cfg_scale: 1.0,
    default_sampler: "euler",
    default_scheduler: "simple",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary: "Official ComfyUI ERNIE-Image Turbo template preset on the current non-SD translation seam.",
    experimental: true,
    aliases: ["ernie-image-turbo", "ernie image turbo"],
    notes: [
      "Matches the official ERNIE-Image Turbo template defaults.",
      "Text Encoder selector stays hidden because the official template owns both the Ministral and prompt-enhancer pairing.",
    ],
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
    default_cfg_scale: 1.0,
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
    notes: [
      "Matches the official Flux.1 Dev FP8 template defaults.",
      "Text Encoder selector stays hidden because the official template owns the dual-encoder bundle.",
    ],
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
    default_cfg_scale: 1.0,
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
    notes: [
      "Matches the official Flux.2 4B Distilled Klein template defaults.",
      "Text Encoder selector stays hidden because the official template owns the fixed qwen_3_4b pairing.",
    ],
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
    default_cfg_scale: 5.0,
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
    notes: [
      "Matches the official Flux.2 4B Klein template defaults.",
      "Text Encoder selector stays hidden because the official template owns the fixed qwen_3_4b pairing.",
    ],
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
    default_cfg_scale: 1.0,
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
    notes: [
      "Matches the official Flux.2 9B Distilled Klein template defaults.",
      "Text Encoder selector stays hidden because the official template owns the fixed qwen_3_8b pairing.",
    ],
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
    default_cfg_scale: 5.0,
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
    notes: [
      "Matches the official Flux.2 9B Klein template defaults.",
      "Text Encoder selector stays hidden because the official template owns the fixed qwen_3_8b pairing.",
    ],
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
    default_cfg_scale: 1.0,
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
    notes: [
      "Matches the official HiDream i1 Dev FP8 template defaults.",
      "Text Encoder selector stays hidden because the official template owns the four-encoder bundle.",
    ],
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
    default_cfg_scale: 1.0,
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
    notes: [
      "Matches the official HiDream i1 fast template defaults.",
      "Text Encoder selector stays hidden because the official template owns the four-encoder bundle.",
    ],
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
    default_cfg_scale: 5.0,
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
    notes: [
      "Matches the official HiDream i1 full template defaults.",
      "Text Encoder selector stays hidden because the official template owns the four-encoder bundle.",
    ],
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
    default_cfg_scale: 4.0,
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
    notes: [
      "Matches the official Longcat BF16 template defaults.",
      "Text Encoder selector stays hidden because the official template owns the fixed qwen_2.5_vl pairing.",
    ],
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
    default_cfg_scale: 1.0,
    default_sampler: "euler",
    default_scheduler: "simple",
    default_clip_skip: 1,
    supports_clip_skip: false,
    primary_model_category: "diffusion_models",
    text_encoder_visible: false,
    support_tier: "family-adapted",
    compatibility_summary:
      "Official ComfyUI Qwen-Image 2512 template preset on the current non-SD translation seam.",
    experimental: true,
    aliases: ["qwen image", "qwen-image 2512", "qwen image 2512"],
    notes: [
      "Matches the official Qwen-Image 2512 template defaults.",
      "Text Encoder selector stays hidden because the official template owns the fixed qwen_2.5_vl pairing and template-baked LoRA.",
    ],
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
    default_cfg_scale: 4.0,
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
    notes: [
      "Matches the official Z-Image template defaults.",
      "Text Encoder selector stays hidden because the official template owns the fixed qwen_3_4b pairing.",
    ],
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
    default_cfg_scale: 1.0,
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
    notes: [
      "Matches the official Z-Image Turbo template defaults.",
      "Text Encoder selector stays hidden because the official template owns the fixed qwen_3_4b pairing.",
    ],
  },
]);

const DEFAULT_PARITY_PROFILES = Object.freeze(
  DEFAULT_MODEL_FAMILY_ENTRIES.map((entry) => ({
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
  })),
);

const DEFAULT_TEMPLATE_PARAMETER_OVERRIDES = Object.freeze({
  chroma: { shift_visible: true, default_shift: 1.0 },
  ernie_image: {
    prompt_enhancement_visible: true,
    default_prompt_enhancement_enabled: true,
  },
  ernie_image_turbo: {
    prompt_enhancement_visible: true,
    default_prompt_enhancement_enabled: true,
  },
  hidream_i1_dev_fp8: { shift_visible: true, default_shift: 6.0 },
  hidream_i1_fast: { shift_visible: true, default_shift: 3.0 },
  hidream_i1_full: { shift_visible: true, default_shift: 3.0 },
  longcat_image: { flux_guidance_visible: true, default_flux_guidance: 4.0 },
  qwen_image: { shift_visible: true, default_shift: 3.0 },
  z_image: { shift_visible: true, default_shift: 3.0 },
  z_image_turbo: { shift_visible: true, default_shift: 3.0 },
});

const DEFAULT_PRIMARY_MODEL_CATEGORY_BY_FAMILY = Object.freeze(
  DEFAULT_MODEL_FAMILY_ENTRIES.reduce((categoryMap, entry) => {
    const keys = new Set([entry.id, entry.public_base_family, ...entry.aliases]);
    keys.forEach((key) => {
      if (typeof key === "string" && key.trim()) {
        categoryMap[key] = entry.primary_model_category;
      }
    });
    return categoryMap;
  }, {}),
);

const DEFAULT_PRESETS = Object.freeze(
  DEFAULT_MODEL_FAMILY_ENTRIES.map((entry) => ({
    id: entry.id,
    title: entry.id === "sd15" ? "SD1.5" : entry.id === "sdxl" ? "SDXL" : entry.title,
    profile: entry.id,
    base_family: entry.public_base_family,
    checkpoint_name: "__host_default__",
    vae_name: "Automatic",
    text_encoder_name: "Automatic",
    width: entry.default_width,
    height: entry.default_height,
    steps: entry.default_steps,
    cfg_scale: entry.default_cfg_scale,
    shift: DEFAULT_TEMPLATE_PARAMETER_OVERRIDES[entry.id]?.default_shift ?? null,
    flux_guidance: DEFAULT_TEMPLATE_PARAMETER_OVERRIDES[entry.id]?.default_flux_guidance ?? null,
    sampler_name: entry.default_sampler,
    scheduler_name: entry.default_scheduler,
    clip_skip: entry.default_clip_skip,
    prompt_enhancement_enabled:
      DEFAULT_TEMPLATE_PARAMETER_OVERRIDES[entry.id]?.default_prompt_enhancement_enabled ?? false,
  })),
);

const DEFAULT_NEWER_FAMILY_PROFILES = Object.freeze(
  DEFAULT_MODEL_FAMILY_ENTRIES.filter((entry) => entry.support_tier !== "parity").map((entry) => ({
    id: entry.id,
    title: entry.title,
    summary: entry.compatibility_summary,
    default: false,
    experimental: entry.experimental,
    aliases: [...entry.aliases],
  })),
);

const DEFAULT_CAPABILITIES = Object.freeze({
  service: "rookieui",
  visibility: "internal",
  // IMPORTANT: shell version must come from backend capabilities (pyproject source of truth).
  shell_version: "",
  host_surfaces: ["standalone-web", "desktop"],
  features: {
    sidebarShell: true,
    capabilityBootstrap: true,
    parityMatrix: true,
    workflowTranslation: true,
    modelInventory: true,
    presets: true,
    compatibilityLayer: true,
    txt2img: true,
    img2img: true,
    adetailer: true,
    controlnet: true,
    pngInfo: true,
    queue: true,
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
    profiles: DEFAULT_PARITY_PROFILES,
    sampler_aliases: {
      samplers: { "euler a": "euler_ancestral", "dpm++ 2m": "dpmpp_2m" },
      scheduler_aliases: { automatic: "normal", ddim: "ddim_uniform" },
      scheduler_overrides: { "dpm++ 2m karras": "karras" },
      supported_schedulers: [
        "normal",
        "karras",
        "exponential",
        "sgm_uniform",
        "simple",
        "ddim_uniform",
        "beta",
        "linear_quadratic",
        "kl_optimal",
      ],
    },
  },
  model_families: {
    contract_version: "f151-20260418",
    entries: DEFAULT_MODEL_FAMILY_ENTRIES.map((entry) => ({
      shift_visible: false,
      default_shift: null,
      flux_guidance_visible: false,
      default_flux_guidance: null,
      prompt_enhancement_visible: false,
      default_prompt_enhancement_enabled: false,
      ...entry,
      ...(DEFAULT_TEMPLATE_PARAMETER_OVERRIDES[entry.id] ?? {}),
    })),
  },
  prompt_semantics: {
    contract_version: "r55-20260411",
    contract_scope: "sd-family-first",
    rollout: {
      default_mode: "semantic_v2",
      legacy_fallback_env: "ROOKIEUI_PROMPT_DSL_LEGACY",
      warning_code_contract: "stable",
    },
    compiler_constraints: {
      conditioning_nodes: ["ConditioningCombine", "ConditioningConcat", "ConditioningSetTimestepRange"],
      execution_backend: "ComfyUI graph translation",
    },
    capabilities: [
      {
        id: "and_composition",
        title: "AND Composition",
        a1111_semantics: "Composable multi-condition prompt branches via AND and optional branch weight suffix.",
        rookieui_contract: "Parsed and compiled to multi-branch conditioning composition for SD-family execution lanes.",
        status: "supported",
        translation: "conditioning_combine",
        reference: "a1111_prompt_parser",
      },
      {
        id: "break_chunks",
        title: "BREAK Chunking",
        a1111_semantics: "BREAK token splits prompt chunks for chunked conditioning behavior.",
        rookieui_contract: "Parsed into prompt chunks and compiled with explicit chunk-composition nodes.",
        status: "supported",
        translation: "conditioning_concat",
        reference: "a1111_prompt_parser",
      },
      {
        id: "prompt_scheduling",
        title: "Prompt Scheduling",
        a1111_semantics: "Schedule syntax [from:to:at] swaps text by step-progress.",
        rookieui_contract: "Parsed into schedule slices and compiled with timestep range conditioning.",
        status: "supported",
        translation: "conditioning_set_timestep_range",
        reference: "a1111_prompt_parser",
      },
      {
        id: "attention_weighting",
        title: "Attention Weighting",
        a1111_semantics: "Parenthesis/bracket prompt attention and explicit (text:weight) weighting.",
        rookieui_contract: "Structured detection with SD-family-first weighted text preservation.",
        status: "supported",
        translation: "weighted_text_tokens",
        reference: "a1111_prompt_parser",
      },
      {
        id: "extra_network_lora",
        title: "Extra Network (LoRA/LyCORIS)",
        a1111_semantics: "Inline extra-network token <lora:...> / <lyco:...> merges into model graph.",
        rookieui_contract: "Deterministic extraction + merged activation chain through LoraLoader nodes.",
        status: "supported",
        translation: "lora_loader_chain",
        reference: "a1111_extra_networks",
      },
      {
        id: "extra_network_other",
        title: "Extra Network (Unsupported Families)",
        a1111_semantics: "Non-LoRA extra network token families in prompt body.",
        rookieui_contract: "Removed from prompt payload with explicit warning diagnostics.",
        status: "guarded",
        translation: "warning_and_strip",
        reference: "a1111_extra_networks",
      },
    ],
  },
  adetailer: {
    contract: {
      version: "r74f77-20260414",
      ui_variant: "a1111_integrated_detailer",
      unit_count: 4,
      prompt_tokens: ["[PROMPT]", "[SEP]", "[SKIP]"],
      controlnet_modes: ["none", "passthrough", "custom"],
      detector_provider_families: ["none", "ultralytics_bbox", "ultralytics_segm", "mediapipe_face"],
      detector_result_contract: "rookieui_detection_regions_v1",
      controlnet_advanced_contract: {
        version: "r111-20260415",
        weight_presets: ["balanced", "soft", "strong"],
        supports_layer_weights: true,
        supports_timestep_keyframes: true,
        supports_mask_aware_apply: true,
        runtime_state: "rookieui_native_advanced_runtime",
      },
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
    behavior_source: "integrated_detailer_contract",
    ui_reference: "localhost_7860_a1111_integrated_host",
    execution_backend: "rookieui_comfy_native_refinement_pipeline",
    skip_img2img_surfaces: ["img2img"],
    controlnet_modes: ["none", "passthrough", "custom"],
    prompt_tokens: ["[PROMPT]", "[SEP]", "[SKIP]"],
    warning_code_contract: "stable_f81",
    availability: {
      execution_backend: "rookieui_comfy_native_refinement_pipeline",
      runtime_stages: ["base_decode", "detect_mask", "inpaint_encode", "refine_sampler", "final_decode"],
      detector_source: "fallback",
      detector_count: 3,
      controlnet_model_count: 0,
      detector_runtime: {
        none: "disabled",
        ultralytics_bbox: "native_runtime_dependency_missing",
        ultralytics_segm: "native_runtime_dependency_missing",
        mediapipe_face: "native_runtime_dependency_missing",
      },
      detector_provider_families: ["none", "ultralytics_bbox", "ultralytics_segm", "mediapipe_face"],
      degraded_warning_codes: [
        "ADETAILER_DETECTOR_NOT_IN_CATALOG",
        "ADETAILER_DETECTOR_RUNTIME_FALLBACK_MASK",
        "ADETAILER_CONTROLNET_PASSTHROUGH_EMPTY",
        "ADETAILER_CONTROLNET_CUSTOM_MODEL_MISSING",
      ],
    },
    warning_codes: {
      ADETAILER_UNIT_LIMIT_TRUNCATED: "ADetailer unit payload exceeded the supported 4-unit contract and was truncated.",
      ADETAILER_SKIP_IMG2IMG_IGNORED: "ADetailer skip-img2img is only meaningful for img2img surfaces and was ignored.",
      ADETAILER_NO_ACTIVE_UNITS: "ADetailer is enabled but no enabled unit has a detector selected.",
      ADETAILER_DETECTOR_NOT_IN_CATALOG: "ADetailer detector is not present in the current host catalog; fallback mask behavior may be used.",
      ADETAILER_DETECTOR_RUNTIME_FALLBACK_MASK:
        "ADetailer detector runtime degraded to RookieUI's fallback mask seam for the selected provider family.",
      ADETAILER_CONTROLNET_PASSTHROUGH_EMPTY: "ADetailer ControlNet passthrough was requested but no primary ControlNet unit is enabled.",
      ADETAILER_CONTROLNET_CUSTOM_MODEL_MISSING: "ADetailer custom ControlNet mode was requested without a ControlNet model.",
    },
    routes: ["/rookieui/adetailer/catalog"],
  },
  routes: [
    "/rookieui/health",
    "/rookieui/bootstrap",
    "/rookieui/capabilities",
    "/rookieui/parity",
    "/rookieui/compatibility",
    "/rookieui/models",
    "/rookieui/presets",
    "/rookieui/controlnet/model_list",
    "/rookieui/controlnet/module_list",
    "/rookieui/controlnet/control_types",
    "/rookieui/controlnet/detect",
    "/rookieui/adetailer/catalog",
    "/rookieui/queue",
    "/rookieui/queue/{prompt_id}",
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
});

export function createDefaultCapabilities() {
  return JSON.parse(JSON.stringify(DEFAULT_CAPABILITIES));
}

function toErrorDetail(error) {
  if (!error) {
    return "";
  }
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

export async function fetchRookieUICapabilities(fetchImpl = globalThis.fetch) {
  if (typeof fetchImpl !== "function") {
    rookieUIDebugWarn("api.capabilities", "Using fallback capabilities because fetch() is unavailable.");
    return {
      ok: false,
      source: "fallback",
      data: createDefaultCapabilities(),
    };
  }

  try {
    const response = await fetchImpl("/rookieui/capabilities", {
      headers: { Accept: "application/json" },
    });

    if (!response?.ok) {
      throw new Error(`Capability request failed with status ${response?.status ?? "unknown"}`);
    }

    return {
      ok: true,
      source: "server",
      data: await response.json(),
    };
  } catch (_error) {
    rookieUIDebugWarn("api.capabilities", "Capability request failed; returning fallback payload.", {
      error: toErrorDetail(_error),
    });
    return {
      ok: false,
      source: "fallback",
      data: createDefaultCapabilities(),
    };
  }
}

async function fetchRookieUIResource(path, fallbackData, fetchImpl = globalThis.fetch) {
  if (typeof fetchImpl !== "function") {
    rookieUIDebugWarn("api.resource", "Using fallback resource because fetch() is unavailable.", { path });
    return { ok: false, source: "fallback", data: fallbackData };
  }

  try {
    const response = await fetchImpl(path, {
      headers: { Accept: "application/json" },
    });
    if (!response?.ok) {
      throw new Error(`Request failed with status ${response?.status ?? "unknown"}`);
    }
    return {
      ok: true,
      source: "server",
      data: await response.json(),
    };
  } catch (_error) {
    rookieUIDebugWarn("api.resource", "Resource request failed; returning fallback payload.", {
      path,
      error: toErrorDetail(_error),
    });
    return { ok: false, source: "fallback", data: fallbackData };
  }
}

export async function fetchRookieUIModels(fetchImpl = globalThis.fetch) {
  return fetchRookieUIResource(
    "/rookieui/models",
    {
      source: "fallback",
      checkpoints: ["__host_default__"],
      clip: [],
      clip_vision: [],
      controlnet: [],
      diffusion_models: [],
      vae: ["Automatic"],
      text_encoders: ["Automatic"],
      embeddings: [],
      loras: [],
      ultralytics: [],
      unet: [],
      upscale_models: [],
      default_checkpoint: "__host_default__",
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
        primary_model_category_by_family: { ...DEFAULT_PRIMARY_MODEL_CATEGORY_BY_FAMILY },
        categories: {
          checkpoints: {
            title: "Checkpoints",
            items: ["__host_default__"],
            default_value: "__host_default__",
            sidebar_visible: true,
          },
          diffusion_models: {
            title: "Diffusion Models",
            items: [],
            default_value: "",
            sidebar_visible: false,
          },
          vae: {
            title: "VAE",
            items: ["Automatic"],
            default_value: "Automatic",
            sidebar_visible: true,
          },
          text_encoders: {
            title: "Text Encoders",
            items: ["Automatic"],
            default_value: "Automatic",
            sidebar_visible: true,
          },
          embeddings: {
            title: "Embeddings",
            items: [],
            default_value: "",
            sidebar_visible: true,
          },
          loras: {
            title: "LoRAs",
            items: [],
            default_value: "",
            sidebar_visible: true,
          },
        },
      },
    },
    fetchImpl,
  );
}

export async function fetchRookieUIPresets(fetchImpl = globalThis.fetch) {
  return fetchRookieUIResource(
    "/rookieui/presets",
    {
      source: "fallback",
      presets: DEFAULT_PRESETS,
    },
    fetchImpl,
  );
}

export async function fetchRookieUICompatibility(fetchImpl = globalThis.fetch) {
  return fetchRookieUIResource(
    "/rookieui/compatibility",
    {
      source: "fallback",
      samplers: [
        { id: "euler_ancestral", title: "Euler a", tier: "core", default: true, aliases: ["euler a"] },
        { id: "euler", title: "Euler", tier: "core", default: false, aliases: [] },
        { id: "ddim", title: "DDIM", tier: "core", default: false, aliases: [] },
        { id: "dpmpp_2m", title: "DPM++ 2M", tier: "core", default: false, aliases: ["dpm++ 2m"] },
      ],
      schedulers: [
        { id: "normal", title: "Normal", tier: "core", default: true, aliases: ["automatic"] },
        { id: "karras", title: "Karras", tier: "core", default: false, aliases: [] },
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
      newer_family_profiles: DEFAULT_NEWER_FAMILY_PROFILES,
    },
    fetchImpl,
  );
}

export async function fetchRookieUIControlNetModels(fetchImpl = globalThis.fetch) {
  return fetchRookieUIResource(
    "/rookieui/controlnet/model_list",
    {
      source: "fallback",
      contract: {
        version: "r72-20260412",
        ui_variant: "integrated_sidebar_controlnet",
        unit_count: 3,
        advanced_contract: {
          version: "r111-20260415",
          weight_presets: ["balanced", "soft", "strong"],
          supports_layer_weights: true,
          supports_timestep_keyframes: true,
          supports_mask_aware_apply: true,
          runtime_state: "rookieui_native_advanced_runtime",
        },
      },
      model_list: [],
      default_model: "",
    },
    fetchImpl,
  );
}

export async function fetchRookieUIControlNetModules(fetchImpl = globalThis.fetch) {
  return fetchRookieUIResource(
    "/rookieui/controlnet/module_list",
    {
      source: "fallback",
      contract: {
        version: "r72-20260412",
        ui_variant: "integrated_sidebar_controlnet",
        unit_count: 3,
        advanced_contract: {
          version: "r111-20260415",
          weight_presets: ["balanced", "soft", "strong"],
          supports_layer_weights: true,
          supports_timestep_keyframes: true,
          supports_mask_aware_apply: true,
          runtime_state: "rookieui_native_advanced_runtime",
        },
      },
      module_list: ["none", "canny"],
      default_module: "none",
    },
    fetchImpl,
  );
}

export async function fetchRookieUIControlNetTypes(fetchImpl = globalThis.fetch) {
  return fetchRookieUIResource(
    "/rookieui/controlnet/control_types",
    {
      source: "fallback",
      contract: {
        version: "r72-20260412",
        ui_variant: "integrated_sidebar_controlnet",
        unit_count: 3,
        advanced_contract: {
          version: "r111-20260415",
          weight_presets: ["balanced", "soft", "strong"],
          supports_layer_weights: true,
          supports_timestep_keyframes: true,
          supports_mask_aware_apply: true,
          runtime_state: "rookieui_native_advanced_runtime",
        },
      },
      control_type_order: [
        "All",
        "Blur",
        "Canny",
        "Depth",
        "IP-Adapter",
        "Inpaint",
        "Instant-ID",
        "Lineart",
        "MLSD",
        "NormalMap",
        "OpenPose",
        "Reference",
        "Scribble",
        "Segmentation",
        "Shuffle",
        "Sketch",
        "SoftEdge",
        "T2I-Adapter",
        "Tile",
      ],
      default_type: "All",
      control_types: {
        All: {
          module_list: ["none", "canny"],
          model_list: [],
          default_option: "none",
        },
      },
    },
    fetchImpl,
  );
}

export async function fetchRookieUIADetailerCatalog(fetchImpl = globalThis.fetch) {
  return fetchRookieUIResource(
    "/rookieui/adetailer/catalog",
    {
      source: "fallback",
      contract: {
        version: "r74f77-20260414",
        ui_variant: "a1111_integrated_detailer",
        unit_count: 4,
        prompt_tokens: ["[PROMPT]", "[SEP]", "[SKIP]"],
        controlnet_modes: ["none", "passthrough", "custom"],
        detector_provider_families: ["none", "ultralytics_bbox", "ultralytics_segm", "mediapipe_face"],
        detector_result_contract: "rookieui_detection_regions_v1",
        controlnet_advanced_contract: {
          version: "r111-20260415",
          weight_presets: ["balanced", "soft", "strong"],
          supports_layer_weights: true,
          supports_timestep_keyframes: true,
          supports_mask_aware_apply: true,
          runtime_state: "rookieui_native_advanced_runtime",
        },
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
      detector_list: ["None", "face_yolov8n.pt", "mediapipe_face_full"],
      detectors: [
        { id: "None", label: "None", family: "none", source: "builtin", supports_class_filter: false },
        {
          id: "face_yolov8n.pt",
          label: "face_yolov8n.pt",
          family: "ultralytics_bbox",
          source: "fallback",
          supports_class_filter: false,
          supports_mask_refine: false,
        },
        {
          id: "mediapipe_face_full",
          label: "mediapipe_face_full",
          family: "mediapipe_face",
          source: "builtin",
          supports_class_filter: false,
          supports_mask_refine: false,
        },
      ],
      default_detector: "None",
      prompt_tokens: ["[PROMPT]", "[SEP]", "[SKIP]"],
      skip_img2img_surfaces: ["img2img"],
      controlnet_modes: ["none", "passthrough", "custom"],
      controlnet_model_list: [],
      controlnet_default_model: "",
      controlnet_module_list: ["none"],
      controlnet_default_module: "none",
      checkpoint_choices: ["__host_default__"],
      vae_choices: ["Automatic"],
      sampler_choices: ["Euler a", "DPM++ 2M Karras"],
      scheduler_choices: ["Normal", "Karras"],
      mask_filter_methods: ["Area", "Confidence"],
      mask_merge_modes: ["None", "Merge", "Merge and Invert"],
      availability: {
        execution_backend: "rookieui_comfy_native_refinement_pipeline",
        runtime_stages: ["base_decode", "detect_mask", "inpaint_encode", "refine_sampler", "final_decode"],
        detector_source: "fallback",
        detector_count: 3,
        controlnet_model_count: 0,
        detector_runtime: {
          none: "disabled",
          ultralytics_bbox: "native_runtime_dependency_missing",
          ultralytics_segm: "native_runtime_dependency_missing",
          mediapipe_face: "native_runtime_dependency_missing",
        },
        detector_provider_families: ["none", "ultralytics_bbox", "ultralytics_segm", "mediapipe_face"],
        degraded_warning_codes: [
          "ADETAILER_DETECTOR_NOT_IN_CATALOG",
          "ADETAILER_DETECTOR_RUNTIME_FALLBACK_MASK",
          "ADETAILER_CONTROLNET_PASSTHROUGH_EMPTY",
          "ADETAILER_CONTROLNET_CUSTOM_MODEL_MISSING",
        ],
      },
      warning_codes: {
        ADETAILER_UNIT_LIMIT_TRUNCATED: "ADetailer unit payload exceeded the supported 4-unit contract and was truncated.",
        ADETAILER_SKIP_IMG2IMG_IGNORED: "ADetailer skip-img2img is only meaningful for img2img surfaces and was ignored.",
        ADETAILER_NO_ACTIVE_UNITS: "ADetailer is enabled but no enabled unit has a detector selected.",
        ADETAILER_DETECTOR_NOT_IN_CATALOG: "ADetailer detector is not present in the current host catalog; fallback mask behavior may be used.",
        ADETAILER_DETECTOR_RUNTIME_FALLBACK_MASK:
          "ADetailer detector runtime degraded to RookieUI's fallback mask seam for the selected provider family.",
        ADETAILER_CONTROLNET_PASSTHROUGH_EMPTY: "ADetailer ControlNet passthrough was requested but no primary ControlNet unit is enabled.",
        ADETAILER_CONTROLNET_CUSTOM_MODEL_MISSING: "ADetailer custom ControlNet mode was requested without a ControlNet model.",
      },
    },
    fetchImpl,
  );
}

export async function fetchRookieUIPromptWorkbenchConfig(fetchImpl = globalThis.fetch) {
  return fetchRookieUIResource(
    "/rookieui/prompt-tools/config",
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_config",
        route_family: "/rookieui/prompt-tools",
        state_schema_version: 1,
        namespaces: ["txt2img_prompt", "txt2img_negative", "img2img_prompt", "img2img_negative"],
        provider_secret_field_keys: ["access_token", "api_key", "authorization", "password", "secret", "token"],
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
          instruction_preset:
            "Write a concise Stable Diffusion prompt from the user's image description. Keep the result comma-separated and production-ready. Preserve any explicit prompt syntax the user already includes. Do not add explanation, markdown, numbering, or surrounding quotes. Return prompt text only.",
        },
      },
      blacklist: {
        enabled: false,
        entries: [],
      },
      host_actions: {
        danbooru_upsample: {
          action_id: "danbooru_upsample",
          title: "Upsample Tags",
          route_path: "/rookieui/prompt-tools/upsample",
          available: false,
          fixed_profile: "host_node_defaults",
          node_aliases: ["DanbooruTagsUpsampler", "DanbooruTagsUpsamplerNodeRay"],
          resolved_node_alias: "",
          availability: {
            status: "host_missing",
            detail: "Host-installed Danbooru upsampler node is not available in the active ComfyUI registry.",
          },
          input_fields: ["prompt", "negative_prompt_tags", "ban_tags"],
        },
      },
      language_options: [
        { code: "en", title: "English" },
        { code: "zh-TW", title: "Traditional Chinese" },
        { code: "zh-CN", title: "Simplified Chinese" },
        { code: "ja", title: "Japanese" },
        { code: "ko", title: "Korean" },
      ],
      theme_style_options: [
        { id: "rookieui_classic", title: "RookieUI Classic", summary: "Default RookieUI framing with neutral panel contrast." },
        { id: "rookieui_graphite", title: "Graphite Studio", summary: "Higher-contrast shell chrome for denser prompt editing sessions." },
        { id: "rookieui_paper", title: "Paper Notes", summary: "Lighter note-card treatment for catalog and prompt drafting work." },
      ],
    },
    fetchImpl,
  );
}

function buildPromptWorkbenchNamespacePath(basePath, namespace) {
  const normalizedNamespace = String(namespace ?? "").trim();
  if (!normalizedNamespace) {
    return basePath;
  }
  const params = new URLSearchParams({ namespace: normalizedNamespace });
  return `${basePath}?${params.toString()}`;
}

async function postRookieUIJson(path, payload, fallbackData, fetchImpl = globalThis.fetch) {
  if (typeof fetchImpl !== "function") {
    rookieUIDebugWarn("api.resource_post", "Using fallback payload because fetch() is unavailable.", { path });
    return { ok: false, status: 0, data: fallbackData };
  }

  try {
    const response = await fetchImpl(path, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload ?? {}),
    });
    const data = await response.json();
    return {
      ok: response.ok,
      status: response.status,
      data,
    };
  } catch (_error) {
    rookieUIDebugWarn("api.resource_post", "POST request failed; returning fallback payload.", {
      path,
      error: toErrorDetail(_error),
    });
    return { ok: false, status: 0, data: fallbackData };
  }
}

export async function fetchRookieUIPromptWorkbenchState(namespace, fetchImpl = globalThis.fetch) {
  const normalizedNamespace = String(namespace ?? "").trim();
  return fetchRookieUIResource(
    buildPromptWorkbenchNamespacePath("/rookieui/prompt-tools/state", normalizedNamespace),
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_state",
      },
      namespace: normalizedNamespace,
      state: {
        namespace: normalizedNamespace,
        workbench_open: false,
        active_panel: "editor",
        draft_prompt: "",
        selected_entry_id: "",
      },
    },
    fetchImpl,
  );
}

export async function updateRookieUIPromptWorkbenchState(namespace, state, fetchImpl = globalThis.fetch) {
  const normalizedNamespace = String(namespace ?? "").trim();
  return postRookieUIJson(
    "/rookieui/prompt-tools/state",
    {
      namespace: normalizedNamespace,
      state: state ?? {},
    },
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_state",
      },
      namespace: normalizedNamespace,
      state: {
        namespace: normalizedNamespace,
        workbench_open: Boolean(state?.workbench_open),
        active_panel: String(state?.active_panel ?? "editor"),
        draft_prompt: String(state?.draft_prompt ?? ""),
        selected_entry_id: String(state?.selected_entry_id ?? ""),
      },
      saved: false,
    },
    fetchImpl,
  );
}

export async function fetchRookieUIPromptWorkbenchHistory(namespace, fetchImpl = globalThis.fetch) {
  const normalizedNamespace = String(namespace ?? "").trim();
  return fetchRookieUIResource(
    buildPromptWorkbenchNamespacePath("/rookieui/prompt-tools/history", normalizedNamespace),
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_history",
      },
      namespace: normalizedNamespace,
      items: [],
    },
    fetchImpl,
  );
}

export async function fetchRookieUIPromptWorkbenchFavorites(namespace, fetchImpl = globalThis.fetch) {
  const normalizedNamespace = String(namespace ?? "").trim();
  return fetchRookieUIResource(
    buildPromptWorkbenchNamespacePath("/rookieui/prompt-tools/favorites", normalizedNamespace),
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_favorites",
      },
      namespace: normalizedNamespace,
      items: [],
    },
    fetchImpl,
  );
}

export async function fetchRookieUIPromptWorkbenchProviders(fetchImpl = globalThis.fetch) {
  return fetchRookieUIResource(
    "/rookieui/prompt-tools/providers",
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_providers",
      },
      surfaces: {
        translation: { providers: [], shipped_provider_ids: [], deferred_provider_ids: [], reference_only_provider_ids: [] },
        ai_assist: { providers: [], shipped_provider_ids: [], deferred_provider_ids: [], reference_only_provider_ids: [] },
      },
    },
    fetchImpl,
  );
}

export async function fetchRookieUIPromptWorkbenchCatalog(language = "en", fetchImpl = globalThis.fetch) {
  const params = new URLSearchParams();
  const normalizedLanguage = String(language ?? "").trim();
  if (normalizedLanguage) {
    params.set("language", normalizedLanguage);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return fetchRookieUIResource(
    `/rookieui/prompt-tools/catalog${suffix}`,
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_catalog",
      },
      group_tags: { language: normalizedLanguage || "en", source: "fallback", groups: [] },
      prompt_library: { source: "fallback", sections: [] },
      extra_networks: { embeddings: [], loras: [] },
    },
    fetchImpl,
  );
}

export async function translateRookieUIPromptWorkbench(payload, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/prompt-tools/translate",
    payload ?? {},
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_translate",
      },
      provider_id: String(payload?.provider ?? ""),
      provider_title: "",
      mode: Array.isArray(payload?.texts) ? "batch" : "single",
      from_lang: String(payload?.from_lang ?? "auto"),
      to_lang: String(payload?.to_lang ?? "en"),
      translated_text: String(payload?.text ?? ""),
      translated_texts: Array.isArray(payload?.texts) ? payload.texts.map((value) => String(value ?? "")) : [],
    },
    fetchImpl,
  );
}

export async function assistRookieUIPromptWorkbench(payload, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/prompt-tools/assist",
    payload ?? {},
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_assist",
      },
      provider_id: String(payload?.provider ?? ""),
      provider_title: "",
      language: String(payload?.language ?? "en"),
      theme_style: String(payload?.theme_style ?? "rookieui_classic"),
      instruction_preset: String(payload?.instruction_preset ?? ""),
      image_description: String(payload?.image_description ?? ""),
      generated_prompt: "",
    },
    fetchImpl,
  );
}

export async function upsampleRookieUIPromptWorkbench(payload, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/prompt-tools/upsample",
    payload ?? {},
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_upsample",
      },
      action_id: "danbooru_upsample",
      final_prompt: String(payload?.prompt ?? ""),
      generated_suffix: "",
      host_node_alias: "",
      availability: {
        status: "host_missing",
        detail: "Host-installed Danbooru upsampler node is not available in the active ComfyUI registry.",
      },
      warnings: [],
      warning_codes: [],
    },
    fetchImpl,
  );
}

export async function updateRookieUIPromptWorkbenchConfig(config, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/prompt-tools/config",
    { config: config ?? {} },
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_config",
      },
      config: config ?? {},
      saved: false,
    },
    fetchImpl,
  );
}

export async function fetchRookieUIPromptWorkbenchBlacklist(fetchImpl = globalThis.fetch) {
  return fetchRookieUIResource(
    "/rookieui/prompt-tools/blacklist",
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_blacklist",
      },
      blacklist: {
        enabled: false,
        entries: [],
      },
    },
    fetchImpl,
  );
}

export async function fetchRookieUIXYZPlotAxes(fetchImpl = globalThis.fetch) {
  return fetchRookieUIResource(
    "/rookieui/xyz-plot/axes",
    {
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
        },
        cfg_scale: {
          axis_id: "cfg_scale",
          title: "CFG Scale",
          support_tier: "direct",
          mode_scopes: ["txt2img", "img2img"],
          value_input_mode: "float_csv_or_range",
          choices: [],
          session_runner_support: true,
        },
        sampler: {
          axis_id: "sampler",
          title: "Sampler",
          support_tier: "direct",
          mode_scopes: ["txt2img", "img2img"],
          value_input_mode: "choices_or_csv",
          choices: [],
          session_runner_support: true,
        },
      },
      axis_order: ["steps", "cfg_scale", "sampler"],
    },
    fetchImpl,
  );
}

export async function submitRookieUIXYZPlotEstimate(payload, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/xyz-plot/estimate",
    payload ?? {},
    {
      contract: {
        version: "r125-20260417",
        surface: "xyz_plot_estimate",
        route_family: "/rookieui/xyz-plot",
      },
      estimate: {
        cell_count: 0,
        generated_image_count: 0,
        total_steps: 0,
        projected_grid_megapixels: 0,
        max_grid_megapixels: 200,
      },
      can_run: false,
      warnings: [],
      warning_codes: [],
    },
    fetchImpl,
  );
}

export async function submitRookieUIXYZPlotRun(payload, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/xyz-plot/run",
    payload ?? {},
    {
      contract: {
        version: "r125-20260417",
        surface: "xyz_plot_run",
        route_family: "/rookieui/xyz-plot",
      },
      session: {
        session_id: "",
        status: "pending",
        summary: { total_cells: 0, pending_cells: 0 },
        axes: [],
        results: { status: "pending", main_grid: {}, sub_grids: [], lone_images: [], warnings: [] },
      },
    },
    fetchImpl,
  );
}

function buildXYZPlotSessionsPath(clientId) {
  if (!clientId) {
    return "/rookieui/xyz-plot/sessions";
  }
  const params = new URLSearchParams({ client_id: clientId });
  return `/rookieui/xyz-plot/sessions?${params.toString()}`;
}

export async function fetchRookieUIXYZPlotSessions(fetchImpl = globalThis.fetch, options = {}) {
  const clientId = typeof options?.clientId === "string" ? options.clientId : "";
  return fetchRookieUIResource(
    buildXYZPlotSessionsPath(clientId),
    {
      contract: {
        version: "r125-20260417",
        surface: "xyz_plot_session_list",
        route_family: "/rookieui/xyz-plot",
      },
      sessions: [],
    },
    fetchImpl,
  );
}

export async function fetchRookieUIXYZPlotSessionDetail(sessionId, options = {}, fetchImpl = globalThis.fetch) {
  const normalizedSessionId = String(sessionId ?? "").trim();
  if (!normalizedSessionId) {
    return {
      ok: false,
      status: 400,
      data: {
        status: "invalid-request",
        detail: "sessionId is required.",
      },
    };
  }
  const clientId = typeof options?.clientId === "string" ? options.clientId : "";
  const params = new URLSearchParams();
  if (clientId) {
    params.set("client_id", clientId);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return fetchRookieUIResource(
    `/rookieui/xyz-plot/sessions/${encodeURIComponent(normalizedSessionId)}${suffix}`,
    {
      contract: {
        version: "r125-20260417",
        surface: "xyz_plot_session_detail",
        route_family: "/rookieui/xyz-plot",
      },
      session: {
        session_id: normalizedSessionId,
        status: "pending",
        summary: { total_cells: 0, pending_cells: 0 },
        axes: [],
        cells: [],
        results: { status: "pending", main_grid: {}, sub_grids: [], lone_images: [], warnings: [] },
      },
    },
    fetchImpl,
  );
}

export async function cancelRookieUIXYZPlotSession(sessionId, options = {}, fetchImpl = globalThis.fetch) {
  const normalizedSessionId = String(sessionId ?? "").trim();
  if (!normalizedSessionId) {
    return {
      ok: false,
      status: 400,
      data: {
        status: "invalid-request",
        detail: "sessionId is required.",
      },
    };
  }
  const clientId = typeof options?.clientId === "string" ? options.clientId : "";
  return postRookieUIJson(
    `/rookieui/xyz-plot/sessions/${encodeURIComponent(normalizedSessionId)}/cancel`,
    clientId ? { client_id: clientId } : {},
    {
      contract: {
        version: "r125-20260417",
        surface: "xyz_plot_session_cancel",
        route_family: "/rookieui/xyz-plot",
      },
      session: {
        session_id: normalizedSessionId,
        status: "cancelled",
        cancel_requested: true,
        summary: { total_cells: 0, cancelled_cells: 0 },
        axes: [],
        cells: [],
        results: { status: "pending", main_grid: {}, sub_grids: [], lone_images: [], warnings: [] },
      },
    },
    fetchImpl,
  );
}

export async function updateRookieUIPromptWorkbenchBlacklist(blacklist, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/prompt-tools/blacklist",
    { blacklist: blacklist ?? {} },
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_blacklist",
      },
      blacklist: blacklist ?? { enabled: false, entries: [] },
    },
    fetchImpl,
  );
}

export async function updateRookieUIPromptWorkbenchHistory(namespace, action, payload, fetchImpl = globalThis.fetch) {
  const normalizedNamespace = String(namespace ?? "").trim();
  const normalizedAction = String(action ?? "").trim() || "push";
  return postRookieUIJson(
    "/rookieui/prompt-tools/history",
    {
      namespace: normalizedNamespace,
      action: normalizedAction,
      ...(payload && typeof payload === "object" ? payload : {}),
    },
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_history",
      },
      namespace: normalizedNamespace,
      items: [],
    },
    fetchImpl,
  );
}

export async function updateRookieUIPromptWorkbenchFavorites(namespace, action, payload, fetchImpl = globalThis.fetch) {
  const normalizedNamespace = String(namespace ?? "").trim();
  const normalizedAction = String(action ?? "").trim() || "push";
  return postRookieUIJson(
    "/rookieui/prompt-tools/favorites",
    {
      namespace: normalizedNamespace,
      action: normalizedAction,
      ...(payload && typeof payload === "object" ? payload : {}),
    },
    {
      contract: {
        version: PROMPT_WORKBENCH_CONTRACT_VERSION,
        surface: "prompt_tools_favorites",
      },
      namespace: normalizedNamespace,
      items: [],
    },
    fetchImpl,
  );
}

export async function detectRookieUIControlNet(payload, fetchImpl = globalThis.fetch) {
  if (typeof fetchImpl !== "function") {
    rookieUIDebugWarn("api.controlnet_detect", "Detect request skipped because fetch() is unavailable.");
    return {
      ok: false,
      status: 0,
      data: {
        status: "network-unavailable",
        detail: "RookieUI controlnet detect is unavailable without fetch().",
      },
    };
  }

  try {
    const response = await fetchImpl("/rookieui/controlnet/detect", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    return {
      ok: response.ok,
      status: response.status,
      data,
    };
  } catch (_error) {
    rookieUIDebugWarn("api.controlnet_detect", "Detect request failed before reaching backend.", {
      error: toErrorDetail(_error),
    });
    return {
      ok: false,
      status: 0,
      data: {
        status: "network-unavailable",
        detail: "RookieUI controlnet detect failed before reaching the backend.",
      },
    };
  }
}

function buildQueuePath(clientId) {
  if (!clientId) {
    return "/rookieui/queue";
  }
  const params = new URLSearchParams({ client_id: clientId });
  return `/rookieui/queue?${params.toString()}`;
}

export async function fetchRookieUIQueue(fetchImpl = globalThis.fetch, options = {}) {
  const clientId = typeof options?.clientId === "string" ? options.clientId : "";
  return fetchRookieUIResource(
    buildQueuePath(clientId),
    {
      source: "fallback",
      queue_remaining: 0,
      jobs: [],
    },
    fetchImpl,
  );
}

export async function fetchRookieUIQueueJob(promptId, options = {}, fetchImpl = globalThis.fetch) {
  const normalizedPromptId = String(promptId ?? "").trim();
  if (!normalizedPromptId) {
    return {
      ok: false,
      status: 400,
      data: {
        status: "invalid-request",
        detail: "promptId is required.",
      },
    };
  }
  const clientId = typeof options?.clientId === "string" ? options.clientId : "";
  const params = new URLSearchParams();
  if (clientId) {
    params.set("client_id", clientId);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const path = `/rookieui/queue/${encodeURIComponent(normalizedPromptId)}${suffix}`;
  return fetchRookieUIResource(
    path,
    {
      source: "fallback",
      queue_remaining: 0,
      job: null,
    },
    fetchImpl,
  );
}

export async function fetchRookieUIHistoryPrompt(promptId, fetchImpl = globalThis.fetch) {
  const normalizedPromptId = String(promptId ?? "").trim();
  if (!normalizedPromptId) {
    return {
      ok: false,
      status: 400,
      data: {
        status: "invalid-request",
        detail: "promptId is required.",
      },
    };
  }
  return fetchRookieUIResource(`/history/${encodeURIComponent(normalizedPromptId)}`, {}, fetchImpl);
}

export async function submitRookieUITxt2Img(payload, fetchImpl = globalThis.fetch) {
  if (typeof fetchImpl !== "function") {
    rookieUIDebugWarn("api.submit_txt2img", "Submission skipped because fetch() is unavailable.");
    return {
      ok: false,
      status: 0,
      data: {
        status: "network-unavailable",
        detail: "RookieUI txt2img submission is unavailable without fetch().",
      },
    };
  }

  try {
    const response = await fetchImpl("/rookieui/generate/txt2img", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    return {
      ok: response.ok,
      status: response.status,
      data,
    };
  } catch (_error) {
    rookieUIDebugWarn("api.submit_txt2img", "Submission failed before reaching backend.", {
      error: toErrorDetail(_error),
    });
    return {
      ok: false,
      status: 0,
      data: {
        status: "network-unavailable",
        detail: "RookieUI txt2img submission failed before reaching the backend.",
      },
    };
  }
}

export async function submitRookieUIImg2Img(payload, fetchImpl = globalThis.fetch) {
  if (typeof fetchImpl !== "function") {
    rookieUIDebugWarn("api.submit_img2img", "Submission skipped because fetch() is unavailable.");
    return {
      ok: false,
      status: 0,
      data: {
        status: "network-unavailable",
        detail: "RookieUI img2img submission is unavailable without fetch().",
      },
    };
  }

  try {
    const response = await fetchImpl("/rookieui/generate/img2img", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    return {
      ok: response.ok,
      status: response.status,
      data,
    };
  } catch (_error) {
    rookieUIDebugWarn("api.submit_img2img", "Submission failed before reaching backend.", {
      error: toErrorDetail(_error),
    });
    return {
      ok: false,
      status: 0,
      data: {
        status: "network-unavailable",
        detail: "RookieUI img2img submission failed before reaching the backend.",
      },
    };
  }
}

export async function inspectRookieUIPngInfo(payload, fetchImpl = globalThis.fetch) {
  if (typeof fetchImpl !== "function") {
    rookieUIDebugWarn("api.inspect_pnginfo", "Inspection skipped because fetch() is unavailable.");
    return {
      ok: false,
      status: 0,
      data: {
        status: "network-unavailable",
        detail: "RookieUI pnginfo inspection is unavailable without fetch().",
      },
    };
  }

  try {
    const response = await fetchImpl("/rookieui/pnginfo/inspect", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    return {
      ok: response.ok,
      status: response.status,
      data,
    };
  } catch (_error) {
    rookieUIDebugWarn("api.inspect_pnginfo", "Inspection request failed before reaching backend.", {
      error: toErrorDetail(_error),
    });
    return {
      ok: false,
      status: 0,
      data: {
        status: "network-unavailable",
        detail: "RookieUI pnginfo inspection failed before reaching the backend.",
      },
    };
  }
}

export async function submitRookieUIExtras(payload, fetchImpl = globalThis.fetch) {
  if (typeof fetchImpl !== "function") {
    rookieUIDebugWarn("api.submit_extras", "Submission skipped because fetch() is unavailable.");
    return {
      ok: false,
      status: 0,
      data: {
        status: "network-unavailable",
        detail: "RookieUI extras submission is unavailable without fetch().",
      },
    };
  }

  try {
    const response = await fetchImpl("/rookieui/extras/run", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    return {
      ok: response.ok,
      status: response.status,
      data,
    };
  } catch (_error) {
    rookieUIDebugWarn("api.submit_extras", "Submission failed before reaching backend.", {
      error: toErrorDetail(_error),
    });
    return {
      ok: false,
      status: 0,
      data: {
        status: "network-unavailable",
        detail: "RookieUI extras submission failed before reaching the backend.",
      },
    };
  }
}

export { inspectRookieUIPngInfo as parseRookieUIPngInfo };
