export function appendTextElement(parent, tagName, className, text, id = "") {
  const node = document.createElement(tagName);
  if (className) {
    node.className = className;
  }
  if (id) {
    node.id = id;
  }
  node.textContent = text;
  parent.appendChild(node);
  return node;
}

export function buildProfileLookup(capabilities) {
  const profiles = capabilities.parity?.profiles ?? [];
  const familyEntries = capabilities.model_families?.entries ?? [];
  const lookup = new Map();
  profiles.forEach((profile) => {
    lookup.set(profile.id, profile);
  });
  familyEntries.forEach((entry) => {
    if (!entry || !entry.id) {
      return;
    }
    const merged = {
      ...(lookup.get(entry.id) ?? {}),
      id: entry.id,
      title: entry.title,
      base_family: entry.translation_base_family || entry.public_base_family || "",
      public_base_family: entry.public_base_family || "",
      text_encoder_visible: Boolean(entry.text_encoder_visible),
      shift_visible: Boolean(entry.shift_visible),
      default_shift: entry.default_shift ?? null,
      flux_guidance_visible: Boolean(entry.flux_guidance_visible),
      default_flux_guidance: entry.default_flux_guidance ?? null,
      prompt_enhancement_visible: Boolean(entry.prompt_enhancement_visible),
      default_prompt_enhancement_enabled: Boolean(entry.default_prompt_enhancement_enabled),
      edit_megapixels_visible: Boolean(entry.edit_megapixels_visible),
      default_edit_megapixels: entry.default_edit_megapixels ?? null,
      template_lora_visible: Boolean(entry.template_lora_visible),
      template_lora_override_allowed: Boolean(entry.template_lora_override_allowed),
      official_template_lora_label: entry.official_template_lora_label || "",
      default_template_lora_enabled: Boolean(entry.default_template_lora_enabled),
      default_template_lora_strength: Number(entry.default_template_lora_strength ?? 1),
      default_template_lora_trigger_word: String(entry.default_template_lora_trigger_word ?? ""),
      template_lora_trigger_visible: Boolean(entry.template_lora_trigger_visible),
      primary_model_category: entry.primary_model_category || "",
      support_tier: entry.support_tier || "",
      experimental: Boolean(entry.experimental),
      compatibility_summary: entry.compatibility_summary || "",
      image_edit_profile: Boolean(entry.image_edit_profile),
      request_contract_surface: String(entry.request_contract_surface || "").trim().toLowerCase(),
      reference_input_mode: String(entry.reference_input_mode || "").trim().toLowerCase(),
      max_direct_references: Number(entry.max_direct_references ?? 0) || 0,
      encoder_family: String(entry.encoder_family || "").trim().toLowerCase(),
      template_lora_chain_mode: String(entry.template_lora_chain_mode || "").trim().toLowerCase(),
      ideogram_modes: Array.isArray(entry.ideogram_modes)
        ? entry.ideogram_modes.map((mode) => String(mode ?? "").trim().toLowerCase()).filter(Boolean)
        : [],
      default_ideogram_mode: String(entry.default_ideogram_mode || "").trim().toLowerCase(),
      aliases: Array.isArray(entry.aliases) ? entry.aliases : [],
      available_surface_flows: Array.isArray(entry.available_surface_flows)
        ? entry.available_surface_flows.map((flow) => String(flow ?? "").trim().toLowerCase()).filter(Boolean)
        : ["txt2img", "img2img"],
    };
    lookup.set(entry.id, merged);
    (Array.isArray(entry.aliases) ? entry.aliases : []).forEach((alias) => {
      const normalizedAlias = String(alias ?? "").trim().toLowerCase();
      if (normalizedAlias) {
        lookup.set(normalizedAlias, merged);
      }
    });
  });
  return lookup;
}

