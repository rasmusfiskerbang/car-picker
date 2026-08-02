# PROTOTYPE — Contract shape

This file uses TypeScript-like notation because it makes JSON unions compact. Pydantic remains authoritative. Every object forbids unknown fields, every array has stable source order unless stated otherwise, and every field shown is required.

## Shared primitives

```ts
type SchemaVersion = "catalogue-dataset/v1";
type Instant = string; // RFC 3339 UTC, canonical `YYYY-MM-DDTHH:mm:ssZ`
type HttpsUrl = string;
type NonEmptyString = string;
type NonEmptyArray<T> = [T, ...T[]];
type ProviderId = string; // stable kebab-case registry identity
type OfferIdentity = string; // provider ID + source identity + configuration key

// Finite JSON number representing DKK. Non-negative unless explicitly signed.
type Dkk = number;
type SignedDkk = number;

type UnavailableState =
  | "not_stated"
  | "unclear"
  | "conflicting"
  | "not_applicable";

type Fact<T> =
  | { state: "known"; value: T }
  | { state: UnavailableState };
```

`Fact<T>` is used only where a Catalogue Offer is allowed to survive admission without a known value. Admission-guaranteed facts are direct values. `null`, omitted properties, empty strings, and sentinel numbers never stand for unavailable facts.

`Dkk` is a Pydantic `float` serialized as a JSON number. NaN and infinity are rejected. Small binary floating-point errors are accepted; materialized monetary results are rounded to two decimal places before serialization and validation compares those rounded values.

## Dataset

```ts
type CatalogueDataset = {
  schemaVersion: SchemaVersion;
  generatedAt: Instant;
  providers: ProviderRecord[];
  offers: CatalogueOffer[];
  quarantinedCandidates: QuarantinedCandidate[];
};
```

There is no nested `providerRegistry` object: `ProviderRegistry` names a behavioral module, while `providers` is its immutable record snapshot. There is no `catalogue` wrapper around offers and no `publication` wrapper around the Dataset.

### Dataset invariants

- `generatedAt` is the only Dataset timestamp. Nested provider, offer, and quarantine records have no collection or update timestamps.
- Provider IDs are unique. Offer identities are unique across both `offers` and `quarantinedCandidates`.
- Every Offer and Quarantined Candidate refers to an active Provider Registry record. Inactive providers own neither.
- Arrays use Provider Registry order, then Provider Adapter source order. No score or derived value changes ordering.
- Every URL is absolute HTTPS. An exception for an explicitly approved non-HTTPS public source would require a later schema version, not a relaxed generic URL type.

## Provider Registry copy

```ts
type ActiveProvider = {
  id: ProviderId;
  name: NonEmptyString;
  url: HttpsUrl;
  status: "active";
};

type InactiveProvider = {
  id: ProviderId;
  name: NonEmptyString;
  url: HttpsUrl;
  status: "inactive";
  reason: "deferred" | "ineligible" | "blocked";
  explanation: NonEmptyString;
};

type ProviderRecord = ActiveProvider | InactiveProvider;
```

These are the exact Provider Registry records already decided by the map. No source configuration, evidence, contact data, credentials, operational notes, or transition history is added during Dataset serialization.

## Catalogue Offer

```ts
type CatalogueOffer = {
  offerIdentity: OfferIdentity;
  providerId: ProviderId;
  canonicalOfferUrl: HttpsUrl;

  vehicleSpecification: VehicleSpecification;
  supportedLeasingForm: "financial" | "flex" | "operational" | "hybrid";
  providerFormLabel: NonEmptyString;
  termMonths: number; // positive integer
  annualMileageKm: Fact<number>; // positive integer when known

  normalEndMechanism: Fact<
    | "return_to_provider"
    | "designate_third_party_buyer"
    | "mandatory_purchase_or_payoff"
    | "other"
  >;
  residualRiskAllocation: Fact<"provider" | "lessee" | "shared">;
  registrationTaxTreatment: Fact<"full" | "proportional">;

  serviceArrangements: Fact<ServiceArrangement[]>;
  baseCashFlowStream: NonEmptyArray<BaseCashFlowEvent>;
  providerAdvertisedAggregate: Fact<ProviderAdvertisedAggregate>;

  comparison: ComparisonResults;
};
```

`providerFormLabel` is direct because classifying a Supported Leasing Form requires an actual provider-described form. Private-consumer eligibility, passenger-car scope, current availability, and admission outcome are absent: admission already guarantees them, so repeating them as always-true fields would be shallow data.

The provider-advertised monthly payment is not a field. It is the known amount of the single recurring `lease_payment` Base Cash-flow Event. Dataset validation rejects zero or multiple candidate events and any contradiction with the admitted source facts.

