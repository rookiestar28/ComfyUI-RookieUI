export function resolveActiveImg2ImgProfile(profileLookup, profileId) {
  const normalizedProfileId = String(profileId ?? "").trim().toLowerCase();
  return profileLookup.get(normalizedProfileId) ?? profileLookup.get(profileId) ?? null;
}

export function buildImageEditReferencePayloadFromElements(elements, referenceLimit = null) {
  const resolvedLimit = Math.max(0, Number(referenceLimit ?? elements.maxDirectReferences?.value ?? 0) || 0);
  if (resolvedLimit <= 0) {
    return {
      referenceImages: [],
      mainReferenceIndex: 0,
      selectedMainSlot: 0,
    };
  }

  const normalizedLimit = Math.max(1, resolvedLimit);
  const orderedSlots = [
    {
      image_asset: String(elements.imageAsset?.value ?? "").trim(),
      image_data: String(elements.imageData?.value ?? "").trim(),
    },
    {
      image_asset: String(elements.referenceAsset2?.value ?? "").trim(),
      image_data: String(elements.referenceData2?.value ?? "").trim(),
    },
    {
      image_asset: String(elements.referenceAsset3?.value ?? "").trim(),
      image_data: String(elements.referenceData3?.value ?? "").trim(),
    },
  ].slice(0, normalizedLimit);

  const selectedMainSlot = Math.min(
    Math.max(0, Number(elements.mainReferenceIndex?.value ?? 0) || 0),
    Math.max(0, normalizedLimit - 1),
  );
  const referenceImages = [];
  let mainReferenceIndex = -1;
  orderedSlots.forEach((entry, slotIndex) => {
    if (!entry.image_asset && !entry.image_data) {
      return;
    }
    if (slotIndex === selectedMainSlot) {
      mainReferenceIndex = referenceImages.length;
    }
    referenceImages.push(entry);
  });

  return {
    referenceImages,
    mainReferenceIndex,
    selectedMainSlot,
  };
}

export function syncImageEditProfileStateFromElements(elements, activeProfile) {
  const imageEditProfile = Boolean(activeProfile?.image_edit_profile);
  const referenceLimit = imageEditProfile ? Math.max(1, Number(activeProfile?.max_direct_references ?? 0) || 0) : 0;
  elements.imageEditProfile.value = imageEditProfile ? "true" : "false";
  elements.maxDirectReferences.value = String(referenceLimit);
  const normalizedMainSlot = Math.min(
    Math.max(0, Number(elements.mainReferenceIndex.value ?? 0) || 0),
    Math.max(0, referenceLimit - 1),
  );
  elements.mainReferenceIndex.value = String(normalizedMainSlot);
  return {
    activeProfile,
    imageEditProfile,
    referenceLimit,
    normalizedMainSlot,
  };
}
