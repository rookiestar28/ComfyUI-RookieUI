function buildResult(data, source = "fixture") {
  return { source, data };
}

export function createVueSpikeLoaders() {
  const modelFamilies = {
    contract_version: "f72-20260418",
    entries: [
      {
        id: "sdxl",
        title: "Stable Diffusion XL",
        translation_base_family: "sdxl",
        support_tier: "parity",
        primary_model_category: "checkpoints",
        text_encoder_visible: false,
      },
      {
        id: "flux",
        title: "Flux",
        translation_base_family: "sdxl",
        support_tier: "family-adapted",
        primary_model_category: "diffusion_models",
        text_encoder_visible: true,
      },
    ],
  };

  return {
    capabilities: async () =>
      buildResult({
        service: "rookieui",
        host_surfaces: ["desktop"],
        parity: {
          profiles: [
            {
              id: "sdxl",
              title: "Stable Diffusion XL",
              base_family: "sdxl",
              default_width: 1024,
              default_height: 1024,
            },
            {
              id: "flux",
              title: "Flux",
              base_family: "sdxl",
              default_width: 1024,
              default_height: 1024,
            },
          ],
        },
        model_families: modelFamilies,
      }),
    compatibility: async () =>
      buildResult({
        samplers: ["euler", "euler_ancestral"],
        schedulers: ["normal", "beta"],
        dtype_profiles: ["fp16", "bf16"],
      }),
    models: async () =>
      buildResult({
        catalog: {
          primary_model_category_by_family: {
            sdxl: "checkpoints",
            flux: "diffusion_models",
          },
        },
        checkpoints: ["sdxl-base.safetensors"],
        diffusion_models: ["flux1-dev.safetensors"],
      }),
    presets: async () =>
      buildResult({
        presets: [
          {
            id: "sdxl",
            title: "Stable Diffusion XL",
            profile: "sdxl",
            base_family: "sdxl",
          },
          {
            id: "flux",
            title: "Flux",
            profile: "flux",
            base_family: "flux",
          },
        ],
      }),
    controlnetModels: async () =>
      buildResult({
        model_list: ["canny.safetensors"],
        default_model: "canny.safetensors",
      }),
    controlnetModules: async () =>
      buildResult({
        module_list: ["none", "canny"],
        default_module: "none",
      }),
    controlnetTypes: async () =>
      buildResult({
        control_type_order: ["All", "Canny"],
        default_type: "All",
        control_types: {
          Canny: {
            module_list: ["none", "canny"],
            model_list: ["canny.safetensors"],
          },
        },
      }),
    adetailerCatalog: async () =>
      buildResult({
        detectors: [{ id: "face_yolov8n.pt", label: "Face" }],
      }),
    promptWorkbench: async () =>
      buildResult({
        config: {
          language: "en",
          theme_style: "host",
        },
      }),
    xyzPlot: async () =>
      buildResult({
        axes: {
          steps: { axis_id: "steps", title: "Steps" },
          cfg_scale: { axis_id: "cfg_scale", title: "CFG Scale" },
        },
      }),
    queue: async (_fetchImpl, { clientId }) =>
      buildResult({
        jobs: [],
        queue_remaining: 0,
        clientId,
      }),
  };
}
