const CONTROLNET_ADVANCED_CONTRACT_FALLBACK = Object.freeze({
  version: "r111-20260415",
  weight_presets: ["balanced", "soft", "strong"],
  supports_layer_weights: true,
  supports_timestep_keyframes: true,
  supports_mask_aware_apply: true,
  runtime_state: "rookieui_native_advanced_runtime",
});

export const CONTROLNET_UNION_CONTRACT_FALLBACK = Object.freeze({
  host_node: "SetUnionControlNetType",
  type_map: Object.freeze({
    OpenPose: "openpose",
    Depth: "depth",
    SoftEdge: "hed/pidi/scribble/ted",
    Scribble: "hed/pidi/scribble/ted",
    Canny: "canny/lineart/anime_lineart/mlsd",
    Lineart: "canny/lineart/anime_lineart/mlsd",
    MLSD: "canny/lineart/anime_lineart/mlsd",
    NormalMap: "normal",
    Segmentation: "segment",
    Tile: "tile",
    Inpaint: "repaint",
  }),
  unmapped_policy: "preserve_control_object",
  fallback_warning_code: "control_type_fallback_all",
  inpaint_source_mask_policy: "native_source_mask_required",
});

function createControlNetFallbackContract() {
  return {
    version: "r72-20260412",
    ui_variant: "integrated_sidebar_controlnet",
    unit_count: 3,
    advanced_contract: CONTROLNET_ADVANCED_CONTRACT_FALLBACK,
    union_contract: CONTROLNET_UNION_CONTRACT_FALLBACK,
  };
}

export function createControlNetResourceFetchers(fetchResource) {
  return {
    async fetchRookieUIControlNetModels(fetchImpl = globalThis.fetch) {
      return fetchResource(
        "/rookieui/controlnet/model_list",
        {
          source: "fallback",
          contract: createControlNetFallbackContract(),
          model_list: [],
          default_model: "",
        },
        fetchImpl,
      );
    },

    async fetchRookieUIControlNetModules(fetchImpl = globalThis.fetch) {
      return fetchResource(
        "/rookieui/controlnet/module_list",
        {
          source: "fallback",
          contract: createControlNetFallbackContract(),
          module_list: ["none", "canny"],
          default_module: "none",
        },
        fetchImpl,
      );
    },

    async fetchRookieUIControlNetTypes(fetchImpl = globalThis.fetch) {
      return fetchResource(
        "/rookieui/controlnet/control_types",
        {
          source: "fallback",
          contract: createControlNetFallbackContract(),
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
    },
  };
}
