import { describe, expect, test, vi } from "vitest";

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

function buildEditor(idPrefix, overrides = {}) {
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
    readFileAsDataUrl: overrides.readFileAsDataUrl ?? (async () => "data:image/png;base64,dGVzdA=="),
    syncBoundControls: () => {},
    onStatusMessage: overrides.onStatusMessage ?? (() => {}),
  });

  return { host, hiddenInput, editor };
}

describe("createControlNetUnitEditor layout and rollback contract", () => {
  test("defaults the integrated section to collapsed after refresh", () => {
    const { host } = buildEditor("rookieui-img2img-controlnet");
    const section = host.querySelector("#rookieui-img2img-controlnet-section");
    expect(section).not.toBeNull();
    expect(section?.open).toBe(false);
  });

  test("keeps exactly one active control-type chip while switching radio options", () => {
    const { host } = buildEditor("rookieui-img2img-controlnet");
    document.body.appendChild(host);

    const allRadio = host.querySelector("#rookieui-img2img-controlnet-control-type-0-all");
    const blurRadio = host.querySelector("#rookieui-img2img-controlnet-control-type-0-blur");
    const cannyRadio = host.querySelector("#rookieui-img2img-controlnet-control-type-0-canny");
    const controlTypeGroup = allRadio?.closest(".rookieui-shell__controlnet-radio-grid");
    expect(allRadio).not.toBeNull();
    expect(blurRadio).not.toBeNull();
    expect(cannyRadio).not.toBeNull();
    expect(controlTypeGroup).not.toBeNull();

    expect(controlTypeGroup.querySelectorAll(".rookieui-shell__controlnet-radio-option[data-active='true']")).toHaveLength(1);
    expect(allRadio?.parentElement?.dataset.active).toBe("true");

    blurRadio.click();
    expect(controlTypeGroup.querySelectorAll(".rookieui-shell__controlnet-radio-option[data-active='true']")).toHaveLength(1);
    expect(blurRadio?.parentElement?.dataset.active).toBe("true");
    expect(allRadio?.parentElement?.dataset.active).toBe("false");

    cannyRadio.click();
    expect(controlTypeGroup.querySelectorAll(".rookieui-shell__controlnet-radio-option[data-active='true']")).toHaveLength(1);
    expect(cannyRadio?.parentElement?.dataset.active).toBe("true");
    expect(blurRadio?.parentElement?.dataset.active).toBe("false");
  });

  test("filters preprocessor options by control type using variant catalog entries", () => {
    const { host, editor } = buildEditor("rookieui-img2img-controlnet");
    document.body.appendChild(host);

    editor.setControlTypeCatalog({
      All: {
        module_list: ["none", "lineart_anime", "lineart_standard", "depth_anything_v2"],
        model_list: [],
        default_option: "none",
      },
      Lineart: {
        module_list: ["none", "lineart_anime", "lineart_anime_denoise", "lineart_standard"],
        model_list: [],
        default_option: "lineart_anime",
      },
      Depth: {
        module_list: ["none", "depth_anything_v2", "depth_midas"],
        model_list: [],
        default_option: "depth_anything_v2",
      },
    });

    const moduleSelect = host.querySelector("#rookieui-img2img-controlnet-module-0");
    const lineartRadio = host.querySelector("#rookieui-img2img-controlnet-control-type-0-lineart");
    const depthRadio = host.querySelector("#rookieui-img2img-controlnet-control-type-0-depth");
    expect(moduleSelect).not.toBeNull();
    expect(lineartRadio).not.toBeNull();
    expect(depthRadio).not.toBeNull();

    lineartRadio.click();
    let moduleOptions = Array.from(moduleSelect.options).map((entry) => entry.value);
    expect(moduleOptions).toEqual(["none", "lineart_anime", "lineart_anime_denoise", "lineart_standard"]);
    expect(moduleSelect.value).toBe("lineart_anime");

    moduleSelect.value = "lineart_standard";
    moduleSelect.dispatchEvent(new Event("change", { bubbles: true }));

    depthRadio.click();
    moduleOptions = Array.from(moduleSelect.options).map((entry) => entry.value);
    expect(moduleOptions).toEqual(["none", "depth_anything_v2", "depth_midas"]);
    expect(moduleSelect.value).toBe("depth_anything_v2");
  });

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
    expect(runButton?.getAttribute("title")).toBe("Run Preprocessor");
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
    expect(host.querySelector("#rookieui-txt2img-controlnet-source-0-brush-toggle")).not.toBeNull();
    expect(host.querySelector("#rookieui-txt2img-controlnet-source-0-brush-width")?.value).toBe("25");
    expect(host.querySelector("#rookieui-txt2img-controlnet-source-0-brush-opacity")?.value).toBe("100");
    expect(host.querySelector("#rookieui-txt2img-controlnet-source-0-brush-softness")?.value).toBe("0");
    expect(host.querySelector("#rookieui-txt2img-controlnet-source-0-brush-indicator")).not.toBeNull();
    expect(host.querySelector("#rookieui-txt2img-controlnet-source-0-brush-width")?.disabled).toBe(true);

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
    expect(runButton?.getAttribute("title")).toBe("Run Preprocessor");

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

  test("switches preview-stage click behavior from upload mode to edit mode after source bind", () => {
    const { host } = buildEditor("rookieui-img2img-controlnet");

    const stage = host.querySelector("#rookieui-img2img-controlnet-preview-stage-0");
    const imageData = host.querySelector("#rookieui-img2img-controlnet-image-data-0");
    const uploadInput = host.querySelector("#rookieui-img2img-controlnet-preview-image-upload-0");
    expect(stage).not.toBeNull();
    expect(imageData).not.toBeNull();
    expect(uploadInput).not.toBeNull();

    const uploadClickSpy = vi.fn();
    uploadInput.click = uploadClickSpy;

    expect(stage?.dataset.interactionMode).toBe("upload");
    stage?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(uploadClickSpy).toHaveBeenCalledTimes(1);

    imageData.value = "data:image/png;base64,aW1hZ2UtYmluZA==";
    imageData.dispatchEvent(new Event("input", { bubbles: true }));
    expect(stage?.dataset.interactionMode).toBe("edit");
    stage?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(uploadClickSpy).toHaveBeenCalledTimes(1);

    stage?.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(uploadClickSpy).toHaveBeenCalledTimes(1);
  });

  test("keeps source immutable when run-preprocessor updates generated preview state", async () => {
    const { host } = buildEditor("rookieui-img2img-controlnet");

    const imageData = host.querySelector("#rookieui-img2img-controlnet-image-data-0");
    const moduleSelect = host.querySelector("#rookieui-img2img-controlnet-module-0");
    const allowPreview = host.querySelector("#rookieui-img2img-controlnet-allow-preview-0");
    const runButton = host.querySelector("#rookieui-img2img-controlnet-run-preprocessor-0");
    const dualPane = host.querySelector("#rookieui-img2img-controlnet-preview-dual-pane-0");
    const generatedLane = host.querySelector("#rookieui-img2img-controlnet-preview-generated-lane-0");
    const generatedImage = host.querySelector("#rookieui-img2img-controlnet-preview-generated-image-0");
    expect(imageData).not.toBeNull();
    expect(moduleSelect).not.toBeNull();
    expect(allowPreview).not.toBeNull();
    expect(runButton).not.toBeNull();
    expect(dualPane).not.toBeNull();
    expect(generatedLane).not.toBeNull();
    expect(generatedImage).not.toBeNull();
    expect(dualPane?.dataset.generatedVisible).toBe("false");

    const originalFetch = globalThis.fetch;
    try {
      globalThis.fetch = vi.fn(async () => ({
        ok: true,
        async json() {
          return { images: ["data:image/png;base64,cHJldmlldy1pbWFnZQ=="] };
        },
      }));

      imageData.value = "data:image/png;base64,c291cmNlLWltYWdl";
      imageData.dispatchEvent(new Event("input", { bubbles: true }));
      moduleSelect.value = "depth";
      moduleSelect.dispatchEvent(new Event("change", { bubbles: true }));
      expect(runButton?.hidden).toBe(false);

      const sourceBeforeRun = imageData.value;
      runButton.click();
      await new Promise((resolve) => setTimeout(resolve, 0));
      expect(imageData.value).toBe(sourceBeforeRun);
      expect(generatedLane.hidden).toBe(true);

      allowPreview.checked = true;
      allowPreview.dispatchEvent(new Event("change", { bubbles: true }));
      expect(generatedLane.hidden).toBe(false);
      expect(dualPane?.dataset.generatedVisible).toBe("true");
      expect(generatedImage.src).toContain("data:image/png;base64,cHJldmlldy1pbWFnZQ==");

      imageData.value = "data:image/png;base64,bmV3LXNvdXJjZQ==";
      imageData.dispatchEvent(new Event("input", { bubbles: true }));
      expect(generatedLane.hidden).toBe(true);
      expect(dualPane?.dataset.generatedVisible).toBe("false");

      allowPreview.checked = false;
      allowPreview.dispatchEvent(new Event("change", { bubbles: true }));
      expect(generatedLane.hidden).toBe(true);
      expect(dualPane?.dataset.generatedVisible).toBe("false");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test("reports explicit hidden-preview guidance after run-preprocessor success with Allow Preview disabled", async () => {
    const statusMessages = [];
    const { host } = buildEditor("rookieui-img2img-controlnet", {
      onStatusMessage: (message) => {
        statusMessages.push(String(message ?? ""));
      },
    });

    const imageData = host.querySelector("#rookieui-img2img-controlnet-image-data-0");
    const moduleSelect = host.querySelector("#rookieui-img2img-controlnet-module-0");
    const runButton = host.querySelector("#rookieui-img2img-controlnet-run-preprocessor-0");
    const generatedLane = host.querySelector("#rookieui-img2img-controlnet-preview-generated-lane-0");
    expect(imageData).not.toBeNull();
    expect(moduleSelect).not.toBeNull();
    expect(runButton).not.toBeNull();
    expect(generatedLane).not.toBeNull();

    const originalFetch = globalThis.fetch;
    try {
      globalThis.fetch = vi.fn(async () => ({
        ok: true,
        status: 200,
        async json() {
          return { images: ["data:image/png;base64,cHJldmlldy1pbWFnZQ=="] };
        },
      }));

      imageData.value = "data:image/png;base64,c291cmNlLWltYWdl";
      imageData.dispatchEvent(new Event("input", { bubbles: true }));
      moduleSelect.value = "depth";
      moduleSelect.dispatchEvent(new Event("change", { bubbles: true }));
      runButton.click();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(generatedLane.hidden).toBe(true);
      expect(runButton?.dataset.running).toBe("false");
      expect(runButton?.title).toBe("Run Preprocessor");
      expect(runButton?.querySelector(".rookieui-shell__mini-action-icon")?.textContent).toBe("💥");
      expect(statusMessages.some((entry) => entry.includes("running preprocessor"))).toBe(true);
      expect(statusMessages.some((entry) => entry.includes("hidden because Allow Preview is off"))).toBe(true);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test("reports explicit preview-lane update status when Allow Preview is enabled", async () => {
    const statusMessages = [];
    const { host } = buildEditor("rookieui-img2img-controlnet", {
      onStatusMessage: (message) => {
        statusMessages.push(String(message ?? ""));
      },
    });

    const imageData = host.querySelector("#rookieui-img2img-controlnet-image-data-0");
    const moduleSelect = host.querySelector("#rookieui-img2img-controlnet-module-0");
    const allowPreview = host.querySelector("#rookieui-img2img-controlnet-allow-preview-0");
    const runButton = host.querySelector("#rookieui-img2img-controlnet-run-preprocessor-0");
    const generatedLane = host.querySelector("#rookieui-img2img-controlnet-preview-generated-lane-0");
    expect(imageData).not.toBeNull();
    expect(moduleSelect).not.toBeNull();
    expect(allowPreview).not.toBeNull();
    expect(runButton).not.toBeNull();
    expect(generatedLane).not.toBeNull();

    const originalFetch = globalThis.fetch;
    try {
      globalThis.fetch = vi.fn(async () => ({
        ok: true,
        status: 200,
        async json() {
          return { images: ["data:image/png;base64,cHJldmlldy1pbWFnZQ=="] };
        },
      }));

      imageData.value = "data:image/png;base64,c291cmNlLWltYWdl";
      imageData.dispatchEvent(new Event("input", { bubbles: true }));
      moduleSelect.value = "depth";
      moduleSelect.dispatchEvent(new Event("change", { bubbles: true }));
      allowPreview.checked = true;
      allowPreview.dispatchEvent(new Event("change", { bubbles: true }));
      runButton.click();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(generatedLane.hidden).toBe(false);
      expect(statusMessages.some((entry) => entry.includes("Preview lane updated"))).toBe(true);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test("surfaces backend near-empty warning text when preprocessor returns black/empty-like output", async () => {
    const statusMessages = [];
    const { host } = buildEditor("rookieui-img2img-controlnet", {
      onStatusMessage: (message) => {
        statusMessages.push(String(message ?? ""));
      },
    });

    const imageData = host.querySelector("#rookieui-img2img-controlnet-image-data-0");
    const moduleSelect = host.querySelector("#rookieui-img2img-controlnet-module-0");
    const allowPreview = host.querySelector("#rookieui-img2img-controlnet-allow-preview-0");
    const runButton = host.querySelector("#rookieui-img2img-controlnet-run-preprocessor-0");
    expect(imageData).not.toBeNull();
    expect(moduleSelect).not.toBeNull();
    expect(allowPreview).not.toBeNull();
    expect(runButton).not.toBeNull();

    const originalFetch = globalThis.fetch;
    try {
      globalThis.fetch = vi.fn(async () => ({
        ok: true,
        status: 200,
        async json() {
          return {
            images: ["data:image/png;base64,YmxhY2stb3ItZW1wdHk="],
            warning_codes: ["CONTROLNET_PREPROCESSOR_EMPTY_OUTPUT"],
            warnings: ["ComfyUI host preprocessor completed but output is near-empty for the current image/module settings."],
            detect_backend: "comfy_host_preprocessor",
            processor: "OpenposePreprocessor",
          };
        },
      }));

      imageData.value = "data:image/png;base64,c291cmNlLWltYWdl";
      imageData.dispatchEvent(new Event("input", { bubbles: true }));
      moduleSelect.value = "openpose";
      moduleSelect.dispatchEvent(new Event("change", { bubbles: true }));
      allowPreview.checked = true;
      allowPreview.dispatchEvent(new Event("change", { bubbles: true }));
      runButton.click();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(
        statusMessages.some((entry) => entry.includes("near-empty for the current image/module settings")),
      ).toBe(true);
      expect(statusMessages.some((entry) => entry.includes("Processor: OpenposePreprocessor"))).toBe(true);
      expect(statusMessages.some((entry) => entry.includes("Preview lane updated"))).toBe(true);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test("forwards selected control model in run-preprocessor payload and reports model scope", async () => {
    const statusMessages = [];
    const { host } = buildEditor("rookieui-img2img-controlnet", {
      onStatusMessage: (message) => {
        statusMessages.push(String(message ?? ""));
      },
    });

    const imageData = host.querySelector("#rookieui-img2img-controlnet-image-data-0");
    const moduleSelect = host.querySelector("#rookieui-img2img-controlnet-module-0");
    const modelSelect = host.querySelector("#rookieui-img2img-controlnet-model-0");
    const runButton = host.querySelector("#rookieui-img2img-controlnet-run-preprocessor-0");
    expect(imageData).not.toBeNull();
    expect(moduleSelect).not.toBeNull();
    expect(modelSelect).not.toBeNull();
    expect(runButton).not.toBeNull();

    const originalFetch = globalThis.fetch;
    try {
      globalThis.fetch = vi.fn(async (_url, options) => {
        const body = JSON.parse(String(options?.body ?? "{}"));
        expect(body.controlnet_model).toBe("control_v11p_sd15_canny.safetensors");
        return {
          ok: true,
          status: 200,
          async json() {
            return {
              images: ["data:image/png;base64,cHJldmlldy1pbWFnZQ=="],
              requested_controlnet_model: body.controlnet_model,
            };
          },
        };
      });

      imageData.value = "data:image/png;base64,c291cmNlLWltYWdl";
      imageData.dispatchEvent(new Event("input", { bubbles: true }));
      moduleSelect.value = "depth";
      moduleSelect.dispatchEvent(new Event("change", { bubbles: true }));
      modelSelect.value = "control_v11p_sd15_canny.safetensors";
      modelSelect.dispatchEvent(new Event("change", { bubbles: true }));
      runButton.click();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(
        statusMessages.some((entry) =>
          entry.includes("generation stage only; preprocessor preview is driven by selected preprocessor/annotator"),
        ),
      ).toBe(
        true,
      );
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test("reports backend detail when run-preprocessor returns a non-OK response", async () => {
    const statusMessages = [];
    const { host } = buildEditor("rookieui-img2img-controlnet", {
      onStatusMessage: (message) => {
        statusMessages.push(String(message ?? ""));
      },
    });

    const imageData = host.querySelector("#rookieui-img2img-controlnet-image-data-0");
    const moduleSelect = host.querySelector("#rookieui-img2img-controlnet-module-0");
    const runButton = host.querySelector("#rookieui-img2img-controlnet-run-preprocessor-0");
    expect(imageData).not.toBeNull();
    expect(moduleSelect).not.toBeNull();
    expect(runButton).not.toBeNull();

    const originalFetch = globalThis.fetch;
    try {
      globalThis.fetch = vi.fn(async () => ({
        ok: false,
        status: 503,
        async json() {
          return { detail: "detect route unavailable" };
        },
      }));

      imageData.value = "data:image/png;base64,c291cmNlLWltYWdl";
      imageData.dispatchEvent(new Event("input", { bubbles: true }));
      moduleSelect.value = "depth";
      moduleSelect.dispatchEvent(new Event("change", { bubbles: true }));
      runButton.click();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(statusMessages.some((entry) => entry.includes("detect route unavailable"))).toBe(true);
      expect(runButton?.dataset.running).toBe("false");
      expect(runButton?.title).toBe("Run Preprocessor");
    } finally {
      globalThis.fetch = originalFetch;
    }
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

  test("toggles fullscreen action button between enter and exit states", async () => {
    const statusMessages = [];
    const { host } = buildEditor("rookieui-img2img-controlnet", {
      onStatusMessage: (message) => {
        statusMessages.push(String(message ?? ""));
      },
    });

    const stage = host.querySelector("#rookieui-img2img-controlnet-preview-stage-0");
    const fullscreenButton = host.querySelector("#rookieui-img2img-controlnet-preview-fullscreen-action-0");
    const fullscreenIcon = fullscreenButton?.querySelector(".rookieui-shell__mini-action-icon");
    expect(stage).not.toBeNull();
    expect(fullscreenButton).not.toBeNull();
    expect(fullscreenIcon?.textContent).toBe("⛶");

    let fullscreenElementRef = null;
    const originalFullscreenDescriptor = Object.getOwnPropertyDescriptor(document, "fullscreenElement");
    const originalExitDescriptor = Object.getOwnPropertyDescriptor(document, "exitFullscreen");

    const requestFullscreen = vi.fn(async () => {
      fullscreenElementRef = stage;
      document.dispatchEvent(new Event("fullscreenchange"));
    });
    stage.requestFullscreen = requestFullscreen;

    const exitFullscreen = vi.fn(async () => {
      fullscreenElementRef = null;
      document.dispatchEvent(new Event("fullscreenchange"));
    });

    Object.defineProperty(document, "fullscreenElement", {
      configurable: true,
      get() {
        return fullscreenElementRef;
      },
    });
    Object.defineProperty(document, "exitFullscreen", {
      configurable: true,
      value: exitFullscreen,
    });

    try {
      fullscreenButton.click();
      await new Promise((resolve) => setTimeout(resolve, 0));
      expect(requestFullscreen).toHaveBeenCalledTimes(1);
      expect(fullscreenIcon?.textContent).toBe("🗗");

      fullscreenButton.click();
      await new Promise((resolve) => setTimeout(resolve, 0));
      expect(exitFullscreen).toHaveBeenCalledTimes(1);
      expect(fullscreenIcon?.textContent).toBe("⛶");
      expect(statusMessages.some((entry) => entry.includes("entered fullscreen mode"))).toBe(true);
      expect(statusMessages.some((entry) => entry.includes("exited fullscreen mode"))).toBe(true);
    } finally {
      if (originalFullscreenDescriptor) {
        Object.defineProperty(document, "fullscreenElement", originalFullscreenDescriptor);
      } else {
        Reflect.deleteProperty(document, "fullscreenElement");
      }
      if (originalExitDescriptor) {
        Object.defineProperty(document, "exitFullscreen", originalExitDescriptor);
      } else {
        Reflect.deleteProperty(document, "exitFullscreen");
      }
    }
  });
});
