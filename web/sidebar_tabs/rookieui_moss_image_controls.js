import { isMossImageProfile, MOSS_IMAGE_ASSET_ROLES } from "../rookieui_moss_image_profiles.js";
import { createMossLayoutEditor } from "./rookieui_moss_layout_editor.js";

export function matchesMossAsset(profile, selector, role) {
  const basename = String(selector ?? "").replaceAll("\\", "/").split("/").pop().toLowerCase();
  return MOSS_IMAGE_ASSET_ROLES[profile]?.[role]?.includes(basename) ?? false;
}

export function createMossImagePaneControls({ elements, form, submitButton, profileLookup, bootstrapState,
  isBusy, createInlineCheckboxField }) {
  const field = document.createElement("div");
  field.id = "rookieui-moss-controls";
  field.style.gridColumn = "1 / -1";
  elements.mossLayoutState = Object.assign(document.createElement("input"), { type: "hidden", id: "rookieui-moss-layout-state", value: "" });
  elements.mossSlgExplicit = Object.assign(document.createElement("input"), { type: "hidden", id: "rookieui-moss-slg-explicit", value: "" });
  field.append(elements.mossLayoutState, elements.mossSlgExplicit);
  createInlineCheckboxField(field, "Skip Layer Guidance (SLG)", elements.mossSlgEnabled);
  const status = document.createElement("p");
  status.id = "rookieui-moss-status";
  status.className = "rookieui-shell__status";
  status.setAttribute("role", "status");
  field.appendChild(status);
  return { field, ...createMossImageController({ elements, form, submitButton, profileLookup,
    capabilities: bootstrapState.capabilities, inventory: bootstrapState.models ?? {}, field, status, isBusy }) };
}

function replaceOptions(input, values, preferred, strict = false) {
  if (input.tagName !== "SELECT") return;
  input.replaceChildren(...values.map(value => new Option(value, value)));
  if (!values.length) input.add(new Option("No matching installed model", ""));
  input.value = values.includes(preferred) ? preferred : strict ? "" : values[0] ?? "";
}

export function createMossImageController({ elements, form, submitButton, profileLookup, capabilities,
  inventory, field, status, isBusy = () => false }) {
  const disabledBefore = new Map();
  let previousProfile = "";
  let available = true;
  const unsupportedKeys = ["lowBits", "clipSkip", "clipSkipSlider", "shift", "fluxGuidance",
    "promptEnhancementEnabled", "templateLoraName", "templateLoraEnabled", "templateLoraStrength",
    "templateLoraTriggerWord", "loraName", "loraStrengthModel", "loraStrengthClip", "hiresEnabled",
    "hiresScale", "hiresScaleSlider", "hiresSteps", "hiresStepsSlider", "hiresDenoise", "hiresDenoiseSlider",
    "hiresUpscaleMethod", "adetailer", "controlnetUnits"];
  const roleControls = [["checkpoint", "diffusion_models"], ["textEncoder", "text_encoders"], ["vae", "vae"]];
  const valuesFor = role => inventory.catalog?.categories?.[role]?.items ?? inventory[role] ?? [];
  const layoutController = elements.mossLayoutState ? createMossLayoutEditor({ container: field, elements,
    onChange: () => sync(), onModeChange: enabled => {
      if (elements.mossSlgExplicit.value !== "true") elements.mossSlgEnabled.checked = enabled ||
        profileLookup.get(elements.profileState.value)?.default_moss_slg_enabled === true;
    } }) : null;
  const sync = ({ resetDefaults = false, payload = null } = {}) => {
    const id = elements.profileState.value;
    const active = isMossImageProfile(id);
    field.hidden = !active;
    status.hidden = !active;
    elements.mossSlgEnabled.disabled = !active;
    if (active && resetDefaults) elements.mossSlgEnabled.checked = profileLookup.get(id)?.default_moss_slg_enabled === true;
    if (active && resetDefaults && elements.mossSlgExplicit) elements.mossSlgExplicit.value = "";
    if (active && typeof payload?.moss_options?.slg_enabled === "boolean") {
      elements.mossSlgEnabled.checked = payload.moss_options.slg_enabled;
      if (elements.mossSlgExplicit) elements.mossSlgExplicit.value = "true";
    }
    layoutController?.sync({ resetDefaults: active && resetDefaults, payload: active ? payload : null });
    if (active && (resetDefaults || previousProfile !== id || payload)) {
      const payloadKeys = { checkpoint: "checkpoint_name", textEncoder: "text_encoder_name", vae: "vae_name" };
      roleControls.forEach(([key, role]) => {
        const explicit = payload && Object.hasOwn(payload, payloadKeys[key]);
        replaceOptions(elements[key], valuesFor(role).filter(value => matchesMossAsset(id, value, role)),
          explicit ? payload[payloadKeys[key]] : elements[key].value, Boolean(explicit));
      });
    } else if (!active && isMossImageProfile(previousProfile)) {
      roleControls.filter(([key]) => key !== "checkpoint").forEach(([key, role]) =>
        replaceOptions(elements[key], valuesFor(role), elements[key].value));
    }
    const unsupported = new Set(unsupportedKeys.map(key => elements[key]).filter(Boolean));
    form.querySelectorAll('[id^="rookieui-txt2img-adetailer"], [id^="rookieui-txt2img-controlnet"]').forEach(node => {
      if (node.matches("input,select,textarea,button")) unsupported.add(node);
      node.querySelectorAll("input,select,textarea,button").forEach(child => unsupported.add(child));
    });
    unsupported.forEach(input => {
      if (active) {
        if (!disabledBefore.has(input)) disabledBefore.set(input, input.disabled);
        input.disabled = true;
      } else if (disabledBefore.has(input)) {
        input.disabled = disabledBefore.get(input);
        disabledBefore.delete(input);
      }
    });
    [elements.width, elements.widthSlider, elements.height, elements.heightSlider].filter(Boolean)
      .forEach(input => { input.step = active ? "16" : "8"; });
    const capability = capabilities?.moss_image?.profiles?.[id];
    const slg = elements.mossSlgEnabled.checked;
    const hostAvailable = capability?.[slg ? "slg_available" : "without_slg_available"] === true;
    const reasons = [...(capability?.[slg ? "slg_reasons" : "without_slg_reasons"] ??
      ["MOSS host capability has not been verified."])];
    if (active) {
      const profile = profileLookup.get(id);
      [[elements.sampler, profile?.default_sampler], [elements.scheduler, profile?.default_scheduler]].forEach(([input, expected]) => {
        if (input?.tagName === "SELECT" && !Array.from(input.options).some(option => option.value === expected)) {
          reasons.push(`Refresh the host sampler catalog; MOSS requires ${expected}.`);
        }
      });
      roleControls.forEach(([key, role]) => {
        if (!matchesMossAsset(id, elements[key].value, role)) reasons.push(`Select a matching installed MOSS ${role} model.`);
      });
    }
    available = !active || (hostAvailable && reasons.length === 0 && (layoutController?.valid() ?? true));
    status.textContent = available
      ? "Native MOSS prompts and SLG. LoRA, Hires, ControlNet, ADetailer, CLIP skip and prompt enhancement are unavailable."
      : reasons.join(" ");
    submitButton.disabled = isBusy() || !available;
    previousProfile = id;
  };
  elements.mossSlgEnabled.addEventListener("change", () => {
    if (elements.mossSlgExplicit) elements.mossSlgExplicit.value = "true";
    sync();
  });
  roleControls.forEach(([key]) => elements[key].addEventListener("change", () => sync()));
  return { sync, canSubmit: () => available };
}
