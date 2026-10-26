from __future__ import annotations

import ntpath
from dataclasses import dataclass
from typing import Any, Mapping

from rookieui.contracts.moss_layout import MossLayout, normalize_moss_layout

MOSS_PNG_REQUEST_FIELDS = (
    'profile', 'prompt', 'negative_prompt', 'checkpoint_name', 'text_encoder_name', 'vae_name',
    'width', 'height', 'steps', 'cfg_scale', 'sampler_name', 'scheduler_name', 'seed', 'seed_extra',
    'batch_size', 'batch_count', 'moss_options',
)


def project_moss_png_request(request: Mapping[str, Any]) -> dict[str, Any]:
    result = {key: request[key] for key in MOSS_PNG_REQUEST_FIELDS}
    result['seed'] = request.get('execution_seed', request['seed'])
    return result

MOSS_IMAGE_PROFILE_IDS = frozenset({'moss_image_base', 'moss_image_sft'})
MOSS_DIFFUSION_BASENAMES = {
    profile: frozenset(f'{profile}_{variant}.safetensors' for variant in ('bf16', 'int8_convrot'))
    for profile in MOSS_IMAGE_PROFILE_IDS
}
MOSS_ENCODER_BASENAMES = frozenset({
    'qwen3.5_9b_bf16.safetensors', 'qwen3.5_9b_int8_convrot.safetensors',
    'qwen3.5_9b_w4a8_gptq.safetensors',
})
MOSS_VAE_BASENAMES = frozenset({'flux2-vae_small.safetensors', 'flux2-vae.safetensors'})


def moss_image_asset_role(selector: str) -> str:
    basename = ntpath.basename(str(selector or '').replace('/', '\\')).lower()
    if any(basename in names for names in MOSS_DIFFUSION_BASENAMES.values()):
        return 'diffusion_models'
    if basename in MOSS_ENCODER_BASENAMES:
        return 'text_encoders'
    if basename in MOSS_VAE_BASENAMES:
        return 'vae'
    return ''


def matches_moss_asset(profile_id: str, selector: str, role: str) -> bool:
    basename = ntpath.basename(str(selector or '').replace('/', '\\')).lower()
    if role == 'diffusion_models':
        return basename in MOSS_DIFFUSION_BASENAMES.get(profile_id, ())
    return role in {'text_encoders', 'vae'} and moss_image_asset_role(selector) == role


def is_moss_exclusive_asset(selector: str) -> bool:
    # CRITICAL: only MOSS diffusion/encoder roles are exclusive. FLUX.2 VAEs
    # remain compatible with older FLUX.2 consumers and must not be quarantined.
    return moss_image_asset_role(selector) in {'diffusion_models', 'text_encoders'}


@dataclass(frozen=True)
class MossImageOptions:
    slg_enabled: bool
    layout: MossLayout | None = None

    def to_payload(self) -> dict[str, object]:
        result: dict[str, object] = {'slg_enabled': self.slg_enabled}
        if self.layout is not None:
            result['layout'] = self.layout.to_payload()
        return result


def normalize_moss_options(value: object, *, default_slg: bool | None) -> MossImageOptions | None:
    if default_slg is None:
        if value is not None:
            raise ValueError('moss_options requires a MOSS Image profile.')
        return None
    if value is None:
        return MossImageOptions(slg_enabled=default_slg)
    if not isinstance(value, dict) or set(value) - {'slg_enabled', 'layout'}:
        raise ValueError('moss_options must be an object containing only slg_enabled and layout.')
    if 'layout' in value and value['layout'] is None:
        raise ValueError('moss_options.layout must be an object when present.')
    layout = normalize_moss_layout(value.get('layout'))
    enabled = value.get('slg_enabled', True if layout is not None and layout.enabled else default_slg)
    if type(enabled) is not bool:
        raise ValueError('moss_options.slg_enabled must be a boolean.')
    return MossImageOptions(slg_enabled=enabled, layout=layout)
