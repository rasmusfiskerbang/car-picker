"""PROTOTYPE — generate the accepted browser contract and a stress Dataset.

This keeps the throwaway UI on the intended Pydantic → JSON Schema →
TypeScript/Zod seam. The eventual clean-room model replaces this illustrative
generator; page and variant code must not become production implementation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Generic, Literal, TypeVar

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


FRONTEND = Path(__file__).parents[2]
GENERATED = FRONTEND / "src" / "generated"
PUBLIC = FRONTEND / "public"


class CatalogueModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        strict=True,
    )


HttpsUrl = Annotated[AnyUrl, UrlConstraints(allowed_schemes=["https"])]
NonEmptyString = Annotated[str, Field(min_length=1)]
ProviderId = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
Dkk = Annotated[FiniteFloat, Field(ge=0)]
FourDigitYear = Annotated[int, Field(ge=1000, le=9999)]
NonNegativeInt = Annotated[int, Field(ge=0)]

UnavailableState = Literal[
    "not_stated",
    "unclear",
    "conflicting",
    "not_applicable",
]

T = TypeVar("T")


class KnownFact(CatalogueModel, Generic[T]):
    state: Literal["known"]
    value: T


class UnavailableFact(CatalogueModel):
    state: UnavailableState


StringFact = Annotated[
    KnownFact[NonEmptyString] | UnavailableFact,
    Field(discriminator="state"),
]
PositiveIntFact = Annotated[
    KnownFact[PositiveInt] | UnavailableFact,
    Field(discriminator="state"),
]
NonNegativeIntFact = Annotated[
    KnownFact[NonNegativeInt] | UnavailableFact,
    Field(discriminator="state"),
]
YearFact = Annotated[
    KnownFact[FourDigitYear] | UnavailableFact,
    Field(discriminator="state"),
]
DkkFact = Annotated[
    KnownFact[Dkk] | UnavailableFact,
    Field(discriminator="state"),
]


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


class SharedVehicleSpecification(CatalogueModel):
    make: NonEmptyString
    model: NonEmptyString
    trim: StringFact
    model_year: YearFact
    first_registration_year: YearFact
    body_style: Annotated[
        KnownFact[
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
        | UnavailableFact,
        Field(discriminator="state"),
    ]
    odometer_km: NonNegativeIntFact


class CombustionVehicleSpecification(SharedVehicleSpecification):
    kind: Literal["combustion"]
    fuel_type: Literal["gasoline", "diesel"]
    fuel_efficiency_km_per_liter: Annotated[
        KnownFact[PositiveFloat] | UnavailableFact,
        Field(discriminator="state"),
    ]


class BatteryCapacity(CatalogueModel):
    value_kwh: PositiveFloat
    basis: Literal["gross", "usable", "not_stated"]


class MaximumChargingPower(CatalogueModel):
    value_kw: PositiveFloat
    kind: Literal["ac", "dc", "not_stated"]


class BatteryElectricVehicleSpecification(SharedVehicleSpecification):
    kind: Literal["battery_electric"]
    battery_capacity: Annotated[
        KnownFact[BatteryCapacity] | UnavailableFact,
        Field(discriminator="state"),
    ]
    wltp_range_km: PositiveIntFact
    max_charging_power: Annotated[
        KnownFact[MaximumChargingPower] | UnavailableFact,
        Field(discriminator="state"),
    ]
    charging_time_10_to_80_minutes: Annotated[
        KnownFact[PositiveFloat] | UnavailableFact,
        Field(discriminator="state"),
    ]


VehicleSpecification = Annotated[
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
    limits: StringFact


ServiceArrangementsFact = Annotated[
    KnownFact[tuple[ServiceArrangement, ...]] | UnavailableFact,
    Field(discriminator="state"),
]


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
    amount: DkkFact
    refundability: Annotated[
        KnownFact[Literal["refundable", "not_refundable"]] | UnavailableFact,
        Field(discriminator="state"),
    ]


class CatalogueOffer(CatalogueModel):
    offer_identity: NonEmptyString
    provider_id: ProviderId
    canonical_offer_url: HttpsUrl
    image_urls: tuple[HttpsUrl, ...]
    vehicle_specification: VehicleSpecification
    leasing_form: Literal["financial", "flex", "operational", "hybrid"]
    term_months: PositiveInt
    annual_mileage_km: PositiveIntFact
    normal_end_mechanism: Annotated[
        KnownFact[
            Literal[
                "return_to_provider",
                "designate_third_party_buyer",
                "mandatory_purchase_or_payoff",
                "other",
            ]
        ]
        | UnavailableFact,
        Field(discriminator="state"),
    ]
    residual_risk_allocation: Annotated[
        KnownFact[Literal["provider", "lessee", "shared"]] | UnavailableFact,
        Field(discriminator="state"),
    ]
    service_arrangements: ServiceArrangementsFact
    base_cash_flow_stream: Annotated[tuple[BaseCashFlowEvent, ...], Field(min_length=1)]
    advertised_total_dkk: DkkFact
    total_dkk: Dkk | None
    total_dkk_per_month: Dkk | None


class QuarantineEvidence(CatalogueModel):
    source_url: HttpsUrl
    excerpt: Annotated[str, Field(min_length=1, max_length=500)]


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
    offer_identity: NonEmptyString
    provider_id: ProviderId
    canonical_source_url: HttpsUrl
    reasons: Annotated[tuple[QuarantineReason, ...], Field(min_length=1)]


class CatalogueDataset(CatalogueModel):
    schema_version: Literal["catalogue-dataset/v1"]
    generated_at: AwareDatetime
    providers: tuple[ProviderRecord, ...]
    offers: tuple[CatalogueOffer, ...]
    quarantined_candidates: tuple[QuarantinedCandidate, ...]


VEHICLES = (
    ("Volvo", "EX30", "Ultra Single Motor", "battery_electric", "suv"),
    ("Hyundai", "IONIQ 5", "Ultimate 84 kWh", "battery_electric", "suv"),
    ("Volkswagen", "ID.7", "Style S", "battery_electric", "saloon"),
    ("BMW", "i4", "eDrive40 M Sport", "battery_electric", "saloon"),
    ("Audi", "A6 Avant", "40 TDI S line", "combustion", "estate"),
    ("Mercedes-Benz", "C-Klasse", "C220d AMG Line", "combustion", "saloon"),
    ("Porsche", "911", "Carrera PDK", "combustion", "coupe"),
    ("Volvo", "V90", "B4 Plus Dark", "combustion", "estate"),
)

IMAGE_URLS = (
    "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7",
    "https://images.unsplash.com/photo-1503376780353-7e6692767b70",
    "https://images.unsplash.com/photo-1504215680853-026ed2a45def",
    "https://images.unsplash.com/photo-1494976388531-d1058494cdd8",
    "https://images.unsplash.com/photo-1552519507-da3b142c6e3d",
    "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf",
    "https://images.unsplash.com/photo-1542362567-b07e54358753",
    "https://images.unsplash.com/photo-1549317661-bd32c8ce0db2",
)


def known(value: object) -> dict[str, object]:
    return {"state": "known", "value": value}


def unavailable(state: UnavailableState = "not_stated") -> dict[str, str]:
    return {"state": state}


def vehicle_specification(index: int) -> dict[str, object]:
    make, model, trim, kind, body_style = VEHICLES[index % len(VEHICLES)]
    shared: dict[str, object] = {
        "kind": kind,
        "make": make,
        "model": model,
        "trim": known(trim),
        "modelYear": known(2024 + (index % 3)),
        "firstRegistrationYear": unavailable("not_applicable")
        if index % 4 == 0
        else known(2022 + (index % 4)),
        "bodyStyle": known(body_style),
        "odometerKm": known(index * 2_750) if index % 5 else unavailable(),
    }
    if kind == "battery_electric":
        shared.update(
            {
                "batteryCapacity": known(
                    {"valueKwh": float(64 + (index % 4) * 10), "basis": "usable"}
                ),
                "wltpRangeKm": known(410 + (index % 5) * 38),
                "maxChargingPower": known(
                    {"valueKw": float(150 + (index % 4) * 25), "kind": "dc"}
                ),
                "chargingTime10To80Minutes": known(float(26 + index % 8)),
            }
        )
    else:
        shared.update(
            {
                "fuelType": "diesel" if index % 2 else "gasoline",
                "fuelEfficiencyKmPerLiter": known(float(14 + index % 7)),
            }
        )
    return shared


def cash_flows(index: int, term: int, monthly: float) -> tuple[list[dict[str, object]], float | None]:
    events: list[dict[str, object]] = [
        {
            "key": "initial-payment",
            "occursAtMonth": 0,
            "kind": "initial_payment",
            "direction": "payment",
            "amount": known(float(19_995 + (index % 6) * 10_000)),
            "refundability": known("not_refundable"),
        },
        {
            "key": "establishment-fee",
            "occursAtMonth": 0,
            "kind": "establishment_fee",
            "direction": "payment",
            "amount": known(float(3_995 + (index % 3) * 1_000)),
            "refundability": unavailable("not_applicable"),
        },
    ]

    if index % 4 == 0:
        events.append(
            {
                "key": "deposit",
                "occursAtMonth": 0,
                "kind": "deposit",
                "direction": "payment",
                "amount": known(15_000.0),
                "refundability": known("refundable"),
            }
        )

    for month in range(1, term + 1):
        events.append(
            {
                "key": f"lease-payment-{month:02d}",
                "occursAtMonth": month,
                "kind": "lease_payment",
                "direction": "payment",
                "amount": known(monthly),
                "refundability": unavailable("not_applicable"),
            }
        )

    if index % 4 == 0:
        events.append(
            {
                "key": "deposit-refund",
                "occursAtMonth": term,
                "kind": "deposit_refund",
                "direction": "receipt",
                "amount": known(15_000.0),
                "refundability": unavailable("not_applicable"),
            }
        )

    if index % 7 == 0:
        events.append(
            {
                "key": "other-required-cost",
                "occursAtMonth": term,
                "kind": "other",
                "direction": "payment",
                "amount": unavailable("unclear"),
                "refundability": unavailable("not_applicable"),
            }
        )
        return events, None

    total = sum(
        float(event["amount"]["value"])
        * (1 if event["direction"] == "payment" else -1)
        for event in events
    )
    return events, total


def catalogue_offer(index: int) -> dict[str, object]:
    provider_id = "fleasing" if index % 2 == 0 else "terminalen"
    term = (12, 24, 36)[index % 3]
    monthly = float(3_295 + (index % 8) * 675)
    events, total = cash_flows(index, term, monthly)
    image = IMAGE_URLS[index % len(IMAGE_URLS)]
    image_urls = [] if index % 9 == 0 else [
        f"{image}?auto=format&fit=crop&w=1400&q=82",
        f"{image}?auto=format&fit=crop&w=1000&q=78&sat=-12",
    ]
    return {
        "offerIdentity": f"{provider_id}:prototype-{index:02d}:config-{index % 3}",
        "providerId": provider_id,
        "canonicalOfferUrl": f"https://example.com/offers/{provider_id}-{index:02d}",
        "imageUrls": image_urls,
        "vehicleSpecification": vehicle_specification(index),
        "leasingForm": ("financial", "operational", "flex")[index % 3],
        "termMonths": term,
        "annualMileageKm": unavailable() if index % 6 == 0 else known((10_000, 15_000, 20_000)[index % 3]),
        "normalEndMechanism": known(
            "return_to_provider" if index % 3 == 1 else "designate_third_party_buyer"
        ),
        "residualRiskAllocation": unavailable("unclear")
        if index % 5 == 0
        else known("provider" if index % 3 == 1 else "lessee"),
        "serviceArrangements": known(
            [
                {
                    "category": "service",
                    "treatment": "included",
                    "summary": "Planlagt service er inkluderet i perioden.",
                    "limits": unavailable(),
                }
            ]
        )
        if index % 3 == 1
        else unavailable(),
        "baseCashFlowStream": events,
        "advertisedTotalDkk": unavailable() if index % 4 == 0 else known(float(monthly * term + 25_000)),
        "totalDkk": total,
        "totalDkkPerMonth": None if total is None else total / term,
    }


def stress_dataset() -> CatalogueDataset:
    value = {
        "schemaVersion": "catalogue-dataset/v1",
        "generatedAt": "2026-08-04T04:00:00Z",
        "providers": [
            {"id": "fleasing", "name": "Fleasing", "url": "https://fleasing.dk", "status": "active"},
            {"id": "terminalen", "name": "Terminalen", "url": "https://terminalen.dk", "status": "active"},
            {
                "id": "example-deferred",
                "name": "Eksempeludbyder (prototype)",
                "url": "https://example.com",
                "status": "inactive",
                "reason": "deferred",
                "explanation": "Illustrativ inaktiv Provider i prototypens stressdata.",
            },
        ],
        "offers": [catalogue_offer(index) for index in range(24)],
        "quarantinedCandidates": [
            {
                "offerIdentity": "fleasing:prototype-quarantine:config-0",
                "providerId": "fleasing",
                "canonicalSourceUrl": "https://example.com/offers/quarantined",
                "reasons": [
                    {
                        "criterion": "term_months",
                        "state": "conflicting",
                        "code": "conflicting-term",
                        "evidence": [
                            {
                                "sourceUrl": "https://example.com/offers/quarantined",
                                "excerpt": "12 måneder / 24 måneder",
                            }
                        ],
                    }
                ],
            }
        ],
    }
    # Validate through the JSON boundary so strict tuples and datetimes receive
    # their real serialized representations rather than Python test shortcuts.
    return CatalogueDataset.model_validate_json(json.dumps(value))


def main() -> None:
    GENERATED.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)

    schema = CatalogueDataset.model_json_schema(
        mode="serialization",
        by_alias=True,
        ref_template="#/$defs/{model}",
    )
    schema_json = json.dumps(schema, ensure_ascii=False, indent=2) + "\n"
    (GENERATED / "catalogue-dataset.schema.json").write_text(
        schema_json,
        encoding="utf-8",
    )
    (GENERATED / "catalogue-dataset.schema.generated.ts").write_text(
        "// PROTOTYPE — generated from Pydantic CatalogueDataset. Do not edit.\n"
        f"export const catalogueDatasetJsonSchema = {schema_json.rstrip()} as const;\n",
        encoding="utf-8",
    )

    dataset = stress_dataset()
    (PUBLIC / "catalogue-dataset.json").write_text(
        json.dumps(
            dataset.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
