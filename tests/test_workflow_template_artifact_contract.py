from __future__ import annotations

import hashlib
import importlib
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


MODULE_NAME = "rookieui.contracts.workflow_template_artifact_contract"


class WorkflowTemplateArtifactContractTests(unittest.TestCase):
    def _api(self):
        self.assertIsNotNone(
            importlib.util.find_spec(MODULE_NAME),
            "Workflow-template artifact verification contract is missing.",
        )
        return importlib.import_module(MODULE_NAME)

    def test_exact_regular_artifact_is_verified(self) -> None:
        api = self._api()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            payload = b"synthetic inert artifact"
            target = root / "artifact.whl"
            target.write_bytes(payload)
            spec = api.ArtifactSpec(
                filename="artifact.whl",
                bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest(),
            )

            result = api.verify_artifact(root, spec)

            self.assertEqual(result.filename, spec.filename)
            self.assertEqual(result.bytes, len(payload))
            self.assertEqual(result.sha256, spec.sha256)

    def test_unsafe_filename_size_and_hash_fail_closed(self) -> None:
        api = self._api()
        payload = b"bounded artifact"
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "artifact.whl").write_bytes(payload)
            for name, spec, message in (
                (
                    "traversal",
                    api.ArtifactSpec(
                        "../artifact.whl",
                        len(payload),
                        hashlib.sha256(payload).hexdigest(),
                    ),
                    "filename",
                ),
                (
                    "backslash",
                    api.ArtifactSpec(
                        "nested\\artifact.whl",
                        len(payload),
                        hashlib.sha256(payload).hexdigest(),
                    ),
                    "filename",
                ),
                (
                    "size",
                    api.ArtifactSpec(
                        "artifact.whl",
                        len(payload) + 1,
                        hashlib.sha256(payload).hexdigest(),
                    ),
                    "size",
                ),
                (
                    "hash",
                    api.ArtifactSpec("artifact.whl", len(payload), "0" * 64),
                    "SHA-256",
                ),
            ):
                with self.subTest(name):
                    with self.assertRaisesRegex(ValueError, message):
                        api.verify_artifact(root, spec)

    def test_resource_limit_and_link_fail_closed(self) -> None:
        api = self._api()
        payload = b"0123456789"
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "artifact.whl"
            target.write_bytes(payload)
            spec = api.ArtifactSpec(
                "artifact.whl",
                len(payload),
                hashlib.sha256(payload).hexdigest(),
            )
            with self.assertRaisesRegex(ValueError, "resource limit"):
                api.verify_artifact(root, spec, max_bytes=len(payload) - 1)

            link = root / "linked.whl"
            try:
                os.symlink(target, link)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable on this platform")
            linked_spec = api.ArtifactSpec(
                "linked.whl",
                len(payload),
                hashlib.sha256(payload).hexdigest(),
            )
            with self.assertRaisesRegex(ValueError, "link|reparse"):
                api.verify_artifact(root, linked_spec)


if __name__ == "__main__":
    unittest.main()
