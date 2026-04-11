const DEFAULT_UNIT_COUNT = 3;

const MODULE_OPTIONS = [
  { value: "none", label: "None" },
  { value: "canny", label: "Canny" },
  { value: "depth", label: "Depth" },
  { value: "openpose", label: "OpenPose" },
  { value: "lineart", label: "Lineart" },
  { value: "scribble", label: "Scribble" },
  { value: "softedge", label: "SoftEdge" },
  { value: "inpaint", label: "Inpaint" },
];

const CONTROL_MODE_OPTIONS = [
  { value: "balanced", label: "Balanced" },
  { value: "prompt", label: "Prompt Priority" },
  { value: "control", label: "Control Priority" },
];

const HR_OPTION_OPTIONS = [
  { value: "both", label: "Both" },
  { value: "low_res_only", label: "Low-res Only" },
  { value: "high_res_only", label: "High-res Only" },
];

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

function normalizeUnitPayload(rawUnit = {}) {
  return {
    enabled: Boolean(rawUnit.enabled),
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
    Boolean(unit.model) ||
    Boolean(unit.image_asset) ||
    Boolean(unit.image_data) ||
    Boolean(unit.mask_asset) ||
    Boolean(unit.mask_data)
  );
}

export function createControlNetUnitEditor({
  idPrefix,
  parent,
  hiddenInput,
  modelOptions = [],
  createInput,
  createSelect,
  createCheckbox,
  createField,
  createInlineCheckboxField,
  appendTextElement,
  readFileAsDataUrl,
  syncBoundControls,
  onStatusMessage = null,
  unitCount = DEFAULT_UNIT_COUNT,
}) {
  const section = document.createElement("section");
  section.className = "rookieui-shell__section rookieui-shell__section--soft";
  section.id = `${idPrefix}-section`;
  parent.appendChild(section);
  appendTextElement(section, "h4", "rookieui-shell__section-title", "ControlNet");
  appendTextElement(
    section,
    "p",
    "rookieui-shell__status",
    "A1111-style unit groups: set model + source image per enabled unit.",
  );

  const unitRows = [];
  const models = [{ value: "", label: "(Select ControlNet Model)" }, ...modelOptions];

  const syncHiddenField = () => {
    const units = unitRows
      .map((row) => ({
        enabled: row.enabled.checked,
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

  const bindSyncHandlers = (elements) => {
    Object.values(elements).forEach((element) => {
      if (!element || element.type === "file") {
        return;
      }
      element.addEventListener("change", syncHiddenField);
      if (element.tagName === "INPUT" || element.tagName === "SELECT" || element.tagName === "TEXTAREA") {
        element.addEventListener("input", syncHiddenField);
      }
    });
  };

  const attachUploadHandler = (fileInput, { dataField, assetField, label }) => {
    fileInput.addEventListener("change", async () => {
      const [file] = Array.from(fileInput.files ?? []);
      if (!file) {
        return;
      }
      try {
        dataField.value = await readFileAsDataUrl(file);
        assetField.value = "";
        syncHiddenField();
        if (onStatusMessage) {
          onStatusMessage(`Loaded ControlNet ${label}: ${file.name}`);
        }
      } catch (_error) {
        if (onStatusMessage) {
          onStatusMessage(`Failed to load ControlNet ${label}.`);
        }
      }
    });
  };

  for (let index = 0; index < unitCount; index += 1) {
    const card = document.createElement("div");
    card.className = "rookieui-shell__section rookieui-shell__section--inner";
    card.id = `${idPrefix}-unit-${index}`;
    section.appendChild(card);
    appendTextElement(card, "h5", "rookieui-shell__section-title", `Unit ${index}`);

    const grid = document.createElement("div");
    grid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
    card.appendChild(grid);

    const enabled = createCheckbox(`${idPrefix}-enabled-${index}`, false);
    createInlineCheckboxField(grid, "Enabled", enabled, `${idPrefix}-enabled-field-${index}`);

    const moduleSelect = createSelect(`${idPrefix}-module-${index}`, MODULE_OPTIONS, "none");
    createField(grid, "Preprocessor", moduleSelect);

    const modelSelect = createSelect(`${idPrefix}-model-${index}`, models, "");
    createField(grid, "Model", modelSelect);

    const weightInput = createInput("number", `${idPrefix}-weight-${index}`, "1", {
      min: 0,
      max: 2,
      step: 0.01,
      inputMode: "decimal",
    });
    createField(grid, "Weight", weightInput);

    const guidanceStartInput = createInput("number", `${idPrefix}-guidance-start-${index}`, "0", {
      min: 0,
      max: 1,
      step: 0.01,
      inputMode: "decimal",
    });
    createField(grid, "Guidance Start", guidanceStartInput);

    const guidanceEndInput = createInput("number", `${idPrefix}-guidance-end-${index}`, "1", {
      min: 0,
      max: 1,
      step: 0.01,
      inputMode: "decimal",
    });
    createField(grid, "Guidance End", guidanceEndInput);

    const resizeModeInput = createSelect(
      `${idPrefix}-resize-mode-${index}`,
      [
        { value: "crop_and_resize", label: "Crop and Resize" },
        { value: "just_resize", label: "Just Resize" },
        { value: "resize_and_fill", label: "Resize and Fill" },
      ],
      "crop_and_resize",
    );
    createField(grid, "Resize Mode", resizeModeInput);

    const controlModeInput = createSelect(`${idPrefix}-control-mode-${index}`, CONTROL_MODE_OPTIONS, "balanced");
    createField(grid, "Control Mode", controlModeInput);

    const processorResInput = createInput("number", `${idPrefix}-processor-res-${index}`, "512", {
      min: 64,
      max: 2048,
      step: 8,
      inputMode: "numeric",
    });
    createField(grid, "Processor Res", processorResInput);

    const thresholdAInput = createInput("number", `${idPrefix}-threshold-a-${index}`, "64", {
      min: 0,
      max: 255,
      step: 1,
      inputMode: "numeric",
    });
    createField(grid, "Threshold A", thresholdAInput);

    const thresholdBInput = createInput("number", `${idPrefix}-threshold-b-${index}`, "64", {
      min: 0,
      max: 255,
      step: 1,
      inputMode: "numeric",
    });
    createField(grid, "Threshold B", thresholdBInput);

    const pixelPerfect = createCheckbox(`${idPrefix}-pixel-perfect-${index}`, false);
    createInlineCheckboxField(grid, "Pixel Perfect", pixelPerfect, `${idPrefix}-pixel-perfect-field-${index}`);

    const hrOption = createSelect(`${idPrefix}-hr-option-${index}`, HR_OPTION_OPTIONS, "both");
    createField(grid, "Hires Option", hrOption);

    const imageAsset = createInput("text", `${idPrefix}-image-asset-${index}`, "");
    imageAsset.placeholder = "Control image asset handle";
    createField(grid, "Image Asset", imageAsset);

    const imageData = createInput("hidden", `${idPrefix}-image-data-${index}`, "");
    grid.appendChild(imageData);

    const maskAsset = createInput("text", `${idPrefix}-mask-asset-${index}`, "");
    maskAsset.placeholder = "Optional mask asset handle";
    createField(grid, "Mask Asset", maskAsset);

    const maskData = createInput("hidden", `${idPrefix}-mask-data-${index}`, "");
    grid.appendChild(maskData);

    const uploadRow = document.createElement("div");
    uploadRow.className = "rookieui-shell__mini-actions";
    card.appendChild(uploadRow);

    // CRITICAL: keep ControlNet upload inputs non-overlay; `.rookieui-shell__file-input`
    // is absolute-positioned for dropzones and will intercept unrelated clicks here.
    const imageUpload = createInput("file", `${idPrefix}-image-upload-${index}`, "", {
      className: "rookieui-shell__input",
    });
    imageUpload.accept = "image/png,image/webp,image/jpeg";
    imageUpload.setAttribute("aria-label", "Upload Control Image");
    uploadRow.appendChild(imageUpload);

    const maskUpload = createInput("file", `${idPrefix}-mask-upload-${index}`, "", {
      className: "rookieui-shell__input",
    });
    maskUpload.accept = "image/png,image/webp,image/jpeg";
    maskUpload.setAttribute("aria-label", "Upload Control Mask");
    uploadRow.appendChild(maskUpload);

    const rowElements = {
      enabled,
      module: moduleSelect,
      model: modelSelect,
      weight: weightInput,
      guidanceStart: guidanceStartInput,
      guidanceEnd: guidanceEndInput,
      resizeMode: resizeModeInput,
      controlMode: controlModeInput,
      processorRes: processorResInput,
      thresholdA: thresholdAInput,
      thresholdB: thresholdBInput,
      pixelPerfect,
      hrOption,
      imageAsset,
      imageData,
      maskAsset,
      maskData,
      imageUpload,
      maskUpload,
    };
    unitRows.push(rowElements);
    bindSyncHandlers(rowElements);
    attachUploadHandler(imageUpload, { dataField: imageData, assetField: imageAsset, label: "source image" });
    attachUploadHandler(maskUpload, { dataField: maskData, assetField: maskAsset, label: "mask image" });
  }

  const setUnits = (units) => {
    const normalizedUnits = Array.isArray(units)
      ? units.map((entry) => normalizeUnitPayload(entry))
      : [];
    for (let index = 0; index < unitRows.length; index += 1) {
      const unit = normalizedUnits[index] ?? normalizeUnitPayload();
      const row = unitRows[index];
      row.enabled.checked = unit.enabled;
      row.module.value = unit.module;
      row.model.value = unit.model;
      row.weight.value = String(unit.weight);
      row.guidanceStart.value = String(unit.guidance_start);
      row.guidanceEnd.value = String(unit.guidance_end);
      row.resizeMode.value = unit.resize_mode;
      row.controlMode.value = unit.control_mode;
      row.processorRes.value = String(unit.processor_res);
      row.thresholdA.value = String(unit.threshold_a);
      row.thresholdB.value = String(unit.threshold_b);
      row.pixelPerfect.checked = unit.pixel_perfect;
      row.hrOption.value = unit.hr_option;
      row.imageAsset.value = unit.image_asset;
      row.imageData.value = unit.image_data;
      row.maskAsset.value = unit.mask_asset;
      row.maskData.value = unit.mask_data;
    }
    syncHiddenField();
  };

  const refreshFromHidden = () => {
    const units = toObjectArray(hiddenInput.value);
    setUnits(units);
  };

  syncHiddenField();
  return {
    setUnits,
    refreshFromHidden,
  };
}
