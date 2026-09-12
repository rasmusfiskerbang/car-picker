from __future__ import annotations

import unittest
from pathlib import Path

from car_picker.fleasing import (
    FleasingAdapter,
    StructuralSourceError,
    catalogue_detail_offers,
    catalogue_detail_urls,
    map_detail_page,
)
from car_picker.provider_scope import FLEASING_FLEXLEASING_URL


FIXTURE_DIRECTORY = Path(__file__).resolve().parent / "fixtures/fleasing"
CATALOGUE_URL = "https://fleasing.dk/biler/"
DETAIL_URL = "https://fleasing.dk/bil/?aston-martin-db9-volante-aut&vid=442795427"
MISSING_MONTHLY_DETAIL_URL = "https://fleasing.dk/bil/?bmw-i4&vid=771869804"
MULTI_CONFIGURATION_DETAIL_URL = "https://fleasing.dk/bil/?porsche-taycan&vid=982451736"


class FixtureHttpClient:
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.requested_urls: list[str] = []

    def get_text(self, url: str) -> str:
        self.requested_urls.append(url)
        if url == FLEASING_FLEXLEASING_URL:
            return (FIXTURE_DIRECTORY / "flexleasing.html").read_text(encoding="utf-8")
        return self.responses[url]


class FleasingAdapterTest(unittest.TestCase):
    def test_collects_vehicle_fuel_from_the_current_short_specs_shape(self) -> None:
        current_catalogue = (
            '<a href="/biler/">Personbiler</a>'
            '<a href="/bil/?aston-martin-db9-volante-aut&amp;vid=442795427">'
            "Aston Martin DB9</a>"
        )
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: current_catalogue,
                DETAIL_URL: (FIXTURE_DIRECTORY / "current-detail.html").read_text(
                    encoding="utf-8"
                ),
            }
        )

        candidates = FleasingAdapter(
            client, retrieved_at="2026-08-24T06:00:00Z"
        ).collect()

        self.assertEqual(
            candidates[0]["vehicleSpecification"],
            {
                "state": "known",
                "value": {
                    "make": "Aston Martin",
                    "model": "DB9",
                    "trim": "Volante aut.",
                    "drivetrain": "gasoline",
                },
                "evidence": {
                    "sourceUrl": DETAIL_URL,
                    "wording": "Aston Martin DB9 Volante aut.; Brændstof: Benzin",
                },
            },
        )

    def test_preserves_legacy_drivetrain_source_wording(self) -> None:
        catalogue_html = f'<a href="{DETAIL_URL}">Aston Martin DB9</a>'
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: catalogue_html,
                DETAIL_URL: (FIXTURE_DIRECTORY / "aston-martin-db9.html").read_text(
                    encoding="utf-8"
                ),
            }
        )

        candidate = FleasingAdapter(
            client, retrieved_at="2026-07-22T12:00:00Z"
        ).collect()[0]

        self.assertEqual(
            candidate["vehicleSpecification"]["evidence"],
            {
                "sourceUrl": DETAIL_URL,
                "wording": "Aston Martin DB9 Volante aut.; Drivmiddel Benzin",
            },
        )

    def test_preserves_source_wording_for_unclear_and_conflicting_drivetrains(
        self,
    ) -> None:
        cases = (
            (
                "<dt>Drivmiddel</dt><dd>Hybrid</dd>",
                "unclear",
                "Drivmiddel Hybrid",
            ),
            (
                "<dt>Drivmiddel</dt><dd>Benzin</dd>"
                '<div class="vehicle-page-short-specs">'
                "<span><b>Brændstof:</b> Diesel</span></div>",
                "conflicting",
                "Drivmiddel Benzin; Brændstof: Diesel",
            ),
        )

        for drivetrain_markup, state, wording in cases:
            with self.subTest(state=state):
                detail_html = f"""
                    <div class="vehicle-page-info">
                      <h1>Aston Martin DB9</h1><h3>Volante aut.</h3>
                      <dl>{drivetrain_markup}</dl>
                      <div id="privat">
                        <h2>Privatleasing · inkl. moms</h2>
                        <ul>
                          <li>Ydelse pr. måned 15.865 kr. /inkl. moms</li>
                          <li>Udbetaling 142.813 kr. /inkl. moms</li>
                          <li>Leasingperiode 12</li>
                        </ul>
                      </div>
                    </div>
                """
                client = FixtureHttpClient(
                    {
                        CATALOGUE_URL: f'<a href="{DETAIL_URL}">DB9</a>',
                        DETAIL_URL: detail_html,
                    }
                )

                candidate = FleasingAdapter(
                    client, retrieved_at="2026-08-24T06:00:00Z"
                ).collect()[0]

                self.assertEqual(
                    candidate["vehicleSpecification"],
                    {
                        "state": state,
                        "evidence": {"sourceUrl": DETAIL_URL, "wording": wording},
                    },
                )

    def test_ignores_catalogue_links_to_an_undesignated_host(self) -> None:
        detail_urls = catalogue_detail_urls(
            """
            <a href="/bil/?a&amp;vid=442795427">Fleasing</a>
            <a href="https://bilinfo.dk/bil/?a&amp;vid=999">Bilinfo</a>
            """,
            CATALOGUE_URL,
        )

        self.assertEqual(detail_urls, ["https://fleasing.dk/bil/?a&vid=442795427"])

    def test_collects_each_private_vat_inclusive_configuration_with_evidence(
        self,
    ) -> None:
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: (FIXTURE_DIRECTORY / "catalogue.html").read_text(
                    encoding="utf-8"
                ),
                DETAIL_URL: (FIXTURE_DIRECTORY / "aston-martin-db9.html").read_text(
                    encoding="utf-8"
                ),
                MISSING_MONTHLY_DETAIL_URL: (
                    FIXTURE_DIRECTORY / "bmw-i4.html"
                ).read_text(encoding="utf-8"),
            }
        )

        candidates = FleasingAdapter(
            client, retrieved_at="2026-07-22T12:00:00Z"
        ).collect()

        self.assertEqual(
            client.requested_urls,
            [
                CATALOGUE_URL,
                FLEASING_FLEXLEASING_URL,
                DETAIL_URL,
                MISSING_MONTHLY_DETAIL_URL,
            ],
        )
        self.assertEqual(
            [candidate["offerIdentity"] for candidate in candidates],
            [
                "fleasing:442795427:private-b3e29d362bda",
                "fleasing:771869804:private-390493d196b5",
            ],
        )
        candidate = candidates[0]
        self.assertEqual(candidate["advertisedMonthlyPayment"]["valueDkk"], 15865)
        self.assertEqual(candidate["termMonths"]["value"], 12)
        self.assertIsNone(candidate["baseCashFlowBlockers"])
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
        self.assertEqual(
            candidate["vehicleSpecification"]["value"],
            {
                "make": "Aston Martin",
                "model": "DB9",
                "trim": "Volante aut.",
                "drivetrain": "gasoline",
            },
        )
        self.assertEqual(
            candidate["advertisedMonthlyPayment"]["evidence"],
            {
                "sourceUrl": DETAIL_URL,
                "wording": "Ydelse pr. måned 15.865 kr. /inkl. moms",
            },
        )
        self.assertEqual(
            candidate["sourceMetadata"]["parserVersion"], "fleasing-html-v7"
        )
        self.assertEqual(
            len(candidate["sourceMetadata"]["documents"][0]["contentSha256"]), 64
        )
        self.assertEqual(
            candidate["privateConsumerEligibility"]["evidence"],
            {
                "sourceUrl": DETAIL_URL,
                "wording": "12 måneders privatleasing",
            },
        )
        self.assertEqual(
            candidate["passengerCarScope"]["evidence"],
            {
                "sourceUrl": CATALOGUE_URL,
                "wording": 'href="/biler/" Personbiler',
            },
        )
        self.assertEqual(
            candidate["supportedLeasingForm"],
            {
                "state": "known",
                "value": "financial",
                "evidence": {
                    "sourceUrl": FLEASING_FLEXLEASING_URL,
                    "wording": (
                        "Du kan se vores aktuelle udvalg af flexleasing biler på "
                        "vores hjemmeside; Privatleasing (operationel leasing) og "
                        "flexleasing (finansiel leasing)"
                    ),
                },
            },
        )
        self.assertEqual(
            candidate["normalEndMechanism"],
            {
                "state": "known",
                "value": "designate_third_party_buyer",
                "evidence": {
                    "sourceUrl": FLEASING_FLEXLEASING_URL,
                    "wording": (
                        "Til gengæld har du selv ansvar for at sælge bilen efter "
                        "endt leasingperiode, medmindre du selv vil købe bilen"
                    ),
                },
            },
        )
        self.assertNotIn("quarantineReasons", candidate)
        self.assertNotIn("quarantineReasons", candidates[1])
        self.assertEqual(candidates[1]["baseCashFlowStream"][1]["amountDkk"], None)
        self.assertEqual(
            candidates[1]["baseCashFlowStream"][1]["blockingFacts"],
            ["advertisedMonthlyPayment"],
        )

    def test_unqualified_private_consumer_payments_are_vat_inclusive(self) -> None:
        catalogue_html = f"""
            <a href="/biler/">Personbiler</a>
            <a href="{DETAIL_URL}">Aston Martin DB9</a>
        """
        detail_html = (FIXTURE_DIRECTORY / "aston-martin-db9.html").read_text(
            encoding="utf-8"
        )
        detail_html = detail_html.replace(
            "Ydelse pr. måned 15.865 kr. /inkl. moms",
            "Ydelse pr. måned 15.865 kr.",
        ).replace(
            "Udbetaling 142.813 kr. /inkl. moms",
            "Udbetaling 142.813 kr.",
        )
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: catalogue_html,
                DETAIL_URL: detail_html,
            }
        )

        candidate = FleasingAdapter(
            client, retrieved_at="2026-07-29T12:00:00Z"
        ).collect()[0]

        self.assertNotIn("admissionOutcome", candidate)
        self.assertEqual(candidate["advertisedMonthlyPayment"]["valueDkk"], 15865)
        self.assertEqual(
            [event["amountBasis"] for event in candidate["baseCashFlowStream"]],
            ["including_vat", "including_vat"],
        )

    def test_explicitly_vat_excluding_private_payments_are_quarantined(self) -> None:
        catalogue_html = f"""
            <a href="/biler/">Personbiler</a>
            <a href="{DETAIL_URL}">Aston Martin DB9</a>
        """
        detail_html = (FIXTURE_DIRECTORY / "aston-martin-db9.html").read_text(
            encoding="utf-8"
        )
        detail_html = detail_html.replace(
            "Ydelse pr. måned 15.865 kr. /inkl. moms",
            "Ydelse pr. måned 15.865 kr. /ex. moms",
        ).replace(
            "Udbetaling 142.813 kr. /inkl. moms",
            "Udbetaling 142.813 kr. /ex. moms",
        )
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: catalogue_html,
                DETAIL_URL: detail_html,
            }
        )

        candidate = FleasingAdapter(
            client, retrieved_at="2026-07-29T12:00:00Z"
        ).collect()[0]

        self.assertEqual(candidate["advertisedMonthlyPayment"]["state"], "conflicting")
        self.assertNotIn("quarantineReasons", candidate)

    def test_collects_each_explicit_private_configuration_as_an_admitted_offer(
        self,
    ) -> None:
        catalogue_html = f"""
            <a href="{MULTI_CONFIGURATION_DETAIL_URL}">Porsche Taycan</a>
        """
        detail_html = (
            FIXTURE_DIRECTORY / "porsche-taycan-configurations.html"
        ).read_text(encoding="utf-8")
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: catalogue_html,
                MULTI_CONFIGURATION_DETAIL_URL: detail_html,
            }
        )

        candidates = FleasingAdapter(
            client, retrieved_at="2026-07-28T12:00:00Z"
        ).collect()

        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            [
                (
                    candidate["sourceLocalConfigurationKey"],
                    candidate["advertisedMonthlyPayment"]["valueDkk"],
                    candidate["termMonths"]["value"],
                )
                for candidate in candidates
            ],
            [
                ("private-standard", 9995, 12),
                ("private-low-upfront", 11995, 12),
            ],
        )
        for candidate in candidates:
            self.assertEqual(
                candidate["privateConsumerEligibility"],
                {
                    "state": "known",
                    "value": True,
                    "evidence": {
                        "sourceUrl": MULTI_CONFIGURATION_DETAIL_URL,
                        "wording": "Privatleasing · inkl. moms",
                    },
                },
            )
            self.assertEqual(
                candidate["passengerCarScope"],
                {
                    "state": "known",
                    "value": True,
                    "evidence": {
                        "sourceUrl": MULTI_CONFIGURATION_DETAIL_URL,
                        "wording": "Køretøjstype Personbil",
                    },
                },
            )
            self.assertEqual(
                candidate["supportedLeasingForm"],
                {
                    "state": "known",
                    "value": "financial",
                    "evidence": {
                        "sourceUrl": MULTI_CONFIGURATION_DETAIL_URL,
                        "wording": "Leasingform Finansiel leasing",
                    },
                },
            )
            self.assertEqual(
                candidate["currentAvailability"]["evidence"]["sourceUrl"],
                CATALOGUE_URL,
            )

    def test_quarantines_a_catalogue_link_when_its_detail_page_loses_private_pricing(
        self,
    ) -> None:
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: (FIXTURE_DIRECTORY / "catalogue.html").read_text(
                    encoding="utf-8"
                ),
                DETAIL_URL: """
                    <article data-offer-id="442795427" data-make="Aston Martin" data-model="DB9"
                    data-trim="Volante" data-passenger-car="true" data-availability="available"></article>
                """,
                MISSING_MONTHLY_DETAIL_URL: (
                    FIXTURE_DIRECTORY / "bmw-i4.html"
                ).read_text(encoding="utf-8"),
            }
        )

        candidates = FleasingAdapter(
            client, retrieved_at="2026-07-22T12:00:00Z"
        ).collect()

        self.assertEqual(
            client.requested_urls,
            [
                CATALOGUE_URL,
                FLEASING_FLEXLEASING_URL,
                DETAIL_URL,
                MISSING_MONTHLY_DETAIL_URL,
            ],
        )
        self.assertEqual(
            [candidate["offerIdentity"] for candidate in candidates],
            [
                "fleasing:442795427:detail-unavailable",
                "fleasing:771869804:private-390493d196b5",
            ],
        )
        stale_candidate = candidates[0]
        self.assertEqual(stale_candidate["vehicleSpecification"]["state"], "not_stated")
        self.assertEqual(stale_candidate["currentAvailability"]["state"], "unclear")
        self.assertEqual(
            stale_candidate["advertisedMonthlyPayment"]["state"], "not_stated"
        )
        self.assertEqual(stale_candidate["termMonths"]["state"], "not_stated")
        self.assertNotIn("quarantineReasons", stale_candidate)

    def test_quarantines_conflicting_admission_evidence_without_choosing_a_value(
        self,
    ) -> None:
        catalogue_html = f"""
            <a href="{MULTI_CONFIGURATION_DETAIL_URL}">Porsche Taycan</a>
        """
        detail_html = """
            <div class="vehicle-page-info">
              <h1>Porsche Taycan</h1><h3>Performance Plus</h3>
              <dl>
                <dt>Køretøjstype</dt><dd>Personbil</dd>
                <dt>Køretøjstype</dt><dd>Varebil</dd>
                <dt>Leasingform</dt><dd>Finansiel leasing</dd>
                <dt>Leasingform</dt><dd>Operationel leasing</dd>
              </dl>
              <div id="privat">
                <h2>Privatleasing · inkl. moms</h2>
                <ul data-configuration-id="conflicting">
                  <li>Ydelse pr. måned 9.995 kr. /inkl. moms</li>
                  <li>Udbetaling 149.995 kr. /inkl. moms</li>
                  <li>Leasingperiode 12</li>
                </ul>
              </div>
            </div>
        """
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: catalogue_html,
                MULTI_CONFIGURATION_DETAIL_URL: detail_html,
            }
        )

        [candidate] = FleasingAdapter(
            client, retrieved_at="2026-07-28T12:00:00Z"
        ).collect()

        self.assertEqual(candidate["passengerCarScope"]["state"], "conflicting")
        self.assertEqual(candidate["supportedLeasingForm"]["state"], "conflicting")
        self.assertNotIn("quarantineReasons", candidate)

    def test_quarantines_duplicate_configuration_ids_without_collapsing_candidates(
        self,
    ) -> None:
        catalogue_html = f"""
            <a href="{MULTI_CONFIGURATION_DETAIL_URL}">Porsche Taycan</a>
        """
        detail_html = """
            <div class="vehicle-page-info">
              <h1>Porsche Taycan</h1><h3>Performance Plus</h3>
              <dl>
                <dt>Køretøjstype</dt><dd>Personbil</dd>
                <dt>Leasingform</dt><dd>Finansiel leasing</dd>
              </dl>
              <div id="privat">
                <h2>Privatleasing · inkl. moms</h2>
                <ul data-configuration-id="duplicate">
                  <li>Ydelse pr. måned 9.995 kr. /inkl. moms</li>
                  <li>Udbetaling 149.995 kr. /inkl. moms</li>
                  <li>Leasingperiode 12</li>
                </ul>
                <ul data-configuration-id="duplicate">
                  <li>Ydelse pr. måned 11.995 kr. /inkl. moms</li>
                  <li>Udbetaling 99.995 kr. /inkl. moms</li>
                  <li>Leasingperiode 12</li>
                </ul>
              </div>
            </div>
        """
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: catalogue_html,
                MULTI_CONFIGURATION_DETAIL_URL: detail_html,
            }
        )

        candidates = FleasingAdapter(
            client, retrieved_at="2026-07-28T12:00:00Z"
        ).collect()

        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            len({candidate["offerIdentity"] for candidate in candidates}), 2
        )
        for candidate in candidates:
            self.assertNotIn("admissionOutcome", candidate)
            self.assertNotIn("quarantineReasons", candidate)

    def test_private_tab_without_explicit_vat_inclusive_heading_is_quarantined(
        self,
    ) -> None:
        catalogue_html = f"""
            <a href="{MULTI_CONFIGURATION_DETAIL_URL}">Porsche Taycan</a>
        """
        detail_html = (
            FIXTURE_DIRECTORY / "porsche-taycan-configurations.html"
        ).read_text(encoding="utf-8")
        detail_html = detail_html.replace("<h2>Privatleasing · inkl. moms</h2>", "")
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: catalogue_html,
                MULTI_CONFIGURATION_DETAIL_URL: detail_html,
            }
        )

        candidates = FleasingAdapter(
            client, retrieved_at="2026-07-28T12:00:00Z"
        ).collect()

        for candidate in candidates:
            self.assertEqual(
                candidate["privateConsumerEligibility"]["state"], "not_stated"
            )
            self.assertNotIn("admissionOutcome", candidate)
            self.assertNotIn("quarantineReasons", candidate)

    def test_quarantines_identical_configurations_without_source_ids_as_distinct_candidates(
        self,
    ) -> None:
        catalogue_html = f"""
            <a href="{MULTI_CONFIGURATION_DETAIL_URL}">Porsche Taycan</a>
        """
        configuration = """
            <ul>
              <li>Ydelse pr. måned 9.995 kr. /inkl. moms</li>
              <li>Udbetaling 149.995 kr. /inkl. moms</li>
              <li>Leasingperiode 12</li>
            </ul>
        """
        detail_html = f"""
            <div class="vehicle-page-info">
              <h1>Porsche Taycan</h1><h3>Performance Plus</h3>
              <dl>
                <dt>Køretøjstype</dt><dd>Personbil</dd>
                <dt>Leasingform</dt><dd>Finansiel leasing</dd>
              </dl>
              <div id="privat">
                <h2>Privatleasing · inkl. moms</h2>
                {configuration}
                {configuration}
              </div>
            </div>
        """
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: catalogue_html,
                MULTI_CONFIGURATION_DETAIL_URL: detail_html,
            }
        )

        candidates = FleasingAdapter(
            client, retrieved_at="2026-07-28T12:00:00Z"
        ).collect()

        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            len({candidate["offerIdentity"] for candidate in candidates}), 2
        )
        for candidate in candidates:
            self.assertNotIn("admissionOutcome", candidate)
            self.assertNotIn("quarantineReasons", candidate)

    def test_detects_a_detail_page_that_loses_the_private_configuration_structure(
        self,
    ) -> None:
        catalogue_html = (FIXTURE_DIRECTORY / "catalogue.html").read_text(
            encoding="utf-8"
        )
        first_offer = catalogue_detail_offers(catalogue_html, CATALOGUE_URL)[0]

        with self.assertRaisesRegex(StructuralSourceError, "private-pricing tab"):
            map_detail_page(
                catalogue_url=CATALOGUE_URL,
                catalogue_html=catalogue_html,
                discovered_offer=first_offer,
                detail_html="""
                    <article data-offer-id="442795427" data-make="Aston Martin" data-model="DB9"
                    data-trim="Volante" data-passenger-car="true" data-availability="available"></article>
                """,
                retrieved_at="2026-07-22T12:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
