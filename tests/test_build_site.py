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
            projection = json.loads((site_path / "projection.json").read_text(encoding="utf-8"))

        self.assertEqual(projection["schemaVersion"], "catalogue-presentation/v1")
        self.assertEqual(projection["offers"], [
            {
                "offerIdentity": "terminalen:ioniq-5:essential-84",
                "provider": "Terminalen",
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
                "residualRiskAllocation": {
                    "state": "known",
                    "value": "provider",
                    "evidence": {
                        "sourceUrl": "https://example.test/ioniq-5",
                        "wording": "Udbyderen bærer værditabet.",
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
                    "state": "not_stated",
                    "blockingFacts": ["baseCashFlowStream"],
                    "evidence": {
                        "sourceUrl": "https://example.test/ioniq-5",
                        "wording": "Beregnet af tjenesten fra betalingsstrømmen.",
                    },
                },
                "nominalBaseOutlay": {
                    "state": "not_stated",
                    "blockingFacts": ["baseCashFlowStream"],
                    "evidence": {
                        "sourceUrl": "https://example.test/ioniq-5",
                        "wording": "Beregnet af tjenesten fra betalingsstrømmen.",
                    },
                },
                "nominalMonthlyEquivalent": {
                    "state": "not_stated",
                    "blockingFacts": ["baseCashFlowStream"],
                    "evidence": {
                        "sourceUrl": "https://example.test/ioniq-5",
                        "wording": "Beregnet af tjenesten fra betalingsstrømmen.",
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
                    "value": "Bilen afleveres ved normal udløb.",
                    "evidence": {
                        "sourceUrl": "https://example.test/ioniq-5",
                        "wording": "Bilen afleveres ved leasingperiodens udløb.",
                    },
                },
            }
        ])

    def test_build_site_refuses_an_output_outside_the_ignored_site_boundary(self) -> None:
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

    def test_build_site_withholds_quarantined_candidates_from_the_active_catalogue(self) -> None:
        """A quarantined offer remains in the dataset but cannot enter the static catalogue."""
        dataset = json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))
        quarantined_offer = dataset["catalogueOffers"][0].copy()
        quarantined_offer["offerIdentity"] = "terminalen:ioniq-5:quarantined"
        quarantined_offer["admissionStatus"] = "quarantined"
        dataset["catalogueOffers"].append(quarantined_offer)

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
            projection = json.loads((site_path / "projection.json").read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [offer["offerIdentity"] for offer in projection["offers"]],
            ["terminalen:ioniq-5:essential-84"],
        )

    def test_build_site_derives_values_and_one_cash_flow_breakdown(self) -> None:
        """The public site build exposes service-derived totals from sourced events."""
        dataset = json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))
        offer = dataset["catalogueOffers"][0]
        offer["canonicalOfferUrl"] = "https://example.test/ioniq-5"
        offer["termMonths"] = known_value_fact(12, "Løbetid 12 måneder.")
        offer["baseCashFlowStream"] = [
            cash_flow_event("Førstegangsydelse", "payment", 12000, "acceptance_to_handover"),
            cash_flow_event("Depositum", "payment", 4000, "acceptance_to_handover", "refundable"),
            cash_flow_event("Månedlig ydelse", "payment", 1000, "recurring", recurrence_count=12),
            cash_flow_event("Tilbagebetaling af depositum", "receipt", 4000, "normal_completion_end", "refundable"),
            cash_flow_event("Obligatorisk slutbetaling", "payment", 6000, "normal_completion_end"),
        ]
        missing_monthly_offer = json.loads(json.dumps(offer))
        missing_monthly_offer["offerIdentity"] = "terminalen:ioniq-5:missing-monthly"
        missing_monthly_offer["baseCashFlowStream"][2]["amountDkk"] = None
        missing_monthly_offer["baseCashFlowStream"][2]["blockingFacts"] = ["advertisedMonthlyPayment"]
        dataset["catalogueOffers"].append(missing_monthly_offer)
        malformed_stream_offer = json.loads(json.dumps(offer))
        malformed_stream_offer["offerIdentity"] = "terminalen:ioniq-5:malformed-stream"
        del malformed_stream_offer["baseCashFlowStream"][0]["evidence"]
        dataset["catalogueOffers"].append(malformed_stream_offer)

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
            projection = json.loads((site_path / "projection.json").read_text(encoding="utf-8"))
            app_source = (site_path / "app.js").read_text(encoding="utf-8")

        rendered_offer = projection["offers"][0]
        self.assertEqual(rendered_offer["upfrontCashRequirement"]["valueDkk"], 16000)
        self.assertEqual(rendered_offer["nominalBaseOutlay"]["valueDkk"], 30000)
        self.assertEqual(rendered_offer["nominalMonthlyEquivalent"]["valueDkk"], 2500)
        self.assertEqual(
            rendered_offer["nominalBaseOutlay"]["evidence"]["wording"],
            "Beregnet af tjenesten fra betalingsstrømmen.",
        )
        self.assertIn("Oplyst af udbyderen", app_source)
        self.assertIn("Beregnet af tjenesten", app_source)
        self.assertIn("Betalingsstrøm bag beregningerne", app_source)
        self.assertIn("normal afslutningsmekanisme", app_source)
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
        self.assertEqual(rendered_missing_monthly_offer["upfrontCashRequirement"]["valueDkk"], 16000)
        self.assertEqual(
            rendered_missing_monthly_offer["nominalBaseOutlay"]["blockingFacts"],
            ["advertisedMonthlyPayment"],
        )
        self.assertEqual(
            rendered_missing_monthly_offer["nominalMonthlyEquivalent"]["blockingFacts"],
            ["advertisedMonthlyPayment"],
        )
        self.assertIsNone(rendered_missing_monthly_offer["cashFlowBreakdown"][2]["amountDkk"])
        rendered_malformed_stream_offer = projection["offers"][2]
        self.assertEqual(
            rendered_malformed_stream_offer["upfrontCashRequirement"]["blockingFacts"],
            ["baseCashFlowStream"],
        )
        self.assertNotIn("cashFlowBreakdown", rendered_malformed_stream_offer)

    def test_build_site_exposes_filterable_offer_facts_without_changing_source_order(self) -> None:
        """The public catalogue contract keeps the facts needed to narrow offers."""
        dataset = json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))
        first_offer = dataset["catalogueOffers"][0]
        first_offer["residualRiskAllocation"] = known_value_fact("provider", "Udbyderen bærer værditabet.")
        second_offer = json.loads(json.dumps(first_offer))
        second_offer["offerIdentity"] = "fleasing:i4:private-36"
        second_offer["provider"] = "Fleasing"
        second_offer["vehicleSpecification"]["value"] = {"make": "BMW", "model": "i4", "trim": "eDrive35"}
        second_offer["supportedLeasingForm"] = known_value_fact("financial", "Finansiel leasing.")
        second_offer["residualRiskAllocation"] = known_value_fact("lessee", "Lessee bærer restværdirisikoen.")
        second_offer["upfrontCashRequirement"] = known_money_fact(8000, "Udbetaling 8.000 kr.")
        second_offer["termMonths"] = known_value_fact(24, "Løbetid 24 måneder.")
        second_offer["annualMileageKm"] = known_value_fact(15000, "15.000 km om året.")
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
            projection = json.loads((site_path / "projection.json").read_text(encoding="utf-8"))
            app_source = (site_path / "app.js").read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [offer["offerIdentity"] for offer in projection["offers"]],
            ["terminalen:ioniq-5:essential-84", "fleasing:i4:private-36"],
        )
        self.assertEqual(projection["offers"][1]["residualRiskAllocation"]["value"], "lessee")
        for control in (
            "Søg efter bil eller udbyder",
            "Restværdirisiko",
            "Højeste kontante behov ved start",
            "Højeste fulde løbetid",
            "Højeste kilometer om året",
            "Køretøj",
            "Ingen tilbud matcher dine filtre",
            "Filtrering er ikke personlig rangering",
        ):
            self.assertIn(control, app_source)


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
