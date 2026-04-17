from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp-{secrets.token_hex(8)}")
    try:
        temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def quarantine_corrupt_json(path: Path) -> Path | None:
    if not path.exists():
        return None
    quarantine_path = path.with_name(f"{path.stem}.corrupt-{int(time.time() * 1000)}-{secrets.token_hex(4)}{path.suffix}")
    try:
        os.replace(path, quarantine_path)
    except OSError:
        return None
    return quarantine_path
