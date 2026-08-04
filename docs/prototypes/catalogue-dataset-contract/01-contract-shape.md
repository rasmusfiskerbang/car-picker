# PROTOTYPE — Contract shape

This file uses illustrative Pydantic v2 models because Pydantic is the authoritative contract. The models expose the important constraints and discriminated unions that the serialization-mode JSON Schema must carry across the browser boundary, but prefer readable models over maximal type expressivity. Relationships that become noisy in the type declaration may be enforced by Pydantic validation instead. Every model forbids unknown fields, every tuple has stable source order unless stated otherwise, and fields are required unless explicitly optional.

## Shared primitives

```py
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    AnyUrl,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    PositiveFloat,
    PositiveInt,
    UrlConstraints,
)
from pydantic.alias_generators import to_camel


class CatalogueModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        strict=True,
    )


HttpsUrl = Annotated[AnyUrl, UrlConstraints(allowed_schemes=["https"])]
NonEmptyString = Annotated[str, Field(min_length=1)]
ProviderId = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
OfferIdentity = NonEmptyString

# Non-negative finite JSON number representing DKK.
Dkk = Annotated[FiniteFloat, Field(ge=0)]

UnavailableState = Literal[
    "not_stated",
    "unclear",
    "conflicting",
    "not_applicable",
]

class KnownFact[T](CatalogueModel):
    state: Literal["known"]
    value: T


class UnavailableFact(CatalogueModel):
    state: UnavailableState


type Fact[T] = Annotated[
    KnownFact[T] | UnavailableFact,
    Field(discriminator="state"),
]
```

`Fact[T]` is used only where a Catalogue Offer is allowed to survive admission without a known value. Admission-guaranteed facts are direct values. `null`, omitted properties, empty strings, and sentinel numbers never stand for unavailable facts.

`Dkk` is a Pydantic `float` serialized as a JSON number. NaN and infinity are rejected; small binary floating-point errors are accepted.

## Dataset

```py
class CatalogueDataset(CatalogueModel):
    schema_version: Literal["catalogue-dataset/v1"]
    generated_at: AwareDatetime
    providers: tuple[ProviderRecord, ...]
    offers: tuple[CatalogueOffer, ...]
    quarantined_candidates: tuple[QuarantinedCandidate, ...]
```

There is no nested `providerRegistry` object: `ProviderRegistry` names a behavioral module, while `providers` is its immutable record snapshot. There is no `catalogue` wrapper around offers and no `publication` wrapper around the Dataset.

### Dataset invariants

- `generatedAt` is the only Dataset timestamp. Nested provider, offer, and quarantine records have no collection or update timestamps.
- Provider IDs are unique. Offer identities are unique across both `offers` and `quarantinedCandidates`.
- Every Offer and Quarantined Candidate refers to an active Provider Registry record. Inactive providers own neither.
- `providers` uses Provider Registry order; `offers` and `quarantinedCandidates` use Provider Registry order, then Provider Adapter source order. Base Cash-flow Streams use chronological occurrence order, and other tuple fields preserve normalized source order. Frontend comparison selection does not change Dataset ordering.
- Every URL is absolute HTTPS. An exception for an explicitly approved non-HTTPS public source would require a later schema version, not a relaxed generic URL type.

## Provider Registry copy

```py
class ActiveProvider(CatalogueModel):
    id: ProviderId
    name: NonEmptyString
    url: HttpsUrl
    status: Literal["active"]


class InactiveProvider(CatalogueModel):
    id: ProviderId
    name: NonEmptyString
    url: HttpsUrl
    status: Literal["inactive"]
    reason: Literal["deferred", "ineligible", "blocked"]
    explanation: NonEmptyString


ProviderRecord = Annotated[
    ActiveProvider | InactiveProvider,
    Field(discriminator="status"),
]
```

These are the exact Provider Registry records already decided by the map. No source configuration, evidence, contact data, credentials, operational notes, or transition history is added during Dataset serialization.

## Catalogue Offer

```py
class CatalogueOffer(CatalogueModel):
    offer_identity: OfferIdentity
    provider_id: ProviderId
    canonical_offer_url: HttpsUrl

    vehicle_specification: VehicleSpecification
    leasing_form: Literal["financial", "flex", "operational", "hybrid"]
    term_months: PositiveInt
    annual_mileage_km: Fact[PositiveInt]

    normal_end_mechanism: Fact[
        Literal[
            "return_to_provider",
            "designate_third_party_buyer",
            "mandatory_purchase_or_payoff",
            "other",
        ]
    ]
    residual_risk_allocation: Fact[Literal["provider", "lessee", "shared"]]

    service_arrangements: Fact[tuple[ServiceArrangement, ...]]
    base_cash_flow_stream: Annotated[
        tuple[BaseCashFlowEvent, ...],
        Field(min_length=1),
    ]
    advertised_total_dkk: Fact[Dkk]
    total_dkk: Dkk | None
    total_dkk_per_month: Dkk | None
```

