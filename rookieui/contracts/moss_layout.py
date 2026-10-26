from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from typing import Literal, cast

MAX_LAYOUT_ELEMENTS = 32
MAX_LAYOUT_BYTES = 128 * 1024
LayoutKind = Literal['object', 'text', 'character']
Coordinate = int | float


@dataclass(frozen=True)
class MossLayoutElement:
    kind: LayoutKind
    caption: str
    bbox: tuple[Coordinate, Coordinate, Coordinate, Coordinate]
    text: str | None = None
    palette: tuple[str, ...] | None = None

    def to_payload(self) -> dict[str, object]:
        result: dict[str, object] = {'kind': self.kind, 'caption': self.caption, 'bbox': list(self.bbox)}
        if self.kind == 'text' and self.text is not None:
            result['text'] = self.text
        if self.palette is not None:
            result['palette'] = list(self.palette)
        return result


@dataclass(frozen=True)
class MossLayout:
    enabled: bool
    elements: tuple[MossLayoutElement, ...]

    def to_payload(self) -> dict[str, object]:
        return {'enabled': self.enabled, 'elements': [element.to_payload() for element in self.elements]}


def _text(value: object, name: str, limit: int) -> str:
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(f'MOSS layout {name} must be a string of at most {limit} characters.')
    try:
        value.encode('utf-8')
    except UnicodeEncodeError as exc:
        raise ValueError(f'MOSS layout {name} must contain valid Unicode.') from exc
    return value


def normalize_moss_layout(value: object) -> MossLayout | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {'enabled', 'elements'} or type(value['enabled']) is not bool:
        raise ValueError('MOSS layout requires only a boolean enabled and an elements list.')
    elements = value['elements']
    if not isinstance(elements, list) or len(elements) > MAX_LAYOUT_ELEMENTS:
        raise ValueError('MOSS layout supports at most 32 elements.')
    normalized = []
    for index, element in enumerate(elements, 1):
        if (not isinstance(element, dict) or not {'kind', 'caption', 'bbox'} <= element.keys()
                or set(element) - {'kind', 'caption', 'bbox', 'text', 'palette'}):
            raise ValueError(f'MOSS layout element {index} has invalid fields.')
        kind = element['kind']
        if not isinstance(kind, str) or kind not in ('object', 'text', 'character'):
            raise ValueError(f'MOSS layout element {index} requires object, text or character kind.')
        if kind != 'text' and 'text' in element:
            raise ValueError(f'MOSS layout element {index} permits rendered text only for text kind.')
        caption = _text(element['caption'], f'element {index} caption', 2048)
        text = _text(element['text'], f'element {index} text', 1024) if 'text' in element else None
        bbox = element['bbox']
        if (not isinstance(bbox, list) or len(bbox) != 4
                or any(type(v) not in (int, float) or not 0 <= v <= 1000 or not math.isfinite(v) for v in bbox)
                or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]):
            raise ValueError(f'MOSS layout element {index} bbox requires finite 0..1000 y0,x0,y1,x1 edges with positive area.')
        palette = element.get('palette')
        if ('palette' in element and (not isinstance(palette, list) or len(palette) > 8
                or any(not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color) for color in palette))):
            raise ValueError(f'MOSS layout element {index} palette requires at most eight #RRGGBB colors.')
        normalized.append(MossLayoutElement(cast(LayoutKind, kind), caption,
            (bbox[0], bbox[1], bbox[2], bbox[3]), text, tuple(palette) if palette is not None else None))
    result = MossLayout(value['enabled'], tuple(normalized))
    # IMPORTANT: disabled drafts still cross request/PNG/storage boundaries.
    # Validate their bounds too; disabling compilation must not bypass admission.
    if len(json.dumps(result.to_payload(), ensure_ascii=False, separators=(',', ':')).encode('utf-8')) > MAX_LAYOUT_BYTES:
        raise ValueError('MOSS layout must not exceed 128 KiB of UTF-8 JSON.')
    return result
