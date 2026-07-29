from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import JsonValue

from car_picker.owner_operations import validate_version_controlled_file


CHANGE_HORIZON = date(2026, 11, 20)
DEFAULT_LEGAL_RECORD = Path("config/consumer-credit-legal-review.json")


def validate_legal_release(
    record_path: Path,
    repository_path: Path,
) -> str:
    release_date = date.today()
    validate_version_controlled_file(repository_path, record_path)
    record = read_legal_record(record_path)
    if set(record) != {"schemaVersion", "changeHorizon", "revalidation"}:
        raise ValueError(
            "consumer-credit legal review has unexpected or missing fields"
        )
    if record.get("schemaVersion") != "consumer-credit-legal-review/v1":
        raise ValueError(
            "consumer-credit legal review has an unsupported schemaVersion"
        )
    if record.get("changeHorizon") != CHANGE_HORIZON.isoformat():
        raise ValueError(
            "consumer-credit legal review must record the 2026-11-20 change horizon"
        )
    if release_date < CHANGE_HORIZON:
        if record.get("revalidation") is not None:
            raise ValueError(
                "pre-transition validation cannot claim post-transition revalidation"
            )
        return (
            f"Legal gate: change horizon {CHANGE_HORIZON.isoformat()}; "
            "post-transition revalidation is pending."
        )
    if record.get("revalidation") is None:
        raise ValueError(
            "release on or after 2026-11-20 requires a completed consumer-credit revalidation"
        )
    reviewed_on, owner_name, signed_on = validate_revalidation(
        record["revalidation"],
        release_date,
    )
    return (
        f"Legal gate: consumer-credit revalidation reviewed {reviewed_on}; "
        f"owner sign-off {owner_name} on {signed_on}."
    )


def read_legal_record(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"Cannot read consumer-credit legal review at {path}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise ValueError("consumer-credit legal review must be an object")
    return value


def parse_date(value: JsonValue, name: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an ISO 8601 date")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO 8601 date") from error


def validate_revalidation(value: JsonValue, release_date: date) -> tuple[str, str, str]:
    if not isinstance(value, dict) or set(value) != {
        "reviewedOn",
        "sources",
        "consumerCreditClassificationConclusion",
        "disclosureRulesConclusion",
        "implementationImpact",
        "ownerSignOff",
    }:
        raise ValueError(
            "completed consumer-credit revalidation has unexpected or missing fields"
        )
    reviewed_on = parse_date(value.get("reviewedOn"), "revalidation reviewedOn")
    if not CHANGE_HORIZON <= reviewed_on <= release_date:
        raise ValueError(
            "revalidation reviewedOn must be on or after the change horizon and no later than release"
        )
    sources = value.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError(
            "completed consumer-credit revalidation requires official sources"
        )
    source_kinds = {validate_source(source, reviewed_on) for source in sources}
    if not {"official_law", "official_guidance"}.issubset(source_kinds):
        raise ValueError(
            "revalidation sources must cover then-current official law and official guidance"
        )
    for field_name in (
        "consumerCreditClassificationConclusion",
        "disclosureRulesConclusion",
        "implementationImpact",
    ):
        require_non_empty_string(value.get(field_name), field_name)
    sign_off = value.get("ownerSignOff")
    if not isinstance(sign_off, dict) or set(sign_off) != {"name", "signedOn"}:
        raise ValueError("consumer-credit revalidation requires dated owner sign-off")
    owner_name = require_non_empty_string(sign_off.get("name"), "ownerSignOff.name")
    signed_on = parse_date(sign_off.get("signedOn"), "ownerSignOff.signedOn")
    if not reviewed_on <= signed_on <= release_date:
        raise ValueError(
            "owner sign-off must be on or after review and no later than release"
        )
    return reviewed_on.isoformat(), owner_name, signed_on.isoformat()


def validate_source(value: JsonValue, reviewed_on: date) -> str:
    if not isinstance(value, dict) or set(value) != {
        "kind",
        "title",
        "publisher",
        "url",
        "checkedOn",
        "effectiveFrom",
        "effectiveTo",
    }:
        raise ValueError("consumer-credit source has unexpected or missing fields")
    kind = value.get("kind")
    if not isinstance(kind, str) or kind not in {
        "official_law",
        "official_guidance",
    }:
        raise ValueError(
            "consumer-credit source kind must be official_law or official_guidance"
        )
    require_non_empty_string(value.get("title"), "source.title")
    require_non_empty_string(value.get("publisher"), "source.publisher")
    source_url = require_non_empty_string(value.get("url"), "source.url")
    parsed_url = urlparse(source_url)
    if parsed_url.scheme != "https" or not parsed_url.hostname:
        raise ValueError("consumer-credit official source URL must use HTTPS")
    checked_on = parse_date(value.get("checkedOn"), "source.checkedOn")
    if not CHANGE_HORIZON <= checked_on <= reviewed_on:
        raise ValueError(
            "official sources must be checked after the change horizon and no later than review"
        )
    effective_from = parse_date(value.get("effectiveFrom"), "source.effectiveFrom")
    effective_to_value = value.get("effectiveTo")
    effective_to: date | None = None
    if effective_to_value is not None:
        effective_to = parse_date(effective_to_value, "source.effectiveTo")
        if effective_to < effective_from:
            raise ValueError("source effectiveTo cannot precede effectiveFrom")
    if effective_from > reviewed_on or (
        effective_to is not None and effective_to < reviewed_on
    ):
        raise ValueError(
            "consumer-credit official sources must be effective on the review date"
        )
    return kind


def require_non_empty_string(value: JsonValue, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()
