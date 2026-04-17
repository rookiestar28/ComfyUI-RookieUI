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
        self.assertTrue(payload["prompt_library"]["sections"])
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
        self.assertIn("embedding_count", payload["prompt"]["metrics"])
        self.assertIn("lora_activation_count", payload["prompt"]["metrics"])
        self.assertIn("warning_codes", payload)
