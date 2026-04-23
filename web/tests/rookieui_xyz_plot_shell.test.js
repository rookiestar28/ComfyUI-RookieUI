import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { createIconActionButton } from "../rookieui_action_buttons.js";
import { createPreviewFullscreenViewer } from "../rookieui_preview_fullscreen.js";
import { createXYZPlotShell } from "../sidebar_tabs/rookieui_xyz_plot_shell.js";

function flushPromises() {
  return Promise.resolve().then(() => Promise.resolve());
}

function appendTextElement(parent, tagName, className, textContent) {
  const node = document.createElement(tagName);
  node.className = className;
  node.textContent = textContent;
  parent.appendChild(node);
  return node;
}

function createActionButton(id, label) {
  const button = document.createElement("button");
  button.type = "button";
  button.id = id;
  button.textContent = label;
  button.className = "rookieui-shell__button";
  return button;
}

function createBootstrapState(overrides = {}) {
  return {
    clientId: "browser-1",
    xyzPlot: {
      axes: {
        steps: {
          axis_id: "steps",
          title: "Steps",
          support_tier: "direct",
          mode_scopes: ["txt2img", "img2img"],
          value_input_mode: "int_csv_or_range",
          choices: [],
          session_runner_support: true,
          a1111_reference_label: "Steps",
          notes: [],
        },
        cfg_scale: {
          axis_id: "cfg_scale",
          title: "CFG Scale",
          support_tier: "direct",
          mode_scopes: ["txt2img", "img2img"],
          value_input_mode: "float_csv_or_range",
          choices: [],
          session_runner_support: true,
          a1111_reference_label: "CFG Scale",
          notes: [],
        },
        seed: {
          axis_id: "seed",
          title: "Seed",
          support_tier: "direct",
          mode_scopes: ["txt2img", "img2img"],
          value_input_mode: "int_csv_or_range",
          choices: [],
          session_runner_support: true,
          a1111_reference_label: "Seed",
          notes: [],
        },
        checkpoint_name: {
          axis_id: "checkpoint_name",
          title: "Checkpoint Name",
          support_tier: "direct",
          mode_scopes: ["txt2img", "img2img"],
          value_input_mode: "choices_or_csv",
          choices: ["model-a.safetensors", "model-b.safetensors"],
          session_runner_support: true,
          a1111_reference_label: "Checkpoint name",
          notes: [],
        },
        hires_upscaler: {
          axis_id: "hires_upscaler",
          title: "Hires Upscaler",
          support_tier: "adapted",
          mode_scopes: ["txt2img"],
          value_input_mode: "choices_or_csv",
          choices: ["Latent", "Latent (bicubic)", "Bislerp"],
          session_runner_support: true,
          a1111_reference_label: "Hires upscaler",
          notes: [],
        },
        denoising_strength: {
          axis_id: "denoising_strength",
          title: "Denoising",
          support_tier: "direct",
          mode_scopes: ["img2img"],
          value_input_mode: "float_csv_or_range",
          choices: [],
          session_runner_support: true,
          a1111_reference_label: "Denoising",
          notes: [],
        },
        hires_steps: {
          axis_id: "hires_steps",
          title: "Hires Steps",
          support_tier: "adapted",
          mode_scopes: ["txt2img"],
          value_input_mode: "int_csv_or_range",
          choices: [],
          session_runner_support: true,
          a1111_reference_label: "Hires steps",
          notes: [],
        },
        prompt_sr: {
          axis_id: "prompt_sr",
          title: "Prompt S/R",
          support_tier: "adapted",
          mode_scopes: ["txt2img", "img2img"],
          value_input_mode: "prompt_sr_csv",
          choices: [],
          session_runner_support: true,
          a1111_reference_label: "Prompt S/R",
          notes: [],
        },
        prompt_order: {
          axis_id: "prompt_order",
          title: "Prompt order",
          support_tier: "adapted",
          mode_scopes: ["txt2img", "img2img"],
          value_input_mode: "permutation_csv",
          choices: [],
          session_runner_support: true,
          a1111_reference_label: "Prompt order",
          notes: [],
        },
      },
    },
    estimateXYZPlotRequest: vi.fn(async (payload) => ({
      ok: true,
      data: {
        estimate: {
          cell_count: payload.axes.length * 3,
          generated_image_count: payload.axes.length * 3,
          total_step_estimate: 120,
          projected_grid_megapixels: 2.5,
        },
        can_run: true,
        warnings: [],
        warning_codes: [],
      },
    })),
    runXYZPlotRequest: vi.fn(async () => ({
      ok: true,
      data: {
        session: {
          session_id: "xyz-1",
          status: "in_progress",
          seed_policy: {
            keep_negative_one_seed: false,
            vary_seeds_x: false,
            vary_seeds_y: false,
            vary_seeds_z: false,
            fixed_base_seed: 101,
            fixed_axis_values: {},
          },
          summary: {
            total_cells: 9,
            completed_cells: 2,
            queued_cells: 1,
            failed_cells: 0,
          },
          results: {
            status: "running",
            main_grid: {},
            sub_grids: [],
            lone_images: [],
            warnings: [],
          },
        },
      },
    })),
    fetchXYZPlotSessionsRequest: vi.fn(async () => ({
      ok: true,
      data: {
        sessions: [{ session_id: "xyz-history", status: "completed" }],
      },
    })),
    fetchXYZPlotSessionDetailRequest: vi.fn(async (sessionId) => ({
      ok: true,
      data: {
        session: {
          session_id: sessionId,
          status: "completed",
          seed_policy: {
            keep_negative_one_seed: false,
            vary_seeds_x: false,
            vary_seeds_y: false,
            vary_seeds_z: false,
            fixed_base_seed: 101,
            fixed_axis_values: {},
          },
          summary: {
            total_cells: 9,
            completed_cells: 9,
            queued_cells: 0,
            failed_cells: 0,
          },
          results: {
            status: "ready",
            main_grid: {
              preview_data_url: "data:image/png;base64,ZmFrZQ==",
            },
            sub_grids: [{ z_index: 0 }],
            lone_images: [{ cell_id: "cell-1" }, { cell_id: "cell-2" }],
            warnings: [],
          },
        },
      },
    })),
    cancelXYZPlotSessionRequest: vi.fn(async (sessionId) => ({
      ok: true,
      data: {
        session: {
          session_id: sessionId,
          status: "cancelled",
          cancel_requested: true,
          summary: {
            total_cells: 9,
            completed_cells: 3,
            queued_cells: 0,
            failed_cells: 0,
          },
          results: {
            status: "pending",
            main_grid: {},
            sub_grids: [],
            lone_images: [],
            warnings: [],
          },
        },
      },
    })),
    ...overrides,
  };
}