`leasingForm` is the normalized classification established during admission. The provider's source label is transient classification input and is not retained as per-fact wording. Private-consumer eligibility, passenger-car scope, current availability, and admission outcome are also absent: admission already guarantees them, so repeating them as always-true fields would be shallow data.

The provider-advertised monthly payment is not a field. It is represented by the known amount on the applicable `lease_payment` occurrences in the Base Cash-flow Stream. Dataset validation rejects a missing sequence and any contradiction with the admitted source facts.

### Vehicle Specification

```py
FourDigitYear = Annotated[int, Field(ge=1000, le=9999)]
NonNegativeInt = Annotated[int, Field(ge=0)]


class SharedVehicleSpecification(CatalogueModel):
    make: NonEmptyString
    model: NonEmptyString
    trim: Fact[NonEmptyString]
    model_year: Fact[FourDigitYear]
    first_registration_year: Fact[FourDigitYear]
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
    odometer_km: Fact[NonNegativeInt]


class CombustionVehicleSpecification(SharedVehicleSpecification):
    kind: Literal["combustion"]
    fuel_type: Literal["gasoline", "diesel"]
    fuel_efficiency_km_per_liter: Fact[PositiveFloat]


class BatteryCapacity(CatalogueModel):
    value_kwh: PositiveFloat
    basis: Literal["gross", "usable", "not_stated"]


class MaximumChargingPower(CatalogueModel):
    value_kw: PositiveFloat
    kind: Literal["ac", "dc", "not_stated"]


class BatteryElectricVehicleSpecification(SharedVehicleSpecification):
    kind: Literal["battery_electric"]
    battery_capacity: Fact[BatteryCapacity]
    wltp_range_km: Fact[PositiveInt]
    max_charging_power: Fact[MaximumChargingPower]
    charging_time_10_to_80_minutes: Fact[PositiveFloat]


VehicleSpecification = Annotated[
    CombustionVehicleSpecification | BatteryElectricVehicleSpecification,
    Field(discriminator="kind"),
]
```

This is a shared schema, not a shared entity: every Offer embeds one complete Vehicle Specification. The discriminating `kind` makes impossible combinations unrepresentable—an electric specification cannot carry fuel efficiency and a combustion specification cannot carry battery fields. Make, model, vehicle kind, and combustion fuel type are direct because catalogue scope and admission guarantee them; the other v1 attributes are explicit about availability.

`modelYear` and `firstRegistrationYear` remain separate so the source's meaning is never guessed. Either, both, or neither may be known. A new vehicle that has not been registered uses `not_applicable` for `firstRegistrationYear`; a source that simply omits it uses `not_stated`.

A known battery capacity or maximum charging power remains usable when its basis or charging kind was not disclosed: the nested qualifier is `not_stated`. The outer Fact is unavailable only when the numeric value itself is unavailable. This distinguishes “150 kW, kind not stated” from “charging power not stated.”

`odometerKm` is the advertised distance already driven, deliberately distinct from the leasing Offer's `annualMileageKm` allowance. “Gas” is not used in the contract because the supported kind includes both gasoline and diesel. Hybrid, plug-in hybrid, mild-hybrid, hydrogen, and other vehicle kinds are rejected before Catalogue Admission. The `hybrid` Leasing Form remains a contract classification, not a vehicle drivetrain.

### Service arrangements

```py
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
```

The strings are normalized offer facts, not retained verbatim evidence. A known empty `serviceArrangements.value` means the designated source explicitly establishes that there are no disclosed arrangements; `not_stated` means it did not establish that.

## Base Cash-flow Stream

```py
class BaseCashFlowEvent(CatalogueModel):
    key: NonEmptyString
    occurs_at_month: NonNegativeInt
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
    amount: Fact[Dkk]
    refundability: Fact[Literal["refundable", "not_refundable"]]
```

Each event represents one cash-flow occurrence, not a recurrence rule. `occursAtMonth` is contract-relative: `0` is the upfront bucket at or before handover, `1` is the first month after handover, and `termMonths` is normal contract completion. The stream is ordered by non-decreasing `occursAtMonth`; array order is the stable tie-breaker for occurrences in the same month. Dataset validation rejects an occurrence after `termMonths`.

