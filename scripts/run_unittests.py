from __future__ import annotations

import argparse
import pathlib
import sys
import unittest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run unittest discovery for ComfyUI-RookieUI.")
    parser.add_argument("--start-dir", default="tests")
    parser.add_argument("--pattern", default="test_*.py")
    parser.add_argument("--top-level-dir", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root_dir = pathlib.Path(__file__).resolve().parents[1]
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=str(root_dir / args.start_dir),
        pattern=args.pattern,
        top_level_dir=args.top_level_dir or str(root_dir),
    )
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
