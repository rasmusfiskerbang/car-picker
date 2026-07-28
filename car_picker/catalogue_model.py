"""Versioned canonical catalogue model and the temporary legacy JSON boundary."""

from __future__ import annotations

import copy
from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    StringConstraints,
    ValidationInfo,
    model_validator,
)


NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
OfferIdentity = Annotated[
    str,
    StringConstraints(
        min_length=3, pattern=r"^[a-z0-9][a-z0-9_-]*:[^\s:]+(?::[^\s]+)?$"
    ),
]
FactState = Literal["known", "not_stated", "unclear", "conflicting", "not_applicable"]


def camel_case(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(word.capitalize() for word in rest)


class CatalogueModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=camel_case,
        populate_by_name=True,
        extra="forbid",
        strict=True,
    )


class Evidence(CatalogueModel):
    source_url: NonEmptyString
    wording: str


FactValue = TypeVar("FactValue")


class KnownFact(CatalogueModel, Generic[FactValue]):
    state: Literal["known"]
    evidence: Evidence
    value: FactValue


class KnownMoneyFact(CatalogueModel):
    state: Literal["known"]
    evidence: Evidence
    value_dkk: int = Field(ge=0)


class UnavailableFact(CatalogueModel):
    state: Literal["not_stated", "unclear", "conflicting", "not_applicable"]
    evidence: Evidence


class KnownAggregateFact(KnownMoneyFact):
    scope: Literal["normal_completion_base_cash_flows"]


class VehicleSpecification(CatalogueModel):
    make: NonEmptyString
    model: NonEmptyString
    trim: NonEmptyString | None = None


BooleanFact = Annotated[KnownFact[bool] | UnavailableFact, Field(discriminator="state")]
VehicleFact = Annotated[
    KnownFact[VehicleSpecification] | UnavailableFact,
    Field(discriminator="state"),
]
LeasingFormFact = Annotated[
    KnownFact[Literal["financial", "flex", "operational", "hybrid"]] | UnavailableFact,
    Field(discriminator="state"),
]
TextFact = Annotated[
    KnownFact[NonEmptyString] | UnavailableFact,
    Field(discriminator="state"),
]
PositiveInteger = Annotated[int, Field(gt=0)]
PositiveIntegerFact = Annotated[
    KnownFact[PositiveInteger] | UnavailableFact,
    Field(discriminator="state"),
]
MoneyFact = Annotated[KnownMoneyFact | UnavailableFact, Field(discriminator="state")]
EndMechanismFact = Annotated[
    KnownFact[
        Literal[
            "return_to_provider",
            "designate_third_party_buyer",
            "mandatory_purchase_or_payoff",
        ]
    ]
    | UnavailableFact,
    Field(discriminator="state"),
]
ResidualRiskFact = Annotated[
    KnownFact[Literal["provider", "lessee", "shared"]] | UnavailableFact,
    Field(discriminator="state"),
]
RegistrationTaxFact = Annotated[
    KnownFact[Literal["full", "proportional"]] | UnavailableFact,
    Field(discriminator="state"),
]


class CashFlowEvent(CatalogueModel):
    """One complete, sourced event in the normal-completion cash-flow stream."""

    meaning: NonEmptyString
    direction: Literal["payment", "receipt"]
    amount_dkk: int | None = Field(ge=0)
    amount_basis: Literal["including_vat", "excluding_vat", "not_stated"]
    timing: Literal["acceptance_to_handover", "recurring", "normal_completion_end"]
    recurrence_count: int | None = Field(ge=1)
    refundability: Literal["refundable", "not_refundable", "not_stated"]
    included_in_base: Literal[True]
    blocking_facts: list[NonEmptyString] | None = None
    evidence: Evidence


class SourceDocument(CatalogueModel):
    source_url: NonEmptyString
    content_sha256: (
        Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] | None
    ) = None
    retrieved_at: NonEmptyString | None = None


class SourceMetadata(CatalogueModel):
    parser_version: NonEmptyString | None = None
    documents: Annotated[list[SourceDocument], Field(min_length=1)]


class ServiceArrangement(CatalogueModel):
    category: NonEmptyString
    treatment: Literal["included", "optional", "required_external", "excluded"]
    scope: NonEmptyString
    limits: NonEmptyString | None = None


class ExposureScenario(CatalogueModel):
    kind: NonEmptyString
    trigger: NonEmptyString
    required_inputs: list[NonEmptyString]
    input_kinds: list[NonEmptyString] | None = None
    formula: NonEmptyString | None = None
    amount_dkk: int | None = Field(default=None, ge=0)
    rate_dkk: int | None = Field(default=None, ge=0)
    cap_dkk: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def input_kinds_align_with_inputs(self) -> ExposureScenario:
        if self.input_kinds is not None and len(self.input_kinds) != len(
            self.required_inputs
        ):
            raise ValueError("exposure input kinds must align with required inputs")
        return self


