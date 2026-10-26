from __future__ import annotations

import json
import math

from rookieui.contracts.moss_layout import MossLayout


def compile_moss_layout(prompt: str, layout: MossLayout | None, width: int, height: int) -> str:
    if layout is None or not layout.enabled or not layout.elements:
        return prompt
    items: list[dict[str, object]] = []
    for element in layout.elements:
        item: dict[str, object] = {'label': element.kind, 'caption': element.caption}
        if element.kind == 'text':
            item['text'] = element.text or ''
        if element.palette:
            item['palette'] = list(element.palette)
        # CRITICAL: native boxes enclose pixel edges in yxyx order around the
        # canvas center. Truncation, swapped axes or a stale size moves the layout.
        item['bbox'] = [(math.floor if index < 2 else math.ceil)(round(edge * dimension / 1000, 9)) - dimension // 2
                        for index, (edge, dimension) in enumerate(zip(element.bbox, (height, width, height, width)))]
        items.append(item)
    return json.dumps({'summary': {'caption': prompt.strip()}, 'items': items,
                       'bbox_coord_space': 'abs_centralized', 'bbox_format': 'yxyx'},
                      ensure_ascii=False, separators=(',', ':'))
