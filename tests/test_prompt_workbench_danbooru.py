from __future__ import annotations

import types
import unittest
from unittest import mock

from rookieui.contracts.prompt_workbench import (
    PROMPT_WORKBENCH_DANBOORU_ACTION_ID,
    PROMPT_WORKBENCH_DANBOORU_NODE_ALIASES,
)
from rookieui.services import prompt_workbench_danbooru as danbooru_service


class _FakeDanbooruNode:
    FUNCTION = "upsample"

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, object]:
        return {
            "required": {
                "prompt": ("STRING", {}),
                "model_name": ("STRING", {"default": "dart-v1-sft"}),
                "tag_length": ("STRING", {"default": "long"}),
                "seed": ("INT", {"default": 17}),
                "temperature": ("FLOAT", {"default": 1.1}),
                "top_k": ("INT", {"default": 20}),
                "top_p": ("FLOAT", {"default": 0.9}),
                "num_beams": ("INT", {"default": 2}),
                "model_device": ("STRING", {"default": "auto"}),
                "model_backend": ("STRING", {"default": "ONNX (Quantized)"}),
                "max_new_tokens": ("INT", {"default": 96}),
                "cfg_scale": ("FLOAT", {"default": 1.7}),
                "negative_prompt_tags": ("STRING", {"default": ""}),
                "ban_tags": ("STRING", {"default": ""}),
                "debug_logging": ("BOOLEAN", {"default": False}),
            }
        }

    def upsample(self, **kwargs: object) -> tuple[str]:
        prompt = str(kwargs.get("prompt", "")).strip()
        return (f"{prompt}, enhanced tags",)


class _FakeLegacyDanbooruNode(_FakeDanbooruNode):
    pass


class _EmptyResultNode(_FakeDanbooruNode):
    def upsample(self, **kwargs: object) -> tuple[str]:
        return ("",)


def _install_fake_nodes(**mappings: object) -> dict[str, types.SimpleNamespace]:
    return {"nodes": types.SimpleNamespace(NODE_CLASS_MAPPINGS=dict(mappings))}


class PromptWorkbenchDanbooruTests(unittest.TestCase):
    def test_host_action_payload_marks_ready_when_canonical_node_alias_exists(self) -> None:
        with mock.patch.dict("sys.modules", _install_fake_nodes(DanbooruTagsUpsampler=_FakeDanbooruNode)):
            payload = danbooru_service.build_prompt_workbench_danbooru_host_action_payload()

        self.assertEqual(payload["action_id"], PROMPT_WORKBENCH_DANBOORU_ACTION_ID)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["resolved_node_alias"], PROMPT_WORKBENCH_DANBOORU_NODE_ALIASES[0])
        self.assertEqual(payload["availability"]["status"], "ready")

    def test_host_action_payload_falls_back_to_legacy_alias(self) -> None:
        with mock.patch.dict("sys.modules", _install_fake_nodes(DanbooruTagsUpsamplerNodeRay=_FakeLegacyDanbooruNode)):
            payload = danbooru_service.build_prompt_workbench_danbooru_host_action_payload()

        self.assertTrue(payload["available"])
        self.assertEqual(payload["resolved_node_alias"], PROMPT_WORKBENCH_DANBOORU_NODE_ALIASES[1])

    def test_execute_request_rejects_missing_prompt(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires prompt text"):
            danbooru_service.execute_prompt_workbench_danbooru_request({"prompt": "  "})

    def test_execute_request_returns_final_prompt_and_generated_suffix(self) -> None:
        with mock.patch.dict("sys.modules", _install_fake_nodes(DanbooruTagsUpsampler=_FakeDanbooruNode)):
            result = danbooru_service.execute_prompt_workbench_danbooru_request(
                {
                    "prompt": "masterpiece, city skyline",
                    "negative_prompt_tags": "blurry",
                    "ban_tags": "lowres",
                }
            )

        payload = result.to_payload()
        self.assertEqual(result.host_node_alias, PROMPT_WORKBENCH_DANBOORU_NODE_ALIASES[0])
        self.assertEqual(result.final_prompt, "masterpiece, city skyline, enhanced tags")
        self.assertEqual(result.generated_suffix, "enhanced tags")
        self.assertEqual(payload["contract"]["surface"], "prompt_tools_upsample")

    def test_execute_request_raises_when_host_returns_empty_prompt(self) -> None:
        with mock.patch.dict("sys.modules", _install_fake_nodes(DanbooruTagsUpsampler=_EmptyResultNode)):
            with self.assertRaisesRegex(danbooru_service.PromptWorkbenchDanbooruExecutionError, "empty prompt text"):
                danbooru_service.execute_prompt_workbench_danbooru_request({"prompt": "masterpiece"})
