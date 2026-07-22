from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from car_picker.fleasing import FleasingAdapter, TextHttpClient


FLEASING_CATALOGUE_URL = "https://fleasing.dk/biler/"
FLEASING_DESIGNATED_SOURCE = "Fleasing passenger-car catalogue and linked detail pages"


class UrlLibHttpClient(TextHttpClient):
    """HTTP boundary for a designated source; fetched documents are never persisted."""

    def get_text(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": "car-picker owner refresh"})
        with urlopen(request, timeout=30) as response:  # noqa: S310 - URL is validated by the CLI boundary.
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset)


def refresh_fleasing(
    dataset_path: Path,
    catalogue_url: str = FLEASING_CATALOGUE_URL,
    http_client: TextHttpClient | None = None,
) -> None:
    """Build and atomically replace Fleasing's current catalogue dataset."""
    retrieved_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    candidates = FleasingAdapter(http_client or UrlLibHttpClient(), retrieved_at).collect(catalogue_url)
    dataset = catalogue_dataset(candidates, retrieved_at)
    write_json_atomically(dataset_path, dataset)


def catalogue_dataset(candidates: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    quarantined_count = sum(candidate["admissionStatus"] == "quarantined" for candidate in candidates)
    return {
        "schemaVersion": "catalogue-dataset/v1",
        "generatedAt": generated_at,
        "coverage": {
            "providers": [
                {
                    "name": "Fleasing",
                    "designatedSource": FLEASING_DESIGNATED_SOURCE,
                    "quarantinedCandidateCount": quarantined_count,
                }
            ]
        },
        "catalogueOffers": candidates,
    }


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
