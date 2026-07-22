from __future__ import annotations

import argparse
from pathlib import Path

from car_picker.publication import build_site


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="car-picker",
        description="Build the static evidence-backed leasing catalogue.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    build = subcommands.add_parser("build-site", help="Build a static catalogue site.")
    build.add_argument("--dataset", required=True, type=Path, help="Canonical catalogue dataset JSON.")
    build.add_argument("--output", required=True, type=Path, help="Static site output directory.")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.command == "build-site":
        if arguments.output.name != "site":
            raise SystemExit("--output must name a site directory so generated artifacts stay ignored")
        build_site(arguments.dataset, arguments.output)


if __name__ == "__main__":
    main()
