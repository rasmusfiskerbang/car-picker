from __future__ import annotations

import json
import unittest
from pathlib import Path

from car_picker.fleasing import StructuralSourceError
from car_picker.collection import TerminalenProviderAdapter
from car_picker.terminalen import (
    NAVIGATION_STATE_KEY,
    TerminalenAdapter,
    TerminalenBoundaryRecord,
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


def fixture_responses() -> dict[str, str]:
    return {
        CATALOGUE_URL: (FIXTURES / "catalogue.html").read_text(encoding="utf-8"),
        PRICE_URL: (FIXTURES / "inster-price-page.html").read_text(encoding="utf-8"),
        API_URL: (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8"),
    }


class TerminalenAdapterTest(unittest.TestCase):
    def test_boundary_records_are_pydantic_models_before_composition(self) -> None:
        client = FixtureHttpClient(fixture_responses())

        records = TerminalenAdapter(
            client, retrieved_at="2026-07-22T12:00:00Z"
        ).collect_boundary_records(CATALOGUE_URL)

        self.assertTrue(records)
        self.assertIsInstance(records[0], TerminalenBoundaryRecord)
        self.assertEqual(records[0].provider, "Terminalen")

    def test_skips_a_model_price_page_without_private_lease_offers(self) -> None:
        catalogue = json.loads(
            (
                '<script id="terminalen-ncg-state" type="application/json">'
                f'{{"{NAVIGATION_STATE_KEY}":{{"body":[]}}}}'
                "</script>"
            )
            .split(">", 1)[1]
            .split("</script>", 1)[0]
        )
        empty_path = "/nye-biler/hyundai/hyundai-bayon/pris-og-udstyr"
        empty_url = f"https://www.terminalen.dk{empty_path}"
        empty_api_url = (
            f"https://www.terminalen.dk/api/page/url?url={empty_path}&culture=da-DK"
        )
        catalogue[NAVIGATION_STATE_KEY]["body"] = [
            {
                "children": [
                    {
                        "url": empty_path,
                        "template": "modelSubpage",
                        "children": [],
                    },
                    {
                        "url": PRICE_PATH,
                        "template": "modelSubpage",
                        "children": [],
                    },
                ]
            }
        ]
        catalogue_html = (
            '<script id="terminalen-ncg-state" type="application/json">'
            f"{json.dumps(catalogue)}"
            "</script>"
        )
        empty_payload = json.loads(
            (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8")
        )
        empty_payload["url"] = empty_path
        empty_payload["grid"] = []
        del empty_payload["pimModelId"]
        del empty_payload["vehicleData"]
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: catalogue_html,
                empty_url: "<p>No current private lease offer.</p>",
                empty_api_url: json.dumps(empty_payload),
                PRICE_URL: (FIXTURES / "inster-price-page.html").read_text(
                    encoding="utf-8"
                ),
                API_URL: (FIXTURES / "inster-price-page.json").read_text(
                    encoding="utf-8"
                ),
            }
        )

        candidates = TerminalenAdapter(
            client, retrieved_at="2026-07-29T08:00:00Z"
        ).collect(CATALOGUE_URL)

        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            client.requested_urls,
            [
                CATALOGUE_URL,
                empty_url,
                empty_api_url,
                PRICE_URL,
                API_URL,
            ],
        )

    def test_collects_a_card_that_states_monthly_payment_below_upfront_heading(
        self,
    ) -> None:
        payload = json.loads(
            (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8")
        )
        private_content = payload["grid"][0]["content"]
        private_content.insert(
            2,
            {
                "alias": "imagetextpicker",
                "columns": [
                    {
                        "title": "IONIQ 5 Essential",
                        "text": "<p>Fra 279.995 kr. Inkl. standardudstyr.</p>",
                    }
                ],
            },
        )
        price_cards = private_content[3]["columns"]
        price_cards[1]["text"] = (
            "<h2>14.995 kr.</h2>"
            "<p>Månedlig ydelse fra 3.995 kr./md.<br>"
            "Periode: 36 mdr.<br>"
            "Samlet betaling i perioden: 159.595 kr.</p>"
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

        candidates = TerminalenAdapter(
            client, retrieved_at="2026-07-29T08:00:00Z"
        ).collect(CATALOGUE_URL)

        self.assertEqual(candidates[1]["advertisedMonthlyPayment"]["valueDkk"], 3995)
        self.assertEqual(candidates[1]["baseCashFlowStream"][0]["amountDkk"], 14995)

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
                                "url": (
                                    "https://user:password@www.terminalen.dk"
                                    "/nye-biler/hyundai/hyundai-inster/pris-og-udstyr"
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
        self.assertTrue(
            all("admissionOutcome" not in candidate for candidate in candidates)
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

        self.assertEqual(candidate["passengerCarScope"]["state"], "not_stated")
        self.assertNotIn("quarantineReasons", candidate)

    def test_uses_the_current_private_model_page_when_legacy_flags_are_absent(
        self,
    ) -> None:
        payload = json.loads(
            (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8")
        )
        del payload["vehicleData"]["vehicleType"]
        del payload["isCurrent"]
        payload["pimModelId"] = "HY_IONIQ5"
        payload["vehicleData"]["model"] = "IONIQ 5"
        payload["vehicleData"].update(
            {
                "bodyType": "SUV",
                "numberOfDoors": "5",
                "vehicleSeatingCapacity": "5",
            }
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
            client, retrieved_at="2026-07-29T08:00:00Z"
        ).collect(CATALOGUE_URL)[0]

        self.assertNotIn("admissionOutcome", candidate)
        self.assertEqual(candidate["passengerCarScope"]["state"], "known")
        self.assertEqual(
            candidate["passengerCarScope"]["evidence"]["wording"],
            '{"bodyType":"SUV"}',
        )
        self.assertEqual(candidate["currentAvailability"]["state"], "known")
        self.assertIn(
            '"template":"modelSubpage"',
            candidate["currentAvailability"]["evidence"]["wording"],
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

    def test_treats_an_unqualified_private_consumer_price_as_vat_inclusive(
        self,
    ) -> None:
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
                event["amountBasis"] == "including_vat"
                for event in candidate["baseCashFlowStream"]
            )
        )
        self.assertNotIn("admissionOutcome", candidate)
        self.assertNotIn("quarantineReasons", candidate)

    def test_quarantines_a_private_consumer_price_that_explicitly_excludes_vat(
        self,
    ) -> None:
        payload = json.loads(
            (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8")
        )
        legal = payload["grid"][0]["content"][3]
        legal["text"] = "<p>Alle beløb er ekskl. moms.</p>"
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

        self.assertTrue(
            all(
                event["amountBasis"] == "excluding_vat"
                for event in candidate["baseCashFlowStream"]
            )
        )
        self.assertNotIn("admissionOutcome", candidate)
        self.assertNotIn("quarantineReasons", candidate)

    def test_provider_candidate_marks_contradictory_vat_evidence_as_conflicting(
        self,
    ) -> None:
        payload = json.loads(
            (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8")
        )
        payload["grid"][0]["content"][3]["text"] = (
            "<p>Alle beløb er inkl. moms og ekskl. moms.</p>"
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

        candidates = TerminalenProviderAdapter(
            client, retrieved_at="2026-08-23T12:00:00Z"
        ).collect()

        self.assertTrue(
            all(
                candidate.admission_facts.private_consumer_eligibility.state == "known"
                for candidate in candidates
            )
        )
        self.assertIn(
            "inkl. moms og ekskl. moms",
            candidates[
                0
            ].admission_facts.private_consumer_amount_admissibility.evidence.wording,
        )
        self.assertTrue(
            all(
                candidate.admission_facts.private_consumer_amount_admissibility.state
                == "conflicting"
                for candidate in candidates
            )
        )

    def test_card_level_vat_exclusion_is_quarantined_as_amount_inadmissible(
        self,
    ) -> None:
        payload = json.loads(
            (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8")
        )
        payload["grid"][0]["content"][2]["columns"][0]["text"] += (
            "<p>Alle beløb er ekskl. moms.</p>"
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

        candidates = TerminalenProviderAdapter(
            client, retrieved_at="2026-08-23T12:00:00Z"
        ).collect()

        self.assertEqual(
            candidates[0].admission_facts.private_consumer_eligibility.state,
            "known",
        )
        self.assertEqual(
            candidates[0].admission_facts.private_consumer_amount_admissibility.state,
            "conflicting",
        )
        wording = candidates[
            0
        ].admission_facts.private_consumer_amount_admissibility.evidence.wording
        self.assertIn("ekskl. moms", wording)
        self.assertIn("inkl. moms", wording)

    def test_unsupported_terminalen_drivetrain_is_not_defaulted_to_gasoline(
        self,
    ) -> None:
        payload = json.loads(
            (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8")
        )
        payload["pimModelId"] = "HY_UNKNOWN"
        payload["vehicleData"]["model"] = "UNKNOWN MODEL"
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

        candidates = TerminalenProviderAdapter(
            client, retrieved_at="2026-08-23T12:00:00Z"
        ).collect()

        self.assertTrue(all(candidate.offer is None for candidate in candidates))

    def test_suv_fallback_is_unavailable_for_non_ioniq_5_models(self) -> None:
        payload = json.loads(
            (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8")
        )
        del payload["vehicleData"]["vehicleType"]
        payload["vehicleData"]["bodyType"] = "SUV"
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
            client, retrieved_at="2026-08-23T12:00:00Z"
        ).collect(CATALOGUE_URL)[0]

        self.assertEqual(candidate["passengerCarScope"]["state"], "unclear")

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

        self.assertEqual(candidate["passengerCarScope"]["state"], "unclear")
        self.assertEqual(candidate["currentAvailability"]["state"], "unclear")
        self.assertNotIn("admissionOutcome", candidate)
        self.assertNotIn("quarantineReasons", candidate)

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

    def test_offer_identity_is_stable_when_non_value_card_wording_changes(
        self,
    ) -> None:
        catalogue_html = (FIXTURES / "catalogue.html").read_text(encoding="utf-8")
        page_html = (FIXTURES / "inster-price-page.html").read_text(encoding="utf-8")
        original_payload = json.loads(
            (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8")
        )
        revised_payload = json.loads(json.dumps(original_payload))
        for column in revised_payload["grid"][0]["content"][2]["columns"]:
            column["text"] = column["text"].replace(
                "<p>", '<p><span class="campaign-note">Aktuel kampagne.</span>'
            )

        def collect(payload: dict[str, object]) -> list[str]:
            client = FixtureHttpClient(
                {
                    CATALOGUE_URL: catalogue_html,
                    PRICE_URL: page_html,
                    API_URL: json.dumps(payload),
                }
            )
            return [
                candidate["offerIdentity"]
                for candidate in TerminalenAdapter(
                    client, retrieved_at="2026-08-23T12:00:00Z"
                ).collect(CATALOGUE_URL)
            ]

        self.assertEqual(collect(revised_payload), collect(original_payload))

    def test_collects_all_in_scope_model_pages_in_navigation_order(self) -> None:
        second_path = "/nye-biler/hyundai/hyundai-ioniq-5/pris-og-udstyr"
        second_url = f"https://www.terminalen.dk{second_path}"
        second_api_url = (
            f"https://www.terminalen.dk/api/page/url?url={second_path}&culture=da-DK"
        )
        navigation = {
            NAVIGATION_STATE_KEY: {
                "body": [
                    {
                        "children": [
                            {
                                "url": PRICE_PATH,
                                "template": "modelSubpage",
                                "children": [],
                            },
                            {
                                "url": "/nye-biler/kia/kia-ev3/pris-og-udstyr",
                                "template": "modelSubpage",
                                "children": [],
                            },
                            {
                                "url": second_path,
                                "template": "modelSubpage",
                                "children": [],
                            },
                            {
                                "url": PRICE_PATH,
                                "template": "modelSubpage",
                                "children": [],
                            },
                        ]
                    }
                ]
            }
        }
        catalogue_html = (
            '<script id="terminalen-ncg-state" type="application/json">'
            f"{json.dumps(navigation)}"
            "</script>"
        )
        second_payload = json.loads(
            (FIXTURES / "inster-price-page.json").read_text(encoding="utf-8")
        )
        second_payload["url"] = second_path
        second_payload["pimModelId"] = "HY_IONIQ5"
        second_payload["vehicleData"]["model"] = "IONIQ 5"
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: catalogue_html,
                PRICE_URL: (FIXTURES / "inster-price-page.html").read_text(
                    encoding="utf-8"
                ),
                API_URL: (FIXTURES / "inster-price-page.json").read_text(
                    encoding="utf-8"
                ),
                second_url: (FIXTURES / "inster-price-page.html").read_text(
                    encoding="utf-8"
                ),
                second_api_url: json.dumps(second_payload),
            }
        )

        candidates = TerminalenProviderAdapter(
            client, retrieved_at="2026-08-23T12:00:00Z"
        ).collect()

        self.assertEqual(
            [candidate.offer_identity for candidate in candidates],
            [
                "terminalen:HY_INSTER:private-2f775a9b781a",
                "terminalen:HY_INSTER:private-e25cc77f6e4b",
                "terminalen:HY_IONIQ5:private-2f775a9b781a",
                "terminalen:HY_IONIQ5:private-e25cc77f6e4b",
            ],
        )
        self.assertEqual(
            client.requested_urls,
            [
                CATALOGUE_URL,
                PRICE_URL,
                API_URL,
                second_url,
                second_api_url,
            ],
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
