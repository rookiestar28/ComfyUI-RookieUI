export function buildPngInfoPane(parent, bootstrapState, formRegistry, context) {
  const {
    appendTextElement,
    createInput,
    createActionButton,
    createMiniActionButton,
    createList,
    setPreviewContent,
    setPngInfoSummaryVisibility,
    setListVisibility,
    updatePngInfoApplyButtons,
    inspectPngInfo,
    writeTextToClipboard,
    emitFrontendDebugWarning,
    applyPngInfoResult,
    readFileAsDataUrl,
  } = context;  const section = document.createElement("section");
  section.className = "rookieui-shell__section";
  parent.appendChild(section);

  appendTextElement(section, "h3", "rookieui-shell__section-title", "PNG Info");

  const workspace = document.createElement("div");
  workspace.className = "rookieui-shell__workspace-grid rookieui-shell__workspace-grid--pnginfo";
  section.appendChild(workspace);

  const leftColumn = document.createElement("div");
  leftColumn.className = "rookieui-shell__workspace-column";
  workspace.appendChild(leftColumn);

  const rightColumn = document.createElement("div");
  rightColumn.className = "rookieui-shell__workspace-column";
  workspace.appendChild(rightColumn);

  const form = document.createElement("form");
  form.className = "rookieui-shell__form";
  form.id = "rookieui-pnginfo-form";
  leftColumn.appendChild(form);

  const uploadSection = document.createElement("section");
  uploadSection.className = "rookieui-shell__section rookieui-shell__section--soft";
  form.appendChild(uploadSection);
  appendTextElement(uploadSection, "h4", "rookieui-shell__section-title", "Image Inspector");

  const dropzone = document.createElement("label");
  dropzone.className = "rookieui-shell__dropzone";
  dropzone.id = "rookieui-pnginfo-dropzone";
  uploadSection.appendChild(dropzone);
  appendTextElement(dropzone, "span", "rookieui-shell__dropzone-icon", "⇪");
  appendTextElement(
    dropzone,
    "span",
    "rookieui-shell__dropzone-text",
    "Drop a PNG here or browse for an image to auto-read metadata.",
  );

  const fileInput = createInput("file", "rookieui-pnginfo-image-file", "", {
    className: "rookieui-shell__file-input",
  });
  fileInput.accept = "image/png,image/webp,image/jpeg";
  dropzone.appendChild(fileInput);

  const actions = document.createElement("div");
  actions.className = "rookieui-shell__pnginfo-apply-rail";
  actions.id = "rookieui-pnginfo-apply-rail";
  form.appendChild(actions);

  const applyTxt2ImgButton = createActionButton("rookieui-pnginfo-apply-txt2img", "Apply to Txt2Img");
  const applyImg2ImgButton = createActionButton("rookieui-pnginfo-apply-img2img", "Apply to Img2Img");
  applyTxt2ImgButton.classList.add("rookieui-shell__button--apply");
  applyImg2ImgButton.classList.add("rookieui-shell__button--apply");
  applyTxt2ImgButton.disabled = true;
  applyImg2ImgButton.disabled = true;
  actions.appendChild(applyTxt2ImgButton);
  actions.appendChild(applyImg2ImgButton);

  const statusNode = document.createElement("p");
  statusNode.id = "rookieui-pnginfo-status";
  statusNode.className = "rookieui-shell__status";
  statusNode.textContent = "Idle";
  form.appendChild(statusNode);

  const previewSection = document.createElement("section");
  previewSection.className = "rookieui-shell__section rookieui-shell__section--soft";
  // IMPORTANT: keep PNG Info preview section anchored above the upload/action form; users expect the image preview at the top of the input block.
  leftColumn.insertBefore(previewSection, form);
  appendTextElement(previewSection, "h4", "rookieui-shell__section-title", "Preview");

  const previewBox = document.createElement("div");
  previewBox.className = "rookieui-shell__preview-box rookieui-shell__preview-box--compact";
  previewBox.id = "rookieui-pnginfo-preview";
  previewSection.appendChild(previewBox);
  setPreviewContent(
    previewBox,
    "",
    "Imported PNG preview will appear here after selecting an image.",
  );

  const metadataSection = document.createElement("section");
  metadataSection.className = "rookieui-shell__section rookieui-shell__section--soft";
  metadataSection.id = "rookieui-pnginfo-metadata";
  rightColumn.appendChild(metadataSection);
  const summaryHeader = document.createElement("div");
  summaryHeader.className = "rookieui-shell__pnginfo-header";
  metadataSection.appendChild(summaryHeader);
  appendTextElement(summaryHeader, "h4", "rookieui-shell__section-title", "Generation Summary");
  const sourceBadge = appendTextElement(summaryHeader, "span", "rookieui-shell__pnginfo-source", "");
  sourceBadge.hidden = true;

  const summaryText = appendTextElement(
    metadataSection,
    "p",
    "rookieui-shell__pnginfo-summary-text",
    "Generation summary will appear after metadata is loaded.",
  );

  const metadataCards = document.createElement("div");
  metadataCards.className = "rookieui-shell__pnginfo-cards";
  metadataCards.id = "rookieui-pnginfo-cards";
  metadataSection.appendChild(metadataCards);

  const promptsGrid = document.createElement("div");
  promptsGrid.className = "rookieui-shell__pnginfo-prompts";
  metadataSection.appendChild(promptsGrid);

  const promptCard = document.createElement("article");
  promptCard.className = "rookieui-shell__pnginfo-prompt-card";
  promptsGrid.appendChild(promptCard);
  const promptHeader = document.createElement("div");
  promptHeader.className = "rookieui-shell__pnginfo-prompt-header";
  promptCard.appendChild(promptHeader);
  appendTextElement(promptHeader, "span", "rookieui-shell__pnginfo-prompt-label", "Prompt");
  const copyPromptButton = createMiniActionButton("rookieui-pnginfo-copy-prompt", "Copy");
  copyPromptButton.classList.add("rookieui-shell__pnginfo-copy");
  copyPromptButton.disabled = true;
  promptHeader.appendChild(copyPromptButton);
  const promptTextNode = appendTextElement(
    promptCard,
    "pre",
    "rookieui-shell__pnginfo-prompt-text",
    "Prompt is unavailable in this metadata payload.",
  );

  const negativePromptCard = document.createElement("article");
  negativePromptCard.className = "rookieui-shell__pnginfo-prompt-card";
  promptsGrid.appendChild(negativePromptCard);
  const negativePromptHeader = document.createElement("div");
  negativePromptHeader.className = "rookieui-shell__pnginfo-prompt-header";
  negativePromptCard.appendChild(negativePromptHeader);
  appendTextElement(negativePromptHeader, "span", "rookieui-shell__pnginfo-prompt-label", "Negative Prompt");
  const copyNegativePromptButton = createMiniActionButton("rookieui-pnginfo-copy-negative-prompt", "Copy");
  copyNegativePromptButton.classList.add("rookieui-shell__pnginfo-copy");
  copyNegativePromptButton.disabled = true;
  negativePromptHeader.appendChild(copyNegativePromptButton);
  const negativePromptTextNode = appendTextElement(
    negativePromptCard,
    "pre",
    "rookieui-shell__pnginfo-prompt-text",
    "Negative prompt is unavailable in this metadata payload.",
  );

  const unsupportedHeading = appendTextElement(
    metadataSection,
    "h4",
    "rookieui-shell__subsection-title",
    "Unsupported Fields",
  );
  const unsupportedList = createList("rookieui-pnginfo-unsupported");
  unsupportedList.hidden = true;
  unsupportedHeading.hidden = true;
  metadataSection.appendChild(unsupportedList);

  const warningsHeading = appendTextElement(
    metadataSection,
    "h4",
    "rookieui-shell__subsection-title",
    "Warnings",
  );
  const warningList = createList("rookieui-pnginfo-warnings");
  warningList.hidden = true;
  warningsHeading.hidden = true;
  metadataSection.appendChild(warningList);

  const state = {
    imageData: "",
    inspectionResult: null,
  };

  const runAutoInspection = async () => {
    if (!state.imageData) {
      state.inspectionResult = null;
      setListVisibility(unsupportedHeading, unsupportedList, []);
      setListVisibility(warningsHeading, warningList, []);
      setPngInfoSummaryVisibility(
        {
          sourceBadge,
          summaryText,
          cards: metadataCards,
          promptText: promptTextNode,
          negativePromptText: negativePromptTextNode,
          copyPrompt: copyPromptButton,
          copyNegativePrompt: copyNegativePromptButton,
        },
        null,
      );
      updatePngInfoApplyButtons(state, {
        txt2img: applyTxt2ImgButton,
        img2img: applyImg2ImgButton,
      });
      statusNode.textContent = "Idle";
      return;
    }
    await inspectPngInfo(
      bootstrapState,
      state,
      statusNode,
      {
        summary: {
          sourceBadge,
          summaryText,
          cards: metadataCards,
          promptText: promptTextNode,
          negativePromptText: negativePromptTextNode,
          copyPrompt: copyPromptButton,
          copyNegativePrompt: copyNegativePromptButton,
        },
        unsupportedHeading,
        unsupported: unsupportedList,
        warningsHeading,
        warnings: warningList,
      },
      {
        txt2img: applyTxt2ImgButton,
        img2img: applyImg2ImgButton,
      },
    );
  };

  const syncFileSelection = async (file) => {
    if (!file) {
      return;
    }
    state.imageData = await readFileAsDataUrl(file);
    setPreviewContent(previewBox, state.imageData, "");
    statusNode.textContent = `Loaded ${file.name}; reading metadata...`;
  };

  fileInput.addEventListener("change", async () => {
    const [file] = Array.from(fileInput.files ?? []);
    if (!file) {
      return;
    }
    try {
      await syncFileSelection(file);
      await runAutoInspection();
    } catch (_error) {
      emitFrontendDebugWarning("shell.pnginfo_upload", "PNG Info file input handling failed.", _error);
      statusNode.textContent = "Failed to read the selected image.";
    }
  });
  dropzone.addEventListener("dragover", (event) => {
    event.preventDefault();
    event.stopPropagation();
    dropzone.dataset.dragging = "true";
  });
  dropzone.addEventListener("dragleave", (event) => {
    event.stopPropagation();
    dropzone.dataset.dragging = "false";
  });
  dropzone.addEventListener("drop", async (event) => {
    event.preventDefault();
    // DEBUG HOTSPOT: without containment, the same A1111 PNG drop bubbles to ComfyUI's canvas importer and creates a native workflow behind PNG Info.
    event.stopPropagation();
    dropzone.dataset.dragging = "false";
    const [file] = Array.from(event.dataTransfer?.files ?? []);
    if (!file) {
      return;
    }
    try {
      await syncFileSelection(file);
      await runAutoInspection();
    } catch (_error) {
      emitFrontendDebugWarning("shell.pnginfo_upload", "PNG Info file drop handling failed.", _error);
      statusNode.textContent = "Failed to read the dropped image.";
    }
  });
  copyPromptButton.addEventListener("click", async () => {
    const copied = await writeTextToClipboard(promptTextNode.textContent);
    statusNode.textContent = copied ? "Copied prompt text." : "Prompt text is unavailable to copy.";
  });
  copyNegativePromptButton.addEventListener("click", async () => {
    const copied = await writeTextToClipboard(negativePromptTextNode.textContent);
    statusNode.textContent = copied ? "Copied negative prompt text." : "Negative prompt text is unavailable to copy.";
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void runAutoInspection();
  });

  applyTxt2ImgButton.addEventListener("click", () => {
    applyPngInfoResult(formRegistry, "txt2img", state, statusNode);
  });
  applyImg2ImgButton.addEventListener("click", () => {
    applyPngInfoResult(formRegistry, "img2img", state, statusNode);
  });
}
