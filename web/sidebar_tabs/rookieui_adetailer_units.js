const DEFAULT_UNIT_COUNT = 4;
const UNIT_LABELS = ["1st", "2nd", "3rd", "4th"];

function normalizeNumber(value, fallbackValue) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallbackValue;
}

function normalizeInteger(value, fallbackValue) {
  return Math.round(normalizeNumber(value, fallbackValue));
}

function normalizeString(value, fallbackValue = "") {
  if (typeof value !== "string") {
    return fallbackValue;
  }
  const normalized = value.trim();
  return normalized || fallbackValue;
}

function normalizeBoolean(value, fallbackValue = false) {
  if (typeof value === "boolean") {
    return value;
  }
  if (value === "true" || value === "1" || value === 1) {
    return true;
  }
  if (value === "false" || value === "0" || value === 0) {
    return false;
  }
  return fallbackValue;
}

function parseJsonObjectField(rawValue, fallbackValue) {
  if (typeof rawValue !== "string" || !rawValue.trim()) {
    return fallbackValue;
  }
  try {
    const parsed = JSON.parse(rawValue);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : fallbackValue;
  } catch (_error) {
    return fallbackValue;
  }
}

function buildUnitDefaults(catalog = {}) {
  const defaults = catalog?.contract?.defaults ?? {};
  return {
    enabled: false,
    detector: String(catalog?.default_detector ?? defaults.detector ?? "None"),
    detector_classes: String(defaults.detector_classes ?? ""),
    prompt: "",
    negative_prompt: "",
    confidence: normalizeNumber(defaults.confidence, 0.3),
    mask_filter_method: String(defaults.mask_filter_method ?? "Area"),
    mask_k: normalizeInteger(defaults.mask_k, 0),
    mask_min_ratio: normalizeNumber(defaults.mask_min_ratio, 0.0),
    mask_max_ratio: normalizeNumber(defaults.mask_max_ratio, 1.0),
    x_offset: normalizeInteger(defaults.x_offset, 0),
    y_offset: normalizeInteger(defaults.y_offset, 0),
    dilate_erode: normalizeInteger(defaults.dilate_erode, 4),
    mask_merge_mode: String(defaults.mask_merge_mode ?? "None"),
    mask_blur: normalizeInteger(defaults.mask_blur, 4),
    denoising_strength: normalizeNumber(defaults.denoising_strength, 0.4),
    inpaint_only_masked: normalizeBoolean(defaults.inpaint_only_masked, true),
    inpaint_padding: normalizeInteger(defaults.inpaint_padding, 32),
    use_inpaint_size: normalizeBoolean(defaults.use_inpaint_size, false),
    inpaint_width: normalizeInteger(defaults.inpaint_width, 512),
    inpaint_height: normalizeInteger(defaults.inpaint_height, 512),
    use_steps: normalizeBoolean(defaults.use_steps, false),
    steps: normalizeInteger(defaults.steps, 28),
    use_cfg_scale: normalizeBoolean(defaults.use_cfg_scale, false),
    cfg_scale: normalizeNumber(defaults.cfg_scale, 7.0),
    use_checkpoint: normalizeBoolean(defaults.use_checkpoint, false),
    checkpoint_name: String(defaults.checkpoint_name ?? "Use same checkpoint"),
    use_vae: normalizeBoolean(defaults.use_vae, false),
    vae_name: String(defaults.vae_name ?? "Use same VAE"),
    use_sampler: normalizeBoolean(defaults.use_sampler, false),
    sampler_name: String(defaults.sampler_name ?? "DPM++ 2M Karras"),
    scheduler_name: String(defaults.scheduler_name ?? "Use same scheduler"),
    use_noise_multiplier: normalizeBoolean(defaults.use_noise_multiplier, false),
    noise_multiplier: normalizeNumber(defaults.noise_multiplier, 1.0),
    use_clip_skip: normalizeBoolean(defaults.use_clip_skip, false),
    clip_skip: normalizeInteger(defaults.clip_skip, 1),
    restore_face: normalizeBoolean(defaults.restore_face, false),
    controlnet: {
      mode: "none",
      model: "",
      module: String(catalog?.controlnet_default_module ?? "none"),
      weight: 1.0,
      guidance_start: 0.0,
      guidance_end: 1.0,
    },
  };
}

function buildDefaultPayload(catalog = {}, surface = "txt2img") {
  const unitDefaults = buildUnitDefaults(catalog);
  const units = Array.from({ length: DEFAULT_UNIT_COUNT }, () => ({
    ...unitDefaults,
    enabled: false,
    detector: unitDefaults.detector,
    controlnet: { ...unitDefaults.controlnet },
  }));
  return {
    enabled: false,
    skip_img2img: surface === "img2img",
    units,
  };
}

