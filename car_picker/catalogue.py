"""The strict, publication-safe Catalogue Dataset interface.

The module owns the Dataset contract and the calculations materialized inside a
Catalogue Offer.  Source adapters and the CLI depend on this interface; they
do not need to know how the contract's invariants are implemented.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from datetime import UTC, datetime
import json
from math import isfinite
from pathlib import Path
from typing import (
    Annotated,
    Any,
    Generic,
    Literal,
    Protocol,
    Self,
    TypeAlias,
    TypeAliasType,
    TypeVar,
)
from urllib.parse import urlsplit

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    model_validator,
)

from car_picker.provider_registry import (
    ActiveProvider,
    ProviderId,
    ProviderRecord,
    ProviderRegistry,
    ProviderRegistrySnapshot,
    RegistryInvalid,
)
from car_picker.json_persistence import write_bytes_atomically, write_json_atomically


NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
_SOURCE_URL_PATTERN = r"^https://[^@/?#\s]+(?:/[^?#\s]*)?(?:\?[^#\s]*)?$"


def _validate_source_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
    except ValueError as error:
        raise ValueError("source URL must be a valid HTTPS URL") from error
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError(
            "source URL must be an HTTPS URL without credentials or fragments"
        )
    return value


SourceUrl: TypeAlias = Annotated[
    str,
    StringConstraints(min_length=1, pattern=_SOURCE_URL_PATTERN),
    AfterValidator(_validate_source_url),
]


StableDiagnosticCode: TypeAlias = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$",
    ),
]
UnavailableState = Literal["not_stated", "unclear", "conflicting", "not_applicable"]
RefreshFailureCategory: TypeAlias = Literal[
    "operational",
    "invalid-input",
    "unexpected-defect",
    "interruption",
]
OfferIdentity = Annotated[
    str,
    StringConstraints(
        min_length=5,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*:[^\s:]+:[^\s:]+$",
    ),
]
_PROVIDER_ID_ADAPTER = TypeAdapter(ProviderId)


def _validate_instant(value: str) -> str:
    if value != value.strip():
        raise ValueError("generation timestamp must not have surrounding whitespace")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise ValueError(
            "generation timestamp must be canonical UTC RFC 3339"
        ) from error
    return value


def _validate_trimmed_nonblank_excerpt(value: str) -> str:
    if not value:
        raise ValueError("quarantine evidence excerpt must not be blank")
    if value != value.strip():
        raise ValueError("quarantine evidence excerpt must be trimmed")
    return value


Instant = Annotated[
    NonEmptyString,
    StringConstraints(
        min_length=20,
        max_length=20,
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
    ),
    Field(json_schema_extra={"format": "date-time"}),
    AfterValidator(_validate_instant),
]

PositiveInteger = Annotated[int, Field(gt=0)]
NonNegativeInteger = Annotated[int, Field(ge=0)]
Year = Annotated[int, Field(ge=1000, le=9999)]
PositiveNumber = Annotated[float, Field(gt=0, allow_inf_nan=False)]
NonNegativeDkk = Annotated[float, Field(ge=0, allow_inf_nan=False)]
SignedDkk = Annotated[float, Field(allow_inf_nan=False)]


class CatalogueModel(BaseModel):
    """Strict JSON model base shared by the public Catalogue contract."""

    model_config = ConfigDict(
        alias_generator=lambda name: (
            name.split("_")[0]
            + "".join(part.capitalize() for part in name.split("_")[1:])
        ),
        populate_by_name=False,
        extra="forbid",
        strict=True,
    )


FactValue = TypeVar("FactValue")


class KnownFact(CatalogueModel, Generic[FactValue]):
    state: Literal["known"]
    value: FactValue


class UnavailableFact(CatalogueModel):
    state: UnavailableState


Fact = TypeAliasType(
    "Fact",
    Annotated[KnownFact[FactValue] | UnavailableFact, Field(discriminator="state")],
    type_params=(FactValue,),
)


class BatteryCapacity(CatalogueModel):
    value_kwh: PositiveNumber
    basis: Literal["gross", "usable", "not_stated"]


class ChargingPower(CatalogueModel):
    value_kw: PositiveNumber
    kind: Literal["ac", "dc", "not_stated"]


class SharedVehicleSpecification(CatalogueModel):
    make: NonEmptyString
    model: NonEmptyString
    trim: Fact[NonEmptyString]
    model_year: Fact[Year]
    first_registration_year: Fact[Year]
    body_style: Fact[
        Literal[
            "hatchback",
            "saloon",
            "estate",
            "suv",
            "coupe",
            "convertible",
            "mpv",
            "other",
        ]
    ]
    odometer_km: Fact[NonNegativeInteger]


class CombustionVehicleSpecification(SharedVehicleSpecification):
    kind: Literal["combustion"]
    fuel_type: Literal["gasoline", "diesel"]
    fuel_efficiency_km_per_liter: Fact[PositiveNumber]


class BatteryElectricVehicleSpecification(SharedVehicleSpecification):
    kind: Literal["battery_electric"]
    battery_capacity: Fact[BatteryCapacity]
    wltp_range_km: Fact[PositiveInteger]
    max_charging_power: Fact[ChargingPower]
    charging_time_10_to_80_minutes: Fact[PositiveNumber]


VehicleSpecification: TypeAlias = Annotated[
    CombustionVehicleSpecification | BatteryElectricVehicleSpecification,
    Field(discriminator="kind"),
]


class ServiceArrangement(CatalogueModel):
    category: Literal[
        "service",
        "maintenance",
        "insurance",
        "roadside_assistance",
        "tyres",
        "other",
    ]
    treatment: Literal["included", "optional", "required_external", "excluded"]
    summary: NonEmptyString
    limits: Fact[NonEmptyString]


RefundabilityFact: TypeAlias = Fact[Literal["refundable", "not_refundable"]]


class BaseCashFlowEvent(CatalogueModel):
    key: NonEmptyString
    month: NonNegativeInteger
    kind: Literal[
        "initial_payment",
        "lease_payment",
        "establishment_fee",
        "delivery_fee",
        "deposit",
        "deposit_refund",
        "mandatory_purchase_or_payoff",
        "other",
    ]
    direction: Literal["payment", "receipt"]
    amount: Fact[NonNegativeDkk]
    refundability: RefundabilityFact

    @model_validator(mode="after")
    def validate_direction(self) -> BaseCashFlowEvent:
        if self.kind == "deposit_refund" and self.direction != "receipt":
            raise ValueError("a deposit refund must be an explicit receipt")
        return self


class AdvertisedTotal(CatalogueModel):
    amount_dkk: NonNegativeDkk


class CashFlowFactUnavailableReason(CatalogueModel):
    code: Literal["fact_unavailable"]
    field: Literal["baseCashFlowStream.amount"]
    event_key: NonEmptyString
    fact_state: UnavailableState


UnavailabilityReason: TypeAlias = CashFlowFactUnavailableReason


class ResultValue(CatalogueModel):
    amount_dkk: SignedDkk


class AvailableResult(CatalogueModel):
    state: Literal["available"]
    value: ResultValue


class UnavailableResult(CatalogueModel):
    state: Literal["unavailable"]
    reasons: Annotated[list[UnavailabilityReason], Field(min_length=1)]


MaterializedResult: TypeAlias = Annotated[
    AvailableResult | UnavailableResult,
    Field(discriminator="state"),
]


class QuarantineEvidence(CatalogueModel):
    source_url: SourceUrl
    excerpt: Annotated[
        str,
        StringConstraints(min_length=1, max_length=500),
        AfterValidator(_validate_trimmed_nonblank_excerpt),
    ]


class QuarantineReason(CatalogueModel):
    criterion: Literal[
        "offer_identity",
        "private_consumer_eligibility",
        "private_consumer_amount_admissibility",
        "passenger_car_scope",
        "current_availability",
        "supported_leasing_form",
        "advertised_monthly_payment",
        "upfront_payment",
        "term_months",
        "candidate_shape",
    ]
    state: Literal["not_stated", "unclear", "conflicting"]
    code: StableDiagnosticCode
    evidence: Annotated[list[QuarantineEvidence], Field(min_length=1)]


class QuarantinedCandidate(CatalogueModel):
    offer_identity: OfferIdentity
    provider_id: ProviderId
    canonical_source_url: SourceUrl
    reasons: Annotated[list[QuarantineReason], Field(min_length=1)]

    @model_validator(mode="after")
    def identity_belongs_to_provider(self) -> QuarantinedCandidate:
        _validate_offer_identity_provider(self.offer_identity, self.provider_id)
        return self


class CatalogueOffer(CatalogueModel):
    offer_identity: OfferIdentity
    provider_id: ProviderId
    canonical_offer_url: SourceUrl
    vehicle_specification: VehicleSpecification
    image_urls: list[SourceUrl]
    supported_leasing_form: Literal["financial", "flex", "operational", "hybrid"]
    provider_form_label: NonEmptyString
    term_months: PositiveInteger
    annual_mileage_km: Fact[PositiveInteger]
    normal_end_mechanism: Fact[
        Literal[
            "return_to_provider",
            "designate_third_party_buyer",
            "mandatory_purchase_or_payoff",
            "other",
        ]
    ]
    residual_risk_allocation: Fact[Literal["provider", "lessee", "shared"]]
    service_arrangements: Fact[list[ServiceArrangement]]
    base_cash_flow_stream: Annotated[list[BaseCashFlowEvent], Field(min_length=1)]
    advertised_total: Fact[AdvertisedTotal]
    calculated_total: MaterializedResult
    calculated_monthly_total: MaterializedResult

    @model_validator(mode="after")
    def validate_offer_contract(self) -> CatalogueOffer:
        _validate_offer_identity_provider(self.offer_identity, self.provider_id)

        validate_base_cash_flow_stream(
            self.base_cash_flow_stream,
            self.term_months,
            require_lease_payment=True,
        )

        expected_total, expected_monthly = calculate_catalogue_offer_totals(self)
        if self.calculated_total.model_dump(
            mode="json", by_alias=True
        ) != expected_total.model_dump(
            mode="json", by_alias=True
        ) or self.calculated_monthly_total.model_dump(
            mode="json", by_alias=True
        ) != expected_monthly.model_dump(mode="json", by_alias=True):
            raise ValueError(
                "stored calculated totals do not match base cash-flow facts"
            )
        return self


class CatalogueDataset(CatalogueModel):
    schema_version: Literal["catalogue-dataset/v1"]
    generated_at: Instant
    providers: list[ProviderRecord]
    offers: list[CatalogueOffer]
    quarantined_candidates: list[QuarantinedCandidate]

    @model_validator(mode="after")
    def validate_dataset_graph(self) -> CatalogueDataset:
        provider_ids = [provider.id for provider in self.providers]
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError("Provider IDs must be unique within a Dataset")
        provider_by_id = {provider.id: provider for provider in self.providers}
        active_provider_ids = {
            provider.id for provider in self.providers if provider.status == "active"
        }

        identities: list[str] = []
        for offer in self.offers:
            identities.append(offer.offer_identity)
            if offer.provider_id not in provider_by_id:
                raise ValueError("Catalogue Offers must reference a Dataset Provider")
            if offer.provider_id not in active_provider_ids:
                raise ValueError("Catalogue Offers may reference only active Providers")
        for candidate in self.quarantined_candidates:
            identities.append(candidate.offer_identity)
            if candidate.provider_id not in provider_by_id:
                raise ValueError(
                    "Quarantined Candidates must reference a Dataset Provider"
                )
            if candidate.provider_id not in active_provider_ids:
                raise ValueError(
                    "Quarantined Candidates may reference only active Providers"
                )
        if len(identities) != len(set(identities)):
            raise ValueError("Offer identities must be unique across the Dataset")

        provider_order = {
            provider_id: index for index, provider_id in enumerate(provider_ids)
        }
        offer_order = _provider_order(self.offers, provider_order)
        if offer_order != sorted(offer_order):
            raise ValueError("Catalogue Offers must follow Provider Registry order")
        candidate_order = _provider_order(self.quarantined_candidates, provider_order)
        if candidate_order != sorted(candidate_order):
            raise ValueError(
                "Quarantined Candidates must follow Provider Registry order"
            )
        return self


class CandidateEvidence(CatalogueModel):
    """First-party evidence carried only while a Candidate is transient."""

    source_url: SourceUrl
    wording: NonEmptyString


class KnownCandidateFact(CatalogueModel, Generic[FactValue]):
    """A known source fact with the evidence that establishes its value."""

    state: Literal["known"]
    value: FactValue
    evidence: CandidateEvidence


class UnavailableCandidateFact(CatalogueModel):
    """A source fact whose value is unavailable for a stated reason."""

    state: UnavailableState
    evidence: CandidateEvidence


CandidateFact = TypeAliasType(
    "CandidateFact",
    Annotated[
        KnownCandidateFact[FactValue] | UnavailableCandidateFact,
        Field(discriminator="state"),
    ],
    type_params=(FactValue,),
)


class CandidateAdmissionFacts(CatalogueModel):
    """The complete provider-independent facts needed for admission."""

    private_consumer_eligibility: CandidateFact[bool]
    private_consumer_amount_admissibility: CandidateFact[bool]
    passenger_car_scope: CandidateFact[bool]
    current_availability: CandidateFact[bool]
    supported_leasing_form: CandidateFact[
        Literal["financial", "flex", "operational", "hybrid"]
    ]


class CatalogueCandidate(CatalogueModel):
    """A normalized, evidence-rich Candidate consumed during one refresh."""

    offer_identity: OfferIdentity
    provider_id: ProviderId
    canonical_source_url: SourceUrl
    admission_facts: CandidateAdmissionFacts
    offer: CatalogueOffer | None = None
    # Provider-specific evidence blockers are consumed before publication.
    admission_evidence_failures: list[QuarantineReason] = Field(
        default_factory=list, exclude=True
    )

    @model_validator(mode="after")
    def identity_belongs_to_provider(self) -> CatalogueCandidate:
        _validate_offer_identity_provider(self.offer_identity, self.provider_id)
        if self.offer is not None:
            if self.offer.offer_identity != self.offer_identity:
                raise ValueError(
                    "Candidate Offer Identity must equal nested Offer Identity"
                )
            if self.offer.provider_id != self.provider_id:
                raise ValueError(
                    "Candidate Offer must belong to its Candidate Provider"
                )
        return self


class CatalogueRefreshFailure(CatalogueModel):
    """The validated, safe payload for one failed Catalogue Refresh."""

    category: RefreshFailureCategory
    code: StableDiagnosticCode
    message: NonEmptyString
    provider_id: ProviderId | None = None


class CatalogueRefreshError(ValueError):
    """A safe, classified failure from one complete Catalogue Refresh."""

    def __init__(self, failure: CatalogueRefreshFailure) -> None:
        super().__init__(failure.message)
        self.failure = failure

    @property
    def code(self) -> StableDiagnosticCode:
        return self.failure.code

    @property
    def category(self) -> RefreshFailureCategory:
        return self.failure.category

    @property
    def provider_id(self) -> ProviderId | None:
        return self.failure.provider_id

    @classmethod
    def _from_category(
        cls,
        category: RefreshFailureCategory,
        code: StableDiagnosticCode,
        message: str,
        *,
        provider_id: ProviderId | None = None,
    ) -> Self:
        payload: dict[str, object] = {
            "category": category,
            "code": code,
            "message": message,
        }
        if provider_id is not None:
            payload["providerId"] = provider_id
        return cls(CatalogueRefreshFailure.model_validate(payload))

    @classmethod
    def operational(
        cls,
        code: StableDiagnosticCode,
        message: str,
        *,
        provider_id: ProviderId | None = None,
    ) -> Self:
        return cls._from_category("operational", code, message, provider_id=provider_id)

    @classmethod
    def invalid_input(
        cls,
        code: StableDiagnosticCode,
        message: str,
    ) -> Self:
        return cls._from_category("invalid-input", code, message)

    @classmethod
    def unexpected_defect(
        cls,
        *,
        provider_id: ProviderId | None = None,
    ) -> Self:
        return cls._from_category(
            "unexpected-defect",
            "catalogue.unexpected_defect",
            "Catalogue Refresh encountered an unexpected implementation defect.",
            provider_id=provider_id,
        )

    @classmethod
    def interrupted(cls) -> Self:
        return cls._from_category(
            "interruption",
            "catalogue.refresh_interrupted",
            "Catalogue Refresh was interrupted; the active Catalogue Dataset is unchanged.",
        )


class ProviderAdapter(Protocol):
    """The source-specific collection seam owned by a Catalogue refresh."""

    provider_id: ProviderId

    def collect(self) -> Sequence[CatalogueCandidate]:
        """Collect transient Candidate records in deterministic source order."""


class CatalogueRefreshReport(CatalogueModel):
    """Safe, stable diagnostics for one complete Catalogue Refresh."""

    kind: Literal["catalogue-refresh"]
    generated_at: Instant
    provider_ids: list[ProviderId]
    catalogue_offer_count: NonNegativeInteger
    quarantined_candidate_count: NonNegativeInteger


def _published_catalogue_records(
    dataset: CatalogueDataset,
) -> Iterator[CatalogueOffer | QuarantinedCandidate]:
    yield from dataset.offers
    yield from dataset.quarantined_candidates


class Catalogue:
    """Refresh, open, and inspect the conventional active Catalogue Dataset."""

    def __init__(
        self,
        workspace: Path,
        *,
        adapters: Sequence[ProviderAdapter] = (),
    ) -> None:
        if isinstance(adapters, Mapping):
            raise TypeError(
                "Catalogue adapters must be supplied as a sequence of Provider Adapters"
            )
        resolved_workspace = workspace.resolve()
        self._workspace = resolved_workspace
        self._dataset_path = resolved_workspace / "var" / "catalogue-dataset.json"
        self._registry_path = resolved_workspace / "config" / "provider-registry.jsonl"
        self._adapters: tuple[ProviderAdapter, ...] = tuple(adapters)

    @property
    def dataset_path(self) -> Path:
        return self._dataset_path

    def current(self) -> CatalogueDataset:
        """Read and strictly validate the active Dataset."""
        try:
            raw = json.loads(
                self._dataset_path.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_json_keys,
            )
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
            raise ValueError(
                f"cannot read the active Catalogue Dataset at {self._dataset_path}: {error}"
            ) from error
        try:
            return CatalogueDataset.model_validate(raw)
        except ValueError as error:
            raise ValueError(
                f"active Catalogue Dataset at {self._dataset_path} is invalid: {error}"
            ) from error

    def inspect(
        self, offer_identity: OfferIdentity | None = None
    ) -> CatalogueDataset | CatalogueOffer | QuarantinedCandidate:
        """Return the active Dataset or one exact published catalogue record."""
        dataset = self.current()
        if offer_identity is None:
            return dataset
        for record in _published_catalogue_records(dataset):
            if record.offer_identity == offer_identity:
                return record
        raise LookupError(f"no catalogue record has identity {offer_identity!r}")

    def refresh(self) -> CatalogueRefreshReport:
        """Collect every active Provider and atomically publish one Dataset."""
        snapshot = self._validated_registry_snapshot()
        active_providers = [
            provider
            for provider in snapshot.providers
            if isinstance(provider, ActiveProvider)
        ]
        adapters_by_provider = self._validated_adapter_coverage(
            snapshot.providers,
            active_providers,
        )
        try:
            previous_dataset_bytes = _read_active_dataset_bytes(self._dataset_path)
        except OSError as error:
            raise CatalogueRefreshError.operational(
                "catalogue.dataset_read_failed",
                "The active Catalogue Dataset could not be read safely; no Provider was contacted.",
            ) from error

        offers: list[CatalogueOffer] = []
        quarantined: list[QuarantinedCandidate] = []
        for provider in active_providers:
            adapter = adapters_by_provider[provider.id]
            records = _collect_candidates(adapter, provider.id)
            for record in records:
                try:
                    admitted, candidate = _admit_candidate(record, provider.id)
                except KeyboardInterrupt as error:
                    raise CatalogueRefreshError.interrupted() from error
                except (TypeError, ValueError, ValidationError) as error:
                    raise CatalogueRefreshError.operational(
                        "catalogue.provider_structural_failure",
                        f"Provider {provider.id} collection failed: structurally invalid Candidate data.",
                        provider_id=provider.id,
                    ) from error
                except Exception as error:
                    raise CatalogueRefreshError.unexpected_defect(
                        provider_id=provider.id,
                    ) from error
                if admitted is not None:
                    offers.append(admitted)
                if candidate is not None:
                    quarantined.append(candidate)

        try:
            timestamp = _current_timestamp()
            dataset = CatalogueDataset.model_validate(
                {
                    "schemaVersion": "catalogue-dataset/v1",
                    "generatedAt": timestamp,
                    "providers": list(snapshot.providers),
                    "offers": [
                        offer.model_dump(mode="json", by_alias=True) for offer in offers
                    ],
                    "quarantinedCandidates": [
                        candidate.model_dump(mode="json", by_alias=True)
                        for candidate in quarantined
                    ],
                }
            )
            report = CatalogueRefreshReport.model_validate(
                {
                    "kind": "catalogue-refresh",
                    "generatedAt": dataset.generated_at,
                    "providerIds": [provider.id for provider in active_providers],
                    "catalogueOfferCount": len(dataset.offers),
                    "quarantinedCandidateCount": len(dataset.quarantined_candidates),
                }
            )
        except KeyboardInterrupt as error:
            raise CatalogueRefreshError.interrupted() from error
        except (TypeError, ValueError, ValidationError) as error:
            raise CatalogueRefreshError.operational(
                "catalogue.final_validation_failed",
                "The complete Catalogue Dataset failed final validation.",
            ) from error
        except Exception as error:
            raise CatalogueRefreshError.unexpected_defect() from error

        return _publish_dataset(
            self._dataset_path,
            dataset,
            report,
            previous_dataset_bytes,
        )

    def _validated_registry_snapshot(self) -> ProviderRegistrySnapshot:
        """Validate the conventional workspace and Registry before collection."""
        if not self._workspace.exists() or not self._workspace.is_dir():
            raise CatalogueRefreshError.invalid_input(
                "catalogue.workspace_invalid",
                "Catalogue Refresh requires an existing workspace directory.",
            )
        config_path = self._workspace / "config"
        var_path = self._workspace / "var"
        if config_path.exists() and not config_path.is_dir():
            raise CatalogueRefreshError.invalid_input(
                "catalogue.workspace_invalid",
                "Catalogue Refresh workspace conventions are invalid.",
            )
        if var_path.exists() and not var_path.is_dir():
            raise CatalogueRefreshError.invalid_input(
                "catalogue.workspace_invalid",
                "Catalogue Refresh workspace conventions are invalid.",
            )
        if self._dataset_path.exists() and not self._dataset_path.is_file():
            raise CatalogueRefreshError.invalid_input(
                "catalogue.workspace_invalid",
                "Catalogue Refresh workspace conventions are invalid.",
            )
        try:
            return ProviderRegistry.open(self._registry_path).snapshot()
        except RegistryInvalid as error:
            raise CatalogueRefreshError.invalid_input(
                "catalogue.registry_invalid",
                "The Provider Registry is invalid; no Provider was contacted.",
            ) from error
        except Exception as error:
            raise CatalogueRefreshError.unexpected_defect() from error

    def _validated_adapter_coverage(
        self,
        providers: Sequence[ProviderRecord],
        active_providers: Sequence[ActiveProvider],
    ) -> dict[ProviderId, ProviderAdapter]:
        try:
            adapters_by_provider = _adapters_by_provider(self._adapters)
        except (AttributeError, TypeError, ValueError, ValidationError) as error:
            raise CatalogueRefreshError.invalid_input(
                "catalogue.adapter_invalid",
                "The statically composed Provider Adapters are invalid; no Provider was contacted.",
            ) from error
        registry_provider_ids = {provider.id for provider in providers}
        unknown = sorted(
            provider_id
            for provider_id in adapters_by_provider
            if provider_id not in registry_provider_ids
        )
        if unknown:
            raise CatalogueRefreshError.invalid_input(
                "catalogue.adapter_coverage_invalid",
                "The statically composed Provider Adapters do not match the Provider Registry; no Provider was contacted.",
            )
        missing = [
            provider.id
            for provider in active_providers
            if provider.id not in adapters_by_provider
        ]
        if missing:
            raise CatalogueRefreshError.invalid_input(
                "catalogue.adapter_coverage_invalid",
                "The statically composed Provider Adapters do not cover every active Provider; no Provider was contacted.",
            )
        for adapter in adapters_by_provider.values():
            try:
                collect = getattr(adapter, "collect", None)
            except Exception as error:
                raise CatalogueRefreshError.invalid_input(
                    "catalogue.adapter_invalid",
                    "The statically composed Provider Adapters are invalid; no Provider was contacted.",
                ) from error
            if not callable(collect):
                raise CatalogueRefreshError.invalid_input(
                    "catalogue.adapter_invalid",
                    "The statically composed Provider Adapters are invalid; no Provider was contacted.",
                )
        return adapters_by_provider


def _adapters_by_provider(
    adapters: Sequence[ProviderAdapter],
) -> dict[ProviderId, ProviderAdapter]:
    by_provider: dict[ProviderId, ProviderAdapter] = {}
    for adapter in adapters:
        provider_id = _PROVIDER_ID_ADAPTER.validate_python(
            getattr(adapter, "provider_id")
        )
        if provider_id in by_provider:
            raise ValueError(
                f"cannot refresh the Catalogue: duplicate Provider Adapter for {provider_id}"
            )
        by_provider[provider_id] = adapter
    return by_provider


def _collect_candidates(
    adapter: ProviderAdapter,
    provider_id: ProviderId,
) -> tuple[CatalogueCandidate, ...]:
    try:
        records = adapter.collect()
    except KeyboardInterrupt as error:
        raise CatalogueRefreshError.interrupted() from error
    except OSError as error:
        raise CatalogueRefreshError.operational(
            "catalogue.provider_retrieval_failed",
            f"Provider {provider_id} could not be retrieved safely.",
            provider_id=provider_id,
        ) from error
    except (TypeError, ValueError, ValidationError) as error:
        raise CatalogueRefreshError.operational(
            "catalogue.provider_structural_failure",
            f"Provider {provider_id} returned structurally invalid source data.",
            provider_id=provider_id,
        ) from error
    except Exception as error:
        raise CatalogueRefreshError.unexpected_defect(
            provider_id=provider_id
        ) from error

    if isinstance(records, (str, bytes, bytearray, Mapping)) or not isinstance(
        records, Sequence
    ):
        raise CatalogueRefreshError.operational(
            "catalogue.provider_enumeration_failed",
            f"Provider {provider_id} did not return a complete Candidate enumeration.",
            provider_id=provider_id,
        )
    try:
        return tuple(records)
    except KeyboardInterrupt as error:
        raise CatalogueRefreshError.interrupted() from error
    except Exception as error:
        raise CatalogueRefreshError.operational(
            "catalogue.provider_enumeration_failed",
            f"Provider {provider_id} did not return a complete Candidate enumeration.",
            provider_id=provider_id,
        ) from error


def _admit_candidate(
    record: CatalogueCandidate,
    provider_id: ProviderId,
) -> tuple[CatalogueOffer | None, QuarantinedCandidate | None]:
    if not isinstance(record, CatalogueCandidate):
        raise ValueError("Provider Adapter must return CatalogueCandidate values")
    if record.provider_id != provider_id:
        raise ValueError(
            f"Candidate {record.offer_identity} belongs to Provider "
            f"{record.provider_id}, not Adapter {provider_id}"
        )

    reasons = [
        *record.admission_evidence_failures,
        *_candidate_admission_reasons(record),
    ]
    if record.offer is None and not reasons:
        reasons.append(
            QuarantineReason.model_validate(
                {
                    "criterion": "candidate_shape",
                    "state": "unclear",
                    "code": "candidate-shape.missing-offer",
                    "evidence": [
                        {
                            "sourceUrl": record.canonical_source_url,
                            "excerpt": "Candidate did not contain an Offer payload.",
                        }
                    ],
                }
            )
        )
    if reasons:
        return None, _quarantined_candidate(record, reasons)
    if record.offer is None:
        raise ValueError("admitted Candidate must contain an Offer payload")
    return record.offer, None


def _candidate_admission_reasons(
    candidate: CatalogueCandidate,
) -> list[QuarantineReason]:
    facts = candidate.admission_facts
    ordered_facts = (
        ("private_consumer_eligibility", facts.private_consumer_eligibility),
        (
            "private_consumer_amount_admissibility",
            facts.private_consumer_amount_admissibility,
        ),
        ("passenger_car_scope", facts.passenger_car_scope),
        ("current_availability", facts.current_availability),
        ("supported_leasing_form", facts.supported_leasing_form),
    )
    reasons: list[QuarantineReason] = []
    for criterion, fact in ordered_facts:
        if not isinstance(fact, KnownCandidateFact):
            admitted = False
        elif criterion != "supported_leasing_form":
            admitted = fact.value is True
        else:
            admitted = fact.value is not None
        if admitted:
            continue
        state = (
            "conflicting" if fact.state in {"known", "not_applicable"} else fact.state
        )
        reasons.append(
            QuarantineReason.model_validate(
                {
                    "criterion": criterion,
                    "state": state,
                    "code": f"{criterion.replace('_', '-')}.{state.replace('_', '-')}",
                    "evidence": [
                        {
                            "sourceUrl": fact.evidence.source_url,
                            "excerpt": fact.evidence.wording.strip()[:500].strip(),
                        }
                    ],
                }
            )
        )
    return reasons


def _quarantined_candidate(
    candidate: CatalogueCandidate,
    reasons: Sequence[QuarantineReason],
) -> QuarantinedCandidate:
    return QuarantinedCandidate.model_validate(
        {
            "offerIdentity": candidate.offer_identity,
            "providerId": candidate.provider_id,
            "canonicalSourceUrl": candidate.canonical_source_url,
            "reasons": [
                reason.model_dump(mode="json", by_alias=True) for reason in reasons
            ],
        }
    )


def _current_timestamp() -> str:
    """Return the canonical UTC timestamp used for a completed refresh."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_active_dataset_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _dataset_bytes_equal(path: Path, expected: bytes | None) -> bool:
    try:
        return _read_active_dataset_bytes(path) == expected
    except OSError:
        return False


