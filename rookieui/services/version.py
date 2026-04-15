from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path


_PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"
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