function normalizeUnitPayload(rawUnit, catalog, fallbackUnit = null) {
  const defaults = buildUnitDefaults(catalog);
  const populatedRawUnit =
    rawUnit && typeof rawUnit === "object" && !Array.isArray(rawUnit) && Object.keys(rawUnit).length > 0;
  const controlnet = rawUnit?.controlnet && typeof rawUnit.controlnet === "object" ? rawUnit.controlnet : {};
  return {
    ...defaults,
    ...rawUnit,
    enabled: normalizeBoolean(rawUnit?.enabled, populatedRawUnit ? true : Boolean(fallbackUnit?.enabled)),
    detector: normalizeString(rawUnit?.detector, defaults.detector),
    detector_classes: String(rawUnit?.detector_classes ?? defaults.detector_classes),
    prompt: String(rawUnit?.prompt ?? ""),
    negative_prompt: String(rawUnit?.negative_prompt ?? ""),
    confidence: normalizeNumber(rawUnit?.confidence, defaults.confidence),
    mask_filter_method: normalizeString(rawUnit?.mask_filter_method, defaults.mask_filter_method),
    mask_k: normalizeInteger(rawUnit?.mask_k, defaults.mask_k),
    mask_min_ratio: normalizeNumber(rawUnit?.mask_min_ratio, defaults.mask_min_ratio),
    mask_max_ratio: normalizeNumber(rawUnit?.mask_max_ratio, defaults.mask_max_ratio),
    x_offset: normalizeInteger(rawUnit?.x_offset, defaults.x_offset),
    y_offset: normalizeInteger(rawUnit?.y_offset, defaults.y_offset),
    dilate_erode: normalizeInteger(rawUnit?.dilate_erode, defaults.dilate_erode),
    mask_merge_mode: normalizeString(rawUnit?.mask_merge_mode, defaults.mask_merge_mode),
    mask_blur: normalizeInteger(rawUnit?.mask_blur, defaults.mask_blur),
    denoising_strength: normalizeNumber(rawUnit?.denoising_strength, defaults.denoising_strength),
    inpaint_only_masked: normalizeBoolean(rawUnit?.inpaint_only_masked, defaults.inpaint_only_masked),
    inpaint_padding: normalizeInteger(rawUnit?.inpaint_padding, defaults.inpaint_padding),
    use_inpaint_size: normalizeBoolean(rawUnit?.use_inpaint_size, defaults.use_inpaint_size),
    inpaint_width: normalizeInteger(rawUnit?.inpaint_width, defaults.inpaint_width),
    inpaint_height: normalizeInteger(rawUnit?.inpaint_height, defaults.inpaint_height),
    use_steps: normalizeBoolean(rawUnit?.use_steps, defaults.use_steps),
    steps: normalizeInteger(rawUnit?.steps, defaults.steps),
    use_cfg_scale: normalizeBoolean(rawUnit?.use_cfg_scale, defaults.use_cfg_scale),
    cfg_scale: normalizeNumber(rawUnit?.cfg_scale, defaults.cfg_scale),
    use_checkpoint: normalizeBoolean(rawUnit?.use_checkpoint, defaults.use_checkpoint),
    checkpoint_name: normalizeString(rawUnit?.checkpoint_name, defaults.checkpoint_name),
    use_vae: normalizeBoolean(rawUnit?.use_vae, defaults.use_vae),
    vae_name: normalizeString(rawUnit?.vae_name, defaults.vae_name),
    use_sampler: normalizeBoolean(rawUnit?.use_sampler, defaults.use_sampler),
    sampler_name: normalizeString(rawUnit?.sampler_name, defaults.sampler_name),
    scheduler_name: normalizeString(rawUnit?.scheduler_name, defaults.scheduler_name),
    use_noise_multiplier: normalizeBoolean(rawUnit?.use_noise_multiplier, defaults.use_noise_multiplier),
    noise_multiplier: normalizeNumber(rawUnit?.noise_multiplier, defaults.noise_multiplier),
    use_clip_skip: normalizeBoolean(rawUnit?.use_clip_skip, defaults.use_clip_skip),
    clip_skip: normalizeInteger(rawUnit?.clip_skip, defaults.clip_skip),
    restore_face: normalizeBoolean(rawUnit?.restore_face, defaults.restore_face),
    controlnet: {
      ...defaults.controlnet,
      ...controlnet,
      mode: normalizeString(controlnet?.mode, defaults.controlnet.mode),
      model: String(controlnet?.model ?? defaults.controlnet.model),
      module: normalizeString(controlnet?.module, defaults.controlnet.module),
      weight: normalizeNumber(controlnet?.weight, defaults.controlnet.weight),
      guidance_start: normalizeNumber(controlnet?.guidance_start, defaults.controlnet.guidance_start),
      guidance_end: normalizeNumber(controlnet?.guidance_end, defaults.controlnet.guidance_end),
    },
  };
}

function normalizePayload(rawPayload, catalog, surface) {
  const defaults = buildDefaultPayload(catalog, surface);
  const rawUnits = Array.isArray(rawPayload?.units) ? rawPayload.units : [];
  return {
    enabled: normalizeBoolean(rawPayload?.enabled, defaults.enabled),
    skip_img2img: surface === "img2img" ? normalizeBoolean(rawPayload?.skip_img2img, defaults.skip_img2img) : false,
    units: Array.from({ length: DEFAULT_UNIT_COUNT }, (_, index) =>
      normalizeUnitPayload(rawUnits[index], catalog, defaults.units[index]),
    ),
  };
}

function toSelectOptions(values, fallbackValues = []) {
  const merged = [...(Array.isArray(values) ? values : []), ...fallbackValues]
    .map((value) => String(value ?? "").trim())
    .filter(Boolean);
  return Array.from(new Set(merged)).map((value) => ({ value, label: value }));
}

function createSectionDetails(parent, title, id, appendTextElement) {
  const section = document.createElement("details");
  section.className = "rookieui-shell__section rookieui-shell__section--soft rookieui-shell__adetailer-subsection";
  section.id = id;
  section.open = true;
  parent.appendChild(section);

  const summary = document.createElement("summary");
  summary.className = "rookieui-shell__hires-summary rookieui-shell__adetailer-subsection-summary";
  section.appendChild(summary);
  appendTextElement(summary, "span", "rookieui-shell__section-title", title);

  const body = document.createElement("div");
  body.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
  section.appendChild(body);
  return body;
}