export function syncEffectiveControls(profile, controls) {
  const syncControl = (fieldNode, inputNode, mode, supportedMode, companionNode = null) => {
    if (!fieldNode || !inputNode) return;
    const supported = mode === supportedMode;
    fieldNode.hidden = !supported;
    inputNode.hidden = !supported;
    inputNode.disabled = !supported;
    inputNode.dataset.executionMode = mode;
    if (companionNode) companionNode.hidden = !supported;
    if (!supported) {
      inputNode.value = "";
      inputNode.__syncBinding?.();
    }
  };
  syncControl(controls.schedulerField, controls.schedulerInput, String(profile?.scheduler_control_mode ?? "generic"), "generic");
  syncControl(
    controls.negativePromptField,
    controls.negativePromptInput,
    String(profile?.negative_prompt_mode ?? "encoded"),
    "encoded",
    controls.negativePromptWorkbench,
  );
}

export function readImg2ImgReferencePayload(elements) {
  const imageEditProfile = String(elements.imageEditProfile?.value ?? "").trim().toLowerCase() === "true";
  const maxDirectReferences = Math.max(0, Number(elements.maxDirectReferences?.value ?? 0) || 0);
  const selectedMainSlot = Math.max(0, Number(elements.mainReferenceIndex?.value ?? 0) || 0);
  const orderedReferenceSlots = imageEditProfile
    ? [
        { image_asset: String(elements.imageAsset?.value ?? "").trim(), image_data: String(elements.imageData?.value ?? "").trim() },
        { image_asset: String(elements.referenceAsset2?.value ?? "").trim(), image_data: String(elements.referenceData2?.value ?? "").trim() },
        { image_asset: String(elements.referenceAsset3?.value ?? "").trim(), image_data: String(elements.referenceData3?.value ?? "").trim() },
      ].slice(0, Math.max(1, maxDirectReferences || 1))
    : [];
  const referenceImages = [];
  let mainReferenceIndex = imageEditProfile ? -1 : 0;
  orderedReferenceSlots.forEach((entry, slotIndex) => {
    if (!entry.image_asset && !entry.image_data) {
      return;
    }
    if (slotIndex === selectedMainSlot) {
      mainReferenceIndex = referenceImages.length;
    }
    referenceImages.push(entry);
  });
  return {
    imageEditProfile,
    selectedMainSlot,
    referenceImages,
    mainReferenceIndex,
  };
}

export function buildFeatureList(parent, features) {
  const list = document.createElement("ul");
  list.className = "rookieui-shell__list";
  list.id = "rookieui-feature-list";

  Object.entries(features).forEach(([featureName, enabled]) => {
    const item = document.createElement("li");
    item.className = "rookieui-shell__list-item";
    item.textContent = `${featureName}: ${enabled ? "enabled" : "planned"}`;
    list.appendChild(item);
  });

  parent.appendChild(list);
}

export function buildTabList(parent, tabs) {
  const list = document.createElement("ul");
  list.className = "rookieui-shell__list";
  list.id = "rookieui-tab-list";

  tabs.forEach((tab) => {
    const item = document.createElement("li");
    item.className = "rookieui-shell__list-item";
    item.textContent = `${tab.title} (${tab.state})`;
    list.appendChild(item);
  });

  parent.appendChild(list);
}

export function buildParityList(parent, profiles) {
  const list = document.createElement("ul");
  list.className = "rookieui-shell__list";
  list.id = "rookieui-parity-profile-list";

  profiles.forEach((profile) => {
    const item = document.createElement("li");
    item.className = "rookieui-shell__list-item";
    item.textContent = `${profile.title}: ${profile.base_family} / ${profile.default_sampler} / ${profile.default_scheduler}`;
    list.appendChild(item);
  });

  parent.appendChild(list);
}

export function buildCompatibilityList(parent, entries, id, formatter) {
  const list = document.createElement("ul");
  list.className = "rookieui-shell__list";
  list.id = id;

  entries.forEach((entry) => {
    const item = document.createElement("li");
    item.className = "rookieui-shell__list-item";
    item.textContent = formatter(entry);
    list.appendChild(item);
  });

  parent.appendChild(list);
}

