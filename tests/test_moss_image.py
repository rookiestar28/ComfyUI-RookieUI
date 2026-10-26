from __future__ import annotations

import unittest
import types
import base64
import io
import json
from pathlib import Path
from unittest import mock

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from rookieui.contracts.models import ModelInventorySnapshot
from rookieui.services.model_inventory import resolve_text_encoder_selector_context
from rookieui.services.parity_matrix import get_parity_profile
from rookieui.services.txt2img import normalize_txt2img_request
from rookieui.services.workflow_translation import translate_txt2img_request
from rookieui.services.capabilities import build_capabilities_payload
from rookieui.services.moss_image import moss_host_unavailable_reasons
from rookieui.services.pnginfo import parse_pnginfo_payload
from rookieui.contracts import core_graph_contract
from rookieui.contracts.family_template_manifest import build_model_family_registry_payload
from rookieui.contracts.moss_image import MOSS_DIFFUSION_BASENAMES, MOSS_ENCODER_BASENAMES, MOSS_VAE_BASENAMES


def inventory(profile='moss_image_base'):
    return ModelInventorySnapshot(source='host', diffusion_models=[f'moss/{profile}_int8_convrot.safetensors'],
                                  text_encoders=['moss/qwen3.5_9b_int8_convrot.safetensors'],
                                  vae=['shared/flux2-vae_small.safetensors'])


def normalize(profile='moss_image_base', **overrides):
    with mock.patch('rookieui.services.txt2img.discover_model_inventory', return_value=inventory(profile)):
        return normalize_txt2img_request({'profile': profile, 'prompt': '(literal:1.2) 中文', **overrides})


