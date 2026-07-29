from __future__ import annotations

import json
import unittest
from pathlib import Path

from car_picker.fleasing import StructuralSourceError
from car_picker.terminalen import (
    NAVIGATION_STATE_KEY,
    TerminalenAdapter,
    model_price_urls,
)


FIXTURES = Path(__file__).resolve().parent / "fixtures/terminalen"
CATALOGUE_URL = "https://www.terminalen.dk/nye-biler/hyundai"
PRICE_PATH = "/nye-biler/hyundai/hyundai-inster/pris-og-udstyr"
PRICE_URL = f"https://www.terminalen.dk{PRICE_PATH}"
API_URL = f"https://www.terminalen.dk/api/page/url?url={PRICE_PATH}&culture=da-DK"


class FixtureHttpClient:
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.requested_urls: list[str] = []

    def get_text(self, url: str) -> str:
        self.requested_urls.append(url)
        return self.responses[url]


class TerminalenAdapterTest(unittest.TestCase):
    def test_discovers_deduplicated_model_price_pages_from_the_bounded_navigation_state(
        self,
    ) -> None:
        catalogue_html = (FIXTURES / "catalogue.html").read_text(encoding="utf-8")

        urls = model_price_urls(catalogue_html, CATALOGUE_URL)

        self.assertEqual(urls, [PRICE_URL])

    def test_rejects_unrelated_urls_and_nodes_that_are_not_model_subpages(
        self,
    ) -> None:
        state = {
            "G./api/navigation?culture=da-DK&levels=10": {
                "body": [
                    {
                        "children": [
                            {
                                "url": PRICE_PATH,
                                "template": "otherTemplate",
                            },
                            {
                                "url": (
                                    "/nye-biler/hyundai/hyundai-inster/"
                                    "pris-og-udstyr?tracking=1"
                                ),
                                "template": "modelSubpage",
                            },
                            {
                                "url": f"{PRICE_PATH}#offers",
                                "template": "modelSubpage",
                            },
                            {
                                "url": (
                                    "https://other.example/nye-biler/hyundai/"
                                    "hyundai-inster/pris-og-udstyr"
                                ),
                                "template": "modelSubpage",
                            },
                            {
                                "url": "/nye-biler/kia/ev3/pris-og-udstyr",
                                "template": "modelSubpage",
                            },
                        ]
                    }
                ]
            }
        }
        catalogue_html = (
            '<script id="terminalen-ncg-state" type="application/json">'
            f"{json.dumps(state)}"
            "</script>"
        )

        self.assertEqual(model_price_urls(catalogue_html, CATALOGUE_URL), [])

    def test_rejects_malformed_embedded_navigation_state(self) -> None:
        catalogue_html = (
            '<script id="terminalen-ncg-state" type="application/json">'
            '{"G./api/navigation?culture=da-DK&levels=10":'
            "</script>"
        )

        with self.assertRaisesRegex(
            StructuralSourceError,
            "Terminalen catalogue navigation state is malformed",
        ):
            model_price_urls(catalogue_html, CATALOGUE_URL)

    def test_rejects_malformed_navigation_children_even_beside_a_valid_page(
        self,
    ) -> None:
        state = {
            "G./api/navigation?culture=da-DK&levels=10": {
                "body": [
                    {"children": "not-an-array"},
                    {
                        "url": PRICE_PATH,
                        "template": "modelSubpage",
                        "children": [],
                    },
                ]
            }
        }
        catalogue_html = (
            '<script id="terminalen-ncg-state" type="application/json">'
            f"{json.dumps(state)}"
            "</script>"
        )

        with self.assertRaisesRegex(
            StructuralSourceError,
            "Terminalen catalogue navigation node children must be an array",
        ):
            model_price_urls(catalogue_html, CATALOGUE_URL)

    def test_ignores_incidental_model_price_text_outside_the_navigation_state(
        self,
    ) -> None:
        catalogue_html = (
            f"<p>{PRICE_PATH}</p>"
            '<script type="application/json">'
            f'{{"url":"{PRICE_PATH}","template":"modelSubpage"}}'
            "</script>"
            '<script id="terminalen-ncg-state" type="application/json">'
            f'{{"{NAVIGATION_STATE_KEY}":{{"body":[]}}}}'
            "</script>"
        )

        self.assertEqual(model_price_urls(catalogue_html, CATALOGUE_URL), [])

    def test_rejects_a_missing_designated_navigation_state(self) -> None:
        with self.assertRaisesRegex(
            StructuralSourceError,
            "Terminalen catalogue is missing its designated navigation state",
        ):
            model_price_urls(f"<p>{PRICE_PATH}</p>", CATALOGUE_URL)

    def test_collects_each_explicit_private_vat_inclusive_configuration_from_its_same_path_api_response(
        self,
    ) -> None:
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: (FIXTURES / "catalogue.html").read_text(
                    encoding="utf-8"
                ),
                PRICE_URL: (FIXTURES / "inster-price-page.html").read_text(
                    encoding="utf-8"
                ),
                API_URL: (FIXTURES / "inster-price-page.json").read_text(
                    encoding="utf-8"
                ),
            }
        )

        candidates = TerminalenAdapter(
            client, retrieved_at="2026-07-22T12:00:00Z"
        ).collect(CATALOGUE_URL)

        self.assertEqual(client.requested_urls, [CATALOGUE_URL, PRICE_URL, API_URL])
        identities = [candidate["offerIdentity"] for candidate in candidates]
        self.assertEqual(len(set(identities)), 2)
        self.assertTrue(
            all(
                identity.startswith("terminalen:HY_INSTER:private-")
                for identity in identities
            )
        )
        self.assertEqual(
            [candidate["admissionOutcome"] for candidate in candidates],
            ["admitted", "admitted"],
        )
        self.assertTrue(candidates[0]["passengerCarScope"]["value"])
        self.assertTrue(candidates[0]["currentAvailability"]["value"])
        self.assertEqual(candidates[0]["supportedLeasingForm"]["value"], "operational")
        self.assertEqual(candidates[0]["providerFormLabel"]["value"], "Privatleasing")
        self.assertNotEqual(
            candidates[0]["providerFormLabel"]["evidence"],
            candidates[0]["supportedLeasingForm"]["evidence"],
        )
        self.assertEqual(candidates[0]["advertisedMonthlyPayment"]["valueDkk"], 3095)
        self.assertEqual(candidates[0]["annualMileageKm"]["value"], 10000)
        self.assertEqual(
            candidates[0]["normalEndMechanism"]["value"], "return_to_provider"
        )
        self.assertEqual(candidates[0]["residualRiskAllocation"]["value"], "provider")
        self.assertEqual(
            candidates[0]["providerAdvertisedAggregate"]["valueDkk"], 117195
        )
        self.assertEqual(
            candidates[0]["providerAdvertisedAggregate"]["scope"],
            "normal_completion_base_cash_flows",
        )
        self.assertEqual(
            [event["meaning"] for event in candidates[0]["baseCashFlowStream"]],
            ["Udbetaling", "Månedlig ydelse", "Inspektionsgebyr"],
        )
        self.assertTrue(
            all(
                event["amountBasis"] == "including_vat"
                for event in candidates[0]["baseCashFlowStream"]
            )
        )
        self.assertEqual(
            candidates[0]["serviceArrangements"]["value"][0]["scope"],
            "alle fabriksanbefalede services",
        )
        self.assertEqual(
            candidates[0]["exclusions"]["value"],
            [
                {"category": "co2_fee", "treatment": "excluded", "scope": "CO2-afgift"},
                {
                    "category": "insurance",
                    "treatment": "excluded",
                    "scope": "forsikring",
                },
                {"category": "tyres", "treatment": "excluded", "scope": "ekstra dæk"},
            ],
        )
        self.assertEqual(
            candidates[0]["sourceMetadata"]["documents"][2]["sourceUrl"], API_URL
        )
        self.assertNotIn("quarantineReasons", candidates[0])

    def test_quarantines_a_configuration_when_admission_evidence_is_missing(
        self,
    ) -> None:
        payload = json.loads(
            (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8")
        )
        del payload["vehicleData"]["vehicleType"]
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: (FIXTURES / "catalogue.html").read_text(
                    encoding="utf-8"
                ),
                PRICE_URL: (FIXTURES / "inster-price-page.html").read_text(
                    encoding="utf-8"
                ),
                API_URL: json.dumps(payload),
            }
        )

        candidate = TerminalenAdapter(
            client, retrieved_at="2026-07-22T12:00:00Z"
        ).collect(CATALOGUE_URL)[0]

        self.assertEqual(candidate["admissionOutcome"], "quarantined")
        self.assertEqual(candidate["passengerCarScope"]["state"], "not_stated")
        self.assertEqual(
            candidate["quarantineReasons"],
            [{"fact": "passengerCarScope", "state": "not_stated"}],
        )

    def test_rejects_an_api_response_for_another_model_path(self) -> None:
        payload = json.loads(
            (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8")
        )
        payload["url"] = "/nye-biler/hyundai/hyundai-kona-electric/pris-og-udstyr"
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: (FIXTURES / "catalogue.html").read_text(
                    encoding="utf-8"
                ),
                PRICE_URL: (FIXTURES / "inster-price-page.html").read_text(
                    encoding="utf-8"
                ),
                API_URL: json.dumps(payload),
            }
        )

        with self.assertRaisesRegex(ValueError, "same model-price path"):
            TerminalenAdapter(client, retrieved_at="2026-07-22T12:00:00Z").collect(
                CATALOGUE_URL
            )

    def test_preserves_missing_vat_and_mileage_as_not_stated(self) -> None:
        payload = json.loads(
            (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8")
        )
        legal = payload["grid"][0]["content"][3]
        legal["text"] = (
            "<p>Priseksemplerne er baseret på 36 mdr. Samlet betaling er inkl. service.</p>"
        )
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: (FIXTURES / "catalogue.html").read_text(
                    encoding="utf-8"
                ),
                PRICE_URL: (FIXTURES / "inster-price-page.html").read_text(
                    encoding="utf-8"
                ),
                API_URL: json.dumps(payload),
            }
        )

        candidate = TerminalenAdapter(
            client, retrieved_at="2026-07-22T12:00:00Z"
        ).collect(CATALOGUE_URL)[0]

        self.assertEqual(candidate["annualMileageKm"]["state"], "not_stated")
        self.assertTrue(
            all(
                event["amountBasis"] == "not_stated"
                for event in candidate["baseCashFlowStream"]
            )
        )
        self.assertEqual(candidate["admissionOutcome"], "quarantined")
        self.assertIn(
            {
                "fact": "baseCashFlowStream",
                "state": "not_stated",
                "code": "vat_basis_not_established",
            },
            candidate["quarantineReasons"],
        )

    def test_quarantines_structurally_invalid_admission_evidence(self) -> None:
        payload = json.loads(
            (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8")
        )
        payload["vehicleData"]["vehicleType"] = ["Personbil"]
        payload["isCurrent"] = "yes"
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: (FIXTURES / "catalogue.html").read_text(
                    encoding="utf-8"
                ),
                PRICE_URL: (FIXTURES / "inster-price-page.html").read_text(
                    encoding="utf-8"
                ),
                API_URL: json.dumps(payload),
            }
        )

        candidate = TerminalenAdapter(
            client, retrieved_at="2026-07-22T12:00:00Z"
        ).collect(CATALOGUE_URL)[0]

        self.assertEqual(candidate["admissionOutcome"], "quarantined")
        self.assertEqual(
            candidate["quarantineReasons"],
            [
                {"fact": "passengerCarScope", "state": "unclear"},
                {"fact": "currentAvailability", "state": "unclear"},
            ],
        )

    def test_distinguishes_cards_with_the_same_title_using_selected_source_values(
        self,
    ) -> None:
        payload = json.loads(
            (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8")
        )
        payload["grid"][0]["content"][2]["columns"][1]["title"] = "Lav udbetaling"
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: (FIXTURES / "catalogue.html").read_text(
                    encoding="utf-8"
                ),
                PRICE_URL: (FIXTURES / "inster-price-page.html").read_text(
                    encoding="utf-8"
                ),
                API_URL: json.dumps(payload),
            }
        )

        candidates = TerminalenAdapter(
            client, retrieved_at="2026-07-22T12:00:00Z"
        ).collect(CATALOGUE_URL)

        self.assertEqual(
            len({candidate["sourceLocalConfigurationKey"] for candidate in candidates}),
            2,
        )

    def test_rejects_a_malformed_private_card_instead_of_publishing_a_partial_model(
        self,
    ) -> None:
        payload = json.loads(
            (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8")
        )
        card = payload["grid"][0]["content"][2]["columns"][1]
        card["text"] = card["text"].replace(
            "Samlet betaling i perioden: 151.395 kr.", ""
        )
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: (FIXTURES / "catalogue.html").read_text(
                    encoding="utf-8"
                ),
                PRICE_URL: (FIXTURES / "inster-price-page.html").read_text(
                    encoding="utf-8"
                ),
                API_URL: json.dumps(payload),
            }
        )

        with self.assertRaisesRegex(ValueError, "explicit DKK amount"):
            TerminalenAdapter(client, retrieved_at="2026-07-22T12:00:00Z").collect(
                CATALOGUE_URL
            )


if __name__ == "__main__":
    unittest.main()
