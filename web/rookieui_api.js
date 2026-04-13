import { rookieUIDebugWarn } from "./rookieui_debug.js?v=20260411-r48-debug";

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
    controlnet: true,
    pngInfo: true,
    queue: true,
  },
  tabs: [
    { id: "txt2img", title: "Txt2Img", state: "active", enabled: true },
    { id: "img2img", title: "Img2Img", state: "active", enabled: true },
    { id: "extras", title: "Extras", state: "active", enabled: true },
    { id: "pnginfo", title: "PNG Info", state: "active", enabled: true },
    { id: "queue", title: "Queue", state: "active", enabled: true },
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
        default_cfg_scale: 7.0,
        default_sampler: "euler_ancestral",
        default_scheduler: "normal",
        default_clip_skip: 1,
        supports_clip_skip: true,
        notes: [
          "Primary A1111 parity baseline.",
          "Default prompt execution uses the RookieUI A1111 parity text-encode node at the host CLIP boundary.",
        ],
      },
      {
        id: "sdxl",
        title: "Stable Diffusion XL",
        base_family: "sdxl",
        prompt_encoder: "clip_text_encode_sdxl",
        default_width: 1024,
        default_height: 1024,
        default_steps: 28,
        default_cfg_scale: 7.0,
        default_sampler: "dpmpp_2m",
        default_scheduler: "karras",
        default_clip_skip: 1,
        supports_clip_skip: false,
        notes: [
          "SDXL parity baseline.",
          "Default prompt execution uses the RookieUI A1111 SDXL dual-encoder parity node instead of plain CLIPTextEncodeSDXL ownership.",
        ],
      },
    ],
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
  prompt_semantics: {
    contract_version: "f100-20260414",
    contract_scope: "sd-family-default-exact-with-explicit-fallbacks",
    rollout: {
      default_mode: "a1111_parity_nodes_exact",
      legacy_fallback_env: "ROOKIEUI_PROMPT_DSL_LEGACY",
      legacy_fallback_mode: "graph_compiler_approximate",
      warning_code_contract: "stable",
      exact_parity_cutover: "active_for_sd_family",
      exact_profile_ids: ["sd15", "sdxl", "pony", "illustrious", "noob"],
      approximate_profile_ids: ["flux", "qwen_image", "klein", "lumina", "zit", "wan", "anima"],
    },
    compiler_constraints: {
      conditioning_nodes: [
        "RookieUIA1111TextEncode",
        "RookieUIA1111TextEncodeSDXL",
        "ConditioningCombine",
        "ConditioningConcat",
        "ConditioningSetTimestepRange",
      ],
      execution_backend: "RookieUI A1111 parity text-encode nodes on default SD-family routes; legacy graph translation remains an explicit fallback path.",
    },
    warning_codes: {
      semantic_detection: [
        "PROMPT_AND_DETECTED",
        "PROMPT_BREAK_DETECTED",
        "PROMPT_SCHEDULE_DETECTED",
        "PROMPT_ATTENTION_DETECTED",
      ],
      fallback: ["PROMPT_LEGACY_FALLBACK_ENABLED"],
      guardrails: [
        "PROMPT_GUARD_AND_BRANCH_LIMIT",
        "PROMPT_GUARD_BREAK_CHUNK_LIMIT",
        "PROMPT_GUARD_SCHEDULE_SLICE_LIMIT",
        "PROMPT_SCHEDULE_INVALID_THRESHOLD",
      ],
      unsupported: ["PROMPT_EXTRA_NETWORK_UNSUPPORTED_REMOVED"],
    },
    capabilities: [
      {
        id: "and_composition",
        title: "AND Composition",
        a1111_semantics: "Composable multi-condition prompt branches via AND and optional branch weight suffix.",
        rookieui_contract:
          "Default SD-family routes execute A1111-native branch parsing through RookieUI parity text-encode nodes. Legacy env rollback and secondary-family non-parity lanes explicitly downgrade from this exact path.",
        status: "exact",
        translation: "rookieui_a1111_text_encode_multi_cond",
        reference: "reference/stable-diffusion-webui/modules/prompt_parser.py",
      },
      {
        id: "break_chunks",
        title: "BREAK Chunking",
        a1111_semantics: "BREAK token splits prompt chunks for chunked conditioning behavior.",
        rookieui_contract:
          "Default SD-family routes preserve tokenizer-side BREAK chunk boundaries inside RookieUI parity text-encode nodes. The legacy graph compiler remains an explicit fallback path only.",
        status: "exact",
        translation: "rookieui_a1111_text_encode_chunk_boundary",
        reference: "reference/stable-diffusion-webui/modules/prompt_parser.py",
      },
      {
        id: "prompt_scheduling",
        title: "Prompt Scheduling",
        a1111_semantics: "Schedule syntax [from:to:at] swaps text by step-progress.",
        rookieui_contract:
          "Default SD-family routes build A1111-native schedule segments at the parity text-encode boundary. Graph timestep-range compilation is retained only for explicit fallback lanes.",
        status: "exact",
        translation: "rookieui_a1111_text_encode_schedule_segments",
        reference: "reference/stable-diffusion-webui/modules/prompt_parser.py",
      },
      {
        id: "attention_weighting",
        title: "Attention Weighting",
        a1111_semantics: "Parenthesis/bracket prompt attention and explicit (text:weight) weighting.",
        rookieui_contract:
          "Default SD-family routes apply A1111-native attention parsing inside RookieUI parity text-encode nodes. Legacy rollback keeps only the older graph-compiler approximation path.",
        status: "exact",
        translation: "rookieui_a1111_text_encode_attention",
        reference: "reference/stable-diffusion-webui/modules/prompt_parser.py",
      },
      {
        id: "extra_network_lora",
        title: "Extra Network (LoRA/LyCORIS)",
        a1111_semantics: "Inline extra-network token <lora:...> / <lyco:...> merges into model graph.",
        rookieui_contract: "Deterministic extraction + merged activation chain through LoraLoader nodes.",
        status: "exact",
        translation: "lora_loader_chain",
        reference: "reference/stable-diffusion-webui/modules/extra_networks.py",
      },
      {
        id: "extra_network_other",
        title: "Extra Network (Unsupported Families)",
        a1111_semantics: "Non-LoRA extra network token families in prompt body.",
        rookieui_contract:
          "Unsupported families are stripped from the prompt payload with explicit warning diagnostics; RookieUI makes no exact execution claim for them.",
        status: "unsupported",
        translation: "warning_and_strip",
        reference: "reference/stable-diffusion-webui/modules/extra_networks.py",
      },
    ],
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
    "/rookieui/queue",
    "/rookieui/queue/{prompt_id}",
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
            categories: ["checkpoints", "vae", "text_encoders", "embeddings", "loras"],
          },
        ],
        primary_model_category_by_family: {
          sd15: "checkpoints",
          sdxl: "checkpoints",
          flux: "diffusion_models",
          qwen_image: "diffusion_models",
          klein: "diffusion_models",
          lumina: "diffusion_models",
          zit: "diffusion_models",
          wan: "diffusion_models",
          anima: "diffusion_models",
        },
        categories: {
          checkpoints: {
            title: "Checkpoints",
            items: ["__host_default__"],
            default_value: "__host_default__",
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
      presets: [
        {
          id: "sd15",
          title: "SD1.5",
          profile: "sd15",
          base_family: "sd15",
          checkpoint_name: "__host_default__",
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
          title: "SDXL",
          profile: "sdxl",
          base_family: "sdxl",
          checkpoint_name: "__host_default__",
          vae_name: "Automatic",
          text_encoder_name: "Automatic",
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
          checkpoint_name: "__host_default__",
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
          checkpoint_name: "__host_default__",
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
        {
          id: "klein",
          title: "Klein",
          profile: "klein",
          base_family: "klein",
          checkpoint_name: "__host_default__",
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
          id: "lumina",
          title: "Lumina",
          profile: "lumina",
          base_family: "lumina",
          checkpoint_name: "__host_default__",
          vae_name: "Automatic",
          text_encoder_name: "Automatic",
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
          checkpoint_name: "__host_default__",
          vae_name: "Automatic",
          text_encoder_name: "Automatic",
          width: 1024,
          height: 1024,
          steps: 8,
          cfg_scale: 1,
          sampler_name: "euler",
          scheduler_name: "normal",
          clip_skip: 1,
        },
        {
          id: "wan",
          title: "Wan",
          profile: "wan",
          base_family: "wan",
          checkpoint_name: "__host_default__",
          vae_name: "Automatic",
          text_encoder_name: "Automatic",
          width: 832,
          height: 1216,
          steps: 20,
          cfg_scale: 2,
          sampler_name: "euler",
          scheduler_name: "beta",
          clip_skip: 1,
        },
        {
          id: "anima",
          title: "Anima",
          profile: "anima",
          base_family: "anima",
          checkpoint_name: "__host_default__",
          vae_name: "Automatic",
          text_encoder_name: "Automatic",
          width: 1024,
          height: 1024,
          steps: 20,
          cfg_scale: 2,
          sampler_name: "dpmpp_2m",
          scheduler_name: "karras",
          clip_skip: 1,
        },
      ],
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
        ui_variant: "forge_neo_integrated",
        unit_count: 3,
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
        ui_variant: "forge_neo_integrated",
        unit_count: 3,
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
        ui_variant: "forge_neo_integrated",
        unit_count: 3,
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
