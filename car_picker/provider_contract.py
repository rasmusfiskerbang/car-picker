"""Shared construction rules for provider catalogue candidates."""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import JsonValue

from car_picker.catalogue import UnavailableState


def evidence(source_url: str, wording: str) -> dict[str, str]:
    return {"sourceUrl": source_url, "wording": wording}


def known_fact(value: JsonValue, source_url: str, wording: str) -> dict[str, Any]:
    return {
        "state": "known",
        "value": value,
        "evidence": evidence(source_url, wording),
    }


def unavailable_fact(
    state: UnavailableState, source_url: str, wording: str
) -> dict[str, Any]:
    return {"state": state, "evidence": evidence(source_url, wording)}


def source_document(url: str, content: str, retrieved_at: str) -> dict[str, str]:
    """Identify one fetched source document by URL and exact content."""
    return {
        "sourceUrl": url,
        "contentSha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "retrievedAt": retrieved_at,
    }