export function createField(parent, labelText, input) {
  const field = document.createElement("label");
  field.className = "rookieui-shell__field";
  const label = document.createElement("span");
  label.className = "rookieui-shell__field-label";
  label.textContent = labelText;
  field.appendChild(label);
  field.appendChild(input);
  parent.appendChild(field);
  return field;
}

export function syncBoundControls(controls) {
  const invoked = new Set();
  controls.forEach((control) => {
    const syncBinding = control?.__syncBinding;
    if (typeof syncBinding === "function" && !invoked.has(syncBinding)) {
      invoked.add(syncBinding);
      syncBinding();
    }
  });
}

export function createInlineCheckboxField(parent, labelText, input) {
  const field = document.createElement("label");
  field.className = "rookieui-shell__inline-checkbox-field";
  const label = document.createElement("span");
  label.className = "rookieui-shell__field-label";
  label.textContent = labelText;
  const toggle = document.createElement("span");
  toggle.className = "rookieui-shell__checkbox-toggle";
  toggle.appendChild(input);
  field.appendChild(label);
  field.appendChild(toggle);
  parent.appendChild(field);
  return field;
}

export function preventSummaryToggleOnCheckbox(toggleInput) {
  if (!toggleInput) {
    return;
  }
  const stopToggle = (event) => {
    event.stopPropagation();
  };
  toggleInput.addEventListener("click", stopToggle);
  toggleInput.addEventListener("mousedown", stopToggle);
  toggleInput.addEventListener("keydown", stopToggle);
}

export function createHiresFixSection(parent, sectionId, hiresEnabledInput, titleText = "Hires. fix") {
  const section = document.createElement("details");
  section.className = "rookieui-shell__section rookieui-shell__section--soft rookieui-shell__hires";
  section.id = sectionId;
  parent.appendChild(section);

  const summary = document.createElement("summary");
  summary.className = "rookieui-shell__hires-summary";
  section.appendChild(summary);

  const header = document.createElement("div");
  header.className = "rookieui-shell__hires-header";
  summary.appendChild(header);

  const toggle = document.createElement("label");
  toggle.className = "rookieui-shell__hires-toggle";
  hiresEnabledInput.setAttribute("aria-label", "Enable Hires fix");
  hiresEnabledInput.title = "Enable Hires fix";
  toggle.appendChild(hiresEnabledInput);
  header.appendChild(toggle);
  preventSummaryToggleOnCheckbox(hiresEnabledInput);

  appendTextElement(header, "span", "rookieui-shell__section-title", titleText);
  appendTextElement(header, "span", "rookieui-shell__hires-caret", "▸", "");

  const grid = document.createElement("div");
  grid.className = "rookieui-shell__grid rookieui-shell__grid--two-column";
  section.appendChild(grid);
  return grid;
}

export function installExplicitFormSubmitShortcuts(form) {
  if (!form) {
    return;
  }
  form.addEventListener(
    "keydown",
    (event) => {
      if (event.key !== "Enter") {
        return;
      }
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const textarea = target.closest("textarea");
      if (textarea) {
        if (event.ctrlKey) {
          // IMPORTANT: plain Enter must keep textarea editing semantics; only Ctrl+Enter is an explicit generate shortcut.
          event.preventDefault();
          form.requestSubmit?.();
        }
        return;
      }
      const submitCandidate = target.closest(
        "input:not([type=\"checkbox\"]):not([type=\"radio\"]):not([type=\"range\"]):not([type=\"submit\"]), select",
      );
      if (!submitCandidate) {
        return;
      }
      // CRITICAL: do not allow browser default Enter submit from parameter inputs/selects; it causes accidental generation while editing fields.
      event.preventDefault();
      if (event.ctrlKey) {
        form.requestSubmit?.();
      }
    },
    true,
  );
}

