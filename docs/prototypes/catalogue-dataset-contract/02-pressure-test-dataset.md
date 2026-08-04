# PROTOTYPE — Pressure-test Dataset

This illustrative JSON is intentionally awkward. It is not real provider data and must not become a fixture. It exercises the proposed unions and whole-Dataset invariants in one readable generation.

```json
{
  "schemaVersion": "catalogue-dataset/v1",
  "generatedAt": "2026-07-31T10:00:00Z",
  "providers": [
    {
      "id": "terminalen",
      "name": "Terminalen",
      "url": "https://www.terminalen.dk/",
      "status": "active"
    },
    {
      "id": "fleasing",
      "name": "Fleasing",
      "url": "https://fleasing.dk/",
      "status": "active"
    },
    {
      "id": "future-provider",
      "name": "Future Provider",
      "url": "https://example.test/",
      "status": "inactive",
      "reason": "deferred",
      "explanation": "Source assessment is deferred until the two-provider baseline passes acceptance."
    }
  ],
  "offers": [
    {
      "offerIdentity": "terminalen:ioniq-5:essential-84",
      "providerId": "terminalen",
      "canonicalOfferUrl": "https://example.test/terminalen/ioniq-5",
      "vehicleSpecification": {
        "kind": "battery_electric",
        "make": "Hyundai",
        "model": "IONIQ 5",
        "trim": { "state": "known", "value": "Essential 84 kWh" },
        "modelYear": { "state": "known", "value": 2025 },
        "firstRegistrationYear": { "state": "not_applicable" },
        "bodyStyle": { "state": "known", "value": "suv" },
        "odometerKm": { "state": "known", "value": 0 },
        "batteryCapacity": {
          "state": "known",
          "value": { "valueKwh": 84, "basis": "not_stated" }
        },
        "wltpRangeKm": { "state": "known", "value": 570 },
        "maxChargingPower": {
          "state": "known",
          "value": { "valueKw": 260, "kind": "dc" }
        },
        "chargingTime10To80Minutes": { "state": "known", "value": 18 }
      },
      "leasingForm": "operational",
      "termMonths": 36,
      "annualMileageKm": { "state": "known", "value": 10000 },
      "normalEndMechanism": { "state": "known", "value": "return_to_provider" },
      "residualRiskAllocation": { "state": "known", "value": "provider" },
      "serviceArrangements": {
        "state": "known",
        "value": [
          {
            "category": "service",
            "treatment": "included",
            "summary": "Manufacturer-scheduled service is included.",
            "limits": { "state": "not_stated" }
          },
          {
            "category": "insurance",
            "treatment": "required_external",
            "summary": "Insurance must be arranged and paid separately.",
            "limits": { "state": "not_applicable" }
          }
        ]
      },
      "baseCashFlowStream": [
        { "key": "initial-payment", "occursAtMonth": 0, "kind": "initial_payment", "direction": "payment", "amount": { "state": "known", "value": 15990 }, "refundability": { "state": "known", "value": "not_refundable" } },
        { "key": "delivery-fee", "occursAtMonth": 0, "kind": "delivery_fee", "direction": "payment", "amount": { "state": "not_stated" }, "refundability": { "state": "known", "value": "not_refundable" } },
        { "key": "monthly-lease-payment-01", "occursAtMonth": 1, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-02", "occursAtMonth": 2, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-03", "occursAtMonth": 3, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-04", "occursAtMonth": 4, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-05", "occursAtMonth": 5, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-06", "occursAtMonth": 6, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-07", "occursAtMonth": 7, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-08", "occursAtMonth": 8, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-09", "occursAtMonth": 9, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-10", "occursAtMonth": 10, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-11", "occursAtMonth": 11, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-12", "occursAtMonth": 12, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-13", "occursAtMonth": 13, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-14", "occursAtMonth": 14, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-15", "occursAtMonth": 15, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-16", "occursAtMonth": 16, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-17", "occursAtMonth": 17, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-18", "occursAtMonth": 18, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-19", "occursAtMonth": 19, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-20", "occursAtMonth": 20, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-21", "occursAtMonth": 21, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-22", "occursAtMonth": 22, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-23", "occursAtMonth": 23, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-24", "occursAtMonth": 24, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-25", "occursAtMonth": 25, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-26", "occursAtMonth": 26, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-27", "occursAtMonth": 27, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-28", "occursAtMonth": 28, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-29", "occursAtMonth": 29, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-30", "occursAtMonth": 30, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-31", "occursAtMonth": 31, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-32", "occursAtMonth": 32, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-33", "occursAtMonth": 33, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-34", "occursAtMonth": 34, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-35", "occursAtMonth": 35, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-36", "occursAtMonth": 36, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 3795 }, "refundability": { "state": "not_applicable" } }
      ],
      "advertisedTotalDkk": { "state": "not_stated" },
      "totalDkk": null,
      "totalDkkPerMonth": null
    },
    {
      "offerIdentity": "fleasing:example-flex:configuration-a",
      "providerId": "fleasing",
      "canonicalOfferUrl": "https://example.test/fleasing/example-flex",
      "vehicleSpecification": {
        "kind": "combustion",
        "make": "Example",
        "model": "Touring",
        "trim": { "state": "unclear" },
        "modelYear": { "state": "not_stated" },
        "firstRegistrationYear": { "state": "known", "value": 2022 },
        "bodyStyle": { "state": "known", "value": "estate" },
        "odometerKm": { "state": "known", "value": 42000 },
        "fuelType": "diesel",
        "fuelEfficiencyKmPerLiter": { "state": "known", "value": 18.5 }
      },
      "leasingForm": "flex",
      "termMonths": 12,
      "annualMileageKm": { "state": "not_stated" },
      "normalEndMechanism": {
        "state": "known",
        "value": "designate_third_party_buyer"
      },
      "residualRiskAllocation": { "state": "known", "value": "lessee" },
      "serviceArrangements": { "state": "not_stated" },
      "baseCashFlowStream": [
        { "key": "initial-payment", "occursAtMonth": 0, "kind": "initial_payment", "direction": "payment", "amount": { "state": "known", "value": 25000 }, "refundability": { "state": "known", "value": "not_refundable" } },
        { "key": "refundable-deposit-payment", "occursAtMonth": 0, "kind": "deposit", "direction": "payment", "amount": { "state": "known", "value": 50000 }, "refundability": { "state": "known", "value": "refundable" } },
        { "key": "monthly-lease-payment-01", "occursAtMonth": 1, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 2995 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-02", "occursAtMonth": 2, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 2995 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-03", "occursAtMonth": 3, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 2995 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-04", "occursAtMonth": 4, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 2995 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-05", "occursAtMonth": 5, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 2995 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-06", "occursAtMonth": 6, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 2995 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-07", "occursAtMonth": 7, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 2995 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-08", "occursAtMonth": 8, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 2995 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-09", "occursAtMonth": 9, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 2995 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-10", "occursAtMonth": 10, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 2995 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-11", "occursAtMonth": 11, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 2995 }, "refundability": { "state": "not_applicable" } },
        { "key": "monthly-lease-payment-12", "occursAtMonth": 12, "kind": "lease_payment", "direction": "payment", "amount": { "state": "known", "value": 2995 }, "refundability": { "state": "not_applicable" } },
        { "key": "refundable-deposit-return", "occursAtMonth": 12, "kind": "deposit_refund", "direction": "receipt", "amount": { "state": "known", "value": 50000 }, "refundability": { "state": "not_applicable" } }
      ],
      "advertisedTotalDkk": { "state": "known", "value": 61500 },
      "totalDkk": 60940,
      "totalDkkPerMonth": 5078.333333333333
    }
  ],
  "quarantinedCandidates": [
    {
      "offerIdentity": "terminalen:example-model:mixed-audience",
      "providerId": "terminalen",
      "canonicalSourceUrl": "https://example.test/terminalen/mixed-audience",
      "reasons": [
        {
          "criterion": "private_consumer_eligibility",
          "state": "conflicting",
          "code": "mixed-private-and-business-price-basis",
          "evidence": [
            {
              "sourceUrl": "https://example.test/terminalen/mixed-audience",
              "excerpt": "Privatleasing fra 3.995 kr. pr. måned. Alle priser er ekskl. moms."
            }
          ]
        }
      ]
    }
  ]
}
```

