import { describe, expect, test, vi } from "vitest";

import {
  buildControlNetCatalog,
  buildRookieUIFeatureBootstrapRegistry,
  loadRookieUIBootstrapData,
} from "../rookieui_feature_registry.js";

describe("rookieui feature registry", () => {
  test("lists the expected integrated bootstrap surfaces", () => {
    const registry = buildRookieUIFeatureBootstrapRegistry({
      capabilities: vi.fn(),
      compatibility: vi.fn(),
      models: vi.fn(),
      presets: vi.fn(),
      controlnetModels: vi.fn(),
      controlnetModules: vi.fn(),
      controlnetTypes: vi.fn(),
      adetailerCatalog: vi.fn(),
      xyzPlot: vi.fn(),
      promptWorkbench: vi.fn(),
      queue: vi.fn(),
    });

    expect(registry.map((entry) => entry.featureId)).toEqual([
      "capabilities",
      "compatibility",
      "models",
      "presets",
      "controlnet_models",
      "controlnet_modules",
      "controlnet_types",
      "adetailer_catalog",
      "queue",
      "xyz_plot",
      "prompt_workbench",
      "controlnet_catalog",
      "model_family_registry",
    ]);
  });

  test("builds a composed controlnet catalog from model/module/type payloads", () => {
    expect(
      buildControlNetCatalog(
        { data: { source: "host", model_list: ["canny.safetensors"], default_model: "canny.safetensors" } },
        { data: { module_list: ["none", "canny"], default_module: "none" } },
        {
          data: {
            source: "host",
            contract: { version: "r72f75-test" },
            control_type_order: ["All", "Canny"],
            default_type: "All",
            control_types: { Canny: { module_list: ["none", "canny"], model_list: ["canny.safetensors"] } },
          },
        },
      ),
    ).toEqual({
      source: "host",
      contract: { version: "r72f75-test" },
      model_list: ["canny.safetensors"],
      module_list: ["none", "canny"],
      control_type_order: ["All", "Canny"],
      default_type: "All",
      default_module: "none",
      default_model: "canny.safetensors",
      control_types: { Canny: { module_list: ["none", "canny"], model_list: ["canny.safetensors"] } },
    });
  });

  test("loads bootstrap data through injected loaders and keeps queue client scope", async () => {
    const queueLoader = vi.fn(async (_fetchImpl, { clientId }) => ({ data: { jobs: [], clientId } }));
    const bootstrapData = await loadRookieUIBootstrapData(() => {}, {
      clientId: "client-123",
      loaders: {
        capabilities: async () => ({
          source: "host",
          data: {
            service: "rookieui",
            model_families: {
              contract_version: "f157-20260419",
              entries: [{ id: "ernie_image", text_encoder_visible: false, available_surface_flows: ["txt2img"] }],
            },
          },
        }),
        compatibility: async () => ({ data: { samplers: [] } }),
        models: async () => ({ data: { checkpoints: [] } }),
        presets: async () => ({ data: { presets: [] } }),
        controlnetModels: async () => ({ data: { source: "host", model_list: ["canny.safetensors"], default_model: "" } }),
        controlnetModules: async () => ({ data: { source: "internal", module_list: ["none", "canny"], default_module: "none" } }),
        controlnetTypes: async () => ({
          data: { source: "internal", control_type_order: ["All"], default_type: "All", control_types: {} },
        }),
        adetailerCatalog: async () => ({ data: { detectors: [] } }),
        xyzPlot: async () => ({ data: { axes: { steps: { axis_id: "steps" } } } }),
        promptWorkbench: async () => ({ data: { config: { language: "en" } } }),
        queue: queueLoader,
      },
    });

    expect(queueLoader).toHaveBeenCalledWith(expect.any(Function), { clientId: "client-123" });
    expect(bootstrapData.capabilitySource).toBe("host");
    expect(bootstrapData.capabilities).toMatchObject({ service: "rookieui" });
    expect(bootstrapData.queue).toEqual({ jobs: [], clientId: "client-123" });
    expect(bootstrapData.xyzPlot).toEqual({ axes: { steps: { axis_id: "steps" } } });
    expect(bootstrapData.promptWorkbench).toEqual({ config: { language: "en" } });
    expect(bootstrapData.controlnetCatalog.model_list).toEqual(["canny.safetensors"]);
    expect(bootstrapData.modelFamilyRegistry.contract_version).toBe("f157-20260419");
    expect(bootstrapData.modelFamilyRegistry.entries[0].id).toBe("ernie_image");
    expect(bootstrapData.adetailerCatalog).toEqual({ detectors: [] });
  });
});
