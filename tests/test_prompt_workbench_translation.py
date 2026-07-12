from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest import mock

from rookieui.services import prompt_workbench_state
from rookieui.services.prompt_workbench_translation import (
    build_prompt_workbench_provider_payload,
    translate_prompt_workbench_payload,
)
from rookieui.contracts.prompt_workbench import PROMPT_WORKBENCH_SHIPPED_TRANSLATION_PROVIDER_IDS


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
                            "allow_custom_endpoint": True,
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

    def test_provider_payload_exposes_translation_provider_layers(self) -> None:
        payload = build_prompt_workbench_provider_payload()
        providers = {
            provider["provider_id"]: provider
            for provider in payload["surfaces"]["translation"]["providers"]
        }

        self.assertEqual(
            payload["surfaces"]["translation"]["shipped_provider_ids"],
            list(PROMPT_WORKBENCH_SHIPPED_TRANSLATION_PROVIDER_IDS),
        )
        self.assertEqual(
            payload["surfaces"]["translation"]["provider_layer_order"],
            [
                "csv_tag_dictionary",
                "shipped_lightweight",
                "optional_openai_compatible",
                "optional_local_host_model",
                "reference_only",
            ],
        )
        self.assertEqual(providers["csv_tag_dictionary"]["provider_layer"], "csv_tag_dictionary")
        self.assertEqual(providers["mymemory_free"]["provider_layer"], "shipped_lightweight")
        self.assertEqual(providers["openai"]["provider_layer"], "optional_openai_compatible")
        self.assertEqual(providers["local_host_model"]["provider_layer"], "optional_local_host_model")
        self.assertEqual(providers["local_host_model"]["availability"]["status"], "deferred")
        self.assertEqual(providers["itranslate_free"]["availability"]["status"], "reference_only")
        self.assertEqual(providers["baidu_free"]["execution_state"], "reference_only")
        self.assertEqual(providers["mymemory"]["execution_state"], "reference_only")
        self.assertNotIn("gemma", repr(payload).lower())

    def test_csv_dictionary_provider_translates_exact_runtime_dictionary_hits(self) -> None:
        catalog_root = Path(self.runtime_dir.name) / "catalogs"
        catalog_root.mkdir(parents=True)
        (catalog_root / "translation_dictionary.zh-TW.csv").write_text(
            "source,target\nmasterpiece,傑作\ncity skyline,城市天際線\n",
            encoding="utf-8",
        )
        prompt_workbench_state.update_prompt_workbench_config(
            {
                "translation": {
                    "default_provider": "csv_tag_dictionary",
                    "providers": {},
                }
            }
        )

        payload = translate_prompt_workbench_payload(
            {"text": "masterpiece, city skyline, unknown tag", "to_lang": "zh-TW"}
        ).to_payload()

        self.assertEqual(payload["provider_id"], "csv_tag_dictionary")
        self.assertEqual(payload["provider_layer"], "csv_tag_dictionary")
        self.assertEqual(payload["translated_text"], "傑作, 城市天際線, unknown tag")
        self.assertEqual(payload["dictionary_hits"], ["masterpiece", "city skyline"])
        self.assertEqual(payload["dictionary_misses"], ["unknown tag"])

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
                            "allow_custom_endpoint": True,
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

    @mock.patch("rookieui.services.prompt_workbench_openai.request.urlopen")
    def test_dictionary_first_manual_translation_falls_back_for_misses(self, mocked_urlopen: mock.Mock) -> None:
        catalog_root = Path(self.runtime_dir.name) / "catalogs"
        catalog_root.mkdir(parents=True)
        (catalog_root / "translation_dictionary.zh-TW.csv").write_text(
            "source,target\nmasterpiece,傑作\n",
            encoding="utf-8",
        )
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
        mocked_urlopen.return_value = _FakeHttpResponse({"responseData": {"translatedText": "城市天際線"}})

        payload = translate_prompt_workbench_payload(
            {
                "text": "masterpiece, city skyline",
                "from_lang": "en",
                "to_lang": "zh-TW",
                "dictionary_first": True,
            }
        ).to_payload()

        self.assertEqual(payload["provider_id"], "mymemory_free")
        self.assertEqual(payload["fallback_provider_id"], "mymemory_free")
        self.assertEqual(payload["translated_text"], "傑作, 城市天際線")
        self.assertEqual(payload["dictionary_hits"], ["masterpiece"])
        self.assertEqual(payload["dictionary_misses"], ["city skyline"])
        self.assertEqual(mocked_urlopen.call_count, 1)

    @mock.patch("rookieui.services.prompt_workbench_openai.request.urlopen")
    def test_dictionary_only_auto_translation_does_not_call_network_for_misses(self, mocked_urlopen: mock.Mock) -> None:
        catalog_root = Path(self.runtime_dir.name) / "catalogs"
        catalog_root.mkdir(parents=True)
        (catalog_root / "translation_dictionary.zh-TW.csv").write_text(
            "source,target\nmasterpiece,傑作\n",
            encoding="utf-8",
        )
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

        payload = translate_prompt_workbench_payload(
            {
                "text": "masterpiece, city skyline",
                "from_lang": "en",
                "to_lang": "zh-TW",
                "auto_translate": True,
            }
        ).to_payload()

        self.assertEqual(payload["provider_id"], "csv_tag_dictionary")
        self.assertTrue(payload["dictionary_only"])
        self.assertEqual(payload["translated_text"], "傑作, city skyline")
        self.assertEqual(payload["dictionary_hits"], ["masterpiece"])
        self.assertEqual(payload["dictionary_misses"], ["city skyline"])
        mocked_urlopen.assert_not_called()

    @mock.patch("rookieui.services.prompt_workbench_openai.request.urlopen")
    def test_translation_blacklist_skips_dictionary_and_provider_translation(self, mocked_urlopen: mock.Mock) -> None:
        catalog_root = Path(self.runtime_dir.name) / "catalogs"
        catalog_root.mkdir(parents=True)
        (catalog_root / "translation_dictionary.zh-TW.csv").write_text(
            "source,target\nmasterpiece,傑作\nprivate style,私密風格\n",
            encoding="utf-8",
        )
        prompt_workbench_state.update_prompt_workbench_blacklist(
            {
                "enabled": True,
                "entries": ["bad hands"],
                "translation_entries": ["private style"],
            }
        )
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
        mocked_urlopen.return_value = _FakeHttpResponse({"responseData": {"translatedText": "城市天際線"}})

        payload = translate_prompt_workbench_payload(
            {
                "text": "masterpiece, private style, city skyline",
                "from_lang": "en",
                "to_lang": "zh-TW",
                "dictionary_first": True,
            }
        ).to_payload()

        self.assertEqual(payload["translated_text"], "傑作, private style, 城市天際線")
        self.assertEqual(payload["dictionary_hits"], ["masterpiece"])
        self.assertEqual(payload["dictionary_misses"], ["city skyline"])
        self.assertEqual(payload["blacklisted_terms"], ["private style"])
        self.assertEqual(mocked_urlopen.call_count, 1)

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