ServiceFact = Annotated[
    KnownFact[list[ServiceArrangement]] | UnavailableFact,
    Field(discriminator="state"),
]
ExposureFact = Annotated[
    KnownFact[list[ExposureScenario]] | UnavailableFact,
    Field(discriminator="state"),
]


class QuarantineReason(CatalogueModel):
    fact: NonEmptyString
    state: Literal["not_stated", "unclear", "conflicting"]
    code: NonEmptyString | None = None


class CatalogueCandidate(CatalogueModel):
    offer_identity: OfferIdentity
    provider: NonEmptyString
    provider_source_id: NonEmptyString | None = None
    canonical_offer_url: NonEmptyString | None = None
    source_local_configuration_key: NonEmptyString | None = None
    vehicle_specification: VehicleFact
    private_consumer_eligibility: BooleanFact
    passenger_car_scope: BooleanFact
    current_availability: BooleanFact
    supported_leasing_form: LeasingFormFact
    provider_form_label: TextFact | None = None
    advertised_monthly_payment: MoneyFact
    term_months: PositiveIntegerFact
    base_cash_flow_stream: Annotated[list[CashFlowEvent], Field(min_length=1)]
    source_metadata: SourceMetadata
    base_cash_flow_blockers: list[NonEmptyString] | None = None
    provider_advertised_aggregate: KnownAggregateFact | None = None
    annual_mileage_km: PositiveIntegerFact | None = None
    normal_end_mechanism: EndMechanismFact | None = None
    residual_risk_allocation: ResidualRiskFact | None = None
    registration_tax_treatment: RegistrationTaxFact | None = None
    service_arrangements: ServiceFact | None = None
    exclusions: ServiceFact | None = None
    exposure_scenarios: ExposureFact | None = None


class CatalogueOffer(CatalogueCandidate):
    """An admitted candidate reserved for the active comparison catalogue."""

    admission_outcome: Literal["admitted"]

    @model_validator(mode="after")
    def admission_facts_are_established(self) -> CatalogueOffer:
        boolean_admission_facts = (
            self.private_consumer_eligibility,
            self.passenger_car_scope,
            self.current_availability,
        )
        if any(
            not isinstance(fact, KnownFact) or fact.value is not True
            for fact in boolean_admission_facts
        ):
            raise ValueError(
                "admitted catalogue offers require positive admission facts"
            )
        if not isinstance(self.supported_leasing_form, KnownFact):
            raise ValueError(
                "admitted catalogue offers require a classifiable leasing form"
            )
        return self


class QuarantinedOffer(CatalogueCandidate):
    """A retained candidate that was not admitted to the active catalogue."""

    admission_outcome: Literal["quarantined"]
    quarantine_reasons: Annotated[list[QuarantineReason], Field(min_length=1)]


class CoverageProvider(CatalogueModel):
    name: NonEmptyString
    designated_source: NonEmptyString
    quarantined_candidate_count: int = Field(ge=0)


class Coverage(CatalogueModel):
    providers: list[CoverageProvider]


class EndedProviderCoverage(CatalogueModel):
    name: NonEmptyString
    coverage_ended_at: NonEmptyString


class CatalogueDataset(CatalogueModel):
    _legacy_source: dict[str, Any] | None = PrivateAttr(default=None)

    schema_version: Literal["catalogue-dataset/v1"]
    generated_at: NonEmptyString
    coverage: Coverage
    coverage_ended: list[EndedProviderCoverage]
    catalogue_offers: list[CatalogueOffer]
    quarantined_offers: list[QuarantinedOffer]

    @model_validator(mode="after")
    def validate_complete_replacement(self, info: ValidationInfo) -> CatalogueDataset:
        if info.context and info.context.get("allow_incomplete_legacy_dataset"):
            return self
        provider_rows = self.coverage.providers
        provider_names = [row.name for row in provider_rows]
        if len(provider_names) != len(set(provider_names)):
            raise ValueError("covered provider names must be unique")
        ended_names = [row.name for row in self.coverage_ended]
        if len(ended_names) != len(set(ended_names)):
            raise ValueError("ended provider names must be unique")
        if set(provider_names).intersection(ended_names):
            raise ValueError("a provider cannot be both covered and ended")

        candidates: list[CatalogueCandidate] = [
            *self.catalogue_offers,
            *self.quarantined_offers,
        ]
        identities = [candidate.offer_identity for candidate in candidates]
        if len(identities) != len(set(identities)):
            raise ValueError("offer identities must be unique within a dataset")
        candidate_providers = {candidate.provider for candidate in candidates}
        if candidate_providers != set(provider_names):
            raise ValueError(
                "every and only covered providers must contribute candidates"
            )

        quarantine_counts = {
            provider: sum(
                offer.provider == provider for offer in self.quarantined_offers
            )
            for provider in provider_names
        }
        declared_counts = {
            provider.name: provider.quarantined_candidate_count
            for provider in provider_rows
        }
        if quarantine_counts != declared_counts:
            raise ValueError(
                "provider coverage quarantine counts must match retained candidates"
            )
        return self