### Vehicle Specification

```ts
type SharedVehicleSpecification = {
  make: NonEmptyString;
  model: NonEmptyString;
  trim: Fact<NonEmptyString>;
  modelYear: Fact<number>; // positive four-digit integer
  firstRegistrationYear: Fact<number>; // positive four-digit integer
  bodyStyle: Fact<
    "hatchback" | "saloon" | "estate" | "suv" | "coupe" | "convertible" | "mpv" | "other"
  >;
  odometerKm: Fact<number>; // non-negative integer
};

type CombustionVehicleSpecification = SharedVehicleSpecification & {
  kind: "combustion";
  fuelType: "gasoline" | "diesel";
  fuelEfficiencyKmPerLiter: Fact<number>; // positive finite number
};

type BatteryElectricVehicleSpecification = SharedVehicleSpecification & {
  kind: "battery_electric";
  batteryCapacity: Fact<{
    valueKwh: number; // positive finite number
    basis: "gross" | "usable" | "not_stated";
  }>;
  wltpRangeKm: Fact<number>; // positive integer
  maxChargingPower: Fact<{
    valueKw: number; // positive finite number
    kind: "ac" | "dc" | "not_stated";
  }>;
  chargingTime10To80Minutes: Fact<number>; // positive finite number
};

type VehicleSpecification =
  | CombustionVehicleSpecification
  | BatteryElectricVehicleSpecification;
```

This is a shared schema, not a shared entity: every Offer embeds one complete Vehicle Specification. The discriminating `kind` makes impossible combinations unrepresentable—an electric specification cannot carry fuel efficiency and a combustion specification cannot carry battery fields. Make, model, vehicle kind, and combustion fuel type are direct because catalogue scope and admission guarantee them; the other v1 attributes are explicit about availability.

`modelYear` and `firstRegistrationYear` remain separate so the source's meaning is never guessed. Either, both, or neither may be known. A new vehicle that has not been registered uses `not_applicable` for `firstRegistrationYear`; a source that simply omits it uses `not_stated`.

A known battery capacity or maximum charging power remains usable when its basis or charging kind was not disclosed: the nested qualifier is `not_stated`. The outer Fact is unavailable only when the numeric value itself is unavailable. This distinguishes “150 kW, kind not stated” from “charging power not stated.”

`odometerKm` is the advertised distance already driven, deliberately distinct from the leasing Offer's `annualMileageKm` allowance. “Gas” is not used in the contract because the supported kind includes both gasoline and diesel. Hybrid, plug-in hybrid, mild-hybrid, hydrogen, and other vehicle kinds are rejected before Catalogue Admission. The `hybrid` Supported Leasing Form remains a contract classification, not a vehicle drivetrain.

### Service arrangements

```ts
type ServiceArrangement = {
  category:
    | "service"
    | "maintenance"
    | "insurance"
    | "roadside_assistance"
    | "tyres"
    | "other";
  treatment: "included" | "optional" | "required_external" | "excluded";
  summary: NonEmptyString;
  limits: Fact<NonEmptyString>;
};
```

The strings are normalized offer facts, not retained verbatim evidence. A known empty `serviceArrangements.value` means the designated source explicitly establishes that there are no disclosed arrangements; `not_stated` means it did not establish that.

## Base Cash-flow Stream

```ts
type BaseCashFlowEvent = {
  key: NonEmptyString; // unique, stable within one Offer
  kind:
    | "initial_payment"
    | "lease_payment"
    | "establishment_fee"
    | "delivery_fee"
    | "deposit"
    | "deposit_refund"
    | "mandatory_purchase_or_payoff"
    | "other";
  direction: "payment" | "receipt";
  amount: Fact<Dkk>;
  schedule:
    | {
        kind: "one_off";
        timing: "acceptance_to_handover" | "normal_completion_end";
      }
    | {
        kind: "recurring";
        everyMonths: number; // positive integer
        occurrences: number; // positive integer
        firstPaymentTiming: "acceptance_to_handover" | "after_handover";
      };
  refundability: Fact<"refundable" | "not_refundable">;
};
```

An expected return of a refundable deposit is a separate `receipt` event. The original payment therefore contributes to upfront cash requirement, while payment and receipt net in nominal base outlay. `refundability` describes the payment's terms; it is `not_applicable` on receipts and ordinary non-deposit cash flows only when the concept genuinely does not apply.

The event `key` is the stable local reference used by blocking facts. It does not claim identity across Dataset generations.

## Materialized comparison results

