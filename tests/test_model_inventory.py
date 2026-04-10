from __future__ import annotations

import types
import unittest

from rookieui.services.model_inventory import discover_model_inventory
from rookieui.services.presets import build_preset_payload


class ModelInventoryTests(unittest.TestCase):
    def test_discover_model_inventory_uses_host_folder_paths_when_available(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["dreamshaper.safetensors"],
                "clip": ["clip_l.safetensors"],
                "clip_vision": ["clip_vision_g.safetensors"],
                "controlnet": ["depth_v11.safetensors"],
                "diffusion_models": ["flux1-dev.safetensors"],
                "vae": ["vae-ft-mse.safetensors"],
                "text_encoders": ["clip_l.safetensors"],
                "embeddings": ["badhandv4.pt"],
                "loras": ["detail_tweaker.safetensors"],
                "ultralytics": ["face_yolov8m.pt"],
                "unet": ["sdxl_unet.safetensors"],
                "upscale_models": ["4x_foolhardy.pth"],
            }.get(folder_name, [])
        )

        snapshot = discover_model_inventory(folder_paths_module=module)

        self.assertEqual(snapshot.source, "host")
        self.assertEqual(snapshot.default_checkpoint, "dreamshaper.safetensors")
        self.assertEqual(snapshot.default_vae, "vae-ft-mse.safetensors")
        self.assertEqual(snapshot.default_text_encoder, "clip_l.safetensors")
        self.assertEqual(snapshot.clip, ["clip_l.safetensors"])
        self.assertEqual(snapshot.clip_vision, ["clip_vision_g.safetensors"])
        self.assertEqual(snapshot.controlnet, ["depth_v11.safetensors"])
        self.assertEqual(snapshot.diffusion_models, ["flux1-dev.safetensors"])
        self.assertEqual(snapshot.embeddings, ["badhandv4.pt"])
        self.assertEqual(snapshot.loras, ["detail_tweaker.safetensors"])
        self.assertEqual(snapshot.ultralytics, ["face_yolov8m.pt"])
        self.assertEqual(snapshot.unet, ["sdxl_unet.safetensors"])
        self.assertEqual(snapshot.upscale_models, ["4x_foolhardy.pth"])

    def test_discover_model_inventory_falls_back_without_host_module(self) -> None:
        snapshot = discover_model_inventory(folder_paths_module=None)

        self.assertIn("__host_default__", snapshot.checkpoints)
        self.assertIn("Automatic", snapshot.vae)
        self.assertIn("Automatic", snapshot.text_encoders)
        self.assertEqual(snapshot.embeddings, [])
        self.assertEqual(snapshot.loras, [])
        self.assertEqual(snapshot.diffusion_models, [])
        self.assertEqual(snapshot.upscale_models, [])

    def test_model_inventory_payload_exposes_catalog_groups(self) -> None:
        snapshot = discover_model_inventory(folder_paths_module=None)
        payload = snapshot.to_payload()

        self.assertIn("catalog", payload)
        self.assertIn("surface_groups", payload["catalog"])
        self.assertEqual(
            payload["catalog"]["primary_model_category_by_family"]["flux"],
            "diffusion_models",
        )
        self.assertIn("checkpoints", payload["catalog"]["categories"])
        self.assertIn("upscale_models", payload["catalog"]["categories"])

    def test_build_preset_payload_uses_inventory_defaults(self) -> None:
        module = types.SimpleNamespace(
            get_filename_list=lambda folder_name: {
                "checkpoints": ["realvisxl.safetensors"],
                "vae": ["Automatic"],
                "text_encoders": ["Automatic"],
            }.get(folder_name, [])
        )

        with unittest.mock.patch(
            "rookieui.services.presets.discover_model_inventory",
            return_value=discover_model_inventory(folder_paths_module=module),
        ):
            payload = build_preset_payload()

        preset_ids = [preset["id"] for preset in payload["presets"]]
        self.assertIn("sd15", preset_ids)
        self.assertEqual(payload["presets"][0]["checkpoint_name"], "realvisxl.safetensors")