export function createInput(type, id, value = "", options = {}) {
  const input = document.createElement("input");
  input.className = options.className ?? "rookieui-shell__input";
  input.type = type;
  input.id = id;
  input.value = value;
  if (type === "number" || type === "range") {
    // CRITICAL: browser number inputs default to integer stepping; float-capable controls need explicit step metadata.
    input.step = String(options.step ?? 1);
    if (options.min !== undefined) {
      input.min = String(options.min);
    }
    if (options.max !== undefined) {
      input.max = String(options.max);
    }
    if (type === "number") {
      input.inputMode = options.inputMode ?? (String(input.step).includes(".") ? "decimal" : "numeric");
    }
  }
  return input;
}

export function createCheckbox(id, checked = false) {
  const input = document.createElement("input");
  input.className = "rookieui-shell__checkbox";
  input.type = "checkbox";
  input.id = id;
  input.checked = checked;
  return input;
}

export function createTextarea(id, value = "", rows = 4, options = {}) {
  const input = document.createElement("textarea");
  input.className = options.className ?? "rookieui-shell__textarea";
  input.id = id;
  input.rows = rows;
  input.value = value;
  return input;
}

export function createSelect(id, options, selectedValue, selectOptions = {}) {
  const select = document.createElement("select");
  select.className = selectOptions.className ?? "rookieui-shell__select";
  select.id = id;

  options.forEach((option) => {
    const element = document.createElement("option");
    element.value = option.value;
    element.textContent = option.label;
    if (option.value === selectedValue) {
      element.selected = true;
    }
    select.appendChild(element);
  });

  return select;
}

export function createRangeInput(id, value = "", options = {}) {
  const input = createInput("range", id, value, {
    className: "rookieui-shell__slider",
    min: options.min,
    max: options.max,
    step: options.step,
  });
  const syncVisual = () => {
    const min = Number(input.min || 0);
    const max = Number(input.max || 100);
    const valueNumber = Number(input.value || min);
    const ratio = max > min ? ((valueNumber - min) / (max - min)) * 100 : 0;
    // IMPORTANT: keep slider progress explicit; Chromium accent-color alone cannot recreate the A1111 white-track and blue-progress look.
    input.style.setProperty("--rookieui-slider-progress", `${Math.min(100, Math.max(0, ratio))}%`);
  };
  input.__syncSliderVisual = syncVisual;
  input.addEventListener("input", syncVisual);
  input.addEventListener("change", syncVisual);
  syncVisual();
  return input;
}

export function bindSliderPair(numberInput, rangeInput) {
  const syncFromNumber = () => {
    if (numberInput.value !== "") {
      rangeInput.value = numberInput.value;
    }
    rangeInput.disabled = numberInput.disabled;
    rangeInput.__syncSliderVisual?.();
  };
  const syncFromRange = () => {
    numberInput.value = rangeInput.value;
    rangeInput.__syncSliderVisual?.();
  };
  numberInput.addEventListener("input", syncFromNumber);
  rangeInput.addEventListener("input", () => {
    syncFromRange();
    syncFromNumber();
  });
  numberInput.__syncBinding = syncFromNumber;
  rangeInput.__syncBinding = syncFromNumber;
  syncFromNumber();
}

export function createSliderField(parent, labelText, numberInput, rangeInput, id = "") {
  const field = document.createElement("div");
  field.className = "rookieui-shell__slider-field";
  if (id) {
    field.id = id;
  }
  const header = document.createElement("div");
  header.className = "rookieui-shell__slider-field-header";
  field.appendChild(header);
  const label = document.createElement("span");
  label.className = "rookieui-shell__field-label";
  label.textContent = labelText;
  header.appendChild(label);
  header.appendChild(numberInput);
  field.appendChild(rangeInput);
  parent.appendChild(field);
  return field;
}

export function generateDeterministicSeed() {
  const high = Math.floor(Math.random() * 0x100000000);
  const low = Math.floor(Math.random() * 0x100000000);
  return Number((BigInt(high) << 32n) | BigInt(low));
}
