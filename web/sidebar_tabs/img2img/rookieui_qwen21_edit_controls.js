export function appendQwen21EditControls({
  referenceSection, elements, lifecycle, createField, createActionButton,
  appendTextElement, syncBoundControls, statusNode, syncSizeVisibility,
}) {
  const section = document.createElement("div");
  section.id = "rookieui-img2img-qwen21-controls";
  section.className = "rookieui-shell__section rookieui-shell__section--soft";
  referenceSection.appendChild(section);
  appendTextElement(section, "h5", "rookieui-shell__section-title", "Qwen Image 2.1 Edit");
  const fields = document.createElement("div");
  fields.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
  section.appendChild(fields);
  createField(fields, "Reference resolution (0 keeps source size)", elements.referenceResolution);
  createField(fields, "Output size", elements.outputSizeMode);
  createField(fields, "Task", elements.editTask);
  const button = createActionButton(
    "rookieui-img2img-qwen21-background-instruction", "Apply background removal instruction",
  );
  section.appendChild(button);
  lifecycle.listen(button, "click", () => {
    const instruction = "Remove the background from <image1> and keep the subject with transparent alpha.";
    if (elements.prompt.value.trim() && !window.confirm("Replace the current edit instruction?")) return;
    elements.prompt.value = instruction;
    elements.editTask.value = "background_removal";
    syncBoundControls([elements.prompt, elements.editTask]);
    statusNode.textContent = "Background removal instruction applied. Edit the text before generating if needed.";
  });
  lifecycle.listen(elements.outputSizeMode, "change", syncSizeVisibility);
  return section;
}

export function promoteQwen21Reference({
  selectedIndex, elements, additionalControls, referenceSlots, syncBoundControls,
  maskCanvasContract, refreshSourceCanvasSurface, statusNode, primaryRadio,
}) {
  const slots = [{ assetInput: elements.imageAsset, dataInput: elements.imageData }, ...additionalControls];
  const values = slots.map((slot) => ({ asset: slot.assetInput.value, data: slot.dataInput.value }));
  if (!values[selectedIndex]?.asset && !values[selectedIndex]?.data) {
    statusNode.textContent = `Add Reference ${selectedIndex + 1} before making it primary.`;
    primaryRadio.checked = true;
    return;
  }
  const [promoted] = values.splice(selectedIndex, 1);
  values.unshift(promoted);
  slots.forEach((slot, index) => {
    slot.assetInput.value = values[index].asset;
    slot.dataInput.value = values[index].data;
  });
  elements.mainReferenceIndex.value = "0";
  primaryRadio.checked = true;
  referenceSlots.forEach((slot) => slot.updateStatus?.());
  syncBoundControls([elements.imageAsset, elements.imageData, elements.mainReferenceIndex,
    ...additionalControls.flatMap((slot) => [slot.assetInput, slot.dataInput])]);
  maskCanvasContract.refreshSourceBinding();
  refreshSourceCanvasSurface?.();
  statusNode.textContent = `Reference ${selectedIndex + 1} is now Reference 1 (edit target).`;
}
