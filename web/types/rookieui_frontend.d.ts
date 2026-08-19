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

export type RookieUIRuntimeJobId = string;
export type RookieUIRuntimeNodeId = string | number;

export interface RookieUIRuntimeProgressEvent {
  value: number;
  max: number;
  prompt_id: RookieUIRuntimeJobId;
  node: RookieUIRuntimeNodeId;
}

export interface RookieUIRuntimeNodeProgressState {
  value: number;
  max: number;
  state: "pending" | "running" | "finished" | "error";
  node_id: RookieUIRuntimeNodeId;
  prompt_id: RookieUIRuntimeJobId;
  display_node_id?: RookieUIRuntimeNodeId;
  parent_node_id?: RookieUIRuntimeNodeId;
  real_node_id?: RookieUIRuntimeNodeId;
}

export interface RookieUIRuntimeProgressStateEvent {
  prompt_id: RookieUIRuntimeJobId;
  nodes: Record<string, RookieUIRuntimeNodeProgressState>;
}

export interface RookieUIRuntimeTerminalEvent {
  prompt_id: RookieUIRuntimeJobId;
  [key: string]: unknown;
}

export interface RookieUIRuntimeEventMap {
  progress: RookieUIRuntimeProgressEvent;
  progress_state: RookieUIRuntimeProgressStateEvent;
  b_preview_with_metadata: unknown;
  b_preview: unknown;
  execution_success: RookieUIRuntimeTerminalEvent;
  execution_error: RookieUIRuntimeTerminalEvent;
  execution_interrupted: RookieUIRuntimeTerminalEvent;
}

export type RookieUIRuntimeEventListener<TEvent extends keyof RookieUIRuntimeEventMap> = (
  event: CustomEvent<RookieUIRuntimeEventMap[TEvent]>,
) => void;

export interface RookieUIExtensionRuntimeApi {
  clientId?: string;
  fetchApi?: (route: string, options?: RequestInit) => Promise<Response>;
  apiURL?: (route: string) => string;
  addEventListener?: <TEvent extends keyof RookieUIRuntimeEventMap>(
    eventName: TEvent,
    listener: RookieUIRuntimeEventListener<TEvent>,
  ) => void;
  removeEventListener?: <TEvent extends keyof RookieUIRuntimeEventMap>(
    eventName: TEvent,
    listener: RookieUIRuntimeEventListener<TEvent>,
  ) => void;
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
      destroy?: () => void;
    }) => void;
    unregisterSidebarTab?: (id: string) => void;
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

export type RookieUIDisposer = () => void;

export interface RookieUIControllerEvent<TPayload = unknown> {
  type: string;
  payload: TPayload;
}

export interface RookieUIControllerSubscription<TPayload = unknown> {
  subscribe(listener: (event: RookieUIControllerEvent<TPayload>) => void): RookieUIDisposer;
  destroy(): void;
}

export interface RookieUIImg2ImgControllerState {
  mode: string;
  profileId: string;
  imageEditProfile: boolean;
  referenceLimit: number;
  referenceSlots: ReadonlyArray<Record<string, unknown>>;
  selectedMainSlot: number;
  imageAsset: string;
  imageData: string;
}

export interface RookieUIPromptWorkbenchControllerState {
  activeScope: "prompt" | "negative";
  activePanel: string;
  destroyed: boolean;
}

export interface RookieUILifecycleBoundary {
  mount(): void | Promise<void>;
  destroy(): void;
  readonly destroyed?: boolean;
}
