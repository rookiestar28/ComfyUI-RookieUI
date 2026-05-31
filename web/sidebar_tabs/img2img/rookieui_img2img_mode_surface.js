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
  if (modeUi.referenceSection) {
    modeUi.referenceSection.hidden = !imageEditProfile;
  }
  if (modeUi.referenceHintNode) {
    modeUi.referenceHintNode.textContent =
      referenceLimit > 1
        ? `Reference 1 uses the source image canvas above. Add up to ${referenceLimit - 1} more ordered references here and choose the main reference.`
        : "Reference 1 uses the source image canvas above. This profile accepts only one direct reference image.";
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
    button.setAttribute("aria-disabled", String(!allowed));
  });
}

export function syncImg2ImgModeParameterFields(profileState, modeAwareFieldControls) {
  const editEnabled = profileState.imageEditProfile;
  setImg2ImgFieldVisibility(modeAwareFieldControls.widthField, !editEnabled);
  setImg2ImgFieldVisibility(modeAwareFieldControls.heightField, !editEnabled);
  setImg2ImgFieldVisibility(modeAwareFieldControls.resizeModeField, !editEnabled);
  setImg2ImgFieldVisibility(modeAwareFieldControls.denoiseField, !editEnabled);
  setImg2ImgFieldVisibility(modeAwareFieldControls.growMaskField, !editEnabled);
  setImg2ImgFieldVisibility(modeAwareFieldControls.batchSizeField, !editEnabled);
  setImg2ImgFieldVisibility(modeAwareFieldControls.clipSkipField, !editEnabled);
  if (modeAwareFieldControls.hiresSection) {
    modeAwareFieldControls.hiresSection.hidden = editEnabled;
    modeAwareFieldControls.hiresSection.querySelectorAll("input, select, textarea, button").forEach((control) => {
      control.disabled = editEnabled;
    });
  }
}
