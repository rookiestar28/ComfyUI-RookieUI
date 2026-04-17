from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest import mock

from rookieui.services import prompt_workbench_state
from rookieui.services.prompt_workbench_translation import (
    build_prompt_workbench_provider_payload,
    translate_prompt_workbench_payload,
)


class _FakeHttpResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload).encode("utf-8")
        self.headers = mock.Mock()
        self.headers.get_content_charset.return_value = "utf-8"

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeHttpResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class PromptWorkbenchTranslationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.runtime_dir.cleanup)
        self.env_patcher = mock.patch.dict(
            os.environ,
            {"ROOKIEUI_PROMPT_WORKBENCH_RUNTIME_ROOT": self.runtime_dir.name},
            clear=False,
        )
        self.env_patcher.start()
        self.addCleanup(self.env_patcher.stop)

    def test_provider_payload_reports_default_provider_and_readiness(self) -> None:
        prompt_workbench_state.update_prompt_workbench_config(
            {
                "translation": {
                    "default_provider": "openai",
                    "providers": {
                        "openai": {
                            "api_key": "test-openai-key",  # pragma: allowlist secret
                            "base_url": "https://example.test/v1",
                            "model": "gpt-4.1-mini",
                        }
                    },
                }
            }
        )

        payload = build_prompt_workbench_provider_payload()
        openai_entry = next(
            provider for provider in payload["surfaces"]["translation"]["providers"] if provider["provider_id"] == "openai"
        )

        self.assertEqual(payload["surfaces"]["translation"]["default_provider"], "openai")
        self.assertEqual(openai_entry["availability"]["status"], "ready")
        self.assertTrue(openai_entry["default_selected"])
        ai_openai_entry = next(
            provider for provider in payload["surfaces"]["ai_assist"]["providers"] if provider["provider_id"] == "openai"
        )
        self.assertEqual(ai_openai_entry["availability"]["status"], "configuration_required")

    @mock.patch("rookieui.services.prompt_workbench_openai.request.urlopen")
    def test_translate_payload_uses_openai_provider(self, mocked_urlopen: mock.Mock) -> None:
        prompt_workbench_state.update_prompt_workbench_config(
            {
                "translation": {
                    "default_provider": "openai",
                    "providers": {
                        "openai": {
                            "api_key": "test-openai-key",  # pragma: allowlist secret
                            "base_url": "https://example.test/v1",
                            "model": "gpt-4.1-mini",
                        }
                    },
                }
            }
        )
        mocked_urlopen.return_value = _FakeHttpResponse(
            {"choices": [{"message": {"content": "translated prompt"}}]}
        )

        payload = translate_prompt_workbench_payload({"text": "masterpiece, city skyline", "to_lang": "zh-TW"}).to_payload()

        self.assertEqual(payload["mode"], "single")
        self.assertEqual(payload["provider_id"], "openai")
        self.assertEqual(payload["translated_text"], "translated prompt")
        self.assertIn("/chat/completions", mocked_urlopen.call_args.args[0].full_url)

    @mock.patch("rookieui.services.prompt_workbench_openai.request.urlopen")
    def test_translate_payload_supports_mymemory_batch(self, mocked_urlopen: mock.Mock) -> None:
        prompt_workbench_state.update_prompt_workbench_config(
            {
                "translation": {
                    "default_provider": "mymemory_free",
                    "providers": {
                        "mymemory_free": {
                            "email": "tester@example.com",
                        }
                    },
                }
            }
        )
        mocked_urlopen.side_effect = [
            _FakeHttpResponse({"responseData": {"translatedText": "uno"}}),
            _FakeHttpResponse({"responseData": {"translatedText": "dos"}}),
        ]

        payload = translate_prompt_workbench_payload({"texts": ["one", "two"], "from_lang": "en", "to_lang": "es"}).to_payload()

        self.assertEqual(payload["mode"], "batch")
        self.assertEqual(payload["translated_texts"], ["uno", "dos"])
        self.assertEqual(mocked_urlopen.call_count, 2)

    def test_translate_payload_rejects_missing_provider_configuration(self) -> None:
        prompt_workbench_state.update_prompt_workbench_config(
            {
                "translation": {
                    "default_provider": "openai",
                    "providers": {
                        "openai": {
                            "base_url": "https://example.test/v1",
                            "model": "gpt-4.1-mini",
                        }
                    },
                }
            }
        )

        with self.assertRaises(ValueError):
            translate_prompt_workbench_payload({"text": "test", "to_lang": "ja"})

    def test_translate_payload_normalizes_provider_execution_failures(self) -> None:
        prompt_workbench_state.update_prompt_workbench_config(
            {
                "translation": {
                    "default_provider": "google_free",
                    "providers": {
                        "google_free": {}
                    },
                }
            }
        )

        with self.assertRaises(ValueError):
            translate_prompt_workbench_payload({"text": "test", "to_lang": "ja"})
