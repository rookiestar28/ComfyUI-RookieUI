#!/usr/bin/env python3
"""Repo-local supply-chain hardening checks.

This checker is stdlib-only and read-only so it can run before package code is
executed. It detects known Mini Shai-Hulud package families and persistence
indicators in repository-controlled files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

AFFECTED_NPM_PREFIXES = (
    "@tanstack/",
    "@uipath/",
    "@mistralai/",
    "@opensearch-project/",
    "@squawk/",
    "@tallyui/",
    "@cap-js/",
    "@draftauth/",
    "@draftlab/",
    "@taskflow-corp/",
    "@tolka/",
    "@beproduct/",
    "@dirigible-ai/",
    "@ml-toolkit-ts/",
    "@supersurkhet/",
    "@mesadev/",
)

AFFECTED_NPM_NAMES = {
    "agentwork-cli",
    "cmux-agent-mcp",
    "cross-stitch",
    "git-branch-selector",
    "git-git-git",
    "intercom-client",
    "ml-toolkit-ts",
    "nextmove-mcp",
    "safe-action",
    "ts-dna",
    "wot-api",
}

AFFECTED_PYPI_VERSIONS = {
    "guardrails-ai": {"0.10.1"},
    "intercom-client": {"7.0.4"},
    "lightning": {"2.6.2", "2.6.3"},
    "mistralai": {"2.4.6"},
    "pytorch-lightning": {"2.6.2", "2.6.3"},
}

IOC_FILENAMES = {
    "bun_environment.js",
    "execution.js",
    "opensearch_init.js",
    "router_init.js",
    "router_runtime.js",
    "setup.mjs",
    "setup_bun.js",
    "shai-hulud-workflow.yaml",
    "shai-hulud-workflow.yml",
    "tanstack_runner.js",
    "transformers.pyz",
}

IOC_STRINGS = {
    "83.142.209.194",
    "@tanstack/setup",
    "A Mini Shai-Hulud has Appeared",
    "IfYouRevokeThisTokenItWillWipeTheComputerOfTheOwner",
    "Mini Shai-Hulud",
    "Shai-Hulud",
    "git-tanstack",
    "router_init.js",
    "shai-hulud",
    "transformers.pyz",
}

ALLOWED_INSTALL_SCRIPT_PACKAGES = {
    "esbuild",
    "fsevents",
    "vite/node_modules/fsevents",
}

TEXT_SCAN_PATHS = (
    ".github",
    ".vscode",
    "package.json",
    "package-lock.json",
    "requirements.txt",
    "pyproject.toml",
)

SKIP_DIR_NAMES = {
    ".git",
    ".planning",
    ".playwright-cli",
    ".pytest_cache",
    ".rookieui_runtime",
    ".sessions",
    ".tmp",
    ".venv",
    ".venv-wsl",
    "REFERENCE",
    "__pycache__",
    "node_modules",
    "output",
    "reference",
    "test-results",
}


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    detail: str


def _normalize_package_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _iter_lock_packages(lock_path: Path) -> Iterable[tuple[str, str, dict[str, Any]]]:
    lock = _load_json(lock_path)
    for package_path, metadata in (lock.get("packages") or {}).items():
        if not package_path.startswith("node_modules/"):
            continue
        name = package_path.removeprefix("node_modules/")
        version = str((metadata or {}).get("version") or "")
        yield name, version, metadata or {}


def check_npm_lock(lock_path: Path) -> list[Finding]:
    findings: list[Finding] = []
    if not lock_path.exists():
        return findings

    for name, version, metadata in _iter_lock_packages(lock_path):
        normalized = _normalize_package_name(name)
        if normalized in AFFECTED_NPM_NAMES or normalized.startswith(
            AFFECTED_NPM_PREFIXES
        ):
            findings.append(
                Finding(
                    "mini-shai-hulud-npm-package",
                    str(lock_path),
                    f"{name}@{version} matches a known affected package family",
                )
            )
        if metadata.get("hasInstallScript") is True:
            if name not in ALLOWED_INSTALL_SCRIPT_PACKAGES:
                findings.append(
                    Finding(
                        "unexpected-npm-install-script",
                        str(lock_path),
                        f"{name}@{version} declares hasInstallScript=true and is not allowlisted",
                    )
                )
    return findings


_REQ_LINE_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)(?:\[.*?\])?\s*([^#;\s]*)")
_TOML_DEP_RE = re.compile(
    r"""["']([A-Za-z0-9_.-]+)(?:\[.*?\])?\s*([^"']*)["']"""
)
_VERSION_RE = re.compile(r"(?:===|==)\s*([A-Za-z0-9_.!+*-]+)")


def _extract_pinned_version(spec: str) -> str | None:
    match = _VERSION_RE.search(spec)
    return match.group(1) if match else None


def _iter_python_requirements(path: Path) -> Iterable[tuple[str, str | None]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.name == "requirements.txt":
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("-"):
                continue
            match = _REQ_LINE_RE.match(stripped)
            if match:
                yield _normalize_package_name(match.group(1)), _extract_pinned_version(
                    match.group(2)
                )
        return

    for match in _TOML_DEP_RE.finditer(text):
        yield _normalize_package_name(match.group(1)), _extract_pinned_version(
            match.group(2)
        )


def check_python_manifest(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    if not path.exists():
        return findings

    for name, version in _iter_python_requirements(path):
        affected_versions = AFFECTED_PYPI_VERSIONS.get(name)
        if not affected_versions:
            continue
        if version in affected_versions:
            findings.append(
                Finding(
                    "mini-shai-hulud-pypi-package",
                    str(path),
                    f"{name}=={version} matches a known affected PyPI package version",
                )
            )
    return findings


def _is_skipped_dir(path: Path, root: Path) -> bool:
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        return True
    return any(part in SKIP_DIR_NAMES for part in rel_parts)


def check_ioc_filenames(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    # IMPORTANT: prune skipped dirs before stat; Windows cannot stat WSL venv links reliably.
    for current_dir, dir_names, file_names in os.walk(root):
        current_path = Path(current_dir)
        dir_names[:] = [
            name for name in dir_names if not _is_skipped_dir(current_path / name, root)
        ]
        for file_name in file_names:
            if file_name in IOC_FILENAMES:
                path = current_path / file_name
                findings.append(
                    Finding(
                        "mini-shai-hulud-ioc-file",
                        str(path.relative_to(root)),
                        f"matched suspicious filename {file_name}",
                    )
                )
    return findings


def _iter_text_scan_files(root: Path) -> Iterable[Path]:
    for rel in TEXT_SCAN_PATHS:
        path = root / rel
        if path.is_file():
            yield path
        elif path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and not _is_skipped_dir(child, root):
                    yield child


def check_ioc_strings(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in _iter_text_scan_files(root):
        try:
            if path.stat().st_size > 2_000_000:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for needle in sorted(IOC_STRINGS):
            if needle in text:
                findings.append(
                    Finding(
                        "mini-shai-hulud-ioc-string",
                        str(path.relative_to(root)),
                        f"matched suspicious string {needle!r}",
                    )
                )
    return findings


def run_checks(root: Path) -> list[Finding]:
    root = root.resolve()
    findings: list[Finding] = []
    findings.extend(check_npm_lock(root / "package-lock.json"))
    findings.extend(check_npm_lock(root / "node_modules" / ".package-lock.json"))
    findings.extend(check_python_manifest(root / "requirements.txt"))
    findings.extend(check_python_manifest(root / "pyproject.toml"))
    findings.extend(check_ioc_filenames(root))
    findings.extend(check_ioc_strings(root))
    return findings


def _print_findings(findings: Iterable[Finding]) -> None:
    for finding in findings:
        print(f"{finding.code}: {finding.path}: {finding.detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root to scan")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args(argv)

    findings = run_checks(Path(args.root))
    if args.json:
        print(json.dumps([finding.__dict__ for finding in findings], indent=2))
    elif findings:
        _print_findings(findings)
    else:
        print("supply-chain hardening check passed")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
