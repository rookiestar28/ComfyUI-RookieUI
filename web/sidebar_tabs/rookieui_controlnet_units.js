const DEFAULT_UNIT_COUNT = 3;
const DEFAULT_CONTROL_TYPE = "All";

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
  { value: "prompt", label: "Prompt Priority" },
  { value: "control", label: "Control Priority" },
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
    field.classList.add(extraClass);
  }
  const label = document.createElement("span");
  label.className = "rookieui-shell__field-label";
  label.textContent = labelText;
  field.appendChild(label);
  field.appendChild(control);
  parent.appendChild(field);
  return field;
}

function buildFallbackControlTypeCatalog(controlTypeOptions) {
  const allModules = MODULE_OPTIONS.map((entry) => entry.value);
  const map = {
    All: {
      module_list: allModules,
      model_list: [],
      default_option: "none",
    },
    Canny: {
      module_list: ["canny"],
      model_list: [],
      default_option: "canny",
    },
    Depth: {
      module_list: ["depth"],
      model_list: [],
      default_option: "depth",
    },
    Inpaint: {
      module_list: ["inpaint"],
      model_list: [],
      default_option: "inpaint",
    },
    OpenPose: {
      module_list: ["openpose"],
      model_list: [],
      default_option: "openpose",
    },
    Lineart: {
      module_list: ["lineart"],
      model_list: [],
      default_option: "lineart",
    },
    Scribble: {
      module_list: ["scribble"],
      model_list: [],
      default_option: "scribble",
    },
    SoftEdge: {
      module_list: ["softedge"],
      model_list: [],
      default_option: "softedge",
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
      optionLabel.dataset.active = radio.checked ? "true" : "false";
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
  createSelect,
  createCheckbox,
  createField,
  createInlineCheckboxField,
  appendTextElement,
  readFileAsDataUrl,
  syncBoundControls,
  onStatusMessage = null,
  unitCount = DEFAULT_UNIT_COUNT,
  controlTypeOrder = DEFAULT_CONTROL_TYPE_OPTIONS,
}) {
  const integratedDetails = document.createElement("details");
  integratedDetails.className =
    "rookieui-shell__section rookieui-shell__section--soft rookieui-shell__hires rookieui-shell__controlnet-integrated";
  integratedDetails.id = `${idPrefix}-section`;
  integratedDetails.open = true;
  parent.appendChild(integratedDetails);

  const summary = document.createElement("summary");
  summary.className = "rookieui-shell__hires-summary";
  integratedDetails.appendChild(summary);

  const header = document.createElement("div");
  header.className = "rookieui-shell__hires-header";
  summary.appendChild(header);

  const title = document.createElement("span");
  title.className = "rookieui-shell__hires-title";
  title.textContent = "ControlNet Integrated";
  header.appendChild(title);

  const caret = document.createElement("span");
  caret.className = "rookieui-shell__hires-caret";
  caret.textContent = "▸";
  header.appendChild(caret);

  const body = document.createElement("div");
  body.className = "rookieui-shell__controlnet-body";
  integratedDetails.appendChild(body);

  appendTextElement(
    body,
    "p",
    "rookieui-shell__status rookieui-shell__controlnet-note",
    "A1111/Forge style integrated units: each enabled unit sets control type, preprocessor, model, and source image.",
  );

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

  const attachUploadHandler = (fileInput, { dataField, assetField, label, fileNameField }) => {
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

    const primaryGrid = document.createElement("div");
    primaryGrid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
    panel.appendChild(primaryGrid);

    const enabled = createCheckbox(`${idPrefix}-enabled-${index}`, false);
    createInlineCheckboxField(primaryGrid, "Enable", enabled, `${idPrefix}-enabled-field-${index}`);

    const pixelPerfect = createCheckbox(`${idPrefix}-pixel-perfect-${index}`, false);
    createInlineCheckboxField(primaryGrid, "Pixel Perfect", pixelPerfect, `${idPrefix}-pixel-perfect-field-${index}`);

    const allowPreview = createCheckbox(`${idPrefix}-allow-preview-${index}`, false);
    createInlineCheckboxField(primaryGrid, "Allow Preview", allowPreview, `${idPrefix}-allow-preview-field-${index}`);

    const useMask = createCheckbox(`${idPrefix}-use-mask-${index}`, false);
    createInlineCheckboxField(primaryGrid, "Use Mask", useMask, `${idPrefix}-use-mask-field-${index}`);

    const controlType = createControlTypeSelector({
      idPrefix,
      index,
      controlTypeOptions,
      onChange: () => {
        applyCatalogToRow(rowElements, false);
        syncHiddenField();
      },
    });
    createCustomField(primaryGrid, "Control Type", controlType.group, "rookieui-shell__field--full");

    const settingsGrid = document.createElement("div");
    settingsGrid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
    panel.appendChild(settingsGrid);

    const moduleSelect = createSelect(`${idPrefix}-module-${index}`, MODULE_OPTIONS, "none");
    createField(settingsGrid, "Preprocessor", moduleSelect);

    const modelSelect = createSelect(`${idPrefix}-model-${index}`, currentModelOptions, "");
    createField(settingsGrid, "Model", modelSelect);

    const weightInput = createInput("number", `${idPrefix}-weight-${index}`, "1", {
      min: 0,
      max: 2,
      step: 0.01,
      inputMode: "decimal",
    });
    createField(settingsGrid, "Control Weight", weightInput);

    const guidanceStartInput = createInput("number", `${idPrefix}-guidance-start-${index}`, "0", {
      min: 0,
      max: 1,
      step: 0.01,
      inputMode: "decimal",
    });
    createField(settingsGrid, "Guidance Start", guidanceStartInput);

    const guidanceEndInput = createInput("number", `${idPrefix}-guidance-end-${index}`, "1", {
      min: 0,
      max: 1,
      step: 0.01,
      inputMode: "decimal",
    });
    createField(settingsGrid, "Guidance End", guidanceEndInput);

    const resizeModeInput = createSelect(`${idPrefix}-resize-mode-${index}`, RESIZE_MODE_OPTIONS, "crop_and_resize");
    createField(settingsGrid, "Resize Mode", resizeModeInput);

    const controlModeInput = createSelect(`${idPrefix}-control-mode-${index}`, CONTROL_MODE_OPTIONS, "balanced");
    createField(settingsGrid, "Control Mode", controlModeInput);

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
    uploadRow.className = "rookieui-shell__mini-actions rookieui-shell__controlnet-upload-row";
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

    const rowElements = {
      enabled,
      pixelPerfect,
      allowPreview,
      useMask,
      controlType,
      controlTypeRadios: controlType.radios,
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
      hrOption,
      imageAsset,
      imageData,
      maskAsset,
      maskData,
      imageUpload: imageUploadControl.fileInput,
      maskUpload: maskUploadControl.fileInput,
      imageUploadName: imageUploadControl.fileNameInput,
      maskUploadName: maskUploadControl.fileNameInput,
    };

    unitRows.push(rowElements);
    applyCatalogToRow(rowElements, false);
    bindSyncHandlers(rowElements);

    moduleSelect.addEventListener("change", syncHiddenField);
    modelSelect.addEventListener("change", syncHiddenField);

    attachUploadHandler(imageUploadControl.fileInput, {
      dataField: imageData,
      assetField: imageAsset,
      label: "source image",
      fileNameField: imageUploadControl.fileNameInput,
    });

    attachUploadHandler(maskUploadControl.fileInput, {
      dataField: maskData,
      assetField: maskAsset,
      label: "mask image",
      fileNameField: maskUploadControl.fileNameInput,
    });

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
      row.guidanceStart.value = String(unit.guidance_start);
      row.guidanceEnd.value = String(unit.guidance_end);
      row.resizeMode.value = unit.resize_mode;
      row.controlMode.value = unit.control_mode;
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
