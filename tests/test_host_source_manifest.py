from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

from rookieui.contracts.host_source_basis import HOST_SOURCE_BASIS


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tests" / "fixtures" / "current_host_source_manifest.json"
MODULE_NAME = "rookieui.contracts.host_source_manifest"

EXPECTED_ARTIFACT_KEYS = (
    ("core", "app/user_manager.py"),
    ("core", "comfy_extras/nodes_custom_sampler.py"),
    ("core", "comfy_extras/nodes_model_advanced.py"),
    ("core", "comfy_extras/nodes_model_patch.py"),
    ("core", "comfy_extras/nodes_textgen.py"),
    ("core", "nodes.py"),
    ("core", "requirements.txt"),
    ("core", "server.py"),
    ("desktop", "package.json"),
    ("frontend", "package.json"),
    ("frontend", "src/components/common/ExtensionSlot.vue"),
    ("frontend", "src/schemas/apiSchema.ts"),
    ("frontend", "src/stores/executionStore.ts"),
    ("frontend", "src/stores/workspace/sidebarTabStore.ts"),
    ("frontend", "src/types/extensionTypes.ts"),
    ("workflow_templates", "pyproject.toml"),
)


class HostSourceManifestTests(unittest.TestCase):
    def _api(self):
        self.assertIsNotNone(
            importlib.util.find_spec(MODULE_NAME),
            "Candidate source-manifest contract is missing.",
        )
        return importlib.import_module(MODULE_NAME)

    def _payload(self) -> dict[str, object]:
        self.assertTrue(MANIFEST_PATH.is_file(), "Candidate source manifest is missing.")
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_accepted_candidate_subjects_are_exact_and_match_active_basis(self) -> None:
        api = self._api()
        manifest = api.load_manifest(MANIFEST_PATH)

        self.assertEqual(manifest.schema_version, "current-host-source-manifest-v3")
        self.assertEqual(manifest.manifest_kind, "candidate-host-source-freeze")
        self.assertEqual(set(manifest.subjects), {"core", "frontend", "workflow_templates", "desktop"})
        self.assertEqual(
            manifest.subjects["core"].revision,
            "c67885b14556cf3e4e061862925282d403d09862",
        )
        self.assertEqual(
            dict(manifest.subjects["core"].components),
            {
                "embedded_docs": "0.5.10",
                "frontend_package": "1.49.6",
                "workflow_templates": "0.11.43",
            },
        )
        self.assertEqual(
            manifest.subjects["frontend"].revision,
            "569e65b30fbfe96743c7996e201a32bcf029a310",
        )
        self.assertEqual(manifest.subjects["frontend"].version, "1.52.1")
        self.assertEqual(
            manifest.subjects["workflow_templates"].revision,
            "f54739874c88e5a1154275c4597b3860e5a617b4",
        )
        self.assertEqual(manifest.subjects["workflow_templates"].tag, "v0.11.43")
        self.assertEqual(
            dict(manifest.subjects["workflow_templates"].components),
            {
                "assets": "0.1.29",
                "core": "0.3.314",
                "json": "0.1.49",
                "media_api": "0.3.84",
                "media_image": "0.3.160",
                "media_other": "0.3.229",
                "media_video": "0.3.101",
                "meta": "0.11.43",
            },
        )
        self.assertEqual(
            manifest.subjects["workflow_templates"].artifact_status,
            "artifact-verification-pending",
        )
        self.assertEqual(
            manifest.subjects["desktop"].revision,
            "e2d964b7456cea8423c7b9d3371c612313c06baa",
        )
        self.assertEqual(manifest.subjects["desktop"].status, "unchanged-control")

        # The immutable candidate comparison remains the provenance for the promoted basis.
        self.assertEqual(
            HOST_SOURCE_BASIS.core.revision,
            manifest.subjects["core"].revision,
        )
        self.assertEqual(
            HOST_SOURCE_BASIS.frontend.revision,
            manifest.subjects["frontend"].revision,
        )

    def test_artifact_inventory_and_drift_ownership_are_exact(self) -> None:
        api = self._api()
        manifest = api.load_manifest(MANIFEST_PATH)
        actual_keys = tuple((artifact.subject, artifact.path) for artifact in manifest.artifacts)
        self.assertEqual(actual_keys, EXPECTED_ARTIFACT_KEYS)

        changed_core_paths = {
            "nodes.py",
            "comfy_extras/nodes_custom_sampler.py",
            "comfy_extras/nodes_model_advanced.py",
            "comfy_extras/nodes_model_patch.py",
            "comfy_extras/nodes_textgen.py",
        }
        for artifact in manifest.artifacts:
            with self.subTest(subject=artifact.subject, path=artifact.path):
                self.assertGreater(artifact.bytes, 0)
                self.assertRegex(artifact.sha256, re.compile(r"^[0-9a-f]{64}$"))
                if artifact.subject == "core" and artifact.path in changed_core_paths:
                    self.assertEqual(artifact.byte_drift, "changed")
                    self.assertEqual(
                        artifact.semantic_drift,
                        "covered-signature-compatible-runtime-disposition-complete",
                    )
                elif artifact.subject == "frontend" and artifact.path == "src/stores/executionStore.ts":
                    self.assertEqual(artifact.byte_drift, "changed")
                    self.assertEqual(
                        artifact.semantic_drift,
                        "runtime-event-contract-aligned",
                    )
                else:
                    self.assertEqual(artifact.semantic_drift, "none")

        comparisons = {comparison.subject: comparison for comparison in manifest.comparisons}
        self.assertEqual(set(comparisons), {"core", "frontend", "workflow_templates", "desktop"})
        self.assertEqual(comparisons["core"].owner, "runtime-compatibility-alignment")
        self.assertEqual(
            comparisons["core"].semantic_drift,
            "graph-and-runtime-contract-compatible",
        )
        self.assertEqual(
            comparisons["frontend"].owner,
            "frontend-compatibility-alignment",
        )
        self.assertEqual(
            comparisons["frontend"].semantic_drift,
            "sidebar-and-runtime-event-compatible",
        )
        self.assertEqual(
            comparisons["workflow_templates"].owner,
            "workflow-template-alignment",
        )
        self.assertEqual(comparisons["desktop"].owner, "source-freeze")
        self.assertEqual(comparisons["desktop"].source_drift, "none")

    def test_canonical_serialization_round_trip_is_byte_stable(self) -> None:
        api = self._api()
        original = MANIFEST_PATH.read_text(encoding="utf-8")
        manifest = api.parse_manifest_text(original)
        self.assertEqual(api.serialize_manifest(manifest), original)
        self.assertTrue(original.endswith("\n"))
        self.assertFalse(original.endswith("\n\n"))

    def test_canonical_public_manifest_has_no_internal_item_code_tokens(self) -> None:
        item_code_shape = re.compile(r"\b[A-Z][A-Z0-9-]*[0-9]{3,}\b")
        manifest_text = MANIFEST_PATH.read_text(encoding="utf-8")
        self.assertIsNone(item_code_shape.search(manifest_text))

    def test_parser_rejects_duplicate_and_unknown_members(self) -> None:
        api = self._api()
        duplicate = '{"schema_version":"current-host-source-manifest-v3","schema_version":"x"}'
        with self.assertRaisesRegex(ValueError, "duplicate"):
            api.parse_manifest_text(duplicate)

        for name, mutate, expected_error in (
            ("top-level", lambda value: value.update({"unexpected": True}), "unknown"),
            (
                "nested-subject",
                lambda value: value["subjects"]["core"].update({"unexpected": True}),
                "unknown",
            ),
            (
                "nested-artifact",
                lambda value: value["artifacts"][0].update({"unexpected": True}),
                "unknown",
            ),
        ):
            with self.subTest(name):
                payload = self._payload()
                mutate(payload)
                with self.assertRaisesRegex(ValueError, expected_error):
                    api.parse_manifest_text(json.dumps(payload))

    def test_parser_fails_closed_for_invalid_identity_path_hash_and_enum(self) -> None:
        api = self._api()
        cases = (
            (
                "revision",
                lambda value: value["subjects"]["core"].update({"revision": "A" * 40}),
                "revision",
            ),
            (
                "unsafe-path",
                lambda value: value["artifacts"][0].update({"path": "../escape.py"}),
                "path",
            ),
            (
                "backslash-path",
                lambda value: value["artifacts"][0].update({"path": "app\\user_manager.py"}),
                "path",
            ),
            (
                "hash",
                lambda value: value["artifacts"][0].update({"sha256": "0" * 63}),
                "SHA-256",
            ),
            (
                "bytes",
                lambda value: value["artifacts"][0].update({"bytes": 0}),
                "byte",
            ),
            (
                "enum",
                lambda value: value["artifacts"][0].update({"semantic_drift": "reviewed"}),
                "semantic",
            ),
            (
                "duplicate-artifact",
                lambda value: value["artifacts"].append(value["artifacts"][0].copy()),
                "duplicate",
            ),
            (
                "missing-subject",
                lambda value: value["subjects"].pop("desktop"),
                "subject",
            ),
        )
        for name, mutate, expected_error in cases:
            with self.subTest(name):
                payload = self._payload()
                mutate(payload)
                with self.assertRaisesRegex(ValueError, expected_error):
                    api.parse_manifest_text(json.dumps(payload))

    def test_synthetic_source_verification_detects_revision_file_and_hash_drift(self) -> None:
        api = self._api()
        payload = self._payload()
        expected_revisions = {
            subject: details["revision"] for subject, details in payload["subjects"].items()
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            source_roots = {subject: temp_root / subject for subject in expected_revisions}
            for source_root in source_roots.values():
                source_root.mkdir()
            for artifact in payload["artifacts"]:
                content = f"{artifact['subject']}:{artifact['path']}".encode()
                target = source_roots[artifact["subject"]] / Path(artifact["path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                artifact["bytes"] = len(content)
                artifact["sha256"] = hashlib.sha256(content).hexdigest()

            manifest = api.parse_manifest_text(json.dumps(payload))
            revision_reader = lambda path: expected_revisions[path.name]
            report = api.verify_source_artifacts(
                manifest,
                source_roots=source_roots,
                revision_reader=revision_reader,
            )
            self.assertEqual(report.status, "verified")
            self.assertEqual(len(report.artifacts), 16)

            with self.subTest("revision mismatch"):
                with self.assertRaisesRegex(ValueError, "revision"):
                    api.verify_source_artifacts(
                        manifest,
                        source_roots=source_roots,
                        revision_reader=lambda path: "0" * 40
                        if path.name == "core"
                        else expected_revisions[path.name],
                    )

            with self.subTest("hash mismatch"):
                first = manifest.artifacts[0]
                (source_roots[first.subject] / Path(first.path)).write_bytes(b"drift")
                with self.assertRaisesRegex(ValueError, "hash|byte"):
                    api.verify_source_artifacts(
                        manifest,
                        source_roots=source_roots,
                        revision_reader=revision_reader,
                    )

            with self.subTest("missing artifact"):
                (source_roots[first.subject] / Path(first.path)).unlink()
                with self.assertRaisesRegex(ValueError, "missing"):
                    api.verify_source_artifacts(
                        manifest,
                        source_roots=source_roots,
                        revision_reader=revision_reader,
                    )

    def test_default_reference_verification_is_exact_or_fully_unavailable(self) -> None:
        api = self._api()
        manifest = api.load_manifest(MANIFEST_PATH)
        report = api.verify_source_artifacts(manifest)
        self.assertIn(report.status, {"verified", "unavailable-fixture-only"})
        if report.status == "verified":
            self.assertEqual(len(report.artifacts), 16)
        else:
            self.assertEqual(report.artifacts, ())


if __name__ == "__main__":
    unittest.main()
