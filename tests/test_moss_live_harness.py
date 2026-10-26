from __future__ import annotations

import contextlib
import io
import sys
import unittest
from unittest import mock

from scripts import run_host_embedded_e2e as embedded
from scripts import run_live_smoke_tests as live


class MossLiveHarnessTests(unittest.TestCase):
    def test_embedded_forwards_layout_in_both_strict_phases(self) -> None:
        args = embedded._build_parser().parse_args(
            ['--validation-mode', 'catalog', '--profiles', 'moss_image_base,moss_image_sft', '--moss-layout']
        )
        for execute in (False, True):
            command = embedded._build_live_smoke_command(args, execute=execute)
            self.assertIn('--moss-layout', command)
            self.assertNotIn('--report-only', command)
            self.assertEqual('--execute' in command, execute)
        ordinary = embedded._build_parser().parse_args([])
        self.assertNotIn('--moss-layout', embedded._build_live_smoke_command(ordinary, execute=False))

    def test_layout_rejects_wrong_profile_and_lane_before_network_even_in_report_mode(self) -> None:
        for arguments in (
            ['--profiles', 'moss_image_base,klein_9b'],
            ['--validation-mode', 'image-edit', '--profiles', 'moss_image_base'],
        ):
            with (
                mock.patch.object(sys, 'argv', ['live', '--moss-layout', '--report-only', *arguments]),
                mock.patch.object(live, '_load_bootstrap_payload') as fetch,
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(live.main(), 1)
                fetch.assert_not_called()

    def test_native_plain_defaults_and_rectangular_layout_request(self) -> None:
        for profile, plain_slg in [('moss_image_base', True), ('moss_image_sft', False)]:
            preset = {'width': 1024, 'height': 1024, 'steps': 25, 'cfg_scale': 2.5}
            plain = live._build_txt2img_payload(profile, preset, 'owned-client')
            self.assertEqual(plain['steps'], 25)
            self.assertEqual(plain['moss_options'], {'slg_enabled': plain_slg})
            layout = live._build_txt2img_payload(profile, preset, 'owned-client', moss_layout=True)
            self.assertEqual((layout['width'], layout['height']), (1024, 768))
            self.assertEqual(layout['moss_options']['slg_enabled'], True)
            self.assertEqual([r['kind'] for r in layout['moss_options']['layout']['elements']], ['object', 'text'])
            self.assertEqual(layout['moss_options']['layout']['elements'][1]['text'], 'MOSS')
            layout['moss_options']['layout']['elements'][0]['bbox'][0] = 999
            again = live._build_txt2img_payload(profile, preset, 'owned-client', moss_layout=True)
            self.assertEqual(again['moss_options']['layout']['elements'][0]['bbox'], [200, 100, 850, 450])
            self.assertEqual(again['moss_options']['layout']['elements'][1]['bbox'], [250, 550, 600, 950])
        old = live._build_txt2img_payload('klein_9b', {}, 'owned-client')
        self.assertNotIn('moss_options', old)
        self.assertEqual(old['steps'], 1)
        with self.assertRaises(ValueError):
            live._build_txt2img_payload('klein_9b', {}, 'owned-client', moss_layout=True)

    def test_preflight_requires_effective_native_slg_capability(self) -> None:
        row = {'without_slg_available': True, 'slg_available': False}
        with mock.patch.object(live, '_load_capabilities_payload', return_value={'moss_image': {'profiles': {
            'moss_image_base': row, 'moss_image_sft': row,
        }}}):
            self.assertEqual(live._validate_moss_live_capabilities('http://localhost', ['moss_image_sft'],
                             moss_layout=False, timeout_seconds=1), [])
            self.assertTrue(live._validate_moss_live_capabilities('http://localhost', ['moss_image_base'],
                            moss_layout=False, timeout_seconds=1))
            self.assertTrue(live._validate_moss_live_capabilities('http://localhost', ['moss_image_sft'],
                            moss_layout=True, timeout_seconds=1))
        for payload in ({}, {'moss_image': {'profiles': {'moss_image_sft': {'slg_available': 'true'}}}}):
            with mock.patch.object(live, '_load_capabilities_payload', return_value=payload):
                self.assertTrue(live._validate_moss_live_capabilities('http://localhost', ['moss_image_sft'],
                                moss_layout=True, timeout_seconds=1))

    def test_execute_forwards_layout_without_retrying_failed_submission(self) -> None:
        with mock.patch.object(live, '_request_json', side_effect=RuntimeError('uncertain POST')) as request:
            with self.assertRaisesRegex(RuntimeError, 'uncertain POST'):
                live._run_execute_smoke('http://localhost', ['moss_image_sft'], {}, {'moss_image_sft': {}},
                    request_timeout_seconds=1, poll_timeout_seconds=1, poll_interval_seconds=.1, moss_layout=True)
            self.assertEqual(request.call_count, 1)
            self.assertTrue(request.call_args.kwargs['payload']['moss_options']['layout']['enabled'])