export function createADetailerEditor(options) {
  const {
    idPrefix,
    parent,
    hiddenInput,
    catalog = {},
    surface = "txt2img",
    createInput,
    createRangeInput,
    createSelect,
    createTextarea,
    createCheckbox,
    createField,
    createSliderField,
    createInlineCheckboxField,
    appendTextElement,
    bindSliderPair,
    syncBoundControls,
  } = options;

  const detectorEntries = Array.isArray(catalog.detectors) ? catalog.detectors : [];
  const detectorLookup = new Map(
    detectorEntries.map((entry) => [String(entry?.id ?? ""), entry && typeof entry === "object" ? entry : {}]),
  );
  const detectorOptions = toSelectOptions(detectorEntries.map((entry) => entry?.id), [catalog.default_detector ?? "None"]);
  const controlnetModes = toSelectOptions(catalog.controlnet_modes, ["none", "passthrough", "custom"]);
  const controlnetModels = toSelectOptions(catalog.controlnet_model_list, []);
  const controlnetModules = toSelectOptions(catalog.controlnet_module_list, ["none"]);
  const checkpointChoices = toSelectOptions(catalog.checkpoint_choices, ["Use same checkpoint"]);
  const vaeChoices = toSelectOptions(catalog.vae_choices, ["Use same VAE"]);
  const samplerChoices = toSelectOptions(catalog.sampler_choices, ["DPM++ 2M Karras"]);
  const schedulerChoices = toSelectOptions(catalog.scheduler_choices, ["Use same scheduler"]);
  const maskFilterMethods = toSelectOptions(catalog.mask_filter_methods, ["Area", "Confidence"]);
  const maskMergeModes = toSelectOptions(catalog.mask_merge_modes, ["None", "Merge", "Merge and Invert"]);

  if (!checkpointChoices.some((option) => option.value === "Use same checkpoint")) {
    checkpointChoices.unshift({ value: "Use same checkpoint", label: "Use same checkpoint" });
  }
  if (!vaeChoices.some((option) => option.value === "Use same VAE")) {
    vaeChoices.unshift({ value: "Use same VAE", label: "Use same VAE" });
  }
  if (!schedulerChoices.some((option) => option.value === "Use same scheduler")) {
    schedulerChoices.unshift({ value: "Use same scheduler", label: "Use same scheduler" });
  }

  let state = normalizePayload(parseJsonObjectField(hiddenInput?.value, {}), catalog, surface);
  const rows = [];

  const root = document.createElement("details");
  root.className = "rookieui-shell__section rookieui-shell__section--soft rookieui-shell__hires rookieui-shell__adetailer-integrated";
  root.id = `${idPrefix}-section`;
  root.open = false;
  parent.appendChild(root);

  const summary = document.createElement("summary");
  summary.className = "rookieui-shell__hires-summary rookieui-shell__adetailer-summary";
  root.appendChild(summary);

  const header = document.createElement("div");
  header.className = "rookieui-shell__hires-header rookieui-shell__adetailer-header";
  summary.appendChild(header);

  const topEnabled = createCheckbox(`${idPrefix}-enabled`, state.enabled);
  const topEnabledField = document.createElement("label");
  topEnabledField.className = "rookieui-shell__hires-toggle";
  topEnabled.setAttribute("aria-label", "Enable ADetailer");
  topEnabled.title = "Enable ADetailer";
  topEnabledField.appendChild(topEnabled);
  header.appendChild(topEnabledField);
  topEnabled.addEventListener("click", (event) => event.stopPropagation());
  topEnabled.addEventListener("mousedown", (event) => event.stopPropagation());
  topEnabled.addEventListener("keydown", (event) => event.stopPropagation());
  appendTextElement(header, "span", "rookieui-shell__section-title", "ADetailer");
  appendTextElement(header, "span", "rookieui-shell__hires-caret", "▸");

  const body = document.createElement("div");
  body.className = "rookieui-shell__adetailer-body";
  root.appendChild(body);

  const shellRow = document.createElement("div");
  shellRow.className = "rookieui-shell__adetailer-shell-row";
  body.appendChild(shellRow);

  const skipImg2Img = createCheckbox(`${idPrefix}-skip-img2img`, state.skip_img2img);
  const skipField = createInlineCheckboxField(shellRow, "Skip img2img", skipImg2Img);
  skipField.id = `${idPrefix}-skip-img2img-field`;
  if (surface !== "img2img") {
    skipImg2Img.disabled = true;
    skipField.dataset.executionHint = "txt2img-ignored";
  }

  appendTextElement(
    shellRow,
    "p",
    "rookieui-shell__status rookieui-shell__adetailer-shell-note",
    surface === "img2img"
      ? "Secondary refinement runs after the main img2img pass."
      : "Skip img2img is shown for parity but only applies to img2img surfaces.",
  );

  const tabs = document.createElement("div");
  tabs.className = "rookieui-shell__subtabs rookieui-shell__adetailer-tabs";
  tabs.id = `${idPrefix}-tabs`;
  tabs.setAttribute("role", "tablist");
  body.appendChild(tabs);

  const panelHost = document.createElement("div");
  panelHost.className = "rookieui-shell__controlnet-panel-host rookieui-shell__adetailer-panel-host";
  body.appendChild(panelHost);

  function syncHiddenInput() {
    state = {
      enabled: topEnabled.checked,
      skip_img2img: surface === "img2img" ? skipImg2Img.checked : false,
      units: rows.map((row) => ({
        enabled: row.controls.enabled.checked,
        detector: row.controls.detector.value,
        detector_classes: row.controls.detectorClasses.value,
        prompt: row.controls.prompt.value,
        negative_prompt: row.controls.negativePrompt.value,
        confidence: normalizeNumber(row.controls.confidence.value, 0.3),
        mask_filter_method: row.controls.maskFilterMethod.value,
        mask_k: normalizeInteger(row.controls.maskK.value, 0),
        mask_min_ratio: normalizeNumber(row.controls.maskMinRatio.value, 0.0),
        mask_max_ratio: normalizeNumber(row.controls.maskMaxRatio.value, 1.0),
        x_offset: normalizeInteger(row.controls.xOffset.value, 0),
        y_offset: normalizeInteger(row.controls.yOffset.value, 0),
        dilate_erode: normalizeInteger(row.controls.dilateErode.value, 4),
        mask_merge_mode: row.controls.maskMergeMode.value,
        mask_blur: normalizeInteger(row.controls.maskBlur.value, 4),
        denoising_strength: normalizeNumber(row.controls.denoisingStrength.value, 0.4),
        inpaint_only_masked: row.controls.inpaintOnlyMasked.checked,
        inpaint_padding: normalizeInteger(row.controls.inpaintPadding.value, 32),
        use_inpaint_size: row.controls.useInpaintSize.checked,
        inpaint_width: normalizeInteger(row.controls.inpaintWidth.value, 512),
        inpaint_height: normalizeInteger(row.controls.inpaintHeight.value, 512),
        use_steps: row.controls.useSteps.checked,
        steps: normalizeInteger(row.controls.steps.value, 28),
        use_cfg_scale: row.controls.useCfgScale.checked,
        cfg_scale: normalizeNumber(row.controls.cfgScale.value, 7.0),
        use_checkpoint: row.controls.useCheckpoint.checked,
        checkpoint_name: row.controls.checkpointName.value,
        use_vae: row.controls.useVae.checked,
        vae_name: row.controls.vaeName.value,
        use_sampler: row.controls.useSampler.checked,
        sampler_name: row.controls.samplerName.value,
        scheduler_name: row.controls.schedulerName.value,
        use_noise_multiplier: row.controls.useNoiseMultiplier.checked,
        noise_multiplier: normalizeNumber(row.controls.noiseMultiplier.value, 1.0),
        use_clip_skip: row.controls.useClipSkip.checked,
        clip_skip: normalizeInteger(row.controls.clipSkip.value, 1),
        restore_face: row.controls.restoreFace.checked,
        controlnet: {
          mode: row.controls.controlnetMode.value,
          model: row.controls.controlnetModel.value,
          module: row.controls.controlnetModule.value,
          weight: normalizeNumber(row.controls.controlnetWeight.value, 1.0),
          guidance_start: normalizeNumber(row.controls.controlnetGuidanceStart.value, 0.0),
          guidance_end: normalizeNumber(row.controls.controlnetGuidanceEnd.value, 1.0),
        },
      })),
    };
    hiddenInput.value = JSON.stringify(state);
  }

  function handleTopEnabledChange() {
    // IMPORTANT: top-level enable must bootstrap only the first ADetailer tab on an empty state.
    if (topEnabled.checked && !rows.some((row) => row.controls.enabled.checked) && rows[0]) {
      rows[0].controls.enabled.checked = true;
    }
    syncHiddenInput();
    syncBoundControls([topEnabled, ...rows.map((row) => row.controls.enabled)]);
  }

  function syncUnitVisibility(row) {
    const detectorMeta = detectorLookup.get(row.controls.detector.value) ?? {};
    const supportsClassFilter = Boolean(detectorMeta.supports_class_filter);
    row.detectorClassesField.hidden = !supportsClassFilter;
    row.detectorClassesField.style.display = supportsClassFilter ? "" : "none";
    row.controls.detectorClasses.disabled = !supportsClassFilter;
    row.controls.detectorClasses.readOnly = !supportsClassFilter;

    const useInpaintSize = row.controls.useInpaintSize.checked;
    row.controls.inpaintWidth.disabled = !useInpaintSize;
    row.controls.inpaintHeight.disabled = !useInpaintSize;
    row.controls.inpaintWidthSlider.disabled = !useInpaintSize;
    row.controls.inpaintHeightSlider.disabled = !useInpaintSize;

    const useSteps = row.controls.useSteps.checked;
    row.controls.steps.disabled = !useSteps;
    row.controls.stepsSlider.disabled = !useSteps;

    const useCfgScale = row.controls.useCfgScale.checked;
    row.controls.cfgScale.disabled = !useCfgScale;
    row.controls.cfgScaleSlider.disabled = !useCfgScale;

    row.controls.checkpointName.disabled = !row.controls.useCheckpoint.checked;
    row.controls.vaeName.disabled = !row.controls.useVae.checked;
    row.controls.samplerName.disabled = !row.controls.useSampler.checked;
    row.controls.schedulerName.disabled = !row.controls.useSampler.checked;
    row.controls.noiseMultiplier.disabled = !row.controls.useNoiseMultiplier.checked;
    row.controls.clipSkip.disabled = !row.controls.useClipSkip.checked;

    const customMode = row.controls.controlnetMode.value === "custom";
    row.controlnetCustomGrid.hidden = !customMode;
    row.controlnetModuleField.hidden = !customMode;
    row.controlnetModuleField.style.display = customMode ? "" : "none";
    row.controls.controlnetModel.disabled = !customMode;
    row.controls.controlnetModule.disabled = !customMode;
    row.controls.controlnetWeight.disabled = !customMode;
    row.controls.controlnetWeightSlider.disabled = !customMode;
    row.controls.controlnetGuidanceStart.disabled = !customMode;
    row.controls.controlnetGuidanceStartSlider.disabled = !customMode;
    row.controls.controlnetGuidanceEnd.disabled = !customMode;
    row.controls.controlnetGuidanceEndSlider.disabled = !customMode;
  }

  function bindChange(control, row = null) {
    control.addEventListener("input", () => {
      if (row) {
        syncUnitVisibility(row);
      }
      syncHiddenInput();
      syncBoundControls([control]);
    });
    control.addEventListener("change", () => {
      if (row) {
        syncUnitVisibility(row);
      }
      syncHiddenInput();
      syncBoundControls([control]);
    });
  }

  function activateTab(index) {
    rows.forEach((row, rowIndex) => {
      const active = rowIndex === index;
      row.tab.classList.toggle("is-active", active);
      row.tab.setAttribute("aria-selected", String(active));
      row.tab.tabIndex = active ? 0 : -1;
      row.panel.hidden = !active;
      row.panel.classList.toggle("is-active", active);
    });
  }

  UNIT_LABELS.forEach((label, index) => {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = "rookieui-shell__subtab rookieui-shell__adetailer-tab";
    tab.id = `${idPrefix}-tab-${index}`;
    tab.textContent = label;
    tab.setAttribute("role", "tab");
    tabs.appendChild(tab);

    const panel = document.createElement("div");
    panel.className = "rookieui-shell__controlnet-panel rookieui-shell__adetailer-panel";
    panel.id = `${idPrefix}-panel-${index}`;
    panel.hidden = true;
    panel.classList.toggle("is-active", index === 0);
    panelHost.appendChild(panel);

    const unitState = state.units[index];
    const controls = {
      enabled: createCheckbox(`${idPrefix}-unit-enabled-${index}`, unitState.enabled),
      detector: createSelect(`${idPrefix}-detector-${index}`, detectorOptions, unitState.detector),
      detectorClasses: createInput("text", `${idPrefix}-detector-classes-${index}`, unitState.detector_classes),
      prompt: createTextarea(`${idPrefix}-prompt-${index}`, unitState.prompt, 3, {
        className: "rookieui-shell__textarea rookieui-shell__textarea--prompt",
      }),
      negativePrompt: createTextarea(`${idPrefix}-negative-prompt-${index}`, unitState.negative_prompt, 2, {
        className: "rookieui-shell__textarea rookieui-shell__textarea--negative",
      }),
      confidence: createInput("number", `${idPrefix}-confidence-${index}`, String(unitState.confidence), {
        step: 0.01,
        min: 0,
        max: 1,
        inputMode: "decimal",
      }),
      confidenceSlider: createRangeInput(`${idPrefix}-confidence-slider-${index}`, String(unitState.confidence), {
        step: 0.01,
        min: 0,
        max: 1,
      }),
      maskFilterMethod: createSelect(`${idPrefix}-mask-filter-method-${index}`, maskFilterMethods, unitState.mask_filter_method),
      maskK: createInput("number", `${idPrefix}-mask-k-${index}`, String(unitState.mask_k), { step: 1, min: 0, max: 100 }),
      maskMinRatio: createInput("number", `${idPrefix}-mask-min-ratio-${index}`, String(unitState.mask_min_ratio), {
        step: 0.001,
        min: 0,
        max: 1,
        inputMode: "decimal",
      }),
      maskMaxRatio: createInput("number", `${idPrefix}-mask-max-ratio-${index}`, String(unitState.mask_max_ratio), {
        step: 0.001,
        min: 0,
        max: 1,
        inputMode: "decimal",
      }),
      xOffset: createInput("number", `${idPrefix}-x-offset-${index}`, String(unitState.x_offset), { step: 1, min: -256, max: 256 }),
      yOffset: createInput("number", `${idPrefix}-y-offset-${index}`, String(unitState.y_offset), { step: 1, min: -256, max: 256 }),
      dilateErode: createInput("number", `${idPrefix}-dilate-erode-${index}`, String(unitState.dilate_erode), {
        step: 1,
        min: -128,
        max: 128,
      }),
      maskMergeMode: createSelect(`${idPrefix}-mask-merge-mode-${index}`, maskMergeModes, unitState.mask_merge_mode),
      maskBlur: createInput("number", `${idPrefix}-mask-blur-${index}`, String(unitState.mask_blur), { step: 1, min: 0, max: 64 }),
      denoisingStrength: createInput(
        "number",
        `${idPrefix}-denoising-strength-${index}`,
        String(unitState.denoising_strength),
        { step: 0.01, min: 0, max: 1, inputMode: "decimal" },
      ),
      denoisingStrengthSlider: createRangeInput(
        `${idPrefix}-denoising-strength-slider-${index}`,
        String(unitState.denoising_strength),
        { step: 0.01, min: 0, max: 1 },
      ),
      inpaintOnlyMasked: createCheckbox(`${idPrefix}-inpaint-only-masked-${index}`, unitState.inpaint_only_masked),
      inpaintPadding: createInput("number", `${idPrefix}-inpaint-padding-${index}`, String(unitState.inpaint_padding), {
        step: 1,
        min: 0,
        max: 256,
      }),
      useInpaintSize: createCheckbox(`${idPrefix}-use-inpaint-size-${index}`, unitState.use_inpaint_size),
      inpaintWidth: createInput("number", `${idPrefix}-inpaint-width-${index}`, String(unitState.inpaint_width), {
        step: 8,
        min: 64,
        max: 2048,
      }),
      inpaintWidthSlider: createRangeInput(`${idPrefix}-inpaint-width-slider-${index}`, String(unitState.inpaint_width), {
        step: 8,
        min: 64,
        max: 2048,
      }),
      inpaintHeight: createInput("number", `${idPrefix}-inpaint-height-${index}`, String(unitState.inpaint_height), {
        step: 8,
        min: 64,
        max: 2048,
      }),
      inpaintHeightSlider: createRangeInput(`${idPrefix}-inpaint-height-slider-${index}`, String(unitState.inpaint_height), {
        step: 8,
        min: 64,
        max: 2048,
      }),
      useSteps: createCheckbox(`${idPrefix}-use-steps-${index}`, unitState.use_steps),
      steps: createInput("number", `${idPrefix}-steps-${index}`, String(unitState.steps), { step: 1, min: 1, max: 150 }),
      stepsSlider: createRangeInput(`${idPrefix}-steps-slider-${index}`, String(unitState.steps), { step: 1, min: 1, max: 150 }),
      useCfgScale: createCheckbox(`${idPrefix}-use-cfg-scale-${index}`, unitState.use_cfg_scale),
      cfgScale: createInput("number", `${idPrefix}-cfg-scale-${index}`, String(unitState.cfg_scale), {
        step: 0.01,
        min: 1,
        max: 30,
        inputMode: "decimal",
      }),
      cfgScaleSlider: createRangeInput(`${idPrefix}-cfg-scale-slider-${index}`, String(unitState.cfg_scale), {
        step: 0.1,
        min: 1,
        max: 30,
      }),
      useCheckpoint: createCheckbox(`${idPrefix}-use-checkpoint-${index}`, unitState.use_checkpoint),
      checkpointName: createSelect(`${idPrefix}-checkpoint-name-${index}`, checkpointChoices, unitState.checkpoint_name),
      useVae: createCheckbox(`${idPrefix}-use-vae-${index}`, unitState.use_vae),
      vaeName: createSelect(`${idPrefix}-vae-name-${index}`, vaeChoices, unitState.vae_name),
      useSampler: createCheckbox(`${idPrefix}-use-sampler-${index}`, unitState.use_sampler),
      samplerName: createSelect(`${idPrefix}-sampler-name-${index}`, samplerChoices, unitState.sampler_name),
      schedulerName: createSelect(`${idPrefix}-scheduler-name-${index}`, schedulerChoices, unitState.scheduler_name),
      useNoiseMultiplier: createCheckbox(`${idPrefix}-use-noise-multiplier-${index}`, unitState.use_noise_multiplier),
      noiseMultiplier: createInput("number", `${idPrefix}-noise-multiplier-${index}`, String(unitState.noise_multiplier), {
        step: 0.01,
        min: 0.5,
        max: 1.5,
        inputMode: "decimal",
      }),
      useClipSkip: createCheckbox(`${idPrefix}-use-clip-skip-${index}`, unitState.use_clip_skip),
      clipSkip: createInput("number", `${idPrefix}-clip-skip-${index}`, String(unitState.clip_skip), {
        step: 1,
        min: 1,
        max: 12,
      }),
      restoreFace: createCheckbox(`${idPrefix}-restore-face-${index}`, unitState.restore_face),
      controlnetMode: createSelect(`${idPrefix}-controlnet-mode-${index}`, controlnetModes, unitState.controlnet.mode),
      controlnetModel: createSelect(`${idPrefix}-controlnet-model-${index}`, controlnetModels, unitState.controlnet.model),
      controlnetModule: createSelect(`${idPrefix}-controlnet-module-${index}`, controlnetModules, unitState.controlnet.module),
      controlnetWeight: createInput("number", `${idPrefix}-controlnet-weight-${index}`, String(unitState.controlnet.weight), {
        step: 0.01,
        min: 0,
        max: 1,
        inputMode: "decimal",
      }),
      controlnetWeightSlider: createRangeInput(`${idPrefix}-controlnet-weight-slider-${index}`, String(unitState.controlnet.weight), {
        step: 0.01,
        min: 0,
        max: 1,
      }),
      controlnetGuidanceStart: createInput(
        "number",
        `${idPrefix}-controlnet-guidance-start-${index}`,
        String(unitState.controlnet.guidance_start),
        { step: 0.01, min: 0, max: 1, inputMode: "decimal" },
      ),
      controlnetGuidanceStartSlider: createRangeInput(
        `${idPrefix}-controlnet-guidance-start-slider-${index}`,
        String(unitState.controlnet.guidance_start),
        { step: 0.01, min: 0, max: 1 },
      ),
      controlnetGuidanceEnd: createInput(
        "number",
        `${idPrefix}-controlnet-guidance-end-${index}`,
        String(unitState.controlnet.guidance_end),
        { step: 0.01, min: 0, max: 1, inputMode: "decimal" },
      ),
      controlnetGuidanceEndSlider: createRangeInput(
        `${idPrefix}-controlnet-guidance-end-slider-${index}`,
        String(unitState.controlnet.guidance_end),
        { step: 0.01, min: 0, max: 1 },
      ),
    };

    bindSliderPair(controls.confidence, controls.confidenceSlider);
    bindSliderPair(controls.denoisingStrength, controls.denoisingStrengthSlider);
    bindSliderPair(controls.inpaintWidth, controls.inpaintWidthSlider);
    bindSliderPair(controls.inpaintHeight, controls.inpaintHeightSlider);
    bindSliderPair(controls.steps, controls.stepsSlider);
    bindSliderPair(controls.cfgScale, controls.cfgScaleSlider);
    bindSliderPair(controls.controlnetWeight, controls.controlnetWeightSlider);
    bindSliderPair(controls.controlnetGuidanceStart, controls.controlnetGuidanceStartSlider);
    bindSliderPair(controls.controlnetGuidanceEnd, controls.controlnetGuidanceEndSlider);
    controls.detectorClasses.placeholder = "YOLO-World classes, comma-separated";

    const enableField = createInlineCheckboxField(panel, "Enable this tab", controls.enabled);
    enableField.id = `${idPrefix}-unit-enabled-field-${index}`;
    createField(panel, "ADetailer detector", controls.detector);
    const detectorClassesField = createField(
      panel,
      "ADetailer detector classes (YOLO-World only)",
      controls.detectorClasses,
    );
    detectorClassesField.id = `${idPrefix}-detector-classes-field-${index}`;
    const promptField = createField(panel, "ad_prompt", controls.prompt);
    promptField.classList.add("rookieui-shell__field--full");
    const negativePromptField = createField(panel, "ad_negative_prompt", controls.negativePrompt);
    negativePromptField.classList.add("rookieui-shell__field--full");

    const detectionGrid = createSectionDetails(panel, "Detection", `${idPrefix}-detection-section-${index}`, appendTextElement);
    createSliderField(detectionGrid, "Detection confidence", controls.confidence, controls.confidenceSlider);
    createField(detectionGrid, "Mask filter method", controls.maskFilterMethod);
    createField(detectionGrid, "Top-k masks", controls.maskK);
    createField(detectionGrid, "Min mask ratio", controls.maskMinRatio);
    createField(detectionGrid, "Max mask ratio", controls.maskMaxRatio);

    const maskGrid = createSectionDetails(panel, "Mask Preprocessing", `${idPrefix}-mask-section-${index}`, appendTextElement);
    createField(maskGrid, "Mask x (\u2192) offset", controls.xOffset);
    createField(maskGrid, "Mask y (\u2191) offset", controls.yOffset);
    createField(maskGrid, "Mask erosion (-) / dilation (+)", controls.dilateErode);
    createField(maskGrid, "Mask merge mode", controls.maskMergeMode);

    const inpaintGrid = createSectionDetails(panel, "Inpainting", `${idPrefix}-inpaint-section-${index}`, appendTextElement);
    createField(inpaintGrid, "Inpaint mask blur", controls.maskBlur);
    createField(inpaintGrid, "Inpaint only masked padding", controls.inpaintPadding);
    createSliderField(inpaintGrid, "Inpaint denoising strength", controls.denoisingStrength, controls.denoisingStrengthSlider);
    createField(inpaintGrid, "ADetailer checkpoint", controls.checkpointName);
    createSliderField(inpaintGrid, "ADetailer width", controls.inpaintWidth, controls.inpaintWidthSlider);
    createField(inpaintGrid, "ADetailer VAE", controls.vaeName);
    createSliderField(inpaintGrid, "ADetailer height", controls.inpaintHeight, controls.inpaintHeightSlider);
    createField(inpaintGrid, "ADetailer sampler", controls.samplerName);
    createSliderField(inpaintGrid, "ADetailer steps", controls.steps, controls.stepsSlider);
    createField(inpaintGrid, "ADetailer scheduler", controls.schedulerName);
    createSliderField(inpaintGrid, "ADetailer CFG scale", controls.cfgScale, controls.cfgScaleSlider);
    createField(inpaintGrid, "Noise multiplier for img2img", controls.noiseMultiplier);
    const clipSkipField = createField(inpaintGrid, "ADetailer CLIP skip", controls.clipSkip);
    clipSkipField.classList.add("rookieui-shell__field--full");

    const inpaintToggleGrid = document.createElement("div");
    inpaintToggleGrid.className = "rookieui-shell__adetailer-toggle-grid";
    inpaintGrid.appendChild(inpaintToggleGrid);
    createInlineCheckboxField(inpaintToggleGrid, "Inpaint only masked", controls.inpaintOnlyMasked);
    createInlineCheckboxField(inpaintToggleGrid, "Use separate width/height", controls.useInpaintSize);
    createInlineCheckboxField(inpaintToggleGrid, "Use separate steps", controls.useSteps);
    createInlineCheckboxField(inpaintToggleGrid, "Use separate CFG scale", controls.useCfgScale);
    createInlineCheckboxField(inpaintToggleGrid, "Use separate checkpoint", controls.useCheckpoint);
    createInlineCheckboxField(inpaintToggleGrid, "Use separate VAE", controls.useVae);
    createInlineCheckboxField(inpaintToggleGrid, "Use separate sampler", controls.useSampler);
    createInlineCheckboxField(inpaintToggleGrid, "Use separate noise multiplier", controls.useNoiseMultiplier);
    createInlineCheckboxField(inpaintToggleGrid, "Use separate CLIP skip", controls.useClipSkip);
    createInlineCheckboxField(inpaintToggleGrid, "Restore faces after ADetailer", controls.restoreFace);

    const controlnetGrid = createSectionDetails(panel, "ControlNet", `${idPrefix}-controlnet-section-${index}`, appendTextElement);
    createField(controlnetGrid, "ControlNet mode", controls.controlnetMode);
    const controlnetModuleField = createField(controlnetGrid, "ControlNet module", controls.controlnetModule);
    const controlnetCustomGrid = document.createElement("div");
    controlnetCustomGrid.className = "rookieui-shell__grid rookieui-shell__grid--two-column rookieui-shell__adetailer-controlnet-grid";
    controlnetCustomGrid.style.gridColumn = "1 / -1";
    controlnetGrid.appendChild(controlnetCustomGrid);
    const controlnetModelField = createField(controlnetCustomGrid, "ControlNet model", controls.controlnetModel);
    controlnetModelField.classList.add("rookieui-shell__field--full");
    createSliderField(controlnetCustomGrid, "ControlNet weight", controls.controlnetWeight, controls.controlnetWeightSlider);
    createSliderField(controlnetCustomGrid, "ControlNet guidance start", controls.controlnetGuidanceStart, controls.controlnetGuidanceStartSlider);
    createSliderField(controlnetCustomGrid, "ControlNet guidance end", controls.controlnetGuidanceEnd, controls.controlnetGuidanceEndSlider);

    const row = { tab, panel, controls, detectorClassesField, controlnetCustomGrid, controlnetModuleField };
    Object.values(controls).forEach((control) => bindChange(control, row));
    syncUnitVisibility(row);
    rows.push(row);
    tab.addEventListener("click", () => activateTab(index));
  });

  bindChange(skipImg2Img);
  topEnabled.addEventListener("input", handleTopEnabledChange);
  topEnabled.addEventListener("change", handleTopEnabledChange);
  activateTab(0);
  syncHiddenInput();

  return {
    root,
    getValue() {
      return parseJsonObjectField(hiddenInput.value, buildDefaultPayload(catalog, surface));
    },
    setValue(nextPayload) {
      state = normalizePayload(nextPayload, catalog, surface);
      topEnabled.checked = state.enabled;
      skipImg2Img.checked = surface === "img2img" ? state.skip_img2img : false;
      rows.forEach((row, index) => {
        const unit = state.units[index];
        row.controls.enabled.checked = unit.enabled;
        row.controls.detector.value = unit.detector;
        row.controls.detectorClasses.value = unit.detector_classes;
        row.controls.prompt.value = unit.prompt;
        row.controls.negativePrompt.value = unit.negative_prompt;
        row.controls.confidence.value = String(unit.confidence);
        row.controls.confidenceSlider.value = String(unit.confidence);
        row.controls.maskFilterMethod.value = unit.mask_filter_method;
        row.controls.maskK.value = String(unit.mask_k);
        row.controls.maskMinRatio.value = String(unit.mask_min_ratio);
        row.controls.maskMaxRatio.value = String(unit.mask_max_ratio);
        row.controls.xOffset.value = String(unit.x_offset);
        row.controls.yOffset.value = String(unit.y_offset);
        row.controls.dilateErode.value = String(unit.dilate_erode);
        row.controls.maskMergeMode.value = unit.mask_merge_mode;
        row.controls.maskBlur.value = String(unit.mask_blur);
        row.controls.denoisingStrength.value = String(unit.denoising_strength);
        row.controls.denoisingStrengthSlider.value = String(unit.denoising_strength);
        row.controls.inpaintOnlyMasked.checked = unit.inpaint_only_masked;
        row.controls.inpaintPadding.value = String(unit.inpaint_padding);
        row.controls.useInpaintSize.checked = unit.use_inpaint_size;
        row.controls.inpaintWidth.value = String(unit.inpaint_width);
        row.controls.inpaintWidthSlider.value = String(unit.inpaint_width);
        row.controls.inpaintHeight.value = String(unit.inpaint_height);
        row.controls.inpaintHeightSlider.value = String(unit.inpaint_height);
        row.controls.useSteps.checked = unit.use_steps;
        row.controls.steps.value = String(unit.steps);
        row.controls.stepsSlider.value = String(unit.steps);
        row.controls.useCfgScale.checked = unit.use_cfg_scale;
        row.controls.cfgScale.value = String(unit.cfg_scale);
        row.controls.cfgScaleSlider.value = String(unit.cfg_scale);
        row.controls.useCheckpoint.checked = unit.use_checkpoint;
        row.controls.checkpointName.value = unit.checkpoint_name;
        row.controls.useVae.checked = unit.use_vae;
        row.controls.vaeName.value = unit.vae_name;
        row.controls.useSampler.checked = unit.use_sampler;
        row.controls.samplerName.value = unit.sampler_name;
        row.controls.schedulerName.value = unit.scheduler_name;
        row.controls.useNoiseMultiplier.checked = unit.use_noise_multiplier;
        row.controls.noiseMultiplier.value = String(unit.noise_multiplier);
        row.controls.useClipSkip.checked = unit.use_clip_skip;
        row.controls.clipSkip.value = String(unit.clip_skip);
        row.controls.restoreFace.checked = unit.restore_face;
        row.controls.controlnetMode.value = unit.controlnet.mode;
        row.controls.controlnetModel.value = unit.controlnet.model;
        row.controls.controlnetModule.value = unit.controlnet.module;
        row.controls.controlnetWeight.value = String(unit.controlnet.weight);
        row.controls.controlnetWeightSlider.value = String(unit.controlnet.weight);
        row.controls.controlnetGuidanceStart.value = String(unit.controlnet.guidance_start);
        row.controls.controlnetGuidanceStartSlider.value = String(unit.controlnet.guidance_start);
        row.controls.controlnetGuidanceEnd.value = String(unit.controlnet.guidance_end);
        row.controls.controlnetGuidanceEndSlider.value = String(unit.controlnet.guidance_end);
        syncUnitVisibility(row);
      });
      syncHiddenInput();
      syncBoundControls([topEnabled, skipImg2Img, ...rows.flatMap((row) => Object.values(row.controls))]);
    },
  };
}
