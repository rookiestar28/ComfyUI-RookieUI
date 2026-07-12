export function createIdeogramModeSelect(createSelect) {
  return createSelect(
    "rookieui-ideogram-mode",
    [
      { value: "quality", label: "Quality" },
      { value: "default", label: "Default" },
      { value: "turbo", label: "Turbo" },
    ],
    "default",
  );
}

export function setProfileFieldVisibility(fieldNode, visible) {
  if (!fieldNode) {
    return;
  }
  fieldNode.hidden = !visible;
  fieldNode.querySelectorAll("input, select, textarea, button").forEach((control) => {
    control.disabled = !visible;
  });
}

export function createIdeogramModeController(input, profileInput, profileLookup, setElementValue) {
  let field = null;
  const sync = () => {
    const profile = profileLookup.get(String(profileInput.value ?? "").trim().toLowerCase()) ?? null;
    const modes = Array.isArray(profile?.ideogram_modes) ? profile.ideogram_modes : [];
    setProfileFieldVisibility(field, modes.length > 0);
    if (modes.length > 0 && !modes.includes(input.value)) {
      setElementValue(input, profile.default_ideogram_mode ?? "default");
    }
  };
  return {
    attach(fieldNode) {
      field = fieldNode;
      sync();
    },
    sync,
  };
}
