import {
  CANVAS_FULLSCREEN_ACTIONS,
  CANVAS_ACTIONS,
  canCanvasStageOpenUpload,
  hasCanvasSourceImage,
  isCanvasElementFullscreen,
  resolveCanvasInteractionMode,
  toggleCanvasFullscreen,
} from "./rookieui_canvas_surface_contract.js";
import { createSourceCanvasBrushController } from "./rookieui_canvas_brush_deps.js";

const DEFAULT_UNIT_COUNT = 3;
const DEFAULT_CONTROL_TYPE = "All";

const MODULE_OPTIONS = [
  { value: "none", label: "None" },
  { value: "blur", label: "blur" },
  { value: "canny", label: "Canny" },
  { value: "depth", label: "Depth" },
  { value: "depth_anything_v2", label: "depth_anything_v2" },
  { value: "depth_anything", label: "depth_anything" },
  { value: "depth_midas", label: "depth_midas" },
  { value: "depth_zoe", label: "depth_zoe" },
  { value: "depth_leres", label: "depth_leres" },
  { value: "normalmap", label: "normalmap" },
  { value: "normal_midas", label: "normal_midas" },
  { value: "normal_bae", label: "normal_bae" },
  { value: "normal_dsine", label: "normal_dsine" },
  { value: "openpose", label: "OpenPose" },
  { value: "openpose_full", label: "openpose_full" },
  { value: "openpose_dw", label: "openpose_dw" },
  { value: "openpose_animal", label: "openpose_animal" },
  { value: "openpose_densepose", label: "openpose_densepose" },
  { value: "mlsd", label: "mlsd" },
  { value: "lineart", label: "Lineart" },
  { value: "lineart_anime", label: "lineart_anime" },
  { value: "lineart_anime_denoise", label: "lineart_anime_denoise" },
  { value: "lineart_coarse", label: "lineart_coarse" },
  { value: "lineart_realistic", label: "lineart_realistic" },
  { value: "lineart_standard", label: "lineart_standard" },
  { value: "scribble", label: "Scribble" },
  { value: "scribble_xdog", label: "scribble_xdog" },
  { value: "scribble_pidinet", label: "scribble_pidinet" },
  { value: "scribble_fake", label: "scribble_fake" },
  { value: "segmentation", label: "segmentation" },
  { value: "segmentation_oneformer_coco", label: "segmentation_oneformer_coco" },
  { value: "segmentation_oneformer_ade20k", label: "segmentation_oneformer_ade20k" },
  { value: "segmentation_uniformer", label: "segmentation_uniformer" },
  { value: "segmentation_anime_face", label: "segmentation_anime_face" },
  { value: "shuffle", label: "shuffle" },
  { value: "sketch", label: "sketch" },
  { value: "sketch_scribble", label: "sketch_scribble" },
  { value: "sketch_lineart", label: "sketch_lineart" },
  { value: "sketch_hed", label: "sketch_hed" },
  { value: "softedge", label: "SoftEdge" },
  { value: "softedge_hed", label: "softedge_hed" },
  { value: "softedge_pidinet", label: "softedge_pidinet" },
  { value: "softedge_teed", label: "softedge_teed" },
  { value: "reference", label: "reference" },
  { value: "ipadapter", label: "ipadapter" },
  { value: "instantid", label: "instantid" },
  { value: "t2iadapter", label: "t2iadapter" },
  { value: "tile", label: "tile" },
  { value: "tile_simple", label: "tile_simple" },
  { value: "tile_gf", label: "tile_gf" },
  { value: "inpaint", label: "Inpaint" },
];

const DEPTH_PREPROCESSOR_OPTIONS = [
  "depth",
  "depth_anything_v2",
  "depth_anything",
  "depth_midas",
  "depth_zoe",
  "depth_leres",
];
const LINEART_PREPROCESSOR_OPTIONS = [
  "lineart",
  "lineart_anime",
  "lineart_anime_denoise",
  "lineart_coarse",
  "lineart_realistic",
  "lineart_standard",
];
const OPENPOSE_PREPROCESSOR_OPTIONS = [
  "openpose",
  "openpose_full",
  "openpose_dw",
  "openpose_animal",
  "openpose_densepose",
];
const SOFTEDGE_PREPROCESSOR_OPTIONS = ["softedge", "softedge_hed", "softedge_pidinet", "softedge_teed"];
const SCRIBBLE_PREPROCESSOR_OPTIONS = ["scribble", "scribble_xdog", "scribble_pidinet", "scribble_fake"];

const DEFAULT_CONTROL_TYPE_OPTIONS = [
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
];

const CONTROL_MODE_OPTIONS = [
  { value: "balanced", label: "Balanced" },
  { value: "prompt", label: "My prompt is more important" },
  { value: "control", label: "ControlNet is more important" },
];

const HR_OPTION_OPTIONS = [
  { value: "both", label: "Both" },
  { value: "low_res_only", label: "Low-res Only" },
  { value: "high_res_only", label: "High-res Only" },
];

const RESIZE_MODE_OPTIONS = [
  { value: "crop_and_resize", label: "Crop and Resize" },
  { value: "just_resize", label: "Just Resize" },
  { value: "resize_and_fill", label: "Resize and Fill" },
];

const FILE_SELECTION_PLACEHOLDER = "No file selected";
const FILE_PAYLOAD_PLACEHOLDER = "Loaded from payload";
const PREVIEW_UPLOAD_ICON = "⤴";
const RUN_PREPROCESSOR_ICON = "💥";
const RUN_PREPROCESSOR_BUSY_ICON = "⏳";
const RUN_PREPROCESSOR_TIMEOUT_MS = 30000;
const FULLSCREEN_ENTER_ICON = "⛶";
const FULLSCREEN_EXIT_ICON = "🗗";

function toObjectArray(rawValue) {
  if (typeof rawValue !== "string" || !rawValue.trim()) {
    return [];
  }
  try {
    const parsed = JSON.parse(rawValue);
    return Array.isArray(parsed) ? parsed.filter((entry) => entry && typeof entry === "object") : [];
  } catch (_error) {
    return [];
  }
}

function normalizeNumber(value, fallbackValue) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallbackValue;
}

function normalizeControlTypeOrder(rawControlTypeOrder = []) {
  const normalized = Array.isArray(rawControlTypeOrder)
    ? rawControlTypeOrder.map((value) => String(value ?? "").trim()).filter(Boolean)
    : [];
  const ordered = normalized.length > 0 ? normalized : [...DEFAULT_CONTROL_TYPE_OPTIONS];
  if (!ordered.includes(DEFAULT_CONTROL_TYPE)) {
    ordered.unshift(DEFAULT_CONTROL_TYPE);
  }
  DEFAULT_CONTROL_TYPE_OPTIONS.forEach((typeLabel) => {
    if (!ordered.includes(typeLabel)) {
      ordered.push(typeLabel);
    }
  });
  return ordered;
}

