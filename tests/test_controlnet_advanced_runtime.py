from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

from rookieui import nodes
from rookieui.services import controlnet_advanced_runtime
from rookieui.services.controlnet_advanced_runtime import (
    CONTROLNET_ADVANCED_RUNTIME_STATE,
    build_controlnet_apply_segments,
    build_controlnet_stage_weights,
    stage_weights_require_wrapper,
)
from rookieui.services.controlnet_mask_runtime import (
    apply_effect_mask_to_control,
    normalize_effect_mask,
    prepare_concat_mask,
)


class _HostControlBaseDouble:
    """Deterministic current-host lifecycle double; never loads a real model."""

    def __init__(self, *, name: str = "control", device: str = "cpu") -> None:
        self.name = name
        self.device = device
        self.previous_controlnet = None
        self.multigpu_clones = {}
        self.cond_hint_original = None
        self.cond_hint = None
        self.strength = 1.0
        self.timestep_percent_range = (0.0, 1.0)
        self.timestep_range = None
        self.latent_format = None
        self.global_average_pooling = False
        self.compression_ratio = 8
        self.upscale_algorithm = "nearest-exact"
        self.extra_args = {}
        self.extra_conds = []
        self.strength_type = None
        self.concat_mask = False
        self.extra_concat_orig = []
        self.extra_concat = None
        self.extra_hooks = f"hook:{name}:{device}"
        self.events: list[str] = []
        self.deepclone_requests: list[tuple[str, bool]] = []
        self.raise_on_get_control = False
        self.control_payload = {"input": [2.0], "middle": [3.0], "output": [4.0]}

    def deepclone_multigpu(self, _load_device, autoregister=False):
        _ = autoregister
        raise NotImplementedError("deepclone_multigpu is abstract on the host base")

    def copy_to(self, target):
        target.cond_hint_original = self.cond_hint_original
        target.strength = self.strength
        target.timestep_percent_range = self.timestep_percent_range
        target.latent_format = self.latent_format
        target.global_average_pooling = self.global_average_pooling
        target.compression_ratio = self.compression_ratio
        target.upscale_algorithm = self.upscale_algorithm
        target.extra_args = self.extra_args.copy()
        target.extra_conds = list(self.extra_conds)
        target.strength_type = self.strength_type
        target.concat_mask = self.concat_mask
        target.extra_concat_orig = list(self.extra_concat_orig)
        target.extra_hooks = self.extra_hooks

    def set_cond_hint(self, cond_hint, strength=1.0, timestep_percent_range=(0.0, 1.0), vae=None, extra_concat=None):
        _ = vae
        self.cond_hint_original = cond_hint
        self.strength = strength
        self.timestep_percent_range = timestep_percent_range
        self.extra_concat_orig = list(extra_concat or [])
        return self

    def pre_run(self, _model, percent_to_timestep_function):
        self.events.append("pre_run")
        self.timestep_range = tuple(
            percent_to_timestep_function(value) for value in self.timestep_percent_range
        )

    def cleanup(self):
        self.events.append("cleanup")
        self.cond_hint = None
        self.extra_concat = None
        self.timestep_range = None

    def get_models(self):
        self.events.append("get_models")
        models = [f"model:{self.name}:{self.device}"]
        for clone in self.multigpu_clones.values():
            models.extend(clone.get_models_only_self())
        return models

    def get_models_only_self(self):
        previous = self.previous_controlnet
        self.previous_controlnet = None
        try:
            return self.get_models()
        finally:
            self.previous_controlnet = previous

    def get_extra_hooks(self):
        self.events.append("get_extra_hooks")
        return [self.extra_hooks]

    def inference_memory_requirements(self, _dtype):
        self.events.append("memory")
        return 7

    def control_merge(self, control, control_prev, output_dtype=None):
        _ = output_dtype
        if control_prev is None:
            return control
        merged = {}
        for key in ("input", "middle", "output"):
            merged[key] = list(control.get(key, [])) + list(control_prev.get(key, []))
        return merged


