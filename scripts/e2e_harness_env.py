from __future__ import annotations

import argparse
import socket
import sys


def is_port_bindable(port: int) -> bool:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind(("127.0.0.1", int(port)))
        return True
    except OSError:
        return False
    finally:
        listener.close()


def resolve_bindable_port(candidate_ports: list[int]) -> int:
    for candidate in candidate_ports:
        if is_port_bindable(candidate):
            return int(candidate)
    raise RuntimeError("could not find a bindable localhost port for Playwright E2E")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select the first bindable localhost port for the Playwright harness."
    )
    parser.add_argument(
        "--candidate-ports",
        nargs="+",
        type=int,
        required=True,
        help="Ordered candidate ports to probe on 127.0.0.1.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        selected_port = resolve_bindable_port(list(args.candidate_ports))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(selected_port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
