export type RookieUIApiStatus = "ok" | "queued" | "invalid-request" | "network-unavailable" | string;

export interface RookieUIApiResult<TData> {
  ok: boolean;
  status: number;
  data: TData;
}

export interface RookieUIResourceResult<TData> {
  ok: boolean;
  source: "server" | "fallback" | string;
  data: TData;
}

export type RookieUIJsonObject = Record<string, unknown>;

export interface RookieUIClientScopedOptions {
  clientId?: string;
}

export interface RookieUIAbortableClientOptions extends RookieUIClientScopedOptions {
  signal?: AbortSignal;
}

export interface RookieUIXYZPlotSessionDetailOptions extends RookieUIAbortableClientOptions {
  includeCells?: boolean;
}

export interface RookieUIPromptWorkbenchStatePayload extends RookieUIJsonObject {
  workbench_open?: boolean;
  active_panel?: string;
  draft_prompt?: string;
  selected_entry_id?: string;
}

export interface RookieUIQueueFallback {
  source: "fallback";
  queue_remaining: number;
  jobs?: unknown[];
  job?: unknown;
}

export type RookieUIResourceLoader<TData = RookieUIJsonObject> = (
  fetchImpl?: typeof globalThis.fetch,
) => Promise<RookieUIResourceResult<TData>>;

export interface RookieUINetworkUnavailable {
  status: "network-unavailable";
  detail: string;
}

export interface RookieUIQueuedSubmission {
  accepted?: boolean;
  prompt_id?: string;
  node_id?: string;
  detail?: string;
}

export interface RookieUIGenerationResponse {
  status?: RookieUIApiStatus;
  mode?: "queued" | "fallback" | string;
  submission?: RookieUIQueuedSubmission;
  detail?: string;
}

export interface RookieUITxt2ImgRequest {
  prompt?: string;
  negative_prompt?: string;
  profile?: string;
  checkpoint?: string;
  sampler?: string;
  scheduler?: string;
  seed?: number;
  steps?: number;
  cfg_scale?: number;
  width?: number;
  height?: number;
  batch_size?: number;
  [key: string]: unknown;
}

export interface RookieUIImg2ImgRequest extends RookieUITxt2ImgRequest {
  image_asset?: string;
  image_data?: string;
  denoising_strength?: number;
  mode?: string;
  mask_asset?: string;
  mask_data?: string;
}

export interface RookieUIPngInfoInspectRequest {
  image_asset?: string;
  image_data?: string;
  [key: string]: unknown;
}

export interface RookieUIPngInfoInspectResponse {
  status?: RookieUIApiStatus;
  target_form?: "txt2img" | "img2img" | "extras" | string;
  payload?: Record<string, unknown>;
  unsupported_fields?: string[];
  detail?: string;
}

export interface RookieUIExtrasRequest {
  mode?: "single_image" | "batch" | string;
  image_asset?: string;
  image_data?: string;
  resize_mode?: string;
  scale?: number;
  width?: number;
  height?: number;
  [key: string]: unknown;
}

export interface RookieUIExtrasResponse {
  status?: RookieUIApiStatus;
  output_assets?: string[];
  preview_asset?: string;
  detail?: string;
}

export function submitRookieUITxt2Img(
  payload: RookieUITxt2ImgRequest,
  fetchImpl?: typeof globalThis.fetch,
): Promise<RookieUIApiResult<RookieUIGenerationResponse | RookieUINetworkUnavailable>>;

export function submitRookieUIImg2Img(
  payload: RookieUIImg2ImgRequest,
  fetchImpl?: typeof globalThis.fetch,
): Promise<RookieUIApiResult<RookieUIGenerationResponse | RookieUINetworkUnavailable>>;

export function inspectRookieUIPngInfo(
  payload: RookieUIPngInfoInspectRequest,
  fetchImpl?: typeof globalThis.fetch,
): Promise<RookieUIApiResult<RookieUIPngInfoInspectResponse | RookieUINetworkUnavailable>>;

export function submitRookieUIExtras(
  payload: RookieUIExtrasRequest,
  fetchImpl?: typeof globalThis.fetch,
): Promise<RookieUIApiResult<RookieUIExtrasResponse | RookieUINetworkUnavailable>>;

export function fetchRookieUIResource<TData>(
  path: string,
  fallbackData: TData,
  fetchImpl?: typeof globalThis.fetch,
): Promise<RookieUIResourceResult<TData>>;

export function postRookieUIJson<TPayload, TData>(
  path: string,
  payload: TPayload,
  fallbackData: TData,
  fetchImpl?: typeof globalThis.fetch,
  options?: RookieUIJsonObject,
): Promise<RookieUIApiResult<TData>>;

export const fetchRookieUICapabilities: RookieUIResourceLoader;
export const fetchRookieUIModels: RookieUIResourceLoader;
export const fetchRookieUIPresets: RookieUIResourceLoader;
export const fetchRookieUICompatibility: RookieUIResourceLoader;
export const fetchRookieUIControlNetModels: RookieUIResourceLoader;
export const fetchRookieUIControlNetModules: RookieUIResourceLoader;
export const fetchRookieUIControlNetTypes: RookieUIResourceLoader;
export const fetchRookieUIADetailerCatalog: RookieUIResourceLoader;
export const fetchRookieUIPromptWorkbenchConfig: RookieUIResourceLoader;
export const fetchRookieUIPromptWorkbenchProviders: RookieUIResourceLoader;
export const fetchRookieUIPromptWorkbenchBlacklist: RookieUIResourceLoader;
export const fetchRookieUIXYZPlotAxes: RookieUIResourceLoader;

export function fetchRookieUIPromptWorkbenchState(
  namespace: string,
  fetchImpl?: typeof globalThis.fetch,
): Promise<RookieUIResourceResult<RookieUIJsonObject>>;
export function updateRookieUIPromptWorkbenchState(
  namespace: string,
  state: RookieUIPromptWorkbenchStatePayload,
  fetchImpl?: typeof globalThis.fetch,
): Promise<RookieUIApiResult<RookieUIJsonObject>>;
export function fetchRookieUIQueue(
  fetchImpl?: typeof globalThis.fetch,
  options?: RookieUIClientScopedOptions,
): Promise<RookieUIResourceResult<RookieUIQueueFallback | RookieUIJsonObject>>;
export function fetchRookieUIQueueJob(
  promptId: string,
  options?: RookieUIClientScopedOptions,
  fetchImpl?: typeof globalThis.fetch,
): Promise<RookieUIResourceResult<RookieUIQueueFallback | RookieUIJsonObject> | RookieUIApiResult<RookieUIJsonObject>>;
export function fetchRookieUIXYZPlotSessions(
  fetchImpl?: typeof globalThis.fetch,
  options?: RookieUIAbortableClientOptions,
): Promise<RookieUIResourceResult<RookieUIJsonObject>>;
export function fetchRookieUIXYZPlotSessionDetail(
  sessionId: string,
  options?: RookieUIXYZPlotSessionDetailOptions,
  fetchImpl?: typeof globalThis.fetch,
): Promise<RookieUIResourceResult<RookieUIJsonObject> | RookieUIApiResult<RookieUIJsonObject>>;
export function cancelRookieUIXYZPlotSession(
  sessionId: string,
  options?: RookieUIAbortableClientOptions,
  fetchImpl?: typeof globalThis.fetch,
): Promise<RookieUIApiResult<RookieUIJsonObject>>;
