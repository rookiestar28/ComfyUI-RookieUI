from __future__ import annotations

import importlib
import json
import numpy as np
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from rookieui import nodes
from rookieui.contracts import core_runtime_contract
from rookieui.services import controlnet_mask_runtime
from rookieui.services.prompt_token_rebatch import tokenize_with_rookieui_rebatch
from rookieui.services.workflow_builders.core import _build_sampler_node


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "tests" / "fixtures" / "current_host_core_runtime_contract.json"


class _NumpyTensor(np.ndarray):
    @property
    def device(self):
        return SimpleNamespace(type="cpu")

    def clone(self):
        return self.copy().view(_NumpyTensor)

    def to(self, *, dtype=None, device=None):
        _ = device
        return np.asarray(self, dtype=self.dtype if dtype is None else dtype).view(_NumpyTensor)

    def repeat(self, *sizes):
        return np.tile(np.asarray(self), sizes).view(_NumpyTensor)

    def unsqueeze(self, dim):
        return np.expand_dims(self, axis=dim).view(_NumpyTensor)

    def squeeze(self, dim=None):
        return np.squeeze(np.asarray(self), axis=dim).view(_NumpyTensor)

    def movedim(self, source, destination):
        return np.moveaxis(self, source, destination).view(_NumpyTensor)

    def round(self):
        return np.round(self).view(_NumpyTensor)


def _tensor(value, *, dtype=np.float32):
    return np.asarray(value, dtype=dtype).view(_NumpyTensor)


class _Generator:
    def __init__(self, *, device: str) -> None:
        self.device = device
        self.seed = 0

    def manual_seed(self, seed: int):
        self.seed = seed
        return self


class _Functional:
    @staticmethod
    def interpolate(tensor, *, size, mode, align_corners=None):
        _ = (mode, align_corners)
        if tuple(tensor.shape[-2:]) == tuple(size):
            return tensor.clone()
        return _tensor(
            np.full((*tensor.shape[:-2], *size), float(tensor.mean()), dtype=tensor.dtype)
        )


class _FakeTorch:
    Tensor = _NumpyTensor
    float32 = np.float32
    nn = SimpleNamespace(functional=_Functional())
    Generator = _Generator

    @staticmethod
    def full(shape, value, *, dtype):
        return _tensor(np.full(shape, value, dtype=dtype))

    @staticmethod
    def ones(shape, *, dtype, device=None):
        _ = device
        return _tensor(np.ones(shape, dtype=dtype))

    @staticmethod
    def zeros(shape, *, dtype, device=None):
        _ = device
        return _tensor(np.zeros(shape, dtype=dtype))

    @staticmethod
    def randn(shape, *, generator, device, dtype):
        _ = device
        return _tensor(np.random.default_rng(generator.seed).standard_normal(shape), dtype=dtype)

    @staticmethod
    def equal(left, right):
        return bool(np.array_equal(left, right))

    @staticmethod
    def isfinite(value):
        return np.isfinite(value).view(_NumpyTensor)

    @staticmethod
    def clamp(value, minimum, maximum):
        return np.clip(value, minimum, maximum).view(_NumpyTensor)

    @staticmethod
    def count_nonzero(value):
        return np.asarray(np.count_nonzero(value))


