from __future__ import annotations

import ast
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_INIT = REPO_ROOT / "__init__.py"

TEST_FILE_SUFFIXES = (".test.js", ".spec.js")
TEST_DIRECTORY_NAMES = frozenset({"tests", "test", "__tests__"})


def _declared_web_directory() -> str:
    """Read WEB_DIRECTORY out of the package source without importing the package.

    IMPORTANT: this is read from the declaration rather than hardcoded as "web". The
    invariant being guarded is "nothing under the directory this pack registers with the
    host is a test asset", and ComfyUI serves whatever WEB_DIRECTORY names. Hardcoding the
    current value would let a future change to that declaration move the served tree out
    from under this guard while it kept passing against a directory nobody serves.

    Importing the package instead of parsing it would pull in the node registry and its
    host-facing dependencies, which this check does not need and should not require.
    """
    tree = ast.parse(PACKAGE_INIT.read_text(encoding="utf-8"), filename=str(PACKAGE_INIT))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "WEB_DIRECTORY":
                value = node.value
                if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                    raise AssertionError("WEB_DIRECTORY is not a string literal")
                return value.value
    raise AssertionError("WEB_DIRECTORY is not declared in the package __init__")


def _served_root() -> Path:
    declared = _declared_web_directory()
    resolved = (REPO_ROOT / declared).resolve()
    if not resolved.is_dir():
        raise AssertionError(f"declared web directory does not exist: {declared}")
    return resolved


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


class ServedWebTreeIsRuntimeOnlyTests(unittest.TestCase):
    """The registered web directory is published verbatim to every browser.

    ComfyUI walks the registered directory and serves every JavaScript file under it, and
    its frontend imports them without filtering. A test file placed there is therefore
    downloaded and executed by every visitor on every page load, where it fails on
    test-runner specifiers that do not resolve in a browser, and it exposes the internal
    test layout to anyone reading the extension listing.
    """

    def test_no_test_files_are_served(self) -> None:
        served_root = _served_root()
        offenders = sorted(
            _relative(path)
            for path in served_root.rglob("*")
            if path.is_file() and path.name.endswith(TEST_FILE_SUFFIXES)
        )
        self.assertEqual(
            offenders,
            [],
            "test files are published to every browser under the registered web directory; "
            f"move them outside it: {offenders}",
        )

    def test_no_test_directories_are_served(self) -> None:
        served_root = _served_root()
        offenders = sorted(
            _relative(path)
            for path in served_root.rglob("*")
            if path.is_dir() and path.name.lower() in TEST_DIRECTORY_NAMES
        )
        self.assertEqual(
            offenders,
            [],
            "test directories are published under the registered web directory; "
            f"move them outside it: {offenders}",
        )


if __name__ == "__main__":
    unittest.main()
