export function setImg2ImgFieldVisibility(fieldNode, visible) {
  if (!fieldNode) {
    return;
  }
  fieldNode.hidden = !visible;
  fieldNode.querySelectorAll("input, select, textarea, button").forEach((control) => {
    control.disabled = !visible;
  });
}

export function syncImageEditReferenceUi(profileState, modeUi) {
  const { imageEditProfile, referenceLimit, normalizedMainSlot } = profileState;
  const qwen21Edit = profileState.activeProfile?.id === "qwen_image_21_edit";
  if (modeUi.referenceSection) {
    modeUi.referenceSection.hidden = !imageEditProfile;
  }
  if (modeUi.referenceHintNode) {
    modeUi.referenceHintNode.textContent =
      qwen21Edit
        ? "Reference 1 is the edit target and controls reference-size output. Promote a populated reference to move it visibly to the first slot."
        :
      referenceLimit > 1
        ? `Reference 1 uses the source image canvas above. Add up to ${referenceLimit - 1} more ordered references here and choose the main reference.`
        : "Reference 1 uses the source image canvas above. This profile accepts only one direct reference image.";
  }
  if (modeUi.qwen21Controls) {
    modeUi.qwen21Controls.hidden = !qwen21Edit;
    modeUi.qwen21Controls.querySelectorAll("input, select, button").forEach((control) => {
      control.disabled = !qwen21Edit;
    });
  }
  modeUi.referenceSlots.forEach((slot) => {
    const visible = imageEditProfile && slot.slotIndex < referenceLimit;
    if (slot.card) {
      slot.card.hidden = !visible;
    }
    if (slot.mainRadio) {
      slot.mainRadio.disabled = !visible;
      slot.mainRadio.checked = visible && slot.slotIndex === normalizedMainSlot;
    }
    if (slot.assetInput) {
      slot.assetInput.disabled = !visible;
    }
    if (slot.fileInput) {
      slot.fileInput.disabled = !visible;
    }
    slot.updateStatus?.();
  });
}

export function syncImg2ImgModeAvailability({ profileState, elements, modeRouter, modeUi, setElementValue }) {
  if (profileState.imageEditProfile && elements.mode.value !== "img2img") {
    setElementValue(elements.mode, "img2img");
    modeRouter?.activateSubtab?.("img2img", { dispatchChange: false });
  }
  modeUi.modeButtons.forEach((button, tabId) => {
    const allowed = !profileState.imageEditProfile || tabId === "img2img";
    button.disabled = !allowed;
    button.hidden = profileState.activeProfile?.id === "qwen_image_21_edit" && tabId !== "img2img";
    button.setAttribute("aria-disabled", String(!allowed));
  });
}

export function syncImg2ImgModeParameterFields(profileState, modeAwareFieldControls) {
  const editEnabled = profileState.imageEditProfile;
  const qwen21Edit = profileState.activeProfile?.id === "qwen_image_21_edit";
  const customQwen21Size = qwen21Edit
    && modeAwareFieldControls.outputSizeInput?.value === "custom";
  setImg2ImgFieldVisibility(modeAwareFieldControls.widthField, !editEnabled || customQwen21Size);
  setImg2ImgFieldVisibility(modeAwareFieldControls.heightField, !editEnabled || customQwen21Size);
  setImg2ImgFieldVisibility(modeAwareFieldControls.resizeModeField, !editEnabled);
  setImg2ImgFieldVisibility(modeAwareFieldControls.denoiseField, !editEnabled);
  setImg2ImgFieldVisibility(modeAwareFieldControls.growMaskField, !editEnabled);
  setImg2ImgFieldVisibility(modeAwareFieldControls.batchSizeField, !editEnabled);
  setImg2ImgFieldVisibility(modeAwareFieldControls.clipSkipField, !editEnabled);
  for (const input of modeAwareFieldControls.qwenExcludedInputs ?? []) {
    setImg2ImgFieldVisibility(
      input.closest(".rookieui-shell__field, .rookieui-shell__slider-field, .rookieui-shell__inline-checkbox-field"),
      !qwen21Edit,
    );
  }
  for (const id of [
    "rookieui-img2img-adetailer-section", "rookieui-img2img-controlnet-section",
    "rookieui-img2img-mask-editor",
  ]) {
    const section = document.getElementById(id);
    if (!section) continue;
    section.hidden = qwen21Edit;
  }
  const dtypeQuicksetting = document.getElementById("rookieui-img2img-low-bits-quicksetting");
  if (dtypeQuicksetting) {
    dtypeQuicksetting.hidden = qwen21Edit;
    dtypeQuicksetting.querySelectorAll("input, select").forEach((control) => {
      control.toggleAttribute("disabled", qwen21Edit);
    });
  }
  if (modeAwareFieldControls.hiresSection) {
    modeAwareFieldControls.hiresSection.hidden = editEnabled;
    modeAwareFieldControls.hiresSection.querySelectorAll("input, select, textarea, button").forEach((control) => {
      control.disabled = editEnabled;
    });
  }
}
