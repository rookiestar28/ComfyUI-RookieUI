from __future__ import annotations

import types
import unittest
from unittest import mock

from rookieui.services import controlnet_runtime as runtime


class _FakeAioDepth:
    @staticmethod
    def INPUT_TYPES() -> dict[str, object]:
        return {
            "required": {"image": ("IMAGE",)},
            "optional": {
                "preprocessor": (
                    ["none", "depth_anything_v2", "depth_midas"],
                    {"default": "none"},
                ),
                "resolution": ("INT", {"default": 512}),
            },
        }


class _FakeAioSoftEdge:
    @staticmethod
    def INPUT_TYPES() -> dict[str, object]:
        return {
            "required": {"image": ("IMAGE",)},
            "optional": {
                "preprocessor": (
                    ["none", "hed_safe", "lineart_standard"],
                    {"default": "none"},
                ),
                "resolution": ("INT", {"default": 512}),
            },
        }


class _FakeDictResultNode:
    FUNCTION = "execute"

    @staticmethod
    def INPUT_TYPES() -> dict[str, object]:
        return {
            "required": {"image": ("IMAGE",)},
            "optional": {},
        }

    def execute(self, image: object) -> dict[str, object]:
        return {"result": (image,)}


class ControlNetRuntimeHeuristicsTests(unittest.TestCase):
    def test_normalize_preprocessor_option_key_preserves_lineart_variant(self) -> None:
        normalized = runtime.normalize_preprocessor_option_key("lineart_anime_denoise")
        self.assertEqual(normalized, "lineart_anime_denoise")

    def test_normalize_module_key_collapses_lineart_variant_to_base_module(self) -> None:
        normalized = runtime.normalize_module_key("lineart_anime_denoise")
        self.assertEqual(normalized, "lineart")

    def test_select_aio_preprocessor_name_matches_normalized_explicit_candidates(self) -> None:
        selected = runtime._select_aio_preprocessor_name(_FakeAioDepth, "depth")
        self.assertEqual(selected, "depth_anything_v2")

    def test_select_aio_preprocessor_name_uses_keyword_ranking_when_explicit_candidates_miss(self) -> None:
        selected = runtime._select_aio_preprocessor_name(_FakeAioSoftEdge, "softedge")
        self.assertEqual(selected, "hed_safe")

    def test_extract_primary_node_output_payload_supports_result_dict(self) -> None:
        marker = object()
        payload = runtime._extract_primary_node_output_payload({"result": (marker,)})
        self.assertIs(payload, marker)

    def test_run_host_node_preprocessor_accepts_result_dict_payload(self) -> None:
        marker = object()
        with mock.patch.object(runtime, "_coerce_image_tensor", side_effect=lambda value: value):
            output = runtime._run_host_node_preprocessor(
                node_name="DepthAnythingV2Preprocessor",
                node_cls=_FakeDictResultNode,
                image_tensor=marker,
                mask_tensor=None,
                module_key="depth",
                processor_res=512,
                threshold_a=64.0,
                threshold_b=64.0,
                aio_preprocessor_name=None,
            )
        self.assertIs(output, marker)

    def test_discover_dynamic_host_preprocessors_skips_heavy_depth_candidates(self) -> None:
        discovered = runtime._discover_dynamic_host_preprocessors(
            "depth",
            {
                "DepthAnythingV2Preprocessor": object(),
                "Metric3D-DepthMapPreprocessor": object(),
                "MeshGraphormer-DepthMapPreprocessor": object(),
            },
        )
        self.assertIn("DepthAnythingV2Preprocessor", discovered)
        self.assertNotIn("Metric3D-DepthMapPreprocessor", discovered)
        self.assertNotIn("MeshGraphormer-DepthMapPreprocessor", discovered)

    def test_resolve_host_preprocessor_candidates_prioritizes_depthanything_first(self) -> None:
        resolved = runtime._resolve_host_preprocessor_candidates(
            "depth",
            {
                "MiDaS-DepthMapPreprocessor": object(),
                "DepthAnythingV2Preprocessor": object(),
                "LeReS-DepthMapPreprocessor": object(),
            },
        )
        self.assertGreaterEqual(len(resolved), 2)
        self.assertEqual(resolved[0], "DepthAnythingV2Preprocessor")

    def test_resolve_host_preprocessor_candidates_honors_variant_preferred_order(self) -> None:
        resolved = runtime._resolve_host_preprocessor_candidates(
            "lineart",
            {
                "LineArtPreprocessor": object(),
                "LineartStandardPreprocessor": object(),
                "AnimeLineArtPreprocessor": object(),
            },
            preferred_candidates=("LineartStandardPreprocessor",),
        )
        self.assertGreaterEqual(len(resolved), 2)
        self.assertEqual(resolved[0], "LineartStandardPreprocessor")

    def test_preprocess_controlnet_non_depth_stops_after_global_probe_limit(self) -> None:
        marker = object()
        with mock.patch.object(runtime, "_require_runtime_dependencies", return_value=None):
            with mock.patch.object(runtime, "_coerce_image_tensor", return_value=marker):
                with mock.patch.object(
                    runtime,
                    "_resolve_host_node_class_mappings",
                    return_value={
                        "CannyEdgePreprocessor": object(),
                        "PyraCannyPreprocessor": object(),
                    },
                ):
                    with mock.patch.object(runtime, "_apply_fallback_filters", return_value=marker):
                        with mock.patch.object(
                            runtime,
                            "_run_host_node_preprocessor",
                            side_effect=RuntimeError("CannyEdgePreprocessor failed"),
                        ) as run_mock:
                            result = runtime.preprocess_controlnet_tensor(
                                image_tensor=marker,
                                module="canny",
                                processor_res=512,
                                threshold_a=64.0,
                                threshold_b=64.0,
                                mask_tensor=None,
                            )

        self.assertTrue(result.used_fallback)
        self.assertEqual(result.backend, "rookieui_internal_fallback")
        self.assertEqual(run_mock.call_count, 1)
        self.assertTrue(any("host_probe_limit_reached:1" in entry for entry in result.diagnostics))

    def test_preprocess_controlnet_skips_aio_fallback_when_disabled(self) -> None:
        marker = object()
        with mock.patch.object(runtime, "_require_runtime_dependencies", return_value=None):
            with mock.patch.object(runtime, "_coerce_image_tensor", return_value=marker):
                with mock.patch.object(runtime, "_resolve_host_node_class_mappings", return_value={"AIO_Preprocessor": object()}):
                    with mock.patch.object(runtime, "_apply_fallback_filters", return_value=marker):
                        with mock.patch.object(runtime, "_run_host_node_preprocessor") as run_mock:
                            result = runtime.preprocess_controlnet_tensor(
                                image_tensor=marker,
                                module="softedge",
                                processor_res=512,
                                threshold_a=64.0,
                                threshold_b=64.0,
                                mask_tensor=None,
                            )

        self.assertEqual(result.backend, "rookieui_internal_fallback")
        self.assertTrue(result.used_fallback)
        self.assertIn("aio_preprocessor_disabled", result.diagnostics)
        run_mock.assert_not_called()

    def test_preprocess_controlnet_allows_aio_when_explicitly_enabled(self) -> None:
        marker = object()
        with mock.patch.dict("os.environ", {runtime.ROOKIEUI_CONTROLNET_AIO_PREPROCESSOR_ENABLED_ENV: "1"}, clear=False):
            with mock.patch.object(runtime, "_require_runtime_dependencies", return_value=None):
                with mock.patch.object(runtime, "_coerce_image_tensor", return_value=marker):
                    with mock.patch.object(
                        runtime,
                        "_resolve_host_node_class_mappings",
                        return_value={"AIO_Preprocessor": object()},
                    ):
                        with mock.patch.object(runtime, "_resolve_host_preprocessor_candidates", return_value=()):
                            with mock.patch.object(runtime, "_select_aio_preprocessor_name", return_value="hed_safe"):
                                with mock.patch.object(runtime, "_is_visually_empty_image_tensor", return_value=False):
                                    with mock.patch.object(runtime, "_run_host_node_preprocessor", return_value=marker) as run_mock:
                                        result = runtime.preprocess_controlnet_tensor(
                                            image_tensor=marker,
                                            module="softedge",
                                            processor_res=512,
                                            threshold_a=64.0,
                                            threshold_b=64.0,
                                            mask_tensor=None,
                                        )

        self.assertEqual(result.backend, "comfy_host_preprocessor_aio")
        self.assertEqual(result.processor_name, "hed_safe")
        run_mock.assert_called_once()

    def test_preprocess_controlnet_applies_prompt_server_last_prompt_id_shim_for_host_node(self) -> None:
        marker = object()
        fake_prompt_server_instance = types.SimpleNamespace()

        def _host_runner(**_kwargs: object) -> object:
            if not hasattr(fake_prompt_server_instance, "last_prompt_id"):
                raise RuntimeError("missing_last_prompt_id")
            return marker

        with mock.patch.object(runtime, "_require_runtime_dependencies", return_value=None):
            with mock.patch.object(runtime, "_coerce_image_tensor", return_value=marker):
                with mock.patch.object(
                    runtime,
                    "_resolve_host_node_class_mappings",
                    return_value={"DepthAnythingV2Preprocessor": object()},
                ):
                    with mock.patch.object(runtime, "_resolve_prompt_server_instance", return_value=fake_prompt_server_instance):
                        with mock.patch.object(runtime, "_is_visually_empty_image_tensor", return_value=False):
                            with mock.patch.object(runtime, "_run_host_node_preprocessor", side_effect=_host_runner):
                                result = runtime.preprocess_controlnet_tensor(
                                    image_tensor=marker,
                                    module="depth",
                                    processor_res=512,
                                    threshold_a=64.0,
                                    threshold_b=64.0,
                                    mask_tensor=None,
                                )

        self.assertEqual(result.backend, "comfy_host_preprocessor")
        self.assertEqual(result.processor_name, "DepthAnythingV2Preprocessor")
        self.assertIn("prompt_server_last_prompt_id_shim_applied", result.diagnostics)
        self.assertFalse(hasattr(fake_prompt_server_instance, "last_prompt_id"))

    def test_prompt_server_last_prompt_id_shim_uses_refcounted_lifecycle(self) -> None:
        fake_prompt_server_instance = types.SimpleNamespace()

        with mock.patch.object(runtime, "_PROMPT_SERVER_SHIM_REFCOUNTS", {}):
            with mock.patch.object(runtime, "_PROMPT_SERVER_SHIM_VALUES", {}):
                applied_a, value_a = runtime._ensure_prompt_server_last_prompt_id(fake_prompt_server_instance)
                applied_b, value_b = runtime._ensure_prompt_server_last_prompt_id(fake_prompt_server_instance)

                self.assertTrue(applied_a)
                self.assertTrue(applied_b)
                self.assertEqual(value_a, value_b)
                self.assertEqual(getattr(fake_prompt_server_instance, "last_prompt_id"), value_a)

                runtime._restore_prompt_server_last_prompt_id(fake_prompt_server_instance, applied_a, value_a)
                self.assertEqual(getattr(fake_prompt_server_instance, "last_prompt_id"), value_a)

                runtime._restore_prompt_server_last_prompt_id(fake_prompt_server_instance, applied_b, value_b)
                self.assertFalse(hasattr(fake_prompt_server_instance, "last_prompt_id"))

    def test_preprocess_controlnet_marks_host_success_with_near_empty_output_diagnostic(self) -> None:
        marker = object()
        with mock.patch.object(runtime, "_require_runtime_dependencies", return_value=None):
            with mock.patch.object(runtime, "_coerce_image_tensor", return_value=marker):
                with mock.patch.object(
                    runtime,
                    "_resolve_host_node_class_mappings",
                    return_value={"OpenposePreprocessor": object()},
                ):
                    with mock.patch.object(runtime, "_run_host_node_preprocessor", return_value=marker):
                        with mock.patch.object(runtime, "_is_visually_empty_image_tensor", return_value=True):
                            result = runtime.preprocess_controlnet_tensor(
                                image_tensor=marker,
                                module="openpose",
                                processor_res=512,
                                threshold_a=64.0,
                                threshold_b=64.0,
                                mask_tensor=None,
                            )

        self.assertEqual(result.backend, "comfy_host_preprocessor")
        self.assertEqual(result.processor_name, "OpenposePreprocessor")
        self.assertIn("OpenposePreprocessor:output_near_empty", result.diagnostics)

    @unittest.skipUnless(runtime.torch is not None, "torch is unavailable in this environment")
    def test_coerce_image_tensor_min_max_normalizes_signed_ranges(self) -> None:
        tensor = runtime.torch.tensor(
            [
                [
                    [[-1.0, 0.0, 1.0], [0.5, 0.0, -0.5]],
                    [[1.0, -1.0, 0.25], [0.0, 0.0, 0.0]],
                ]
            ],
            dtype=runtime.torch.float32,
        )
        normalized = runtime._coerce_image_tensor(tensor)
        self.assertGreaterEqual(float(normalized.min().item()), 0.0)
        self.assertLessEqual(float(normalized.max().item()), 1.0)

    @unittest.skipUnless(runtime.torch is not None, "torch is unavailable in this environment")
    def test_normalize_image_value_range_divides_integer_uint8_like_values(self) -> None:
        tensor = runtime.torch.tensor([[[[0.0, 64.0, 255.0]]]], dtype=runtime.torch.float32)

        normalized = runtime._normalize_image_value_range(tensor)

        self.assertAlmostEqual(float(normalized[0, 0, 0, 1].item()), 64.0 / 255.0, places=5)
        self.assertAlmostEqual(float(normalized.max().item()), 1.0, places=5)

    @unittest.skipUnless(runtime.torch is not None, "torch is unavailable in this environment")
    def test_normalize_image_value_range_min_max_normalizes_fractional_low_range(self) -> None:
        tensor = runtime.torch.tensor([[[[0.0, 0.5, 2.0], [1.5, 0.25, 1.0]]]], dtype=runtime.torch.float32)

        normalized = runtime._normalize_image_value_range(tensor)

        self.assertAlmostEqual(float(normalized.min().item()), 0.0, places=5)
        self.assertAlmostEqual(float(normalized.max().item()), 1.0, places=5)
        self.assertGreater(float(normalized[0, 0, 0, 1].item()), 0.2)

    @unittest.skipUnless(runtime.torch is not None, "torch is unavailable in this environment")
    def test_coerce_image_tensor_promotes_alpha_only_rgba_to_visible_rgb(self) -> None:
        tensor = runtime.torch.zeros((1, 2, 2, 4), dtype=runtime.torch.float32)
        tensor[:, :, :, 3] = 1.0
        normalized = runtime._coerce_image_tensor(tensor)
        self.assertGreater(float(normalized.max().item()), 0.0)
        self.assertEqual(normalized.shape[-1], 3)
