function clearChildren(node) {
  if (node) {
    node.replaceChildren();
  }
}

function parseAxisRows(axisRows) {
  return axisRows
    .map((row) => ({
      slot: row.slot,
      axis_id: String(row.select.value ?? "").trim(),
      values: String(getAxisRowValue(row) ?? "").trim(),
    }))
    .filter((row) => row.axis_id && row.values);
}

function normalizeAxisCatalog(rawAxes, mode) {
  const axes = rawAxes && typeof rawAxes === "object" ? Object.values(rawAxes) : [];
  return axes
    .filter((entry) => entry && typeof entry === "object")
    .filter((entry) => String(entry.support_tier ?? "") !== "not_supported_yet")
    .filter((entry) => Boolean(entry.session_runner_support))
    .filter((entry) => Array.isArray(entry.mode_scopes) && entry.mode_scopes.includes(mode))
    .sort((left, right) => String(left.title ?? "").localeCompare(String(right.title ?? "")));
}

function buildFallbackValues(axis) {
  const axisId = String(axis?.axis_id ?? "").trim();
  const inputMode = String(axis?.value_input_mode ?? "").trim();
  const choices = Array.isArray(axis?.choices) ? axis.choices.filter(Boolean) : [];
  if (choices.length) {
    return choices.slice(0, 3).join(", ");
  }
  if (inputMode === "size_csv") {
    return "512x512, 768x768, 1024x1024";
  }
  if (inputMode === "csv_pairs") {
    return "cat -> dog, dusk -> dawn";
  }
  if (inputMode === "permutation_csv") {
    return "cat, dog, bird";
  }
  if (axisId === "seed") {
    return "1, 2, 3";
  }
  if (axisId === "steps") {
    return "20, 28, 36";
  }
  if (axisId === "cfg_scale") {
    return "5.5, 7, 8.5";
  }
  if (axisId === "clip_skip") {
    return "1, 2, 3";
  }
  if (axisId === "denoising_strength") {
    return "0.35, 0.5, 0.65";
  }
  if (axisId === "hires_steps") {
    return "8, 12, 16";
  }
  return "";
}

function buildAxisHint(axis) {
  if (!axis) {
    return "Select an axis to sweep.";
  }
  const reference = String(axis.a1111_reference_label ?? "").trim();
  const tier = String(axis.support_tier ?? "").trim();
  const mode = String(axis.value_input_mode ?? "").trim();
  const notes = Array.isArray(axis.notes) ? axis.notes.filter(Boolean) : [];
  const summary = [`${reference || axis.title}`, `${tier} parity`, mode.replaceAll("_", " ")];
  if (notes[0]) {
    summary.push(notes[0]);
  }
  return summary.join(" | ");
}

function renderWarnings(target, warnings, warningCodes) {
  const normalizedWarnings = Array.isArray(warnings) ? warnings.filter(Boolean) : [];
  const normalizedCodes = Array.isArray(warningCodes) ? warningCodes.filter(Boolean) : [];
  const lines = [];
  normalizedCodes.forEach((code) => lines.push(String(code)));
  normalizedWarnings.forEach((warning) => lines.push(String(warning)));
  target.textContent = lines.length ? lines.join(" | ") : "No warnings";
  target.dataset.empty = String(lines.length === 0);
}

function createCheckboxRow(id, label, checked = false) {
  const labelNode = document.createElement("label");
  labelNode.className = "rookieui-shell__xyz-plot-option";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.id = id;
  input.checked = checked;
  labelNode.appendChild(input);
  const text = document.createElement("span");
  text.className = "rookieui-shell__field-label rookieui-shell__xyz-plot-option-label";
  text.textContent = label;
  labelNode.appendChild(text);
  return { root: labelNode, input };
}

