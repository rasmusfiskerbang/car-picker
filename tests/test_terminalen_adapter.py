from __future__ import annotations

import json
import unittest
from pathlib import Path

from car_picker.terminalen import TerminalenAdapter


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
