export type RookieUIApiStatus = "ok" | "queued" | "invalid-request" | "network-unavailable" | string;

export interface RookieUIApiResult<TData> {
  ok: boolean;
  status: number;
  data: TData;
}

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
