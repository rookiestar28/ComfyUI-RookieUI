from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rookieui.services.prompt_workbench_analysis import analyze_prompt_workbench_payload
from rookieui.services.prompt_workbench_catalog import build_prompt_workbench_catalog_payload


class PromptWorkbenchCatalogTests(unittest.TestCase):
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

    def test_catalog_payload_exposes_builtin_group_tags_library_and_extra_networks(self) -> None:
        payload = build_prompt_workbench_catalog_payload(language="en")

        self.assertEqual(payload["contract"]["surface"], "prompt_tools_catalog")
        self.assertEqual(payload["group_tags"]["source"], "builtin")
        self.assertTrue(payload["group_tags"]["groups"])
        self.assertTrue(payload["group_tags"]["groups"][0]["tag_entries"])
        self.assertTrue(payload["prompt_library"]["sections"])
        self.assertEqual(payload["tagcomplete"]["source"], "builtin")
        self.assertTrue(payload["tagcomplete"]["entries"])
        self.assertIn("catalog_highlights", payload)
        self.assertIn("embeddings", payload["extra_networks"])
        self.assertIn("loras", payload["extra_networks"])

    def test_runtime_group_tag_override_is_preferred_when_present(self) -> None:
        runtime_root = Path(self.runtime_dir.name) / "catalogs"
        runtime_root.mkdir(parents=True, exist_ok=True)
        (runtime_root / "group_tags.custom.json").write_text(
            json.dumps(
                {
                    "groups": [
                        {"id": "custom", "title": "Custom", "tags": ["heroic pose", "golden hour"]}
                    ]
                },
                ensure_ascii=True,
            ),
            encoding="utf-8",
        )

        payload = build_prompt_workbench_catalog_payload(language="en")

        self.assertEqual(payload["group_tags"]["source"], "runtime")
        self.assertEqual(payload["group_tags"]["groups"][0]["id"], "custom")
        self.assertEqual(payload["group_tags"]["groups"][0]["tag_entries"][0]["highlight"], "plain")

    def test_group_tag_payload_preserves_nested_subgroups_and_local_labels(self) -> None:
        runtime_root = Path(self.runtime_dir.name) / "catalogs"
        runtime_root.mkdir(parents=True, exist_ok=True)
        (runtime_root / "group_tags.zh-TW.json").write_text(
            json.dumps(
                {
                    "groups": [
                        {
                            "id": "facial_expression",
                            "title": "表情動作",
                            "subgroups": [
                                {
                                    "id": "eyes",
                                    "title": "眼睛",
                                    "tags": [
                                        {
                                            "tag": "looking at viewer",
                                            "label": "看向鏡頭",
                                            "local_label": "看向鏡頭",
                                            "english_label": "looking at viewer",
                                            "insert_token": "looking at viewer",
                                            "highlight": "composition",
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        payload = build_prompt_workbench_catalog_payload(language="zh-TW")

        group = payload["group_tags"]["groups"][0]
        self.assertEqual(group["id"], "facial_expression")
        self.assertEqual(group["tag_entries"][0]["label"], "看向鏡頭")
        self.assertEqual(group["tag_entries"][0]["local_label"], "看向鏡頭")
        self.assertEqual(group["tag_entries"][0]["english_label"], "looking at viewer")
        self.assertEqual(group["subgroups"][0]["id"], "eyes")
        self.assertEqual(group["subgroups"][0]["tag_entries"][0]["insert_token"], "looking at viewer")

    def test_runtime_tagcomplete_csv_is_preferred_and_normalized(self) -> None:
        runtime_root = Path(self.runtime_dir.name) / "catalogs"
        runtime_root.mkdir(parents=True, exist_ok=True)
        (runtime_root / "tagcomplete.zh-TW.csv").write_text(
            "tag,category,aliases,count,insert_token,highlight\n"
            "city skyline,composition,城市天際線|skyline city,42,city skyline,composition\n"
            "detail tweaker,lora,,7,<lora:detail_tweaker:0.8>,lora\n",
            encoding="utf-8",
        )

        payload = build_prompt_workbench_catalog_payload(language="zh-TW")

        self.assertEqual(payload["tagcomplete"]["source"], "runtime")
        self.assertEqual(payload["tagcomplete"]["entries"][0]["tag"], "city skyline")
        self.assertEqual(payload["tagcomplete"]["entries"][0]["aliases"], ["城市天際線", "skyline city"])
        self.assertEqual(payload["tagcomplete"]["entries"][0]["count"], 42)
        self.assertEqual(payload["tagcomplete"]["entries"][1]["insert_token"], "<lora:detail_tweaker:0.8>")
        self.assertEqual(payload["tagcomplete"]["entries"][1]["highlight"], "lora")

    def test_catalog_language_query_normalizes_alias_before_lookup(self) -> None:
        payload = build_prompt_workbench_catalog_payload(language="zh_TW")

        self.assertEqual(payload["group_tags"]["language"], "zh-TW")
        self.assertEqual(payload["tagcomplete"]["language"], "zh-TW")

        fallback_payload = build_prompt_workbench_catalog_payload(language="not/a-language")
        self.assertEqual(fallback_payload["group_tags"]["language"], "en")
        self.assertEqual(fallback_payload["tagcomplete"]["language"], "en")

    def test_analyze_payload_reuses_prompt_semantics_and_inventory_metrics(self) -> None:
        payload = analyze_prompt_workbench_payload(
            {
                "prompt": "portrait <lora:detail_tweaker.safetensors:0.8> AND embedding:badhandv4.pt [day:night:0.5]",
                "negative_prompt": "low quality, blurry",
                "steps": 30,
            }
        )

        self.assertEqual(payload["contract"]["surface"], "prompt_tools_analyze")
        self.assertEqual(payload["analysis_mode"], "syntax_inventory")
        self.assertIn("prompt_scheduling", payload["prompt"]["semantics"]["features"])
        self.assertEqual(payload["prompt"]["metrics"]["mode"], "syntax_inventory_estimate")
        self.assertTrue(payload["prompt"]["tokens"])
        self.assertIn("raw_text", payload["prompt"]["tokens"][0])
        self.assertEqual(payload["negative_prompt"]["tokens"][0]["raw_text"], "low quality")
        self.assertEqual(payload["negative_prompt"]["tokens"][0]["scope"], "negative")
        self.assertIn("embedding_count", payload["prompt"]["metrics"])
        self.assertIn("lora_activation_count", payload["prompt"]["metrics"])
        self.assertIn("warning_codes", payload)
