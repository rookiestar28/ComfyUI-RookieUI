export function buildExtrasPane(parent, bootstrapState, formRegistry, context) {
  const {
    appendTextElement,
    createSelect,
    createInput,
    createCheckbox,
    createInlineCheckboxField,
    createHiresFixSection,
    createField,
    createList,
    createIconActionButton,
    syncExtrasMode,
    loadExtrasFiles,
    updateExtrasPreview,
    submitExtras,
    populateList,
    applyCrossPanePayload,
    activateShellTab,
    installPaneStateLock,
    emitFrontendDebugWarning,
  } = context;
  const inventory = bootstrapState.models ?? {};
  const section = document.createElement("section");
  section.className = "rookieui-shell__section";
  parent.appendChild(section);

  const workspace = document.createElement("div");
  workspace.className = "rookieui-shell__workspace-grid";
  section.appendChild(workspace);

  const leftColumn = document.createElement("div");
  leftColumn.className = "rookieui-shell__workspace-column";
  workspace.appendChild(leftColumn);

  const rightColumn = document.createElement("div");
  rightColumn.className = "rookieui-shell__workspace-column";
  workspace.appendChild(rightColumn);

  const state = {
    mode: "single_image",
    singleImage: null,
    batchImages: [],
    lastResult: null,
  };

  const modeTabs = document.createElement("div");
  modeTabs.className = "rookieui-shell__subtabs";
  leftColumn.appendChild(modeTabs);

  const singleButton = document.createElement("button");
  singleButton.type = "button";
  singleButton.id = "rookieui-extras-mode-single";
  singleButton.className = "rookieui-shell__subtab";
  singleButton.textContent = "Single Image";
  modeTabs.appendChild(singleButton);

  const batchButton = document.createElement("button");
  batchButton.type = "button";
  batchButton.id = "rookieui-extras-mode-batch";
  batchButton.className = "rookieui-shell__subtab";
  batchButton.textContent = "Batch Process";
  modeTabs.appendChild(batchButton);

  const singlePane = document.createElement("section");
  singlePane.className = "rookieui-shell__section rookieui-shell__section--soft rookieui-shell__subpane";
  singlePane.id = "rookieui-extras-single-pane";
  leftColumn.appendChild(singlePane);
  appendTextElement(singlePane, "h4", "rookieui-shell__section-title", "Single Image");

  const singleDropzone = document.createElement("label");
  singleDropzone.className = "rookieui-shell__dropzone";
  singleDropzone.id = "rookieui-extras-single-dropzone";
  singlePane.appendChild(singleDropzone);
  appendTextElement(singleDropzone, "span", "rookieui-shell__dropzone-icon", "⇪");
  appendTextElement(singleDropzone, "span", "rookieui-shell__dropzone-text", "Drop a single image here or browse.");

  const singleFileInput = createInput("file", "rookieui-extras-single-file", "", {
    className: "rookieui-shell__file-input",
  });
  singleFileInput.accept = "image/png,image/webp,image/jpeg";
  singleDropzone.appendChild(singleFileInput);

  const singleStatus = appendTextElement(
    singlePane,
    "p",
    "rookieui-shell__status",
    "No image selected.",
    "rookieui-extras-single-status",
  );

  const batchPane = document.createElement("section");
  batchPane.className = "rookieui-shell__section rookieui-shell__section--soft rookieui-shell__subpane";
  batchPane.id = "rookieui-extras-batch-pane";
  leftColumn.appendChild(batchPane);
  appendTextElement(batchPane, "h4", "rookieui-shell__section-title", "Batch Process");

  const batchDropzone = document.createElement("label");
  batchDropzone.className = "rookieui-shell__dropzone";
  batchDropzone.id = "rookieui-extras-batch-dropzone";
  batchPane.appendChild(batchDropzone);
  appendTextElement(batchDropzone, "span", "rookieui-shell__dropzone-icon", "⇪");
  appendTextElement(batchDropzone, "span", "rookieui-shell__dropzone-text", "Drop multiple images here or browse.");

  const batchFileInput = createInput("file", "rookieui-extras-batch-file", "", {
    className: "rookieui-shell__file-input",
  });
  batchFileInput.accept = "image/png,image/webp,image/jpeg";
  batchFileInput.multiple = true;
  batchDropzone.appendChild(batchFileInput);

  const batchList = createList("rookieui-extras-batch-list");
  batchPane.appendChild(batchList);
  const batchStatus = appendTextElement(
    batchPane,
    "p",
    "rookieui-shell__status",
    "No batch images selected.",
    "rookieui-extras-batch-status",
  );

  const optionsSection = document.createElement("section");
  optionsSection.className = "rookieui-shell__section rookieui-shell__section--soft";
  leftColumn.appendChild(optionsSection);
  appendTextElement(optionsSection, "h4", "rookieui-shell__section-title", "Postprocessing");

  const optionsGrid = document.createElement("div");
  optionsGrid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
  optionsSection.appendChild(optionsGrid);

  const elements = {
    hiresEnabled: createCheckbox("rookieui-extras-hires-enabled", true),
    scaleMode: createSelect(
      "rookieui-extras-scale-mode",
      [
        { value: "scale_by", label: "Scale by" },
        { value: "scale_to", label: "Scale to" },
      ],
      "scale_by",
    ),
    scaleBy: createInput("number", "rookieui-extras-scale-by", "2", { step: 0.1, min: 1, max: 8 }),
    targetWidth: createInput("number", "rookieui-extras-target-width", "1024", { step: 8, min: 64, max: 4096 }),
    targetHeight: createInput("number", "rookieui-extras-target-height", "1024", { step: 8, min: 64, max: 4096 }),
    upscaler1: createSelect(
      "rookieui-extras-upscaler-1",
      [{ value: "None", label: "None" }, ...(inventory.upscale_models ?? []).map((value) => ({ value, label: value }))],
      "None",
    ),
    upscaler2: createSelect(
      "rookieui-extras-upscaler-2",
      [{ value: "None", label: "None" }, ...(inventory.upscale_models ?? []).map((value) => ({ value, label: value }))],
      "None",
    ),
    upscaler2Visibility: createInput("number", "rookieui-extras-upscaler-2-visibility", "0", {
      step: 0.05,
      min: 0,
      max: 1,
    }),
    colorCorrection: createCheckbox("rookieui-extras-color-correction", false),
    faceRestoration: createSelect(
      "rookieui-extras-face-restoration",
      [
        { value: "none", label: "None" },
        { value: "codeformer", label: "CodeFormer" },
        { value: "gfpgan", label: "GFPGAN" },
      ],
      "none",
    ),
    codeformerWeight: createInput("number", "rookieui-extras-codeformer-weight", "0.5", {
      step: 0.05,
      min: 0,
      max: 1,
    }),
  };

  // IMPORTANT: keep Extras Hires.fix controls wired to existing upscale fields so this section executes real postprocessing behavior.
  const extrasHiresGrid = createHiresFixSection(optionsSection, "rookieui-extras-hires-controls", elements.hiresEnabled);
  extrasHiresGrid.parentElement?.classList.add("rookieui-shell__hires--integrated");
  createField(extrasHiresGrid, "Scale Mode", elements.scaleMode);
  createField(extrasHiresGrid, "Scale By", elements.scaleBy);
  createField(extrasHiresGrid, "Target Width", elements.targetWidth);
  createField(extrasHiresGrid, "Target Height", elements.targetHeight);
  createField(extrasHiresGrid, "Upscaler 1", elements.upscaler1);
  createField(extrasHiresGrid, "Upscaler 2", elements.upscaler2);
  createField(extrasHiresGrid, "Upscaler 2 visibility", elements.upscaler2Visibility);
  createInlineCheckboxField(optionsGrid, "Color Correction", elements.colorCorrection);
  createField(optionsGrid, "Face Restoration", elements.faceRestoration);
  createField(optionsGrid, "CodeFormer Weight", elements.codeformerWeight);

  const actionRail = document.createElement("div");
  actionRail.className = "rookieui-shell__action-rail rookieui-shell__action-rail--extras";
  rightColumn.appendChild(actionRail);

  let extrasRailAlignRafToken = null;
  const resolveActiveExtrasPane = () => (state.mode === "batch_process" ? batchPane : singlePane);
  const syncExtrasActionRailAlignment = () => {
    const ownerPane = section.closest(".rookieui-shell__pane");
    if (ownerPane?.hidden) {
      return;
    }
    const activePaneRect = resolveActiveExtrasPane().getBoundingClientRect();
    const actionRailRect = actionRail.getBoundingClientRect();
    const currentMarginTop = Number.parseFloat(globalThis.getComputedStyle?.(actionRail)?.marginTop ?? "0") || 0;
    const marginTop = Math.max(0, Math.round(currentMarginTop + (activePaneRect.top - actionRailRect.top)));
    // CRITICAL: keep Extras rail alignment dynamic; fixed offsets drift across Linux/Windows font metrics and cause flaky E2E top-delta checks.
    actionRail.style.marginTop = `${marginTop}px`;
  };
  const queueExtrasActionRailAlignment = () => {
    if (extrasRailAlignRafToken !== null && typeof globalThis.cancelAnimationFrame === "function") {
      globalThis.cancelAnimationFrame(extrasRailAlignRafToken);
    }
    if (typeof globalThis.requestAnimationFrame === "function") {
      extrasRailAlignRafToken = globalThis.requestAnimationFrame(() => {
        extrasRailAlignRafToken = null;
        syncExtrasActionRailAlignment();
      });
      return;
    }
    syncExtrasActionRailAlignment();
  };

  const submitButton = document.createElement("button");
  submitButton.id = "rookieui-extras-submit";
  submitButton.className = "rookieui-shell__button rookieui-shell__button--hero";
  submitButton.type = "button";
  submitButton.textContent = "Generate";
  actionRail.appendChild(submitButton);

  const generateActionRow = document.createElement("div");
  generateActionRow.className = "rookieui-shell__mini-actions";
  actionRail.appendChild(generateActionRow);
  // IMPORTANT: keep quick actions directly below Extras Generate; removing this row hides expected A1111-style emoji tools.
  const generateOpenQueue = createIconActionButton(
    "rookieui-extras-generate-open-queue",
    "pi-folder-open",
    "Queue History",
    "queue",
  );
  generateOpenQueue.addEventListener("click", () => {
    activateShellTab(formRegistry, "queue", statusNode, "Opened queue history");
  });
  generateActionRow.appendChild(generateOpenQueue);
  const generateOpenPngInfo = createIconActionButton(
    "rookieui-extras-generate-open-pnginfo",
    "pi-file",
    "PNG Info",
    "metadata",
  );
  generateOpenPngInfo.addEventListener("click", () => {
    activateShellTab(formRegistry, "pnginfo", statusNode, "Opened PNG Info");
  });
  generateActionRow.appendChild(generateOpenPngInfo);

  const statusNode = appendTextElement(
    actionRail,
    "p",
    "rookieui-shell__status rookieui-shell__status--inline",
    "Idle",
    "rookieui-extras-status",
  );

  const previewSection = document.createElement("section");
  previewSection.className = "rookieui-shell__section rookieui-shell__section--soft";
  rightColumn.appendChild(previewSection);
  appendTextElement(previewSection, "h4", "rookieui-shell__section-title", "Preview");

  const previewBox = document.createElement("div");
  previewBox.className = "rookieui-shell__preview-box rookieui-shell__preview-box--compact";
  previewBox.id = "rookieui-extras-preview";
  previewSection.appendChild(previewBox);
  updateExtrasPreview(previewBox, "", "Extras preview will appear here after processing.");

  const previewToolbar = document.createElement("div");
  previewToolbar.className = "rookieui-shell__preview-toolbar";
  previewSection.appendChild(previewToolbar);

  const sendToImg2Img = createIconActionButton(
    "rookieui-extras-preview-img2img",
    "pi-image",
    "Send to Img2Img",
    "transfer",
  );
  sendToImg2Img.addEventListener("click", () => {
    const asset = state.lastResult?.preview_asset;
    if (!asset) {
      statusNode.textContent = "Run Extras before sending an output to img2img.";
      return;
    }
    const applied = applyCrossPanePayload(formRegistry, "img2img", {
      image_asset: asset,
      mode: "img2img",
      mask_asset: "",
    });
    statusNode.textContent = applied ? `Applied ${asset} to img2img` : "Img2Img form is unavailable.";
  });
  previewToolbar.appendChild(sendToImg2Img);

  const openQueue = createIconActionButton(
    "rookieui-extras-open-queue",
    "pi-folder-open",
    "Queue History",
    "queue",
  );
  openQueue.addEventListener("click", () => {
    activateShellTab(formRegistry, "queue", statusNode, "Opened queue history");
  });
  previewToolbar.appendChild(openQueue);

  const openPngInfo = createIconActionButton("rookieui-extras-open-pnginfo", "pi-file", "PNG Info", "metadata");
  openPngInfo.addEventListener("click", () => {
    activateShellTab(formRegistry, "pnginfo", statusNode, "Opened PNG Info");
  });
  previewToolbar.appendChild(openPngInfo);

  const setSingleFiles = async (files) => {
    const [entry] = await loadExtrasFiles(files);
    state.singleImage = entry ?? null;
    singleStatus.textContent = entry ? `Loaded ${entry.name}` : "No image selected.";
    updateExtrasPreview(
      previewBox,
      entry?.dataUrl ?? state.lastResult?.preview_data_url ?? "",
      "Extras preview will appear here after processing.",
    );
  };

  const setBatchFiles = async (files) => {
    state.batchImages = await loadExtrasFiles(files);
    populateList(batchList, state.batchImages.map((entry) => entry.name));
    batchStatus.textContent = state.batchImages.length
      ? `Loaded ${state.batchImages.length} image(s)`
      : "No batch images selected.";
  };

  singleFileInput.addEventListener("change", async () => {
    try {
      await setSingleFiles(singleFileInput.files);
    } catch (_error) {
      emitFrontendDebugWarning("shell.extras_upload", "Extras single-image input handling failed.", _error);
      statusNode.textContent = "Failed to load the selected Extras image.";
    }
  });
  batchFileInput.addEventListener("change", async () => {
    try {
      await setBatchFiles(batchFileInput.files);
    } catch (_error) {
      emitFrontendDebugWarning("shell.extras_upload", "Extras batch-image input handling failed.", _error);
      statusNode.textContent = "Failed to load the selected batch images.";
    }
  });

  [singleDropzone, batchDropzone].forEach((dropzone) => {
    dropzone.addEventListener("dragover", (event) => {
      event.preventDefault();
      dropzone.dataset.dragging = "true";
    });
    dropzone.addEventListener("dragleave", () => {
      dropzone.dataset.dragging = "false";
    });
  });
  singleDropzone.addEventListener("drop", async (event) => {
    event.preventDefault();
    singleDropzone.dataset.dragging = "false";
    try {
      await setSingleFiles(event.dataTransfer?.files);
    } catch (_error) {
      emitFrontendDebugWarning("shell.extras_upload", "Extras single-image drop handling failed.", _error);
      statusNode.textContent = "Failed to load the dropped Extras image.";
    }
  });
  batchDropzone.addEventListener("drop", async (event) => {
    event.preventDefault();
    batchDropzone.dataset.dragging = "false";
    try {
      await setBatchFiles(event.dataTransfer?.files);
    } catch (_error) {
      emitFrontendDebugWarning("shell.extras_upload", "Extras batch-image drop handling failed.", _error);
      statusNode.textContent = "Failed to load the dropped batch images.";
    }
  });

  singleButton.addEventListener("click", () => {
    state.mode = "single_image";
    syncExtrasMode([singleButton, batchButton], [singlePane, batchPane], state.mode);
    syncExtrasActionRailAlignment();
    queueExtrasActionRailAlignment();
  });
  batchButton.addEventListener("click", () => {
    state.mode = "batch_process";
    syncExtrasMode([singleButton, batchButton], [singlePane, batchPane], state.mode);
    syncExtrasActionRailAlignment();
    queueExtrasActionRailAlignment();
  });
  syncExtrasMode([singleButton, batchButton], [singlePane, batchPane], state.mode);
  queueExtrasActionRailAlignment();

  let extrasAlignObserver = null;
  if (typeof ResizeObserver === "function") {
    extrasAlignObserver = new ResizeObserver(() => {
      queueExtrasActionRailAlignment();
    });
    extrasAlignObserver.observe(modeTabs);
    extrasAlignObserver.observe(singlePane);
    extrasAlignObserver.observe(batchPane);
    section.__extrasAlignObserver = extrasAlignObserver;
  }
  globalThis.addEventListener?.("resize", queueExtrasActionRailAlignment);

  let extrasModeSnapshot = state.mode;
  const extrasStateLock = installPaneStateLock(formRegistry, "extras", elements, () => {
    state.mode = extrasModeSnapshot;
    syncExtrasMode([singleButton, batchButton], [singlePane, batchPane], state.mode);
  });
  const captureExtrasState = () => {
    extrasModeSnapshot = state.mode;
    extrasStateLock.capture();
  };
  const restoreExtrasState = () => {
    extrasStateLock.restore();
    state.mode = extrasModeSnapshot;
    syncExtrasMode([singleButton, batchButton], [singlePane, batchPane], state.mode);
  };

  formRegistry.extras = {
    applyPayload(payload) {
      const imageData = String(payload?.image_data ?? "").trim();
      if (!imageData) {
        statusNode.textContent = "Extras requires image data for preview handoff.";
        return;
      }
      state.mode = "single_image";
      state.singleImage = {
        name: String(payload?.image_asset ?? "").trim() || "preview-image.png",
        dataUrl: imageData,
      };
      singleStatus.textContent = `Loaded ${state.singleImage.name}`;
      updateExtrasPreview(previewBox, imageData, "Extras preview will appear here after processing.");
      syncExtrasMode([singleButton, batchButton], [singlePane, batchPane], state.mode);
      captureExtrasState();
    },
  };
  const handlePreviewHandoff = (event) => {
    if (!section.isConnected) {
      return;
    }
    event.preventDefault?.();
    formRegistry.extras.applyPayload(event.detail ?? {});
  };
  globalThis.document?.addEventListener?.("rookieui:extras:preview-handoff", handlePreviewHandoff);

  submitButton.addEventListener("click", async () => {
    await submitExtras(bootstrapState, state, elements, statusNode, previewBox);
    captureExtrasState();
  });

  return {
    onActivate: () => {
      restoreExtrasState();
      syncExtrasActionRailAlignment();
      queueExtrasActionRailAlignment();
    },
    onDeactivate: captureExtrasState,
    destroy: () => {
      if (extrasRailAlignRafToken !== null && typeof globalThis.cancelAnimationFrame === "function") {
        globalThis.cancelAnimationFrame(extrasRailAlignRafToken);
        extrasRailAlignRafToken = null;
      }
      extrasAlignObserver?.disconnect?.();
      globalThis.removeEventListener?.("resize", queueExtrasActionRailAlignment);
      globalThis.document?.removeEventListener?.("rookieui:extras:preview-handoff", handlePreviewHandoff);
    },
  };
}
