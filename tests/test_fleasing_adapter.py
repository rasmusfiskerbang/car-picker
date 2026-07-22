from __future__ import annotations

import unittest
from pathlib import Path

from car_picker.comparison import calculate_comparison_values
from car_picker.fleasing import FleasingAdapter, StructuralSourceError, catalogue_detail_urls


FIXTURE_DIRECTORY = Path(__file__).resolve().parent / "fixtures/fleasing"
CATALOGUE_URL = "https://fleasing.dk/biler/"
DETAIL_URL = "https://fleasing.dk/bil/?aston-martin-db9-volante-aut&vid=442795427"
MISSING_MONTHLY_DETAIL_URL = "https://fleasing.dk/bil/?bmw-i4&vid=771869804"


class FixtureHttpClient:
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.requested_urls: list[str] = []

    def get_text(self, url: str) -> str:
        self.requested_urls.append(url)
        return self.responses[url]


class FleasingAdapterTest(unittest.TestCase):
    def test_ignores_catalogue_links_to_an_undesignated_host(self) -> None:
        detail_urls = catalogue_detail_urls(
            """
            <a href="/bil/?a&amp;vid=442795427">Fleasing</a>
            <a href="https://bilinfo.dk/bil/?a&amp;vid=999">Bilinfo</a>
            """,
            CATALOGUE_URL,
        )

        self.assertEqual(detail_urls, ["https://fleasing.dk/bil/?a&vid=442795427"])

    def test_collects_each_private_vat_inclusive_configuration_with_evidence(self) -> None:
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: (FIXTURE_DIRECTORY / "catalogue.html").read_text(encoding="utf-8"),
                DETAIL_URL: (FIXTURE_DIRECTORY / "aston-martin-db9.html").read_text(encoding="utf-8"),
                MISSING_MONTHLY_DETAIL_URL: (FIXTURE_DIRECTORY / "bmw-i4.html").read_text(encoding="utf-8"),
            }
        )

        candidates = FleasingAdapter(client, retrieved_at="2026-07-22T12:00:00Z").collect()

        self.assertEqual(client.requested_urls, [CATALOGUE_URL, DETAIL_URL, MISSING_MONTHLY_DETAIL_URL])
        self.assertEqual(
            [(candidate["offerIdentity"], candidate["admissionStatus"]) for candidate in candidates],
            [
                ("fleasing:442795427:private-b3e29d362bda", "quarantined"),
                ("fleasing:771869804:private-390493d196b5", "quarantined"),
            ],
        )
        candidate = candidates[0]
        self.assertEqual(candidate["advertisedMonthlyPayment"]["valueDkk"], 15865)
        self.assertEqual(candidate["termMonths"]["value"], 12)
        self.assertEqual(candidate["baseCashFlowBlockers"], ["normalEndMechanism"])
        self.assertEqual(
            calculate_comparison_values(candidate)["nominalBaseOutlay"],
            {"state": "not_stated", "blockingFacts": ["normalEndMechanism"]},
        )
        self.assertEqual(
            candidate["baseCashFlowStream"],
            [
                {
                    "meaning": "Udbetaling",
                    "direction": "payment",
                    "amountDkk": 142813,
                    "amountBasis": "including_vat",
                    "timing": "acceptance_to_handover",
                    "recurrenceCount": 1,
                    "refundability": "not_refundable",
                    "includedInBase": True,
                    "evidence": {
                        "sourceUrl": DETAIL_URL,
                        "wording": "Udbetaling 142.813 kr. /inkl. moms",
                    },
                },
                {
                    "meaning": "Ydelse pr. måned",
                    "direction": "payment",
                    "amountDkk": 15865,
                    "amountBasis": "including_vat",
                    "timing": "recurring",
                    "recurrenceCount": 12,
                    "refundability": "not_refundable",
                    "includedInBase": True,
                    "evidence": {
                        "sourceUrl": DETAIL_URL,
                        "wording": "Ydelse pr. måned 15.865 kr. /inkl. moms; Leasingperiode 12",
                    },
                },
            ],
        )
        self.assertEqual(candidate["vehicleSpecification"]["value"], {
            "make": "Aston Martin",
            "model": "DB9",
            "trim": "Volante aut.",
        })
        self.assertEqual(
            candidate["advertisedMonthlyPayment"]["evidence"],
            {
                "sourceUrl": DETAIL_URL,
                "wording": "Ydelse pr. måned 15.865 kr. /inkl. moms",
            },
        )
        self.assertEqual(candidate["sourceMetadata"]["parserVersion"], "fleasing-html-v2")
        self.assertEqual(len(candidate["sourceMetadata"]["documents"][0]["contentSha256"]), 64)
        self.assertEqual(
            candidate["quarantineReasons"],
            [
                {"fact": "passengerCarScope", "state": "not_stated"},
                {"fact": "supportedLeasingForm", "state": "unclear"},
            ],
        )
        self.assertEqual(
            candidates[1]["quarantineReasons"],
            [
                {"fact": "passengerCarScope", "state": "not_stated"},
                {"fact": "supportedLeasingForm", "state": "unclear"},
                {"fact": "advertisedMonthlyPayment", "state": "not_stated"},
            ],
        )
        self.assertEqual(candidates[1]["baseCashFlowStream"][1]["amountDkk"], None)
        self.assertEqual(
            candidates[1]["baseCashFlowStream"][1]["blockingFacts"],
            ["advertisedMonthlyPayment"],
        )

    def test_detects_a_detail_page_that_loses_the_private_configuration_structure(self) -> None:
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: (FIXTURE_DIRECTORY / "catalogue.html").read_text(encoding="utf-8"),
                DETAIL_URL: """
                    <article data-offer-id="442795427" data-make="Aston Martin" data-model="DB9"
                    data-trim="Volante" data-passenger-car="true" data-availability="available"></article>
                """,
            }
        )

        with self.assertRaisesRegex(StructuralSourceError, "private-pricing tab"):
            FleasingAdapter(client, retrieved_at="2026-07-22T12:00:00Z").collect()



if __name__ == "__main__":
    unittest.main()
