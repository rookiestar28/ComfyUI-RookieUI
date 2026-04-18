export interface RookieUIControlNetCatalog {
  source: string;
  contract: Record<string, unknown>;
  model_list: string[];
  module_list: string[];
  control_type_order: string[];
  default_type: string;
  default_module: string;
  default_model: string;
  control_types: Record<string, unknown>;
}

export interface RookieUIBootstrapLoaderResult<TData = unknown> {
  ok?: boolean;
  source?: string;
  data?: TData;
}

export interface RookieUIBootstrapLoadContext {
  clientId: string;
}

export type RookieUIBootstrapLoader<TData = unknown> = (
  fetchImpl: typeof fetch,
  context?: RookieUIBootstrapLoadContext,
) => Promise<RookieUIBootstrapLoaderResult<TData>>;

export interface RookieUIBootstrapLoaders {
  capabilities: RookieUIBootstrapLoader<Record<string, unknown>>;
  compatibility: RookieUIBootstrapLoader<Record<string, unknown>>;
  models: RookieUIBootstrapLoader<Record<string, unknown>>;
  presets: RookieUIBootstrapLoader<Record<string, unknown>>;
  controlnetModels: RookieUIBootstrapLoader<Record<string, unknown>>;
  controlnetModules: RookieUIBootstrapLoader<Record<string, unknown>>;
  controlnetTypes: RookieUIBootstrapLoader<Record<string, unknown>>;
  adetailerCatalog: RookieUIBootstrapLoader<Record<string, unknown>>;
  promptWorkbench: RookieUIBootstrapLoader<Record<string, unknown>>;
  xyzPlot: RookieUIBootstrapLoader<Record<string, unknown>>;
  queue: RookieUIBootstrapLoader<Record<string, unknown>>;
}

export interface RookieUIFeatureBootstrapRegistryEntry {
  featureId: string;
  bootstrapKey: string;
  sourceKey?: string;
  load?: RookieUIBootstrapLoader;
  compose?: (loadedState: Record<string, any>) => unknown;
}

export interface RookieUIExtensionRuntimeApi {
  clientId?: string;
  addEventListener?: (...args: unknown[]) => void;
  removeEventListener?: (...args: unknown[]) => void;
}

export interface RookieUIExtensionApp {
  api?: RookieUIExtensionRuntimeApi | null;
  registerExtension: (definition: { name: string; setup: () => Promise<void> | void }) => unknown;
  extensionManager?: {
    registerSidebarTab?: (tab: {
      id: string;
      icon: string;
      title: string;
      tooltip: string;
      type: string;
      render: (container: HTMLElement) => void;
    }) => void;
  } | null;
}

export interface RookieUIRegisterExtensionOptions {
  app?: RookieUIExtensionApp;
  windowRef?: Window & {
    app?: { api?: RookieUIExtensionRuntimeApi | null };
    electronAPI?: unknown;
    __COMFYUI_DESKTOP__?: boolean;
    __ROOKIEUI_BOOTSTRAP__?: Record<string, unknown>;
  };
  documentRef?: Document;
  fetchImpl?: typeof fetch;
}
