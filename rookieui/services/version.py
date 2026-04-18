from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"
_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_VERSION_LINE_PATTERN = re.compile(
    r"(?ms)^\ufeff?\[project\]\s*(?:[^\[]*?)^version\s*=\s*[\"']([^\"']+)[\"']\s*$"
)
_FALLBACK_VERSION = "0.0.0"


def _read_project_version_from_pyproject(pyproject_path: Path) -> str | None:
    try:
        content = pyproject_path.read_text(encoding="utf-8")
    except OSError:
        return None

    # Compatibility strategy: prefer stdlib TOML parse, then fallback regex.
    try:
        from tomllib import loads as toml_loads  # type: ignore[attr-defined]
    except Exception:
        toml_loads = None

    if toml_loads:
        try:
            data = toml_loads(content)
            version_value = data.get("project", {}).get("version")
            if version_value:
                return str(version_value).strip() or None
        except Exception:
            pass

    # CRITICAL: tolerate BOM/CRLF and parse only inside [project] so shell version
    # does not silently drift back to fallback when pyproject formatting changes.
    match = _VERSION_LINE_PATTERN.search(content)
    if match:
        return match.group(1).strip() or None
    return None


@lru_cache(maxsize=1)
def resolve_shell_version() -> str:
    pyproject_version = _read_project_version_from_pyproject(_PYPROJECT_PATH)
    if pyproject_version:
        return pyproject_version
    return _FALLBACK_VERSION


def _iter_runtime_fingerprint_paths() -> tuple[Path, ...]:
    package_paths = sorted(path for path in _PACKAGE_ROOT.rglob("*.py") if path.is_file())
    explicit_paths = [
        path
        for path in (
            _REPO_ROOT / "__init__.py",
            _PYPROJECT_PATH,
        )
        if path.is_file()
    ]
    unique_paths: dict[str, Path] = {}
    for path in [*package_paths, *explicit_paths]:
        unique_paths[str(path.resolve())] = path
    return tuple(unique_paths[key] for key in sorted(unique_paths))


def _compute_runtime_build_fingerprint() -> str:
    digest = hashlib.sha256()
    try:
        for path in _iter_runtime_fingerprint_paths():
            relative_path = path.resolve().relative_to(_REPO_ROOT.resolve()).as_posix()
            digest.update(relative_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    except OSError:
        return f"shell-version:{resolve_shell_version()}"
    return f"sha256:{digest.hexdigest()}"


# CRITICAL: compute once at import time so a stale host keeps the fingerprint of
# the code it actually loaded, even if workspace files change on disk before restart.
_RUNTIME_BUILD_FINGERPRINT = _compute_runtime_build_fingerprint()


def resolve_runtime_build_fingerprint() -> str:
    return _RUNTIME_BUILD_FINGERPRINT


def build_runtime_metadata_payload() -> dict[str, str]:
    return {
        "shell_version": resolve_shell_version(),
        "build_fingerprint": resolve_runtime_build_fingerprint(),
    }
