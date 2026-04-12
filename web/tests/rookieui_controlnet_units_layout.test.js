import { describe, expect, test } from "vitest";

import { createControlNetUnitEditor } from "../sidebar_tabs/rookieui_controlnet_units.js";

function createInput(type, id, value = "", options = {}) {
  const input = document.createElement("input");
  input.type = type;
  input.id = id;
  if (type !== "checkbox" && type !== "file") {
    input.value = String(value ?? "");
  }
  if (options.className) {
    input.className = options.className;
  }
  for (const [key, optionValue] of Object.entries(options)) {
    if (key === "className") {
      continue;
    }
    if (optionValue === undefined || optionValue === null) {
      continue;
    }
    input.setAttribute(key, String(optionValue));
  }
  return input;
}

function createRangeInput(id, value, options = {}) {
  return createInput("range", id, value, {
    className: "rookieui-shell__slider",
    ...options,
  });
}

function createSelect(id, options = [], value = "") {
  const select = document.createElement("select");
  select.id = id;
  select.className = "rookieui-shell__input";
  options.forEach((entry) => {
    const option = document.createElement("option");
    const normalized =
      entry && typeof entry === "object"
        ? { value: String(entry.value ?? ""), label: String(entry.label ?? entry.value ?? "") }
        : { value: String(entry ?? ""), label: String(entry ?? "") };
    option.value = normalized.value;
    option.textContent = normalized.label;
    select.appendChild(option);
  });
  select.value = String(value ?? "");
  return select;
}

function createCheckbox(id, checked = false) {
  const input = createInput("checkbox", id, "", { className: "rookieui-shell__checkbox" });
  input.checked = Boolean(checked);
  return input;
}

function createField(parent, labelText, control) {
  const field = document.createElement("label");
  field.className = "rookieui-shell__field";
  const label = document.createElement("span");
  label.className = "rookieui-shell__field-label";
  label.textContent = labelText;
  field.appendChild(label);
  field.appendChild(control);
  parent.appendChild(field);
  return field;
}

function createSliderField(parent, labelText, numberInput, rangeInput, id = "") {
  const field = document.createElement("div");
  field.className = "rookieui-shell__slider-field";
  if (id) {
    field.id = id;
  }
  const header = document.createElement("div");
  header.className = "rookieui-shell__slider-field-header";
  const label = document.createElement("span");
  label.className = "rookieui-shell__field-label";
  label.textContent = labelText;
  header.appendChild(label);
  header.appendChild(numberInput);
  field.appendChild(header);
  field.appendChild(rangeInput);
  parent.appendChild(field);
  return field;
}

function appendTextElement(parent, tagName, className, textContent) {
  const node = document.createElement(tagName);
  node.className = className;
  node.textContent = textContent;
  parent.appendChild(node);
  return node;
}

function buildEditor(idPrefix) {
  const host = document.createElement("div");
  const hiddenInput = createInput("hidden", `${idPrefix}-units`, "[]");
  host.appendChild(hiddenInput);

  const editor = createControlNetUnitEditor({
    idPrefix,
    parent: host,
    hiddenInput,
    modelOptions: [{ value: "control_v11p_sd15_canny.safetensors", label: "control_v11p_sd15_canny.safetensors" }],
    createInput,
    createRangeInput,
    createSelect,
    createCheckbox,
    createField,
    createSliderField,
    appendTextElement,
    readFileAsDataUrl: async () => "data:image/png;base64,dGVzdA==",
    syncBoundControls: () => {},
    onStatusMessage: () => {},
  });

  return { host, hiddenInput, editor };
}