class CurrentHostCoreRuntimeContractTests(unittest.TestCase):
    def test_contract_identity_cases_sources_and_serialization_are_exact(self) -> None:
        contract = core_runtime_contract.load_core_runtime_contract(CONTRACT_PATH)

        self.assertEqual(contract.schema_version, "current-host-core-runtime-contract-v1")
        self.assertEqual(contract.contract_kind, "candidate-core-runtime-semantics")
        self.assertEqual(contract.baseline_revision, "6f7cd7fceaaf60d2669b554936394a7412c6fde5")
        self.assertEqual(contract.source_revision, "c67885b14556cf3e4e061862925282d403d09862")
        self.assertEqual(tuple(case.case_id for case in contract.cases), core_runtime_contract.REQUIRED_CASE_IDS)
        self.assertEqual(tuple(source.path for source in contract.sources), core_runtime_contract.REQUIRED_SOURCE_PATHS)
        self.assertEqual(
            core_runtime_contract.serialize_core_runtime_contract(contract),
            CONTRACT_PATH.read_text(encoding="utf-8"),
        )

    def test_contract_source_rows_are_verified_from_pinned_git_objects(self) -> None:
        contract = core_runtime_contract.load_core_runtime_contract(CONTRACT_PATH)
        report = core_runtime_contract.verify_core_runtime_sources(contract)

        if core_runtime_contract.DEFAULT_SOURCE_ROOT.is_dir():
            self.assertEqual(report.status, "verified")
            self.assertEqual(len(report.sources), len(core_runtime_contract.REQUIRED_SOURCE_PATHS))
            self.assertTrue(all(source.candidate_verified for source in report.sources))
            self.assertTrue(all(source.baseline_verified for source in report.sources))
        else:
            self.assertEqual(report.status, "unavailable-fixture-only")
            self.assertEqual(report.sources, ())

    def test_contract_evidence_targets_resolve_and_public_projection_is_content_free(self) -> None:
        contract = core_runtime_contract.load_core_runtime_contract(CONTRACT_PATH)

        for case in contract.cases:
            with self.subTest(case=case.case_id):
                module_name, class_name, member_name = case.evidence.rsplit(".", 2)
                target_class = getattr(importlib.import_module(module_name), class_name)
                self.assertTrue(callable(getattr(target_class, member_name)))

        public_text = CONTRACT_PATH.read_text(encoding="utf-8")
        for forbidden in (
            ".planning",
            "reference/",
            "provider_payload",
            "private_host",
            "B:\\",
        ):
            self.assertNotIn(forbidden, public_text)
        self.assertNotRegex(public_text, r"\b[A-Z][A-Z0-9-]*[0-9]{3,}\b")

    def test_contract_rejects_duplicate_unknown_unsafe_and_incomplete_data(self) -> None:
        canonical = CONTRACT_PATH.read_text(encoding="utf-8")
        payload = json.loads(canonical)
        mutations = {
            "duplicate-member": canonical.replace(
                '  "schema_version":',
                '  "schema_version": "duplicate",\n  "schema_version":',
                1,
            ),
            "unknown-field": json.dumps({**payload, "unknown": True}),
            "unsafe-path": json.dumps(
                {
                    **payload,
                    "sources": [
                        {**payload["sources"][0], "path": "../outside.py"},
                        *payload["sources"][1:],
                    ],
                }
            ),
            "incomplete-cases": json.dumps({**payload, "cases": payload["cases"][:-1]}),
            "unknown-case-reference": json.dumps(
                {
                    **payload,
                    "sources": [
                        {**payload["sources"][0], "case_ids": ["unknown-case"]},
                        *payload["sources"][1:],
                    ],
                }
            ),
        }
        for case_id, text in mutations.items():
            with self.subTest(case=case_id):
                with self.assertRaises(ValueError):
                    core_runtime_contract.parse_core_runtime_contract_text(text)

    def test_missing_reference_envelope_is_reported_without_live_verification_claim(self) -> None:
        contract = core_runtime_contract.load_core_runtime_contract(CONTRACT_PATH)
        with tempfile.TemporaryDirectory() as directory:
            report = core_runtime_contract.verify_core_runtime_sources(
                contract,
                source_root=Path(directory) / "missing",
            )

        self.assertEqual(report.status, "unavailable-fixture-only")
        self.assertEqual(report.sources, ())


