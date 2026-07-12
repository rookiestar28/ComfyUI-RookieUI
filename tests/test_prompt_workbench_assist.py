from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest import mock

from rookieui.services import prompt_workbench_state
from rookieui.services.prompt_workbench_assist import assist_prompt_workbench_payload


class _FakeHttpResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload).encode("utf-8")
        self.headers = mock.Mock()
        self.headers.get_content_charset.return_value = "utf-8"

    def read(self, amount: int = -1) -> bytes:
        return self._payload if amount < 0 else self._payload[:amount]

    def __enter__(self) -> "_FakeHttpResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class PromptWorkbenchAssistTests(unittest.TestCase):
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

    @mock.patch("rookieui.services.prompt_workbench_openai.request.urlopen")
    def test_ai_assist_generates_prompt_via_openai_provider(self, mocked_urlopen: mock.Mock) -> None:
        prompt_workbench_state.update_prompt_workbench_config(
            {
                "language": "zh-TW",
                "theme_style": "rookieui_graphite",
                "ai_assist": {
                    "default_provider": "openai",
                    "instruction_preset": "Turn this into a concise SD prompt.",
                    "providers": {
                        "openai": {
                            "api_key": "test-openai-key",  # pragma: allowlist secret
                            "base_url": "https://example.test/v1",
                            "allow_custom_endpoint": True,
                            "model": "gpt-4.1-mini",
                        }
                    },
                },
            }
        )
        mocked_urlopen.return_value = _FakeHttpResponse(
            {"choices": [{"message": {"content": "masterpiece, city skyline, dusk lighting"}}]}
        )

        payload = assist_prompt_workbench_payload(
            {
                "image_description": "a city skyline at dusk with dramatic clouds",
                "language": "zh-TW",
                "theme_style": "rookieui_graphite",
            }
        ).to_payload()

        self.assertEqual(payload["provider_id"], "openai")
        self.assertEqual(payload["language"], "zh-TW")
        self.assertEqual(payload["theme_style"], "rookieui_graphite")
        self.assertEqual(payload["generated_prompt"], "masterpiece, city skyline, dusk lighting")
        self.assertIn("/chat/completions", mocked_urlopen.call_args.args[0].full_url)

    def test_ai_assist_rejects_missing_description(self) -> None:
        with self.assertRaises(ValueError):
            assist_prompt_workbench_payload({"image_description": "  "})

    def test_ai_assist_rejects_unconfigured_provider(self) -> None:
        prompt_workbench_state.update_prompt_workbench_config(
            {
                "ai_assist": {
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

        with self.assertRaises(RuntimeError):
            assist_prompt_workbench_payload({"image_description": "portrait with neon city background"})