describe("createControlNetUnitEditor layout and rollback contract", () => {
  test("pins selector row order, icon semantics, and full-width weight lane for txt2img", () => {
    const { host } = buildEditor("rookieui-txt2img-controlnet");
    const selectorRow = host.querySelector("#rookieui-txt2img-controlnet-selector-row-0");
    expect(selectorRow).not.toBeNull();
    expect(selectorRow?.children[0]?.querySelector(".rookieui-shell__field-label")?.textContent?.trim()).toBe(
      "Preprocessor",
    );
    expect(selectorRow?.children[1]?.classList.contains("rookieui-shell__controlnet-run-preprocessor-slot")).toBe(true);
    expect(selectorRow?.children[2]?.querySelector(".rookieui-shell__field-label")?.textContent?.trim()).toBe("Model");

    const runButton = host.querySelector("#rookieui-txt2img-controlnet-run-preprocessor-0");
    expect(runButton).not.toBeNull();
    expect(runButton?.hidden).toBe(false);
    expect(runButton?.querySelector(".rookieui-shell__mini-action-icon")?.textContent).toBe("💥");

    const placeholderIcon = host.querySelector(
      "#rookieui-txt2img-controlnet-preview-stage-0 .rookieui-shell__controlnet-preview-placeholder-icon",
    );
    expect(placeholderIcon?.textContent).toBe("⤴");
    expect(
      host.querySelector("#rookieui-txt2img-controlnet-preview-upload-action-0 .rookieui-shell__mini-action-icon")
        ?.textContent,
    ).toBe("📁");
    expect(
      host.querySelector("#rookieui-txt2img-controlnet-preview-remove-action-0 .rookieui-shell__mini-action-icon")
        ?.textContent,
    ).toBe("🗑");
    expect(host.querySelector("#rookieui-txt2img-controlnet-preview-undo-action-0")?.disabled).toBe(true);
    expect(host.querySelector("#rookieui-txt2img-controlnet-preview-redo-action-0")?.disabled).toBe(true);

    const weightField = host.querySelector("#rookieui-txt2img-controlnet-weight-field-0");
    expect(weightField?.classList.contains("rookieui-shell__field--full")).toBe(true);
    expect(weightField?.classList.contains("rookieui-shell__controlnet-weight-field")).toBe(true);
    expect(host.querySelector("#rookieui-txt2img-controlnet-image-upload-button-0")?.closest(".rookieui-shell__controlnet-upload-row--legacy-source")).not.toBeNull();
  });

  test("keeps img2img run-preprocessor hidden by default and toggles with independent image data", () => {
    const { host, editor } = buildEditor("rookieui-img2img-controlnet");

    const runButton = host.querySelector("#rookieui-img2img-controlnet-run-preprocessor-0");
    const imageData = host.querySelector("#rookieui-img2img-controlnet-image-data-0");
    expect(runButton).not.toBeNull();
    expect(imageData).not.toBeNull();
    expect(runButton?.hidden).toBe(true);

    imageData.value = "data:image/png;base64,aW1hZ2U=";
    imageData.dispatchEvent(new Event("input", { bubbles: true }));
    expect(runButton?.hidden).toBe(false);

    imageData.value = "";
    imageData.dispatchEvent(new Event("input", { bubbles: true }));
    expect(runButton?.hidden).toBe(true);

    editor.setUnits([
      {
        enabled: true,
        module: "openpose",
        image_data: "data:image/png;base64,cGF5bG9hZA==",
      },
    ]);
    expect(runButton?.hidden).toBe(false);

    editor.setUnits([{}]);
    expect(runButton?.hidden).toBe(true);
  });

  test("keeps canvas source history rollback deterministic for remove/undo/redo", async () => {
    const { host } = buildEditor("rookieui-img2img-controlnet");

    const runButton = host.querySelector("#rookieui-img2img-controlnet-run-preprocessor-0");
    const imageData = host.querySelector("#rookieui-img2img-controlnet-image-data-0");
    const previewRemove = host.querySelector("#rookieui-img2img-controlnet-preview-remove-action-0");
    const previewUndo = host.querySelector("#rookieui-img2img-controlnet-preview-undo-action-0");
    const previewRedo = host.querySelector("#rookieui-img2img-controlnet-preview-redo-action-0");
    const uploadInput = host.querySelector("#rookieui-img2img-controlnet-preview-image-upload-0");

    expect(runButton?.hidden).toBe(true);
    expect(imageData).not.toBeNull();
    expect(uploadInput).not.toBeNull();

    const file = new File([Uint8Array.from([137, 80, 78, 71])], "control.png", { type: "image/png" });
    Object.defineProperty(uploadInput, "files", {
      configurable: true,
      value: [file],
    });
    uploadInput.dispatchEvent(new Event("change", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(String(imageData.value || "")).toContain("data:image/png;base64,dGVzdA==");
    expect(runButton?.hidden).toBe(false);

    previewRemove.click();
    expect(imageData.value).toBe("");
    expect(runButton?.hidden).toBe(true);
    expect(previewUndo?.disabled).toBe(false);

    previewUndo.click();
    expect(String(imageData.value || "")).toContain("data:image/png;base64,dGVzdA==");
    expect(runButton?.hidden).toBe(false);
    expect(previewRedo?.disabled).toBe(false);

    previewRedo.click();
    expect(imageData.value).toBe("");
    expect(runButton?.hidden).toBe(true);
  });
});
