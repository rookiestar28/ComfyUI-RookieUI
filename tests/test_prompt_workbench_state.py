from __future__ import annotations

import json
import inspect
import os
import tempfile
import unittest
from unittest import mock

from rookieui.services import prompt_workbench_state


class PromptWorkbenchStateTests(unittest.TestCase):
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

    def test_bootstrap_payload_masks_secret_provider_fields(self) -> None:
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

        payload = prompt_workbench_state.get_prompt_workbench_bootstrap_payload()

        self.assertEqual(payload["config"]["translation"]["providers"]["openai"]["api_key"], "********")
        self.assertEqual(
            payload["config"]["translation"]["providers"]["openai"]["base_url"],
            "https://example.test/v1",
        )
        self.assertEqual(payload["config"]["translation"]["providers"]["openai"]["model"], "gpt-4.1-mini")

    def test_provider_payload_is_catalog_aware_and_strips_unknown_fields(self) -> None:
        updated = prompt_workbench_state.update_prompt_workbench_config(
            {
                "translation": {
                    "default_provider": "unknown",
                    "providers": {
                        "openai": {
                            "api_key": "test-openai-key",  # pragma: allowlist secret
                            "base_url": "https://example.test/v1",
                            "model": "gpt-4.1-mini",
                            "rogue_field": "drop-me",
                        },
                        "unsupported_provider": {"token": "ignored"},
                    },
                }
            }
        )

        self.assertEqual(updated["translation"]["default_provider"], "")
        self.assertNotIn("rogue_field", updated["translation"]["providers"]["openai"])
        self.assertNotIn("unsupported_provider", updated["translation"]["providers"])

    def test_surface_state_update_persists_by_namespace(self) -> None:
        updated = prompt_workbench_state.update_prompt_workbench_surface_state(
            "txt2img_prompt",
            {
                "workbench_open": True,
                "active_panel": "history",
                "draft_prompt": "masterpiece, city skyline",
            },
        )

        self.assertTrue(updated["workbench_open"])
        self.assertEqual(updated["active_panel"], "history")
        self.assertEqual(
            prompt_workbench_state.get_prompt_workbench_surface_state("txt2img_prompt")["draft_prompt"],
            "masterpiece, city skyline",
        )

    def test_panel_preferences_normalize_to_supported_panel_ids(self) -> None:
        config = prompt_workbench_state.update_prompt_workbench_config(
            {
                "ui_preferences": {
                    "default_open": True,
                    "preferred_panel": "unknown-panel",
                    "show_history": False,
                    "show_favorites": True,
                }
            }
        )
        state = prompt_workbench_state.update_prompt_workbench_surface_state(
            "txt2img_prompt",
            {"active_panel": "unknown-panel"},
        )

        self.assertEqual(config["ui_preferences"]["preferred_panel"], "editor")
        self.assertEqual(state["active_panel"], "editor")

    def test_language_config_update_normalizes_supported_aliases(self) -> None:
        config = prompt_workbench_state.update_prompt_workbench_config({"language": "zh_TW"})
        self.assertEqual(config["language"], "zh-TW")

        config = prompt_workbench_state.update_prompt_workbench_config({"language": "pt_BR"})
        self.assertEqual(config["language"], "pt-BR")

        config = prompt_workbench_state.update_prompt_workbench_config({"language": "not/a-language"})
        self.assertEqual(config["language"], "en")

    def test_history_and_favorites_support_push_remove_and_reorder(self) -> None:
        history_items = prompt_workbench_state.apply_prompt_workbench_history_action(
            "txt2img_prompt",
            action="push",
            payload={"item": {"prompt_text": "first prompt", "label": "First"}},
        )
        favorite_items = prompt_workbench_state.apply_prompt_workbench_favorite_action(
            "txt2img_prompt",
            action="push",
            payload={"item": {"prompt_text": "favorite one", "label": "One"}},
        )
        favorite_items = prompt_workbench_state.apply_prompt_workbench_favorite_action(
            "txt2img_prompt",
            action="push",
            payload={"item": {"prompt_text": "favorite two", "label": "Two"}},
        )
        moved = prompt_workbench_state.apply_prompt_workbench_favorite_action(
            "txt2img_prompt",
            action="move_up",
            payload={"item_id": favorite_items[1]["id"]},
        )
        removed = prompt_workbench_state.apply_prompt_workbench_history_action(
            "txt2img_prompt",
            action="remove",
            payload={"item_id": history_items[0]["id"]},
        )

        self.assertEqual(len(history_items), 1)
        self.assertEqual(len(removed), 0)
        self.assertEqual([entry["label"] for entry in moved], ["Two", "One"])

    def test_collection_entries_preserve_normalized_token_payloads(self) -> None:
        items = prompt_workbench_state.apply_prompt_workbench_favorite_action(
            "txt2img_prompt",
            action="push",
            payload={
                "item": {
                    "prompt_text": "masterpiece, city skyline",
                    "label": "Token payload",
                    "tag_tokens": ["masterpiece", "city skyline"],
                    "token_payloads": [
                        {
                            "raw_text": " masterpiece ",
                            "normalized_text": "MASTERPIECE",
                            "scope": "prompt",
                            "order_index": 4,
                            "disabled": "no",
                            "selected": True,
                            "translated_text": "傑作",
                            "keyword_family": "plain",
                            "weight": 1.2,
                            "ignored": "drop",
                        },
                        {"raw_text": ""},
                        "drop",
                    ],
                }
            },
        )

        self.assertEqual(items[0]["tag_tokens"], ["masterpiece", "city skyline"])
        self.assertEqual(
            items[0]["token_payloads"],
            [
                {
                    "raw_text": "masterpiece",
                    "normalized_text": "MASTERPIECE",
                    "scope": "prompt",
                    "order_index": 4,
                    "disabled": False,
                    "selected": True,
                    "translated_text": "傑作",
                    "keyword_family": "plain",
                    "weight": 1.2,
                }
            ],
        )

    def test_history_auto_capture_skips_empty_and_duplicate_latest_prompt(self) -> None:
        first = prompt_workbench_state.apply_prompt_workbench_history_action(
            "txt2img_prompt",
            action="auto_capture",
            payload={
                "item": {
                    "prompt_text": "masterpiece, city skyline",
                    "label": "Prompt",
                    "token_payloads": [{"raw_text": "masterpiece", "scope": "prompt"}],
                }
            },
        )
        duplicate = prompt_workbench_state.apply_prompt_workbench_history_action(
            "txt2img_prompt",
            action="auto_capture",
            payload={"item": {"prompt_text": "masterpiece, city skyline", "label": "Duplicate"}},
        )
        empty = prompt_workbench_state.apply_prompt_workbench_history_action(
            "txt2img_prompt",
            action="auto_capture",
            payload={"item": {"prompt_text": "", "label": "Empty"}},
        )
        second = prompt_workbench_state.apply_prompt_workbench_history_action(
            "txt2img_prompt",
            action="auto_capture",
            payload={"item": {"prompt_text": "masterpiece, night skyline", "label": "Prompt"}},
        )

        self.assertEqual(len(first), 1)
        self.assertEqual(len(duplicate), 1)
        self.assertEqual(len(empty), 1)
        self.assertEqual([entry["prompt_text"] for entry in second], ["masterpiece, city skyline", "masterpiece, night skyline"])
        self.assertEqual(first[0]["token_payloads"][0]["raw_text"], "masterpiece")

    def test_collection_action_rejects_unknown_mutation_names(self) -> None:
        with self.assertRaises(ValueError):
            prompt_workbench_state.apply_prompt_workbench_history_action(
                "txt2img_prompt",
                action="typo_push",
                payload={"item": {"prompt_text": "masterpiece"}},
            )

        with self.assertRaises(ValueError):
            prompt_workbench_state.apply_prompt_workbench_favorite_action(
                "txt2img_prompt",
                action="auto_capture",
                payload={"item": {"prompt_text": "masterpiece"}},
            )

    def test_blacklist_update_normalizes_entries(self) -> None:
        updated = prompt_workbench_state.update_prompt_workbench_blacklist(
            {
                "enabled": True,
                "entries": ["bad-hands", "  blurry  ", "", 123],
                "translation_entries": ["private style", "  secret token  ", "", 456],
            }
        )

        self.assertTrue(updated["enabled"])
        self.assertEqual(updated["entries"], ["bad-hands", "blurry"])
        self.assertEqual(updated["translation_entries"], ["private style", "secret token"])

    def test_load_prompt_workbench_store_quarantines_corrupt_json(self) -> None:
        state_path = prompt_workbench_state._prompt_workbench_state_path()
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text("{not-json", encoding="utf-8")

        store = prompt_workbench_state.load_prompt_workbench_store()

        self.assertIn("config", store)
        self.assertFalse(state_path.exists())
        self.assertEqual(len(list(state_path.parent.glob("state.corrupt-*.json"))), 1)

    def test_export_prompt_workbench_store_masks_provider_secrets(self) -> None:
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

        payload = prompt_workbench_state.export_prompt_workbench_store()

        provider_config = payload["data"]["config"]["translation"]["providers"]["openai"]
        self.assertEqual(payload["secret_policy"], "masked_provider_fields")  # pragma: allowlist secret
        self.assertEqual(provider_config["api_key"], "********")
        self.assertEqual(provider_config["base_url"], "https://example.test/v1")
        self.assertNotIn("test-openai-key", json.dumps(payload))  # pragma: allowlist secret

    def test_export_api_has_no_raw_secret_bypass_parameter(self) -> None:
        signature = inspect.signature(prompt_workbench_state.export_prompt_workbench_store)

        self.assertNotIn("include_secrets", signature.parameters)

    def test_import_prompt_workbench_store_preserves_existing_secret_from_masked_export(self) -> None:
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

        exported = prompt_workbench_state.export_prompt_workbench_store()
        exported["data"]["blacklist"] = {
            "enabled": True,
            "entries": ["bad hands"],
            "translation_entries": ["private style"],
        }
        result = prompt_workbench_state.import_prompt_workbench_store(exported)
        stored = prompt_workbench_state.load_prompt_workbench_store()

        self.assertTrue(result["imported"])
        self.assertEqual(stored["blacklist"]["entries"], ["bad hands"])
        self.assertEqual(stored["blacklist"]["translation_entries"], ["private style"])
        self.assertEqual(
            stored["config"]["translation"]["providers"]["openai"]["api_key"],
            "test-openai-key",  # pragma: allowlist secret
        )

    def test_explicit_secret_replacement_is_persisted_but_never_echoed(self) -> None:
        sentinel = "f284-secret-replacement-sentinel"  # pragma: allowlist secret
        prompt_workbench_state.update_prompt_workbench_config(
            {
                "translation": {
                    "default_provider": "openai",
                    "providers": {
                        "openai": {
                            "api_key": "existing-secret",  # pragma: allowlist secret
                            "base_url": "https://example.test/v1",
                            "model": "gpt-4.1-mini",
                        }
                    },
                }
            }
        )
        exported = prompt_workbench_state.export_prompt_workbench_store()
        exported["data"]["config"]["translation"]["providers"]["openai"]["api_key"] = sentinel

        result = prompt_workbench_state.import_prompt_workbench_store(exported)
        stored = prompt_workbench_state.load_prompt_workbench_store()

        self.assertEqual(stored["config"]["translation"]["providers"]["openai"]["api_key"], sentinel)
        self.assertEqual(result["config"]["translation"]["providers"]["openai"]["api_key"], "********")
        self.assertNotIn(sentinel, json.dumps(result))
