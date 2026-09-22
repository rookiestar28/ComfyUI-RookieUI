export function appendImageEditReferenceCard({
  slotNumber, assetInput, dataInput, grid, lifecycle, createField, createInput,
  createActionButton, appendTextElement, syncBoundControls, statusNode,
  readFile, emitDebugWarning, onMakePrimary,
}) {
  const card = document.createElement("div");
  card.className = "rookieui-shell__section rookieui-shell__section--soft";
  card.id = `rookieui-img2img-reference-card-${slotNumber}`;
  grid.appendChild(card);
  appendTextElement(card, "h5", "rookieui-shell__section-title", `Reference ${slotNumber}`);
  const mainLabel = document.createElement("label");
  mainLabel.className = "rookieui-shell__status";
  mainLabel.htmlFor = `rookieui-img2img-reference-main-${slotNumber - 1}`;
  const mainRadio = document.createElement("input");
  mainRadio.type = "radio";
  mainRadio.name = "rookieui-img2img-main-reference";
  mainRadio.id = `rookieui-img2img-reference-main-${slotNumber - 1}`;
  mainRadio.value = String(slotNumber - 1);
  mainLabel.appendChild(mainRadio);
  mainLabel.append(" Main reference");
  card.appendChild(mainLabel);
  createField(card, `Reference ${slotNumber} Asset`, assetInput);
  const actionRow = document.createElement("div");
  card.appendChild(actionRow);
  const uploadButton = createActionButton(
    `rookieui-img2img-reference-upload-${slotNumber}`, `Upload Reference ${slotNumber}`,
  );
  actionRow.appendChild(uploadButton);
  const clearButton = createActionButton(
    `rookieui-img2img-reference-clear-${slotNumber}`, `Clear Reference ${slotNumber}`,
  );
  actionRow.appendChild(clearButton);
  const fileInput = createInput("file", `rookieui-img2img-reference-file-${slotNumber}`, "", {
    className: "rookieui-shell__file-input",
  });
  fileInput.accept = "image/png,image/webp,image/jpeg";
  fileInput.hidden = true;
  fileInput.tabIndex = -1;
  card.appendChild(fileInput);
  const status = appendTextElement(
    card, "p", "rookieui-shell__status", "No additional reference selected.",
    `rookieui-img2img-reference-status-${slotNumber}`,
  );
  const updateStatus = () => {
    const assetValue = String(assetInput.value ?? "").trim();
    const dataValue = String(dataInput.value ?? "").trim();
    status.textContent = assetValue
      ? `Asset: ${assetValue}`
      : dataValue ? "Uploaded reference image ready." : "No additional reference selected.";
  };
  lifecycle.listen(uploadButton, "click", () => fileInput.click());
  lifecycle.listen(clearButton, "click", () => {
    assetInput.value = "";
    dataInput.value = "";
    syncBoundControls([assetInput, dataInput]);
    updateStatus();
    statusNode.textContent = `Cleared Reference ${slotNumber}.`;
  });
  lifecycle.listen(assetInput, "input", () => {
    if (String(assetInput.value ?? "").trim()) dataInput.value = "";
    syncBoundControls([assetInput, dataInput]);
    updateStatus();
  });
  lifecycle.listen(fileInput, "change", async () => {
    const [file] = Array.from(fileInput.files ?? []);
    if (!file) return;
    try {
      const dataUrl = await readFile(file);
      if (dataUrl === null) return;
      dataInput.value = dataUrl;
      assetInput.value = "";
      syncBoundControls([assetInput, dataInput]);
      updateStatus();
      statusNode.textContent = `Loaded Reference ${slotNumber}: ${file.name}`;
    } catch (error) {
      emitDebugWarning("shell.img2img_reference_upload", "Reference image upload failed.", error);
      statusNode.textContent = `Failed to load Reference ${slotNumber}.`;
    }
  });
  lifecycle.listen(mainRadio, "change", () => {
    if (mainRadio.checked) onMakePrimary(slotNumber - 1);
  });
  updateStatus();
  return {
    slotIndex: slotNumber - 1, card, mainRadio, assetInput, dataInput,
    fileInput, statusNode: status, updateStatus,
  };
}
