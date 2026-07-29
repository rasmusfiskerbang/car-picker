from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DATASET = REPOSITORY_ROOT / "tests/fixtures/one-offer-catalogue-dataset.json"


class BuildSiteTest(unittest.TestCase):
    def test_build_site_projects_one_evidence_backed_catalogue_offer(self) -> None:
        """The public CLI builds the one-offer catalogue shown to a prospective lessee."""
        canonical_offer = json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))[
            "catalogueOffers"
        ][0]
        for derived_fact in (
            "upfrontCashRequirement",
            "nominalBaseOutlay",
            "nominalMonthlyEquivalent",
        ):
            self.assertNotIn(derived_fact, canonical_offer)

        with tempfile.TemporaryDirectory() as temporary_directory:
            site_path = Path(temporary_directory) / "site"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "build-site",
                    "--dataset",
                    str(FIXTURE_DATASET),
                    "--output",
                    str(site_path),
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((site_path / "index.html").is_file())
            self.assertTrue((site_path / "app.js").is_file())
            self.assertTrue((site_path / "styles.css").is_file())
            projection = json.loads(
                (site_path / "projection.json").read_text(encoding="utf-8")
            )
            schema = json.loads(
                (site_path / "projection-schema.json").read_text(encoding="utf-8")
            )

        self.assertEqual(projection["schemaVersion"], "catalogue-presentation/v1")
        self.assertEqual(schema["title"], "CataloguePresentation")
        self.assertIn("PresentationOffer", schema["$defs"])
        self.assertEqual(
            projection["offers"],
            [
                {
                    "offerIdentity": "terminalen:ioniq-5:essential-84",
                    "provider": "Terminalen",
                    "providerSourceUrl": "https://example.test/ioniq-5",
                    "vehicleSpecification": {
                        "state": "known",
                        "value": "Hyundai IONIQ 5 Essential 84 kWh",
                        "evidence": {
                            "sourceUrl": "https://example.test/ioniq-5",
                            "wording": "Hyundai IONIQ 5 Essential 84 kWh.",
                        },
                    },
                    "supportedLeasingForm": {
                        "state": "known",
                        "value": "operational",
                        "evidence": {
                            "sourceUrl": "https://example.test/ioniq-5",
                            "wording": "Privatleasing med aflevering ved udløb.",
                        },
                    },
                    "providerFormLabel": {
                        "state": "known",
                        "value": "Privatleasing med aflevering ved udløb.",
                        "evidence": {
                            "sourceUrl": "https://example.test/ioniq-5",
                            "wording": "Privatleasing med aflevering ved udløb.",
                        },
                    },
                    "residualRiskAllocation": {
                        "state": "known",
                        "value": "provider",
                        "evidence": {
                            "sourceUrl": "https://example.test/ioniq-5",
                            "wording": "Udbyderen bærer værditabet.",
                        },
                    },
                    "registrationTaxTreatment": {
                        "state": "known",
                        "value": "full",
                        "evidence": {
                            "sourceUrl": "https://example.test/ioniq-5",
                            "wording": "Registreringsafgiften er betalt fuldt.",
                        },
                    },
                    "serviceArrangements": {
                        "state": "known",
                        "value": [
                            {
                                "category": "service",
                                "treatment": "included",
                                "scope": "Alle fabriksanbefalede services.",
                            }
                        ],
                        "evidence": {
                            "sourceUrl": "https://example.test/ioniq-5",
                            "wording": "Inkl. alle fabriksanbefalede services.",
                        },
                    },
                    "exclusions": {
                        "state": "known",
                        "value": [
                            {
                                "category": "insurance",
                                "treatment": "required_external",
                                "scope": "Forsikring aftales og betales særskilt.",
                            }
                        ],
                        "evidence": {
                            "sourceUrl": "https://example.test/ioniq-5",
                            "wording": "Forsikring er ikke inkluderet.",
                        },
                    },
                    "exposureScenarios": {
                        "state": "known",
                        "value": [
                            {
                                "kind": "excess_mileage",
                                "trigger": "Hvis kilometergrænsen overskrides.",
                                "requiredInputs": ["Ekstra kilometer"],
                                "inputKinds": ["excess_distance_km"],
                                "rateDkk": 2,
                            },
                            {
                                "kind": "damage",
                                "trigger": "Hvis bilen afleveres med skader ud over normal slitage.",
                                "requiredInputs": [],
                            },
                        ],
                        "evidence": {
                            "sourceUrl": "https://example.test/ioniq-5",
                            "wording": "Overkørte kilometer afregnes med 2 kr. pr. km; skader kan medføre betaling.",
                        },
                    },
                    "advertisedMonthlyPayment": {
                        "state": "known",
                        "valueDkk": 3795,
                        "evidence": {
                            "sourceUrl": "https://example.test/ioniq-5",
                            "wording": "Månedlig ydelse 3.795 kr.",
                        },
                    },
                    "upfrontCashRequirement": {
                        "state": "known",
                        "valueDkk": 15990,
                        "calculation": {
                            "method": "base_cash_flow_stream",
                            "inputEvidence": [
                                {
                                    "sourceUrl": "https://example.test/ioniq-5",
                                    "wording": "Førstegangsydelse 15.990 kr.",
                                },
                                {
                                    "sourceUrl": "https://example.test/ioniq-5",
                                    "wording": "Månedlig ydelse 3.795 kr. i 36 måneder.",
                                },
                            ],
                        },
                    },
                    "nominalBaseOutlay": {
                        "state": "known",
                        "valueDkk": 152610,
                        "calculation": {
                            "method": "base_cash_flow_stream",
                            "inputEvidence": [
                                {
                                    "sourceUrl": "https://example.test/ioniq-5",
                                    "wording": "Førstegangsydelse 15.990 kr.",
                                },
                                {
                                    "sourceUrl": "https://example.test/ioniq-5",
                                    "wording": "Månedlig ydelse 3.795 kr. i 36 måneder.",
                                },
                            ],
                        },
                    },
                    "nominalMonthlyEquivalent": {
                        "state": "known",
                        "valueDkk": 4239,
                        "calculation": {
                            "method": "base_cash_flow_stream",
                            "inputEvidence": [
                                {
                                    "sourceUrl": "https://example.test/ioniq-5",
                                    "wording": "Førstegangsydelse 15.990 kr.",
                                },
                                {
                                    "sourceUrl": "https://example.test/ioniq-5",
                                    "wording": "Månedlig ydelse 3.795 kr. i 36 måneder.",
                                },
                            ],
                        },
                    },
                    "operationReadiness": {
                        "upfrontCashRequirement": {
                            "state": "ready",
                            "blockingFacts": [],
                        },
                        "nominalBaseOutlay": {
                            "state": "ready",
                            "blockingFacts": [],
                        },
                        "nominalMonthlyEquivalent": {
                            "state": "ready",
                            "blockingFacts": [],
                        },
                    },
                    "termMonths": {
                        "state": "known",
                        "value": 36,
                        "evidence": {
                            "sourceUrl": "https://example.test/ioniq-5",
                            "wording": "Løbetid 36 måneder.",
                        },
                    },
                    "annualMileageKm": {
                        "state": "known",
                        "value": 10000,
                        "evidence": {
                            "sourceUrl": "https://example.test/ioniq-5",
                            "wording": "10.000 km om året.",
                        },
                    },
                    "normalEndMechanism": {
                        "state": "known",
                        "value": "return_to_provider",
                        "evidence": {
                            "sourceUrl": "https://example.test/ioniq-5",
                            "wording": "Bilen afleveres ved leasingperiodens udløb.",
                        },
                    },
                    "cashFlowBreakdown": [
                        {
                            "meaning": "Førstegangsydelse",
                            "direction": "payment",
                            "amountDkk": 15990,
                            "amountBasis": "including_vat",
                            "timing": "acceptance_to_handover",
                            "recurrenceCount": 1,
                            "refundability": "not_refundable",
                            "evidence": {
                                "sourceUrl": "https://example.test/ioniq-5",
                                "wording": "Førstegangsydelse 15.990 kr.",
                            },
                        },
                        {
                            "meaning": "Månedlig ydelse",
                            "direction": "payment",
                            "amountDkk": 3795,
                            "amountBasis": "including_vat",
                            "timing": "recurring",
                            "recurrenceCount": 36,
                            "refundability": "not_refundable",
                            "evidence": {
                                "sourceUrl": "https://example.test/ioniq-5",
                                "wording": "Månedlig ydelse 3.795 kr. i 36 måneder.",
                            },
                        },
                    ],
                }
            ],
        )

    def test_build_site_refuses_an_output_outside_the_ignored_site_boundary(
        self,
    ) -> None:
        """The CLI keeps generated site artifacts in an ignored `site` directory."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "dist"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "build-site",
                    "--dataset",
                    str(FIXTURE_DATASET),
                    "--output",
                    str(output_path),
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must name a site directory", result.stderr)

    def test_build_site_rejects_persisted_derived_comparison_values(self) -> None:
        dataset = json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))
        dataset["catalogueOffers"][0]["nominalBaseOutlay"] = {
            "state": "known",
            "valueDkk": 1,
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            dataset_path = Path(temporary_directory) / "catalogue-dataset.json"
            dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "build-site",
                    "--dataset",
                    str(dataset_path),
                    "--output",
                    str(Path(temporary_directory) / "site"),
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nominalBaseOutlay", result.stderr)
        self.assertIn("Extra inputs are not permitted", result.stderr)

    def test_build_site_withholds_quarantined_candidates_from_the_active_catalogue(
        self,
    ) -> None:
        """A quarantined candidate remains in the dataset but cannot enter the static catalogue."""
        dataset = json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))
        quarantined_candidate = json.loads(json.dumps(dataset["catalogueOffers"][0]))
        quarantined_candidate["offerIdentity"] = "terminalen:ioniq-5:quarantined"
        quarantined_candidate["admissionOutcome"] = "quarantined"
        quarantined_candidate["quarantineReasons"] = [
            {
                "fact": "supportedLeasingForm",
                "state": "unclear",
                "code": "admission_fact_unclear",
            }
        ]
        dataset["coverage"]["providers"][0]["quarantinedCandidateCount"] = 1
        dataset["quarantinedCandidates"].append(quarantined_candidate)

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            dataset_path = temporary_path / "catalogue-dataset.json"
            site_path = temporary_path / "site"
            dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "build-site",
                    "--dataset",
                    str(dataset_path),
                    "--output",
                    str(site_path),
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            projection = json.loads(
                (site_path / "projection.json").read_text(encoding="utf-8")
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [offer["offerIdentity"] for offer in projection["offers"]],
            ["terminalen:ioniq-5:essential-84"],
        )

    def test_build_site_explains_coverage_without_claiming_the_whole_market(
        self,
    ) -> None:
        """The public coverage register describes one complete catalogue dataset."""
        dataset = json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))
        dataset["coverage"]["providers"][0]["designatedSource"] = (
            "Terminalen model price page"
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            dataset_path = temporary_path / "catalogue-dataset.json"
            site_path = temporary_path / "site"
            dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "build-site",
                    "--dataset",
                    str(dataset_path),
                    "--output",
                    str(site_path),
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            projection = json.loads(
                (site_path / "projection.json").read_text(encoding="utf-8")
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(projection["generatedAt"], "2026-07-22T12:00:00Z")
        self.assertEqual(
            projection["coverage"]["providers"],
            dataset["coverage"]["providers"],
        )
        for hidden_detail in ("quarantineReasons", "parserMetadata", "hash"):
            self.assertNotIn(hidden_detail, json.dumps(projection["coverage"]))

    def test_build_site_derives_values_and_one_cash_flow_breakdown(self) -> None:
        """The public site build exposes service-derived totals from sourced events."""
        dataset = json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))
        offer = dataset["catalogueOffers"][0]
        offer["canonicalOfferUrl"] = "https://example.test/ioniq-5"
        offer["termMonths"] = known_value_fact(12, "Løbetid 12 måneder.")
        offer["baseCashFlowStream"] = [
            cash_flow_event(
                "Førstegangsydelse", "payment", 12000, "acceptance_to_handover"
            ),
            cash_flow_event(
                "Depositum", "payment", 4000, "acceptance_to_handover", "refundable"
            ),
            cash_flow_event(
                "Månedlig ydelse", "payment", 1000, "recurring", recurrence_count=12
            ),
            cash_flow_event(
                "Tilbagebetaling af depositum",
                "receipt",
                4000,
                "normal_completion_end",
                "refundable",
            ),
            cash_flow_event(
                "Obligatorisk slutbetaling", "payment", 6000, "normal_completion_end"
            ),
        ]
        missing_monthly_offer = json.loads(json.dumps(offer))
        missing_monthly_offer["offerIdentity"] = "terminalen:ioniq-5:missing-monthly"
        missing_monthly_offer["baseCashFlowStream"][2]["amountDkk"] = None
        missing_monthly_offer["baseCashFlowStream"][2]["blockingFacts"] = [
            "advertisedMonthlyPayment"
        ]
        dataset["catalogueOffers"].append(missing_monthly_offer)

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            dataset_path = temporary_path / "catalogue-dataset.json"
            site_path = temporary_path / "site"
            dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "build-site",
                    "--dataset",
                    str(dataset_path),
                    "--output",
                    str(site_path),
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            projection = json.loads(
                (site_path / "projection.json").read_text(encoding="utf-8")
            )

        rendered_offer = projection["offers"][0]
        self.assertEqual(rendered_offer["upfrontCashRequirement"]["valueDkk"], 16000)
        self.assertEqual(rendered_offer["nominalBaseOutlay"]["valueDkk"], 30000)
        self.assertEqual(rendered_offer["nominalMonthlyEquivalent"]["valueDkk"], 2500)
        self.assertEqual(
            rendered_offer["nominalBaseOutlay"]["calculation"]["method"],
            "base_cash_flow_stream",
        )
        self.assertEqual(
            [event["meaning"] for event in rendered_offer["cashFlowBreakdown"]],
            [
                "Førstegangsydelse",
                "Depositum",
                "Månedlig ydelse",
                "Tilbagebetaling af depositum",
                "Obligatorisk slutbetaling",
            ],
        )
        rendered_missing_monthly_offer = projection["offers"][1]
        self.assertEqual(
            rendered_missing_monthly_offer["upfrontCashRequirement"]["valueDkk"], 16000
        )
        self.assertEqual(
            rendered_missing_monthly_offer["nominalBaseOutlay"]["blockingFacts"],
            ["advertisedMonthlyPayment"],
        )
        self.assertEqual(
            rendered_missing_monthly_offer["nominalMonthlyEquivalent"]["blockingFacts"],
            ["advertisedMonthlyPayment"],
        )
        self.assertIsNone(
            rendered_missing_monthly_offer["cashFlowBreakdown"][2]["amountDkk"]
        )

    def test_build_site_exposes_filterable_offer_facts_without_changing_source_order(
        self,
    ) -> None:
        """The public catalogue contract keeps the facts needed to narrow offers."""
        dataset = json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))
        first_offer = dataset["catalogueOffers"][0]
        first_offer["residualRiskAllocation"] = known_value_fact(
            "provider", "Udbyderen bærer værditabet."
        )
        second_offer = json.loads(json.dumps(first_offer))
        second_offer["offerIdentity"] = "fleasing:i4:private-36"
        second_offer["provider"] = "Fleasing"
        second_offer["vehicleSpecification"]["value"] = {
            "make": "BMW",
            "model": "i4",
            "trim": "eDrive35",
        }
        second_offer["supportedLeasingForm"] = known_value_fact(
            "financial", "Finansiel leasing."
        )
        second_offer["residualRiskAllocation"] = known_value_fact(
            "lessee", "Lessee bærer restværdirisikoen."
        )
        second_offer["termMonths"] = known_value_fact(24, "Løbetid 24 måneder.")
        second_offer["annualMileageKm"] = known_value_fact(15000, "15.000 km om året.")
        dataset["coverage"]["providers"].append(
            {
                "name": "Fleasing",
                "designatedSource": "Fleasing private-offer catalogue and linked details",
                "quarantinedCandidateCount": 0,
            }
        )
        dataset["catalogueOffers"].append(second_offer)

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            dataset_path = temporary_path / "catalogue-dataset.json"
            site_path = temporary_path / "site"
            dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "build-site",
                    "--dataset",
                    str(dataset_path),
                    "--output",
                    str(site_path),
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            projection = json.loads(
                (site_path / "projection.json").read_text(encoding="utf-8")
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [offer["offerIdentity"] for offer in projection["offers"]],
            ["terminalen:ioniq-5:essential-84", "fleasing:i4:private-36"],
        )
        self.assertEqual(
            projection["offers"][1]["residualRiskAllocation"]["value"], "lessee"
        )

    def test_build_site_exposes_only_auditable_calculation_examples_for_supported_exposures(
        self,
    ) -> None:
        """A prospective lessee can calculate a sourced example without changing offer values."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            site_path = Path(temporary_directory) / "site"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "build-site",
                    "--dataset",
                    str(FIXTURE_DATASET),
                    "--output",
                    str(site_path),
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            projection = json.loads(
                (site_path / "projection.json").read_text(encoding="utf-8")
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            projection["offers"][0]["exposureScenarios"]["value"],
            [
                {
                    "kind": "excess_mileage",
                    "trigger": "Hvis kilometergrænsen overskrides.",
                    "requiredInputs": ["Ekstra kilometer"],
                    "inputKinds": ["excess_distance_km"],
                    "rateDkk": 2,
                },
                {
                    "kind": "damage",
                    "trigger": "Hvis bilen afleveres med skader ud over normal slitage.",
                    "requiredInputs": [],
                },
            ],
        )

    def test_build_site_rejects_exposure_input_kinds_that_do_not_align_with_their_labels(
        self,
    ) -> None:
        """Normalized input kinds must remain paired with the source labels shown to the prospective lessee."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            dataset_path = Path(temporary_directory) / "catalogue-dataset.json"
            dataset = json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))
            scenario = dataset["catalogueOffers"][0]["exposureScenarios"]["value"][0]
            scenario["inputKinds"].append("unrelated_input")
            dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "build-site",
                    "--dataset",
                    str(dataset_path),
                    "--output",
                    str(Path(temporary_directory) / "site"),
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "exposure input kinds must align with required inputs", result.stderr
        )


def known_value_fact(value: object, wording: str) -> dict[str, object]:
    return {
        "state": "known",
        "value": value,
        "evidence": {"sourceUrl": "https://example.test/ioniq-5", "wording": wording},
    }


def known_money_fact(value: int, wording: str) -> dict[str, object]:
    return {
        "state": "known",
        "valueDkk": value,
        "evidence": {"sourceUrl": "https://example.test/ioniq-5", "wording": wording},
    }


def cash_flow_event(
    meaning: str,
    direction: str,
    amount_dkk: int,
    timing: str,
    refundability: str = "not_refundable",
    recurrence_count: int = 1,
) -> dict[str, object]:
    return {
        "meaning": meaning,
        "direction": direction,
        "amountDkk": amount_dkk,
        "amountBasis": "including_vat",
        "timing": timing,
        "refundability": refundability,
        "recurrenceCount": recurrence_count,
        "includedInBase": True,
        "evidence": {
            "sourceUrl": "https://example.test/ioniq-5",
            "wording": f"{meaning}: {amount_dkk} kr.",
        },
    }


if __name__ == "__main__":
    unittest.main()