describe("xyz plot shell", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    document.body.innerHTML = "";
  });

  afterEach(async () => {
    vi.runOnlyPendingTimers();
    await flushPromises();
    vi.useRealTimers();
  });

  test("estimates from the current base request and configured axes", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);
    const statusMessages = [];
    const bootstrapState = createBootstrapState();
    const baseRequest = {
      prompt: "masterpiece skyline",
      steps: 28,
      cfg_scale: 7,
      checkpoint_name: "model-a.safetensors",
    };

    createXYZPlotShell({
      idPrefix: "txt2img-xyz",
      parent,
      mode: "txt2img",
      bootstrapState,
      buildBaseRequest: () => baseRequest,
      appendTextElement,
      createActionButton,
      onStatusMessage: (message) => statusMessages.push(message),
    });

    await flushPromises();

    const section = document.getElementById("txt2img-xyz-section");
    expect(section?.open).toBe(false);
    expect(section?.querySelector("summary")?.className).toContain("rookieui-shell__hires-summary");
    expect(section?.textContent).not.toContain("Bottom-mounted sweep surface");
    expect(document.querySelector("#txt2img-xyz-draw-legend + span")?.className).toContain("rookieui-shell__field-label");
    const actionOrder = Array.from(
      section?.querySelectorAll(".rookieui-shell__xyz-plot-actions > button") ?? [],
    ).map((node) => node.textContent?.trim());
    expect(actionOrder).toEqual(["Estimate", "Refresh", "Run XYZ Plot", "Cancel Session"]);
    expect(document.getElementById("txt2img-xyz-estimate")?.className).toContain("rookieui-shell__xyz-plot-action--estimate");
    expect(document.getElementById("txt2img-xyz-run")?.className).toContain("rookieui-shell__button--accent");
    expect(document.getElementById("txt2img-xyz-refresh")?.className).toContain("rookieui-shell__xyz-plot-action--refresh");
    expect(document.getElementById("txt2img-xyz-cancel")?.className).toContain("rookieui-shell__button--danger");
    expect(document.getElementById("txt2img-xyz-cancel")?.className).toContain("rookieui-shell__xyz-plot-action--danger");
    expect(document.getElementById("txt2img-xyz-cancel")?.className).not.toContain("rookieui-shell__button--secondary");

    expect(document.getElementById("txt2img-xyz-axis-x-select").value).toBe("steps");
    document.getElementById("txt2img-xyz-axis-z-select").value = "checkpoint_name";
    document.getElementById("txt2img-xyz-axis-z-select").dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("txt2img-xyz-axis-z-values").hidden).toBe(true);
    expect(document.getElementById("txt2img-xyz-axis-z-values-multiselect").hidden).toBe(false);
    expect(document.getElementById("txt2img-xyz-axis-z-fill").hidden).toBe(false);
    expect(document.getElementById("txt2img-xyz-axis-z-fill").disabled).toBe(false);
    expect(document.getElementById("txt2img-xyz-axis-z-values-summary").textContent).toContain("Select values");
    document.getElementById("txt2img-xyz-axis-z-fill").click();
    expect(
      Array.from(
        document.querySelectorAll("#txt2img-xyz-axis-z-values-options input:checked"),
      ).map((input) => input.value),
    ).toEqual(["model-a.safetensors", "model-b.safetensors"]);
    expect(
      document.querySelector("#txt2img-xyz-axis-z-values-options .rookieui-shell__xyz-plot-choice-option-text")?.title,
    ).toBe("model-a.safetensors");
    expect(
      document.querySelector("#txt2img-xyz-axis-z-values-summary .rookieui-shell__xyz-plot-choice-summary-text")?.title,
    ).toBe("model-a.safetensors, model-b.safetensors");
    document.getElementById("txt2img-xyz-axis-z-values-summary").click();
    expect(document.getElementById("txt2img-xyz-axis-z-values-multiselect")?.open).toBe(true);
    document.body.dispatchEvent(new Event("pointerdown", { bubbles: true }));
    expect(document.getElementById("txt2img-xyz-axis-z-values-multiselect")?.open).toBe(false);
    document.getElementById("txt2img-xyz-axis-z-values-summary").click();
    expect(document.getElementById("txt2img-xyz-axis-z-values-multiselect")?.open).toBe(true);
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(document.getElementById("txt2img-xyz-axis-z-values-multiselect")?.open).toBe(false);
    document.getElementById("txt2img-xyz-axis-z-fill").click();
    expect(
      Array.from(
        document.querySelectorAll("#txt2img-xyz-axis-z-values-options input:checked"),
      ),
    ).toHaveLength(0);
    document.getElementById("txt2img-xyz-axis-z-fill").click();

    document.getElementById("txt2img-xyz-axis-x-values").value = "20, 28, 36";
    document.getElementById("txt2img-xyz-axis-y-values").value = "5.5, 7, 8.5";
    document.getElementById("txt2img-xyz-keep-negative-one-seed").checked = true;
    document.getElementById("txt2img-xyz-vary-seeds-y").checked = true;
    document.getElementById("txt2img-xyz-estimate").click();
    await flushPromises();

    expect(bootstrapState.estimateXYZPlotRequest).toHaveBeenCalledWith({
      mode: "txt2img",
      client_id: "browser-1",
      max_parallel: 1,
      base_request: baseRequest,
      axes: [
        { axis_id: "steps", values: "20, 28, 36" },
        { axis_id: "cfg_scale", values: "5.5, 7, 8.5" },
        { axis_id: "checkpoint_name", values: "model-a.safetensors, model-b.safetensors" },
      ],
      draw_legend: true,
      include_lone_images: false,
      include_sub_grids: false,
      keep_negative_one_seed: true,
      vary_seeds_x: false,
      vary_seeds_y: true,
      vary_seeds_z: false,
      margin_size: 0,
    });
    expect(statusMessages.at(-1)).toContain("estimate");
  });

  test("runs, refreshes, and cancels sessions while updating preview state", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);
    const syncPrimaryPreview = vi.fn();
    const bootstrapState = createBootstrapState({
      fetchXYZPlotSessionsRequest: vi.fn(async () => ({
        ok: true,
        data: { sessions: [] },
      })),
      fetchXYZPlotSessionDetailRequest: vi.fn(async (sessionId) => ({
        ok: true,
        data: {
          session: {
            session_id: sessionId,
            status: "in_progress",
            summary: {
              total_cells: 9,
              completed_cells: 5,
              queued_cells: 1,
              failed_cells: 0,
            },
            results: {
              status: "running",
              main_grid: {
                preview_data_url: "data:image/png;base64,ZmFrZQ==",
              },
              sub_grids: [{ z_index: 0 }],
              lone_images: [{ cell_id: "cell-1" }, { cell_id: "cell-2" }],
              warnings: [],
            },
          },
        },
      })),
    });

    createXYZPlotShell({
      idPrefix: "img2img-xyz",
      parent,
      mode: "img2img",
      bootstrapState,
      buildBaseRequest: () => ({
        prompt: "portrait",
        mode: "inpaint",
        denoise_strength: 0.55,
      }),
      appendTextElement,
      createActionButton,
      syncPrimaryPreview,
    });

    await flushPromises();

    const section = document.getElementById("img2img-xyz-section");
    expect(section?.open).toBe(false);

    document.getElementById("img2img-xyz-axis-x-values").value = "1, 2, 3";
    document.getElementById("img2img-xyz-axis-y-values").value = "0.35, 0.55, 0.75";
    document.getElementById("img2img-xyz-axis-y-select").value = "denoising_strength";
    document.getElementById("img2img-xyz-axis-y-select").dispatchEvent(new Event("change", { bubbles: true }));
    document.getElementById("img2img-xyz-axis-z-select").value = "";
    document.getElementById("img2img-xyz-axis-z-select").dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("img2img-xyz-keep-negative-one-seed").checked).toBe(false);
    expect(document.getElementById("img2img-xyz-vary-seeds-x").checked).toBe(false);
    expect(document.getElementById("img2img-xyz-vary-seeds-y").checked).toBe(false);
    expect(document.getElementById("img2img-xyz-vary-seeds-z").checked).toBe(false);

    document.getElementById("img2img-xyz-run").click();
    await flushPromises();

    expect(bootstrapState.runXYZPlotRequest).toHaveBeenCalledTimes(1);
    expect(document.getElementById("img2img-xyz-session-status").textContent).toContain("in_progress");

    document.getElementById("img2img-xyz-refresh").click();
    await flushPromises();

    expect(bootstrapState.fetchXYZPlotSessionDetailRequest).toHaveBeenCalledWith("xyz-1", "browser-1");
    const previewImage = document.querySelector("#img2img-xyz-main-grid-preview img");
    expect(previewImage?.getAttribute("src")).toBe("data:image/png;base64,ZmFrZQ==");
    expect(syncPrimaryPreview).toHaveBeenCalledWith("data:image/png;base64,ZmFrZQ==", expect.any(Object));
    expect(document.getElementById("img2img-xyz-result-summary").textContent).toContain("Sub-grids: 1");

    document.getElementById("img2img-xyz-cancel").click();
    await flushPromises();

    expect(bootstrapState.cancelXYZPlotSessionRequest).toHaveBeenCalledWith("xyz-1", "browser-1");
    expect(document.getElementById("img2img-xyz-session-status").textContent).toContain("cancelled");
  });

  test("uses dropdown values for non-numeric choice axes and preserves them across swaps", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);
    const bootstrapState = createBootstrapState({
      xyzPlot: {
        axes: {
          ...createBootstrapState().xyzPlot.axes,
          sampler: {
            axis_id: "sampler",
            title: "Sampler",
            support_tier: "direct",
            mode_scopes: ["txt2img", "img2img"],
            value_input_mode: "choices_or_csv",
            choices: ["euler", "dpmpp_2m"],
            session_runner_support: true,
            a1111_reference_label: "Sampler",
            notes: [],
          },
        },
      },
    });

    createXYZPlotShell({
      idPrefix: "swap-xyz",
      parent,
      mode: "txt2img",
      bootstrapState,
      buildBaseRequest: () => ({ prompt: "city" }),
      appendTextElement,
      createActionButton,
    });

    await flushPromises();

    document.getElementById("swap-xyz-axis-x-select").value = "sampler";
    document.getElementById("swap-xyz-axis-x-select").dispatchEvent(new Event("change", { bubbles: true }));
    document.querySelector("#swap-xyz-axis-x-values-options input[value='euler']").checked = true;
    document.querySelector("#swap-xyz-axis-x-values-options input[value='euler']").dispatchEvent(new Event("change", { bubbles: true }));
    document.querySelector("#swap-xyz-axis-x-values-options input[value='dpmpp_2m']").checked = true;
    document.querySelector("#swap-xyz-axis-x-values-options input[value='dpmpp_2m']").dispatchEvent(new Event("change", { bubbles: true }));
    document.getElementById("swap-xyz-swap-xy").click();

    expect(document.getElementById("swap-xyz-axis-y-select").value).toBe("sampler");
    expect(document.getElementById("swap-xyz-axis-y-values-multiselect").hidden).toBe(false);
    expect(
      Array.from(
        document.querySelectorAll("#swap-xyz-axis-y-values-options input:checked"),
      ).map((input) => input.value),
    ).toEqual(["euler", "dpmpp_2m"]);
    expect(document.getElementById("swap-xyz-axis-x-values").hidden).toBe(false);
  });

  test("switches choice axes between dropdown and text modes like a1111 csv mode", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);
    const bootstrapState = createBootstrapState();

    createXYZPlotShell({
      idPrefix: "csv-mode-xyz",
      parent,
      mode: "txt2img",
      bootstrapState,
      buildBaseRequest: () => ({ prompt: "city" }),
      appendTextElement,
      createActionButton,
    });

    await flushPromises();

    document.getElementById("csv-mode-xyz-axis-z-select").value = "checkpoint_name";
    document.getElementById("csv-mode-xyz-axis-z-select").dispatchEvent(new Event("change", { bubbles: true }));
    document.querySelector("#csv-mode-xyz-axis-z-values-options input[value='model-a.safetensors']").checked = true;
    document.querySelector("#csv-mode-xyz-axis-z-values-options input[value='model-a.safetensors']").dispatchEvent(new Event("change", { bubbles: true }));
    document.querySelector("#csv-mode-xyz-axis-z-values-options input[value='model-b.safetensors']").checked = true;
    document.querySelector("#csv-mode-xyz-axis-z-values-options input[value='model-b.safetensors']").dispatchEvent(new Event("change", { bubbles: true }));

    document.getElementById("csv-mode-xyz-csv-mode").checked = true;
    document.getElementById("csv-mode-xyz-csv-mode").dispatchEvent(new Event("change", { bubbles: true }));

    expect(document.getElementById("csv-mode-xyz-axis-z-values").hidden).toBe(false);
    expect(document.getElementById("csv-mode-xyz-axis-z-values-multiselect").hidden).toBe(true);
    expect(document.getElementById("csv-mode-xyz-axis-z-values").value).toBe("model-a.safetensors, model-b.safetensors");

    document.getElementById("csv-mode-xyz-axis-z-fill").click();
    expect(document.getElementById("csv-mode-xyz-axis-z-values").value).toBe(
      "model-a.safetensors, model-b.safetensors",
    );

    document.getElementById("csv-mode-xyz-csv-mode").checked = false;
    document.getElementById("csv-mode-xyz-csv-mode").dispatchEvent(new Event("change", { bubbles: true }));

    expect(document.getElementById("csv-mode-xyz-axis-z-values").hidden).toBe(true);
    expect(document.getElementById("csv-mode-xyz-axis-z-values-multiselect").hidden).toBe(false);
    expect(
      Array.from(
        document.querySelectorAll("#csv-mode-xyz-axis-z-values-options input:checked"),
      ).map((input) => input.value),
    ).toEqual(["model-a.safetensors", "model-b.safetensors"]);
  });

  test("uses dropdown mode for whitelisted choice axes including hires upscaler", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);

    createXYZPlotShell({
      idPrefix: "txt2img-hires",
      parent,
      mode: "txt2img",
      bootstrapState: createBootstrapState(),
      buildBaseRequest: () => ({ prompt: "city" }),
      appendTextElement,
      createActionButton,
    });

    await flushPromises();

    document.getElementById("txt2img-hires-axis-z-select").value = "hires_upscaler";
    document.getElementById("txt2img-hires-axis-z-select").dispatchEvent(new Event("change", { bubbles: true }));

    expect(document.getElementById("txt2img-hires-axis-z-values").hidden).toBe(true);
    expect(document.getElementById("txt2img-hires-axis-z-values-multiselect").hidden).toBe(false);
    expect(document.getElementById("txt2img-hires-axis-z-values-summary").textContent).toContain("Select values");
    expect(document.getElementById("txt2img-hires-axis-z-fill").hidden).toBe(false);
    expect(document.getElementById("txt2img-hires-axis-z-fill").disabled).toBe(false);
    expect(
      Array.from(document.querySelectorAll("#txt2img-hires-axis-z-values-options input")).map((input) => input.value),
    ).toEqual(["Latent", "Latent (bicubic)", "Bislerp"]);
  });

  test("serializes xyz seed-policy controls into the run payload", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);
    const bootstrapState = createBootstrapState();

    createXYZPlotShell({
      idPrefix: "seed-policy-xyz",
      parent,
      mode: "txt2img",
      bootstrapState,
      buildBaseRequest: () => ({ prompt: "seed city", seed: -1 }),
      appendTextElement,
      createActionButton,
    });

    await flushPromises();

    document.getElementById("seed-policy-xyz-axis-x-values").value = "10, 20";
    document.getElementById("seed-policy-xyz-axis-y-values").value = "5.5, 7";
    document.getElementById("seed-policy-xyz-axis-z-select").value = "";
    document.getElementById("seed-policy-xyz-axis-z-select").dispatchEvent(new Event("change", { bubbles: true }));
    document.getElementById("seed-policy-xyz-keep-negative-one-seed").checked = true;
    document.getElementById("seed-policy-xyz-vary-seeds-x").checked = true;
    document.getElementById("seed-policy-xyz-vary-seeds-z").checked = true;

    document.getElementById("seed-policy-xyz-run").click();
    await flushPromises();

    expect(bootstrapState.runXYZPlotRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        keep_negative_one_seed: true,
        vary_seeds_x: true,
        vary_seeds_y: false,
        vary_seeds_z: true,
      }),
    );
  });

  test("keeps prompt-axis examples in placeholders while hiding fill", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);

    createXYZPlotShell({
      idPrefix: "prompt-xyz",
      parent,
      mode: "txt2img",
      bootstrapState: createBootstrapState(),
      buildBaseRequest: () => ({ prompt: "cat portrait" }),
      appendTextElement,
      createActionButton,
    });

    await flushPromises();

    document.getElementById("prompt-xyz-axis-x-select").value = "prompt_sr";
    document.getElementById("prompt-xyz-axis-x-select").dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("prompt-xyz-axis-x-values").placeholder).toBe("cat, dog, fox");
    expect(document.getElementById("prompt-xyz-axis-x-fill").hidden).toBe(true);

    document.getElementById("prompt-xyz-axis-y-select").value = "prompt_order";
    document.getElementById("prompt-xyz-axis-y-select").dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("prompt-xyz-axis-y-values").placeholder).toBe("cat, dog, bird");
    expect(document.getElementById("prompt-xyz-axis-y-fill").hidden).toBe(true);
  });

  test("uses A1111 hires examples and user-facing input-mode hints", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);

    createXYZPlotShell({
      idPrefix: "hires-hint-xyz",
      parent,
      mode: "txt2img",
      bootstrapState: createBootstrapState(),
      buildBaseRequest: () => ({ prompt: "city" }),
      appendTextElement,
      createActionButton,
    });

    await flushPromises();

    document.getElementById("hires-hint-xyz-axis-x-select").value = "hires_steps";
    document.getElementById("hires-hint-xyz-axis-x-select").dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("hires-hint-xyz-axis-x-values").placeholder).toBe("0, 10, 20");
    expect(document.getElementById("hires-hint-xyz-axis-x-hint").textContent).toContain("CSV values or ranges");

    document.getElementById("hires-hint-xyz-axis-y-select").value = "prompt_sr";
    document.getElementById("hires-hint-xyz-axis-y-select").dispatchEvent(new Event("change", { bubbles: true }));
    expect(document.getElementById("hires-hint-xyz-axis-y-hint").textContent).toContain("SOURCE, TARGET1, TARGET2");
  });

  test("wires the results preview into the shared fullscreen viewer", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);
    let fullscreenActive = false;

    createXYZPlotShell({
      idPrefix: "xyz-preview",
      parent,
      mode: "img2img",
      bootstrapState: createBootstrapState({
        fetchXYZPlotSessionsRequest: vi.fn(async () => ({
          ok: true,
          data: { sessions: [] },
        })),
      }),
      buildBaseRequest: () => ({ prompt: "portrait", denoise_strength: 0.5 }),
      appendTextElement,
      createActionButton,
      createIconActionButton,
      createPreviewFullscreenViewer: (config) =>
        createPreviewFullscreenViewer(config, {
          isCanvasElementFullscreen: () => fullscreenActive,
          toggleCanvasFullscreen: async () => {
            fullscreenActive = !fullscreenActive;
            return fullscreenActive ? "entered" : "exited";
          },
        }),
    });

    await flushPromises();

    document.getElementById("xyz-preview-axis-y-select").value = "denoising_strength";
    document.getElementById("xyz-preview-axis-y-select").dispatchEvent(new Event("change", { bubbles: true }));
    document.getElementById("xyz-preview-axis-x-values").value = "1, 2";
    document.getElementById("xyz-preview-axis-y-values").value = "0.35, 0.55";
    document.getElementById("xyz-preview-axis-z-select").value = "";
    document.getElementById("xyz-preview-axis-z-select").dispatchEvent(new Event("change", { bubbles: true }));

    document.getElementById("xyz-preview-run").click();
    await flushPromises();
    document.getElementById("xyz-preview-refresh").click();
    await flushPromises();

    const fullscreenButton = document.getElementById("xyz-preview-preview-fullscreen");
    expect(fullscreenButton).not.toBeNull();
    fullscreenButton.click();
    await flushPromises();

    const zoomSlider = document.getElementById("xyz-preview-fullscreen-zoom");
    expect(zoomSlider).not.toBeNull();
    expect(zoomSlider.parentElement.hidden).toBe(false);
    expect(document.getElementById("xyz-preview-session-status").textContent).toContain("entered fullscreen mode");
  });
});
