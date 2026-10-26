from __future__ import annotations

import json

from rookieui.contracts.moss_image import MOSS_IMAGE_PROFILE_IDS, MOSS_PNG_REQUEST_FIELDS, project_moss_png_request
from rookieui.contracts.pnginfo import PNGInfoParseResult
from rookieui.services.txt2img import normalize_txt2img_request

_MAX_METADATA_BYTES = 1024 * 1024


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate RookieUI PNG metadata field.')
        result[key] = value
    return result


def _reject_nonfinite(_value: str) -> object:
    raise ValueError('Non-finite RookieUI PNG metadata number.')


def parse_moss_pnginfo(metadata_items: dict[str, str], asset_handle: str) -> PNGInfoParseResult | None:
    raw = metadata_items.get('rookieui')
    if not raw:
        return None
    # IMPORTANT: infotext's character limit cannot bound JSON; escaped Unicode
    # expands sixfold. Keep the PNG chunk ceiling and revalidate request bounds.
    if len(raw) > _MAX_METADATA_BYTES or len(raw.encode('utf-8')) > _MAX_METADATA_BYTES:
        raise ValueError('RookieUI PNG metadata exceeds the text limit.')
    try:
        metadata = json.loads(raw, object_pairs_hook=_unique_fields, parse_constant=_reject_nonfinite)
    except (ValueError, RecursionError) as exc:
        raise ValueError('Invalid RookieUI PNG metadata JSON.') from exc
    if not isinstance(metadata, dict):
        raise ValueError('RookieUI PNG metadata must be an object.')
    request = metadata.get('request')
    request_profile = request.get('profile') if isinstance(request, dict) else None
    profile = metadata.get('profile')
    moss_profile = isinstance(profile, str) and profile in MOSS_IMAGE_PROFILE_IDS
    moss_request = isinstance(request_profile, str) and request_profile in MOSS_IMAGE_PROFILE_IDS
    if not (moss_profile or moss_request or isinstance(request, dict) and 'moss_options' in request):
        return None
    # CRITICAL: MOSS selectors/SLG cannot pass through SD infotext inference or
    # checkpoint fallback. Invalid MOSS metadata must fail before those heuristics.
    if (not moss_profile or metadata.get('schema') != 'rookieui.generation_metadata.v1'
            or metadata.get('surface') != 'txt2img'
            or metadata.get('profile') != request_profile
            or not isinstance(request, dict)
            or set(request) != set(MOSS_PNG_REQUEST_FIELDS)):
        raise ValueError('Invalid MOSS PNG request schema, profile or fields.')
    normalized = normalize_txt2img_request(request)
    return PNGInfoParseResult(
        source='image.rookieui', source_type='rookieui', target_form='txt2img',
        payload=project_moss_png_request(normalized.to_payload()), raw_parameters={},
        metadata_items={'rookieui': raw}, apply_targets=['txt2img'], asset_handle=asset_handle,
        warnings=['MOSS Image supports txt2img restoration only; img2img transfer is unavailable.'],
    )