function slugifyLabel(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function toOptionEntries(values, fallbackLabels = {}) {
  return values
    .map((value) => String(value ?? "").trim())
    .filter(Boolean)
    .map((value) => ({ value, label: fallbackLabels[value] ?? value }));
}

function createCustomField(parent, labelText, control, extraClass = "") {
  const field = document.createElement("label");
  field.className = "rookieui-shell__field";
  if (extraClass) {
    String(extraClass)
      .split(/\s+/)
      .map((value) => value.trim())
      .filter(Boolean)
      .forEach((className) => field.classList.add(className));
  }
  const label = document.createElement("span");
  label.className = "rookieui-shell__field-label";
  label.textContent = labelText;
  field.appendChild(label);
  field.appendChild(control);
  parent.appendChild(field);
  return field;
}

function createCompactCheckboxField(parent, labelText, input, fieldId = "") {
  const field = document.createElement("label");
  field.className = "rookieui-shell__inline-checkbox-field rookieui-shell__controlnet-toggle-field";
  if (fieldId) {
    field.id = fieldId;
  }

  const toggle = document.createElement("span");
  toggle.className = "rookieui-shell__checkbox-toggle";
  toggle.appendChild(input);

  const label = document.createElement("span");
  label.className = "rookieui-shell__field-label";
  label.textContent = labelText;

  field.appendChild(toggle);
  field.appendChild(label);
  parent.appendChild(field);
  return field;
}

function createSegmentedSelectBridge({ idPrefix, index, name, select, options }) {
  const group = document.createElement("div");
  group.className = "rookieui-shell__controlnet-segmented";
  group.id = `${idPrefix}-${name}-segmented-${index}`;
  const buttons = [];

  const updateActiveStyles = () => {
    buttons.forEach((button) => {
      const isActive = button.dataset.value === select.value;
      button.dataset.active = isActive ? "true" : "false";
      button.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
  };

  options.forEach((entry) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "rookieui-shell__controlnet-segmented-option";
    button.id = `${idPrefix}-${name}-option-${entry.value}-${index}`;
    button.dataset.value = String(entry.value ?? "");
    button.textContent = String(entry.label ?? entry.value ?? "");
    button.addEventListener("click", () => {
      const nextValue = String(entry.value ?? "");
      if (select.value === nextValue) {
        return;
      }
      select.value = nextValue;
      updateActiveStyles();
      select.dispatchEvent(new Event("input", { bubbles: true }));
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });
    group.appendChild(button);
    buttons.push(button);
  });

  select.addEventListener("change", updateActiveStyles);
  updateActiveStyles();

  return {
    group,
    setValue(nextValue) {
      const normalized = String(nextValue ?? "");
      if (options.some((entry) => String(entry.value ?? "") === normalized)) {
        select.value = normalized;
      } else if (options.length > 0) {
        select.value = String(options[0].value ?? "");
      }
      updateActiveStyles();
    },
  };
}

function bindSliderNumberPair(numberInput, sliderInput) {
  const syncFromNumber = () => {
    if (numberInput.value !== "") {
      sliderInput.value = numberInput.value;
    }
    sliderInput.disabled = numberInput.disabled;
    sliderInput.__syncSliderVisual?.();
  };
  const syncFromSlider = () => {
    numberInput.value = sliderInput.value;
    sliderInput.__syncSliderVisual?.();
  };

  numberInput.addEventListener("input", syncFromNumber);
  numberInput.addEventListener("change", syncFromNumber);
  sliderInput.addEventListener("input", () => {
    syncFromSlider();
    syncFromNumber();
  });
  sliderInput.addEventListener("change", () => {
    syncFromSlider();
    syncFromNumber();
  });
  syncFromNumber();
}

function createControlNetPreviewActionButton({ toolbar, idPrefix, index, action, icon, label }) {
  const button = document.createElement("button");
  button.type = "button";
  button.id = `${idPrefix}-preview-${action}-action-${index}`;
  button.className = "rookieui-shell__mini-action rookieui-shell__mini-action--icon rookieui-shell__mini-action--tone-neutral";
  button.dataset.canvasAction = action;
  button.title = label;
  button.setAttribute("aria-label", label);
  const iconNode = document.createElement("span");
  iconNode.className = "rookieui-shell__mini-action-icon";
  iconNode.textContent = icon;
  button.appendChild(iconNode);
  toolbar.appendChild(button);
  return button;
}

function createControlNetPreviewStage({ idPrefix, index, appendTextElement, createInput }) {
  const stage = document.createElement("div");
  stage.className = "rookieui-shell__controlnet-preview-stage";
  stage.id = `${idPrefix}-preview-stage-${index}`;

  const toolbar = document.createElement("div");
  toolbar.className = "rookieui-shell__controlnet-preview-toolbar";
  stage.appendChild(toolbar);

  const fullscreenButton = createControlNetPreviewActionButton({
    toolbar,
    idPrefix,
    index,
    action: CANVAS_ACTIONS.fullscreen,
    icon: FULLSCREEN_ENTER_ICON,
    label: "Fullscreen preview",
  });
  const uploadButton = createControlNetPreviewActionButton({
    toolbar,
    idPrefix,
    index,
    action: CANVAS_ACTIONS.upload,
    icon: "📁",
    label: "Upload control image",
  });
  const removeButton = createControlNetPreviewActionButton({
    toolbar,
    idPrefix,
    index,
    action: CANVAS_ACTIONS.remove,
    icon: "🗑",
    label: "Remove control image",
  });
  const resetButton = createControlNetPreviewActionButton({
    toolbar,
    idPrefix,
    index,
    action: CANVAS_ACTIONS.reset,
    icon: "↺",
    label: "Reset control image view",
  });
  const undoButton = createControlNetPreviewActionButton({
    toolbar,
    idPrefix,
    index,
    action: CANVAS_ACTIONS.undo,
    icon: "↶",
    label: "Undo control image change",
  });
  const redoButton = createControlNetPreviewActionButton({
    toolbar,
    idPrefix,
    index,
    action: CANVAS_ACTIONS.redo,
    icon: "↷",
    label: "Redo control image change",
  });

  const previewImage = document.createElement("img");
  previewImage.className = "rookieui-shell__controlnet-preview-image";
  previewImage.id = `${idPrefix}-preview-image-${index}`;
  previewImage.alt = `ControlNet source preview ${index + 1}`;
  previewImage.hidden = true;
  stage.appendChild(previewImage);

  const placeholder = document.createElement("div");
  placeholder.className = "rookieui-shell__controlnet-preview-placeholder";
  const icon = document.createElement("span");
  icon.className = "rookieui-shell__controlnet-preview-placeholder-icon";
  icon.textContent = PREVIEW_UPLOAD_ICON;
  placeholder.appendChild(icon);
  const text = appendTextElement(
    placeholder,
    "span",
    "rookieui-shell__controlnet-preview-placeholder-text",
    "Upload control image",
  );
  stage.appendChild(placeholder);

  const sourceUploadInput = createInput("file", `${idPrefix}-preview-image-upload-${index}`, "", {
    className: "rookieui-shell__input",
  });
  sourceUploadInput.accept = "image/png,image/webp,image/jpeg";
  sourceUploadInput.hidden = true;
  sourceUploadInput.setAttribute("tabindex", "-1");
  sourceUploadInput.setAttribute("aria-hidden", "true");
  stage.appendChild(sourceUploadInput);

  const generatedLane = document.createElement("div");
  generatedLane.className = "rookieui-shell__controlnet-generated-preview";
  generatedLane.id = `${idPrefix}-preview-generated-lane-${index}`;
  generatedLane.hidden = true;

  const generatedImage = document.createElement("img");
  generatedImage.className = "rookieui-shell__controlnet-generated-preview-image";
  generatedImage.id = `${idPrefix}-preview-generated-image-${index}`;
  generatedImage.alt = `ControlNet generated preview ${index + 1}`;
  generatedImage.hidden = true;
  generatedLane.appendChild(generatedImage);

  const generatedPlaceholder = document.createElement("div");
  generatedPlaceholder.className = "rookieui-shell__controlnet-generated-preview-placeholder";
  appendTextElement(
    generatedPlaceholder,
    "span",
    "rookieui-shell__controlnet-generated-preview-placeholder-text",
    "Run Preprocessor output preview",
  );
  generatedLane.appendChild(generatedPlaceholder);

  const dualPane = document.createElement("div");
  dualPane.className = "rookieui-shell__controlnet-preview-dual-pane";
  dualPane.id = `${idPrefix}-preview-dual-pane-${index}`;
  dualPane.dataset.generatedVisible = "false";
  dualPane.appendChild(stage);
  dualPane.appendChild(generatedLane);

  return {
    unitIndex: index,
    dualPane,
    stage,
    generatedLane,
    generatedImage,
    generatedPlaceholder,
    toolbar,
    previewImage,
    placeholder,
    placeholderText: text,
    sourceUploadInput,
    fullscreenButton,
    uploadButton,
    removeButton,
    resetButton,
    undoButton,
    redoButton,
    history: {
      undo: [],
      redo: [],
      limit: 24,
    },
  };
}

function setControlNetPreview(previewState, { imageData = "", imageAsset = "", fallbackText = "Upload control image" } = {}) {
  const normalizedImage = String(imageData ?? "").trim();
  const normalizedAsset = String(imageAsset ?? "").trim();
  const hasSource = hasCanvasSourceImage(normalizedImage, normalizedAsset);
  const interactionMode = resolveCanvasInteractionMode(normalizedImage, normalizedAsset);
  const unitLabel = `ControlNet Unit ${(previewState.unitIndex ?? 0) + 1}`;
  previewState.stage.dataset.hasSource = hasSource ? "true" : "false";
  previewState.stage.dataset.interactionMode = interactionMode;
  previewState.stage.setAttribute(
    "aria-label",
    interactionMode === "upload" ? `${unitLabel} upload source image` : `${unitLabel} source image editing surface`,
  );
  if (normalizedImage.startsWith("data:image/")) {
    previewState.previewImage.src = normalizedImage;
    previewState.previewImage.hidden = false;
    previewState.placeholder.hidden = true;
  } else {
    previewState.previewImage.hidden = true;
    previewState.previewImage.removeAttribute("src");
    previewState.placeholder.hidden = false;
    if (normalizedAsset) {
      // IMPORTANT: asset handles are server-side identifiers; keep text fallback instead of forcing /view fetches that may fail on non-image handles.
      previewState.placeholderText.textContent = `Asset: ${normalizedAsset}`;
    } else {
      previewState.placeholderText.textContent = fallbackText;
    }
  }

  previewState.removeButton.disabled = !hasSource;
  previewState.resetButton.disabled = !hasSource;
  previewState.undoButton.disabled = previewState.history.undo.length === 0;
  previewState.redoButton.disabled = previewState.history.redo.length === 0;
}

function setControlNetGeneratedPreview(previewState, { imageData = "", visible = false } = {}) {
  const normalizedImage = String(imageData ?? "").trim();
  const hasGeneratedImage = normalizedImage.startsWith("data:image/");
  const shouldShow = Boolean(visible) && hasGeneratedImage;
  if (previewState.dualPane) {
    previewState.dualPane.dataset.generatedVisible = shouldShow ? "true" : "false";
  }
  previewState.generatedLane.hidden = !shouldShow;
  if (shouldShow) {
    previewState.generatedImage.src = normalizedImage;
    previewState.generatedImage.hidden = false;
    previewState.generatedPlaceholder.hidden = true;
    return;
  }
  previewState.generatedImage.hidden = true;
  previewState.generatedImage.removeAttribute("src");
  previewState.generatedPlaceholder.hidden = false;
}

function hasIndependentControlImageData(row) {
  return hasCanvasSourceImage(row?.imageData?.value ?? "", "");
}

function syncRunPreprocessorVisibility(row, isImg2ImgEditor) {
  if (!row?.runPreprocessorButton) {
    return;
  }
  const shouldShow = !isImg2ImgEditor || hasIndependentControlImageData(row);
  const isBusy = Boolean(row.preprocessorBusy);
  row.runPreprocessorButton.hidden = !shouldShow;
  row.runPreprocessorButton.style.display = shouldShow ? "" : "none";
  row.runPreprocessorButton.dataset.running = isBusy ? "true" : "false";
  row.runPreprocessorButton.setAttribute("aria-busy", isBusy ? "true" : "false");
  row.runPreprocessorButton.title = isBusy ? "Running Preprocessor..." : "Run Preprocessor";
  row.runPreprocessorButton.setAttribute("aria-label", row.runPreprocessorButton.title);
  const runIcon = row.runPreprocessorButton.querySelector(".rookieui-shell__mini-action-icon");
  if (runIcon) {
    runIcon.textContent = isBusy ? RUN_PREPROCESSOR_BUSY_ICON : RUN_PREPROCESSOR_ICON;
  }
  // CRITICAL: img2img must hide Run Preprocessor until an independent control image is present.
  row.runPreprocessorButton.disabled = !shouldShow || isBusy;
}

function buildFallbackControlTypeCatalog(controlTypeOptions) {
  const allModules = MODULE_OPTIONS.map((entry) => entry.value);
  const map = {
    All: {
      module_list: allModules,
      model_list: [],
      default_option: "none",
    },
    Blur: {
      module_list: ["none", "blur"],
      model_list: [],
      default_option: "blur",
    },
    Canny: {
      module_list: ["none", "canny"],
      model_list: [],
      default_option: "canny",
    },
    Depth: {
      module_list: ["none", ...DEPTH_PREPROCESSOR_OPTIONS],
      model_list: [],
      default_option: "depth",
    },
    NormalMap: {
      module_list: ["none", "normalmap", "normal_midas", "normal_bae", "normal_dsine"],
      model_list: [],
      default_option: "normalmap",
    },
    MLSD: {
      module_list: ["none", "mlsd"],
      model_list: [],
      default_option: "mlsd",
    },
    Inpaint: {
      module_list: ["none", "inpaint"],
      model_list: [],
      default_option: "inpaint",
    },
    OpenPose: {
      module_list: ["none", ...OPENPOSE_PREPROCESSOR_OPTIONS],
      model_list: [],
      default_option: "openpose",
    },
    Lineart: {
      module_list: ["none", ...LINEART_PREPROCESSOR_OPTIONS],
      model_list: [],
      default_option: "lineart",
    },
    Scribble: {
      module_list: ["none", ...SCRIBBLE_PREPROCESSOR_OPTIONS],
      model_list: [],
      default_option: "scribble",
    },
    Segmentation: {
      module_list: [
        "none",
        "segmentation",
        "segmentation_oneformer_coco",
        "segmentation_oneformer_ade20k",
        "segmentation_uniformer",
        "segmentation_anime_face",
      ],
      model_list: [],
      default_option: "segmentation",
    },
    Shuffle: {
      module_list: ["none", "shuffle"],
      model_list: [],
      default_option: "shuffle",
    },
    Sketch: {
      module_list: ["none", "sketch", "sketch_scribble", "sketch_lineart", "sketch_hed"],
      model_list: [],
      default_option: "sketch",
    },
    SoftEdge: {
      module_list: ["none", ...SOFTEDGE_PREPROCESSOR_OPTIONS],
      model_list: [],
      default_option: "softedge",
    },
    Reference: {
      module_list: ["none", "reference"],
      model_list: [],
      default_option: "reference",
    },
    "IP-Adapter": {
      module_list: ["none", "ipadapter"],
      model_list: [],
      default_option: "ipadapter",
    },
    "Instant-ID": {
      module_list: ["none", "instantid"],
      model_list: [],
      default_option: "instantid",
    },
    "T2I-Adapter": {
      module_list: ["none", "t2iadapter"],
      model_list: [],
      default_option: "t2iadapter",
    },
    Tile: {
      module_list: ["none", "tile", "tile_simple", "tile_gf"],
      model_list: [],
      default_option: "tile",
    },
  };

  controlTypeOptions.forEach((label) => {
    if (!map[label]) {
      map[label] = {
        module_list: allModules,
        model_list: [],
        default_option: "none",
      };
    }
  });
  return map;
}

function normalizeControlTypeCatalog(rawCatalog, allModelValues, controlTypeOptions) {
  const fallbackCatalog = buildFallbackControlTypeCatalog(controlTypeOptions);
  if (!rawCatalog || typeof rawCatalog !== "object") {
    return fallbackCatalog;
  }

  const normalizedCatalog = { ...fallbackCatalog };
  Object.entries(rawCatalog).forEach(([typeLabel, rawTypeValue]) => {
    if (!rawTypeValue || typeof rawTypeValue !== "object") {
      return;
    }
    const typeKey = String(typeLabel ?? "").trim();
    if (!typeKey) {
      return;
    }

    const fallbackEntry = fallbackCatalog[typeKey] ?? fallbackCatalog.All;
    const moduleList = Array.isArray(rawTypeValue.module_list)
      ? rawTypeValue.module_list.map((value) => String(value ?? "").trim()).filter(Boolean)
      : fallbackEntry.module_list;
    const modelList = Array.isArray(rawTypeValue.model_list)
      ? rawTypeValue.model_list.map((value) => String(value ?? "").trim()).filter(Boolean)
      : [];

    normalizedCatalog[typeKey] = {
      module_list: moduleList.length > 0 ? moduleList : fallbackEntry.module_list,
      model_list: modelList.length > 0 ? modelList : allModelValues,
      default_option: String(rawTypeValue.default_option ?? fallbackEntry.default_option ?? "none") || "none",
    };
  });

  controlTypeOptions.forEach((typeLabel) => {
    if (!normalizedCatalog[typeLabel]) {
      normalizedCatalog[typeLabel] = {
        ...fallbackCatalog[typeLabel],
      };
    }
  });
  return normalizedCatalog;
}

function normalizeUnitPayload(rawUnit = {}) {
  const normalizedType = String(rawUnit.control_type ?? rawUnit.type ?? DEFAULT_CONTROL_TYPE).trim();
  return {
    enabled: Boolean(rawUnit.enabled),
    allow_preview: Boolean(rawUnit.allow_preview),
    use_mask: Boolean(rawUnit.use_mask),
    control_type: normalizedType || DEFAULT_CONTROL_TYPE,
    module: String(rawUnit.module ?? "none") || "none",
    model: String(rawUnit.model ?? "").trim(),
    weight: normalizeNumber(rawUnit.weight, 1),
    guidance_start: normalizeNumber(rawUnit.guidance_start, 0),
    guidance_end: normalizeNumber(rawUnit.guidance_end, 1),
    resize_mode: String(rawUnit.resize_mode ?? "crop_and_resize") || "crop_and_resize",
    control_mode: String(rawUnit.control_mode ?? "balanced") || "balanced",
    processor_res: Math.max(64, Math.min(2048, Math.round(normalizeNumber(rawUnit.processor_res, 512)))),
    threshold_a: normalizeNumber(rawUnit.threshold_a, 64),
    threshold_b: normalizeNumber(rawUnit.threshold_b, 64),
    pixel_perfect: Boolean(rawUnit.pixel_perfect),
    hr_option: String(rawUnit.hr_option ?? "both") || "both",
    image_asset: String(rawUnit.image_asset ?? "").trim(),
    image_data: String(rawUnit.image_data ?? "").trim(),
    mask_asset: String(rawUnit.mask_asset ?? "").trim(),
    mask_data: String(rawUnit.mask_data ?? "").trim(),
  };
}

function shouldEmitUnit(unit) {
  return (
    unit.enabled ||
    unit.allow_preview ||
    unit.use_mask ||
    unit.control_type !== DEFAULT_CONTROL_TYPE ||
    unit.module !== "none" ||
    Boolean(unit.model) ||
    Boolean(unit.image_asset) ||
    Boolean(unit.image_data) ||
    Boolean(unit.mask_asset) ||
    Boolean(unit.mask_data)
  );
}

function createEnglishUploadControl({
  uploadRow,
  createInput,
  idPrefix,
  index,
  target,
  buttonLabel,
  buttonAriaLabel,
}) {
  const controlRow = document.createElement("div");
  controlRow.className = "rookieui-shell__action-target-row";
  uploadRow.appendChild(controlRow);

  const fileNameInput = createInput("text", `${idPrefix}-${target}-upload-name-${index}`, FILE_SELECTION_PLACEHOLDER, {
    className: "rookieui-shell__action-target",
  });
  fileNameInput.readOnly = true;
  fileNameInput.setAttribute("aria-live", "polite");
  controlRow.appendChild(fileNameInput);

  const chooseButton = document.createElement("button");
  chooseButton.id = `${idPrefix}-${target}-upload-button-${index}`;
  chooseButton.type = "button";
  chooseButton.className = "rookieui-shell__mini-action rookieui-shell__mini-action--tone-neutral";
  chooseButton.textContent = buttonLabel;
  chooseButton.setAttribute("aria-label", buttonAriaLabel);
  controlRow.appendChild(chooseButton);

  const fileInput = createInput("file", `${idPrefix}-${target}-upload-${index}`, "", {
    className: "rookieui-shell__input",
  });
  fileInput.accept = "image/png,image/webp,image/jpeg";
  fileInput.hidden = true;
  fileInput.setAttribute("tabindex", "-1");
  fileInput.setAttribute("aria-hidden", "true");
  controlRow.appendChild(fileInput);

  // IMPORTANT: keep file chooser chrome custom/English-only; browser-native file inputs localize by OS language.
  chooseButton.addEventListener("click", () => {
    fileInput.click();
  });

  return {
    controlRow,
    fileInput,
    fileNameInput,
    chooseButton,
  };
}

function setSelectOptions(select, options, preferredValue = "") {
  const preferred = String(preferredValue ?? "");
  const fragment = document.createDocumentFragment();
  options.forEach((entry) => {
    const option = document.createElement("option");
    option.value = String(entry.value ?? "");
    option.textContent = String(entry.label ?? entry.value ?? "");
    fragment.appendChild(option);
  });
  select.replaceChildren(fragment);
  const hasPreferred = options.some((entry) => String(entry.value ?? "") === preferred);
  if (hasPreferred) {
    select.value = preferred;
  } else if (options.length > 0) {
    select.value = String(options[0].value ?? "");
  } else {
    select.value = "";
  }
}

function createControlTypeSelector({ idPrefix, index, controlTypeOptions, onChange }) {
  const group = document.createElement("div");
  group.className = "rookieui-shell__controlnet-radio-grid";
  const groupName = `${idPrefix}-control-type-${index}`;
  const radios = [];

  controlTypeOptions.forEach((labelText) => {
    const optionLabel = document.createElement("label");
    optionLabel.className = "rookieui-shell__controlnet-radio-option";

    const radio = document.createElement("input");
    radio.className = "rookieui-shell__checkbox";
    radio.type = "radio";
    radio.name = groupName;
    radio.value = labelText;
    radio.id = `${groupName}-${slugifyLabel(labelText)}`;

    const text = document.createElement("span");
    text.className = "rookieui-shell__field-label";
    text.textContent = labelText;

    optionLabel.appendChild(radio);
    optionLabel.appendChild(text);
    group.appendChild(optionLabel);
    radios.push(radio);

    radio.addEventListener("change", () => {
      // DEBUG HOTSPOT: radio-group highlight sync seam. Always refresh the full group state here;
      // updating only the clicked label leaves stale `data-active=true` chips after rapid control-type switching.
      updateActiveStyles();
      if (onChange) {
        onChange();
      }
    });
  });

  const updateActiveStyles = () => {
    radios.forEach((radio) => {
      const hostLabel = radio.parentElement;
      if (hostLabel) {
        hostLabel.dataset.active = radio.checked ? "true" : "false";
      }
    });
  };

  const getValue = () => {
    const selected = radios.find((radio) => radio.checked);
    return selected ? selected.value : DEFAULT_CONTROL_TYPE;
  };

  const setValue = (nextValue) => {
    const normalized = String(nextValue ?? "").trim() || DEFAULT_CONTROL_TYPE;
    const target = radios.find((radio) => radio.value === normalized) ?? radios[0];
    if (target) {
      target.checked = true;
    }
    updateActiveStyles();
  };

  setValue(DEFAULT_CONTROL_TYPE);
  return {
    group,
    radios,
    getValue,
    setValue,
  };
}

export function createControlNetUnitEditor({
  idPrefix,
  parent,
  hiddenInput,
  modelOptions = [],
  createInput,
  createRangeInput,
  createSelect,
  createCheckbox,
  createField,
  createSliderField,
  appendTextElement,
  readFileAsDataUrl,
  syncBoundControls,
  onStatusMessage = null,
  unitCount = DEFAULT_UNIT_COUNT,
  controlTypeOrder = DEFAULT_CONTROL_TYPE_OPTIONS,
}) {
  const isImg2ImgEditor = String(idPrefix ?? "").startsWith("rookieui-img2img-controlnet");
  const integratedDetails = document.createElement("details");
  integratedDetails.className =
    "rookieui-shell__section rookieui-shell__section--soft rookieui-shell__hires rookieui-shell__controlnet-integrated";
  integratedDetails.id = `${idPrefix}-section`;
  integratedDetails.open = true;
  parent.appendChild(integratedDetails);

  const summary = document.createElement("summary");
  summary.className = "rookieui-shell__hires-summary rookieui-shell__controlnet-summary";
  integratedDetails.appendChild(summary);

  const header = document.createElement("div");
  header.className = "rookieui-shell__hires-header";
  summary.appendChild(header);

  const title = document.createElement("span");
  title.className = "rookieui-shell__hires-title";
  title.textContent = "Controlnet";
  header.appendChild(title);

  const caret = document.createElement("span");
  caret.className = "rookieui-shell__hires-caret";
  caret.textContent = "▸";
  header.appendChild(caret);

  const body = document.createElement("div");
  body.className = "rookieui-shell__controlnet-body";
  integratedDetails.appendChild(body);

  const tabs = document.createElement("div");
  tabs.className = "rookieui-shell__subtabs rookieui-shell__controlnet-tabs";
  body.appendChild(tabs);

  const panelHost = document.createElement("div");
  panelHost.className = "rookieui-shell__controlnet-panel-host";
  body.appendChild(panelHost);

  const moduleLabelMap = MODULE_OPTIONS.reduce((acc, entry) => {
    acc[entry.value] = entry.label;
    return acc;
  }, {});

  let currentModelOptions = [{ value: "", label: "(Select ControlNet Model)" }, ...modelOptions];
  let currentModelValues = modelOptions.map((entry) => String(entry.value ?? "")).filter(Boolean);
  const controlTypeOptions = normalizeControlTypeOrder(controlTypeOrder);
  let controlTypeCatalog = normalizeControlTypeCatalog({}, currentModelValues, controlTypeOptions);

  const unitRows = [];
  const tabButtons = [];
  const unitPanels = [];

  const syncHiddenField = () => {
    const units = unitRows
      .map((row) => ({
        enabled: row.enabled.checked,
        allow_preview: row.allowPreview.checked,
        use_mask: row.useMask.checked,
        control_type: row.controlType.getValue(),
        module: row.module.value,
        model: row.model.value,
        weight: normalizeNumber(row.weight.value, 1),
        guidance_start: normalizeNumber(row.guidanceStart.value, 0),
        guidance_end: normalizeNumber(row.guidanceEnd.value, 1),
        resize_mode: row.resizeMode.value,
        control_mode: row.controlMode.value,
        processor_res: Math.round(normalizeNumber(row.processorRes.value, 512)),
        threshold_a: normalizeNumber(row.thresholdA.value, 64),
        threshold_b: normalizeNumber(row.thresholdB.value, 64),
        pixel_perfect: row.pixelPerfect.checked,
        hr_option: row.hrOption.value,
        image_asset: row.imageAsset.value.trim(),
        image_data: row.imageData.value.trim(),
        mask_asset: row.maskAsset.value.trim(),
        mask_data: row.maskData.value.trim(),
      }))
      .filter(shouldEmitUnit);

    hiddenInput.value = JSON.stringify(units);
    if (syncBoundControls) {
      syncBoundControls([hiddenInput]);
    }
  };

  const activateTab = (index) => {
    tabButtons.forEach((button, buttonIndex) => {
      const isActive = buttonIndex === index;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-selected", isActive ? "true" : "false");
      button.tabIndex = isActive ? 0 : -1;
      button.dataset.active = isActive ? "true" : "false";
    });

    unitPanels.forEach((panel, panelIndex) => {
      const isActive = panelIndex === index;
      panel.hidden = !isActive;
      panel.classList.toggle("is-active", isActive);
    });
  };

  const applyCatalogToRow = (row, preserveSelection = true) => {
    const controlType = row.controlType.getValue();
    const typeConfig = controlTypeCatalog[controlType] ?? controlTypeCatalog.All;

    const rawModules = Array.isArray(typeConfig?.module_list) ? typeConfig.module_list : [];
    const moduleEntries = toOptionEntries(rawModules, moduleLabelMap);
    const normalizedModuleEntries = moduleEntries.length > 0 ? moduleEntries : MODULE_OPTIONS;

    const preferredModule = preserveSelection ? row.module.value : typeConfig?.default_option ?? "none";
    setSelectOptions(row.module, normalizedModuleEntries, preferredModule);

    const modelValues = Array.isArray(typeConfig?.model_list) && typeConfig.model_list.length > 0
      ? typeConfig.model_list.map((value) => String(value ?? "").trim()).filter(Boolean)
      : currentModelValues;

    const modelEntries = [{ value: "", label: "(Select ControlNet Model)" }, ...toOptionEntries(modelValues)];
    setSelectOptions(row.model, modelEntries, preserveSelection ? row.model.value : "");
  };

  const bindSyncHandlers = (row) => {
    Object.values(row).forEach((element) => {
      if (!element) {
        return;
      }
      if (Array.isArray(element)) {
        element.forEach((entry) => {
          if (entry?.type === "file") {
            return;
          }
          entry?.addEventListener("change", syncHiddenField);
          if (entry?.tagName === "INPUT" || entry?.tagName === "SELECT" || entry?.tagName === "TEXTAREA") {
            entry.addEventListener("input", syncHiddenField);
          }
        });
        return;
      }
      if (
        typeof element !== "object" ||
        element.type === "file" ||
        typeof element.addEventListener !== "function"
      ) {
        // CRITICAL: keep this guard. Test harness/stub rows can contain non-DOM objects, and direct binding crashes on addEventListener.
        return;
      }
      element.addEventListener("change", syncHiddenField);
      if (element.tagName === "INPUT" || element.tagName === "SELECT" || element.tagName === "TEXTAREA") {
        element.addEventListener("input", syncHiddenField);
      }
    });
  };

  const attachUploadHandler = (
    fileInput,
    {
      dataField,
      assetField,
      label,
      fileNameField,
      onFileLoaded = null,
    },
  ) => {
    fileInput.addEventListener("change", async () => {
      const [file] = Array.from(fileInput.files ?? []);
      if (!file) {
        if (fileNameField) {
          fileNameField.value = FILE_SELECTION_PLACEHOLDER;
        }
        return;
      }

      if (fileNameField) {
        fileNameField.value = file.name;
      }

      try {
        dataField.value = await readFileAsDataUrl(file);
        assetField.value = "";
        if (typeof onFileLoaded === "function") {
          onFileLoaded(dataField.value, file.name);
        }
        syncHiddenField();
        if (onStatusMessage) {
          onStatusMessage(`Loaded ControlNet ${label}: ${file.name}`);
        }
      } catch (_error) {
        if (fileNameField) {
          fileNameField.value = FILE_SELECTION_PLACEHOLDER;
        }
        if (onStatusMessage) {
          onStatusMessage(`Failed to load ControlNet ${label}.`);
        }
      }
    });
  };

  const runPreprocessorForRow = async (row, unitIndex) => {
    if (row.preprocessorBusy) {
      return;
    }
    const sourceImage = row.imageData.value.trim();
    if (!sourceImage) {
      if (onStatusMessage) {
        onStatusMessage(`ControlNet Unit ${unitIndex + 1}: upload a source image before running preprocessor.`);
      }
      return;
    }

    const moduleName = String(row.module.value ?? "none").trim() || "none";
    if (moduleName === "none") {
      if (onStatusMessage) {
        onStatusMessage(`ControlNet Unit ${unitIndex + 1}: preprocessor module is set to None.`);
      }
      return;
    }

    if (typeof globalThis.fetch !== "function") {
      if (onStatusMessage) {
        onStatusMessage("ControlNet preprocessor is unavailable because fetch() is not available.");
      }
      return;
    }

    row.preprocessorBusy = true;
    syncRunPreprocessorVisibility(row, isImg2ImgEditor);
    if (onStatusMessage) {
      onStatusMessage(`ControlNet Unit ${unitIndex + 1}: running preprocessor...`);
    }
    const maskImage = row.useMask.checked ? String(row.maskData.value ?? "").trim() : "";
    const selectedControlModel = String(row.model?.value ?? "").trim();

    const abortController = typeof globalThis.AbortController === "function" ? new globalThis.AbortController() : null;
    let timeoutHandle = null;
    if (abortController && typeof globalThis.setTimeout === "function") {
      timeoutHandle = globalThis.setTimeout(() => {
        abortController.abort();
      }, RUN_PREPROCESSOR_TIMEOUT_MS);
    }
    try {
      const response = await globalThis.fetch("/rookieui/controlnet/detect", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          controlnet_module: moduleName,
          controlnet_model: selectedControlModel,
          controlnet_input_images: [sourceImage],
          controlnet_processor_res: Math.round(normalizeNumber(row.processorRes.value, 512)),
          controlnet_threshold_a: normalizeNumber(row.thresholdA.value, 64),
          controlnet_threshold_b: normalizeNumber(row.thresholdB.value, 64),
          controlnet_masks: maskImage ? [maskImage] : [],
          low_vram: false,
        }),
        signal: abortController?.signal,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = String(data?.detail ?? "").trim();
        const statusDetail = Number.isFinite(Number(response.status)) ? ` (HTTP ${response.status})` : "";
        if (onStatusMessage) {
          onStatusMessage(detail || `ControlNet Unit ${unitIndex + 1}: run preprocessor failed${statusDetail}.`);
        }
        return;
      }

      const outputImage = Array.isArray(data?.images) ? String(data.images[0] ?? "").trim() : "";
      if (!outputImage) {
        if (onStatusMessage) {
          onStatusMessage(`ControlNet Unit ${unitIndex + 1}: no preprocessor output image was returned.`);
        }
        return;
      }
      // CRITICAL: run-preprocessor output is generated preview state only; source image fields must remain immutable to preserve user-selected source/rollback semantics.
      row.generatedPreviewData = outputImage;
      setControlNetGeneratedPreview(row.preview, {
        imageData: row.generatedPreviewData,
        visible: row.allowPreview.checked,
      });

      const warningMessages = Array.isArray(data?.warnings) ? data.warnings : [];
      const warningCodes = Array.isArray(data?.warning_codes) ? data.warning_codes.map((entry) => String(entry)) : [];
      const warningText = warningMessages.length > 0 ? ` (${warningMessages[0]})` : "";
      const detectBackend = String(data?.detect_backend ?? "").trim().toLowerCase();
      const processorName = String(data?.processor ?? "").trim();
      const requestedModule = String(data?.module ?? moduleName).trim();
      const requestedControlModel = String(data?.requested_controlnet_model ?? selectedControlModel).trim();
      // DEBUG HOTSPOT: backend/processor/status-text stitching seam for run-preprocessor triage.
      // Keep this branch map aligned with backend warning diagnostics so UI messages explain fallback cause precisely.
      const hostFallback = warningCodes.includes("CONTROLNET_PREPROCESSOR_HOST_FALLBACK");
      let backendText = " via ComfyUI host preprocessor.";
      if (detectBackend === "comfy_host_preprocessor_aio") {
        backendText = " via ComfyUI host AIO preprocessor.";
      } else if (detectBackend === "passthrough_none" || detectBackend === "passthrough_module") {
        backendText = " (passthrough output).";
      } else if (hostFallback || detectBackend === "rookieui_internal_fallback") {
        backendText = " via RookieUI fallback preprocessor (approximate output).";
      } else if (detectBackend.startsWith("rookieui_internal")) {
        backendText = " via RookieUI internal preprocessor.";
      }
      const visibilityText = row.allowPreview.checked
        ? " Preview lane updated."
        : " Preview output is ready but hidden because Allow Preview is off.";
      const preprocessorText = requestedModule ? ` Preprocessor: ${requestedModule}.` : "";
      const processorText = processorName ? ` Processor: ${processorName}.` : "";
      const controlModelText = requestedControlModel
        ? ` Control model: ${requestedControlModel} (generation stage only; preprocessor preview is driven by selected preprocessor/annotator).`
        : "";
      if (onStatusMessage) {
        onStatusMessage(
          `ControlNet Unit ${unitIndex + 1}: preprocessor completed${warningText}${backendText}${preprocessorText}${processorText}${controlModelText}${visibilityText}`,
        );
      }
    } catch (error) {
      if (error?.name === "AbortError") {
        if (onStatusMessage) {
          onStatusMessage(
            `ControlNet Unit ${unitIndex + 1}: preprocessor request timed out after ${Math.round(RUN_PREPROCESSOR_TIMEOUT_MS / 1000)} seconds.`,
          );
        }
        return;
      }
      if (onStatusMessage) {
        onStatusMessage(`ControlNet Unit ${unitIndex + 1}: preprocessor request failed.`);
      }
    } finally {
      if (timeoutHandle !== null && typeof globalThis.clearTimeout === "function") {
        globalThis.clearTimeout(timeoutHandle);
      }
      row.preprocessorBusy = false;
      syncRunPreprocessorVisibility(row, isImg2ImgEditor);
    }
  };

  const buildRangeInput = (id, value, options) => {
    if (typeof createRangeInput === "function") {
      return createRangeInput(id, value, options);
    }
    return createInput("range", id, value, {
      className: "rookieui-shell__slider",
      min: options?.min,
      max: options?.max,
      step: options?.step,
    });
  };

  const appendSliderField = (parentNode, labelText, numberInput, sliderInput, fieldId) => {
    if (typeof createSliderField === "function") {
      const createdField = createSliderField(parentNode, labelText, numberInput, sliderInput, fieldId);
      return createdField ?? null;
    }
    const fallbackField = document.createElement("div");
    fallbackField.className = "rookieui-shell__slider-field";
    if (fieldId) {
      fallbackField.id = fieldId;
    }
    const headerNode = document.createElement("div");
    headerNode.className = "rookieui-shell__slider-field-header";
    const labelNode = document.createElement("span");
    labelNode.className = "rookieui-shell__field-label";
    labelNode.textContent = labelText;
    headerNode.appendChild(labelNode);
    headerNode.appendChild(numberInput);
    fallbackField.appendChild(headerNode);
    fallbackField.appendChild(sliderInput);
    parentNode.appendChild(fallbackField);
    return fallbackField;
  };

  for (let index = 0; index < unitCount; index += 1) {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = "rookieui-shell__subtab rookieui-shell__controlnet-tab";
    tab.id = `${idPrefix}-tab-${index}`;
    tab.setAttribute("role", "tab");
    tab.setAttribute("aria-controls", `${idPrefix}-panel-${index}`);
    tab.textContent = `ControlNet Unit ${index + 1}`;
    tabs.appendChild(tab);
    tabButtons.push(tab);

    const panel = document.createElement("section");
    panel.className = "rookieui-shell__controlnet-panel";
    panel.id = `${idPrefix}-panel-${index}`;
    panel.hidden = index !== 0;
    panelHost.appendChild(panel);
    unitPanels.push(panel);

    const preview = createControlNetPreviewStage({ idPrefix, index, appendTextElement, createInput });
    panel.appendChild(preview.dualPane);

    const primaryGrid = document.createElement("div");
    primaryGrid.className = "rookieui-shell__controlnet-toggle-grid";
    panel.appendChild(primaryGrid);

    const enabled = createCheckbox(`${idPrefix}-enabled-${index}`, false);
    createCompactCheckboxField(primaryGrid, "Enable", enabled, `${idPrefix}-enabled-field-${index}`);

    const pixelPerfect = createCheckbox(`${idPrefix}-pixel-perfect-${index}`, false);
    createCompactCheckboxField(primaryGrid, "Pixel Perfect", pixelPerfect, `${idPrefix}-pixel-perfect-field-${index}`);

    const allowPreview = createCheckbox(`${idPrefix}-allow-preview-${index}`, false);
    createCompactCheckboxField(primaryGrid, "Allow Preview", allowPreview, `${idPrefix}-allow-preview-field-${index}`);

    const useMask = createCheckbox(`${idPrefix}-use-mask-${index}`, false);
    createCompactCheckboxField(primaryGrid, "Use Mask", useMask, `${idPrefix}-use-mask-field-${index}`);

    let rowElements = null;
    const controlType = createControlTypeSelector({
      idPrefix,
      index,
      controlTypeOptions,
      onChange: () => {
        applyCatalogToRow(rowElements, false);
        syncHiddenField();
      },
    });
    createCustomField(panel, "Control Type", controlType.group, "rookieui-shell__field--full");

    const settingsGrid = document.createElement("div");
    settingsGrid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
    panel.appendChild(settingsGrid);

    const selectorRow = document.createElement("div");
    selectorRow.className = "rookieui-shell__field rookieui-shell__field--full rookieui-shell__controlnet-selector-row";
    selectorRow.id = `${idPrefix}-selector-row-${index}`;
    settingsGrid.appendChild(selectorRow);

    const moduleSelect = createSelect(`${idPrefix}-module-${index}`, MODULE_OPTIONS, "none");
    const preprocessorField = createField(selectorRow, "Preprocessor", moduleSelect);
    preprocessorField.classList.add("rookieui-shell__controlnet-selector-field");

    const runPreprocessorSlot = document.createElement("div");
    runPreprocessorSlot.className = "rookieui-shell__controlnet-run-preprocessor-slot";
    selectorRow.appendChild(runPreprocessorSlot);

    const runPreprocessorButton = document.createElement("button");
    runPreprocessorButton.id = `${idPrefix}-run-preprocessor-${index}`;
    runPreprocessorButton.type = "button";
    runPreprocessorButton.className =
      "rookieui-shell__mini-action rookieui-shell__mini-action--icon rookieui-shell__mini-action--tone-neutral rookieui-shell__controlnet-run-preprocessor";
    runPreprocessorButton.setAttribute("aria-label", "Run Preprocessor");
    runPreprocessorButton.title = "Run Preprocessor";
    const runIcon = document.createElement("span");
    runIcon.className = "rookieui-shell__mini-action-icon";
    runIcon.textContent = RUN_PREPROCESSOR_ICON;
    runPreprocessorButton.appendChild(runIcon);
    runPreprocessorSlot.appendChild(runPreprocessorButton);

    const modelSelect = createSelect(`${idPrefix}-model-${index}`, currentModelOptions, "");
    const modelField = createField(selectorRow, "Model", modelSelect);
    modelField.classList.add("rookieui-shell__controlnet-selector-field");

    const weightInput = createInput("number", `${idPrefix}-weight-${index}`, "1", {
      min: 0,
      max: 2,
      step: 0.01,
      inputMode: "decimal",
    });
    const weightSlider = buildRangeInput(`${idPrefix}-weight-slider-${index}`, "1", {
      min: 0,
      max: 2,
      step: 0.01,
    });
    const weightField = appendSliderField(
      settingsGrid,
      "Control Weight",
      weightInput,
      weightSlider,
      `${idPrefix}-weight-field-${index}`,
    );
    weightField?.classList.add("rookieui-shell__field--full", "rookieui-shell__controlnet-weight-field");
    bindSliderNumberPair(weightInput, weightSlider);

    const guidanceStartInput = createInput("number", `${idPrefix}-guidance-start-${index}`, "0", {
      min: 0,
      max: 1,
      step: 0.01,
      inputMode: "decimal",
    });
    const guidanceEndInput = createInput("number", `${idPrefix}-guidance-end-${index}`, "1", {
      min: 0,
      max: 1,
      step: 0.01,
      inputMode: "decimal",
    });
    const guidanceStartSlider = buildRangeInput(`${idPrefix}-guidance-start-slider-${index}`, "0", {
      min: 0,
      max: 1,
      step: 0.01,
    });
    const guidanceEndSlider = buildRangeInput(`${idPrefix}-guidance-end-slider-${index}`, "1", {
      min: 0,
      max: 1,
      step: 0.01,
    });
    bindSliderNumberPair(guidanceStartInput, guidanceStartSlider);
    bindSliderNumberPair(guidanceEndInput, guidanceEndSlider);

    const timestepField = document.createElement("div");
    timestepField.className = "rookieui-shell__field rookieui-shell__field--full rookieui-shell__controlnet-timestep-field";
    timestepField.id = `${idPrefix}-timestep-range-field-${index}`;
    const timestepLabel = document.createElement("span");
    timestepLabel.className = "rookieui-shell__field-label";
    timestepLabel.textContent = "Timestep Range";
    timestepField.appendChild(timestepLabel);
    const timestepValues = document.createElement("div");
    timestepValues.className = "rookieui-shell__controlnet-timestep-values";
    timestepValues.appendChild(guidanceStartInput);
    timestepValues.appendChild(guidanceEndInput);
    timestepField.appendChild(timestepValues);
    const timestepSliders = document.createElement("div");
    timestepSliders.className = "rookieui-shell__controlnet-timestep-sliders";
    timestepSliders.appendChild(guidanceStartSlider);
    timestepSliders.appendChild(guidanceEndSlider);
    timestepField.appendChild(timestepSliders);
    const timestepScale = document.createElement("div");
    timestepScale.className = "rookieui-shell__controlnet-slider-scale";
    appendTextElement(timestepScale, "span", "rookieui-shell__controlnet-slider-scale-label", "0");
    appendTextElement(timestepScale, "span", "rookieui-shell__controlnet-slider-scale-label", "1");
    timestepField.appendChild(timestepScale);
    settingsGrid.appendChild(timestepField);

    const ensureGuidanceBounds = (source) => {
      let start = normalizeNumber(guidanceStartInput.value, 0);
      let end = normalizeNumber(guidanceEndInput.value, 1);
      if (start > end) {
        // IMPORTANT: keep timestep bounds ordered; reversed ranges produce ambiguous backend semantics and user-visible mismatches.
        if (source === "start") {
          end = start;
        } else {
          start = end;
        }
      }
      guidanceStartInput.value = String(start);
      guidanceEndInput.value = String(end);
      guidanceStartSlider.value = String(start);
      guidanceEndSlider.value = String(end);
      guidanceStartSlider.__syncSliderVisual?.();
      guidanceEndSlider.__syncSliderVisual?.();
    };
    guidanceStartInput.addEventListener("input", () => ensureGuidanceBounds("start"));
    guidanceEndInput.addEventListener("input", () => ensureGuidanceBounds("end"));
    guidanceStartSlider.addEventListener("input", () => ensureGuidanceBounds("start"));
    guidanceEndSlider.addEventListener("input", () => ensureGuidanceBounds("end"));
    ensureGuidanceBounds("start");

    const processorResInput = createInput("number", `${idPrefix}-processor-res-${index}`, "512", {
      min: 64,
      max: 2048,
      step: 8,
      inputMode: "numeric",
    });
    createField(settingsGrid, "Processor Res", processorResInput);

    const thresholdAInput = createInput("number", `${idPrefix}-threshold-a-${index}`, "64", {
      min: 0,
      max: 255,
      step: 1,
      inputMode: "numeric",
    });
    createField(settingsGrid, "Threshold A", thresholdAInput);

    const thresholdBInput = createInput("number", `${idPrefix}-threshold-b-${index}`, "64", {
      min: 0,
      max: 255,
      step: 1,
      inputMode: "numeric",
    });
    createField(settingsGrid, "Threshold B", thresholdBInput);

    const controlModeInput = createSelect(`${idPrefix}-control-mode-${index}`, CONTROL_MODE_OPTIONS, "balanced");
    controlModeInput.hidden = true;
    controlModeInput.tabIndex = -1;
    controlModeInput.setAttribute("aria-hidden", "true");
    const controlModeBridge = createSegmentedSelectBridge({
      idPrefix,
      index,
      name: "control-mode",
      select: controlModeInput,
      options: CONTROL_MODE_OPTIONS,
    });
    const controlModeField = createCustomField(
      settingsGrid,
      "Control Mode",
      controlModeBridge.group,
      "rookieui-shell__field--full rookieui-shell__controlnet-segmented-field",
    );
    controlModeField.appendChild(controlModeInput);

    const resizeModeInput = createSelect(`${idPrefix}-resize-mode-${index}`, RESIZE_MODE_OPTIONS, "crop_and_resize");
    resizeModeInput.hidden = true;
    resizeModeInput.tabIndex = -1;
    resizeModeInput.setAttribute("aria-hidden", "true");
    const resizeModeBridge = createSegmentedSelectBridge({
      idPrefix,
      index,
      name: "resize-mode",
      select: resizeModeInput,
      options: RESIZE_MODE_OPTIONS,
    });
    const resizeModeField = createCustomField(
      settingsGrid,
      "Resize Mode",
      resizeModeBridge.group,
      "rookieui-shell__field--full rookieui-shell__controlnet-segmented-field",
    );
    resizeModeField.appendChild(resizeModeInput);

    const hrOption = createSelect(`${idPrefix}-hr-option-${index}`, HR_OPTION_OPTIONS, "both");
    createField(settingsGrid, "Hires Option", hrOption);

    const imageAsset = createInput("text", `${idPrefix}-image-asset-${index}`, "");
    imageAsset.placeholder = "Control image asset handle";
    createField(settingsGrid, "Image Asset", imageAsset);

    const maskAsset = createInput("text", `${idPrefix}-mask-asset-${index}`, "");
    maskAsset.placeholder = "Optional mask asset handle";
    createField(settingsGrid, "Mask Asset", maskAsset);

    const imageData = createInput("hidden", `${idPrefix}-image-data-${index}`, "");
    panel.appendChild(imageData);

    const maskData = createInput("hidden", `${idPrefix}-mask-data-${index}`, "");
    panel.appendChild(maskData);

    const uploadRow = document.createElement("div");
    uploadRow.className = "rookieui-shell__controlnet-upload-row";
    panel.appendChild(uploadRow);

    const imageUploadControl = createEnglishUploadControl({
      uploadRow,
      createInput,
      idPrefix,
      index,
      target: "image",
      buttonLabel: "Choose Image File",
      buttonAriaLabel: "Choose ControlNet image file",
    });

    const maskUploadControl = createEnglishUploadControl({
      uploadRow,
      createInput,
      idPrefix,
      index,
      target: "mask",
      buttonLabel: "Choose Mask File",
      buttonAriaLabel: "Choose ControlNet mask file",
    });

    rowElements = {
      enabled,
      pixelPerfect,
      allowPreview,
      useMask,
      preview,
      controlType,
      controlTypeRadios: controlType.radios,
      module: moduleSelect,
      model: modelSelect,
      weight: weightInput,
      weightSlider,
      guidanceStart: guidanceStartInput,
      guidanceStartSlider,
      guidanceEnd: guidanceEndInput,
      guidanceEndSlider,
      resizeMode: resizeModeInput,
      resizeModeBridge,
      controlMode: controlModeInput,
      controlModeBridge,
      processorRes: processorResInput,
      thresholdA: thresholdAInput,
      thresholdB: thresholdBInput,
      ensureGuidanceBounds,
      hrOption,
      imageAsset,
      imageData,
      maskAsset,
      maskData,
      imageUpload: imageUploadControl.fileInput,
      maskUpload: maskUploadControl.fileInput,
      imageUploadName: imageUploadControl.fileNameInput,
      maskUploadName: maskUploadControl.fileNameInput,
      runPreprocessorButton,
      sourceBrush: null,
      generatedPreviewData: "",
      preprocessorBusy: false,
    };

    imageUploadControl.controlRow.classList.add("rookieui-shell__controlnet-upload-row--legacy-source");
    imageUploadControl.controlRow.hidden = true;

    const readRowSourceSnapshot = () => ({
      imageData: String(rowElements.imageData.value ?? "").trim(),
      imageAsset: String(rowElements.imageAsset.value ?? "").trim(),
      fileName: String(rowElements.imageUploadName.value ?? FILE_SELECTION_PLACEHOLDER).trim() || FILE_SELECTION_PLACEHOLDER,
    });

    const areSourceSnapshotsEqual = (left, right) =>
      String(left?.imageData ?? "") === String(right?.imageData ?? "") &&
      String(left?.imageAsset ?? "") === String(right?.imageAsset ?? "");

    const syncPreviewHistoryButtons = () => {
      rowElements.preview.undoButton.disabled = rowElements.preview.history.undo.length === 0;
      rowElements.preview.redoButton.disabled = rowElements.preview.history.redo.length === 0;
    };

    const pushPreviewUndoSnapshot = () => {
      const snapshot = readRowSourceSnapshot();
      const previous = rowElements.preview.history.undo[rowElements.preview.history.undo.length - 1];
      if (areSourceSnapshotsEqual(snapshot, previous)) {
        return;
      }
      rowElements.preview.history.undo.push(snapshot);
      if (rowElements.preview.history.undo.length > rowElements.preview.history.limit) {
        rowElements.preview.history.undo.shift();
      }
    };

    const applyRowSourceSnapshot = (snapshot, options = {}) => {
      const normalizedSnapshot = {
        imageData: String(snapshot?.imageData ?? "").trim(),
        imageAsset: String(snapshot?.imageAsset ?? "").trim(),
        fileName: String(snapshot?.fileName ?? "").trim(),
      };
      if (options.recordHistory) {
        pushPreviewUndoSnapshot();
        rowElements.preview.history.redo = [];
      }
      rowElements.imageData.value = normalizedSnapshot.imageData;
      rowElements.imageAsset.value = normalizedSnapshot.imageAsset;
      if (normalizedSnapshot.fileName) {
        rowElements.imageUploadName.value = normalizedSnapshot.fileName;
      } else if (normalizedSnapshot.imageData) {
        rowElements.imageUploadName.value = FILE_PAYLOAD_PLACEHOLDER;
      } else {
        rowElements.imageUploadName.value = FILE_SELECTION_PLACEHOLDER;
      }
      setControlNetPreview(rowElements.preview, {
        imageData: normalizedSnapshot.imageData,
        imageAsset: normalizedSnapshot.imageAsset,
      });
      rowElements.generatedPreviewData = "";
      setControlNetGeneratedPreview(rowElements.preview, {
        imageData: rowElements.generatedPreviewData,
        visible: rowElements.allowPreview.checked,
      });
      const brushSyncPromise = rowElements.sourceBrush?.syncSourceData(normalizedSnapshot.imageData);
      if (brushSyncPromise && typeof brushSyncPromise.catch === "function") {
        // CRITICAL: brush sync is async decode work; keep source snapshot application deterministic even if a decode attempt fails.
        brushSyncPromise.catch(() => {});
      }
      syncPreviewHistoryButtons();
      syncRunPreprocessorVisibility(rowElements, isImg2ImgEditor);
      syncHiddenField();
      if (options.statusMessage && onStatusMessage) {
        onStatusMessage(options.statusMessage);
      }
    };

    const bindSourceUploadInput = (fileInput) => {
      fileInput.addEventListener("change", async () => {
        const [file] = Array.from(fileInput.files ?? []);
        if (!file) {
          return;
        }
        try {
          const imageDataUrl = await readFileAsDataUrl(file);
          applyRowSourceSnapshot(
            {
              imageData: imageDataUrl,
              imageAsset: "",
              fileName: file.name,
            },
            {
              recordHistory: true,
              statusMessage: `Loaded ControlNet source image: ${file.name}`,
            },
          );
        } catch (_error) {
          rowElements.imageUploadName.value = FILE_SELECTION_PLACEHOLDER;
          if (onStatusMessage) {
            onStatusMessage("Failed to load ControlNet source image.");
          }
        }
      });
    };

    bindSourceUploadInput(imageUploadControl.fileInput);
    bindSourceUploadInput(preview.sourceUploadInput);

    rowElements.sourceBrush = createSourceCanvasBrushController({
      idPrefix: `${idPrefix}-source-${index}`,
      stage: preview.stage,
      toolbar: preview.toolbar,
      previewImage: preview.previewImage,
      onCommitSource: async (editedImageData) => {
        applyRowSourceSnapshot(
          {
            imageData: editedImageData,
            imageAsset: "",
            fileName: FILE_PAYLOAD_PLACEHOLDER,
          },
          {
            recordHistory: true,
            statusMessage: `ControlNet Unit ${index + 1}: applied source brush edits.`,
          },
        );
      },
      onStatusMessage: (message) => {
        if (onStatusMessage) {
          onStatusMessage(`ControlNet Unit ${index + 1}: ${message}`);
        }
      },
    });

    unitRows.push(rowElements);
    applyCatalogToRow(rowElements, false);
    bindSyncHandlers(rowElements);
    setControlNetPreview(preview, { imageData: "", imageAsset: "" });
    setControlNetGeneratedPreview(preview, { imageData: "", visible: false });
    rowElements.sourceBrush.syncSourceData("");

    moduleSelect.addEventListener("change", syncHiddenField);
    modelSelect.addEventListener("change", syncHiddenField);

    attachUploadHandler(maskUploadControl.fileInput, {
      dataField: maskData,
      assetField: maskAsset,
      label: "mask image",
      fileNameField: maskUploadControl.fileNameInput,
    });

    imageAsset.addEventListener("input", () => {
      rowElements.generatedPreviewData = "";
      setControlNetGeneratedPreview(preview, {
        imageData: rowElements.generatedPreviewData,
        visible: rowElements.allowPreview.checked,
      });
      if (imageData.value.trim()) {
        syncRunPreprocessorVisibility(rowElements, isImg2ImgEditor);
        return;
      }
      setControlNetPreview(preview, { imageData: "", imageAsset: imageAsset.value });
      syncRunPreprocessorVisibility(rowElements, isImg2ImgEditor);
    });
    imageData.addEventListener("input", () => {
      setControlNetPreview(preview, { imageData: imageData.value, imageAsset: imageAsset.value });
      rowElements.generatedPreviewData = "";
      setControlNetGeneratedPreview(preview, {
        imageData: rowElements.generatedPreviewData,
        visible: rowElements.allowPreview.checked,
      });
      rowElements.sourceBrush?.syncSourceData(imageData.value);
      syncRunPreprocessorVisibility(rowElements, isImg2ImgEditor);
    });
    allowPreview.addEventListener("change", () => {
      setControlNetGeneratedPreview(preview, {
        imageData: rowElements.generatedPreviewData,
        visible: allowPreview.checked,
      });
      if (rowElements.generatedPreviewData && onStatusMessage) {
        onStatusMessage(
          allowPreview.checked
            ? `ControlNet Unit ${index + 1}: generated preview is now visible.`
            : `ControlNet Unit ${index + 1}: generated preview hidden (Allow Preview off).`,
        );
      }
    });

    preview.uploadButton.addEventListener("click", () => {
      preview.sourceUploadInput.click();
    });
    preview.stage.addEventListener("click", (event) => {
      const target = event.target;
      if (target && typeof target.closest === "function" && target.closest(".rookieui-shell__controlnet-preview-toolbar")) {
        return;
      }
      if (!canCanvasStageOpenUpload(imageData.value, imageAsset.value)) {
        // CRITICAL: when a source image is already bound, stage click must no longer open file picker; this reserves click interactions for edit-first canvas behavior.
        return;
      }
      preview.sourceUploadInput.click();
    });
    preview.stage.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (!canCanvasStageOpenUpload(imageData.value, imageAsset.value)) {
          return;
        }
        preview.sourceUploadInput.click();
      }
    });
    preview.stage.setAttribute("tabindex", "0");
    preview.stage.setAttribute("role", "button");

    const syncPreviewFullscreenButton = () => {
      const fullscreenActive = isCanvasElementFullscreen(preview.stage);
      // CRITICAL: keep icon/title state derived from real fullscreen element so toolbar stays correct after Esc-based exits.
      const iconNode = preview.fullscreenButton.querySelector(".rookieui-shell__mini-action-icon");
      if (iconNode) {
        iconNode.textContent = fullscreenActive ? FULLSCREEN_EXIT_ICON : FULLSCREEN_ENTER_ICON;
      }
      preview.fullscreenButton.title = fullscreenActive ? "Exit fullscreen preview" : "Fullscreen preview";
      preview.fullscreenButton.setAttribute(
        "aria-label",
        fullscreenActive ? "Exit fullscreen preview" : "Fullscreen preview",
      );
    };
    syncPreviewFullscreenButton();
    if (globalThis.document && typeof globalThis.document.addEventListener === "function") {
      globalThis.document.addEventListener("fullscreenchange", syncPreviewFullscreenButton);
      globalThis.document.addEventListener("webkitfullscreenchange", syncPreviewFullscreenButton);
    }

    preview.stage.addEventListener("dragover", (event) => {
      event.preventDefault();
      preview.stage.dataset.dragging = "true";
    });
    preview.stage.addEventListener("dragleave", () => {
      preview.stage.dataset.dragging = "false";
    });
    preview.stage.addEventListener("drop", async (event) => {
      event.preventDefault();
      preview.stage.dataset.dragging = "false";
      const [file] = Array.from(event.dataTransfer?.files ?? []);
      if (!file) {
        return;
      }
      try {
        const imageDataUrl = await readFileAsDataUrl(file);
        applyRowSourceSnapshot(
          {
            imageData: imageDataUrl,
            imageAsset: "",
            fileName: file.name,
          },
          {
            recordHistory: true,
            statusMessage: `Loaded ControlNet source image: ${file.name}`,
          },
        );
      } catch (_error) {
        if (onStatusMessage) {
          onStatusMessage("Failed to load dropped ControlNet source image.");
        }
      }
    });

    preview.removeButton.addEventListener("click", () => {
      // IMPORTANT: clear both fields atomically; split source state causes stale visibility and payload mismatches.
      applyRowSourceSnapshot(
        {
          imageData: "",
          imageAsset: "",
          fileName: FILE_SELECTION_PLACEHOLDER,
        },
        {
          recordHistory: true,
          statusMessage: `ControlNet Unit ${index + 1}: cleared source image.`,
        },
      );
    });

    preview.resetButton.addEventListener("click", () => {
      const snapshot = readRowSourceSnapshot();
      if (!hasCanvasSourceImage(snapshot.imageData, snapshot.imageAsset)) {
        if (onStatusMessage) {
          onStatusMessage(`ControlNet Unit ${index + 1}: no source image to reset.`);
        }
        return;
      }
      setControlNetPreview(preview, { imageData: snapshot.imageData, imageAsset: snapshot.imageAsset });
      if (onStatusMessage) {
        onStatusMessage(`ControlNet Unit ${index + 1}: source preview reset.`);
      }
    });

    preview.fullscreenButton.addEventListener("click", async () => {
      const fullscreenAction = await toggleCanvasFullscreen(preview.stage);
      syncPreviewFullscreenButton();
      rowElements.sourceBrush?.syncFullscreenState?.();
      if (onStatusMessage) {
        const statusMessage =
          fullscreenAction === CANVAS_FULLSCREEN_ACTIONS.entered
            ? `ControlNet Unit ${index + 1}: source preview entered fullscreen mode.`
            : fullscreenAction === CANVAS_FULLSCREEN_ACTIONS.exited
              ? `ControlNet Unit ${index + 1}: source preview exited fullscreen mode.`
              : `ControlNet Unit ${index + 1}: fullscreen is unavailable.`;
        onStatusMessage(statusMessage);
      }
    });

    preview.undoButton.addEventListener("click", () => {
      if (!preview.history.undo.length) {
        return;
      }
      const currentSnapshot = readRowSourceSnapshot();
      const previousSnapshot = preview.history.undo.pop();
      preview.history.redo.push(currentSnapshot);
      applyRowSourceSnapshot(previousSnapshot, {
        recordHistory: false,
        statusMessage: `ControlNet Unit ${index + 1}: restored previous source image.`,
      });
    });

    preview.redoButton.addEventListener("click", () => {
      if (!preview.history.redo.length) {
        return;
      }
      const currentSnapshot = readRowSourceSnapshot();
      const nextSnapshot = preview.history.redo.pop();
      preview.history.undo.push(currentSnapshot);
      applyRowSourceSnapshot(nextSnapshot, {
        recordHistory: false,
        statusMessage: `ControlNet Unit ${index + 1}: reapplied source image.`,
      });
    });

    runPreprocessorButton.addEventListener("click", () => {
      runPreprocessorForRow(rowElements, index);
    });

    syncRunPreprocessorVisibility(rowElements, isImg2ImgEditor);
    syncPreviewHistoryButtons();

    tab.addEventListener("click", () => {
      activateTab(index);
    });
  }

  activateTab(0);

  const setUnits = (units) => {
    const normalizedUnits = Array.isArray(units) ? units.map((entry) => normalizeUnitPayload(entry)) : [];
    for (let index = 0; index < unitRows.length; index += 1) {
      const row = unitRows[index];
      const unit = normalizedUnits[index] ?? normalizeUnitPayload();

      row.enabled.checked = unit.enabled;
      row.pixelPerfect.checked = unit.pixel_perfect;
      row.allowPreview.checked = unit.allow_preview;
      row.useMask.checked = unit.use_mask;
      row.controlType.setValue(unit.control_type);
      applyCatalogToRow(row, false);

      row.module.value = unit.module;
      row.model.value = unit.model;
      row.weight.value = String(unit.weight);
      row.weightSlider.value = String(unit.weight);
      row.guidanceStart.value = String(unit.guidance_start);
      row.guidanceStartSlider.value = String(unit.guidance_start);
      row.guidanceEnd.value = String(unit.guidance_end);
      row.guidanceEndSlider.value = String(unit.guidance_end);
      row.ensureGuidanceBounds("start");
      row.resizeMode.value = unit.resize_mode;
      row.resizeModeBridge.setValue(unit.resize_mode);
      row.controlMode.value = unit.control_mode;
      row.controlModeBridge.setValue(unit.control_mode);
      row.processorRes.value = String(unit.processor_res);
      row.thresholdA.value = String(unit.threshold_a);
      row.thresholdB.value = String(unit.threshold_b);
      row.hrOption.value = unit.hr_option;
      row.imageAsset.value = unit.image_asset;
      row.imageData.value = unit.image_data;
      row.maskAsset.value = unit.mask_asset;
      row.maskData.value = unit.mask_data;

      row.imageUploadName.value = unit.image_data ? FILE_PAYLOAD_PLACEHOLDER : FILE_SELECTION_PLACEHOLDER;
      row.maskUploadName.value = unit.mask_data ? FILE_PAYLOAD_PLACEHOLDER : FILE_SELECTION_PLACEHOLDER;
      row.preview.history.undo = [];
      row.preview.history.redo = [];
      setControlNetPreview(row.preview, { imageData: unit.image_data, imageAsset: unit.image_asset });
      row.sourceBrush?.syncSourceData(unit.image_data);
      row.preprocessorBusy = false;
      row.generatedPreviewData = "";
      setControlNetGeneratedPreview(row.preview, { imageData: row.generatedPreviewData, visible: row.allowPreview.checked });
      syncRunPreprocessorVisibility(row, isImg2ImgEditor);
    }
    syncHiddenField();
  };

  const refreshFromHidden = () => {
    const units = toObjectArray(hiddenInput.value);
    setUnits(units);
  };

  const setModelOptions = (nextModelOptions = []) => {
    currentModelOptions = [{ value: "", label: "(Select ControlNet Model)" }, ...nextModelOptions];
    currentModelValues = nextModelOptions.map((entry) => String(entry.value ?? "")).filter(Boolean);
    controlTypeCatalog = normalizeControlTypeCatalog(controlTypeCatalog, currentModelValues, controlTypeOptions);
    unitRows.forEach((row) => {
      applyCatalogToRow(row, true);
    });
    syncHiddenField();
  };

  const setControlTypeCatalog = (rawControlTypes = {}) => {
    controlTypeCatalog = normalizeControlTypeCatalog(rawControlTypes, currentModelValues, controlTypeOptions);
    unitRows.forEach((row) => {
      applyCatalogToRow(row, false);
    });
    syncHiddenField();
  };

  syncHiddenField();

  return {
    setUnits,
    refreshFromHidden,
    setModelOptions,
    setControlTypeCatalog,
  };
}
