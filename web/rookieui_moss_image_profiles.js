// Static offline projection of the canonical Python manifest and MOSS asset-role contract.
export const MOSS_IMAGE_FALLBACK_ENTRIES = Object.freeze([
  {
    "id": "moss_image_base",
    "title": "MOSS-Image Base",
    "translation_base_family": "sdxl",
    "public_base_family": "moss_image",
    "prompt_encoder": "clip_text_encode_sdxl",
    "default_width": 1024,
    "default_height": 1024,
    "default_steps": 25,
    "default_cfg_scale": 2.5,
    "default_sampler": "er_sde",
    "default_scheduler": "simple",
    "default_clip_skip": 1,
    "supports_clip_skip": false,
    "primary_model_category": "diffusion_models",
    "text_encoder_visible": true,
    "shift_visible": false,
    "default_shift": null,
    "flux_guidance_visible": false,
    "default_flux_guidance": null,
    "prompt_enhancement_visible": false,
    "default_prompt_enhancement_enabled": false,
    "edit_megapixels_visible": false,
    "default_edit_megapixels": null,
    "template_lora_visible": false,
    "template_lora_override_allowed": false,
    "official_template_lora_label": "",
    "default_template_lora_enabled": false,
    "default_template_lora_strength": 1.0,
    "default_template_lora_trigger_word": "",
    "template_lora_trigger_visible": false,
    "support_tier": "family-adapted",
    "compatibility_summary": "Native MOSS-Image text-to-image; real inference requires host qualification.",
    "experimental": true,
    "aliases": [],
    "notes": [
      "Requires matching Base/SFT diffusion, Qwen3.5 9B generation encoder and FLUX.2 VAE.",
      "Prompt enhancement is off; authored text is sent directly to the native encoder.",
      "Apache-2.0: https://github.com/OpenMOSS/MOSS-Image/blob/main/LICENSE",
      "Img2Img, Hires, ControlNet, ADetailer and LoRA controls are unavailable in this profile."
    ],
    "image_edit_profile": false,
    "request_contract_surface": "",
    "reference_input_mode": "none",
    "max_direct_references": 0,
    "encoder_family": "",
    "template_lora_chain_mode": "none",
    "available_surface_flows": [
      "txt2img"
    ],
    "ideogram_modes": [],
    "default_ideogram_mode": "",
    "scheduler_control_mode": "generic",
    "negative_prompt_mode": "encoded",
    "default_moss_slg_enabled": true
  },
  {
    "id": "moss_image_sft",
    "title": "MOSS-Image SFT",
    "translation_base_family": "sdxl",
    "public_base_family": "moss_image",
    "prompt_encoder": "clip_text_encode_sdxl",
    "default_width": 1024,
    "default_height": 1024,
    "default_steps": 25,
    "default_cfg_scale": 2.5,
    "default_sampler": "er_sde",
    "default_scheduler": "simple",
    "default_clip_skip": 1,
    "supports_clip_skip": false,
    "primary_model_category": "diffusion_models",
    "text_encoder_visible": true,
    "shift_visible": false,
    "default_shift": null,
    "flux_guidance_visible": false,
    "default_flux_guidance": null,
    "prompt_enhancement_visible": false,
    "default_prompt_enhancement_enabled": false,
    "edit_megapixels_visible": false,
    "default_edit_megapixels": null,
    "template_lora_visible": false,
    "template_lora_override_allowed": false,
    "official_template_lora_label": "",
    "default_template_lora_enabled": false,
    "default_template_lora_strength": 1.0,
    "default_template_lora_trigger_word": "",
    "template_lora_trigger_visible": false,
    "support_tier": "family-adapted",
    "compatibility_summary": "Native MOSS-Image text-to-image; real inference requires host qualification.",
    "experimental": true,
    "aliases": [],
    "notes": [
      "Requires matching Base/SFT diffusion, Qwen3.5 9B generation encoder and FLUX.2 VAE.",
      "Prompt enhancement is off; authored text is sent directly to the native encoder.",
      "Apache-2.0: https://github.com/OpenMOSS/MOSS-Image/blob/main/LICENSE",
      "Img2Img, Hires, ControlNet, ADetailer and LoRA controls are unavailable in this profile."
    ],
    "image_edit_profile": false,
    "request_contract_surface": "",
    "reference_input_mode": "none",
    "max_direct_references": 0,
    "encoder_family": "",
    "template_lora_chain_mode": "none",
    "available_surface_flows": [
      "txt2img"
    ],
    "ideogram_modes": [],
    "default_ideogram_mode": "",
    "scheduler_control_mode": "generic",
    "negative_prompt_mode": "encoded",
    "default_moss_slg_enabled": false
  }
]);
export const MOSS_IMAGE_ASSET_ROLES = Object.freeze({
  "moss_image_base": {
    "diffusion_models": [
      "moss_image_base_bf16.safetensors",
      "moss_image_base_int8_convrot.safetensors"
    ],
    "text_encoders": [
      "qwen3.5_9b_bf16.safetensors",
      "qwen3.5_9b_int8_convrot.safetensors",
      "qwen3.5_9b_w4a8_gptq.safetensors"
    ],
    "vae": [
      "flux2-vae.safetensors",
      "flux2-vae_small.safetensors"
    ]
  },
  "moss_image_sft": {
    "diffusion_models": [
      "moss_image_sft_bf16.safetensors",
      "moss_image_sft_int8_convrot.safetensors"
    ],
    "text_encoders": [
      "qwen3.5_9b_bf16.safetensors",
      "qwen3.5_9b_int8_convrot.safetensors",
      "qwen3.5_9b_w4a8_gptq.safetensors"
    ],
    "vae": [
      "flux2-vae.safetensors",
      "flux2-vae_small.safetensors"
    ]
  }
});
export const isMossImageProfile = (id) => Object.hasOwn(MOSS_IMAGE_ASSET_ROLES, id);
