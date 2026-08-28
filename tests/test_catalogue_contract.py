from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

from pydantic import ValidationError

from car_picker import (
    AvailableResult,
    BaseCashFlowEvent,
    CatalogueDataset,
    calculate_catalogue_offer_totals,
)


class CatalogueContractTest(unittest.TestCase):
    def test_public_dataset_contract_round_trips_a_strict_offer(self) -> None:
        dataset = sample_dataset()

        parsed = CatalogueDataset.model_validate(dataset)
        serialized = parsed.model_dump(mode="json", by_alias=True)

        self.assertEqual(serialized, dataset)
        self.assertEqual(serialized["schemaVersion"], "catalogue-dataset/v1")
        self.assertEqual(serialized["offers"][0]["providerId"], "terminalen")
        calculated_total, calculated_monthly = calculate_catalogue_offer_totals(
            parsed.offers[0]
        )
        self.assertEqual(
            calculated_total.model_dump(mode="json", by_alias=True),
            serialized["offers"][0]["calculatedTotal"],
        )
        self.assertEqual(
            calculated_monthly.model_dump(mode="json", by_alias=True),
            serialized["offers"][0]["calculatedMonthlyTotal"],
        )

    def test_dataset_serialization_has_exactly_five_fields_and_compact_quarantine(
        self,
    ) -> None:
        dataset = sample_dataset()
        cast(list[object], dataset["quarantinedCandidates"]).append(
            sample_quarantined_candidate()
        )

        serialized = CatalogueDataset.model_validate(dataset).model_dump(
            mode="json", by_alias=True
        )

        self.assertEqual(
            list(serialized),
            [
                "schemaVersion",
                "generatedAt",
                "providers",
                "offers",
                "quarantinedCandidates",
            ],
        )
        self.assertEqual(
            set(serialized["quarantinedCandidates"][0]),
            {"offerIdentity", "providerId", "canonicalSourceUrl", "reasons"},
        )
        self.assertNotIn("vehicleSpecification", serialized["quarantinedCandidates"][0])

    def test_quarantined_candidate_rejects_retained_candidate_data(self) -> None:
        invalid = sample_dataset()
        candidate = sample_quarantined_candidate()
        candidate["vehicleSpecification"] = {}
        cast(list[object], invalid["quarantinedCandidates"]).append(candidate)

        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(invalid)

    def test_quarantine_reason_requires_a_stable_diagnostic_code(self) -> None:
        for invalid_code in ("   ", "term not-stated", "Term.not-stated", "a" * 65):
            with self.subTest(invalid_code=invalid_code):
                invalid = sample_dataset()
                candidate = sample_quarantined_candidate()
                cast(dict[str, object], cast(list[object], candidate["reasons"])[0])[
                    "code"
                ] = invalid_code
                cast(list[object], invalid["quarantinedCandidates"]).append(candidate)

                with self.assertRaises(ValidationError):
                    CatalogueDataset.model_validate(invalid)

    def test_quarantine_evidence_excerpt_must_be_trimmed_and_nonblank(self) -> None:
        for invalid_excerpt in ("   ", "\t\n", " Term not stated", "Term not stated "):
            with self.subTest(invalid_excerpt=invalid_excerpt):
                invalid = sample_dataset()
                candidate = sample_quarantined_candidate()
                evidence = cast(
                    dict[str, object],
                    cast(
                        list[object],
                        cast(
                            dict[str, object],
                            cast(list[object], candidate["reasons"])[0],
                        )["evidence"],
                    )[0],
                )
                evidence["excerpt"] = invalid_excerpt
                cast(list[object], invalid["quarantinedCandidates"]).append(candidate)

                with self.assertRaises(ValidationError):
                    CatalogueDataset.model_validate(invalid)

    def test_dataset_rejects_identity_collision_between_offer_and_quarantine(
        self,
    ) -> None:
        invalid = sample_dataset()
        duplicate = sample_quarantined_candidate()
        duplicate["offerIdentity"] = "terminalen:ioniq-5:essential-84"
        cast(list[object], invalid["quarantinedCandidates"]).append(duplicate)

        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(invalid)

    def test_dataset_rejects_records_for_inactive_providers(self) -> None:
        invalid = sample_dataset()
        add_fleasing_provider(invalid, active=False)
        offer = copy.deepcopy(sample_offer())
        offer["offerIdentity"] = "fleasing:aston-martin:one"
        offer["providerId"] = "fleasing"
        offer["canonicalOfferUrl"] = "https://example.test/fleasing/aston-martin"
        cast(list[object], invalid["offers"]).append(offer)

        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(invalid)

    def test_dataset_records_follow_provider_registry_order(self) -> None:
        invalid = sample_dataset()
        add_fleasing_provider(invalid)
        misordered_offer = copy.deepcopy(sample_offer())
        misordered_offer["offerIdentity"] = "fleasing:aston-martin:one"
        misordered_offer["providerId"] = "fleasing"
        misordered_offer["canonicalOfferUrl"] = (
            "https://example.test/fleasing/aston-martin"
        )
        offers = cast(list[object], invalid["offers"])
        invalid["offers"] = [misordered_offer, offers[0]]

        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(invalid)

        invalid = sample_dataset()
        add_fleasing_provider(invalid)
        misordered_candidate = sample_quarantined_candidate()
        misordered_candidate["offerIdentity"] = "fleasing:aston-martin:missing-term"
        misordered_candidate["providerId"] = "fleasing"
        misordered_candidate["canonicalSourceUrl"] = (
            "https://example.test/fleasing/aston-martin"
        )
        invalid["quarantinedCandidates"] = [
            misordered_candidate,
            sample_quarantined_candidate(),
        ]

        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(invalid)

    def test_public_dataset_contract_rejects_unknown_fields_and_unsupported_vehicle_kinds(
        self,
    ) -> None:
        unknown = copy.deepcopy(sample_dataset())
        unknown_offer = first_offer(unknown)
        unknown_offer["unexpected"] = True
        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(unknown)

        unsupported = copy.deepcopy(sample_dataset())
        unsupported_offer = first_offer(unsupported)
        vehicle = cast(dict[str, object], unsupported_offer["vehicleSpecification"])
        vehicle["kind"] = "hybrid"
        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(unsupported)

        unsupported_version = copy.deepcopy(sample_dataset())
        unsupported_version["schemaVersion"] = "catalogue-dataset/v2"
        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(unsupported_version)

    def test_public_dataset_contract_accepts_only_current_serialized_field_names(
        self,
    ) -> None:
        snake_case = copy.deepcopy(sample_dataset())
        snake_case["schema_version"] = snake_case.pop("schemaVersion")
        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(snake_case)

        legacy_month = copy.deepcopy(sample_dataset())
        legacy_event = cast(
            dict[str, object],
            cast(list[object], first_offer(legacy_month)["baseCashFlowStream"])[0],
        )
        legacy_event["contractMonth"] = legacy_event.pop("month")
        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(legacy_month)

        legacy_total = copy.deepcopy(sample_dataset())
        legacy_offer = first_offer(legacy_total)
        legacy_offer["providerAdvertisedAggregate"] = legacy_offer.pop(
            "advertisedTotal"
        )
        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(legacy_total)

    def test_public_offer_contract_deliberately_omits_registration_tax_treatment(
        self,
    ) -> None:
        without_tax_treatment = copy.deepcopy(sample_dataset())

        parsed = CatalogueDataset.model_validate(without_tax_treatment)

        self.assertNotIn(
            "registrationTaxTreatment",
            parsed.offers[0].model_dump(mode="json", by_alias=True),
        )

        with_tax_treatment = copy.deepcopy(sample_dataset())
        first_offer(with_tax_treatment)["registrationTaxTreatment"] = {
            "state": "known",
            "value": "full",
        }
        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(with_tax_treatment)

    def test_public_cli_inspects_the_active_dataset_and_exact_offer(self) -> None:
        dataset = sample_dataset()
        offer = first_offer(dataset)
        offer["imageUrls"] = ["https://example.test/terminalen/ioniq-5.jpg"]
        quarantined = cast(list[object], dataset["quarantinedCandidates"])
        quarantined.append(
            {
                "offerIdentity": "terminalen:ioniq-6:unknown",
                "providerId": "terminalen",
                "canonicalSourceUrl": "https://example.test/terminalen/ioniq-6",
                "reasons": [
                    {
                        "criterion": "term_months",
                        "state": "not_stated",
                        "code": "term.not-stated",
                        "evidence": [
                            {
                                "sourceUrl": "https://example.test/terminalen/ioniq-6",
                                "excerpt": "Term not stated",
                            }
                        ],
                    }
                ],
            }
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            write_dataset(workspace, dataset)

            human = run_cli("--workspace", str(workspace), "catalogue", "inspect")
            human_offer = run_cli(
                "--workspace",
                str(workspace),
                "catalogue",
                "inspect",
                "terminalen:ioniq-5:essential-84",
            )
            dataset_json_result = run_cli(
                "--workspace", str(workspace), "--json", "catalogue", "inspect"
            )
            offer_json_result = run_cli(
                "--workspace",
                str(workspace),
                "--json",
                "catalogue",
                "inspect",
                "terminalen:ioniq-5:essential-84",
            )
            invalid_identity = run_cli(
                "--workspace",
                str(workspace),
                "catalogue",
                "inspect",
                "not-an-offer-identity",
            )

        self.assertEqual(human.returncode, 0, human.stderr)
        self.assertIn("Catalogue Dataset", human.stdout)
        self.assertIn("terminalen:ioniq-5:essential-84", human.stdout)
        self.assertIn("https://www.terminalen.dk/", human.stdout)
        self.assertIn("terminalen:ioniq-6:unknown", human.stdout)
        self.assertIn("canonicalSourceUrl", human.stdout)
        self.assertEqual(human_offer.returncode, 0, human_offer.stderr)
        self.assertIn("Calculated Total", human_offer.stdout)
        self.assertIn("Advertised Total", human_offer.stdout)
        self.assertIn("batteryCapacity", human_offer.stdout)
        self.assertIn("https://example.test/terminalen/ioniq-5.jpg", human_offer.stdout)
        self.assertEqual(dataset_json_result.returncode, 0, dataset_json_result.stderr)
        dataset_report = json.loads(dataset_json_result.stdout)
        self.assertEqual(dataset_report["kind"], "catalogue-dataset")
        self.assertEqual(
            dataset_report["dataset"]["schemaVersion"], "catalogue-dataset/v1"
        )
        self.assertEqual(offer_json_result.returncode, 0, offer_json_result.stderr)
        report = json.loads(offer_json_result.stdout)
        self.assertEqual(report["kind"], "catalogue-offer")
        self.assertEqual(
            report["offer"]["offerIdentity"],
            "terminalen:ioniq-5:essential-84",
        )
        self.assertIn("calculatedTotal", report["offer"])
        self.assertEqual(invalid_identity.returncode, 2)
        self.assertIn("must be a valid Offer Identity", invalid_identity.stderr)
        self.assertNotIn("Traceback", invalid_identity.stderr)

    def test_public_cli_inspects_one_exact_quarantined_candidate(self) -> None:
        dataset = sample_dataset()
        quarantined = cast(list[object], dataset["quarantinedCandidates"])
        quarantined.append(sample_quarantined_candidate())

        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            write_dataset(workspace, dataset)

            human = run_cli(
                "--workspace",
                str(workspace),
                "catalogue",
                "inspect",
                "terminalen:ioniq-6:unknown",
            )
            candidate_json_result = run_cli(
                "--workspace",
                str(workspace),
                "--json",
                "catalogue",
                "inspect",
                "terminalen:ioniq-6:unknown",
            )

        self.assertEqual(human.returncode, 0, human.stderr)
        self.assertIn("Quarantined Candidate", human.stdout)
        self.assertIn("terminalen:ioniq-6:unknown", human.stdout)
        self.assertIn("term_months", human.stdout)
        self.assertIn("Term not stated", human.stdout)
        self.assertEqual(
            candidate_json_result.returncode, 0, candidate_json_result.stderr
        )
        report = json.loads(candidate_json_result.stdout)
        self.assertEqual(report["kind"], "quarantined-candidate")
        self.assertEqual(
            report["quarantinedCandidate"]["offerIdentity"],
            "terminalen:ioniq-6:unknown",
        )
        self.assertNotIn("vehicleSpecification", report["quarantinedCandidate"])
        human_record = json.loads(
            human.stdout.split("Compact Candidate Record:\n", maxsplit=1)[1]
        )
        self.assertEqual(human_record, report["quarantinedCandidate"])

    def test_public_cli_reports_a_missing_catalogue_record_neutrally(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            write_dataset(workspace, sample_dataset())

            human = run_cli(
                "--workspace",
                str(workspace),
                "catalogue",
                "inspect",
                "terminalen:ioniq-7:unknown",
            )
            stable_json = run_cli(
                "--workspace",
                str(workspace),
                "--json",
                "catalogue",
                "inspect",
                "terminalen:ioniq-7:unknown",
            )

        self.assertEqual(human.returncode, 1)
        self.assertIn("catalogue.record_not_found", human.stderr)
        self.assertNotIn("catalogue.offer_not_found", human.stderr)
        self.assertEqual(stable_json.returncode, 1)
        report = json.loads(stable_json.stderr)
        self.assertEqual(report["error"]["code"], "catalogue.record_not_found")

    def test_public_cash_flow_calculation_nets_an_explicit_deposit_receipt(
        self,
    ) -> None:
        events = [
            BaseCashFlowEvent.model_validate(
                {
                    "key": "initial-payment",
                    "month": 0,
                    "kind": "initial_payment",
                    "direction": "payment",
                    "amount": {"state": "known", "value": 25000},
                    "refundability": {
                        "state": "known",
                        "value": "not_refundable",
                    },
                }
            ),
            BaseCashFlowEvent.model_validate(
                {
                    "key": "deposit-payment",
                    "month": 0,
                    "kind": "deposit",
                    "direction": "payment",
                    "amount": {"state": "known", "value": 50000},
                    "refundability": {
                        "state": "known",
                        "value": "refundable",
                    },
                }
            ),
            *[
                BaseCashFlowEvent.model_validate(
                    {
                        "key": f"monthly-lease-payment-{month}",
                        "month": month,
                        "kind": "lease_payment",
                        "direction": "payment",
                        "amount": {"state": "known", "value": 2995},
                        "refundability": {"state": "not_applicable"},
                    }
                )
                for month in range(1, 13)
            ],
            BaseCashFlowEvent.model_validate(
                {
                    "key": "deposit-refund",
                    "month": 12,
                    "kind": "deposit_refund",
                    "direction": "receipt",
                    "amount": {"state": "known", "value": 50000},
                    "refundability": {"state": "not_applicable"},
                }
            ),
        ]

        dataset = sample_dataset()
        offer = first_offer(dataset)
        offer["termMonths"] = 12
        offer["baseCashFlowStream"] = [
            event.model_dump(mode="json", by_alias=True) for event in events
        ]
        offer["calculatedTotal"] = {
            "state": "available",
            "value": {"amountDkk": 60940},
        }
        offer["calculatedMonthlyTotal"] = {
            "state": "available",
            "value": {"amountDkk": 5078.33},
        }
        parsed = CatalogueDataset.model_validate(dataset)
        total, monthly = calculate_catalogue_offer_totals(parsed.offers[0])

        assert isinstance(total, AvailableResult)
        assert isinstance(monthly, AvailableResult)
        self.assertEqual(total.value.amount_dkk, 60940)
        self.assertEqual(monthly.value.amount_dkk, 5078.33)

    def test_public_cash_flow_calculation_preserves_negative_signed_totals(
        self,
    ) -> None:
        events = [
            BaseCashFlowEvent.model_validate(
                {
                    "key": "payment",
                    "month": 0,
                    "kind": "lease_payment",
                    "direction": "payment",
                    "amount": {"state": "known", "value": 10},
                    "refundability": {"state": "known", "value": "refundable"},
                }
            ),
            BaseCashFlowEvent.model_validate(
                {
                    "key": "receipt",
                    "month": 1,
                    "kind": "deposit_refund",
                    "direction": "receipt",
                    "amount": {"state": "known", "value": 20},
                    "refundability": {"state": "not_applicable"},
                }
            ),
        ]

        dataset = sample_dataset()
        offer = first_offer(dataset)
        offer["termMonths"] = 1
        offer["baseCashFlowStream"] = [
            event.model_dump(mode="json", by_alias=True) for event in events
        ]
        offer["calculatedTotal"] = {
            "state": "available",
            "value": {"amountDkk": -10},
        }
        offer["calculatedMonthlyTotal"] = {
            "state": "available",
            "value": {"amountDkk": -10},
        }
        parsed = CatalogueDataset.model_validate(dataset)
        total, monthly = calculate_catalogue_offer_totals(parsed.offers[0])

        assert isinstance(total, AvailableResult)
        assert isinstance(monthly, AvailableResult)
        self.assertEqual(total.value.amount_dkk, -10)
        self.assertEqual(monthly.value.amount_dkk, -10)

    def test_public_cash_flow_rejects_a_deposit_refund_as_a_payment(self) -> None:
        with self.assertRaises(ValidationError):
            BaseCashFlowEvent.model_validate(
                {
                    "key": "deposit-refund",
                    "month": 12,
                    "kind": "deposit_refund",
                    "direction": "payment",
                    "amount": {"state": "known", "value": 50000},
                    "refundability": {"state": "not_applicable"},
                }
            )

    def test_dataset_rejects_unavailable_required_amount_with_unavailable_totals(
        self,
    ) -> None:
        dataset = sample_dataset()
        offer = first_offer(dataset)
        events = cast(list[object], offer["baseCashFlowStream"])
        monthly = cast(dict[str, object], events[1])
        monthly["amount"] = {"state": "not_stated"}
        unavailable = {
            "state": "unavailable",
            "reasons": [
                {
                    "code": "fact_unavailable",
                    "field": "baseCashFlowStream.amount",
                    "eventKey": "lease-payment-1",
                    "factState": "not_stated",
                }
            ],
        }
        offer["calculatedTotal"] = unavailable
        offer["calculatedMonthlyTotal"] = copy.deepcopy(unavailable)

        parsed = CatalogueDataset.model_validate(dataset)

        self.assertEqual(parsed.offers[0].calculated_total.state, "unavailable")

    def test_advertised_total_remains_independent_from_calculated_totals(self) -> None:
        dataset = sample_dataset()
        offer = first_offer(dataset)
        offer["advertisedTotal"] = {
            "state": "known",
            "value": {"amountDkk": 1},
        }

        parsed = CatalogueDataset.model_validate(dataset)

        calculated = parsed.offers[0].calculated_total
        assert isinstance(calculated, AvailableResult)
        self.assertEqual(calculated.value.amount_dkk, 152610)

    def test_dataset_rejects_out_of_term_events_and_inconsistent_stored_totals(
        self,
    ) -> None:
        out_of_term = copy.deepcopy(sample_dataset())
        offer = first_offer(out_of_term)
        stream = cast(list[object], offer["baseCashFlowStream"])
        out_of_term_event = cast(dict[str, object], stream[-1])
        out_of_term_event["month"] = 37
        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(out_of_term)

        inconsistent = copy.deepcopy(sample_dataset())
        offer = first_offer(inconsistent)
        calculated = cast(dict[str, object], offer["calculatedTotal"])
        value = cast(dict[str, object], calculated["value"])
        value["amountDkk"] = 1
        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(inconsistent)


def sample_dataset() -> dict[str, object]:
    return {
        "schemaVersion": "catalogue-dataset/v1",
        "generatedAt": "2026-07-31T10:00:00Z",
        "providers": [
            {
                "id": "terminalen",
                "name": "Terminalen",
                "url": "https://www.terminalen.dk/",
                "status": "active",
            }
        ],
        "offers": [sample_offer()],
        "quarantinedCandidates": [],
    }


def add_fleasing_provider(
    dataset: dict[str, object],
    *,
    active: bool = True,
) -> None:
    provider: dict[str, object] = {
        "id": "fleasing",
        "name": "Fleasing",
        "url": "https://www.fleasing.dk/",
        "status": "active" if active else "inactive",
    }
    if not active:
        provider.update(
            {
                "reason": "deferred",
                "explanation": "Source review is pending.",
            }
        )
    cast(list[object], dataset["providers"]).append(provider)


def sample_offer() -> dict[str, object]:
    return {
        "offerIdentity": "terminalen:ioniq-5:essential-84",
        "providerId": "terminalen",
        "canonicalOfferUrl": "https://example.test/terminalen/ioniq-5",
        "vehicleSpecification": {
            "kind": "battery_electric",
            "make": "Hyundai",
            "model": "IONIQ 5",
            "trim": {"state": "known", "value": "Essential 84 kWh"},
            "modelYear": {"state": "known", "value": 2025},
            "firstRegistrationYear": {"state": "not_applicable"},
            "bodyStyle": {"state": "known", "value": "suv"},
            "odometerKm": {"state": "known", "value": 0},
            "batteryCapacity": {
                "state": "known",
                "value": {"valueKwh": 84, "basis": "not_stated"},
            },
            "wltpRangeKm": {"state": "known", "value": 570},
            "maxChargingPower": {
                "state": "known",
                "value": {"valueKw": 260, "kind": "dc"},
            },
            "chargingTime10To80Minutes": {"state": "known", "value": 18},
        },
        "imageUrls": [],
        "supportedLeasingForm": "operational",
        "providerFormLabel": "Privatleasing",
        "termMonths": 36,
        "annualMileageKm": {"state": "known", "value": 10000},
        "normalEndMechanism": {
            "state": "known",
            "value": "return_to_provider",
        },
        "residualRiskAllocation": {"state": "known", "value": "provider"},
        "serviceArrangements": {"state": "known", "value": []},
        "baseCashFlowStream": [
            {
                "key": "initial-payment",
                "month": 0,
                "kind": "initial_payment",
                "direction": "payment",
                "amount": {"state": "known", "value": 15990},
                "refundability": {
                    "state": "known",
                    "value": "not_refundable",
                },
            },
            *[
                {
                    "key": f"lease-payment-{month}",
                    "month": month,
                    "kind": "lease_payment",
                    "direction": "payment",
                    "amount": {"state": "known", "value": 3795},
                    "refundability": {"state": "not_applicable"},
                }
                for month in range(1, 37)
            ],
        ],
        "advertisedTotal": {"state": "not_stated"},
        "calculatedTotal": {
            "state": "available",
            "value": {"amountDkk": 152610},
        },
        "calculatedMonthlyTotal": {
            "state": "available",
            "value": {"amountDkk": 4239.17},
        },
    }


def sample_quarantined_candidate() -> dict[str, object]:
    return {
        "offerIdentity": "terminalen:ioniq-6:unknown",
        "providerId": "terminalen",
        "canonicalSourceUrl": "https://example.test/terminalen/ioniq-6",
        "reasons": [
            {
                "criterion": "term_months",
                "state": "not_stated",
                "code": "term.not-stated",
                "evidence": [
                    {
                        "sourceUrl": "https://example.test/terminalen/ioniq-6",
                        "excerpt": "Term not stated",
                    }
                ],
            }
        ],
    }


def first_offer(dataset: dict[str, object]) -> dict[str, object]:
    offers = cast(list[object], dataset["offers"])
    return cast(dict[str, object], offers[0])


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "car_picker", *arguments],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )


def write_dataset(workspace: Path, dataset: dict[str, object]) -> None:
    dataset_path = workspace / "var/catalogue-dataset.json"
    dataset_path.parent.mkdir(parents=True)
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
