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
