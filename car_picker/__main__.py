from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlparse

from car_picker.collection import FLEASING_CATALOGUE_URL, refresh_fleasing
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
    refresh = subcommands.add_parser("refresh-fleasing", help="Refresh Fleasing's bounded first-party catalogue.")
    refresh.add_argument("--dataset", required=True, type=Path, help="Active catalogue dataset JSON.")
    refresh.add_argument(
        "--catalogue-url",
        default=FLEASING_CATALOGUE_URL,
        help="Fleasing catalogue URL; loopback URLs are accepted only for fixture-backed checks.",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.command == "build-site":
        if arguments.output.name != "site":
            raise SystemExit("--output must name a site directory so generated artifacts stay ignored")
        build_site(arguments.dataset, arguments.output)
    if arguments.command == "refresh-fleasing":
        validate_fleasing_catalogue_url(arguments.catalogue_url)
        refresh_fleasing(arguments.dataset, arguments.catalogue_url)


def validate_fleasing_catalogue_url(catalogue_url: str) -> None:
    parsed = urlparse(catalogue_url)
    if (
        parsed.scheme == "https"
        and parsed.hostname == "fleasing.dk"
        and parsed.port is None
        and parsed.path == "/biler/"
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
    ):
        return
    if (
        parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "localhost"}
        and parsed.port is not None
        and parsed.path == "/biler/"
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
    ):
        return
    raise SystemExit("--catalogue-url must be Fleasing's designated catalogue or a local fixture server")


if __name__ == "__main__":
    main()
