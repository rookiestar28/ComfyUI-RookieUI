import { createControlNetUnitEditor, createADetailerEditor } from "./rookieui_pane_deps.js";

export function buildTxt2ImgPane(parent, bootstrapState, formRegistry, context) {
  const {
    buildProfileLookup,
    buildPresetLookup,
    createGenerationRuntimeState,
    createSelect,
    createInput,
    createRangeInput,
    createTextarea,
    createCheckbox,
    createInlineCheckboxField,
    createField,
    createSliderField,
    createHiresFixSection,
    createSeedControlField,
    createPromptField,
    installExplicitFormSubmitShortcuts,
    createActionButton,
    createIconActionButton,
    createPreviewFullscreenViewer,
    buildQuicksettingCard,
    buildSelectionLibrary,
    buildSubtabShell,
    buildEmbeddingLibrary,
    buildLoraLibrary,
    appendTextElement,
    updateFormFromPreset,
    syncFamilyAwareModuleQuicksetting,
    syncClipSkipAvailability,
    transferPreviewToImg2Img,
    activateShellTab,
    submitTxt2Img,
    readFileAsDataUrl,
    bindSliderPair,
    installPaneStateLock,
    applyPayloadToElements,
    findPresetIdForProfile,
    setElementValue,
    syncBoundControls,
  } = context;
  const section = document.createElement("section");
  section.className = "rookieui-shell__integrated-pane";
  parent.appendChild(section);

  const form = document.createElement("form");
  form.className = "rookieui-shell__form rookieui-shell__integrated-form";
  form.id = "rookieui-txt2img-form";
  section.appendChild(form);
  installExplicitFormSubmitShortcuts(form);

  const profileLookup = buildProfileLookup(bootstrapState.capabilities);
  const presetLookup = buildPresetLookup(bootstrapState.presets?.presets ?? []);
  const profiles = bootstrapState.capabilities.parity?.profiles ?? [];
  const inventory = bootstrapState.models ?? {
    checkpoints: ["__host_default__"],
    vae: ["Automatic"],
    text_encoders: ["Automatic"],
    embeddings: [],
    loras: [],
    default_checkpoint: "__host_default__",
    default_vae: "Automatic",
    default_text_encoder: "Automatic",
  };
  const controlnetCatalog = bootstrapState.controlnetCatalog ?? {};
  const adetailerCatalog = bootstrapState.adetailerCatalog ?? {};
  const controlnetModelValues =
    Array.isArray(controlnetCatalog.model_list) && controlnetCatalog.model_list.length > 0
      ? controlnetCatalog.model_list
      : inventory.controlnet ?? [];
  const adetailerCheckpointChoices = Array.from(
    new Set(
      [
        ...(Array.isArray(adetailerCatalog.checkpoint_choices) ? adetailerCatalog.checkpoint_choices : []),
        ...(Array.isArray(inventory.checkpoints) ? inventory.checkpoints : []),
        ...(Array.isArray(inventory.diffusion_models) ? inventory.diffusion_models : []),
      ]
        .map((value) => String(value ?? "").trim())
        .filter(Boolean),
    ),
  );
  const mergedADetailerCatalog = {
    ...adetailerCatalog,
    // IMPORTANT: ADetailer-local ControlNet must fall back to the primary ControlNet catalog when the dedicated payload is stale or partial.
    controlnet_model_list:
      Array.isArray(adetailerCatalog.controlnet_model_list) && adetailerCatalog.controlnet_model_list.length > 0
        ? adetailerCatalog.controlnet_model_list
        : controlnetModelValues,
    controlnet_module_list:
      Array.isArray(adetailerCatalog.controlnet_module_list) && adetailerCatalog.controlnet_module_list.length > 0
        ? adetailerCatalog.controlnet_module_list
        : Array.isArray(controlnetCatalog.module_list) && controlnetCatalog.module_list.length > 0
          ? controlnetCatalog.module_list
          : ["none"],
    checkpoint_choices: adetailerCheckpointChoices,
  };
  const controlnetTypeCatalog =
    controlnetCatalog.control_types && typeof controlnetCatalog.control_types === "object"
      ? controlnetCatalog.control_types
      : {};
  const controlnetTypeOrder = Array.isArray(controlnetCatalog.control_type_order)
    ? controlnetCatalog.control_type_order
    : undefined;
  const presetOptions = (bootstrapState.presets?.presets ?? []).map((preset) => ({
    value: preset.id,
    label: preset.title,
  }));
  const allPresets = bootstrapState.presets?.presets ?? [];
  const initialPreset = presetOptions[0]?.value ?? "sd15";
  const initialProfile = profiles[0]?.id ?? "sd15";
  const dtypeProfiles = bootstrapState.compatibility?.dtype_profiles ?? [
    { id: "automatic", title: "Automatic", default: true },
  ];
  const samplerCatalog = bootstrapState.compatibility?.samplers ?? [
    { id: "euler_ancestral", title: "Euler a", default: true },
  ];
  const schedulerCatalog = bootstrapState.compatibility?.schedulers ?? [
    { id: "normal", title: "Normal", default: true },
  ];
  const initialLowBits = dtypeProfiles.find((entry) => entry.default)?.id ?? dtypeProfiles[0]?.id ?? "automatic";
  const initialSampler = samplerCatalog.find((entry) => entry.default)?.id ?? samplerCatalog[0]?.id ?? "euler_ancestral";
  const initialScheduler =
    schedulerCatalog.find((entry) => entry.default)?.id ?? schedulerCatalog[0]?.id ?? "normal";
  const runtimeState = createGenerationRuntimeState({
    previewPlaceholder: "Generation preview will update while the job is running.",
  });
  let txt2imgPreviewBox = null;
  let txt2imgControlNetEditor = null;
  let txt2imgADetailerEditor = null;

  const elements = {
    prompt: createTextarea("rookieui-prompt", "", 4, {
      className: "rookieui-shell__textarea rookieui-shell__textarea--prompt",
    }),
    negativePrompt: createTextarea("rookieui-negative-prompt", "", 3, {
      className: "rookieui-shell__textarea rookieui-shell__textarea--negative",
    }),
    preset: createSelect("rookieui-preset", presetOptions, initialPreset),
    profileState: createSelect(
      "rookieui-profile",
      profiles.map((profile) => ({ value: profile.id, label: profile.title })),
      initialProfile,
    ),
    checkpoint: createSelect(
      "rookieui-checkpoint",
      inventory.checkpoints.map((value) => ({ value, label: value })),
      inventory.default_checkpoint,
    ),
    vae: createSelect(
      "rookieui-vae",
      inventory.vae.map((value) => ({ value, label: value })),
      inventory.default_vae,
    ),
    textEncoder: createSelect(
      "rookieui-text-encoder",
      inventory.text_encoders.map((value) => ({ value, label: value })),
      inventory.default_text_encoder,
    ),
    lowBits: createSelect(
      "rookieui-low-bits",
      dtypeProfiles.map((profile) => ({ value: profile.id, label: profile.title })),
      initialLowBits,
    ),
    loraName: createInput("text", "rookieui-lora-name", ""),
    loraStrengthModel: createInput("number", "rookieui-lora-strength-model", "1", {
      step: 0.05,
      min: -4,
      max: 4,
      inputMode: "decimal",
    }),
    loraStrengthClip: createInput("number", "rookieui-lora-strength-clip", "1", {
      step: 0.05,
      min: -4,
      max: 4,
      inputMode: "decimal",
    }),
    width: createInput("number", "rookieui-width", "512", { step: 8, min: 64, max: 2048 }),
    widthSlider: createRangeInput("rookieui-width-slider", "512", { step: 8, min: 64, max: 2048 }),
    height: createInput("number", "rookieui-height", "512", { step: 8, min: 64, max: 2048 }),
    heightSlider: createRangeInput("rookieui-height-slider", "512", { step: 8, min: 64, max: 2048 }),
    steps: createInput("number", "rookieui-steps", "28", { step: 1, min: 1, max: 150 }),
    stepsSlider: createRangeInput("rookieui-steps-slider", "28", { step: 1, min: 1, max: 150 }),
    cfgScale: createInput("number", "rookieui-cfg-scale", "7", {
      step: 0.01,
      min: 1,
      max: 30,
      inputMode: "decimal",
    }),
    cfgScaleSlider: createRangeInput("rookieui-cfg-scale-slider", "7", { step: 0.1, min: 1, max: 30 }),
    sampler: createSelect(
      "rookieui-sampler",
      samplerCatalog.map((entry) => ({ value: entry.id, label: entry.title })),
      initialSampler,
    ),
    scheduler: createSelect(
      "rookieui-scheduler",
      schedulerCatalog.map((entry) => ({ value: entry.id, label: entry.title })),
      initialScheduler,
    ),
    seed: createInput("number", "rookieui-seed", "-1", { step: 1 }),
    seedExtra: createCheckbox("rookieui-seed-extra", false),
    batchSize: createInput("number", "rookieui-batch-size", "1", { step: 1, min: 1, max: 8 }),
    batchSizeSlider: createRangeInput("rookieui-batch-size-slider", "1", { step: 1, min: 1, max: 8 }),
    batchCount: createInput("number", "rookieui-batch-count", "1", { step: 1, min: 1, max: 32 }),
    batchCountSlider: createRangeInput("rookieui-batch-count-slider", "1", { step: 1, min: 1, max: 32 }),
    clipSkip: createInput("number", "rookieui-clip-skip", "1", { step: 1, min: 1, max: 12 }),
    clipSkipSlider: createRangeInput("rookieui-clip-skip-slider", "1", { step: 1, min: 1, max: 12 }),
    hiresEnabled: createCheckbox("rookieui-hires-enabled", false),
    hiresScale: createInput("number", "rookieui-hires-scale", "1.5", {
      step: 0.01,
      min: 1,
      max: 2.5,
      inputMode: "decimal",
    }),
    hiresSteps: createInput("number", "rookieui-hires-steps", "14", { step: 1, min: 1, max: 150 }),
    hiresDenoise: createInput("number", "rookieui-hires-denoise", "0.35", {
      step: 0.01,
      min: 0.1,
      max: 1,
      inputMode: "decimal",
    }),
    hiresScaleSlider: createRangeInput("rookieui-hires-scale-slider", "1.5", { step: 0.1, min: 1, max: 2.5 }),
    hiresStepsSlider: createRangeInput("rookieui-hires-steps-slider", "14", { step: 1, min: 1, max: 150 }),
    hiresDenoiseSlider: createRangeInput("rookieui-hires-denoise-slider", "0.35", {
      step: 0.05,
      min: 0.1,
      max: 1,
    }),
    hiresUpscaleMethod: createSelect(
      "rookieui-hires-upscale-method",
      [
        { value: "bislerp", label: "Bislerp" },
        { value: "bicubic", label: "Bicubic" },
        { value: "bilinear", label: "Bilinear" },
        { value: "nearest-exact", label: "Nearest Exact" },
        { value: "area", label: "Area" },
      ],
      "bislerp",
    ),
    adetailer: createInput("hidden", "rookieui-adetailer", "{}"),
    controlnetUnits: createInput("hidden", "rookieui-controlnet-units", "[]"),
  };
  form.appendChild(elements.adetailer);
  form.appendChild(elements.controlnetUnits);
  bindSliderPair(elements.width, elements.widthSlider);
  bindSliderPair(elements.height, elements.heightSlider);
  bindSliderPair(elements.steps, elements.stepsSlider);
  bindSliderPair(elements.cfgScale, elements.cfgScaleSlider);
  bindSliderPair(elements.batchSize, elements.batchSizeSlider);
  bindSliderPair(elements.batchCount, elements.batchCountSlider);
  bindSliderPair(elements.clipSkip, elements.clipSkipSlider);
  bindSliderPair(elements.hiresScale, elements.hiresScaleSlider);
  bindSliderPair(elements.hiresSteps, elements.hiresStepsSlider);
  bindSliderPair(elements.hiresDenoise, elements.hiresDenoiseSlider);
  elements.prompt.placeholder = "Prompt\n(Ctrl+Enter to Generate ; Alt+Enter to Skip ; Esc to Interrupt)";
  elements.negativePrompt.placeholder =
    "Negative Prompt\n(Ctrl+Enter to Generate ; Alt+Enter to Skip ; Esc to Interrupt)";

  const quicksettings = document.createElement("div");
  quicksettings.className = "rookieui-shell__quicksettings";
  quicksettings.id = "rookieui-txt2img-quicksettings";
  form.appendChild(quicksettings);
  buildQuicksettingCard(quicksettings, "UI Preset", elements.preset, "rookieui-preset-quicksetting");
  buildQuicksettingCard(quicksettings, "Checkpoint", elements.checkpoint, "rookieui-checkpoint-quicksetting");
  const modulesQuicksetting = buildQuicksettingCard(
    quicksettings,
    "VAE / Text Encoder",
    [elements.vae, elements.textEncoder],
    "rookieui-modules-quicksetting",
  );
  const modulesQuicksettingLabel = modulesQuicksetting.querySelector(".rookieui-shell__quicksetting-label");
  buildQuicksettingCard(
    quicksettings,
    "Diffusion in Low Bits",
    elements.lowBits,
    "rookieui-low-bits-quicksetting",
  );

  const promptBand = document.createElement("div");
  promptBand.className = "rookieui-shell__prompt-band";
  form.appendChild(promptBand);

  const promptStack = document.createElement("div");
  promptStack.className = "rookieui-shell__prompt-stack";
  promptBand.appendChild(promptStack);
  createPromptField(promptStack, "Prompt", elements.prompt, "rookieui-prompt-counter");
  createPromptField(promptStack, "Negative Prompt", elements.negativePrompt, "rookieui-negative-prompt-counter");

  const actionRail = document.createElement("div");
  actionRail.className = "rookieui-shell__action-rail";
  promptBand.appendChild(actionRail);

  const submitButton = document.createElement("button");
  submitButton.id = "rookieui-txt2img-submit";
  submitButton.className = "rookieui-shell__button rookieui-shell__button--hero";
  submitButton.type = "submit";
  submitButton.textContent = "Generate";
  actionRail.appendChild(submitButton);

  const actionRow = document.createElement("div");
  actionRow.className = "rookieui-shell__mini-actions";
  actionRail.appendChild(actionRow);

  const queueIconButton = createIconActionButton(
    "rookieui-txt2img-open-queue-icon",
    "pi-check-square",
    "Open Queue",
    "queue",
  );
  queueIconButton.addEventListener("click", () => {
    activateShellTab(formRegistry, "queue", statusNode, "Opened queue view");
  });
  actionRow.appendChild(queueIconButton);

  const clearButton = createIconActionButton("rookieui-txt2img-clear", "pi-trash", "Clear Prompt Fields", "danger");
  clearButton.addEventListener("click", () => {
    elements.prompt.value = "";
    elements.negativePrompt.value = "";
    syncBoundControls([elements.prompt, elements.negativePrompt]);
    statusNode.textContent = "Cleared prompt fields";
  });
  actionRow.appendChild(clearButton);

  const pngInfoButton = createIconActionButton("rookieui-txt2img-open-pnginfo", "pi-file", "Open PNG Info", "metadata");
  pngInfoButton.addEventListener("click", () => {
    activateShellTab(formRegistry, "pnginfo", statusNode, "Opened PNG Info");
  });
  actionRow.appendChild(pngInfoButton);

  const actionTargetRow = document.createElement("div");
  actionTargetRow.className = "rookieui-shell__action-target-row";
  actionRail.appendChild(actionTargetRow);

  const actionTarget = createSelect(
    "rookieui-txt2img-action-target",
    [
      { value: "queue", label: "Queue / History" },
      { value: "pnginfo", label: "PNG Info" },
      { value: "img2img", label: "Send to Img2Img" },
      { value: "extras", label: "Extras" },
    ],
    "queue",
  );
  actionTarget.classList.add("rookieui-shell__action-target");
  actionTargetRow.appendChild(actionTarget);

  const actionApplyButton = createIconActionButton(
    "rookieui-txt2img-apply-action-target",
    "pi-pencil",
    "Apply Action",
    "transfer",
  );
  actionApplyButton.addEventListener("click", () => {
    const actionLabels = {
      queue: "Opened queue view",
      pnginfo: "Opened PNG Info",
      img2img: "Sent preview image to Img2Img",
      extras: "Opened Extras",
    };
    if (actionTarget.value === "img2img") {
      void transferPreviewToImg2Img(formRegistry, runtimeState, statusNode, txt2imgPreviewBox);
      return;
    }
    activateShellTab(formRegistry, actionTarget.value, statusNode, actionLabels[actionTarget.value] ?? "Action applied");
  });
  actionTargetRow.appendChild(actionApplyButton);

  const statusNode = document.createElement("p");
  statusNode.id = "rookieui-txt2img-status";
  statusNode.className = "rookieui-shell__status rookieui-shell__status--inline";
  statusNode.textContent = "Idle";
  actionRail.appendChild(statusNode);

  updateFormFromPreset(presetLookup, initialPreset, elements, profileLookup, bootstrapState.models);
  syncFamilyAwareModuleQuicksetting(
    profileLookup,
    elements.profileState.value,
    modulesQuicksetting,
    modulesQuicksettingLabel,
    elements.textEncoder,
  );
  elements.preset.addEventListener("change", () => {
    updateFormFromPreset(presetLookup, elements.preset.value, elements, profileLookup, bootstrapState.models);
    syncFamilyAwareModuleQuicksetting(
      profileLookup,
      elements.profileState.value,
      modulesQuicksetting,
      modulesQuicksettingLabel,
      elements.textEncoder,
    );
  });

  const subtabHost = document.createElement("div");
  subtabHost.className = "rookieui-shell__workspace-frame";
  form.appendChild(subtabHost);

  buildSubtabShell(subtabHost, "rookieui-txt2img-workspace", [
    {
      id: "generation",
      label: "Generation",
      render: (pane) => {
        const workspace = document.createElement("div");
        workspace.className = "rookieui-shell__workspace-grid";
        pane.appendChild(workspace);

        const leftColumn = document.createElement("div");
        leftColumn.className = "rookieui-shell__workspace-column";
        workspace.appendChild(leftColumn);

        const samplingSection = document.createElement("section");
        samplingSection.className = "rookieui-shell__section rookieui-shell__section--soft";
        samplingSection.id = "rookieui-txt2img-generation-section";
        leftColumn.appendChild(samplingSection);
        appendTextElement(samplingSection, "h4", "rookieui-shell__section-title", "Generation");

        const samplingGrid = document.createElement("div");
        samplingGrid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
        samplingSection.appendChild(samplingGrid);
        createField(samplingGrid, "Sampling Method", elements.sampler);
        createField(samplingGrid, "Schedule Type", elements.scheduler);
        createSliderField(samplingGrid, "Sampling Steps", elements.steps, elements.stepsSlider, "rookieui-steps-field");
        createSliderField(samplingGrid, "CFG Scale", elements.cfgScale, elements.cfgScaleSlider, "rookieui-cfg-scale-field");
        createSliderField(samplingGrid, "Width", elements.width, elements.widthSlider, "rookieui-width-field");
        createSliderField(samplingGrid, "Height", elements.height, elements.heightSlider, "rookieui-height-field");
        createSliderField(samplingGrid, "Batch Count", elements.batchCount, elements.batchCountSlider, "rookieui-batch-count-field");
        createSliderField(samplingGrid, "Batch Size", elements.batchSize, elements.batchSizeSlider, "rookieui-batch-size-field");
        createSliderField(samplingGrid, "Clip Skip", elements.clipSkip, elements.clipSkipSlider, "rookieui-clip-skip-field");
        createSeedControlField(samplingGrid, "Seed", elements.seed, elements.seedExtra, "rookieui-seed-field");

        const advancedGrid = createHiresFixSection(
          samplingSection,
          "rookieui-advanced-controls",
          elements.hiresEnabled,
        );
        // IMPORTANT: keep Hires.fix border/checkbox chrome while integrating into Generation section.
        advancedGrid.parentElement?.classList.add("rookieui-shell__hires--integrated");
        createSliderField(advancedGrid, "Hires Scale", elements.hiresScale, elements.hiresScaleSlider, "rookieui-hires-scale-field");
        createSliderField(advancedGrid, "Hires Steps", elements.hiresSteps, elements.hiresStepsSlider, "rookieui-hires-steps-field");
        createSliderField(advancedGrid, "Hires Denoise", elements.hiresDenoise, elements.hiresDenoiseSlider, "rookieui-hires-denoise-field");
        createField(advancedGrid, "Upscale Method", elements.hiresUpscaleMethod);

        txt2imgControlNetEditor = createControlNetUnitEditor({
          idPrefix: "rookieui-txt2img-controlnet",
          parent: samplingSection,
          hiddenInput: elements.controlnetUnits,
          modelOptions: controlnetModelValues.map((value) => ({ value, label: value })),
          controlTypeOrder: controlnetTypeOrder,
          createInput,
          createRangeInput,
          createSelect,
          createCheckbox,
          createField,
          createSliderField,
          appendTextElement,
          readFileAsDataUrl,
          syncBoundControls,
          onStatusMessage: (message) => {
            statusNode.textContent = message;
          },
        });
        txt2imgControlNetEditor.setControlTypeCatalog(controlnetTypeCatalog);

        txt2imgADetailerEditor = createADetailerEditor({
          idPrefix: "rookieui-txt2img-adetailer",
          parent: samplingSection,
          hiddenInput: elements.adetailer,
          catalog: mergedADetailerCatalog,
          surface: "txt2img",
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
        });

        const rightColumn = document.createElement("div");
        rightColumn.className = "rookieui-shell__workspace-column";
        workspace.appendChild(rightColumn);

        const previewSection = document.createElement("section");
        previewSection.className = "rookieui-shell__section rookieui-shell__section--soft";
        rightColumn.appendChild(previewSection);
        appendTextElement(previewSection, "h4", "rookieui-shell__section-title", "Preview");

        const previewBox = document.createElement("div");
        previewBox.className = "rookieui-shell__preview-box";
        previewBox.id = "rookieui-txt2img-preview";
        previewSection.appendChild(previewBox);
        txt2imgPreviewBox = previewBox;
        appendTextElement(
          previewBox,
          "span",
          "rookieui-shell__preview-placeholder",
          runtimeState.previewPlaceholder,
        );

        const previewToolbar = document.createElement("div");
        previewToolbar.className = "rookieui-shell__preview-toolbar";
        previewSection.appendChild(previewToolbar);

        createPreviewFullscreenViewer({
          idPrefix: "rookieui-txt2img",
          previewBox,
          previewToolbar,
          createIconActionButton,
          statusNode,
          labelText: "Preview",
        });

        const previewActions = [
          {
            id: "rookieui-txt2img-preview-queue",
            iconClass: "pi-folder-open",
            label: "Queue History",
            tabId: "queue",
            message: "Opened queue history",
            tone: "queue",
          },
          {
            id: "rookieui-txt2img-preview-pnginfo",
            iconClass: "pi-file",
            label: "PNG Info",
            tabId: "pnginfo",
            message: "Opened PNG Info",
            tone: "metadata",
          },
          {
            id: "rookieui-txt2img-preview-img2img",
            iconClass: "pi-image",
            label: "Send to Img2Img",
            tabId: "img2img",
            message: "Opened Img2Img",
            tone: "transfer",
          },
          {
            id: "rookieui-txt2img-preview-extras",
            iconClass: "pi-star",
            label: "Extras",
            tabId: "extras",
            message: "Opened Extras",
            tone: "extras",
          },
          {
            id: "rookieui-txt2img-preview-return",
            iconClass: "pi-sliders-h",
            label: "Generation Controls",
            tabId: "txt2img",
            message: "Returned to txt2img controls",
            tone: "neutral",
          },
          {
            id: "rookieui-txt2img-preview-history",
            iconClass: "pi-images",
            label: "History",
            tabId: "queue",
            message: "Opened queue history",
            tone: "queue",
          },
        ];

        previewActions.forEach((action) => {
          const button = createIconActionButton(action.id, action.iconClass, action.label, action.tone);
          button.addEventListener("click", async () => {
            if (action.id === "rookieui-txt2img-preview-img2img") {
              await transferPreviewToImg2Img(formRegistry, runtimeState, statusNode, previewBox);
              return;
            }
            activateShellTab(formRegistry, action.tabId, statusNode, action.message);
          });
          previewToolbar.appendChild(button);
        });
      },
    },
    {
      id: "textual-inversion",
      label: "Textual Inversion",
      render: (pane) => {
        const infoSection = document.createElement("section");
        infoSection.className = "rookieui-shell__section rookieui-shell__section--soft";
        infoSection.id = "rookieui-txt2img-textual-inversion-pane";
        pane.appendChild(infoSection);
        appendTextElement(infoSection, "h4", "rookieui-shell__section-title", "Textual Inversion");
        appendTextElement(
          infoSection,
          "p",
          "rookieui-shell__status",
          "Click an embedding to inject a Comfy-compatible embedding token into the prompt.",
        );
        buildEmbeddingLibrary(
          pane,
          "Available Embeddings",
          inventory.embeddings ?? [],
          elements.prompt,
          "rookieui-txt2img-embedding-item",
        );
      },
    },
    {
      id: "checkpoints",
      label: "Checkpoints",
      render: (pane) =>
        buildSelectionLibrary(
          pane,
          "Available Checkpoints",
          inventory.checkpoints ?? [],
          () => elements.checkpoint.value,
          (value) => {
            elements.checkpoint.value = value;
          },
          "rookieui-txt2img-checkpoint-item",
        ),
    },
    {
      id: "lora",
      label: "Lora",
      render: (pane) => {
        const loraSection = document.createElement("section");
        loraSection.className = "rookieui-shell__section rookieui-shell__section--soft";
        loraSection.id = "rookieui-txt2img-lora-pane";
        pane.appendChild(loraSection);
        appendTextElement(loraSection, "h4", "rookieui-shell__section-title", "LoRA");
        appendTextElement(
          loraSection,
          "p",
          "rookieui-shell__status",
          "Select one host LoRA to inject through a workflow LoraLoader seam during generation.",
        );

        const loraGrid = document.createElement("div");
        loraGrid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
        loraSection.appendChild(loraGrid);
        createField(loraGrid, "Model Strength", elements.loraStrengthModel);
        createField(loraGrid, "CLIP Strength", elements.loraStrengthClip);

        const loraStatus = document.createElement("p");
        loraStatus.className = "rookieui-shell__status";
        loraStatus.id = "rookieui-txt2img-lora-status";
        loraSection.appendChild(loraStatus);

        const clearButton = createActionButton("rookieui-txt2img-clear-lora", "Clear LoRA");
        clearButton.addEventListener("click", () => {
          elements.loraName.value = "";
          loraStatus.textContent = "No LoRA selected. Generation will use the base checkpoint only.";
          pane.querySelectorAll(".rookieui-shell__library-item").forEach((node) => {
            node.dataset.active = "false";
          });
        });
        loraSection.appendChild(clearButton);

        buildLoraLibrary(
          pane,
          "Available LoRAs",
          inventory.loras ?? [],
          elements,
          "rookieui-txt2img-lora-item",
          loraStatus,
        );
      },
    },
  ]);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitTxt2Img(bootstrapState, elements, statusNode, runtimeState, txt2imgPreviewBox);
  });

  const txt2imgStateLock = installPaneStateLock(formRegistry, "txt2img", elements, () => {
    // IMPORTANT: tab restore must re-apply Clip Skip editability; otherwise old profile lock state can persist and look frozen.
    syncClipSkipAvailability(profileLookup, elements.profileState.value, elements.clipSkip, elements.clipSkipSlider);
    syncFamilyAwareModuleQuicksetting(
      profileLookup,
      elements.profileState.value,
      modulesQuicksetting,
      modulesQuicksettingLabel,
      elements.textEncoder,
    );
  });

  formRegistry.txt2img = {
    applyPayload(payload) {
      applyPayloadToElements(elements, payload, {
        prompt: "prompt",
        negative_prompt: "negativePrompt",
        profile: "profileState",
        checkpoint_name: "checkpoint",
        vae_name: "vae",
        text_encoder_name: "textEncoder",
        dtype_profile: "lowBits",
        width: "width",
        height: "height",
        steps: "steps",
        cfg_scale: "cfgScale",
        sampler_name: "sampler",
        scheduler_name: "scheduler",
        seed: "seed",
        seed_extra: "seedExtra",
        batch_count: "batchCount",
        batch_size: "batchSize",
        clip_skip: "clipSkip",
        hires_enabled: "hiresEnabled",
        hires_scale: "hiresScale",
        hires_steps: "hiresSteps",
        hires_denoise: "hiresDenoise",
        hires_upscale_method: "hiresUpscaleMethod",
        lora_name: "loraName",
        lora_strength_model: "loraStrengthModel",
        lora_strength_clip: "loraStrengthClip",
      });
      if (Array.isArray(payload.controlnet_units)) {
        elements.controlnetUnits.value = JSON.stringify(payload.controlnet_units);
        txt2imgControlNetEditor?.setUnits(payload.controlnet_units);
      }
      if (payload.adetailer && typeof payload.adetailer === "object") {
        elements.adetailer.value = JSON.stringify(payload.adetailer);
        txt2imgADetailerEditor?.setValue(payload.adetailer);
      }
      const resolvedPresetId = findPresetIdForProfile(allPresets, elements.profileState.value);
      if (resolvedPresetId) {
        setElementValue(elements.preset, resolvedPresetId);
      }
      // IMPORTANT: PNG Info / history apply may change profile; always re-sync Clip Skip editability after payload apply.
      syncClipSkipAvailability(profileLookup, elements.profileState.value, elements.clipSkip, elements.clipSkipSlider);
      syncFamilyAwareModuleQuicksetting(
        profileLookup,
        elements.profileState.value,
        modulesQuicksetting,
        modulesQuicksettingLabel,
        elements.textEncoder,
      );
      syncBoundControls(Object.values(elements));
      txt2imgStateLock.capture();
    },
  };

  return {
    onActivate: txt2imgStateLock.restore,
    onDeactivate: txt2imgStateLock.capture,
  };
}
