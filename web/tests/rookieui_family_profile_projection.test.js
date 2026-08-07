import { describe, expect, test } from "vitest";

import {
  DEFAULT_MODEL_FAMILY_REGISTRY_ENTRIES,
  DEFAULT_MODEL_FAMILY_FALLBACK_PROVENANCE,
  buildModelFamilyStableProjection,
} from "../rookieui_api.js";

const EXPECTED_SHIPPED_PROFILE_IDS = [
  "sd15",
  "sdxl",
  "pony",
  "illustrious",
  "noob",
  "anima",
  "chroma",
  "ernie_image",
  "ernie_image_turbo",
  "flux",
  "flux_krea_dev",
  "flux2_dev",
  "ideogram4",
  "krea2_turbo",
  "klein_4b",
  "klein_9b",
  "hidream_i1_dev_fp8",
  "hidream_i1_fast",
  "hidream_i1_full",
  "longcat_image",
  "qwen_image",
  "qwen_image_edit",
  "qwen_image_edit_2511",
  "firered_image_edit",
  "firered_image_edit_lightning",
  "flux_kontext_dev_edit",
  "flux2_image_edit",
  "klein_9b_kv_image_edit",
  "longcat_image_edit",
  "z_image",
  "z_image_turbo",
];

describe("family/profile offline fallback projection", () => {
  test("freezes the shipped order and explicit fallback provenance", () => {
    expect(DEFAULT_MODEL_FAMILY_REGISTRY_ENTRIES.map((entry) => entry.id)).toEqual(EXPECTED_SHIPPED_PROFILE_IDS);
    expect(DEFAULT_MODEL_FAMILY_FALLBACK_PROVENANCE).toEqual({
      canonical_owner: "python_manifest",
      contract_version: "model-family-20260713-effective-parameters",
      mode: "static-fail-closed",
      source: "fallback",
    });
  });

  test("matches stable backend fields for current profiles", () => {
    const byId = new Map(DEFAULT_MODEL_FAMILY_REGISTRY_ENTRIES.map((entry) => [entry.id, entry]));
    expect(buildModelFamilyStableProjection(byId.get("flux_krea_dev"))).toMatchObject({
      id: "flux_krea_dev",
      default_steps: 20,
      default_cfg_scale: 1,
      public_base_family: "flux",
      available_surface_flows: ["txt2img"],
      negative_prompt_mode: "zeroed",
    });
    expect(buildModelFamilyStableProjection(byId.get("qwen_image"))).toMatchObject({
      id: "qwen_image",
      default_steps: 50,
      default_cfg_scale: 4,
      default_shift: 3.1,
      official_template_lora_label: "Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors",
    });
    expect(buildModelFamilyStableProjection(byId.get("qwen_image_edit_2511"))).toMatchObject({
      id: "qwen_image_edit_2511",
      default_steps: 40,
      default_cfg_scale: 4,
      image_edit_profile: true,
      reference_input_mode: "multi",
      max_direct_references: 3,
      encoder_family: "qwen_image_edit_2511",
      available_surface_flows: ["img2img"],
    });
  });
});