## What this example demonstrates

- `future-provider` proves the Provider Registry copy is broader than the providers represented by Offers and Quarantined Candidates.
- The Terminalen offer remains admitted with an unavailable delivery-fee amount, while both calculated totals are explicitly `null` rather than partial or zero.
- The Fleasing offer keeps refundable-deposit payment and receipt events separate. Its 50,000 DKK deposit payment and 50,000 DKK refund net to zero, producing `totalDkk` of `60940` rather than `110940`.
- Both Offers expose one chronologically ordered event per cash-flow occurrence. The frontend can plot the streams directly without expanding a recurrence rule; same-month event order is preserved at months `0` and `12`.
- The provider's advertised Fleasing total of `61500` remains visible beside the independently calculated `60940`; neither overwrites the other and no reconciliation state is added.
- Missing annual mileage does not prevent admission or block the Fleasing totals. The frontend can still show that Offer beside another while rendering the mileage fact as unavailable.
- Comparison selection and presentation are absent from the Dataset; the frontend selects these Offer records by identity and renders their facts and flat totals side by side.
- The Quarantined Candidate retains the exact public contradiction that explains failed admission, but none of its parsed vehicle, contract, or cash-flow data.

## Resolved pressure point outside the JSON shape

An active provider may legitimately contribute zero Candidates only when its Provider Adapter recognizes and exhaustively enumerates a valid empty source. Missing expected structure, failed enumeration, or an ambiguous empty page is a structural failure that rejects the refresh. The distinction belongs to Provider Adapter behavior and therefore adds no field to this Dataset example.
