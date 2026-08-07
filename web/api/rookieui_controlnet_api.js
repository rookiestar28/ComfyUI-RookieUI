import { rookieUIDebugWarn } from "../rookieui_debug_deps.js";
import { fetchRookieUIResource, toErrorDetail } from "./rookieui_api_transport.js";
import {
  CONTROLNET_UNION_CONTRACT_FALLBACK,
  createControlNetResourceFetchers,
} from "./rookieui_controlnet_resources.js";

const {
  fetchRookieUIControlNetModels,
  fetchRookieUIControlNetModules,
  fetchRookieUIControlNetTypes,
} = createControlNetResourceFetchers(fetchRookieUIResource);
export {
  fetchRookieUIControlNetModels,
  fetchRookieUIControlNetModules,
  fetchRookieUIControlNetTypes,
};

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
        controlnet_union_contract: CONTROLNET_UNION_CONTRACT_FALLBACK,
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
