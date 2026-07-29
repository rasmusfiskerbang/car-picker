from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from pydantic import JsonValue

from car_picker.collection import write_json_atomically
from car_picker.provider_scope import CoveredProvider, PROVIDER_NAMES


DEFAULT_PROVIDER_CONTROL = Path("config/provider-control.json")


def read_provider_control(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read provider control at {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError("provider control must be an object")
    validate_provider_control(value)
    return value


def validate_provider_control(control: Mapping[str, Any]) -> None:
    if control.get("schemaVersion") != "provider-control/v1":
        raise ValueError("provider control requires schemaVersion provider-control/v1")
    providers = control.get("providers")
    if not isinstance(providers, list) or len(providers) != len(PROVIDER_NAMES):
        raise ValueError("provider control must contain every covered provider")
    for expected_name, provider in zip(PROVIDER_NAMES, providers, strict=True):
        if (
            not isinstance(provider, dict)
            or provider.get("name") != expected_name
            or not isinstance(provider.get("retrievalEnabled"), bool)
            or set(provider) != {"name", "retrievalEnabled"}
        ):
            raise ValueError("provider control has an invalid provider entry")
    withdrawals = control.get("withdrawals")
    if not isinstance(withdrawals, list):
        raise ValueError("provider control withdrawals must be an array")
    withdrawn_names: set[str] = set()
    for withdrawal in withdrawals:
        validate_withdrawal_record(withdrawal)
        provider_name = withdrawal["provider"]
        if provider_name in withdrawn_names:
            raise ValueError("provider control has duplicate withdrawal records")
        withdrawn_names.add(provider_name)
    disabled_names = {
        provider["name"] for provider in providers if not provider["retrievalEnabled"]
    }
    if withdrawn_names != disabled_names:
        raise ValueError(
            "every disabled covered provider requires exactly one withdrawal record"
        )


def validate_withdrawal_record(value: JsonValue) -> None:
    if not isinstance(value, dict):
        raise ValueError("withdrawal record must be an object")
    required_strings = (
        "provider",
        "receivedAt",
        "authenticationNote",
        "retrievalDisabledAt",
        "deadlineAt",
    )
    if (
        not all(
            isinstance(value.get(field), str) and value.get(field)
            for field in required_strings
        )
        or value.get("provider") not in PROVIDER_NAMES
    ):
        raise ValueError("withdrawal record is missing required operational facts")
    for field in (
        "receivedAt",
        "retrievalDisabledAt",
        "deadlineAt",
        "refreshCompletedAt",
        "siteBuildCompletedAt",
    ):
        if field in value:
            parse_timestamp(value.get(field), field)
    if "completedWithinDeadline" in value and not isinstance(
        value.get("completedWithinDeadline"), bool
    ):
        raise ValueError("completedWithinDeadline must be a boolean")
    if ("siteBuildCompletedAt" in value) != ("completedWithinDeadline" in value):
        raise ValueError("site build completion requires a deadline result")


def active_provider_names(control: Mapping[str, Any]) -> tuple[CoveredProvider, ...]:
    return tuple(
        cast(CoveredProvider, provider["name"])
        for provider in control["providers"]
        if provider["retrievalEnabled"]
    )


def coverage_ended_facts(control: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "name": withdrawal["provider"],
            "coverageEndedAt": withdrawal["retrievalDisabledAt"],
        }
        for withdrawal in control["withdrawals"]
    ]


def withdraw_provider(
    path: Path,
    provider_name: str,
    received_at: str,
    authentication_note: str,
    *,
    retrieval_disabled_at: str | None = None,
) -> dict[str, Any]:
    control = read_provider_control(path)
    if provider_name not in PROVIDER_NAMES:
        raise ValueError(f"unsupported covered provider: {provider_name}")
    provider = next(row for row in control["providers"] if row["name"] == provider_name)
    if not provider["retrievalEnabled"]:
        raise ValueError(f"{provider_name} retrieval is already disabled")
    received = parse_timestamp(received_at, "receivedAt")
    disabled_at = retrieval_disabled_at or current_timestamp()
    parse_timestamp(disabled_at, "retrievalDisabledAt")
    if not authentication_note.strip():
        raise ValueError("authentication note must be non-empty")
    provider["retrievalEnabled"] = False
    control["withdrawals"].append(
        {
            "provider": provider_name,
            "receivedAt": format_timestamp(received),
            "authenticationNote": authentication_note.strip(),
            "retrievalDisabledAt": disabled_at,
            "deadlineAt": format_timestamp(received + timedelta(hours=24)),
        }
    )
    validate_provider_control(control)
    write_json_atomically(path, control)
    return control


def record_refresh_completion(path: Path, completed_at: str) -> None:
    record_completion(path, "refreshCompletedAt", completed_at)


def record_site_build_completion(path: Path, completed_at: str) -> None:
    control = read_provider_control(path)
    if any(
        "refreshCompletedAt" not in withdrawal for withdrawal in control["withdrawals"]
    ):
        raise ValueError(
            "provider withdrawal requires a completed catalogue refresh before the site build"
        )
    completed = parse_timestamp(completed_at, "siteBuildCompletedAt")
    missed_deadline = False
    changed = False
    for withdrawal in control["withdrawals"]:
        if "siteBuildCompletedAt" in withdrawal:
            continue
        withdrawal["siteBuildCompletedAt"] = completed_at
        withdrawal["completedWithinDeadline"] = completed <= parse_timestamp(
            withdrawal["deadlineAt"], "deadlineAt"
        )
        missed_deadline = missed_deadline or not withdrawal["completedWithinDeadline"]
        changed = True
    if changed:
        validate_provider_control(control)
        write_json_atomically(path, control)
    if missed_deadline:
        raise ValueError(
            "completed static site missed the 24-hour provider-withdrawal deadline"
        )


def record_completion(
    path: Path,
    field_name: str,
    completed_at: str,
    *,
    control: dict[str, Any] | None = None,
) -> None:
    control = control or read_provider_control(path)
    parse_timestamp(completed_at, field_name)
    changed = False
    for withdrawal in control["withdrawals"]:
        if field_name not in withdrawal:
            withdrawal[field_name] = completed_at
            changed = True
    if changed:
        validate_provider_control(control)
        write_json_atomically(path, control)


def validate_dataset_for_withdrawals(
    dataset_path: Path, control: Mapping[str, Any]
) -> None:
    withdrawals = control["withdrawals"]
    if not withdrawals:
        return
    try:
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"Cannot read canonical catalogue dataset at {dataset_path}: {error}"
        ) from error
    if not isinstance(dataset, dict):
        raise ValueError("canonical catalogue dataset must be an object")
    if any("refreshCompletedAt" not in withdrawal for withdrawal in withdrawals):
        raise ValueError(
            "provider withdrawal requires a completed catalogue refresh before the site build"
        )
    pending_withdrawals = [
        withdrawal
        for withdrawal in withdrawals
        if "siteBuildCompletedAt" not in withdrawal
    ]
    completed_generations = {
        withdrawal["refreshCompletedAt"] for withdrawal in pending_withdrawals
    }
    if pending_withdrawals and (
        len(completed_generations) != 1
        or dataset.get("generatedAt") not in completed_generations
    ):
        raise ValueError(
            "site build dataset is not the completed catalogue refresh for the provider withdrawal"
        )
    if dataset.get("coverageEnded") != coverage_ended_facts(control):
        raise ValueError(
            "site build dataset does not retain the current ended-coverage facts"
        )
    withdrawn_names = {withdrawal["provider"] for withdrawal in withdrawals}
    offers = dataset.get("catalogueOffers")
    quarantined = dataset.get("quarantinedCandidates")
    coverage = dataset.get("coverage")
    providers = coverage.get("providers") if isinstance(coverage, dict) else None
    if (
        not isinstance(offers, list)
        or not isinstance(quarantined, list)
        or not isinstance(providers, list)
        or any(
            isinstance(offer, dict) and offer.get("provider") in withdrawn_names
            for offer in offers
        )
        or any(
            isinstance(candidate, dict) and candidate.get("provider") in withdrawn_names
            for candidate in quarantined
        )
        or any(
            isinstance(provider, dict) and provider.get("name") in withdrawn_names
            for provider in providers
        )
    ):
        raise ValueError("site build dataset still contains a withdrawn provider")


def parse_timestamp(value: JsonValue, name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be an ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO 8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must include a UTC offset")
    return parsed.astimezone(UTC)


def format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def current_timestamp() -> str:
    return format_timestamp(datetime.now(UTC))
