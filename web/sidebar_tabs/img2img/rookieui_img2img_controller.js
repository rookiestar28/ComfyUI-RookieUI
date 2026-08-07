export const IMG2IMG_GENERATION_MODES = Object.freeze([
  "img2img",
  "sketch",
  "inpaint",
  "inpaint_sketch",
  "inpaint_upload",
  "batch",
]);

const MAX_REFERENCE_SLOTS = 3;

function cloneValue(value) {
  if (Array.isArray(value)) {
    return value.map((entry) => cloneValue(entry));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, entry]) => [key, cloneValue(entry)]));
  }
  return value;
}

function normalizeMode(value) {
  const candidate = String(value ?? "").trim().toLowerCase();
  return IMG2IMG_GENERATION_MODES.includes(candidate) ? candidate : "img2img";
}

function normalizeReferenceEntry(entry) {
  const value = entry && typeof entry === "object" ? entry : {};
  return {
    image_asset: String(value.image_asset ?? value.asset ?? "").trim(),
    image_data: String(value.image_data ?? value.data ?? "").trim(),
  };
}

function normalizeReferenceLimit(value, fallback = 0) {
  const candidate = Number(value ?? fallback);
  if (!Number.isFinite(candidate)) {
    return Math.max(0, Math.min(MAX_REFERENCE_SLOTS, Number(fallback) || 0));
  }
  return Math.max(0, Math.min(MAX_REFERENCE_SLOTS, Math.trunc(candidate)));
}

function normalizeBatchImages(value) {
  return (Array.isArray(value) ? value : [])
    .map((entry) => String(entry ?? "").trim())
    .filter(Boolean);
}

function normalizeMask(payload = {}, fallback = {}) {
  const mask = payload.mask && typeof payload.mask === "object" ? payload.mask : {};
  const hasMaskFields = [
    "mask_asset",
    "mask_data",
    "mask_metadata",
    "staged_mask_data",
    "mask_dirty",
    "asset",
    "data",
    "metadata",
    "stagedData",
    "dirty",
  ].some((key) => Object.prototype.hasOwnProperty.call(payload, key));
  if (!hasMaskFields && !Object.keys(mask).length) {
    return cloneValue(fallback);
  }
  return {
    asset: String(payload.mask_asset ?? payload.asset ?? mask.asset ?? "").trim(),
    data: String(payload.mask_data ?? payload.data ?? mask.data ?? "").trim(),
    metadata: cloneValue(payload.mask_metadata ?? payload.metadata ?? mask.metadata ?? {}),
    stagedData: String(payload.staged_mask_data ?? payload.stagedData ?? mask.stagedData ?? "").trim(),
    dirty: Boolean(payload.mask_dirty ?? payload.dirty ?? mask.dirty),
  };
}

function normalizeProfileState(options = {}, current = {}) {
  const profileId = String(options.profileId ?? options.profile ?? current.profileId ?? "").trim();
  const imageEditProfile = Boolean(
    options.imageEditProfile ?? options.image_edit_profile ?? current.imageEditProfile,
  );
  const requestedLimit = options.maxDirectReferences ?? options.referenceLimit ?? options.max_direct_references;
  const referenceLimit = normalizeReferenceLimit(
    requestedLimit !== undefined ? requestedLimit : imageEditProfile ? 1 : 0,
    current.referenceLimit,
  );
  return { profileId, imageEditProfile, referenceLimit, referenceLimitExplicit: requestedLimit !== undefined || imageEditProfile };
}

function clampIndex(index, limit) {
  return Math.min(Math.max(0, Number(index) || 0), Math.max(0, limit - 1));
}

