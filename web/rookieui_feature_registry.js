/** @typedef {import("./types/rookieui_frontend").RookieUIBootstrapLoaders} RookieUIBootstrapLoaders */

import { buildDefaultBootstrapLoaders } from "./rookieui_feature_registry_loaders.js";

function toStringArray(rawValue) {
  return Array.isArray(rawValue)
    ? rawValue.map((value) => String(value ?? "").trim()).filter(Boolean)
    : [];
}

export function buildControlNetCatalog(modelResult, moduleResult, typeResult) {
  const modelList = toStringArray(modelResult?.data?.model_list);
  const moduleList = toStringArray(moduleResult?.data?.module_list);
  const controlTypeOrder = toStringArray(typeResult?.data?.control_type_order);
  const controlTypes =
    typeResult?.data?.control_types && typeof typeResult.data.control_types === "object"
      ? typeResult.data.control_types
      : {};
  const preprocessorProfiles =
    typeResult?.data?.preprocessor_profiles && typeof typeResult.data.preprocessor_profiles === "object"
      ? typeResult.data.preprocessor_profiles
      : {};

  return {
    source: String(typeResult?.data?.source ?? modelResult?.data?.source ?? moduleResult?.data?.source ?? "fallback"),
    contract:
      typeResult?.data?.contract ??
      modelResult?.data?.contract ??
      moduleResult?.data?.contract ?? {
        version: "r72-20260412",
        ui_variant: "integrated_sidebar_controlnet",
        unit_count: 3,
      },
    model_list: modelList,
    module_list: moduleList,
    control_type_order: controlTypeOrder,
    default_type: String(typeResult?.data?.default_type ?? "All"),
    default_module: String(moduleResult?.data?.default_module ?? "none"),
    default_model: String(modelResult?.data?.default_model ?? ""),
    control_types: controlTypes,
    preprocessor_profiles: preprocessorProfiles,
  };
}

/**
 * @param {RookieUIBootstrapLoaders} loaders
 */
export function buildRookieUIFeatureBootstrapRegistry(loaders) {
  return [
    {
      featureId: "capabilities",
      bootstrapKey: "capabilities",
      sourceKey: "capabilitySource",
      load: (fetchImpl) => loaders.capabilities(fetchImpl),
    },
    {
      featureId: "compatibility",
      bootstrapKey: "compatibility",
      load: (fetchImpl) => loaders.compatibility(fetchImpl),
    },
    {
      featureId: "models",
      bootstrapKey: "models",
      load: (fetchImpl) => loaders.models(fetchImpl),
    },
    {
      featureId: "presets",
      bootstrapKey: "presets",
      load: (fetchImpl) => loaders.presets(fetchImpl),
    },
    {
      featureId: "controlnet_models",
      bootstrapKey: "__controlnetModels",
      load: (fetchImpl) => loaders.controlnetModels(fetchImpl),
    },
    {
      featureId: "controlnet_modules",
      bootstrapKey: "__controlnetModules",
      load: (fetchImpl) => loaders.controlnetModules(fetchImpl),
    },
    {
      featureId: "controlnet_types",
      bootstrapKey: "__controlnetTypes",
      load: (fetchImpl) => loaders.controlnetTypes(fetchImpl),
    },
    {
      featureId: "adetailer_catalog",
      bootstrapKey: "adetailerCatalog",
      load: (fetchImpl) => loaders.adetailerCatalog(fetchImpl),
    },
    {
      featureId: "queue",
      bootstrapKey: "queue",
      load: (fetchImpl, context) => loaders.queue(fetchImpl, context),
    },
    {
      featureId: "xyz_plot",
      bootstrapKey: "xyzPlot",
      load: (fetchImpl) => loaders.xyzPlot(fetchImpl),
    },
    {
      featureId: "prompt_workbench",
      bootstrapKey: "promptWorkbench",
      load: (fetchImpl) => loaders.promptWorkbench(fetchImpl),
    },
    {
      featureId: "controlnet_catalog",
      bootstrapKey: "controlnetCatalog",
      compose: (loadedState) =>
        buildControlNetCatalog(
          loadedState.__controlnetModels,
          loadedState.__controlnetModules,
          loadedState.__controlnetTypes,
        ),
    },
    {
      featureId: "model_family_registry",
      bootstrapKey: "modelFamilyRegistry",
      compose: (loadedState) => loadedState.capabilities?.model_families ?? { contract_version: "", entries: [] },
    },
  ];
}

export async function loadRookieUIBootstrapData(
  fetchImpl,
  { clientId = "", loaders = null } = {},
) {
  const resolvedLoaders = loaders ?? (await buildDefaultBootstrapLoaders());
  const registry = buildRookieUIFeatureBootstrapRegistry(resolvedLoaders);
  const directEntries = registry.filter((entry) => typeof entry.load === "function");
  /** @type {Record<string, any>} */
  const loadedState = {};
  const results = await Promise.all(
    directEntries.map((entry) => entry.load(fetchImpl, { clientId })),
  );

  results.forEach((result, index) => {
    const entry = directEntries[index];
    loadedState[entry.bootstrapKey] = entry.bootstrapKey.startsWith("__") ? result : result?.data;
    if (entry.sourceKey) {
      loadedState[entry.sourceKey] = result?.source;
    }
  });

  registry
    .filter((entry) => typeof entry.compose === "function")
    .forEach((entry) => {
      loadedState[entry.bootstrapKey] = entry.compose(loadedState);
    });

  delete loadedState.__controlnetModels;
  delete loadedState.__controlnetModules;
  delete loadedState.__controlnetTypes;
  return loadedState;
}