class MossNativeGraphTests(unittest.TestCase):
    def test_offline_projection_and_roles_match_the_canonical_python_owner(self):
        source = (Path(__file__).parents[1] / 'web/rookieui_moss_image_profiles.js').read_text(encoding='utf-8')
        entries = json.loads(source.split('MOSS_IMAGE_FALLBACK_ENTRIES = Object.freeze(', 1)[1].split(');', 1)[0])
        expected = [entry for entry in build_model_family_registry_payload()['entries'] if entry['id'] in MOSS_DIFFUSION_BASENAMES]
        self.assertEqual(entries, expected)
        roles = json.loads(source.split('MOSS_IMAGE_ASSET_ROLES = Object.freeze(', 1)[1].split(');', 1)[0])
        self.assertEqual(roles, {profile: {'diffusion_models': sorted(names), 'text_encoders': sorted(MOSS_ENCODER_BASENAMES),
            'vae': sorted(MOSS_VAE_BASENAMES)} for profile, names in MOSS_DIFFUSION_BASENAMES.items()})

    def test_every_admitted_asset_variant_and_separator_stays_registered(self):
        for profile, models in MOSS_DIFFUSION_BASENAMES.items():
            for model in models:
                for encoder in MOSS_ENCODER_BASENAMES:
                    for vae in MOSS_VAE_BASENAMES:
                        assets = ModelInventorySnapshot(source='host', diffusion_models=['moss/'+model],
                            text_encoders=['moss\\'+encoder], vae=['shared/'+vae])
                        with self.subTest(profile=profile, model=model, encoder=encoder, vae=vae), mock.patch(
                            'rookieui.services.txt2img.discover_model_inventory', return_value=assets):
                            request = normalize_txt2img_request({'profile': profile, 'prompt': 'synthetic'})
                            self.assertEqual((request.checkpoint_name, request.text_encoder_name, request.vae_name),
                                (assets.diffusion_models[0], assets.text_encoders[0], assets.vae[0]))

    def test_scoped_graph_envelope_matches_independent_native_edges(self):
        fixture = Path(__file__).parent / 'fixtures/moss_image_candidate_graph_contract.json'
        contract = core_graph_contract.load_profile_graph_contract(fixture)
        self.assertEqual(contract.source_revision, '19ae172bff6c9e4c738e7f2e00fe087f5b5b46ab')
        self.assertEqual(tuple(row.id for row in contract.profiles), ('moss_image_base', 'moss_image_sft'))
        for row in contract.profiles:
            workflow = translate_txt2img_request(normalize(row.id)).workflow
            self.assertEqual(core_graph_contract.build_profile_graph_row(row.id, 'txt2img', workflow), row)
    def test_distinct_profiles_and_defaults_match_native_basic_modes(self):
        for profile, slg in [('moss_image_base', True), ('moss_image_sft', False)]:
            with self.subTest(profile=profile):
                request = normalize(profile, negative_prompt='unwanted', seed=42, width=1024, height=768)
                self.assertEqual(get_parity_profile(profile).id, profile)
                self.assertEqual((request.steps, request.cfg_scale, request.sampler_name, request.scheduler_name),
                                 (25, 2.5, 'er_sde', 'simple'))
                self.assertEqual(request.to_payload()['moss_options'], {'slg_enabled': slg})
                self.assertEqual(request.prompt, '(literal:1.2) 中文')
                translation = translate_txt2img_request(request)
                graph = translation.workflow
                by_class = {node['class_type']: (key, node['inputs']) for key, node in graph.items()}
                self.assertEqual(by_class['CLIPLoader'][1]['type'], 'moss_image')
                self.assertEqual(by_class['EmptyFlux2LatentImage'][1], {'width': 1024, 'height': 768, 'batch_size': 1})
                encodes = [(key, node['inputs']) for key, node in graph.items() if node['class_type'] == 'CLIPTextEncode']
                self.assertEqual([node['text'] for _, node in encodes], ['(literal:1.2) 中文', 'unwanted'])
                self.assertEqual(by_class['KSampler'][1]['positive'], [encodes[0][0], 0])
                self.assertEqual(by_class['KSampler'][1]['negative'], [encodes[1][0], 0])
                self.assertEqual(by_class['KSampler'][1]['denoise'], 1.0)
                self.assertEqual('SkipLayerGuidanceDiTSimple' in by_class, slg)
                if slg:
                    self.assertEqual(by_class['SkipLayerGuidanceDiTSimple'][1], {
                        'model': [by_class['UNETLoader'][0], 0], 'double_layers': '', 'single_layers': '22',
                        'start_percent': 0.0, 'end_percent': 0.5})
                    self.assertEqual(by_class['KSampler'][1]['model'], [by_class['SkipLayerGuidanceDiTSimple'][0], 0])
                self.assertFalse({'TextGenerate', 'ModelSamplingAuraFlow', 'ModelSamplingFlux', 'RookieUIA1111Encode'} & by_class.keys())

    def test_explicit_slg_override_is_effective_in_both_variants(self):
        for profile, enabled in [('moss_image_base', False), ('moss_image_sft', True)]:
            graph = translate_txt2img_request(normalize(profile, moss_options={'slg_enabled': enabled})).workflow
            self.assertEqual(any(node['class_type'] == 'SkipLayerGuidanceDiTSimple' for node in graph.values()), enabled)

    def test_invalid_options_bounds_and_unsupported_operations_fail(self):
        cases = [{'moss_options': value} for value in ('{}', [], 1, {'slg_enabled': 'false'},
                 {'slg_enabled': 1}, {'unknown': True}, {'layout': {}})]
        cases += [{'width': 72}, {'height': 2056}, {'batch_size': 9}, {'shift': 3.0},
                  {'clip_skip': 2},
                  {'seed': -2}, {'seed': 2**63}, {'steps': 0}, {'cfg_scale': 31},
                  {'hires_enabled': True}, {'lora_name': 'synthetic.safetensors'},
                  {'prompt_enhancement_enabled': True}]
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises((ValueError, TypeError)):
                normalize(**payload)

    def test_matching_names_still_require_registered_host_inventory_and_variant(self):
        for overrides in ({'checkpoint_name': 'moss_image_sft_bf16.safetensors'},
                          {'text_encoder_name': 'qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors'},
                          {'vae_name': 'ae.safetensors'}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                normalize(**overrides)
        with mock.patch('rookieui.services.txt2img.discover_model_inventory', return_value=ModelInventorySnapshot(source='host')):
            with self.assertRaises(ValueError):
                normalize_txt2img_request({'profile':'moss_image_base', 'prompt':'synthetic',
                    'checkpoint_name':'moss_image_base_bf16.safetensors',
                    'text_encoder_name':'qwen3.5_9b_bf16.safetensors', 'vae_name':'flux2-vae.safetensors'})

    def test_loaded_incompatible_host_fails_before_enqueue(self):
        request = normalize()
        with mock.patch.dict('sys.modules', {'nodes': types.SimpleNamespace(NODE_CLASS_MAPPINGS={})}):
            with self.assertRaisesRegex(ValueError, 'MOSS'):
                translate_txt2img_request(request)


class MossCapabilityTests(unittest.TestCase):
    def _nodes(self):
        inputs = {
            'UNETLoader': ['unet_name', 'weight_dtype'], 'CLIPLoader': ['clip_name', 'type'],
            'VAELoader': ['vae_name'], 'CLIPTextEncode': ['clip', 'text'],
            'EmptyFlux2LatentImage': ['width', 'height', 'batch_size'],
            'KSampler': ['model', 'positive', 'negative', 'latent_image', 'seed', 'steps', 'cfg',
                         'sampler_name', 'scheduler', 'denoise'], 'VAEDecode': ['samples', 'vae'],
            'SkipLayerGuidanceDiTSimple': ['model', 'double_layers', 'single_layers', 'start_percent', 'end_percent'],
        }
        schemas = {node: {'required': {name: ('STRING',) for name in names}} for node, names in inputs.items()}
        schemas['CLIPLoader']['required']['type'] = (['moss_image'],)
        schemas['KSampler']['required'].update(sampler_name=(['er_sde', 'euler'],), scheduler=(['simple'],))
        mappings = {name: types.SimpleNamespace(INPUT_TYPES=lambda schema=schema: schema) for name, schema in schemas.items()}
        return schemas, types.SimpleNamespace(NODE_CLASS_MAPPINGS=mappings)

    def test_actual_enums_and_optional_slg_gate_the_graph(self):
        schemas, nodes = self._nodes()
        with mock.patch.dict('sys.modules', {'nodes': nodes}):
            self.assertEqual(moss_host_unavailable_reasons(slg_enabled=True), ())
            schemas['CLIPLoader']['required']['type'] = (['qwen_image'],)
            with self.assertRaisesRegex(ValueError, 'moss_image'):
                translate_txt2img_request(normalize())
            schemas['CLIPLoader']['required']['type'] = (['moss_image'],)
            schemas['KSampler']['required']['sampler_name'] = (['euler'],)
            with self.assertRaisesRegex(ValueError, 'er_sde'):
                translate_txt2img_request(normalize())
            schemas['KSampler']['required']['sampler_name'] = (['er_sde'],)
            del nodes.NODE_CLASS_MAPPINGS['SkipLayerGuidanceDiTSimple']
            translate_txt2img_request(normalize('moss_image_sft'))
            with self.assertRaisesRegex(ValueError, 'SkipLayerGuidance'):
                translate_txt2img_request(normalize())

    def test_capability_reports_actual_host_and_inventory_reasons(self):
        _, nodes = self._nodes()
        with mock.patch.dict('sys.modules', {'nodes': nodes}), mock.patch(
            'rookieui.services.model_inventory.discover_model_inventory', return_value=inventory()
        ):
            capability = build_capabilities_payload(routes=[])['moss_image']
        self.assertTrue(capability['profiles']['moss_image_base']['available'])
        self.assertFalse(capability['profiles']['moss_image_sft']['available'])
        self.assertTrue(capability['profiles']['moss_image_sft']['reasons'])


class MossEncoderIsolationTests(unittest.TestCase):
    def test_moss_encoders_never_become_older_family_defaults(self) -> None:
        for profile in ('qwen_image', 'qwen_image_edit', 'krea2_turbo', 'klein_4b', 'z_image'):
            for encoder in ('qwen3.5_9b_bf16.safetensors', 'qwen3.5_9b_int8_convrot.safetensors',
                            'qwen3.5_9b_w4a8_gptq.safetensors'):
                with self.subTest(profile=profile, encoder=encoder):
                    inventory = ModelInventorySnapshot(source='host', text_encoders=[encoder],
                                                       default_text_encoder=encoder)
                    self.assertEqual(resolve_text_encoder_selector_context(profile, inventory), '')

    def test_mixed_inventory_preserves_valid_older_encoders(self) -> None:
        pairs = {'qwen_image': 'qwen_2.5_vl_7b_fp8_scaled.safetensors',
                 'qwen_image_edit': 'qwen_2.5_vl_7b_fp8_scaled.safetensors',
                 'krea2_turbo': 'qwen_3_4b.safetensors',
                 'klein_4b': 'qwen_3_4b.safetensors', 'z_image': 'qwen_3_4b.safetensors'}
        for profile, valid in pairs.items():
            with self.subTest(profile=profile):
                inventory = ModelInventorySnapshot(source='host', text_encoders=[
                    'qwen3.5_9b_bf16.safetensors', valid])
                self.assertEqual(resolve_text_encoder_selector_context(profile, inventory), valid)

    def test_default_only_inventory_cannot_bypass_encoder_isolation(self) -> None:
        inventory = ModelInventorySnapshot(source='host', default_text_encoder='qwen3.5_9b_bf16.safetensors')
        self.assertEqual(resolve_text_encoder_selector_context('qwen_image', inventory), '')


class MossPNGRoundtripTests(unittest.TestCase):
    def parse(self, metadata):
        pnginfo = PngInfo()
        for key, value in metadata.items():
            pnginfo.add_text(key, value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
        image = io.BytesIO()
        Image.new('RGB', (16, 16)).save(image, format='PNG', pnginfo=pnginfo)
        data = 'data:image/png;base64,' + base64.b64encode(image.getvalue()).decode('ascii')
        with mock.patch('rookieui.services.txt2img.discover_model_inventory', return_value=inventory()):
            return parse_pnginfo_payload({'image_data': data})

    def metadata(self):
        request = normalize(seed=-1, moss_options={'slg_enabled': False}, negative_prompt='否定文字',
                            width=768, height=1024, steps=27, cfg_scale=3.0)
        metadata = translate_txt2img_request(request).generation_metadata
        return request, {'parameters': metadata['parameters'], **metadata['extra_pnginfo']}

    def test_png_restores_effective_request_without_sd_inference(self):
        request, metadata = self.metadata()
        result = self.parse(metadata)
        self.assertEqual(result.source_type, 'rookieui')
        self.assertEqual(result.apply_targets, ['txt2img'])
        restored = result.payload
        for key in ('profile', 'prompt', 'negative_prompt', 'checkpoint_name', 'text_encoder_name',
                    'vae_name', 'width', 'height', 'steps', 'cfg_scale', 'moss_options'):
            self.assertEqual(restored[key], request.to_payload()[key])
        self.assertEqual(restored['seed'], request.execution_seed)
        self.assertIn('img2img', ' '.join(result.warnings))
        self.assertNotIn('execution_seed', metadata['rookieui']['request'])

    def test_invalid_moss_envelope_never_falls_back_to_sd(self):
        for mutation in ('schema', 'profile', 'surface', 'unknown', 'slg', 'selector'):
            with self.subTest(mutation=mutation):
                _, metadata = self.metadata()
                envelope = metadata['rookieui']
                if mutation in ('schema', 'profile', 'surface'):
                    envelope[mutation] = 'invalid'
                elif mutation == 'unknown':
                    envelope['request']['internal_path'] = 'synthetic'
                elif mutation == 'slg':
                    envelope['request']['moss_options']['slg_enabled'] = 'false'
                else:
                    envelope['request']['text_encoder_name'] = 'unregistered.safetensors'
                with self.assertRaises((ValueError, TypeError)):
                    self.parse(metadata)

    def test_full_length_unicode_and_json_escaping_round_trip(self):
        request = normalize(prompt='字' * 12000, negative_prompt='否' * 12000, seed=1)
        metadata = translate_txt2img_request(request).generation_metadata
        png = {'parameters': metadata['parameters'],
               'rookieui': json.dumps(metadata['extra_pnginfo']['rookieui'], ensure_ascii=True)}
        self.assertEqual(self.parse(png).payload['prompt'], request.prompt)

    def test_duplicate_slg_fields_fail_instead_of_silently_picking_one(self):
        _, metadata = self.metadata()
        metadata['rookieui'] = json.dumps(metadata['rookieui']).replace(
            '"slg_enabled": false', '"slg_enabled": true, "slg_enabled": false')
        with self.assertRaises(ValueError):
            self.parse(metadata)


if __name__ == '__main__':
    unittest.main()
