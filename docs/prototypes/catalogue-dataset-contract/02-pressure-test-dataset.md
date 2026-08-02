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
      "supportedLeasingForm": "operational",
      "providerFormLabel": "Privatleasing",
      "termMonths": 36,
      "annualMileageKm": { "state": "known", "value": 10000 },
      "normalEndMechanism": { "state": "known", "value": "return_to_provider" },
      "residualRiskAllocation": { "state": "known", "value": "provider" },
      "registrationTaxTreatment": { "state": "known", "value": "full" },
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
        {
          "key": "initial-payment",
          "kind": "initial_payment",
          "direction": "payment",
          "amount": { "state": "known", "value": 15990 },
          "schedule": {
            "kind": "one_off",
            "timing": "acceptance_to_handover"
          },
          "refundability": { "state": "known", "value": "not_refundable" }
        },
        {
          "key": "monthly-lease-payment",
          "kind": "lease_payment",
          "direction": "payment",
          "amount": { "state": "known", "value": 3795 },
          "schedule": {
            "kind": "recurring",
            "everyMonths": 1,
            "occurrences": 36,
            "firstPaymentTiming": "after_handover"
          },
          "refundability": { "state": "not_applicable" }
        }
      ],
      "providerAdvertisedAggregate": { "state": "not_stated" },
      "comparison": {
        "upfrontCashRequirement": {
          "state": "available",
          "value": { "amountDkk": 15990 }
        },
        "nominalBaseOutlay": {
          "state": "available",
          "value": { "amountDkk": 152610 }
        },
        "nominalMonthlyEquivalent": {
          "state": "available",
          "value": { "amountDkk": 4239.17 }
        },
        "aggregateReconciliation": { "status": "not_stated" }
      }
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
      "supportedLeasingForm": "flex",
      "providerFormLabel": "Flexleasing",
      "termMonths": 12,
      "annualMileageKm": { "state": "not_stated" },
      "normalEndMechanism": {
        "state": "known",
        "value": "designate_third_party_buyer"
      },
      "residualRiskAllocation": { "state": "known", "value": "lessee" },
      "registrationTaxTreatment": { "state": "known", "value": "proportional" },
      "serviceArrangements": { "state": "not_stated" },
      "baseCashFlowStream": [
        {
          "key": "initial-payment",
          "kind": "initial_payment",
          "direction": "payment",
          "amount": { "state": "known", "value": 25000 },
          "schedule": {
            "kind": "one_off",
            "timing": "acceptance_to_handover"
          },
          "refundability": { "state": "known", "value": "not_refundable" }
        },
        {
          "key": "refundable-deposit-payment",
          "kind": "deposit",
          "direction": "payment",
          "amount": { "state": "known", "value": 50000 },
          "schedule": {
            "kind": "one_off",
            "timing": "acceptance_to_handover"
          },
          "refundability": { "state": "known", "value": "refundable" }
        },
        {
          "key": "monthly-lease-payment",
          "kind": "lease_payment",
          "direction": "payment",
          "amount": { "state": "known", "value": 2995 },
          "schedule": {
            "kind": "recurring",
            "everyMonths": 1,
            "occurrences": 12,
            "firstPaymentTiming": "after_handover"
          },
          "refundability": { "state": "not_applicable" }
        },
        {
          "key": "refundable-deposit-return",
          "kind": "deposit_refund",
          "direction": "receipt",
          "amount": { "state": "known", "value": 50000 },
          "schedule": {
            "kind": "one_off",
            "timing": "normal_completion_end"
          },
          "refundability": { "state": "not_applicable" }
        }
      ],
      "providerAdvertisedAggregate": {
        "state": "known",
        "value": {
          "scope": "normal_completion_base_cash_flows",
          "amountDkk": 61500
        }
      },
      "comparison": {
        "upfrontCashRequirement": {
          "state": "available",
          "value": { "amountDkk": 75000 }
        },
        "nominalBaseOutlay": {
          "state": "unavailable",
          "reasons": [
            { "code": "aggregate_mismatch" }
          ]
        },
        "nominalMonthlyEquivalent": {
          "state": "unavailable",
          "reasons": [
            { "code": "aggregate_mismatch" }
          ]
        },
        "aggregateReconciliation": {
          "status": "mismatch",
          "providerAmountDkk": 61500,
          "reconstructedAmountDkk": 60940,
          "signedDifferenceDkk": 560,
          "toleranceDkk": 1
        }
      }
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
- The Terminalen offer's missing aggregate does not block reconstructed values; there is simply nothing to reconcile.
- The Fleasing offer's refundable deposit contributes `50000` DKK to upfront cash requirement and nets to zero in reconstructed nominal base outlay.
- The Fleasing arithmetic is `25000 + (2995 × 12) + 50000 - 50000 = 60940`. The provider assertion differs by `560`, beyond the `1` DKK tolerance, so only the dependent derived values are unavailable.
- Missing annual mileage does not prevent admission and does not make the whole Offer incomplete. It makes mileage filtering unavailable for that Offer.
- The Quarantined Candidate retains the exact public contradiction that explains failed admission, but none of its parsed vehicle, contract, or cash-flow data.

## Resolved pressure point outside the JSON shape

An active provider may legitimately contribute zero Candidates only when its Provider Adapter recognizes and exhaustively enumerates a valid empty source. Missing expected structure, failed enumeration, or an ambiguous empty page is a structural failure that rejects the refresh. The distinction belongs to Provider Adapter behavior and therefore adds no field to this Dataset example.
