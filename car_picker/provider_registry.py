"""The publication-safe Provider Registry and its JSONL persistence boundary."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Literal, Self, TypeAlias
from urllib.parse import urlsplit

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)


ProviderId: TypeAlias = Annotated[
    str,
    StringConstraints(
        min_length=1,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    ),
]
InactiveReason: TypeAlias = Literal["deferred", "ineligible", "blocked"]
ProviderStatus: TypeAlias = Literal["active", "inactive"]
_HTTPS_URL_PATTERN = r"^https://[^@/?#\s]+(?:/[^?#\s]*)?$"


def _validate_public_https_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
    except ValueError as error:
        raise ValueError("provider url must be a valid HTTPS URL") from error
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "provider url must be an HTTPS website URL without credentials, query, or fragment"
        )
    return value


HttpsUrl: TypeAlias = Annotated[
    str,
    StringConstraints(min_length=1, pattern=_HTTPS_URL_PATTERN),
    AfterValidator(_validate_public_https_url),
]


class RegistryInvalid(ValueError):
    """The persisted Provider Registry is missing, malformed, or inconsistent."""


class ProviderRecordInvalid(ValueError):
    """A proposed Provider record is not a strict publication-safe record."""


class _ProviderBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: ProviderId
    name: str
    url: HttpsUrl

    @field_validator("name")
    @classmethod
    def name_must_be_non_empty(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("provider name must be a non-empty trimmed string")
        return value

    @field_validator("url")
    @classmethod
    def url_must_be_public_https(cls, value: str) -> str:
        return _validate_public_https_url(value)


class ActiveProvider(_ProviderBase):
    """One active, publication-safe Provider record."""

    status: Literal["active"]


class InactiveProvider(_ProviderBase):
    """One inactive Provider record with its current reason and explanation."""

    status: Literal["inactive"]
    reason: InactiveReason
    explanation: str

    @field_validator("explanation")
    @classmethod
    def explanation_must_be_non_empty(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError(
                "inactive provider explanation must be a non-empty trimmed string"
            )
        return value


ProviderRecord: TypeAlias = Annotated[
    ActiveProvider | InactiveProvider,
    Field(discriminator="status"),
]


class ProviderRegistrySnapshot(BaseModel):
    """An immutable, ordered view of the complete Provider Registry."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    providers: tuple[ProviderRecord, ...]

    @model_validator(mode="after")
    def provider_ids_must_be_unique(self) -> Self:
        ids = [provider.id for provider in self.providers]
        if len(ids) != len(set(ids)):
            raise ValueError("provider registry contains duplicate provider IDs")
        return self


_PROVIDER_RECORD_ADAPTER = TypeAdapter(ProviderRecord)


class ProviderRegistry:
    """Open, inspect, and later atomically replace a Provider Registry."""

    def __init__(self, path: Path, snapshot: ProviderRegistrySnapshot) -> None:
        self._path = path
        self._snapshot = snapshot

    @classmethod
    def open(cls, path: Path) -> Self:
        """Open and validate one ordered JSONL Provider Registry."""
        return cls(path, _read_snapshot(path))

    def snapshot(self) -> ProviderRegistrySnapshot:
        """Return the current immutable ordered Registry view."""
        return self._snapshot

    def put(
        self,
        record: ProviderRecord | Mapping[str, object],
    ) -> ProviderRegistrySnapshot:
        """Validate and atomically replace one existing complete Provider record."""
        checked_record = _validate_record(record)
        providers = list(self._snapshot.providers)
        for index, current in enumerate(providers):
            if current.id == checked_record.id:
                providers[index] = checked_record
                break
        else:
            raise ProviderRecordInvalid(
                f"Provider ID {checked_record.id!r} is not in the Provider Registry"
            )

        try:
            next_snapshot = ProviderRegistrySnapshot(providers=tuple(providers))
        except ValidationError as error:
            raise ProviderRecordInvalid(
                f"Provider Registry update is invalid: {error}"
            ) from error
        _write_snapshot(self._path, next_snapshot)
        self._snapshot = next_snapshot
        return next_snapshot


def _read_snapshot(path: Path) -> ProviderRegistrySnapshot:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise RegistryInvalid(
            f"cannot read Provider Registry at {path}: {error}"
        ) from error

    records: list[ProviderRecord] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            raise RegistryInvalid(
                f"Provider Registry line {line_number} must contain one JSON object"
            )
        try:
            value = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
        except (ValueError, json.JSONDecodeError) as error:
            raise RegistryInvalid(
                f"Provider Registry line {line_number} is not valid JSON: {error}"
            ) from error
        try:
            records.append(_PROVIDER_RECORD_ADAPTER.validate_python(value))
        except ValidationError as error:
            raise RegistryInvalid(
                f"Provider Registry line {line_number} is not a valid Provider record"
            ) from error

    try:
        return ProviderRegistrySnapshot(providers=tuple(records))
    except ValidationError as error:
        raise RegistryInvalid(f"Provider Registry is invalid: {error}") from error


def _validate_record(
    record: ProviderRecord | Mapping[str, object],
) -> ProviderRecord:
    try:
        return _PROVIDER_RECORD_ADAPTER.validate_python(record)
    except ValidationError as error:
        raise ProviderRecordInvalid(
            "Provider update must be one complete active or inactive record"
        ) from error


def _write_snapshot(path: Path, snapshot: ProviderRegistrySnapshot) -> None:
    temporary_path: Path | None = None
    try:
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
            for provider in snapshot.providers:
                json.dump(
                    provider.model_dump(mode="json"),
                    temporary_file,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    except OSError as error:
        raise RegistryInvalid(
            f"cannot atomically replace Provider Registry at {path}: {error}"
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _reject_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> Mapping[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON member {key!r}")
        value[key] = item
    return value


__all__ = [
    "ActiveProvider",
    "InactiveProvider",
    "InactiveReason",
    "ProviderId",
    "ProviderRecord",
    "ProviderRegistry",
    "ProviderRegistrySnapshot",
    "ProviderStatus",
    "ProviderRecordInvalid",
    "RegistryInvalid",
]