class _ConcreteControlDouble(_HostControlBaseDouble):
    def copy(self):
        clone = type(self)(name=f"{self.name}.copy", device=self.device)
        self.copy_to(clone)
        clone.control_payload = {key: list(values) for key, values in self.control_payload.items()}
        clone.raise_on_get_control = self.raise_on_get_control
        return clone

    def deepclone_multigpu(self, load_device, autoregister=False):
        self.deepclone_requests.append((str(load_device), bool(autoregister)))
        clone = self.copy()
        clone.name = f"{self.name}.clone"
        clone.device = str(load_device)
        if autoregister:
            self.multigpu_clones[load_device] = clone
        return clone

    def cleanup(self):
        for clone in list(self.multigpu_clones.values()):
            clone.cleanup()
        super().cleanup()

    def get_control(self, *_args):
        self.events.append("get_control")
        if self.raise_on_get_control:
            raise RuntimeError("injected control failure")
        return {
            key: [value * float(self.strength) for value in values]
            for key, values in self.control_payload.items()
        }


def _wrapper_probe_type():
    # Rebuild the private wrapper against the deterministic host base so tests
    # exercise the same inheritance seam without importing reference code.
    controlnet_module = types.ModuleType("comfy.controlnet")
    controlnet_module.ControlBase = _HostControlBaseDouble
    cli_args_module = types.ModuleType("comfy.cli_args")
    cli_args_module.args = types.SimpleNamespace(disable_metadata=False)
    model_management_module = types.ModuleType("comfy.model_management")
    comfy_module = types.ModuleType("comfy")
    comfy_module.__path__ = []
    comfy_module.model_management = model_management_module
    module_name = "rookieui._nodes_wrapper_probe"
    spec = importlib.util.spec_from_file_location(module_name, Path(nodes.__file__))
    if spec is None or spec.loader is None:
        raise RuntimeError("test could not load the local nodes module.")
    probe_module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(
        sys.modules,
        {
            "comfy": comfy_module,
            "comfy.controlnet": controlnet_module,
            "comfy.cli_args": cli_args_module,
            "comfy.model_management": model_management_module,
        },
    ):
        spec.loader.exec_module(probe_module)
    return probe_module._RookieUIStageWeightedControlNet


def _wrapper_probe(*, weight_preset="soft", layer_weights=None, effect_mask=None):
    wrapper_type = _wrapper_probe_type()
    return wrapper_type(
        _ConcreteControlDouble(),
        weight_preset=weight_preset,
        layer_weights=list(layer_weights or [0.5]),
        effect_mask=effect_mask,
    )


