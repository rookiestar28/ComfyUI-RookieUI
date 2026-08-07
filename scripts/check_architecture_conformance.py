from __future__ import annotations

import json
from pathlib import Path

from architecture_conformance import validate_repository


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "tests" / "architecture_contract.json"


def main() -> int:
    violations = validate_repository(ROOT, CONTRACT)
    report = {
        "contract": str(CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        "status": "passed" if not violations else "failed",
        "violation_count": len(violations),
        "violations": [
            {"code": item.code, "path": item.path, "detail": item.detail}
            for item in violations
        ],
    }
    print(json.dumps(report, sort_keys=True))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
