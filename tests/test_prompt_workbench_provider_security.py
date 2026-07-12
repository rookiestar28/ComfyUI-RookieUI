from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest import mock

from rookieui.services import prompt_workbench_openai as provider


class _FakeHttpResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.headers = mock.Mock()
        self.headers.get_content_charset.return_value = "utf-8"
        self.read_amounts: list[int] = []

    def read(self, amount: int = -1) -> bytes:
        self.read_amounts.append(amount)
        return self.payload if amount < 0 else self.payload[:amount]

    def __enter__(self) -> "_FakeHttpResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class PromptWorkbenchProviderSecurityTests(unittest.TestCase):
    def test_default_and_explicit_custom_http_endpoints_are_distinct(self) -> None:
        validate = getattr(provider, "validate_provider_endpoint", None)
        self.assertTrue(callable(validate), "provider endpoint validator is required")
        if not callable(validate):
            return

        self.assertEqual(
            validate("", default_url="https://api.openai.com/v1", allow_custom_endpoint=False),
            "https://api.openai.com/v1",
        )
        with self.assertRaisesRegex(provider.PromptWorkbenchOpenAIProviderError, "allow_custom_endpoint"):
            validate(
                "https://example.test/v1",
                default_url="https://api.openai.com/v1",
                allow_custom_endpoint=False,
            )
        self.assertEqual(
            validate(
                "http://127.0.0.1:11434/v1",
                default_url="https://api.openai.com/v1",
                allow_custom_endpoint=True,
            ),
            "http://127.0.0.1:11434/v1",
        )

    def test_endpoint_rejects_scheme_credentials_fragment_and_missing_host(self) -> None:
        validate = getattr(provider, "validate_provider_endpoint", None)
        self.assertTrue(callable(validate), "provider endpoint validator is required")
        if not callable(validate):
            return

        invalid_urls = (
            "file:///tmp/provider.json",
            "ftp://example.test/v1",
            "https://user:pass@example.test/v1",  # pragma: allowlist secret
            "https://example.test/v1#fragment",
            "https:///missing-host",
            "http://[invalid-ipv6",
            "https://example.test/white space",
        )
        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(provider.PromptWorkbenchOpenAIProviderError):
                    validate(
                        url,
                        default_url="https://api.openai.com/v1",
                        allow_custom_endpoint=True,
                    )

    def test_timeout_request_and_response_sizes_are_bounded(self) -> None:
        bounded_timeout = getattr(provider, "bounded_provider_timeout", None)
        self.assertTrue(callable(bounded_timeout), "provider timeout bound is required")
        if not callable(bounded_timeout):
            return

        self.assertEqual(bounded_timeout(1), 5)
        self.assertEqual(bounded_timeout(999), 60)
        self.assertEqual(bounded_timeout(20), 20)

        max_request = getattr(provider, "MAX_PROVIDER_REQUEST_BYTES", 0)
        max_response = getattr(provider, "MAX_PROVIDER_RESPONSE_BYTES", 0)
        self.assertEqual(max_request, 256 * 1024)
        self.assertEqual(max_response, 1024 * 1024)

        with mock.patch.object(provider.request, "urlopen") as mocked_urlopen:
            with self.assertRaisesRegex(provider.PromptWorkbenchOpenAIProviderError, "request body"):
                provider.urlopen_json(
                    "https://api.openai.com/v1/chat/completions",
                    data=b"x" * (max_request + 1),
                )
            mocked_urlopen.assert_not_called()

        response = _FakeHttpResponse(b"x" * (max_response + 1))
        with mock.patch.object(provider.request, "urlopen", return_value=response):
            with self.assertRaisesRegex(provider.PromptWorkbenchOpenAIProviderError, "response body"):
                provider.urlopen_json("https://api.openai.com/v1/models")
        self.assertEqual(response.read_amounts, [max_response + 1])

    def test_openai_custom_endpoint_requires_opt_in_before_network(self) -> None:
        config = {
            "api_key": "provider-test-key",  # pragma: allowlist secret
            "base_url": "https://example.test/v1",
            "model": "test-model",
        }
        with mock.patch.object(provider.request, "urlopen") as mocked_urlopen:
            with self.assertRaisesRegex(provider.PromptWorkbenchOpenAIProviderError, "allow_custom_endpoint"):
                provider.openai_chat_completion(
                    provider_config=config,
                    messages=[{"role": "user", "content": "hello"}],
                )
            mocked_urlopen.assert_not_called()

        config["allow_custom_endpoint"] = True
        response = _FakeHttpResponse(
            json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")
        )
        with mock.patch.object(provider.request, "urlopen", return_value=response):
            self.assertEqual(
                provider.openai_chat_completion(
                    provider_config=config,
                    messages=[{"role": "user", "content": "hello"}],
                ),
                "ok",
            )

    def test_scope_explicitly_does_not_claim_enterprise_network_isolation(self) -> None:
        module_text = Path(provider.__file__).read_text(encoding="utf-8") if provider.__file__ else ""
        self.assertIn("does not provide DNS-rebinding or enterprise egress isolation", module_text)


if __name__ == "__main__":
    unittest.main()