export function createImg2ImgController(options = {}) {
  const initialProfile = normalizeProfileState(options);
  const state = {
    mode: initialProfile.imageEditProfile ? "img2img" : normalizeMode(options.initialMode),
    profileId: initialProfile.profileId,
    imageEditProfile: initialProfile.imageEditProfile,
    referenceLimit: normalizeReferenceLimit(
      options.referenceLimit ?? options.maxDirectReferences,
      initialProfile.referenceLimit,
    ),
    referenceLimitExplicit:
      options.referenceLimit !== undefined || options.maxDirectReferences !== undefined || initialProfile.referenceLimitExplicit,
    referenceSlots: [],
    selectedMainSlot: 0,
    imageAsset: String(options.initialImageAsset ?? "").trim(),
    imageData: String(options.initialImageData ?? "").trim(),
    mask: normalizeMask(options.initialMask ?? {}, {}),
    batchImages: normalizeBatchImages(options.initialBatchImages),
  };
  state.referenceSlots = (Array.isArray(options.initialReferenceSlots) ? options.initialReferenceSlots : [])
    .slice(0, MAX_REFERENCE_SLOTS)
    .map(normalizeReferenceEntry);
  state.selectedMainSlot = clampIndex(options.initialMainReferenceSlot, state.referenceLimit || state.referenceSlots.length);

  let destroyed = false;
  let epoch = 0;

  const setReferenceSlots = (slots) => {
    if (destroyed) return getReferencePayload();
    const normalizedSlots = (Array.isArray(slots) ? slots : [])
      .slice(0, MAX_REFERENCE_SLOTS)
      .map(normalizeReferenceEntry);
    state.referenceSlots = normalizedSlots;
    const effectiveLimit = state.referenceLimitExplicit ? state.referenceLimit : normalizedSlots.length;
    state.selectedMainSlot = clampIndex(state.selectedMainSlot, effectiveLimit);
    return getReferencePayload();
  };

  const getReferencePayload = () => {
    const limit = Math.min(
      MAX_REFERENCE_SLOTS,
      Math.max(0, state.referenceLimitExplicit ? state.referenceLimit : state.referenceSlots.length),
    );
    if (limit <= 0) {
      return { referenceImages: [], mainReferenceIndex: 0, selectedMainSlot: 0 };
    }
    const slots = Array.from({ length: limit }, (_, index) => normalizeReferenceEntry(state.referenceSlots[index]));
    const selectedMainSlot = clampIndex(state.selectedMainSlot, limit);
    const referenceImages = [];
    let mainReferenceIndex = -1;
    slots.forEach((entry, slotIndex) => {
      if (!entry.image_asset && !entry.image_data) return;
      if (slotIndex === selectedMainSlot) mainReferenceIndex = referenceImages.length;
      referenceImages.push(entry);
    });
    return { referenceImages: cloneValue(referenceImages), mainReferenceIndex, selectedMainSlot };
  };

  const setMode = (mode) => {
    if (destroyed) return state.mode;
    const normalized = normalizeMode(mode);
    state.mode = state.imageEditProfile ? "img2img" : normalized;
    return state.mode;
  };

  const setProfileState = (profile = {}) => {
    if (destroyed) return getSnapshot();
    const next = normalizeProfileState(profile, state);
    state.profileId = next.profileId;
    state.imageEditProfile = next.imageEditProfile;
    state.referenceLimit = next.referenceLimit;
    state.referenceLimitExplicit = next.referenceLimitExplicit;
    if (state.imageEditProfile) state.mode = "img2img";
    state.selectedMainSlot = clampIndex(state.selectedMainSlot, state.referenceLimit);
    return getSnapshot();
  };

  /**
   * @param {{
   *   profile?: unknown,
   *   profile_id?: unknown,
   *   image_edit_profile?: unknown,
   *   max_direct_references?: unknown,
   *   mode?: unknown,
   *   image_asset?: unknown,
   *   imageAsset?: unknown,
   *   image_data?: unknown,
   *   imageData?: unknown,
   *   batch_images?: unknown,
   *   batchImages?: unknown,
   *   reference_images?: unknown,
   *   main_reference_index?: unknown,
   * }} payload
   */
  const applyPayload = (payload = {}) => {
    if (destroyed || !payload || typeof payload !== "object") return getSnapshot();
    const hasProfileState =
      payload.profile !== undefined ||
      payload.profile_id !== undefined ||
      payload.image_edit_profile !== undefined ||
      payload.max_direct_references !== undefined;
    if (hasProfileState) {
      setProfileState({
        profileId: payload.profile ?? payload.profile_id,
        imageEditProfile: payload.image_edit_profile,
        maxDirectReferences: payload.max_direct_references,
      });
    }
    if (payload.mode !== undefined) setMode(payload.mode);
    state.imageAsset = String(payload.image_asset ?? payload.imageAsset ?? state.imageAsset).trim();
    state.imageData = String(payload.image_data ?? payload.imageData ?? state.imageData).trim();
    state.mask = normalizeMask(payload, state.mask);
    state.batchImages = normalizeBatchImages(payload.batch_images ?? payload.batchImages ?? state.batchImages);
    if (Array.isArray(payload.reference_images)) {
      setReferenceSlots(payload.reference_images);
      state.selectedMainSlot = clampIndex(
        payload.main_reference_index,
        state.referenceLimitExplicit ? state.referenceLimit : state.referenceSlots.length,
      );
    } else if (payload.image_asset !== undefined || payload.image_data !== undefined) {
      setReferenceSlots([
        { image_asset: payload.image_asset, image_data: payload.image_data },
        ...state.referenceSlots.slice(1),
      ]);
    }
    return getSnapshot();
  };

  const getSnapshot = () => ({
    mode: state.mode,
    profileId: state.profileId,
    imageEditProfile: state.imageEditProfile,
    referenceLimit: state.referenceLimit,
    referenceSlots: cloneValue(state.referenceSlots),
    selectedMainSlot: state.selectedMainSlot,
    imageAsset: state.imageAsset,
    imageData: state.imageData,
    mask: cloneValue(state.mask),
    batchImages: [...state.batchImages],
  });

  return {
    getSupportedModes: () => [...IMG2IMG_GENERATION_MODES],
    getSnapshot,
    setMode,
    setProfileState,
    setReferenceSlots,
    setMainReferenceSlot(index) {
      if (!destroyed) {
        state.selectedMainSlot = clampIndex(
          index,
          state.referenceLimitExplicit ? state.referenceLimit : state.referenceSlots.length,
        );
      }
      return state.selectedMainSlot;
    },
    getReferencePayload,
    applyPayload,
    beginAsyncEpoch() {
      epoch += 1;
      return epoch;
    },
    invalidateAsyncEpoch() {
      epoch += 1;
      return epoch;
    },
    isAsyncEpochCurrent(candidate) {
      return !destroyed && Number.isInteger(candidate) && candidate === epoch;
    },
    destroy() {
      if (destroyed) return;
      destroyed = true;
      epoch += 1;
    },
    isDestroyed: () => destroyed,
  };
}
