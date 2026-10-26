from __future__ import annotations

import sys
from collections.abc import Mapping


def moss_host_unavailable_reasons(*, slg_enabled: bool, sampler: str = 'er_sde', scheduler: str = 'simple') -> tuple[str, ...]:
    # CRITICAL: inspect only the loaded host. Importing nodes here pulls GPU and
    # optional dependencies into standalone/CI contract validation.
    host = sys.modules.get('nodes')
    if host is None:
        return ('MOSS host node inventory is not loaded.',)
    mappings = getattr(host, 'NODE_CLASS_MAPPINGS', None)
    expected = {
        'UNETLoader': {'unet_name', 'weight_dtype'}, 'CLIPLoader': {'clip_name', 'type'},
        'VAELoader': {'vae_name'}, 'CLIPTextEncode': {'clip', 'text'},
        'EmptyFlux2LatentImage': {'width', 'height', 'batch_size'},
        'KSampler': {'model', 'positive', 'negative', 'latent_image', 'seed', 'steps', 'cfg',
                     'sampler_name', 'scheduler', 'denoise'},
        'VAEDecode': {'samples', 'vae'},
    }
    if slg_enabled:
        expected['SkipLayerGuidanceDiTSimple'] = {'model', 'double_layers', 'single_layers', 'start_percent', 'end_percent'}
    reasons = []
    for node_id, names in expected.items():
        node = mappings.get(node_id) if isinstance(mappings, Mapping) else None
        try:
            schema = node.INPUT_TYPES()
            available = {key: value for group in ('required', 'optional')
                         for key, value in schema.get(group, {}).items()}
        except Exception:
            reasons.append(f'MOSS requires compatible host node {node_id}.')
            continue
        if not names <= available.keys():
            reasons.append(f'MOSS requires compatible inputs on host node {node_id}.')
            continue
        checks = {'type': 'moss_image'} if node_id == 'CLIPLoader' else (
            {'sampler_name': sampler, 'scheduler': scheduler} if node_id == 'KSampler' else {})
        for field, value in checks.items():
            descriptor = available[field]
            choices = descriptor[0] if isinstance(descriptor, (list, tuple)) and descriptor else None
            if not isinstance(choices, (list, tuple)) or value not in choices:
                reasons.append(f'MOSS requires {node_id}.{field} choice {value}.')
    return tuple(reasons)


def validate_moss_host(*, slg_enabled: bool, sampler: str, scheduler: str) -> None:
    if sys.modules.get('nodes') is None:
        return  # Offline graph translation; never interpreted as live capability.
    reasons = moss_host_unavailable_reasons(slg_enabled=slg_enabled, sampler=sampler, scheduler=scheduler)
    if reasons:
        raise ValueError(' '.join(reasons))


def build_moss_capability_payload() -> dict[str, object]:
    from rookieui.contracts.family_template_manifest import get_family_template_manifest_entry
    from rookieui.contracts.moss_image import MOSS_IMAGE_PROFILE_IDS, matches_moss_asset
    from rookieui.services.model_inventory import discover_model_inventory

    inventory = discover_model_inventory()
    basic_reasons = moss_host_unavailable_reasons(slg_enabled=False)
    all_reasons = moss_host_unavailable_reasons(slg_enabled=True)
    slg_reasons = tuple(reason for reason in all_reasons if reason not in basic_reasons)
    profiles = {}
    for profile in sorted(MOSS_IMAGE_PROFILE_IDS):
        model_reasons = [f'MOSS requires an installed matching {role} selector.'
                         for role in ('diffusion_models', 'text_encoders', 'vae')
                         if not any(matches_moss_asset(profile, value, role) for value in getattr(inventory, role))]
        without_slg = [*basic_reasons, *model_reasons]
        default_slg = get_family_template_manifest_entry(profile).default_moss_slg_enabled
        reasons = [*without_slg, *(slg_reasons if default_slg else ())]
        profiles[profile] = {'available': not reasons, 'reasons': reasons,
                             'without_slg_available': not without_slg, 'without_slg_reasons': without_slg,
                             'slg_available': not (all_reasons or model_reasons),
                             'slg_reasons': [*all_reasons, *model_reasons]}
    return {'profiles': profiles, 'prompt_enhancement_available': False, 'supported_flows': ['txt2img']}