class ControlNetAdvancedRuntimeTests(unittest.TestCase):
    def test_control_mode_profiles_are_distinct_and_advanced_precedence_is_fail_closed(self) -> None:
        self.assertEqual(
            controlnet_advanced_runtime.resolve_controlnet_stage_profile(
                control_mode="balanced",
                advanced={"enabled": False, "weight_preset": "strong", "layer_weights": [0.2, 0.4]},
            ),
            {"weight_preset": "balanced", "layer_weights": [], "apply_to_negative": True},
        )
        self.assertEqual(
            controlnet_advanced_runtime.resolve_controlnet_stage_profile(
                control_mode="prompt",
                advanced={"enabled": False, "weight_preset": "strong", "layer_weights": [0.2, 0.4]},
            ),
            {"weight_preset": "soft", "layer_weights": [], "apply_to_negative": True},
        )
        self.assertEqual(
            controlnet_advanced_runtime.resolve_controlnet_stage_profile(
                control_mode="control",
                advanced={"enabled": False, "weight_preset": "strong", "layer_weights": [0.2, 0.4]},
            ),
            {"weight_preset": "soft", "layer_weights": [], "apply_to_negative": False},
        )
        self.assertEqual(
            controlnet_advanced_runtime.resolve_controlnet_stage_profile(
                control_mode="control",
                advanced={"enabled": True, "weight_preset": "strong", "layer_weights": [0.2, 0.4]},
            ),
            {"weight_preset": "strong", "layer_weights": [0.2, 0.4], "apply_to_negative": False},
        )

    def test_stage_weight_wrapper_current_host_multigpu_clone_is_registered_after_repair(self) -> None:
        wrapper = _wrapper_probe()

        clone = wrapper.deepclone_multigpu("cuda:1", autoregister=True)

        self.assertIs(wrapper.get_instance_for_device("cuda:1"), clone)

    def test_stage_weight_wrapper_implements_current_host_clone_protocol(self) -> None:
        wrapper = _wrapper_probe(layer_weights=[0.5, 0.75])

        clone = wrapper.deepclone_multigpu("cuda:1", autoregister=True)

        self.assertIsNot(clone, wrapper)
        self.assertIsNot(clone.base_control, wrapper.base_control)
        self.assertEqual(clone.base_control.device, "cuda:1")
        self.assertIs(wrapper.get_instance_for_device("cuda:1"), clone)
        self.assertIs(wrapper.get_instance_for_device("cuda:2"), wrapper)
        self.assertEqual(wrapper.base_control.deepclone_requests, [("cuda:1", False)])
        self.assertEqual(clone.multigpu_clones, {})
        self.assertEqual(clone.layer_weights, (0.5, 0.75))
        self.assertIsInstance(clone.layer_weights, tuple)
        clone.layer_weights += (0.9,)
        self.assertEqual(wrapper.layer_weights, (0.5, 0.75))

        unregistered = wrapper.deepclone_multigpu("cuda:2", autoregister=False)
        self.assertEqual(unregistered.base_control.device, "cuda:2")
        self.assertNotIn("cuda:2", wrapper.multigpu_clones)

    def test_stage_weight_wrapper_lifecycle_enumerates_owned_objects_once(self) -> None:
        wrapper = _wrapper_probe()
        previous = _ConcreteControlDouble(name="previous")
        wrapper.set_previous_controlnet(previous)
        clone = wrapper.deepclone_multigpu("cuda:1", autoregister=True)
        previous_clone = previous.deepclone_multigpu("cuda:1", autoregister=True)
        clone.set_previous_controlnet(previous_clone)

        models = wrapper.get_models()
        self.assertEqual(
            models,
            [
                "model:control.clone:cuda:1",
                "model:control:cpu",
                "model:previous:cpu",
                "model:previous.clone:cuda:1",
            ],
        )
        self.assertEqual(wrapper.get_models_only_self(), ["model:control.clone:cuda:1", "model:control:cpu"])

        wrapper.pre_run(object(), lambda percent: percent + 10.0)
        self.assertEqual(wrapper.base_control.events.count("pre_run"), 1)
        self.assertEqual(previous.events.count("pre_run"), 1)
        self.assertEqual(wrapper.get_extra_hooks(), ["hook:control:cpu", "hook:previous:cpu"])
        self.assertEqual(wrapper.inference_memory_requirements(None), 14)

        wrapper.cleanup()
        self.assertEqual(wrapper.base_control.events.count("cleanup"), 1)
        self.assertEqual(clone.base_control.events.count("cleanup"), 1)
        self.assertEqual(previous.events.count("cleanup"), 1)
        self.assertEqual(previous_clone.events.count("cleanup"), 1)

    def test_stage_weight_wrapper_restores_wrapped_previous_control_on_success_and_failure(self) -> None:
        wrapper = _wrapper_probe(layer_weights=[0.5, 0.5, 0.5])
        sentinel = _ConcreteControlDouble(name="wrapped-previous")
        wrapper.base_control.previous_controlnet = sentinel

        result = wrapper.get_control(None, None, {}, 1, {})
        self.assertEqual(result["input"], [1.0])
        self.assertIs(wrapper.base_control.previous_controlnet, sentinel)

        wrapper.base_control.raise_on_get_control = True
        with self.assertRaisesRegex(RuntimeError, "injected control failure"):
            wrapper.get_control(None, None, {}, 1, {})
        self.assertIs(wrapper.base_control.previous_controlnet, sentinel)

    def test_stage_weight_wrapper_preserves_single_device_strength_and_previous_chain_output(self) -> None:
        wrapper = _wrapper_probe(weight_preset="balanced", layer_weights=[0.5, 0.5, 0.5])
        wrapper.set_cond_hint(None, strength=0.5)
        previous = _ConcreteControlDouble(name="previous")
        previous.control_payload = {"input": [10.0], "middle": [20.0], "output": [30.0]}
        wrapper.set_previous_controlnet(previous)

        result = wrapper.get_control(None, None, {}, 1, {})

        self.assertEqual(result["input"], [0.5, 10.0])
        self.assertEqual(result["middle"], [0.75, 20.0])
        self.assertEqual(result["output"], [1.0, 30.0])
        self.assertEqual(wrapper.base_control.events.count("get_control"), 1)
        self.assertEqual(previous.events.count("get_control"), 1)

    def test_build_controlnet_apply_segments_returns_base_segment_when_advanced_disabled(self) -> None:
        segments = build_controlnet_apply_segments(
            weight=0.8,
            guidance_start=0.1,
            guidance_end=0.9,
            advanced={"enabled": False},
        )

        self.assertEqual(
            segments,
            [
                {
                    "strength": 0.8,
                    "start_percent": 0.1,
                    "end_percent": 0.9,
                }
            ],
        )

    def test_build_controlnet_apply_segments_intersects_keyframes_with_guidance_range(self) -> None:
        segments = build_controlnet_apply_segments(
            weight=0.75,
            guidance_start=0.1,
            guidance_end=0.9,
            advanced={
                "enabled": True,
                "timestep_keyframes": [
                    {"start_percent": 0.0, "end_percent": 0.5, "strength_scale": 0.5},
                    {"start_percent": 0.5, "end_percent": 1.0, "strength_scale": 1.25},
                ],
            },
        )

        self.assertEqual(
            segments,
            [
                {"strength": 0.375, "start_percent": 0.1, "end_percent": 0.5},
                {"strength": 0.9375, "start_percent": 0.5, "end_percent": 0.9},
            ],
        )

    def test_build_controlnet_apply_segments_rolls_back_to_base_segment_when_keyframes_collapse(self) -> None:
        segments = build_controlnet_apply_segments(
            weight=0.55,
            guidance_start=0.2,
            guidance_end=0.7,
            advanced={
                "enabled": True,
                "timestep_keyframes": [
                    {"start_percent": 0.0, "end_percent": 0.1, "strength_scale": 1.0},
                    {"start_percent": 0.9, "end_percent": 1.0, "strength_scale": 0.0},
                ],
            },
        )

        self.assertEqual(
            segments,
            [
                {
                    "strength": 0.55,
                    "start_percent": 0.2,
                    "end_percent": 0.7,
                }
            ],
        )

    def test_build_controlnet_stage_weights_uses_preset_and_explicit_overrides(self) -> None:
        stage_weights = build_controlnet_stage_weights(
            input_count=2,
            middle_count=1,
            output_count=3,
            weight_preset="soft",
            layer_weights=[0.2, 0.4],
        )

        self.assertEqual(stage_weights["output"][:2], [0.2, 0.4])
        self.assertEqual(len(stage_weights["output"]), 3)
        self.assertEqual(len(stage_weights["middle"]), 1)
        self.assertEqual(len(stage_weights["input"]), 2)
        self.assertTrue(stage_weights_require_wrapper(stage_weights))

    def test_runtime_state_constant_is_native(self) -> None:
        self.assertEqual(CONTROLNET_ADVANCED_RUNTIME_STATE, "rookieui_native_advanced_runtime")

    @unittest.skipUnless(nodes.torch is not None, "torch is required for tensor mask semantics")
    def test_effect_mask_scales_only_new_outputs_before_previous_chain_merge(self) -> None:
        torch = nodes.torch
        effect_mask = torch.tensor([[[1.0, 0.0], [0.0, 1.0]]], dtype=torch.float32)
        wrapper = _wrapper_probe(weight_preset="balanced", layer_weights=[1.0], effect_mask=effect_mask)
        wrapper.set_cond_hint(None, strength=1.0)
        wrapper.base_control.control_payload = {
            "input": [torch.ones((1, 1, 2, 2), dtype=torch.float32)],
            "middle": [],
            "output": [],
        }
        previous = _ConcreteControlDouble(name="previous")
        previous.control_payload = {
            "input": [torch.full((1, 1, 2, 2), 7.0, dtype=torch.float32)],
            "middle": [],
            "output": [],
        }
        wrapper.set_previous_controlnet(previous)

        result = wrapper.get_control(None, None, {}, 1, {})

        self.assertEqual(len(result["input"]), 2)
        self.assertTrue(torch.equal(result["input"][0], torch.tensor([[[[1.0, 0.0], [0.0, 1.0]]]])))
        self.assertTrue(torch.equal(result["input"][1], torch.full((1, 1, 2, 2), 7.0)))
        self.assertTrue(torch.equal(previous.control_payload["input"][0], torch.full((1, 1, 2, 2), 7.0)))

    @unittest.skipUnless(nodes.torch is not None, "torch is required for tensor mask semantics")
    def test_all_zero_effect_mask_is_apply_identity_before_conditioning_mutation(self) -> None:
        torch = nodes.torch
        positive = [["positive", {"prompt": "keep"}]]
        negative = [["negative", {"prompt": "keep"}]]
        image = torch.zeros((1, 2, 2, 3), dtype=torch.float32)
        node = nodes.RookieUIControlNetApplyNativeAdvanced()
        with mock.patch.object(node, "_require_controlnet_runtime"):
            result = node.apply_controlnet(
                positive,
                negative,
                None,
                image,
                1.0,
                0.0,
                1.0,
                mask_aware_apply=True,
                mask_optional=torch.zeros((1, 2, 2), dtype=torch.float32),
            )

        self.assertIs(result[0], positive)
        self.assertIs(result[1], negative)
        self.assertNotIn("mask", positive[0][1])

    @unittest.skipUnless(nodes.torch is not None, "torch is required for tensor mask semantics")
    def test_concat_mask_prepares_real_extra_concat_and_zeroes_masked_source_pixels(self) -> None:
        torch = nodes.torch
        image = torch.ones((1, 4, 4, 3), dtype=torch.float32)
        source_mask = torch.tensor([[[0.0, 1.0], [1.0, 0.0]]], dtype=torch.float32)

        masked_image, extra_concat = prepare_concat_mask(image, source_mask)

        self.assertEqual(tuple(extra_concat[0].shape), (1, 1, 2, 2))
        self.assertTrue(torch.equal(extra_concat[0], torch.tensor([[[[1.0, 0.0], [0.0, 1.0]]]])))
        self.assertEqual(tuple(masked_image.shape), (1, 4, 4, 3))
        self.assertEqual(float(masked_image.min().item()), 0.0)
        self.assertEqual(float(masked_image.max().item()), 1.0)

    @unittest.skipUnless(nodes.torch is not None, "torch is required for tensor mask semantics")
    def test_apply_passes_real_concat_mask_to_native_control_lifecycle(self) -> None:
        torch = nodes.torch
        control_net = _ConcreteControlDouble()
        control_net.concat_mask = True
        image = torch.ones((1, 4, 4, 3), dtype=torch.float32)
        source_mask = torch.tensor([[[0.0, 1.0], [1.0, 0.0]]], dtype=torch.float32)
        positive = [["positive", {}]]
        negative = [["negative", {}]]
        node = nodes.RookieUIControlNetApplyNativeAdvanced()
        with mock.patch.object(node, "_require_controlnet_runtime"):
            result = node.apply_controlnet(
                positive,
                negative,
                control_net,
                image,
                1.0,
                0.0,
                1.0,
                inpaint_mask_optional=source_mask,
                vae_optional=object(),
            )

        applied_control = result[0][0][1]["control"]
        self.assertEqual(len(applied_control.extra_concat_orig), 1)
        self.assertTrue(torch.equal(applied_control.extra_concat_orig[0], torch.tensor([[[[1.0, 0.0], [0.0, 1.0]]]])))
        self.assertTrue(torch.equal(applied_control.cond_hint_original[:, :, 0, 2], torch.zeros((1, 1))))

    @unittest.skipUnless(nodes.torch is not None, "torch is required for tensor mask semantics")
    def test_mask_shapes_are_strict_and_single_batch_broadcasts(self) -> None:
        torch = nodes.torch
        normalized = normalize_effect_mask(torch.ones((1, 2, 2), dtype=torch.float32), batch_size=2)
        self.assertEqual(tuple(normalized.shape), (2, 2, 2))
        with self.assertRaisesRegex(ValueError, "shape \[B,H,W\] or \[B,1,H,W\]"):
            normalize_effect_mask(torch.ones((1, 1, 2, 2, 1), dtype=torch.float32))
        with self.assertRaisesRegex(ValueError, "single-channel"):
            normalize_effect_mask(torch.ones((1, 2, 2, 2), dtype=torch.float32))
        with self.assertRaisesRegex(ValueError, "does not match target batch"):
            normalize_effect_mask(torch.ones((2, 2, 2), dtype=torch.float32), batch_size=3)

    @unittest.skipUnless(nodes.torch is not None, "torch is required for tensor mask semantics")
    def test_non_tensor_control_output_fails_closed_when_effect_mask_is_enabled(self) -> None:
        torch = nodes.torch
        with self.assertRaisesRegex(ValueError, "rank 4"):
            apply_effect_mask_to_control(
                {"input": [1.0], "middle": [], "output": []},
                torch.ones((1, 2, 2), dtype=torch.float32),
            )


if __name__ == "__main__":
    unittest.main()
