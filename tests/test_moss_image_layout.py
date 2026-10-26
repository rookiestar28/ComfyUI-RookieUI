from __future__ import annotations

import copy
import dataclasses
import json
import unittest

from rookieui.contracts.moss_layout import normalize_moss_layout
from rookieui.services.moss_layout import compile_moss_layout
from rookieui.services.workflow_translation import translate_txt2img_request
from tests import test_moss_image as moss_tests

normalize = moss_tests.normalize


def layout(*elements, enabled=True):
    return {'enabled': enabled, 'elements': list(elements)}


def element(kind='object', **overrides):
    return {'kind': kind, 'caption': '角色中文\ncaption', 'bbox': [0, 0, 500, 1000], **overrides}


class MossLayoutTests(unittest.TestCase):
    def test_native_rectangular_centered_edges_unicode_and_order(self):
        source = layout(element(bbox=[0, 0, 500, 333.33333333333]),
            element('character', bbox=[250, 500, 1000, 1000]),
            element('text', text='字面\n<script>text</script>', palette=['#Ab12Cd', '#ffffff'],
                    bbox=[200.1, 100.1, 799.9, 899.9]))
        actual = compile_moss_layout('  authored summary\n中文  ', normalize_moss_layout(source), 768, 512)
        expected = {'summary': {'caption': 'authored summary\n中文'}, 'items': [
            {'label': 'object', 'caption': '角色中文\ncaption', 'bbox': [-256, -384, 0, -128]},
            {'label': 'character', 'caption': '角色中文\ncaption', 'bbox': [-128, 0, 256, 384]},
            {'label': 'text', 'caption': '角色中文\ncaption', 'text': '字面\n<script>text</script>',
             'palette': ['#Ab12Cd', '#ffffff'], 'bbox': [-154, -308, 154, 308]},
        ], 'bbox_coord_space': 'abs_centralized', 'bbox_format': 'yxyx'}
        self.assertEqual(actual, json.dumps(expected, ensure_ascii=False, separators=(',', ':')))
        self.assertIn('中文', actual)
        resized = json.loads(compile_moss_layout('summary', normalize_moss_layout(source), 1024, 768))
        self.assertEqual(resized['items'][1]['bbox'], [-192, 0, 384, 512])

    def test_empty_disabled_and_absent_preserve_original_positive(self):
        for source in (None, layout(), layout(element(), enabled=False)):
            with self.subTest(source=source):
                self.assertEqual(compile_moss_layout('  original\n中文  ', normalize_moss_layout(source), 768, 512),
                                 '  original\n中文  ')

    def test_immutable_validated_snapshot_does_not_alias_author_input(self):
        source = layout(element('text', text='unchanged', palette=['#abcdef']))
        value = normalize_moss_layout(source)
        source['elements'][0]['bbox'][0] = 200
        source['elements'][0]['palette'].append('#ffffff')
        self.assertEqual(value.elements[0].bbox[0], 0)
        self.assertEqual(value.elements[0].palette, ('#abcdef',))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            value.enabled = False

    def test_optional_empty_field_presence_roundtrips_without_changing_byte_admission(self):
        for row in (element(), element(palette=[]), element('text'), element('text', text='', palette=[])):
            source = layout(row)
            with self.subTest(row=row):
                self.assertEqual(normalize_moss_layout(source).to_payload(), source)

    def test_strict_schema_numeric_types_and_coordinates(self):
        with self.assertRaisesRegex(ValueError, 'object'):
            normalize(moss_options={'layout': None})
        with self.assertRaisesRegex(ValueError, 'MOSS Image profile'):
            normalize('sd15', moss_options={'layout': layout()})
        invalid = [[], {}, {'enabled': True}, layout(enabled='false'),
            {**layout(), 'extra': 1}, layout({'kind': 'object'}), layout(element('unknown')),
            layout(element(extra='ignored')), layout(element(text='not a text element')),
            layout(element(caption=1)), layout(element('text', text=False)),
            layout(element(bbox=[False, 0, 1, 1])), layout(element(bbox=['0', 0, 1, 1])),
            layout(element(bbox=[float('nan'), 0, 1, 1])), layout(element(bbox=[0, 0, float('inf'), 1])),
            layout(element(bbox=[-1, 0, 1, 1])), layout(element(bbox=[0, 0, 1001, 1])),
            layout(element(bbox=[500, 0, 500, 1000])), layout(element(bbox=[0, 900, 500, 100])),
            layout(element(bbox=[0, 0, 1])), layout(element(palette=['red'])),
            layout(element(palette=['#ffffff'] * 9)), layout(element(palette='[]')),
            layout(element(caption='x' * 2049)), layout(element('text', text='x' * 1025))]
        for source in invalid:
            with self.subTest(source=source), self.assertRaises(ValueError):
                normalize_moss_layout(source)

    def test_element_count_and_utf8_byte_limits_including_disabled_drafts(self):
        self.assertEqual(len(normalize_moss_layout(layout(*[element()] * 32)).elements), 32)
        for source in (layout(*[element()] * 33),
                       layout(*[element(caption='字' * 2048)] * 32),
                       layout(element(bbox=[0, 0, 0, 0]), enabled=False)):
            with self.subTest(source=source), self.assertRaises(ValueError):
                normalize_moss_layout(source)
        self.assertEqual(normalize_moss_layout(layout(element(caption='😀' * 2048))).elements[0].caption,
                         '😀' * 2048)

    def test_mode_defaults_and_explicit_slg_overrides_are_effective(self):
        for profile in ('moss_image_base', 'moss_image_sft'):
            for explicit in (None, False, True):
                options = {'layout': layout(element())}
                if explicit is not None:
                    options['slg_enabled'] = explicit
                request = normalize(profile, moss_options=options, width=768, height=512)
                self.assertEqual(request.moss_options.slg_enabled, True if explicit is None else explicit)
                workflow = translate_txt2img_request(request).workflow
                self.assertEqual(any(n['class_type'] == 'SkipLayerGuidanceDiTSimple' for n in workflow.values()),
                                 request.moss_options.slg_enabled)
        self.assertFalse(normalize('moss_image_sft', moss_options={'layout': layout(enabled=False)}).moss_options.slg_enabled)

    def test_graph_conditioning_is_string_same_dimensions_and_no_output_side_effects(self):
        source = layout(element('text', text='rendered 中文'))
        request = normalize(moss_options={'layout': source}, width=768, height=512, negative_prompt='native negative')
        workflow = translate_txt2img_request(request).workflow
        encodes = [n['inputs']['text'] for n in workflow.values() if n['class_type'] == 'CLIPTextEncode']
        self.assertEqual(json.loads(encodes[0])['items'][0]['bbox'], [-256, -384, 0, 384])
        self.assertEqual(encodes[1], 'native negative')
        latent = next(n['inputs'] for n in workflow.values() if n['class_type'] == 'EmptyFlux2LatentImage')
        self.assertEqual((latent['width'], latent['height']), (768, 512))
        self.assertFalse(any(n['class_type'] in {'CreateBoundingBoxes', 'MOSSImageLayoutPrompt', 'TextGenerate'}
                             for n in workflow.values()))
        for node in workflow.values():
            for value in node['inputs'].values():
                if isinstance(value, list):
                    self.assertEqual(len(value), 2)
                    self.assertIn(value[0], workflow)
                    self.assertIs(type(value[1]), int)

    def test_original_request_and_real_png_roundtrip_preserve_disabled_layout_and_effective_seed(self):
        source = layout(element('text', text='字\nraw', palette=['#abcdef']), enabled=False)
        original = copy.deepcopy(source)
        request = normalize(moss_options={'layout': source, 'slg_enabled': False}, seed=-1)
        payload = request.to_payload()
        self.assertEqual(payload['moss_options']['layout'], original)
        metadata = translate_txt2img_request(request).generation_metadata
        restored = moss_tests.MossPNGRoundtripTests().parse({'parameters': metadata['parameters'], **metadata['extra_pnginfo']})
        self.assertEqual(restored.payload['moss_options'], payload['moss_options'])
        self.assertEqual(restored.payload['seed'], request.execution_seed)
        self.assertEqual(source, original)
        self.assertNotIn('layout', normalize().to_payload()['moss_options'])


if __name__ == '__main__':
    unittest.main()
