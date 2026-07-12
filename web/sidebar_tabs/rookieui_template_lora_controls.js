import { setProfileFieldVisibility } from "./rookieui_ideogram_mode_controls.js";

export function createTemplateLoraController({ profileLookup, presetLookup, elements, controls }) {
  const resolvePresetDefault = () =>
    String(presetLookup.get(elements.preset.value)?.template_lora_name ?? "").trim();
  const sync = () => {
    const profile = profileLookup.get(String(elements.profileState.value ?? "").trim().toLowerCase()) ?? null;
    const visible = Boolean(profile?.template_lora_visible);
    const overrideAllowed = Boolean(profile?.template_lora_override_allowed);
    const currentValue = String(elements.templateLoraName.value ?? "").trim();
    const presetDefault = resolvePresetDefault();
    const officialLabel = String(profile?.official_template_lora_label ?? "").trim();
    const officialResolved = presetDefault || officialLabel;
    setProfileFieldVisibility(controls.field, visible);
    if (controls.libraryHeading) {
      controls.libraryHeading.hidden = !visible;
    }
    if (controls.libraryHost) {
      controls.libraryHost.hidden = !visible;
      controls.libraryHost.querySelectorAll("button").forEach((button) => {
        button.disabled = !visible || !overrideAllowed;
      });
    }
    if (controls.statusNode) {
      controls.statusNode.hidden = !visible;
    }
    if (controls.resetButton) {
      controls.resetButton.hidden = !visible;
      controls.resetButton.disabled = !visible || !overrideAllowed;
    }
    elements.templateLoraName.disabled = !visible || !overrideAllowed;
    if (!visible || !controls.statusNode) {
      return;
    }
    if (!currentValue && !officialResolved) {
      controls.statusNode.textContent = "No template-owned LoRA is required for this preset.";
      return;
    }
    if (!officialResolved) {
      controls.statusNode.textContent = `Official template LoRA '${officialLabel || "template-owned LoRA"}' is not available on the current host. Generation can continue; to add a LoRA manually, use <lora:model_name:1> in the prompt.`;
      return;
    }
    if (!currentValue || currentValue === presetDefault) {
      controls.statusNode.textContent = `Official default active: ${officialResolved}`;
      return;
    }
    controls.statusNode.textContent = `Custom override active: ${currentValue}. Official default is ${officialResolved}; exact official template parity no longer applies.`;
  };
  return { resolvePresetDefault, sync };
}
