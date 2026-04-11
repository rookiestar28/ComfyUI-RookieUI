function _readTrimmedValue(input) {
  if (!input) {
    return "";
  }
  return String(input.value ?? "").trim();
}

function _resolveExecutionMode(modeValue, resolver) {
  if (typeof resolver === "function") {
    return String(resolver(modeValue) ?? "img2img").trim().toLowerCase();
  }
  return String(modeValue ?? "img2img").trim().toLowerCase();
}

export function createImg2ImgMaskCanvasContract({
  modeInput,
  imageDataInput,
  imageAssetInput,
  maskDataInput,
  maskAssetInput,
  resolveExecutionMode,
  syncBoundControls,
} = {}) {
  const state = {
    sourceImageData: "",
    sourceImageAsset: "",
    sourceSignature: "",
    stagedMaskData: "",
    stagedMaskDirty: false,
    stagedRevision: 0,
    appliedRevision: 0,
    lastMode: "",
  };

  const refreshSourceBinding = () => {
    state.sourceImageData = _readTrimmedValue(imageDataInput);
    state.sourceImageAsset = _readTrimmedValue(imageAssetInput);
    const nextSignature = `${state.sourceImageData}::${state.sourceImageAsset}`;
    if (nextSignature !== state.sourceSignature) {
      state.sourceSignature = nextSignature;
      const hasCommittedMask = Boolean(_readTrimmedValue(maskDataInput) || _readTrimmedValue(maskAssetInput));
      if (!hasCommittedMask) {
        // CRITICAL: source-image mutations must invalidate stale staged mask buffers when no payload mask exists, otherwise send-to-img2img can carry phantom dirty state across tabs/modes.
        state.stagedMaskData = "";
        state.stagedMaskDirty = false;
      }
    }
  };

  const stageMaskData = (maskDataUrl, metadata = {}) => {
    const normalized = String(maskDataUrl ?? "").trim();
    if (!normalized) {
      return false;
    }
    refreshSourceBinding();
    state.stagedMaskData = normalized;
    state.stagedMaskDirty = true;
    state.stagedRevision += 1;
    if (metadata.sourceImageData) {
      state.sourceImageData = String(metadata.sourceImageData).trim();
    }
    if (metadata.sourceImageAsset) {
      state.sourceImageAsset = String(metadata.sourceImageAsset).trim();
    }
    return true;
  };

  const clearStagedMask = () => {
    state.stagedMaskData = "";
    state.stagedMaskDirty = false;
  };

  const applyStagedMask = () => {
    if (!maskDataInput || !maskAssetInput || !state.stagedMaskData) {
      return { ok: false, applied: false, message: "No staged mask to apply." };
    }
    // IMPORTANT: canvas output must commit into mask_data and clear mask_asset to keep one deterministic payload source.
    maskDataInput.value = state.stagedMaskData;
    maskAssetInput.value = "";
    state.stagedMaskDirty = false;
    state.appliedRevision = state.stagedRevision;
    if (typeof syncBoundControls === "function") {
      syncBoundControls([maskDataInput, maskAssetInput]);
    }
    return { ok: true, applied: true, message: "Applied staged mask to Img2Img request payload." };
  };

  const handleExternalMaskMutation = () => {
    const currentMaskData = _readTrimmedValue(maskDataInput);
    if (!currentMaskData) {
      state.stagedMaskData = "";
      state.stagedMaskDirty = false;
      return;
    }
    if (currentMaskData !== state.stagedMaskData) {
      state.stagedMaskData = currentMaskData;
      state.stagedMaskDirty = false;
      state.stagedRevision += 1;
      state.appliedRevision = state.stagedRevision;
    }
  };

  const getSubmissionReadiness = () => {
    if (state.stagedMaskDirty) {
      return {
        ok: false,
        message: "Mask canvas has unapplied changes. Click Apply Mask before submitting.",
      };
    }
    return { ok: true };
  };

  const onModeChange = () => {
    const modeValue = modeInput ? modeInput.value : state.lastMode;
    state.lastMode = String(modeValue ?? "").trim().toLowerCase();
    refreshSourceBinding();
    const executionMode = _resolveExecutionMode(modeValue, resolveExecutionMode);
    const inpaintExecution = executionMode === "inpaint";
    const hasMaskPayload = Boolean(_readTrimmedValue(maskDataInput) || _readTrimmedValue(maskAssetInput));
    // IMPORTANT: block silent inpaint submits when user has staged-but-unapplied canvas edits.
    if (inpaintExecution && !hasMaskPayload && state.stagedMaskDirty) {
      return {
        ok: false,
        message: "Inpaint mode detected staged mask changes. Apply Mask to commit the canvas output.",
      };
    }
    return { ok: true };
  };

  const getStateSnapshot = () => ({
    sourceImageData: state.sourceImageData,
    sourceImageAsset: state.sourceImageAsset,
    sourceSignature: state.sourceSignature,
    stagedMaskData: state.stagedMaskData,
    stagedMaskDirty: state.stagedMaskDirty,
    stagedRevision: state.stagedRevision,
    appliedRevision: state.appliedRevision,
    lastMode: state.lastMode,
  });

  refreshSourceBinding();

  return {
    applyStagedMask,
    clearStagedMask,
    getStateSnapshot,
    getSubmissionReadiness,
    handleExternalMaskMutation,
    onModeChange,
    refreshSourceBinding,
    stageMaskData,
  };
}