def _restore_active_dataset_bytes(path: Path, previous: bytes | None) -> None:
    if previous is None:
        path.unlink(missing_ok=True)
    else:
        write_bytes_atomically(path, previous)
    if not _dataset_bytes_equal(path, previous):
        raise OSError("the previous active Catalogue Dataset could not be restored")


def _serialized_dataset_bytes(dataset: CatalogueDataset) -> bytes:
    return json.dumps(
        dataset.model_dump(mode="json", by_alias=True),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _publish_dataset(
    path: Path,
    dataset: CatalogueDataset,
    report: CatalogueRefreshReport,
    previous: bytes | None,
) -> CatalogueRefreshReport:
    """Publish a Dataset and classify only outcomes whose active bytes are known."""
    expected: bytes | None = None
    try:
        expected = _serialized_dataset_bytes(dataset)
        _write_dataset_atomically(path, dataset)
    except BaseException as error:
        if expected is not None and _dataset_bytes_equal(path, expected):
            return report
        _restore_active_dataset_bytes(path, previous)
        if isinstance(error, KeyboardInterrupt):
            raise CatalogueRefreshError.interrupted() from error
        if isinstance(error, OSError):
            raise CatalogueRefreshError.operational(
                "catalogue.dataset_replace_failed",
                "The active Catalogue Dataset could not be replaced; it is unchanged.",
            ) from error
        if isinstance(error, Exception):
            raise CatalogueRefreshError.unexpected_defect() from error
        raise
    return report


def _write_dataset_atomically(path: Path, dataset: CatalogueDataset) -> None:
    write_json_atomically(
        path,
        dataset.model_dump(mode="json", by_alias=True),
    )


def validate_base_cash_flow_stream(
    events: Sequence[BaseCashFlowEvent],
    term_months: int,
    *,
    require_lease_payment: bool = False,
) -> None:
    """Validate event identity, chronology, term bounds, and lease payment shape."""
    if not events or term_months <= 0:
        raise ValueError("a Base Cash-flow Stream must contain at least one event")
    keys = [event.key for event in events]
    if len(keys) != len(set(keys)):
        raise ValueError("base cash-flow event keys must be unique within an Offer")

    previous_month = -1
    lease_payment_count = 0
    for event in events:
        if event.month > term_months:
            raise ValueError("base cash-flow events must fall within the Offer term")
        if event.month < previous_month:
            raise ValueError("base cash-flow events must be chronological")
        previous_month = event.month
        if event.kind == "lease_payment":
            lease_payment_count += 1

    if require_lease_payment and lease_payment_count == 0:
        raise ValueError("an Offer must have at least one lease payment event")


def calculate_catalogue_offer_totals(
    offer: CatalogueOffer,
) -> tuple[MaterializedResult, MaterializedResult]:
    """Recalculate an Offer's signed total and term-normalized total."""
    all_reasons: list[UnavailabilityReason] = []
    nominal_total = 0.0

    for event in offer.base_cash_flow_stream:
        amount = known_fact_value(event.amount)
        if amount is None:
            all_reasons.append(cash_flow_reason(event))
        else:
            nominal_total += _signed_cash_flow_amount(event, amount)

    all_reasons = unique_reasons(all_reasons)
    if all_reasons:
        unavailable = unavailable_result(all_reasons)
        return unavailable, unavailable
    return available_result(nominal_total), available_result(
        nominal_total / offer.term_months
    )


def known_fact_value(value: Fact[FactValue]) -> FactValue | None:
    if isinstance(value, KnownFact):
        return value.value
    return None


def _validate_offer_identity_provider(
    offer_identity: OfferIdentity,
    provider_id: ProviderId,
) -> None:
    if offer_identity.split(":", 1)[0] != provider_id:
        raise ValueError("offer identity must begin with its provider ID")


def _signed_cash_flow_amount(event: BaseCashFlowEvent, amount: float) -> float:
    return amount if event.direction == "payment" else -amount


def cash_flow_reason(event: BaseCashFlowEvent) -> CashFlowFactUnavailableReason:
    if not isinstance(event.amount, UnavailableFact):
        raise ValueError("an unavailable amount is required for a calculation reason")
    return CashFlowFactUnavailableReason.model_validate(
        {
            "code": "fact_unavailable",
            "field": "baseCashFlowStream.amount",
            "eventKey": event.key,
            "factState": event.amount.state,
        }
    )


def available_result(amount: float) -> AvailableResult:
    return AvailableResult(
        state="available",
        value=ResultValue.model_validate({"amountDkk": round_money(amount)}),
    )


def unavailable_result(
    reasons: Sequence[UnavailabilityReason],
) -> UnavailableResult:
    return UnavailableResult(state="unavailable", reasons=unique_reasons(list(reasons)))


def unique_reasons(
    reasons: list[UnavailabilityReason],
) -> list[UnavailabilityReason]:
    unique: list[UnavailabilityReason] = []
    seen: set[str] = set()
    for reason in reasons:
        key = json.dumps(reason.model_dump(mode="json", by_alias=True), sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(reason)
    return unique


def round_money(value: float) -> float:
    if not isfinite(value):
        raise ValueError("DKK values must be finite")
    return round(value + 0.0, 2)


def _provider_order(
    records: Sequence[CatalogueOffer | QuarantinedCandidate],
    provider_order: Mapping[str, int],
) -> list[int]:
    return [provider_order.get(record.provider_id, -1) for record in records]


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON member {key!r}")
        value[key] = item
    return value


def catalogue_dataset_json_schema() -> dict[str, Any]:
    """Generate the serialization schema from the public Dataset model."""
    return CatalogueDataset.model_json_schema(mode="serialization", by_alias=True)


__all__ = [
    "AdvertisedTotal",
    "AvailableResult",
    "BaseCashFlowEvent",
    "BatteryCapacity",
    "BatteryElectricVehicleSpecification",
    "CandidateAdmissionFacts",
    "CandidateEvidence",
    "CandidateFact",
    "CatalogueCandidate",
    "CatalogueDataset",
    "CatalogueOffer",
    "Catalogue",
    "CatalogueRefreshError",
    "CatalogueRefreshFailure",
    "CatalogueRefreshReport",
    "ChargingPower",
    "CombustionVehicleSpecification",
    "Fact",
    "KnownFact",
    "MaterializedResult",
    "OfferIdentity",
    "ProviderAdapter",
    "QuarantineEvidence",
    "QuarantineReason",
    "QuarantinedCandidate",
    "RefreshFailureCategory",
    "ServiceArrangement",
    "SourceUrl",
    "SharedVehicleSpecification",
    "StableDiagnosticCode",
    "UnavailableFact",
    "UnavailableState",
    "UnavailabilityReason",
    "VehicleSpecification",
    "calculate_catalogue_offer_totals",
    "catalogue_dataset_json_schema",
    "validate_base_cash_flow_stream",
]
