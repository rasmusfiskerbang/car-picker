"""Public presentation contract generated from one authoritative Pydantic model."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from car_picker.catalogue_model import (
    CatalogueModel,
    Evidence,
    ExposureScenario,
    ServiceArrangement,
)


NonEmptyString = Annotated[str, StringConstraints(min_length=1)]


class KnownPresentationMoneyFact(CatalogueModel):
    state: Literal["known"]
    evidence: Evidence
    value_dkk: int


class UnavailablePresentationFact(CatalogueModel):
    state: Literal["not_stated", "unclear", "conflicting", "not_applicable"]
    evidence: Evidence


PresentationMoneyFact = Annotated[
    KnownPresentationMoneyFact | UnavailablePresentationFact,
    Field(discriminator="state"),
]


class CalculationProvenance(CatalogueModel):
    method: Literal["base_cash_flow_stream"]
    input_evidence: list[Evidence]


class KnownDerivedMoneyFact(CatalogueModel):
    state: Literal["known"]
    calculation: CalculationProvenance
    value_dkk: int


class UnavailableDerivedMoneyFact(CatalogueModel):
    state: Literal["not_stated"]
    calculation: CalculationProvenance
    blocking_facts: list[NonEmptyString]


DerivedMoneyFact = Annotated[
    KnownDerivedMoneyFact | UnavailableDerivedMoneyFact,
    Field(discriminator="state"),
]


class KnownPresentationValueFact(CatalogueModel):
    state: Literal["known"]
    evidence: Evidence
    value: str | int


PresentationValueFact = Annotated[
    KnownPresentationValueFact | UnavailablePresentationFact,
    Field(discriminator="state"),
]


class KnownPresentationServiceFact(CatalogueModel):
    state: Literal["known"]
    evidence: Evidence
    value: list[ServiceArrangement]


PresentationServiceFact = Annotated[
    KnownPresentationServiceFact | UnavailablePresentationFact,
    Field(discriminator="state"),
]


class KnownPresentationExposureFact(CatalogueModel):
    state: Literal["known"]
    evidence: Evidence
    value: list[ExposureScenario]


PresentationExposureFact = Annotated[
    KnownPresentationExposureFact | UnavailablePresentationFact,
    Field(discriminator="state"),
]


class PresentationCashFlowEvent(CatalogueModel):
    meaning: NonEmptyString
    direction: Literal["payment", "receipt"]
    amount_dkk: int | None = Field(ge=0)
    amount_basis: Literal["including_vat", "excluding_vat", "not_stated"]
    timing: Literal["acceptance_to_handover", "recurring", "normal_completion_end"]
    recurrence_count: int | None = Field(ge=1)
    refundability: Literal["refundable", "not_refundable", "not_stated"]
    evidence: Evidence
    blocking_facts: list[NonEmptyString] | None = None


class OperationReadiness(CatalogueModel):
    state: Literal["ready", "blocked"]
    blocking_facts: list[NonEmptyString]


class ComparisonOperationReadiness(CatalogueModel):
    upfront_cash_requirement: OperationReadiness
    nominal_base_outlay: OperationReadiness
    nominal_monthly_equivalent: OperationReadiness


class PresentationAggregateAssertion(CatalogueModel):
    value_dkk: int = Field(ge=0)
    evidence: Evidence


class AggregateReconciliation(CatalogueModel):
    status: Literal[
        "not_available",
        "not_reconstructed",
        "matching",
        "within_ordinary_rounding_tolerance",
        "mismatch",
    ]
    provider_advertised_aggregate: PresentationAggregateAssertion | None
    reconstructed_nominal_base_outlay_dkk: int | None
    unexplained_difference_dkk: int | None
    tolerance_dkk: int = Field(ge=0)


class PresentationCoverageProvider(CatalogueModel):
    name: NonEmptyString
    designated_source: NonEmptyString
    quarantined_candidate_count: int = Field(ge=0)


class PresentationCoverage(CatalogueModel):
    providers: list[PresentationCoverageProvider]


class PresentationEndedProviderCoverage(CatalogueModel):
    name: NonEmptyString
    coverage_ended_at: NonEmptyString


class PresentationOffer(CatalogueModel):
    offer_identity: NonEmptyString
    provider: NonEmptyString
    provider_source_url: NonEmptyString
    vehicle_specification: PresentationValueFact
    supported_leasing_form: PresentationValueFact
    provider_form_label: PresentationValueFact
    residual_risk_allocation: PresentationValueFact
    registration_tax_treatment: PresentationValueFact
    service_arrangements: PresentationServiceFact
    exclusions: PresentationServiceFact
    exposure_scenarios: PresentationExposureFact
    advertised_monthly_payment: PresentationMoneyFact
    upfront_cash_requirement: DerivedMoneyFact
    nominal_base_outlay: DerivedMoneyFact
    nominal_monthly_equivalent: DerivedMoneyFact
    operation_readiness: ComparisonOperationReadiness
    aggregate_reconciliation: AggregateReconciliation
    term_months: PresentationValueFact
    annual_mileage_km: PresentationValueFact
    normal_end_mechanism: PresentationValueFact
    cash_flow_breakdown: list[PresentationCashFlowEvent] | None = None


class CataloguePresentation(CatalogueModel):
    model_config = CatalogueModel.model_config | {
        "json_schema_extra": {
            "$id": "https://car-picker.local/schemas/catalogue-presentation-v1.json"
        }
    }

    schema_version: Literal["catalogue-presentation/v1"]
    generated_at: NonEmptyString
    coverage: PresentationCoverage
    coverage_ended: list[PresentationEndedProviderCoverage]
    offers: list[PresentationOffer]


def presentation_json_schema() -> dict[str, object]:
    """Generate the browser serialization contract from the presentation model."""
    return CataloguePresentation.model_json_schema(mode="serialization", by_alias=True)