function coerceNumber(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

const XYZ_DROPDOWN_AXIS_IDS = new Set([
  "checkpoint_name",
  "sampler",
  "scheduler",
  "vae",
  "hires_upscaler",
]);

function axisUsesChoiceDropdown(axis) {
  const axisId = String(axis?.axis_id ?? "").trim();
  const inputMode = String(axis?.value_input_mode ?? "").trim();
  const choices = Array.isArray(axis?.choices) ? axis.choices.filter(Boolean) : [];
  return XYZ_DROPDOWN_AXIS_IDS.has(axisId) && inputMode === "choices_or_csv" && choices.length > 0;
}

function parseChoiceValueList(value) {
  if (Array.isArray(value)) {
    return value.map((entry) => String(entry ?? "").trim()).filter(Boolean);
  }
  return String(value ?? "")
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function buildChoiceSummaryText(values) {
  const normalizedValues = Array.isArray(values) ? values.filter(Boolean) : [];
  if (!normalizedValues.length) {
    return "Select values";
  }
  if (normalizedValues.length <= 2) {
    return normalizedValues.join(", ");
  }
  return `${normalizedValues.length} selected`;
}

function getAxisRowSelectedValues(row) {
  return Array.isArray(row.choiceOptions)
    ? row.choiceOptions.filter((entry) => entry.input.checked).map((entry) => entry.value)
    : [];
}

function closeAxisRowChoiceDropdown(row) {
  if (row?.choiceRoot) {
    row.choiceRoot.open = false;
  }
}

function axisRowHasAllChoicesSelected(row) {
  if (!Array.isArray(row?.choiceOptions) || !row.choiceOptions.length) {
    return false;
  }
  return row.choiceOptions.every((entry) => entry.input.checked);
}

function syncAxisRowChoiceSummary(row) {
  if (!row.choiceSummaryText) {
    return;
  }
  const selectedValues = getAxisRowSelectedValues(row);
  const summaryText = buildChoiceSummaryText(selectedValues);
  row.choiceSummaryText.textContent = summaryText;
  row.choiceSummaryText.title = selectedValues.length ? selectedValues.join(", ") : summaryText;
}

function rebuildAxisRowChoiceOptions(row, choices) {
  clearChildren(row.choiceOptionList);
  row.choiceOptions = [];
  choices.forEach((choice, index) => {
    const label = document.createElement("label");
    label.className = "rookieui-shell__xyz-plot-choice-option";

    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = String(choice);
    input.id = `${row.choiceRoot.id}-option-${index}`;
    input.addEventListener("change", () => {
      syncAxisRowChoiceSummary(row);
    });
    label.appendChild(input);

    const text = document.createElement("span");
    text.className = "rookieui-shell__xyz-plot-choice-option-text";
    text.textContent = String(choice);
    text.title = String(choice);
    label.appendChild(text);

    row.choiceOptionList.appendChild(label);
    row.choiceOptions.push({ value: String(choice), input });
  });
}

function getAxisRowValue(row) {
  return row.usesChoiceDropdown ? getAxisRowSelectedValues(row).join(", ") : row.valueInput.value;
}

function setAxisRowValue(row, value) {
  if (row.usesChoiceDropdown) {
    const selectedValues = new Set(parseChoiceValueList(value));
    row.choiceOptions.forEach((entry) => {
      entry.input.checked = selectedValues.has(entry.value);
    });
    syncAxisRowChoiceSummary(row);
    return;
  }
  row.valueInput.value = String(value ?? "");
}

export function createXYZPlotShell({
  idPrefix,
  parent,
  mode,
  bootstrapState,
  buildBaseRequest,
  appendTextElement,
  createActionButton,
  createIconActionButton,
  createPreviewFullscreenViewer,
  syncPrimaryPreview,
  onStatusMessage,
} = {}) {
  const shell = document.createElement("details");
  shell.id = `${idPrefix}-section`;
  shell.className = "rookieui-shell__section rookieui-shell__section--soft rookieui-shell__hires rookieui-shell__xyz-plot";
  shell.open = false;
  parent.appendChild(shell);

  const axisCatalog = normalizeAxisCatalog(bootstrapState?.xyzPlot?.axes ?? {}, mode);
  const axisOptions = [{ value: "", label: "Disabled" }].concat(
    axisCatalog.map((entry) => ({
      value: String(entry.axis_id ?? ""),
      label: String(entry.title ?? entry.axis_id ?? ""),
    })),
  );
  const axisLookup = new Map(axisCatalog.map((entry) => [String(entry.axis_id ?? ""), entry]));
  const state = {
    activeSessionId: "",
    pollTimer: null,
    axesLoaded: axisCatalog.length > 0,
    axisCatalog,
  };

  const summary = document.createElement("summary");
  summary.className = "rookieui-shell__hires-summary rookieui-shell__xyz-plot-summary-bar";
  shell.appendChild(summary);

  const header = document.createElement("div");
  header.className = "rookieui-shell__hires-header";
  summary.appendChild(header);
  appendTextElement(header, "span", "rookieui-shell__hires-title", "XYZ Plot");
  appendTextElement(header, "span", "rookieui-shell__hires-caret", "▸");

  const body = document.createElement("div");
  body.className = "rookieui-shell__xyz-plot-body";
  shell.appendChild(body);

  appendTextElement(
    body,
    "p",
    "rookieui-shell__status rookieui-shell__xyz-plot-note",
    `Bottom-mounted sweep surface for ${mode}. It stays below ControlNet / ADetailer blocks by design.`,
  );

  const leftColumn = document.createElement("div");
  leftColumn.className = "rookieui-shell__xyz-plot-column";
  body.appendChild(leftColumn);

  const rightColumn = document.createElement("div");
  rightColumn.className = "rookieui-shell__xyz-plot-column rookieui-shell__xyz-plot-column--results";
  body.appendChild(rightColumn);

  const setupSection = document.createElement("section");
  setupSection.className = "rookieui-shell__xyz-plot-card";
  leftColumn.appendChild(setupSection);
  appendTextElement(setupSection, "h5", "rookieui-shell__xyz-plot-card-title", "Plot Setup");

  const setupSummary = appendTextElement(
    setupSection,
    "p",
    "rookieui-shell__xyz-plot-summary",
    "Import the current txt2img / img2img form as the baseline request and sweep one to three axes.",
  );
  setupSummary.id = `${idPrefix}-setup-summary`;

  const axisHost = document.createElement("div");
  axisHost.className = "rookieui-shell__xyz-plot-axis-host";
  setupSection.appendChild(axisHost);

  const axisRows = ["X", "Y", "Z"].map((slot, index) => {
    const row = document.createElement("div");
    row.className = "rookieui-shell__xyz-plot-axis-row";
    axisHost.appendChild(row);

    appendTextElement(row, "strong", "rookieui-shell__xyz-plot-axis-slot", slot);

    const select = document.createElement("select");
    select.id = `${idPrefix}-axis-${slot.toLowerCase()}-select`;
    select.className = "rookieui-shell__input rookieui-shell__xyz-plot-axis-select";
    axisOptions.forEach((entry) => {
      const option = document.createElement("option");
      option.value = entry.value;
      option.textContent = entry.label;
      select.appendChild(option);
    });
    if (index === 0 && axisLookup.has("steps")) {
      select.value = "steps";
    }
    if (index === 1 && axisLookup.has("cfg_scale")) {
      select.value = "cfg_scale";
    }
    if (index === 2 && axisLookup.has("seed")) {
      select.value = "seed";
    }
    row.appendChild(select);

    const valueInput = document.createElement("input");
    valueInput.type = "text";
    valueInput.id = `${idPrefix}-axis-${slot.toLowerCase()}-values`;
    valueInput.className = "rookieui-shell__input rookieui-shell__xyz-plot-axis-values";
    row.appendChild(valueInput);

    const choiceRoot = document.createElement("details");
    choiceRoot.id = `${idPrefix}-axis-${slot.toLowerCase()}-values-multiselect`;
    choiceRoot.className = "rookieui-shell__xyz-plot-choice-dropdown";
    choiceRoot.hidden = true;
    row.appendChild(choiceRoot);

    const choiceSummary = document.createElement("summary");
    choiceSummary.id = `${idPrefix}-axis-${slot.toLowerCase()}-values-summary`;
    choiceSummary.className = "rookieui-shell__xyz-plot-choice-summary";
    choiceRoot.appendChild(choiceSummary);
    const choiceSummaryText = document.createElement("span");
    choiceSummaryText.className = "rookieui-shell__xyz-plot-choice-summary-text";
    choiceSummaryText.textContent = "Select values";
    choiceSummary.appendChild(choiceSummaryText);
    appendTextElement(choiceSummary, "span", "rookieui-shell__xyz-plot-choice-caret", "▾");

    const choicePanel = document.createElement("div");
    choicePanel.className = "rookieui-shell__xyz-plot-choice-panel";
    choiceRoot.appendChild(choicePanel);

    const choiceOptionList = document.createElement("div");
    choiceOptionList.id = `${idPrefix}-axis-${slot.toLowerCase()}-values-options`;
    choiceOptionList.className = "rookieui-shell__xyz-plot-choice-options";
    choicePanel.appendChild(choiceOptionList);

    const fillButton = createActionButton(`${idPrefix}-axis-${slot.toLowerCase()}-fill`, "Fill");
    fillButton.classList.add("rookieui-shell__button--secondary");
    row.appendChild(fillButton);

    const hint = appendTextElement(row, "p", "rookieui-shell__xyz-plot-axis-hint", "Select an axis to sweep.");
    hint.id = `${idPrefix}-axis-${slot.toLowerCase()}-hint`;

    return {
      slot,
      row,
      select,
      valueInput,
      choiceRoot,
      choiceSummaryText,
      choiceOptionList,
      fillButton,
      hint,
      choiceOptions: [],
      usesChoiceDropdown: false,
    };
  });

  function closeChoiceDropdowns(exceptRow = null) {
    axisRows.forEach((row) => {
      if (row !== exceptRow) {
        closeAxisRowChoiceDropdown(row);
      }
    });
  }

  const swapRow = document.createElement("div");
  swapRow.className = "rookieui-shell__xyz-plot-swap-row";
  setupSection.appendChild(swapRow);
  const swapButtons = [
    { id: "xy", label: "Swap X/Y", left: 0, right: 1 },
    { id: "yz", label: "Swap Y/Z", left: 1, right: 2 },
    { id: "xz", label: "Swap X/Z", left: 0, right: 2 },
  ].map((entry) => {
    const button = createActionButton(`${idPrefix}-swap-${entry.id}`, entry.label);
    button.classList.add("rookieui-shell__button--secondary");
    swapRow.appendChild(button);
    return { ...entry, button };
  });

  const optionsSection = document.createElement("section");
  optionsSection.className = "rookieui-shell__xyz-plot-card";
  leftColumn.appendChild(optionsSection);
  appendTextElement(optionsSection, "h5", "rookieui-shell__xyz-plot-card-title", "Plot Options");

  const optionGrid = document.createElement("div");
  optionGrid.className = "rookieui-shell__xyz-plot-options";
  optionsSection.appendChild(optionGrid);
  const drawLegend = createCheckboxRow(`${idPrefix}-draw-legend`, "Draw legend", true);
  const includeLoneImages = createCheckboxRow(`${idPrefix}-include-lone-images`, "Include lone images", false);
  const includeSubGrids = createCheckboxRow(`${idPrefix}-include-sub-grids`, "Include sub-grids", false);
  const keepNegativeOneSeed = createCheckboxRow(
    `${idPrefix}-keep-negative-one-seed`,
    "Keep -1 for seeds",
    false,
  );
  const varySeedsX = createCheckboxRow(`${idPrefix}-vary-seeds-x`, "Vary seeds for X", false);
  const varySeedsY = createCheckboxRow(`${idPrefix}-vary-seeds-y`, "Vary seeds for Y", false);
  const varySeedsZ = createCheckboxRow(`${idPrefix}-vary-seeds-z`, "Vary seeds for Z", false);
  optionGrid.append(
    drawLegend.root,
    includeLoneImages.root,
    includeSubGrids.root,
    keepNegativeOneSeed.root,
    varySeedsX.root,
    varySeedsY.root,
    varySeedsZ.root,
  );

  const marginRow = document.createElement("label");
  marginRow.className = "rookieui-shell__xyz-plot-margin";
  appendTextElement(marginRow, "span", "rookieui-shell__field-label", "Grid margin");
  const marginInput = document.createElement("input");
  marginInput.type = "number";
  marginInput.id = `${idPrefix}-margin-size`;
  marginInput.className = "rookieui-shell__input";
  marginInput.min = "0";
  marginInput.max = "500";
  marginInput.step = "1";
  marginInput.value = "0";
  marginRow.appendChild(marginInput);
  optionsSection.appendChild(marginRow);

  const actionRow = document.createElement("div");
  actionRow.className = "rookieui-shell__xyz-plot-actions";
  leftColumn.appendChild(actionRow);
  const estimateButton = createActionButton(`${idPrefix}-estimate`, "Estimate");
  const runButton = createActionButton(`${idPrefix}-run`, "Run XYZ Plot");
  const refreshButton = createActionButton(`${idPrefix}-refresh`, "Refresh");
  const cancelButton = createActionButton(`${idPrefix}-cancel`, "Cancel Session");
  [estimateButton, runButton, refreshButton, cancelButton].forEach((button) => {
    button.classList.remove("rookieui-shell__button--secondary");
    button.classList.add("rookieui-shell__xyz-plot-action");
  });
  [estimateButton, runButton, refreshButton].forEach((button) => {
    button.classList.add("rookieui-shell__button--accent");
  });
  // IMPORTANT: keep the XYZ cancel action on its own Ferrari-red lane; the shared danger token is intentionally softer elsewhere.
  cancelButton.classList.add("rookieui-shell__button--danger", "rookieui-shell__xyz-plot-action--danger");
  [estimateButton, runButton, refreshButton, cancelButton].forEach((button) => actionRow.appendChild(button));

  const estimateSection = document.createElement("section");
  estimateSection.className = "rookieui-shell__xyz-plot-card";
  rightColumn.appendChild(estimateSection);
  appendTextElement(estimateSection, "h5", "rookieui-shell__xyz-plot-card-title", "Estimate");

  const estimateGrid = document.createElement("div");
  estimateGrid.className = "rookieui-shell__xyz-plot-estimate-grid";
  estimateSection.appendChild(estimateGrid);
  const estimateNodes = {};
  ["Cells", "Images", "Steps", "Grid MP"].forEach((label) => {
    const card = document.createElement("article");
    card.className = "rookieui-shell__xyz-plot-metric";
    appendTextElement(card, "span", "rookieui-shell__xyz-plot-metric-label", label);
    const valueNode = document.createElement("strong");
    valueNode.className = "rookieui-shell__xyz-plot-metric-value";
    valueNode.textContent = "0";
    card.appendChild(valueNode);
    estimateGrid.appendChild(card);
    estimateNodes[label] = valueNode;
  });
  const warningsNode = appendTextElement(estimateSection, "p", "rookieui-shell__xyz-plot-warnings", "No warnings");
  warningsNode.id = `${idPrefix}-warnings`;

  const sessionSection = document.createElement("section");
  sessionSection.className = "rookieui-shell__xyz-plot-card";
  rightColumn.appendChild(sessionSection);
  appendTextElement(sessionSection, "h5", "rookieui-shell__xyz-plot-card-title", "Session");
  const sessionStatusNode = appendTextElement(
    sessionSection,
    "p",
    "rookieui-shell__xyz-plot-session-status",
    "Idle",
  );
  sessionStatusNode.id = `${idPrefix}-session-status`;
  const sessionSummaryNode = appendTextElement(
    sessionSection,
    "p",
    "rookieui-shell__xyz-plot-session-summary",
    "No active session",
  );
  sessionSummaryNode.id = `${idPrefix}-session-summary`;

  const resultSection = document.createElement("section");
  resultSection.className = "rookieui-shell__xyz-plot-card";
  rightColumn.appendChild(resultSection);
  appendTextElement(resultSection, "h5", "rookieui-shell__xyz-plot-card-title", "Results");
  const previewBox = document.createElement("div");
  previewBox.id = `${idPrefix}-main-grid-preview`;
  previewBox.className = "rookieui-shell__preview-box rookieui-shell__preview-box--compact rookieui-shell__xyz-plot-preview";
  resultSection.appendChild(previewBox);
  appendTextElement(previewBox, "span", "rookieui-shell__preview-placeholder", "No XYZ plot grid yet.");

  const previewToolbar = document.createElement("div");
  previewToolbar.className = "rookieui-shell__preview-toolbar";
  previewToolbar.hidden = true;
  resultSection.appendChild(previewToolbar);

  const previewViewer =
    typeof createIconActionButton === "function" && typeof createPreviewFullscreenViewer === "function"
      ? createPreviewFullscreenViewer({
          idPrefix,
          previewBox,
          previewToolbar,
          createIconActionButton,
          statusNode: sessionStatusNode,
          labelText: "Preview",
        })
      : null;

  const resultSummaryNode = appendTextElement(
    resultSection,
    "p",
    "rookieui-shell__xyz-plot-result-summary",
    "Sub-grids: 0 | Lone images: 0",
  );
  resultSummaryNode.id = `${idPrefix}-result-summary`;

  function setPreview(dataUrl) {
    previewBox.replaceChildren();
    if (typeof dataUrl === "string" && dataUrl.trim()) {
      const image = document.createElement("img");
      image.className = "rookieui-shell__preview-image";
      image.src = dataUrl;
      image.alt = "XYZ Plot grid preview";
      previewBox.appendChild(image);
    } else {
      appendTextElement(previewBox, "span", "rookieui-shell__preview-placeholder", "No XYZ plot grid yet.");
    }
    previewViewer?.syncImage?.();
    previewBox.__previewFullscreenController?.syncImage?.();
  }

  function collectPayload() {
    return {
      mode,
      client_id: String(bootstrapState?.clientId ?? "").trim(),
      max_parallel: 1,
      base_request: buildBaseRequest?.() ?? {},
      axes: parseAxisRows(axisRows).map((entry) => ({
        axis_id: entry.axis_id,
        values: entry.values,
      })),
      draw_legend: drawLegend.input.checked,
      include_lone_images: includeLoneImages.input.checked,
      include_sub_grids: includeSubGrids.input.checked,
      keep_negative_one_seed: keepNegativeOneSeed.input.checked,
      vary_seeds_x: varySeedsX.input.checked,
      vary_seeds_y: varySeedsY.input.checked,
      vary_seeds_z: varySeedsZ.input.checked,
      margin_size: coerceNumber(marginInput.value, 0),
    };
  }

  function syncAxisRow(row) {
    const axis = axisLookup.get(String(row.select.value ?? "").trim());
    row.usesChoiceDropdown = axisUsesChoiceDropdown(axis);
    const nextValue = getAxisRowValue(row);
    row.valueInput.hidden = row.usesChoiceDropdown;
    row.choiceRoot.hidden = !row.usesChoiceDropdown;
    row.valueInput.disabled = !axis || row.usesChoiceDropdown;
    row.valueInput.placeholder = axis ? buildFallbackValues(axis) : "";
    if (row.usesChoiceDropdown) {
      const choices = Array.isArray(axis?.choices) ? axis.choices.filter(Boolean) : [];
      rebuildAxisRowChoiceOptions(row, choices);
      setAxisRowValue(row, nextValue);
    } else {
      row.choiceRoot.open = false;
      clearChildren(row.choiceOptionList);
      row.choiceOptions = [];
      row.valueInput.value = nextValue;
    }
    row.fillButton.disabled = !axis;
    row.hint.textContent = buildAxisHint(axis);
  }

  function syncEstimatePayload(result) {
    const estimate = result?.data?.estimate ?? {};
    estimateNodes.Cells.textContent = String(estimate.cell_count ?? 0);
    estimateNodes.Images.textContent = String(estimate.generated_image_count ?? 0);
    estimateNodes.Steps.textContent = String(
      estimate.total_step_estimate ?? estimate.total_steps ?? 0,
    );
    estimateNodes["Grid MP"].textContent = String(
      estimate.projected_grid_megapixels ?? 0,
    );
    renderWarnings(warningsNode, result?.data?.warnings, result?.data?.warning_codes);
  }

  function stopPolling() {
    if (state.pollTimer) {
      clearTimeout(state.pollTimer);
      state.pollTimer = null;
    }
  }

  function schedulePoll() {
    stopPolling();
    if (!state.activeSessionId) {
      return;
    }
    state.pollTimer = setTimeout(() => {
      void refreshSessionDetail();
    }, 1200);
  }

  function syncSessionPayload(session) {
    const normalizedSession = session && typeof session === "object" ? session : {};
    const summary = normalizedSession.summary ?? {};
    state.activeSessionId = String(normalizedSession.session_id ?? state.activeSessionId ?? "").trim();
    sessionStatusNode.textContent = `Status: ${String(normalizedSession.status ?? "idle")}`;
    sessionSummaryNode.textContent = [
      `Session: ${state.activeSessionId || "none"}`,
      `Cells ${summary.completed_cells ?? 0}/${summary.total_cells ?? 0}`,
      `Queued ${summary.queued_cells ?? 0}`,
      `Failed ${summary.failed_cells ?? 0}`,
    ].join(" | ");
    const results = normalizedSession.results ?? {};
    const mainGridPreview = String(results?.main_grid?.preview_data_url ?? "");
    setPreview(mainGridPreview);
    if (mainGridPreview && typeof syncPrimaryPreview === "function") {
      // IMPORTANT: XYZ sessions must drive the pane's primary preview as well as the local Results card; removing this reintroduces the "top preview stays empty" regression.
      syncPrimaryPreview(mainGridPreview, {
        session: normalizedSession,
        results,
      });
    }
    resultSummaryNode.textContent = `Sub-grids: ${Array.isArray(results.sub_grids) ? results.sub_grids.length : 0} | Lone images: ${
      Array.isArray(results.lone_images) ? results.lone_images.length : 0
    }`;
    renderWarnings(warningsNode, results?.warnings, []);
    const status = String(normalizedSession.status ?? "");
    cancelButton.disabled = !state.activeSessionId || ["completed", "failed", "cancelled"].includes(status);
    if (["pending", "queued", "in_progress", "running"].includes(status)) {
      schedulePoll();
    } else {
      stopPolling();
    }
  }

  async function ensureAxisCatalogLoaded() {
    if (state.axesLoaded || typeof bootstrapState?.fetchXYZPlotAxesRequest !== "function") {
      return;
    }
    const result = await bootstrapState.fetchXYZPlotAxesRequest();
    if (result?.data?.axes && typeof result.data.axes === "object") {
      state.axisCatalog = normalizeAxisCatalog(result.data.axes, mode);
      state.axesLoaded = true;
    }
  }

  async function refreshSessionList() {
    if (typeof bootstrapState?.fetchXYZPlotSessionsRequest !== "function") {
      return;
    }
    const result = await bootstrapState.fetchXYZPlotSessionsRequest(String(bootstrapState?.clientId ?? "").trim());
    const sessions = Array.isArray(result?.data?.sessions) ? result.data.sessions : [];
    if (!state.activeSessionId && sessions[0]?.session_id) {
      state.activeSessionId = String(sessions[0].session_id);
    }
  }

  async function refreshSessionDetail() {
    if (!state.activeSessionId || typeof bootstrapState?.fetchXYZPlotSessionDetailRequest !== "function") {
      return;
    }
    const result = await bootstrapState.fetchXYZPlotSessionDetailRequest(
      state.activeSessionId,
      String(bootstrapState?.clientId ?? "").trim(),
    );
    if (result?.ok) {
      syncSessionPayload(result.data.session);
      onStatusMessage?.(`XYZ Plot session ${state.activeSessionId} refreshed`);
      return;
    }
    sessionStatusNode.textContent = `Status: ${String(result?.data?.status ?? "error")}`;
    stopPolling();
  }

  axisRows.forEach((row) => {
    syncAxisRow(row);
    row.select.addEventListener("change", () => {
      closeChoiceDropdowns();
      syncAxisRow(row);
    });
    row.choiceRoot.addEventListener("toggle", () => {
      if (row.choiceRoot.open) {
        closeChoiceDropdowns(row);
      }
    });
    row.fillButton.addEventListener("click", () => {
      const axis = axisLookup.get(String(row.select.value ?? "").trim());
      if (row.usesChoiceDropdown) {
        const choiceValues = Array.isArray(axis?.choices) ? axis.choices.filter(Boolean) : [];
        setAxisRowValue(row, axisRowHasAllChoicesSelected(row) ? [] : choiceValues);
      } else {
        setAxisRowValue(row, buildFallbackValues(axis));
      }
      onStatusMessage?.(`Filled ${row.slot} axis values`);
    });
  });

  // IMPORTANT: native details/summary does not auto-collapse on outside click here; keep explicit document-level close handling.
  document.addEventListener("pointerdown", (event) => {
    if (!(event.target instanceof Node)) {
      return;
    }
    const activeRow = axisRows.find((row) => row.choiceRoot.open);
    if (!activeRow) {
      return;
    }
    if (!activeRow.choiceRoot.contains(event.target)) {
      closeChoiceDropdowns();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeChoiceDropdowns();
    }
  });

  swapButtons.forEach((entry) => {
    entry.button.addEventListener("click", () => {
      const leftRow = axisRows[entry.left];
      const rightRow = axisRows[entry.right];
      const leftAxis = leftRow.select.value;
      const leftValues = getAxisRowValue(leftRow);
      leftRow.select.value = rightRow.select.value;
      const rightValues = getAxisRowValue(rightRow);
      rightRow.select.value = leftAxis;
      syncAxisRow(leftRow);
      syncAxisRow(rightRow);
      setAxisRowValue(leftRow, rightValues);
      setAxisRowValue(rightRow, leftValues);
      onStatusMessage?.(`Swapped ${leftRow.slot} and ${rightRow.slot} axes`);
    });
  });

  estimateButton.addEventListener("click", async () => {
    const payload = collectPayload();
    if (!payload.axes.length) {
      onStatusMessage?.("XYZ Plot requires at least one configured axis");
      sessionStatusNode.textContent = "Status: configure at least one axis";
      return;
    }
    const result = await bootstrapState?.estimateXYZPlotRequest?.(payload);
    syncEstimatePayload(result);
    onStatusMessage?.(result?.ok ? "XYZ Plot estimate updated" : "XYZ Plot estimate failed");
  });

  runButton.addEventListener("click", async () => {
    const payload = collectPayload();
    if (!payload.axes.length) {
      onStatusMessage?.("XYZ Plot requires at least one configured axis");
      sessionStatusNode.textContent = "Status: configure at least one axis";
      return;
    }
    const result = await bootstrapState?.runXYZPlotRequest?.(payload);
    if (!result?.ok) {
      sessionStatusNode.textContent = `Status: ${String(result?.data?.status ?? "error")}`;
      onStatusMessage?.("XYZ Plot run failed");
      return;
    }
    syncSessionPayload(result.data.session);
    onStatusMessage?.(`Started XYZ Plot session ${state.activeSessionId}`);
  });

  refreshButton.addEventListener("click", () => {
    void refreshSessionDetail();
  });

  cancelButton.addEventListener("click", async () => {
    if (!state.activeSessionId) {
      return;
    }
    const result = await bootstrapState?.cancelXYZPlotSessionRequest?.(
      state.activeSessionId,
      String(bootstrapState?.clientId ?? "").trim(),
    );
    if (!result?.ok) {
      onStatusMessage?.("XYZ Plot cancel failed");
      return;
    }
    syncSessionPayload(result.data.session);
    onStatusMessage?.(`Cancelled XYZ Plot session ${state.activeSessionId}`);
  });

  void ensureAxisCatalogLoaded();
  void refreshSessionList().then(() => refreshSessionDetail());
  return {
    element: shell,
    stopPolling,
  };
}
