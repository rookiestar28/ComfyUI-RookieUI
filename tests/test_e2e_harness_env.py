from __future__ import annotations

import contextlib
import io
import socket
import sys
import unittest
from unittest import mock

from scripts import e2e_harness_env


def _reserve_loopback_port() -> tuple[socket.socket, int]:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    return listener, int(listener.getsockname()[1])


def _pick_free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class E2EHarnessEnvTests(unittest.TestCase):
    def test_resolve_bindable_port_returns_first_free_candidate(self) -> None:
        first_port = _pick_free_loopback_port()
        second_port = _pick_free_loopback_port()

        resolved_port = e2e_harness_env.resolve_bindable_port([first_port, second_port])

        self.assertEqual(resolved_port, first_port)

    def test_resolve_bindable_port_skips_occupied_candidate(self) -> None:
        occupied_listener, occupied_port = _reserve_loopback_port()
        try:
            fallback_port = _pick_free_loopback_port()

            resolved_port = e2e_harness_env.resolve_bindable_port([occupied_port, fallback_port])

            self.assertEqual(resolved_port, fallback_port)
        finally:
            occupied_listener.close()

    def test_main_prints_selected_port(self) -> None:
        target_port = _pick_free_loopback_port()

        with (
            mock.patch.object(sys, "argv", ["e2e_harness_env.py", "--candidate-ports", str(target_port)]),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = e2e_harness_env.main()

        self.assertEqual(result, 0)
        self.assertEqual(stdout.getvalue().strip(), str(target_port))
