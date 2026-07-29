from __future__ import annotations

import argparse
import json
import socket
from collections.abc import Mapping
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from socketserver import BaseServer
from typing import Any, cast
from urllib.parse import urlparse

from car_picker.catalogue_model import CatalogueDataset
from car_picker.collection import (
    FLEASING_CATALOGUE_URL,
    PROVIDER_NAMES,
    TERMINALEN_CATALOGUE_URL,
    refresh_all_providers,
)
from car_picker.comparison import reconcile_provider_advertised_aggregate
from car_picker.legal_release import DEFAULT_LEGAL_RECORD, validate_legal_release
from car_picker.owner_operations import validate_owner_checkout
from car_picker.provider_access import (
    DEFAULT_PROVIDER_ACCESS,
    read_provider_access,
    validate_access_before_refresh,
)
from car_picker.provider_scope import CoveredProvider
from car_picker.provider_withdrawal import (
    DEFAULT_PROVIDER_CONTROL,
    active_provider_names,
    coverage_ended_facts,
    current_timestamp,
    read_provider_control,
    record_refresh_completion,
    record_site_build_completion,
    validate_dataset_for_withdrawals,
    withdraw_provider,
)
from car_picker.publication import build_site, verify_static_artifact


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="car-picker",
        description="Build the static evidence-backed leasing catalogue.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    build = subcommands.add_parser("build-site", help="Build a static catalogue site.")
    build.add_argument(
        "--dataset", required=True, type=Path, help="Canonical catalogue dataset JSON."
    )
    build.add_argument(
        "--output", required=True, type=Path, help="Static site output directory."
    )
    build.add_argument(
        "--provider-control", default=DEFAULT_PROVIDER_CONTROL, type=Path
    )
    complete_refresh = subcommands.add_parser(
        "refresh-catalogue", help="Refresh the complete covered-provider catalogue."
    )
    complete_refresh.add_argument(
        "--dataset", required=True, type=Path, help="Active catalogue dataset JSON."
    )
    complete_refresh.add_argument(
        "--fleasing-catalogue-url", default=FLEASING_CATALOGUE_URL
    )
    complete_refresh.add_argument(
        "--terminalen-catalogue-url", default=TERMINALEN_CATALOGUE_URL
    )
    complete_refresh.add_argument(
        "--provider-control", default=DEFAULT_PROVIDER_CONTROL, type=Path
    )
    complete_refresh.add_argument(
        "--provider-access", default=DEFAULT_PROVIDER_ACCESS, type=Path
    )
    withdraw = subcommands.add_parser(
        "withdraw-provider",
        help="Record an authenticated provider withdrawal and disable retrieval.",
    )
    withdraw.add_argument("--provider", required=True, choices=PROVIDER_NAMES)
    withdraw.add_argument(
        "--provider-control", default=DEFAULT_PROVIDER_CONTROL, type=Path
    )
    withdraw.add_argument(
        "--received-at",
        required=True,
        help="Authenticated request receipt time as ISO 8601.",
    )
    withdraw.add_argument(
        "--authentication-note",
        required=True,
        help="How the request was authenticated.",
    )
    diagnose = subcommands.add_parser(
        "diagnose-aggregates", help="Diagnose provider aggregate reconciliation."
    )
    diagnose.add_argument(
        "--dataset", required=True, type=Path, help="Canonical catalogue dataset JSON."
    )
    diagnose.add_argument(
        "--offer", help="One offer identity to diagnose; omit for every offer."
    )
    validate = subcommands.add_parser(
        "validate", help="Validate schemas and generated-content boundaries."
    )
    validate.add_argument(
        "--dataset", required=True, type=Path, help="Canonical catalogue dataset JSON."
    )
    validate.add_argument(
        "--repository", default=Path("."), type=Path, help="Git checkout to inspect."
    )
    validate.add_argument(
        "--provider-control", default=DEFAULT_PROVIDER_CONTROL, type=Path
    )
    validate.add_argument(
        "--provider-access", default=DEFAULT_PROVIDER_ACCESS, type=Path
    )
    validate.add_argument("--legal-record", default=DEFAULT_LEGAL_RECORD, type=Path)
    serve = subcommands.add_parser(
        "serve-site", help="Serve a completed static site on the local network."
    )
    serve.add_argument(
        "--site", required=True, type=Path, help="Completed static site directory."
    )
    serve.add_argument(
        "--port", type=int, default=4173, help="TCP port to serve (default: 4173)."
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.command == "build-site":
        validate_site_directory(arguments.output, "--output")
        control = read_provider_control_or_exit(arguments.provider_control)
        validate_dataset_for_withdrawals_or_exit(arguments.dataset, control)
        build_site(arguments.dataset, arguments.output)
        record_site_build_completion_or_exit(
            arguments.provider_control, current_timestamp()
        )
    elif arguments.command == "refresh-catalogue":
        validate_fleasing_catalogue_url(arguments.fleasing_catalogue_url)
        validate_terminalen_catalogue_url(arguments.terminalen_catalogue_url)
        control = read_provider_control_or_exit(arguments.provider_control)
        active_providers = active_provider_names(control)
        access = read_provider_access_or_exit(arguments.provider_access)
        validate_access_before_refresh_or_exit(access, active_providers)
        dataset = refresh_all_providers(
            arguments.dataset,
            arguments.fleasing_catalogue_url,
            arguments.terminalen_catalogue_url,
            active_providers=active_providers,
            ended_providers=coverage_ended_facts(control),
        )
        record_refresh_completion_or_exit(
            arguments.provider_control, dataset["generatedAt"]
        )
        print(refresh_reconciliation_summary(dataset))
    elif arguments.command == "withdraw-provider":
        withdraw_provider_or_exit(
            arguments.provider_control,
            arguments.provider,
            arguments.received_at,
            arguments.authentication_note,
        )
    elif arguments.command == "diagnose-aggregates":
        print(
            json.dumps(
                aggregate_diagnostics(arguments.dataset, arguments.offer),
                ensure_ascii=False,
            )
        )
    elif arguments.command == "validate":
        validate_owner_checkout_or_exit(
            arguments.dataset,
            arguments.repository,
            arguments.provider_control,
            arguments.provider_access,
            arguments.legal_record,
        )
    elif arguments.command == "serve-site":
        serve_site(arguments.site, arguments.port)


def read_provider_control_or_exit(path: Path) -> dict[str, object]:
    try:
        return read_provider_control(path)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error


def read_provider_access_or_exit(path: Path) -> dict[str, Any]:
    try:
        return read_provider_access(path)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error


def validate_access_before_refresh_or_exit(
    access: Mapping[str, Any], active_providers: tuple[CoveredProvider, ...]
) -> None:
    try:
        validate_access_before_refresh(access, active_providers)
    except ValueError as error:
        raise SystemExit(str(error)) from error


def validate_owner_checkout_or_exit(
    dataset_path: Path,
    repository_path: Path,
    provider_control_path: Path,
    provider_access_path: Path,
    legal_record_path: Path,
) -> None:
    try:
        validate_owner_checkout(dataset_path, repository_path, provider_control_path)
        read_provider_access(provider_access_path)
        legal_status = validate_legal_release(
            legal_record_path,
            repository_path,
        )
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(f"Catalogue schema and Git-history validation passed. {legal_status}")


def validate_dataset_for_withdrawals_or_exit(
    dataset_path: Path, control: dict[str, object]
) -> None:
    try:
        validate_dataset_for_withdrawals(dataset_path, control)
    except ValueError as error:
        raise SystemExit(str(error)) from error


def withdraw_provider_or_exit(
    path: Path, provider: str, received_at: str, authentication_note: str
) -> None:
    try:
        withdraw_provider(path, provider, received_at, authentication_note)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(
        f"{provider} retrieval disabled; authenticated withdrawal recorded in {path}."
    )


def record_refresh_completion_or_exit(path: Path, completed_at: str) -> None:
    try:
        record_refresh_completion(path, completed_at)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error


def record_site_build_completion_or_exit(path: Path, completed_at: str) -> None:
    try:
        record_site_build_completion(path, completed_at)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error


def aggregate_diagnostics(
    dataset_path: Path, offer_identity: str | None
) -> dict[str, object]:
    try:
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(
            f"Cannot read canonical catalogue dataset at {dataset_path}: {error}"
        ) from error
    try:
        offers = CatalogueDataset.model_validate(dataset).catalogue_offers
    except ValueError as error:
        raise SystemExit(str(error)) from error
    selected = [
        offer
        for offer in offers
        if offer_identity is None or offer.offer_identity == offer_identity
    ]
    if offer_identity is not None and not selected:
        raise SystemExit(f"No catalogue offer has identity {offer_identity}")
    return {
        "schemaVersion": "aggregate-reconciliation-diagnostics/v1",
        "offers": [
            reconcile_provider_advertised_aggregate(
                offer.model_dump(mode="json", by_alias=True, exclude_none=True)
            )
            for offer in selected
        ],
    }


def refresh_reconciliation_summary(dataset: dict[str, object]) -> str:
    offers = dataset.get("catalogueOffers")
    if not isinstance(offers, list):
        return "Provider aggregate reconciliation: no mismatches."
    affected = [
        offer.get("offerIdentity")
        for offer in offers
        if isinstance(offer, dict)
        and reconcile_provider_advertised_aggregate(cast(Mapping[str, Any], offer))[
            "status"
        ]
        == "mismatch"
    ]
    if affected:
        return f"WARNING provider aggregate reconciliation mismatch: {', '.join(str(identity) for identity in affected)}"
    return "Provider aggregate reconciliation: no mismatches."


def serve_site(site_path: Path, port: int) -> None:
    validate_site_directory(site_path, "--site")
    if not 1 <= port <= 65535:
        raise SystemExit("--port must be between 1 and 65535")
    site_path = site_path.resolve()
    try:
        verify_static_artifact(site_path)
    except (OSError, ValueError) as error:
        raise SystemExit(f"Cannot serve incomplete static artifact: {error}") from error

    class StaticSiteHandler(SimpleHTTPRequestHandler):
        def __init__(
            self,
            request: socket.socket | tuple[bytes, socket.socket],
            client_address: tuple[str, int],
            server: BaseServer,
        ) -> None:
            super().__init__(request, client_address, server, directory=str(site_path))

    with ThreadingHTTPServer(("0.0.0.0", port), StaticSiteHandler) as server:
        print(
            f"Serving completed static artifact on http://0.0.0.0:{port}/", flush=True
        )
        server.serve_forever()


def validate_site_directory(path: Path, option: str) -> None:
    if path.name != "site":
        raise SystemExit(
            f"{option} must name a site directory so generated artifacts stay ignored"
        )


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
    raise SystemExit(
        "--catalogue-url must be Fleasing's designated catalogue or a local fixture server"
    )


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
    raise SystemExit(
        "--terminalen-catalogue-url must be Terminalen's designated catalogue or a local fixture server"
    )


if __name__ == "__main__":
    main()
