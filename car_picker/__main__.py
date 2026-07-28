from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from car_picker.collection import FLEASING_CATALOGUE_URL, TERMINALEN_CATALOGUE_URL, refresh_all_providers
from car_picker.comparison import reconcile_provider_advertised_aggregate
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
    complete_refresh = subcommands.add_parser("refresh-catalogue", help="Refresh the complete covered-provider catalogue.")
    complete_refresh.add_argument("--dataset", required=True, type=Path, help="Active catalogue dataset JSON.")
    complete_refresh.add_argument("--fleasing-catalogue-url", default=FLEASING_CATALOGUE_URL)
    complete_refresh.add_argument("--terminalen-catalogue-url", default=TERMINALEN_CATALOGUE_URL)
    diagnose = subcommands.add_parser("diagnose-aggregates", help="Diagnose provider aggregate reconciliation.")
    diagnose.add_argument("--dataset", required=True, type=Path, help="Canonical catalogue dataset JSON.")
    diagnose.add_argument("--offer", help="One offer identity to diagnose; omit for every offer.")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.command == "build-site":
        if arguments.output.name != "site":
            raise SystemExit("--output must name a site directory so generated artifacts stay ignored")
        build_site(arguments.dataset, arguments.output)
    elif arguments.command == "refresh-catalogue":
        validate_fleasing_catalogue_url(arguments.fleasing_catalogue_url)
        validate_terminalen_catalogue_url(arguments.terminalen_catalogue_url)
        dataset = refresh_all_providers(arguments.dataset, arguments.fleasing_catalogue_url, arguments.terminalen_catalogue_url)
        print(refresh_reconciliation_summary(dataset))
    elif arguments.command == "diagnose-aggregates":
        print(json.dumps(aggregate_diagnostics(arguments.dataset, arguments.offer), ensure_ascii=False))


def aggregate_diagnostics(dataset_path: Path, offer_identity: str | None) -> dict[str, object]:
    try:
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Cannot read canonical catalogue dataset at {dataset_path}: {error}") from error
    offers = dataset.get("catalogueOffers") if isinstance(dataset, dict) else None
    if not isinstance(offers, list):
        raise SystemExit("Canonical catalogue dataset requires catalogueOffers")
    selected = [offer for offer in offers if isinstance(offer, dict) and (offer_identity is None or offer.get("offerIdentity") == offer_identity)]
    if offer_identity is not None and not selected:
        raise SystemExit(f"No catalogue offer has identity {offer_identity}")
    return {
        "schemaVersion": "aggregate-reconciliation-diagnostics/v1",
        "offers": [reconcile_provider_advertised_aggregate(offer) for offer in selected],
    }


def refresh_reconciliation_summary(dataset: dict[str, object]) -> str:
    offers = dataset.get("catalogueOffers")
    if not isinstance(offers, list):
        return "Provider aggregate reconciliation: no mismatches."
    affected = [
        offer.get("offerIdentity")
        for offer in offers if isinstance(offer, dict)
        and reconcile_provider_advertised_aggregate(offer)["status"] == "mismatch"
    ]
    if affected:
        return f"WARNING provider aggregate reconciliation mismatch: {', '.join(str(identity) for identity in affected)}"
    return "Provider aggregate reconciliation: no mismatches."


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


def validate_terminalen_catalogue_url(catalogue_url: str) -> None:
    parsed = urlparse(catalogue_url)
    if (
        parsed.scheme == "https"
        and parsed.hostname == "www.terminalen.dk"
        and parsed.port is None
        and parsed.path == "/nye-biler/hyundai"
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
    ):
        return
    if (
        parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "localhost"}
        and parsed.port is not None
        and parsed.path == "/terminalen"
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
    ):
        return
    raise SystemExit("--terminalen-catalogue-url must be Terminalen's designated catalogue or a local fixture server")


if __name__ == "__main__":
    main()
