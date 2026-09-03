from __future__ import annotations

import hashlib
import importlib
import importlib.util
import os
import stat
import tarfile
import tempfile
import unittest
import zipfile
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

    def test_verified_wheel_members_are_read_inertly_and_bounded(self) -> None:
        api = self._api()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "artifact.whl"
            with zipfile.ZipFile(target, "w") as archive:
                archive.writestr("package/", b"")
                archive.writestr("package/a.json", b'{}')
            spec = api.ArtifactSpec(
                target.name,
                target.stat().st_size,
                hashlib.sha256(target.read_bytes()).hexdigest(),
            )

            inventory = api.inspect_wheel(root, spec)

            self.assertEqual(inventory.member_count, 2)
            self.assertEqual(inventory.file_count, 1)
            self.assertEqual(inventory.total_uncompressed_bytes, 2)
            self.assertEqual(tuple(member.name for member in inventory.members), (
                "package/",
                "package/a.json",
            ))
            self.assertEqual(inventory.members[1].sha256, hashlib.sha256(b"{}").hexdigest())

            with self.assertRaisesRegex(ValueError, "member limit"):
                api.inspect_wheel(root, spec, max_members=1)
            with self.assertRaisesRegex(ValueError, "uncompressed"):
                api.inspect_wheel(root, spec, max_total_uncompressed_bytes=1)

    def test_unsafe_wheel_members_fail_closed(self) -> None:
        api = self._api()
        cases = (
            ("traversal", (("../escape.json", b"{}", None),), "unsafe"),
            (
                "case-collision",
                (("Package/a.json", b"{}", None), ("package/A.json", b"{}", None)),
                "collision",
            ),
            (
                "symlink",
                (("package/link", b"target", (stat.S_IFLNK | 0o777) << 16),),
                "link|regular",
            ),
            (
                "child-before-file-parent",
                (("Package/child.json", b"{}", None), ("package", b"file", None)),
                "ancestor",
            ),
        )
        for name, members, message in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                target = root / "artifact.whl"
                with zipfile.ZipFile(target, "w") as archive:
                    for member_name, payload, external_attr in members:
                        info = zipfile.ZipInfo(member_name)
                        if external_attr is not None:
                            info.create_system = 3
                            info.external_attr = external_attr
                        archive.writestr(info, payload)
                spec = api.ArtifactSpec(
                    target.name,
                    target.stat().st_size,
                    hashlib.sha256(target.read_bytes()).hexdigest(),
                )
                with self.assertRaisesRegex(ValueError, message):
                    api.inspect_wheel(root, spec)

    def test_verified_sdist_members_are_read_inertly_and_bounded(self) -> None:
        api = self._api()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "payload.txt"
            source.write_bytes(b"inert")
            target = root / "artifact.tar.gz"
            with tarfile.open(target, "w:gz") as archive:
                archive.add(source, arcname="package/payload.txt")
            spec = api.ArtifactSpec(
                target.name,
                target.stat().st_size,
                hashlib.sha256(target.read_bytes()).hexdigest(),
            )

            inventory = api.inspect_sdist(root, spec)

            self.assertEqual(inventory.member_count, 1)
            self.assertEqual(inventory.file_count, 1)
            self.assertEqual(inventory.total_uncompressed_bytes, 5)
            self.assertEqual(inventory.members[0].name, "package/payload.txt")
            with self.assertRaisesRegex(ValueError, "member limit"):
                api.inspect_sdist(root, spec, max_members=0)

    def test_unsafe_sdist_member_fails_closed(self) -> None:
        api = self._api()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "artifact.tar.gz"
            with tarfile.open(target, "w:gz") as archive:
                info = tarfile.TarInfo("../escape.txt")
                info.size = 0
                archive.addfile(info)
            spec = api.ArtifactSpec(
                target.name,
                target.stat().st_size,
                hashlib.sha256(target.read_bytes()).hexdigest(),
            )
            with self.assertRaisesRegex(ValueError, "unsafe"):
                api.inspect_sdist(root, spec)


if __name__ == "__main__":
    unittest.main()
