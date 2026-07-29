from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

from car_picker.provider_scope import CoveredProvider, PROVIDER_NAMES


DEFAULT_PROVIDER_ACCESS = Path("config/provider-access.json")


def read_provider_access(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read provider access at {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError("provider access must be an object")
    validate_provider_access(value)
    return value


def validate_provider_access(access: Mapping[str, Any]) -> None:
    if access.get("schemaVersion") != "provider-access/v1":
        raise ValueError("provider access requires schemaVersion provider-access/v1")
    providers = access.get("providers")
    if not isinstance(providers, list) or len(providers) != len(PROVIDER_NAMES):
        raise ValueError("provider access must contain every covered provider")
    for expected_name, provider in zip(PROVIDER_NAMES, providers, strict=True):
        if not isinstance(provider, dict):
            raise ValueError("provider access has an invalid provider entry")
        checked_at = provider.get("checkedAt")
        source_audit = provider.get("sourceAudit")
        if (
            provider.get("name") != expected_name
            or provider.get("decision") not in {"allowed", "paused", "blocked"}
            or not isinstance(checked_at, str)
            or not isinstance(source_audit, str)
            or not source_audit
            or set(provider) != {"name", "decision", "checkedAt", "sourceAudit"}
        ):
            raise ValueError("provider access has an invalid provider entry")
        try:
            date.fromisoformat(checked_at)
        except ValueError as error:
            raise ValueError(
                "provider access checkedAt must be an ISO 8601 date"
            ) from error


def validate_access_before_refresh(
    access: Mapping[str, Any], active_providers: tuple[CoveredProvider, ...]
) -> None:
    decisions = {
        provider["name"]: provider["decision"] for provider in access["providers"]
    }
    for provider_name in active_providers:
        if decisions[provider_name] != "allowed":
            raise ValueError(
                f"{provider_name} provider access decision must be allowed before refresh"
            )