An expected return of a refundable deposit is a separate `receipt` occurrence so the offer preserves both directions and their timing. `refundability` describes the payment's terms; it is `not_applicable` on receipts and ordinary non-deposit cash flows only when the concept genuinely does not apply.

Event keys are unique within one Offer. The `key` is a stable local reference and does not claim identity across Dataset generations.

### Conditional amounts

There is deliberately no Exposure Scenario type. Excess-mileage rates, damage charges, early-termination charges, and other amounts triggered by conditional or uncertain events are not represented in the Dataset and do not enter the Base Cash-flow Stream. Their disclosure does not quarantine an otherwise admissible Offer. They are omitted, not assigned a zero value.

### Offer totals

`advertisedTotalDkk` is a provider-stated Fact and is not used as a calculation input. `totalDkk` and `totalDkkPerMonth` are flat backend-calculated fields on the Offer, not a nested Comparison model:

```text
totalDkk = sum(payment occurrence amounts) − sum(receipt occurrence amounts)
totalDkkPerMonth = totalDkk ÷ termMonths
```

An explicit refund therefore reduces `totalDkk`. For example, a 50,000 DKK deposit payment and an explicit 50,000 DKK deposit-refund receipt net to zero. The backend never invents a refund: when a required cash-flow amount is unavailable, both calculated fields are `null`. They are always present, `0` remains a genuine calculated value, and `totalDkkPerMonth` is `null` exactly when `totalDkk` is `null`. Ordinary floating-point errors are accepted; display precision belongs to the frontend.

Dataset validation recomputes both calculated fields from the Base Cash-flow Stream and term. Each occurrence contributes exactly once; there is no recurrence multiplier. Validation rejects a non-null disagreement, a number where the inputs are unavailable, or a `null` where the inputs are sufficient. `advertisedTotalDkk` remains independent even when it disagrees with `totalDkk`; there is no reconciliation state.

## Frontend comparison

There is no backend Comparison model, aggregate reconciliation, readiness structure, or comparison-specific availability state. The frontend selects Catalogue Offers by identity from the parsed Dataset and renders their normalized facts and flat calculated totals side by side. That selection and presentation state are not added to the Dataset and do not create a second durable model.

## Quarantined Candidate

```py
EvidenceExcerpt = Annotated[str, Field(min_length=1, max_length=500)]


class QuarantineEvidence(CatalogueModel):
    source_url: HttpsUrl
    excerpt: EvidenceExcerpt


class QuarantineReason(CatalogueModel):
    criterion: Literal[
        "offer_identity",
        "private_consumer_eligibility",
        "passenger_car_scope",
        "current_availability",
        "leasing_form",
        "advertised_monthly_payment",
        "term_months",
        "candidate_shape",
    ]
    state: Literal["not_stated", "unclear", "conflicting"]
    code: NonEmptyString
    evidence: Annotated[tuple[QuarantineEvidence, ...], Field(min_length=1)]


class QuarantinedCandidate(CatalogueModel):
    offer_identity: OfferIdentity
    provider_id: ProviderId
    canonical_source_url: HttpsUrl
    reasons: Annotated[tuple[QuarantineReason, ...], Field(min_length=1)]
```

The full Candidate, vehicle facts, cash flows, source documents, and adapter metadata are absent. Evidence is limited to the public designated first-party material needed to support the failed criterion. Multiple reasons may cite the same excerpt; compactness is preferred over adding a global evidence graph.

An adapter that cannot establish any deterministic Offer Identity has a structural mapping failure and rejects the refresh. `offer_identity` remains a quarantine criterion for contradictory candidate identity, not for an unaddressable anonymous record.

## Whole-model validation

Pydantic field validation is not sufficient. `CatalogueDataset` performs one after-validation pass that:

1. checks all cross-record identities, active-provider references, and ordering;
2. checks Offer invariants, including unique event keys, chronological occurrence order, occurrence months within the term, and the lease-payment sequence;
3. recomputes `totalDkk` and `totalDkkPerMonth`, including signed receipts, and compares them to the materialized fields;
4. rejects forbidden evidence and operational metadata anywhere outside Quarantined Candidate reasons;
5. rejects the complete Dataset on any disagreement.

The Dataset therefore remains a normalized offer artifact rather than a backend comparison artifact.

Because this Markdown presents models in domain-reading order rather than Python dependency order, the eventual module resolves its forward references after all declarations with `CatalogueDataset.model_rebuild()`.
