from __future__ import annotations

import contextlib
import io
import sys
import unittest
from unittest import mock

from scripts import run_host_embedded_e2e as host_e2e


class HostEmbeddedE2ETests(unittest.TestCase):
    def test_build_live_smoke_command_forwards_runtime_options(self) -> None:
        args = host_e2e._build_parser().parse_args(
            [
                "--base-url",
                "http://127.0.0.1:9191",
                "--validation-mode",
                "prompt-workbench",
                "--profiles",
                "sd15,sdxl",
                "--request-timeout-seconds",
                "12",
                "--poll-timeout-seconds",
                "34",
                "--poll-interval-seconds",
                "5",
            ]
        )

        command = host_e2e._build_live_smoke_command(args, execute=True)

        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[1], str(host_e2e._LIVE_SMOKE_SCRIPT))
        self.assertIn("--validation-mode", command)
        self.assertIn("prompt-workbench", command)
        self.assertIn("--profiles", command)
        self.assertIn("sd15,sdxl", command)
        self.assertIn("--execute", command)

    def test_main_runs_report_then_execute_by_default(self) -> None:
        completed = mock.Mock(returncode=0)
        with (
            mock.patch.object(sys, "argv", ["run_host_embedded_e2e.py"]),
            mock.patch.object(host_e2e.subprocess, "run", side_effect=[completed, completed]) as run_mock,
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = host_e2e.main()

        self.assertEqual(result, 0)
        self.assertEqual(run_mock.call_count, 2)
        report_command = run_mock.call_args_list[0].args[0]
        execute_command = run_mock.call_args_list[1].args[0]
        self.assertNotIn("--execute", report_command)
        self.assertIn("--execute", execute_command)

    def test_main_skips_execute_when_requested(self) -> None:
        completed = mock.Mock(returncode=0)
        with (
            mock.patch.object(sys, "argv", ["run_host_embedded_e2e.py", "--skip-execute"]),
            mock.patch.object(host_e2e.subprocess, "run", return_value=completed) as run_mock,
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = host_e2e.main()

        self.assertEqual(result, 0)
        self.assertEqual(run_mock.call_count, 1)
        report_command = run_mock.call_args.args[0]
        self.assertNotIn("--execute", report_command)

    def test_main_returns_report_failure_without_running_execute(self) -> None:
        failing = mock.Mock(returncode=1)
        with (
            mock.patch.object(sys, "argv", ["run_host_embedded_e2e.py"]),
            mock.patch.object(host_e2e.subprocess, "run", return_value=failing) as run_mock,
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = host_e2e.main()

        self.assertEqual(result, 1)
        self.assertEqual(run_mock.call_count, 1)
