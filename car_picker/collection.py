from __future__ import annotations

import json
import os
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from car_picker.fleasing import FleasingAdapter, TextHttpClient
from car_picker.terminalen import TerminalenAdapter


FLEASING_CATALOGUE_URL = "https://fleasing.dk/biler/"
FLEASING_DESIGNATED_SOURCE = "Fleasing passenger-car catalogue and linked detail pages"
TERMINALEN_CATALOGUE_URL = "https://www.terminalen.dk/nye-biler/hyundai"
TERMINALEN_DESIGNATED_SOURCE = "Terminalen Hyundai model price pages and paired page API responses"
PROVIDER_DESIGNATED_SOURCES = {
    "Fleasing": FLEASING_DESIGNATED_SOURCE,
    "Terminalen": TERMINALEN_DESIGNATED_SOURCE,
}
PROVIDER_NAMES = tuple(PROVIDER_DESIGNATED_SOURCES)


class UrlLibHttpClient(TextHttpClient):
    """HTTP boundary for a designated source; fetched documents are never persisted."""

    def get_text(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": "car-picker owner refresh"})
        with urlopen(request, timeout=30) as response:  # noqa: S310 - URL is validated by the CLI boundary.
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset)


def refresh_catalogue(
    dataset_path: Path,
    *,
    collect_fleasing: Callable[[], list[dict[str, Any]]],
    collect_terminalen: Callable[[], list[dict[str, Any]]],
    generated_at: Callable[[], str],
    sleep: Callable[[float], None],
    active_providers: tuple[str, ...] = PROVIDER_NAMES,
    ended_providers: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Atomically replace the complete enabled-provider catalogue after every provider succeeds."""
    fleasing_candidates = (
        collect_with_retries("Fleasing", collect_fleasing, sleep)
        if "Fleasing" in active_providers
        else []
    )
    terminalen_candidates = (
        collect_with_retries("Terminalen", collect_terminalen, sleep)
        if "Terminalen" in active_providers
        else []
    )
    timestamp = generated_at()
    dataset = complete_catalogue_dataset(
        fleasing_candidates,
        terminalen_candidates,
        timestamp,
        active_providers=active_providers,
        ended_providers=ended_providers or [],
    )
    validate_complete_catalogue_dataset(dataset)
    write_json_atomically(dataset_path, dataset)
    return dataset


def collect_with_retries(
    provider_name: str,
    collect: Callable[[], list[dict[str, Any]]],
    sleep: Callable[[float], None],
) -> list[dict[str, Any]]:
    """Allow the initial request and at most two retry attempts with bounded backoff."""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            return collect()
        except Exception as error:
            last_error = error
            if attempt == 2:
                break
            sleep(float(2**attempt))
    raise RuntimeError(f"{provider_name} collection failed after two retries") from last_error


def complete_catalogue_dataset(
    fleasing_candidates: list[dict[str, Any]],
    terminalen_candidates: list[dict[str, Any]],
    generated_at: str,
    *,
    active_providers: tuple[str, ...] = PROVIDER_NAMES,
    ended_providers: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    candidates_by_provider = {
        "Fleasing": fleasing_candidates,
        "Terminalen": terminalen_candidates,
    }
    return {
        "schemaVersion": "catalogue-dataset/v1",
        "generatedAt": generated_at,
        "coverage": {
            "providers": [
                coverage_provider(name, PROVIDER_DESIGNATED_SOURCES[name], candidates_by_provider[name])
                for name in active_providers
            ],
        },
        "coverageEnded": ended_providers or [],
        "catalogueOffers": [
            candidate
            for name in active_providers
            for candidate in candidates_by_provider[name]
        ],
    }


def coverage_provider(name: str, designated_source: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "name": name,
        "designatedSource": designated_source,
        "quarantinedCandidateCount": sum(candidate.get("admissionStatus") == "quarantined" for candidate in candidates),
    }


def validate_complete_catalogue_dataset(dataset: dict[str, Any]) -> None:
    offers = dataset.get("catalogueOffers")
    coverage = dataset.get("coverage")
    provider_rows = coverage.get("providers") if isinstance(coverage, dict) else None
    ended_rows = dataset.get("coverageEnded")
    if not isinstance(offers, list) or not isinstance(provider_rows, list) or not isinstance(ended_rows, list):
        raise ValueError("complete catalogue dataset requires coverage and catalogue offers")
    provider_names = [
        provider.get("name")
        for provider in provider_rows
        if isinstance(provider, dict)
    ]
    if (
        len(provider_names) != len(provider_rows)
        or len(provider_names) != len(set(provider_names))
        or any(name not in PROVIDER_NAMES for name in provider_names)
    ):
        raise ValueError("complete catalogue dataset has invalid covered providers")
    ended_names: set[str] = set()
    for ended_provider in ended_rows:
        if (
            not isinstance(ended_provider, dict)
            or set(ended_provider) != {"name", "coverageEndedAt"}
            or ended_provider.get("name") not in PROVIDER_NAMES
            or not isinstance(ended_provider.get("coverageEndedAt"), str)
            or not ended_provider["coverageEndedAt"]
        ):
            raise ValueError("complete catalogue dataset has invalid ended provider coverage")
        ended_names.add(ended_provider["name"])
    if ended_names.intersection(provider_names):
        raise ValueError("a provider cannot be both covered and ended")
    providers = {name: 0 for name in provider_names}
    identities: set[str] = set()
    for offer in offers:
        if not isinstance(offer, dict):
            raise ValueError("catalogue offer must be an object")
        provider = offer.get("provider")
        identity = offer.get("offerIdentity")
        if provider not in providers or not isinstance(identity, str) or not identity or identity in identities:
            raise ValueError("catalogue offers require unique identities from each covered provider")
        if offer.get("admissionStatus") not in {"admitted", "quarantined"}:
            raise ValueError("catalogue offer has an invalid admission status")
        validate_candidate(offer)
        providers[provider] += 1
        identities.add(identity)
    if providers and not all(providers.values()):
        raise ValueError("complete catalogue dataset requires every covered provider")


def validate_candidate(candidate: dict[str, Any]) -> None:
    """Reject partial candidates before they can replace the active full dataset."""
    required_facts = (
        "vehicleSpecification",
        "privateConsumerEligibility",
        "passengerCarScope",
        "currentAvailability",
        "supportedLeasingForm",
        "advertisedMonthlyPayment",
        "termMonths",
    )
    for name in required_facts:
        fact = candidate.get(name)
        if not isinstance(fact, dict) or fact.get("state") not in {
            "known",
            "not_stated",
            "unclear",
            "conflicting",
            "not_applicable",
        }:
            raise ValueError(f"catalogue offer requires a valid {name} fact")
        evidence = fact.get("evidence")
        if (
            not isinstance(evidence, dict)
            or not isinstance(evidence.get("sourceUrl"), str)
            or not isinstance(evidence.get("wording"), str)
        ):
            raise ValueError(f"catalogue offer {name} fact requires evidence")
    events = candidate.get("baseCashFlowStream")
    if not isinstance(events, list) or not events:
        raise ValueError("catalogue offer requires a base cash-flow stream")
    metadata = candidate.get("sourceMetadata")
    if (
        not isinstance(metadata, dict)
        or not isinstance(metadata.get("documents"), list)
        or not metadata["documents"]
    ):
        raise ValueError("catalogue offer requires source documents")


def refresh_all_providers(
    dataset_path: Path,
    fleasing_catalogue_url: str = FLEASING_CATALOGUE_URL,
    terminalen_catalogue_url: str = TERMINALEN_CATALOGUE_URL,
    http_client: TextHttpClient | None = None,
    *,
    active_providers: tuple[str, ...] = PROVIDER_NAMES,
    ended_providers: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Collect enabled providers in source order into one generation and atomic replacement."""
    client = http_client or UrlLibHttpClient()
    return refresh_catalogue(
        dataset_path,
        collect_fleasing=lambda: FleasingAdapter(client, now()).collect(fleasing_catalogue_url),
        collect_terminalen=lambda: TerminalenAdapter(client, now()).collect(terminalen_catalogue_url),
        generated_at=now,
        sleep=time.sleep,
        active_providers=active_providers,
        ended_providers=ended_providers,
    )


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def write_json_atomically(path: Path, value: dict[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)
        json.dump(value, temporary_file, ensure_ascii=False, separators=(",", ":"))
    try:
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