class CurrentHostCoreRuntimeBehaviorTests(unittest.TestCase):
    def test_stock_sampler_preserves_seed_denoise_scheduler_and_latent_link(self) -> None:
        request = SimpleNamespace(
            execution_seed=18446744073709551615,
            steps=23,
            cfg_scale=6.5,
            sampler_name="euler",
            scheduler_name="normal",
        )
        workflow: dict[str, object] = {}

        _build_sampler_node(
            workflow,
            node_id="9",
            positive_id="2",
            negative_id="3",
            latent_id="8",
            request=request,
            denoise=0.37,
            model_source=["1", 0],
        )

        self.assertEqual(
            workflow,
            {
                "9": {
                    "class_type": "KSampler",
                    "inputs": {
                        "model": ["1", 0],
                        "positive": ["2", 0],
                        "negative": ["3", 0],
                        "latent_image": ["8", 0],
                        "seed": 18446744073709551615,
                        "steps": 23,
                        "cfg": 6.5,
                        "sampler_name": "euler",
                        "scheduler": "normal",
                        "denoise": 0.37,
                    },
                }
            },
        )
        self.assertEqual(json.loads(json.dumps(workflow)), workflow)

        profile_contract = json.loads(
            (ROOT / "tests" / "fixtures" / "current_host_profile_graph_contract.json").read_text(
                encoding="utf-8"
            )
        )
        emitted_classes = {
            class_type
            for profile in profile_contract["profiles"]
            for class_type in profile["class_types"]
        }
        self.assertIn("RandomNoise", emitted_classes)
        self.assertNotIn("DisableNoise", emitted_classes)
        self.assertNotIn("KSamplerAdvanced", emitted_classes)

    def test_inpaint_runtime_preserves_cropped_mask_and_latent_geometry(self) -> None:
        torch = _FakeTorch()

        class _FakeVae:
            @staticmethod
            def spacial_compression_encode() -> int:
                return 8

            @staticmethod
            def encode(pixels):
                return torch.zeros(
                    (pixels.shape[0], 4, pixels.shape[1] // 8, pixels.shape[2] // 8),
                    dtype=pixels.dtype,
                    device=pixels.device,
                )

        pixels = torch.full((1, 19, 17, 3), 0.5, dtype=torch.float32)
        mask = torch.ones((1, 19, 17), dtype=torch.float32)
        node = nodes.RookieUIVAEEncodeForInpaint()

        with mock.patch.object(nodes, "torch", torch):
            first = node.encode(
                pixels,
                _FakeVae(),
                mask,
                grow_mask_by=0,
                masked_content="latent_noise",
                seed=42,
            )[0]
            second = node.encode(
                pixels,
                _FakeVae(),
                mask,
                grow_mask_by=0,
                masked_content="latent_noise",
                seed=42,
            )[0]

        self.assertEqual(tuple(first["samples"].shape), (1, 4, 2, 2))
        self.assertEqual(tuple(first["noise_mask"].shape), (1, 1, 16, 16))
        self.assertTrue(torch.equal(first["samples"], second["samples"]))
        self.assertTrue(torch.equal(first["noise_mask"], second["noise_mask"]))

    def test_controlnet_mask_protocol_executes_broadcast_effect_and_concat_geometry(self) -> None:
        torch = _FakeTorch()
        source_mask = _tensor([[[1.0, 0.0], [0.0, 1.0]]])
        control = {
            "input": [torch.ones((2, 1, 2, 2), dtype=torch.float32)],
            "middle": [None],
            "output": [],
        }
        image = torch.ones((2, 2, 2, 3), dtype=torch.float32)

        with mock.patch.object(controlnet_mask_runtime, "torch", torch):
            normalized = controlnet_mask_runtime.normalize_effect_mask(source_mask, batch_size=2)
            masked = controlnet_mask_runtime.apply_effect_mask_to_control(control, normalized)
            masked_image, extra_concat = controlnet_mask_runtime.prepare_concat_mask(image, source_mask)

        self.assertEqual(tuple(normalized.shape), (2, 2, 2))
        self.assertEqual(tuple(masked["input"][0].shape), (2, 1, 2, 2))
        self.assertTrue(np.array_equal(masked["input"][0][:, 0], normalized))
        self.assertIsNone(masked["middle"][0])
        self.assertEqual(tuple(masked_image.shape), (2, 2, 2, 3))
        self.assertEqual(tuple(extra_concat[0].shape), (2, 1, 2, 2))
        self.assertTrue(np.all(masked_image[:, 0, 0, :] == 0.0))
        self.assertTrue(np.all(masked_image[:, 0, 1, :] == 1.0))

    def test_controlnet_mask_protocol_rejects_non_tensor_control_output(self) -> None:
        torch = _FakeTorch()
        source_mask = _tensor([[[1.0, 0.0], [0.0, 1.0]]])

        with mock.patch.object(controlnet_mask_runtime, "torch", torch):
            with self.assertRaisesRegex(ValueError, r"rank 4 \[B,C,H,W\]"):
                controlnet_mask_runtime.apply_effect_mask_to_control(
                    {"input": [1.0], "middle": [], "output": []},
                    source_mask,
                )

    def test_tokenizer_capability_mismatch_uses_stock_tokens_without_prompt_logging(self) -> None:
        class _StockOnlyClip:
            def __init__(self) -> None:
                self.calls: list[tuple[str, bool]] = []

            def tokenize(self, text: str, return_word_ids: bool = False):
                self.calls.append((text, return_word_ids))
                if return_word_ids:
                    raise TypeError("return_word_ids is unsupported")
                return {"l": [[(100, 1.0), (7, 1.0), (101, 1.0)]]}

        clip = _StockOnlyClip()
        tokens = tokenize_with_rookieui_rebatch(clip, "synthetic public-safe text")

        self.assertEqual(tokens, {"l": [[(100, 1.0), (7, 1.0), (101, 1.0)]]})
        self.assertEqual(
            clip.calls,
            [
                ("synthetic public-safe text", False),
                ("synthetic public-safe text", True),
            ],
        )


if __name__ == "__main__":
    unittest.main()
