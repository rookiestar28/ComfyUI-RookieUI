from __future__ import annotations

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
                            "api_key": "sk-live-secret",
                            "endpoint": "https://example.test",
                        }
                    },
                }
            }
        )

        payload = prompt_workbench_state.get_prompt_workbench_bootstrap_payload()

        self.assertEqual(payload["config"]["translation"]["providers"]["openai"]["api_key"], "********")
        self.assertEqual(
            payload["config"]["translation"]["providers"]["openai"]["endpoint"],
            "https://example.test",
        )

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

    def test_blacklist_update_normalizes_entries(self) -> None:
        updated = prompt_workbench_state.update_prompt_workbench_blacklist(
            {
                "enabled": True,
                "entries": ["bad-hands", "  blurry  ", "", 123],
            }
        )

        self.assertTrue(updated["enabled"])
        self.assertEqual(updated["entries"], ["bad-hands", "blurry"])
