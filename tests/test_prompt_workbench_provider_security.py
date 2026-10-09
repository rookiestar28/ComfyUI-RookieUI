from __future__ import annotations

from contextlib import contextmanager
from email.message import Message
import os
import socket
import ssl
import unittest
from unittest import mock

from rookieui.services import prompt_workbench_openai as provider


_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_MYMEMORY_URL = "https://api.mymemory.translated.net/get?q=fixture&langpair=en%7Ces"


class _FakeHttpResponse:
    def __init__(self, body: bytes = b'{"ok": true}', *, status: int = 200) -> None:
        self.body = body
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = "application/json; charset=utf-8"
        self.read_amounts: list[int] = []
        self.closed = False

    def read(self, amount: int) -> bytes:
        self.read_amounts.append(amount)
        return self.body[:amount]

    def __enter__(self) -> "_FakeHttpResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.closed = True


class PromptWorkbenchProviderSecurityTests(unittest.TestCase):
    @staticmethod
    def _dns_answer(address: str, family: socket.AddressFamily = socket.AF_INET) -> tuple:
        sockaddr = (address, 443) if family == socket.AF_INET else (address, 443, 0, 0)
        return family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr

    @contextmanager
    def _transport(self, response: _FakeHttpResponse):
        connection = mock.Mock()
        connection.getresponse.return_value = response
        with (
            mock.patch.object(provider.socket, "getaddrinfo", return_value=[self._dns_answer("1.1.1.1")]) as dns,
            mock.patch.object(provider, "_PinnedProviderHTTPSConnection", return_value=connection) as factory,
        ):
            yield connection, dns, factory

    def test_only_the_provider_specific_official_base_is_accepted(self) -> None:
        for default in (provider.DEFAULT_OPENAI_BASE_URL, provider.DEFAULT_MYMEMORY_BASE_URL):
            for url in ("", default, default + "/"):
                with self.subTest(default=default, url=url):
                    self.assertEqual(
                        provider.validate_provider_endpoint(url, default_url=default, allow_custom_endpoint=False),
                        default,
                    )
        with self.assertRaises(provider.PromptWorkbenchOpenAIProviderError):
            provider.validate_provider_endpoint(
                provider.DEFAULT_MYMEMORY_BASE_URL,
                default_url=provider.DEFAULT_OPENAI_BASE_URL,
                allow_custom_endpoint=True,
            )

    def test_request_controlled_opt_in_never_authorizes_a_custom_endpoint(self) -> None:
        for url in (
            "http://127.0.0.1/v1",
            "https://example.test/v1",
            "https://api.openai.com.attacker.test/v1",
            "https://api.openai.com@attacker.test/v1",
            "https://api.openai.com:444/v1",
            "https://api.openai.com/v1?redirect=fixture",
            "https://api.openai.com/v1#fragment",
            "https://api.openai.com/v1/../v1",
            "https://api.openai.com/v1\nother",
            "file:///fixture.json",
            "https://[invalid/v1",
        ):
            with self.subTest(url=url):
                with mock.patch.object(provider, "_open_provider_response") as network:
                    with self.assertRaises(provider.PromptWorkbenchOpenAIProviderError):
                        provider.openai_chat_completion(
                            provider_config={
                                "base_url": url,
                                "allow_custom_endpoint": True,
                                "api_key": "synthetic-key",  # pragma: allowlist secret
                                "model": "fixture-model",
                            },
                            messages=[{"role": "user", "content": "fixture"}],
                        )
                    network.assert_not_called()

    def test_low_level_transport_rejects_unapproved_methods_paths_hosts_and_headers_before_dns(self) -> None:
        cases = (
            (_OPENAI_URL, None, {}),
            ("http://api.openai.com/v1/chat/completions", b"{}", {}),
            ("https://api.openai.com:444/v1/chat/completions", b"{}", {}),
            ("https://api.openai.com/v1/models", b"{}", {}),
            (_OPENAI_URL + "?q=fixture", b"{}", {}),
            ("https://api.openai.com.attacker.test/v1/chat/completions", b"{}", {}),
            (_OPENAI_URL, b"{}", {"Host": "attacker.test"}),
            (_MYMEMORY_URL, b"{}", {}),
            (_MYMEMORY_URL, None, {"Authorization": "Bearer synthetic-key"}),
            (_MYMEMORY_URL + "&q=duplicate", None, {}),
            (_MYMEMORY_URL + "&redirect=fixture", None, {}),
        )
        with mock.patch.object(provider.socket, "getaddrinfo") as dns:
            for url, data, headers in cases:
                with self.subTest(url=url, data_present=data is not None):
                    with self.assertRaises(provider.PromptWorkbenchOpenAIProviderError):
                        provider.urlopen_json(url, data=data, headers=headers)
            dns.assert_not_called()

    def test_all_dns_answers_must_be_public_unicast(self) -> None:
        unsafe = (
            "127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.1.1", "169.254.169.254",
            "100.64.0.1", "0.0.0.0", "224.0.0.1", "240.0.0.1", "192.0.2.1",
            "::", "::1", "fc00::1", "fe80::1", "fec0::1", "ff0e::1",
            "::ffff:127.0.0.1", "::ffff:1.1.1.1", "2002:7f00:1::", "64:ff9b::7f00:1",
        )
        for address in unsafe:
            family = socket.AF_INET6 if ":" in address else socket.AF_INET
            for mixed in (False, True):
                answers = ([self._dns_answer("1.1.1.1")] if mixed else []) + [self._dns_answer(address, family)]
                with self.subTest(address=address, mixed=mixed):
                    with (
                        mock.patch.object(provider.socket, "getaddrinfo", return_value=answers),
                        mock.patch.object(provider.socket, "socket") as connect,
                    ):
                        with self.assertRaisesRegex(provider.PromptWorkbenchOpenAIProviderError, "unsafe address"):
                            provider.urlopen_json(_OPENAI_URL, data=b"{}")
                        connect.assert_not_called()

    def test_public_ipv6_is_retained_and_invalid_dns_is_rejected(self) -> None:
        answer = self._dns_answer("2606:4700:4700::1111", socket.AF_INET6)
        with mock.patch.object(provider.socket, "getaddrinfo", return_value=[answer]):
            selected = provider._resolve_public_provider_address("api.openai.com")
        self.assertEqual(selected.family, socket.AF_INET6)
        self.assertEqual(selected.address, "2606:4700:4700::1111")
        for answers in ([], [self._dns_answer("invalid")], [self._dns_answer("::1", socket.AF_INET)]):
            with mock.patch.object(provider.socket, "getaddrinfo", return_value=answers):
                with self.assertRaises(provider.PromptWorkbenchOpenAIProviderError):
                    provider._resolve_public_provider_address("api.openai.com")

    def test_connect_pins_numeric_address_without_reresolution_and_verifies_original_tls_hostname(self) -> None:
        for family, address, target in (
            (socket.AF_INET, "1.1.1.1", ("1.1.1.1", 443)),
            (socket.AF_INET6, "2606:4700:4700::1111", ("2606:4700:4700::1111", 443, 0, 0)),
        ):
            with self.subTest(family=family):
                connection = provider._PinnedProviderHTTPSConnection(
                    "api.openai.com", provider._ProviderAddress(family, address), timeout=20
                )
                self.assertTrue(connection._context.check_hostname)
                self.assertEqual(connection._context.verify_mode, ssl.CERT_REQUIRED)
                sock = mock.Mock()
                tls = mock.Mock(wraps=connection._context)
                connection._context = tls
                with (
                    mock.patch.object(provider.socket, "socket", return_value=sock),
                    mock.patch.object(provider.socket, "getaddrinfo") as dns,
                ):
                    tls.wrap_socket.return_value = mock.Mock()
                    connection.connect()
                sock.connect.assert_called_once_with(target)
                sock.settimeout.assert_called_once_with(20)
                tls.wrap_socket.assert_called_once_with(sock, server_hostname="api.openai.com")
                dns.assert_not_called()
                connection.close()

    def test_tls_failure_closes_socket_and_tunnels_are_rejected(self) -> None:
        connection = provider._PinnedProviderHTTPSConnection(
            "api.openai.com", provider._ProviderAddress(socket.AF_INET, "1.1.1.1"), timeout=20
        )
        sock = mock.Mock()
        connection._context = mock.Mock()
        connection._context.wrap_socket.side_effect = ssl.SSLCertVerificationError("synthetic failure")
        with mock.patch.object(provider.socket, "socket", return_value=sock):
            with self.assertRaises(ssl.SSLCertVerificationError):
                connection.connect()
        sock.close.assert_called_once()
        connection.set_tunnel("attacker.test")
        with mock.patch.object(provider.socket, "socket") as connect:
            with self.assertRaises(provider.PromptWorkbenchOpenAIProviderError):
                connection.connect()
            connect.assert_not_called()

    def test_redirects_never_issue_a_second_request_or_read_body(self) -> None:
        for status in (301, 302, 303, 307, 308):
            response = _FakeHttpResponse(status=status)
            response.headers["Location"] = "http://127.0.0.1/fixture"
            with self.subTest(status=status):
                with self._transport(response) as (connection, dns, factory):
                    with self.assertRaisesRegex(provider.PromptWorkbenchOpenAIProviderError, "redirects"):
                        provider.urlopen_json(_OPENAI_URL, data=b"{}", headers=provider.openai_headers("fixture"))
                    connection.request.assert_called_once()
                    connection.close.assert_called_once()
                    factory.assert_called_once()
                    dns.assert_called_once()
                self.assertTrue(response.closed)
                self.assertEqual(response.read_amounts, [])

    def test_proxy_environment_cannot_replace_the_provider_destination(self) -> None:
        response = _FakeHttpResponse()
        with (
            mock.patch.dict(os.environ, {"HTTPS_PROXY": "http://127.0.0.1:1", "ALL_PROXY": "http://attacker.test"}),
            mock.patch.object(provider.request, "urlopen") as urllib_network,
            self._transport(response) as (connection, dns, factory),
        ):
            self.assertEqual(provider.urlopen_json(_OPENAI_URL, data=b"{}"), {"ok": True})
            factory.assert_called_once_with("api.openai.com", provider._ProviderAddress(socket.AF_INET, "1.1.1.1"), timeout=20)
            connection.request.assert_called_once_with("POST", "/v1/chat/completions", body=b"{}", headers={})
            dns.assert_called_once_with("api.openai.com", 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
            urllib_network.assert_not_called()
        self.assertTrue(response.closed)

    def test_mymemory_get_sends_no_authorization_and_preserves_query(self) -> None:
        with self._transport(_FakeHttpResponse()) as (connection, _, factory):
            provider.urlopen_json(_MYMEMORY_URL)
            factory.assert_called_once_with(
                "api.mymemory.translated.net", provider._ProviderAddress(socket.AF_INET, "1.1.1.1"), timeout=20
            )
            connection.request.assert_called_once_with("GET", "/get?q=fixture&langpair=en%7Ces", body=None, headers={})

    def test_timeout_request_url_and_response_sizes_remain_bounded(self) -> None:
        self.assertEqual(provider.bounded_provider_timeout(1), 5)
        self.assertEqual(provider.bounded_provider_timeout(999), 60)
        for timeout, expected in ((1, 5), (999, 60)):
            with self._transport(_FakeHttpResponse()) as (_, _, factory):
                provider.urlopen_json(_OPENAI_URL, data=b"{}", timeout=timeout)
                self.assertEqual(factory.call_args.kwargs["timeout"], expected)
        with mock.patch.object(provider.socket, "getaddrinfo") as dns:
            with self.assertRaisesRegex(provider.PromptWorkbenchOpenAIProviderError, "request body"):
                provider.urlopen_json(_OPENAI_URL, data=b"x" * (provider.MAX_PROVIDER_REQUEST_BYTES + 1))
            with self.assertRaisesRegex(provider.PromptWorkbenchOpenAIProviderError, "URL"):
                provider.urlopen_json(_MYMEMORY_URL + "&de=" + "x" * provider.MAX_PROVIDER_REQUEST_BYTES)
            dns.assert_not_called()
        response = _FakeHttpResponse(b"x" * (provider.MAX_PROVIDER_RESPONSE_BYTES + 1))
        with self._transport(response) as (connection, _, _):
            with self.assertRaisesRegex(provider.PromptWorkbenchOpenAIProviderError, "response body"):
                provider.urlopen_json(_OPENAI_URL, data=b"{}")
            connection.close.assert_called_once()
        self.assertEqual(response.read_amounts, [provider.MAX_PROVIDER_RESPONSE_BYTES + 1])
        self.assertTrue(response.closed)

    def test_provider_errors_are_sanitized_and_connections_close_without_retry(self) -> None:
        for status in (401, 429, 500):
            response = _FakeHttpResponse(b"synthetic-sensitive-body", status=status)
            with self._transport(response) as (connection, _, _):
                with self.assertRaisesRegex(provider.PromptWorkbenchOpenAIProviderError, f"HTTP {status}") as error:
                    provider.urlopen_json(_OPENAI_URL, data=b"{}")
                self.assertNotIn("synthetic-sensitive-body", str(error.exception))
                connection.close.assert_called_once()
                connection.request.assert_called_once()
                self.assertTrue(response.closed)
        with self._transport(_FakeHttpResponse()) as (connection, _, _):
            connection.request.side_effect = OSError("synthetic-sensitive-body")
            with self.assertRaisesRegex(provider.PromptWorkbenchOpenAIProviderError, "OSError") as error:
                provider.urlopen_json(_OPENAI_URL, data=b"{}")
            self.assertNotIn("synthetic-sensitive-body", str(error.exception))
            connection.close.assert_called_once()
            connection.request.assert_called_once()

    def test_invalid_json_charset_and_nonobject_payloads_fail_after_cleanup(self) -> None:
        for body, charset in ((b"invalid", "utf-8"), (b"[]", "utf-8"), (b"{}", "unknown-charset"), (b"\xff", "utf-8")):
            response = _FakeHttpResponse(body)
            response.headers.replace_header("Content-Type", f"application/json; charset={charset}")
            with self.subTest(charset=charset, size=len(body)):
                with self._transport(response) as (connection, _, _):
                    with self.assertRaises(provider.PromptWorkbenchOpenAIProviderError):
                        provider.urlopen_json(_OPENAI_URL, data=b"{}")
                    connection.close.assert_called_once()
                self.assertTrue(response.closed)


if __name__ == "__main__":
    unittest.main()
