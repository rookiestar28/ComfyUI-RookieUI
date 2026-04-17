import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

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

    expect(document.getElementById("txt2img-xyz-axis-x-select").value).toBe("steps");
    document.getElementById("txt2img-xyz-axis-z-select").value = "checkpoint_name";
    document.getElementById("txt2img-xyz-axis-z-select").dispatchEvent(new Event("change", { bubbles: true }));
    document.getElementById("txt2img-xyz-axis-z-fill").click();
    expect(document.getElementById("txt2img-xyz-axis-z-values").value).toContain("model-a.safetensors");

    document.getElementById("txt2img-xyz-axis-x-values").value = "20, 28, 36";
    document.getElementById("txt2img-xyz-axis-y-values").value = "5.5, 7, 8.5";
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
      margin_size: 0,
    });
    expect(statusMessages.at(-1)).toContain("estimate");
  });

  test("runs, refreshes, and cancels sessions while updating preview state", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);
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
    });

    await flushPromises();

    document.getElementById("img2img-xyz-axis-x-values").value = "1, 2, 3";
    document.getElementById("img2img-xyz-axis-y-values").value = "0.35, 0.55, 0.75";
    document.getElementById("img2img-xyz-axis-y-select").value = "denoising_strength";
    document.getElementById("img2img-xyz-axis-y-select").dispatchEvent(new Event("change", { bubbles: true }));
    document.getElementById("img2img-xyz-axis-z-select").value = "";
    document.getElementById("img2img-xyz-axis-z-select").dispatchEvent(new Event("change", { bubbles: true }));

    document.getElementById("img2img-xyz-run").click();
    await flushPromises();

    expect(bootstrapState.runXYZPlotRequest).toHaveBeenCalledTimes(1);
    expect(document.getElementById("img2img-xyz-session-status").textContent).toContain("in_progress");

    document.getElementById("img2img-xyz-refresh").click();
    await flushPromises();

    expect(bootstrapState.fetchXYZPlotSessionDetailRequest).toHaveBeenCalledWith("xyz-1", "browser-1");
    const previewImage = document.querySelector("#img2img-xyz-main-grid-preview img");
    expect(previewImage?.getAttribute("src")).toBe("data:image/png;base64,ZmFrZQ==");
    expect(document.getElementById("img2img-xyz-result-summary").textContent).toContain("Sub-grids: 1");

    document.getElementById("img2img-xyz-cancel").click();
    await flushPromises();

    expect(bootstrapState.cancelXYZPlotSessionRequest).toHaveBeenCalledWith("xyz-1", "browser-1");
    expect(document.getElementById("img2img-xyz-session-status").textContent).toContain("cancelled");
  });
});
