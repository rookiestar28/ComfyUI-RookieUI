import { rookieUIDebugWarn } from "./rookieui_debug_deps.js";

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
        notes: ["Primary A1111 parity baseline."],
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
        notes: ["SDXL parity baseline."],
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
