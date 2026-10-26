// @vitest-environment jsdom
import { describe, expect, test, vi } from "vitest";
import { createMossImageController, matchesMossAsset } from "../../web/sidebar_tabs/rookieui_moss_image_controls.js";
import { MOSS_IMAGE_FALLBACK_ENTRIES } from "../../web/rookieui_moss_image_profiles.js";
import { buildTxt2ImgPayloadFromElements } from "../../web/sidebar_tabs/rookieui_generation_payload_state.js";
import { createDefaultCapabilities } from "../../web/api/rookieui_inventory_api.js";
import { buildProfileLookup } from "../../web/rookieui_sidebar_shell_utils.js";
import { createGenerationRuntimeHelpers, createGenerationRuntimeState } from "../../web/rookieui_generation_runtime.js";

const control = (value = "") => Object.assign(document.createElement("input"), { value });
function elements(profile = "moss_image_base") {
  const result = {};
  for (const name of ["prompt", "negativePrompt", "profileState", "lowBits", "checkpoint", "vae", "textEncoder", "width", "height", "steps", "cfgScale", "shift", "fluxGuidance", "sampler", "scheduler", "ideogramMode", "promptEnhancementEnabled", "seed", "seedExtra", "batchSize", "batchCount", "clipSkip", "hiresEnabled", "hiresScale", "hiresSteps", "hiresDenoise", "hiresUpscaleMethod", "templateLoraName", "templateLoraEnabled", "templateLoraStrength", "templateLoraTriggerWord", "loraName", "loraStrengthModel", "loraStrengthClip", "adetailer", "controlnetUnits", "mossSlgEnabled"]) {
    result[name] = control();
  }
  Object.assign(result.profileState, { value: profile });
  result.prompt.value = "(literal:1.2) 中文";
  result.negativePrompt.value = "否定";
  result.lowBits.value = "fp8";
  result.clipSkip.value = "2";
  result.shift.value = "3";
  result.loraName.value = "old.safetensors";
  result.adetailer.value = '{"enabled":true}';
  result.controlnetUnits.value = '[{"enabled":true}]';
  result.hiresEnabled.checked = true;
  result.promptEnhancementEnabled.checked = true;
  result.mossSlgEnabled.checked = false;
  return result;
}

describe("native MOSS controls", () => {
  test("preview transfer cannot silently apply MOSS metadata to img2img", async () => {
    const applyCrossPanePayload = vi.fn();
    const helpers = createGenerationRuntimeHelpers({ emitFrontendDebugWarning: vi.fn(),
      setPreviewContent: vi.fn(), applyCrossPanePayload, activateShellTab: vi.fn() });
    const preview = document.createElement("div");
    preview.innerHTML = '<img class="rookieui-shell__preview-image" src="data:image/png;base64,ZmFrZQ==">';
    const status = document.createElement("p");
    await helpers.transferPreviewToImg2Img({ img2img: { applyPayload: vi.fn() } },
      createGenerationRuntimeState(), status, preview, {
        inspectPngInfoRequest: async () => ({ ok: true, data: { source_type: "rookieui",
          payload: { profile: "moss_image_base", moss_options: { slg_enabled: true } } } }),
      });
    expect(applyCrossPanePayload).not.toHaveBeenCalled();
    expect(status.textContent).toContain("MOSS");
  });
  test("submitted options preserve authored text and exclude stale SD controls", () => {
    const payload = buildTxt2ImgPayloadFromElements(elements());
    expect(payload).toMatchObject({ prompt: "(literal:1.2) 中文", negative_prompt: "否定",
      moss_options: { slg_enabled: false }, dtype_profile: "automatic", clip_skip: 1,
      shift: null, flux_guidance: null, lora_name: "", hires_enabled: false,
      prompt_enhancement_enabled: false, controlnet_units: [], adetailer: {} });
    expect(buildTxt2ImgPayloadFromElements(elements("sd15"))).not.toHaveProperty("moss_options");
  });

  test("role filtering is exact and variant scoped, including subfolders", () => {
    expect(matchesMossAsset("moss_image_base", "sub\\moss_image_base_bf16.safetensors", "diffusion_models")).toBe(true);
    expect(matchesMossAsset("moss_image_base", "moss_image_sft_bf16.safetensors", "diffusion_models")).toBe(false);
    expect(matchesMossAsset("moss_image_base", "qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors", "text_encoders")).toBe(false);
    expect(matchesMossAsset("moss_image_base", "shared/flux2-vae.safetensors", "vae")).toBe(true);
  });

  test("offline capabilities fail closed and keep per-variant SLG defaults", () => {
    expect(MOSS_IMAGE_FALLBACK_ENTRIES.map(entry => entry.default_moss_slg_enabled)).toEqual([true, false]);
    const capabilities = createDefaultCapabilities();
    expect(capabilities.moss_image.profiles.moss_image_base.available).toBe(false);
    expect(capabilities.moss_image.profiles.moss_image_base.reasons.length).toBeGreaterThan(0);
  });

  test("profile defaults, explicit restore and missing SLG cannot bypass enqueue gating", () => {
    const inputs = elements();
    for (const key of ["checkpoint", "textEncoder", "vae"]) inputs[key] = document.createElement("select");
    const form = document.createElement("form");
    Object.values(inputs).forEach(input => form.append(input));
    const submit = document.createElement("button");
    const field = document.createElement("div");
    const status = document.createElement("div");
    const profileLookup = buildProfileLookup({ model_families: { entries: MOSS_IMAGE_FALLBACK_ENTRIES } });
    const capabilities = { moss_image: { profiles: { moss_image_base: {
      without_slg_available: true, without_slg_reasons: [], slg_available: false, slg_reasons: ["Missing SLG node"]
    }, moss_image_sft: { without_slg_available: true, without_slg_reasons: [], slg_available: true, slg_reasons: [] } } } };
    const controller = createMossImageController({ elements: inputs, form, submitButton: submit,
      profileLookup, capabilities, inventory: {
        diffusion_models: ["moss_image_base_bf16.safetensors", "moss_image_sft_bf16.safetensors"],
        text_encoders: ["qwen3.5_9b_bf16.safetensors"], vae: ["flux2-vae.safetensors"],
      }, field, status });
    controller.sync({ resetDefaults: true });
    expect(inputs.mossSlgEnabled.checked).toBe(true);
    expect(submit.disabled).toBe(true);
    expect(status.textContent).toContain("Missing SLG node");
    expect(inputs.clipSkip.disabled).toBe(true);
    inputs.mossSlgEnabled.checked = false;
    inputs.mossSlgEnabled.dispatchEvent(new Event("change"));
    expect(submit.disabled).toBe(false);
    inputs.profileState.value = "moss_image_sft";
    controller.sync({ resetDefaults: true });
    expect(inputs.mossSlgEnabled.checked).toBe(false);
    controller.sync({ payload: { moss_options: { slg_enabled: true } } });
    expect(inputs.mossSlgEnabled.checked).toBe(true);
    controller.sync({ payload: { checkpoint_name: "missing/moss_image_sft_bf16.safetensors" } });
    expect(inputs.checkpoint.value).toBe("");
    expect(submit.disabled).toBe(true);
    expect(status.textContent).toContain("Select a matching installed MOSS");
    inputs.profileState.value = "sd15";
    controller.sync();
    expect(field.hidden).toBe(true);
    expect(inputs.clipSkip.disabled).toBe(false);
    expect(submit.disabled).toBe(false);
    expect(inputs.prompt.value).toBe("(literal:1.2) 中文");
  });
});
