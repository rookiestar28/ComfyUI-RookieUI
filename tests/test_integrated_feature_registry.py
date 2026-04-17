from __future__ import annotations

import unittest

from rookieui.services.integrated_feature_registry import (
    INTEGRATED_FEATURE_REGISTRY_VERSION,
    build_integrated_bootstrap_route_map,
    build_integrated_feature_registry_payload,
    build_integrated_feature_validation_map,
)


class IntegratedFeatureRegistryTests(unittest.TestCase):
    def test_registry_payload_lists_expected_bootstrap_features(self) -> None:
        payload = build_integrated_feature_registry_payload()

        self.assertEqual(payload["version"], INTEGRATED_FEATURE_REGISTRY_VERSION)
        self.assertEqual(
            [entry["feature_id"] for entry in payload["features"]],
            [
                "capabilities",
                "compatibility",
                "models",
                "presets",
                "controlnet_catalog",
                "adetailer_catalog",
                "queue",
                "prompt_workbench",
                "xyz_plot",
            ],
        )

    def test_route_map_keeps_composed_controlnet_and_client_queue_surfaces(self) -> None:
        route_map = build_integrated_bootstrap_route_map()

        self.assertEqual(
            route_map["controlnetCatalog"],
            [
                "/rookieui/controlnet/model_list",
                "/rookieui/controlnet/module_list",
                "/rookieui/controlnet/control_types",
            ],
        )
        self.assertEqual(route_map["queue"], ["/rookieui/queue"])
        self.assertEqual(route_map["promptWorkbench"], ["/rookieui/prompt-tools/config"])
        self.assertEqual(route_map["xyzPlot"], ["/rookieui/xyz-plot/axes"])

    def test_validation_map_links_integrated_surfaces_to_live_smoke_modes(self) -> None:
        validation_map = build_integrated_feature_validation_map()

        self.assertEqual(validation_map["controlnet_catalog"], ["controlnet", "full-pipeline"])
        self.assertEqual(validation_map["adetailer_catalog"], ["adetailer", "full-pipeline"])
        self.assertEqual(validation_map["queue"], ["auxiliary-pipelines", "full-pipeline"])
        self.assertEqual(validation_map["prompt_workbench"], ["prompt-workbench"])
        self.assertEqual(validation_map["xyz_plot"], ["xyz-plot"])
