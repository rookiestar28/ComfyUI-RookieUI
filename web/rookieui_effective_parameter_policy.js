const EFFECTIVE_PARAMETER_POLICY_BY_PROFILE = Object.freeze({
  ernie_image_turbo: { negative_prompt_mode: "zeroed" },
  flux: { negative_prompt_mode: "zeroed" },
  flux_krea_dev: { negative_prompt_mode: "zeroed" },
  flux2_dev: { scheduler_control_mode: "flux2", negative_prompt_mode: "unused" },
  ideogram4: { scheduler_control_mode: "ideogram4", negative_prompt_mode: "zeroed" },
  krea2_turbo: { negative_prompt_mode: "zeroed" },
  klein_4b: { scheduler_control_mode: "flux2" },
  klein_9b: { scheduler_control_mode: "flux2" },
  qwen_image: { negative_prompt_mode: "zeroed" },
  flux_kontext_dev_edit: { negative_prompt_mode: "zeroed" },
  flux2_image_edit: { scheduler_control_mode: "flux2", negative_prompt_mode: "unused" },
  klein_9b_kv_image_edit: { scheduler_control_mode: "flux2", negative_prompt_mode: "zeroed" },
  z_image_turbo: { negative_prompt_mode: "zeroed" },
});

export const POLICY_CONTRACT_VERSION = "model-family-20260713-effective-parameters";

export function resolveEffectiveParameterPolicy(profileId) {
  return {
    scheduler_control_mode: "generic",
    negative_prompt_mode: "encoded",
    ...(EFFECTIVE_PARAMETER_POLICY_BY_PROFILE[profileId] ?? {}),
  };
}
