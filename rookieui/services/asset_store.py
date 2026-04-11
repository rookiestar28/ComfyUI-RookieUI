from __future__ import annotations

import base64
import binascii
import hashlib
import io
import logging
import re
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from rookieui.security.asset_guard import validate_asset_identifier

_DATA_URL_RE = re.compile(r"^data:image/(?P<fmt>[a-zA-Z0-9.+-]+);base64,(?P<data>.+)$")
_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME_ROOT = _WORKSPACE_ROOT / ".rookieui_runtime"
_INPUT_ROOT = _RUNTIME_ROOT / "input"
_OUTPUT_ROOT = _RUNTIME_ROOT / "output"
_SUPPORTED_EXTENSIONS = {
    "png": ".png",
    "jpeg": ".jpg",
    "jpg": ".jpg",
    "webp": ".webp",
}
_LOGGER = logging.getLogger("ComfyUI-RookieUI")
_RUNTIME_RETENTION_HOURS = 24
_RUNTIME_MAX_FILES_PER_DIR = 500
_RUNTIME_CLEANUP_INTERVAL_SECONDS = 60
_cleanup_lock = threading.Lock()
# IMPORTANT: throttle runtime cleanup scans; running on every asset operation causes avoidable I/O spikes.
_last_cleanup_at = 0.0


@dataclass(frozen=True)
class StoredAsset:
    handle: str
    filename: str
    path: Path
    extension: str
    sha256: str


def _ensure_runtime_dirs() -> None:
    _INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    _OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    _run_runtime_cleanup()


def _cleanup_directory(
    root: Path,
    *,
    now_epoch: float,
    max_age_seconds: float,
    max_files: int,
) -> None:
    files: list[Path] = [entry for entry in root.iterdir() if entry.is_file()]
    for path in files:
        try:
            age_seconds = now_epoch - path.stat().st_mtime
            if age_seconds > max_age_seconds:
                path.unlink(missing_ok=True)
        except Exception:
            _LOGGER.debug(
                "RookieUI runtime cleanup skipped stale candidate '%s' due to access error.",
                path,
                exc_info=True,
            )

    remaining = sorted(
        (entry for entry in root.iterdir() if entry.is_file()),
        key=lambda entry: entry.stat().st_mtime,
        reverse=True,
    )
    # IMPORTANT: enforce hard cap after age pruning so long-running sessions cannot grow unbounded on disk.
    for overflow_path in remaining[max_files:]:
        try:
            overflow_path.unlink(missing_ok=True)
        except Exception:
            _LOGGER.debug(
                "RookieUI runtime cleanup skipped overflow candidate '%s' due to access error.",
                overflow_path,
                exc_info=True,
            )


def _run_runtime_cleanup() -> None:
    global _last_cleanup_at

    now_epoch = time.time()
    with _cleanup_lock:
        if (now_epoch - _last_cleanup_at) < _RUNTIME_CLEANUP_INTERVAL_SECONDS:
            return
        _last_cleanup_at = now_epoch

    max_age_seconds = float(_RUNTIME_RETENTION_HOURS) * 3600.0
    _cleanup_directory(
        _INPUT_ROOT,
        now_epoch=now_epoch,
        max_age_seconds=max_age_seconds,
        max_files=_RUNTIME_MAX_FILES_PER_DIR,
    )
    _cleanup_directory(
        _OUTPUT_ROOT,
        now_epoch=now_epoch,
        max_age_seconds=max_age_seconds,
        max_files=_RUNTIME_MAX_FILES_PER_DIR,
    )


def _reset_runtime_cleanup_state_for_tests() -> None:
    global _last_cleanup_at
    with _cleanup_lock:
        _last_cleanup_at = 0.0


def decode_image_data(raw_value: object) -> tuple[bytes, str]:
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValueError("image_data is required.")

    candidate = raw_value.strip()
    match = _DATA_URL_RE.match(candidate)
    if match:
        image_format = match.group("fmt").lower()
        encoded = match.group("data")
    else:
        image_format = "png"
        encoded = candidate

    extension = _SUPPORTED_EXTENSIONS.get(image_format)
    if extension is None:
        raise ValueError("image_data must be a supported PNG, JPEG, or WEBP data URL.")

    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("image_data must be valid base64-encoded image content.") from exc

    if not decoded:
        raise ValueError("image_data must not be empty.")

    return decoded, extension


def store_uploaded_image(raw_value: object, *, prefix: str = "rookieui") -> StoredAsset:
    image_bytes, extension = decode_image_data(raw_value)
    image = Image.open(io.BytesIO(image_bytes))
    image.verify()

    _ensure_runtime_dirs()
    handle = validate_asset_identifier(
        f"{prefix}_{secrets.token_hex(8)}{extension}"
    )
    path = _INPUT_ROOT / handle
    path.write_bytes(image_bytes)
    digest = hashlib.sha256(image_bytes).hexdigest()
    return StoredAsset(
        handle=handle,
        filename=handle,
        path=path,
        extension=extension,
        sha256=digest,
    )


def resolve_input_asset_path(handle: str) -> Path:
    normalized_handle = validate_asset_identifier(handle)
    path = _INPUT_ROOT / normalized_handle
    if not path.exists() or not path.is_file():
        raise ValueError(f"Unknown RookieUI asset handle: {normalized_handle}")
    return path


def resolve_asset_path(handle: str) -> Path:
    normalized_handle = validate_asset_identifier(handle)
    for root in (_INPUT_ROOT, _OUTPUT_ROOT):
        path = root / normalized_handle
        if path.exists() and path.is_file():
            return path
    raise ValueError(f"Unknown RookieUI asset handle: {normalized_handle}")


def list_output_assets() -> list[str]:
    _ensure_runtime_dirs()
    return sorted(
        entry.name
        for entry in _OUTPUT_ROOT.iterdir()
        if entry.is_file()
    )


def save_output_image(
    image: Image.Image,
    *,
    prefix: str = "rookieui_output",
    metadata: dict[str, Any] | None = None,
) -> StoredAsset:
    _ensure_runtime_dirs()
    handle = validate_asset_identifier(f"{prefix}_{secrets.token_hex(8)}.png")
    path = _OUTPUT_ROOT / handle
    pnginfo = None
    if metadata:
        try:
            from PIL import PngImagePlugin

            pnginfo = PngImagePlugin.PngInfo()
            for key, value in metadata.items():
                if isinstance(key, str) and isinstance(value, str):
                    pnginfo.add_text(key, value)
        except Exception:
            _LOGGER.debug("RookieUI output PNG metadata embedding fallback triggered.", exc_info=True)
            pnginfo = None

    image.save(path, format="PNG", pnginfo=pnginfo)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return StoredAsset(
        handle=handle,
        filename=handle,
        path=path,
        extension=".png",
        sha256=digest,
    )


def build_data_url_from_path(path: Path) -> str:
    extension = path.suffix.lower()
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(extension, "application/octet-stream")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"