```ts
type UnavailabilityReason =
  | {
      code: "fact_unavailable";
      field: "annualMileageKm";
      factState: UnavailableState;
    }
  | {
      code: "fact_unavailable";
      field: "normalEndMechanism";
      factState: UnavailableState;
    }
  | {
      code: "fact_unavailable";
      field: "residualRiskAllocation";
      factState: UnavailableState;
    }
  | {
      code: "fact_unavailable";
      field: "registrationTaxTreatment";
      factState: UnavailableState;
    }
  | {
      code: "fact_unavailable";
      field: "baseCashFlowStream.amount" | "baseCashFlowStream.refundability";
      eventKey: NonEmptyString;
      factState: UnavailableState;
    }
  | {
      code: "fact_unavailable";
      field: "providerAdvertisedAggregate";
      factState: UnavailableState;
    }
  | { code: "aggregate_mismatch" };

type MaterializedResult<T> =
  | { state: "available"; value: T }
  | { state: "unavailable"; reasons: NonEmptyArray<UnavailabilityReason> };

type ComparisonResults = {
  upfrontCashRequirement: MaterializedResult<{ amountDkk: Dkk }>;
  nominalBaseOutlay: MaterializedResult<{ amountDkk: Dkk }>;
  nominalMonthlyEquivalent: MaterializedResult<{ amountDkk: Dkk }>;
  aggregateReconciliation: AggregateReconciliation;
};
```

Availability lives inside each result. This prevents illegal combinations such as a value beside a separate record saying the operation is blocked. Filtering on an ordinary Fact uses that Fact's own evidentiary state; it does not require a parallel operation index.

The frontend may format and explain these values, but it does not recalculate the authoritative result. It renders arithmetic from the Base Cash-flow Stream and term already present in the same Offer.

### Aggregate reconciliation

```ts
type ProviderAdvertisedAggregate = {
  scope: "normal_completion_base_cash_flows";
  amountDkk: Dkk;
};

type AggregateReconciliation =
  | { status: "not_stated" }
  | {
      status: "not_reconstructable";
      reasons: NonEmptyArray<UnavailabilityReason>;
    }
  | {
      status: "matching" | "within_rounding_tolerance";
      providerAmountDkk: Dkk;
      reconstructedAmountDkk: Dkk;
      signedDifferenceDkk: SignedDkk;
      toleranceDkk: Dkk;
    }
  | {
      status: "mismatch";
      providerAmountDkk: Dkk;
      reconstructedAmountDkk: Dkk;
      signedDifferenceDkk: SignedDkk;
      toleranceDkk: Dkk;
    };
```

A `mismatch` makes `nominalBaseOutlay` and `nominalMonthlyEquivalent` unavailable with reason `aggregate_mismatch`; it does not affect `upfrontCashRequirement`. Validation recomputes the reconstruction and every difference.

## Quarantined Candidate

```ts
type QuarantinedCandidate = {
  offerIdentity: OfferIdentity;
  providerId: ProviderId;
  canonicalSourceUrl: HttpsUrl;
  reasons: NonEmptyArray<QuarantineReason>;
};

type QuarantineReason = {
  criterion:
    | "offer_identity"
    | "private_consumer_eligibility"
    | "passenger_car_scope"
    | "current_availability"
    | "supported_leasing_form"
    | "advertised_monthly_payment"
    | "term_months"
    | "candidate_shape";
  state: "not_stated" | "unclear" | "conflicting";
  code: NonEmptyString;
  evidence: NonEmptyArray<QuarantineEvidence>;
};

type QuarantineEvidence = {
  sourceUrl: HttpsUrl;
  excerpt: NonEmptyString; // exact public first-party excerpt, max 500 characters
};
```

The full Candidate, vehicle facts, cash flows, source documents, and adapter metadata are absent. Evidence is limited to the public designated first-party material needed to support the failed criterion. Multiple reasons may cite the same excerpt; compactness is preferred over adding a global evidence graph.

An adapter that cannot establish any deterministic Offer Identity has a structural mapping failure and rejects the refresh. `offer_identity` remains a quarantine criterion for contradictory candidate identity, not for an unaddressable anonymous record.

## Whole-model validation

Pydantic field validation is not sufficient. `CatalogueDataset` performs one after-validation pass that:

1. checks all cross-record identities, active-provider references, and ordering;
2. checks Offer invariants, including the single recurring lease-payment event;
3. recalculates every comparison result and reconciliation with the same float arithmetic and two-decimal materialization rule;
4. compares the recalculated structures to the materialized structures exactly;
5. rejects forbidden evidence and operational metadata anywhere outside Quarantined Candidate reasons;
6. rejects the complete Dataset on any disagreement.

The materialized values are therefore cache-like output inside one validated generation, never a second authority.