def from_legacy_dataset(
    value: dict[str, Any],
    *,
    require_complete_replacement: bool = True,
) -> CatalogueDataset:
    """Parse the current combined-list representation into the canonical model."""
    legacy = copy.deepcopy(value)
    candidates = legacy.pop("catalogueOffers", None)
    if not isinstance(candidates, list):
        return CatalogueDataset.model_validate(legacy)
    forbidden_derived_facts = {
        "upfrontCashRequirement",
        "nominalBaseOutlay",
        "nominalMonthlyEquivalent",
        "operationReadiness",
    }
    if any(
        isinstance(candidate, dict) and forbidden_derived_facts.intersection(candidate)
        for candidate in candidates
    ):
        raise ValueError("canonical offers must not persist derived comparison values")
    admitted: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    for candidate_value in candidates:
        if not isinstance(candidate_value, dict):
            admitted.append(candidate_value)
            continue
        candidate = dict(candidate_value)
        normalize_legacy_cash_flow_events(candidate)
        status = candidate.pop("admissionStatus", None)
        if status == "admitted":
            candidate["admissionOutcome"] = "admitted"
            admitted.append(candidate)
        elif status == "quarantined":
            candidate["admissionOutcome"] = "quarantined"
            if (
                not require_complete_replacement
                and "quarantineReasons" not in candidate
            ):
                candidate["quarantineReasons"] = [
                    {"fact": "admissionOutcome", "state": "unclear"}
                ]
            quarantined.append(candidate)
        else:
            candidate["admissionStatus"] = status
            admitted.append(candidate)
    legacy["catalogueOffers"] = admitted
    legacy["quarantinedOffers"] = quarantined
    dataset = CatalogueDataset.model_validate(
        legacy,
        context={
            "allow_incomplete_legacy_dataset": not require_complete_replacement,
        },
    )
    dataset._legacy_source = copy.deepcopy(value)
    return dataset


def to_legacy_dataset(dataset: CatalogueDataset) -> dict[str, Any]:
    """Serialize canonical data in the unchanged shape consumed by existing commands."""
    if dataset._legacy_source is not None:
        return copy.deepcopy(dataset._legacy_source)
    value = dataset.model_dump(mode="json", by_alias=True, exclude_none=True)
    admitted = value.pop("catalogueOffers")
    quarantined = value.pop("quarantinedOffers")
    combined = []
    for status, offers in (("admitted", admitted), ("quarantined", quarantined)):
        for offer in offers:
            offer.pop("admissionOutcome")
            combined.append({"admissionStatus": status, **offer})
    value["catalogueOffers"] = combined
    return value


def normalize_legacy_cash_flow_events(candidate: dict[str, Any]) -> None:
    """Confine the oldest fixture's incomplete event shape to the legacy adapter."""
    events = candidate.get("baseCashFlowStream")
    metadata = candidate.get("sourceMetadata")
    documents = metadata.get("documents") if isinstance(metadata, dict) else None
    source_url = (
        documents[0].get("sourceUrl")
        if isinstance(documents, list) and documents and isinstance(documents[0], dict)
        else "legacy:unknown"
    )
    if not isinstance(events, list):
        return
    for event in events:
        if not isinstance(event, dict):
            continue
        if set(event) != {"meaning"}:
            continue
        event.setdefault("direction", "payment")
        event.setdefault("amountDkk", None)
        event.setdefault("amountBasis", "not_stated")
        event.setdefault("timing", "recurring")
        event.setdefault("recurrenceCount", None)
        event.setdefault("refundability", "not_stated")
        event.setdefault("includedInBase", True)
        if event.get("amountDkk") is None or event.get("recurrenceCount") is None:
            event.setdefault("blockingFacts", ["baseCashFlowStream"])
        event.setdefault(
            "evidence",
            {
                "sourceUrl": source_url,
                "wording": event.get("meaning", "Legacy cash-flow event"),
            },
        )


def catalogue_dataset_json_schema() -> dict[str, Any]:
    """Generate the serialization contract directly from the authoritative model."""
    return CatalogueDataset.model_json_schema(mode="serialization", by_alias=True)
