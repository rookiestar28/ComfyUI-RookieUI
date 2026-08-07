import { fetchRookieUIResource, postRookieUIJson } from "./rookieui_api_transport.js";

export async function fetchRookieUIXYZPlotAxes(fetchImpl = globalThis.fetch) {
  return fetchRookieUIResource(
    "/rookieui/xyz-plot/axes",
    {
      contract: {
        version: "r125-20260417",
        surface: "xyz_plot_axes",
        route_family: "/rookieui/xyz-plot",
      },
      axes: {
        steps: {
          axis_id: "steps",
          title: "Steps",
          support_tier: "direct",
          mode_scopes: ["txt2img", "img2img"],
          value_input_mode: "int_csv_or_range",
          choices: [],
          session_runner_support: true,
        },
        cfg_scale: {
          axis_id: "cfg_scale",
          title: "CFG Scale",
          support_tier: "direct",
          mode_scopes: ["txt2img", "img2img"],
          value_input_mode: "float_csv_or_range",
          choices: [],
          session_runner_support: true,
        },
        sampler: {
          axis_id: "sampler",
          title: "Sampler",
          support_tier: "direct",
          mode_scopes: ["txt2img", "img2img"],
          value_input_mode: "choices_or_csv",
          choices: [],
          session_runner_support: true,
        },
      },
      axis_order: ["steps", "cfg_scale", "sampler"],
    },
    fetchImpl,
  );
}

export async function submitRookieUIXYZPlotEstimate(payload, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/xyz-plot/estimate",
    payload ?? {},
    {
      contract: {
        version: "r125-20260417",
        surface: "xyz_plot_estimate",
        route_family: "/rookieui/xyz-plot",
      },
      estimate: {
        cell_count: 0,
        generated_image_count: 0,
        total_steps: 0,
        projected_grid_megapixels: 0,
        max_grid_megapixels: 200,
      },
      can_run: false,
      warnings: [],
      warning_codes: [],
    },
    fetchImpl,
  );
}

export async function submitRookieUIXYZPlotRun(payload, fetchImpl = globalThis.fetch) {
  return postRookieUIJson(
    "/rookieui/xyz-plot/run",
    payload ?? {},
    {
      contract: {
        version: "r125-20260417",
        surface: "xyz_plot_run",
        route_family: "/rookieui/xyz-plot",
      },
      session: {
        session_id: "",
        status: "pending",
        summary: { total_cells: 0, pending_cells: 0 },
        axes: [],
        results: { status: "pending", main_grid: {}, sub_grids: [], lone_images: [], warnings: [] },
      },
    },
    fetchImpl,
  );
}

function buildXYZPlotSessionsPath(clientId) {
  if (!clientId) {
    return "/rookieui/xyz-plot/sessions";
  }
  const params = new URLSearchParams({ client_id: clientId });
  return `/rookieui/xyz-plot/sessions?${params.toString()}`;
}

export async function fetchRookieUIXYZPlotSessions(fetchImpl = globalThis.fetch, options = {}) {
  const clientId = typeof options?.clientId === "string" ? options.clientId : "";
  return fetchRookieUIResource(
    buildXYZPlotSessionsPath(clientId),
    {
      contract: {
        version: "r125-20260417",
        surface: "xyz_plot_session_list",
        route_family: "/rookieui/xyz-plot",
      },
      sessions: [],
    },
    fetchImpl,
  );
}

export async function fetchRookieUIXYZPlotSessionDetail(sessionId, options = {}, fetchImpl = globalThis.fetch) {
  const normalizedSessionId = String(sessionId ?? "").trim();
  if (!normalizedSessionId) {
    return {
      ok: false,
      status: 400,
      data: {
        status: "invalid-request",
        detail: "sessionId is required.",
      },
    };
  }
  const clientId = typeof options?.clientId === "string" ? options.clientId : "";
  const params = new URLSearchParams();
  if (clientId) {
    params.set("client_id", clientId);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return fetchRookieUIResource(
    `/rookieui/xyz-plot/sessions/${encodeURIComponent(normalizedSessionId)}${suffix}`,
    {
      contract: {
        version: "r125-20260417",
        surface: "xyz_plot_session_detail",
        route_family: "/rookieui/xyz-plot",
      },
      session: {
        session_id: normalizedSessionId,
        status: "pending",
        summary: { total_cells: 0, pending_cells: 0 },
        axes: [],
        cells: [],
        results: { status: "pending", main_grid: {}, sub_grids: [], lone_images: [], warnings: [] },
      },
    },
    fetchImpl,
  );
}

export async function cancelRookieUIXYZPlotSession(sessionId, options = {}, fetchImpl = globalThis.fetch) {
  const normalizedSessionId = String(sessionId ?? "").trim();
  if (!normalizedSessionId) {
    return {
      ok: false,
      status: 400,
      data: {
        status: "invalid-request",
        detail: "sessionId is required.",
      },
    };
  }
  const clientId = typeof options?.clientId === "string" ? options.clientId : "";
  return postRookieUIJson(
    `/rookieui/xyz-plot/sessions/${encodeURIComponent(normalizedSessionId)}/cancel`,
    clientId ? { client_id: clientId } : {},
    {
      contract: {
        version: "r125-20260417",
        surface: "xyz_plot_session_cancel",
        route_family: "/rookieui/xyz-plot",
      },
      session: {
        session_id: normalizedSessionId,
        status: "cancelled",
        cancel_requested: true,
        summary: { total_cells: 0, cancelled_cells: 0 },
        axes: [],
        cells: [],
        results: { status: "pending", main_grid: {}, sub_grids: [], lone_images: [], warnings: [] },
      },
    },
    fetchImpl,
  );
}
