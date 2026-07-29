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

from car_picker.catalogue_model import CatalogueDataset
from car_picker.fleasing import FleasingAdapter, TextHttpClient
from car_picker.provider_scope import (
    CoveredProvider,
    FLEASING_CATALOGUE_URL,
    PROVIDER_DESIGNATED_SOURCES,
    PROVIDER_NAMES,
    TERMINALEN_CATALOGUE_URL,
)
from car_picker.terminalen import TerminalenAdapter


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
    active_providers: tuple[CoveredProvider, ...] = PROVIDER_NAMES,
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
    raise RuntimeError(
        f"{provider_name} collection failed after two retries"
    ) from last_error


def complete_catalogue_dataset(
    fleasing_candidates: list[dict[str, Any]],
    terminalen_candidates: list[dict[str, Any]],
    generated_at: str,
    *,
    active_providers: tuple[CoveredProvider, ...] = PROVIDER_NAMES,
    ended_providers: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    candidates_by_provider = {
        "Fleasing": fleasing_candidates,
        "Terminalen": terminalen_candidates,
    }
    candidates = [
        candidate
        for name in active_providers
        for candidate in candidates_by_provider[name]
    ]
    if any(
        candidate.get("admissionOutcome") not in {"admitted", "quarantined"}
        for candidate in candidates
    ):
        raise ValueError("provider candidate requires a valid admission outcome")
    dataset = {
        "schemaVersion": "catalogue-dataset/v1",
        "generatedAt": generated_at,
        "coverage": {
            "providers": [
                coverage_provider(
                    name,
                    PROVIDER_DESIGNATED_SOURCES[name],
                    candidates_by_provider[name],
                )
                for name in active_providers
            ],
        },
        "coverageEnded": ended_providers or [],
        "catalogueOffers": [
            candidate
            for candidate in candidates
            if candidate.get("admissionOutcome") == "admitted"
        ],
        "quarantinedCandidates": [
            candidate
            for candidate in candidates
            if candidate.get("admissionOutcome") == "quarantined"
        ],
    }
    return CatalogueDataset.model_validate(dataset).model_dump(
        mode="json", by_alias=True
    )


def coverage_provider(
    name: str, designated_source: str, candidates: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "name": name,
        "designatedSource": designated_source,
        "quarantinedCandidateCount": sum(
            candidate.get("admissionOutcome") == "quarantined"
            for candidate in candidates
        ),
    }


def refresh_all_providers(
    dataset_path: Path,
    fleasing_catalogue_url: str = FLEASING_CATALOGUE_URL,
    terminalen_catalogue_url: str = TERMINALEN_CATALOGUE_URL,
    http_client: TextHttpClient | None = None,
    *,
    active_providers: tuple[CoveredProvider, ...] = PROVIDER_NAMES,
    ended_providers: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Collect enabled providers in source order into one generation and atomic replacement."""
    client = http_client or UrlLibHttpClient()
    return refresh_catalogue(
        dataset_path,
        collect_fleasing=lambda: FleasingAdapter(client, now()).collect(
            fleasing_catalogue_url
        ),
        collect_terminalen=lambda: TerminalenAdapter(client, now()).collect(
            terminalen_catalogue_url
        ),
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
